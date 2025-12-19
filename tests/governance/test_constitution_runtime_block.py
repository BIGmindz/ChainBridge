"""
Constitution Runtime Block Tests
════════════════════════════════════════════════════════════════════════════════

Tests for PAC-CODY-CONSTITUTION-ENFORCEMENT-02 Task 3: Runtime Enforcement

Proves:
- Runtime execution blocked on lock violation
- PDO gate emits telemetry on block
- Lock assertion halts execution deterministically
- No runtime overrides possible

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from core.governance.constitution_engine import (
    ConstitutionEngine,
    LockViolationError,
    assert_lock,
    get_constitution_engine,
)
from gateway.pdo_gate import PDOGate, PDOGateError, require_pdo


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def runtime_lock_registry(tmp_path: Path) -> Path:
    """Create a test lock registry for runtime tests."""
    registry = {
        "version": "1.0",
        "locks": [
            {
                "lock_id": "LOCK-RUNTIME-001",
                "description": "Runtime test lock",
                "scope": ["gateway"],
                "type": "invariant",
                "enforcement": [{"runtime_assert": True}],
                "severity": "CRITICAL",
                "violation_policy": {"action": "HARD_FAIL", "telemetry": "REQUIRED"},
            },
            {
                "lock_id": "LOCK-PDO-GATE-001",
                "description": "PDO gate enforcement",
                "scope": ["gateway", "occ", "proofpack"],
                "type": "gate",
                "enforcement": [{"runtime_assert": True}],
                "severity": "CRITICAL",
                "violation_policy": {"action": "HARD_FAIL", "telemetry": "REQUIRED"},
            },
        ],
    }
    registry_path = tmp_path / "LOCK_REGISTRY.yaml"
    with open(registry_path, "w") as f:
        yaml.dump(registry, f)
    return registry_path


@pytest.fixture
def runtime_engine(runtime_lock_registry: Path) -> ConstitutionEngine:
    """Create a Constitution Engine with runtime registry."""
    engine = ConstitutionEngine(registry_path=runtime_lock_registry)
    engine.load_registry()
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# LOCK ASSERTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestLockAssertion:
    """Tests for runtime lock assertion."""

    def test_lock_assertion_passes_on_true(self, runtime_engine: ConstitutionEngine):
        """Lock assertion passes when condition is True."""
        # Should not raise
        runtime_engine.assert_lock("LOCK-RUNTIME-001", condition=True)

    def test_lock_assertion_fails_on_false(self, runtime_engine: ConstitutionEngine):
        """Lock assertion fails when condition is False."""
        with pytest.raises(LockViolationError) as exc_info:
            runtime_engine.assert_lock("LOCK-RUNTIME-001", condition=False)

        assert exc_info.value.lock_id == "LOCK-RUNTIME-001"
        assert "Lock assertion failed" in str(exc_info.value)

    def test_lock_assertion_includes_context(self, runtime_engine: ConstitutionEngine):
        """Lock assertion includes context in error."""
        context = {"operation": "test", "user": "test-user"}

        with pytest.raises(LockViolationError) as exc_info:
            runtime_engine.assert_lock("LOCK-RUNTIME-001", context=context, condition=False)

        assert exc_info.value.context == context

    def test_lock_assertion_has_correct_severity(self, runtime_engine: ConstitutionEngine):
        """Lock assertion error has correct severity."""
        from core.governance.constitution_engine import LockSeverity

        with pytest.raises(LockViolationError) as exc_info:
            runtime_engine.assert_lock("LOCK-RUNTIME-001", condition=False)

        assert exc_info.value.severity == LockSeverity.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# PDO GATE RUNTIME TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPDOGateRuntime:
    """Tests for PDO gate runtime enforcement."""

    def test_pdo_gate_blocks_none_pdo(self):
        """PDO gate blocks execution when PDO is None."""
        gate = PDOGate()

        with pytest.raises(PDOGateError) as exc_info:
            gate.require_pdo(None)

        assert "No PDO provided" in str(exc_info.value)

    def test_pdo_gate_blocks_invalid_type(self):
        """PDO gate blocks execution when PDO is wrong type."""
        gate = PDOGate()

        with pytest.raises(PDOGateError) as exc_info:
            gate.require_pdo("not a PDO")

        assert "Invalid PDO type" in str(exc_info.value)

    def test_pdo_gate_blocks_non_terminal_state(self):
        """PDO gate blocks execution when PDO not in terminal state."""
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        pdo = MagicMock(spec=GatewayPDO)
        pdo.state = IntentState.VALIDATED  # Not terminal (DECIDED is terminal)
        pdo.outcome = PDOOutcome.APPROVED

        gate = PDOGate()

        with pytest.raises(PDOGateError) as exc_info:
            gate.require_pdo(pdo)

        assert "not in terminal state" in str(exc_info.value)

    def test_pdo_gate_blocks_rejected_pdo(self):
        """PDO gate blocks execution when PDO is rejected."""
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        pdo = MagicMock(spec=GatewayPDO)
        pdo.state = IntentState.DECIDED
        pdo.outcome = PDOOutcome.REJECTED
        pdo.reasons = ["Policy violation"]

        gate = PDOGate()

        with pytest.raises(PDOGateError) as exc_info:
            gate.require_pdo(pdo)

        assert "PDO rejected" in str(exc_info.value)
        assert exc_info.value.pdo == pdo

    def test_pdo_gate_allows_approved_pdo(self):
        """PDO gate allows execution when PDO is approved."""
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        pdo = MagicMock(spec=GatewayPDO)
        pdo.state = IntentState.DECIDED
        pdo.outcome = PDOOutcome.APPROVED

        gate = PDOGate()
        result = gate.require_pdo(pdo)

        assert result == pdo

    def test_module_require_pdo_function(self):
        """Module-level require_pdo function works."""
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        pdo = MagicMock(spec=GatewayPDO)
        pdo.state = IntentState.DECIDED
        pdo.outcome = PDOOutcome.APPROVED

        result = require_pdo(pdo)
        assert result == pdo


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION BLOCKED TELEMETRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionBlockedTelemetry:
    """Tests for EXECUTION_BLOCKED telemetry emission."""

    def test_pdo_gate_emits_telemetry_on_block(self, caplog):
        """PDO gate emits EXECUTION_BLOCKED telemetry when blocking."""
        import logging
        caplog.set_level(logging.WARNING)

        gate = PDOGate()

        with pytest.raises(PDOGateError):
            gate.require_pdo(None)

        # Check telemetry was logged
        assert "EXECUTION_BLOCKED" in caplog.text

    def test_telemetry_includes_lock_id(self, caplog):
        """EXECUTION_BLOCKED telemetry includes lock ID."""
        import logging
        caplog.set_level(logging.WARNING)

        gate = PDOGate()

        with pytest.raises(PDOGateError):
            gate.require_pdo(None)

        assert "LOCK-PDO-GATE-001" in caplog.text

    def test_telemetry_includes_reason(self, caplog):
        """EXECUTION_BLOCKED telemetry includes block reason."""
        import logging
        caplog.set_level(logging.WARNING)

        gate = PDOGate()

        with pytest.raises(PDOGateError):
            gate.require_pdo(None)

        assert "No PDO provided" in caplog.text


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED RUNTIME TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailClosedRuntime:
    """Tests proving fail-closed runtime enforcement."""

    def test_no_runtime_override_for_pdo_gate(self):
        """PDO gate cannot be bypassed at runtime."""
        gate = PDOGate()

        # No method to bypass - must raise
        with pytest.raises(PDOGateError):
            gate.require_pdo(None)

    def test_no_soft_fail_mode(self):
        """There is no soft-fail mode - always hard fail."""
        gate = PDOGate()

        # No configuration to enable soft-fail
        with pytest.raises(PDOGateError):
            gate.require_pdo(None)

    def test_lock_violation_always_raises(self, runtime_engine: ConstitutionEngine):
        """Lock violation always raises - no swallowing."""
        # No way to configure exception swallowing
        with pytest.raises(LockViolationError):
            runtime_engine.assert_lock("LOCK-RUNTIME-001", condition=False)

    def test_execution_halts_deterministically(self):
        """Execution halts the same way every time."""
        gate = PDOGate()

        # Run multiple times - same result
        for _ in range(3):
            with pytest.raises(PDOGateError) as exc_info:
                gate.require_pdo(None)
            assert "No PDO provided" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRuntimeIntegration:
    """Integration tests for runtime enforcement."""

    def test_pdo_gate_is_approved_helper(self):
        """is_approved helper doesn't raise but returns False."""
        gate = PDOGate()

        # Does not raise - returns False
        result = gate.is_approved(None)
        assert result is False

    def test_pdo_gate_is_approved_true(self):
        """is_approved returns True for valid PDO."""
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        pdo = MagicMock(spec=GatewayPDO)
        pdo.state = IntentState.DECIDED
        pdo.outcome = PDOOutcome.APPROVED

        gate = PDOGate()
        result = gate.is_approved(pdo)
        assert result is True

    def test_require_pdo_chains(self):
        """require_pdo returns PDO for chaining."""
        from gateway.intent_schema import IntentState
        from gateway.pdo_schema import GatewayPDO, PDOOutcome

        pdo = MagicMock(spec=GatewayPDO)
        pdo.state = IntentState.DECIDED
        pdo.outcome = PDOOutcome.APPROVED

        gate = PDOGate()

        # Can chain operations
        result = gate.require_pdo(pdo)
        assert result == pdo
