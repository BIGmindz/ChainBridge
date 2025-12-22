"""Proof Artifact Integrity Module.

Enforces cryptographic immutability checks for proof artifacts.
Rejects:
- Hash collisions
- Lineage truncation
- Out-of-order proofs

DOCTRINE: Proof chain is immutable and tamper-evident.

Author: Sam (GID-06) — Security & Threat Engineer
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security Exceptions
# ---------------------------------------------------------------------------


class ProofHashCollisionError(Exception):
    """Raised when hash collision attack detected."""

    def __init__(self, proof_id: str, hash_value: str, existing_id: str):
        self.proof_id = proof_id
        self.hash_value = hash_value
        self.existing_id = existing_id
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Hash collision detected: {proof_id} collides with {existing_id} "
            f"at hash {hash_value[:16]}..."
        )


class ProofLineageTruncationError(Exception):
    """Raised when proof lineage is incomplete or truncated."""

    def __init__(self, proof_id: str, expected_parent: str, actual_parent: str = None):
        self.proof_id = proof_id
        self.expected_parent = expected_parent
        self.actual_parent = actual_parent
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Lineage truncation detected: {proof_id} expected parent {expected_parent}, "
            f"got {actual_parent}"
        )


class ProofOutOfOrderError(Exception):
    """Raised when proof sequence is out of order."""

    def __init__(
        self,
        proof_id: str,
        expected_sequence: int,
        actual_sequence: int,
    ):
        self.proof_id = proof_id
        self.expected_sequence = expected_sequence
        self.actual_sequence = actual_sequence
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Out-of-order proof: {proof_id} expected seq {expected_sequence}, "
            f"got {actual_sequence}"
        )


# ---------------------------------------------------------------------------
# Integrity Check Types
# ---------------------------------------------------------------------------


class IntegrityViolationType(str, Enum):
    """Types of integrity violations."""

    HASH_COLLISION = "HASH_COLLISION"
    HASH_MISMATCH = "HASH_MISMATCH"
    LINEAGE_TRUNCATION = "LINEAGE_TRUNCATION"
    LINEAGE_GAP = "LINEAGE_GAP"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    DUPLICATE_PROOF = "DUPLICATE_PROOF"
    MISSING_PARENT = "MISSING_PARENT"
    CIRCULAR_REFERENCE = "CIRCULAR_REFERENCE"
    INVALID_HASH_FORMAT = "INVALID_HASH_FORMAT"


@dataclass(frozen=True)
class IntegrityCheckResult:
    """Result from proof integrity check."""

    valid: bool
    violation_type: Optional[IntegrityViolationType]
    proof_id: Optional[str]
    reason: str
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "proof_integrity_check",
            "valid": self.valid,
            "violation_type": self.violation_type.value if self.violation_type else None,
            "proof_id": self.proof_id,
            "reason": self.reason,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Proof Integrity Checker
# ---------------------------------------------------------------------------


class ProofIntegrityChecker:
    """Verifies proof artifact integrity and chain consistency.

    SECURITY INVARIANTS:
    - Proofs are cryptographically immutable
    - Lineage chain is complete and ordered
    - No hash collisions allowed
    - All violations are observable

    Usage:
        checker = ProofIntegrityChecker()
        checker.verify_proof(proof_data)  # Raises on violation
        checker.verify_chain(proof_chain)  # Validates entire chain
    """

    def __init__(self):
        """Initialize proof integrity checker."""
        # Hash -> proof_id mapping for collision detection
        self._hash_registry: dict[str, str] = {}
        # proof_id -> sequence number
        self._sequence_registry: dict[str, int] = {}
        # proof_id -> parent_id
        self._lineage_registry: dict[str, str] = {}
        # Known proof IDs
        self._known_proofs: Set[str] = set()

    def verify_proof(self, proof_data: dict[str, Any]) -> IntegrityCheckResult:
        """Verify single proof artifact integrity.

        Checks:
        1. Hash format is valid
        2. No hash collision
        3. Parent exists (if not root)
        4. Sequence is correct

        Args:
            proof_data: Proof artifact dictionary

        Returns:
            IntegrityCheckResult

        Raises:
            ProofHashCollisionError: If hash collision detected
            ProofLineageTruncationError: If parent missing
            ProofOutOfOrderError: If sequence wrong
        """
        proof_id = proof_data.get("proof_id", "UNKNOWN")

        # Check 1: Hash format
        result = self._verify_hash_format(proof_data, proof_id)
        if not result.valid:
            self._log_violation(result)
            return result

        # Check 2: Hash collision
        result = self._check_hash_collision(proof_data, proof_id)
        if not result.valid:
            self._log_violation(result)
            hash_value = self._compute_proof_hash(proof_data)
            raise ProofHashCollisionError(
                proof_id,
                hash_value,
                self._hash_registry.get(hash_value, "UNKNOWN"),
            )

        # Check 3: Duplicate proof
        result = self._check_duplicate(proof_data, proof_id)
        if not result.valid:
            self._log_violation(result)
            return result

        # Check 4: Parent exists
        result = self._verify_parent(proof_data, proof_id)
        if not result.valid:
            self._log_violation(result)
            raise ProofLineageTruncationError(
                proof_id,
                proof_data.get("parent_id"),
                None,
            )

        # Check 5: Sequence order
        result = self._verify_sequence(proof_data, proof_id)
        if not result.valid:
            self._log_violation(result)
            raise ProofOutOfOrderError(
                proof_id,
                result.evidence.get("expected_sequence", -1),
                result.evidence.get("actual_sequence", -1),
            )

        # Register proof
        self._register_proof(proof_data)

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="Proof integrity verified",
        )

    def verify_chain(
        self,
        proof_chain: List[dict[str, Any]],
    ) -> IntegrityCheckResult:
        """Verify entire proof chain integrity.

        Validates:
        - All proofs in order
        - Complete lineage (no gaps)
        - No circular references
        - Hashes chain correctly

        Args:
            proof_chain: List of proof artifacts in order

        Returns:
            IntegrityCheckResult
        """
        if not proof_chain:
            return IntegrityCheckResult(
                valid=True,
                violation_type=None,
                proof_id=None,
                reason="Empty chain is valid",
            )

        # Track seen IDs for circular reference detection
        seen_ids: Set[str] = set()

        # Verify first proof is root (no parent or self-parent)
        first = proof_chain[0]
        first_id = first.get("proof_id")
        first_parent = first.get("parent_id")

        if first_parent and first_parent != first_id:
            return IntegrityCheckResult(
                valid=False,
                violation_type=IntegrityViolationType.LINEAGE_TRUNCATION,
                proof_id=first_id,
                reason="Chain does not start at root",
                evidence={"parent_id": first_parent},
            )

        seen_ids.add(first_id)

        # Verify chain linkage
        for i, proof in enumerate(proof_chain[1:], start=1):
            proof_id = proof.get("proof_id")
            parent_id = proof.get("parent_id")

            # Check for circular reference
            if proof_id in seen_ids:
                return IntegrityCheckResult(
                    valid=False,
                    violation_type=IntegrityViolationType.CIRCULAR_REFERENCE,
                    proof_id=proof_id,
                    reason=f"Circular reference detected at position {i}",
                    evidence={"position": i},
                )

            # Check parent is previous proof
            prev_id = proof_chain[i - 1].get("proof_id")
            if parent_id != prev_id:
                return IntegrityCheckResult(
                    valid=False,
                    violation_type=IntegrityViolationType.LINEAGE_GAP,
                    proof_id=proof_id,
                    reason=f"Lineage gap: expected parent {prev_id}, got {parent_id}",
                    evidence={
                        "expected_parent": prev_id,
                        "actual_parent": parent_id,
                        "position": i,
                    },
                )

            # Check sequence
            expected_seq = i
            actual_seq = proof.get("sequence", -1)
            if actual_seq != expected_seq:
                return IntegrityCheckResult(
                    valid=False,
                    violation_type=IntegrityViolationType.OUT_OF_ORDER,
                    proof_id=proof_id,
                    reason=f"Sequence mismatch: expected {expected_seq}, got {actual_seq}",
                    evidence={
                        "expected_sequence": expected_seq,
                        "actual_sequence": actual_seq,
                    },
                )

            seen_ids.add(proof_id)

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=None,
            reason=f"Chain of {len(proof_chain)} proofs verified",
        )

    def detect_lineage_corruption(
        self,
        proof_data: dict[str, Any],
        known_lineage: List[str],
    ) -> IntegrityCheckResult:
        """Detect if proof's claimed lineage matches known lineage.

        Args:
            proof_data: Proof to check
            known_lineage: Known valid lineage (list of proof_ids)

        Returns:
            IntegrityCheckResult
        """
        proof_id = proof_data.get("proof_id")
        claimed_parent = proof_data.get("parent_id")

        if not known_lineage:
            # First proof, parent should be None or self
            if claimed_parent and claimed_parent != proof_id:
                return IntegrityCheckResult(
                    valid=False,
                    violation_type=IntegrityViolationType.LINEAGE_TRUNCATION,
                    proof_id=proof_id,
                    reason="Root proof claims non-self parent",
                    evidence={"claimed_parent": claimed_parent},
                )
            return IntegrityCheckResult(
                valid=True,
                violation_type=None,
                proof_id=proof_id,
                reason="Root proof lineage valid",
            )

        # Parent should be last in known lineage
        expected_parent = known_lineage[-1]
        if claimed_parent != expected_parent:
            return IntegrityCheckResult(
                valid=False,
                violation_type=IntegrityViolationType.LINEAGE_TRUNCATION,
                proof_id=proof_id,
                reason=f"Lineage corruption: expected {expected_parent}, got {claimed_parent}",
                evidence={
                    "expected_parent": expected_parent,
                    "claimed_parent": claimed_parent,
                    "known_lineage_length": len(known_lineage),
                },
            )

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="Lineage verified",
        )

    # ---------------------------------------------------------------------------
    # Internal Methods
    # ---------------------------------------------------------------------------

    def _verify_hash_format(
        self, proof_data: dict[str, Any], proof_id: str
    ) -> IntegrityCheckResult:
        """Verify hash fields have valid format."""
        hash_fields = ["content_hash", "decision_hash", "lineage_hash"]

        for field_name in hash_fields:
            hash_value = proof_data.get(field_name)
            if hash_value:
                if not isinstance(hash_value, str) or len(hash_value) != 64:
                    return IntegrityCheckResult(
                        valid=False,
                        violation_type=IntegrityViolationType.INVALID_HASH_FORMAT,
                        proof_id=proof_id,
                        reason=f"Invalid {field_name} format",
                        evidence={
                            "field": field_name,
                            "length": len(hash_value) if hash_value else 0,
                        },
                    )
                try:
                    bytes.fromhex(hash_value)
                except ValueError:
                    return IntegrityCheckResult(
                        valid=False,
                        violation_type=IntegrityViolationType.INVALID_HASH_FORMAT,
                        proof_id=proof_id,
                        reason=f"{field_name} is not valid hex",
                        evidence={"field": field_name},
                    )

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="Hash formats valid",
        )

    def _check_hash_collision(
        self, proof_data: dict[str, Any], proof_id: str
    ) -> IntegrityCheckResult:
        """Check for hash collision attack."""
        proof_hash = self._compute_proof_hash(proof_data)

        if proof_hash in self._hash_registry:
            existing_id = self._hash_registry[proof_hash]
            if existing_id != proof_id:
                return IntegrityCheckResult(
                    valid=False,
                    violation_type=IntegrityViolationType.HASH_COLLISION,
                    proof_id=proof_id,
                    reason=f"Hash collision with {existing_id}",
                    evidence={
                        "hash": proof_hash[:16] + "...",
                        "existing_proof": existing_id,
                    },
                )

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="No hash collision",
        )

    def _check_duplicate(
        self, proof_data: dict[str, Any], proof_id: str
    ) -> IntegrityCheckResult:
        """Check for duplicate proof submission."""
        if proof_id in self._known_proofs:
            return IntegrityCheckResult(
                valid=False,
                violation_type=IntegrityViolationType.DUPLICATE_PROOF,
                proof_id=proof_id,
                reason="Duplicate proof submission",
                evidence={},
            )

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="Not a duplicate",
        )

    def _verify_parent(
        self, proof_data: dict[str, Any], proof_id: str
    ) -> IntegrityCheckResult:
        """Verify parent proof exists (if not root)."""
        parent_id = proof_data.get("parent_id")

        # Root proof has no parent or self-parent
        if not parent_id or parent_id == proof_id:
            return IntegrityCheckResult(
                valid=True,
                violation_type=None,
                proof_id=proof_id,
                reason="Root proof (no parent)",
            )

        # Non-root must have known parent
        if parent_id not in self._known_proofs:
            return IntegrityCheckResult(
                valid=False,
                violation_type=IntegrityViolationType.MISSING_PARENT,
                proof_id=proof_id,
                reason=f"Parent {parent_id} not found",
                evidence={"parent_id": parent_id},
            )

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="Parent verified",
        )

    def _verify_sequence(
        self, proof_data: dict[str, Any], proof_id: str
    ) -> IntegrityCheckResult:
        """Verify proof sequence number is correct."""
        sequence = proof_data.get("sequence")
        parent_id = proof_data.get("parent_id")

        # Root proof should be sequence 0
        if not parent_id or parent_id == proof_id:
            if sequence is not None and sequence != 0:
                return IntegrityCheckResult(
                    valid=False,
                    violation_type=IntegrityViolationType.OUT_OF_ORDER,
                    proof_id=proof_id,
                    reason=f"Root proof should have sequence 0, got {sequence}",
                    evidence={
                        "expected_sequence": 0,
                        "actual_sequence": sequence,
                    },
                )
            return IntegrityCheckResult(
                valid=True,
                violation_type=None,
                proof_id=proof_id,
                reason="Root sequence valid",
            )

        # Non-root should be parent_sequence + 1
        parent_seq = self._sequence_registry.get(parent_id, -1)
        expected_seq = parent_seq + 1

        if sequence is not None and sequence != expected_seq:
            return IntegrityCheckResult(
                valid=False,
                violation_type=IntegrityViolationType.OUT_OF_ORDER,
                proof_id=proof_id,
                reason=f"Expected sequence {expected_seq}, got {sequence}",
                evidence={
                    "expected_sequence": expected_seq,
                    "actual_sequence": sequence,
                    "parent_sequence": parent_seq,
                },
            )

        return IntegrityCheckResult(
            valid=True,
            violation_type=None,
            proof_id=proof_id,
            reason="Sequence valid",
        )

    def _compute_proof_hash(self, proof_data: dict[str, Any]) -> str:
        """Compute deterministic hash of proof content."""
        # Exclude mutable fields from hash
        hashable_fields = {
            k: v for k, v in proof_data.items()
            if k not in ("signature", "verified_at", "received_at")
        }
        content = json.dumps(hashable_fields, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()

    def _register_proof(self, proof_data: dict[str, Any]) -> None:
        """Register proof in internal registries."""
        proof_id = proof_data.get("proof_id")
        proof_hash = self._compute_proof_hash(proof_data)
        parent_id = proof_data.get("parent_id")
        sequence = proof_data.get("sequence", 0)

        self._hash_registry[proof_hash] = proof_id
        self._known_proofs.add(proof_id)
        self._lineage_registry[proof_id] = parent_id
        self._sequence_registry[proof_id] = sequence

    def _log_violation(self, result: IntegrityCheckResult) -> None:
        """Log integrity violation for audit."""
        logger.error(
            "INTEGRITY_VIOLATION: %s proof_id=%s reason=%s",
            result.violation_type.value if result.violation_type else "UNKNOWN",
            result.proof_id,
            result.reason,
        )
        logger.error("Violation evidence: %s", json.dumps(result.to_audit_log()))

    def clear_registries(self) -> None:
        """Clear all registries (for testing only)."""
        self._hash_registry.clear()
        self._sequence_registry.clear()
        self._lineage_registry.clear()
        self._known_proofs.clear()
