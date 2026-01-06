"""
Pilot Configuration Tests — PAC-JEFFREY-P44

Tests for external pilot mode configuration and guards.
"""

import pytest
from unittest.mock import patch
import os

from core.occ.pilot.config import (
    PilotMode,
    PDOClassification,
    PilotConfig,
    PilotRateLimits,
    EXTERNAL_PILOT_CONFIG,
    INTERNAL_PILOT_CONFIG,
    DEMO_CONFIG,
    DISABLED_CONFIG,
    get_pilot_config,
    check_pilot_endpoint_access,
    is_claim_forbidden,
    FORBIDDEN_PILOT_CLAIMS,
)


class TestPilotConfig:
    """Tests for PilotConfig functionality."""

    def test_external_pilot_config_defaults(self):
        """External pilot config has correct defaults."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.mode == PilotMode.EXTERNAL_PILOT
        assert config.enabled is True
        assert PDOClassification.SHADOW in config.visible_classifications
        assert PDOClassification.PRODUCTION not in config.visible_classifications

    def test_pilot_rate_limits(self):
        """Rate limits are configured correctly."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.rate_limits.requests_per_minute == 30
        assert config.rate_limits.requests_per_hour == 500
        assert config.rate_limits.concurrent_connections == 5
        assert config.rate_limits.burst_limit == 10

    def test_permitted_operations(self):
        """Permitted operations are correct."""
        config = EXTERNAL_PILOT_CONFIG
        
        # Permitted
        assert config.is_operation_permitted("pdo:read:shadow")
        assert config.is_operation_permitted("timeline:read")
        assert config.is_operation_permitted("health:read")
        
        # Denied
        assert not config.is_operation_permitted("pdo:create")
        assert not config.is_operation_permitted("pdo:update")
        assert not config.is_operation_permitted("pdo:delete")
        assert not config.is_operation_permitted("pdo:read:production")

    def test_kill_switch_denied_for_pilots(self):
        """Kill-switch operations are denied for pilots."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert not config.is_operation_permitted("kill_switch:arm")
        assert not config.is_operation_permitted("kill_switch:engage")
        assert not config.is_operation_permitted("kill_switch:disengage")

    def test_operator_wildcard_denied(self):
        """Operator wildcard operations are denied."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert not config.is_operation_permitted("operator:anything")
        assert not config.is_operation_permitted("operator:modify")
        assert not config.is_operation_permitted("config:update")

    def test_fail_closed_behavior(self):
        """Unknown operations are denied (fail-closed)."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.fail_closed is True
        assert not config.is_operation_permitted("unknown:operation")
        assert not config.is_operation_permitted("some:random:thing")

    def test_classification_visibility(self):
        """Classification visibility is correct."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.can_view_classification(PDOClassification.SHADOW)
        assert not config.can_view_classification(PDOClassification.PRODUCTION)

    def test_disabled_config(self):
        """Disabled config denies everything."""
        config = DISABLED_CONFIG
        
        assert config.mode == PilotMode.DISABLED
        assert config.enabled is False


class TestPilotConfigEnvironment:
    """Tests for environment-based config loading."""

    def test_default_is_disabled(self):
        """Default config (no env var) is DISABLED."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing CHAINBRIDGE_PILOT_MODE
            os.environ.pop("CHAINBRIDGE_PILOT_MODE", None)
            config = get_pilot_config()
            assert config.mode == PilotMode.DISABLED

    def test_external_pilot_env(self):
        """EXTERNAL_PILOT env var loads correct config."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "EXTERNAL_PILOT"}):
            config = get_pilot_config()
            assert config.mode == PilotMode.EXTERNAL_PILOT
            assert config.enabled is True

    def test_invalid_mode_falls_back_to_disabled(self):
        """Invalid mode falls back to DISABLED."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "INVALID_MODE"}):
            config = get_pilot_config()
            assert config.mode == PilotMode.DISABLED


class TestEndpointAccess:
    """Tests for endpoint access checks."""

    def test_read_pdo_allowed(self):
        """GET /oc/pdo is allowed for pilots."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "EXTERNAL_PILOT"}):
            assert check_pilot_endpoint_access("GET", "/oc/pdo")

    def test_create_pdo_denied(self):
        """POST /oc/pdo is denied for pilots."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "EXTERNAL_PILOT"}):
            assert not check_pilot_endpoint_access("POST", "/oc/pdo")

    def test_health_allowed(self):
        """GET /health is allowed for pilots."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "EXTERNAL_PILOT"}):
            assert check_pilot_endpoint_access("GET", "/health")

    def test_kill_switch_denied(self):
        """Kill-switch endpoints are denied."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "EXTERNAL_PILOT"}):
            assert not check_pilot_endpoint_access("POST", "/occ/kill-switch/arm")
            assert not check_pilot_endpoint_access("POST", "/occ/kill-switch/engage")

    def test_disabled_mode_denies_all(self):
        """DISABLED mode denies all access."""
        with patch.dict(os.environ, {"CHAINBRIDGE_PILOT_MODE": "DISABLED"}):
            assert not check_pilot_endpoint_access("GET", "/oc/pdo")
            assert not check_pilot_endpoint_access("GET", "/health")


class TestForbiddenClaims:
    """Tests for forbidden claims detection."""

    def test_production_ready_forbidden(self):
        """'Production-ready' claims are forbidden."""
        assert is_claim_forbidden("ChainBridge is production-ready")
        assert is_claim_forbidden("Our platform is production ready now")

    def test_certification_claims_forbidden(self):
        """Certification claims are forbidden."""
        assert is_claim_forbidden("ChainBridge is auditor-certified")
        assert is_claim_forbidden("We are SOC2 certified")

    def test_autonomy_claims_forbidden(self):
        """Autonomy claims are forbidden."""
        assert is_claim_forbidden("ChainBridge provides autonomous compliance")
        assert is_claim_forbidden("ChainBridge replaces compliance teams")

    def test_safe_claims_allowed(self):
        """Safe claims are not flagged."""
        assert not is_claim_forbidden("ChainBridge assists operators")
        assert not is_claim_forbidden("We are evaluating the platform")
        assert not is_claim_forbidden("This is a pilot program")

    def test_forbidden_claims_list_populated(self):
        """Forbidden claims list is populated."""
        assert len(FORBIDDEN_PILOT_CLAIMS) >= 8


class TestPilotModeIntegrity:
    """Tests for pilot mode integrity constraints."""

    def test_config_is_immutable(self):
        """PilotConfig is frozen (immutable)."""
        config = EXTERNAL_PILOT_CONFIG
        
        with pytest.raises(Exception):
            config.enabled = False

    def test_rate_limits_immutable(self):
        """Rate limits are frozen."""
        limits = PilotRateLimits()
        
        with pytest.raises(Exception):
            limits.requests_per_minute = 1000

    def test_token_settings(self):
        """Token settings are correct."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.token_max_lifetime_hours == 24
        assert config.token_auto_refresh is False
        assert config.token_audience == "chainbridge-pilot"

    def test_audit_settings(self):
        """Audit settings are enabled."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.audit_all_requests is True
        assert config.audit_include_ip_hash is True

    def test_safety_settings(self):
        """Safety settings are enabled."""
        config = EXTERNAL_PILOT_CONFIG
        
        assert config.fail_closed is True
        assert config.hide_production_pdos is True
