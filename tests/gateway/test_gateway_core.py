import pytest
from pydantic import ValidationError

from gateway.decision_engine import DecisionEngine
from gateway.intent_schema import GatewayIntent, IntentAction, IntentChannel, IntentState, IntentType
from gateway.pdo_schema import PDOOutcome
from gateway.validator import GatewayValidator


@pytest.fixture()
def valid_intent_payload():
    return {
        "intent_type": IntentType.PAYMENT,
        "action": IntentAction.CREATE,
        "channel": IntentChannel.API,
        "payload": {
            "resource_id": "ship-123",
            "amount_minor": 1500,
            "currency": "USD",
            "metadata": {"source": "unit-test"},
        },
        "correlation_id": "corr-123",
    }


def test_validate_intent_hard_rejects_missing_intent_type(valid_intent_payload):
    validator = GatewayValidator()
    invalid_payload = {k: v for k, v in valid_intent_payload.items() if k != "intent_type"}

    with pytest.raises(ValidationError):
        validator.validate_intent(invalid_payload)


def test_validate_intent_blocks_free_form_payload(valid_intent_payload):
    validator = GatewayValidator()
    invalid_payload = {
        **valid_intent_payload,
        "payload": {
            **valid_intent_payload["payload"],
            "unexpected": "free-form",
        },
    }

    with pytest.raises(ValidationError):
        validator.validate_intent(invalid_payload)


def test_validator_blocks_invalid_start_state(valid_intent_payload):
    validator = GatewayValidator()
    payload_with_invalid_state = {**valid_intent_payload, "state": IntentState.VALIDATED}

    with pytest.raises(ValueError):
        validator.validate_intent(payload_with_invalid_state)


def test_decision_engine_approves_valid_intent(valid_intent_payload):
    engine = DecisionEngine()
    pdo = engine.evaluate(valid_intent_payload)

    assert pdo.outcome is PDOOutcome.APPROVED
    assert pdo.state is IntentState.DECIDED
    assert pdo.reasons == []
    assert pdo.intent.state is IntentState.DECIDED


def test_decision_engine_rejects_underspecified_payload(valid_intent_payload):
    engine = DecisionEngine()
    minimal_payload = {
        **valid_intent_payload,
        "payload": {},
    }

    pdo = engine.evaluate(minimal_payload)

    assert pdo.outcome is PDOOutcome.REJECTED
    assert any("deterministic field" in reason for reason in pdo.reasons)
    assert pdo.state is IntentState.DECIDED
