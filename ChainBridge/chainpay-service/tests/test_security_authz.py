"""
ChainPay Security Authorization Tests

Tests for:
- 401 Unauthorized (missing/invalid auth)
- 403 Forbidden (IDOR - wrong tenant accessing other's shipment)
- Proper access with valid auth
"""

import os

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def unauth_client(client: TestClient) -> TestClient:
    """Client without Authorization header."""
    # Ensure DEV_AUTH_BYPASS is disabled
    os.environ.pop("DEV_AUTH_BYPASS", None)
    return client


@pytest.fixture
def tenant1_client(client: TestClient) -> TestClient:
    """Client authenticated as TENANT1."""
    os.environ.pop("DEV_AUTH_BYPASS", None)
    client.headers["Authorization"] = "Bearer demo-token-tenant1"
    return client


@pytest.fixture
def tenant2_client(client: TestClient) -> TestClient:
    """Client authenticated as TENANT2."""
    os.environ.pop("DEV_AUTH_BYPASS", None)
    client.headers["Authorization"] = "Bearer demo-token-tenant2"
    return client


@pytest.fixture
def admin_client(client: TestClient) -> TestClient:
    """Client authenticated as admin (bypasses tenant checks)."""
    os.environ.pop("DEV_AUTH_BYPASS", None)
    client.headers["Authorization"] = "Bearer demo-token-admin"
    return client


@pytest.fixture
def demo_client(client: TestClient) -> TestClient:
    """Client authenticated as demo tenant (can access SHIP-* format)."""
    os.environ.pop("DEV_AUTH_BYPASS", None)
    client.headers["Authorization"] = "Bearer demo-token"
    return client


# ---------------------------------------------------------------------------
# 401 Unauthorized Tests - Missing/Invalid Auth
# ---------------------------------------------------------------------------


class TestUnauthorized:
    """Tests for 401 Unauthorized responses."""

    def test_settlements_endpoint_requires_auth(self, unauth_client: TestClient):
        """GET /api/chainpay/settlements/{id} returns 401 without auth."""
        response = unauth_client.get("/api/chainpay/settlements/SHIP-12345")
        assert response.status_code == 401
        assert "Bearer" in response.headers.get("WWW-Authenticate", "")

    def test_analytics_endpoint_requires_auth(self, unauth_client: TestClient):
        """GET /api/chainpay/analytics/usd-mxn returns 401 without auth."""
        response = unauth_client.get("/api/chainpay/analytics/usd-mxn")
        assert response.status_code == 401

    def test_audit_shipment_requires_auth(self, unauth_client: TestClient):
        """GET /audit/shipments/{id} returns 401 without auth."""
        response = unauth_client.get("/audit/shipments/SHIP-12345")
        assert response.status_code == 401

    def test_settle_onchain_requires_auth(self, unauth_client: TestClient):
        """POST /chainpay/settle-onchain returns 401 without auth."""
        response = unauth_client.post(
            "/chainpay/settle-onchain",
            json={"settlement_id": "test-123", "amount": 100.0},
        )
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient):
        """Invalid token returns 401."""
        os.environ.pop("DEV_AUTH_BYPASS", None)
        client.headers["Authorization"] = "Bearer invalid-garbage-token"
        response = client.get("/api/chainpay/settlements/SHIP-12345")
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json().get("detail", "")


# ---------------------------------------------------------------------------
# 403 Forbidden Tests - IDOR Protection
# ---------------------------------------------------------------------------


