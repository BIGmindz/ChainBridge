"""
OCC Security Guards — Rate Limiting & Auth Validation
PAC-BENSON-P42: OCC Operationalization & Defect Remediation

Guards for:
- Rate limiting on mutation endpoints
- Auth token validation
- Request logging and audit

Author: DAN (GID-07) — DevOps/Security
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.occ.auth.operator_auth import get_operator_auth_service


# =============================================================================
# RATE LIMITER
# =============================================================================


class RateLimitWindow(Enum):
    """Rate limit time windows."""
    
    SECOND = 1
    MINUTE = 60
    HOUR = 3600


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    # Requests per window
    requests: int
    # Window duration in seconds
    window: int
    # Paths this config applies to (prefix match)
    paths: List[str] = field(default_factory=list)
    # Methods this config applies to (empty = all)
    methods: List[str] = field(default_factory=list)


@dataclass
class RateLimitEntry:
    """Tracking entry for a single client."""
    
    requests: int = 0
    window_start: float = 0.0


class RateLimiter:
    """
    Token bucket rate limiter for API endpoints.
    
    Tracks request counts per client (IP or session) within time windows.
    """
    
    def __init__(self) -> None:
        # client_id -> RateLimitEntry
        self._buckets: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        
        # Default configs for OCC endpoints
        self._configs: List[RateLimitConfig] = [
            # Kill switch mutations: strict limit
            RateLimitConfig(
                requests=5,
                window=60,
                paths=["/occ/kill-switch/arm", "/occ/kill-switch/engage", "/occ/kill-switch/disengage", "/occ/kill-switch/disarm"],
                methods=["POST"],
            ),
            # Auth endpoints: moderate limit
            RateLimitConfig(
                requests=10,
                window=60,
                paths=["/occ/auth/login", "/occ/auth/logout"],
                methods=["POST"],
            ),
            # Dashboard reads: generous limit
            RateLimitConfig(
                requests=100,
                window=60,
                paths=["/occ/dashboard"],
                methods=["GET"],
            ),
        ]
    
    def get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Prefer X-Forwarded-For if behind proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def get_config_for_path(self, path: str, method: str) -> Optional[RateLimitConfig]:
        """Find matching rate limit config for path."""
        for config in self._configs:
            # Check path prefix match
            if any(path.startswith(p) for p in config.paths):
                # Check method match (empty = all methods)
                if not config.methods or method in config.methods:
                    return config
        return None
    
    def check_rate_limit(self, request: Request) -> Optional[JSONResponse]:
        """
        Check if request exceeds rate limit.
        
        Returns:
            JSONResponse if rate limited, None if allowed
        """
        path = request.url.path
        method = request.method
        
        config = self.get_config_for_path(path, method)
        if config is None:
            return None  # No rate limit for this path
        
        client_id = self.get_client_id(request)
        bucket_key = f"{client_id}:{path}"
        
        now = time.time()
        entry = self._buckets[bucket_key]
        
        # Check if window has expired
        if now - entry.window_start > config.window:
            # Reset window
            entry.requests = 0
            entry.window_start = now
        
        # Check limit
        if entry.requests >= config.requests:
            retry_after = int(config.window - (now - entry.window_start))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        
        # Increment counter
        entry.requests += 1
        return None
    
    def add_config(self, config: RateLimitConfig) -> None:
        """Add a rate limit configuration."""
        self._configs.append(config)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset the rate limiter (for testing)."""
    global _rate_limiter
    _rate_limiter = None


# =============================================================================
# AUTH VALIDATOR
# =============================================================================


@dataclass
class AuthValidationResult:
    """Result of auth validation."""
    
    is_valid: bool
    session_id: Optional[str] = None
    operator_id: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    error: Optional[str] = None


