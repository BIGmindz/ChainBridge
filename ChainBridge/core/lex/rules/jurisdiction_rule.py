"""
Jurisdiction Rules
==================

Deterministic jurisdiction/compliance enforcement rules.

Validates geographic and regulatory compliance.
"""

from typing import Any, Callable

from ..schema import LexRule, RuleCategory, RuleSeverity


# Type alias
RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


# ============================================================================
# BLOCKED/ALLOWED LISTS (configurable via context)
# ============================================================================

DEFAULT_BLOCKED_JURISDICTIONS = {
    # OFAC sanctioned countries (example list)
    "KP",  # North Korea
    "IR",  # Iran
    "SY",  # Syria
    "CU",  # Cuba
}

DEFAULT_ALLOWED_JURISDICTIONS = {
    # Default allowed (empty means all non-blocked are allowed)
}


# ============================================================================
# RULE DEFINITIONS
# ============================================================================

RULE_JUR_001 = LexRule(
    rule_id="LEX-JUR-001",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.CRITICAL,
    name="Jurisdiction Not Blocked",
    description="Transaction must not originate from or target blocked jurisdiction",
    predicate_fn="check_jurisdiction_not_blocked",
    error_template="[{rule_id}] Transaction involves blocked jurisdiction",
    override_allowed=False,  # Critical — no override (sanctions compliance)
    requires_senior_override=False,
)

RULE_JUR_002 = LexRule(
    rule_id="LEX-JUR-002",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.HIGH,
    name="Source Jurisdiction Valid",
    description="Source jurisdiction must be identified and valid",
    predicate_fn="check_source_jurisdiction",
    error_template="[{rule_id}] Source jurisdiction not identified or invalid",
    override_allowed=True,
    requires_senior_override=True,
)

RULE_JUR_003 = LexRule(
    rule_id="LEX-JUR-003",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.HIGH,
    name="Destination Jurisdiction Valid",
    description="Destination jurisdiction must be identified and valid",
    predicate_fn="check_destination_jurisdiction",
    error_template="[{rule_id}] Destination jurisdiction not identified or invalid",
    override_allowed=True,
    requires_senior_override=True,
)

RULE_JUR_004 = LexRule(
    rule_id="LEX-JUR-004",
    category=RuleCategory.COMPLIANCE,
    severity=RuleSeverity.MEDIUM,
    name="Cross-Border Flagged",
    description="Cross-border transactions must be explicitly flagged",
    predicate_fn="check_cross_border_flagged",
    error_template="[{rule_id}] Cross-border transaction not properly flagged",
    override_allowed=True,
    requires_senior_override=False,
)


# ============================================================================
# PREDICATE IMPLEMENTATIONS
# ============================================================================

def _get_blocked_jurisdictions(context: dict[str, Any]) -> set[str]:
    """Get blocked jurisdictions from context or use defaults."""
    blocked = context.get("blocked_jurisdictions")
    if blocked is not None:
        return set(blocked)
    return DEFAULT_BLOCKED_JURISDICTIONS


def _get_jurisdiction(pdo: dict[str, Any], key: str) -> str | None:
    """Extract jurisdiction code from PDO."""
    # Direct field
    jur = pdo.get(key)
    if jur:
        return jur.upper() if isinstance(jur, str) else None
    
    # Check nested locations
    for nested_key in ["source", "destination", "payload", "metadata"]:
        if nested_key in pdo and isinstance(pdo[nested_key], dict):
            jur = pdo[nested_key].get(key) or pdo[nested_key].get("jurisdiction")
            if jur:
                return jur.upper() if isinstance(jur, str) else None
    
    return None


def check_jurisdiction_not_blocked(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that transaction does not involve blocked jurisdiction."""
    blocked = _get_blocked_jurisdictions(context)
    
    # Check source
    source_jur = _get_jurisdiction(pdo, "source_jurisdiction")
    if source_jur and source_jur in blocked:
        return False
    
    # Check destination
    dest_jur = _get_jurisdiction(pdo, "destination_jurisdiction")
    if dest_jur and dest_jur in blocked:
        return False
    
    # Check generic jurisdiction field
    jur = pdo.get("jurisdiction")
    if jur and isinstance(jur, str) and jur.upper() in blocked:
        return False
    
    return True


def check_source_jurisdiction(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that source jurisdiction is identified and valid."""
    source_jur = _get_jurisdiction(pdo, "source_jurisdiction")
    
    # If no jurisdiction required flag, pass
    if not context.get("require_jurisdiction", True):
        return True
    
    if not source_jur:
        return False
    
    # Validate format (ISO 3166-1 alpha-2)
    if len(source_jur) != 2 or not source_jur.isalpha():
        return False
    
    return True


def check_destination_jurisdiction(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that destination jurisdiction is identified and valid."""
    dest_jur = _get_jurisdiction(pdo, "destination_jurisdiction")
    
    # If no jurisdiction required flag, pass
    if not context.get("require_jurisdiction", True):
        return True
    
    if not dest_jur:
        return False
    
    # Validate format (ISO 3166-1 alpha-2)
    if len(dest_jur) != 2 or not dest_jur.isalpha():
        return False
    
    return True


def check_cross_border_flagged(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that cross-border transactions are flagged."""
    source_jur = _get_jurisdiction(pdo, "source_jurisdiction")
    dest_jur = _get_jurisdiction(pdo, "destination_jurisdiction")
    
    # If both jurisdictions present and different, check for flag
    if source_jur and dest_jur and source_jur != dest_jur:
        is_cross_border = pdo.get("is_cross_border") or pdo.get("cross_border")
        
        # Check nested
        if not is_cross_border:
            for key in ["metadata", "flags", "payload"]:
                if key in pdo and isinstance(pdo[key], dict):
                    is_cross_border = pdo[key].get("is_cross_border") or pdo[key].get("cross_border")
                    if is_cross_border:
                        break
        
        return bool(is_cross_border)
    
    return True  # Not cross-border or jurisdictions not specified


# ============================================================================
# EXPORTS
# ============================================================================

JURISDICTION_RULES = [
    (RULE_JUR_001, check_jurisdiction_not_blocked),
    (RULE_JUR_002, check_source_jurisdiction),
    (RULE_JUR_003, check_destination_jurisdiction),
    (RULE_JUR_004, check_cross_border_flagged),
]


def create_jurisdiction_validator():
    """
    Create a validator function for all jurisdiction rules.
    
    Returns:
        List of (rule, predicate) tuples
    """
    return JURISDICTION_RULES
