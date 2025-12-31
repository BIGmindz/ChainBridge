"""
Signature Rules
===============

Deterministic signature verification rules.

No cryptographic operations — validates signature presence and format.
Actual cryptographic verification should be done by a dedicated service.
"""

from typing import Any, Callable
import re

from ..schema import LexRule, RuleCategory, RuleSeverity


# Type alias
RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


# ============================================================================
# RULE DEFINITIONS
# ============================================================================

RULE_SIG_001 = LexRule(
    rule_id="LEX-SIG-001",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.CRITICAL,
    name="Signature Present",
    description="PDO must contain a signature field",
    predicate_fn="check_signature_present",
    error_template="[{rule_id}] PDO missing required signature field",
    override_allowed=False,  # Critical — no override
    requires_senior_override=False,
)

RULE_SIG_002 = LexRule(
    rule_id="LEX-SIG-002",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.HIGH,
    name="Signature Format Valid",
    description="Signature must be in valid format (hex or base64)",
    predicate_fn="check_signature_format",
    error_template="[{rule_id}] Invalid signature format",
    override_allowed=True,
    requires_senior_override=True,
)

RULE_SIG_003 = LexRule(
    rule_id="LEX-SIG-003",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.HIGH,
    name="Signer Identity Present",
    description="PDO must identify the signer",
    predicate_fn="check_signer_present",
    error_template="[{rule_id}] PDO missing signer identity",
    override_allowed=True,
    requires_senior_override=False,
)

RULE_SIG_004 = LexRule(
    rule_id="LEX-SIG-004",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.MEDIUM,
    name="Signature Timestamp Present",
    description="Signature should include timestamp",
    predicate_fn="check_signature_timestamp",
    error_template="[{rule_id}] Signature missing timestamp",
    override_allowed=True,
    requires_senior_override=False,
)


# ============================================================================
# PREDICATE IMPLEMENTATIONS
# ============================================================================

def check_signature_present(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that PDO contains a signature field."""
    return "signature" in pdo and pdo["signature"] is not None


def check_signature_format(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that signature is in valid format."""
    sig = pdo.get("signature")
    if not sig:
        return False
    
    if isinstance(sig, dict):
        sig = sig.get("value", "")
    
    if not isinstance(sig, str):
        return False
    
    # Check hex format (64+ chars)
    hex_pattern = r"^[a-fA-F0-9]{64,}$"
    if re.match(hex_pattern, sig):
        return True
    
    # Check base64 format
    base64_pattern = r"^[A-Za-z0-9+/]{40,}={0,2}$"
    if re.match(base64_pattern, sig):
        return True
    
    return False


def check_signer_present(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that PDO identifies the signer."""
    # Check for signer field
    if "signer" in pdo and pdo["signer"]:
        return True
    
    # Check for signer in signature object
    sig = pdo.get("signature")
    if isinstance(sig, dict) and sig.get("signer"):
        return True
    
    # Check for agent_id as signer
    if "agent_id" in pdo and pdo["agent_id"]:
        return True
    
    return False


def check_signature_timestamp(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that signature includes timestamp."""
    sig = pdo.get("signature")
    
    if isinstance(sig, dict):
        if "timestamp" in sig or "signed_at" in sig:
            return True
    
    # Also accept PDO-level timestamp
    if "timestamp" in pdo or "created_at" in pdo:
        return True
    
    return False


# ============================================================================
# EXPORTS
# ============================================================================

SIGNATURE_RULES = [
    (RULE_SIG_001, check_signature_present),
    (RULE_SIG_002, check_signature_format),
    (RULE_SIG_003, check_signer_present),
    (RULE_SIG_004, check_signature_timestamp),
]


def create_signature_validator():
    """
    Create a validator function for all signature rules.
    
    Returns:
        List of (rule, predicate) tuples
    """
    return SIGNATURE_RULES
