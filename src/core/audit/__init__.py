"""
ChainAudit — Immutable Persistence Layer (PAC-OCC-P30)
The Black Box for ChainBridge Constitutional AI.

"If it isn't in the DB, it didn't happen."
"""

from .models import AuditLog, Base
from .recorder import AuditRecorder, get_recorder

__all__ = ["AuditLog", "Base", "AuditRecorder", "get_recorder"]
