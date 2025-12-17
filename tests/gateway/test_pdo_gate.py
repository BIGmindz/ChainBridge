"""Tests for PDO Gate Enforcement (PAC-GW-01).

Verifies that:
1. All execution paths fail closed without a PDO
2. Rejected PDOs block execution
3. Only approved PDOs allow execution
4. Centralized gate is used consistently
"""

import pytest

from gateway.decision_engine import DecisionEngine
from gateway.intent_schema import IntentAction, IntentChannel, IntentState, IntentType
from gateway.pdo_gate import PDOGate, PDOGateError, is_pdo_approved, require_pdo
from gateway.pdo_schema import GatewayPDO, PDOOutcome
from gateway.validator import GatewayValidator


@pytest.fixture
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


@pytest.fixture
def approved_pdo(valid_intent_payload):
    """Create an approved PDO through the decision engine."""
    engine = DecisionEngine()
    return engine.evaluate(valid_intent_payload)


@pytest.fixture
def rejected_pdo(valid_intent_payload):
    """Create a rejected PDO (missing required fields)."""
    engine = DecisionEngine()
    rejected_payload = {
        **valid_intent_payload,
        "payload": {},  # Empty payload triggers rejection
    }
    return engine.evaluate(rejected_payload)


# =============================================================================
# PDO Gate Core Tests
# =============================================================================


class TestPDOGateCore:
    """Test the centralized PDO gate module."""

    def test_require_pdo_raises_on_none(self):
        """No PDO → No execution."""
        with pytest.raises(PDOGateError) as exc_info:
            require_pdo(None)
        assert "No PDO provided" in str(exc_info.value)

    def test_require_pdo_raises_on_invalid_type(self):
        """Invalid PDO type → No execution."""
        with pytest.raises(PDOGateError) as exc_info:
            require_pdo({"not": "a pdo"})  # type: ignore
        assert "Invalid PDO type" in str(exc_info.value)

    def test_require_pdo_raises_on_rejected(self, rejected_pdo):
        """Rejected PDO → No execution."""
        assert rejected_pdo.outcome == PDOOutcome.REJECTED
        with pytest.raises(PDOGateError) as exc_info:
            require_pdo(rejected_pdo)
        assert "PDO rejected" in str(exc_info.value)
        assert exc_info.value.pdo is rejected_pdo

    def test_require_pdo_passes_on_approved(self, approved_pdo):
        """Approved PDO → Execution allowed."""
        assert approved_pdo.outcome == PDOOutcome.APPROVED
        result = require_pdo(approved_pdo)
        assert result is approved_pdo

    def test_require_pdo_raises_on_non_terminal_state(self, approved_pdo):
        """PDO not in DECIDED state → No execution."""
        # Manually create a PDO with non-terminal state
        non_terminal_pdo = GatewayPDO(
            outcome=PDOOutcome.APPROVED,
            state=IntentState.VALIDATED,  # Not DECIDED
            intent=approved_pdo.intent,
            reasons=[],
        )
        with pytest.raises(PDOGateError) as exc_info:
            require_pdo(non_terminal_pdo)
        assert "not in terminal state" in str(exc_info.value)

    def test_is_pdo_approved_helper(self, approved_pdo, rejected_pdo):
        """Helper function correctly identifies approval status."""
        assert is_pdo_approved(approved_pdo) is True
        assert is_pdo_approved(rejected_pdo) is False
        assert is_pdo_approved(None) is False


class TestPDOGateClass:
    """Test the PDOGate class directly."""

    def test_gate_instance_require_pdo(self, approved_pdo):
        """PDOGate instance enforces same rules."""
        gate = PDOGate()
        result = gate.require_pdo(approved_pdo)
        assert result is approved_pdo

    def test_gate_instance_is_approved(self, approved_pdo, rejected_pdo):
        """PDOGate.is_approved matches module-level function."""
        gate = PDOGate()
        assert gate.is_approved(approved_pdo) is True
        assert gate.is_approved(rejected_pdo) is False


# =============================================================================
# Decision Engine Integration Tests
# =============================================================================


class TestDecisionEngineGate:
    """Test PDO gate integration with DecisionEngine."""

    def test_execute_blocks_rejected_pdo(self, rejected_pdo):
        """DecisionEngine.execute() blocks rejected PDOs."""
        engine = DecisionEngine()
        with pytest.raises(PDOGateError):
            engine.execute(rejected_pdo)

    def test_execute_allows_approved_pdo(self, approved_pdo):
        """DecisionEngine.execute() allows approved PDOs."""
        engine = DecisionEngine()
        result = engine.execute(approved_pdo)
        assert result is approved_pdo

    def test_execute_blocks_none_pdo(self):
        """DecisionEngine.execute() blocks None PDO."""
        engine = DecisionEngine()
        with pytest.raises(PDOGateError):
            engine.execute(None)  # type: ignore


# =============================================================================
# Validator Integration Tests
# =============================================================================


class TestValidatorGate:
    """Test PDO gate integration with GatewayValidator."""

    def test_assert_pdo_allows_execution_passes(self, approved_pdo):
        """Validator passes approved PDO."""
        validator = GatewayValidator()
        validator.assert_pdo_allows_execution(approved_pdo)

    def test_assert_pdo_allows_execution_blocks(self, rejected_pdo):
        """Validator blocks rejected PDO."""
        validator = GatewayValidator()
        with pytest.raises(PDOGateError):
            validator.assert_pdo_allows_execution(rejected_pdo)


# =============================================================================
# Fail-Closed Verification
# =============================================================================


class TestFailClosed:
    """Verify all paths fail closed."""

    def test_pdo_gate_error_contains_pdo_reference(self, rejected_pdo):
        """PDOGateError includes PDO for debugging."""
        try:
            require_pdo(rejected_pdo)
        except PDOGateError as e:
            assert e.pdo is rejected_pdo
            assert "rejected" in str(e).lower()

    def test_no_bypass_via_empty_reasons(self, valid_intent_payload):
        """Cannot bypass gate by having empty rejection reasons."""
        # Create a rejected PDO with no reasons
        engine = DecisionEngine()
        pdo = engine.evaluate(valid_intent_payload)
        # Manually corrupt the PDO (simulating potential attack)
        corrupted_pdo = GatewayPDO(
            outcome=PDOOutcome.REJECTED,
            state=IntentState.DECIDED,
            intent=pdo.intent,
            reasons=[],  # Empty reasons
        )
        with pytest.raises(PDOGateError):
            require_pdo(corrupted_pdo)
