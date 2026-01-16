"""
Escalation State Machine (ESM)
PAC-JEFFREY-CTRLPLANE-REPLACEMENT-R2-001 | Task 1

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true
SUPERSEDES: authority_lattice.py (P1)

Authority is STATE, not ATTRIBUTE.
The ESM defines explicit, deterministic state transitions.
No implicit authority — all escalation follows the state graph.

STATE GRAPH:
  NOMINAL → REQUESTING → GRANTED → ACTIVE → EXPIRING → TERMINATED
                ↓            ↓         ↓
             DENIED      REVOKED    SCRAM_HALT

INVARIANTS ENFORCED:
- INV-EXPLICIT-TRANSITIONS: No implicit state changes
- INV-SCRAM-HALT: SCRAM forces immediate SCRAM_HALT state
- INV-TERMINAL-STATES: TERMINATED/DENIED/REVOKED are final
- INV-NO-BACKWARD: Cannot transition to previous states

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)


# =============================================================================
# SECTION 1: CONSTANTS
# =============================================================================

VERSION: Final[str] = "2.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-CTRLPLANE-REPLACEMENT-R2-001"
SUPERSEDES: Final[str] = "PAC-JEFFREY-CTRLPLANE-HARDENING-P1-001"

# Timing
TRANSITION_TIMEOUT_MS: Final[int] = 100
STATE_TTL_CHECK_INTERVAL_MS: Final[int] = 1000

# Invariants
INV_EXPLICIT_TRANSITIONS: Final[str] = "INV-EXPLICIT-TRANSITIONS"
INV_SCRAM_HALT: Final[str] = "INV-SCRAM-HALT"
INV_TERMINAL_STATES: Final[str] = "INV-TERMINAL-STATES"
INV_NO_BACKWARD: Final[str] = "INV-NO-BACKWARD"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class ESMState(Enum):
    """
    Escalation State Machine states.
    
    Authority is represented as discrete states, not continuous values.
    """
    # Initial state
    NOMINAL = 0          # No escalation, baseline authority
    
    # Transition states
    REQUESTING = 1       # Escalation requested, pending approval
    GRANTED = 2          # Escalation granted, not yet active
    ACTIVE = 3           # Escalation active, authority elevated
    EXPIRING = 4         # Within expiration window
    
    # Terminal states (no exit)
    TERMINATED = 10      # Normal termination (TTL expired)
    DENIED = 11          # Request denied
    REVOKED = 12         # Revoked by authority
    SCRAM_HALT = 13      # SCRAM-forced halt (highest priority)
    
    @property
    def is_terminal(self) -> bool:
        """Check if state is terminal (no transitions out)."""
        return self.value >= 10
    
    @property
    def has_authority(self) -> bool:
        """Check if state grants elevated authority."""
        return self in (ESMState.ACTIVE, ESMState.EXPIRING)


class TransitionResult(Enum):
    """Result of state transition attempt."""
    SUCCESS = auto()           # Transition completed
    INVALID_TRANSITION = auto() # Not a valid transition
    TERMINAL_STATE = auto()    # Cannot exit terminal state
    SCRAM_OVERRIDE = auto()    # SCRAM forced transition
    TIMEOUT = auto()           # Transition timed out
    PRECONDITION_FAILED = auto() # Precondition not met


class TransitionTrigger(Enum):
    """What triggered the transition."""
    REQUEST = auto()           # Principal requested
    APPROVAL = auto()          # Authority approved
    DENIAL = auto()            # Authority denied
    ACTIVATION = auto()        # Grant activated
    TTL_WARNING = auto()       # Approaching expiration
    TTL_EXPIRED = auto()       # TTL expired
    REVOCATION = auto()        # Manual revocation
    SCRAM = auto()             # SCRAM triggered
    RESET = auto()             # System reset (after terminal)


# =============================================================================
# SECTION 3: STATE TRANSITION MATRIX
# =============================================================================

# Valid transitions: (from_state, to_state) -> trigger
VALID_TRANSITIONS: Dict[Tuple[ESMState, ESMState], TransitionTrigger] = {
    # From NOMINAL
    (ESMState.NOMINAL, ESMState.REQUESTING): TransitionTrigger.REQUEST,
    (ESMState.NOMINAL, ESMState.SCRAM_HALT): TransitionTrigger.SCRAM,
    
    # From REQUESTING
    (ESMState.REQUESTING, ESMState.GRANTED): TransitionTrigger.APPROVAL,
    (ESMState.REQUESTING, ESMState.DENIED): TransitionTrigger.DENIAL,
    (ESMState.REQUESTING, ESMState.SCRAM_HALT): TransitionTrigger.SCRAM,
    
    # From GRANTED
    (ESMState.GRANTED, ESMState.ACTIVE): TransitionTrigger.ACTIVATION,
    (ESMState.GRANTED, ESMState.REVOKED): TransitionTrigger.REVOCATION,
    (ESMState.GRANTED, ESMState.SCRAM_HALT): TransitionTrigger.SCRAM,
    
    # From ACTIVE
    (ESMState.ACTIVE, ESMState.EXPIRING): TransitionTrigger.TTL_WARNING,
    (ESMState.ACTIVE, ESMState.REVOKED): TransitionTrigger.REVOCATION,
    (ESMState.ACTIVE, ESMState.SCRAM_HALT): TransitionTrigger.SCRAM,
    
    # From EXPIRING
    (ESMState.EXPIRING, ESMState.TERMINATED): TransitionTrigger.TTL_EXPIRED,
    (ESMState.EXPIRING, ESMState.REVOKED): TransitionTrigger.REVOCATION,
    (ESMState.EXPIRING, ESMState.SCRAM_HALT): TransitionTrigger.SCRAM,
}

# States that SCRAM can reach from ANY state
SCRAM_REACHABLE: FrozenSet[ESMState] = frozenset([
    ESMState.NOMINAL,
    ESMState.REQUESTING,
    ESMState.GRANTED,
    ESMState.ACTIVE,
    ESMState.EXPIRING,
])


# =============================================================================
# SECTION 4: DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class ESMTransition:
    """
    Immutable record of a state transition.
    """
    transition_id: str
    session_id: str
    principal_id: str
    from_state: ESMState
    to_state: ESMState
    trigger: TransitionTrigger
    result: TransitionResult
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "session_id": self.session_id,
            "principal_id": self.principal_id,
            "from_state": self.from_state.name,
            "to_state": self.to_state.name,
            "trigger": self.trigger.name,
            "result": self.result.name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ESMSession:
    """
    Escalation session tracking state and history.
    """
    session_id: str
    principal_id: str
    current_state: ESMState
    created_at: datetime
    last_transition_at: Optional[datetime]
    ttl_expires_at: Optional[datetime]
    transition_count: int = 0
    history: List[ESMTransition] = field(default_factory=list)
    
    @property
    def has_authority(self) -> bool:
        return self.current_state.has_authority
    
    @property
    def is_terminal(self) -> bool:
        return self.current_state.is_terminal
    
    @property
    def is_expired(self) -> bool:
        if not self.ttl_expires_at:
            return False
        return datetime.now(timezone.utc) >= self.ttl_expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "principal_id": self.principal_id,
            "current_state": self.current_state.name,
            "created_at": self.created_at.isoformat(),
            "last_transition_at": self.last_transition_at.isoformat() if self.last_transition_at else None,
            "ttl_expires_at": self.ttl_expires_at.isoformat() if self.ttl_expires_at else None,
            "transition_count": self.transition_count,
            "has_authority": self.has_authority,
            "is_terminal": self.is_terminal,
        }


# =============================================================================
# SECTION 5: ESCALATION STATE MACHINE
# =============================================================================

class EscalationStateMachine:
    """
    Escalation State Machine (ESM).
    
    Manages authority through explicit, deterministic state transitions.
    No implicit authority changes — all escalation follows the state graph.
    
    INVARIANTS:
    - INV-EXPLICIT-TRANSITIONS: All transitions explicit
    - INV-SCRAM-HALT: SCRAM forces SCRAM_HALT state
    - INV-TERMINAL-STATES: Terminal states have no exit
    - INV-NO-BACKWARD: Cannot go to previous states
    """
    
    def __init__(self) -> None:
        self._sessions: Dict[str, ESMSession] = {}
        self._principal_sessions: Dict[str, str] = {}  # principal -> session_id
        self._scram_active = False
        self._transition_log: List[ESMTransition] = []
        self._lock = threading.Lock()
    
    @property
    def scram_active(self) -> bool:
        return self._scram_active
    
    def create_session(self, principal_id: str) -> ESMSession:
        """
        Create new escalation session for principal.
        
        Sessions start in NOMINAL state.
        """
        with self._lock:
            # Check for existing active session
            if principal_id in self._principal_sessions:
                existing_id = self._principal_sessions[principal_id]
                existing = self._sessions.get(existing_id)
                if existing and not existing.is_terminal:
                    return existing
            
            session_id = f"ESM-{uuid.uuid4().hex[:12].upper()}"
            session = ESMSession(
                session_id=session_id,
                principal_id=principal_id,
                current_state=ESMState.NOMINAL,
                created_at=datetime.now(timezone.utc),
                last_transition_at=None,
                ttl_expires_at=None,
            )
            
            self._sessions[session_id] = session
            self._principal_sessions[principal_id] = session_id
            
            return session
    
    def get_session(self, session_id: str) -> Optional[ESMSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    def get_principal_session(self, principal_id: str) -> Optional[ESMSession]:
        """Get active session for principal."""
        session_id = self._principal_sessions.get(principal_id)
        if session_id:
            return self._sessions.get(session_id)
        return None
    
    def transition(
        self,
        session_id: str,
        target_state: ESMState,
        trigger: TransitionTrigger,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TransitionResult, str, Optional[ESMTransition]]:
        """
        Attempt state transition.
        
        Returns (result, message, transition_record).
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return (TransitionResult.INVALID_TRANSITION, 
                        f"Session not found: {session_id}", None)
            
            # Check terminal state (INV-TERMINAL-STATES)
            if session.is_terminal:
                return (TransitionResult.TERMINAL_STATE,
                        f"Cannot exit terminal state: {session.current_state.name}", None)
            
            # SCRAM override (INV-SCRAM-HALT)
            if self._scram_active and target_state != ESMState.SCRAM_HALT:
                return self._force_scram_halt(session)
            
            # Validate transition (INV-EXPLICIT-TRANSITIONS)
            transition_key = (session.current_state, target_state)
            if transition_key not in VALID_TRANSITIONS:
                return (TransitionResult.INVALID_TRANSITION,
                        f"Invalid transition: {session.current_state.name} → {target_state.name}", None)
            
            # Check trigger matches
            expected_trigger = VALID_TRANSITIONS[transition_key]
            if trigger != expected_trigger:
                return (TransitionResult.PRECONDITION_FAILED,
                        f"Wrong trigger: expected {expected_trigger.name}, got {trigger.name}", None)
            
            # Execute transition
            return self._execute_transition(
                session, target_state, trigger, ttl_seconds, metadata or {}
            )
    
    def _execute_transition(
        self,
        session: ESMSession,
        target_state: ESMState,
        trigger: TransitionTrigger,
        ttl_seconds: Optional[int],
        metadata: Dict[str, Any],
    ) -> Tuple[TransitionResult, str, ESMTransition]:
        """Execute validated transition."""
        now = datetime.now(timezone.utc)
        from_state = session.current_state
        
        # Create transition record
        transition = ESMTransition(
            transition_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            session_id=session.session_id,
            principal_id=session.principal_id,
            from_state=from_state,
            to_state=target_state,
            trigger=trigger,
            result=TransitionResult.SUCCESS,
            timestamp=now,
            metadata=metadata,
        )
        
        # Update session
        session.current_state = target_state
        session.last_transition_at = now
        session.transition_count += 1
        session.history.append(transition)
        
        # Set TTL if entering ACTIVE state
        if target_state == ESMState.ACTIVE and ttl_seconds:
            session.ttl_expires_at = now + timedelta(seconds=ttl_seconds)
        
        # Log transition
        self._transition_log.append(transition)
        
        return (TransitionResult.SUCCESS,
                f"Transition: {from_state.name} → {target_state.name}",
                transition)
    
    def _force_scram_halt(
        self,
        session: ESMSession,
    ) -> Tuple[TransitionResult, str, ESMTransition]:
        """Force session to SCRAM_HALT state."""
        now = datetime.now(timezone.utc)
        from_state = session.current_state
        
        transition = ESMTransition(
            transition_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
            session_id=session.session_id,
            principal_id=session.principal_id,
            from_state=from_state,
            to_state=ESMState.SCRAM_HALT,
            trigger=TransitionTrigger.SCRAM,
            result=TransitionResult.SCRAM_OVERRIDE,
            timestamp=now,
            metadata={"forced": True, "scram_active": True},
        )
        
        session.current_state = ESMState.SCRAM_HALT
        session.last_transition_at = now
        session.transition_count += 1
        session.history.append(transition)
        self._transition_log.append(transition)
        
        return (TransitionResult.SCRAM_OVERRIDE,
                "SCRAM forced transition to SCRAM_HALT",
                transition)
    
    def request_escalation(
        self,
        principal_id: str,
        justification: str = "",
    ) -> Tuple[TransitionResult, str, Optional[ESMSession]]:
        """
        Request escalation for principal.
        
        Creates session if needed, transitions to REQUESTING.
        """
        session = self.create_session(principal_id)
        
        if session.current_state != ESMState.NOMINAL:
            return (TransitionResult.INVALID_TRANSITION,
                    f"Cannot request from state: {session.current_state.name}",
                    session)
        
        result, msg, _ = self.transition(
            session.session_id,
            ESMState.REQUESTING,
            TransitionTrigger.REQUEST,
            metadata={"justification": justification},
        )
        
        return (result, msg, session)
    
    def approve_escalation(
        self,
        session_id: str,
        ttl_seconds: int,
        approved_by: str,
    ) -> Tuple[TransitionResult, str]:
        """
        Approve pending escalation request.
        
        Transitions REQUESTING → GRANTED.
        """
        session = self._sessions.get(session_id)
        if not session:
            return (TransitionResult.INVALID_TRANSITION, "Session not found")
        
        if session.current_state != ESMState.REQUESTING:
            return (TransitionResult.INVALID_TRANSITION,
                    f"Cannot approve from state: {session.current_state.name}")
        
        result, msg, _ = self.transition(
            session_id,
            ESMState.GRANTED,
            TransitionTrigger.APPROVAL,
            metadata={"approved_by": approved_by, "ttl_seconds": ttl_seconds},
        )
        
        if result == TransitionResult.SUCCESS:
            # Auto-activate
            result, msg, _ = self.transition(
                session_id,
                ESMState.ACTIVE,
                TransitionTrigger.ACTIVATION,
                ttl_seconds=ttl_seconds,
            )
        
        return (result, msg)
    
    def deny_escalation(
        self,
        session_id: str,
        denied_by: str,
        reason: str = "",
    ) -> Tuple[TransitionResult, str]:
        """Deny pending escalation request."""
        result, msg, _ = self.transition(
            session_id,
            ESMState.DENIED,
            TransitionTrigger.DENIAL,
            metadata={"denied_by": denied_by, "reason": reason},
        )
        return (result, msg)
    
    def revoke_escalation(
        self,
        session_id: str,
        revoked_by: str,
        reason: str = "",
    ) -> Tuple[TransitionResult, str]:
        """Revoke active escalation."""
        result, msg, _ = self.transition(
            session_id,
            ESMState.REVOKED,
            TransitionTrigger.REVOCATION,
            metadata={"revoked_by": revoked_by, "reason": reason},
        )
        return (result, msg)
    
    def check_expiration(self, session_id: str) -> Tuple[bool, str]:
        """
        Check and handle TTL expiration.
        
        Returns (expired, message).
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return (False, "Session not found")
            
            if session.current_state == ESMState.ACTIVE:
                if session.is_expired:
                    # Transition to EXPIRING then TERMINATED
                    self.transition(
                        session_id,
                        ESMState.EXPIRING,
                        TransitionTrigger.TTL_WARNING,
                    )
                    self.transition(
                        session_id,
                        ESMState.TERMINATED,
                        TransitionTrigger.TTL_EXPIRED,
                    )
                    return (True, "Session terminated due to TTL expiration")
            
            return (False, "Session not expired")
    
    def activate_scram(self) -> int:
        """
        Activate SCRAM — force all active sessions to SCRAM_HALT.
        
        Returns count of affected sessions.
        """
        with self._lock:
            self._scram_active = True
            affected = 0
            
            for session in self._sessions.values():
                if session.current_state in SCRAM_REACHABLE:
                    self._force_scram_halt(session)
                    affected += 1
            
            return affected
    
    def deactivate_scram(self, authorization_code: str) -> bool:
        """Deactivate SCRAM."""
        if len(authorization_code) < 16:
            return False
        
        with self._lock:
            self._scram_active = False
            return True
    
    def has_authority(self, principal_id: str) -> bool:
        """Check if principal has elevated authority."""
        session = self.get_principal_session(principal_id)
        if not session:
            return False
        
        # Check expiration first
        if session.current_state == ESMState.ACTIVE and session.is_expired:
            self.check_expiration(session.session_id)
            return False
        
        return session.has_authority
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ESM statistics."""
        state_counts = {state.name: 0 for state in ESMState}
        for session in self._sessions.values():
            state_counts[session.current_state.name] += 1
        
        return {
            "total_sessions": len(self._sessions),
            "total_transitions": len(self._transition_log),
            "scram_active": self._scram_active,
            "state_distribution": state_counts,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "statistics": self.get_statistics(),
            "scram_active": self._scram_active,
        }


