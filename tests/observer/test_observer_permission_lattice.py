"""
Observer Permission Lattice Tests — PAC-JEFFREY-P45

Tests for regulated observer access control.
"""

import pytest
from unittest.mock import patch
import os

from core.occ.observer.permission_lattice import (
    ObserverCategory,
    ObserverPermissionLattice,
    ObserverRateLimits,
    ObserverSessionConfig,
    Permission,
    PermissionLevel,
    ResourceType,
    Operation,
    OBSERVER_READ_PERMISSIONS,
    OBSERVER_DENIED_PERMISSIONS,
    REGULATORY_OBSERVER_LATTICE,
    EXTERNAL_AUDITOR_LATTICE,
    COMPLIANCE_OBSERVER_LATTICE,
    DISABLED_OBSERVER_LATTICE,
    get_observer_lattice,
    check_observer_access,
    check_observer_endpoint_access,
    verify_lattice_invariants,
)


class TestObserverPermissionLattice:
    """Tests for ObserverPermissionLattice functionality."""

    def test_regulatory_observer_lattice_defaults(self):
        """Regulatory observer lattice has correct defaults."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        assert lattice.category == ObserverCategory.OBSERVER_REG
        assert lattice.enabled is True
        assert lattice.fail_closed is True

    def test_observer_rate_limits(self):
        """Observer rate limits are configured correctly."""
        limits = ObserverRateLimits()
        
        assert limits.requests_per_minute == 20
        assert limits.requests_per_hour == 300
        assert limits.concurrent_connections == 1
        assert limits.burst_limit == 5
        assert limits.proofpack_downloads_per_day == 50

    def test_read_permissions_granted(self):
        """Read permissions are granted to observers."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        # Timeline read
        assert lattice.check_permission(ResourceType.TIMELINE, Operation.READ)
        assert lattice.check_permission(ResourceType.TIMELINE, Operation.LIST)
        
        # PDO shadow read
        assert lattice.check_permission(ResourceType.PDO_SHADOW, Operation.READ)
        assert lattice.check_permission(ResourceType.PDO_SHADOW, Operation.LIST)
        
        # ProofPack access
        assert lattice.check_permission(ResourceType.PROOFPACK, Operation.READ)
        assert lattice.check_permission(ResourceType.PROOFPACK, Operation.VERIFY)
        assert lattice.check_permission(ResourceType.PROOFPACK, Operation.DOWNLOAD)
        
        # Health
        assert lattice.check_permission(ResourceType.HEALTH, Operation.READ)

    def test_write_permissions_denied(self):
        """Write permissions are denied to observers."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        # PDO write
        assert not lattice.check_permission(ResourceType.PDO_SHADOW, Operation.CREATE)
        assert not lattice.check_permission(ResourceType.PDO_SHADOW, Operation.UPDATE)
        assert not lattice.check_permission(ResourceType.PDO_SHADOW, Operation.DELETE)

    def test_production_data_denied(self):
        """Production data access is denied."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        assert not lattice.check_permission(ResourceType.PDO_PRODUCTION, Operation.READ)
        assert not lattice.check_permission(ResourceType.PDO_PRODUCTION, Operation.LIST)

    def test_kill_switch_view_only(self):
        """Kill-switch is view-only for observers."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        # Can view state
        assert lattice.can_access_kill_switch_state()
        
        # Cannot control (hard-coded false)
        assert not lattice.can_control_kill_switch()
        
        # Control operations denied
        assert not lattice.check_permission(ResourceType.KILL_SWITCH, Operation.CONTROL)
        assert not lattice.check_permission(ResourceType.KILL_SWITCH, Operation.MODIFY)

    def test_settlement_denied(self):
        """Settlement operations are denied."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        assert not lattice.check_permission(ResourceType.SETTLEMENT, Operation.READ)
        assert not lattice.check_permission(ResourceType.SETTLEMENT, Operation.CREATE)
        assert not lattice.check_permission(ResourceType.SETTLEMENT, Operation.CONTROL)

    def test_operator_denied(self):
        """Operator operations are denied."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        assert not lattice.check_permission(ResourceType.OPERATOR, Operation.READ)
        assert not lattice.check_permission(ResourceType.OPERATOR, Operation.MODIFY)
        assert not lattice.check_permission(ResourceType.OPERATOR, Operation.CONTROL)

    def test_fail_closed_behavior(self):
        """Unknown permissions are denied (fail-closed)."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        assert lattice.fail_closed is True
        # Unknown operation
        assert not lattice.check_permission(ResourceType.CONFIG, Operation.READ)

    def test_disabled_lattice_denies_all(self):
        """Disabled lattice denies everything."""
        lattice = DISABLED_OBSERVER_LATTICE
        
        assert lattice.category == ObserverCategory.DISABLED
        assert lattice.enabled is False
        assert not lattice.check_permission(ResourceType.TIMELINE, Operation.READ)
        assert not lattice.check_permission(ResourceType.HEALTH, Operation.READ)


