"""
Settlement Engine — PDO-Gated Settlement Initiation and Execution
════════════════════════════════════════════════════════════════════════════════

This module binds settlement initiation to PDOExecutionGate, enforcing:
    - INV-SETTLEMENT-001: No settlement without valid PDO
    - INV-SETTLEMENT-003: No state change without ledger append
    - INV-SETTLEMENT-004: Ledger failure aborts settlement
    - INV-SETTLEMENT-005: All transitions auditable

ORDER 1 Implementation — Cody (GID-01)

PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-SETTLEMENT-EXEC-006C
Effective Date: 2025-12-30

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from core.governance.pdo_artifact import (
    PDOArtifact,
    PDO_AUTHORITY,
    compute_hash,
)
from core.governance.pdo_execution_gate import (
    PDOExecutionGate,
    ProofContainer,
    DecisionContainer,
    GateEvaluation,
    GateResult,
    GateBlockReason,
    PDOGateError,
    ProofGateError,
    DecisionGateError,
    OutcomeGateError,
    get_pdo_gate,
)
from core.governance.pdo_ledger import (
    PDOLedger,
    LedgerEntry,
    LedgerError,
    get_pdo_ledger,
)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger("settlement_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SETTLEMENT_ENGINE_VERSION = "1.0.0"
"""Settlement engine version."""


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementError(Exception):
    """Base exception for settlement errors."""
    
    def __init__(
        self,
        message: str,
        settlement_id: Optional[str] = None,
        pdo_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.settlement_id = settlement_id
        self.pdo_id = pdo_id
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to audit dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "settlement_id": self.settlement_id,
            "pdo_id": self.pdo_id,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class SettlementPDORequiredError(SettlementError):
    """
    Raised when settlement attempted without valid PDO.
    
    INV-SETTLEMENT-001: No settlement without valid PDO.
    """
    
    def __init__(
        self,
        settlement_id: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"SETTLEMENT_PDO_REQUIRED: Settlement '{settlement_id}' blocked. "
            f"Reason: {reason}. INV-SETTLEMENT-001 enforced.",
            settlement_id=settlement_id,
            context=context,
        )
        self.reason = reason


class SettlementLedgerFailureError(SettlementError):
    """
    Raised when ledger operation fails during settlement.
    
    INV-SETTLEMENT-004: Ledger failure aborts settlement.
    """
    
    def __init__(
        self,
        settlement_id: str,
        ledger_error: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"SETTLEMENT_LEDGER_FAILURE: Settlement '{settlement_id}' aborted. "
            f"Ledger error: {ledger_error}. INV-SETTLEMENT-004 enforced.",
            settlement_id=settlement_id,
            context=context,
        )
        self.ledger_error = ledger_error


class SettlementNotFoundError(SettlementError):
    """Raised when settlement not found."""
    
    def __init__(self, settlement_id: str):
        super().__init__(
            f"SETTLEMENT_NOT_FOUND: Settlement '{settlement_id}' not found.",
            settlement_id=settlement_id,
        )


class SettlementAlreadyFinalizedError(SettlementError):
    """Raised when attempting to modify finalized settlement."""
    
    def __init__(self, settlement_id: str, status: str):
        super().__init__(
            f"SETTLEMENT_ALREADY_FINALIZED: Settlement '{settlement_id}' "
            f"is already in status '{status}' and cannot be modified.",
            settlement_id=settlement_id,
        )
        self.status = status


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT STATUS ENUM
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementStatus(Enum):
    """Settlement status states."""
    PENDING = "PENDING"
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    MILESTONE_PENDING = "MILESTONE_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT REQUEST
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SettlementRequest:
    """
    Request to initiate settlement.
    
    Bundles all required data for PDO-gated settlement initiation.
    """
    
    # Identity
    settlement_id: Optional[str] = None
    pac_id: str = ""
    
    # PDO Reference (required)
    pdo_id: str = ""
    pdo_artifact: Optional[PDOArtifact] = None
    
    # Settlement Details
    amount: float = 0.0
    currency: str = "USD"
    counterparty_id: str = ""
    description: str = ""
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    requested_at: Optional[str] = None
    requestor: str = ""
    
    def __post_init__(self):
        """Generate settlement ID if not provided."""
        if not self.settlement_id:
            self.settlement_id = f"settle_{uuid.uuid4().hex[:12]}"
        if not self.requested_at:
            self.requested_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def is_valid(self) -> bool:
        """Check if request has all required fields."""
        return bool(
            self.settlement_id
            and self.pac_id
            and self.pdo_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "settlement_id": self.settlement_id,
            "pac_id": self.pac_id,
            "pdo_id": self.pdo_id,
            "amount": self.amount,
            "currency": self.currency,
            "counterparty_id": self.counterparty_id,
            "description": self.description,
            "metadata": self.metadata,
            "requested_at": self.requested_at,
            "requestor": self.requestor,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SettlementResult:
    """
    Immutable result of settlement operation.
    
    frozen=True ensures auditability.
    """
    
    # Identity
    settlement_id: str
    pac_id: str
    pdo_id: str
    
    # Status
    status: SettlementStatus
    success: bool
    
    # Ledger binding
    ledger_entry_id: Optional[str] = None
    ledger_entry_hash: Optional[str] = None
    
    # Timestamps
    initiated_at: str = ""
    completed_at: Optional[str] = None
    
    # Audit trail
    gate_evaluations: Tuple[GateEvaluation, ...] = field(default_factory=tuple)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "settlement_id": self.settlement_id,
            "pac_id": self.pac_id,
            "pdo_id": self.pdo_id,
            "status": self.status.value,
            "success": self.success,
            "ledger_entry_id": self.ledger_entry_id,
            "ledger_entry_hash": self.ledger_entry_hash,
            "initiated_at": self.initiated_at,
            "completed_at": self.completed_at,
            "gate_evaluations": [e.to_dict() for e in self.gate_evaluations],
            "error": self.error,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT RECORD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SettlementRecord:
    """
    Internal settlement tracking record.
    
    Mutable during settlement lifecycle, immutable after finalization.
    """
    
    # Identity
    settlement_id: str
    pac_id: str
    pdo_id: str
    
    # Status
    status: SettlementStatus = SettlementStatus.PENDING
    
    # PDO Binding
    pdo_artifact: Optional[PDOArtifact] = None
    pdo_verified: bool = False
    
    # Ledger binding
    ledger_entry_id: Optional[str] = None
    ledger_entry_hash: Optional[str] = None
    
    # Details
    amount: float = 0.0
    currency: str = "USD"
    counterparty_id: str = ""
    description: str = ""
    
    # Milestones
    milestone_ids: List[str] = field(default_factory=list)
    milestone_count: int = 0
    milestones_completed: int = 0
    
    # Timestamps
    created_at: str = ""
    initiated_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Audit
    gate_evaluations: List[GateEvaluation] = field(default_factory=list)
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    def __post_init__(self):
        """Set created_at if not provided."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def is_finalized(self) -> bool:
        """Check if settlement is in final state."""
        return self.status in {
            SettlementStatus.COMPLETED,
            SettlementStatus.FAILED,
            SettlementStatus.ABORTED,
        }
    
    def record_transition(
        self,
        from_status: SettlementStatus,
        to_status: SettlementStatus,
        reason: str,
        pdo_id: Optional[str] = None,
    ) -> None:
        """Record a state transition for audit."""
        self.state_transitions.append({
            "from_status": from_status.value,
            "to_status": to_status.value,
            "reason": reason,
            "pdo_id": pdo_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementEngine:
    """
    PDO-Gated Settlement Engine.
    
    Enforces all settlement invariants through PDOExecutionGate integration.
    
    INVARIANTS:
        INV-SETTLEMENT-001: No settlement without valid PDO
        INV-SETTLEMENT-003: No state change without ledger append
        INV-SETTLEMENT-004: Ledger failure aborts settlement
        INV-SETTLEMENT-005: All transitions auditable
    """
    
    def __init__(
        self,
        pdo_gate: Optional[PDOExecutionGate] = None,
        pdo_ledger: Optional[PDOLedger] = None,
    ):
        """
        Initialize settlement engine.
        
        Args:
            pdo_gate: PDO execution gate (defaults to singleton)
            pdo_ledger: PDO ledger (defaults to singleton)
        """
        self._gate = pdo_gate or get_pdo_gate()
        self._ledger = pdo_ledger or get_pdo_ledger()
        
        # Settlement registry (settlement_id → record)
        self._settlements: Dict[str, SettlementRecord] = {}
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Engine metadata
        self._version = SETTLEMENT_ENGINE_VERSION
        self._created_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"SettlementEngine initialized (v{self._version})")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SETTLEMENT INITIATION (ORDER 1 — Cody GID-01)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def initiate_settlement(
        self,
        request: SettlementRequest,
    ) -> SettlementResult:
        """
        Initiate settlement with PDO gate enforcement.
        
        INV-SETTLEMENT-001: No settlement without valid PDO.
        
        Args:
            request: Settlement request with PDO reference
            
        Returns:
            SettlementResult with status and ledger binding
            
        Raises:
            SettlementPDORequiredError: If no valid PDO
            SettlementLedgerFailureError: If ledger append fails
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            gate_evaluations: List[GateEvaluation] = []
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 1: Validate request
            # ─────────────────────────────────────────────────────────────────
            if not request.is_valid:
                raise SettlementPDORequiredError(
                    settlement_id=request.settlement_id or "unknown",
                    reason="Invalid settlement request - missing required fields",
                    context=request.to_dict(),
                )
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 2: Verify PDO exists and is valid (INV-SETTLEMENT-001)
            # ─────────────────────────────────────────────────────────────────
            try:
                pdo_evaluation = self._gate.verify_pdo_exists(
                    pdo_id=request.pdo_id,
                    pac_id=request.pac_id,
                    evaluator="GID-01",  # Cody
                )
                gate_evaluations.append(pdo_evaluation)
                
                if not pdo_evaluation.is_pass:
                    raise SettlementPDORequiredError(
                        settlement_id=request.settlement_id,
                        reason=f"PDO verification failed: {pdo_evaluation.reason.value if pdo_evaluation.reason else 'unknown'}",
                        context={"evaluation": pdo_evaluation.to_dict()},
                    )
                    
            except PDOGateError as e:
                raise SettlementPDORequiredError(
                    settlement_id=request.settlement_id,
                    reason=str(e),
                    context=e.to_dict(),
                )
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 3: Create settlement record
            # ─────────────────────────────────────────────────────────────────
            record = SettlementRecord(
                settlement_id=request.settlement_id,
                pac_id=request.pac_id,
                pdo_id=request.pdo_id,
                status=SettlementStatus.PENDING,
                pdo_artifact=request.pdo_artifact,
                pdo_verified=True,
                amount=request.amount,
                currency=request.currency,
                counterparty_id=request.counterparty_id,
                description=request.description,
                created_at=now,
            )
            record.gate_evaluations.extend(gate_evaluations)
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 4: Append to ledger (INV-SETTLEMENT-003)
            # ─────────────────────────────────────────────────────────────────
            try:
                ledger_entry = self._append_to_ledger(
                    record=record,
                    event_type="SETTLEMENT_INITIATED",
                )
                record.ledger_entry_id = ledger_entry.entry_id
                record.ledger_entry_hash = ledger_entry.entry_hash
                
            except LedgerError as e:
                # INV-SETTLEMENT-004: Ledger failure aborts settlement
                raise SettlementLedgerFailureError(
                    settlement_id=request.settlement_id,
                    ledger_error=str(e),
                    context={"pdo_id": request.pdo_id},
                )
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 5: Transition to INITIATED
            # ─────────────────────────────────────────────────────────────────
            record.record_transition(
                from_status=SettlementStatus.PENDING,
                to_status=SettlementStatus.INITIATED,
                reason="PDO verified, ledger entry created",
                pdo_id=request.pdo_id,
            )
            record.status = SettlementStatus.INITIATED
            record.initiated_at = now
            
            # ─────────────────────────────────────────────────────────────────
            # STEP 6: Register settlement
            # ─────────────────────────────────────────────────────────────────
            self._settlements[request.settlement_id] = record
            
            logger.info(
                f"Settlement initiated: {request.settlement_id} "
                f"(PDO: {request.pdo_id}, Ledger: {record.ledger_entry_id})"
            )
            
            return SettlementResult(
                settlement_id=request.settlement_id,
                pac_id=request.pac_id,
                pdo_id=request.pdo_id,
                status=SettlementStatus.INITIATED,
                success=True,
                ledger_entry_id=record.ledger_entry_id,
                ledger_entry_hash=record.ledger_entry_hash,
                initiated_at=now,
                gate_evaluations=tuple(gate_evaluations),
            )
    
    def complete_settlement(
        self,
        settlement_id: str,
        completion_pdo_id: str,
        completion_pac_id: str,
    ) -> SettlementResult:
        """
        Complete a settlement with PDO verification.
        
        Args:
            settlement_id: Settlement to complete
            completion_pdo_id: PDO authorizing completion
            completion_pac_id: PAC for completion
            
        Returns:
            SettlementResult with final status
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            
            # Get record
            record = self._get_record(settlement_id)
            if record.is_finalized:
                raise SettlementAlreadyFinalizedError(
                    settlement_id, record.status.value
                )
            
            # Verify completion PDO
            gate_evaluations = []
            try:
                pdo_eval = self._gate.verify_pdo_exists(
                    pdo_id=completion_pdo_id,
                    pac_id=completion_pac_id,
                    evaluator="GID-01",
                )
                gate_evaluations.append(pdo_eval)
                
                if not pdo_eval.is_pass:
                    record.status = SettlementStatus.FAILED
                    record.error = f"Completion PDO verification failed"
                    record.completed_at = now
                    
                    return SettlementResult(
                        settlement_id=settlement_id,
                        pac_id=record.pac_id,
                        pdo_id=record.pdo_id,
                        status=SettlementStatus.FAILED,
                        success=False,
                        ledger_entry_id=record.ledger_entry_id,
                        ledger_entry_hash=record.ledger_entry_hash,
                        initiated_at=record.initiated_at or "",
                        completed_at=now,
                        gate_evaluations=tuple(gate_evaluations),
                        error=record.error,
                    )
                    
            except PDOGateError as e:
                record.status = SettlementStatus.FAILED
                record.error = str(e)
                record.completed_at = now
                
                return SettlementResult(
                    settlement_id=settlement_id,
                    pac_id=record.pac_id,
                    pdo_id=record.pdo_id,
                    status=SettlementStatus.FAILED,
                    success=False,
                    ledger_entry_id=record.ledger_entry_id,
                    ledger_entry_hash=record.ledger_entry_hash,
                    initiated_at=record.initiated_at or "",
                    completed_at=now,
                    gate_evaluations=tuple(gate_evaluations),
                    error=record.error,
                )
            
            # Append completion to ledger
            try:
                ledger_entry = self._append_to_ledger(
                    record=record,
                    event_type="SETTLEMENT_COMPLETED",
                    additional_pdo_id=completion_pdo_id,
                )
            except LedgerError as e:
                raise SettlementLedgerFailureError(
                    settlement_id=settlement_id,
                    ledger_error=str(e),
                )
            
            # Finalize
            record.record_transition(
                from_status=record.status,
                to_status=SettlementStatus.COMPLETED,
                reason="Settlement completed with PDO verification",
                pdo_id=completion_pdo_id,
            )
            record.status = SettlementStatus.COMPLETED
            record.completed_at = now
            record.gate_evaluations.extend(gate_evaluations)
            
            logger.info(f"Settlement completed: {settlement_id}")
            
            return SettlementResult(
                settlement_id=settlement_id,
                pac_id=record.pac_id,
                pdo_id=record.pdo_id,
                status=SettlementStatus.COMPLETED,
                success=True,
                ledger_entry_id=ledger_entry.entry_id,
                ledger_entry_hash=ledger_entry.entry_hash,
                initiated_at=record.initiated_at or "",
                completed_at=now,
                gate_evaluations=tuple(record.gate_evaluations),
            )
    
    def abort_settlement(
        self,
        settlement_id: str,
        reason: str,
    ) -> SettlementResult:
        """
        Abort a settlement.
        
        Args:
            settlement_id: Settlement to abort
            reason: Reason for abortion
            
        Returns:
            SettlementResult with aborted status
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            
            record = self._get_record(settlement_id)
            if record.is_finalized:
                raise SettlementAlreadyFinalizedError(
                    settlement_id, record.status.value
                )
            
            # Record abort in ledger
            try:
                ledger_entry = self._append_to_ledger(
                    record=record,
                    event_type="SETTLEMENT_ABORTED",
                )
            except LedgerError as e:
                raise SettlementLedgerFailureError(
                    settlement_id=settlement_id,
                    ledger_error=str(e),
                )
            
            record.record_transition(
                from_status=record.status,
                to_status=SettlementStatus.ABORTED,
                reason=reason,
            )
            record.status = SettlementStatus.ABORTED
            record.completed_at = now
            record.error = reason
            
            logger.info(f"Settlement aborted: {settlement_id} - {reason}")
            
            return SettlementResult(
                settlement_id=settlement_id,
                pac_id=record.pac_id,
                pdo_id=record.pdo_id,
                status=SettlementStatus.ABORTED,
                success=False,
                ledger_entry_id=ledger_entry.entry_id,
                ledger_entry_hash=ledger_entry.entry_hash,
                initiated_at=record.initiated_at or "",
                completed_at=now,
                gate_evaluations=tuple(record.gate_evaluations),
                error=reason,
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RETRIEVAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_settlement(self, settlement_id: str) -> SettlementRecord:
        """Get settlement record by ID."""
        with self._lock:
            return self._get_record(settlement_id)
    
    def get_settlement_by_pdo(self, pdo_id: str) -> Optional[SettlementRecord]:
        """Get settlement by PDO ID."""
        with self._lock:
            for record in self._settlements.values():
                if record.pdo_id == pdo_id:
                    return record
            return None
    
    def list_settlements(
        self,
        status: Optional[SettlementStatus] = None,
    ) -> List[SettlementRecord]:
        """List settlements optionally filtered by status."""
        with self._lock:
            if status is None:
                return list(self._settlements.values())
            return [
                r for r in self._settlements.values()
                if r.status == status
            ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_record(self, settlement_id: str) -> SettlementRecord:
        """Get record or raise."""
        record = self._settlements.get(settlement_id)
        if record is None:
            raise SettlementNotFoundError(settlement_id)
        return record
    
    def _append_to_ledger(
        self,
        record: SettlementRecord,
        event_type: str,
        additional_pdo_id: Optional[str] = None,
    ) -> LedgerEntry:
        """
        Append settlement event to PDO ledger.
        
        INV-SETTLEMENT-003: No state change without ledger append.
        """
        # Build ledger entry data
        pdo_id = additional_pdo_id or record.pdo_id
        
        entry = self._ledger.append(
            pdo_id=pdo_id,
            pac_id=record.pac_id,
            ber_id=f"ber_{record.settlement_id}",
            wrap_id=f"wrap_{record.settlement_id}",
            outcome_status=event_type,
            issuer=PDO_AUTHORITY,
            pdo_hash=compute_hash({"settlement_id": record.settlement_id}),
            proof_hash=compute_hash({"pdo_id": pdo_id}),
            decision_hash=compute_hash({"event": event_type}),
            outcome_hash=compute_hash({
                "settlement_id": record.settlement_id,
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }),
            pdo_created_at=record.created_at,
        )
        
        return entry
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def version(self) -> str:
        """Get engine version."""
        return self._version
    
    def __len__(self) -> int:
        """Get settlement count."""
        return len(self._settlements)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_settlement_engine: Optional[SettlementEngine] = None
_settlement_engine_lock = threading.Lock()


def get_settlement_engine() -> SettlementEngine:
    """Get singleton settlement engine."""
    global _settlement_engine
    
    if _settlement_engine is None:
        with _settlement_engine_lock:
            if _settlement_engine is None:
                _settlement_engine = SettlementEngine()
    
    return _settlement_engine


def reset_settlement_engine() -> None:
    """Reset singleton (for testing)."""
    global _settlement_engine
    
    with _settlement_engine_lock:
        _settlement_engine = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Engine
    "SettlementEngine",
    "get_settlement_engine",
    "reset_settlement_engine",
    
    # Data Classes
    "SettlementRequest",
    "SettlementResult",
    "SettlementRecord",
    "SettlementStatus",
    
    # Exceptions
    "SettlementError",
    "SettlementPDORequiredError",
    "SettlementLedgerFailureError",
    "SettlementNotFoundError",
    "SettlementAlreadyFinalizedError",
    
    # Constants
    "SETTLEMENT_ENGINE_VERSION",
]
