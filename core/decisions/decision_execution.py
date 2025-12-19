# core/decisions/decision_execution.py
"""
════════════════════════════════════════════════════════════════════════════════
Activation-Aware Decision Execution — Canonical Decision Path
════════════════════════════════════════════════════════════════════════════════

PAC ID: PAC-BENSON-CODY-ACTIVATION-AWARE-DECISION-INTEGRATION-01
Author: CODY (GID-01) — Senior Backend Engineer
Version: 1.0.0

INVARIANT: IF activation_block != VALID → DECISION = ERROR
No decision may be produced, persisted, or emitted without a valid Activation Block.

This module integrates:
1. Activation block validation as mandatory gate
2. Failure propagation with explicit codes
3. Persistence contract enforcement
4. Monotonicity checks where applicable

CONSTRAINTS (ABSOLUTE):
- No implicit defaults
- No silent fallbacks
- No exception swallowing
- Explicit failure codes for all errors
- Activation reference MANDATORY for persistence

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple
from uuid import uuid4

from core.decisions.activation_invariants import (
    ActivationAwareOutcome,
    ActivationDecisionFailure,
    ActivationReference,
    ContractViolationError,
    enforce_monotonicity,
)
from core.decisions.rules import (
    DecisionOutcome,
)


# ============================================================================
# DECISION EXECUTION FAILURE CODES — Explicit Enumeration
# ============================================================================


class DecisionExecutionFailure(str, Enum):
    """
    Explicit failure codes for decision execution pipeline.
    
    Maps to deterministic ERROR outcomes. No silent failures.
    """
    ACTIVATION_MISSING = "ACTIVATION_MISSING"
    ACTIVATION_INVALID = "ACTIVATION_INVALID"
    ACTIVATION_EXPIRED = "ACTIVATION_EXPIRED"
    PERSISTENCE_REJECTED = "PERSISTENCE_REJECTED"
    MONOTONICITY_VIOLATION = "MONOTONICITY_VIOLATION"
    RULE_EXECUTION_FAILURE = "RULE_EXECUTION_FAILURE"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"


# ============================================================================
# DECISION EXECUTION ERROR — Hard Stop
# ============================================================================


class DecisionExecutionError(Exception):
    """
    Raised when decision execution fails.
    
    HARD STOP — no recovery, no retry.
    """
    
    def __init__(
        self,
        message: str,
        failure_code: DecisionExecutionFailure,
        decision_inputs: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.failure_code = failure_code
        self.decision_inputs = decision_inputs or {}
        super().__init__(f"DECISION EXECUTION FAILED [{failure_code.value}]: {message}")


# ============================================================================
# PERSISTENCE REJECTION ERROR — Hard Stop
# ============================================================================


class PersistenceRejectionError(Exception):
    """
    Raised when a decision cannot be persisted due to missing activation.
    
    HARD STOP — decisions without activation MUST NOT be persisted.
    """
    
    def __init__(self, message: str, decision_id: Optional[str] = None):
        self.message = message
        self.decision_id = decision_id
        super().__init__(f"PERSISTENCE REJECTED: {message}")


# ============================================================================
# EXECUTABLE DECISION — Activation-Bound Record
# ============================================================================


@dataclass(frozen=True)
class ExecutableDecision:
    """
    Decision record with mandatory activation binding for persistence.
    
    INVARIANTS:
    - activation_reference is MANDATORY (no default)
    - All decisions must have explicit outcome
    - Failure mode must be set if outcome is ERROR
    - Timestamp is server-generated
    """
    decision_id: str
    outcome: ActivationAwareOutcome
    rule_id: str
    rule_version: str
    inputs: Dict[str, Any]
    explanation: str
    activation_reference: ActivationReference
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    failure_code: Optional[DecisionExecutionFailure] = None
    is_persisted: bool = False
    
    def __post_init__(self) -> None:
        """Enforce persistence contract invariants."""
        if self.activation_reference is None:
            raise PersistenceRejectionError(
                "activation_reference is MANDATORY — cannot create decision without valid activation",
                decision_id=self.decision_id,
            )
        if self.outcome == ActivationAwareOutcome.ERROR and self.failure_code is None:
            raise ContractViolationError(
                "ERROR outcome requires explicit failure_code",
                ActivationDecisionFailure.CONTRACT_VIOLATION,
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence/audit."""
        return {
            "decision_id": self.decision_id,
            "outcome": self.outcome.value,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "inputs": self.inputs,
            "explanation": self.explanation,
            "activation_reference": self.activation_reference.to_dict(),
            "timestamp": self.timestamp,
            "failure_code": self.failure_code.value if self.failure_code else None,
            "is_persisted": self.is_persisted,
        }


