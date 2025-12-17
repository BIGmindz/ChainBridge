"""Gateway validator: schema enforcement + deterministic state checks."""

from __future__ import annotations

from typing import Mapping, Optional, Union

from pydantic import ValidationError

from gateway.intent_schema import GatewayIntent, IntentState


class GatewayValidator:
    """Deterministic validator for gateway intents."""

    _ALLOWED_TRANSITIONS = {
        IntentState.RECEIVED: {IntentState.VALIDATED},
        IntentState.VALIDATED: {IntentState.DECIDED},
        IntentState.DECIDED: set(),
    }

    def validate_intent(
        self,
        raw_intent: Union[GatewayIntent, Mapping[str, object]],
        previous_state: Optional[IntentState] = None,
    ) -> GatewayIntent:
        """Validate shape and initial state; reject free-form or missing intent_type."""

        try:
            intent = raw_intent if isinstance(raw_intent, GatewayIntent) else GatewayIntent.model_validate(raw_intent)
        except ValidationError:
            raise

        self._assert_start_state(intent, previous_state)
        return intent

    def assert_transition(self, current_state: IntentState, next_state: IntentState) -> None:
        """Enforce deterministic state transitions (fail closed)."""

        allowed = self._ALLOWED_TRANSITIONS.get(current_state, set())
        if next_state not in allowed:
            raise ValueError(f"Invalid state transition: {current_state} -> {next_state}")

    def _assert_start_state(self, intent: GatewayIntent, previous_state: Optional[IntentState]) -> None:
        """Ensure intent enters the state machine in a deterministic way."""

        if previous_state is None and intent.state != IntentState.RECEIVED:
            raise ValueError("Intent must begin in 'received' state")

        if previous_state is not None and intent.state != previous_state:
            raise ValueError("Intent state does not match previously recorded state")

    def assert_pdo_allows_execution(self, pdo: object) -> None:
        """
        Validate that a PDO permits execution.

        This is a fail-closed check: if the PDO is not explicitly approved,
        execution is blocked.

        Args:
            pdo: The Policy Decision Object to validate.

        Raises:
            PDOGateError: If execution should not proceed.
        """
        from gateway.pdo_gate import require_pdo

        require_pdo(pdo)  # type: ignore[arg-type]
