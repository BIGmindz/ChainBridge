"""
Core Authentication Middleware
==============================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: Core JWT/API Key Validation

INVARIANTS:
  INV-AUTH-001: All API requests MUST pass authentication (fail-closed)
  INV-AUTH-006: Token expiry MUST be enforced with zero tolerance
  INV-AUTH-007: API keys MUST be verified against secure hash storage

FAIL-CLOSED BEHAVIOR:
  - Any authentication error → 401 Unauthorized
  - Missing credentials → 401 Unauthorized
  - Invalid credentials → 401 Unauthorized
  - Expired credentials → 401 Unauthorized
  - System error → 401 Unauthorized (never expose internal errors)
"""

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
logger = logging.getLogger("chainbridge.auth")


@dataclass
class AuthConfig:
    """
    Authentication configuration loaded from config/auth_config.yaml.
    
    Provides fail-safe defaults for all security-critical parameters.
    """
    # JWT Configuration
    jwt_secret_key: str = field(default_factory=lambda: os.environ.get("JWT_SECRET_KEY", ""))
    jwt_algorithm: str = "HS256"
    jwt_expiry_seconds: int = 3600  # 1 hour default
    jwt_issuer: str = "chainbridge"
    jwt_audience: str = "chainbridge-api"
    
    # API Key Configuration
    api_key_header: str = "X-API-Key"
    api_key_hash_algorithm: str = "sha256"
    api_keys_file: str = "config/api_keys.json"
    
    # Security Settings
    fail_closed: bool = True  # MUST be True per INV-AUTH-001
    log_auth_failures: bool = True
    max_auth_attempts: int = 5
    lockout_duration_seconds: int = 300  # 5 minutes
    
    # Token refresh settings
    allow_token_refresh: bool = True
    refresh_window_seconds: int = 300  # Allow refresh within 5 min of expiry
    
    def __post_init__(self):
        """Validate configuration and enforce invariants."""
        if not self.fail_closed:
            raise ValueError("INV-AUTH-001 VIOLATION: fail_closed MUST be True")
        
        if not self.jwt_secret_key:
            logger.warning("JWT_SECRET_KEY not set - JWT validation will fail")


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    authenticated: bool
    auth_type: Optional[str] = None  # "jwt" or "api_key"
    user_id: Optional[str] = None
    gid: Optional[str] = None
    claims: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class JWTValidator:
    """
    JWT token validation with fail-closed behavior.
    
    Uses HMAC-SHA256 for signature verification by default.
    Enforces expiry with zero tolerance.
    """
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self._secret = config.jwt_secret_key.encode() if config.jwt_secret_key else b""
    
    def validate(self, token: str) -> AuthResult:
        """
        Validate a JWT token.
        
        Returns AuthResult with authenticated=False on ANY error (fail-closed).
        """
        try:
            # Split token parts
            parts = token.split(".")
            if len(parts) != 3:
                return AuthResult(authenticated=False, error="Invalid token format")
            
            header_b64, payload_b64, signature_b64 = parts
            
            # Decode header and payload (base64url)
            import base64
            
            def b64url_decode(data: str) -> bytes:
                """Decode base64url with padding."""
                padding = 4 - (len(data) % 4)
                if padding != 4:
                    data += "=" * padding
                return base64.urlsafe_b64decode(data)
            
            try:
                header = json.loads(b64url_decode(header_b64))
                payload = json.loads(b64url_decode(payload_b64))
            except (json.JSONDecodeError, ValueError):
                return AuthResult(authenticated=False, error="Invalid token encoding")
            
            # Verify algorithm
            if header.get("alg") != self.config.jwt_algorithm:
                return AuthResult(authenticated=False, error="Invalid algorithm")
            
            # Verify signature
            signing_input = f"{header_b64}.{payload_b64}".encode()
            if self.config.jwt_algorithm == "HS256":
                expected_sig = hmac.new(
                    self._secret,
                    signing_input,
                    hashlib.sha256
                ).digest()
                
                try:
                    actual_sig = b64url_decode(signature_b64)
                except Exception:
                    return AuthResult(authenticated=False, error="Invalid signature encoding")
                
                if not hmac.compare_digest(expected_sig, actual_sig):
                    return AuthResult(authenticated=False, error="Invalid signature")
            else:
                return AuthResult(authenticated=False, error="Unsupported algorithm")
            
            # Verify expiry (zero tolerance)
            exp = payload.get("exp")
            if exp is None:
                return AuthResult(authenticated=False, error="Missing expiry")
            
            now = time.time()
            if now > exp:
                return AuthResult(authenticated=False, error="Token expired")
            
            # Verify issuer
            if payload.get("iss") != self.config.jwt_issuer:
                return AuthResult(authenticated=False, error="Invalid issuer")
            
            # Verify audience
            aud = payload.get("aud")
            if isinstance(aud, list):
                if self.config.jwt_audience not in aud:
                    return AuthResult(authenticated=False, error="Invalid audience")
            elif aud != self.config.jwt_audience:
                return AuthResult(authenticated=False, error="Invalid audience")
            
            # Extract identity
            return AuthResult(
                authenticated=True,
                auth_type="jwt",
                user_id=payload.get("sub"),
                gid=payload.get("gid"),
                claims=payload,
            )
            
        except Exception as e:
            # FAIL-CLOSED: Any exception = authentication failure
            logger.error(f"JWT validation error: {e}")
            return AuthResult(authenticated=False, error="Authentication failed")


