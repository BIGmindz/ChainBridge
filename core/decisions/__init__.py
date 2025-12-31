# core/decisions/__init__.py
"""
Decision Logic Module — Glass-Box, Deterministic, Auditable

PAC ID: PAC-MAGGIE-DECISION-LOGIC-01
Extended By: PAC-MAGGIE-ACTIVATION-BLOCK-DECISION-INTEGRITY-01
Author: MAGGIE (GID-10) — ML & Applied AI Lead

This module provides:
- Deterministic decision rules (rules.py)
- Human-readable explanations (explanations.py)
- Activation-aware decision invariants (activation_invariants.py)
- Full specification (spec.md)

CONSTRAINTS (ABSOLUTE):
- No probabilities
- No learned weights
- No hidden state
- Every rule is auditable
- Every output has an explanation
- Activation block must be valid before any decision
"""

from core.decisions.rules import (
    PAYMENT_THRESHOLD,
    RULE_EVENT_TYPE,
    RULE_INPUT_VALIDATION,
    RULE_PAYMENT_THRESHOLD,
    RULE_VERSIONS,
    DecisionOutcome,
    DecisionResult,
    decide,
    decide_payment_request,
    verify_monotonicity,
)
from core.decisions.explanations import (
    format_audit_entry,
    generate_explanation,
    get_example_decisions,
    verify_explanation_completeness,
    verify_explanation_determinism,
)
from core.decisions.activation_invariants import (
    ActivationAwareDecision,
    ActivationAwareOutcome,
    ActivationDecisionFailure,
    ActivationReference,
    ContractViolationError,
    decide_with_activation,
    enforce_monotonicity,
    handle_invalid_activation,
    handle_missing_activation,
    verify_determinism,
    verify_explanation_completeness as verify_activation_explanation_completeness,
    verify_monotonicity_for_payment,
)
from core.decisions.decision_execution import (
    ACTIVATION_TO_DECISION_FAILURE_MAP,
    DecisionExecutionError,
    DecisionExecutionFailure,
    ExecutableDecision,
    PersistenceRejectionError,
    enforce_payment_monotonicity,
    execute_decision,
    execute_decision_with_enforcement,
    map_activation_failure,
    require_persistence_contract,
    validate_for_persistence,
    verify_monotonicity_invariant,
)

__all__ = [
    # Decision outcomes
    "DecisionOutcome",
    "DecisionResult",
    # Main functions
    "decide",
    "decide_payment_request",
    # Constants
    "PAYMENT_THRESHOLD",
    "RULE_EVENT_TYPE",
    "RULE_INPUT_VALIDATION",
    "RULE_PAYMENT_THRESHOLD",
    "RULE_VERSIONS",
    # Explanation functions
    "format_audit_entry",
    "generate_explanation",
    "get_example_decisions",
    # Verification functions
    "verify_monotonicity",
    "verify_explanation_completeness",
    "verify_explanation_determinism",
    # Activation-aware decisions (PAC-MAGGIE-ACTIVATION-BLOCK-DECISION-INTEGRITY-01)
    "ActivationAwareDecision",
    "ActivationAwareOutcome",
    "ActivationDecisionFailure",
    "ActivationReference",
    "ContractViolationError",
    "decide_with_activation",
    "enforce_monotonicity",
    "handle_invalid_activation",
    "handle_missing_activation",
    "verify_determinism",
    "verify_activation_explanation_completeness",
    "verify_monotonicity_for_payment",
    # Decision execution (PAC-BENSON-CODY-ACTIVATION-AWARE-DECISION-INTEGRATION-01)
    "DecisionExecutionError",
    "DecisionExecutionFailure",
    "ExecutableDecision",
    "PersistenceRejectionError",
    "execute_decision",
    "execute_decision_with_enforcement",
    "validate_for_persistence",
    "require_persistence_contract",
    "enforce_payment_monotonicity",
    "verify_monotonicity_invariant",
    "map_activation_failure",
    "ACTIVATION_TO_DECISION_FAILURE_MAP",
]
