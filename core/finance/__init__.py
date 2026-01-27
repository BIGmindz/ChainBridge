"""
ChainBridge Sovereign Finance Package
PAC-PILOT-STRIKE-01 | Financial Finality Module
PAC-FIN-P80 | Sovereign Treasury Activation

This package provides revenue recognition, ARR management, and treasury allocation:
- Revenue Settlement Engine: Deal capture and settlement
- ARR Engine: Annual Recurring Revenue calculations
- Epoch Closure Engine: Master BER generation
- Sovereign Treasury: Deterministic liquidity management with quantum signatures

Exports:
- PilotStrikeOrchestrator: Main strike coordinator
- RevenueSettlementEngine: Deal settlement handler
- ARREngine: ARR calculation engine
- EpochClosureEngine: Closure report generator
- DealRecord: Deal data structure
- ARRSnapshot: ARR snapshot structure
- SovereignTreasury: Treasury allocation manager (PAC-FIN-P80)
- AllocationPolicy: Treasury policy definition (PAC-FIN-P80)
- AllocationMandate: Signed allocation mandate (PAC-FIN-P80)
- get_global_treasury: Global treasury singleton (PAC-FIN-P80)
"""

from core.finance.revenue_settlement import (
    PilotStrikeOrchestrator,
    RevenueSettlementEngine,
    ARREngine,
    EpochClosureEngine,
    DealRecord,
    ARRSnapshot,
    EpochClosureReport,
    DealStatus,
    RevenueType,
    SettlementResult,
    BASELINE_ARR_USD,
    GENESIS_ANCHOR,
    EPOCH_001,
    execute_megacorp_alpha_strike,
)

# PAC-FIN-P80: Sovereign Treasury
from core.finance.treasury import (
    SovereignTreasury,
    AllocationPolicy,
    AllocationMandate,
    get_global_treasury,
)

__all__ = [
    # Revenue & ARR (PAC-PILOT-STRIKE-01)
    "PilotStrikeOrchestrator",
    "RevenueSettlementEngine",
    "ARREngine",
    "EpochClosureEngine",
    "DealRecord",
    "ARRSnapshot",
    "EpochClosureReport",
    "DealStatus",
    "RevenueType",
    "SettlementResult",
    "BASELINE_ARR_USD",
    "GENESIS_ANCHOR",
    "EPOCH_001",
    "execute_megacorp_alpha_strike",
    # Treasury (PAC-FIN-P80)
    "SovereignTreasury",
    "AllocationPolicy",
    "AllocationMandate",
    "get_global_treasury",
]

__version__ = "1.0.0"
__pac__ = "PAC-PILOT-STRIKE-01"
