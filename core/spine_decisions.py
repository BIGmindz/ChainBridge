"""
core/decisions.py - Decision Logic for Execution Spine
PAC-CODY-EXEC-SPINE-01

Deterministic decision function:
- Input: IngestEvent
- Output: Decision result (action to take)
- No randomness, no side effects
- Same input → same output

DECISION RULE (V1):
- event_type == "payment_request" → APPROVE if amount <= 10000, else ESCALATE
- All other event types → ACKNOWLEDGE
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from core.events import IngestEvent

logger = logging.getLogger(__name__)


class DecisionOutcome(str, Enum):
    """Canonical decision outcomes."""
    APPROVE = "approve"
    ESCALATE = "escalate"
    ACKNOWLEDGE = "acknowledge"
    REJECT = "reject"


@dataclass(frozen=True)
class Decision:
    """
    Immutable decision result.

    Attributes:
        outcome: The decision outcome (approve, escalate, acknowledge, reject)
        reason: Human-readable reason for the decision
        event_id: ID of the event this decision is for
        rule_applied: Name of the rule that produced this decision
    """
    outcome: DecisionOutcome
    reason: str
    event_id: str
    rule_applied: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "outcome": self.outcome.value,
            "reason": self.reason,
            "event_id": self.event_id,
            "rule_applied": self.rule_applied,
        }


# Decision threshold constants (explicit, no magic numbers)
PAYMENT_APPROVAL_THRESHOLD = 10000.0


def decide(event: IngestEvent) -> Decision:
    """
    Deterministic decision function.

    Rules:
    1. event_type == "payment_request":
       - amount <= 10000 → APPROVE
       - amount > 10000 → ESCALATE
    2. All other event types → ACKNOWLEDGE

    Args:
        event: The IngestEvent to decide on

    Returns:
        Decision object with outcome and reason
    """
    event_id_str = str(event.event_id)

    logger.info(
        "decide: processing event",
        extra={"event_id": event_id_str, "event_type": event.event_type}
    )

    if event.event_type == "payment_request":
        return _decide_payment_request(event, event_id_str)

    # Default: acknowledge all other event types
    logger.info(
        "decide: acknowledging event",
        extra={"event_id": event_id_str, "decision": DecisionOutcome.ACKNOWLEDGE.value}
    )
    return Decision(
        outcome=DecisionOutcome.ACKNOWLEDGE,
        reason=f"Event type '{event.event_type}' acknowledged",
        event_id=event_id_str,
        rule_applied="default_acknowledge",
    )


def _decide_payment_request(event: IngestEvent, event_id_str: str) -> Decision:
    """
    Decision logic for payment_request events.

    Rule:
    - amount <= 10000 → APPROVE
    - amount > 10000 → ESCALATE
    - missing/invalid amount → REJECT
    """
    payload = event.payload
    amount = payload.get("amount")

    # Validate amount exists and is numeric
    if amount is None:
        logger.warning(
            "decide: payment_request missing amount",
            extra={"event_id": event_id_str}
        )
        return Decision(
            outcome=DecisionOutcome.REJECT,
            reason="Payment request missing 'amount' field",
            event_id=event_id_str,
            rule_applied="payment_validation",
        )

    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        logger.warning(
            "decide: payment_request invalid amount",
            extra={"event_id": event_id_str, "amount": amount}
        )
        return Decision(
            outcome=DecisionOutcome.REJECT,
            reason=f"Payment request has invalid 'amount': {amount}",
            event_id=event_id_str,
            rule_applied="payment_validation",
        )

    # Apply threshold rule
    if amount_value <= PAYMENT_APPROVAL_THRESHOLD:
        logger.info(
            "decide: approving payment",
            extra={"event_id": event_id_str, "amount": amount_value, "decision": DecisionOutcome.APPROVE.value}
        )
        return Decision(
            outcome=DecisionOutcome.APPROVE,
            reason=f"Payment amount {amount_value} within threshold {PAYMENT_APPROVAL_THRESHOLD}",
            event_id=event_id_str,
            rule_applied="payment_threshold",
        )
    else:
        logger.info(
            "decide: escalating payment",
            extra={"event_id": event_id_str, "amount": amount_value, "decision": DecisionOutcome.ESCALATE.value}
        )
        return Decision(
            outcome=DecisionOutcome.ESCALATE,
            reason=f"Payment amount {amount_value} exceeds threshold {PAYMENT_APPROVAL_THRESHOLD}",
            event_id=event_id_str,
            rule_applied="payment_threshold",
        )
