"""
Authentication Middleware Unit Tests
=====================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: Comprehensive unit tests for auth middleware stack

TEST COVERAGE:
  - AuthMiddleware: JWT validation, API key validation, fail-closed behavior
  - IdentityMiddleware: GID registry binding, lane permissions
  - SessionMiddleware: Redis session management, TTL enforcement
  - RateLimitMiddleware: Sliding window algorithm, tier multipliers
  - SignatureMiddleware: HMAC verification, timestamp tolerance, nonce replay

INVARIANTS TESTED:
  INV-AUTH-001: Fail-closed authentication
  INV-AUTH-002: GID registry binding
  INV-AUTH-003: Redis-backed sessions
  INV-AUTH-004: Sliding window rate limiting
  INV-AUTH-005: Cryptographic signatures
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import middleware components
from api.middleware.auth import (
    AuthConfig,
    AuthResult,
    JWTValidator,
    APIKeyValidator,
    AuthMiddleware,
)
from api.middleware.identity import (
    GIDValidator,
    GIDInfo,
    IdentityMiddleware,
    IdentityContext,
)
from api.middleware.session import (
    SessionConfig,
    SessionData,
    SessionManager,
    SessionMiddleware,
)
from api.middleware.rate_limit import (
    RateLimitConfig,
    RateLimitResult,
    SlidingWindowRateLimiter,
    RateLimitMiddleware,
)
from api.middleware.signature import (
    SignatureConfig,
    SignatureResult,
    SignatureVerifier,
    NonceStore,
    SignatureMiddleware,
)


# ══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def jwt_secret():
    """Test JWT secret key."""
    return "test-secret-key-for-unit-tests-256-bits"


@pytest.fixture
def auth_config(jwt_secret):
    """Test authentication configuration."""
    return AuthConfig(
        jwt_secret_key=jwt_secret,
        jwt_algorithm="HS256",
        jwt_expiry_seconds=3600,
        jwt_issuer="chainbridge",
        jwt_audience="chainbridge-api",
        fail_closed=True,
    )


@pytest.fixture
def valid_jwt_token(jwt_secret):
    """Generate a valid JWT token for testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "user-123",
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
    signature_b64 = b64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


