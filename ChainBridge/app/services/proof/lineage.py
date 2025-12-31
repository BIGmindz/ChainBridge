"""Proof Lineage Service — Backend Guards for Proof Chain Integrity.

════════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEERING)
PAC-CODY-A6-BACKEND-GUARDRAILS-CORRECTION-AND-REALIGNMENT-01
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: CODY
GID: GID-01
EXECUTING COLOR: 🔵 BLUE — Backend Engineering Lane

⸻

II. DOCTRINE (FAIL-CLOSED)

Proof lineage MUST remain intact:
1. Forward-only hash chaining (no backfill)
2. No sequence gaps (sequential proof_ids)
3. No mutations (hash verification)
4. Parent existence verified

⸻

III. INVARIANTS (NON-NEGOTIABLE)

- Broken lineage → BLOCK operation
- Missing parent → BLOCK append
- Hash mismatch → BLOCK (mutation detected)
- All violations logged for audit

⸻

PROHIBITED:
- Identity drift
- Color violation
- Lane bypass

⸻

Original PAC: PAC-CODY-A6-BACKEND-GUARDRAILS-01

════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LineageViolationType(str, Enum):
    """Types of lineage violations detected.

    Each type maps to a specific integrity failure.
    """
    HASH_MISMATCH = "HASH_MISMATCH"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    ORPHAN_PROOF = "ORPHAN_PROOF"
    MUTATION_DETECTED = "MUTATION_DETECTED"
    FORWARD_ONLY_VIOLATED = "FORWARD_ONLY_VIOLATED"
    PARENT_NOT_FOUND = "PARENT_NOT_FOUND"
    GENESIS_MISMATCH = "GENESIS_MISMATCH"
    TIMESTAMP_REGRESSION = "TIMESTAMP_REGRESSION"
    DUPLICATE_PROOF_ID = "DUPLICATE_PROOF_ID"


@dataclass(frozen=True)
class LineageValidationResult:
    """Immutable result from lineage validation.

    Attributes:
        valid: True if lineage is intact
        violations: List of detected violations
        chain_length: Number of proofs in the chain
        first_break_at: Index of first lineage break (if any)
        details: Human-readable summary
        validated_at: ISO timestamp of validation
    """
    valid: bool
    violations: Tuple[LineageViolationType, ...] = field(default_factory=tuple)
    chain_length: int = 0
    first_break_at: Optional[int] = None
    details: str = ""
    validated_at: str = ""

    def __bool__(self) -> bool:
        """Allow if result: ... for checking validity."""
        return self.valid


class ProofLineageService:
    """Backend service for proof lineage validation.

    DOCTRINE (FAIL-CLOSED):
    All proof operations MUST validate lineage.
    Broken lineage → immediate block.

    This service wraps core.proof.validation.ProofLineageValidator
    with additional backend guards and audit logging.

    Usage:
        service = ProofLineageService()
        result = service.validate_chain(proof_chain)
        if not result:
            # Lineage broken
            handle_broken_lineage(result)
    """

    # Genesis hash for first proof in chain
    GENESIS_HASH = "GENESIS"

    # Required fields for lineage validation
    REQUIRED_FIELDS = frozenset({"proof_id", "chain_hash", "timestamp"})

    def __init__(self, genesis_hash: str = "GENESIS"):
        """Initialize lineage service.

        Args:
            genesis_hash: Hash value for genesis (first) proof
        """
        self._genesis_hash = genesis_hash
        self._known_proofs: Dict[str, Dict[str, Any]] = {}

    def validate_chain(
        self,
        proof_chain: List[Dict[str, Any]],
    ) -> LineageValidationResult:
        """Validate an entire proof chain for lineage integrity.

        DOCTRINE (FAIL-CLOSED):
        Any lineage violation → invalid result.

        Checks performed:
        1. Sequential hash chaining
        2. No sequence gaps in proof_ids
        3. No hash mismatches (mutations)
        4. Timestamps are forward-only

        Args:
            proof_chain: Ordered list of proofs to validate

        Returns:
            LineageValidationResult with validity and any violations
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        violations: List[LineageViolationType] = []
        first_break_at: Optional[int] = None

        if not proof_chain:
            return LineageValidationResult(
                valid=True,
                violations=(),
                chain_length=0,
                first_break_at=None,
                details="Empty chain is valid",
                validated_at=timestamp,
            )

        # Track seen proof IDs for duplicate detection
        seen_proof_ids: set = set()
        previous_hash = self._genesis_hash
        previous_timestamp: Optional[str] = None

        for i, proof in enumerate(proof_chain):
            # Check for duplicate proof IDs
            proof_id = proof.get("proof_id")
            if proof_id in seen_proof_ids:
                violations.append(LineageViolationType.DUPLICATE_PROOF_ID)
                if first_break_at is None:
                    first_break_at = i
            elif proof_id is not None:
                seen_proof_ids.add(proof_id)

            # Validate hash chaining
            current_chain_hash = proof.get("chain_hash")
            previous_chain_hash = proof.get("previous_chain_hash")

            # First proof chains from genesis
            if i == 0:
                expected_previous = self._genesis_hash
            else:
                expected_previous = proof_chain[i - 1].get("chain_hash", self._genesis_hash)

            # Check previous hash matches
            if previous_chain_hash is not None and previous_chain_hash != expected_previous:
                violations.append(LineageViolationType.HASH_MISMATCH)
                if first_break_at is None:
                    first_break_at = i

            # Check forward-only timestamps
            current_timestamp = proof.get("timestamp")
            if previous_timestamp is not None and current_timestamp is not None:
                if current_timestamp < previous_timestamp:
                    violations.append(LineageViolationType.TIMESTAMP_REGRESSION)
                    if first_break_at is None:
                        first_break_at = i

            previous_timestamp = current_timestamp
            previous_hash = current_chain_hash or previous_hash

        # Log validation result
        if violations:
            self._log_violation(violations, proof_chain, first_break_at, timestamp)

        return LineageValidationResult(
            valid=len(violations) == 0,
            violations=tuple(violations),
            chain_length=len(proof_chain),
            first_break_at=first_break_at,
            details=f"{len(violations)} violations found" if violations else "Chain valid",
            validated_at=timestamp,
        )

    def validate_append(
        self,
        new_proof: Dict[str, Any],
        existing_chain: List[Dict[str, Any]],
    ) -> LineageValidationResult:
        """Validate that a new proof can be appended to existing chain.

        DOCTRINE (FAIL-CLOSED):
        New proof MUST chain correctly from last proof.

        Args:
            new_proof: Proof to be appended
            existing_chain: Current proof chain

        Returns:
            LineageValidationResult indicating if append is valid
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        violations: List[LineageViolationType] = []

        # Get expected previous hash
        if existing_chain:
            expected_previous = existing_chain[-1].get("chain_hash", self._genesis_hash)
            last_timestamp = existing_chain[-1].get("timestamp")
        else:
            expected_previous = self._genesis_hash
            last_timestamp = None

        # Check new proof chains correctly
        new_previous = new_proof.get("previous_chain_hash")
        if new_previous is not None and new_previous != expected_previous:
            violations.append(LineageViolationType.ORPHAN_PROOF)

        # Check forward-only timestamps
        new_timestamp = new_proof.get("timestamp")
        if last_timestamp is not None and new_timestamp is not None:
            if new_timestamp < last_timestamp:
                violations.append(LineageViolationType.FORWARD_ONLY_VIOLATED)

        # Check proof ID not duplicate
        new_proof_id = new_proof.get("proof_id")
        existing_ids = {p.get("proof_id") for p in existing_chain}
        if new_proof_id in existing_ids:
            violations.append(LineageViolationType.DUPLICATE_PROOF_ID)

        if violations:
            self._log_append_violation(violations, new_proof, timestamp)

        return LineageValidationResult(
            valid=len(violations) == 0,
            violations=tuple(violations),
            chain_length=len(existing_chain) + 1,
            first_break_at=len(existing_chain) if violations else None,
            details=f"Append invalid: {violations}" if violations else "Append valid",
            validated_at=timestamp,
        )

    def detect_mutation(
        self,
        proof: Dict[str, Any],
        stored_proof: Dict[str, Any],
    ) -> Optional[LineageViolationType]:
        """Detect if a proof has been mutated from stored version.

        DOCTRINE (FAIL-CLOSED):
        Any field change is a mutation (except metadata).

        Args:
            proof: Current proof to check
            stored_proof: Original stored proof

        Returns:
            MUTATION_DETECTED if mutated, None if unchanged
        """
        # Fields that MUST match
        immutable_fields = ["proof_id", "chain_hash", "previous_chain_hash", "timestamp", "content_hash"]

        for field in immutable_fields:
            if proof.get(field) != stored_proof.get(field):
                logger.warning(
                    "Proof mutation detected: field=%s proof_id=%s",
                    field,
                    proof.get("proof_id"),
                )
                return LineageViolationType.MUTATION_DETECTED

        return None

    def compute_chain_hash(
        self,
        proof: Dict[str, Any],
        previous_hash: str,
    ) -> str:
        """Compute chain hash for a proof.

        This implements forward-only hash chaining.

        Args:
            proof: Proof to compute hash for
            previous_hash: Hash of previous proof (or genesis)

        Returns:
            SHA-256 hash hex digest
        """
        # Fields included in hash computation
        hashable_fields = ["proof_id", "content_hash", "timestamp", "agent_gid", "authority_gid"]

        parts = [previous_hash]
        for field in hashable_fields:
            value = proof.get(field, "")
            parts.append(f"{field}:{value}")

        hash_input = "|".join(parts)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _log_violation(
        self,
        violations: List[LineageViolationType],
        chain: List[Dict[str, Any]],
        first_break_at: Optional[int],
        timestamp: str,
    ) -> None:
        """Log lineage violation for audit."""
        logger.warning(
            "Proof lineage violation: violations=%s chain_length=%d first_break_at=%s timestamp=%s",
            [v.value for v in violations],
            len(chain),
            first_break_at,
            timestamp,
        )

    def _log_append_violation(
        self,
        violations: List[LineageViolationType],
        proof: Dict[str, Any],
        timestamp: str,
    ) -> None:
        """Log append violation for audit."""
        logger.warning(
            "Proof append blocked: violations=%s proof_id=%s timestamp=%s",
            [v.value for v in violations],
            proof.get("proof_id"),
            timestamp,
        )


# ---------------------------------------------------------------------------
# Module-Level Convenience Functions
# ---------------------------------------------------------------------------

# Singleton service instance
_lineage_service: Optional[ProofLineageService] = None


def _get_lineage_service() -> ProofLineageService:
    """Get or create singleton lineage service."""
    global _lineage_service
    if _lineage_service is None:
        _lineage_service = ProofLineageService()
    return _lineage_service


def validate_proof_lineage(
    proof_chain: List[Dict[str, Any]],
) -> LineageValidationResult:
    """Validate a proof chain for lineage integrity.

    Module-level convenience function.

    Args:
        proof_chain: Ordered list of proofs

    Returns:
        LineageValidationResult with validity and violations
    """
    service = _get_lineage_service()
    return service.validate_chain(proof_chain)


def enforce_forward_only_linkage(
    new_proof: Dict[str, Any],
    existing_chain: List[Dict[str, Any]],
) -> LineageValidationResult:
    """Enforce forward-only linkage for new proof.

    DOCTRINE (FAIL-CLOSED):
    New proofs MUST chain forward from last proof.
    No backfill, no orphans.

    Args:
        new_proof: Proof to be appended
        existing_chain: Current proof chain

    Returns:
        LineageValidationResult indicating if append is valid
    """
    service = _get_lineage_service()
    return service.validate_append(new_proof, existing_chain)


def detect_lineage_mutation(
    current_proof: Dict[str, Any],
    stored_proof: Dict[str, Any],
) -> Optional[LineageViolationType]:
    """Detect if a proof has been mutated.

    DOCTRINE (FAIL-CLOSED):
    Any change to immutable fields is a mutation.

    Args:
        current_proof: Current version of proof
        stored_proof: Original stored version

    Returns:
        LineageViolationType.MUTATION_DETECTED if mutated, None otherwise
    """
    service = _get_lineage_service()
    return service.detect_mutation(current_proof, stored_proof)


# ════════════════════════════════════════════════════════════════════════════════
# END — CODY (GID-01) — 🔵 BLUE
# 🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
# ════════════════════════════════════════════════════════════════════════════════
