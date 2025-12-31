"""
ChainBridge Settlement Core — PDO-Gated Settlement Enforcement
════════════════════════════════════════════════════════════════════════════════

This package provides the PDO-gated settlement enforcement layer.

PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-SETTLEMENT-EXEC-006C
Effective Date: 2025-12-30

INVARIANTS:
    INV-SETTLEMENT-001: No settlement without valid PDO
    INV-SETTLEMENT-002: No milestone without milestone PDO
    INV-SETTLEMENT-003: No state change without ledger append
    INV-SETTLEMENT-004: Ledger failure aborts settlement
    INV-SETTLEMENT-005: All transitions auditable

════════════════════════════════════════════════════════════════════════════════
"""

from core.settlement.settlement_engine import (
    SettlementEngine,
    SettlementRequest,
    SettlementResult,
    SettlementError,
    SettlementPDORequiredError,
    SettlementLedgerFailureError,
    get_settlement_engine,
    reset_settlement_engine,
)

from core.settlement.settlement_state_machine import (
    SettlementStateMachine,
    SettlementState,
    MilestoneState,
    SettlementTransition,
    MilestoneTransition,
    StateTransitionError,
    MilestonePDORequiredError,
)


__all__ = [
    # Engine
    "SettlementEngine",
    "SettlementRequest",
    "SettlementResult",
    "get_settlement_engine",
    "reset_settlement_engine",
    
    # State Machine
    "SettlementStateMachine",
    "SettlementState",
    "MilestoneState",
    "SettlementTransition",
    "MilestoneTransition",
    
    # Exceptions
    "SettlementError",
    "SettlementPDORequiredError",
    "SettlementLedgerFailureError",
    "StateTransitionError",
    "MilestonePDORequiredError",
]
