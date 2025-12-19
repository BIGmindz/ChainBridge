# core/decisions/activation_invariants.py
"""
════════════════════════════════════════════════════════════════════════════════
Activation-Aware Decision Invariants — Glass-Box Decision Contract
════════════════════════════════════════════════════════════════════════════════

PAC ID: PAC-MAGGIE-ACTIVATION-BLOCK-DECISION-INTEGRITY-01
Author: MAGGIE (GID-10) — ML & Applied AI Lead
Version: 1.0.0

INVARIANT: IF activation_block != VALID → DECISION = ERROR
No fallback. No default. No probabilistic override.

This module specifies:
1. Activation-aware decision contract
2. Mandatory decision output fields
3. Monotonicity constraints
4. Explanation completeness requirements
5. Failure mode enumeration

CONSTRAINTS (ABSOLUTE):
- No opaque inference
- No learned weights
- No hidden state
- Deterministic only
- Activation block MUST be valid before any decision

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple


# ============================================================================
# FAILURE MODES — Explicit Enumeration
# ============================================================================


class ActivationDecisionFailure(str, Enum):
    """
    Explicit failure modes for activation-aware decisions.
    
    Each failure mode maps to a deterministic ERROR outcome.
    No silent failures. No soft warnings.
    """
    MISSING_ACTIVATION = "MISSING_ACTIVATION"
    INVALID_ACTIVATION = "INVALID_ACTIVATION"
    NON_DETERMINISTIC_OUTPUT = "NON_DETERMINISTIC_OUTPUT"
    EXPLANATION_GAP = "EXPLANATION_GAP"
    MONOTONICITY_VIOLATION = "MONOTONICITY_VIOLATION"
    INPUT_VALIDATION_FAILURE = "INPUT_VALIDATION_FAILURE"
    RULE_NOT_FOUND = "RULE_NOT_FOUND"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"


# ============================================================================
# DECISION OUTCOME — Activation-Aware
# ============================================================================


class ActivationAwareOutcome(str, Enum):
    """
    Decision outcomes that are activation-aware.
    
    Severity ordering (monotonic):
    APPROVED (100) < REJECTED (200) < REQUIRES_REVIEW (300) < ERROR (400)
    """
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"
    ERROR = "error"


# Severity map for monotonicity enforcement
OUTCOME_SEVERITY_MAP: Dict[ActivationAwareOutcome, int] = {
    ActivationAwareOutcome.APPROVED: 100,
    ActivationAwareOutcome.REJECTED: 200,
    ActivationAwareOutcome.REQUIRES_REVIEW: 300,
    ActivationAwareOutcome.ERROR: 400,
}


# ============================================================================
# ACTIVATION REFERENCE — Minimal Binding
# ============================================================================


@dataclass(frozen=True)
class ActivationReference:
    """
    Minimal activation block reference for decision binding.
    
    Links a decision to its authorizing activation block.
    """
    agent_name: str
    gid: str
    color: str
    validation_timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "gid": self.gid,
            "color": self.color,
            "validation_timestamp": self.validation_timestamp,
        }


# ============================================================================
# GLASS-BOX DECISION CONTRACT — Mandatory Fields
# ============================================================================


@dataclass(frozen=True)
class ActivationAwareDecision:
    """
    Glass-box decision with mandatory activation binding.
    
    MANDATORY FIELDS (all required, no defaults):
    - decision_outcome: The outcome of the decision
    - decision_rule_id: The rule that produced the outcome
    - decision_inputs: All inputs used in the decision
    - decision_explanation: Human-readable explanation
    - activation_reference: Link to authorizing activation block
    
    INVARIANTS:
    - Immutable after creation
    - All fields must be non-None
    - Explanation must be non-empty
    - Activation reference must be valid
    """
    decision_outcome: ActivationAwareOutcome
    decision_rule_id: str
    decision_rule_version: str
    decision_inputs: Dict[str, Any]
    decision_explanation: str
    activation_reference: ActivationReference
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    failure_mode: Optional[ActivationDecisionFailure] = None
    
    def __post_init__(self) -> None:
        """Validate contract invariants on creation."""
        # Mandatory field validation
        if self.decision_outcome is None:
            raise ContractViolationError(
                "decision_outcome is mandatory",
                ActivationDecisionFailure.CONTRACT_VIOLATION,
            )
        if not self.decision_rule_id:
            raise ContractViolationError(
                "decision_rule_id is mandatory",
                ActivationDecisionFailure.CONTRACT_VIOLATION,
            )
        if not self.decision_rule_version:
            raise ContractViolationError(
                "decision_rule_version is mandatory",
                ActivationDecisionFailure.CONTRACT_VIOLATION,
            )
        if self.decision_inputs is None:
            raise ContractViolationError(
                "decision_inputs is mandatory",
                ActivationDecisionFailure.CONTRACT_VIOLATION,
            )
        if not self.decision_explanation:
            raise ContractViolationError(
                "decision_explanation is mandatory and cannot be empty",
                ActivationDecisionFailure.EXPLANATION_GAP,
            )
        if self.activation_reference is None:
            raise ContractViolationError(
                "activation_reference is mandatory",
                ActivationDecisionFailure.MISSING_ACTIVATION,
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for audit trail."""
        return {
            "decision_outcome": self.decision_outcome.value,
            "decision_rule_id": self.decision_rule_id,
            "decision_rule_version": self.decision_rule_version,
            "decision_inputs": self.decision_inputs,
            "decision_explanation": self.decision_explanation,
            "activation_reference": self.activation_reference.to_dict(),
            "timestamp": self.timestamp,
            "failure_mode": self.failure_mode.value if self.failure_mode else None,
        }


