"""Tests for ACM Evaluator — Task 3 of PAC-ACM-02.

These tests verify the core ALEX enforcement logic:
- ESCALATE always allowed
- BLOCK only for Sam/ALEX
- EXECUTE requires explicit permission
- READ/PROPOSE require matching scope
- Default deny for everything else
"""

import pytest

from core.governance.acm_evaluator import ACMDecision, ACMEvaluator, DenialReason, EvaluationResult, evaluate_intent
from core.governance.acm_loader import ACMLoader
from core.governance.intent_schema import AgentIntent, IntentVerb, create_intent


class TestEscalateAlwaysAllowed:
    """Test that ESCALATE is always allowed (universal capability)."""

    def test_escalate_allowed_for_cody(self, manifests_dir):
        """Test Cody can always escalate."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "ESCALATE", "security implications")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_escalate_allowed_for_sonny(self, manifests_dir):
        """Test Sonny can always escalate."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-02", "ESCALATE", "backend API requirements")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_escalate_allowed_for_any_target(self, manifests_dir):
        """Test ESCALATE is allowed regardless of target."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        # Random target should still be allowed for ESCALATE
        intent = create_intent("GID-01", "ESCALATE", "completely random target")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW


class TestBlockOnlyForAuthorized:
    """Test that BLOCK is only allowed for Sam (GID-06) and ALEX (GID-08)."""

    def test_block_allowed_for_sam(self, manifests_dir):
        """Test Sam can BLOCK within their scope."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-06", "BLOCK", "insecure code changes")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_block_allowed_for_alex(self, manifests_dir):
        """Test ALEX can BLOCK within their scope."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-08", "BLOCK", "governance violations")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_block_denied_for_cody(self, manifests_dir):
        """Test Cody cannot BLOCK (no BLOCK authority)."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "BLOCK", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.BLOCK_NOT_PERMITTED

    def test_block_denied_for_sonny(self, manifests_dir):
        """Test Sonny cannot BLOCK (no BLOCK authority)."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-02", "BLOCK", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.BLOCK_NOT_PERMITTED

    def test_block_denied_for_dan(self, manifests_dir):
        """Test Dan cannot BLOCK (no BLOCK authority)."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-07", "BLOCK", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.BLOCK_NOT_PERMITTED


class TestExecuteRequiresExplicitPermission:
    """Test that EXECUTE requires explicit ACM entry."""

    def test_execute_allowed_for_cody_test_runs(self, manifests_dir):
        """Test Cody can EXECUTE local test runs."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "EXECUTE", "local test runs")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_execute_allowed_for_cody_pytest(self, manifests_dir):
        """Test Cody can EXECUTE pytest (matches 'local test runs')."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "EXECUTE", "pytest")
        result = evaluator.evaluate(intent)

        # Should match because "test" is in "local test runs"
        assert result.decision == ACMDecision.ALLOW

    def test_execute_denied_for_cody_production_deploy(self, manifests_dir):
        """Test Cody cannot EXECUTE production deployment."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "EXECUTE", "production deployment")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.EXECUTE_NOT_PERMITTED

    def test_execute_denied_for_sam(self, manifests_dir):
        """Test Sam cannot EXECUTE anything (empty execute list)."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-06", "EXECUTE", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.EXECUTE_NOT_PERMITTED

    def test_execute_denied_for_alex(self, manifests_dir):
        """Test ALEX cannot EXECUTE anything (empty execute list)."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-08", "EXECUTE", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.EXECUTE_NOT_PERMITTED


class TestReadProposeScopeMatching:
    """Test READ/PROPOSE require matching scope."""

    def test_read_allowed_in_scope(self, manifests_dir):
        """Test READ allowed for targets in scope."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "READ", "backend source code")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_read_denied_out_of_scope(self, manifests_dir):
        """Test READ denied for targets not in scope."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        # Cody (backend) cannot read frontend code
        intent = create_intent("GID-01", "READ", "frontend components")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.TARGET_NOT_IN_SCOPE

    def test_propose_allowed_in_scope(self, manifests_dir):
        """Test PROPOSE allowed for targets in scope."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "PROPOSE", "backend code changes")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_propose_denied_out_of_scope(self, manifests_dir):
        """Test PROPOSE denied for targets not in scope."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        # Cody cannot propose frontend changes
        intent = create_intent("GID-01", "PROPOSE", "UI component changes")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY


class TestUnknownAgentDenied:
    """Test that unknown agents are denied."""

    def test_unknown_gid_denied(self, manifests_dir):
        """Test unknown GID results in denial."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-99", "READ", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.UNKNOWN_AGENT


class TestMalformedIntentDenied:
    """Test that malformed intents are denied."""

    def test_malformed_intent_dict_denied(self, manifests_dir):
        """Test malformed intent dictionary is denied."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        result = evaluator.evaluate_dict({"invalid": "data"})

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.INVALID_INTENT


class TestEvaluationResultAudit:
    """Test evaluation result contains all audit fields."""

    def test_result_contains_timestamp(self, manifests_dir):
        """Test result includes timestamp."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "READ", "test")
        result = evaluator.evaluate(intent)

        assert result.timestamp is not None
        assert "T" in result.timestamp  # ISO format

    def test_result_contains_acm_version(self, manifests_dir):
        """Test result includes ACM version."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "READ", "backend source code")
        result = evaluator.evaluate(intent)

        assert result.acm_version == "1.0.0"

    def test_deny_result_contains_reason(self, manifests_dir):
        """Test denial contains structured reason."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "BLOCK", "anything")
        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason is not None
        assert result.reason_detail is not None

    def test_to_audit_dict_format(self, manifests_dir):
        """Test to_audit_dict() produces correct format."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()
        evaluator = ACMEvaluator(loader)

        intent = create_intent("GID-01", "READ", "backend code", correlation_id="test-123")
        result = evaluator.evaluate(intent)

        audit = result.to_audit_dict()

        assert "agent_gid" in audit
        assert "intent" in audit
        assert "decision" in audit
        assert "timestamp" in audit
        assert "acm_version" in audit
        assert audit["correlation_id"] == "test-123"


class TestConvenienceFunction:
    """Test evaluate_intent convenience function."""

    def test_evaluate_intent_function(self, manifests_dir):
        """Test evaluate_intent() convenience function."""
        loader = ACMLoader(manifests_dir)
        loader.load_all()

        intent = create_intent("GID-01", "ESCALATE", "test")
        result = evaluate_intent(intent, loader)

        assert result.decision == ACMDecision.ALLOW
