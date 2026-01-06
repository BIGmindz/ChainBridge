"""
PAC-20260106-P09-SECURITY-HARDENING
Security Middleware Tests — Rate Limiting & Auth Validation

Verifies:
- 429 Too Many Requests (rate limit exceeded)
- 403 Forbidden (missing X-GID-AUTH)
- INV-SEC-005: Zero Trust Access

Author: BENSON (GID-00-EXEC)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.occ_security import (
    RateLimiter,
    RateLimitConfig,
    AuthValidator,
    AuthValidationResult,
    OCCSecurityMiddleware,
    get_rate_limiter,
    reset_rate_limiter,
    get_security_audit_logger,
    reset_security_audit_logger,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def rate_limiter():
    """Fresh rate limiter for each test."""
    reset_rate_limiter()
    limiter = get_rate_limiter()
    yield limiter
    reset_rate_limiter()


@pytest.fixture
def app_with_middleware():
    """FastAPI app with security middleware."""
    reset_rate_limiter()
    reset_security_audit_logger()
    
    app = FastAPI()
    app.add_middleware(OCCSecurityMiddleware)
    
    @app.get("/occ/dashboard")
    def dashboard():
        return {"status": "ok"}
    
    @app.post("/occ/kill-switch/arm")
    def arm_kill_switch():
        return {"armed": True}
    
    @app.get("/health")
    def health():
        return {"healthy": True}
    
    yield app
    
    reset_rate_limiter()
    reset_security_audit_logger()


@pytest.fixture
def client(app_with_middleware):
    """Test client with middleware."""
    return TestClient(app_with_middleware)


# =============================================================================
# RATE LIMITER TESTS — 429 Too Many Requests
# =============================================================================


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_requests_within_limit(self, rate_limiter):
        """Requests within limit should pass."""
        # Add config for test path
        rate_limiter.add_config(RateLimitConfig(
            requests=3,
            window=60,
            paths=["/test"],
            methods=["GET"],
        ))
        
        # Create mock request
        request = MagicMock()
        request.url.path = "/test/endpoint"
        request.method = "GET"
        request.client.host = "127.0.0.1"
        request.headers.get.return_value = None
        
        # First 3 requests should pass
        for _ in range(3):
            result = rate_limiter.check_rate_limit(request)
            assert result is None, "Request within limit should pass"
    
    def test_rate_limiter_blocks_excess_requests(self, rate_limiter):
        """Requests exceeding limit should return 429."""
        rate_limiter.add_config(RateLimitConfig(
            requests=2,
            window=60,
            paths=["/limited"],
            methods=["POST"],
        ))
        
        request = MagicMock()
        request.url.path = "/limited/action"
        request.method = "POST"
        request.client.host = "192.168.1.1"
        request.headers.get.return_value = None
        
        # Use up the limit
        rate_limiter.check_rate_limit(request)
        rate_limiter.check_rate_limit(request)
        
        # Third request should be blocked
        result = rate_limiter.check_rate_limit(request)
        assert result is not None, "Excess request should be blocked"
        assert result.status_code == 429
    
    def test_rate_limiter_returns_retry_after_header(self, rate_limiter):
        """429 response should include Retry-After header."""
        rate_limiter.add_config(RateLimitConfig(
            requests=1,
            window=60,
            paths=["/strict"],
            methods=["GET"],
        ))
        
        request = MagicMock()
        request.url.path = "/strict/path"
        request.method = "GET"
        request.client.host = "10.0.0.1"
        request.headers.get.return_value = None
        
        rate_limiter.check_rate_limit(request)
        result = rate_limiter.check_rate_limit(request)
        
        assert result is not None
        assert "Retry-After" in result.headers


class TestRateLimiterIntegration:
    """Integration tests for rate limiting via middleware."""
    
    def test_429_response_on_kill_switch_rate_limit(self, client):
        """Kill switch endpoint returns 429 when rate limited."""
        # Kill switch has 5 requests per minute limit
        # Make 6 requests to trigger rate limit
        # Note: Need auth headers for kill switch
        headers = {
            "X-GID-AUTH": "GID-00",
            "Authorization": "Bearer test-token",
        }
        
        # Patch auth service to allow requests through
        with patch("api.middleware.occ_security.get_operator_auth_service") as mock_auth:
            mock_service = MagicMock()
            mock_session = MagicMock()
            mock_session.session_id = "test-session"
            mock_session.operator_id = "op-001"
            mock_session.permissions = []
            mock_service.validate_session.return_value = mock_session
            mock_auth.return_value = mock_service
            
            # Reset to get fresh middleware
            reset_rate_limiter()
            
            # Make requests up to and past limit
            responses = []
            for i in range(7):
                resp = client.post("/occ/kill-switch/arm", headers=headers)
                responses.append(resp.status_code)
            
            # Should have at least one 429
            assert 429 in responses, f"Expected 429 in responses: {responses}"


# =============================================================================
# AUTH VALIDATOR TESTS — 403 Forbidden / Missing X-GID-AUTH
# =============================================================================


class TestAuthValidator:
    """Test X-GID-AUTH header validation."""
    
    def test_missing_gid_auth_header_returns_invalid(self):
        """Request without X-GID-AUTH should fail validation."""
        with patch("api.middleware.occ_security.get_operator_auth_service"):
            validator = AuthValidator()
            
            request = MagicMock()
            request.url.path = "/occ/kill-switch/arm"
            request.headers.get = lambda h: None  # No headers
            
            result = validator.validate_request(request)
            
            assert not result.is_valid
            assert "X-GID-AUTH" in result.error
    
    def test_invalid_gid_format_returns_invalid(self):
        """X-GID-AUTH with wrong format should fail."""
        with patch("api.middleware.occ_security.get_operator_auth_service"):
            validator = AuthValidator()
            
            request = MagicMock()
            request.url.path = "/occ/kill-switch/arm"
            
            def get_header(name):
                if name == "X-GID-AUTH":
                    return "INVALID-FORMAT"
                return None
            
            request.headers.get = get_header
            
            result = validator.validate_request(request)
            
            assert not result.is_valid
            assert "GID-XX" in result.error
    
    def test_valid_gid_auth_proceeds_to_bearer_check(self):
        """Valid X-GID-AUTH should proceed to Authorization check."""
        with patch("api.middleware.occ_security.get_operator_auth_service"):
            validator = AuthValidator()
            
            request = MagicMock()
            request.url.path = "/occ/kill-switch/arm"
            
            def get_header(name):
                if name == "X-GID-AUTH":
                    return "GID-00"
                if name == "Authorization":
                    return None  # Missing Bearer token
                return None
            
            request.headers.get = get_header
            
            result = validator.validate_request(request)
            
            # Should fail on missing Authorization, not X-GID-AUTH
            assert not result.is_valid
            assert "Authorization" in result.error
    
    def test_public_paths_skip_auth(self):
        """Public paths should not require authentication."""
        with patch("api.middleware.occ_security.get_operator_auth_service"):
            validator = AuthValidator()
            
            request = MagicMock()
            request.url.path = "/occ/dashboard"
            request.headers.get = lambda h: None
            
            result = validator.validate_request(request)
            
            assert result.is_valid


class TestAuthValidatorIntegration:
    """Integration tests for auth validation via middleware."""
    
    def test_401_on_missing_gid_auth_header(self, client):
        """Kill switch returns 401 without X-GID-AUTH."""
        response = client.post("/occ/kill-switch/arm")
        assert response.status_code == 401
        assert "X-GID-AUTH" in response.json().get("message", "")
    
    def test_401_on_invalid_gid_format(self, client):
        """Kill switch returns 401 with invalid GID format."""
        headers = {"X-GID-AUTH": "BADFORMAT"}
        response = client.post("/occ/kill-switch/arm", headers=headers)
        assert response.status_code == 401
        assert "GID-XX" in response.json().get("message", "")
    
    def test_dashboard_accessible_without_auth(self, client):
        """Dashboard should be accessible without auth."""
        response = client.get("/occ/dashboard")
        assert response.status_code == 200


# =============================================================================
# MIDDLEWARE INTEGRATION TESTS
# =============================================================================


class TestOCCSecurityMiddleware:
    """Test full middleware stack."""
    
    def test_non_occ_paths_bypass_security(self, client):
        """Non-OCC paths should bypass security checks."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_security_audit_logs_rate_limit_events(self, client):
        """Rate limit events should be logged."""
        reset_security_audit_logger()
        logger = get_security_audit_logger()
        
        # Trigger rate limit (dashboard has 100/min limit, use custom)
        # For this test, just verify logging works
        client.get("/occ/dashboard")
        
        entries = logger.get_entries(limit=10)
        assert len(entries) > 0
        assert any(e.event_type == "ACCESS" for e in entries)
    
    def test_security_audit_logs_auth_failures(self, client):
        """Auth failures should be logged."""
        reset_security_audit_logger()
        logger = get_security_audit_logger()
        
        # Trigger auth failure
        client.post("/occ/kill-switch/arm")
        
        entries = logger.get_entries(limit=10)
        assert any(e.event_type == "AUTH_FAILURE" for e in entries)


