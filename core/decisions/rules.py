# core/decisions/rules.py
"""
Glass-Box Decision Rules — Deterministic, Auditable Logic

PAC ID: PAC-MAGGIE-DECISION-LOGIC-01
Author: MAGGIE (GID-10) — ML & Applied AI Lead
Version: 1.0.0

CONSTRAINTS (ABSOLUTE):
- No probabilities
- No learned weights
- No hidden state
- Every rule is auditable
- Every output has an explanation

This module defines:
1. Input validation rules
2. Decision threshold rules
3. Rule registry for traceability
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Decision Outcomes
# ============================================================================


class DecisionOutcome(str, Enum):
    """
    Canonical decision outcomes.
    
    Ordered by severity (APPROVED < REJECTED < REQUIRES_REVIEW < ERROR).
    Monotonic rules should only increase severity, never decrease.
    """
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"
    ERROR = "error"


# Severity ordering for monotonicity checks
OUTCOME_SEVERITY: Dict[DecisionOutcome, int] = {
    DecisionOutcome.APPROVED: 100,
    DecisionOutcome.REJECTED: 200,
    DecisionOutcome.REQUIRES_REVIEW: 300,
    DecisionOutcome.ERROR: 400,
}


# ============================================================================
# Decision Result (Immutable)
# ============================================================================


@dataclass(frozen=True)
class DecisionResult:
    """
    Immutable decision result with full traceability.
    
    Every decision includes:
    - The outcome (what was decided)
    - The rule that produced it (traceability)
    - The inputs used (reproducibility)
    - A human-readable explanation (auditability)
    """
    outcome: DecisionOutcome
    rule_id: str
    rule_version: str
    inputs_snapshot: Dict[str, Any]
    explanation: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging/storage."""
        return {
            "outcome": self.outcome.value,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "inputs_snapshot": self.inputs_snapshot,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
        }


# ============================================================================
# Rule Registry
# ============================================================================


# Rule IDs (canonical identifiers)
RULE_INPUT_VALIDATION = "RULE-INPUT-VALIDATION-V1"
RULE_PAYMENT_THRESHOLD = "RULE-PAYMENT-THRESHOLD-V1"
RULE_EVENT_TYPE = "RULE-EVENT-TYPE-V1"

# Rule versions
RULE_VERSIONS: Dict[str, str] = {
    RULE_INPUT_VALIDATION: "1.0.0",
    RULE_PAYMENT_THRESHOLD: "1.0.0",
    RULE_EVENT_TYPE: "1.0.0",
}


# ============================================================================
# Configuration Constants (LOCKED)
# ============================================================================


# Payment threshold (USD)
PAYMENT_THRESHOLD: float = 10_000.00

# Supported event types
SUPPORTED_EVENT_TYPES: Tuple[str, ...] = ("payment_request",)


# ============================================================================
# Validation Rules
# ============================================================================


def validate_amount(amount: Any) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    Validate payment amount.
    
    Returns:
        (is_valid, error_message, normalized_value)
        
    Validation Rules:
    - Must not be None
    - Must be convertible to float
    - Must be positive (> 0)
    - Must be finite (not NaN, not Inf)
    """
    if amount is None:
        return False, "Missing required field: amount", None
    
    # Attempt numeric conversion
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return False, f"Invalid amount type: expected numeric, got {type(amount).__name__}", None
    
    # Check for special float values
    if math.isnan(value):
        return False, "Invalid amount: NaN is not allowed", None
    
    if math.isinf(value):
        return False, "Invalid amount: Infinity is not allowed", None
    
    # Check positivity
    if value <= 0:
        return False, f"Invalid amount: must be positive, got {value}", None
    
    return True, None, value


def validate_string_field(value: Any, field_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate a required string field.
    
    Returns:
        (is_valid, error_message, normalized_value)
        
    Validation Rules:
    - Must not be None
    - Must be string type
    - Must not be empty or whitespace-only
    """
    if value is None:
        return False, f"Missing required field: {field_name}", None
    
    if not isinstance(value, str):
        return False, f"Invalid {field_name} type: expected string, got {type(value).__name__}", None
    
    normalized = value.strip()
    if not normalized:
        return False, f"Invalid {field_name}: cannot be empty or whitespace", None
    
    return True, None, normalized


