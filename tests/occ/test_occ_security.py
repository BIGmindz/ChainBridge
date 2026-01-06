"""
OCC Security Guards Tests
PAC-BENSON-P42: OCC Operationalization & Defect Remediation

Tests for:
- Rate limiting
- Auth validation
- Audit logging

Author: DAN (GID-07) — DevOps/Security
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import time

import pytest

from api.middleware.occ_security import (
    RateLimiter,
    RateLimitConfig,
    get_rate_limiter,
    reset_rate_limiter,
    AuthValidator,
    AuthValidationResult,
    SecurityAuditLogger,
    SecurityAuditEntry,
    get_security_audit_logger,
    reset_security_audit_logger,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    reset_rate_limiter()
    reset_security_audit_logger()
    yield
    reset_rate_limiter()
    reset_security_audit_logger()


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/occ/dashboard/health"
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = MagicMock()
    request.headers.get = MagicMock(return_value=None)
    return request


# =============================================================================
# RATE LIMITER TESTS
# =============================================================================


class TestRateLimiter:
    """Rate limiter functionality tests."""
    
    def test_singleton_returns_same_instance(self):
        """Singleton should return same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2
    
    def test_reset_creates_new_instance(self):
        """Reset should create new instance."""
        limiter1 = get_rate_limiter()
        reset_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is not limiter2
    
    def test_get_client_id_from_host(self, mock_request):
        """Client ID should be extracted from host."""
        limiter = RateLimiter()
        mock_request.headers.get.return_value = None
        
        client_id = limiter.get_client_id(mock_request)
        assert client_id == "127.0.0.1"
    
    def test_get_client_id_from_forwarded(self, mock_request):
        """Client ID should prefer X-Forwarded-For."""
        limiter = RateLimiter()
        mock_request.headers.get.return_value = "10.0.0.1, 192.168.1.1"
        
        client_id = limiter.get_client_id(mock_request)
        assert client_id == "10.0.0.1"
    
    def test_no_config_allows_request(self, mock_request):
        """Request without matching config should be allowed."""
        limiter = RateLimiter()
        mock_request.url.path = "/unprotected/path"
        
        result = limiter.check_rate_limit(mock_request)
        assert result is None  # None means allowed
    
    def test_rate_limit_allows_under_threshold(self, mock_request):
        """Requests under limit should be allowed."""
        limiter = RateLimiter()
        limiter._configs = [
            RateLimitConfig(requests=5, window=60, paths=["/occ/dashboard"], methods=["GET"]),
        ]
        
        # Make 4 requests (under limit of 5)
        for _ in range(4):
            result = limiter.check_rate_limit(mock_request)
            assert result is None
    
    def test_rate_limit_blocks_over_threshold(self, mock_request):
        """Requests over limit should be blocked."""
        limiter = RateLimiter()
        limiter._configs = [
            RateLimitConfig(requests=3, window=60, paths=["/occ/dashboard"], methods=["GET"]),
        ]
        
        # Make 3 requests (at limit)
        for _ in range(3):
            result = limiter.check_rate_limit(mock_request)
            assert result is None
        
        # 4th request should be blocked
        result = limiter.check_rate_limit(mock_request)
        assert result is not None
        assert result.status_code == 429
    
    def test_rate_limit_resets_after_window(self, mock_request):
        """Rate limit should reset after window expires."""
        limiter = RateLimiter()
        limiter._configs = [
            RateLimitConfig(requests=2, window=1, paths=["/occ/dashboard"], methods=["GET"]),
        ]
        
        # Use up limit
        limiter.check_rate_limit(mock_request)
        limiter.check_rate_limit(mock_request)
        
        # Should be blocked
        result = limiter.check_rate_limit(mock_request)
        assert result is not None
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        result = limiter.check_rate_limit(mock_request)
        assert result is None
    
    def test_kill_switch_has_strict_limit(self):
        """Kill switch endpoints should have strict rate limits."""
        limiter = get_rate_limiter()
        
        config = limiter.get_config_for_path("/occ/kill-switch/engage", "POST")
        assert config is not None
        assert config.requests == 5
        assert config.window == 60


