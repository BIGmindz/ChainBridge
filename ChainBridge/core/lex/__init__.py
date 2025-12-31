"""
Lex — ChainBridge Runtime Law Engine
=====================================

Deterministic enforcement engine for PDO validation and ChainBridge Law.

Lex Principles:
    - Enforces state, not intent
    - No discretionary decisions
    - Every block must cite a rule ID
    - Binary APPROVE / REJECT only
    - PDOs are immutable — Lex cannot modify

Governance: GOLD STANDARD
Failure Discipline: FAIL-CLOSED
Override: Requires explicit human ACK with audit trail
"""

from .schema import (
    LexRule,
    RuleCategory,
    RuleSeverity,
    LexVerdict,
    VerdictStatus,
    EnforcementRecord,
)
from .validator import LexValidator
from .override import OverrideManager, OverrideRequest, OverrideStatus

__all__ = [
    # Schema
    "LexRule",
    "RuleCategory",
    "RuleSeverity",
    "LexVerdict",
    "VerdictStatus",
    "EnforcementRecord",
    # Validator
    "LexValidator",
    # Override
    "OverrideManager",
    "OverrideRequest",
    "OverrideStatus",
]

__version__ = "1.0.0"
__schema__ = "LEX_POLICY_SCHEMA v1.0.0"
