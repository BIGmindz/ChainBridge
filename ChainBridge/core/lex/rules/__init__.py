"""
Lex Rules Package
=================

Deterministic rule implementations for mechanical enforcement.

All rules are:
    - Binary (PASS / FAIL)
    - Deterministic (same input → same output)
    - Citable (every failure cites rule ID)
"""

from .base_rule import create_rule, RuleBuilder
from .signature_rule import SIGNATURE_RULES, create_signature_validator
from .hash_rule import HASH_RULES, create_hash_validator
from .limit_rule import LIMIT_RULES, create_limit_validator
from .jurisdiction_rule import JURISDICTION_RULES, create_jurisdiction_validator

__all__ = [
    # Base
    "create_rule",
    "RuleBuilder",
    # Rules
    "SIGNATURE_RULES",
    "HASH_RULES",
    "LIMIT_RULES",
    "JURISDICTION_RULES",
    # Validators
    "create_signature_validator",
    "create_hash_validator",
    "create_limit_validator",
    "create_jurisdiction_validator",
]


def get_all_standard_rules():
    """Get all standard Lex rules with their validators."""
    rules = []
    rules.extend(SIGNATURE_RULES)
    rules.extend(HASH_RULES)
    rules.extend(LIMIT_RULES)
    rules.extend(JURISDICTION_RULES)
    return rules
