"""
ChainBridge Multi-Currency Engine
=================================

The Exchange of the Invisible Bank. Enables global trade by supporting
multiple currencies with proper precision handling and exchange rate management.

CORE PRINCIPLES:
1. Precision Safety: Respect atomic units of each currency
2. Rate Transparency: All conversions record the rate used
3. ISO Compliance: Use ISO 4217 currency codes
4. Staleness Protection: Reject stale exchange rates

INVARIANTS:
- INV-FIN-007: Precision Safety
- INV-FIN-008: Rate Transparency

PAC: PAC-FIN-P203-MULTI-CURRENCY-ENGINE
Created: 2026-01-11
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_DOWN, ROUND_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
import uuid


# =============================================================================
# EXCEPTIONS
# =============================================================================

class CurrencyError(Exception):
    """Base exception for currency operations."""
    pass


class UnknownCurrencyError(CurrencyError):
    """Raised when referencing an unknown currency code."""
    
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Unknown currency code: {code}")


class ExchangeRateNotFoundError(CurrencyError):
    """Raised when no exchange rate exists for a currency pair."""
    
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        super().__init__(f"No exchange rate found for {source}/{target}")


class StaleExchangeRateError(CurrencyError):
    """Raised when an exchange rate is too old to use."""
    
    def __init__(self, pair: str, age: timedelta, max_age: timedelta):
        self.pair = pair
        self.age = age
        self.max_age = max_age
        super().__init__(
            f"Exchange rate for {pair} is stale: "
            f"age={age}, max_allowed={max_age}"
        )


class PrecisionViolationError(CurrencyError):
    """Raised when an amount violates currency precision rules."""
    
    def __init__(self, currency: str, amount: Decimal, decimals: int):
        self.currency = currency
        self.amount = amount
        self.decimals = decimals
        super().__init__(
            f"Amount {amount} violates precision for {currency} "
            f"(max {decimals} decimal places)"
        )


class NegativeAmountError(CurrencyError):
    """Raised when amount is negative."""
    
    def __init__(self, amount: Decimal):
        self.amount = amount
        super().__init__(f"Amount cannot be negative: {amount}")


# =============================================================================
# CURRENCY DEFINITION
# =============================================================================

@dataclass(frozen=True)
class Currency:
    """
    Represents a currency with its properties.
    
    Follows ISO 4217 standard where applicable.
    """
    code: str              # ISO 4217 code (e.g., "USD", "EUR", "BTC")
    name: str              # Full name (e.g., "US Dollar")
    decimals: int          # Number of decimal places (e.g., 2 for USD, 0 for JPY)
    symbol: str = ""       # Currency symbol (e.g., "$", "€", "¥")
    is_crypto: bool = False  # Whether this is a cryptocurrency
    
    def __post_init__(self):
        """Validate currency definition."""
        if self.decimals < 0:
            raise ValueError(f"Decimals cannot be negative: {self.decimals}")
        if self.decimals > 18:  # Max for crypto precision
            raise ValueError(f"Decimals too high: {self.decimals}")
    
    @property
    def atomic_unit(self) -> Decimal:
        """The smallest representable unit of this currency."""
        return Decimal(10) ** -self.decimals
    
    def quantize(self, amount: Decimal, rounding: str = ROUND_HALF_EVEN) -> Decimal:
        """
        Round amount to this currency's precision.
        
        Args:
            amount: The amount to quantize
            rounding: Rounding mode (default: Banker's rounding)
            
        Returns:
            Amount rounded to currency's precision
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        return amount.quantize(self.atomic_unit, rounding=rounding)
    
    def validate_amount(self, amount: Decimal) -> bool:
        """Check if amount respects this currency's precision."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        quantized = self.quantize(amount)
        return amount == quantized


# =============================================================================
# CURRENCY REGISTRY (ISO 4217 + Crypto)
# =============================================================================

class CurrencyRegistry:
    """
    Registry of supported currencies.
    
    Includes major fiat currencies (ISO 4217) and common cryptocurrencies.
    """
    
    # Standard fiat currencies
    _FIAT_CURRENCIES = {
        # Major currencies
        "USD": Currency("USD", "US Dollar", 2, "$"),
        "EUR": Currency("EUR", "Euro", 2, "€"),
        "GBP": Currency("GBP", "British Pound", 2, "£"),
        "JPY": Currency("JPY", "Japanese Yen", 0, "¥"),
        "CHF": Currency("CHF", "Swiss Franc", 2, "CHF"),
        "CAD": Currency("CAD", "Canadian Dollar", 2, "C$"),
        "AUD": Currency("AUD", "Australian Dollar", 2, "A$"),
        "NZD": Currency("NZD", "New Zealand Dollar", 2, "NZ$"),
        
        # Asian currencies
        "CNY": Currency("CNY", "Chinese Yuan", 2, "¥"),
        "HKD": Currency("HKD", "Hong Kong Dollar", 2, "HK$"),
        "SGD": Currency("SGD", "Singapore Dollar", 2, "S$"),
        "KRW": Currency("KRW", "South Korean Won", 0, "₩"),
        "INR": Currency("INR", "Indian Rupee", 2, "₹"),
        
        # Other major currencies
        "MXN": Currency("MXN", "Mexican Peso", 2, "$"),
        "BRL": Currency("BRL", "Brazilian Real", 2, "R$"),
        "ZAR": Currency("ZAR", "South African Rand", 2, "R"),
        "RUB": Currency("RUB", "Russian Ruble", 2, "₽"),
        "TRY": Currency("TRY", "Turkish Lira", 2, "₺"),
        "PLN": Currency("PLN", "Polish Zloty", 2, "zł"),
        "SEK": Currency("SEK", "Swedish Krona", 2, "kr"),
        "NOK": Currency("NOK", "Norwegian Krone", 2, "kr"),
        "DKK": Currency("DKK", "Danish Krone", 2, "kr"),
        
        # Middle East
        "AED": Currency("AED", "UAE Dirham", 2, "د.إ"),
        "SAR": Currency("SAR", "Saudi Riyal", 2, "﷼"),
        "ILS": Currency("ILS", "Israeli Shekel", 2, "₪"),
        
        # Special currencies (0 decimals)
        "KWD": Currency("KWD", "Kuwaiti Dinar", 3, "د.ك"),  # 3 decimals
        "BHD": Currency("BHD", "Bahraini Dinar", 3, ".د.ب"),  # 3 decimals
        "OMR": Currency("OMR", "Omani Rial", 3, "﷼"),  # 3 decimals
    }
    
    # Cryptocurrencies
    _CRYPTO_CURRENCIES = {
        "BTC": Currency("BTC", "Bitcoin", 8, "₿", is_crypto=True),
        "ETH": Currency("ETH", "Ethereum", 18, "Ξ", is_crypto=True),
        "USDT": Currency("USDT", "Tether", 6, "₮", is_crypto=True),
        "USDC": Currency("USDC", "USD Coin", 6, "USDC", is_crypto=True),
        "SOL": Currency("SOL", "Solana", 9, "◎", is_crypto=True),
        "XRP": Currency("XRP", "Ripple", 6, "XRP", is_crypto=True),
        "ADA": Currency("ADA", "Cardano", 6, "₳", is_crypto=True),
        "DOGE": Currency("DOGE", "Dogecoin", 8, "Ð", is_crypto=True),
    }
    
    def __init__(self):
        """Initialize the currency registry."""
        self._currencies: Dict[str, Currency] = {}
        self._currencies.update(self._FIAT_CURRENCIES)
        self._currencies.update(self._CRYPTO_CURRENCIES)
    
    def get(self, code: str) -> Currency:
        """
        Get a currency by its code.
        
        Args:
            code: ISO 4217 currency code (case-insensitive)
            
        Returns:
            Currency object
            
        Raises:
            UnknownCurrencyError: If currency code is not registered
        """
        code = code.upper()
        if code not in self._currencies:
            raise UnknownCurrencyError(code)
        return self._currencies[code]
    
    def register(self, currency: Currency):
        """Register a custom currency."""
        self._currencies[currency.code.upper()] = currency
    
    def list_all(self) -> List[str]:
        """List all registered currency codes."""
        return sorted(self._currencies.keys())
    
    def list_fiat(self) -> List[str]:
        """List all fiat currency codes."""
        return sorted(c.code for c in self._currencies.values() if not c.is_crypto)
    
    def list_crypto(self) -> List[str]:
        """List all cryptocurrency codes."""
        return sorted(c.code for c in self._currencies.values() if c.is_crypto)


# =============================================================================
# MONEY AMOUNT
# =============================================================================

@dataclass
class Money:
    """
    Represents a monetary amount in a specific currency.
    
    Enforces precision rules for the currency.
    """
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        """Validate and normalize the amount."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        
        if self.amount < 0:
            raise NegativeAmountError(self.amount)
        
        # Quantize to currency precision
        self.amount = self.currency.quantize(self.amount)
    
    @classmethod
    def from_code(cls, amount: Union[Decimal, str, float], currency_code: str, 
                  registry: CurrencyRegistry = None) -> "Money":
        """
        Create Money from a currency code.
        
        Args:
            amount: The monetary amount
            currency_code: ISO 4217 currency code
            registry: Optional currency registry (uses default if not provided)
        """
        registry = registry or CurrencyRegistry()
        currency = registry.get(currency_code)
        return cls(Decimal(str(amount)), currency)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        if self.currency.symbol:
            return f"{self.currency.symbol}{self.amount:,.{self.currency.decimals}f}"
        return f"{self.amount:,.{self.currency.decimals}f} {self.currency.code}"
    
    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency.code})"
    
    def __eq__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency.code == other.currency.code
    
    def __add__(self, other: "Money") -> "Money":
        if self.currency.code != other.currency.code:
            raise CurrencyError(
                f"Cannot add different currencies: {self.currency.code} + {other.currency.code}"
            )
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: "Money") -> "Money":
        if self.currency.code != other.currency.code:
            raise CurrencyError(
                f"Cannot subtract different currencies: {self.currency.code} - {other.currency.code}"
            )
        return Money(self.amount - other.amount, self.currency)
    
    def to_dict(self) -> Dict:
        """Serialize for JSON."""
        return {
            "amount": str(self.amount),
            "currency": self.currency.code,
            "formatted": str(self),
        }


