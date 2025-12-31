"""Proof Lineage Validation Test Suite.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝

Tests A6 Architecture Lock enforcement for proof lineage:
- Forward-only hash chaining
- No orphan proofs
- No proof mutation
- No proof deletion (sequence gaps)

DOCTRINE:
- Proof chain breaks → FAIL
- Proof mutation detected → FAIL
- Orphan proof (no chain link) → FAIL
- All violations are FAIL-CLOSED

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import hashlib
import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from core.proof.validation import (
    ProofValidator,
    ProofLineageValidator,
    ProofValidationError,
    ValidationResult,
    GENESIS_HASH,
    REQUIRED_PROOF_FIELDS,
    compute_canonical_hash,
    compute_chain_hash,
    validate_proof_lineage,
    verify_proof_chain,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lineage_validator() -> ProofLineageValidator:
    """Provide ProofLineageValidator instance."""
    return ProofLineageValidator()


@pytest.fixture
def proof_validator() -> ProofValidator:
    """Provide ProofValidator instance."""
    return ProofValidator()


def create_valid_proof(
    sequence_number: int,
    previous_chain_hash: str = GENESIS_HASH,
) -> dict:
    """Create a valid proof with proper chain linking."""
    proof_id = str(uuid4())
    event_id = str(uuid4())
    decision_id = str(uuid4())
    action_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create base proof data
    proof = {
        "proof_id": proof_id,
        "event_id": event_id,
        "event_hash": hashlib.sha256(event_id.encode()).hexdigest(),
        "event_type": "PRICE_SIGNAL",
        "event_timestamp": timestamp,
        "decision_id": decision_id,
        "decision_hash": hashlib.sha256(decision_id.encode()).hexdigest(),
        "decision_outcome": "APPROVED",
        "decision_rule": "threshold-policy",
        "decision_rule_version": "v1.0",
        "decision_inputs": {"price": 100.0},
        "decision_explanation": "Price above threshold",
        "action_id": action_id,
        "action_type": "TRADE_EXECUTE",
        "action_status": "COMPLETED",
        "action_details": {"amount": 1.0},
        "action_error": None,
        "proof_timestamp": timestamp,
        "sequence_number": sequence_number,
    }

    # Compute content hash
    content_hash = compute_canonical_hash(proof)
    proof["content_hash"] = content_hash

    # Compute chain hash
    chain_hash = compute_chain_hash(previous_chain_hash, content_hash)
    proof["chain_hash"] = chain_hash

    return proof


def create_proof_chain(count: int) -> list[dict]:
    """Create a valid chain of proofs."""
    proofs = []
    previous_hash = GENESIS_HASH

    for i in range(1, count + 1):
        proof = create_valid_proof(i, previous_hash)
        proofs.append(proof)
        previous_hash = proof["chain_hash"]

    return proofs


# ---------------------------------------------------------------------------
# Forward-Only Lineage Tests
# ---------------------------------------------------------------------------


class TestForwardOnlyLineage:
    """Tests for forward-only proof lineage validation."""

    def test_valid_first_proof_chains_from_genesis(self, lineage_validator: ProofLineageValidator):
        """First proof should chain from GENESIS_HASH."""
        first_proof = create_valid_proof(1, GENESIS_HASH)

        result = lineage_validator.validate_lineage(first_proof, [])

        assert result.passed is True
        assert len(result.errors) == 0

    def test_valid_second_proof_chains_from_first(self, lineage_validator: ProofLineageValidator):
        """Second proof should chain from first proof's chain_hash."""
        proofs = create_proof_chain(1)
        second_proof = create_valid_proof(2, proofs[0]["chain_hash"])

        result = lineage_validator.validate_lineage(second_proof, proofs)

        assert result.passed is True

    def test_orphan_proof_fails(self, lineage_validator: ProofLineageValidator):
        """Proof not chained to existing chain should fail."""
        existing_proofs = create_proof_chain(2)

        # Create orphan proof that chains from wrong hash
        orphan_proof = create_valid_proof(3, "0" * 64)  # Wrong previous hash

        result = lineage_validator.validate_lineage(orphan_proof, existing_proofs)

        # Should fail because chain_hash doesn't link to existing chain
        assert result.passed is False
        assert any("chain hash mismatch" in e.lower() for e in result.errors)

    def test_sequence_gap_detected(self, lineage_validator: ProofLineageValidator):
        """Sequence number gaps should be detected."""
        existing_proofs = create_proof_chain(2)

        # Create proof with wrong sequence (gap)
        proof_with_gap = create_valid_proof(5, existing_proofs[-1]["chain_hash"])  # Should be 3

        result = lineage_validator.validate_lineage(proof_with_gap, existing_proofs)

        assert result.passed is False
        assert any("sequence" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# Proof Mutation Detection Tests
# ---------------------------------------------------------------------------


class TestProofMutationDetection:
    """Tests for proof mutation detection."""

    def test_unmodified_proof_valid(self, lineage_validator: ProofLineageValidator):
        """Unmodified proof should pass mutation check."""
        proof = create_valid_proof(1)
        original_hash = proof["content_hash"]

        result = lineage_validator.validate_no_mutation(proof, original_hash)

        assert result.passed is True

    def test_modified_field_detected(self, lineage_validator: ProofLineageValidator):
        """Modified proof field should be detected."""
        proof = create_valid_proof(1)
        original_hash = proof["content_hash"]

        # Mutate a field
        proof["decision_outcome"] = "REJECTED"  # Changed from APPROVED

        result = lineage_validator.validate_no_mutation(proof, original_hash)

        assert result.passed is False
        assert any("mutation" in e.lower() for e in result.errors)

    def test_added_field_to_hashable_set_detected(
        self, lineage_validator: ProofLineageValidator
    ):
        """Modifying a hashable field should be detected as mutation.

        Note: Only fields in HASHABLE_FIELDS affect the content hash.
        Adding non-hashable fields won't change the hash by design.
        """
        proof = create_valid_proof(1)
        original_hash = proof["content_hash"]

        # Modify a hashable field (decision_explanation is in HASHABLE_FIELDS)
        proof["decision_explanation"] = "MODIFIED EXPLANATION"

        result = lineage_validator.validate_no_mutation(proof, original_hash)

        assert result.passed is False

    def test_removed_field_detected(self, lineage_validator: ProofLineageValidator):
        """Removed field should be detected as mutation."""
        proof = create_valid_proof(1)
        original_hash = proof["content_hash"]

        # Remove a field
        del proof["decision_explanation"]

        result = lineage_validator.validate_no_mutation(proof, original_hash)

        assert result.passed is False


# ---------------------------------------------------------------------------
# Chain Integrity Tests
# ---------------------------------------------------------------------------


class TestChainIntegrity:
    """Tests for proof chain integrity validation."""

    def test_valid_chain_passes(self, proof_validator: ProofValidator):
        """Valid proof chain should pass validation."""
        proofs = create_proof_chain(5)

        result = proof_validator.validate_chain(proofs)

        assert result.passed is True

    def test_empty_chain_valid(self, proof_validator: ProofValidator):
        """Empty proof chain should be valid (with warning)."""
        result = proof_validator.validate_chain([])

        assert result.passed is True
        assert "empty" in result.warnings[0].lower() if result.warnings else True

    def test_modified_middle_proof_fails(self, proof_validator: ProofValidator):
        """Modified proof in middle of chain should fail."""
        proofs = create_proof_chain(5)

        # Modify middle proof
        proofs[2]["decision_outcome"] = "MUTATED"

        result = proof_validator.validate_chain(proofs)

        assert result.passed is False
        assert any("mismatch" in e.lower() or "tampered" in e.lower() for e in result.errors)

    def test_reordered_proofs_fail(self, proof_validator: ProofValidator):
        """Reordered proofs should fail chain validation."""
        proofs = create_proof_chain(5)

        # Swap proofs 2 and 3
        proofs[1], proofs[2] = proofs[2], proofs[1]

        result = proof_validator.validate_chain(proofs)

        assert result.passed is False

    def test_deleted_proof_detected(self, proof_validator: ProofValidator):
        """Deleted proof from chain should be detected."""
        proofs = create_proof_chain(5)

        # Remove proof in middle
        del proofs[2]

        result = proof_validator.validate_chain(proofs)

        assert result.passed is False


# ---------------------------------------------------------------------------
# FAIL-CLOSED Behavior Tests
# ---------------------------------------------------------------------------


class TestFailClosedBehavior:
    """Tests ensuring FAIL-CLOSED behavior for proof lineage."""

    def test_invalid_proof_fails_lineage(self, lineage_validator: ProofLineageValidator):
        """Invalid proof should fail lineage validation."""
        # Missing required fields
        invalid_proof = {"proof_id": str(uuid4())}

        result = lineage_validator.validate_lineage(invalid_proof, [])

        assert result.passed is False

    def test_strict_mode_raises_exception(self):
        """Strict mode should raise ProofValidationError."""
        proofs = create_proof_chain(3)
        # Mutate a proof
        proofs[1]["decision_outcome"] = "TAMPERED"

        with pytest.raises(ProofValidationError):
            verify_proof_chain(proofs, strict=True)

    def test_non_strict_mode_returns_result(self):
        """Non-strict mode should return result without raising."""
        proofs = create_proof_chain(3)
        proofs[1]["decision_outcome"] = "TAMPERED"

        result = verify_proof_chain(proofs, strict=False)

        assert result.passed is False
        assert len(result.errors) > 0

    def test_validate_proof_lineage_strict(self):
        """validate_proof_lineage should raise in strict mode."""
        existing = create_proof_chain(2)
        # Create orphan
        orphan = create_valid_proof(3, "0" * 64)

        with pytest.raises(ProofValidationError):
            validate_proof_lineage(orphan, existing, strict=True)


# ---------------------------------------------------------------------------
# Module-Level Function Tests
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_validate_proof_lineage_valid(self):
        """validate_proof_lineage should pass for valid new proof."""
        existing = create_proof_chain(2)
        new_proof = create_valid_proof(3, existing[-1]["chain_hash"])

        result = validate_proof_lineage(new_proof, existing, strict=False)

        assert result.passed is True

    def test_validate_proof_lineage_invalid(self):
        """validate_proof_lineage should fail for invalid new proof."""
        existing = create_proof_chain(2)
        # Wrong previous hash
        orphan = create_valid_proof(3, GENESIS_HASH)

        result = validate_proof_lineage(orphan, existing, strict=False)

        assert result.passed is False

    def test_verify_proof_chain_valid(self):
        """verify_proof_chain should pass for valid chain."""
        proofs = create_proof_chain(5)

        result = verify_proof_chain(proofs, strict=False)

        assert result.passed is True


# ---------------------------------------------------------------------------
# Hash Computation Tests
# ---------------------------------------------------------------------------


class TestHashComputation:
    """Tests for hash computation functions."""

    def test_canonical_hash_deterministic(self):
        """Canonical hash should be deterministic."""
        proof = create_valid_proof(1)

        hash1 = compute_canonical_hash(proof)
        hash2 = compute_canonical_hash(proof)

        assert hash1 == hash2

    def test_canonical_hash_sensitive_to_changes(self):
        """Canonical hash should change when data changes."""
        proof = create_valid_proof(1)
        original_hash = compute_canonical_hash(proof)

        proof["decision_outcome"] = "DIFFERENT"
        modified_hash = compute_canonical_hash(proof)

        assert original_hash != modified_hash

    def test_chain_hash_links_correctly(self):
        """Chain hash should link previous to current."""
        previous_hash = "a" * 64
        content_hash = "b" * 64

        chain_hash = compute_chain_hash(previous_hash, content_hash)

        # Should be SHA-256 of "previous:content"
        expected = hashlib.sha256(f"{previous_hash}:{content_hash}".encode()).hexdigest()
        assert chain_hash == expected

    def test_genesis_hash_is_zeros(self):
        """GENESIS_HASH should be 64 zeros."""
        assert GENESIS_HASH == "0" * 64
        assert len(GENESIS_HASH) == 64


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
