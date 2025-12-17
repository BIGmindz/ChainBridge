"""Tests for ALEX Middleware Checklist Integration — PAC-GOV-VAL-01.

These tests verify that ALEX refuses to start without a valid checklist:
- Missing checklist = startup refused
- Invalid checklist = startup refused
- Version mismatch = startup refused
"""

import tempfile
from pathlib import Path

import pytest

from core.governance.acm_loader import ACMLoader
from core.governance.checklist_loader import ChecklistLoader
from gateway.alex_middleware import ALEXMiddleware, ALEXMiddlewareError, ChecklistEnforcementError, MiddlewareConfig


class TestChecklistHardDependency:
    """Tests for checklist as a hard dependency."""

    def test_middleware_refuses_to_start_without_checklist(self, manifests_dir, tmp_path):
        """Test that ALEX refuses to start if checklist is missing."""
        # Point to a nonexistent checklist
        fake_checklist_path = tmp_path / "nonexistent" / "checklist.yaml"
        checklist_loader = ChecklistLoader(fake_checklist_path)

        config = MiddlewareConfig(require_checklist=True)
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(
            config=config,
            loader=loader,
            checklist_loader=checklist_loader,
        )

        with pytest.raises(ChecklistEnforcementError) as exc_info:
            middleware.initialize()

        assert "REFUSED" in str(exc_info.value)
        assert "checklist" in str(exc_info.value).lower()

    def test_middleware_starts_without_checklist_when_disabled(self, manifests_dir, tmp_path):
        """Test that middleware starts if checklist is disabled."""
        # Point to a nonexistent checklist, but disable requirement
        fake_checklist_path = tmp_path / "nonexistent" / "checklist.yaml"
        checklist_loader = ChecklistLoader(fake_checklist_path)

        config = MiddlewareConfig(require_checklist=False)
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(
            config=config,
            loader=loader,
            checklist_loader=checklist_loader,
        )

        # Should not raise
        middleware.initialize()
        assert middleware.is_initialized()
        assert not middleware.has_checklist()

    def test_middleware_loads_checklist_on_startup(self, manifests_dir):
        """Test that middleware loads checklist during initialization."""
        config = MiddlewareConfig(require_checklist=True)
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(config=config, loader=loader)

        middleware.initialize()

        assert middleware.has_checklist()
        checklist = middleware.get_checklist()
        assert checklist is not None
        assert checklist.version == "1.0.0"


class TestChecklistVersionEnforcement:
    """Tests for checklist version enforcement on startup."""

    def test_middleware_refuses_incompatible_version(self, manifests_dir, tmp_path):
        """Test that ALEX refuses to start with incompatible checklist version."""
        # Create a checklist with version below minimum
        old_checklist = tmp_path / "old_checklist.yaml"
        old_checklist.write_text(
            """
version: "0.5.0"
minimum_compatible_version: "1.0.0"
status: "GOVERNANCE-LOCKED"
enforced_by: "GID-08"
required_checks: []
failure_mode: "DENY"
"""
        )

        checklist_loader = ChecklistLoader(old_checklist)
        config = MiddlewareConfig(require_checklist=True)
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(
            config=config,
            loader=loader,
            checklist_loader=checklist_loader,
        )

        with pytest.raises(ChecklistEnforcementError) as exc_info:
            middleware.initialize()

        assert "version" in str(exc_info.value).lower()


class TestChecklistValidationOnStartup:
    """Tests for checklist validation on startup."""

    def test_middleware_refuses_invalid_checklist(self, manifests_dir, tmp_path):
        """Test that ALEX refuses to start with invalid checklist structure."""
        # Create a checklist missing required fields
        invalid_checklist = tmp_path / "invalid_checklist.yaml"
        invalid_checklist.write_text(
            """
# Missing version, status, etc.
some_field: "some_value"
"""
        )

        checklist_loader = ChecklistLoader(invalid_checklist)
        config = MiddlewareConfig(require_checklist=True)
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(
            config=config,
            loader=loader,
            checklist_loader=checklist_loader,
        )

        with pytest.raises(ChecklistEnforcementError) as exc_info:
            middleware.initialize()

        assert "missing" in str(exc_info.value).lower()


class TestChecklistAuditLogging:
    """Tests for checklist audit logging."""

    def test_checklist_loaded_event_is_logged(self, manifests_dir, tmp_path):
        """Test that checklist loading is logged to audit."""
        import json

        from gateway.alex_middleware import GovernanceAuditLogger

        log_file = tmp_path / "governance.log"
        audit_logger = GovernanceAuditLogger(log_file)

        config = MiddlewareConfig(require_checklist=True)
        loader = ACMLoader(manifests_dir)
        middleware = ALEXMiddleware(
            config=config,
            loader=loader,
            audit_logger=audit_logger,
        )

        middleware.initialize()

        # Check that checklist loaded event was logged
        log_content = log_file.read_text()
        assert "CHECKLIST_LOADED" in log_content

        # Parse the log and verify structure
        events = [json.loads(line) for line in log_content.strip().split("\n")]
        checklist_events = [e for e in events if e.get("event") == "CHECKLIST_LOADED"]

        assert len(checklist_events) >= 1
        assert checklist_events[0]["checklist_version"] == "1.0.0"
        assert checklist_events[0]["checklist_status"] == "GOVERNANCE-LOCKED"
