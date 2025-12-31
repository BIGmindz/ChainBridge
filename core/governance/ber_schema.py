"""
BER Schema - Benson Execution Response Schema with POSITIVE_CLOSURE Reference.

PAC Reference: PAC-JEFFREY-DRAFT-GOVERNANCE-POSITIVE-CLOSURE-STANDARD-030
Purpose: Define BER schema with mandatory POSITIVE_CLOSURE binding.

A BER without POSITIVE_CLOSURE is INVALID (INV-PC-001).

INVARIANTS:
    INV-BER-PC-001: BER must be followed by POSITIVE_CLOSURE emission
    INV-BER-PC-002: BER artifact must reference future closure hash
    INV-BER-PC-003: Orphaned BERs (without closure) are SESSION_INVALID
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

BER_SCHEMA_VERSION = "2.0.0"
"""Schema version with POSITIVE_CLOSURE support."""

BER_AUTHORITY = "GID-00"
"""Only orchestration engine (GID-00) may issue BER."""


# =============================================================================
# EXCEPTIONS
# =============================================================================

class BERSchemaError(Exception):
    """Base exception for BER schema violations."""
    pass


class BEROrphanedError(BERSchemaError):
    """
    Raised when BER exists without POSITIVE_CLOSURE.
    
    Violation of INV-PC-001: BER without POSITIVE_CLOSURE is INVALID.
    """
    
    def __init__(self, ber_id: str, pac_id: str) -> None:
        self.ber_id = ber_id
        self.pac_id = pac_id
        super().__init__(
            f"BER '{ber_id}' for PAC '{pac_id}' is ORPHANED: "
            f"no POSITIVE_CLOSURE exists. Session is INVALID. [INV-PC-001]"
        )


class BERClosureMismatchError(BERSchemaError):
    """
    Raised when BER closure reference doesn't match actual closure.
    """
    
    def __init__(self, ber_id: str, expected: str, actual: str) -> None:
        self.ber_id = ber_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"BER '{ber_id}' closure mismatch: expected '{expected[:16]}...' "
            f"but closure hash is '{actual[:16]}...'"
        )


class BERAuthorityError(BERSchemaError):
    """
    Raised when non-GID-00 attempts BER issuance.
    """
    
    def __init__(self, attempted_issuer: str) -> None:
        self.attempted_issuer = attempted_issuer
        super().__init__(
            f"BER authority violation: '{attempted_issuer}' attempted issuance. "
            f"Only '{BER_AUTHORITY}' may issue BER."
        )


# =============================================================================
# ENUMS
# =============================================================================

class BERDecision(Enum):
    """BER decision outcomes."""
    APPROVE = "APPROVE"
    CORRECTIVE = "CORRECTIVE"
    REJECT = "REJECT"


class BERState(Enum):
    """BER lifecycle states."""
    ISSUED = "ISSUED"           # BER issued internally
    EMITTED = "EMITTED"         # BER emitted externally
    CLOSURE_BOUND = "CLOSURE_BOUND"  # POSITIVE_CLOSURE emitted
    ORPHANED = "ORPHANED"       # No closure (invalid)


# =============================================================================
# BER SCHEMA (v2 with POSITIVE_CLOSURE)
# =============================================================================

@dataclass(frozen=True)
class BERSchemaV2:
    """
    BER Schema Version 2 with POSITIVE_CLOSURE support.
    
    INV-PC-001: BER must have corresponding POSITIVE_CLOSURE.
    INV-BER-PC-001: BER must be followed by POSITIVE_CLOSURE emission.
    
    This schema extends BERArtifact with closure binding fields.
    """
    
    # Identity
    ber_id: str
    pac_id: str
    
    # Decision
    decision: str
    issuer: str
    
    # Timestamps
    issued_at: str
    emitted_at: Optional[str] = None
    
    # WRAP reference
    wrap_status: str = "UNKNOWN"
    wrap_hash: Optional[str] = None
    
    # Session state
    session_state: str = "BER_ISSUED"
    
    # PAC-030: POSITIVE_CLOSURE binding
    closure_id: Optional[str] = None
    closure_hash: Optional[str] = None
    closure_bound_at: Optional[str] = None
    
    # Schema version
    schema_version: str = BER_SCHEMA_VERSION
    
    def __post_init__(self) -> None:
        """Validate BER on creation."""
        if self.issuer != BER_AUTHORITY:
            raise BERAuthorityError(self.issuer)
    
    @property
    def is_emitted(self) -> bool:
        """True if BER has been emitted."""
        return self.emitted_at is not None
    
    @property
    def is_closure_bound(self) -> bool:
        """True if BER is bound to POSITIVE_CLOSURE."""
        return self.closure_hash is not None
    
    @property
    def is_orphaned(self) -> bool:
        """True if BER is emitted but not closure-bound."""
        return self.is_emitted and not self.is_closure_bound
    
    @property
    def state(self) -> BERState:
        """Get current BER state."""
        if self.is_closure_bound:
            return BERState.CLOSURE_BOUND
        elif self.is_emitted:
            return BERState.EMITTED
        else:
            return BERState.ISSUED
    
    def bind_closure(
        self,
        closure_id: str,
        closure_hash: str,
    ) -> "BERSchemaV2":
        """
        Create new BER with closure binding.
        
        Returns a new immutable BER with closure fields populated.
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Create new instance with closure binding
        return BERSchemaV2(
            ber_id=self.ber_id,
            pac_id=self.pac_id,
            decision=self.decision,
            issuer=self.issuer,
            issued_at=self.issued_at,
            emitted_at=self.emitted_at,
            wrap_status=self.wrap_status,
            wrap_hash=self.wrap_hash,
            session_state="CLOSURE_BOUND",
            closure_id=closure_id,
            closure_hash=closure_hash,
            closure_bound_at=now,
            schema_version=self.schema_version,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "ber_id": self.ber_id,
            "pac_id": self.pac_id,
            "decision": self.decision,
            "issuer": self.issuer,
            "issued_at": self.issued_at,
            "emitted_at": self.emitted_at,
            "wrap_status": self.wrap_status,
            "wrap_hash": self.wrap_hash,
            "session_state": self.session_state,
            "closure_id": self.closure_id,
            "closure_hash": self.closure_hash,
            "closure_bound_at": self.closure_bound_at,
            "schema_version": self.schema_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BERSchemaV2":
        """Create from dictionary representation."""
        return cls(
            ber_id=data["ber_id"],
            pac_id=data["pac_id"],
            decision=data["decision"],
            issuer=data["issuer"],
            issued_at=data["issued_at"],
            emitted_at=data.get("emitted_at"),
            wrap_status=data.get("wrap_status", "UNKNOWN"),
            wrap_hash=data.get("wrap_hash"),
            session_state=data.get("session_state", "BER_ISSUED"),
            closure_id=data.get("closure_id"),
            closure_hash=data.get("closure_hash"),
            closure_bound_at=data.get("closure_bound_at"),
            schema_version=data.get("schema_version", BER_SCHEMA_VERSION),
        )


# =============================================================================
# BER VALIDATION
# =============================================================================

@dataclass
class BERValidationResult:
    """Result of BER validation."""
    
    valid: bool
    ber: Optional[BERSchemaV2]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid and len(self.errors) == 0


def validate_ber_closure_binding(
    ber: BERSchemaV2,
    expected_closure_hash: Optional[str] = None,
) -> BERValidationResult:
    """
    Validate BER closure binding (INV-PC-001).
    
    Args:
        ber: BER to validate
        expected_closure_hash: Optional expected closure hash
        
    Returns:
        BERValidationResult with validation status
    """
    errors = []
    warnings = []
    
    # Check if emitted BER has closure binding
    if ber.is_emitted and not ber.is_closure_bound:
        errors.append(
            f"BER '{ber.ber_id}' is ORPHANED: emitted but no POSITIVE_CLOSURE [INV-PC-001]"
        )
    
    # Check closure hash match if expected provided
    if expected_closure_hash and ber.closure_hash:
        if ber.closure_hash != expected_closure_hash:
            errors.append(
                f"BER closure hash mismatch: expected '{expected_closure_hash[:16]}...' "
                f"but got '{ber.closure_hash[:16]}...'"
            )
    
    return BERValidationResult(
        valid=len(errors) == 0,
        ber=ber,
        errors=errors,
        warnings=warnings,
    )


def enforce_ber_closure_binding(ber: BERSchemaV2) -> None:
    """
    Enforce INV-PC-001: Orphaned BERs are invalid.
    
    Args:
        ber: BER to check
        
    Raises:
        BEROrphanedError: If BER is emitted without closure binding
    """
    if ber.is_orphaned:
        raise BEROrphanedError(ber.ber_id, ber.pac_id)


# =============================================================================
# BER FACTORY
# =============================================================================

def create_ber_v2(
    pac_id: str,
    decision: str,
    wrap_status: str = "UNKNOWN",
    wrap_hash: Optional[str] = None,
) -> BERSchemaV2:
    """
    Create a new BER v2 artifact.
    
    Args:
        pac_id: PAC identifier
        decision: BER decision (APPROVE, CORRECTIVE, REJECT)
        wrap_status: WRAP status
        wrap_hash: WRAP content hash
        
    Returns:
        New BERSchemaV2 artifact
    """
    ber_id = f"BER-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    
    return BERSchemaV2(
        ber_id=ber_id,
        pac_id=pac_id,
        decision=decision,
        issuer=BER_AUTHORITY,
        issued_at=now,
        wrap_status=wrap_status,
        wrap_hash=wrap_hash,
        session_state="BER_ISSUED",
    )


def emit_ber_v2(ber: BERSchemaV2) -> BERSchemaV2:
    """
    Mark BER as emitted.
    
    Returns new BER with emitted_at timestamp.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    return BERSchemaV2(
        ber_id=ber.ber_id,
        pac_id=ber.pac_id,
        decision=ber.decision,
        issuer=ber.issuer,
        issued_at=ber.issued_at,
        emitted_at=now,
        wrap_status=ber.wrap_status,
        wrap_hash=ber.wrap_hash,
        session_state="BER_EMITTED",
        closure_id=ber.closure_id,
        closure_hash=ber.closure_hash,
        closure_bound_at=ber.closure_bound_at,
        schema_version=ber.schema_version,
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Constants
    "BER_SCHEMA_VERSION",
    "BER_AUTHORITY",
    # Exceptions
    "BERSchemaError",
    "BEROrphanedError",
    "BERClosureMismatchError",
    "BERAuthorityError",
    # Enums
    "BERDecision",
    "BERState",
    # Data Classes
    "BERSchemaV2",
    "BERValidationResult",
    # Functions
    "validate_ber_closure_binding",
    "enforce_ber_closure_binding",
    "create_ber_v2",
    "emit_ber_v2",
]
