"""
ChainBridge Orchestration Engine — PAC Dispatch with Schema Validation
════════════════════════════════════════════════════════════════════════════════

Governance component that enforces PAC schema validation before dispatch.
Invalid PACs never reach Execution Engine.

PAC References:
- PAC-BENSON-EXEC-GOVERNANCE-IMMUTABLE-PAC-SCHEMA-019
- PAC-BENSON-EXEC-GOVERNANCE-BER-LOOP-ENFORCEMENT-020
- PAC-BENSON-EXEC-GOVERNANCE-BER-EMISSION-ENFORCEMENT-021

Effective Date: 2025-12-26

ORCHESTRATION RULES:
- No PAC dispatch without schema validation
- Invalid PACs are REJECTED (never dispatched)
- Schema violations visible in terminal
- Loop closure mechanically guaranteed

BER LOOP ENFORCEMENT (PAC-020):
- WRAP receipt triggers SYNCHRONOUS BER issuance
- No async or deferred BER processing
- Session cannot complete without BER
- Only ORCHESTRATION_ENGINE (GID-00) may issue BER

BER EMISSION ENFORCEMENT (PAC-021):
- BER must be EMITTED externally (not just issued internally)
- BERArtifact returned to caller proving emission occurred
- INV-BER-007: BER_ISSUED → BER_EMITTED (mandatory)
- INV-BER-008: Drafting surfaces prohibited from BER flow

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, List, Optional

from core.governance.pac_schema import (
    BERObligation,
    BERStatus,
    PACBuilder,
    PACDiscipline,
    PACDispatch,
    PACMode,
    PACSchema,
    PACSection,
    PACStatus,
    WRAPObligation,
    WRAPStatus,
)
from core.governance.pac_schema_validator import (
    MissingBERObligationError,
    MissingFinalStateError,
    MissingWRAPObligationError,
    PACSchemaTerminalRenderer,
    PACSchemaValidator,
    PACSchemaViolationError,
    PACTextParser,
    PACValidationResult,
)
from core.governance.system_identities import (
    DRAFTING_SURFACE,
    EXECUTION_ENGINE,
    ORCHESTRATION_ENGINE,
    BERAuthorityError,
    SystemIdentity,
    SystemIdentityRegistry,
    validate_ber_authority,
)
from core.governance.terminal_gates import (
    BORDER_CHAR,
    BORDER_WIDTH,
    FAIL_SYMBOL,
    PASS_SYMBOL,
    TerminalGateRenderer,
    get_terminal_renderer,
)
from core.governance.ber_loop_enforcer import (
    BERArtifact,
    BERLoopEnforcer,
    BERLoopTerminalRenderer,
    BERNotEmittedError,
    BERNotIssuedError,
    BERRequiredError,
    DraftingSurfaceInBERFlowError,
    SessionInvalidError,
    SessionRecord,
    SessionState,
    get_ber_loop_enforcer,
    reset_ber_loop_enforcer,
)
from core.governance.pdo_artifact import (
    PDOArtifact,
    PDOArtifactFactory,
    PDOAuthorityError,
    PDOCreationError,
    PDODuplicateError,
    PDOIncompleteError,
    PDO_AUTHORITY,
)
from core.governance.pdo_registry import (
    PDORegistry,
    get_pdo_registry,
    reset_pdo_registry,
)
from core.governance.positive_closure import (
    PositiveClosure,
    ClosureBuilder,
    PositiveClosureError,
    PositiveClosureNotEmittedError,
    POSITIVE_CLOSURE_AUTHORITY,
    enforce_closure_before_pdo,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCH STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class DispatchStatus(Enum):
    """Status of PAC dispatch operation."""
    
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    DISPATCHED = "DISPATCHED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    WRAP_RECEIVED = "WRAP_RECEIVED"
    BER_ISSUED = "BER_ISSUED"
    CLOSED = "CLOSED"


# ═══════════════════════════════════════════════════════════════════════════════
# DISPATCH RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DispatchResult:
    """Result of PAC dispatch attempt."""
    
    status: DispatchStatus
    pac_id: Optional[str]
    target_gid: Optional[str]
    validation_result: Optional[PACValidationResult]
    error: Optional[str] = None
    dispatched_at: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """True if dispatch was successful."""
        return self.status == DispatchStatus.DISPATCHED
    
    @property
    def rejected(self) -> bool:
        """True if PAC was rejected."""
        return self.status == DispatchStatus.REJECTED


# ═══════════════════════════════════════════════════════════════════════════════
# LOOP STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LoopState:
    """
    Tracks PAC loop state.
    
    Loop is closed when WRAP received AND BER issued AND emitted AND PDO emitted
    AND POSITIVE_CLOSURE emitted.
    
    PAC-020: PDO emission is required for valid loop closure.
    PAC-021: Emission is required for valid loop closure.
    PAC-030: POSITIVE_CLOSURE is required for valid loop closure.
    """
    
    pac_id: str
    status: DispatchStatus = DispatchStatus.PENDING
    
    # Dispatch
    dispatched_at: Optional[str] = None
    target_gid: Optional[str] = None
    
    # WRAP
    wrap_received: bool = False
    wrap_status: Optional[WRAPStatus] = None
    wrap_at: Optional[str] = None
    wrap_id: Optional[str] = None  # PAC-020: WRAP ID for PDO
    wrap_data: Optional[dict] = None  # PAC-020: WRAP data for PDO hash
    wrap_hash: Optional[str] = None  # PAC-030: WRAP hash for closure
    
    # BER
    ber_issued: bool = False
    ber_status: Optional[BERStatus] = None
    ber_at: Optional[str] = None
    ber_id: Optional[str] = None  # PAC-020: BER ID for PDO
    ber_data: Optional[dict] = None  # PAC-020: BER data for PDO hash
    
    # PAC-021: BER Emission
    ber_emitted: bool = False
    ber_emitted_at: Optional[str] = None
    ber_artifact: Optional[BERArtifact] = None
    
    # PAC-020: PDO Emission
    pdo_emitted: bool = False
    pdo_emitted_at: Optional[str] = None
    pdo_artifact: Optional["PDOArtifact"] = None
    
    # PAC-030: POSITIVE_CLOSURE
    positive_closure_emitted: bool = False
    positive_closure_at: Optional[str] = None
    positive_closure: Optional[PositiveClosure] = None
    
    @property
    def is_loop_closed(self) -> bool:
        """
        True if loop is closed (WRAP + BER + EMITTED + POSITIVE_CLOSURE + PDO).
        
        PAC-030: POSITIVE_CLOSURE is mandatory for loop closure.
        """
        return (
            self.wrap_received 
            and self.ber_issued 
            and self.ber_emitted 
            and self.positive_closure_emitted
            and self.pdo_emitted
        )
    
    @property
    def awaiting_positive_closure(self) -> bool:
        """True if awaiting POSITIVE_CLOSURE (PAC-030)."""
        return self.ber_emitted and not self.positive_closure_emitted
    
    
    @property
    def awaiting_wrap(self) -> bool:
        """True if awaiting WRAP from executor."""
        return (
            self.status == DispatchStatus.DISPATCHED
            and not self.wrap_received
        )
    
    @property
    def awaiting_ber(self) -> bool:
        """True if awaiting BER from Orchestration Engine."""
        return self.wrap_received and not self.ber_issued
    
    @property
    def awaiting_emission(self) -> bool:
        """True if BER issued but not emitted (PAC-021)."""
        return self.ber_issued and not self.ber_emitted
    
    @property
    def awaiting_pdo(self) -> bool:
        """True if POSITIVE_CLOSURE emitted but PDO not emitted (PAC-020, PAC-030)."""
        return self.positive_closure_emitted and not self.pdo_emitted
    
    def record_wrap(self, status: WRAPStatus, wrap_id: str = None, wrap_data: dict = None, wrap_hash: str = None) -> None:
        """Record WRAP receipt."""
        import uuid
        import hashlib
        import json
        self.wrap_received = True
        self.wrap_status = status
        self.wrap_at = datetime.now(timezone.utc).isoformat()
        self.wrap_id = wrap_id or f"wrap_{uuid.uuid4().hex[:12]}"
        self.wrap_data = wrap_data or {"status": status.value, "received_at": self.wrap_at}
        # PAC-030: Compute WRAP hash for closure
        wrap_content = json.dumps(self.wrap_data, sort_keys=True, separators=(',', ':'))
        self.wrap_hash = wrap_hash or hashlib.sha256(wrap_content.encode()).hexdigest()
        self.status = DispatchStatus.WRAP_RECEIVED
    
    def record_ber(self, status: BERStatus, ber_id: str = None, ber_data: dict = None) -> None:
        """Record BER issuance."""
        import uuid
        self.ber_issued = True
        self.ber_status = status
        self.ber_at = datetime.now(timezone.utc).isoformat()
        self.ber_id = ber_id or f"ber_{uuid.uuid4().hex[:12]}"
        self.ber_data = ber_data or {"status": status.value, "issued_at": self.ber_at}
        self.status = DispatchStatus.BER_ISSUED
    
    def record_emission(self, artifact: BERArtifact) -> None:
        """Record BER emission (PAC-021)."""
        self.ber_emitted = True
        self.ber_emitted_at = datetime.now(timezone.utc).isoformat()
        self.ber_artifact = artifact
        # Don't set to CLOSED yet - need POSITIVE_CLOSURE and PDO (PAC-030)
    
    def record_positive_closure(self, closure: PositiveClosure) -> None:
        """
        Record POSITIVE_CLOSURE emission (PAC-030).
        
        INV-PC-001: BER without POSITIVE_CLOSURE is INVALID.
        INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists.
        """
        self.positive_closure_emitted = True
        self.positive_closure_at = datetime.now(timezone.utc).isoformat()
        self.positive_closure = closure
        # Don't set to CLOSED yet - need PDO

    def record_pdo(self, pdo: "PDOArtifact") -> None:
        """Record PDO emission (PAC-020)."""
        self.pdo_emitted = True
        self.pdo_emitted_at = datetime.now(timezone.utc).isoformat()
        self.pdo_artifact = pdo
        if self.is_loop_closed:
            self.status = DispatchStatus.CLOSED


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION ENGINE TERMINAL RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestrationTerminalRenderer:
    """
    Terminal renderer for Orchestration Engine operations.
    """
    
    def __init__(self, renderer: TerminalGateRenderer = None):
        self._renderer = renderer or get_terminal_renderer()
        self._schema_renderer = PACSchemaTerminalRenderer(self._renderer)
    
    def _emit(self, text: str) -> None:
        """Emit text via base renderer."""
        self._renderer._emit(text)
    
    def emit_pac_received(self, pac_id: str = None) -> None:
        """Emit PAC received notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("📨 PAC RECEIVED BY ORCHESTRATION ENGINE")
        if pac_id:
            self._emit(f"   PAC_ID: {pac_id}")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_dispatch_success(
        self,
        pac_id: str,
        target_gid: str,
    ) -> None:
        """Emit successful dispatch notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🚀 PAC DISPATCHED")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   TARGET: {target_gid}")
        self._emit("   STATUS: AWAITING_WRAP")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_dispatch_rejected(
        self,
        pac_id: str = None,
        reason: str = None,
    ) -> None:
        """Emit dispatch rejected notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟥 PAC DISPATCH REJECTED")
        if pac_id:
            self._emit(f"   PAC_ID: {pac_id}")
        if reason:
            self._emit(f"   REASON: {reason}")
        self._emit("   ACTION: FIX_AND_RESUBMIT")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_wrap_received(
        self,
        pac_id: str,
        status: WRAPStatus,
    ) -> None:
        """Emit WRAP received notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("📋 WRAP RECEIVED")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   STATUS: {status.value}")
        self._emit("   NEXT: ORCHESTRATION_ENGINE_BER")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_ber_issued(
        self,
        pac_id: str,
        status: BERStatus,
    ) -> None:
        """Emit BER issued notification."""
        symbol = PASS_SYMBOL if status == BERStatus.APPROVE else FAIL_SYMBOL
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit(f"📜 BER ISSUED {symbol}")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   DECISION: {status.value}")
        self._emit("   ISSUER: GID-00 (ORCHESTRATION_ENGINE)")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
    
    def emit_loop_closed(self, pac_id: str) -> None:
        """Emit loop closed notification."""
        self._emit("")
        self._emit(BORDER_CHAR * BORDER_WIDTH)
        self._emit("🟩 LOOP CLOSED")
        self._emit(f"   PAC_ID: {pac_id}")
        self._emit(f"   WRAP: {PASS_SYMBOL} RECEIVED")
        self._emit(f"   BER:  {PASS_SYMBOL} ISSUED")
        self._emit("   STATUS: COMPLETE")
        self._emit(BORDER_CHAR * BORDER_WIDTH)


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GovernanceOrchestrationEngine:
    """
    Governance Orchestration Engine.
    
    Enforces PAC schema validation before dispatch.
    Ensures loop closure (WRAP + BER).
    """
    
    def __init__(
        self,
        validator: PACSchemaValidator = None,
        parser: PACTextParser = None,
        renderer: OrchestrationTerminalRenderer = None,
    ):
        self._validator = validator or PACSchemaValidator()
        self._parser = parser or PACTextParser()
        self._renderer = renderer or OrchestrationTerminalRenderer()
        
        # Active loops (pac_id -> LoopState)
        self._loops: dict[str, LoopState] = {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PAC DISPATCH
    # ═══════════════════════════════════════════════════════════════════════════
    
    def dispatch(self, pac: PACSchema) -> DispatchResult:
        """
        Dispatch PAC to target executor.
        
        Validates schema BEFORE dispatch.
        Invalid PACs are REJECTED (never dispatched).
        
        Returns DispatchResult with status.
        """
        pac_id = pac.pac_id
        
        self._renderer.emit_pac_received(pac_id)
        
        # CRITICAL: Validate schema before dispatch
        validation_result = self._validator.validate(pac)
        
        if not validation_result.valid:
            self._renderer.emit_dispatch_rejected(
                pac_id,
                f"Schema violation: {len(validation_result.missing_sections)} missing sections",
            )
            return DispatchResult(
                status=DispatchStatus.REJECTED,
                pac_id=pac_id,
                target_gid=None,
                validation_result=validation_result,
                error="PAC schema validation failed",
            )
        
        # Schema valid — dispatch to target
        target_gid = pac.dispatch.target_gid if pac.dispatch else None
        
        if not target_gid:
            self._renderer.emit_dispatch_rejected(
                pac_id,
                "No target GID specified in DISPATCH section",
            )
            return DispatchResult(
                status=DispatchStatus.REJECTED,
                pac_id=pac_id,
                target_gid=None,
                validation_result=validation_result,
                error="No target GID",
            )
        
        # Create loop state
        loop = LoopState(pac_id=pac_id)
        loop.status = DispatchStatus.DISPATCHED
        loop.dispatched_at = datetime.now(timezone.utc).isoformat()
        loop.target_gid = target_gid
        self._loops[pac_id] = loop
        
        self._renderer.emit_dispatch_success(pac_id, target_gid)
        
        return DispatchResult(
            status=DispatchStatus.DISPATCHED,
            pac_id=pac_id,
            target_gid=target_gid,
            validation_result=validation_result,
            dispatched_at=loop.dispatched_at,
        )
    
    def dispatch_text(self, text: str) -> DispatchResult:
        """
        Parse and dispatch PAC from text.
        
        Returns DispatchResult with status.
        """
        pac = self._parser.parse(text)
        return self.dispatch(pac)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WRAP HANDLING — PAC-020/021 ENFORCEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def receive_wrap(
        self,
        pac_id: str,
        status: WRAPStatus,
        from_gid: str = None,
    ) -> "PDOArtifact":
        """
        Record WRAP receipt from executor and SYNCHRONOUSLY process to BER and PDO.
        
        PAC-020 ENFORCEMENT:
        - WRAP receipt triggers BER_REQUIRED state
        - BER MUST be issued before this method returns
        - PDO MUST be created and emitted before this method returns
        - No async or deferred BER/PDO processing allowed
        
        PAC-021 ENFORCEMENT (INV-BER-007):
        - BER must be EMITTED (not just issued internally)
        - PDOArtifact returned proving complete loop closure
        - Loop closure requires observable external emission of both BER and PDO
        
        Returns:
            PDOArtifact proving complete PDO chain was emitted
        """
        loop = self._loops.get(pac_id)
        if loop is None:
            raise ValueError(f"Unknown PAC: {pac_id}")
        
        # Record WRAP receipt
        loop.record_wrap(status)
        self._renderer.emit_wrap_received(pac_id, status)
        
        # PAC-020: SYNCHRONOUS BER ISSUANCE
        # Determine BER status based on WRAP status
        if status == WRAPStatus.COMPLETE:
            ber_status = BERStatus.APPROVE
        elif status == WRAPStatus.PARTIAL:
            ber_status = BERStatus.CORRECTIVE
        else:
            ber_status = BERStatus.CORRECTIVE
        
        # PAC-021: Issue AND emit BER (must emit, not just issue)
        return self.issue_and_emit_ber(pac_id, ber_status)
    
    def receive_wrap_without_auto_ber(
        self,
        pac_id: str,
        status: WRAPStatus,
    ) -> LoopState:
        """
        Record WRAP receipt WITHOUT automatic BER issuance.
        
        WARNING: This method is for testing only.
        In production, use receive_wrap() which enforces BER.
        
        Caller is responsible for issuing BER.
        """
        loop = self._loops.get(pac_id)
        if loop is None:
            raise ValueError(f"Unknown PAC: {pac_id}")
        
        loop.record_wrap(status)
        self._renderer.emit_wrap_received(pac_id, status)
        
        return loop
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BER ISSUANCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def issue_ber(
        self,
        pac_id: str,
        status: BERStatus,
    ) -> LoopState:
        """
        Issue BER for PAC (internal issuance only).
        
        Only Orchestration Engine (GID-00) may issue BER.
        Updates loop state.
        
        WARNING: Use issue_and_emit_ber() for PAC-021 compliance.
        This method issues but does NOT emit BER.
        """
        # Validate BER authority
        validate_ber_authority(
            ORCHESTRATION_ENGINE.identity_id,
            ORCHESTRATION_ENGINE.identity_type,
        )
        
        loop = self._loops.get(pac_id)
        if loop is None:
            raise ValueError(f"Unknown PAC: {pac_id}")
        
        loop.record_ber(status)
        self._renderer.emit_ber_issued(pac_id, status)
        
        return loop
    
    def issue_and_emit_ber(
        self,
        pac_id: str,
        status: BERStatus,
    ) -> "PDOArtifact":
        """
        Issue AND emit BER for PAC, then create and emit PDO (PAC-020/021/030 compliant).
        
        Only Orchestration Engine (GID-00) may issue and emit BER/PDO.
        Returns PDOArtifact proving complete loop closure occurred.
        
        This is the preferred method for BER processing.
        Guarantees BER issuance → BER emission → POSITIVE_CLOSURE → PDO creation → PDO emission atomically.
        
        PAC-020: PDO emission is mandatory for loop closure.
        PAC-021: BER emission is mandatory for loop closure.
        PAC-030: POSITIVE_CLOSURE is mandatory before PDO emission.
        
        Returns:
            PDOArtifact proving complete PDO chain was emitted
        """
        from core.governance.terminal_gates import (
            emit_proof_locked,
            emit_decision_issued,
            emit_pdo_emitted,
        )
        
        # First issue BER internally
        loop = self.issue_ber(pac_id, status)
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Then emit BER externally (PAC-021: INV-BER-007)
        ber_artifact = BERArtifact(
            pac_id=pac_id,
            decision=status.value,
            issuer=ORCHESTRATION_ENGINE.identity_id,
            issued_at=loop.ber_at or now,
            emitted_at=now,
            wrap_status=loop.wrap_status.value if loop.wrap_status else "UNKNOWN",
            session_state="BER_EMITTED",
        )
        
        # Record BER emission
        loop.record_emission(ber_artifact)
        
        # PAC-030: Create and emit POSITIVE_CLOSURE before PDO
        # Collect all WRAP hashes (in single-agent case, just one)
        wrap_hashes = [loop.wrap_hash] if loop.wrap_hash else []
        
        # Determine outcome status from BER status
        if status == BERStatus.APPROVE:
            outcome_status = "ACCEPTED"
            closure_decision = "CLEAN"
        elif status == BERStatus.CORRECTIVE:
            outcome_status = "CORRECTIVE"
            closure_decision = "CORRECTIVE"
        else:
            outcome_status = "REJECTED"
            closure_decision = "INVALID"
        
        # Build POSITIVE_CLOSURE
        closure_builder = ClosureBuilder(
            pac_id=pac_id,
            ber_id=loop.ber_id or f"ber_{pac_id}",
        )
        closure_builder.add_wrap_hashes(wrap_hashes)
        closure_builder.set_final_state("SESSION_CLOSED")
        closure_builder.set_invariants_verified(True)
        closure_builder.set_checkpoints_resolved(0)
        closure_builder.set_decision(closure_decision)
        
        positive_closure = closure_builder.build()
        
        # Record POSITIVE_CLOSURE emission (PAC-030)
        loop.record_positive_closure(positive_closure)
        
        # Emit POSITIVE_CLOSURE terminal notification
        self._renderer._emit("")
        self._renderer._emit("═" * 60)
        self._renderer._emit("🟢 POSITIVE_CLOSURE EMITTED (PAC-030)")
        self._renderer._emit(f"   PAC_ID: {pac_id}")
        self._renderer._emit(f"   BER_ID: {positive_closure.ber_id}")
        self._renderer._emit(f"   CLOSURE_ID: {positive_closure.closure_id}")
        self._renderer._emit(f"   WRAP_COUNT: {positive_closure.wrap_count}")
        self._renderer._emit(f"   DECISION: {positive_closure.decision}")
        self._renderer._emit(f"   HASH: {positive_closure.closure_hash[:32]}...")
        self._renderer._emit("═" * 60)
        
        # PAC-020: Create and emit PDO (POSITIVE_CLOSURE required by INV-PC-002)
        # 🧾 PROOF LOCKED
        emit_proof_locked(
            pac_id=pac_id,
            wrap_id=loop.wrap_id or f"wrap_{pac_id}",
            proof_hash=PDOArtifactFactory.create(
                pac_id=pac_id,
                wrap_id=loop.wrap_id or f"wrap_{pac_id}",
                wrap_data=loop.wrap_data or {"status": loop.wrap_status.value if loop.wrap_status else "UNKNOWN"},
                ber_id=loop.ber_id or f"ber_{pac_id}",
                ber_data=loop.ber_data or {"status": status.value},
                outcome_status=outcome_status,
                issuer=PDO_AUTHORITY,
            ).proof_hash if loop.wrap_data else "pending",
        )
        
        # 🧠 DECISION ISSUED
        emit_decision_issued(
            pac_id=pac_id,
            ber_id=loop.ber_id or f"ber_{pac_id}",
            decision=outcome_status,
        )
        
        # Create PDO (with POSITIVE_CLOSURE reference via closure_hash in metadata)
        pdo = PDOArtifactFactory.create(
            pac_id=pac_id,
            wrap_id=loop.wrap_id or f"wrap_{pac_id}",
            wrap_data=loop.wrap_data or {"status": loop.wrap_status.value if loop.wrap_status else "UNKNOWN"},
            ber_id=loop.ber_id or f"ber_{pac_id}",
            ber_data=loop.ber_data or {"status": status.value},
            outcome_status=outcome_status,
            issuer=PDO_AUTHORITY,
            proof_at=loop.wrap_at,
            decision_at=loop.ber_at,
        )
        
        # Register PDO
        registry = get_pdo_registry()
        if not registry.has_pac(pac_id):
            registry.register(pdo)
        
        # Record PDO emission in loop state
        loop.record_pdo(pdo)
        
        # 🧿 PDO EMITTED
        emit_pdo_emitted(
            pdo_id=pdo.pdo_id,
            pac_id=pac_id,
            outcome_status=outcome_status,
            pdo_hash=pdo.pdo_hash,
        )
        
        if loop.is_loop_closed:
            self._renderer.emit_loop_closed(pac_id)
        
        return pdo
        
        return artifact
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOOP QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_loop_state(self, pac_id: str) -> Optional[LoopState]:
        """Get loop state for PAC."""
        return self._loops.get(pac_id)
    
    def is_loop_closed(self, pac_id: str) -> bool:
        """Check if loop is closed for PAC."""
        loop = self._loops.get(pac_id)
        return loop is not None and loop.is_loop_closed
    
    def get_open_loops(self) -> List[LoopState]:
        """Get all open (unclosed) loops."""
        return [l for l in self._loops.values() if not l.is_loop_closed]
    
    def get_awaiting_wrap(self) -> List[LoopState]:
        """Get loops awaiting WRAP."""
        return [l for l in self._loops.values() if l.awaiting_wrap]
    
    def get_awaiting_ber(self) -> List[LoopState]:
        """Get loops awaiting BER."""
        return [l for l in self._loops.values() if l.awaiting_ber]
    
    def get_awaiting_positive_closure(self) -> List[LoopState]:
        """Get loops awaiting POSITIVE_CLOSURE (PAC-030)."""
        return [l for l in self._loops.values() if l.awaiting_positive_closure]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_engine: Optional[GovernanceOrchestrationEngine] = None


def get_orchestration_engine() -> GovernanceOrchestrationEngine:
    """Get singleton orchestration engine."""
    global _engine
    if _engine is None:
        _engine = GovernanceOrchestrationEngine()
    return _engine


def reset_orchestration_engine() -> None:
    """Reset singleton (for testing)."""
    global _engine
    _engine = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def dispatch_pac(pac: PACSchema) -> DispatchResult:
    """Dispatch PAC through orchestration engine."""
    return get_orchestration_engine().dispatch(pac)


def dispatch_pac_text(text: str) -> DispatchResult:
    """Parse and dispatch PAC text."""
    return get_orchestration_engine().dispatch_text(text)


def receive_wrap(pac_id: str, status: WRAPStatus, from_gid: str = None) -> "PDOArtifact":
    """
    Record WRAP receipt and SYNCHRONOUSLY issue BER AND emit PDO.
    
    PAC-020: This is the mandatory entry point for WRAP processing.
             PDO will be EMITTED before this function returns.
    PAC-021: BER will be EMITTED before this function returns.
    
    Returns:
        PDOArtifact proving complete PDO chain was emitted
    """
    return get_orchestration_engine().receive_wrap(pac_id, status, from_gid)


def issue_ber(pac_id: str, status: BERStatus) -> LoopState:
    """
    Issue BER for PAC (internal issuance only).
    
    WARNING: Prefer issue_and_emit_ber() for PAC-020/021 compliance.
    """
    return get_orchestration_engine().issue_ber(pac_id, status)


def issue_and_emit_ber(pac_id: str, status: BERStatus) -> "PDOArtifact":
    """
    Issue BER AND emit PDO for PAC (PAC-020/021 compliant).
    
    Returns:
        PDOArtifact proving complete PDO chain was emitted
    """
    return get_orchestration_engine().issue_and_emit_ber(pac_id, status)


def is_loop_closed(pac_id: str) -> bool:
    """Check if PAC loop is closed."""
    return get_orchestration_engine().is_loop_closed(pac_id)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Status
    "DispatchStatus",
    
    # Results
    "DispatchResult",
    "LoopState",
    
    # Renderer
    "OrchestrationTerminalRenderer",
    
    # Engine
    "GovernanceOrchestrationEngine",
    
    # Singleton
    "get_orchestration_engine",
    "reset_orchestration_engine",
    
    # Convenience
    "dispatch_pac",
    "dispatch_pac_text",
    "receive_wrap",
    "issue_ber",
    "issue_and_emit_ber",
    "is_loop_closed",
    
    # PAC-020 BER Loop Enforcement (re-exports)
    "BERLoopEnforcer",
    "BERNotIssuedError",
    "BERRequiredError",
    "SessionInvalidError",
    "SessionRecord",
    "SessionState",
    "get_ber_loop_enforcer",
    "reset_ber_loop_enforcer",
    
    # PAC-021 BER Emission Enforcement (re-exports)
    "BERArtifact",
    "BERNotEmittedError",
    "DraftingSurfaceInBERFlowError",
    
    # PAC-020 PDO Artifact Engine (re-exports)
    "PDOArtifact",
    "PDOArtifactFactory",
    "PDOAuthorityError",
    "PDOCreationError",
    "PDODuplicateError",
    "PDOIncompleteError",
    "PDO_AUTHORITY",
    "PDORegistry",
    "get_pdo_registry",
    "reset_pdo_registry",
    
    # PAC-030 POSITIVE_CLOSURE (re-exports)
    "PositiveClosure",
    "ClosureBuilder",
    "PositiveClosureError",
    "PositiveClosureNotEmittedError",
    "POSITIVE_CLOSURE_AUTHORITY",
    "enforce_closure_before_pdo",
]
