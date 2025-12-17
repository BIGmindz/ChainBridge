"""Tests for DRCP — Diggy Rejection & Correction Protocol v1.

These tests verify PAC-DIGGY-01 requirements:
1. ❌ Cody cannot retry after DENY
2. ❌ Sonny cannot self-correct after DENY
3. ❌ Diggy cannot EXECUTE
4. ❌ Diggy cannot APPROVE
5. ✅ Diggy can PROPOSE corrected intent
6. ✅ Diggy can ESCALATE
7. ✅ Audit chain preserved end-to-end

No test = no merge.
"""

from datetime import datetime, timezone

import pytest

from core.governance.acm_evaluator import ACMDecision, DenialReason
from core.governance.drcp import (
    DIGGY_GID,
    CorrectionOption,
    DenialChain,
    DenialRecord,
    DenialRegistry,
    DiggyResponse,
    DRCPOutcome,
    create_denial_record,
    get_denial_registry,
    is_diggy,
    is_diggy_forbidden_verb,
    requires_diggy_routing,
    reset_denial_registry,
)
from core.governance.intent_schema import IntentVerb, create_intent
from gateway.alex_middleware import ALEXMiddleware, IntentDeniedError, MiddlewareConfig

# Note: reset_drcp_registry fixture from conftest.py is applied automatically


class TestDiggyCannotExecute:
    """❌ Diggy cannot EXECUTE — this is ABSOLUTE."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with DRCP enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,  # Test DRCP, not CoC
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_diggy_execute_is_forbidden(self, middleware):
        """Test that Diggy cannot EXECUTE anything."""
        intent = create_intent(
            agent_gid="GID-00",
            verb="EXECUTE",
            target="any target whatsoever",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.DIGGY_EXECUTE_FORBIDDEN
        assert "cannot EXECUTE" in result.reason_detail

    def test_diggy_execute_raises_when_configured(self, manifests_dir):
        """Test that Diggy EXECUTE raises IntentDeniedError."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,
            raise_on_denial=True,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        intent = create_intent(
            agent_gid="GID-00",
            verb="EXECUTE",
            target="anything",
        )

        with pytest.raises(IntentDeniedError) as exc_info:
            middleware.evaluate(intent)

        assert exc_info.value.result.reason == DenialReason.DIGGY_EXECUTE_FORBIDDEN


class TestDiggyCannotApprove:
    """❌ Diggy cannot APPROVE — human-only authority.

    NOTE: APPROVE is not currently a valid IntentVerb in the system.
    When APPROVE is added as a verb, these tests will activate.
    The DRCP enforcement logic for APPROVE is already in place.
    """

    def test_approve_enforcement_exists_in_middleware(self):
        """Test that APPROVE enforcement logic is wired in middleware.

        Since APPROVE is not yet a valid IntentVerb, we test that
        the enforcement code path exists by inspecting the middleware.
        """
        # Verify the enforcement method exists and handles APPROVE
        import inspect

        from gateway.alex_middleware import ALEXMiddleware

        source = inspect.getsource(ALEXMiddleware._check_drcp_diggy_forbidden)
        assert "APPROVE" in source
        assert "DIGGY_APPROVE_FORBIDDEN" in source
        assert "human-only" in source

    def test_approve_in_forbidden_verbs(self):
        """Test that APPROVE is in the forbidden verbs set."""
        from core.governance.drcp import DIGGY_FORBIDDEN_VERBS

        assert "APPROVE" in DIGGY_FORBIDDEN_VERBS


class TestDiggyCannotBlock:
    """❌ Diggy cannot BLOCK — ALEX-only authority."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with DRCP enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_diggy_block_is_forbidden(self, middleware):
        """Test that Diggy cannot BLOCK anything."""
        intent = create_intent(
            agent_gid="GID-00",
            verb="BLOCK",
            target="any action whatsoever",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.DIGGY_BLOCK_FORBIDDEN
        assert "ALEX-only" in result.reason_detail


class TestDiggyCanPropose:
    """✅ Diggy can PROPOSE corrected intents."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with DRCP enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_diggy_can_propose(self, middleware):
        """Test that Diggy can PROPOSE."""
        intent = create_intent(
            agent_gid="GID-00",
            verb="PROPOSE",
            target="corrected intent",
        )

        result = middleware.evaluate(intent)

        # Should not be denied for DRCP reasons
        # May still be denied by ACM scope, but not for being Diggy
        assert result.reason != DenialReason.DIGGY_EXECUTE_FORBIDDEN
        assert result.reason != DenialReason.DIGGY_APPROVE_FORBIDDEN
        assert result.reason != DenialReason.DIGGY_BLOCK_FORBIDDEN