# ============================================================================
# CONTRACT VIOLATION ERROR
# ============================================================================


class ContractViolationError(Exception):
    """
    Raised when the glass-box decision contract is violated.
    
    HARD STOP — no recovery.
    """
    
    def __init__(self, message: str, failure_mode: ActivationDecisionFailure):
        self.message = message
        self.failure_mode = failure_mode
        super().__init__(f"CONTRACT VIOLATION [{failure_mode.value}]: {message}")


# ============================================================================
# MONOTONICITY CONSTRAINT — Enforcement
# ============================================================================


def enforce_monotonicity(
    outcome_a: ActivationAwareOutcome,
    outcome_b: ActivationAwareOutcome,
    input_severity_a: float,
    input_severity_b: float,
) -> Tuple[bool, Optional[str]]:
    """
    Enforce monotonicity constraint.
    
    RULE: If input_severity_a > input_severity_b,
          then outcome_severity_a >= outcome_severity_b
    
    More severe inputs must produce equal or more severe outcomes.
    Never less severe.
    
    Args:
        outcome_a: First decision outcome
        outcome_b: Second decision outcome
        input_severity_a: Severity measure of first input
        input_severity_b: Severity measure of second input
        
    Returns:
        (is_monotonic, violation_message)
    """
    severity_a = OUTCOME_SEVERITY_MAP[outcome_a]
    severity_b = OUTCOME_SEVERITY_MAP[outcome_b]
    
    if input_severity_a > input_severity_b:
        if severity_a < severity_b:
            return False, (
                f"Monotonicity violation: input severity {input_severity_a} > {input_severity_b} "
                f"but outcome severity {severity_a} < {severity_b}"
            )
    
    return True, None


def verify_monotonicity_for_payment(
    amount_a: float,
    amount_b: float,
    outcome_a: ActivationAwareOutcome,
    outcome_b: ActivationAwareOutcome,
) -> Tuple[bool, Optional[str]]:
    """
    Verify monotonicity for payment decisions.
    
    RULE: Higher amount → equal or higher severity outcome.
    
    Args:
        amount_a: First payment amount
        amount_b: Second payment amount
        outcome_a: First decision outcome
        outcome_b: Second decision outcome
        
    Returns:
        (is_monotonic, violation_message)
    """
    return enforce_monotonicity(outcome_a, outcome_b, amount_a, amount_b)


# ============================================================================
# EXPLANATION COMPLETENESS — Verification
# ============================================================================