class AuthValidator:
    """
    Validates authentication tokens for OCC endpoints.
    
    Integrates with OperatorAuthService to validate session tokens.
    """
    
    # Paths that require authentication
    PROTECTED_PATHS = [
        "/occ/kill-switch/arm",
        "/occ/kill-switch/engage",
        "/occ/kill-switch/disengage",
        "/occ/kill-switch/disarm",
    ]
    
    # Paths that are always public
    PUBLIC_PATHS = [
        "/occ/dashboard",
        "/occ/auth/login",
        "/occ/auth/modes",
    ]
    
    def __init__(self) -> None:
        self._auth_service = get_operator_auth_service()
    
    def requires_auth(self, path: str) -> bool:
        """Check if path requires authentication."""
        return any(path.startswith(p) for p in self.PROTECTED_PATHS)
    
    def validate_request(self, request: Request) -> AuthValidationResult:
        """
        Validate authentication for request.
        
        Returns:
            AuthValidationResult with validation outcome
        """
        path = request.url.path
        
        # Check if path requires auth
        if not self.requires_auth(path):
            return AuthValidationResult(is_valid=True)
        
        # PAC-P09: Require X-GID-AUTH header (Zero Trust)
        gid_auth = request.headers.get("X-GID-AUTH")
        if not gid_auth:
            return AuthValidationResult(
                is_valid=False,
                error="Missing X-GID-AUTH header",
            )
        
        # Validate GID format (GID-XX)
        if not gid_auth.startswith("GID-"):
            return AuthValidationResult(
                is_valid=False,
                error="Invalid X-GID-AUTH format. Expected: GID-XX",
            )
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return AuthValidationResult(
                is_valid=False,
                error="Missing Authorization header",
            )
        
        # Parse Bearer token
        if not auth_header.startswith("Bearer "):
            return AuthValidationResult(
                is_valid=False,
                error="Invalid Authorization header format. Expected: Bearer <token>",
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate token with auth service
        session = self._auth_service.validate_session(token)
        if session is None:
            return AuthValidationResult(
                is_valid=False,
                error="Invalid or expired session token",
            )
        
        # Session was validated by validate_session (which checks expiry)
        # so if we get here, it's valid
        
        return AuthValidationResult(
            is_valid=True,
            session_id=str(session.session_id),
            operator_id=session.operator_id,
            permissions=[p.value for p in session.permissions],
        )


# =============================================================================
# AUDIT LOGGER
# =============================================================================


@dataclass
class SecurityAuditEntry:
    """Audit log entry for security events."""
    
    timestamp: str
    event_type: str
    path: str
    method: str
    client_id: str
    session_id: Optional[str]
    operator_id: Optional[str]
    outcome: str
    details: Dict[str, str] = field(default_factory=dict)


class SecurityAuditLogger:
    """
    Logs security-relevant events for OCC endpoints.
    """
    
    def __init__(self) -> None:
        self._entries: List[SecurityAuditEntry] = []
        self._max_entries = 10000
    
    def log(
        self,
        event_type: str,
        request: Request,
        outcome: str,
        session_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a security event."""
        client_id = request.client.host if request.client else "unknown"
        
        entry = SecurityAuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            path=request.url.path,
            method=request.method,
            client_id=client_id,
            session_id=session_id,
            operator_id=operator_id,
            outcome=outcome,
            details=details or {},
        )
        
        self._entries.append(entry)
        
        # Trim old entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
    
    def get_entries(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> List[SecurityAuditEntry]:
        """Get audit entries, newest first."""
        entries = self._entries
        
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        
        return list(reversed(entries[-limit:]))


# Global audit logger instance
_audit_logger: Optional[SecurityAuditLogger] = None


def get_security_audit_logger() -> SecurityAuditLogger:
    """Get or create the security audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger()
    return _audit_logger


def reset_security_audit_logger() -> None:
    """Reset the audit logger (for testing)."""
    global _audit_logger
    _audit_logger = None


# =============================================================================
# MIDDLEWARE
# =============================================================================


class OCCSecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for OCC endpoints.
    
    Applies:
    - Rate limiting
    - Auth validation
    - Audit logging
    """
    
    def __init__(self, app, occ_path_prefix: str = "/occ") -> None:
        super().__init__(app)
        self._occ_prefix = occ_path_prefix
        self._rate_limiter = get_rate_limiter()
        self._auth_validator = AuthValidator()
        self._audit_logger = get_security_audit_logger()
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request through security guards."""
        path = request.url.path
        
        # Only apply to OCC paths
        if not path.startswith(self._occ_prefix):
            return await call_next(request)
        
        # Step 1: Rate limiting
        rate_limit_response = self._rate_limiter.check_rate_limit(request)
        if rate_limit_response:
            self._audit_logger.log(
                event_type="RATE_LIMIT_EXCEEDED",
                request=request,
                outcome="BLOCKED",
            )
            return rate_limit_response
        
        # Step 2: Auth validation
        auth_result = self._auth_validator.validate_request(request)
        if not auth_result.is_valid:
            self._audit_logger.log(
                event_type="AUTH_FAILURE",
                request=request,
                outcome="BLOCKED",
                details={"error": auth_result.error or "Unknown"},
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "UNAUTHORIZED",
                    "message": auth_result.error,
                },
            )
        
        # Step 3: Log successful access
        self._audit_logger.log(
            event_type="ACCESS",
            request=request,
            outcome="ALLOWED",
            session_id=auth_result.session_id,
            operator_id=auth_result.operator_id,
        )
        
        # Process request
        response = await call_next(request)
        
        return response


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "get_rate_limiter",
    "reset_rate_limiter",
    "AuthValidator",
    "AuthValidationResult",
    "SecurityAuditLogger",
    "SecurityAuditEntry",
    "get_security_audit_logger",
    "reset_security_audit_logger",
    "OCCSecurityMiddleware",
]
