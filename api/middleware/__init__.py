"""
ChainBridge Authentication Middleware Stack
============================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING v2.0.0
GOVERNANCE_TIER: POLICY
PRIORITY: 2 (Critical Security Gap)
MODE: MAXIMUM QUALITY

INVARIANTS:
  INV-AUTH-001: All API requests MUST pass authentication (fail-closed)
  INV-AUTH-002: GID binding MUST be verified against gid_registry.json
  INV-AUTH-003: Session state MUST be Redis-backed with TTL enforcement
  INV-AUTH-004: Rate limiting MUST use sliding window per endpoint
  INV-AUTH-005: Request signatures MUST be cryptographically verified
  INV-AUTH-014: High-risk auth MUST trigger MFA challenge (MAGGIE enforced)
  INV-AUTH-015: Risk score MUST be computed on every request (ChainIQ integration)
  INV-AUTH-016: Biometric auth MUST be hardware-backed when available
  INV-AUTH-017: Biometric templates MUST never leave secure enclave
  INV-AUTH-018: Hardware token verification MUST check attestation chain
  INV-AUTH-019: All auth events MUST be logged to audit stream
  INV-AUTH-020: Audit records MUST be immutable once written

STACK ORDER (applied bottom-to-top, 11 middleware layers):
  1. RateLimitMiddleware      - First line of defense, prevents abuse
  2. SignatureMiddleware      - Verify request integrity
  3. RiskBasedAuthMiddleware  - ML-powered risk scoring
  4. AuthMiddleware           - JWT/API key validation
  5. IdentityMiddleware       - GID registry binding
  6. SessionMiddleware        - Redis session management
  7. MFAMiddleware            - Multi-factor authentication
  8. BiometricMiddleware      - WebAuthn/FIDO2 biometric auth
  9. HardwareTokenMiddleware  - TPM/HSM hardware-bound auth
  10. AuditStreamMiddleware   - Real-time audit event streaming

USAGE:
    from api.middleware import apply_auth_stack, apply_enterprise_auth_stack

    # Basic stack (6 middleware)
    apply_auth_stack(app)

    # Enterprise stack (all 11 middleware)
    apply_enterprise_auth_stack(app)
"""

# Core middleware (v1.0)
from .audit_stream import AuditConfig, AuditEventType, AuditStream, AuditStreamMiddleware
from .auth import AuthConfig, AuthMiddleware
from .biometric import BiometricConfig, BiometricMiddleware, WebAuthnRPHandler
from .hardware_token import HardwareTokenConfig, HardwareTokenMiddleware, HardwareTokenType
from .identity import GIDValidator, IdentityMiddleware

# Enterprise middleware (v2.0)
from .mfa import MFAConfig, MFAMethod, MFAMiddleware, OTPManager, TOTPGenerator
from .rate_limit import RateLimitConfig, RateLimitMiddleware
from .risk_based_auth import RiskBasedAuthMiddleware, RiskConfig, RiskLevel, RiskScorer
from .session import SessionManager, SessionMiddleware
from .signature import SignatureMiddleware, SignatureVerifier

__all__ = [
    # Core middleware classes
    "AuthMiddleware",
    "IdentityMiddleware",
    "SessionMiddleware",
    "RateLimitMiddleware",
    "SignatureMiddleware",
    # Enterprise middleware classes
    "MFAMiddleware",
    "RiskBasedAuthMiddleware",
    "BiometricMiddleware",
    "HardwareTokenMiddleware",
    "AuditStreamMiddleware",
    # Configuration classes
    "AuthConfig",
    "RateLimitConfig",
    "MFAConfig",
    "RiskConfig",
    "BiometricConfig",
    "HardwareTokenConfig",
    "AuditConfig",
    # Utility classes
    "GIDValidator",
    "SessionManager",
    "SignatureVerifier",
    "TOTPGenerator",
    "OTPManager",
    "RiskScorer",
    "RiskLevel",
    "WebAuthnRPHandler",
    "HardwareTokenType",
    "AuditStream",
    "AuditEventType",
    "MFAMethod",
    # Stack application functions
    "apply_auth_stack",
    "apply_enterprise_auth_stack",
]

# Exempt paths that do not require authentication
DEFAULT_EXEMPT_PATHS = frozenset({
    "/",
    "/health",
    "/healthz",
    "/ready",
    "/readyz",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    # Biometric and hardware token registration endpoints
    "/auth/biometric/register/options",
    "/auth/biometric/authenticate/options",
    "/auth/hardware/challenge",
})