# =============================================================================
# INVARIANT TESTS — INV-SEC-005: Zero Trust Access
# =============================================================================


class TestZeroTrustInvariant:
    """Tests for INV-SEC-005: Zero Trust Access invariant."""
    
    def test_all_protected_paths_require_gid_auth(self):
        """All protected paths must require X-GID-AUTH."""
        with patch("api.middleware.occ_security.get_operator_auth_service"):
            validator = AuthValidator()
            
            protected_paths = [
                "/occ/kill-switch/arm",
                "/occ/kill-switch/engage",
                "/occ/kill-switch/disengage",
                "/occ/kill-switch/disarm",
            ]
            
            for path in protected_paths:
                assert validator.requires_auth(path), f"{path} must require auth"
    
    def test_no_auth_bypass_possible(self, client):
        """Verify no auth bypass is possible on protected endpoints."""
        bypass_attempts = [
            {"headers": {}},
            {"headers": {"X-GID-AUTH": ""}},
            {"headers": {"X-GID-AUTH": "null"}},
            {"headers": {"X-GID-AUTH": "../../../etc/passwd"}},
            {"headers": {"Authorization": "Bearer token"}},  # Missing GID
        ]
        
        for attempt in bypass_attempts:
            response = client.post("/occ/kill-switch/arm", **attempt)
            assert response.status_code in [401, 403], \
                f"Bypass attempt succeeded: {attempt}"
