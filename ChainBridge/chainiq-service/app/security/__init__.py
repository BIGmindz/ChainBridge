"""
ChainIQ Security Module (SAM GID-06)

Security primitives for ChainIQ service including:
- FusionGuard: Memory safety and input validation
- Rate limiting
- Strict serialization
- Timing attack mitigations

Author: SAM (GID-06) - Security & Threat Engineer
"""

from .fusion_guard import (
    FusionGuard,
    FusionRateLimitError,
    FusionSecurityError,
    FusionValidationError,
    RateLimiter,
    SecureSerializer,
    TimingSafeCompare,
    get_fusion_guard,
    validate_fusion_input,
)

__all__ = [
    "FusionGuard",
    "FusionSecurityError",
    "FusionRateLimitError",
    "FusionValidationError",
    "RateLimiter",
    "SecureSerializer",
    "TimingSafeCompare",
    "get_fusion_guard",
    "validate_fusion_input",
]