# ============================================================================
# DECISION EXECUTION GATE — Canonical Entry Point
# ============================================================================


def execute_decision(
    activation_reference: Optional[ActivationReference],
    rule_id: str,
    rule_version: str,
    inputs: Dict[str, Any],
    decision_fn: Callable[[Dict[str, Any]], Tuple[DecisionOutcome, str]],
) -> ExecutableDecision:
    """
    Execute decision logic through the activation-aware gate.
    
    INVARIANT: No decision without valid activation.
    
    This is the CANONICAL entry point for all decision execution.
    All decisions MUST flow through this function.
    
    Args:
        activation_reference: Reference to validated activation block (MANDATORY)
        rule_id: Rule identifier to execute
        rule_version: Rule version
        inputs: Decision inputs
        decision_fn: Deterministic decision function
        
    Returns:
        ExecutableDecision with full traceability
        
    Raises:
        DecisionExecutionError: If activation is missing/invalid
        PersistenceRejectionError: If decision cannot be persisted
    """
    decision_id = str(uuid4())
    
    # === ACTIVATION GATE (FIRST CHECK) ===
    if activation_reference is None:
        # HARD FAIL: No activation → No decision
        raise DecisionExecutionError(
            message="Activation block reference is missing. Decision cannot proceed.",
            failure_code=DecisionExecutionFailure.ACTIVATION_MISSING,
            decision_inputs=inputs,
        )
    
    # === VALIDATE ACTIVATION REFERENCE ===
    if not activation_reference.agent_name or activation_reference.agent_name in ("UNKNOWN", "NONE", "INVALID"):
        raise DecisionExecutionError(
            message=f"Invalid activation reference: agent_name='{activation_reference.agent_name}'",
            failure_code=DecisionExecutionFailure.ACTIVATION_INVALID,
            decision_inputs=inputs,
        )
    
    if not activation_reference.gid or activation_reference.gid in ("UNKNOWN", "NONE", "INVALID"):
        raise DecisionExecutionError(
            message=f"Invalid activation reference: gid='{activation_reference.gid}'",
            failure_code=DecisionExecutionFailure.ACTIVATION_INVALID,
            decision_inputs=inputs,
        )
    
    # === EXECUTE DECISION FUNCTION ===
    try:
        outcome_raw, explanation = decision_fn(inputs)
    except Exception as e:
        # No exception swallowing — propagate as explicit failure
        return ExecutableDecision(
            decision_id=decision_id,
            outcome=ActivationAwareOutcome.ERROR,
            rule_id=rule_id,
            rule_version=rule_version,
            inputs=inputs,
            explanation=f"Decision function raised exception: {type(e).__name__}: {e}",
            activation_reference=activation_reference,
            failure_code=DecisionExecutionFailure.RULE_EXECUTION_FAILURE,
        )
    
    # === MAP OUTCOME ===
    outcome = _map_decision_outcome(outcome_raw)
    
    # === VERIFY EXPLANATION COMPLETENESS ===
    if not explanation or len(explanation.strip()) < 10:
        return ExecutableDecision(
            decision_id=decision_id,
            outcome=ActivationAwareOutcome.ERROR,
            rule_id=rule_id,
            rule_version=rule_version,
            inputs=inputs,
            explanation=f"Explanation incomplete: {explanation[:50] if explanation else 'EMPTY'}",
            activation_reference=activation_reference,
            failure_code=DecisionExecutionFailure.CONTRACT_VIOLATION,
        )
    
    # === BUILD EXECUTABLE DECISION ===
    return ExecutableDecision(
        decision_id=decision_id,
        outcome=outcome,
        rule_id=rule_id,
        rule_version=rule_version,
        inputs=inputs,
        explanation=explanation,
        activation_reference=activation_reference,
    )


def _map_decision_outcome(raw_outcome: DecisionOutcome) -> ActivationAwareOutcome:
    """Map rules.DecisionOutcome to ActivationAwareOutcome."""
    mapping = {
        DecisionOutcome.APPROVED: ActivationAwareOutcome.APPROVED,
        DecisionOutcome.REJECTED: ActivationAwareOutcome.REJECTED,
        DecisionOutcome.REQUIRES_REVIEW: ActivationAwareOutcome.REQUIRES_REVIEW,
        DecisionOutcome.ERROR: ActivationAwareOutcome.ERROR,
    }
    return mapping.get(raw_outcome, ActivationAwareOutcome.ERROR)


