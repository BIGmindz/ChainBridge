"""
ChainBridge PDO Artifact — Proof → Decision → Outcome Engine
════════════════════════════════════════════════════════════════════════════════

The PDOArtifact is the canonical, immutable, machine-verifiable object
representing every completed execution loop.

PDO formalizes Proof → Decision → Outcome as a concrete object, not a narrative.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-PDO-ARTIFACT-ENGINE-020
Effective Date: 2025-12-26

INVARIANTS:
- INV-PDO-001: One PDO per PAC (1:1:1:1 mapping)
- INV-PDO-002: Only GID-00 may create PDO
- INV-PDO-003: PDO is immutable after creation
- INV-PDO-004: Hash chain binds Proof → Decision → Outcome
- INV-PDO-005: PDO emission is synchronous with BER
- INV-PDO-006: All components required (no partial PDOs)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.governance.ber_loop_enforcer import BERArtifact


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Only ORCHESTRATION_ENGINE (GID-00) may create PDO
PDO_AUTHORITY = "GID-00"

# Valid outcome statuses
VALID_OUTCOMES = frozenset({"ACCEPTED", "CORRECTIVE", "REJECTED"})

# Hash pattern for validation
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class PDOCreationError(Exception):
    """Base exception for PDO creation errors."""
    pass


class PDOAuthorityError(PDOCreationError):
    """
    Raised when non-GID-00 attempts PDO creation.
    
    INV-PDO-002: Only ORCHESTRATION_ENGINE (GID-00) may create PDO.
    """
    
    def __init__(self, issuer: str):
        self.issuer = issuer
        super().__init__(
            f"PDO_AUTHORITY_VIOLATION: '{issuer}' attempted PDO creation. "
            f"Only '{PDO_AUTHORITY}' may create PDOArtifact. "
            f"Agents and drafting surfaces are prohibited."
        )


class PDOIncompleteError(PDOCreationError):
    """
    Raised when PDO is missing required components.
    
    INV-PDO-006: All components required (no partial PDOs).
    """
    
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(
            f"PDO_INCOMPLETE: Missing required components: {', '.join(missing)}. "
            f"PDO cannot be created without all components."
        )


class PDODuplicateError(PDOCreationError):
    """
    Raised when PDO already exists for PAC.
    
    INV-PDO-001: One PDO per PAC (1:1:1:1 mapping).
    """
    
    def __init__(self, pac_id: str, existing_pdo_id: str):
        self.pac_id = pac_id
        self.existing_pdo_id = existing_pdo_id
        super().__init__(
            f"PDO_DUPLICATE: PDO '{existing_pdo_id}' already exists for PAC '{pac_id}'. "
            f"One PAC produces exactly one PDO."
        )


class PDOHashMismatchError(PDOCreationError):
    """
    Raised when hash chain verification fails.
    
    INV-PDO-004: Hash chain binds Proof → Decision → Outcome.
    """
    
    def __init__(self, expected: str, actual: str, component: str):
        self.expected = expected
        self.actual = actual
        self.component = component
        super().__init__(
            f"PDO_HASH_MISMATCH: {component} hash mismatch. "
            f"Expected: {expected[:16]}..., Got: {actual[:16]}... "
            f"Hash chain integrity compromised."
        )


class PDOInvalidOutcomeError(PDOCreationError):
    """Raised when outcome status is invalid."""
    
    def __init__(self, outcome: str):
        self.outcome = outcome
        super().__init__(
            f"PDO_INVALID_OUTCOME: '{outcome}' is not a valid outcome status. "
            f"Valid outcomes: {', '.join(sorted(VALID_OUTCOMES))}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PDO ARTIFACT (IMMUTABLE)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PDOArtifact:
    """
    Immutable PDO (Proof → Decision → Outcome) artifact.
    
    This is the canonical, machine-verifiable object representing
    a completed execution loop. Created only by GID-00.
    
    INV-PDO-003: PDO is immutable after creation (frozen=True).
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
    
    # Timestamps
    proof_at: str
    decision_at: str
    outcome_at: str
    created_at: str
    
    # Status
    outcome_status: str  # ACCEPTED / CORRECTIVE / REJECTED
    
    # ───────────────────────────────────────────────────────────────────────────
    # PROPERTIES
    # ───────────────────────────────────────────────────────────────────────────
    
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
    def is_valid(self) -> bool:
        """True if PDO has valid structure."""
        return (
            self.issuer == PDO_AUTHORITY
            and self.outcome_status in VALID_OUTCOMES
            and _is_valid_hash(self.proof_hash)
            and _is_valid_hash(self.decision_hash)
            and _is_valid_hash(self.outcome_hash)
            and _is_valid_hash(self.pdo_hash)
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # SERIALIZATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (deterministic serialization)."""
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
            "proof_at": self.proof_at,
            "decision_at": self.decision_at,
            "outcome_at": self.outcome_at,
            "created_at": self.created_at,
            "outcome_status": self.outcome_status,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string (deterministic)."""
        return json.dumps(self.to_dict(), sort_keys=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PDOArtifact":
        """Create from dictionary."""
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
            proof_at=data["proof_at"],
            decision_at=data["decision_at"],
            outcome_at=data["outcome_at"],
            created_at=data["created_at"],
            outcome_status=data["outcome_status"],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HASH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _is_valid_hash(h: str) -> bool:
    """Check if string is valid SHA-256 hash."""
    return bool(SHA256_PATTERN.match(h))


def compute_hash(data: Any) -> str:
    """Compute SHA-256 hash of data (deterministic)."""
    if isinstance(data, str):
        content = data
    elif isinstance(data, bytes):
        content = data.decode("utf-8")
    elif isinstance(data, dict):
        content = json.dumps(data, sort_keys=True)
    else:
        content = str(data)
    
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_proof_hash(wrap_data: Dict[str, Any]) -> str:
    """Compute proof hash from WRAP data."""
    return compute_hash(wrap_data)


def compute_decision_hash(proof_hash: str, ber_data: Dict[str, Any]) -> str:
    """Compute decision hash from proof hash and BER data."""
    combined = {
        "proof_hash": proof_hash,
        "ber_data": ber_data,
    }
    return compute_hash(combined)


def compute_outcome_hash(decision_hash: str, outcome_data: Dict[str, Any]) -> str:
    """Compute outcome hash from decision hash and outcome data."""
    combined = {
        "decision_hash": decision_hash,
        "outcome_data": outcome_data,
    }
    return compute_hash(combined)


def compute_pdo_hash(outcome_hash: str, metadata: Dict[str, Any]) -> str:
    """Compute final PDO hash (chain binding)."""
    combined = {
        "outcome_hash": outcome_hash,
        "metadata": metadata,
    }
    return compute_hash(combined)


# ═══════════════════════════════════════════════════════════════════════════════
# PDO ARTIFACT FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

class PDOArtifactFactory:
    """
    Factory for creating PDOArtifact instances.
    
    Enforces:
    - INV-PDO-002: Only GID-00 may create PDO
    - INV-PDO-004: Hash chain integrity
    - INV-PDO-006: All components required
    """
    
    @staticmethod
    def create(
        pac_id: str,
        wrap_id: str,
        wrap_data: Dict[str, Any],
        ber_id: str,
        ber_data: Dict[str, Any],
        outcome_status: str,
        issuer: str,
        proof_at: Optional[str] = None,
        decision_at: Optional[str] = None,
    ) -> PDOArtifact:
        """
        Create PDOArtifact with full validation.
        
        Args:
            pac_id: PAC identifier
            wrap_id: WRAP artifact ID
            wrap_data: WRAP data for proof hash
            ber_id: BER artifact ID
            ber_data: BER data for decision hash
            outcome_status: Final outcome (ACCEPTED/CORRECTIVE/REJECTED)
            issuer: Must be "GID-00"
            proof_at: When proof was received (optional, defaults to now)
            decision_at: When decision was made (optional, defaults to now)
        
        Returns:
            PDOArtifact: Immutable PDO artifact
        
        Raises:
            PDOAuthorityError: If issuer is not GID-00
            PDOIncompleteError: If required components missing
            PDOInvalidOutcomeError: If outcome status invalid
        """
        # INV-PDO-002: Authority check
        if issuer != PDO_AUTHORITY:
            raise PDOAuthorityError(issuer)
        
        # INV-PDO-006: Completeness check
        missing = []
        if not pac_id:
            missing.append("pac_id")
        if not wrap_id:
            missing.append("wrap_id")
        if not wrap_data:
            missing.append("wrap_data")
        if not ber_id:
            missing.append("ber_id")
        if not ber_data:
            missing.append("ber_data")
        if not outcome_status:
            missing.append("outcome_status")
        
        if missing:
            raise PDOIncompleteError(missing)
        
        # Validate outcome status
        if outcome_status not in VALID_OUTCOMES:
            raise PDOInvalidOutcomeError(outcome_status)
        
        # Generate timestamps
        now = datetime.now(timezone.utc).isoformat()
        proof_at = proof_at or now
        decision_at = decision_at or now
        outcome_at = now
        created_at = now
        
        # INV-PDO-004: Compute hash chain
        proof_hash = compute_proof_hash(wrap_data)
        decision_hash = compute_decision_hash(proof_hash, ber_data)
        
        outcome_data = {
            "outcome_status": outcome_status,
            "outcome_at": outcome_at,
        }
        outcome_hash = compute_outcome_hash(decision_hash, outcome_data)
        
        # Generate PDO ID
        pdo_id = f"pdo_{uuid.uuid4().hex[:12]}"
        
        # Compute final PDO hash (chain binding)
        metadata = {
            "pdo_id": pdo_id,
            "pac_id": pac_id,
            "wrap_id": wrap_id,
            "ber_id": ber_id,
            "issuer": issuer,
            "created_at": created_at,
        }
        pdo_hash = compute_pdo_hash(outcome_hash, metadata)
        
        return PDOArtifact(
            pdo_id=pdo_id,
            pac_id=pac_id,
            wrap_id=wrap_id,
            ber_id=ber_id,
            issuer=issuer,
            proof_hash=proof_hash,
            decision_hash=decision_hash,
            outcome_hash=outcome_hash,
            pdo_hash=pdo_hash,
            proof_at=proof_at,
            decision_at=decision_at,
            outcome_at=outcome_at,
            created_at=created_at,
            outcome_status=outcome_status,
        )
    
    @staticmethod
    def create_from_artifacts(
        pac_id: str,
        wrap_artifact: Any,
        ber_artifact: Any,
        issuer: str,
    ) -> PDOArtifact:
        """
        Create PDOArtifact from WRAP and BER artifacts.
        
        Convenience method that extracts data from artifact objects.
        """
        # Extract WRAP data
        if hasattr(wrap_artifact, "to_dict"):
            wrap_data = wrap_artifact.to_dict()
        elif hasattr(wrap_artifact, "__dict__"):
            wrap_data = {
                k: v for k, v in wrap_artifact.__dict__.items()
                if not k.startswith("_")
            }
        else:
            wrap_data = {"wrap": str(wrap_artifact)}
        
        wrap_id = getattr(wrap_artifact, "wrap_id", None) or f"wrap_{uuid.uuid4().hex[:12]}"
        
        # Extract BER data
        if hasattr(ber_artifact, "to_dict"):
            ber_data = ber_artifact.to_dict()
        elif hasattr(ber_artifact, "__dict__"):
            ber_data = {
                k: v for k, v in ber_artifact.__dict__.items()
                if not k.startswith("_")
            }
        else:
            ber_data = {"ber": str(ber_artifact)}
        
        ber_id = getattr(ber_artifact, "ber_id", None) or f"ber_{uuid.uuid4().hex[:12]}"
        
        # Determine outcome from BER
        ber_decision = getattr(ber_artifact, "decision", None)
        if ber_decision == "APPROVE":
            outcome_status = "ACCEPTED"
        elif ber_decision == "CORRECTIVE":
            outcome_status = "CORRECTIVE"
        elif ber_decision == "REJECT":
            outcome_status = "REJECTED"
        else:
            outcome_status = "ACCEPTED"  # Default for approved
        
        # Get timestamps from artifacts
        proof_at = getattr(wrap_artifact, "received_at", None)
        decision_at = getattr(ber_artifact, "issued_at", None)
        
        return PDOArtifactFactory.create(
            pac_id=pac_id,
            wrap_id=wrap_id,
            wrap_data=wrap_data,
            ber_id=ber_id,
            ber_data=ber_data,
            outcome_status=outcome_status,
            issuer=issuer,
            proof_at=proof_at,
            decision_at=decision_at,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def verify_pdo_chain(pdo: PDOArtifact) -> bool:
    """
    Verify PDO hash chain integrity.
    
    Returns True if chain is valid, False otherwise.
    
    Note: This verifies structural validity only.
    Full verification requires original WRAP and BER data.
    """
    # Basic structure checks
    if pdo.issuer != PDO_AUTHORITY:
        return False
    
    if pdo.outcome_status not in VALID_OUTCOMES:
        return False
    
    # Hash format checks
    for h in [pdo.proof_hash, pdo.decision_hash, pdo.outcome_hash, pdo.pdo_hash]:
        if not _is_valid_hash(h):
            return False
    
    return True


def verify_pdo_full(
    pdo: PDOArtifact,
    wrap_data: Dict[str, Any],
    ber_data: Dict[str, Any],
) -> bool:
    """
    Full PDO verification with original data.
    
    Recomputes hash chain and compares to stored hashes.
    """
    # Recompute proof hash
    expected_proof = compute_proof_hash(wrap_data)
    if pdo.proof_hash != expected_proof:
        return False
    
    # Recompute decision hash
    expected_decision = compute_decision_hash(pdo.proof_hash, ber_data)
    if pdo.decision_hash != expected_decision:
        return False
    
    # Recompute outcome hash
    outcome_data = {
        "outcome_status": pdo.outcome_status,
        "outcome_at": pdo.outcome_at,
    }
    expected_outcome = compute_outcome_hash(pdo.decision_hash, outcome_data)
    if pdo.outcome_hash != expected_outcome:
        return False
    
    # Recompute PDO hash
    metadata = {
        "pdo_id": pdo.pdo_id,
        "pac_id": pdo.pac_id,
        "wrap_id": pdo.wrap_id,
        "ber_id": pdo.ber_id,
        "issuer": pdo.issuer,
        "created_at": pdo.created_at,
    }
    expected_pdo = compute_pdo_hash(pdo.outcome_hash, metadata)
    if pdo.pdo_hash != expected_pdo:
        return False
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Artifact
    "PDOArtifact",
    "PDOArtifactFactory",
    
    # Constants
    "PDO_AUTHORITY",
    "VALID_OUTCOMES",
    
    # Exceptions
    "PDOCreationError",
    "PDOAuthorityError",
    "PDOIncompleteError",
    "PDODuplicateError",
    "PDOHashMismatchError",
    "PDOInvalidOutcomeError",
    
    # Hash utilities
    "compute_hash",
    "compute_proof_hash",
    "compute_decision_hash",
    "compute_outcome_hash",
    "compute_pdo_hash",
    
    # Verification
    "verify_pdo_chain",
    "verify_pdo_full",
]
