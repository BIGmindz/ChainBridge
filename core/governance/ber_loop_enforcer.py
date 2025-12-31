"""
ChainBridge BER Loop Enforcer — Mandatory BER Issuance AND Emission
════════════════════════════════════════════════════════════════════════════════

Enforces deterministic WRAP → BER routing AND external emission.
Prevents "awaiting BER" limbo state AND silent internal completion.

PAC References:
- PAC-BENSON-EXEC-GOVERNANCE-BER-LOOP-ENFORCEMENT-020
- PAC-BENSON-EXEC-GOVERNANCE-BER-EMISSION-ENFORCEMENT-021 (supersedes)

Effective Date: 2025-12-26

ENFORCEMENT RULES:
- WRAP_RECEIVED → BER_REQUIRED (state transition)
- Session cannot complete without BER
- BER issuance is synchronous, not deferred
- Only GID-00 (ORCHESTRATION_ENGINE) may issue BER

PAC-021 ADDITIONS:
- BER must be externally EMITTED (not just issued)
- BER artifact must be RETURNED to caller
- Drafting surfaces prohibited from BER flow
- INV-BER-007: BER_ISSUED → BER_EMITTED

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from core.governance.system_identities import (
    ORCHESTRATION_ENGINE,
    validate_ber_authority,
    BERAuthorityError,
    SystemIdentityType,
)
from core.governance.terminal_gates import (
    BORDER_CHAR,
    BORDER_WIDTH,
    FAIL_SYMBOL,
    PASS_SYMBOL,
    TerminalGateRenderer,
    get_terminal_renderer,
)

if TYPE_CHECKING:
    from core.governance.pac_schema import BERStatus, WRAPStatus


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class BERLoopError(Exception):
    """Base exception for BER loop enforcement errors."""
    pass


class BERNotIssuedError(BERLoopError):
    """
    Raised when BER is not issued for a received WRAP.
    
    This error indicates a governance violation:
    - WRAP was received
    - BER was not issued
    - Session cannot complete validly
    """
    
    def __init__(self, pac_id: str, reason: str = None):
        self.pac_id = pac_id
        self.reason = reason or "BER not issued after WRAP received"
        super().__init__(
            f"BER_NOT_ISSUED: PAC {pac_id} — {self.reason}. "
            f"WRAP cannot exist without BER. Session invalid."
        )


class SessionInvalidError(BERLoopError):
    """
    Raised when session cannot be completed validly.
    
    Terminal states:
    - BER_ISSUED: Valid completion
    - SESSION_INVALID: Invalid (this error)
    """
    
    def __init__(self, pac_id: str, reason: str = None):
        self.pac_id = pac_id
        self.reason = reason or "Session terminated due to governance violation"
        super().__init__(
            f"SESSION_INVALID: PAC {pac_id} — {self.reason}"
        )


class BERRequiredError(BERLoopError):
    """
    Raised when attempting to complete session without BER.
    
    BER_REQUIRED is a non-terminal state. Session cannot end here.
    """
    
    def __init__(self, pac_id: str):
        self.pac_id = pac_id
        super().__init__(
            f"BER_REQUIRED: PAC {pac_id} cannot complete session. "
            f"BER must be issued before session can close."
        )


class WRAPNotRoutedError(BERLoopError):
    """
    Raised when WRAP is not routed to ORCHESTRATION_ENGINE.
    
    All WRAPs must be processed by ORCHESTRATION_ENGINE.
    """
    
    def __init__(self, pac_id: str):
        self.pac_id = pac_id
        super().__init__(
            f"WRAP_NOT_ROUTED: PAC {pac_id} WRAP not routed to ORCHESTRATION_ENGINE. "
            f"Drafting surface cannot consume WRAP directly."
        )


class BERNotEmittedError(BERLoopError):
    """
    Raised when BER is issued but not emitted externally.
    
    PAC-021 INV-BER-007: BER must be externally emitted.
    Internal BER without emission = SESSION_INVALID.
    """
    
    def __init__(self, pac_id: str):
        self.pac_id = pac_id
        super().__init__(
            f"BER_NOT_EMITTED: PAC {pac_id} — BER was issued but not emitted. "
            f"Violation of INV-BER-007. Session invalid. "
            f"Loop closure requires external emission."
        )


class DraftingSurfaceInBERFlowError(BERLoopError):
    """
    Raised when drafting surface appears in BER flow.
    
    PAC-021 INV-BER-008: Drafting surfaces prohibited from BER flow.
    Only ORCHESTRATION_ENGINE may process BER.
    """
    
    def __init__(self, pac_id: str, operation: str):
        self.pac_id = pac_id
        self.operation = operation
        super().__init__(
            f"DRAFTING_SURFACE_IN_BER_FLOW: PAC {pac_id} — "
            f"Drafting surface cannot {operation}. "
            f"Only ORCHESTRATION_ENGINE may process BER."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

class SessionState(Enum):
    """
    Session state machine.
    
    Valid terminal states:
    - BER_ISSUED
    - SESSION_INVALID
    
    Non-terminal states:
    - PAC_RECEIVED
    - PAC_DISPATCHED
    - EXECUTING
    - WRAP_RECEIVED
    - BER_REQUIRED (CANNOT terminate here)
    """
    
    # Initial states
    PAC_RECEIVED = "PAC_RECEIVED"
    PAC_DISPATCHED = "PAC_DISPATCHED"
    
    # Execution states
    EXECUTING = "EXECUTING"
    
    # Post-WRAP states
    WRAP_RECEIVED = "WRAP_RECEIVED"
    BER_REQUIRED = "BER_REQUIRED"  # Non-terminal!
    
    # BER states (PAC-021)
    BER_ISSUED = "BER_ISSUED"  # Internal only, non-terminal without emission!
    BER_EMITTED = "BER_EMITTED"  # External emission complete
    
    # Terminal states (valid)
    SESSION_COMPLETE = "SESSION_COMPLETE"
    
    # Terminal states (invalid)
    SESSION_INVALID = "SESSION_INVALID"
    REJECTED = "REJECTED"


# Terminal state sets (PAC-021: BER_EMITTED is required for valid completion)
VALID_TERMINAL_STATES = frozenset({
    SessionState.BER_EMITTED,  # PAC-021: Emission required
    SessionState.SESSION_COMPLETE,
    SessionState.REJECTED,
})

INVALID_TERMINAL_STATES = frozenset({
    SessionState.SESSION_INVALID,
})

ALL_TERMINAL_STATES = VALID_TERMINAL_STATES | INVALID_TERMINAL_STATES

# PAC-021: BER_ISSUED without emission is NON-TERMINAL
NON_TERMINAL_STATES = frozenset({
    SessionState.PAC_RECEIVED,
    SessionState.PAC_DISPATCHED,
    SessionState.EXECUTING,
    SessionState.WRAP_RECEIVED,
    SessionState.BER_REQUIRED,
    SessionState.BER_ISSUED,  # PAC-021: Must emit to complete
})


def is_terminal_state(state: SessionState) -> bool:
    """Check if state is terminal."""
    return state in ALL_TERMINAL_STATES


def is_valid_terminal_state(state: SessionState) -> bool:
    """Check if state is a valid terminal state."""
    return state in VALID_TERMINAL_STATES


def is_invalid_terminal_state(state: SessionState) -> bool:
    """Check if state is an invalid terminal state."""
    return state in INVALID_TERMINAL_STATES


# ═══════════════════════════════════════════════════════════════════════════════
# BER ARTIFACT (PAC-021)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BERArtifact:
    """
    Immutable BER artifact returned to external caller.
    
    PAC-021: BER must be externally emitted AND returned.
    This artifact proves emission occurred.
    """
    
    pac_id: str
    decision: str  # APPROVE, CORRECTIVE, REJECT
    issuer: str  # Always "GID-00"
    issued_at: str
    emitted_at: str
    wrap_status: str
    session_state: str  # BER_EMITTED or SESSION_INVALID
    
    @property
    def is_approved(self) -> bool:
        """True if BER decision is APPROVE."""
        return self.decision == "APPROVE"
    
    @property
    def is_emitted(self) -> bool:
        """True if BER was emitted."""
        return self.session_state == "BER_EMITTED"


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION RECORD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SessionRecord:
    """
    Record of a PAC session with state tracking.
    """
    
    pac_id: str
    state: SessionState = SessionState.PAC_RECEIVED
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dispatched_at: Optional[str] = None
    wrap_received_at: Optional[str] = None
    ber_required_at: Optional[str] = None
    ber_issued_at: Optional[str] = None
    ber_emitted_at: Optional[str] = None  # PAC-021: Emission timestamp
    completed_at: Optional[str] = None
    
    # WRAP info
    wrap_status: Optional[str] = None
    wrap_from_gid: Optional[str] = None
    
    # BER info
    ber_status: Optional[str] = None
    ber_issuer: str = "GID-00"  # Only ORCHESTRATION_ENGINE
    ber_emitted: bool = False  # PAC-021: Emission tracking
    
    # Error info
    error: Optional[str] = None
    
    @property
    def is_terminal(self) -> bool:
        """True if session is in terminal state."""
        return is_terminal_state(self.state)
    
    @property
    def is_valid_terminal(self) -> bool:
        """True if session completed validly."""
        return is_valid_terminal_state(self.state)
    
    @property
    def is_ber_required(self) -> bool:
        """True if BER is required but not yet issued."""
        return self.state == SessionState.BER_REQUIRED
    
    @property
    def is_ber_issued_not_emitted(self) -> bool:
        """True if BER issued but not yet emitted (PAC-021 violation state)."""
        return self.state == SessionState.BER_ISSUED and not self.ber_emitted
    
    @property
    def can_complete(self) -> bool:
        """True if session can complete (BER emitted or rejected)."""
        # PAC-021: Must be EMITTED, not just ISSUED
        return self.state in {SessionState.BER_EMITTED, SessionState.REJECTED}
    
    def transition_to(self, new_state: SessionState) -> None:
        """
        Transition to new state with validation.
        
        Raises SessionInvalidError if transition is invalid.
        """
        # Cannot transition from terminal state
        if self.is_terminal:
            raise SessionInvalidError(
                self.pac_id,
                f"Cannot transition from terminal state {self.state.value}",
            )
        
        # Cannot skip BER_REQUIRED
        if (
            self.state == SessionState.WRAP_RECEIVED
            and new_state not in {SessionState.BER_REQUIRED, SessionState.SESSION_INVALID}
        ):
            raise SessionInvalidError(
                self.pac_id,
                f"Must transition through BER_REQUIRED after WRAP_RECEIVED",
            )
        
        # Cannot skip BER_ISSUED
        if (
            self.state == SessionState.BER_REQUIRED
            and new_state not in {SessionState.BER_ISSUED, SessionState.SESSION_INVALID}
        ):
            raise BERRequiredError(self.pac_id)
        
        # PAC-021: Cannot skip BER_EMITTED (must emit before completing)
        if (
            self.state == SessionState.BER_ISSUED
            and new_state not in {SessionState.BER_EMITTED, SessionState.SESSION_INVALID}
        ):
            raise BERNotEmittedError(self.pac_id)
        
        self.state = new_state
        
        # Record timestamps
        now = datetime.now(timezone.utc).isoformat()
        if new_state == SessionState.PAC_DISPATCHED:
            self.dispatched_at = now
        elif new_state == SessionState.WRAP_RECEIVED:
            self.wrap_received_at = now
        elif new_state == SessionState.BER_REQUIRED:
            self.ber_required_at = now
        elif new_state == SessionState.BER_ISSUED:
            self.ber_issued_at = now
        elif new_state == SessionState.BER_EMITTED:
            self.ber_emitted_at = now
            self.ber_emitted = True
        elif new_state == SessionState.SESSION_COMPLETE:
            self.completed_at = now


# ═══════════════════════════════════════════════════════════════════════════════
# BER LOOP ENFORCER TERMINAL RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class BERLoopTerminalRenderer:
    """
    Terminal renderer for BER loop enforcement operations.
    """
    
    def __init__(self, renderer: TerminalGateRenderer = None):
        self._renderer = renderer or get_terminal_renderer()
    
    def _emit(self, text: str) -> None:
        """Emit text via base renderer."""
        self._renderer._emit(text)
    
    def emit_wrap_routing(self, pac_id: str, from_gid: str = None) -> None:
        """Emit WRAP routing notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("📥 WRAP RECEIVED — ROUTING TO ORCHESTRATION ENGINE")
        self._emit(f"   PAC_ID: {pac_id}")
        if from_gid:
            self._emit(f"   FROM: {from_gid}")
        self._emit("   ROUTING: ORCHESTRATION_ENGINE (GID-00)")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ber_required(self, pac_id: str) -> None:
        """Emit BER required notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🧠 ORCHESTRATION ENGINE REVIEWING WRAP")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit("   STATE: BER_REQUIRED")
        self._emit("   ACTION: SYNCHRONOUS_BER_PROCESSING")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ber_issued_loop_closed(
        self,
        pac_id: str,
        ber_status: str,
    ) -> None:
        """Emit BER issued and loop closed notification."""
        symbol = PASS_SYMBOL if ber_status == "APPROVE" else "⚠️"
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"🟩 BER ISSUED — LOOP CLOSED {symbol}")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   DECISION: {ber_status}")
        self._emit("   ISSUER: GID-00 (ORCHESTRATION_ENGINE)")
        self._emit("   STATE: SESSION_COMPLETE")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ber_missing_session_invalid(
        self,
        pac_id: str,
        reason: str = None,
    ) -> None:
        """Emit BER missing and session terminated notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"🟥 BER MISSING — SESSION TERMINATED {FAIL_SYMBOL}")
        self._emit(f"   PAC_ID: {pac_id}")
        if reason:
            self._emit(f"   REASON: {reason}")
        self._emit("   STATE: SESSION_INVALID")
        self._emit("   VIOLATION: WRAP_WITHOUT_BER")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_session_state_transition(
        self,
        pac_id: str,
        from_state: SessionState,
        to_state: SessionState,
    ) -> None:
        """Emit state transition notification."""
        self._emit(f"   STATE: {from_state.value} → {to_state.value}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAC-021: BER EMISSION TERMINAL EMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def emit_ber_emitting(self, pac_id: str, ber_status: str) -> None:
        """Emit BER emission in progress notification (INV-BER-007)."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("📤 BER EMISSION IN PROGRESS")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   DECISION: {ber_status}")
        self._emit("   STATE: BER_ISSUED → BER_EMITTED")
        self._emit("   CONSTRAINT: INV-BER-007 (MUST_EMIT)")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ber_emitted_success(
        self,
        pac_id: str,
        ber_status: str,
        artifact_id: str,
    ) -> None:
        """Emit BER emitted successfully notification (INV-BER-007 satisfied)."""
        symbol = PASS_SYMBOL if ber_status == "APPROVE" else "⚠️"
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"✅ BER EMITTED — LOOP CLOSED {symbol}")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   DECISION: {ber_status}")
        self._emit(f"   ARTIFACT_ID: {artifact_id}")
        self._emit("   ISSUER: GID-00 (ORCHESTRATION_ENGINE)")
        self._emit("   STATE: BER_EMITTED")
        self._emit("   CONSTRAINT: INV-BER-007 ✓ SATISFIED")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ber_not_emitted_violation(
        self,
        pac_id: str,
        reason: str = None,
    ) -> None:
        """Emit BER not emitted violation notification (INV-BER-007 violated)."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"🟥 BER NOT EMITTED — VIOLATION {FAIL_SYMBOL}")
        self._emit(f"   PAC_ID: {pac_id}")
        if reason:
            self._emit(f"   REASON: {reason}")
        self._emit("   STATE: SESSION_INVALID")
        self._emit("   VIOLATION: INV-BER-007 (BER_ISSUED_NOT_EMITTED)")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_drafting_surface_violation(
        self,
        pac_id: str,
        surface_id: str,
    ) -> None:
        """Emit drafting surface in BER flow violation (INV-BER-008)."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"🟥 DRAFTING SURFACE IN BER FLOW — VIOLATION {FAIL_SYMBOL}")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   SURFACE_ID: {surface_id}")
        self._emit("   VIOLATION: INV-BER-008 (DRAFTING_SURFACE_PROHIBITED)")
        self._emit("   AUTHORITY: ONLY ORCHESTRATION_ENGINE MAY EMIT BER")
        self._emit(BORDER_CHAR * BORDER_WIDTH)


# ═══════════════════════════════════════════════════════════════════════════════
# BER LOOP ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class BERLoopEnforcer:
    """
    Enforces mandatory BER loop closure.
    
    Key behaviors:
    - WRAP_RECEIVED → BER_REQUIRED (automatic)
    - Session cannot complete without BER
    - BER issuance is synchronous
    - Only ORCHESTRATION_ENGINE (GID-00) may issue BER
    
    PAC Reference: PAC-020
    """
    
    def __init__(
        self,
        renderer: BERLoopTerminalRenderer = None,
        emit_terminal: bool = True,
    ):
        self._renderer = renderer or BERLoopTerminalRenderer()
        self._emit_terminal = emit_terminal
        
        # Active sessions (pac_id -> SessionRecord)
        self._sessions: Dict[str, SessionRecord] = {}
        
        # BER processing callback
        self._ber_processor: Optional[Callable[[str, str], str]] = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_session(self, pac_id: str) -> SessionRecord:
        """Create new session record."""
        session = SessionRecord(pac_id=pac_id)
        self._sessions[pac_id] = session
        return session
    
    def get_session(self, pac_id: str) -> Optional[SessionRecord]:
        """Get session record."""
        return self._sessions.get(pac_id)
    
    def require_session(self, pac_id: str) -> SessionRecord:
        """Get session, raising if not found."""
        session = self._sessions.get(pac_id)
        if session is None:
            raise ValueError(f"Unknown session: {pac_id}")
        return session
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE TRANSITIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def dispatch(self, pac_id: str) -> SessionRecord:
        """Record PAC dispatch."""
        session = self._sessions.get(pac_id)
        if session is None:
            session = self.create_session(pac_id)
        
        session.transition_to(SessionState.PAC_DISPATCHED)
        return session
    
    def receive_wrap(
        self,
        pac_id: str,
        wrap_status: str,
        from_gid: str = None,
    ) -> SessionRecord:
        """
        Record WRAP receipt and IMMEDIATELY transition to BER_REQUIRED.
        
        This method enforces synchronous BER processing.
        """
        session = self.require_session(pac_id)
        
        # Record WRAP
        session.wrap_status = wrap_status
        session.wrap_from_gid = from_gid
        session.transition_to(SessionState.WRAP_RECEIVED)
        
        if self._emit_terminal:
            self._renderer.emit_wrap_routing(pac_id, from_gid)
        
        # IMMEDIATELY transition to BER_REQUIRED
        session.transition_to(SessionState.BER_REQUIRED)
        
        if self._emit_terminal:
            self._renderer.emit_ber_required(pac_id)
        
        return session
    
    def require_ber(self, pac_id: str) -> SessionRecord:
        """
        Ensure session is in BER_REQUIRED state.
        
        Called after WRAP receipt to enforce BER obligation.
        """
        session = self.require_session(pac_id)
        
        if session.state == SessionState.WRAP_RECEIVED:
            session.transition_to(SessionState.BER_REQUIRED)
        
        if session.state != SessionState.BER_REQUIRED:
            raise SessionInvalidError(
                pac_id,
                f"Expected BER_REQUIRED, got {session.state.value}",
            )
        
        return session
    
    def issue_ber(
        self,
        pac_id: str,
        ber_status: str,
        issuer_gid: str = "GID-00",
    ) -> SessionRecord:
        """
        Issue BER for session.
        
        ONLY GID-00 (ORCHESTRATION_ENGINE) may issue BER.
        """
        # Validate authority
        if issuer_gid != "GID-00":
            # Determine identity type based on GID pattern
            if issuer_gid.startswith("GID-"):
                id_type = SystemIdentityType.AGENT
            elif issuer_gid == "DRAFTING_SURFACE":
                id_type = SystemIdentityType.DRAFTING_SURFACE
            else:
                id_type = SystemIdentityType.AGENT  # Default to AGENT for unknown
            raise BERAuthorityError(issuer_gid, id_type)
        
        session = self.require_session(pac_id)
        
        # Must be in BER_REQUIRED state
        if session.state != SessionState.BER_REQUIRED:
            if session.state == SessionState.WRAP_RECEIVED:
                # Auto-transition through BER_REQUIRED
                session.transition_to(SessionState.BER_REQUIRED)
            else:
                raise SessionInvalidError(
                    pac_id,
                    f"Cannot issue BER from state {session.state.value}",
                )
        
        # Record BER
        session.ber_status = ber_status
        session.ber_issuer = issuer_gid
        session.transition_to(SessionState.BER_ISSUED)
        
        if self._emit_terminal:
            self._renderer.emit_ber_issued_loop_closed(pac_id, ber_status)
        
        return session
    
    def emit_ber(
        self,
        pac_id: str,
        issuer_gid: str = "GID-00",
    ) -> BERArtifact:
        """
        Emit BER for session (PAC-021: INV-BER-007).
        
        BER issuance is internal; emission is external.
        This method transitions from BER_ISSUED → BER_EMITTED.
        
        ONLY GID-00 (ORCHESTRATION_ENGINE) may emit BER.
        
        Returns:
            BERArtifact proving emission occurred
        
        Raises:
            BERNotIssuedError: If BER not yet issued
            BERAuthorityError: If caller is not GID-00
            DraftingSurfaceInBERFlowError: If drafting surface attempts emission
        """
        # Validate authority
        if issuer_gid != "GID-00":
            if issuer_gid == "DRAFTING_SURFACE" or "DRAFTING" in issuer_gid.upper():
                if self._emit_terminal:
                    self._renderer.emit_drafting_surface_violation(pac_id, issuer_gid)
                raise DraftingSurfaceInBERFlowError(pac_id, issuer_gid)
            
            if issuer_gid.startswith("GID-"):
                id_type = SystemIdentityType.AGENT
            else:
                id_type = SystemIdentityType.AGENT
            raise BERAuthorityError(issuer_gid, id_type)
        
        session = self.require_session(pac_id)
        
        # Must be in BER_ISSUED state
        if session.state != SessionState.BER_ISSUED:
            if session.state == SessionState.BER_REQUIRED:
                raise BERNotIssuedError(
                    pac_id,
                    f"BER not yet issued for {pac_id}",
                )
            raise SessionInvalidError(
                pac_id,
                f"Cannot emit BER from state {session.state.value}",
            )
        
        if self._emit_terminal:
            self._renderer.emit_ber_emitting(pac_id, session.ber_status)
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Create artifact
        artifact = BERArtifact(
            pac_id=pac_id,
            decision=session.ber_status,
            issuer=session.ber_issuer,
            issued_at=session.ber_issued_at or now,
            emitted_at=now,
            wrap_status=session.wrap_status or "UNKNOWN",
            session_state="BER_EMITTED",
        )
        
        # Transition to emitted
        session.transition_to(SessionState.BER_EMITTED)
        
        if self._emit_terminal:
            self._renderer.emit_ber_emitted_success(
                pac_id, session.ber_status, f"BER-{pac_id}"
            )
        
        return artifact
    
    def issue_and_emit_ber(
        self,
        pac_id: str,
        ber_status: str,
        issuer_gid: str = "GID-00",
    ) -> BERArtifact:
        """
        Issue AND emit BER in single operation (PAC-021 compliant).
        
        This is the primary method for BER processing.
        Guarantees both issuance AND emission occur atomically.
        
        Returns:
            BERArtifact proving emission occurred
        """
        # Issue BER
        self.issue_ber(pac_id, ber_status, issuer_gid)
        
        # Emit BER (returns artifact)
        return self.emit_ber(pac_id, issuer_gid)
    
    def complete_session(self, pac_id: str) -> SessionRecord:
        """
        Complete session.
        
        Raises BERRequiredError if BER not issued.
        Raises BERNotEmittedError if BER issued but not emitted (PAC-021).
        """
        session = self.require_session(pac_id)
        
        if not session.can_complete:
            if session.is_ber_required:
                raise BERRequiredError(pac_id)
            # PAC-021: Check for BER_ISSUED without emission
            if session.is_ber_issued_not_emitted:
                raise BERNotEmittedError(pac_id)
            raise SessionInvalidError(
                pac_id,
                f"Cannot complete session from state {session.state.value}",
            )
        
        if session.state == SessionState.BER_EMITTED:
            session.transition_to(SessionState.SESSION_COMPLETE)
        
        return session
    
    def invalidate_session(
        self,
        pac_id: str,
        reason: str = None,
    ) -> SessionRecord:
        """
        Invalidate session.
        
        Used when BER cannot be issued.
        """
        session = self.require_session(pac_id)
        
        session.error = reason
        session.state = SessionState.SESSION_INVALID  # Direct assignment for invalid
        
        if self._emit_terminal:
            self._renderer.emit_ber_missing_session_invalid(pac_id, reason)
        
        return session
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYNCHRONOUS WRAP → BER PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_wrap_synchronously(
        self,
        pac_id: str,
        wrap_status: str,
        from_gid: str = None,
        ber_processor: Callable[[str, str], str] = None,
    ) -> BERArtifact:
        """
        Process WRAP to BER synchronously (PAC-021 compliant).
        
        This is the primary entry point for WRAP processing.
        Guarantees BER issuance AND emission, or session invalidation.
        
        Args:
            pac_id: PAC identifier
            wrap_status: WRAP status (COMPLETE, PARTIAL, etc.)
            from_gid: Source GID (agent)
            ber_processor: Optional callback to determine BER status
        
        Returns:
            BERArtifact proving emission occurred
        
        Raises:
            Various governance exceptions on failure
        """
        try:
            # 1. Receive WRAP (transitions to BER_REQUIRED)
            session = self.receive_wrap(pac_id, wrap_status, from_gid)
            
            # 2. Determine BER status
            if ber_processor:
                ber_status = ber_processor(pac_id, wrap_status)
            elif self._ber_processor:
                ber_status = self._ber_processor(pac_id, wrap_status)
            else:
                # Default: APPROVE for COMPLETE, CORRECTIVE otherwise
                ber_status = "APPROVE" if wrap_status == "COMPLETE" else "CORRECTIVE"
            
            # 3. Issue AND emit BER (PAC-021: must emit, not just issue)
            artifact = self.issue_and_emit_ber(pac_id, ber_status)
            
            return artifact
            
        except Exception as e:
            # If anything fails, invalidate session
            self.invalidate_session(pac_id, str(e))
            raise
    
    def set_ber_processor(
        self,
        processor: Callable[[str, str], str],
    ) -> None:
        """
        Set BER processing callback.
        
        Callback receives (pac_id, wrap_status) and returns ber_status.
        """
        self._ber_processor = processor
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENFORCEMENT QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_ber_required_sessions(self) -> List[SessionRecord]:
        """Get all sessions awaiting BER."""
        return [
            s for s in self._sessions.values()
            if s.is_ber_required
        ]
    
    def get_invalid_sessions(self) -> List[SessionRecord]:
        """Get all invalid sessions."""
        return [
            s for s in self._sessions.values()
            if s.state == SessionState.SESSION_INVALID
        ]
    
    def get_open_sessions(self) -> List[SessionRecord]:
        """Get all non-terminal sessions."""
        return [
            s for s in self._sessions.values()
            if not s.is_terminal
        ]
    
    def has_ber_required(self) -> bool:
        """True if any sessions awaiting BER."""
        return any(s.is_ber_required for s in self._sessions.values())
    
    def enforce_no_ber_required(self) -> None:
        """
        Enforce that no sessions are awaiting BER.
        
        Raises BERNotIssuedError if any sessions in BER_REQUIRED state.
        """
        ber_required = self.get_ber_required_sessions()
        if ber_required:
            pac_ids = [s.pac_id for s in ber_required]
            raise BERNotIssuedError(
                pac_ids[0],
                f"Sessions awaiting BER: {pac_ids}",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_enforcer: Optional[BERLoopEnforcer] = None


def get_ber_loop_enforcer() -> BERLoopEnforcer:
    """Get singleton BER loop enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = BERLoopEnforcer()
    return _enforcer


def reset_ber_loop_enforcer() -> None:
    """Reset singleton (for testing)."""
    global _enforcer
    _enforcer = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def process_wrap_to_ber(
    pac_id: str,
    wrap_status: str,
    from_gid: str = None,
) -> BERArtifact:
    """
    Process WRAP to BER synchronously (PAC-021 compliant).
    
    Guarantees BER issuance AND emission.
    Returns BERArtifact proving emission occurred.
    """
    return get_ber_loop_enforcer().process_wrap_synchronously(
        pac_id, wrap_status, from_gid
    )


def enforce_ber_issued(pac_id: str) -> SessionRecord:
    """
    Enforce that BER has been issued for session.
    
    Raises BERRequiredError if BER not issued.
    """
    session = get_ber_loop_enforcer().require_session(pac_id)
    if session.is_ber_required:
        raise BERRequiredError(pac_id)
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Exceptions
    "BERLoopError",
    "BERNotIssuedError",
    "BERNotEmittedError",
    "DraftingSurfaceInBERFlowError",
    "SessionInvalidError",
    "BERRequiredError",
    "WRAPNotRoutedError",
    
    # State
    "SessionState",
    "VALID_TERMINAL_STATES",
    "INVALID_TERMINAL_STATES",
    "ALL_TERMINAL_STATES",
    "NON_TERMINAL_STATES",
    "is_terminal_state",
    "is_valid_terminal_state",
    "is_invalid_terminal_state",
    
    # Artifacts (PAC-021)
    "BERArtifact",
    
    # Records
    "SessionRecord",
    
    # Renderer
    "BERLoopTerminalRenderer",
    
    # Enforcer
    "BERLoopEnforcer",
    
    # Singleton
    "get_ber_loop_enforcer",
    "reset_ber_loop_enforcer",
    
    # Convenience
    "process_wrap_to_ber",
    "enforce_ber_issued",
]