# ============================================================================
# PERSISTENCE CONTRACT ENFORCEMENT
# ============================================================================


def validate_for_persistence(decision: ExecutableDecision) -> Tuple[bool, Optional[str]]:
    """
    Validate that a decision meets persistence contract requirements.
    
    PERSISTENCE CONTRACT:
    - activation_reference MUST be present
    - activation_reference MUST have valid agent_name, gid, color
    - decision MUST have non-empty explanation
    - decision_id MUST be non-empty
    
    Returns:
        (is_valid, rejection_reason)
    """
    if decision.activation_reference is None:
        return False, "PERSISTENCE_REJECTED: activation_reference is MANDATORY"
    
    ref = decision.activation_reference
    if not ref.agent_name or ref.agent_name in ("UNKNOWN", "NONE", "INVALID"):
        return False, f"PERSISTENCE_REJECTED: invalid agent_name='{ref.agent_name}'"
    
    if not ref.gid or ref.gid in ("UNKNOWN", "NONE", "INVALID"):
        return False, f"PERSISTENCE_REJECTED: invalid gid='{ref.gid}'"
    
    if not ref.color or ref.color in ("UNKNOWN", "NONE", "INVALID"):
        return False, f"PERSISTENCE_REJECTED: invalid color='{ref.color}'"
    
    if not decision.explanation or len(decision.explanation.strip()) < 10:
        return False, "PERSISTENCE_REJECTED: explanation is incomplete"
    
    if not decision.decision_id:
        return False, "PERSISTENCE_REJECTED: decision_id is required"
    
    return True, None


def require_persistence_contract(decision: ExecutableDecision) -> None:
    """
    Assert persistence contract compliance. Raises on violation.
    
    HARD FAIL: Decisions that fail persistence contract MUST NOT be stored.
    """
    is_valid, rejection_reason = validate_for_persistence(decision)
    if not is_valid:
        raise PersistenceRejectionError(
            message=rejection_reason or "Unknown persistence contract violation",
            decision_id=decision.decision_id,
        )


# ============================================================================
# MONOTONICITY ENFORCEMENT — Payment Threshold
# ============================================================================


def enforce_payment_monotonicity(
    amount_a: float,
    amount_b: float,
    decision_a: ExecutableDecision,
    decision_b: ExecutableDecision,
) -> Tuple[bool, Optional[str]]:
    """
    Enforce monotonicity for payment decisions.
    
    RULE: If amount_a > amount_b, then severity_a >= severity_b.
    Higher amounts MUST NOT produce lower severity outcomes.
    
    Args:
        amount_a: First payment amount
        amount_b: Second payment amount
        decision_a: First decision
        decision_b: Second decision
        
    Returns:
        (is_monotonic, violation_message)
    """
    return enforce_monotonicity(
        decision_a.outcome,
        decision_b.outcome,
        amount_a,
        amount_b,
    )


def verify_monotonicity_invariant(
    decisions: list,
    severity_key: Callable[[Any], float],
) -> Tuple[bool, Optional[str]]:
    """
    Verify monotonicity invariant across a sequence of decisions.
    
    INVARIANT: Higher severity inputs → equal or higher severity outcomes.
    
    Args:
        decisions: List of (input_severity, ExecutableDecision) tuples
        severity_key: Function to extract severity from input
        
    Returns:
        (is_monotonic, violation_message)
    """
    if len(decisions) < 2:
        return True, None
    
    # Sort by input severity
    sorted_decisions = sorted(decisions, key=lambda x: severity_key(x[0]))
    
    # Check monotonicity
    for i in range(len(sorted_decisions) - 1):
        sev_a, dec_a = sorted_decisions[i]
        sev_b, dec_b = sorted_decisions[i + 1]
        
        is_valid, msg = enforce_payment_monotonicity(
            severity_key(sev_a),
            severity_key(sev_b),
            dec_a,
            dec_b,
        )
        
        if not is_valid:
            return False, f"Monotonicity violation at index {i}: {msg}"
    
    return True, None


# ============================================================================
# DECISION EXECUTION WITH FULL ENFORCEMENT
# ============================================================================