def apply_auth_stack(
    app,
    exempt_paths: frozenset = DEFAULT_EXEMPT_PATHS,
    enable_rate_limit: bool = True,
    enable_signature: bool = True,
    enable_session: bool = True,
    redis_url: str = "redis://localhost:6379/0",
) -> None:
    """
    Apply the basic authentication middleware stack to a FastAPI application.

    This applies the core 6-middleware stack for standard authentication.
    For enterprise features, use apply_enterprise_auth_stack().

    Middleware is applied in reverse order because FastAPI processes them
    as a LIFO stack (last added = first executed).

    Args:
        app: FastAPI application instance
        exempt_paths: Paths that bypass authentication
        enable_rate_limit: Enable rate limiting middleware
        enable_signature: Enable signature verification middleware
        enable_session: Enable Redis session management
        redis_url: Redis connection URL for session storage

    Execution Order (per request):
        1. RateLimitMiddleware (if enabled)
        2. SignatureMiddleware (if enabled)
        3. AuthMiddleware (always)
        4. IdentityMiddleware (always)
        5. SessionMiddleware (if enabled)
    """
    # Apply in reverse order (last added = first executed)

    # 5. Session management (last to execute)
    if enable_session:
        app.add_middleware(
            SessionMiddleware,
            redis_url=redis_url,
            exempt_paths=exempt_paths,
        )

    # 4. Identity/GID verification
    app.add_middleware(
        IdentityMiddleware,
        exempt_paths=exempt_paths,
    )

    # 3. Core authentication
    app.add_middleware(
        AuthMiddleware,
        exempt_paths=exempt_paths,
    )

    # 2. Signature verification
    if enable_signature:
        app.add_middleware(
            SignatureMiddleware,
            exempt_paths=exempt_paths,
        )

    # 1. Rate limiting (first to execute)
    if enable_rate_limit:
        app.add_middleware(
            RateLimitMiddleware,
            exempt_paths=exempt_paths,
        )


def apply_enterprise_auth_stack(
    app,
    exempt_paths: frozenset = DEFAULT_EXEMPT_PATHS,
    redis_url: str = "redis://localhost:6379/0",
    redis_client=None,
    enable_rate_limit: bool = True,
    enable_signature: bool = True,
    enable_session: bool = True,
    enable_mfa: bool = True,
    enable_risk_scoring: bool = True,
    enable_biometric: bool = True,
    enable_hardware_token: bool = True,
    enable_audit_stream: bool = True,
    mfa_config: MFAConfig = None,
    risk_config: RiskConfig = None,
    biometric_config: BiometricConfig = None,
    hardware_config: HardwareTokenConfig = None,
    audit_config: AuditConfig = None,
) -> None:
    """
    Apply the full enterprise authentication middleware stack.

    This applies all 11 middleware layers for maximum security:
    - Core authentication (JWT, API keys)
    - GID identity binding
    - Redis session management
    - Rate limiting with sliding window
    - Cryptographic request signatures
    - Multi-factor authentication (TOTP, SMS, push)
    - ML-powered risk-based authentication
    - WebAuthn/FIDO2 biometric authentication
    - TPM/HSM hardware token binding
    - Real-time audit event streaming

    Args:
        app: FastAPI application instance
        exempt_paths: Paths that bypass authentication
        redis_url: Redis connection URL
        redis_client: Pre-initialized Redis client (optional)
        enable_*: Feature toggles for each middleware
        *_config: Configuration objects for each middleware

    Execution Order (per request):
        1. RateLimitMiddleware
        2. AuditStreamMiddleware (captures all requests)
        3. SignatureMiddleware
        4. RiskBasedAuthMiddleware
        5. AuthMiddleware
        6. IdentityMiddleware
        7. SessionMiddleware
        8. MFAMiddleware
        9. BiometricMiddleware
        10. HardwareTokenMiddleware
    """
    # Apply in reverse order (last added = first executed)

    # 10. Hardware token authentication
    if enable_hardware_token:
        app.add_middleware(
            HardwareTokenMiddleware,
            config=hardware_config,
            redis_client=redis_client,
            exempt_paths=exempt_paths,
        )

    # 9. Biometric authentication
    if enable_biometric:
        app.add_middleware(
            BiometricMiddleware,
            config=biometric_config,
            redis_client=redis_client,
            exempt_paths=exempt_paths,
        )

    # 8. MFA challenges
    if enable_mfa:
        app.add_middleware(
            MFAMiddleware,
            config=mfa_config,
            redis_client=redis_client,
            exempt_paths=exempt_paths,
        )

    # 7. Session management
    if enable_session:
        app.add_middleware(
            SessionMiddleware,
            redis_url=redis_url,
            exempt_paths=exempt_paths,
        )

    # 6. Identity/GID verification
    app.add_middleware(
        IdentityMiddleware,
        exempt_paths=exempt_paths,
    )

    # 5. Core authentication
    app.add_middleware(
        AuthMiddleware,
        exempt_paths=exempt_paths,
    )

    # 4. Risk-based authentication
    if enable_risk_scoring:
        app.add_middleware(
            RiskBasedAuthMiddleware,
            config=risk_config,
            redis_client=redis_client,
            exempt_paths=exempt_paths,
        )

    # 3. Signature verification
    if enable_signature:
        app.add_middleware(
            SignatureMiddleware,
            exempt_paths=exempt_paths,
        )

    # 2. Audit stream (captures all requests early)
    if enable_audit_stream:
        app.add_middleware(
            AuditStreamMiddleware,
            config=audit_config,
            redis_client=redis_client,
            exempt_paths=frozenset(),  # Audit everything
        )

    # 1. Rate limiting (first to execute)
    if enable_rate_limit:
        app.add_middleware(
            RateLimitMiddleware,
            exempt_paths=exempt_paths,
        )