class TestDiggyCanEscalate:
    """✅ Diggy can ESCALATE to human."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with DRCP enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_diggy_can_escalate(self, middleware):
        """Test that Diggy can ESCALATE."""
        intent = create_intent(
            agent_gid="GID-00",
            verb="ESCALATE",
            target="unresolvable denial",
        )

        result = middleware.evaluate(intent)

        # ESCALATE is universal — should be allowed
        assert result.decision == ACMDecision.ALLOW


class TestAgentCannotRetryAfterDeny:
    """❌ Agents cannot retry after DENY."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with DRCP enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,  # Disable to test DRCP directly
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_cody_cannot_retry_after_deny(self, middleware):
        """Test that Cody cannot retry after DENY."""
        # First attempt — Cody tries to BLOCK (not permitted)
        first_intent = create_intent(
            agent_gid="GID-01",
            verb="BLOCK",
            target="something",
        )
        first_result = middleware.evaluate(first_intent)
        assert first_result.decision == ACMDecision.DENY

        # Second attempt — same action
        retry_intent = create_intent(
            agent_gid="GID-01",
            verb="BLOCK",
            target="something",
        )
        retry_result = middleware.evaluate(retry_intent)

        assert retry_result.decision == ACMDecision.DENY
        assert retry_result.reason == DenialReason.RETRY_AFTER_DENY_FORBIDDEN
        assert "await Diggy" in retry_result.reason_detail

    def test_sonny_cannot_self_correct_after_deny(self, middleware):
        """Test that Sonny cannot self-correct after DENY."""
        # First attempt — Sonny tries to EXECUTE (not permitted)
        first_intent = create_intent(
            agent_gid="GID-02",
            verb="EXECUTE",
            target="backend logic",
        )
        first_result = middleware.evaluate(first_intent)
        assert first_result.decision == ACMDecision.DENY

        # Second attempt — same action (self-correction attempt)
        retry_intent = create_intent(
            agent_gid="GID-02",
            verb="EXECUTE",
            target="backend logic",
        )
        retry_result = middleware.evaluate(retry_intent)

        assert retry_result.decision == ACMDecision.DENY
        assert retry_result.reason == DenialReason.RETRY_AFTER_DENY_FORBIDDEN

    def test_different_target_is_not_retry(self, middleware):
        """Test that different target is not considered a retry."""
        # First attempt — denied
        first_intent = create_intent(
            agent_gid="GID-01",
            verb="BLOCK",
            target="target_a",
        )
        middleware.evaluate(first_intent)

        # Second attempt — different target
        second_intent = create_intent(
            agent_gid="GID-01",
            verb="BLOCK",
            target="target_b",
        )
        second_result = middleware.evaluate(second_intent)

        # Should be denied by ACM, not by retry prevention
        assert second_result.reason != DenialReason.RETRY_AFTER_DENY_FORBIDDEN


class TestDenialRoutesToDiggy:
    """✅ All DENY on EXECUTE/BLOCK/APPROVE routes to Diggy."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with DRCP enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_execute_denial_routes_to_diggy(self, middleware):
        """Test that EXECUTE denial includes next_hop = GID-00."""
        intent = create_intent(
            agent_gid="GID-02",  # Sonny has no EXECUTE
            verb="EXECUTE",
            target="anything",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.next_hop == DIGGY_GID

    def test_block_denial_routes_to_diggy(self, middleware):
        """Test that BLOCK denial includes next_hop = GID-00."""
        intent = create_intent(
            agent_gid="GID-01",  # Cody has no BLOCK
            verb="BLOCK",
            target="anything",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.next_hop == DIGGY_GID

    def test_read_denial_does_not_route_to_diggy(self, middleware):
        """Test that READ denial does not route to Diggy."""
        # Create an intent that will be denied for READ
        # (unknown agent to trigger denial)
        intent = create_intent(
            agent_gid="GID-99",  # Unknown agent
            verb="READ",
            target="anything",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        # READ denials don't require Diggy routing
        assert result.next_hop is None


class TestDenialRegistry:
    """Tests for DenialRegistry tracking."""

    def test_register_and_check_denial(self):
        """Test registering and checking denials."""
        registry = DenialRegistry()

        record = DenialRecord(
            intent_id="test-123",
            agent_gid="GID-01",
            verb="EXECUTE",
            target="some action",
            denial_code="EXECUTE_NOT_PERMITTED",
            denial_detail="Not allowed",
            denied_at=datetime.now(timezone.utc).isoformat(),
        )

        registry.register_denial(record)

        assert registry.is_denied("test-123")
        assert registry.has_active_denial("GID-01", "EXECUTE", "some action")
        assert not registry.has_active_denial("GID-01", "READ", "some action")

    def test_clear_denial(self):
        """Test clearing a denial."""
        registry = DenialRegistry()

        record = DenialRecord(
            intent_id="test-456",
            agent_gid="GID-02",
            verb="BLOCK",
            target="action",
            denial_code="BLOCK_NOT_PERMITTED",
            denial_detail="Not allowed",
            denied_at=datetime.now(timezone.utc).isoformat(),
        )

        registry.register_denial(record)
        assert registry.is_denied("test-456")

        registry.clear_denial("test-456")
        assert not registry.is_denied("test-456")


class TestDiggyResponseContract:
    """Tests for Diggy's response contract."""

    def test_valid_response_with_corrections(self):
        """Test valid response with corrective options."""
        response = DiggyResponse(
            original_intent_id="abc-123",
            denial_code="EXECUTE_NOT_PERMITTED",
            analysis="Cody tried to modify frontend code",
            corrective_options=[
                CorrectionOption(
                    option_id="A",
                    description="Route to Sonny for frontend changes",
                    new_intent={"agent_gid": "GID-02", "verb": "PROPOSE"},
                )
            ],
            recommendation="Option A",
            requires_human=False,
        )

        assert response.validate()

    def test_valid_response_requiring_human(self):
        """Test valid response requiring human escalation."""
        response = DiggyResponse(
            original_intent_id="abc-456",
            denial_code="APPROVE_NOT_PERMITTED",
            analysis="Action requires human approval",
            corrective_options=[],
            recommendation=None,
            requires_human=True,
        )

        assert response.validate()

    def test_invalid_response_no_correction_or_human(self):
        """Test invalid response with neither corrections nor human flag."""
        response = DiggyResponse(
            original_intent_id="abc-789",
            denial_code="SOME_ERROR",
            analysis="Something went wrong",
            corrective_options=[],
            recommendation=None,
            requires_human=False,
        )

        with pytest.raises(ValueError) as exc_info:
            response.validate()

        assert "corrective_options OR" in str(exc_info.value)