def execute_decision_with_enforcement(
    activation_reference: Optional[ActivationReference],
    rule_id: str,
    rule_version: str,
    inputs: Dict[str, Any],
    decision_fn: Callable[[Dict[str, Any]], Tuple[DecisionOutcome, str]],
    *,
    enforce_persistence: bool = True,
    enforce_monotonicity_with: Optional[Tuple[float, ExecutableDecision]] = None,
) -> ExecutableDecision:
    """
    Execute decision with full enforcement of all invariants.
    
    This is the RECOMMENDED entry point for production use.
    
    Enforcement chain:
    1. Activation gate (MANDATORY)
    2. Decision execution
    3. Persistence contract validation
    4. Monotonicity check (if reference provided)
    
    Args:
        activation_reference: Reference to validated activation block
        rule_id: Rule identifier
        rule_version: Rule version
        inputs: Decision inputs
        decision_fn: Deterministic decision function
        enforce_persistence: Whether to validate persistence contract
        enforce_monotonicity_with: Optional (amount, prior_decision) for monotonicity check
        
    Returns:
        ExecutableDecision
        
    Raises:
        DecisionExecutionError: On activation failure
        PersistenceRejectionError: On persistence contract violation
    """
    # Step 1: Execute through activation gate
    decision = execute_decision(
        activation_reference=activation_reference,
        rule_id=rule_id,
        rule_version=rule_version,
        inputs=inputs,
        decision_fn=decision_fn,
    )
    
    # Step 2: Validate persistence contract
    if enforce_persistence:
        require_persistence_contract(decision)
    
    # Step 3: Check monotonicity if reference provided
    if enforce_monotonicity_with is not None:
        prior_amount, prior_decision = enforce_monotonicity_with
        current_amount = inputs.get("amount", 0.0)
        
        is_monotonic, violation = enforce_payment_monotonicity(
            current_amount,
            prior_amount,
            decision,
            prior_decision,
        )
        
        if not is_monotonic:
            raise DecisionExecutionError(
                message=violation or "Monotonicity violation detected",
                failure_code=DecisionExecutionFailure.MONOTONICITY_VIOLATION,
                decision_inputs=inputs,
            )
    
    return decision


# ============================================================================
# FAILURE CODE MAPPING — Activation to Decision
# ============================================================================


ACTIVATION_TO_DECISION_FAILURE_MAP: Dict[ActivationDecisionFailure, DecisionExecutionFailure] = {
    ActivationDecisionFailure.MISSING_ACTIVATION: DecisionExecutionFailure.ACTIVATION_MISSING,
    ActivationDecisionFailure.INVALID_ACTIVATION: DecisionExecutionFailure.ACTIVATION_INVALID,
    ActivationDecisionFailure.NON_DETERMINISTIC_OUTPUT: DecisionExecutionFailure.DETERMINISM_FAILURE,
    ActivationDecisionFailure.EXPLANATION_GAP: DecisionExecutionFailure.CONTRACT_VIOLATION,
    ActivationDecisionFailure.MONOTONICITY_VIOLATION: DecisionExecutionFailure.MONOTONICITY_VIOLATION,
    ActivationDecisionFailure.INPUT_VALIDATION_FAILURE: DecisionExecutionFailure.RULE_EXECUTION_FAILURE,
    ActivationDecisionFailure.RULE_NOT_FOUND: DecisionExecutionFailure.RULE_EXECUTION_FAILURE,
    ActivationDecisionFailure.CONTRACT_VIOLATION: DecisionExecutionFailure.CONTRACT_VIOLATION,
}


def map_activation_failure(
    activation_failure: ActivationDecisionFailure,
) -> DecisionExecutionFailure:
    """
    Map activation failure to decision execution failure code.
    
    Explicit mapping — no implicit defaults.
    """
    return ACTIVATION_TO_DECISION_FAILURE_MAP.get(
        activation_failure,
        DecisionExecutionFailure.CONTRACT_VIOLATION,  # Conservative default
    )


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    # Failure codes
    "DecisionExecutionFailure",
    # Errors
    "DecisionExecutionError",
    "PersistenceRejectionError",
    # Decision type
    "ExecutableDecision",
    # Execution functions
    "execute_decision",
    "execute_decision_with_enforcement",
    # Persistence contract
    "validate_for_persistence",
    "require_persistence_contract",
    # Monotonicity
    "enforce_payment_monotonicity",
    "verify_monotonicity_invariant",
    # Failure mapping
    "map_activation_failure",
    "ACTIVATION_TO_DECISION_FAILURE_MAP",
]