def validate_currency(currency: Any) -> Tuple[bool, Optional[str], str]:
    """
    Validate and normalize currency code.
    
    Returns:
        (is_valid, error_message, normalized_value)
        
    Validation Rules:
    - If None, defaults to "USD"
    - Must be string if provided
    - Must be 3 characters
    - Normalized to uppercase
    """
    if currency is None:
        return True, None, "USD"
    
    if not isinstance(currency, str):
        return False, f"Invalid currency type: expected string, got {type(currency).__name__}", "USD"
    
    normalized = currency.strip().upper()
    if len(normalized) != 3:
        return False, f"Invalid currency code: must be 3 characters, got '{currency}'", "USD"
    
    return True, None, normalized


def validate_event_type(event_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate event type is supported.
    
    Returns:
        (is_valid, error_message)
    """
    if event_type not in SUPPORTED_EVENT_TYPES:
        return False, f"Unsupported event type: {event_type}. Supported: {SUPPORTED_EVENT_TYPES}"
    
    return True, None


# ============================================================================
# Decision Rules
# ============================================================================


def apply_input_validation(payload: Dict[str, Any]) -> Optional[DecisionResult]:
    """
    RULE-INPUT-VALIDATION-V1: Validate all required inputs.
    
    Returns:
        DecisionResult with ERROR if validation fails, None if valid.
    """
    errors: List[str] = []
    
    # Validate amount
    amount_valid, amount_error, _ = validate_amount(payload.get("amount"))
    if not amount_valid:
        errors.append(amount_error)
    
    # Validate vendor_id
    vendor_valid, vendor_error, _ = validate_string_field(
        payload.get("vendor_id"), "vendor_id"
    )
    if not vendor_valid:
        errors.append(vendor_error)
    
    # Validate requestor_id
    requestor_valid, requestor_error, _ = validate_string_field(
        payload.get("requestor_id"), "requestor_id"
    )
    if not requestor_valid:
        errors.append(requestor_error)
    
    # Validate currency (optional but must be valid if provided)
    currency_valid, currency_error, _ = validate_currency(payload.get("currency"))
    if not currency_valid:
        errors.append(currency_error)
    
    if errors:
        return DecisionResult(
            outcome=DecisionOutcome.ERROR,
            rule_id=RULE_INPUT_VALIDATION,
            rule_version=RULE_VERSIONS[RULE_INPUT_VALIDATION],
            inputs_snapshot={"raw_payload": payload},
            explanation=f"Input validation failed: {'; '.join(errors)}",
        )
    
    return None  # All inputs valid


def apply_payment_threshold(
    amount: float,
    currency: str,
    vendor_id: str,
    requestor_id: str,
) -> DecisionResult:
    """
    RULE-PAYMENT-THRESHOLD-V1: Apply payment threshold decision.
    
    Rule (LOCKED):
    - amount <= $10,000: APPROVED
    - amount > $10,000: REQUIRES_REVIEW
    
    This rule is MONOTONIC: higher amounts never result in lower severity.
    """
    inputs_snapshot = {
        "amount": amount,
        "currency": currency,
        "vendor_id": vendor_id,
        "requestor_id": requestor_id,
        "threshold": PAYMENT_THRESHOLD,
        "threshold_currency": "USD",
    }
    
    if amount <= PAYMENT_THRESHOLD:
        return DecisionResult(
            outcome=DecisionOutcome.APPROVED,
            rule_id=RULE_PAYMENT_THRESHOLD,
            rule_version=RULE_VERSIONS[RULE_PAYMENT_THRESHOLD],
            inputs_snapshot=inputs_snapshot,
            explanation=(
                f"Payment of ${amount:,.2f} {currency} is within auto-approval threshold "
                f"of ${PAYMENT_THRESHOLD:,.2f}. Approved."
            ),
        )
    else:
        return DecisionResult(
            outcome=DecisionOutcome.REQUIRES_REVIEW,
            rule_id=RULE_PAYMENT_THRESHOLD,
            rule_version=RULE_VERSIONS[RULE_PAYMENT_THRESHOLD],
            inputs_snapshot=inputs_snapshot,
            explanation=(
                f"Payment of ${amount:,.2f} {currency} exceeds auto-approval threshold "
                f"of ${PAYMENT_THRESHOLD:,.2f}. Human review required."
            ),
        )


# ============================================================================
# Main Decision Function
# ============================================================================


def decide_payment_request(payload: Dict[str, Any]) -> DecisionResult:
    """
    Execute deterministic decision logic for payment requests.
    
    Decision Flow:
    1. Validate all inputs (RULE-INPUT-VALIDATION-V1)
    2. Apply threshold rule (RULE-PAYMENT-THRESHOLD-V1)
    
    Args:
        payload: Payment request payload with amount, vendor_id, requestor_id, currency
        
    Returns:
        Immutable DecisionResult with full traceability
        
    Guarantees:
    - Deterministic: same payload → same result
    - Traceable: result includes rule ID and version
    - Auditable: result includes inputs snapshot and explanation
    - Fail-closed: errors result in ERROR outcome, never silent pass
    """
    # Step 1: Input validation
    validation_result = apply_input_validation(payload)
    if validation_result is not None:
        return validation_result
    
    # Step 2: Extract and normalize validated inputs
    _, _, amount = validate_amount(payload.get("amount"))
    _, _, vendor_id = validate_string_field(payload.get("vendor_id"), "vendor_id")
    _, _, requestor_id = validate_string_field(payload.get("requestor_id"), "requestor_id")
    _, _, currency = validate_currency(payload.get("currency"))
    
    # Step 3: Apply threshold rule
    return apply_payment_threshold(
        amount=amount,
        currency=currency,
        vendor_id=vendor_id,
        requestor_id=requestor_id,
    )


def decide(event_type: str, payload: Dict[str, Any]) -> DecisionResult:
    """
    Main decision entry point.
    
    Routes to appropriate decision logic based on event type.
    
    Args:
        event_type: Type of event (e.g., "payment_request")
        payload: Event payload data
        
    Returns:
        Immutable DecisionResult
    """
    # Validate event type
    type_valid, type_error = validate_event_type(event_type)
    if not type_valid:
        return DecisionResult(
            outcome=DecisionOutcome.ERROR,
            rule_id=RULE_EVENT_TYPE,
            rule_version=RULE_VERSIONS[RULE_EVENT_TYPE],
            inputs_snapshot={"event_type": event_type, "payload": payload},
            explanation=type_error,
        )
    
    # Route to specific decision logic
    if event_type == "payment_request":
        return decide_payment_request(payload)
    
    # Unreachable if validate_event_type is correct, but fail safe
    return DecisionResult(
        outcome=DecisionOutcome.ERROR,
        rule_id=RULE_EVENT_TYPE,
        rule_version=RULE_VERSIONS[RULE_EVENT_TYPE],
        inputs_snapshot={"event_type": event_type, "payload": payload},
        explanation=f"No decision logic implemented for event type: {event_type}",
    )


# ============================================================================
# Monotonicity Check (Invariant Verification)
# ============================================================================


def verify_monotonicity(result_a: DecisionResult, result_b: DecisionResult) -> bool:
    """
    Verify that result_a severity <= result_b severity.
    
    Used for testing the monotonicity invariant:
    For payment threshold, higher amounts should never result in lower severity.
    
    Returns:
        True if monotonicity holds (severity_a <= severity_b)
    """
    severity_a = OUTCOME_SEVERITY[result_a.outcome]
    severity_b = OUTCOME_SEVERITY[result_b.outcome]
    return severity_a <= severity_b
