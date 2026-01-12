"""
ChainBridge Fee Engine
======================

The Tollbooth of the Invisible Bank. Calculates and captures revenue
from every transaction flowing through the system.

CORE PRINCIPLES:
1. Revenue Conservation: Gross == Net + Fee (ALWAYS)
2. Transparency: Fees are explicit Ledger entries, never hidden
3. Flexibility: Support flat fees, percentage fees, and composites
4. Precision: Banker's rounding to 2 decimal places

INVARIANTS:
- INV-FIN-005: Revenue Conservation
- INV-FIN-006: Transparency

PAC: PAC-FIN-P202-FEE-ENGINE
Created: 2026-01-11
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from enum import Enum
from typing import Dict, List, Optional, Tuple
import uuid


# =============================================================================
# EXCEPTIONS
# =============================================================================

class FeeError(Exception):
    """Base exception for fee calculation errors."""
    pass


class FeeExceedsAmountError(FeeError):
    """Raised when calculated fee exceeds the transaction amount."""
    
    def __init__(self, gross: Decimal, fee: Decimal):
        self.gross = gross
        self.fee = fee
        super().__init__(
            f"Fee ({fee}) exceeds transaction amount ({gross}). "
            f"This would result in negative net amount."
        )


class InvalidFeeConfigurationError(FeeError):
    """Raised when fee strategy is misconfigured."""
    
    def __init__(self, message: str):
        super().__init__(f"Invalid fee configuration: {message}")


class NegativeAmountError(FeeError):
    """Raised when attempting to calculate fee on negative amount."""
    
    def __init__(self, amount: Decimal):
        self.amount = amount
        super().__init__(f"Cannot calculate fee on negative amount: {amount}")


# =============================================================================
# FEE CALCULATION RESULT
# =============================================================================

@dataclass
class FeeBreakdown:
    """
    Complete breakdown of a fee calculation.
    
    INVARIANT: gross_amount == net_amount + total_fee
    """
    gross_amount: Decimal          # Original transaction amount
    net_amount: Decimal            # Amount after fees (payee receives)
    total_fee: Decimal             # Total fee collected
    fee_components: List[Dict]     # Breakdown of individual fee components
    strategy_name: str             # Name of the fee strategy applied
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    calculation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """Validate the invariant."""
        # Ensure all are Decimal with proper precision
        self.gross_amount = Decimal(str(self.gross_amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
        self.net_amount = Decimal(str(self.net_amount)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
        self.total_fee = Decimal(str(self.total_fee)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
        
        # INVARIANT CHECK: INV-FIN-005
        if self.gross_amount != self.net_amount + self.total_fee:
            raise FeeError(
                f"Revenue conservation violated: "
                f"Gross ({self.gross_amount}) != Net ({self.net_amount}) + Fee ({self.total_fee}). "
                f"INV-FIN-005 violated."
            )
    
    @property
    def fee_percentage(self) -> Decimal:
        """Calculate effective fee percentage."""
        if self.gross_amount == 0:
            return Decimal("0.00")
        return (self.total_fee / self.gross_amount * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
    
    def to_dict(self) -> Dict:
        """Serialize for JSON."""
        return {
            "calculation_id": self.calculation_id,
            "gross_amount": str(self.gross_amount),
            "net_amount": str(self.net_amount),
            "total_fee": str(self.total_fee),
            "fee_percentage": str(self.fee_percentage),
            "fee_components": self.fee_components,
            "strategy_name": self.strategy_name,
            "calculated_at": self.calculated_at.isoformat(),
        }


# =============================================================================
# FEE STRATEGIES (Strategy Pattern)
# =============================================================================

class FeeStrategy(ABC):
    """
    Abstract base class for fee calculation strategies.
    
    Implementations must:
    1. Calculate fee deterministically
    2. Use Banker's rounding (ROUND_HALF_EVEN)
    3. Never return a fee > gross amount
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""
        pass
    
    @abstractmethod
    def calculate(self, amount: Decimal) -> FeeBreakdown:
        """
        Calculate fee for the given amount.
        
        Args:
            amount: Gross transaction amount
            
        Returns:
            FeeBreakdown with all fee details
            
        Raises:
            FeeExceedsAmountError: If fee would exceed amount
            NegativeAmountError: If amount is negative
        """
        pass
    
    def _validate_amount(self, amount: Decimal) -> Decimal:
        """Validate and normalize amount."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        
        if amount < 0:
            raise NegativeAmountError(amount)
        
        return amount
    
    def _validate_fee(self, gross: Decimal, fee: Decimal) -> Decimal:
        """Ensure fee doesn't exceed gross amount."""
        fee = fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        
        if fee > gross:
            raise FeeExceedsAmountError(gross, fee)
        
        return fee


