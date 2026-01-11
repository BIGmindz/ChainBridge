#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               LIQUIDITY ENGINE - THE SOVEREIGN EXCHANGE                      ║
║                    PAC-ECON-P420-LIQUIDITY-ENGINE                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Oracle-Driven Swap Protocol for Institutional FX                            ║
║                                                                              ║
║  "Flow is Life. Stagnation is Death."                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Unlike Crypto AMMs (volatile curves), Institutional FX requires Oracle Pricing:
  - Price = Oracle_Rate +/- Spread
  - No slippage for liquidity-backed trades
  - Atomic PvP (Payment vs Payment) settlement

INVARIANTS:
  INV-ECON-005 (PvP Finality): No leg executes without the other
  INV-ECON-006 (Oracle Bound): Execution price cannot deviate from Oracle

Usage:
    from modules.economy.exchange import LiquidityEngine, MockOracle
    
    # Create engine with oracle
    oracle = MockOracle()
    oracle.set_rate("USD/EUR", Decimal("0.92"))
    
    engine = LiquidityEngine(oracle=oracle)
    
    # Create a liquidity pool
    pool = engine.create_pool("USD", "EUR")
    
    # Add liquidity
    engine.add_liquidity("USD/EUR", "LP_001", usd_amount=10000, eur_amount=9200)
    
    # Execute swap
    result = engine.swap(
        pool_id="USD/EUR",
        trader="TRADER_001",
        amount_in=100,
        token_in="USD",
        token_out="EUR"
    )
    # Result: 92 EUR received (at 0.92 rate minus fee)
"""

import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class ExchangeError(Exception):
    """Base exception for exchange operations."""
    pass


class InsufficientLiquidityError(ExchangeError):
    """Raised when pool has insufficient reserves."""
    pass


class OraclePriceError(ExchangeError):
    """Raised when oracle price is unavailable or stale."""
    pass


class PriceDeviationError(ExchangeError):
    """Raised when execution price deviates beyond tolerance (INV-ECON-006)."""
    pass


class AtomicSettlementError(ExchangeError):
    """Raised when atomic settlement fails (INV-ECON-005)."""
    pass


class PoolNotFoundError(ExchangeError):
    """Raised when liquidity pool not found."""
    pass


class InvalidAmountError(ExchangeError):
    """Raised when amount is invalid."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class SwapStatus(Enum):
    """Status of a swap operation."""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    REVERTED = "REVERTED"