class TestForbidden:
    """Tests for 403 Forbidden responses (IDOR protection)."""

    def test_tenant1_cannot_access_tenant2_shipment(self, tenant1_client: TestClient):
        """TENANT1 cannot access TENANT2's shipment (403)."""
        # TENANT1 tries to access TENANT2's shipment
        response = tenant1_client.get("/api/chainpay/settlements/TENANT2-SHIP-999")
        assert response.status_code == 403
        assert "Access denied" in response.json().get("detail", "")

    def test_tenant2_cannot_access_tenant1_shipment(self, tenant2_client: TestClient):
        """TENANT2 cannot access TENANT1's shipment (403)."""
        response = tenant2_client.get("/api/chainpay/settlements/TENANT1-SHIP-888")
        assert response.status_code == 403

    def test_tenant1_cannot_access_audit_for_tenant2(self, tenant1_client: TestClient):
        """TENANT1 cannot access audit for TENANT2's shipment (403)."""
        response = tenant1_client.get("/audit/shipments/TENANT2-SHIP-777")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# 200 OK Tests - Proper Access
# ---------------------------------------------------------------------------


class TestAuthorizedAccess:
    """Tests for successful authorized access."""

    def test_tenant1_can_access_own_shipment(self, tenant1_client: TestClient):
        """TENANT1 can access their own shipment."""
        response = tenant1_client.get("/api/chainpay/settlements/TENANT1-SHIP-123")
        # Should not be 401 or 403 (may be 200 or 404 depending on data)
        assert response.status_code not in (401, 403)

    def test_admin_can_access_any_shipment(self, admin_client: TestClient):
        """Admin can access any tenant's shipment."""
        # Admin accessing TENANT1's shipment
        response = admin_client.get("/api/chainpay/settlements/TENANT1-SHIP-123")
        assert response.status_code not in (401, 403)

        # Admin accessing TENANT2's shipment
        response = admin_client.get("/api/chainpay/settlements/TENANT2-SHIP-456")
        assert response.status_code not in (401, 403)

    def test_demo_tenant_can_access_ship_format(self, demo_client: TestClient):
        """Demo tenant can access SHIP-xxx format shipments."""
        response = demo_client.get("/api/chainpay/settlements/SHIP-12345")
        # Should return 200 (mock data exists) or 404, but not 401/403
        assert response.status_code not in (401, 403)
        if response.status_code == 200:
            data = response.json()
            assert data["shipment_id"] == "SHIP-12345"

    def test_analytics_endpoint_with_auth(self, demo_client: TestClient):
        """Analytics endpoint works with valid auth."""
        response = demo_client.get("/api/chainpay/analytics/usd-mxn")
        # Should not be 401 or 403
        assert response.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# DEV_AUTH_BYPASS Tests
# ---------------------------------------------------------------------------


class TestDevAuthBypass:
    """Tests for DEV_AUTH_BYPASS behavior."""

    def test_bypass_disabled_by_default(self, unauth_client: TestClient):
        """Without DEV_AUTH_BYPASS, auth is required."""
        os.environ.pop("DEV_AUTH_BYPASS", None)
        response = unauth_client.get("/api/chainpay/settlements/SHIP-12345")
        assert response.status_code == 401

    def test_bypass_enabled_allows_access(self, client: TestClient):
        """With DEV_AUTH_BYPASS=true, auth is bypassed."""
        os.environ["DEV_AUTH_BYPASS"] = "true"
        try:
            # Remove any auth header
            client.headers.pop("Authorization", None)
            response = client.get("/api/chainpay/settlements/SHIP-12345")
            # Should not be 401 (bypass active)
            assert response.status_code != 401
        finally:
            os.environ.pop("DEV_AUTH_BYPASS", None)

    def test_bypass_false_requires_auth(self, client: TestClient):
        """With DEV_AUTH_BYPASS=false, auth is required."""
        os.environ["DEV_AUTH_BYPASS"] = "false"
        try:
            client.headers.pop("Authorization", None)
            response = client.get("/api/chainpay/settlements/SHIP-12345")
            assert response.status_code == 401
        finally:
            os.environ.pop("DEV_AUTH_BYPASS", None)


# ---------------------------------------------------------------------------
# Health Endpoint (should remain unauthenticated)
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Health endpoint should remain public."""

    def test_health_no_auth_required(self, unauth_client: TestClient):
        """GET /health should work without auth."""
        response = unauth_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
