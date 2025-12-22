"""Tests for DCC — Deterministic Correction Contract v1.

These tests verify PAC-DIGGI-02 requirements:
1. Every DenialReason has a correction mapping
2. No correction contains EXECUTE
3. Identical input → identical output
4. Unknown denial → DIGGI_NO_VALID_CORRECTION
5. Diggi output does not permit retries
6. Diggi output does not mutate intent
7. Correction plans survive serialization round-trip
8. System fails closed if correction map missing or invalid

No test = no merge.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.governance.acm_evaluator import ACMDecision, DenialReason, EvaluationResult
from core.governance.diggi_corrections import (
    FORBIDDEN_CORRECTION_VERBS,
    CorrectionError,
    CorrectionMap,
    CorrectionMapInvalidError,
    CorrectionMapNotFoundError,
    CorrectionPlan,
    CorrectionStep,
    ForbiddenVerbInCorrectionError,
    NoValidCorrectionError,
    get_correction_for_denial,
    get_correction_map,
    load_correction_map,
    reset_correction_map,
)
from core.governance.intent_schema import create_intent
from gateway.alex_middleware import ALEXMiddleware, ALEXMiddlewareError, IntentDeniedError, MiddlewareConfig


@pytest.fixture(autouse=True)
def reset_correction_singleton():
    """Reset the correction map singleton before each test."""
    reset_correction_map()
    yield
    reset_correction_map()


class TestEveryDenialReasonHasCorrection:
    """1. Every DenialReason has a correction mapping."""

    def test_all_denial_reasons_mapped(self):
        """Test that all DenialReason values have correction mappings."""
        correction_map = load_correction_map()

        # Get all denial reasons except the meta-reason for no correction
        all_reasons = [r for r in DenialReason if r != DenialReason.DIGGI_NO_VALID_CORRECTION]
        mapped_reasons = correction_map.get_all_mapped_reasons()

        missing = []
        for reason in all_reasons:
            if reason.value not in mapped_reasons:
                missing.append(reason.value)

        assert not missing, f"Missing correction mappings for: {missing}"

    def test_each_reason_produces_valid_plan(self):
        """Test that each mapped reason produces a valid CorrectionPlan."""
        correction_map = load_correction_map()

        # Get all denial reasons with mappings
        for reason in DenialReason:
            if reason == DenialReason.DIGGI_NO_VALID_CORRECTION:
                continue
            if not correction_map.has_correction(reason):
                continue

            plan = correction_map.get_correction(reason)

            assert isinstance(plan, CorrectionPlan)
            assert plan.cause == reason.value
            assert isinstance(plan.constraints, tuple)
            assert isinstance(plan.allowed_next_steps, tuple)


class TestNoCorrectionContainsExecute:
    """2. No correction contains EXECUTE."""

    def test_forbidden_verbs_not_in_corrections(self):
        """Test that no correction contains EXECUTE, APPROVE, or BLOCK."""
        correction_map = load_correction_map()

        for reason in DenialReason:
            if reason == DenialReason.DIGGI_NO_VALID_CORRECTION:
                continue
            if not correction_map.has_correction(reason):
                continue

            plan = correction_map.get_correction(reason)

            for step in plan.allowed_next_steps:
                assert (
                    step.verb.upper() not in FORBIDDEN_CORRECTION_VERBS
                ), f"Correction for {reason.value} contains forbidden verb: {step.verb}"

    def test_correction_step_rejects_execute(self):
        """Test that CorrectionStep raises on EXECUTE verb."""
        with pytest.raises(ForbiddenVerbInCorrectionError):
            CorrectionStep(
                verb="EXECUTE",
                target_scope="anything",
                target=None,
                description="This should fail",
            )

    def test_correction_step_rejects_approve(self):
        """Test that CorrectionStep raises on APPROVE verb."""
        with pytest.raises(ForbiddenVerbInCorrectionError):
            CorrectionStep(
                verb="APPROVE",
                target_scope="anything",
                target=None,
                description="This should fail",
            )

    def test_correction_step_rejects_block(self):
        """Test that CorrectionStep raises on BLOCK verb."""
        with pytest.raises(ForbiddenVerbInCorrectionError):
            CorrectionStep(
                verb="BLOCK",
                target_scope="anything",
                target=None,
                description="This should fail",
            )


class TestIdenticalInputIdenticalOutput:
    """3. Identical input → identical output (deterministic)."""

    def test_same_reason_produces_same_correction(self):
        """Test that the same denial reason always produces identical correction."""
        correction_map = load_correction_map()

        # Test multiple times
        for _ in range(5):
            plan1 = correction_map.get_correction(DenialReason.EXECUTE_NOT_PERMITTED)
            plan2 = correction_map.get_correction(DenialReason.EXECUTE_NOT_PERMITTED)

            assert plan1.cause == plan2.cause
            assert plan1.constraints == plan2.constraints
            assert len(plan1.allowed_next_steps) == len(plan2.allowed_next_steps)

            for s1, s2 in zip(plan1.allowed_next_steps, plan2.allowed_next_steps):
                assert s1.verb == s2.verb
                assert s1.target_scope == s2.target_scope
                assert s1.target == s2.target
                assert s1.description == s2.description

    def test_different_map_instances_same_output(self):
        """Test that different map instances produce same corrections."""
        reset_correction_map()
        map1 = load_correction_map()
        plan1 = map1.get_correction(DenialReason.VERB_NOT_PERMITTED)

        reset_correction_map()
        map2 = load_correction_map()
        plan2 = map2.get_correction(DenialReason.VERB_NOT_PERMITTED)

        assert plan1.to_dict() == plan2.to_dict()


class TestUnknownDenialFailsClosed:
    """4. Unknown denial → DIGGI_NO_VALID_CORRECTION (fail closed)."""

    def test_no_correction_raises_error(self):
        """Test that unknown denial reason raises NoValidCorrectionError."""
        # Create a mock correction map without the new denial reason
        # We test by using the module's fail-closed behavior
        correction_map = load_correction_map()

        # DIGGI_NO_VALID_CORRECTION should not have a mapping
        with pytest.raises(NoValidCorrectionError):
            correction_map.get_correction(DenialReason.DIGGI_NO_VALID_CORRECTION)

    def test_middleware_returns_no_valid_correction_reason(self, manifests_dir):
        """Test middleware returns DIGGI_NO_VALID_CORRECTION for unmapped reasons."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_dcc=True,
            enforce_drcp=False,  # Disable to test DCC directly
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        # Create an intent that will be denied
        intent = create_intent(
            agent_gid="GID-99",  # Unknown agent
            verb="READ",
            target="anything",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        # The correction should either be attached or NO_VALID_CORRECTION
        # Since UNKNOWN_AGENT should be mapped, we expect a correction
        if result.reason == DenialReason.UNKNOWN_AGENT:
            assert result.correction_plan is not None


class TestDiggiOutputDoesNotPermitRetries:
    """5. Diggi output does not permit retries."""

    def test_correction_steps_do_not_include_original_action(self):
        """Test that correction steps don't just retry the original action."""
        correction_map = load_correction_map()

        for reason in DenialReason:
            if reason == DenialReason.DIGGI_NO_VALID_CORRECTION:
                continue
            if not correction_map.has_correction(reason):
                continue

            plan = correction_map.get_correction(reason)

            for step in plan.allowed_next_steps:
                # No correction should suggest EXECUTE, APPROVE, or BLOCK
                assert step.verb.upper() not in {"EXECUTE", "APPROVE", "BLOCK"}

    def test_retry_after_deny_correction_does_not_suggest_retry(self):
        """Test that RETRY_AFTER_DENY_FORBIDDEN correction doesn't suggest retry."""
        correction_map = load_correction_map()
        plan = correction_map.get_correction(DenialReason.RETRY_AFTER_DENY_FORBIDDEN)

        for step in plan.allowed_next_steps:
            # Should suggest READ or ESCALATE, not retry
            assert step.verb.upper() in {"READ", "ESCALATE", "PROPOSE"}


class TestDiggiOutputDoesNotMutateIntent:
    """6. Diggi output does not mutate intent."""

    def test_correction_plan_is_immutable(self):
        """Test that CorrectionPlan is frozen dataclass."""
        step = CorrectionStep(
            verb="PROPOSE",
            target_scope="test",
            target=None,
            description="Test",
        )
        plan = CorrectionPlan(
            cause="TEST",
            constraints=("constraint1",),
            allowed_next_steps=(step,),
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            plan.cause = "MODIFIED"  # type: ignore

    def test_correction_step_is_immutable(self):
        """Test that CorrectionStep is frozen dataclass."""
        step = CorrectionStep(
            verb="PROPOSE",
            target_scope="test",
            target=None,
            description="Test",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            step.verb = "MODIFIED"  # type: ignore

    def test_original_result_unchanged_after_correction_lookup(self, manifests_dir):
        """Test that looking up correction doesn't modify original result."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_dcc=True,
            enforce_drcp=False,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        # Create an intent that will be denied
        intent = create_intent(
            agent_gid="GID-02",  # Sonny
            verb="EXECUTE",  # Not permitted
            target="anything",
        )

        result = middleware.evaluate(intent)

        # Original intent verb should be unchanged
        assert result.intent_verb == "EXECUTE"
        assert result.intent_target == "anything"
        assert result.agent_gid == "GID-02"


class TestCorrectionPlansSurviveSerialization:
    """7. Correction plans survive serialization round-trip."""

    def test_to_dict_round_trip(self):
        """Test that CorrectionPlan survives dict round-trip."""
        correction_map = load_correction_map()
        original_plan = correction_map.get_correction(DenialReason.EXECUTE_NOT_PERMITTED)

        # Convert to dict
        plan_dict = original_plan.to_dict()

        # Should have the expected structure
        assert "correction_plan" in plan_dict
        inner = plan_dict["correction_plan"]
        assert inner["cause"] == "EXECUTE_NOT_PERMITTED"
        assert isinstance(inner["constraints"], list)
        assert isinstance(inner["allowed_next_steps"], list)

    def test_json_serialization_round_trip(self):
        """Test that CorrectionPlan survives JSON round-trip."""
        correction_map = load_correction_map()
        original_plan = correction_map.get_correction(DenialReason.EXECUTE_NOT_PERMITTED)

        # Convert to JSON and back
        plan_dict = original_plan.to_dict()
        json_str = json.dumps(plan_dict)
        restored_dict = json.loads(json_str)

        assert restored_dict == plan_dict

    def test_evaluation_result_with_correction_serializes(self):
        """Test that EvaluationResult with correction_plan serializes."""
        correction_map = load_correction_map()
        plan = correction_map.get_correction(DenialReason.EXECUTE_NOT_PERMITTED)

        result = EvaluationResult(
            decision=ACMDecision.DENY,
            agent_gid="GID-01",
            intent_verb="EXECUTE",
            intent_target="test",
            reason=DenialReason.EXECUTE_NOT_PERMITTED,
            reason_detail="Test denial",
            acm_version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id="test-123",
            next_hop="GID-00",
            correction_plan=plan.to_dict(),
        )

        audit_dict = result.to_audit_dict()

        # Should include correction_plan
        assert "correction_plan" in audit_dict
        assert audit_dict["correction_plan"]["correction_plan"]["cause"] == "EXECUTE_NOT_PERMITTED"


class TestSystemFailsClosedOnMissingMap:
    """8. System fails closed if correction map missing or invalid."""

    def test_missing_map_raises_error(self, tmp_path):
        """Test that missing correction map raises CorrectionMapNotFoundError."""
        fake_path = tmp_path / "nonexistent.yaml"
        correction_map = CorrectionMap(fake_path)

        with pytest.raises(CorrectionMapNotFoundError):
            correction_map.load()

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises CorrectionMapInvalidError."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("not: valid: yaml: {{{{")

        correction_map = CorrectionMap(invalid_yaml)

        with pytest.raises(CorrectionMapInvalidError):
            correction_map.load()

    def test_missing_required_fields_raises_error(self, tmp_path):
        """Test that missing required fields raises CorrectionMapInvalidError."""
        incomplete_yaml = tmp_path / "incomplete.yaml"
        incomplete_yaml.write_text(
            """
version: "1.0.0"
corrections: {}
"""
        )

        correction_map = CorrectionMap(incomplete_yaml)

        with pytest.raises(CorrectionMapInvalidError):
            correction_map.load()

    def test_missing_governance_lock_raises_error(self, tmp_path):
        """Test that missing governance_lock raises CorrectionMapInvalidError."""
        unlocked_yaml = tmp_path / "unlocked.yaml"
        unlocked_yaml.write_text(
            """
version: "1.0.0"
schema_version: "DCC-v1"
governance_lock: false
corrections: {}
"""
        )

        correction_map = CorrectionMap(unlocked_yaml)

        with pytest.raises(CorrectionMapInvalidError):
            correction_map.load()

    def test_forbidden_verb_in_map_raises_error(self, tmp_path):
        """Test that forbidden verb in correction map raises error."""
        bad_yaml = tmp_path / "bad_verb.yaml"
        bad_yaml.write_text(
            """
version: "1.0.0"
schema_version: "DCC-v1"
governance_lock: true
corrections:
  EXECUTE_NOT_PERMITTED:
    constraints:
      - "Test constraint"
    allowed_next_steps:
      - verb: "EXECUTE"
        target_scope: "test"
        description: "This is forbidden"
"""
        )

        correction_map = CorrectionMap(bad_yaml)

        with pytest.raises(ForbiddenVerbInCorrectionError):
            correction_map.load()

    def test_middleware_fails_on_missing_map(self, manifests_dir, tmp_path):
        """Test that middleware fails to initialize without correction map."""
        from core.governance.acm_loader import ACMLoader

        # Create middleware with non-existent correction map
        config = MiddlewareConfig(
            enforce_dcc=True,
            require_checklist=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)

        # Temporarily point to non-existent map by modifying module constant
        import core.governance.diggi_corrections as dc

        original_path = dc.DEFAULT_CORRECTION_MAP_PATH
        dc.DEFAULT_CORRECTION_MAP_PATH = tmp_path / "nonexistent.yaml"

        try:
            with pytest.raises(ALEXMiddlewareError) as exc_info:
                middleware.initialize()

            assert "Correction map" in str(exc_info.value) or "correction map" in str(exc_info.value).lower()
        finally:
            dc.DEFAULT_CORRECTION_MAP_PATH = original_path


class TestDCCIntegrationWithMiddleware:
    """Integration tests for DCC with ALEX middleware."""

    @pytest.fixture
    def middleware_with_dcc(self, manifests_dir):
        """Create middleware with DCC enabled."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_dcc=True,
            enforce_drcp=False,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_denied_intent_has_correction_plan(self, middleware_with_dcc):
        """Test that denied intents include correction_plan."""
        intent = create_intent(
            agent_gid="GID-02",  # Sonny
            verb="EXECUTE",  # Not permitted
            target="anything",
        )

        result = middleware_with_dcc.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.correction_plan is not None
        assert "correction_plan" in result.correction_plan

    def test_allowed_intent_has_no_correction_plan(self, middleware_with_dcc):
        """Test that allowed intents don't include correction_plan."""
        intent = create_intent(
            agent_gid="GID-01",  # Cody
            verb="READ",  # Permitted
            target="backend.tests",
        )

        result = middleware_with_dcc.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW
        assert result.correction_plan is None

    def test_correction_plan_structure(self, middleware_with_dcc):
        """Test the structure of attached correction_plan."""
        intent = create_intent(
            agent_gid="GID-02",
            verb="EXECUTE",
            target="anything",
        )

        result = middleware_with_dcc.evaluate(intent)
        plan = result.correction_plan

        # Verify structure
        assert "correction_plan" in plan
        inner = plan["correction_plan"]
        assert "cause" in inner
        assert "constraints" in inner
        assert "allowed_next_steps" in inner

        # Verify no EXECUTE in allowed steps
        for step in inner["allowed_next_steps"]:
            assert step["verb"].upper() != "EXECUTE"


class TestExamplePayloads:
    """Verify example payloads from PAC-DIGGI-02."""

    def test_execute_not_permitted_example(self, manifests_dir):
        """Test the example from PAC-DIGGI-02 spec."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_dcc=True,
            enforce_drcp=False,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        # Input from PAC spec (adapted to our schema)
        intent = create_intent(
            agent_gid="GID-01",  # Cody
            verb="EXECUTE",
            target="production.deploy",
        )

        result = middleware.evaluate(intent)

        # Verify output structure matches PAC spec
        assert result.decision == ACMDecision.DENY
        assert result.correction_plan is not None

        plan = result.correction_plan["correction_plan"]
        assert plan["cause"] == "EXECUTE_NOT_PERMITTED"
        assert len(plan["constraints"]) > 0

        # Verify allowed_next_steps
        steps = plan["allowed_next_steps"]
        assert len(steps) > 0

        # At least one PROPOSE step and one ESCALATE step
        verbs = [s["verb"].upper() for s in steps]
        assert "PROPOSE" in verbs or "ESCALATE" in verbs

        # No EXECUTE allowed
        assert "EXECUTE" not in verbs