# =============================================================================
# AUTH VALIDATOR TESTS
# =============================================================================


class TestAuthValidator:
    """Auth validation tests."""
    
    def test_public_paths_dont_require_auth(self, mock_request):
        """Public paths should not require auth."""
        validator = AuthValidator()
        
        assert not validator.requires_auth("/occ/dashboard/health")
        assert not validator.requires_auth("/occ/auth/login")
    
    def test_protected_paths_require_auth(self):
        """Protected paths should require auth."""
        validator = AuthValidator()
        
        assert validator.requires_auth("/occ/kill-switch/arm")
        assert validator.requires_auth("/occ/kill-switch/engage")
        assert validator.requires_auth("/occ/kill-switch/disengage")
        assert validator.requires_auth("/occ/kill-switch/disarm")
    
    def test_public_path_allows_without_token(self, mock_request):
        """Public path should allow request without token."""
        validator = AuthValidator()
        mock_request.url.path = "/occ/dashboard/health"
        
        result = validator.validate_request(mock_request)
        assert result.is_valid is True
    
    def test_protected_path_requires_header(self, mock_request):
        """Protected path without X-GID-AUTH header should fail."""
        validator = AuthValidator()
        mock_request.url.path = "/occ/kill-switch/arm"
        mock_request.headers.get.return_value = None
        
        result = validator.validate_request(mock_request)
        assert result.is_valid is False
        assert "X-GID-AUTH" in result.error
    
    def test_invalid_header_format_fails(self, mock_request):
        """Invalid X-GID-AUTH format should fail."""
        validator = AuthValidator()
        mock_request.url.path = "/occ/kill-switch/arm"
        
        # Return X-GID-AUTH with invalid format
        def header_get(name):
            if name == "X-GID-AUTH":
                return "INVALID-FORMAT"
            return None
        mock_request.headers.get = header_get
        
        result = validator.validate_request(mock_request)
        assert result.is_valid is False
        assert "GID-XX" in result.error
    
    def test_invalid_token_fails(self, mock_request):
        """Invalid token should fail (after X-GID-AUTH passes)."""
        validator = AuthValidator()
        mock_request.url.path = "/occ/kill-switch/arm"
        
        # Valid X-GID-AUTH but invalid Bearer token
        def header_get(name):
            if name == "X-GID-AUTH":
                return "GID-00"
            if name == "Authorization":
                return "Bearer invalid-token"
            return None
        mock_request.headers.get = header_get
        
        result = validator.validate_request(mock_request)
        assert result.is_valid is False
        assert "Invalid or expired" in result.error
    
    def test_valid_token_succeeds(self, mock_request):
        """Valid X-GID-AUTH and Bearer token should succeed."""
        from core.occ.auth.operator_auth import get_operator_auth_service, reset_operator_auth_service, OperatorMode
        
        reset_operator_auth_service()
        auth_service = get_operator_auth_service()
        
        # Create a valid session via authenticate
        # JEFFREY is the default known operator with JEFFREY_INTERNAL access
        result = auth_service.authenticate("JEFFREY", OperatorMode.JEFFREY_INTERNAL)
        assert result.success, f"Auth failed: {result.message}"
        token = result.token  # Use the TOKEN, not session_id
        session = result.session
        
        # Create validator AFTER we have created the session
        # The validator will use the same auth service singleton
        validator = AuthValidator()
        mock_request.url.path = "/occ/kill-switch/arm"
        
        # Must provide both X-GID-AUTH and Bearer token (PAC-P09)
        def header_get(name):
            if name == "X-GID-AUTH":
                return "GID-00"
            if name == "Authorization":
                return f"Bearer {token}"
            return None
        mock_request.headers.get = header_get
        
        # Debug: verify session exists in the service
        verified = auth_service.validate_session(token)
        assert verified is not None, "Session should exist in auth service"
        
        validation_result = validator.validate_request(mock_request)
        assert validation_result.is_valid is True, f"Validation failed: {validation_result.error}"
        # Compare using session_id from validated session
        assert validation_result.operator_id == session.operator_id
        
        reset_operator_auth_service()