# =============================================================================
# EXCHANGE RATE
# =============================================================================

@dataclass
class ExchangeRate:
    """
    Represents an exchange rate between two currencies.
    
    Rate is expressed as: 1 base_currency = rate * quote_currency
    Example: EUR/USD = 1.08 means 1 EUR = 1.08 USD
    """
    base_currency: str      # The currency being sold (e.g., "EUR")
    quote_currency: str     # The currency being bought (e.g., "USD")
    rate: Decimal          # Exchange rate
    timestamp: datetime    # When the rate was fetched/set
    source: str = "manual"  # Rate source (e.g., "manual", "ECB", "binance")
    bid: Optional[Decimal] = None   # Bid price (what buyer pays)
    ask: Optional[Decimal] = None   # Ask price (what seller receives)
    rate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """Normalize rate values."""
        if not isinstance(self.rate, Decimal):
            self.rate = Decimal(str(self.rate))
        if self.bid and not isinstance(self.bid, Decimal):
            self.bid = Decimal(str(self.bid))
        if self.ask and not isinstance(self.ask, Decimal):
            self.ask = Decimal(str(self.ask))
    
    @property
    def pair(self) -> str:
        """Currency pair notation (e.g., 'EUR/USD')."""
        return f"{self.base_currency}/{self.quote_currency}"
    
    @property
    def inverse_rate(self) -> Decimal:
        """Inverse rate (e.g., if EUR/USD=1.08, USD/EUR=0.926)."""
        if self.rate == 0:
            raise CurrencyError("Cannot compute inverse of zero rate")
        return Decimal("1") / self.rate
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Bid-ask spread as a percentage."""
        if self.bid and self.ask:
            return ((self.ask - self.bid) / self.rate * 100).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_EVEN
            )
        return None
    
    def age(self) -> timedelta:
        """How old is this rate."""
        return datetime.now(timezone.utc) - self.timestamp
    
    def is_stale(self, max_age: timedelta = timedelta(hours=24)) -> bool:
        """Check if rate is too old."""
        return self.age() > max_age
    
    def to_dict(self) -> Dict:
        """Serialize for JSON."""
        return {
            "rate_id": self.rate_id,
            "pair": self.pair,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "rate": str(self.rate),
            "inverse_rate": str(self.inverse_rate),
            "bid": str(self.bid) if self.bid else None,
            "ask": str(self.ask) if self.ask else None,
            "spread": str(self.spread) if self.spread else None,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "age_seconds": self.age().total_seconds(),
        }


# =============================================================================
# CONVERSION RESULT
# =============================================================================

@dataclass
class ConversionResult:
    """
    Complete record of a currency conversion.
    
    Provides audit trail with full transparency (INV-FIN-008).
    """
    source_money: Money
    target_money: Money
    rate_used: ExchangeRate
    conversion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    converted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def effective_rate(self) -> Decimal:
        """The effective rate of the conversion."""
        if self.source_money.amount == 0:
            return Decimal("0")
        return self.target_money.amount / self.source_money.amount
    
    def to_dict(self) -> Dict:
        """Serialize for JSON/audit."""
        return {
            "conversion_id": self.conversion_id,
            "source": self.source_money.to_dict(),
            "target": self.target_money.to_dict(),
            "rate_used": self.rate_used.to_dict(),
            "effective_rate": str(self.effective_rate),
            "converted_at": self.converted_at.isoformat(),
        }


# =============================================================================
# CURRENCY ENGINE
# =============================================================================

class CurrencyEngine:
    """
    The Exchange of the Invisible Bank.
    
    Handles multi-currency operations with proper precision
    and exchange rate management.
    
    INVARIANTS:
    - INV-FIN-007: Precision Safety
    - INV-FIN-008: Rate Transparency
    """
    
    # Default maximum age for exchange rates
    DEFAULT_MAX_RATE_AGE = timedelta(hours=24)
    
    def __init__(
        self,
        registry: CurrencyRegistry = None,
        max_rate_age: timedelta = None,
    ):
        """
        Initialize the Currency Engine.
        
        Args:
            registry: Currency registry (uses default if not provided)
            max_rate_age: Maximum allowed age for exchange rates
        """
        self.registry = registry or CurrencyRegistry()
        self.max_rate_age = max_rate_age or self.DEFAULT_MAX_RATE_AGE
        
        # Exchange rate storage: {pair: ExchangeRate}
        self._rates: Dict[str, ExchangeRate] = {}
        
        # Conversion history for audit
        self._conversions: List[ConversionResult] = []
        
        # Metrics
        self._total_conversions: int = 0
    
    # =========================================================================
    # EXCHANGE RATE MANAGEMENT
    # =========================================================================
    
    def set_rate(
        self,
        base_currency: str,
        quote_currency: str,
        rate: Decimal,
        source: str = "manual",
        bid: Decimal = None,
        ask: Decimal = None,
        timestamp: datetime = None,
    ) -> ExchangeRate:
        """
        Set an exchange rate.
        
        Args:
            base_currency: Base currency code (e.g., "EUR")
            quote_currency: Quote currency code (e.g., "USD")
            rate: The exchange rate (1 base = rate * quote)
            source: Rate source identifier
            bid: Optional bid price
            ask: Optional ask price
            timestamp: Rate timestamp (defaults to now)
            
        Returns:
            The created ExchangeRate
        """
        # Validate currencies exist
        self.registry.get(base_currency.upper())
        self.registry.get(quote_currency.upper())
        
        if not isinstance(rate, Decimal):
            rate = Decimal(str(rate))
        
        if rate <= 0:
            raise CurrencyError(f"Exchange rate must be positive: {rate}")
        
        exchange_rate = ExchangeRate(
            base_currency=base_currency.upper(),
            quote_currency=quote_currency.upper(),
            rate=rate,
            timestamp=timestamp or datetime.now(timezone.utc),
            source=source,
            bid=bid,
            ask=ask,
        )
        
        pair = exchange_rate.pair
        self._rates[pair] = exchange_rate
        
        # Also store inverse rate for convenience
        inverse_pair = f"{quote_currency.upper()}/{base_currency.upper()}"
        self._rates[inverse_pair] = ExchangeRate(
            base_currency=quote_currency.upper(),
            quote_currency=base_currency.upper(),
            rate=exchange_rate.inverse_rate,
            timestamp=exchange_rate.timestamp,
            source=f"{source} (inverse)",
            bid=Decimal("1") / ask if ask else None,
            ask=Decimal("1") / bid if bid else None,
        )
        
        return exchange_rate
    
    def get_rate(
        self,
        base_currency: str,
        quote_currency: str,
        validate_freshness: bool = True,
    ) -> ExchangeRate:
        """
        Get an exchange rate.
        
        Args:
            base_currency: Base currency code
            quote_currency: Quote currency code
            validate_freshness: Whether to check for staleness
            
        Returns:
            The ExchangeRate
            
        Raises:
            ExchangeRateNotFoundError: If rate doesn't exist
            StaleExchangeRateError: If rate is too old
        """
        base = base_currency.upper()
        quote = quote_currency.upper()
        
        # Same currency = rate of 1
        if base == quote:
            return ExchangeRate(
                base_currency=base,
                quote_currency=quote,
                rate=Decimal("1"),
                timestamp=datetime.now(timezone.utc),
                source="identity",
            )
        
        pair = f"{base}/{quote}"
        
        if pair not in self._rates:
            raise ExchangeRateNotFoundError(base, quote)
        
        rate = self._rates[pair]
        
        if validate_freshness and rate.is_stale(self.max_rate_age):
            raise StaleExchangeRateError(pair, rate.age(), self.max_rate_age)
        
        return rate
    
    def list_rates(self) -> List[ExchangeRate]:
        """List all stored exchange rates."""
        return list(self._rates.values())
    
    # =========================================================================
    # CURRENCY CONVERSION
    # =========================================================================
    
    def convert(
        self,
        amount: Union[Decimal, Money],
        source_currency: str = None,
        target_currency: str = None,
        rate: ExchangeRate = None,
        rounding: str = ROUND_HALF_EVEN,
    ) -> ConversionResult:
        """
        Convert money from one currency to another.
        
        Args:
            amount: Amount to convert (Money object or Decimal)
            source_currency: Source currency code (required if amount is Decimal)
            target_currency: Target currency code
            rate: Optional explicit exchange rate to use
            rounding: Rounding mode for target amount
            
        Returns:
            ConversionResult with full audit trail
            
        Raises:
            ExchangeRateNotFoundError: If rate not available
            StaleExchangeRateError: If rate is too old
            PrecisionViolationError: If conversion violates precision
        """
        # Normalize input
        if isinstance(amount, Money):
            source_money = amount
            source_currency = source_money.currency.code
        else:
            if not source_currency:
                raise CurrencyError("source_currency required when amount is Decimal")
            source_money = Money.from_code(amount, source_currency, self.registry)
            source_currency = source_currency.upper()
        
        if not target_currency:
            raise CurrencyError("target_currency is required")
        
        target_currency = target_currency.upper()
        target_cur = self.registry.get(target_currency)
        
        # Get exchange rate
        if rate is None:
            rate = self.get_rate(source_currency, target_currency)
        
        # Perform conversion
        raw_target_amount = source_money.amount * rate.rate
        
        # Apply target currency precision (INV-FIN-007)
        target_amount = target_cur.quantize(raw_target_amount, rounding)
        
        target_money = Money(target_amount, target_cur)
        
        # Create result with full audit trail (INV-FIN-008)
        result = ConversionResult(
            source_money=source_money,
            target_money=target_money,
            rate_used=rate,
        )
        
        # Record for audit
        self._conversions.append(result)
        self._total_conversions += 1
        
        return result
    
    def convert_to_base(
        self,
        amount: Money,
        base_currency: str = "USD",
    ) -> ConversionResult:
        """
        Convert any currency to a base currency (default USD).
        
        Useful for reporting and aggregation.
        """
        return self.convert(amount, target_currency=base_currency)
    
    # =========================================================================
    # MONEY OPERATIONS
    # =========================================================================
    
    def create_money(
        self,
        amount: Union[Decimal, str, float],
        currency_code: str,
    ) -> Money:
        """Create a Money object with validation."""
        return Money.from_code(amount, currency_code, self.registry)
    
    def format_money(
        self,
        amount: Union[Decimal, str, float],
        currency_code: str,
    ) -> str:
        """Format an amount as money string."""
        money = self.create_money(amount, currency_code)
        return str(money)
    
    def get_currency(self, code: str) -> Currency:
        """Get currency details by code."""
        return self.registry.get(code)
    
    # =========================================================================
    # AUDIT & METRICS
    # =========================================================================
    
    def get_metrics(self) -> Dict:
        """Get engine metrics."""
        return {
            "total_conversions": self._total_conversions,
            "rates_stored": len(self._rates),
            "currencies_supported": len(self.registry.list_all()),
            "fiat_currencies": len(self.registry.list_fiat()),
            "crypto_currencies": len(self.registry.list_crypto()),
        }
    
    def get_conversion_history(self, limit: int = 100) -> List[Dict]:
        """Get recent conversion history for audit."""
        return [c.to_dict() for c in self._conversions[-limit:]]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_default_engine_with_rates() -> CurrencyEngine:
    """
    Create a currency engine with common exchange rates.
    
    Rates are approximate and should be updated with real data in production.
    """
    engine = CurrencyEngine()
    now = datetime.now(timezone.utc)
    
    # Approximate rates (as of late 2025/early 2026)
    # In production, these would be fetched from an oracle
    rates = [
        ("EUR", "USD", "1.08"),
        ("GBP", "USD", "1.27"),
        ("USD", "JPY", "148.50"),
        ("USD", "CHF", "0.88"),
        ("USD", "CAD", "1.36"),
        ("USD", "AUD", "1.54"),
        ("USD", "CNY", "7.24"),
        ("USD", "INR", "83.50"),
        ("USD", "MXN", "17.20"),
        ("USD", "BRL", "4.95"),
        ("USD", "KRW", "1320.00"),
        ("BTC", "USD", "97500.00"),
        ("ETH", "USD", "3450.00"),
        ("USDT", "USD", "1.00"),
        ("USDC", "USD", "1.00"),
    ]
    
    for base, quote, rate in rates:
        engine.set_rate(base, quote, Decimal(rate), source="default", timestamp=now)
    
    return engine