class PoolStatus(Enum):
    """Status of a liquidity pool."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DEPLETED = "DEPLETED"


# ══════════════════════════════════════════════════════════════════════════════
# ORACLE INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

class Oracle(ABC):
    """
    Abstract Oracle interface for price feeds.
    
    Production implementations would connect to:
      - Bloomberg/Reuters feeds
      - Central Bank rates
      - Aggregated FX providers
    """
    
    @abstractmethod
    def get_price(self, pair: str) -> Optional[Decimal]:
        """
        Get the current price for a trading pair.
        
        Args:
            pair: Trading pair (e.g., "USD/EUR")
            
        Returns:
            Price as Decimal, or None if unavailable
        """
        pass
        
    @abstractmethod
    def get_price_with_timestamp(self, pair: str) -> Optional[Tuple[Decimal, float]]:
        """
        Get price with timestamp for staleness checks.
        
        Returns:
            Tuple of (price, timestamp) or None
        """
        pass
        
    @abstractmethod
    def is_stale(self, pair: str, max_age_seconds: int = 60) -> bool:
        """Check if the price feed is stale."""
        pass


class MockOracle(Oracle):
    """
    Mock Oracle for testing and development.
    
    In production, this would be replaced with real price feeds.
    """
    
    def __init__(self):
        self._rates: Dict[str, Tuple[Decimal, float]] = {}
        self._default_rates = {
            "USD/EUR": Decimal("0.92"),
            "EUR/USD": Decimal("1.087"),
            "USD/GBP": Decimal("0.79"),
            "GBP/USD": Decimal("1.266"),
            "USD/JPY": Decimal("149.50"),
            "JPY/USD": Decimal("0.00669"),
            "EUR/GBP": Decimal("0.858"),
            "GBP/EUR": Decimal("1.165"),
            "USD/CHF": Decimal("0.88"),
            "CHF/USD": Decimal("1.136"),
        }
        # Initialize with default rates
        for pair, rate in self._default_rates.items():
            self._rates[pair] = (rate, time.time())
            
    def set_rate(self, pair: str, rate: Decimal) -> None:
        """Set a rate for testing."""
        self._rates[pair] = (Decimal(str(rate)), time.time())
        # Also set inverse
        inverse_pair = f"{pair.split('/')[1]}/{pair.split('/')[0]}"
        inverse_rate = Decimal("1") / Decimal(str(rate))
        self._rates[inverse_pair] = (inverse_rate.quantize(Decimal("0.000001")), time.time())
        
    def get_price(self, pair: str) -> Optional[Decimal]:
        if pair in self._rates:
            return self._rates[pair][0]
        return None
        
    def get_price_with_timestamp(self, pair: str) -> Optional[Tuple[Decimal, float]]:
        return self._rates.get(pair)
        
    def is_stale(self, pair: str, max_age_seconds: int = 60) -> bool:
        if pair not in self._rates:
            return True
        _, timestamp = self._rates[pair]
        return (time.time() - timestamp) > max_age_seconds


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LiquidityPool:
    """
    A liquidity pool for a trading pair.
    
    Institutional FX pools differ from AMM pools:
      - Price is set by Oracle, not by reserve ratio
      - LPs earn fees but don't suffer impermanent loss from price movement
      - Reserves must cover the trade (no virtual liquidity)
    """
    
    pool_id: str                              # e.g., "USD/EUR"
    token_a: str                              # Base token (e.g., "USD")
    token_b: str                              # Quote token (e.g., "EUR")
    reserve_a: Decimal = Decimal("0")         # Reserve of token A
    reserve_b: Decimal = Decimal("0")         # Reserve of token B
    fee_bps: int = 10                         # Fee in basis points (10 = 0.1%)
    status: PoolStatus = PoolStatus.ACTIVE
    total_volume_a: Decimal = Decimal("0")    # Cumulative volume
    total_volume_b: Decimal = Decimal("0")
    total_fees_a: Decimal = Decimal("0")      # Accumulated fees
    total_fees_b: Decimal = Decimal("0")
    swap_count: int = 0
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "token_a": self.token_a,
            "token_b": self.token_b,
            "reserve_a": str(self.reserve_a),
            "reserve_b": str(self.reserve_b),
            "fee_bps": self.fee_bps,
            "status": self.status.value,
            "total_volume_a": str(self.total_volume_a),
            "total_volume_b": str(self.total_volume_b),
            "total_fees_a": str(self.total_fees_a),
            "total_fees_b": str(self.total_fees_b),
            "swap_count": self.swap_count,
            "created_at": self.created_at
        }


@dataclass
class LPPosition:
    """Liquidity Provider's position in a pool."""
    
    position_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    pool_id: str = ""
    provider: str = ""                # LP address
    deposited_a: Decimal = Decimal("0")
    deposited_b: Decimal = Decimal("0")
    share_pct: Decimal = Decimal("0")  # Share of pool (for fee distribution)
    earned_fees_a: Decimal = Decimal("0")
    earned_fees_b: Decimal = Decimal("0")
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "pool_id": self.pool_id,
            "provider": self.provider,
            "deposited_a": str(self.deposited_a),
            "deposited_b": str(self.deposited_b),
            "share_pct": str(self.share_pct),
            "earned_fees_a": str(self.earned_fees_a),
            "earned_fees_b": str(self.earned_fees_b)
        }


@dataclass
class SwapResult:
    """Result of a swap operation."""
    
    swap_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pool_id: str = ""
    trader: str = ""
    token_in: str = ""
    token_out: str = ""
    amount_in: Decimal = Decimal("0")
    amount_out: Decimal = Decimal("0")
    fee_amount: Decimal = Decimal("0")
    oracle_rate: Decimal = Decimal("0")
    effective_rate: Decimal = Decimal("0")
    status: SwapStatus = SwapStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "swap_id": self.swap_id,
            "pool_id": self.pool_id,
            "trader": self.trader,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "amount_in": str(self.amount_in),
            "amount_out": str(self.amount_out),
            "fee_amount": str(self.fee_amount),
            "oracle_rate": str(self.oracle_rate),
            "effective_rate": str(self.effective_rate),
            "status": self.status.value,
            "timestamp": self.timestamp,
            "error": self.error
        }