class TestObserverSessionConfig:
    """Tests for observer session configuration."""

    def test_regulatory_session_config(self):
        """Regulatory observer session config is correct."""
        lattice = REGULATORY_OBSERVER_LATTICE
        config = lattice.get_session_config()
        
        assert config.max_session_hours == 8
        assert config.idle_timeout_minutes == 30
        assert config.require_mfa is True
        assert config.allow_token_refresh is False
        assert config.concurrent_sessions == 1

    def test_auditor_session_config(self):
        """External auditor session config is correct."""
        lattice = EXTERNAL_AUDITOR_LATTICE
        config = lattice.get_session_config()
        
        assert config.max_session_hours == 4
        assert config.require_mfa is True

    def test_compliance_session_config(self):
        """Compliance observer session config is correct."""
        lattice = COMPLIANCE_OBSERVER_LATTICE
        config = lattice.get_session_config()
        
        assert config.max_session_hours == 2
        assert config.idle_timeout_minutes == 15


class TestObserverEnvironment:
    """Tests for environment-based config loading."""

    def test_default_is_disabled(self):
        """Default config (no env var) is DISABLED."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CHAINBRIDGE_OBSERVER_MODE", None)
            lattice = get_observer_lattice()
            assert lattice.category == ObserverCategory.DISABLED

    def test_regulatory_env(self):
        """OBSERVER_REG env var loads correct lattice."""
        with patch.dict(os.environ, {"CHAINBRIDGE_OBSERVER_MODE": "OBSERVER_REG"}):
            lattice = get_observer_lattice()
            assert lattice.category == ObserverCategory.OBSERVER_REG
            assert lattice.enabled is True

    def test_auditor_env(self):
        """OBSERVER_AUDIT env var loads correct lattice."""
        with patch.dict(os.environ, {"CHAINBRIDGE_OBSERVER_MODE": "OBSERVER_AUDIT"}):
            lattice = get_observer_lattice()
            assert lattice.category == ObserverCategory.OBSERVER_AUDIT

    def test_invalid_mode_falls_back_to_disabled(self):
        """Invalid mode falls back to DISABLED."""
        with patch.dict(os.environ, {"CHAINBRIDGE_OBSERVER_MODE": "INVALID_MODE"}):
            lattice = get_observer_lattice()
            assert lattice.category == ObserverCategory.DISABLED


class TestObserverEndpointAccess:
    """Tests for endpoint access checks."""

    def test_timeline_read_allowed(self):
        """GET /occ/timeline is allowed for observers."""
        assert check_observer_endpoint_access("OBSERVER_REG", "GET", "/occ/timeline")

    def test_pdo_read_allowed(self):
        """GET /oc/pdo is allowed for observers."""
        assert check_observer_endpoint_access("OBSERVER_REG", "GET", "/oc/pdo")

    def test_proofpack_verify_allowed(self):
        """GET /oc/proofpack/{id}/verify is allowed."""
        assert check_observer_endpoint_access("OBSERVER_REG", "GET", "/oc/proofpack/123/verify")

    def test_health_allowed(self):
        """GET /health is allowed for observers."""
        assert check_observer_endpoint_access("OBSERVER_REG", "GET", "/health")

    def test_kill_switch_state_allowed(self):
        """GET /occ/kill-switch/state is allowed."""
        assert check_observer_endpoint_access("OBSERVER_REG", "GET", "/occ/kill-switch/state")

    def test_kill_switch_control_denied(self):
        """POST kill-switch endpoints are denied."""
        # Note: These endpoints aren't in the map, so they're denied by fail-closed
        assert not check_observer_endpoint_access("OBSERVER_REG", "POST", "/occ/kill-switch/arm")
        assert not check_observer_endpoint_access("OBSERVER_REG", "POST", "/occ/kill-switch/engage")

    def test_disabled_mode_denies_all(self):
        """DISABLED mode denies all access."""
        assert not check_observer_endpoint_access("DISABLED", "GET", "/occ/timeline")
        assert not check_observer_endpoint_access("DISABLED", "GET", "/health")


class TestObserverAccessFunction:
    """Tests for check_observer_access function."""

    def test_timeline_read_access(self):
        """Timeline read access check."""
        assert check_observer_access("OBSERVER_REG", "timeline", "read")

    def test_pdo_shadow_read_access(self):
        """PDO shadow read access check."""
        assert check_observer_access("OBSERVER_REG", "pdo:shadow", "read")

    def test_pdo_production_denied(self):
        """PDO production access denied."""
        assert not check_observer_access("OBSERVER_REG", "pdo:production", "read")

    def test_kill_switch_view_access(self):
        """Kill-switch view state access check."""
        assert check_observer_access("OBSERVER_REG", "kill_switch", "view_state")

    def test_kill_switch_control_denied(self):
        """Kill-switch control access denied."""
        assert not check_observer_access("OBSERVER_REG", "kill_switch", "control")

    def test_invalid_resource_denied(self):
        """Invalid resource is denied."""
        assert not check_observer_access("OBSERVER_REG", "invalid_resource", "read")


class TestLatticeInvariants:
    """Tests for governance invariants."""

    def test_no_write_paths_invariant(self):
        """INV-OBS-001: No write paths."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert results["INV-OBS-001_NO_WRITE_PATHS"] is True

    def test_no_control_paths_invariant(self):
        """INV-OBS-002: No control paths."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert results["INV-OBS-002_NO_CONTROL_PATHS"] is True

    def test_production_isolation_invariant(self):
        """INV-OBS-003: Production isolation."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert results["INV-OBS-003_PRODUCTION_ISOLATION"] is True

    def test_kill_switch_no_control_invariant(self):
        """INV-OBS-004: Kill-switch no control."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert results["INV-OBS-004_KILL_SWITCH_NO_CONTROL"] is True

    def test_fail_closed_invariant(self):
        """INV-OBS-005: Fail closed."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert results["INV-OBS-005_FAIL_CLOSED"] is True

    def test_audit_enabled_invariant(self):
        """INV-OBS-006: Audit enabled."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert results["INV-OBS-006_AUDIT_ENABLED"] is True

    def test_all_invariants_pass(self):
        """All invariants pass for regulatory observer."""
        results = verify_lattice_invariants(REGULATORY_OBSERVER_LATTICE)
        assert all(results.values())


class TestLatticeImmutability:
    """Tests for lattice immutability."""

    def test_lattice_is_frozen(self):
        """Lattice is frozen (immutable)."""
        lattice = REGULATORY_OBSERVER_LATTICE
        
        with pytest.raises(Exception):
            lattice.enabled = False

    def test_rate_limits_frozen(self):
        """Rate limits are frozen."""
        limits = ObserverRateLimits()
        
        with pytest.raises(Exception):
            limits.requests_per_minute = 1000

    def test_session_config_frozen(self):
        """Session config is frozen."""
        config = ObserverSessionConfig(max_session_hours=8)
        
        with pytest.raises(Exception):
            config.max_session_hours = 24


class TestProofPackAccess:
    """Tests for proofpack access."""

    def test_can_access_proofpack(self):
        """Observer can access proofpacks."""
        lattice = REGULATORY_OBSERVER_LATTICE
        assert lattice.can_access_proofpack()

    def test_can_download_proofpack(self):
        """Observer can download proofpacks."""
        lattice = REGULATORY_OBSERVER_LATTICE
        assert lattice.can_download_proofpack()

    def test_can_verify_proofpack(self):
        """Observer can verify proofpacks."""
        lattice = REGULATORY_OBSERVER_LATTICE
        assert lattice.can_verify_proofpack()
