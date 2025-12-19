# tests/decisions/test_activation_aware_decisions.py
"""
════════════════════════════════════════════════════════════════════════════════
Activation-Aware Decision Integration Tests
════════════════════════════════════════════════════════════════════════════════

PAC ID: PAC-BENSON-CODY-ACTIVATION-AWARE-DECISION-INTEGRATION-01
Author: CODY (GID-01) — Senior Backend Engineer
Version: 1.0.0

TEST COVERAGE:
- Missing activation → decision rejected
- Invalid activation → decision rejected
- Valid activation → decision proceeds
- Persistence contract enforcement
- Monotonicity enforcement
- Failure code propagation

NO TEST SKIPS. NO SOFT ASSERTIONS.

════════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timezone
from typing import Dict, Any, Tuple

import pytest

from core.decisions import (
    DecisionOutcome,
    DecisionExecutionError,
    DecisionExecutionFailure,
    ExecutableDecision,
    PersistenceRejectionError,
    execute_decision,
    execute_decision_with_enforcement,
    validate_for_persistence,
    require_persistence_contract,
    enforce_payment_monotonicity,
    verify_monotonicity_invariant,
    map_activation_failure,
    ACTIVATION_TO_DECISION_FAILURE_MAP,
)
from core.decisions.activation_invariants import (
    ActivationAwareOutcome,
    ActivationDecisionFailure,
    ActivationReference,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================


def make_valid_activation() -> ActivationReference:
    """Create a valid activation reference for testing."""
    return ActivationReference(
        agent_name="CODY",
        gid="GID-01",
        color="BLUE",
        validation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def make_invalid_activation() -> ActivationReference:
    """Create an invalid activation reference for testing."""
    return ActivationReference(
        agent_name="INVALID",
        gid="INVALID",
        color="INVALID",
        validation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def make_unknown_activation() -> ActivationReference:
    """Create an unknown activation reference for testing."""
    return ActivationReference(
        agent_name="UNKNOWN",
        gid="UNKNOWN",
        color="UNKNOWN",
        validation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def sample_decision_fn(inputs: Dict[str, Any]) -> Tuple[DecisionOutcome, str]:
    """Sample deterministic decision function for testing."""
    amount = inputs.get("amount", 0)
    if amount <= 10000:
        return DecisionOutcome.APPROVED, f"Payment of ${amount:,.2f} approved (under threshold)"
    else:
        return DecisionOutcome.REQUIRES_REVIEW, f"Payment of ${amount:,.2f} requires review (over threshold)"


def failing_decision_fn(inputs: Dict[str, Any]) -> Tuple[DecisionOutcome, str]:
    """Decision function that raises an exception."""
    raise ValueError("Simulated decision failure")


def empty_explanation_fn(inputs: Dict[str, Any]) -> Tuple[DecisionOutcome, str]:
    """Decision function that returns empty explanation."""
    return DecisionOutcome.APPROVED, ""


def short_explanation_fn(inputs: Dict[str, Any]) -> Tuple[DecisionOutcome, str]:
    """Decision function that returns short explanation."""
    return DecisionOutcome.APPROVED, "OK"


# ============================================================================
# MISSING ACTIVATION TESTS
# ============================================================================


class TestMissingActivation:
    """Test that missing activation blocks reject decisions."""

    def test_execute_decision_rejects_none_activation(self):
        """execute_decision MUST reject when activation_reference is None."""
        with pytest.raises(DecisionExecutionError) as exc_info:
            execute_decision(
                activation_reference=None,
                rule_id="TEST-RULE-01",
                rule_version="1.0.0",
                inputs={"amount": 5000},
                decision_fn=sample_decision_fn,
            )
        
        assert exc_info.value.failure_code == DecisionExecutionFailure.ACTIVATION_MISSING
        assert "missing" in exc_info.value.message.lower()

    def test_execute_with_enforcement_rejects_none_activation(self):
        """execute_decision_with_enforcement MUST reject when activation_reference is None."""
        with pytest.raises(DecisionExecutionError) as exc_info:
            execute_decision_with_enforcement(
                activation_reference=None,
                rule_id="TEST-RULE-01",
                rule_version="1.0.0",
                inputs={"amount": 5000},
                decision_fn=sample_decision_fn,
            )
        
        assert exc_info.value.failure_code == DecisionExecutionFailure.ACTIVATION_MISSING

    def test_no_implicit_default_activation(self):
        """No implicit default activation reference should be used."""
        # Explicitly test that there's no fallback
        with pytest.raises(DecisionExecutionError) as exc_info:
            execute_decision(
                activation_reference=None,
                rule_id="TEST-RULE-01",
                rule_version="1.0.0",
                inputs={},
                decision_fn=sample_decision_fn,
            )
        
        # Must fail with ACTIVATION_MISSING, not proceed with default
        assert exc_info.value.failure_code == DecisionExecutionFailure.ACTIVATION_MISSING


# ============================================================================
# INVALID ACTIVATION TESTS
# ============================================================================


class TestInvalidActivation:
    """Test that invalid activation blocks reject decisions."""

    def test_execute_decision_rejects_invalid_agent_name(self):
        """Activation with agent_name='INVALID' MUST be rejected."""
        with pytest.raises(DecisionExecutionError) as exc_info:
            execute_decision(
                activation_reference=make_invalid_activation(),
                rule_id="TEST-RULE-01",
                rule_version="1.0.0",
                inputs={"amount": 5000},
                decision_fn=sample_decision_fn,
            )
        
        assert exc_info.value.failure_code == DecisionExecutionFailure.ACTIVATION_INVALID
        assert "agent_name" in exc_info.value.message

    def test_execute_decision_rejects_unknown_agent_name(self):
        """Activation with agent_name='UNKNOWN' MUST be rejected."""
        with pytest.raises(DecisionExecutionError) as exc_info:
            execute_decision(
                activation_reference=make_unknown_activation(),
                rule_id="TEST-RULE-01",
                rule_version="1.0.0",
                inputs={"amount": 5000},
                decision_fn=sample_decision_fn,
            )
        
        assert exc_info.value.failure_code == DecisionExecutionFailure.ACTIVATION_INVALID

    def test_execute_decision_rejects_none_gid(self):
        """Activation with gid='NONE' MUST be rejected."""
        activation = ActivationReference(
            agent_name="CODY",
            gid="NONE",
            color="BLUE",
            validation_timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        with pytest.raises(DecisionExecutionError) as exc_info:
            execute_decision(
                activation_reference=activation,
                rule_id="TEST-RULE-01",
                rule_version="1.0.0",
                inputs={"amount": 5000},
                decision_fn=sample_decision_fn,
            )
        
        assert exc_info.value.failure_code == DecisionExecutionFailure.ACTIVATION_INVALID
        assert "gid" in exc_info.value.message


# ============================================================================
# VALID ACTIVATION TESTS
# ============================================================================


class TestValidActivation:
    """Test that valid activation blocks allow decisions to proceed."""

    def test_execute_decision_proceeds_with_valid_activation(self):
        """Valid activation MUST allow decision to proceed."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        assert decision.outcome == ActivationAwareOutcome.APPROVED
        assert decision.activation_reference.agent_name == "CODY"
        assert decision.activation_reference.gid == "GID-01"
        assert decision.decision_id is not None

    def test_execute_decision_preserves_activation_reference(self):
        """Decision MUST preserve the activation reference."""
        activation = make_valid_activation()
        decision = execute_decision(
            activation_reference=activation,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        assert decision.activation_reference.agent_name == activation.agent_name
        assert decision.activation_reference.gid == activation.gid
        assert decision.activation_reference.color == activation.color

    def test_execute_decision_above_threshold_requires_review(self):
        """Amount above threshold MUST produce REQUIRES_REVIEW outcome."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 15000},
            decision_fn=sample_decision_fn,
        )
        
        assert decision.outcome == ActivationAwareOutcome.REQUIRES_REVIEW

    def test_execute_decision_includes_rule_metadata(self):
        """Decision MUST include rule_id and rule_version."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        assert decision.rule_id == "TEST-RULE-01"
        assert decision.rule_version == "1.0.0"


# ============================================================================
# FAILURE PROPAGATION TESTS
# ============================================================================


class TestFailurePropagation:
    """Test that failures are explicitly propagated with failure codes."""

    def test_decision_function_exception_produces_error_outcome(self):
        """Exception in decision function MUST produce ERROR outcome."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=failing_decision_fn,
        )
        
        assert decision.outcome == ActivationAwareOutcome.ERROR
        assert decision.failure_code == DecisionExecutionFailure.RULE_EXECUTION_FAILURE
        assert "ValueError" in decision.explanation

    def test_empty_explanation_produces_error_outcome(self):
        """Empty explanation MUST produce ERROR outcome."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=empty_explanation_fn,
        )
        
        assert decision.outcome == ActivationAwareOutcome.ERROR
        assert decision.failure_code == DecisionExecutionFailure.CONTRACT_VIOLATION

    def test_short_explanation_produces_error_outcome(self):
        """Explanation under 10 chars MUST produce ERROR outcome."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=short_explanation_fn,
        )
        
        assert decision.outcome == ActivationAwareOutcome.ERROR
        assert decision.failure_code == DecisionExecutionFailure.CONTRACT_VIOLATION

    def test_no_exception_swallowing(self):
        """Exceptions MUST NOT be swallowed silently."""
        # This should not raise - the exception is caught and converted to ERROR
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=failing_decision_fn,
        )
        
        # But it MUST have explicit failure information
        assert decision.outcome == ActivationAwareOutcome.ERROR
        assert decision.failure_code is not None
        assert "exception" in decision.explanation.lower()


# ============================================================================
# PERSISTENCE CONTRACT TESTS
# ============================================================================


class TestPersistenceContract:
    """Test that persistence contract is enforced."""

    def test_validate_for_persistence_accepts_valid_decision(self):
        """Valid decision MUST pass persistence validation."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        is_valid, rejection = validate_for_persistence(decision)
        assert is_valid is True
        assert rejection is None

    def test_require_persistence_contract_passes_for_valid_decision(self):
        """Valid decision MUST pass require_persistence_contract."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        # Should not raise
        require_persistence_contract(decision)

    def test_validate_for_persistence_rejects_invalid_agent_name(self):
        """Decision with invalid agent_name MUST fail persistence validation."""
        # Create decision that bypasses execution checks (for testing persistence)
        decision = ExecutableDecision(
            decision_id="test-id",
            outcome=ActivationAwareOutcome.APPROVED,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            explanation="Valid explanation for testing purposes",
            activation_reference=ActivationReference(
                agent_name="INVALID",
                gid="GID-01",
                color="BLUE",
                validation_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
        
        is_valid, rejection = validate_for_persistence(decision)
        assert is_valid is False
        assert "agent_name" in rejection

    def test_validate_for_persistence_rejects_invalid_gid(self):
        """Decision with invalid gid MUST fail persistence validation."""
        decision = ExecutableDecision(
            decision_id="test-id",
            outcome=ActivationAwareOutcome.APPROVED,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            explanation="Valid explanation for testing purposes",
            activation_reference=ActivationReference(
                agent_name="CODY",
                gid="UNKNOWN",
                color="BLUE",
                validation_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
        
        is_valid, rejection = validate_for_persistence(decision)
        assert is_valid is False
        assert "gid" in rejection

    def test_validate_for_persistence_rejects_invalid_color(self):
        """Decision with invalid color MUST fail persistence validation."""
        decision = ExecutableDecision(
            decision_id="test-id",
            outcome=ActivationAwareOutcome.APPROVED,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            explanation="Valid explanation for testing purposes",
            activation_reference=ActivationReference(
                agent_name="CODY",
                gid="GID-01",
                color="NONE",
                validation_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )
        
        is_valid, rejection = validate_for_persistence(decision)
        assert is_valid is False
        assert "color" in rejection

    def test_execute_with_enforcement_validates_persistence(self):
        """execute_decision_with_enforcement MUST validate persistence contract."""
        # Valid decision should succeed
        decision = execute_decision_with_enforcement(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
            enforce_persistence=True,
        )
        
        assert decision.outcome == ActivationAwareOutcome.APPROVED


# ============================================================================
# MONOTONICITY TESTS
# ============================================================================


class TestMonotonicity:
    """Test monotonicity enforcement for payment decisions."""

    def test_higher_amount_higher_severity_is_monotonic(self):
        """Higher amount → higher severity MUST be monotonic."""
        decision_low = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        decision_high = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 15000},
            decision_fn=sample_decision_fn,
        )
        
        is_monotonic, violation = enforce_payment_monotonicity(
            15000, 5000, decision_high, decision_low
        )
        
        # Higher amount, higher severity = monotonic
        assert is_monotonic is True
        assert violation is None

    def test_higher_amount_lower_severity_violates_monotonicity(self):
        """Higher amount → lower severity MUST violate monotonicity."""
        # Create artificial decisions to test violation
        decision_low_amount_high_severity = ExecutableDecision(
            decision_id="test-1",
            outcome=ActivationAwareOutcome.REQUIRES_REVIEW,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            explanation="Low amount but requires review",
            activation_reference=make_valid_activation(),
        )
        
        decision_high_amount_low_severity = ExecutableDecision(
            decision_id="test-2",
            outcome=ActivationAwareOutcome.APPROVED,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 15000},
            explanation="High amount but approved",
            activation_reference=make_valid_activation(),
        )
        
        is_monotonic, violation = enforce_payment_monotonicity(
            15000, 5000, decision_high_amount_low_severity, decision_low_amount_high_severity
        )
        
        # Higher amount, lower severity = NOT monotonic
        assert is_monotonic is False
        assert violation is not None
        assert "violation" in violation.lower()

    def test_execute_with_enforcement_checks_monotonicity(self):
        """execute_decision_with_enforcement MUST check monotonicity when reference provided."""
        prior_decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 15000},
            decision_fn=sample_decision_fn,
        )
        
        # Lower amount should produce lower or equal severity
        decision = execute_decision_with_enforcement(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
            enforce_monotonicity_with=(15000, prior_decision),
        )
        
        # This should succeed - lower amount, lower severity is monotonic
        assert decision.outcome == ActivationAwareOutcome.APPROVED


# ============================================================================
# FAILURE CODE MAPPING TESTS
# ============================================================================


class TestFailureCodeMapping:
    """Test that activation failures map to decision execution failures."""

    def test_all_activation_failures_have_mapping(self):
        """Every ActivationDecisionFailure MUST have a mapping."""
        for activation_failure in ActivationDecisionFailure:
            decision_failure = map_activation_failure(activation_failure)
            assert decision_failure is not None
            assert isinstance(decision_failure, DecisionExecutionFailure)

    def test_missing_activation_maps_correctly(self):
        """MISSING_ACTIVATION → ACTIVATION_MISSING."""
        result = map_activation_failure(ActivationDecisionFailure.MISSING_ACTIVATION)
        assert result == DecisionExecutionFailure.ACTIVATION_MISSING

    def test_invalid_activation_maps_correctly(self):
        """INVALID_ACTIVATION → ACTIVATION_INVALID."""
        result = map_activation_failure(ActivationDecisionFailure.INVALID_ACTIVATION)
        assert result == DecisionExecutionFailure.ACTIVATION_INVALID

    def test_monotonicity_violation_maps_correctly(self):
        """MONOTONICITY_VIOLATION → MONOTONICITY_VIOLATION."""
        result = map_activation_failure(ActivationDecisionFailure.MONOTONICITY_VIOLATION)
        assert result == DecisionExecutionFailure.MONOTONICITY_VIOLATION

    def test_mapping_is_complete(self):
        """ACTIVATION_TO_DECISION_FAILURE_MAP MUST cover all activation failures."""
        for activation_failure in ActivationDecisionFailure:
            assert activation_failure in ACTIVATION_TO_DECISION_FAILURE_MAP


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================


class TestSerialization:
    """Test that decisions serialize correctly for audit/persistence."""

    def test_decision_to_dict_includes_all_fields(self):
        """to_dict MUST include all required fields."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        data = decision.to_dict()
        
        assert "decision_id" in data
        assert "outcome" in data
        assert "rule_id" in data
        assert "rule_version" in data
        assert "inputs" in data
        assert "explanation" in data
        assert "activation_reference" in data
        assert "timestamp" in data

    def test_decision_to_dict_includes_activation_reference(self):
        """to_dict MUST include nested activation_reference fields."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        data = decision.to_dict()
        ref = data["activation_reference"]
        
        assert ref["agent_name"] == "CODY"
        assert ref["gid"] == "GID-01"
        assert ref["color"] == "BLUE"
        assert "validation_timestamp" in ref

    def test_error_decision_includes_failure_code(self):
        """ERROR decisions MUST include failure_code in serialization."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=failing_decision_fn,
        )
        
        data = decision.to_dict()
        
        assert data["outcome"] == "error"
        assert data["failure_code"] is not None


