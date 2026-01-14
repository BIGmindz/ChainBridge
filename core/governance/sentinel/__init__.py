"""
ChainBridge Sentinel Deep-Audit Framework
PAC-SENTINEL-DEEP-AUDIT-14

6-Guard Defense Matrix for runtime logic verification.
"""

from .deep_audit import (
    SentinelDeepAudit,
    SentinelAuditReport,
    GuardReport,
    ProofTrace,
    GuardType,
    AuditResult,
    run_sentinel_deep_audit,
)

__all__ = [
    "SentinelDeepAudit",
    "SentinelAuditReport",
    "GuardReport",
    "ProofTrace",
    "GuardType",
    "AuditResult",
    "run_sentinel_deep_audit",
]
