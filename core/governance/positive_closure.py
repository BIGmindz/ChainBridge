"""
POSITIVE CLOSURE - Governance Primitive for Verified Execution Termination.

PAC Reference: PAC-JEFFREY-DRAFT-GOVERNANCE-POSITIVE-CLOSURE-STANDARD-030
Purpose: Terminal governance artifact asserting all requirements met.

A session is NOT complete until POSITIVE_CLOSURE is explicitly emitted.
Success must be provable, not assumed.

INVARIANTS:
    INV-PC-001: BER without POSITIVE_CLOSURE is INVALID
    INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists
    INV-PC-003: POSITIVE_CLOSURE may only be emitted by GID-00
    INV-PC-004: Must reference PAC ID, BER ID, all WRAP hashes, final state
    INV-PC-005: Absence forces SESSION_INVALID
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, FrozenSet, Optional, Sequence
import uuid


# =============================================================================
# CONSTANTS
# =============================================================================

POSITIVE_CLOSURE_AUTHORITY = "GID-00"
"""Only orchestration engine (GID-00) may emit POSITIVE_CLOSURE."""

POSITIVE_CLOSURE_VERSION = "1.0.0"
"""Schema version for POSITIVE_CLOSURE artifacts."""


# =============================================================================
# EXCEPTIONS
# =============================================================================

class PositiveClosureError(Exception):
    """Base exception for all positive closure violations."""
    pass


class PositiveClosureAuthorityError(PositiveClosureError):
    """
    Raised when non-GID-00 entity attempts to emit POSITIVE_CLOSURE.
    
    Violation of INV-PC-003.
    """
    
    def __init__(self, attempted_issuer: str) -> None:
        self.attempted_issuer = attempted_issuer
        super().__init__(
            f"POSITIVE_CLOSURE authority violation: '{attempted_issuer}' "
            f"attempted emission. Only '{POSITIVE_CLOSURE_AUTHORITY}' permitted. "
            f"[INV-PC-003]"
        )


class PositiveClosureIncompleteError(PositiveClosureError):
    """
    Raised when POSITIVE_CLOSURE is missing required components.
    
    Violation of INV-PC-004.
    """
    
    def __init__(self, missing_fields: Sequence[str]) -> None:
        self.missing_fields = list(missing_fields)
        super().__init__(
            f"POSITIVE_CLOSURE incomplete: missing required fields "
            f"{self.missing_fields}. [INV-PC-004]"
        )


class PositiveClosureNotEmittedError(PositiveClosureError):
    """
    Raised when session completes without POSITIVE_CLOSURE.
    
    Violation of INV-PC-005.
    """
    
    def __init__(self, pac_id: str, session_id: Optional[str] = None) -> None:
        self.pac_id = pac_id
        self.session_id = session_id
        context = f" (session: {session_id})" if session_id else ""
        super().__init__(
            f"POSITIVE_CLOSURE not emitted for PAC '{pac_id}'{context}. "
            f"Session is INVALID. [INV-PC-005]"
        )


class PositiveClosureHashMismatchError(PositiveClosureError):
    """
    Raised when POSITIVE_CLOSURE content hash doesn't match expected.
    
    Indicates tampering or corruption.
    """
    
    def __init__(self, expected: str, actual: str) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"POSITIVE_CLOSURE hash mismatch: expected '{expected[:16]}...' "
            f"but got '{actual[:16]}...'. Content may be tampered."
        )


class PositiveClosureWrapMismatchError(PositiveClosureError):
    """
    Raised when WRAP hashes in closure don't match expected.
    
    Indicates missing or extra WRAPs.
    """
    
    def __init__(
        self, 
        expected_count: int, 
        actual_count: int,
        missing: Optional[Sequence[str]] = None
    ) -> None:
        self.expected_count = expected_count
        self.actual_count = actual_count
        self.missing = list(missing) if missing else []
        super().__init__(
            f"POSITIVE_CLOSURE WRAP mismatch: expected {expected_count} WRAPs "
            f"but closure contains {actual_count}. Missing: {self.missing}"
        )


class PositiveClosureBERMissingError(PositiveClosureError):
    """
    Raised when POSITIVE_CLOSURE lacks BER reference.
    
    Violation of INV-PC-001 and INV-PC-004.
    """
    
    def __init__(self, pac_id: str) -> None:
        self.pac_id = pac_id
        super().__init__(
            f"POSITIVE_CLOSURE for PAC '{pac_id}' missing BER reference. "
            f"BER without POSITIVE_CLOSURE is INVALID. [INV-PC-001, INV-PC-004]"
        )


# =============================================================================
# ENUMS
# =============================================================================

class ClosureState(Enum):
    """
    States for positive closure lifecycle.
    """
    PENDING = "PENDING"           # Closure not yet created
    VALIDATING = "VALIDATING"     # Validation in progress
    EMITTED = "EMITTED"           # Successfully emitted
    INVALID = "INVALID"           # Failed validation
    ORPHANED = "ORPHANED"         # BER exists but closure missing


class ClosureDecision(Enum):
    """
    Closure decision outcomes.
    """
    CLEAN = "CLEAN"               # Session closed cleanly
    CORRECTIVE = "CORRECTIVE"     # Session closed with corrections
    INVALID = "INVALID"           # Session invalid, closure failed


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class PositiveClosure:
    """
    Immutable positive closure artifact.
    
    INV-PC-003: Only GID-00 may create.
    INV-PC-004: Must reference PAC ID, BER ID, all WRAP hashes, final state.
    
    This is a terminal governance artifact marking verified execution completion.
    Once created, it is immutable and hash-verified.
    
    Attributes:
        closure_id: Unique identifier for this closure
        pac_id: Reference to originating PAC
        ber_id: Reference to issued BER
        wrap_hashes: Tuple of all agent WRAP hashes (immutable)
        wrap_count: Number of WRAPs (for validation)
        final_state: Terminal execution state name
        invariants_verified: Whether all invariants passed
        checkpoints_resolved: Count of resolved checkpoints (0 unresolved required)
        issuer: Must be GID-00
        closed_at: ISO-8601 timestamp of closure
        closure_hash: SHA-256 hash of closure content
        version: Schema version
        decision: Closure decision (CLEAN, CORRECTIVE, INVALID)
    """
    
    closure_id: str
    pac_id: str
    ber_id: str
    wrap_hashes: tuple[str, ...]
    wrap_count: int
    final_state: str
    invariants_verified: bool
    checkpoints_resolved: int
    issuer: str
    closed_at: str
    closure_hash: str
    version: str = POSITIVE_CLOSURE_VERSION
    decision: str = "CLEAN"
    
    def __post_init__(self) -> None:
        """Validate closure on creation."""
        # INV-PC-003: Authority check
        if self.issuer != POSITIVE_CLOSURE_AUTHORITY:
            raise PositiveClosureAuthorityError(self.issuer)
        
        # INV-PC-004: Required references
        missing = []
        if not self.pac_id:
            missing.append("pac_id")
        if not self.ber_id:
            missing.append("ber_id")
        if self.wrap_hashes is None:
            missing.append("wrap_hashes")
        if not self.final_state:
            missing.append("final_state")
        
        if missing:
            raise PositiveClosureIncompleteError(missing)
        
        # Validate hash
        expected_hash = compute_closure_hash_from_parts(
            pac_id=self.pac_id,
            ber_id=self.ber_id,
            wrap_hashes=self.wrap_hashes,
            wrap_count=self.wrap_count,
            final_state=self.final_state,
            issuer=self.issuer,
            closed_at=self.closed_at,
        )
        
        if self.closure_hash != expected_hash:
            raise PositiveClosureHashMismatchError(expected_hash, self.closure_hash)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "closure_id": self.closure_id,
            "pac_id": self.pac_id,
            "ber_id": self.ber_id,
            "wrap_hashes": list(self.wrap_hashes),
            "wrap_count": self.wrap_count,
            "final_state": self.final_state,
            "invariants_verified": self.invariants_verified,
            "checkpoints_resolved": self.checkpoints_resolved,
            "issuer": self.issuer,
            "closed_at": self.closed_at,
            "closure_hash": self.closure_hash,
            "version": self.version,
            "decision": self.decision,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PositiveClosure":
        """Create from dictionary representation."""
        return cls(
            closure_id=data["closure_id"],
            pac_id=data["pac_id"],
            ber_id=data["ber_id"],
            wrap_hashes=tuple(data["wrap_hashes"]),
            wrap_count=data["wrap_count"],
            final_state=data["final_state"],
            invariants_verified=data["invariants_verified"],
            checkpoints_resolved=data["checkpoints_resolved"],
            issuer=data["issuer"],
            closed_at=data["closed_at"],
            closure_hash=data["closure_hash"],
            version=data.get("version", POSITIVE_CLOSURE_VERSION),
            decision=data.get("decision", "CLEAN"),
        )


@dataclass
class ClosureBuilder:
    """
    Builder for constructing POSITIVE_CLOSURE artifacts.
    
    Only GID-00 should use this builder. Provides validation and
    hash computation for closure creation.
    
    Usage:
        builder = ClosureBuilder(pac_id="PAC-001", ber_id="BER-001")
        builder.add_wrap_hash("wrap-hash-1")
        builder.add_wrap_hash("wrap-hash-2")
        builder.set_final_state("SESSION_CLOSED")
        closure = builder.build()
    """
    
    pac_id: str
    ber_id: str
    wrap_hashes: list[str] = field(default_factory=list)
    final_state: Optional[str] = None
    invariants_verified: bool = True
    checkpoints_resolved: int = 0
    decision: str = "CLEAN"
    _issuer: str = field(default=POSITIVE_CLOSURE_AUTHORITY, init=False)
    
    def add_wrap_hash(self, wrap_hash: str) -> "ClosureBuilder":
        """Add a WRAP hash to the closure."""
        if wrap_hash not in self.wrap_hashes:
            self.wrap_hashes.append(wrap_hash)
        return self
    
    def add_wrap_hashes(self, hashes: Sequence[str]) -> "ClosureBuilder":
        """Add multiple WRAP hashes to the closure."""
        for h in hashes:
            self.add_wrap_hash(h)
        return self
    
    def set_final_state(self, state: str) -> "ClosureBuilder":
        """Set the final execution state."""
        self.final_state = state
        return self
    
    def set_invariants_verified(self, verified: bool) -> "ClosureBuilder":
        """Set whether all invariants were verified."""
        self.invariants_verified = verified
        return self
    
    def set_checkpoints_resolved(self, count: int) -> "ClosureBuilder":
        """Set the count of resolved checkpoints."""
        self.checkpoints_resolved = count
        return self
    
    def set_decision(self, decision: str) -> "ClosureBuilder":
        """Set the closure decision."""
        self.decision = decision
        return self
    
    def validate(self) -> list[str]:
        """
        Validate builder state before building.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.pac_id:
            errors.append("pac_id is required")
        if not self.ber_id:
            errors.append("ber_id is required")
        if not self.wrap_hashes:
            errors.append("at least one wrap_hash is required")
        if not self.final_state:
            errors.append("final_state is required")
        
        return errors
    
    def build(self) -> PositiveClosure:
        """
        Build the POSITIVE_CLOSURE artifact.
        
        Raises:
            PositiveClosureIncompleteError: If required fields are missing
            
        Returns:
            Immutable PositiveClosure artifact
        """
        errors = self.validate()
        if errors:
            raise PositiveClosureIncompleteError(errors)
        
        closure_id = f"PC-{uuid.uuid4().hex[:12].upper()}"
        closed_at = datetime.now(timezone.utc).isoformat()
        wrap_tuple = tuple(sorted(self.wrap_hashes))
        wrap_count = len(wrap_tuple)
        
        closure_hash = compute_closure_hash_from_parts(
            pac_id=self.pac_id,
            ber_id=self.ber_id,
            wrap_hashes=wrap_tuple,
            wrap_count=wrap_count,
            final_state=self.final_state,
            issuer=self._issuer,
            closed_at=closed_at,
        )
        
        return PositiveClosure(
            closure_id=closure_id,
            pac_id=self.pac_id,
            ber_id=self.ber_id,
            wrap_hashes=wrap_tuple,
            wrap_count=wrap_count,
            final_state=self.final_state,
            invariants_verified=self.invariants_verified,
            checkpoints_resolved=self.checkpoints_resolved,
            issuer=self._issuer,
            closed_at=closed_at,
            closure_hash=closure_hash,
            decision=self.decision,
        )