def verify_explanation_completeness(decision: ActivationAwareDecision) -> Tuple[bool, Optional[str]]:
    """
    Verify that a decision has a complete, valid explanation.
    
    RULES:
    - Explanation must not be empty
    - Explanation must not be whitespace only
    - Explanation must contain actual reasoning
    - No auto-generated placeholder text
    
    Args:
        decision: The decision to verify
        
    Returns:
        (is_complete, violation_message)
    """
    explanation = decision.decision_explanation
    
    if not explanation:
        return False, "Explanation is empty"
    
    if not explanation.strip():
        return False, "Explanation is whitespace only"
    
    # Minimum meaningful explanation length
    if len(explanation.strip()) < 10:
        return False, f"Explanation too short ({len(explanation.strip())} chars): likely incomplete"
    
    # Check for placeholder patterns
    placeholder_patterns = [
        "TODO",
        "FIXME",
        "placeholder",
        "auto-generated",
        "...",
    ]
    explanation_lower = explanation.lower()
    for pattern in placeholder_patterns:
        if pattern.lower() in explanation_lower:
            return False, f"Explanation contains placeholder pattern: '{pattern}'"
    
    return True, None


# ============================================================================
# ACTIVATION-AWARE DECISION GATE — Core Invariant
# ============================================================================


