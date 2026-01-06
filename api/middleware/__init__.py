# ═══════════════════════════════════════════════════════════════════════════════
# API Middleware Package
# PAC-BENSON-P23-C: Parallel Platform Hardening (Corrective)
# PAC-BENSON-P42: OCC Security Middleware
#
# Middleware components for API hardening and enforcement.
#
# Author: CODY (GID-01) — Backend Lead
# Author: DAN (GID-07) — DevOps/Security (OCC Security)
# ═══════════════════════════════════════════════════════════════════════════════

from api.middleware.read_only_enforcement import (
    READ_ONLY_PATH_PREFIXES,
    FORBIDDEN_METHODS,
    WRITE_ALLOWED_PATHS,
    ReadOnlyEnforcementMiddleware,
    reject_mutation,
    EvidenceHashEnforcer,
    audit_request,
)

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
    OCCSecurityMiddleware,
)

__all__ = [
    # Read-only enforcement
    "READ_ONLY_PATH_PREFIXES",
    "FORBIDDEN_METHODS",
    "WRITE_ALLOWED_PATHS",
    "ReadOnlyEnforcementMiddleware",
    "reject_mutation",
    "EvidenceHashEnforcer",
    "audit_request",
    # OCC Security
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