class FlatFeeStrategy(FeeStrategy):
    """
    Fixed flat fee regardless of transaction amount.
    
    Example: $0.30 per transaction
    """
    
    def __init__(self, flat_fee: Decimal, strategy_name: str = None):
        """
        Args:
            flat_fee: Fixed fee amount (e.g., Decimal("0.30"))
            strategy_name: Optional custom name
        """
        if not isinstance(flat_fee, Decimal):
            flat_fee = Decimal(str(flat_fee))
        
        if flat_fee < 0:
            raise InvalidFeeConfigurationError(f"Flat fee cannot be negative: {flat_fee}")
        
        self._flat_fee = flat_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        self._strategy_name = strategy_name or f"Flat ${self._flat_fee}"
    
    @property
    def name(self) -> str:
        return self._strategy_name
    
    @property
    def flat_fee(self) -> Decimal:
        return self._flat_fee
    
    def calculate(self, amount: Decimal) -> FeeBreakdown:
        gross = self._validate_amount(amount)
        fee = self._validate_fee(gross, self._flat_fee)
        net = gross - fee
        
        return FeeBreakdown(
            gross_amount=gross,
            net_amount=net,
            total_fee=fee,
            fee_components=[
                {"type": "flat", "amount": str(fee), "description": f"Flat fee"}
            ],
            strategy_name=self.name,
        )


class PercentageFeeStrategy(FeeStrategy):
    """
    Percentage-based fee on transaction amount.
    
    Example: 2.9% of transaction
    """
    
    def __init__(self, percentage: Decimal, strategy_name: str = None):
        """
        Args:
            percentage: Fee percentage (e.g., Decimal("2.9") for 2.9%)
            strategy_name: Optional custom name
        """
        if not isinstance(percentage, Decimal):
            percentage = Decimal(str(percentage))
        
        if percentage < 0:
            raise InvalidFeeConfigurationError(f"Percentage cannot be negative: {percentage}")
        
        if percentage > 100:
            raise InvalidFeeConfigurationError(f"Percentage cannot exceed 100%: {percentage}")
        
        self._percentage = percentage
        self._rate = percentage / Decimal("100")
        self._strategy_name = strategy_name or f"{percentage}% Fee"
    
    @property
    def name(self) -> str:
        return self._strategy_name
    
    @property
    def percentage(self) -> Decimal:
        return self._percentage
    
    def calculate(self, amount: Decimal) -> FeeBreakdown:
        gross = self._validate_amount(amount)
        raw_fee = gross * self._rate
        fee = self._validate_fee(gross, raw_fee)
        net = gross - fee
        
        return FeeBreakdown(
            gross_amount=gross,
            net_amount=net,
            total_fee=fee,
            fee_components=[
                {
                    "type": "percentage",
                    "rate": str(self._percentage),
                    "amount": str(fee),
                    "description": f"{self._percentage}% of {gross}",
                }
            ],
            strategy_name=self.name,
        )


class CompositeFeeStrategy(FeeStrategy):
    """
    Combination of multiple fee strategies.
    
    Example: 2.9% + $0.30 (like Stripe)
    
    Fees are applied in sequence and summed.
    """
    
    def __init__(self, strategies: List[FeeStrategy], strategy_name: str = None):
        """
        Args:
            strategies: List of fee strategies to combine
            strategy_name: Optional custom name
        """
        if not strategies:
            raise InvalidFeeConfigurationError("Composite strategy requires at least one sub-strategy")
        
        self._strategies = strategies
        self._strategy_name = strategy_name or " + ".join(s.name for s in strategies)
    
    @property
    def name(self) -> str:
        return self._strategy_name
    
    @property
    def strategies(self) -> List[FeeStrategy]:
        return self._strategies
    
    def calculate(self, amount: Decimal) -> FeeBreakdown:
        gross = self._validate_amount(amount)
        
        total_fee = Decimal("0.00")
        all_components = []
        
        for strategy in self._strategies:
            # Calculate each component fee on the GROSS amount
            breakdown = strategy.calculate(gross)
            total_fee += breakdown.total_fee
            all_components.extend(breakdown.fee_components)
        
        # Validate total fee
        total_fee = self._validate_fee(gross, total_fee)
        net = gross - total_fee
        
        return FeeBreakdown(
            gross_amount=gross,
            net_amount=net,
            total_fee=total_fee,
            fee_components=all_components,
            strategy_name=self.name,
        )


