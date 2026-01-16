"""
ChainBridge Sovereign Finance Package
PAC-PILOT-STRIKE-01 | Financial Finality Module

This package provides revenue recognition and ARR management:
- Revenue Settlement Engine: Deal capture and settlement
- ARR Engine: Annual Recurring Revenue calculations
- Epoch Closure Engine: Master BER generation

Exports:
- PilotStrikeOrchestrator: Main strike coordinator
- RevenueSettlementEngine: Deal settlement handler
- ARREngine: ARR calculation engine
- EpochClosureEngine: Closure report generator
- DealRecord: Deal data structure
- ARRSnapshot: ARR snapshot structure
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

__all__ = [
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
]

__version__ = "1.0.0"
__pac__ = "PAC-PILOT-STRIKE-01"