class APIKeyValidator:
    """
    API key validation with secure hash comparison.
    
    Keys are stored as salted hashes to prevent exposure.
    Uses constant-time comparison to prevent timing attacks.
    """
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load_keys()
    
    def _load_keys(self) -> None:
        """Load API keys from secure storage."""
        keys_path = Path(self.config.api_keys_file)
        if keys_path.exists():
            try:
                with open(keys_path) as f:
                    self._keys = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")
                self._keys = {}
    
    def _hash_key(self, key: str, salt: str = "") -> str:
        """Generate salted hash of API key."""
        return hashlib.sha256(f"{salt}{key}".encode()).hexdigest()
    
    def validate(self, api_key: str) -> AuthResult:
        """
        Validate an API key.
        
        Returns AuthResult with authenticated=False on ANY error (fail-closed).
        """
        try:
            if not api_key:
                return AuthResult(authenticated=False, error="Missing API key")
            
            # Check each registered key
            for key_id, key_data in self._keys.items():
                stored_hash = key_data.get("hash", "")
                salt = key_data.get("salt", "")
                
                computed_hash = self._hash_key(api_key, salt)
                
                # Constant-time comparison
                if hmac.compare_digest(computed_hash, stored_hash):
                    # Check if key is enabled
                    if not key_data.get("enabled", True):
                        return AuthResult(authenticated=False, error="API key disabled")
                    
                    # Check expiry
                    expires = key_data.get("expires")
                    if expires:
                        exp_time = datetime.fromisoformat(expires)
                        if datetime.now(timezone.utc) > exp_time:
                            return AuthResult(authenticated=False, error="API key expired")
                    
                    return AuthResult(
                        authenticated=True,
                        auth_type="api_key",
                        user_id=key_data.get("user_id"),
                        gid=key_data.get("gid"),
                        claims={
                            "key_id": key_id,
                            "scopes": key_data.get("scopes", []),
                            "rate_limit": key_data.get("rate_limit"),
                        },
                    )
            
            return AuthResult(authenticated=False, error="Invalid API key")
            
        except Exception as e:
            # FAIL-CLOSED: Any exception = authentication failure
            logger.error(f"API key validation error: {e}")
            return AuthResult(authenticated=False, error="Authentication failed")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Core authentication middleware with fail-closed behavior.
    
    Enforces INV-AUTH-001: All API requests MUST pass authentication.
    
    Authentication Methods (in order of precedence):
      1. Bearer token in Authorization header (JWT)
      2. X-API-Key header (API key)
      3. api_key query parameter (API key, lower security)
    """
    
    def __init__(
        self,
        app,
        exempt_paths: FrozenSet[str] = frozenset(),
        config: Optional[AuthConfig] = None,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths
        self.config = config or AuthConfig()
        self.jwt_validator = JWTValidator(self.config)
        self.api_key_validator = APIKeyValidator(self.config)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from authentication."""
        # Exact match
        if path in self.exempt_paths:
            return True
        
        # Strip trailing slash and check
        path_normalized = path.rstrip("/")
        if path_normalized in self.exempt_paths:
            return True
        
        # Check if path starts with exempt prefix (for /docs/*, etc.)
        for exempt in self.exempt_paths:
            if path.startswith(exempt + "/"):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process authentication for incoming request."""
        path = request.url.path
        
        # Check exemption
        if self._is_exempt(path):
            return await call_next(request)
        
        # Extract credentials
        auth_result = self._authenticate(request)
        
        # FAIL-CLOSED: Reject on any authentication failure
        if not auth_result.authenticated:
            if self.config.log_auth_failures:
                logger.warning(
                    f"Auth failure: path={path} error={auth_result.error} "
                    f"ip={request.client.host if request.client else 'unknown'}"
                )
            
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Authentication required",
                    "code": "AUTH_REQUIRED",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Attach auth result to request state for downstream middleware
        request.state.auth = auth_result
        request.state.user_id = auth_result.user_id
        request.state.gid = auth_result.gid
        
        return await call_next(request)
    
    def _authenticate(self, request: Request) -> AuthResult:
        """
        Attempt authentication using available credentials.
        
        Order of precedence:
          1. Authorization: Bearer <token>
          2. X-API-Key header
          3. api_key query parameter
        """
        # Try Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            result = self.jwt_validator.validate(token)
            if result.authenticated:
                return result
        
        # Try X-API-Key header
        api_key = request.headers.get(self.config.api_key_header)
        if api_key:
            result = self.api_key_validator.validate(api_key)
            if result.authenticated:
                return result
        
        # Try query parameter (lower security, last resort)
        api_key = request.query_params.get("api_key")
        if api_key:
            logger.warning(
                f"API key in query parameter - consider using header instead: "
                f"path={request.url.path}"
            )
            result = self.api_key_validator.validate(api_key)
            if result.authenticated:
                return result
        
        # No valid credentials found
        return AuthResult(authenticated=False, error="No valid credentials")
