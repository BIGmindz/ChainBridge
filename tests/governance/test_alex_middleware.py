"""Tests for ALEX Middleware — Task 4 & 5 of PAC-ACM-02.

These tests verify:
- Gateway intercept behavior
- Fail-closed on initialization failure
- Audit log emission for every decision
- Structured denial handling
"""

import json
from pathlib import Path

import pytest

from core.governance.acm_evaluator import ACMDecision, DenialReason
from core.governance.acm_loader import ACMLoader
from core.governance.intent_schema import IntentVerb, create_intent
from gateway.alex_middleware import ALEXMiddleware, ALEXMiddlewareError, GovernanceAuditLogger, IntentDeniedError, MiddlewareConfig


class TestMiddlewareInitialization:
    """Test middleware initialization and fail-closed behavior."""

    def test_initialize_with_valid_manifests(self, manifests_dir):
        """Test successful initialization with valid manifests."""
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(loader=loader)

        middleware.initialize()

        assert middleware.is_initialized()

    def test_initialize_fails_with_missing_manifests(self, tmp_path):
        """Test initialization fails with missing manifests directory."""
        loader = ACMLoader(tmp_path / "nonexistent")
        middleware = ALEXMiddleware(loader=loader)

        with pytest.raises(ALEXMiddlewareError) as exc_info:
            middleware.initialize()

        assert "startup failed" in str(exc_info.value).lower()

    def test_initialize_fails_with_invalid_manifest(self, temp_manifests_dir):
        """Test initialization fails with invalid manifest."""
        # Create invalid manifest (missing governance lock)
        (temp_manifests_dir / "GID-99_Invalid.yaml").write_text(
            """
agent_id: "Invalid"
gid: "GID-99"
role: "Test"
color: "Test"
version: "1.0.0"
capabilities:
  read: []
  propose: []
  execute: []
  block: []
  escalate: []
# Missing governance lock marker
"""
        )
        loader = ACMLoader(temp_manifests_dir)
        middleware = ALEXMiddleware(loader=loader)

        with pytest.raises(ALEXMiddlewareError):
            middleware.initialize()

    def test_evaluate_before_initialize_raises(self, manifests_dir):
        """Test evaluate() raises if called before initialize()."""
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(loader=loader)

        intent = create_intent("GID-01", "READ", "test")

        with pytest.raises(ALEXMiddlewareError) as exc_info:
            middleware.evaluate(intent)

        assert "not initialized" in str(exc_info.value).lower()


