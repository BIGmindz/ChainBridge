"""
Hash Rules
==========

Deterministic hash verification rules.

Validates hash presence, format, and consistency.
"""

from typing import Any, Callable
import hashlib
import json
import re

from ..schema import LexRule, RuleCategory, RuleSeverity


# Type alias
RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


# ============================================================================
# RULE DEFINITIONS
# ============================================================================

RULE_HASH_001 = LexRule(
    rule_id="LEX-HASH-001",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.CRITICAL,
    name="PDO Hash Present",
    description="PDO must contain a hash field for integrity verification",
    predicate_fn="check_hash_present",
    error_template="[{rule_id}] PDO missing required hash field",
    override_allowed=False,  # Critical — no override
    requires_senior_override=False,
)

RULE_HASH_002 = LexRule(
    rule_id="LEX-HASH-002",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.CRITICAL,
    name="Hash Format Valid",
    description="Hash must be valid SHA-256 format (64 hex chars)",
    predicate_fn="check_hash_format",
    error_template="[{rule_id}] Invalid hash format (expected SHA-256)",
    override_allowed=False,  # Critical — no override
    requires_senior_override=False,
)

RULE_HASH_003 = LexRule(
    rule_id="LEX-HASH-003",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.CRITICAL,
    name="Hash Integrity Valid",
    description="Computed hash must match declared hash",
    predicate_fn="check_hash_integrity",
    error_template="[{rule_id}] Hash mismatch - PDO may have been tampered",
    override_allowed=False,  # Critical — no override
    requires_senior_override=False,
)

RULE_HASH_004 = LexRule(
    rule_id="LEX-HASH-004",
    category=RuleCategory.INTEGRITY,
    severity=RuleSeverity.MEDIUM,
    name="Proof Hash Present",
    description="Proof section should have its own hash",
    predicate_fn="check_proof_hash_present",
    error_template="[{rule_id}] Proof section missing hash",
    override_allowed=True,
    requires_senior_override=False,
)


# ============================================================================
# PREDICATE IMPLEMENTATIONS
# ============================================================================

def check_hash_present(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that PDO contains a hash field."""
    return "hash" in pdo and pdo["hash"] is not None


def check_hash_format(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that hash is valid SHA-256 format."""
    hash_value = pdo.get("hash")
    if not hash_value:
        return False
    
    if not isinstance(hash_value, str):
        return False
    
    # SHA-256 is 64 hex characters
    sha256_pattern = r"^[a-fA-F0-9]{64}$"
    return bool(re.match(sha256_pattern, hash_value))


def check_hash_integrity(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that computed hash matches declared hash."""
    declared_hash = pdo.get("hash")
    if not declared_hash:
        return False
    
    # Create a copy without the hash field for computation
    pdo_copy = {k: v for k, v in pdo.items() if k != "hash"}
    
    # Compute hash
    data = json.dumps(pdo_copy, sort_keys=True)
    computed_hash = hashlib.sha256(data.encode()).hexdigest()
    
    return computed_hash.lower() == declared_hash.lower()


def check_proof_hash_present(pdo: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check that proof section has its own hash."""
    proof = pdo.get("proof")
    if not proof:
        return False
    
    if isinstance(proof, dict):
        return "hash" in proof or "proof_hash" in proof
    
    return False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def compute_pdo_hash(pdo: dict[str, Any], exclude_fields: list[str] = None) -> str:
    """
    Compute SHA-256 hash of PDO.
    
    Args:
        pdo: The PDO dictionary
        exclude_fields: Fields to exclude from hash computation
        
    Returns:
        SHA-256 hash as hex string
    """
    exclude = exclude_fields or ["hash", "signature"]
    pdo_copy = {k: v for k, v in pdo.items() if k not in exclude}
    data = json.dumps(pdo_copy, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


# ============================================================================
# EXPORTS
# ============================================================================

HASH_RULES = [
    (RULE_HASH_001, check_hash_present),
    (RULE_HASH_002, check_hash_format),
    (RULE_HASH_003, check_hash_integrity),
    (RULE_HASH_004, check_proof_hash_present),
]


def create_hash_validator():
    """
    Create a validator function for all hash rules.
    
    Returns:
        List of (rule, predicate) tuples
    """
    return HASH_RULES