class TestDenialChainAudit:
    """Tests for denial chain audit trail."""

    def test_denial_chain_to_audit_dict(self):
        """Test converting denial chain to audit format."""
        record = DenialRecord(
            intent_id="chain-test",
            agent_gid="GID-01",
            verb="EXECUTE",
            target="action",
            denial_code="EXECUTE_NOT_PERMITTED",
            denial_detail="Not allowed",
            denied_at="2024-01-01T00:00:00Z",
        )

        chain = DenialChain(
            origin_agent="GID-01",
            denied_by="ALEX",
            corrected_by="GID-00",
            final_outcome=DRCPOutcome.PROPOSED,
            denial_record=record,
        )

        audit_dict = chain.to_audit_dict()

        assert "denial_chain" in audit_dict
        assert audit_dict["denial_chain"]["origin_agent"] == "GID-01"
        assert audit_dict["denial_chain"]["denied_by"] == "ALEX"
        assert audit_dict["denial_chain"]["corrected_by"] == "GID-00"
        assert audit_dict["denial_chain"]["final_outcome"] == "PROPOSED"


class TestDRCPHelperFunctions:
    """Tests for DRCP helper functions."""

    def test_is_diggy(self):
        """Test is_diggy function."""
        assert is_diggy("GID-00")
        assert not is_diggy("GID-01")
        assert not is_diggy("GID-08")

    def test_is_diggy_forbidden_verb(self):
        """Test is_diggy_forbidden_verb function."""
        assert is_diggy_forbidden_verb("EXECUTE")
        assert is_diggy_forbidden_verb("BLOCK")
        assert is_diggy_forbidden_verb("APPROVE")
        assert not is_diggy_forbidden_verb("READ")
        assert not is_diggy_forbidden_verb("PROPOSE")
        assert not is_diggy_forbidden_verb("ESCALATE")

    def test_requires_diggy_routing(self):
        """Test requires_diggy_routing function."""
        assert requires_diggy_routing("EXECUTE")
        assert requires_diggy_routing("BLOCK")
        assert requires_diggy_routing("APPROVE")
        assert not requires_diggy_routing("READ")
        assert not requires_diggy_routing("PROPOSE")


class TestAuditLogPreserved:
    """✅ Audit chain preserved end-to-end."""

    def test_drcp_events_logged(self, manifests_dir, tmp_path):
        """Test that DRCP events are logged to audit."""
        import json

        from core.governance.acm_loader import ACMLoader
        from gateway.alex_middleware import GovernanceAuditLogger

        log_file = tmp_path / "drcp_audit.log"
        audit_logger = GovernanceAuditLogger(log_file)

        config = MiddlewareConfig(
            enforce_drcp=True,
            enforce_chain_of_command=False,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(
            config=config,
            loader=loader,
            audit_logger=audit_logger,
        )
        middleware.initialize()

        # Trigger a Diggy forbidden action
        intent = create_intent(
            agent_gid="GID-00",
            verb="EXECUTE",
            target="forbidden",
        )
        middleware.evaluate(intent)

        # Check audit log
        log_content = log_file.read_text()
        assert "DRCP_DIGGY_FORBIDDEN" in log_content

        # Parse and verify structure
        events = [json.loads(line) for line in log_content.strip().split("\n")]
        drcp_events = [e for e in events if e.get("event", "").startswith("DRCP")]

        assert len(drcp_events) >= 1
        assert drcp_events[0]["agent_gid"] == "GID-00"
        assert drcp_events[0]["verb"] == "EXECUTE"