def decide_with_activation(
    activation_valid: bool,
    activation_reference: Optional[ActivationReference],
    rule_id: str,
    rule_version: str,
    inputs: Dict[str, Any],
    decision_fn,  # Callable[[Dict[str, Any]], Tuple[ActivationAwareOutcome, str]]
) -> ActivationAwareDecision:
    """
    Execute decision logic with activation block enforcement.
    
    INVARIANT: IF activation_block != VALID → DECISION = ERROR
    
    This is the core gate. No decision may proceed without a valid activation block.
    
    Args:
        activation_valid: Whether the activation block was validated
        activation_reference: Reference to the validated activation block
        rule_id: The rule ID to apply
        rule_version: The rule version
        inputs: Decision inputs
        decision_fn: The deterministic decision function to execute
        
    Returns:
        ActivationAwareDecision (always, even on failure)
    """
    # INVARIANT: No valid activation → ERROR
    if not activation_valid:
        return ActivationAwareDecision(
            decision_outcome=ActivationAwareOutcome.ERROR,
            decision_rule_id="ACTIVATION_GATE",
            decision_rule_version="1.0.0",
            decision_inputs=inputs,
            decision_explanation="Decision halted: activation block is not valid. No fallback.",
            activation_reference=ActivationReference(
                agent_name="UNKNOWN",
                gid="UNKNOWN",
                color="UNKNOWN",
                validation_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            failure_mode=ActivationDecisionFailure.INVALID_ACTIVATION,
        )
    
    if activation_reference is None:
        return ActivationAwareDecision(
            decision_outcome=ActivationAwareOutcome.ERROR,
            decision_rule_id="ACTIVATION_GATE",
            decision_rule_version="1.0.0",
            decision_inputs=inputs,
            decision_explanation="Decision halted: activation block reference is missing. No fallback.",
            activation_reference=ActivationReference(
                agent_name="UNKNOWN",
                gid="UNKNOWN",
                color="UNKNOWN",
                validation_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            failure_mode=ActivationDecisionFailure.MISSING_ACTIVATION,
        )
    
    # Execute deterministic decision
    try:
        outcome, explanation = decision_fn(inputs)
    except Exception as e:
        return ActivationAwareDecision(
            decision_outcome=ActivationAwareOutcome.ERROR,
            decision_rule_id=rule_id,
            decision_rule_version=rule_version,
            decision_inputs=inputs,
            decision_explanation=f"Decision function raised exception: {type(e).__name__}: {e}",
            activation_reference=activation_reference,
            failure_mode=ActivationDecisionFailure.NON_DETERMINISTIC_OUTPUT,
        )
    
    # Build decision with activation binding
    decision = ActivationAwareDecision(
        decision_outcome=outcome,
        decision_rule_id=rule_id,
        decision_rule_version=rule_version,
        decision_inputs=inputs,
        decision_explanation=explanation,
        activation_reference=activation_reference,
    )
    
    # Verify explanation completeness
    is_complete, violation_msg = verify_explanation_completeness(decision)
    if not is_complete:
        return ActivationAwareDecision(
            decision_outcome=ActivationAwareOutcome.ERROR,
            decision_rule_id=rule_id,
            decision_rule_version=rule_version,
            decision_inputs=inputs,
            decision_explanation=f"Explanation completeness failure: {violation_msg}",
            activation_reference=activation_reference,
            failure_mode=ActivationDecisionFailure.EXPLANATION_GAP,
        )
    
    return decision


# ============================================================================
# DETERMINISM VERIFICATION
# ============================================================================


def verify_determinism(
    inputs: Dict[str, Any],
    decision_fn,
    iterations: int = 3,
) -> Tuple[bool, Optional[str]]:
    """
    Verify that a decision function is deterministic.
    
    RULE: Same inputs → same output, every time.
    
    Args:
        inputs: The inputs to test
        decision_fn: The decision function to verify
        iterations: Number of iterations to test
        
    Returns:
        (is_deterministic, violation_message)
    """
    results = []
    for _ in range(iterations):
        try:
            outcome, explanation = decision_fn(inputs)
            results.append((outcome, explanation))
        except Exception as e:
            return False, f"Decision function raised exception: {e}"
    
    # All results must be identical
    first_result = results[0]
    for i, result in enumerate(results[1:], 2):
        if result != first_result:
            return False, (
                f"Non-deterministic: iteration 1 returned {first_result}, "
                f"iteration {i} returned {result}"
            )
    
    return True, None


# ============================================================================
# FAILURE MODE HANDLERS — Explicit Enumeration
# ============================================================================


def handle_missing_activation(inputs: Dict[str, Any]) -> ActivationAwareDecision:
    """Handle MISSING_ACTIVATION failure mode."""
    return ActivationAwareDecision(
        decision_outcome=ActivationAwareOutcome.ERROR,
        decision_rule_id="FAILURE_HANDLER",
        decision_rule_version="1.0.0",
        decision_inputs=inputs,
        decision_explanation="Activation block is missing. Decision cannot proceed without valid activation.",
        activation_reference=ActivationReference(
            agent_name="NONE",
            gid="NONE",
            color="NONE",
            validation_timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        failure_mode=ActivationDecisionFailure.MISSING_ACTIVATION,
    )


def handle_invalid_activation(
    inputs: Dict[str, Any],
    validation_error: str,
) -> ActivationAwareDecision:
    """Handle INVALID_ACTIVATION failure mode."""
    return ActivationAwareDecision(
        decision_outcome=ActivationAwareOutcome.ERROR,
        decision_rule_id="FAILURE_HANDLER",
        decision_rule_version="1.0.0",
        decision_inputs=inputs,
        decision_explanation=f"Activation block validation failed: {validation_error}",
        activation_reference=ActivationReference(
            agent_name="INVALID",
            gid="INVALID",
            color="INVALID",
            validation_timestamp=datetime.now(timezone.utc).isoformat(),
        ),
        failure_mode=ActivationDecisionFailure.INVALID_ACTIVATION,
    )


def handle_explanation_gap(
    inputs: Dict[str, Any],
    activation_reference: ActivationReference,
    gap_description: str,
) -> ActivationAwareDecision:
    """Handle EXPLANATION_GAP failure mode."""
    return ActivationAwareDecision(
        decision_outcome=ActivationAwareOutcome.ERROR,
        decision_rule_id="FAILURE_HANDLER",
        decision_rule_version="1.0.0",
        decision_inputs=inputs,
        decision_explanation=f"Explanation completeness violation: {gap_description}",
        activation_reference=activation_reference,
        failure_mode=ActivationDecisionFailure.EXPLANATION_GAP,
    )


def handle_non_deterministic_output(
    inputs: Dict[str, Any],
    activation_reference: ActivationReference,
    violation_description: str,
) -> ActivationAwareDecision:
    """Handle NON_DETERMINISTIC_OUTPUT failure mode."""
    return ActivationAwareDecision(
        decision_outcome=ActivationAwareOutcome.ERROR,
        decision_rule_id="FAILURE_HANDLER",
        decision_rule_version="1.0.0",
        decision_inputs=inputs,
        decision_explanation=f"Determinism violation: {violation_description}",
        activation_reference=activation_reference,
        failure_mode=ActivationDecisionFailure.NON_DETERMINISTIC_OUTPUT,
    )
