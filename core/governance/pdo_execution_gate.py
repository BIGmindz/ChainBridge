"""
PDO Execution Gate — Canonical Enforcement of Proof → Decision → Outcome Pipeline
════════════════════════════════════════════════════════════════════════════════

This module implements the core PDO enforcement invariant:
    NO EXECUTION WITHOUT PROOF → NO SETTLEMENT WITHOUT DECISION → NO OUTCOME WITHOUT PDO

PAC Reference: PAC-JEFFREY-CHAINBRIDGE-PDO-CORE-EXEC-005
Effective Date: 2025-12-30

INVARIANTS:
    INV-PDO-GATE-001: Execution blocked without valid Proof
    INV-PDO-GATE-002: Settlement blocked without valid Decision
    INV-PDO-GATE-003: Outcome blocked without persisted PDO
    INV-PDO-GATE-004: All gates are fail-closed (default=DENY)
    INV-PDO-GATE-005: Gate violations produce immutable audit records

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
    PDOArtifactFactory,
    PDOAuthorityError,
    PDOIncompleteError,
    PDO_AUTHORITY,
    compute_hash,
)
from core.governance.pdo_registry import (
    PDORegistry,
    PDONotFoundError,
    get_pdo_registry,
)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger("pdo_execution_gate")


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

GATE_VERSION = "1.0.0"
"""PDO Execution Gate version."""

# Gate identifiers for telemetry
GATE_PROOF = "PROOF_GATE"
GATE_DECISION = "DECISION_GATE"
GATE_OUTCOME = "OUTCOME_GATE"
GATE_PDO_FINAL = "PDO_FINAL_GATE"


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class GateResult(Enum):
    """Result of gate evaluation."""
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class GateBlockReason(Enum):
    """Reasons for gate blocking execution."""
    NO_PROOF = "NO_PROOF"
    INVALID_PROOF = "INVALID_PROOF"
    PROOF_HASH_MISMATCH = "PROOF_HASH_MISMATCH"
    NO_DECISION = "NO_DECISION"
    INVALID_DECISION = "INVALID_DECISION"
    DECISION_NOT_APPROVED = "DECISION_NOT_APPROVED"
    NO_PDO = "NO_PDO"
    PDO_NOT_EMITTED = "PDO_NOT_EMITTED"
    AUTHORITY_VIOLATION = "AUTHORITY_VIOLATION"
    ORDERING_VIOLATION = "ORDERING_VIOLATION"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class PDOGateError(Exception):
    """Base exception for PDO gate violations."""
    
    def __init__(
        self,
        message: str,
        gate_id: str,
        reason: GateBlockReason,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.gate_id = gate_id
        self.reason = reason
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to audit-friendly dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "gate_id": self.gate_id,
            "reason": self.reason.value,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class ProofGateError(PDOGateError):
    """Raised when proof gate blocks execution."""
    
    def __init__(self, message: str, reason: GateBlockReason, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, GATE_PROOF, reason, context)


class DecisionGateError(PDOGateError):
    """Raised when decision gate blocks settlement."""
    
    def __init__(self, message: str, reason: GateBlockReason, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, GATE_DECISION, reason, context)


class OutcomeGateError(PDOGateError):
    """Raised when outcome gate blocks completion."""
    
    def __init__(self, message: str, reason: GateBlockReason, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, GATE_OUTCOME, reason, context)


# ═══════════════════════════════════════════════════════════════════════════════
# GATE EVALUATION RECORD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GateEvaluation:
    """
    Immutable record of a gate evaluation.
    
    Every gate check produces this artifact for audit trail.
    """
    
    evaluation_id: str
    gate_id: str
    pac_id: str
    result: GateResult
    reason: Optional[GateBlockReason]
    evaluated_at: str
    proof_hash: Optional[str]
    decision_hash: Optional[str]
    evaluator: str  # GID of evaluator
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "gate_id": self.gate_id,
            "pac_id": self.pac_id,
            "result": self.result.value,
            "reason": self.reason.value if self.reason else None,
            "evaluated_at": self.evaluated_at,
            "proof_hash": self.proof_hash,
            "decision_hash": self.decision_hash,
            "evaluator": self.evaluator,
            "context": self.context,
        }
    
    @property
    def is_pass(self) -> bool:
        """True if gate passed."""
        return self.result == GateResult.PASS
    
    @property
    def is_blocked(self) -> bool:
        """True if gate blocked."""
        return self.result == GateResult.BLOCKED


# ═══════════════════════════════════════════════════════════════════════════════
# PROOF CONTAINER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProofContainer:
    """
    Container for proof artifacts.
    
    Used to package all proof elements before gate evaluation.
    """
    
    pac_id: str
    wrap_id: str
    wrap_data: Dict[str, Any]
    wrap_hash: Optional[str] = None
    received_at: Optional[str] = None
    agent_gid: Optional[str] = None
    
    def __post_init__(self):
        """Compute hash if not provided."""
        if self.wrap_hash is None:
            self.wrap_hash = compute_hash(self.wrap_data)
        if self.received_at is None:
            self.received_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def is_valid(self) -> bool:
        """Check if container has all required fields."""
        return bool(
            self.pac_id
            and self.wrap_id
            and self.wrap_data
            and self.wrap_hash
        )


@dataclass
class DecisionContainer:
    """
    Container for decision artifacts.
    
    Used to package decision elements before gate evaluation.
    """
    
    pac_id: str
    ber_id: str
    ber_data: Dict[str, Any]
    decision_hash: Optional[str] = None
    proof_hash: str = ""  # Must link to proof
    decision_status: str = ""  # APPROVE / REJECT / CORRECTIVE
    decided_at: Optional[str] = None
    issuer: str = PDO_AUTHORITY
    rationale: str = ""
    
    def __post_init__(self):
        """Compute hash if not provided."""
        if self.decision_hash is None:
            combined = {
                "proof_hash": self.proof_hash,
                "ber_data": self.ber_data,
            }
            self.decision_hash = compute_hash(combined)
        if self.decided_at is None:
            self.decided_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def is_approved(self) -> bool:
        """True if decision is APPROVE."""
        return self.decision_status in ("APPROVE", "ACCEPTED")
    
    @property
    def is_valid(self) -> bool:
        """Check if container has all required fields."""
        return bool(
            self.pac_id
            and self.ber_id
            and self.ber_data
            and self.decision_hash
            and self.proof_hash
            and self.decision_status
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PDO EXECUTION GATE (CORE ENFORCEMENT)
# ═══════════════════════════════════════════════════════════════════════════════

class PDOExecutionGate:
    """
    Central enforcement gate for PDO pipeline.
    
    This is the SINGLE enforcement point for:
        - Proof → Execution authorization
        - Decision → Settlement authorization
        - PDO → Outcome finalization
    
    All paths through the execution spine MUST pass through this gate.
    
    INVARIANTS:
        INV-PDO-GATE-001: No execution without proof (fail-closed)
        INV-PDO-GATE-002: No settlement without decision (fail-closed)
        INV-PDO-GATE-003: No outcome without PDO (fail-closed)
        INV-PDO-GATE-004: All evaluations recorded immutably
    """
    
    def __init__(self, registry: Optional[PDORegistry] = None):
        """
        Initialize PDO Execution Gate.
        
        Args:
            registry: PDO registry for lookup (defaults to singleton)
        """
        self._registry = registry or get_pdo_registry()
        self._evaluations: List[GateEvaluation] = []
        self._lock = threading.Lock()
        self._strict_mode = True  # Fail-closed by default
    
    # ───────────────────────────────────────────────────────────────────────────
    # GATE 1: PROOF GATE (No Execution Without Proof)
    # ───────────────────────────────────────────────────────────────────────────
    
    def require_proof(self, proof: ProofContainer) -> GateEvaluation:
        """
        Enforce INV-PDO-GATE-001: No execution without valid proof.
        
        Args:
            proof: ProofContainer with WRAP data
        
        Returns:
            GateEvaluation record
        
        Raises:
            ProofGateError: If proof gate blocks execution
        """
        evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Check proof existence
        if proof is None:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_PROOF,
                pac_id="UNKNOWN",
                result=GateResult.BLOCKED,
                reason=GateBlockReason.NO_PROOF,
                evaluated_at=now,
                proof_hash=None,
                decision_hash=None,
                evaluator=PDO_AUTHORITY,
            )
            self._record_evaluation(evaluation)
            raise ProofGateError(
                "Execution blocked: No proof provided",
                GateBlockReason.NO_PROOF,
            )
        
        # Check proof validity
        if not proof.is_valid:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_PROOF,
                pac_id=proof.pac_id or "UNKNOWN",
                result=GateResult.BLOCKED,
                reason=GateBlockReason.INVALID_PROOF,
                evaluated_at=now,
                proof_hash=proof.wrap_hash,
                decision_hash=None,
                evaluator=PDO_AUTHORITY,
                context={"missing_fields": self._get_missing_proof_fields(proof)},
            )
            self._record_evaluation(evaluation)
            raise ProofGateError(
                f"Execution blocked: Invalid proof for PAC '{proof.pac_id}'",
                GateBlockReason.INVALID_PROOF,
                {"pac_id": proof.pac_id},
            )
        
        # Proof passes
        evaluation = GateEvaluation(
            evaluation_id=evaluation_id,
            gate_id=GATE_PROOF,
            pac_id=proof.pac_id,
            result=GateResult.PASS,
            reason=None,
            evaluated_at=now,
            proof_hash=proof.wrap_hash,
            decision_hash=None,
            evaluator=PDO_AUTHORITY,
        )
        self._record_evaluation(evaluation)
        
        logger.info(
            "PROOF_GATE_PASS: pac_id=%s proof_hash=%s",
            proof.pac_id,
            proof.wrap_hash[:16] + "...",
        )
        
        return evaluation
    
    # ───────────────────────────────────────────────────────────────────────────
    # GATE 2: DECISION GATE (No Settlement Without Decision)
    # ───────────────────────────────────────────────────────────────────────────
    
    def require_decision(
        self,
        decision: DecisionContainer,
        proof_hash: str,
    ) -> GateEvaluation:
        """
        Enforce INV-PDO-GATE-002: No settlement without valid decision.
        
        Args:
            decision: DecisionContainer with BER data
            proof_hash: Hash from proof gate (must match)
        
        Returns:
            GateEvaluation record
        
        Raises:
            DecisionGateError: If decision gate blocks settlement
        """
        evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Check decision existence
        if decision is None:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_DECISION,
                pac_id="UNKNOWN",
                result=GateResult.BLOCKED,
                reason=GateBlockReason.NO_DECISION,
                evaluated_at=now,
                proof_hash=proof_hash,
                decision_hash=None,
                evaluator=PDO_AUTHORITY,
            )
            self._record_evaluation(evaluation)
            raise DecisionGateError(
                "Settlement blocked: No decision provided",
                GateBlockReason.NO_DECISION,
            )
        
        # Check decision validity
        if not decision.is_valid:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_DECISION,
                pac_id=decision.pac_id or "UNKNOWN",
                result=GateResult.BLOCKED,
                reason=GateBlockReason.INVALID_DECISION,
                evaluated_at=now,
                proof_hash=proof_hash,
                decision_hash=decision.decision_hash,
                evaluator=PDO_AUTHORITY,
            )
            self._record_evaluation(evaluation)
            raise DecisionGateError(
                f"Settlement blocked: Invalid decision for PAC '{decision.pac_id}'",
                GateBlockReason.INVALID_DECISION,
                {"pac_id": decision.pac_id},
            )
        
        # Check proof hash linkage
        if decision.proof_hash != proof_hash:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_DECISION,
                pac_id=decision.pac_id,
                result=GateResult.BLOCKED,
                reason=GateBlockReason.PROOF_HASH_MISMATCH,
                evaluated_at=now,
                proof_hash=proof_hash,
                decision_hash=decision.decision_hash,
                evaluator=PDO_AUTHORITY,
                context={
                    "expected_proof_hash": proof_hash[:16] + "...",
                    "decision_proof_hash": decision.proof_hash[:16] + "...",
                },
            )
            self._record_evaluation(evaluation)
            raise DecisionGateError(
                f"Settlement blocked: Proof hash mismatch for PAC '{decision.pac_id}'",
                GateBlockReason.PROOF_HASH_MISMATCH,
                {"pac_id": decision.pac_id},
            )
        
        # Check decision approval (for settlement)
        if not decision.is_approved:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_DECISION,
                pac_id=decision.pac_id,
                result=GateResult.BLOCKED,
                reason=GateBlockReason.DECISION_NOT_APPROVED,
                evaluated_at=now,
                proof_hash=proof_hash,
                decision_hash=decision.decision_hash,
                evaluator=PDO_AUTHORITY,
                context={"decision_status": decision.decision_status},
            )
            self._record_evaluation(evaluation)
            raise DecisionGateError(
                f"Settlement blocked: Decision not approved for PAC '{decision.pac_id}' "
                f"(status={decision.decision_status})",
                GateBlockReason.DECISION_NOT_APPROVED,
                {"pac_id": decision.pac_id, "status": decision.decision_status},
            )
        
        # Decision passes
        evaluation = GateEvaluation(
            evaluation_id=evaluation_id,
            gate_id=GATE_DECISION,
            pac_id=decision.pac_id,
            result=GateResult.PASS,
            reason=None,
            evaluated_at=now,
            proof_hash=proof_hash,
            decision_hash=decision.decision_hash,
            evaluator=PDO_AUTHORITY,
        )
        self._record_evaluation(evaluation)
        
        logger.info(
            "DECISION_GATE_PASS: pac_id=%s decision_hash=%s",
            decision.pac_id,
            decision.decision_hash[:16] + "...",
        )
        
        return evaluation
    
    # ───────────────────────────────────────────────────────────────────────────
    # GATE 3: OUTCOME GATE (No Outcome Without PDO)
    # ───────────────────────────────────────────────────────────────────────────
    
    def require_pdo(self, pac_id: str) -> Tuple[GateEvaluation, PDOArtifact]:
        """
        Enforce INV-PDO-GATE-003: No outcome without persisted PDO.
        
        Args:
            pac_id: PAC identifier
        
        Returns:
            Tuple of (GateEvaluation, PDOArtifact)
        
        Raises:
            OutcomeGateError: If PDO gate blocks outcome
        """
        evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Check PDO existence
        pdo = self._registry.get_by_pac_id(pac_id)
        
        if pdo is None:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_OUTCOME,
                pac_id=pac_id,
                result=GateResult.BLOCKED,
                reason=GateBlockReason.NO_PDO,
                evaluated_at=now,
                proof_hash=None,
                decision_hash=None,
                evaluator=PDO_AUTHORITY,
            )
            self._record_evaluation(evaluation)
            raise OutcomeGateError(
                f"Outcome blocked: No PDO for PAC '{pac_id}'",
                GateBlockReason.NO_PDO,
                {"pac_id": pac_id},
            )
        
        # PDO exists, pass gate
        evaluation = GateEvaluation(
            evaluation_id=evaluation_id,
            gate_id=GATE_OUTCOME,
            pac_id=pac_id,
            result=GateResult.PASS,
            reason=None,
            evaluated_at=now,
            proof_hash=pdo.proof_hash,
            decision_hash=pdo.decision_hash,
            evaluator=PDO_AUTHORITY,
            context={"pdo_id": pdo.pdo_id},
        )
        self._record_evaluation(evaluation)
        
        logger.info(
            "OUTCOME_GATE_PASS: pac_id=%s pdo_id=%s",
            pac_id,
            pdo.pdo_id,
        )
        
        return evaluation, pdo
    
    # ───────────────────────────────────────────────────────────────────────────
    # PDO VERIFICATION (Settlement Support)
    # ───────────────────────────────────────────────────────────────────────────
    
    def verify_pdo_exists(
        self,
        pdo_id: str,
        pac_id: str,
        evaluator: str = PDO_AUTHORITY,
    ) -> GateEvaluation:
        """
        Verify that a PDO exists and is valid for settlement.
        
        Used by settlement engine to enforce INV-SETTLEMENT-001:
        No settlement without valid PDO.
        
        Args:
            pdo_id: PDO identifier to verify
            pac_id: PAC identifier for context
            evaluator: GID of evaluating agent
        
        Returns:
            GateEvaluation record
        """
        evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Try to find PDO by PDO ID first, then fall back to PAC ID
        pdo = None
        try:
            pdo = self._registry.get_by_pdo_id(pdo_id)
        except AttributeError:
            pass
        
        # Fallback to PAC lookup
        if pdo is None:
            pdo = self._registry.get_by_pac_id(pac_id)
        
        if pdo is None:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_PDO_FINAL,
                pac_id=pac_id,
                result=GateResult.BLOCKED,
                reason=GateBlockReason.NO_PDO,
                evaluated_at=now,
                proof_hash=None,
                decision_hash=None,
                evaluator=evaluator,
                context={"pdo_id": pdo_id, "pac_id": pac_id},
            )
            self._record_evaluation(evaluation)
            return evaluation
        
        # Verify PDO ID matches (if found via PAC)
        if pdo.pdo_id != pdo_id:
            evaluation = GateEvaluation(
                evaluation_id=evaluation_id,
                gate_id=GATE_PDO_FINAL,
                pac_id=pac_id,
                result=GateResult.BLOCKED,
                reason=GateBlockReason.PDO_NOT_EMITTED,
                evaluated_at=now,
                proof_hash=pdo.proof_hash,
                decision_hash=pdo.decision_hash,
                evaluator=evaluator,
                context={
                    "expected_pdo_id": pdo_id,
                    "found_pdo_id": pdo.pdo_id,
                },
            )
            self._record_evaluation(evaluation)
            return evaluation
        
        # PDO exists and matches
        evaluation = GateEvaluation(
            evaluation_id=evaluation_id,
            gate_id=GATE_PDO_FINAL,
            pac_id=pac_id,
            result=GateResult.PASS,
            reason=None,
            evaluated_at=now,
            proof_hash=pdo.proof_hash,
            decision_hash=pdo.decision_hash,
            evaluator=evaluator,
            context={"pdo_id": pdo.pdo_id, "outcome": pdo.outcome_status},
        )
        self._record_evaluation(evaluation)
        
        logger.info(
            "PDO_VERIFY_PASS: pdo_id=%s pac_id=%s evaluator=%s",
            pdo_id,
            pac_id,
            evaluator,
        )
        
        return evaluation
    
    # ───────────────────────────────────────────────────────────────────────────
    # COMBINED GATE: FULL PDO PIPELINE
    # ───────────────────────────────────────────────────────────────────────────
    
    def execute_with_pdo(
        self,
        proof: ProofContainer,
        decision: DecisionContainer,
        persist: bool = True,
    ) -> PDOArtifact:
        """
        Execute full PDO pipeline with all gates.
        
        This is the canonical entry point for PDO-governed execution:
            1. Proof gate
            2. Decision gate
            3. PDO creation
            4. PDO registration (if persist=True)
        
        Args:
            proof: ProofContainer with WRAP data
            decision: DecisionContainer with BER data
            persist: Whether to register PDO (default True)
        
        Returns:
            PDOArtifact: Created PDO
        
        Raises:
            ProofGateError: If proof gate fails
            DecisionGateError: If decision gate fails
            PDOAuthorityError: If authority check fails
        """
        # Gate 1: Proof
        proof_eval = self.require_proof(proof)
        
        # Gate 2: Decision (linked to proof)
        decision_eval = self.require_decision(decision, proof.wrap_hash)
        
        # Create PDO
        pdo = PDOArtifactFactory.create(
            pac_id=proof.pac_id,
            wrap_id=proof.wrap_id,
            wrap_data=proof.wrap_data,
            ber_id=decision.ber_id,
            ber_data=decision.ber_data,
            outcome_status="ACCEPTED" if decision.is_approved else "CORRECTIVE",
            issuer=PDO_AUTHORITY,
            proof_at=proof.received_at,
            decision_at=decision.decided_at,
        )
        
        # Register PDO
        if persist:
            self._registry.register(pdo)
        
        logger.info(
            "PDO_CREATED: pdo_id=%s pac_id=%s outcome=%s",
            pdo.pdo_id,
            pdo.pac_id,
            pdo.outcome_status,
        )
        
        return pdo
    
    # ───────────────────────────────────────────────────────────────────────────
    # AUDIT & QUERY
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_evaluations(
        self,
        pac_id: Optional[str] = None,
        gate_id: Optional[str] = None,
        result: Optional[GateResult] = None,
    ) -> List[GateEvaluation]:
        """
        Query gate evaluations with optional filters.
        
        Args:
            pac_id: Filter by PAC ID
            gate_id: Filter by gate ID
            result: Filter by result
        
        Returns:
            List of matching evaluations
        """
        with self._lock:
            evals = self._evaluations.copy()
        
        if pac_id:
            evals = [e for e in evals if e.pac_id == pac_id]
        if gate_id:
            evals = [e for e in evals if e.gate_id == gate_id]
        if result:
            evals = [e for e in evals if e.result == result]
        
        return evals
    
    def get_blocked_evaluations(self) -> List[GateEvaluation]:
        """Get all blocked evaluations."""
        return self.get_evaluations(result=GateResult.BLOCKED)
    
    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Export full audit trail for compliance."""
        with self._lock:
            return [e.to_dict() for e in self._evaluations]
    
    # ───────────────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ───────────────────────────────────────────────────────────────────────────
    
    def _record_evaluation(self, evaluation: GateEvaluation) -> None:
        """Record evaluation to audit trail (thread-safe)."""
        with self._lock:
            self._evaluations.append(evaluation)
        
        # Log blocked evaluations at warning level
        if evaluation.is_blocked:
            logger.warning(
                "GATE_BLOCKED: gate=%s pac_id=%s reason=%s",
                evaluation.gate_id,
                evaluation.pac_id,
                evaluation.reason.value if evaluation.reason else "UNKNOWN",
            )
    
    def _get_missing_proof_fields(self, proof: ProofContainer) -> List[str]:
        """Get list of missing proof fields."""
        missing = []
        if not proof.pac_id:
            missing.append("pac_id")
        if not proof.wrap_id:
            missing.append("wrap_id")
        if not proof.wrap_data:
            missing.append("wrap_data")
        if not proof.wrap_hash:
            missing.append("wrap_hash")
        return missing


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_default_gate: Optional[PDOExecutionGate] = None
_gate_lock = threading.Lock()


def get_pdo_gate() -> PDOExecutionGate:
    """Get the default PDO execution gate (singleton)."""
    global _default_gate
    with _gate_lock:
        if _default_gate is None:
            _default_gate = PDOExecutionGate()
        return _default_gate


def reset_pdo_gate() -> None:
    """Reset the default PDO gate (for testing)."""
    global _default_gate
    with _gate_lock:
        _default_gate = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Gate
    "PDOExecutionGate",
    "get_pdo_gate",
    "reset_pdo_gate",
    
    # Containers
    "ProofContainer",
    "DecisionContainer",
    
    # Evaluation
    "GateEvaluation",
    "GateResult",
    "GateBlockReason",
    
    # Exceptions
    "PDOGateError",
    "ProofGateError",
    "DecisionGateError",
    "OutcomeGateError",
    
    # Constants
    "GATE_VERSION",
    "GATE_PROOF",
    "GATE_DECISION",
    "GATE_OUTCOME",
]