class TestMiddlewareEvaluation:
    """Test middleware evaluation behavior."""

    def test_allow_returns_result(self, manifests_dir):
        """Test allowed intent returns ALLOW result."""
        loader = ACMLoader(manifests_dir)
        config = MiddlewareConfig(raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        intent = create_intent("GID-01", "ESCALATE", "test")
        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_deny_raises_by_default(self, manifests_dir):
        """Test denied intent raises IntentDeniedError by default."""
        loader = ACMLoader(manifests_dir)
        # Disable CoC enforcement to test ACM-level denial
        config = MiddlewareConfig(enforce_chain_of_command=False)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        intent = create_intent("GID-01", "BLOCK", "anything")

        with pytest.raises(IntentDeniedError) as exc_info:
            middleware.evaluate(intent)

        assert exc_info.value.result.decision == ACMDecision.DENY
        assert exc_info.value.result.reason == DenialReason.BLOCK_NOT_PERMITTED

    def test_deny_returns_result_when_configured(self, manifests_dir):
        """Test denied intent returns result when raise_on_denial=False."""
        loader = ACMLoader(manifests_dir)
        # Disable CoC enforcement to test ACM-level denial
        config = MiddlewareConfig(raise_on_denial=False, enforce_chain_of_command=False)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        intent = create_intent("GID-01", "BLOCK", "anything")
        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY


class TestMiddlewareGuardMethod:
    """Test middleware guard() convenience method."""

    def test_guard_with_string_verb(self, manifests_dir):
        """Test guard() accepts string verb."""
        loader = ACMLoader(manifests_dir)
        config = MiddlewareConfig(raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        result = middleware.guard("GID-01", "ESCALATE", "test")

        assert result.decision == ACMDecision.ALLOW

    def test_guard_with_enum_verb(self, manifests_dir):
        """Test guard() accepts IntentVerb enum."""
        loader = ACMLoader(manifests_dir)
        config = MiddlewareConfig(raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        result = middleware.guard("GID-01", IntentVerb.ESCALATE, "test")

        assert result.decision == ACMDecision.ALLOW

    def test_guard_with_scope(self, manifests_dir):
        """Test guard() handles scope parameter."""
        loader = ACMLoader(manifests_dir)
        config = MiddlewareConfig(raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader)
        middleware.initialize()

        result = middleware.guard("GID-01", "READ", "backend", scope="source.code")

        assert result.decision == ACMDecision.ALLOW


class TestAuditLogging:
    """Test audit log emission."""

    def test_audit_logger_creates_file(self, tmp_path):
        """Test audit logger creates log file."""
        log_file = tmp_path / "logs" / "test.log"
        logger = GovernanceAuditLogger(log_file)

        # Log file parent should be created
        assert log_file.parent.exists()

    def test_decisions_are_logged(self, manifests_dir, tmp_path):
        """Test all decisions are logged when configured."""
        log_file = tmp_path / "governance.log"
        loader = ACMLoader(manifests_dir)
        audit_logger = GovernanceAuditLogger(log_file)
        config = MiddlewareConfig(log_all_decisions=True, raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader, audit_logger=audit_logger)
        middleware.initialize()

        # Make some evaluations
        middleware.guard("GID-01", "ESCALATE", "test1")
        middleware.guard("GID-01", "READ", "backend source code")
        middleware.guard("GID-01", "BLOCK", "anything")  # Will be denied

        # Check log file contains all decisions
        log_content = log_file.read_text()
        lines = [line for line in log_content.strip().split("\n") if line]

        # Should have startup + 3 decisions = at least 3 decision lines
        decision_lines = [line for line in lines if '"decision"' in line]
        assert len(decision_lines) >= 3

    def test_denial_always_logged(self, manifests_dir, tmp_path):
        """Test denials are always logged even if log_all=False."""
        log_file = tmp_path / "governance.log"
        loader = ACMLoader(manifests_dir)
        audit_logger = GovernanceAuditLogger(log_file)
        config = MiddlewareConfig(log_all_decisions=False, raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader, audit_logger=audit_logger)
        middleware.initialize()

        # Make a denial
        middleware.guard("GID-01", "BLOCK", "anything")

        # Check log file contains the denial
        log_content = log_file.read_text()
        assert '"DENY"' in log_content

    def test_audit_record_format(self, manifests_dir, tmp_path):
        """Test audit record has correct JSON format."""
        log_file = tmp_path / "governance.log"
        loader = ACMLoader(manifests_dir)
        audit_logger = GovernanceAuditLogger(log_file)
        config = MiddlewareConfig(log_all_decisions=True, raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader, audit_logger=audit_logger)
        middleware.initialize()

        middleware.guard("GID-01", "READ", "backend source code")

        # Parse last line as JSON
        log_content = log_file.read_text().strip()
        last_line = [line for line in log_content.split("\n") if '"decision"' in line][-1]
        record = json.loads(last_line)

        assert "agent_gid" in record
        assert "intent" in record
        assert "decision" in record
        assert "timestamp" in record


class TestMiddlewareAcceptanceCriteria:
    """Test PAC-ACM-02 acceptance criteria."""

    @pytest.fixture
    def middleware(self, manifests_dir):
        """Create initialized middleware for testing.

        Note: CoC enforcement is disabled for these tests to isolate
        ACM-level capability evaluation. CoC tests are in test_chain_of_command.py.
        """
        loader = ACMLoader(manifests_dir)
        config = MiddlewareConfig(
            raise_on_denial=False,
            enforce_chain_of_command=False,  # Test ACM logic, not CoC
        )
        mw = ALEXMiddleware(config=config, loader=loader)
        mw.initialize()
        return mw

    def test_gateway_rejects_unpermitted_intent(self, middleware):
        """✅ Gateway rejects any intent not explicitly allowed."""
        # Cody trying to BLOCK (not permitted)
        result = middleware.guard("GID-01", "BLOCK", "anything")
        assert result.decision == ACMDecision.DENY

        # Unknown agent
        result = middleware.guard("GID-99", "READ", "anything")
        assert result.decision == ACMDecision.DENY

    def test_execute_without_permission_blocked(self, middleware):
        """✅ EXECUTE without EXECUTE permission is blocked."""
        # Sam has empty execute list
        result = middleware.guard("GID-06", "EXECUTE", "anything")
        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.EXECUTE_NOT_PERMITTED

        # ALEX has empty execute list
        result = middleware.guard("GID-08", "EXECUTE", "anything")
        assert result.decision == ACMDecision.DENY

    def test_read_propose_cannot_mutate(self):
        """✅ READ/PROPOSE cannot mutate state (verified by is_mutating())."""
        from core.governance.intent_schema import AgentIntent, IntentVerb

        read_intent = AgentIntent(agent_gid="GID-01", verb=IntentVerb.READ, target="test")
        assert not read_intent.is_mutating()

        propose_intent = AgentIntent(agent_gid="GID-01", verb=IntentVerb.PROPOSE, target="test")
        assert not propose_intent.is_mutating()

        execute_intent = AgentIntent(agent_gid="GID-01", verb=IntentVerb.EXECUTE, target="test")
        assert execute_intent.is_mutating()

    def test_block_only_for_sam_alex(self, middleware):
        """✅ BLOCK only works for Sam/ALEX."""
        # Sam can block
        result = middleware.guard("GID-06", "BLOCK", "insecure code")
        assert result.decision == ACMDecision.ALLOW

        # ALEX can block
        result = middleware.guard("GID-08", "BLOCK", "governance violations")
        assert result.decision == ACMDecision.ALLOW

        # Cody cannot block
        result = middleware.guard("GID-01", "BLOCK", "anything")
        assert result.decision == ACMDecision.DENY

        # Sonny cannot block
        result = middleware.guard("GID-02", "BLOCK", "anything")
        assert result.decision == ACMDecision.DENY

        # Dan cannot block
        result = middleware.guard("GID-07", "BLOCK", "anything")
        assert result.decision == ACMDecision.DENY

    def test_escalate_always_allowed(self, middleware):
        """✅ ESCALATE always allowed."""
        for gid in ["GID-01", "GID-02", "GID-06", "GID-07", "GID-08"]:
            result = middleware.guard(gid, "ESCALATE", "any target")
            assert result.decision == ACMDecision.ALLOW, f"ESCALATE failed for {gid}"

    def test_audit_log_emitted_for_every_decision(self, manifests_dir, tmp_path):
        """✅ Audit log emitted for every decision."""
        log_file = tmp_path / "audit.log"
        loader = ACMLoader(manifests_dir)
        audit_logger = GovernanceAuditLogger(log_file)
        config = MiddlewareConfig(log_all_decisions=True, raise_on_denial=False)
        middleware = ALEXMiddleware(config=config, loader=loader, audit_logger=audit_logger)
        middleware.initialize()

        # Make 5 evaluations
        middleware.guard("GID-01", "ESCALATE", "test1")
        middleware.guard("GID-01", "READ", "backend source code")
        middleware.guard("GID-06", "BLOCK", "insecure code")
        middleware.guard("GID-01", "BLOCK", "anything")  # Denied
        middleware.guard("GID-08", "EXECUTE", "anything")  # Denied

        # Count decision records
        log_content = log_file.read_text()
        decision_count = log_content.count('"decision"')
        assert decision_count >= 5

    def test_system_fails_closed_on_invalid_acm(self, tmp_path):
        """✅ System fails closed if ACM missing or invalid."""
        # Missing manifests directory
        loader = ACMLoader(tmp_path / "missing")
        middleware = ALEXMiddleware(loader=loader)

        with pytest.raises(ALEXMiddlewareError):
            middleware.initialize()

        # Invalid manifest
        manifests = tmp_path / "manifests"
        manifests.mkdir()
        (manifests / "GID-99_Bad.yaml").write_text("invalid: yaml: structure")

        loader = ACMLoader(manifests)
        middleware = ALEXMiddleware(loader=loader)

        with pytest.raises(ALEXMiddlewareError):
            middleware.initialize()
