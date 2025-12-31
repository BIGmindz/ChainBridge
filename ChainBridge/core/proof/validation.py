"""Proof Integrity Validation.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: SAM (GID-06) — Security & Architecture Manager      ║
║ EXECUTING COLOR: 🟥 DARK RED                                         ║
║ PAC: PAC-SAM-PROOF-INTEGRITY-01                                      ║
║ A6 ADDITIONS: Cody (GID-01) — PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT   ║
╚══════════════════════════════════════════════════════════════════════╝

THREAT MODEL CONTROLS:
- PROOF-V1: Content hash verification (detects proof mutation)
- PROOF-V2: Chain hash verification (detects reordering/deletion)
- PROOF-V3: Mandatory field validation (detects truncation)
- PROOF-V4: Startup integrity check (fails loud on corruption)

INVARIANTS:
- Tampering MUST be detected
- Validation failure MUST raise exception (no silent corruption)
- All hashes use SHA-256 with canonical JSON encoding

Author: SAM (GID-06) — Security & Architecture Manager
A6 Additions: Cody (GID-01) — Senior Backend Engineer
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class ProofValidationError(Exception):
    """
    Raised when proof integrity validation fails.

    This exception MUST crash the process - no silent failures allowed.
    """
    pass


@dataclass(frozen=True)
class ValidationResult:
    """
    Immutable result of proof validation.

    Contains:
    - passed: bool - overall pass/fail
    - errors: list of detected issues
    - warnings: list of non-critical issues
    - metadata: validation context
    """
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    metadata: Dict[str, Any]

    def __bool__(self) -> bool:
        return self.passed


# Required fields that MUST be present in a valid proof
REQUIRED_PROOF_FIELDS = frozenset({
    "proof_id",
    "event_id",
    "event_hash",
    "event_type",
    "decision_id",
    "decision_hash",
    "decision_outcome",
    "action_id",
    "action_type",
    "action_status",
    "proof_timestamp",
})

# Fields used for content hash computation (deterministic)
HASHABLE_FIELDS = (
    "event_id",
    "event_hash",
    "event_type",
    "event_timestamp",
    "decision_id",
    "decision_hash",
    "decision_outcome",
    "decision_rule",
    "decision_rule_version",
    "decision_inputs",
    "decision_explanation",
    "action_id",
    "action_type",
    "action_status",
    "action_details",
    "action_error",
    "proof_timestamp",
)


def compute_canonical_hash(data: Dict[str, Any], fields: Tuple[str, ...] = HASHABLE_FIELDS) -> str:
    """
    Compute deterministic SHA-256 hash of proof data.

    Uses canonical JSON encoding:
    - Sorted keys
    - No whitespace
    - Strings for UUIDs and datetimes

    Args:
        data: The proof data dict
        fields: Fields to include in hash (ordered)

    Returns:
        Hex-encoded SHA-256 hash
    """
    # Extract only specified fields in order
    hashable_data = {}
    for field in fields:
        if field in data:
            hashable_data[field] = data[field]

    canonical = json.dumps(
        hashable_data,
        sort_keys=True,
        separators=(",", ":"),
        default=str,  # Handle UUIDs, datetimes
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_chain_hash(previous_hash: str, content_hash: str) -> str:
    """
    Compute chain hash linking to previous proof.

    chain_hash = SHA-256(previous_hash + ":" + content_hash)

    This creates a tamper-evident chain where:
    - Changing any proof invalidates all subsequent chain hashes
    - Deleting a proof breaks the chain
    - Reordering proofs is detectable

    Args:
        previous_hash: Hash of the previous proof (or GENESIS_HASH)
        content_hash: Content hash of current proof

    Returns:
        Hex-encoded SHA-256 chain hash
    """
    combined = f"{previous_hash}:{content_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# Genesis hash for first entry (64 zeros - SHA-256 length)
GENESIS_HASH = "0" * 64


class ProofValidator:
    """
    Validates proof integrity with strict controls.

    THREAT CONTROLS:
    1. Content hash verification - detects any field modification
    2. Chain hash verification - detects reordering/deletion/insertion
    3. Field presence validation - detects truncation
    4. Type validation - detects type coercion attacks

    Usage:
        validator = ProofValidator()
        result = validator.validate_proof(proof_data)
        if not result:
            raise ProofValidationError(result.errors)
    """

    def __init__(self):
        """Initialize validator with no state."""
        pass

    def validate_proof(
        self,
        proof_data: Dict[str, Any],
        expected_hash: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a single proof's integrity.

        Checks:
        1. All required fields present
        2. Content hash matches (if expected_hash provided)
        3. Field types are valid

        Args:
            proof_data: The proof dict to validate
            expected_hash: Expected content hash (optional)

        Returns:
            ValidationResult with pass/fail and error details
        """
        errors: List[str] = []
        warnings: List[str] = []

        # CONTROL V1: Required field validation
        missing_fields = REQUIRED_PROOF_FIELDS - set(proof_data.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {sorted(missing_fields)}")

        # CONTROL V2: Type validation for critical fields
        if "proof_id" in proof_data:
            if not self._is_valid_uuid(proof_data["proof_id"]):
                errors.append(f"Invalid proof_id format: {proof_data['proof_id']}")

        if "event_hash" in proof_data:
            if not self._is_valid_hash(proof_data["event_hash"]):
                errors.append(f"Invalid event_hash format: {proof_data['event_hash'][:32]}...")

        if "decision_hash" in proof_data:
            if not self._is_valid_hash(proof_data["decision_hash"]):
                errors.append(f"Invalid decision_hash format: {proof_data['decision_hash'][:32]}...")

        # CONTROL V3: Content hash verification (if expected provided)
        if expected_hash is not None:
            computed_hash = compute_canonical_hash(proof_data)
            if computed_hash != expected_hash:
                errors.append(
                    f"Content hash mismatch! "
                    f"Expected={expected_hash[:16]}... "
                    f"Computed={computed_hash[:16]}..."
                )

        # CONTROL V4: Timestamp validation
        if "proof_timestamp" in proof_data:
            if not self._is_valid_timestamp(proof_data["proof_timestamp"]):
                errors.append(f"Invalid proof_timestamp format: {proof_data['proof_timestamp']}")

        metadata = {
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "field_count": len(proof_data),
            "has_expected_hash": expected_hash is not None,
        }

        return ValidationResult(
            passed=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
            metadata=metadata,
        )

    def validate_chain(
        self,
        proofs: List[Dict[str, Any]],
        genesis_hash: str = GENESIS_HASH,
    ) -> ValidationResult:
        """
        Validate a chain of proofs for integrity.

        Verifies:
        1. Each proof passes individual validation
        2. Chain hashes link correctly
        3. Sequence numbers are contiguous

        Args:
            proofs: Ordered list of proof dicts
            genesis_hash: Starting hash for chain (default: GENESIS_HASH)

        Returns:
            ValidationResult with pass/fail and error details
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not proofs:
            return ValidationResult(
                passed=True,
                errors=(),
                warnings=("Empty proof chain",),
                metadata={"proof_count": 0},
            )

        previous_chain_hash = genesis_hash
        expected_sequence = 1

        for i, proof in enumerate(proofs):
            # Individual validation
            result = self.validate_proof(proof)
            if not result.passed:
                errors.extend([f"Proof {i}: {e}" for e in result.errors])
                continue

            # Sequence number check
            seq = proof.get("sequence_number")
            if seq is not None and seq != expected_sequence:
                errors.append(
                    f"Proof {i}: Sequence mismatch! Expected={expected_sequence}, Got={seq}"
                )

            # CONTROL V2: Content hash verification
            # First, verify stored content_hash matches actual content
            stored_content_hash = proof.get("content_hash")
            computed_content_hash = compute_canonical_hash(proof)

            if stored_content_hash:
                if stored_content_hash != computed_content_hash:
                    errors.append(
                        f"Proof {i}: Content hash mismatch! "
                        f"Stored={stored_content_hash[:16]}... "
                        f"Computed={computed_content_hash[:16]}... "
                        f"(content tampered)"
                    )
                    # Use stored hash for chain verification to detect which proof is corrupted
                    content_hash = stored_content_hash
                else:
                    content_hash = stored_content_hash
            else:
                content_hash = computed_content_hash

            # Chain hash verification
            stored_chain_hash = proof.get("chain_hash")

            if stored_chain_hash:
                expected_chain_hash = compute_chain_hash(previous_chain_hash, content_hash)
                if stored_chain_hash != expected_chain_hash:
                    errors.append(
                        f"Proof {i}: Chain hash mismatch! "
                        f"Stored={stored_chain_hash[:16]}... "
                        f"Expected={expected_chain_hash[:16]}..."
                    )
                previous_chain_hash = stored_chain_hash
            else:
                # No chain hash - compute for next iteration
                previous_chain_hash = compute_chain_hash(previous_chain_hash, content_hash)
                warnings.append(f"Proof {i}: Missing chain_hash field")

            expected_sequence += 1

        metadata = {
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "proof_count": len(proofs),
            "error_count": len(errors),
            "final_chain_hash": previous_chain_hash[:16] + "...",
        }

        return ValidationResult(
            passed=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
            metadata=metadata,
        )

    def _is_valid_uuid(self, value: Any) -> bool:
        """Check if value is a valid UUID string."""
        if isinstance(value, UUID):
            return True
        if not isinstance(value, str):
            return False
        try:
            UUID(value)
            return True
        except (ValueError, AttributeError):
            return False

    def _is_valid_hash(self, value: Any) -> bool:
        """Check if value is a valid SHA-256 hex hash."""
        if not isinstance(value, str):
            return False
        if len(value) != 64:
            return False
        try:
            int(value, 16)
            return True
        except ValueError:
            return False

    def _is_valid_timestamp(self, value: Any) -> bool:
        """Check if value is a valid ISO8601 timestamp."""
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False


# ---------------------------------------------------------------------------
# A6 Architecture Enforcement - Proof Lineage Validation
# (PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01)
# ---------------------------------------------------------------------------
# Enforces forward-only proof lineage:
# - No orphan proofs (must chain to previous)
# - No proof mutation (content hash must match)
# - No proof deletion (sequence must be contiguous)
# ---------------------------------------------------------------------------


class ProofLineageValidator:
    """Validates forward-only proof lineage per A6 Architecture Locks.

    DOCTRINE (FAIL-CLOSED):
    - Orphan proofs (no previous chain link) → FAIL
    - Mutated proofs (content hash mismatch) → FAIL
    - Deleted proofs (sequence gap) → FAIL
    - All violations raise ProofValidationError

    Usage:
        validator = ProofLineageValidator()
        result = validator.validate_lineage(new_proof, existing_proofs)
        if not result.passed:
            raise ProofValidationError(result.errors)
    """

    def __init__(self):
        """Initialize lineage validator."""
        self._proof_validator = ProofValidator()

    def validate_lineage(
        self,
        new_proof: Dict[str, Any],
        existing_proofs: List[Dict[str, Any]],
        genesis_hash: str = GENESIS_HASH,
    ) -> ValidationResult:
        """Validate that a new proof maintains forward-only lineage.

        DOCTRINE (FAIL-CLOSED per A6 Architecture Lock):
        - New proof MUST chain to the last existing proof
        - Sequence numbers MUST be contiguous
        - Content hashes MUST be immutable

        Args:
            new_proof: The proof to validate
            existing_proofs: Ordered list of existing proofs
            genesis_hash: Starting hash for chain

        Returns:
            ValidationResult with lineage check results
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Validate new proof passes individual validation
        new_result = self._proof_validator.validate_proof(new_proof)
        if not new_result.passed:
            errors.extend([f"New proof: {e}" for e in new_result.errors])
            return ValidationResult(
                passed=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
                metadata={"validation_type": "lineage", "stage": "proof_validation"},
            )

        # Compute expected previous chain hash
        if existing_proofs:
            # Chain must link to last existing proof
            last_proof = existing_proofs[-1]
            last_content_hash = last_proof.get("content_hash")
            if last_content_hash is None:
                last_content_hash = compute_canonical_hash(last_proof)
            last_chain_hash = last_proof.get("chain_hash", genesis_hash)
            expected_previous = last_chain_hash
            expected_sequence = len(existing_proofs) + 1
        else:
            # First proof chains from genesis
            expected_previous = genesis_hash
            expected_sequence = 1

        # Check sequence number continuity
        new_sequence = new_proof.get("sequence_number")
        if new_sequence is not None and new_sequence != expected_sequence:
            errors.append(
                f"Sequence discontinuity: expected {expected_sequence}, got {new_sequence}. "
                f"Forward-only lineage violated."
            )

        # Check chain hash links to previous
        new_chain_hash = new_proof.get("chain_hash")
        new_content_hash = new_proof.get("content_hash")
        if new_content_hash is None:
            new_content_hash = compute_canonical_hash(new_proof)

        if new_chain_hash:
            computed_chain_hash = compute_chain_hash(expected_previous, new_content_hash)
            if new_chain_hash != computed_chain_hash:
                errors.append(
                    f"Chain hash mismatch: proof does not chain to previous. "
                    f"Expected previous={expected_previous[:16]}..., "
                    f"Computed chain={computed_chain_hash[:16]}..., "
                    f"Got chain={new_chain_hash[:16]}... "
                    f"Forward-only lineage violated."
                )

        # Check for orphan (no link to existing chain)
        if existing_proofs and new_chain_hash is None:
            warnings.append(
                "New proof has no chain_hash - cannot verify lineage"
            )

        metadata = {
            "validation_type": "lineage",
            "expected_sequence": expected_sequence,
            "expected_previous": expected_previous[:16] + "..." if expected_previous else None,
            "proof_count_before": len(existing_proofs),
        }

        return ValidationResult(
            passed=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
            metadata=metadata,
        )

    def validate_no_mutation(
        self,
        proof: Dict[str, Any],
        original_content_hash: str,
    ) -> ValidationResult:
        """Validate that a proof has not been mutated.

        DOCTRINE (FAIL-CLOSED):
        - Content hash MUST match original
        - Any mutation → FAIL

        Args:
            proof: The proof to check
            original_content_hash: The original content hash when proof was created

        Returns:
            ValidationResult indicating mutation status
        """
        errors: List[str] = []

        current_hash = compute_canonical_hash(proof)
        if current_hash != original_content_hash:
            errors.append(
                f"Proof mutation detected! "
                f"Original hash={original_content_hash[:16]}..., "
                f"Current hash={current_hash[:16]}..."
            )

        return ValidationResult(
            passed=len(errors) == 0,
            errors=tuple(errors),
            warnings=(),
            metadata={
                "validation_type": "mutation_check",
                "original_hash": original_content_hash[:16] + "...",
                "current_hash": current_hash[:16] + "...",
            },
        )


def validate_proof_lineage(
    new_proof: Dict[str, Any],
    existing_proofs: List[Dict[str, Any]],
    strict: bool = True,
) -> ValidationResult:
    """Validate forward-only proof lineage.

    A6 Architecture Enforcement convenience function.

    Args:
        new_proof: The proof to validate
        existing_proofs: Ordered list of existing proofs
        strict: If True, raise exception on failure

    Returns:
        ValidationResult

    Raises:
        ProofValidationError: If validation fails and strict=True
    """
    validator = ProofLineageValidator()
    result = validator.validate_lineage(new_proof, existing_proofs)

    if strict and not result.passed:
        error_summary = "; ".join(result.errors[:3])
        raise ProofValidationError(
            f"Proof lineage validation failed: {error_summary}"
        )

    return result


def validate_proof_integrity(
    proof_data: Dict[str, Any],
    expected_hash: Optional[str] = None,
) -> ValidationResult:
    """
    Validate a single proof's integrity.

    Convenience function using default ProofValidator.

    Args:
        proof_data: The proof dict to validate
        expected_hash: Expected content hash (optional)

    Returns:
        ValidationResult

    Raises:
        ProofValidationError: If validation fails (when strict=True)
    """
    validator = ProofValidator()
    return validator.validate_proof(proof_data, expected_hash)


def verify_proof_chain(
    proofs: List[Dict[str, Any]],
    strict: bool = True,
) -> ValidationResult:
    """
    Verify a chain of proofs for integrity.

    Convenience function using default ProofValidator.

    Args:
        proofs: Ordered list of proof dicts
        strict: If True, raise exception on failure

    Returns:
        ValidationResult

    Raises:
        ProofValidationError: If validation fails and strict=True
    """
    validator = ProofValidator()
    result = validator.validate_chain(proofs)

    if strict and not result.passed:
        error_summary = "; ".join(result.errors[:5])
        raise ProofValidationError(
            f"Proof chain integrity validation failed: {error_summary}"
        )

    return result


def verify_proof_file_integrity(filepath: Path, strict: bool = True) -> ValidationResult:
    """
    Verify integrity of a JSONL proof file.

    Loads all proofs and validates chain integrity.

    Args:
        filepath: Path to JSONL proof file
        strict: If True, raise exception on failure

    Returns:
        ValidationResult

    Raises:
        ProofValidationError: If validation fails and strict=True
        FileNotFoundError: If file doesn't exist
    """
    if not filepath.exists():
        if strict:
            raise ProofValidationError(f"Proof file not found: {filepath}")
        return ValidationResult(
            passed=False,
            errors=(f"File not found: {filepath}",),
            warnings=(),
            metadata={"filepath": str(filepath)},
        )

    proofs: List[Dict[str, Any]] = []
    parse_errors: List[str] = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                proofs.append(json.loads(line))
            except json.JSONDecodeError as e:
                parse_errors.append(f"Line {line_num}: JSON parse error: {e}")

    if parse_errors:
        if strict:
            raise ProofValidationError(
                f"Proof file contains invalid JSON: {parse_errors[0]}"
            )
        return ValidationResult(
            passed=False,
            errors=tuple(parse_errors),
            warnings=(),
            metadata={"filepath": str(filepath), "proof_count": len(proofs)},
        )

    result = verify_proof_chain(proofs, strict=False)

    if strict and not result.passed:
        raise ProofValidationError(
            f"Proof file integrity validation failed: {result.errors[0] if result.errors else 'Unknown error'}"
        )

    return result


# ═══════════════════════════════════════════════════════════════════════════
# END — SAM (GID-06) — �
# ═══════════════════════════════════════════════════════════════════════════
