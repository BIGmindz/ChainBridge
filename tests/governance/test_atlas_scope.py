"""
Atlas Scope Tests — PAC-GOV-ATLAS-01

Tests for Atlas (GID-11) domain boundary enforcement.
Verifies that Atlas cannot modify frontend, backend, or service code.

Test Requirements:
- test_atlas_cannot_modify_frontend
- test_atlas_cannot_modify_backend
- test_atlas_can_modify_docs
- test_atlas_can_modify_manifests
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.governance.acm_evaluator import ACMDecision, DenialReason
from core.governance.atlas_scope import (
    ATLAS_GID,
    AtlasScope,
    AtlasScopeInvalidError,
    AtlasScopeNotFoundError,
    get_atlas_scope,
    is_atlas,
    load_atlas_scope,
    reset_atlas_scope,
    set_atlas_scope,
)
from core.governance.intent_schema import AgentIntent, IntentVerb, create_intent
from gateway.alex_middleware import ALEXMiddleware, ALEXMiddlewareError, IntentDeniedError, MiddlewareConfig

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def atlas_scope() -> AtlasScope:
    """Create a test Atlas scope."""
    return AtlasScope(
        version="1.0.0",
        forbidden_paths=(
            "ChainBridge/chainboard-ui/**",
            "src/components/**",
            "src/types/**",
            "core/**",
            "gateway/**",
            "services/**",
            "api/**",
        ),
        allowed_paths=(
            "docs/**",
            "manifests/**",
            ".github/**",
        ),
        governance_lock=True,
    )


@pytest.fixture
def middleware_with_atlas_scope(atlas_scope: AtlasScope) -> ALEXMiddleware:
    """Create middleware with Atlas scope enabled."""
    config = MiddlewareConfig(
        enforce_atlas_scope=True,
        enforce_drcp=False,  # Disable to isolate Atlas tests
        enforce_dcc=False,  # Disable to isolate Atlas tests
        require_checklist=False,  # Disable to isolate Atlas tests
        raise_on_denial=False,
    )
    middleware = ALEXMiddleware(config=config)

    # Manually set the scope and mark as initialized
    middleware._atlas_scope = atlas_scope
    middleware._evaluator = MagicMock()
    middleware._evaluator.evaluate.return_value = MagicMock(
        decision=ACMDecision.ALLOW,
        agent_gid="GID-11",
        intent_verb="PROPOSE",
        intent_target="docs/test.md",
        reason=None,
        reason_detail=None,
        acm_version="1.0.0",
        timestamp="2025-12-17T00:00:00Z",
        correlation_id=None,
        next_hop=None,
        correction_plan=None,
    )
    middleware._initialized = True

    return middleware


# ============================================================
# UNIT TESTS — is_atlas()
# ============================================================


class TestIsAtlas:
    """Tests for is_atlas() function."""

    def test_atlas_gid_returns_true(self) -> None:
        """GID-11 is Atlas."""
        assert is_atlas("GID-11") is True

    def test_other_gids_return_false(self) -> None:
        """Other GIDs are not Atlas."""
        assert is_atlas("GID-00") is False
        assert is_atlas("GID-01") is False
        assert is_atlas("GID-02") is False
        assert is_atlas("GID-08") is False

    def test_invalid_gid_returns_false(self) -> None:
        """Invalid GIDs are not Atlas."""
        assert is_atlas("") is False
        assert is_atlas("ATLAS") is False
        assert is_atlas("gid-11") is False  # Case sensitive


# ============================================================
# UNIT TESTS — AtlasScope.is_path_forbidden()
# ============================================================


class TestAtlasScopePathCheck:
    """Tests for AtlasScope path checking."""

    def test_frontend_paths_forbidden(self, atlas_scope: AtlasScope) -> None:
        """Frontend paths are forbidden for Atlas."""
        assert atlas_scope.is_path_forbidden("ChainBridge/chainboard-ui/src/App.tsx") is not None
        assert atlas_scope.is_path_forbidden("ChainBridge/chainboard-ui/src/components/Button.tsx") is not None
        assert atlas_scope.is_path_forbidden("src/components/Header.tsx") is not None
        assert atlas_scope.is_path_forbidden("src/types/approval.ts") is not None

    def test_backend_paths_forbidden(self, atlas_scope: AtlasScope) -> None:
        """Backend paths are forbidden for Atlas."""
        assert atlas_scope.is_path_forbidden("core/governance/acm_evaluator.py") is not None
        assert atlas_scope.is_path_forbidden("gateway/alex_middleware.py") is not None
        assert atlas_scope.is_path_forbidden("services/payment.py") is not None
        assert atlas_scope.is_path_forbidden("api/server.py") is not None

    def test_docs_paths_allowed(self, atlas_scope: AtlasScope) -> None:
        """Docs paths are allowed for Atlas."""
        assert atlas_scope.is_path_forbidden("docs/README.md") is None
        assert atlas_scope.is_path_forbidden("docs/governance/ATLAS_SCOPE_LOCK.yaml") is None

    def test_manifests_paths_allowed(self, atlas_scope: AtlasScope) -> None:
        """Manifest paths are allowed for Atlas."""
        assert atlas_scope.is_path_forbidden("manifests/agent_acm.yaml") is None
        assert atlas_scope.is_path_forbidden(".github/workflows/ci.yml") is None

    def test_path_normalization(self, atlas_scope: AtlasScope) -> None:
        """Paths are normalized for comparison."""
        # Leading slashes are stripped
        assert atlas_scope.is_path_forbidden("/core/test.py") is not None
        # Backslashes are converted
        assert atlas_scope.is_path_forbidden("core\\test.py") is not None


# ============================================================
# UNIT TESTS — load_atlas_scope()
# ============================================================


class TestLoadAtlasScope:
    """Tests for load_atlas_scope() function."""

    def test_load_real_scope_file(self) -> None:
        """Load the real Atlas scope file."""
        reset_atlas_scope()
        scope = load_atlas_scope()

        assert scope.version == "1.0.0"
        assert scope.governance_lock is True
        assert len(scope.forbidden_paths) > 0
        assert len(scope.allowed_paths) > 0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing scope file raises AtlasScopeNotFoundError."""
        with pytest.raises(AtlasScopeNotFoundError):
            load_atlas_scope(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML raises AtlasScopeInvalidError."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{{invalid yaml}}")

        with pytest.raises(AtlasScopeInvalidError):
            load_atlas_scope(bad_file)

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        """Missing version field raises AtlasScopeInvalidError."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("forbidden_paths: []\nallowed_paths: []")

        with pytest.raises(AtlasScopeInvalidError, match="missing 'version'"):
            load_atlas_scope(bad_file)


# ============================================================
# INTEGRATION TESTS — Middleware Enforcement
# ============================================================


class TestAtlasCannotModifyFrontend:
    """Tests that Atlas cannot modify frontend code."""

    def test_atlas_denied_on_chainboard_ui(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting ChainBoard UI files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,  # Use PROPOSE for write-like operations
            target="ChainBridge/chainboard-ui/src/App.tsx",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION
        assert "GID-11" in result.reason_detail
        assert "domain-owned" in result.reason_detail.lower()

    def test_atlas_denied_on_components(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting component files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="src/components/approval/HumanApprovalModal.tsx",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION

    def test_atlas_denied_on_types(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting type files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="src/types/approval.ts",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION


class TestAtlasCannotModifyBackend:
    """Tests that Atlas cannot modify backend code."""

    def test_atlas_denied_on_core(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting core files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="core/governance/new_module.py",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION

    def test_atlas_denied_on_gateway(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting gateway files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="gateway/alex_middleware.py",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION

    def test_atlas_denied_on_services(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting services files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="services/payment/handler.py",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION

    def test_atlas_denied_on_api(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas denied when targeting API files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="api/server.py",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION


class TestAtlasCanModifyDocs:
    """Tests that Atlas CAN modify docs."""

    def test_atlas_allowed_on_docs(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas allowed when targeting docs files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="docs/governance/ATLAS_SCOPE_LOCK.yaml",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        # Should pass Atlas check and hit the mock evaluator
        assert result.decision == ACMDecision.ALLOW

    def test_atlas_allowed_on_readme(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas allowed when targeting README files in docs."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="docs/README.md",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW


class TestAtlasCanModifyManifests:
    """Tests that Atlas CAN modify manifests."""

    def test_atlas_allowed_on_github(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas allowed when targeting .github files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target=".github/workflows/ci.yml",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW

    def test_atlas_allowed_on_manifests(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas allowed when targeting manifest files."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="manifests/agent_acm.yaml",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        assert result.decision == ACMDecision.ALLOW


class TestOtherAgentsNotAffected:
    """Tests that other agents are not affected by Atlas scope."""

    def test_sonny_can_modify_frontend(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Sonny (GID-02) can modify frontend (Atlas check does not apply)."""
        intent = create_intent(
            agent_gid="GID-02",  # Sonny
            verb=IntentVerb.PROPOSE,
            target="ChainBridge/chainboard-ui/src/App.tsx",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        # Should pass Atlas check (not GID-11) and hit mock evaluator
        assert result.decision == ACMDecision.ALLOW

    def test_diggy_can_read_anywhere(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Diggy (GID-00) can read anywhere (Atlas check does not apply)."""
        intent = create_intent(
            agent_gid="GID-00",  # Diggy
            verb=IntentVerb.READ,
            target="core/governance/acm_evaluator.py",
        )

        result = middleware_with_atlas_scope.evaluate(intent)

        # Should pass Atlas check (not GID-11)
        assert result.decision == ACMDecision.ALLOW


class TestAuditLogging:
    """Tests that Atlas violations are audit logged."""

    def test_atlas_violation_logged(self, middleware_with_atlas_scope: ALEXMiddleware) -> None:
        """Atlas domain violation is logged to audit trail."""
        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="core/test.py",
        )

        with patch.object(middleware_with_atlas_scope._audit, "log_atlas_domain_violation") as mock_log:
            result = middleware_with_atlas_scope.evaluate(intent)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs["agent_gid"] == "GID-11"
            assert "core" in call_args.kwargs["target_path"]


class TestSystemFailsClosed:
    """Tests that system fails closed on missing scope file."""

    def test_middleware_refuses_boot_without_scope(self) -> None:
        """Middleware refuses to initialize if scope file missing."""
        config = MiddlewareConfig(
            enforce_atlas_scope=True,
            require_checklist=False,
            enforce_dcc=False,
        )
        middleware = ALEXMiddleware(config=config)

        # Mock the scope file as not found
        with patch(
            "gateway.alex_middleware.load_atlas_scope",
            side_effect=AtlasScopeNotFoundError("File not found"),
        ):
            with pytest.raises(ALEXMiddlewareError, match="scope"):
                middleware.initialize()


class TestCorrectionPlanAttached:
    """Tests that correction plan is attached to Atlas violations."""

    def test_correction_plan_on_atlas_violation(self) -> None:
        """Atlas violation includes correction plan when DCC enabled."""
        # This test uses the real correction map
        reset_atlas_scope()

        config = MiddlewareConfig(
            enforce_atlas_scope=True,
            enforce_dcc=True,
            enforce_drcp=False,
            require_checklist=False,
            raise_on_denial=False,
        )
        middleware = ALEXMiddleware(config=config)

        try:
            middleware.initialize()
        except Exception:
            pytest.skip("Cannot initialize middleware (missing dependencies)")

        intent = create_intent(
            agent_gid="GID-11",
            verb=IntentVerb.PROPOSE,
            target="core/test.py",
        )

        result = middleware.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.ATLAS_DOMAIN_VIOLATION
        assert result.correction_plan is not None
        assert "constraints" in result.correction_plan.get("correction_plan", {})