class TieredFeeStrategy(FeeStrategy):
    """
    Tiered fee structure based on volume or transaction amount.
    
    Example:
    - Transactions < $100: 3.0%
    - Transactions $100-$1000: 2.5%
    - Transactions > $1000: 2.0%
    """
    
    def __init__(
        self,
        tiers: List[Tuple[Decimal, FeeStrategy]],
        strategy_name: str = None,
    ):
        """
        Args:
            tiers: List of (threshold, strategy) tuples, sorted ascending by threshold.
                   The threshold is the MINIMUM amount for that tier.
                   Example: [(0, 3% strategy), (100, 2.5% strategy), (1000, 2% strategy)]
            strategy_name: Optional custom name
        """
        if not tiers:
            raise InvalidFeeConfigurationError("Tiered strategy requires at least one tier")
        
        # Sort tiers by threshold
        self._tiers = sorted(tiers, key=lambda t: t[0])
        self._strategy_name = strategy_name or "Tiered Fee"
    
    @property
    def name(self) -> str:
        return self._strategy_name
    
    def calculate(self, amount: Decimal) -> FeeBreakdown:
        gross = self._validate_amount(amount)
        
        # Find applicable tier (highest threshold <= amount)
        applicable_strategy = self._tiers[0][1]  # Default to first tier
        applicable_threshold = Decimal("0.00")
        
        for threshold, strategy in self._tiers:
            if gross >= threshold:
                applicable_strategy = strategy
                applicable_threshold = threshold
        
        breakdown = applicable_strategy.calculate(gross)
        
        # Add tier info to components
        for component in breakdown.fee_components:
            component["tier_threshold"] = str(applicable_threshold)
        
        return FeeBreakdown(
            gross_amount=breakdown.gross_amount,
            net_amount=breakdown.net_amount,
            total_fee=breakdown.total_fee,
            fee_components=breakdown.fee_components,
            strategy_name=f"{self.name} (Tier: >=${applicable_threshold})",
        )


# =============================================================================
# FEE ENGINE
# =============================================================================