@dataclass
class ClosureValidationResult:
    """Result of closure validation."""
    
    valid: bool
    closure: Optional[PositiveClosure]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.valid and len(self.errors) == 0


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def compute_closure_hash_from_parts(
    pac_id: str,
    ber_id: str,
    wrap_hashes: tuple[str, ...] | Sequence[str],
    wrap_count: int,
    final_state: str,
    issuer: str,
    closed_at: str,
) -> str:
    """
    Compute deterministic hash of closure content.
    
    The hash is computed from a canonical JSON representation
    ensuring consistent ordering and formatting.
    
    Args:
        pac_id: PAC identifier
        ber_id: BER identifier
        wrap_hashes: Sequence of WRAP hashes
        wrap_count: Number of WRAPs
        final_state: Terminal state name
        issuer: Closure issuer (must be GID-00)
        closed_at: ISO-8601 timestamp
        
    Returns:
        SHA-256 hex digest of canonical content
    """
    content = {
        "pac_id": pac_id,
        "ber_id": ber_id,
        "wrap_hashes": sorted(wrap_hashes),
        "wrap_count": wrap_count,
        "final_state": final_state,
        "issuer": issuer,
        "closed_at": closed_at,
    }
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_closure_hash(closure: PositiveClosure) -> bool:
    """
    Verify that closure hash matches content.
    
    Args:
        closure: PositiveClosure to verify
        
    Returns:
        True if hash matches, False otherwise
    """
    expected = compute_closure_hash_from_parts(
        pac_id=closure.pac_id,
        ber_id=closure.ber_id,
        wrap_hashes=closure.wrap_hashes,
        wrap_count=closure.wrap_count,
        final_state=closure.final_state,
        issuer=closure.issuer,
        closed_at=closure.closed_at,
    )
    return closure.closure_hash == expected


