"""
ChainBridge Governance Module
PAC-P820-SCRAM-IMPLEMENTATION v1.0.0

This module provides constitutional enforcement mechanisms:
- SCRAM: Emergency halt protocol (kill switch)
- TGL: Test Governance Layer (coming in P823)
- Policy enforcement (coming in P824)
"""

from core.governance.scram import (
    SCRAMController,
    SCRAMState,
    SCRAMReason,
    SCRAMKey,
    SCRAMAuditEvent,
    get_scram_controller,
    emergency_scram
)

__all__ = [
    "SCRAMController",
    "SCRAMState",
    "SCRAMReason",
    "SCRAMKey",
    "SCRAMAuditEvent",
    "get_scram_controller",
    "emergency_scram"
]

__version__ = "1.0.0"
__pac_id__ = "PAC-P820-SCRAM-IMPLEMENTATION"
