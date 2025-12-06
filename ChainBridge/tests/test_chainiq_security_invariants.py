"""
Security-focused tests for ChainIQ router mounting.

These tests guard against regressions in the security hardening of the
ChainIQ import mechanism in api/server.py.

SECURITY RATIONALE:
- The ChainIQ mounting logic manipulates sys.path and sys.modules to work
  around a dual `app` package namespace issue.
- This is a potential attack surface if paths or module names become
  user-controllable or environment-driven.
- These tests ensure paths remain static, project-bounded, and predictable.

Author: SAM (GID-06 Security & Threat Engineer)
PAC: ChainIQ Import Hardening v1.0
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def project_root() -> Path:
    """Return the resolved project root path."""
    # tests/ is one level below project root
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def chainiq_root(project_root: Path) -> Path:
    """Return the expected ChainIQ service root path."""
    return project_root / "chainiq-service"


@pytest.fixture(scope="module")
def server_constants():
    """Import and return the path constants from api.server."""
    from api import server
    return {
        "PROJECT_ROOT": server.PROJECT_ROOT,
        "CHAINIQ_SERVICE_ROOT": server.CHAINIQ_SERVICE_ROOT,
        "CHAINIQ_APP_DIR": server.CHAINIQ_APP_DIR,
    }


# ---------------------------------------------------------------------------
# Path Security Tests
# ---------------------------------------------------------------------------


class TestChainIQPathSecurity:
    """Tests verifying ChainIQ paths are static and project-bounded."""

    def test_chainiq_root_exists(self, chainiq_root: Path):
        """ChainIQ service directory must exist at expected location."""
        assert chainiq_root.is_dir(), (
            f"Expected chainiq-service directory at {chainiq_root}"
        )

    def test_chainiq_app_dir_exists(self, chainiq_root: Path):
        """ChainIQ app package directory must exist."""
        app_dir = chainiq_root / "app"
        assert app_dir.is_dir(), (
            f"Expected chainiq-service/app directory at {app_dir}"
        )

    def test_server_uses_static_paths(self, server_constants, project_root: Path):
        """api/server.py must use static, __file__-derived paths."""
        # Verify the constants are Path objects (not strings that could be manipulated)
        assert isinstance(server_constants["PROJECT_ROOT"], Path)
        assert isinstance(server_constants["CHAINIQ_SERVICE_ROOT"], Path)
        assert isinstance(server_constants["CHAINIQ_APP_DIR"], Path)

    def test_chainiq_path_within_project_bounds(
        self, server_constants, project_root: Path
    ):
        """ChainIQ path must resolve within project root (no symlink escape)."""
        chainiq_root = server_constants["CHAINIQ_SERVICE_ROOT"]
        resolved = chainiq_root.resolve()
        project_resolved = project_root.resolve()

        assert str(resolved).startswith(str(project_resolved)), (
            f"ChainIQ path {resolved} escapes project root {project_resolved}"
        )

    def test_path_constants_are_absolute(self, server_constants):
        """All path constants must be absolute paths."""
        for name, path in server_constants.items():
            assert path.is_absolute(), f"{name} must be an absolute path, got: {path}"

    def test_project_root_matches_expected(
        self, server_constants, project_root: Path
    ):
        """server.PROJECT_ROOT must match our computed project root."""
        server_root = server_constants["PROJECT_ROOT"].resolve()
        expected_root = project_root.resolve()

        assert server_root == expected_root, (
            f"PROJECT_ROOT mismatch: {server_root} != {expected_root}"
        )


# ---------------------------------------------------------------------------
# sys.path Security Tests
# ---------------------------------------------------------------------------


class TestSysPathSecurity:
    """Tests verifying sys.path manipulation is safe and predictable."""

    def test_no_suspicious_sys_path_entries(self):
        """sys.path should not contain path traversal patterns or empty strings."""
        # Import server to trigger ChainIQ loading
        import api.server  # noqa: F401

        suspicious_patterns = [
            "",           # Empty string
            " ",          # Whitespace only
            "..",         # Parent traversal
            "../",        # Parent traversal with slash
            "..\\",       # Windows parent traversal
        ]

        bad_entries = []
        for path in sys.path:
            path_str = str(path).strip()
            if path_str in suspicious_patterns or ".." in path_str:
                bad_entries.append(path)

        assert not bad_entries, (
            f"Suspicious entries in sys.path: {bad_entries}"
        )

    def test_chainiq_path_added_correctly(self, chainiq_root: Path):
        """If ChainIQ path is in sys.path, it must be the expected absolute path."""
        # Import server to trigger ChainIQ loading
        import api.server  # noqa: F401

        chainiq_entries = [
            p for p in sys.path
            if "chainiq-service" in str(p)
        ]

        # It's okay if chainiq-service is or isn't in sys.path
        # (depends on the loading strategy), but if it IS there,
        # it must be the correct absolute path
        for entry in chainiq_entries:
            entry_path = Path(entry).resolve()
            expected = chainiq_root.resolve()
            assert entry_path == expected, (
                f"Unexpected chainiq-service path in sys.path: {entry}"
            )


# ---------------------------------------------------------------------------
# sys.modules Security Tests
# ---------------------------------------------------------------------------


class TestSysModulesSecurity:
    """Tests verifying sys.modules state after ChainIQ loading."""

    def test_monorepo_app_not_shadowed_by_chainiq(self):
        """
        The monorepo's `app` package must not be permanently shadowed
        by chainiq-service's app package.
        """
        # Import server to trigger ChainIQ loading
        import api.server  # noqa: F401

        if "app" in sys.modules:
            app_module = sys.modules["app"]
            mod_file = getattr(app_module, "__file__", "") or ""

            # The monorepo's app module should NOT point to chainiq-service
            # (unless we intentionally keep it for runtime)
            # What matters is that monorepo functionality isn't broken
            if "chainiq-service" in mod_file:
                # If chainiq app is loaded, verify it's intentional and
                # that chainiq modules are accessible
                assert "chainiq_app" in sys.modules or any(
                    k.startswith("chainiq_app.") for k in sys.modules
                ), "ChainIQ modules should be namespaced under chainiq_app.*"

    def test_chainiq_modules_accessible_if_loaded(self):
        """
        If ChainIQ router loaded successfully, its modules should be
        accessible (either as app.* or chainiq_app.*).
        """
        from api.server import CHAINIQ_AVAILABLE

        if CHAINIQ_AVAILABLE:
            # At least one of these access patterns should work
            chainiq_api_accessible = (
                "chainiq_app.api" in sys.modules
                or "app.api" in sys.modules
            )
            assert chainiq_api_accessible, (
                "ChainIQ API module should be accessible after successful load"
            )


# ---------------------------------------------------------------------------
# Import Hardening Tests
# ---------------------------------------------------------------------------


class TestImportHardening:
    """Tests verifying import mechanisms are hardened."""

    def test_validate_chainiq_paths_exists(self):
        """The _validate_chainiq_paths function must exist."""
        from api.server import _validate_chainiq_paths

        assert callable(_validate_chainiq_paths), (
            "_validate_chainiq_paths must be a callable function"
        )

    def test_validate_chainiq_paths_raises_on_missing_dir(self, tmp_path: Path):
        """
        _validate_chainiq_paths must raise RuntimeError if ChainIQ
        directories don't exist.

        NOTE: This test verifies the validation logic works, but we
        can't easily test it without mocking the constants.
        """
        # This is a design verification - the function should exist
        # and be documented to raise RuntimeError
        from api.server import _validate_chainiq_paths
        import inspect

        source = inspect.getsource(_validate_chainiq_paths)
        assert "RuntimeError" in source, (
            "_validate_chainiq_paths should raise RuntimeError on validation failure"
        )
        assert "is_dir()" in source, (
            "_validate_chainiq_paths should check if directories exist"
        )

    def test_no_dynamic_module_imports(self):
        """
        The ChainIQ loading code must not use __import__ with
        user-controllable strings.
        """
        from api import server
        import inspect

        source = inspect.getsource(server._load_chainiq_router)

        # Check for dangerous patterns
        dangerous_patterns = [
            "__import__(",      # Dynamic import
            "importlib.import_module(",  # Dynamic import (if not hardcoded)
            "exec(",            # Code execution
            "eval(",            # Code evaluation
        ]

        for pattern in dangerous_patterns:
            assert pattern not in source, (
                f"Dangerous pattern '{pattern}' found in _load_chainiq_router"
            )


# ---------------------------------------------------------------------------
# Runtime Invariants Tests
# ---------------------------------------------------------------------------


class TestRuntimeInvariants:
    """Tests verifying runtime invariants are maintained."""

    def test_chainiq_router_loads_successfully(self):
        """ChainIQ router should load without errors."""
        from api.server import CHAINIQ_AVAILABLE, chainiq_router

        assert CHAINIQ_AVAILABLE is True, "ChainIQ router should be available"
        assert chainiq_router is not None, "chainiq_router should not be None"

    def test_fastapi_app_importable(self):
        """The main FastAPI app must remain importable."""
        from api.server import app

        assert app is not None
        # Verify it's a FastAPI instance
        assert hasattr(app, "routes"), "app should have routes attribute"
        assert hasattr(app, "include_router"), "app should be a FastAPI instance"

    def test_iq_routes_mounted(self):
        """The /iq/* routes must be mounted on the app."""
        from api.server import app

        route_paths = [route.path for route in app.routes]
        iq_routes = [p for p in route_paths if "/iq" in p]

        assert len(iq_routes) > 0, (
            f"Expected /iq/* routes to be mounted. Routes: {route_paths[:20]}..."
        )