def create_positive_closure(
    pac_id: str,
    ber_id: str,
    wrap_hashes: Sequence[str],
    final_state: str,
    invariants_verified: bool = True,
    checkpoints_resolved: int = 0,
    decision: str = "CLEAN",
) -> PositiveClosure:
    """
    Factory function to create POSITIVE_CLOSURE.
    
    This function should only be called by GID-00 (orchestration engine).
    
    Args:
        pac_id: PAC identifier
        ber_id: BER identifier  
        wrap_hashes: List of WRAP hashes from agents
        final_state: Terminal execution state
        invariants_verified: Whether all invariants passed
        checkpoints_resolved: Number of resolved checkpoints
        decision: Closure decision (CLEAN, CORRECTIVE, INVALID)
        
    Returns:
        Immutable PositiveClosure artifact
        
    Raises:
        PositiveClosureIncompleteError: If required fields missing
    """
    builder = ClosureBuilder(pac_id=pac_id, ber_id=ber_id)
    builder.add_wrap_hashes(wrap_hashes)
    builder.set_final_state(final_state)
    builder.set_invariants_verified(invariants_verified)
    builder.set_checkpoints_resolved(checkpoints_resolved)
    builder.set_decision(decision)
    
    return builder.build()


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_closure_for_ber(
    closure: Optional[PositiveClosure],
    ber_id: str,
) -> ClosureValidationResult:
    """
    Validate closure for BER emission (INV-PC-001).
    
    A BER without POSITIVE_CLOSURE is INVALID.
    
    Args:
        closure: PositiveClosure to validate (or None)
        ber_id: BER identifier to check against
        
    Returns:
        ClosureValidationResult with validation status
    """
    errors = []
    warnings = []
    
    if closure is None:
        errors.append(f"BER '{ber_id}' has no POSITIVE_CLOSURE [INV-PC-001]")
        return ClosureValidationResult(valid=False, closure=None, errors=errors)
    
    if closure.ber_id != ber_id:
        errors.append(
            f"Closure BER mismatch: closure references '{closure.ber_id}' "
            f"but BER is '{ber_id}'"
        )
    
    if not verify_closure_hash(closure):
        errors.append("Closure hash verification failed")
    
    return ClosureValidationResult(
        valid=len(errors) == 0,
        closure=closure,
        errors=errors,
        warnings=warnings,
    )


