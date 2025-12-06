"""
Tests verifying ChainIQ router mounting invariants.

These tests ensure the module isolation strategy in api/server.py
correctly handles the dual `app` package situation (monorepo vs chainiq-service).
"""

from __future__ import annotations

import sys


def test_chainiq_router_is_available():
    """Verify the ChainIQ router was successfully loaded."""
    from api.server import CHAINIQ_AVAILABLE, chainiq_router

    assert CHAINIQ_AVAILABLE is True, "ChainIQ router should be available"
    assert chainiq_router is not None, "chainiq_router should not be None"


def test_chainiq_modules_are_namespaced():
    """
    ChainIQ modules should be stored under chainiq_* prefix
    for explicit access (in addition to their original names).
    """
    # Import server to trigger the ChainIQ loading
    import api.server  # noqa: F401

    # Look for namespaced chainiq modules
    chainiq_namespaced = [k for k in sys.modules.keys() if k.startswith("chainiq_app")]

    # At least the main chainiq_app.api should exist if loading succeeded
    from api.server import CHAINIQ_AVAILABLE
    if CHAINIQ_AVAILABLE:
        assert len(chainiq_namespaced) > 0, (
            "ChainIQ modules should be namespaced under chainiq_* prefix"
        )


def test_chainiq_app_modules_available_for_runtime():
    """
    ChainIQ's app.* modules must remain in sys.modules for lazy imports
    in the service layer (e.g., from app.risk.db_models import RiskEvaluation).
    """
    # Import server to trigger the ChainIQ loading
    import api.server  # noqa: F401

    from api.server import CHAINIQ_AVAILABLE
    if CHAINIQ_AVAILABLE:
        # Check that chainiq's app.risk modules are still accessible
        assert "app.risk" in sys.modules, "app.risk should be in sys.modules for chainiq"

        # Verify it points to chainiq-service
        app_risk = sys.modules["app.risk"]
        mod_file = getattr(app_risk, "__file__", "") or ""
        assert "chainiq-service" in mod_file, (
            f"app.risk should point to chainiq-service, got {mod_file}"
        )


def test_iq_routes_are_mounted():
    """
    Verify that /iq/* routes are actually available on the FastAPI app.
    """
    from api.server import app

    # Collect all route paths
    route_paths = [route.path for route in app.routes]

    # Check that at least some /iq/ routes exist
    iq_routes = [p for p in route_paths if "/iq" in p]

    assert len(iq_routes) > 0, (
        f"Expected /iq/* routes to be mounted. Found routes: {route_paths[:20]}..."
    )


def test_risk_endpoints_accessible():
    """
    Verify the risk endpoints are accessible via TestClient.

    Note: These endpoints require a database session, so we expect them to
    fail with an error (not 404). The key invariant is that the routes
    exist and the code path reaches the endpoint handler.
    """
    from fastapi.testclient import TestClient

    from api.server import app

    client = TestClient(app, raise_server_exceptions=False)

    # Test the risk scoring endpoint exists (may return error without payload, but not 404)
    response = client.post("/iq/risk/score", json={})
    assert response.status_code != 404, (
        f"Risk scoring endpoint should exist. Got {response.status_code}"
    )

    # Test the evaluations endpoint - expect 500 (no DB) but not 404 (route missing)
    response = client.get("/iq/risk/evaluations")
    assert response.status_code != 404, (
        f"Evaluations endpoint should exist. Got {response.status_code}"
    )
