"""Gateway core deterministic middleware package.

Includes ALEX middleware for ACM enforcement (GID-08).
"""

from gateway.alex_middleware import (
    ALEXMiddleware,
    ALEXMiddlewareError,
    GovernanceAuditLogger,
    IntentDeniedError,
    MiddlewareConfig,
    get_alex_middleware,
    guard_action,
    initialize_alex,
)

__all__ = [
    "ALEXMiddleware",
    "ALEXMiddlewareError",
    "GovernanceAuditLogger",
    "IntentDeniedError",
    "MiddlewareConfig",
    "get_alex_middleware",
    "guard_action",
    "initialize_alex",
]