def validate_closure_for_pdo(
    closure: Optional[PositiveClosure],
    pac_id: str,
) -> ClosureValidationResult:
    """
    Validate closure for PDO emission (INV-PC-002).
    
    A PDO may not be emitted unless POSITIVE_CLOSURE exists.
    
    Args:
        closure: PositiveClosure to validate (or None)
        pac_id: PAC identifier to check against
        
    Returns:
        ClosureValidationResult with validation status
    """
    errors = []
    warnings = []
    
    if closure is None:
        errors.append(f"PDO for PAC '{pac_id}' blocked: no POSITIVE_CLOSURE [INV-PC-002]")
        return ClosureValidationResult(valid=False, closure=None, errors=errors)
    
    if closure.pac_id != pac_id:
        errors.append(
            f"Closure PAC mismatch: closure references '{closure.pac_id}' "
            f"but PDO is for '{pac_id}'"
        )
    
    if not closure.invariants_verified:
        warnings.append("Closure has unverified invariants")
    
    if not verify_closure_hash(closure):
        errors.append("Closure hash verification failed")
    
    return ClosureValidationResult(
        valid=len(errors) == 0,
        closure=closure,
        errors=errors,
        warnings=warnings,
    )


def validate_closure_wraps(
    closure: PositiveClosure,
    expected_wrap_hashes: Sequence[str],
) -> ClosureValidationResult:
    """
    Validate that closure contains all expected WRAP hashes.
    
    Args:
        closure: PositiveClosure to validate
        expected_wrap_hashes: Expected WRAP hashes
        
    Returns:
        ClosureValidationResult with validation status
    """
    errors = []
    warnings = []
    
    expected_set = frozenset(expected_wrap_hashes)
    actual_set = frozenset(closure.wrap_hashes)
    
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    
    if missing:
        errors.append(f"Closure missing WRAPs: {list(missing)}")
    
    if extra:
        warnings.append(f"Closure has unexpected WRAPs: {list(extra)}")
    
    if closure.wrap_count != len(expected_wrap_hashes):
        errors.append(
            f"WRAP count mismatch: closure has {closure.wrap_count} "
            f"but expected {len(expected_wrap_hashes)}"
        )
    
    return ClosureValidationResult(
        valid=len(errors) == 0,
        closure=closure,
        errors=errors,
        warnings=warnings,
    )


