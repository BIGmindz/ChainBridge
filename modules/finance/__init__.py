"""
ChainBridge Finance Module - The Invisible Bank
================================================

Phase 2 of ChainBridge: From Gatekeeper to Treasurer.

This module provides the financial primitives for holding and moving value:
- Double-entry ledger with cryptographic audit trail
- Account management with balance enforcement
- Atomic transaction processing
- Settlement engine integration

INVARIANTS ENFORCED:
- INV-FIN-001: Conservation of Value (Debits == Credits)
- INV-FIN-002: Immutability (Posted entries cannot be modified)

Created: 2026-01-11
PAC: PAC-FIN-P200-INVISIBLE-BANK-INIT
"""

from modules.finance.ledger import (
    Ledger,
    Account,
    AccountType,
    Entry,
    Transaction,
    TransactionStatus,
    LedgerError,
    InsufficientFundsError,
    BalanceViolationError,
    ImmutabilityViolationError,
)

from modules.finance.settlement import (
    SettlementEngine,
    PaymentIntent,
    IntentStatus,
    CaptureType,
    SettlementError,
    IdempotencyViolationError,
    LifecycleViolationError,
    AmountExceedsAuthorizationError,
    AuthorizationExpiredError,
    IntentNotFoundError,
)

from modules.finance.fees import (
    FeeEngine,
    FeeStrategy,
    FlatFeeStrategy,
    PercentageFeeStrategy,
    CompositeFeeStrategy,
    TieredFeeStrategy,
    FeeBreakdown,
    FeeError,
    FeeExceedsAmountError,
    InvalidFeeConfigurationError,
    create_stripe_strategy,
    create_tiered_percentage_strategy,
)

__all__ = [
    # Ledger Classes
    "Ledger",
    "Account",
    "AccountType",
    "Entry",
    "Transaction",
    "TransactionStatus",
    # Ledger Exceptions
    "LedgerError",
    "InsufficientFundsError",
    "BalanceViolationError",
    "ImmutabilityViolationError",
    # Settlement Classes
    "SettlementEngine",
    "PaymentIntent",
    "IntentStatus",
    "CaptureType",
    # Settlement Exceptions
    "SettlementError",
    "IdempotencyViolationError",
    "LifecycleViolationError",
    "AmountExceedsAuthorizationError",
    "AuthorizationExpiredError",
    "IntentNotFoundError",
    # Fee Classes
    "FeeEngine",
    "FeeStrategy",
    "FlatFeeStrategy",
    "PercentageFeeStrategy",
    "CompositeFeeStrategy",
    "TieredFeeStrategy",
    "FeeBreakdown",
    # Fee Exceptions
    "FeeError",
    "FeeExceedsAmountError",
    "InvalidFeeConfigurationError",
    # Fee Helpers
    "create_stripe_strategy",
    "create_tiered_percentage_strategy",
]

__version__ = "2.0.0"
__phase__ = "INVISIBLE_BANK"
