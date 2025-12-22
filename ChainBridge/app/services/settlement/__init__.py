"""Settlement Services Module.

════════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEERING)
PAC-CODY-A6-BACKEND-GUARDRAILS-CORRECTION-AND-REALIGNMENT-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: CODY
GID: GID-01
EXECUTING COLOR: 🔵 BLUE — Backend Engineering Lane

⸻

Settlement services with mandatory backend guards.

⸻

PROHIBITED:
- Identity drift
- Color violation
- Lane bypass

════════════════════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════════════════════
# END — CODY (GID-01) — 🔵 BLUE
# 🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
# ════════════════════════════════════════════════════════════════════════════════