# =============================================================================
# AUDIT LOGGER TESTS
# =============================================================================


class TestSecurityAuditLogger:
    """Security audit logger tests."""
    
    def test_singleton_returns_same_instance(self):
        """Singleton should return same instance."""
        logger1 = get_security_audit_logger()
        logger2 = get_security_audit_logger()
        assert logger1 is logger2
    
    def test_logs_event(self, mock_request):
        """Logger should record events."""
        logger = SecurityAuditLogger()
        
        logger.log(
            event_type="ACCESS",
            request=mock_request,
            outcome="ALLOWED",
        )
        
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].event_type == "ACCESS"
        assert entries[0].outcome == "ALLOWED"
    
    def test_logs_with_session_info(self, mock_request):
        """Logger should record session info."""
        logger = SecurityAuditLogger()
        
        logger.log(
            event_type="ACCESS",
            request=mock_request,
            outcome="ALLOWED",
            session_id="sess-123",
            operator_id="op-456",
        )
        
        entries = logger.get_entries()
        assert entries[0].session_id == "sess-123"
        assert entries[0].operator_id == "op-456"
    
    def test_entries_returned_newest_first(self, mock_request):
        """Entries should be returned newest first."""
        logger = SecurityAuditLogger()
        
        logger.log(event_type="EVENT_1", request=mock_request, outcome="OK")
        logger.log(event_type="EVENT_2", request=mock_request, outcome="OK")
        logger.log(event_type="EVENT_3", request=mock_request, outcome="OK")
        
        entries = logger.get_entries()
        assert entries[0].event_type == "EVENT_3"
        assert entries[2].event_type == "EVENT_1"
    
    def test_filter_by_event_type(self, mock_request):
        """Should filter entries by event type."""
        logger = SecurityAuditLogger()
        
        logger.log(event_type="ACCESS", request=mock_request, outcome="OK")
        logger.log(event_type="AUTH_FAILURE", request=mock_request, outcome="BLOCKED")
        logger.log(event_type="ACCESS", request=mock_request, outcome="OK")
        
        entries = logger.get_entries(event_type="AUTH_FAILURE")
        assert len(entries) == 1
        assert entries[0].event_type == "AUTH_FAILURE"
    
    def test_limit_entries(self, mock_request):
        """Should limit number of entries returned."""
        logger = SecurityAuditLogger()
        
        for i in range(10):
            logger.log(event_type=f"EVENT_{i}", request=mock_request, outcome="OK")
        
        entries = logger.get_entries(limit=3)
        assert len(entries) == 3
    
    def test_trims_old_entries(self, mock_request):
        """Should trim entries when exceeding max."""
        logger = SecurityAuditLogger()
        logger._max_entries = 5
        
        for i in range(10):
            logger.log(event_type=f"EVENT_{i}", request=mock_request, outcome="OK")
        
        # Should only have last 5 entries
        assert len(logger._entries) == 5
        assert logger._entries[0].event_type == "EVENT_5"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSecurityIntegration:
    """Integration tests for security components."""
    
    def test_rate_limit_and_auth_together(self, mock_request):
        """Rate limiting and auth should work together."""
        limiter = RateLimiter()
        limiter._configs = [
            RateLimitConfig(requests=2, window=60, paths=["/occ/kill-switch"], methods=["POST"]),
        ]
        
        validator = AuthValidator()
        mock_request.url.path = "/occ/kill-switch/arm"
        mock_request.method = "POST"
        mock_request.headers.get.return_value = None
        
        # First check rate limit (should pass)
        rate_result = limiter.check_rate_limit(mock_request)
        assert rate_result is None
        
        # Then check auth (should fail - no token)
        auth_result = validator.validate_request(mock_request)
        assert auth_result.is_valid is False
