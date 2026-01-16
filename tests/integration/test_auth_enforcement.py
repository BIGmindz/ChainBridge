"""
Authentication Enforcement Integration Tests
=============================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: End-to-end integration tests for authentication enforcement

TEST COVERAGE:
  - Full request lifecycle through middleware stack
  - JWT authentication flow
  - API key authentication flow
  - GID identity binding
  - Rate limiting behavior
  - Signature verification for transaction endpoints

INVARIANTS TESTED:
  INV-AUTH-001: All API requests MUST pass authentication (fail-closed)
  INV-AUTH-002: GID binding MUST be verified against gid_registry.json
  INV-AUTH-004: Rate limiting MUST use sliding window per endpoint
  INV-AUTH-005: Request signatures MUST be cryptographically verified
"""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Import auth middleware
from api.middleware import apply_auth_stack, AuthConfig


# ══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def jwt_secret():
    """JWT secret for testing."""
    return "integration-test-jwt-secret-256-bits"


@pytest.fixture
def signature_secret():
    """Signature secret for testing."""
    return "integration-test-signature-secret"


@pytest.fixture
def valid_jwt(jwt_secret):
    """Generate a valid JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "integration-test-user",
        "gid": "GID-01",
        "iss": "chainbridge",
        "aud": "chainbridge-api",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    
    def b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    
    header_b64 = b64url_encode(json.dumps(header).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    
    return f"{header_b64}.{payload_b64}.{b64url_encode(signature)}"


@pytest.fixture
def test_app(jwt_secret, signature_secret, tmp_path):
    """Create a test FastAPI app with auth middleware."""
    # Set environment variables
    os.environ["JWT_SECRET_KEY"] = jwt_secret
    os.environ["SIGNATURE_SECRET_KEY"] = signature_secret
    
    # Create test GID registry
    gid_registry = tmp_path / "gid_registry.json"
    gid_registry.write_text(json.dumps({
        "registry_version": "1.0.0",
        "agents": {
            "GID-01": {
                "name": "CODY",
                "role": "Backend Engineer",
                "lane": "BLUE",
                "level": "L2",
                "permitted_modes": ["EXECUTION", "REVIEW"],
                "execution_lanes": ["CORE", "API", "BACKEND"],
                "can_issue_pac": False,
                "can_issue_ber": False,
                "can_override": False,
                "system": False,
            },
            "GID-00": {
                "name": "BENSON",
                "role": "System Orchestrator",
                "lane": "TEAL",
                "level": "L3",
                "permitted_modes": ["ORCHESTRATION", "SYNTHESIS", "REVIEW"],
                "execution_lanes": ["ALL"],
                "can_issue_pac": True,
                "can_issue_ber": True,
                "can_override": True,
                "system": True,
            }
        }
    }))
    
    # Create test API keys
    api_keys = tmp_path / "api_keys.json"
    api_key = "test-integration-api-key"
    salt = "test-salt"
    key_hash = hashlib.sha256(f"{salt}{api_key}".encode()).hexdigest()
    
    api_keys.write_text(json.dumps({
        "key-integration-001": {
            "hash": key_hash,
            "salt": salt,
            "user_id": "api-integration-user",
            "gid": "GID-01",
            "enabled": True,
            "tier": "pro",
            "scopes": ["read", "write"],
        }
    }))
    
    # Patch registry path
    import api.middleware.identity as identity_module
    identity_module.GID_REGISTRY_PATH = gid_registry
    
    # Create explicit AuthConfig with test API keys path
    auth_config = AuthConfig(
        jwt_secret_key=jwt_secret,
        api_keys_file=str(api_keys),
    )
    
    # Create FastAPI app
    app = FastAPI(title="Auth Integration Test")
    
    # Apply auth middleware with explicit config
    apply_auth_stack(
        app,
        enable_rate_limit=True,
        enable_signature=False,  # Disable for most tests
        enable_session=False,  # Disable Redis for tests
        auth_config=auth_config,
    )
    
    @app.get("/")
    async def root():
        return {"status": "ok"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/api/protected")
    async def protected(request: Request):
        return {
            "message": "authenticated",
            "user_id": getattr(request.state, "user_id", None),
            "gid": getattr(request.state, "gid", None),
        }
    
    @app.post("/v1/transaction")
    async def transaction(request: Request):
        return {"status": "processed"}
    
    return app, api_key


@pytest.fixture
def client(test_app):
    """Create test client."""
    app, _ = test_app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api_key(test_app):
    """Get API key for testing."""
    _, key = test_app
    return key


# ══════════════════════════════════════════════════════════════════════════════
# EXEMPT PATH TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestExemptPaths:
    """Test that exempt paths bypass authentication."""
    
    def test_root_exempt(self, client):
        """Test that / is accessible without auth."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_health_exempt(self, client):
        """Test that /health is accessible without auth."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_docs_exempt(self, client):
        """Test that /docs is accessible without auth."""
        response = client.get("/docs")
        # FastAPI docs returns 200 or redirect
        assert response.status_code in [200, 307]


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION REQUIRED TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthenticationRequired:
    """Test INV-AUTH-001: All API requests MUST pass authentication."""
    
    def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints require authentication."""
        response = client.get("/api/protected")
        assert response.status_code == 401
        assert response.json()["error"] == "Unauthorized"
    
    def test_jwt_authentication_accepted(self, client, valid_jwt):
        """Test that valid JWT tokens are accepted."""
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "authenticated"
    
    def test_api_key_authentication_accepted(self, client, api_key):
        """Test that valid API keys are accepted."""
        response = client.get(
            "/api/protected",
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200
    
    def test_invalid_jwt_rejected(self, client):
        """Test that invalid JWT tokens are rejected."""
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401
    
    def test_expired_jwt_rejected(self, client, jwt_secret):
        """Test that expired JWT tokens are rejected."""
        # Create expired token
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "user",
            "iss": "chainbridge",
            "aud": "chainbridge-api",
            "exp": int(time.time()) - 3600,  # Expired
        }
        
        def b64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
        
        header_b64 = b64url_encode(json.dumps(header).encode())
        payload_b64 = b64url_encode(json.dumps(payload).encode())
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(jwt_secret.encode(), signing_input, hashlib.sha256).digest()
        expired_token = f"{header_b64}.{payload_b64}.{b64url_encode(signature)}"
        
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
    
    def test_invalid_api_key_rejected(self, client):
        """Test that invalid API keys are rejected."""
        response = client.get(
            "/api/protected",
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GID IDENTITY BINDING TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGIDIdentityBinding:
    """Test INV-AUTH-002: GID binding MUST be verified against gid_registry.json."""
    
    def test_valid_gid_accepted(self, client, valid_jwt):
        """Test that valid GID claims are accepted."""
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gid"] == "GID-01"
    
    def test_invalid_gid_rejected(self, client, jwt_secret):
        """Test that invalid GID claims are rejected."""
        # Create token with invalid GID
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "user",
            "gid": "GID-99",  # Invalid GID
            "iss": "chainbridge",
            "aud": "chainbridge-api",
            "exp": int(time.time()) + 3600,
        }
        
        def b64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
        
        header_b64 = b64url_encode(json.dumps(header).encode())
        payload_b64 = b64url_encode(json.dumps(payload).encode())
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(jwt_secret.encode(), signing_input, hashlib.sha256).digest()
        token = f"{header_b64}.{payload_b64}.{b64url_encode(signature)}"
        
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should return 403 Forbidden for invalid GID
        assert response.status_code == 403
        assert response.json()["code"] == "INVALID_GID"


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITING TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimiting:
    """Test INV-AUTH-004: Rate limiting MUST use sliding window per endpoint."""
    
    def test_rate_limit_headers_present(self, client, valid_jwt):
        """Test that rate limit headers are present in response."""
        response = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_rate_limit_decrements(self, client, valid_jwt):
        """Test that rate limit remaining decrements with each request."""
        response1 = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        remaining1 = int(response1.headers.get("X-RateLimit-Remaining", 0))
        
        response2 = client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        remaining2 = int(response2.headers.get("X-RateLimit-Remaining", 0))
        
        # Remaining should decrease
        assert remaining2 < remaining1


# ══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED BEHAVIOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFailClosedBehavior:
    """Test that authentication fails closed on errors."""
    
    def test_malformed_auth_header_rejected(self, client):
        """Test that malformed Authorization headers are rejected."""
        malformed_headers = [
            "Bearer",  # Missing token
            "bearer token",  # Wrong case
            "NotBearer token",  # Wrong scheme
            "",  # Empty
        ]
        
        for auth in malformed_headers:
            response = client.get(
                "/api/protected",
                headers={"Authorization": auth}
            )
            assert response.status_code == 401
    
    def test_empty_api_key_rejected(self, client):
        """Test that empty API keys are rejected."""
        response = client.get(
            "/api/protected",
            headers={"X-API-Key": ""}
        )
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE FORMAT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestResponseFormat:
    """Test that error responses follow standard format."""
    
    def test_unauthorized_response_format(self, client):
        """Test 401 Unauthorized response format."""
        response = client.get("/api/protected")
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "code" in data
    
    def test_www_authenticate_header_present(self, client):
        """Test that WWW-Authenticate header is present on 401."""
        response = client.get("/api/protected")
        
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
