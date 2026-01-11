"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        ECONOMY MODULE - THE MINT & EXCHANGE                  ║
║                       Phase 4: Economic Sovereignty                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  "We do not just move money; we create it (responsibly)."                    ║
║  "Flow is Life. Stagnation is Death."                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

This module provides the economic primitives for ChainBridge:
  - Native Asset creation and management (P410)
  - Controlled issuance (Sovereign minting)
  - Freeze and clawback capabilities (Compliance)
  - Supply conservation enforcement
  - Oracle-Driven FX Exchange (P420)
  - Atomic PvP Settlement

Components:
  - Asset: Token definition with metadata
  - AssetFactory: Mint, transfer, burn operations
  - AssetRegistry: Track all assets in the system
  - LiquidityEngine: Oracle-driven swap protocol
  - LiquidityPool: Trading pair reserves
"""

from .assets import (
    # Models
    Asset,
    AssetAccount,
    AssetTransfer,
    AssetOperation,
    
    # Enums
    AssetStatus,
    OperationType,
    
    # Factory
    AssetFactory,
    
    # Registry
    AssetRegistry,
    
    # Exceptions
    AssetError,
    InsufficientBalanceError,
    AssetFrozenError,
    UnauthorizedError,
    DuplicateTickerError,
)

from .exchange import (
    # Engine
    LiquidityEngine,
    
    # Models
    LiquidityPool,
    LPPosition,
    SwapResult,
    
    # Oracle
    Oracle,
    MockOracle,
    
    # Enums
    SwapStatus,
    PoolStatus,
    
    # Exceptions
    ExchangeError,
    InsufficientLiquidityError,
    OraclePriceError,
    PriceDeviationError,
    AtomicSettlementError,
)

__all__ = [
    # Models
    "Asset",
    "AssetAccount",
    "AssetTransfer",
    "AssetOperation",
    
    # Enums
    "AssetStatus",
    "OperationType",
    
    # Factory
    "AssetFactory",
    
    # Registry
    "AssetRegistry",
    
    # Exceptions (Assets)
    "AssetError",
    "InsufficientBalanceError",
    "AssetFrozenError",
    "UnauthorizedError",
    "DuplicateTickerError",
    
    # Exchange (P420)
    "LiquidityEngine",
    "LiquidityPool",
    "LPPosition",
    "SwapResult",
    "Oracle",
    "MockOracle",
    "SwapStatus",
    "PoolStatus",
    
    # Exceptions (Exchange)
    "ExchangeError",
    "InsufficientLiquidityError",
    "OraclePriceError",
    "PriceDeviationError",
    "AtomicSettlementError",
]

__version__ = "3.0.0"