class FeeEngine:
    """
    Central fee calculation and management engine.
    
    The Tollbooth of the Invisible Bank - calculates fees,
    validates conservation, and provides audit trails.
    """
    
    # Common pre-built strategies
    STRATEGIES = {
        "stripe_standard": CompositeFeeStrategy(
            [PercentageFeeStrategy(Decimal("2.9")), FlatFeeStrategy(Decimal("0.30"))],
            strategy_name="Stripe Standard (2.9% + $0.30)"
        ),
        "wire_domestic": FlatFeeStrategy(Decimal("25.00"), "Domestic Wire ($25)"),
        "wire_international": FlatFeeStrategy(Decimal("45.00"), "International Wire ($45)"),
        "ach_standard": FlatFeeStrategy(Decimal("0.50"), "ACH Standard ($0.50)"),
        "percentage_1": PercentageFeeStrategy(Decimal("1.0"), "1% Fee"),
        "percentage_2": PercentageFeeStrategy(Decimal("2.0"), "2% Fee"),
        "percentage_3": PercentageFeeStrategy(Decimal("3.0"), "3% Fee"),
        "zero": FlatFeeStrategy(Decimal("0.00"), "No Fee"),
    }
    
    def __init__(self, default_strategy: FeeStrategy = None):
        """
        Initialize the Fee Engine.
        
        Args:
            default_strategy: Default fee strategy to use. If None, uses 'zero'.
        """
        self._custom_strategies: Dict[str, FeeStrategy] = {}
        self._default_strategy = default_strategy or self.STRATEGIES["zero"]
        self._calculations: List[FeeBreakdown] = []
        
        # Metrics
        self._total_fees_calculated: Decimal = Decimal("0.00")
        self._total_transactions: int = 0
    
    def register_strategy(self, name: str, strategy: FeeStrategy):
        """Register a custom fee strategy."""
        self._custom_strategies[name] = strategy
    
    def get_strategy(self, name: str) -> FeeStrategy:
        """Get a fee strategy by name."""
        if name in self._custom_strategies:
            return self._custom_strategies[name]
        if name in self.STRATEGIES:
            return self.STRATEGIES[name]
        raise FeeError(f"Unknown fee strategy: {name}")
    
    def calculate(
        self,
        amount: Decimal,
        strategy: FeeStrategy = None,
        strategy_name: str = None,
    ) -> FeeBreakdown:
        """
        Calculate fee for a transaction.
        
        Args:
            amount: Transaction gross amount
            strategy: Fee strategy to use (overrides strategy_name)
            strategy_name: Name of registered strategy to use
            
        Returns:
            FeeBreakdown with complete fee details
        """
        if strategy is None:
            if strategy_name:
                strategy = self.get_strategy(strategy_name)
            else:
                strategy = self._default_strategy
        
        breakdown = strategy.calculate(amount)
        
        # Track for audit
        self._calculations.append(breakdown)
        self._total_fees_calculated += breakdown.total_fee
        self._total_transactions += 1
        
        return breakdown
    
    def calculate_for_net(
        self,
        desired_net: Decimal,
        strategy: FeeStrategy = None,
        strategy_name: str = None,
    ) -> FeeBreakdown:
        """
        Calculate the gross amount needed to achieve a specific net amount.
        
        This is useful when the payee must receive an exact amount.
        
        Args:
            desired_net: The net amount payee should receive
            strategy: Fee strategy to use
            strategy_name: Name of registered strategy
            
        Returns:
            FeeBreakdown where net_amount == desired_net
        """
        if strategy is None:
            if strategy_name:
                strategy = self.get_strategy(strategy_name)
            else:
                strategy = self._default_strategy
        
        # For percentage-only strategies, we can calculate exactly
        # For flat or composite, we use iteration
        
        if not isinstance(desired_net, Decimal):
            desired_net = Decimal(str(desired_net))
        
        desired_net = desired_net.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        
        # Start with an estimate and refine
        gross_estimate = desired_net
        max_iterations = 10
        
        for _ in range(max_iterations):
            breakdown = strategy.calculate(gross_estimate)
            
            if breakdown.net_amount == desired_net:
                self._calculations.append(breakdown)
                self._total_fees_calculated += breakdown.total_fee
                self._total_transactions += 1
                return breakdown
            
            # Adjust estimate
            diff = desired_net - breakdown.net_amount
            gross_estimate = gross_estimate + diff
            
            if gross_estimate < 0:
                raise FeeError(
                    f"Cannot achieve net amount {desired_net} with strategy {strategy.name}"
                )
        
        # Final attempt with best estimate
        breakdown = strategy.calculate(gross_estimate)
        self._calculations.append(breakdown)
        self._total_fees_calculated += breakdown.total_fee
        self._total_transactions += 1
        return breakdown
    
    def get_metrics(self) -> Dict:
        """Get fee engine metrics."""
        return {
            "total_transactions": self._total_transactions,
            "total_fees_calculated": str(self._total_fees_calculated),
            "average_fee": str(
                (self._total_fees_calculated / self._total_transactions).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_EVEN
                )
            ) if self._total_transactions > 0 else "0.00",
            "registered_strategies": list(self._custom_strategies.keys()),
            "builtin_strategies": list(self.STRATEGIES.keys()),
        }
    
    def get_calculation_history(self, limit: int = 100) -> List[Dict]:
        """Get recent calculation history for audit."""
        return [c.to_dict() for c in self._calculations[-limit:]]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_stripe_strategy() -> FeeStrategy:
    """Create a Stripe-like fee strategy (2.9% + $0.30)."""
    return CompositeFeeStrategy(
        [
            PercentageFeeStrategy(Decimal("2.9")),
            FlatFeeStrategy(Decimal("0.30")),
        ],
        strategy_name="Stripe Standard"
    )


def create_tiered_percentage_strategy(
    small_rate: Decimal = Decimal("3.0"),
    medium_rate: Decimal = Decimal("2.5"),
    large_rate: Decimal = Decimal("2.0"),
    medium_threshold: Decimal = Decimal("100"),
    large_threshold: Decimal = Decimal("1000"),
) -> FeeStrategy:
    """Create a tiered percentage fee strategy."""
    return TieredFeeStrategy(
        [
            (Decimal("0"), PercentageFeeStrategy(small_rate)),
            (medium_threshold, PercentageFeeStrategy(medium_rate)),
            (large_threshold, PercentageFeeStrategy(large_rate)),
        ],
        strategy_name="Tiered Percentage"
    )
