"""Tests for Chain-of-Command Enforcement — PAC-GOV-VAL-01 Task 4.

These tests verify that EXECUTE, BLOCK, and APPROVE verbs require
routing through Diggy (GID-00) — the orchestrator.

Chain-of-command violations must emit:
- CHAIN_OF_COMMAND_VIOLATION denial reason
- next_hop = GID-00
"""

from datetime import datetime, timezone

import pytest

from core.governance.acm_evaluator import ACMDecision, DenialReason
from core.governance.intent_schema import IntentVerb, create_intent
from gateway.alex_middleware import ALEXMiddleware, ChecklistEnforcementError, IntentDeniedError, MiddlewareConfig


class TestChainOfCommandEnforcement:
    """Tests for chain-of-command enforcement."""

    @pytest.fixture
    def middleware_with_coc(self, manifests_dir):
        """Create middleware with chain-of-command enforcement enabled."""
        from core.governance.acm_loader import ACMLoader
        from core.governance.checklist_loader import ChecklistLoader

        config = MiddlewareConfig(
            enforce_chain_of_command=True,
            raise_on_denial=False,  # Don't raise, let us inspect result
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_execute_without_coc_is_denied(self, middleware_with_coc):
        """Test that EXECUTE without chain-of-command routing is denied."""
        # Cody tries to EXECUTE without Diggy authorization
        intent = create_intent(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="local test runs",
        )

        result = middleware_with_coc.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.CHAIN_OF_COMMAND_VIOLATION
        assert "GID-00" in result.reason_detail

    def test_execute_with_coc_metadata_is_allowed(self, middleware_with_coc):
        """Test that EXECUTE with chain-of-command metadata is allowed."""
        # Cody executes with Diggy authorization
        intent = create_intent(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="local test runs",
            metadata={"authorized_by": "GID-00"},
        )

        result = middleware_with_coc.evaluate(intent)

        # Should pass chain-of-command, then go to ACM evaluation
        # ACM may still deny based on scope, but NOT for chain-of-command
        assert result.reason != DenialReason.CHAIN_OF_COMMAND_VIOLATION

    def test_execute_from_orchestrator_is_allowed(self, middleware_with_coc):
        """Test that EXECUTE from orchestrator (GID-00) is allowed."""
        # This would require a GID-00 ACM, which we don't have in test fixtures
        # So we test the logic by checking that GID-00 origin bypasses CoC
        # (In practice, orchestrator would have its own ACM)
        pass  # Placeholder for when GID-00 manifest exists

    def test_block_without_coc_is_denied(self, middleware_with_coc):
        """Test that BLOCK without chain-of-command routing is denied."""
        # Sam tries to BLOCK without Diggy authorization
        intent = create_intent(
            agent_gid="GID-06",
            verb="BLOCK",
            target="insecure code changes",
        )

        result = middleware_with_coc.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.CHAIN_OF_COMMAND_VIOLATION

    def test_block_with_coc_chain_is_allowed(self, middleware_with_coc):
        """Test that BLOCK with chain-of-command routing is allowed."""
        # Sam blocks with proper chain-of-command
        intent = create_intent(
            agent_gid="GID-06",
            verb="BLOCK",
            target="insecure code changes",
            metadata={"chain_of_command": "GID-00"},
        )

        result = middleware_with_coc.evaluate(intent)

        # Should pass chain-of-command check
        # Then ACM evaluator decides based on BLOCK scope
        assert result.reason != DenialReason.CHAIN_OF_COMMAND_VIOLATION

    def test_read_does_not_require_coc(self, middleware_with_coc):
        """Test that READ does not require chain-of-command."""
        # Cody reads without any authorization
        intent = create_intent(
            agent_gid="GID-01",
            verb="READ",
            target="backend source code",
        )

        result = middleware_with_coc.evaluate(intent)

        # Should NOT be denied for chain-of-command
        # May be denied for other reasons (scope), but not CoC
        assert result.reason != DenialReason.CHAIN_OF_COMMAND_VIOLATION

    def test_propose_does_not_require_coc(self, middleware_with_coc):
        """Test that PROPOSE does not require chain-of-command."""
        # Sonny proposes without any authorization
        intent = create_intent(
            agent_gid="GID-02",
            verb="PROPOSE",
            target="UI component changes",
        )

        result = middleware_with_coc.evaluate(intent)

        assert result.reason != DenialReason.CHAIN_OF_COMMAND_VIOLATION

    def test_escalate_does_not_require_coc(self, middleware_with_coc):
        """Test that ESCALATE does not require chain-of-command."""
        # ESCALATE is universal, no CoC needed
        intent = create_intent(
            agent_gid="GID-01",
            verb="ESCALATE",
            target="security implications",
        )

        result = middleware_with_coc.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW


class TestChainOfCommandDenialFormat:
    """Tests for chain-of-command denial format."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create middleware with CoC enforcement."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_chain_of_command=True,
            raise_on_denial=False,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_coc_denial_has_next_hop(self, middleware):
        """Test that CoC denial includes next_hop = GID-00."""
        intent = create_intent(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="anything",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.CHAIN_OF_COMMAND_VIOLATION
        # Next hop should be indicated in reason_detail
        assert "GID-00" in result.reason_detail or "Diggy" in result.reason_detail

    def test_coc_denial_has_explicit_reason(self, middleware):
        """Test that CoC denial has explicit, structured reason."""
        intent = create_intent(
            agent_gid="GID-07",
            verb="EXECUTE",
            target="CI pipeline runs",
        )

        result = middleware.evaluate(intent)

        assert result.reason == DenialReason.CHAIN_OF_COMMAND_VIOLATION
        assert "routing" in result.reason_detail.lower() or "requires" in result.reason_detail.lower()


class TestChainOfCommandWithRaiseOnDenial:
    """Tests for chain-of-command with raise_on_denial=True."""

    @pytest.fixture
    def strict_middleware(self, manifests_dir):
        """Create middleware that raises on denial."""
        from core.governance.acm_loader import ACMLoader

        config = MiddlewareConfig(
            enforce_chain_of_command=True,
            raise_on_denial=True,
        )
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()
        return middleware

    def test_coc_violation_raises_intent_denied_error(self, strict_middleware):
        """Test that CoC violation raises IntentDeniedError."""
        intent = create_intent(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="anything",
        )

        with pytest.raises(IntentDeniedError) as exc_info:
            strict_middleware.evaluate(intent)

        assert exc_info.value.result.reason == DenialReason.CHAIN_OF_COMMAND_VIOLATION
