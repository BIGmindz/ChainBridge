"""
ChainBridge Sovereign Swarm API Package
PAC-BLIND-PORTAL-28 | JOB B

This package provides REST API endpoints for:
- Blind Portal: Zero-PII vetting of .cbh files
- Module interaction and extensibility

Exports:
- BlindPortalOrchestrator: Main portal controller
- CBHValidator: .cbh file validator
- BlindVettingEngine: Identity gate vetting engine
- GIDTokenManager: One-time token manager
- BlindAuditResponse: Standardized response schema
- PortalSecurityLimits: Security constants
"""

# Blind Portal exports
from api.blind_portal import (
    BlindPortalOrchestrator,
    CBHValidator,
    BlindVettingEngine,
    GIDTokenManager,
    BlindAuditResponse,
    PortalSecurityLimits,
    ProgressEngine,
    ProgressUpdate,
    PortalSession,
    SessionStatus,
    VettingResult,
    VettedRecord,
    SecurityEvent,
    SecurityEventType,
    run_portal_test,
)

__all__ = [
    "BlindPortalOrchestrator",
    "CBHValidator",
    "BlindVettingEngine",
    "GIDTokenManager",
    "BlindAuditResponse",
    "PortalSecurityLimits",
    "ProgressEngine",
    "ProgressUpdate",
    "PortalSession",
    "SessionStatus",
    "VettingResult",
    "VettedRecord",
    "SecurityEvent",
    "SecurityEventType",
    "run_portal_test",
]

__version__ = "1.0.0"
__pac__ = "PAC-BLIND-PORTAL-28"
