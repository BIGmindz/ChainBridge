"""
PDO Schema - Proof Decision Outcome Schema with POSITIVE_CLOSURE Requirement.

PAC Reference: PAC-JEFFREY-DRAFT-GOVERNANCE-POSITIVE-CLOSURE-STANDARD-030
Purpose: Define PDO schema with mandatory POSITIVE_CLOSURE binding.

A PDO may not be emitted unless POSITIVE_CLOSURE exists (INV-PC-002).

INVARIANTS:
    INV-PDO-PC-001: PDO must reference POSITIVE_CLOSURE hash
    INV-PDO-PC-002: PDO without closure reference is INVALID
    INV-PDO-PC-003: PDO emission is gated by POSITIVE_CLOSURE existence
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Sequence
import uuid


# =============================================================================
# CONSTANTS
# =============================================================================

PDO_SCHEMA_VERSION = "2.0.0"
"""Schema version with POSITIVE_CLOSURE support."""

PDO_AUTHORITY = "GID-00"
"""Only orchestration engine (GID-00) may create PDO."""

VALID_OUTCOMES = frozenset({"ACCEPTED", "CORRECTIVE", "REJECTED"})
"""Valid PDO outcome statuses."""


# =============================================================================
# EXCEPTIONS
# =============================================================================

class PDOSchemaError(Exception):
    """Base exception for PDO schema violations."""
    pass


class PDOClosureMissingError(PDOSchemaError):
    """
    Raised when PDO is created without POSITIVE_CLOSURE.
    
    Violation of INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists.
    """
    
    def __init__(self, pac_id: str) -> None:
        self.pac_id = pac_id
        super().__init__(
            f"PDO for PAC '{pac_id}' blocked: POSITIVE_CLOSURE does not exist. "
            f"INV-PC-002 requires closure before PDO emission."
        )


class PDOClosureHashMismatchError(PDOSchemaError):
    """
    Raised when PDO closure reference doesn't match actual closure.
    """
    
    def __init__(self, pdo_id: str, expected: str, actual: str) -> None:
        self.pdo_id = pdo_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"PDO '{pdo_id}' closure mismatch: expected '{expected[:16]}...' "
            f"but closure hash is '{actual[:16]}...'"
        )


class PDOAuthorityError(PDOSchemaError):
    """
    Raised when non-GID-00 attempts PDO creation.
    """
    
    def __init__(self, attempted_issuer: str) -> None:
        self.attempted_issuer = attempted_issuer
        super().__init__(
            f"PDO authority violation: '{attempted_issuer}' attempted creation. "
            f"Only '{PDO_AUTHORITY}' may create PDO."
        )


class PDOInvalidOutcomeError(PDOSchemaError):
    """Raised when outcome status is invalid."""
    
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        super().__init__(
            f"PDO invalid outcome: '{outcome}' is not valid. "
            f"Valid outcomes: {', '.join(sorted(VALID_OUTCOMES))}"
        )


# =============================================================================
# ENUMS
# =============================================================================

class PDOOutcome(Enum):
    """PDO outcome statuses."""
    ACCEPTED = "ACCEPTED"
    CORRECTIVE = "CORRECTIVE"
    REJECTED = "REJECTED"


class PDOState(Enum):
    """PDO lifecycle states."""
    PENDING = "PENDING"         # PDO not yet created
    BLOCKED = "BLOCKED"         # Blocked by missing closure
    CREATED = "CREATED"         # PDO created
    EMITTED = "EMITTED"         # PDO emitted externally


# =============================================================================
# PDO SCHEMA (v2 with POSITIVE_CLOSURE)
# =============================================================================

@dataclass(frozen=True)
class PDOSchemaV2:
    """
    PDO Schema Version 2 with POSITIVE_CLOSURE support.
    
    INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists.
    INV-PDO-PC-001: PDO must reference POSITIVE_CLOSURE hash.
    
    This schema extends PDOArtifact with closure binding fields.
    """
    
    # Identity
    pdo_id: str
    pac_id: str
    
    # Component IDs
    wrap_id: str
    ber_id: str
    
    # Authority
    issuer: str  # Always "GID-00"
    
    # Hash Chain (Proof → Decision → Outcome)
    proof_hash: str
    decision_hash: str
    outcome_hash: str
    pdo_hash: str  # Chain binding
    
    # PAC-030: POSITIVE_CLOSURE binding
    closure_id: str
    closure_hash: str
    
    # Timestamps
    proof_at: str
    decision_at: str
    outcome_at: str
    created_at: str
    
    # Status
    outcome_status: str  # ACCEPTED / CORRECTIVE / REJECTED
    
    # Schema version
    schema_version: str = PDO_SCHEMA_VERSION
    
    def __post_init__(self) -> None:
        """Validate PDO on creation."""
        if self.issuer != PDO_AUTHORITY:
            raise PDOAuthorityError(self.issuer)
        
        if self.outcome_status not in VALID_OUTCOMES:
            raise PDOInvalidOutcomeError(self.outcome_status)
        
        # INV-PC-002: Must have closure reference
        if not self.closure_hash:
            raise PDOClosureMissingError(self.pac_id)
    
    @property
    def is_accepted(self) -> bool:
        """True if outcome is ACCEPTED."""
        return self.outcome_status == "ACCEPTED"
    
    @property
    def is_corrective(self) -> bool:
        """True if outcome is CORRECTIVE."""
        return self.outcome_status == "CORRECTIVE"
    
    @property
    def is_rejected(self) -> bool:
        """True if outcome is REJECTED."""
        return self.outcome_status == "REJECTED"
    
    @property
    def has_valid_closure(self) -> bool:
        """True if PDO has closure binding."""
        return bool(self.closure_id and self.closure_hash)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "wrap_id": self.wrap_id,
            "ber_id": self.ber_id,
            "issuer": self.issuer,
            "proof_hash": self.proof_hash,
            "decision_hash": self.decision_hash,
            "outcome_hash": self.outcome_hash,
            "pdo_hash": self.pdo_hash,
            "closure_id": self.closure_id,
            "closure_hash": self.closure_hash,
            "proof_at": self.proof_at,
            "decision_at": self.decision_at,
            "outcome_at": self.outcome_at,
            "created_at": self.created_at,
            "outcome_status": self.outcome_status,
            "schema_version": self.schema_version,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string (deterministic)."""
        return json.dumps(self.to_dict(), sort_keys=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDOSchemaV2":
        """Create from dictionary representation."""
        return cls(
            pdo_id=data["pdo_id"],
            pac_id=data["pac_id"],
            wrap_id=data["wrap_id"],
            ber_id=data["ber_id"],
            issuer=data["issuer"],
            proof_hash=data["proof_hash"],
            decision_hash=data["decision_hash"],
            outcome_hash=data["outcome_hash"],
            pdo_hash=data["pdo_hash"],
            closure_id=data["closure_id"],
            closure_hash=data["closure_hash"],
            proof_at=data["proof_at"],
            decision_at=data["decision_at"],
            outcome_at=data["outcome_at"],
            created_at=data["created_at"],
            outcome_status=data["outcome_status"],
            schema_version=data.get("schema_version", PDO_SCHEMA_VERSION),
        )


# =============================================================================
# PDO VALIDATION
# =============================================================================

@dataclass
class PDOValidationResult:
    """Result of PDO validation."""
    
    valid: bool
    pdo: Optional[PDOSchemaV2]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid and len(self.errors) == 0


def validate_pdo_closure_binding(
    pdo: PDOSchemaV2,
    expected_closure_hash: Optional[str] = None,
) -> PDOValidationResult:
    """
    Validate PDO closure binding (INV-PC-002).
    
    Args:
        pdo: PDO to validate
        expected_closure_hash: Optional expected closure hash
        
    Returns:
        PDOValidationResult with validation status
    """
    errors = []
    warnings = []
    
    # Check if PDO has closure binding
    if not pdo.has_valid_closure:
        errors.append(
            f"PDO '{pdo.pdo_id}' missing POSITIVE_CLOSURE reference [INV-PC-002]"
        )
    
    # Check closure hash match if expected provided
    if expected_closure_hash and pdo.closure_hash:
        if pdo.closure_hash != expected_closure_hash:
            errors.append(
                f"PDO closure hash mismatch: expected '{expected_closure_hash[:16]}...' "
                f"but got '{pdo.closure_hash[:16]}...'"
            )
    
    return PDOValidationResult(
        valid=len(errors) == 0,
        pdo=pdo,
        errors=errors,
        warnings=warnings,
    )


def enforce_pdo_closure_requirement(
    pac_id: str,
    closure_exists: bool,
) -> None:
    """
    Enforce INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists.
    
    Args:
        pac_id: PAC identifier
        closure_exists: Whether POSITIVE_CLOSURE exists
        
    Raises:
        PDOClosureMissingError: If closure doesn't exist
    """
    if not closure_exists:
        raise PDOClosureMissingError(pac_id)


# =============================================================================
# PDO FACTORY
# =============================================================================

def compute_proof_hash(wrap_data: Dict[str, Any]) -> str:
    """Compute proof hash from WRAP data."""
    canonical = json.dumps(wrap_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_decision_hash(ber_data: Dict[str, Any]) -> str:
    """Compute decision hash from BER data."""
    canonical = json.dumps(ber_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_outcome_hash(
    proof_hash: str,
    decision_hash: str,
    outcome_status: str,
) -> str:
    """Compute outcome hash binding proof and decision."""
    content = {
        "proof_hash": proof_hash,
        "decision_hash": decision_hash,
        "outcome_status": outcome_status,
    }
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_pdo_hash(
    pac_id: str,
    proof_hash: str,
    decision_hash: str,
    outcome_hash: str,
    closure_hash: str,
) -> str:
    """Compute PDO chain hash binding all components."""
    content = {
        "pac_id": pac_id,
        "proof_hash": proof_hash,
        "decision_hash": decision_hash,
        "outcome_hash": outcome_hash,
        "closure_hash": closure_hash,
    }
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def create_pdo_v2(
    pac_id: str,
    wrap_id: str,
    wrap_data: Dict[str, Any],
    ber_id: str,
    ber_data: Dict[str, Any],
    outcome_status: str,
    closure_id: str,
    closure_hash: str,
    proof_at: Optional[str] = None,
    decision_at: Optional[str] = None,
) -> PDOSchemaV2:
    """
    Create a new PDO v2 artifact with POSITIVE_CLOSURE binding.
    
    INV-PC-002: Requires closure_id and closure_hash.
    
    Args:
        pac_id: PAC identifier
        wrap_id: WRAP identifier
        wrap_data: WRAP data for proof hash
        ber_id: BER identifier
        ber_data: BER data for decision hash
        outcome_status: ACCEPTED/CORRECTIVE/REJECTED
        closure_id: POSITIVE_CLOSURE identifier
        closure_hash: POSITIVE_CLOSURE hash
        proof_at: Optional proof timestamp
        decision_at: Optional decision timestamp
        
    Returns:
        New PDOSchemaV2 artifact
    """
    # Enforce closure requirement
    enforce_pdo_closure_requirement(pac_id, bool(closure_hash))
    
    pdo_id = f"PDO-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Compute hash chain
    proof_hash = compute_proof_hash(wrap_data)
    decision_hash = compute_decision_hash(ber_data)
    outcome_hash = compute_outcome_hash(proof_hash, decision_hash, outcome_status)
    pdo_hash = compute_pdo_hash(pac_id, proof_hash, decision_hash, outcome_hash, closure_hash)
    
    return PDOSchemaV2(
        pdo_id=pdo_id,
        pac_id=pac_id,
        wrap_id=wrap_id,
        ber_id=ber_id,
        issuer=PDO_AUTHORITY,
        proof_hash=proof_hash,
        decision_hash=decision_hash,
        outcome_hash=outcome_hash,
        pdo_hash=pdo_hash,
        closure_id=closure_id,
        closure_hash=closure_hash,
        proof_at=proof_at or now,
        decision_at=decision_at or now,
        outcome_at=now,
        created_at=now,
        outcome_status=outcome_status,
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Constants
    "PDO_SCHEMA_VERSION",
    "PDO_AUTHORITY",
    "VALID_OUTCOMES",
    # Exceptions
    "PDOSchemaError",
    "PDOClosureMissingError",
    "PDOClosureHashMismatchError",
    "PDOAuthorityError",
    "PDOInvalidOutcomeError",
    # Enums
    "PDOOutcome",
    "PDOState",
    # Data Classes
    "PDOSchemaV2",
    "PDOValidationResult",
    # Functions
    "validate_pdo_closure_binding",
    "enforce_pdo_closure_requirement",
    "compute_proof_hash",
    "compute_decision_hash",
    "compute_outcome_hash",
    "compute_pdo_hash",
    "create_pdo_v2",
]