@pytest.fixture
def expired_jwt_token(jwt_secret):
    """Generate an expired JWT token for testing."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "user-123",
        "gid": "GID-01",
        "iss": "chainbridge",
        "aud": "chainbridge-api",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        "iat": int(time.time()) - 7200,
    }
    
    def b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    
    header_b64 = b64url_encode(json.dumps(header).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


# ══════════════════════════════════════════════════════════════════════════════
# JWT VALIDATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestJWTValidator:
    """Tests for JWT validation with fail-closed behavior."""
    
    def test_valid_token(self, auth_config, valid_jwt_token):
        """Test that valid JWT tokens are accepted."""
        validator = JWTValidator(auth_config)
        result = validator.validate(valid_jwt_token)
        
        assert result.authenticated is True
        assert result.auth_type == "jwt"
        assert result.user_id == "user-123"
        assert result.gid == "GID-01"
        assert result.error is None
    
    def test_expired_token_rejected(self, auth_config, expired_jwt_token):
        """INV-AUTH-006: Token expiry MUST be enforced with zero tolerance."""
        validator = JWTValidator(auth_config)
        result = validator.validate(expired_jwt_token)
        
        assert result.authenticated is False
        assert result.error == "Token expired"
    
    def test_invalid_signature_rejected(self, auth_config, valid_jwt_token):
        """Test that tokens with invalid signatures are rejected."""
        # Tamper with the token
        parts = valid_jwt_token.split(".")
        parts[2] = "invalid_signature_base64"
        tampered_token = ".".join(parts)
        
        validator = JWTValidator(auth_config)
        result = validator.validate(tampered_token)
        
        assert result.authenticated is False
    
    def test_malformed_token_rejected(self, auth_config):
        """Test that malformed tokens are rejected."""
        validator = JWTValidator(auth_config)
        
        # Test various malformed tokens
        malformed_tokens = [
            "",
            "not.a.token",
            "only.two.parts",
            "too.many.parts.here.now",
            "invalid-base64.payload.signature",
        ]
        
        for token in malformed_tokens:
            result = validator.validate(token)
            assert result.authenticated is False
    
    def test_wrong_issuer_rejected(self, auth_config, jwt_secret):
        """Test that tokens with wrong issuer are rejected."""
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "user-123",
            "iss": "wrong-issuer",  # Wrong issuer
            "aud": "chainbridge-api",
            "exp": int(time.time()) + 3600,
        }
        
        def b64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
        
        header_b64 = b64url_encode(json.dumps(header).encode())
        payload_b64 = b64url_encode(json.dumps(payload).encode())
        
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(jwt_secret.encode(), signing_input, hashlib.sha256).digest()
        signature_b64 = b64url_encode(signature)
        
        token = f"{header_b64}.{payload_b64}.{signature_b64}"
        
        validator = JWTValidator(auth_config)
        result = validator.validate(token)
        
        assert result.authenticated is False
        assert result.error == "Invalid issuer"


# ══════════════════════════════════════════════════════════════════════════════
# API KEY VALIDATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIKeyValidator:
    """Tests for API key validation with secure hash comparison."""
    
    def test_valid_api_key(self, auth_config, tmp_path):
        """Test that valid API keys are accepted."""
        # Create test API keys file
        api_key = "test-api-key-12345"
        salt = "random-salt"
        key_hash = hashlib.sha256(f"{salt}{api_key}".encode()).hexdigest()
        
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text(json.dumps({
            "key-001": {
                "hash": key_hash,
                "salt": salt,
                "user_id": "api-user-001",
                "gid": "GID-01",
                "enabled": True,
                "scopes": ["read", "write"],
            }
        }))
        
        auth_config.api_keys_file = str(keys_file)
        validator = APIKeyValidator(auth_config)
        result = validator.validate(api_key)
        
        assert result.authenticated is True
        assert result.auth_type == "api_key"
        assert result.user_id == "api-user-001"
    
    def test_invalid_api_key_rejected(self, auth_config, tmp_path):
        """Test that invalid API keys are rejected."""
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text(json.dumps({}))
        
        auth_config.api_keys_file = str(keys_file)
        validator = APIKeyValidator(auth_config)
        result = validator.validate("invalid-key")
        
        assert result.authenticated is False
        assert result.error == "Invalid API key"
    
    def test_disabled_api_key_rejected(self, auth_config, tmp_path):
        """Test that disabled API keys are rejected."""
        api_key = "disabled-key"
        salt = "salt"
        key_hash = hashlib.sha256(f"{salt}{api_key}".encode()).hexdigest()
        
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text(json.dumps({
            "key-disabled": {
                "hash": key_hash,
                "salt": salt,
                "enabled": False,  # Disabled
            }
        }))
        
        auth_config.api_keys_file = str(keys_file)
        validator = APIKeyValidator(auth_config)
        result = validator.validate(api_key)
        
        assert result.authenticated is False
        assert result.error == "API key disabled"


# ══════════════════════════════════════════════════════════════════════════════
# GID VALIDATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGIDValidator:
    """Tests for GID registry validation with HARD FAIL enforcement."""
    
    def test_valid_gid(self, tmp_path):
        """Test that valid GIDs are accepted."""
        registry_file = tmp_path / "gid_registry.json"
        registry_file.write_text(json.dumps({
            "registry_version": "1.0.0",
            "agents": {
                "GID-01": {
                    "name": "CODY",
                    "role": "Backend Engineer",
                    "lane": "BLUE",
                    "level": "L2",
                    "permitted_modes": ["EXECUTION", "REVIEW"],
                    "execution_lanes": ["CORE", "API"],
                    "can_issue_pac": False,
                    "can_issue_ber": False,
                    "can_override": False,
                    "system": False,
                }
            }
        }))
        
        validator = GIDValidator(registry_path=registry_file)
        gid_info = validator.validate_gid("GID-01")
        
        assert gid_info is not None
        assert gid_info.name == "CODY"
        assert gid_info.can_execute_in_lane("CORE") is True
    
    def test_unknown_gid_hard_fail(self, tmp_path):
        """RULE-GID-002: Unknown GID → immediate rejection (HARD FAIL)."""
        registry_file = tmp_path / "gid_registry.json"
        registry_file.write_text(json.dumps({
            "registry_version": "1.0.0",
            "agents": {}
        }))
        
        validator = GIDValidator(registry_path=registry_file)
        gid_info = validator.validate_gid("GID-99")
        
        assert gid_info is None
    
    def test_invalid_gid_format_rejected(self, tmp_path):
        """RULE-GID-003: GID format must match pattern GID-XX."""
        registry_file = tmp_path / "gid_registry.json"
        registry_file.write_text(json.dumps({
            "registry_version": "1.0.0",
            "agents": {}
        }))
        
        validator = GIDValidator(registry_path=registry_file)
        
        invalid_gids = [
            "invalid",
            "GID-1",  # Must be two digits
            "GID-001",  # Three digits
            "GID-AB",  # Letters
            "",
        ]
        
        for gid in invalid_gids:
            assert validator.validate_gid(gid) is None
    
    def test_lane_permission_check(self, tmp_path):
        """Test execution lane permission checking."""
        registry_file = tmp_path / "gid_registry.json"
        registry_file.write_text(json.dumps({
            "agents": {
                "GID-02": {
                    "name": "SONNY",
                    "role": "Frontend",
                    "lane": "YELLOW",
                    "level": "L2",
                    "permitted_modes": ["EXECUTION"],
                    "execution_lanes": ["FRONTEND", "UI"],
                    "can_issue_pac": False,
                    "can_issue_ber": False,
                    "can_override": False,
                    "system": False,
                }
            }
        }))
        
        validator = GIDValidator(registry_path=registry_file)
        gid_info = validator.validate_gid("GID-02")
        
        assert gid_info.can_execute_in_lane("FRONTEND") is True
        assert gid_info.can_execute_in_lane("BACKEND") is False


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSlidingWindowRateLimiter:
    """Tests for sliding window rate limiting algorithm."""
    
    def test_within_limit_allowed(self):
        """Test that requests within limit are allowed."""
        config = RateLimitConfig(default_limit=10, default_window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)
        
        # Make 5 requests (under limit of 10)
        for i in range(5):
            result = limiter.check("user-1", "/api/test")
            assert result.allowed is True
            assert result.remaining >= 0
    
    def test_over_limit_rejected(self):
        """INV-AUTH-004: Rate limit must be enforced."""
        config = RateLimitConfig(default_limit=3, default_window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)
        
        # Make 3 requests (at limit)
        for i in range(3):
            result = limiter.check("user-1", "/api/test")
            assert result.allowed is True
        
        # 4th request should be rejected
        result = limiter.check("user-1", "/api/test")
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.retry_after > 0
    
    def test_separate_identifiers_independent(self):
        """Test that different identifiers have independent limits."""
        config = RateLimitConfig(default_limit=2, default_window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)
        
        # User 1 exhausts limit
        limiter.check("user-1", "/api/test")
        limiter.check("user-1", "/api/test")
        result = limiter.check("user-1", "/api/test")
        assert result.allowed is False
        
        # User 2 should still be allowed
        result = limiter.check("user-2", "/api/test")
        assert result.allowed is True
    
    def test_tier_multiplier_applied(self):
        """Test that tier multipliers increase limits."""
        config = RateLimitConfig(default_limit=2, default_window_seconds=60)
        limiter = SlidingWindowRateLimiter(config)
        
        # With 2x multiplier, effective limit should be 4
        for i in range(4):
            result = limiter.check("premium-user", "/api/test", multiplier=2.0)
            assert result.allowed is True
        
        # 5th request should be rejected
        result = limiter.check("premium-user", "/api/test", multiplier=2.0)
        assert result.allowed is False


# ══════════════════════════════════════════════════════════════════════════════
# SIGNATURE VERIFIER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSignatureVerifier:
    """Tests for cryptographic signature verification."""
    
    @pytest.fixture
    def sig_config(self):
        """Signature configuration for tests."""
        return SignatureConfig(
            secret_key="test-signature-secret",
            algorithm="hmac-sha256",
            timestamp_tolerance_seconds=300,
            enable_nonce_check=False,  # Disable for basic tests
        )
    
    def test_valid_signature_accepted(self, sig_config):
        """Test that valid signatures are accepted."""
        verifier = SignatureVerifier(sig_config)
        
        method = "POST"
        path = "/v1/transaction"
        timestamp = int(time.time() * 1000)
        body = b'{"amount": 100}'
        
        # Compute expected signature
        body_hash = hashlib.sha256(body).hexdigest()
        expected_sig = verifier.compute_signature(method, path, timestamp, body_hash)
        
        signature_header = f"sha256={expected_sig}"
        
        result = verifier.verify(method, path, signature_header, timestamp, body)
        
        assert result.valid is True
        assert result.error is None
    
    def test_invalid_signature_rejected(self, sig_config):
        """INV-AUTH-005: Invalid signatures MUST be rejected."""
        verifier = SignatureVerifier(sig_config)
        
        timestamp = int(time.time() * 1000)
        signature_header = "sha256=invalid_signature_base64=="
        
        result = verifier.verify("POST", "/v1/transaction", signature_header, timestamp, b'{}')
        
        assert result.valid is False
    
    def test_timestamp_outside_tolerance_rejected(self, sig_config):
        """Test that requests with old timestamps are rejected."""
        verifier = SignatureVerifier(sig_config)
        
        # Timestamp from 10 minutes ago (outside 5 minute tolerance)
        old_timestamp = int((time.time() - 600) * 1000)
        body = b'{}'
        body_hash = hashlib.sha256(body).hexdigest()
        sig = verifier.compute_signature("POST", "/test", old_timestamp, body_hash)
        
        result = verifier.verify("POST", "/test", f"sha256={sig}", old_timestamp, body)
        
        assert result.valid is False
        assert "tolerance" in result.error.lower()
    
    def test_nonce_replay_detected(self):
        """Test that nonce replay attacks are detected."""
        config = SignatureConfig(
            secret_key="test-secret",
            enable_nonce_check=True,
        )
        verifier = SignatureVerifier(config)
        
        timestamp = int(time.time() * 1000)
        nonce = "unique-nonce-123"
        body = b'{}'
        body_hash = hashlib.sha256(body).hexdigest()
        sig = verifier.compute_signature("POST", "/test", timestamp, body_hash, nonce)
        
        # First request should succeed
        result1 = verifier.verify("POST", "/test", f"sha256={sig}", timestamp, body, nonce)
        assert result1.valid is True
        
        # Replay should be detected
        result2 = verifier.verify("POST", "/test", f"sha256={sig}", timestamp, body, nonce)
        assert result2.valid is False
        assert "replay" in result2.error.lower()


# ══════════════════════════════════════════════════════════════════════════════
# SESSION MANAGER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionManager:
    """Tests for Redis-backed session management."""
    
    @pytest.fixture
    def session_config(self):
        """Session configuration for tests."""
        return SessionConfig(
            session_ttl=3600,
            refresh_threshold=300,
            session_id_bytes=32,
        )
    
    @pytest.mark.asyncio
    async def test_session_creation(self, session_config):
        """Test that sessions are created correctly."""
        manager = SessionManager(session_config)
        
        session = await manager.create_session(
            user_id="user-123",
            gid="GID-01",
            ip_address="127.0.0.1",
        )
        
        assert session.session_id is not None
        assert len(session.session_id) == 64  # SHA256 hex
        assert session.user_id == "user-123"
        assert session.gid == "GID-01"
        assert session.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_session_retrieval(self, session_config):
        """Test that sessions can be retrieved."""
        manager = SessionManager(session_config)
        
        created = await manager.create_session(user_id="user-456")
        retrieved = await manager.get_session(created.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.user_id == created.user_id
    
    @pytest.mark.asyncio
    async def test_session_invalidation(self, session_config):
        """INV-SESSION-003: Session invalidation MUST propagate immediately."""
        manager = SessionManager(session_config)
        
        session = await manager.create_session(user_id="user-789")
        
        # Invalidate
        result = await manager.invalidate_session(session.session_id)
        assert result is True
        
        # Should not be retrievable
        retrieved = await manager.get_session(session.session_id)
        assert retrieved is None


# ══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED BEHAVIOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFailClosedBehavior:
    """Tests for INV-AUTH-001: Fail-closed authentication."""
    
    def test_auth_config_fail_closed_required(self):
        """Test that fail_closed=False raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            AuthConfig(fail_closed=False)
        
        assert "INV-AUTH-001" in str(excinfo.value)
    
    def test_jwt_validator_exception_returns_unauthenticated(self, auth_config):
        """Test that JWT validation exceptions result in authentication failure."""
        validator = JWTValidator(auth_config)
        
        # Any exception should result in authenticated=False
        result = validator.validate(None)  # Will cause exception
        assert result.authenticated is False
    
    def test_api_key_validator_exception_returns_unauthenticated(self, auth_config, tmp_path):
        """Test that API key validation exceptions result in authentication failure."""
        # Create invalid JSON file
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text("invalid json {")
        
        auth_config.api_keys_file = str(keys_file)
        validator = APIKeyValidator(auth_config)
        
        # Should not raise, should return unauthenticated
        result = validator.validate("any-key")
        assert result.authenticated is False


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS FOR MIDDLEWARE STACK
# ══════════════════════════════════════════════════════════════════════════════

class TestMiddlewareStack:
    """Integration tests for the complete middleware stack."""
    
    def test_exempt_paths_bypass_auth(self):
        """Test that exempt paths bypass authentication."""
        from api.middleware import DEFAULT_EXEMPT_PATHS
        
        assert "/" in DEFAULT_EXEMPT_PATHS
        assert "/health" in DEFAULT_EXEMPT_PATHS
        assert "/docs" in DEFAULT_EXEMPT_PATHS
    
    def test_apply_auth_stack_function(self):
        """Test that apply_auth_stack adds all middleware."""
        from fastapi import FastAPI
        from api.middleware import apply_auth_stack
        
        app = FastAPI()
        initial_middleware_count = len(app.user_middleware)
        
        apply_auth_stack(
            app,
            enable_rate_limit=True,
            enable_signature=True,
            enable_session=True,
        )
        
        # Should have added multiple middleware
        assert len(app.user_middleware) > initial_middleware_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
