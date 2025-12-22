"""Settlement Services Module.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🔵 BLUE                                             ║
║ PAC: PAC-CODY-A6-BACKEND-GUARDRAILS-01                               ║
╚══════════════════════════════════════════════════════════════════════╝

Settlement services with mandatory backend guards.
"""
from app.services.settlement.gate import (
    SettlementGate,
    SettlementGateResult,
    SettlementBlockReason,
    validate_settlement_request,
    block_direct_settlement,
)

__all__ = [
    "SettlementGate",
    "SettlementGateResult",
    "SettlementBlockReason",
    "validate_settlement_request",
    "block_direct_settlement",
]
