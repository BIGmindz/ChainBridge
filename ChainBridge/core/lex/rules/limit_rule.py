"""
Limit Rules
===========

Deterministic limit/cap enforcement rules.

Validates amounts, quantities, and thresholds against configured limits.
"""

from typing import Any, Callable
from decimal import Decimal, InvalidOperation

from ..schema import LexRule, RuleCategory, RuleSeverity


# Type alias
RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


# ============================================================================
# RULE DEFINITIONS
# ============================================================================

RULE_LIM_001 = LexRule(
    rule_id="LEX-LIM-001",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.HIGH,
    name="Amount Within Daily Limit",
    description="Transaction amount must not exceed daily limit",
    predicate_fn="check_daily_limit",
    error_template="[{rule_id}] Amount exceeds daily limit",
    override_allowed=True,
    requires_senior_override=True,
)

RULE_LIM_002 = LexRule(
    rule_id="LEX-LIM-002",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.HIGH,
    name="Amount Within Single Transaction Limit",
    description="Transaction amount must not exceed single transaction limit",
    predicate_fn="check_single_tx_limit",
    error_template="[{rule_id}] Amount exceeds single transaction limit",
    override_allowed=True,
    requires_senior_override=True,
)

RULE_LIM_003 = LexRule(
    rule_id="LEX-LIM-003",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.CRITICAL,
    name="Amount Within Hard Cap",
    description="Transaction amount must not exceed absolute hard cap",
    predicate_fn="check_hard_cap",
    error_template="[{rule_id}] Amount exceeds hard cap - no override allowed",
    override_allowed=False,  # Critical — no override
    requires_senior_override=False,
)

RULE_LIM_004 = LexRule(
    rule_id="LEX-LIM-004",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.MEDIUM,
    name="Rate Limit Not Exceeded",
    description="Request rate must not exceed configured rate limit",
    predicate_fn="check_rate_limit",
    error_template="[{rule_id}] Rate limit exceeded",
    override_allowed=True,
    requires_senior_override=False,
)

RULE_LIM_005 = LexRule(
    rule_id="LEX-LIM-005",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.MEDIUM,
    name="Amount Positive",
    description="Transaction amount must be positive",
    predicate_fn="check_amount_positive",
    error_template="[{rule_id}] Amount must be positive",
    override_allowed=False,
    requires_senior_override=False,
)


# ============================================================================
# DEFAULT LIMITS (can be overridden via context)
# ============================================================================

DEFAULT_LIMITS = {
    "daily_limit": Decimal("100000.00"),
    "single_tx_limit": Decimal("10000.00"),
    "hard_cap": Decimal("1000000.00"),
    "rate_limit_per_minute": 60,
}


# ============================================================================
# PREDICATE IMPLEMENTATIONS
# ============================================================================

def _get_amount(pdo: dict[str, Any]) -> Decimal | None:
    """Extract amount from PDO."""
    amount = pdo.get("amount")
    if amount is None:
        # Check nested locations
        for key in ["payload", "data", "transaction"]:
            if key in pdo and isinstance(pdo[key], dict):
                amount = pdo[key].get("amount")
                if amount is not None:
                    break
    
    if amount is None:
        return None
    
    try:
        return Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return None


def _get_limit(context: dict[str, Any], key: str) -> Decimal:
    """Get limit from context or use default."""
    value = context.get(key, DEFAULT_LIMITS.get(key))
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def check_daily_limit(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that amount does not exceed daily limit."""
    amount = _get_amount(pdo)
    if amount is None:
        return True  # No amount to check
    
    daily_limit = _get_limit(context, "daily_limit")
    daily_used = Decimal(str(context.get("daily_used", "0")))
    
    return (daily_used + amount) <= daily_limit


def check_single_tx_limit(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that amount does not exceed single transaction limit."""
    amount = _get_amount(pdo)
    if amount is None:
        return True  # No amount to check
    
    single_tx_limit = _get_limit(context, "single_tx_limit")
    return amount <= single_tx_limit


def check_hard_cap(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that amount does not exceed hard cap."""
    amount = _get_amount(pdo)
    if amount is None:
        return True  # No amount to check
    
    hard_cap = _get_limit(context, "hard_cap")
    return amount <= hard_cap


def check_rate_limit(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that rate limit is not exceeded."""
    rate_limit = int(context.get("rate_limit_per_minute", DEFAULT_LIMITS["rate_limit_per_minute"]))
    current_rate = int(context.get("current_rate_per_minute", 0))
    
    return current_rate < rate_limit


def check_amount_positive(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that amount is positive."""
    amount = _get_amount(pdo)
    if amount is None:
        return True  # No amount to check
    
    return amount > Decimal("0")


# ============================================================================
# EXPORTS
# ============================================================================

LIMIT_RULES = [
    (RULE_LIM_001, check_daily_limit),
    (RULE_LIM_002, check_single_tx_limit),
    (RULE_LIM_003, check_hard_cap),
    (RULE_LIM_004, check_rate_limit),
    (RULE_LIM_005, check_amount_positive),
]


def create_limit_validator():
    """
    Create a validator function for all limit rules.
    
    Returns:
        List of (rule, predicate) tuples
    """
    return LIMIT_RULES