# ============================================================================
# NO RETRY / IDEMPOTENCY TESTS
# ============================================================================


class TestNoRetrySemantics:
    """Test that failed decisions don't allow retry."""

    def test_decision_is_immutable(self):
        """ExecutableDecision MUST be immutable (frozen dataclass)."""
        decision = execute_decision(
            activation_reference=make_valid_activation(),
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        with pytest.raises(AttributeError):
            decision.outcome = ActivationAwareOutcome.REJECTED  # type: ignore

    def test_activation_reference_is_immutable(self):
        """ActivationReference MUST be immutable (frozen dataclass)."""
        activation = make_valid_activation()
        
        with pytest.raises(AttributeError):
            activation.agent_name = "HACKER"  # type: ignore


# ============================================================================
# DETERMINISM TESTS
# ============================================================================


class TestDeterminism:
    """Test that decisions are deterministic."""

    def test_same_inputs_produce_same_outcome(self):
        """Same inputs MUST produce same outcome."""
        inputs = {"amount": 5000}
        activation = make_valid_activation()
        
        decision1 = execute_decision(
            activation_reference=activation,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs=inputs,
            decision_fn=sample_decision_fn,
        )
        
        decision2 = execute_decision(
            activation_reference=activation,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs=inputs,
            decision_fn=sample_decision_fn,
        )
        
        assert decision1.outcome == decision2.outcome
        assert decision1.rule_id == decision2.rule_id

    def test_different_amounts_produce_different_outcomes(self):
        """Different amounts MUST produce appropriate different outcomes."""
        activation = make_valid_activation()
        
        decision_low = execute_decision(
            activation_reference=activation,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 5000},
            decision_fn=sample_decision_fn,
        )
        
        decision_high = execute_decision(
            activation_reference=activation,
            rule_id="TEST-RULE-01",
            rule_version="1.0.0",
            inputs={"amount": 15000},
            decision_fn=sample_decision_fn,
        )
        
        assert decision_low.outcome == ActivationAwareOutcome.APPROVED
        assert decision_high.outcome == ActivationAwareOutcome.REQUIRES_REVIEW