# ══════════════════════════════════════════════════════════════════════════════
# LIQUIDITY ENGINE - THE SOVEREIGN EXCHANGE
# ══════════════════════════════════════════════════════════════════════════════

class LiquidityEngine:
    """
    Oracle-Driven Swap Protocol for Institutional FX.
    
    Key Differences from AMM (Uniswap-style):
      1. Price is set by Oracle, not by x*y=k curve
      2. No slippage for liquidity-backed trades
      3. Atomic PvP settlement (both legs or neither)
      4. LP fee is fixed basis points, not curve-dependent
      
    INVARIANTS:
      INV-ECON-005 (PvP Finality): No leg executes without the other
      INV-ECON-006 (Oracle Bound): Price cannot deviate from Oracle
    """
    
    # Maximum allowed deviation from oracle price (in basis points)
    MAX_PRICE_DEVIATION_BPS = 50  # 0.5%
    
    # Default stale price threshold (seconds)
    MAX_ORACLE_AGE = 60
    
    def __init__(
        self,
        oracle: Optional[Oracle] = None,
        fee_bps: int = 10,
        max_deviation_bps: int = 50
    ):
        """
        Initialize the Liquidity Engine.
        
        Args:
            oracle: Price oracle (defaults to MockOracle)
            fee_bps: Default fee in basis points
            max_deviation_bps: Max price deviation from oracle
        """
        self.oracle = oracle or MockOracle()
        self.default_fee_bps = fee_bps
        self.max_deviation_bps = max_deviation_bps
        
        self._pools: Dict[str, LiquidityPool] = {}
        self._positions: Dict[str, LPPosition] = {}  # position_id -> position
        self._swaps: List[SwapResult] = []
        
    # ══════════════════════════════════════════════════════════════════════════
    # POOL MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    
    def create_pool(
        self,
        token_a: str,
        token_b: str,
        fee_bps: Optional[int] = None
    ) -> LiquidityPool:
        """
        Create a new liquidity pool.
        
        Args:
            token_a: Base token symbol
            token_b: Quote token symbol
            fee_bps: Fee in basis points (optional)
            
        Returns:
            The created LiquidityPool
        """
        pool_id = f"{token_a}/{token_b}"
        
        if pool_id in self._pools:
            raise ExchangeError(f"Pool '{pool_id}' already exists")
            
        pool = LiquidityPool(
            pool_id=pool_id,
            token_a=token_a,
            token_b=token_b,
            fee_bps=fee_bps or self.default_fee_bps
        )
        
        self._pools[pool_id] = pool
        logger.info(f"🏊 Created pool: {pool_id} (fee: {pool.fee_bps} bps)")
        
        return pool
        
    def get_pool(self, pool_id: str) -> LiquidityPool:
        """Get a pool by ID."""
        if pool_id not in self._pools:
            raise PoolNotFoundError(f"Pool '{pool_id}' not found")
        return self._pools[pool_id]
        
    def list_pools(self) -> List[LiquidityPool]:
        """List all pools."""
        return list(self._pools.values())
        
    # ══════════════════════════════════════════════════════════════════════════
    # LIQUIDITY PROVISION
    # ══════════════════════════════════════════════════════════════════════════
    
    def add_liquidity(
        self,
        pool_id: str,
        provider: str,
        amount_a: Decimal,
        amount_b: Decimal
    ) -> LPPosition:
        """
        Add liquidity to a pool.
        
        Args:
            pool_id: Pool identifier
            provider: LP address
            amount_a: Amount of token A to deposit
            amount_b: Amount of token B to deposit
            
        Returns:
            LPPosition representing the deposit
        """
        pool = self.get_pool(pool_id)
        
        amount_a = Decimal(str(amount_a))
        amount_b = Decimal(str(amount_b))
        
        if amount_a <= 0 or amount_b <= 0:
            raise InvalidAmountError("Deposit amounts must be positive")
            
        # Calculate share (simplified - equal weighting)
        total_before = pool.reserve_a + pool.reserve_b
        deposit_total = amount_a + amount_b
        
        if total_before == 0:
            share_pct = Decimal("100")
        else:
            share_pct = (deposit_total / (total_before + deposit_total)) * 100
            
        # Update pool reserves
        pool.reserve_a += amount_a
        pool.reserve_b += amount_b
        
        # Create position
        position = LPPosition(
            pool_id=pool_id,
            provider=provider,
            deposited_a=amount_a,
            deposited_b=amount_b,
            share_pct=share_pct.quantize(Decimal("0.01"))
        )
        
        self._positions[position.position_id] = position
        
        logger.info(f"💧 Added liquidity: {provider} deposited "
                   f"{amount_a} {pool.token_a} + {amount_b} {pool.token_b} to {pool_id}")
        
        return position
        
    def remove_liquidity(
        self,
        position_id: str,
        provider: str
    ) -> Tuple[Decimal, Decimal]:
        """
        Remove liquidity from a pool.
        
        Args:
            position_id: Position to withdraw
            provider: Must match position owner
            
        Returns:
            Tuple of (amount_a, amount_b) withdrawn
        """
        if position_id not in self._positions:
            raise ExchangeError(f"Position '{position_id}' not found")
            
        position = self._positions[position_id]
        
        if position.provider != provider:
            raise ExchangeError("Only position owner can withdraw")
            
        pool = self.get_pool(position.pool_id)
        
        # Calculate withdrawal based on share
        withdraw_a = (pool.reserve_a * position.share_pct / 100).quantize(Decimal("0.01"))
        withdraw_b = (pool.reserve_b * position.share_pct / 100).quantize(Decimal("0.01"))
        
        # Update pool
        pool.reserve_a -= withdraw_a
        pool.reserve_b -= withdraw_b
        
        # Remove position
        del self._positions[position_id]
        
        logger.info(f"🚰 Removed liquidity: {provider} withdrew "
                   f"{withdraw_a} {pool.token_a} + {withdraw_b} {pool.token_b}")
        
        return withdraw_a, withdraw_b
        
    # ══════════════════════════════════════════════════════════════════════════
    # SWAP - THE CORE OPERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_quote(
        self,
        pool_id: str,
        amount_in: Decimal,
        token_in: str,
        token_out: str
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Get a quote for a swap (without executing).
        
        Args:
            pool_id: Pool to use
            amount_in: Amount of input token
            token_in: Input token symbol
            token_out: Output token symbol
            
        Returns:
            Tuple of (amount_out, fee, oracle_rate)
        """
        pool = self.get_pool(pool_id)
        amount_in = Decimal(str(amount_in))
        
        # Determine the oracle pair
        if token_in == pool.token_a:
            oracle_pair = f"{token_in}/{token_out}"
        else:
            oracle_pair = f"{token_in}/{token_out}"
            
        # Get oracle price
        oracle_rate = self.oracle.get_price(oracle_pair)
        if oracle_rate is None:
            raise OraclePriceError(f"No oracle price for {oracle_pair}")
            
        # Calculate fee
        fee_amount = (amount_in * pool.fee_bps / 10000).quantize(Decimal("0.000001"))
        
        # Calculate output
        net_input = amount_in - fee_amount
        amount_out = (net_input * oracle_rate).quantize(Decimal("0.01"), ROUND_DOWN)
        
        return amount_out, fee_amount, oracle_rate
        
    def swap(
        self,
        pool_id: str,
        trader: str,
        amount_in: Decimal,
        token_in: str,
        token_out: str
    ) -> SwapResult:
        """
        Execute an atomic swap (Payment vs Payment).
        
        This is the core operation of the Liquidity Engine.
        
        INVARIANTS ENFORCED:
          INV-ECON-005: Both legs execute atomically or neither
          INV-ECON-006: Price is oracle-bound
          
        Args:
            pool_id: Pool to use
            trader: Trader address
            amount_in: Amount of input token
            token_in: Input token symbol
            token_out: Output token symbol
            
        Returns:
            SwapResult with execution details
        """
        result = SwapResult(
            pool_id=pool_id,
            trader=trader,
            token_in=token_in,
            token_out=token_out,
            amount_in=Decimal(str(amount_in))
        )
        
        try:
            pool = self.get_pool(pool_id)
            amount_in = Decimal(str(amount_in))
            
            if amount_in <= 0:
                raise InvalidAmountError("Swap amount must be positive")
                
            if pool.status != PoolStatus.ACTIVE:
                raise ExchangeError(f"Pool '{pool_id}' is not active")
                
            # Validate tokens
            if token_in not in (pool.token_a, pool.token_b):
                raise ExchangeError(f"Token '{token_in}' not in pool")
            if token_out not in (pool.token_a, pool.token_b):
                raise ExchangeError(f"Token '{token_out}' not in pool")
            if token_in == token_out:
                raise ExchangeError("Cannot swap same token")
                
            # Get oracle price
            oracle_pair = f"{token_in}/{token_out}"
            oracle_rate = self.oracle.get_price(oracle_pair)
            
            if oracle_rate is None:
                raise OraclePriceError(f"No oracle price for {oracle_pair}")
                
            # Check staleness
            if self.oracle.is_stale(oracle_pair, self.MAX_ORACLE_AGE):
                raise OraclePriceError(f"Oracle price for {oracle_pair} is stale")
                
            result.oracle_rate = oracle_rate
            
            # Calculate fee
            fee_amount = (amount_in * pool.fee_bps / 10000).quantize(Decimal("0.000001"))
            result.fee_amount = fee_amount
            
            # Calculate output amount
            net_input = amount_in - fee_amount
            amount_out = (net_input * oracle_rate).quantize(Decimal("0.01"), ROUND_DOWN)
            result.amount_out = amount_out
            
            # Calculate effective rate
            if amount_in > 0:
                result.effective_rate = (amount_out / amount_in).quantize(Decimal("0.000001"))
                
            # ══════════════════════════════════════════════════════════════════
            # INV-ECON-006: Oracle Bound Check
            # ══════════════════════════════════════════════════════════════════
            deviation_bps = abs(
                ((result.effective_rate - oracle_rate) / oracle_rate) * 10000
            )
            if deviation_bps > self.max_deviation_bps:
                raise PriceDeviationError(
                    f"Price deviation {deviation_bps:.0f} bps exceeds max {self.max_deviation_bps} bps"
                )
                
            # ══════════════════════════════════════════════════════════════════
            # INV-ECON-005: Check Liquidity (Pre-flight for PvP)
            # ══════════════════════════════════════════════════════════════════
            if token_out == pool.token_a:
                if pool.reserve_a < amount_out:
                    raise InsufficientLiquidityError(
                        f"Insufficient {token_out}: need {amount_out}, have {pool.reserve_a}"
                    )
            else:
                if pool.reserve_b < amount_out:
                    raise InsufficientLiquidityError(
                        f"Insufficient {token_out}: need {amount_out}, have {pool.reserve_b}"
                    )
                    
            # ══════════════════════════════════════════════════════════════════
            # ATOMIC SETTLEMENT (PvP)
            # Both legs must succeed or neither executes
            # ══════════════════════════════════════════════════════════════════
            
            # Snapshot for rollback
            reserve_a_before = pool.reserve_a
            reserve_b_before = pool.reserve_b
            
            try:
                # LEG 1: Receive input token
                if token_in == pool.token_a:
                    pool.reserve_a += amount_in
                    pool.total_fees_a += fee_amount
                else:
                    pool.reserve_b += amount_in
                    pool.total_fees_b += fee_amount
                    
                # LEG 2: Send output token
                if token_out == pool.token_a:
                    pool.reserve_a -= amount_out
                else:
                    pool.reserve_b -= amount_out
                    
                # Update stats
                if token_in == pool.token_a:
                    pool.total_volume_a += amount_in
                else:
                    pool.total_volume_b += amount_in
                    
                pool.swap_count += 1
                result.status = SwapStatus.EXECUTED
                
            except Exception as e:
                # ROLLBACK - INV-ECON-005
                pool.reserve_a = reserve_a_before
                pool.reserve_b = reserve_b_before
                raise AtomicSettlementError(f"Settlement failed, rolled back: {e}")
                
            self._swaps.append(result)
            
            logger.info(f"💱 Swap executed: {trader} swapped "
                       f"{amount_in} {token_in} -> {amount_out} {token_out} @ {oracle_rate}")
                       
        except ExchangeError as e:
            result.status = SwapStatus.FAILED
            result.error = str(e)
            self._swaps.append(result)
            raise
            
        return result
        
    # ══════════════════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_reserves(self, pool_id: str) -> Tuple[Decimal, Decimal]:
        """Get current reserves for a pool."""
        pool = self.get_pool(pool_id)
        return pool.reserve_a, pool.reserve_b
        
    def get_swap_history(self, trader: Optional[str] = None) -> List[SwapResult]:
        """Get swap history, optionally filtered by trader."""
        if trader:
            return [s for s in self._swaps if s.trader == trader]
        return self._swaps.copy()
        
    def get_pool_stats(self, pool_id: str) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        pool = self.get_pool(pool_id)
        
        # Get current oracle rate
        oracle_rate = self.oracle.get_price(pool_id)
        
        return {
            "pool_id": pool_id,
            "token_a": pool.token_a,
            "token_b": pool.token_b,
            "reserve_a": str(pool.reserve_a),
            "reserve_b": str(pool.reserve_b),
            "oracle_rate": str(oracle_rate) if oracle_rate else "N/A",
            "fee_bps": pool.fee_bps,
            "total_volume_a": str(pool.total_volume_a),
            "total_volume_b": str(pool.total_volume_b),
            "total_fees_a": str(pool.total_fees_a),
            "total_fees_b": str(pool.total_fees_b),
            "swap_count": pool.swap_count,
            "status": pool.status.value
        }
        
    def verify_pvp_finality(self, swap: SwapResult) -> bool:
        """
        Verify INV-ECON-005: PvP Finality.
        
        Both legs executed atomically.
        """
        if swap.status != SwapStatus.EXECUTED:
            return False
            
        # If swap executed, both legs succeeded
        return swap.amount_in > 0 and swap.amount_out > 0
        
    def verify_oracle_bound(self, swap: SwapResult) -> bool:
        """
        Verify INV-ECON-006: Oracle Bound.
        
        Effective rate within tolerance of oracle rate.
        """
        if swap.oracle_rate == 0:
            return False
            
        deviation = abs(swap.effective_rate - swap.oracle_rate) / swap.oracle_rate
        return deviation * 10000 <= self.max_deviation_bps


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> bool:
    """Run self-tests for the Liquidity Engine."""
    print("=" * 70)
    print("           LIQUIDITY ENGINE SELF-TEST")
    print("           The Sovereign Exchange")
    print("=" * 70)
    
    tests_passed = 0
    tests_total = 0
    
    # Initialize
    oracle = MockOracle()
    oracle.set_rate("USD/EUR", Decimal("0.92"))
    engine = LiquidityEngine(oracle=oracle, fee_bps=10)
    
    # Test 1: Create Pool
    tests_total += 1
    print("\n[TEST 1] Create Liquidity Pool...")
    try:
        pool = engine.create_pool("USD", "EUR")
        assert pool.pool_id == "USD/EUR"
        assert pool.fee_bps == 10
        print(f"  ✅ PASSED: Created pool USD/EUR (fee: {pool.fee_bps} bps)")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 2: Add Liquidity
    tests_total += 1
    print("\n[TEST 2] Add Liquidity...")
    try:
        position = engine.add_liquidity(
            "USD/EUR",
            provider="LP_001",
            amount_a=Decimal("10000"),
            amount_b=Decimal("9200")
        )
        reserves = engine.get_reserves("USD/EUR")
        assert reserves[0] == Decimal("10000")
        assert reserves[1] == Decimal("9200")
        print(f"  ✅ PASSED: Deposited 10,000 USD + 9,200 EUR")
        print(f"            Reserves: {reserves[0]} USD, {reserves[1]} EUR")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 3: Get Quote
    tests_total += 1
    print("\n[TEST 3] Get Swap Quote...")
    try:
        amount_out, fee, rate = engine.get_quote(
            "USD/EUR",
            amount_in=Decimal("100"),
            token_in="USD",
            token_out="EUR"
        )
        print(f"  ✅ PASSED: 100 USD -> {amount_out} EUR @ {rate}")
        print(f"            Fee: {fee} USD")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 4: Execute Swap
    tests_total += 1
    print("\n[TEST 4] Execute Swap (100 USD -> EUR)...")
    try:
        result = engine.swap(
            pool_id="USD/EUR",
            trader="TRADER_001",
            amount_in=Decimal("100"),
            token_in="USD",
            token_out="EUR"
        )
        assert result.status == SwapStatus.EXECUTED
        assert result.amount_out > 0
        print(f"  ✅ PASSED: Swapped 100 USD -> {result.amount_out} EUR")
        print(f"            Oracle Rate: {result.oracle_rate}")
        print(f"            Effective Rate: {result.effective_rate}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 5: PvP Finality (INV-ECON-005)
    tests_total += 1
    print("\n[TEST 5] PvP Finality (INV-ECON-005)...")
    try:
        assert engine.verify_pvp_finality(result)
        reserves = engine.get_reserves("USD/EUR")
        # Pool should have more USD (received), less EUR (sent)
        assert reserves[0] > Decimal("10000")  # Received 100 USD
        assert reserves[1] < Decimal("9200")   # Sent ~92 EUR
        print(f"  ✅ PASSED: Both legs executed atomically")
        print(f"            New Reserves: {reserves[0]} USD, {reserves[1]} EUR")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 6: Oracle Bound (INV-ECON-006)
    tests_total += 1
    print("\n[TEST 6] Oracle Bound (INV-ECON-006)...")
    try:
        assert engine.verify_oracle_bound(result)
        deviation = abs(result.effective_rate - result.oracle_rate) / result.oracle_rate * 10000
        print(f"  ✅ PASSED: Price deviation {deviation:.2f} bps (max: {engine.max_deviation_bps})")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 7: Insufficient Liquidity Protection
    tests_total += 1
    print("\n[TEST 7] Insufficient Liquidity Protection...")
    try:
        try:
            # Try to swap more than available
            engine.swap(
                pool_id="USD/EUR",
                trader="TRADER_002",
                amount_in=Decimal("1000000"),  # 1M USD
                token_in="USD",
                token_out="EUR"
            )
            print("  ❌ FAILED: Should have rejected due to insufficient liquidity")
        except InsufficientLiquidityError:
            print(f"  ✅ PASSED: Correctly rejected (insufficient liquidity)")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 8: Reverse Swap (EUR -> USD)
    tests_total += 1
    print("\n[TEST 8] Reverse Swap (EUR -> USD)...")
    try:
        oracle.set_rate("EUR/USD", Decimal("1.087"))
        result2 = engine.swap(
            pool_id="USD/EUR",
            trader="TRADER_003",
            amount_in=Decimal("50"),
            token_in="EUR",
            token_out="USD"
        )
        assert result2.status == SwapStatus.EXECUTED
        print(f"  ✅ PASSED: Swapped 50 EUR -> {result2.amount_out} USD @ {result2.oracle_rate}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 9: Fee Collection
    tests_total += 1
    print("\n[TEST 9] Fee Collection...")
    try:
        stats = engine.get_pool_stats("USD/EUR")
        total_fees_usd = Decimal(stats["total_fees_a"])
        total_fees_eur = Decimal(stats["total_fees_b"])
        assert total_fees_usd > 0 or total_fees_eur > 0
        print(f"  ✅ PASSED: Fees collected: {total_fees_usd} USD, {total_fees_eur} EUR")
        print(f"            Total swaps: {stats['swap_count']}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 10: Stale Oracle Protection
    tests_total += 1
    print("\n[TEST 10] Stale Oracle Protection...")
    try:
        # Create a stale oracle scenario
        class StaleOracle(MockOracle):
            def is_stale(self, pair: str, max_age: int = 60) -> bool:
                return True  # Always stale
                
        stale_engine = LiquidityEngine(oracle=StaleOracle())
        stale_engine.create_pool("USD", "GBP")
        stale_engine.add_liquidity("USD/GBP", "LP", Decimal("1000"), Decimal("800"))
        
        try:
            stale_engine.swap("USD/GBP", "TRADER", Decimal("10"), "USD", "GBP")
            print("  ❌ FAILED: Should reject stale oracle")
        except OraclePriceError:
            print(f"  ✅ PASSED: Correctly rejected stale oracle price")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Summary
    print("\n" + "=" * 70)
    print(f"                    RESULTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 70)
    
    if tests_passed == tests_total:
        print("\n💱 LIQUIDITY ENGINE OPERATIONAL")
        print("INV-ECON-005 (PvP Finality): ✅ ENFORCED")
        print("INV-ECON-006 (Oracle Bound): ✅ ENFORCED")
        print("\n🏦 The Market is Open. Trade may begin.")
        
    return tests_passed == tests_total


if __name__ == "__main__":
    import sys
    success = _self_test()
    sys.exit(0 if success else 1)