# =============================================================================
# SECTION 6: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    import time
    
    print("=" * 72)
    print("  ESCALATION STATE MACHINE (R2) - SELF-TEST")
    print("  PAC-JEFFREY-CTRLPLANE-REPLACEMENT-R2-001 | Task 1")
    print("  SUPERSEDES: authority_lattice.py (P1)")
    print("=" * 72)
    
    tests_passed = 0
    tests_failed = 0
    
    def test(name: str, condition: bool, msg: str = "") -> None:
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✓ {name}")
            tests_passed += 1
        else:
            print(f"  ✗ {name}: {msg}")
            tests_failed += 1
    
    # Test 1: State Properties
    print("\n[1] ESM State Tests")
    test("NOMINAL is not terminal", not ESMState.NOMINAL.is_terminal)
    test("TERMINATED is terminal", ESMState.TERMINATED.is_terminal)
    test("SCRAM_HALT is terminal", ESMState.SCRAM_HALT.is_terminal)
    test("ACTIVE has authority", ESMState.ACTIVE.has_authority)
    test("NOMINAL has no authority", not ESMState.NOMINAL.has_authority)
    test("TERMINATED has no authority", not ESMState.TERMINATED.has_authority)
    
    # Test 2: Session Creation
    print("\n[2] Session Creation Tests")
    esm = EscalationStateMachine()
    session = esm.create_session("USER-001")
    test("Session created", session is not None)
    test("Session starts NOMINAL", session.current_state == ESMState.NOMINAL)
    test("Session has no authority", not session.has_authority)
    test("Session not terminal", not session.is_terminal)
    
    # Test 3: Valid Transition Path
    print("\n[3] Valid Transition Path Tests")
    result, msg, _ = esm.transition(
        session.session_id,
        ESMState.REQUESTING,
        TransitionTrigger.REQUEST,
    )
    test("NOMINAL → REQUESTING", result == TransitionResult.SUCCESS)
    test("State is REQUESTING", session.current_state == ESMState.REQUESTING)
    
    result, msg, _ = esm.transition(
        session.session_id,
        ESMState.GRANTED,
        TransitionTrigger.APPROVAL,
    )
    test("REQUESTING → GRANTED", result == TransitionResult.SUCCESS)
    
    result, msg, _ = esm.transition(
        session.session_id,
        ESMState.ACTIVE,
        TransitionTrigger.ACTIVATION,
        ttl_seconds=3600,
    )
    test("GRANTED → ACTIVE", result == TransitionResult.SUCCESS)
    test("Has authority when ACTIVE", session.has_authority)
    test("TTL set", session.ttl_expires_at is not None)
    
    # Test 4: Invalid Transitions (INV-EXPLICIT-TRANSITIONS)
    print("\n[4] Invalid Transition Tests")
    result, msg, _ = esm.transition(
        session.session_id,
        ESMState.NOMINAL,  # Cannot go backward
        TransitionTrigger.RESET,
    )
    test("Cannot go backward", result == TransitionResult.INVALID_TRANSITION)
    
    result, msg, _ = esm.transition(
        session.session_id,
        ESMState.DENIED,  # Not valid from ACTIVE
        TransitionTrigger.DENIAL,
    )
    test("Invalid from ACTIVE", result == TransitionResult.INVALID_TRANSITION)
    
    # Test 5: Wrong Trigger
    print("\n[5] Wrong Trigger Tests")
    esm2 = EscalationStateMachine()
    session2 = esm2.create_session("USER-002")
    
    result, msg, _ = esm2.transition(
        session2.session_id,
        ESMState.REQUESTING,
        TransitionTrigger.APPROVAL,  # Wrong trigger (should be REQUEST)
    )
    test("Wrong trigger rejected", result == TransitionResult.PRECONDITION_FAILED)
    
    # Test 6: Terminal States (INV-TERMINAL-STATES)
    print("\n[6] Terminal State Tests")
    esm3 = EscalationStateMachine()
    session3 = esm3.create_session("USER-003")
    
    # Move to DENIED (terminal)
    esm3.transition(session3.session_id, ESMState.REQUESTING, TransitionTrigger.REQUEST)
    esm3.transition(session3.session_id, ESMState.DENIED, TransitionTrigger.DENIAL)
    
    test("DENIED is terminal", session3.is_terminal)
    
    result, msg, _ = esm3.transition(
        session3.session_id,
        ESMState.NOMINAL,
        TransitionTrigger.RESET,
    )
    test("Cannot exit terminal state", result == TransitionResult.TERMINAL_STATE)
    
    # Test 7: SCRAM Supremacy (INV-SCRAM-HALT)
    print("\n[7] SCRAM Supremacy Tests")
    esm4 = EscalationStateMachine()
    s1 = esm4.create_session("SCRAM-USER-1")
    s2 = esm4.create_session("SCRAM-USER-2")
    
    # Move s1 to ACTIVE
    esm4.transition(s1.session_id, ESMState.REQUESTING, TransitionTrigger.REQUEST)
    esm4.transition(s1.session_id, ESMState.GRANTED, TransitionTrigger.APPROVAL)
    esm4.transition(s1.session_id, ESMState.ACTIVE, TransitionTrigger.ACTIVATION, ttl_seconds=3600)
    
    test("User 1 has authority before SCRAM", s1.has_authority)
    
    # Activate SCRAM
    affected = esm4.activate_scram()
    test("SCRAM activated", esm4.scram_active)
    test("SCRAM affected 2 sessions", affected == 2)
    test("User 1 in SCRAM_HALT", s1.current_state == ESMState.SCRAM_HALT)
    test("User 2 in SCRAM_HALT", s2.current_state == ESMState.SCRAM_HALT)
    test("SCRAM_HALT is terminal", s1.is_terminal)
    
    # Test 8: Request/Approve Flow
    print("\n[8] Request/Approve Flow Tests")
    esm5 = EscalationStateMachine()
    
    result, msg, session5 = esm5.request_escalation("FLOW-USER", "Need access")
    test("Request escalation succeeded", result == TransitionResult.SUCCESS)
    test("In REQUESTING state", session5.current_state == ESMState.REQUESTING)
    
    result, msg = esm5.approve_escalation(session5.session_id, 1800, "ADMIN")
    test("Approve succeeded", result == TransitionResult.SUCCESS)
    test("In ACTIVE state", session5.current_state == ESMState.ACTIVE)
    test("Has authority after approval", session5.has_authority)
    
    # Test 9: Deny Flow
    print("\n[9] Deny Flow Tests")
    esm6 = EscalationStateMachine()
    result, msg, session6 = esm6.request_escalation("DENY-USER", "Testing denial")
    
    result, msg = esm6.deny_escalation(session6.session_id, "ADMIN", "Not authorized")
    test("Deny succeeded", result == TransitionResult.SUCCESS)
    test("In DENIED state", session6.current_state == ESMState.DENIED)
    test("No authority after denial", not session6.has_authority)
    
    # Test 10: Revoke Flow
    print("\n[10] Revoke Flow Tests")
    esm7 = EscalationStateMachine()
    result, _, session7 = esm7.request_escalation("REVOKE-USER", "Will be revoked")
    esm7.approve_escalation(session7.session_id, 3600, "ADMIN")
    
    test("Has authority before revoke", session7.has_authority)
    
    result, msg = esm7.revoke_escalation(session7.session_id, "ADMIN", "Policy change")
    test("Revoke succeeded", result == TransitionResult.SUCCESS)
    test("In REVOKED state", session7.current_state == ESMState.REVOKED)
    test("No authority after revoke", not session7.has_authority)
    
    # Test 11: TTL Expiration
    print("\n[11] TTL Expiration Tests")
    esm8 = EscalationStateMachine()
    result, _, session8 = esm8.request_escalation("TTL-USER", "Short TTL")
    esm8.approve_escalation(session8.session_id, 1, "ADMIN")  # 1 second TTL
    
    test("Has authority initially", session8.has_authority)
    
    # Force expiration
    session8.ttl_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    
    expired, msg = esm8.check_expiration(session8.session_id)
    test("Expiration detected", expired)
    test("In TERMINATED state", session8.current_state == ESMState.TERMINATED)
    test("No authority after expiration", not session8.has_authority)
    
    # Test 12: has_authority Check
    print("\n[12] has_authority Check Tests")
    esm9 = EscalationStateMachine()
    
    test("Unknown user has no authority", not esm9.has_authority("UNKNOWN"))
    
    esm9.request_escalation("AUTH-USER", "Check authority")
    test("REQUESTING has no authority", not esm9.has_authority("AUTH-USER"))
    
    session9 = esm9.get_principal_session("AUTH-USER")
    esm9.approve_escalation(session9.session_id, 3600, "ADMIN")
    test("ACTIVE has authority", esm9.has_authority("AUTH-USER"))
    
    # Test 13: Transition History
    print("\n[13] Transition History Tests")
    test("Session has history", len(session9.history) >= 3)
    test("History has transitions", all(isinstance(t, ESMTransition) for t in session9.history))
    
    # Test 14: Statistics
    print("\n[14] Statistics Tests")
    stats = esm9.get_statistics()
    test("Stats has total_sessions", "total_sessions" in stats)
    test("Stats has total_transitions", "total_transitions" in stats)
    test("Stats has state_distribution", "state_distribution" in stats)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
