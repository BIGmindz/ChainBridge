"""Deterministic gateway decision engine (approve/reject without AI)."""

from __future__ import annotations

from typing import List, Mapping, Union

from gateway.intent_schema import GatewayIntent, IntentState, IntentType
from gateway.pdo_gate import require_pdo
from gateway.pdo_schema import GatewayPDO, PDOOutcome
from gateway.validator import GatewayValidator


class DecisionEngine:
    """Deterministic approve/reject engine for gateway intents."""

    def __init__(self, validator: GatewayValidator | None = None):
        self.validator = validator or GatewayValidator()

    def evaluate(
        self,
        raw_intent: Union[GatewayIntent, Mapping[str, object]],
        previous_state: IntentState | None = None,
    ) -> GatewayPDO:
        """Validate, enforce state, and deterministically approve/reject."""

        intent = self.validator.validate_intent(raw_intent, previous_state=previous_state)

        # Step 1: move from received -> validated
        self.validator.assert_transition(intent.state, IntentState.VALIDATED)
        validated_intent = intent.model_copy(update={"state": IntentState.VALIDATED})

        # Step 2: deterministic rule evaluation (fail-closed)
        rejection_reasons = self._deterministic_rejections(validated_intent)

        # Step 3: validated -> decided
        self.validator.assert_transition(validated_intent.state, IntentState.DECIDED)
        final_intent = validated_intent.model_copy(update={"state": IntentState.DECIDED})

        outcome = PDOOutcome.APPROVED if not rejection_reasons else PDOOutcome.REJECTED
        return GatewayPDO(
            outcome=outcome,
            state=IntentState.DECIDED,
            intent=final_intent,
            reasons=rejection_reasons,
        )

    def _deterministic_rejections(self, intent: GatewayIntent) -> List[str]:
        """Simple deterministic rule set. No AI, no heuristics."""

        reasons: List[str] = []
        payload = intent.payload

        # Require at least one deterministic payload attribute to avoid free-form inputs.
        if not any([payload.resource_id, payload.amount_minor is not None, payload.currency, payload.metadata]):
            reasons.append("Payload must include at least one deterministic field")

        # Payment intents require currency context.
        if intent.intent_type == IntentType.PAYMENT and payload.currency is None:
            reasons.append("Currency is required for payment intents")

        return reasons

    def execute(self, pdo: GatewayPDO) -> GatewayPDO:
        """
        Execute gateway action ONLY if PDO is approved.

        This is the single execution entry point that enforces:
        "No PDO → No execution"

        Args:
            pdo: The Policy Decision Object from evaluate().

        Returns:
            The validated PDO (unchanged).

        Raises:
            PDOGateError: If PDO is missing, invalid, or rejected.
        """
        return require_pdo(pdo)