# =============================================================================
# ENFORCEMENT FUNCTIONS
# =============================================================================

def enforce_closure_before_ber(
    closure: Optional[PositiveClosure],
    ber_id: str,
) -> None:
    """
    Enforce INV-PC-001: BER without POSITIVE_CLOSURE is INVALID.
    
    Args:
        closure: PositiveClosure to check
        ber_id: BER identifier
        
    Raises:
        PositiveClosureBERMissingError: If closure is missing
    """
    result = validate_closure_for_ber(closure, ber_id)
    if not result.is_valid:
        # Get PAC ID from closure or use placeholder
        pac_id = closure.pac_id if closure else "UNKNOWN"
        raise PositiveClosureBERMissingError(pac_id)


def enforce_closure_before_pdo(
    closure: Optional[PositiveClosure],
    pac_id: str,
) -> None:
    """
    Enforce INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists.
    
    Args:
        closure: PositiveClosure to check
        pac_id: PAC identifier
        
    Raises:
        PositiveClosureNotEmittedError: If closure is missing
    """
    result = validate_closure_for_pdo(closure, pac_id)
    if not result.is_valid:
        raise PositiveClosureNotEmittedError(pac_id)


def enforce_closure_authority(issuer: str) -> None:
    """
    Enforce INV-PC-003: POSITIVE_CLOSURE may only be emitted by GID-00.
    
    Args:
        issuer: Entity attempting to emit closure
        
    Raises:
        PositiveClosureAuthorityError: If issuer is not GID-00
    """
    if issuer != POSITIVE_CLOSURE_AUTHORITY:
        raise PositiveClosureAuthorityError(issuer)


def enforce_session_closure(
    closure: Optional[PositiveClosure],
    pac_id: str,
    session_id: Optional[str] = None,
) -> None:
    """
    Enforce INV-PC-005: Absence of POSITIVE_CLOSURE forces SESSION_INVALID.
    
    Args:
        closure: PositiveClosure to check
        pac_id: PAC identifier
        session_id: Optional session identifier
        
    Raises:
        PositiveClosureNotEmittedError: If closure is missing
    """
    if closure is None:
        raise PositiveClosureNotEmittedError(pac_id, session_id)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Constants
    "POSITIVE_CLOSURE_AUTHORITY",
    "POSITIVE_CLOSURE_VERSION",
    # Exceptions
    "PositiveClosureError",
    "PositiveClosureAuthorityError",
    "PositiveClosureIncompleteError",
    "PositiveClosureNotEmittedError",
    "PositiveClosureHashMismatchError",
    "PositiveClosureWrapMismatchError",
    "PositiveClosureBERMissingError",
    # Enums
    "ClosureState",
    "ClosureDecision",
    # Data Classes
    "PositiveClosure",
    "ClosureBuilder",
    "ClosureValidationResult",
    # Functions
    "compute_closure_hash_from_parts",
    "verify_closure_hash",
    "create_positive_closure",
    "validate_closure_for_ber",
    "validate_closure_for_pdo",
    "validate_closure_wraps",
    "enforce_closure_before_ber",
    "enforce_closure_before_pdo",
    "enforce_closure_authority",
    "enforce_session_closure",
]
