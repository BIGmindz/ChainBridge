"""
Security Tests - Proof Integrity & Replay Detection

PAC-SAM-PROOF-INTEGRITY-01

QA & ACCEPTANCE CHECKLIST:
- [x] Proof mutation is detected
- [x] Replay attempt is rejected
- [x] Missing proof causes startup failure
- [x] Threat model matches implementation
- [x] No silent downgrade paths exist

Author: SAM (GID-06)
Date: 2025-12-19
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from core.proof.validation import (
    GENESIS_HASH,
    ProofValidationError,
    ProofValidator,
    compute_canonical_hash,
    compute_chain_hash,
    validate_proof_integrity,
    verify_proof_chain,
    verify_proof_file_integrity,
)
from core.security.replay_guard import (
    ReplayAttackError,
    ReplayGuard,
    get_replay_guard,
)


# =============================================================================
# PROOF VALIDATION TESTS
# =============================================================================


class TestProofContentHashValidation:
    """Tests for CTRL-V1: Content hash verification."""

    def test_valid_proof_passes_validation(self):
        """Valid proof with matching hash passes."""
        proof_data = self._create_valid_proof()
        result = validate_proof_integrity(proof_data)

        assert result.passed
        assert len(result.errors) == 0

    def test_tampered_content_detected(self):
        """Tampered proof content produces hash mismatch."""
        proof_data = self._create_valid_proof()
        original_hash = compute_canonical_hash(proof_data)

        # ATTACK: Modify decision outcome
        proof_data["decision_outcome"] = "approved"  # Was "rejected"

        result = validate_proof_integrity(proof_data, expected_hash=original_hash)

        assert not result.passed
        assert any("hash mismatch" in e.lower() for e in result.errors)

    def test_tampered_amount_detected(self):
        """Tampered amount in inputs produces hash mismatch."""
        proof_data = self._create_valid_proof()
        original_hash = compute_canonical_hash(proof_data)

        # ATTACK: Modify amount in decision inputs
        proof_data["decision_inputs"]["amount"] = 1.00  # Was 50000.00

        result = validate_proof_integrity(proof_data, expected_hash=original_hash)

        assert not result.passed

    def test_tampered_timestamp_detected(self):
        """Tampered timestamp produces hash mismatch."""
        proof_data = self._create_valid_proof()
        original_hash = compute_canonical_hash(proof_data)

        # ATTACK: Backdate the proof
        proof_data["proof_timestamp"] = "2020-01-01T00:00:00+00:00"

        result = validate_proof_integrity(proof_data, expected_hash=original_hash)

        assert not result.passed

    def test_missing_required_field_fails(self):
        """Missing required field is detected."""
        proof_data = self._create_valid_proof()
        del proof_data["decision_hash"]

        result = validate_proof_integrity(proof_data)

        assert not result.passed
        assert any("missing" in e.lower() for e in result.errors)

    def test_invalid_hash_format_fails(self):
        """Invalid hash format is detected."""
        proof_data = self._create_valid_proof()
        proof_data["event_hash"] = "not-a-valid-hash"

        result = validate_proof_integrity(proof_data)

        assert not result.passed
        assert any("invalid event_hash" in e.lower() for e in result.errors)

    def _create_valid_proof(self) -> dict:
        """Create a valid proof for testing."""
        return {
            "proof_id": str(uuid4()),
            "event_id": str(uuid4()),
            "event_hash": "a" * 64,
            "event_type": "payment_request",
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_id": str(uuid4()),
            "decision_hash": "b" * 64,
            "decision_outcome": "rejected",
            "decision_rule": "payment_threshold_v1",
            "decision_rule_version": "1.0.0",
            "decision_inputs": {"amount": 50000.00, "vendor_id": "v1"},
            "decision_explanation": "Amount exceeds threshold",
            "action_id": str(uuid4()),
            "action_type": "state_transition",
            "action_status": "success",
            "action_details": {"new_status": "REJECTED"},
            "action_error": None,
            "proof_timestamp": datetime.now(timezone.utc).isoformat(),
        }


class TestProofChainValidation:
    """Tests for CTRL-V2: Chain hash linking."""

    def test_valid_chain_passes(self):
        """Valid proof chain passes validation."""
        proofs = self._create_valid_chain(3)
        result = verify_proof_chain(proofs, strict=False)

        assert result.passed
        assert len(result.errors) == 0

    def test_tampered_chain_hash_detected(self):
        """Tampered chain hash is detected."""
        proofs = self._create_valid_chain(3)

        # ATTACK: Modify chain hash of middle proof
        proofs[1]["chain_hash"] = "x" * 64

        result = verify_proof_chain(proofs, strict=False)

        assert not result.passed
        assert any("chain hash mismatch" in e.lower() for e in result.errors)

    def test_deleted_proof_detected(self):
        """Deleted proof (gap in chain) is detected."""
        proofs = self._create_valid_chain(3)

        # ATTACK: Delete middle proof
        del proofs[1]

        result = verify_proof_chain(proofs, strict=False)

        assert not result.passed
        # Chain hash of #3 won't match because #2 is missing

    def test_reordered_proofs_detected(self):
        """Reordered proofs are detected."""
        proofs = self._create_valid_chain(3)

        # ATTACK: Swap order of proofs
        proofs[0], proofs[2] = proofs[2], proofs[0]

        result = verify_proof_chain(proofs, strict=False)

        assert not result.passed

    def test_sequence_gap_detected(self):
        """Gap in sequence numbers is detected."""
        proofs = self._create_valid_chain(3)

        # ATTACK: Skip sequence number
        proofs[1]["sequence_number"] = 5  # Should be 2

        result = verify_proof_chain(proofs, strict=False)

        assert not result.passed
        assert any("sequence" in e.lower() for e in result.errors)

    def test_strict_mode_raises_exception(self):
        """Strict mode raises exception on failure."""
        proofs = self._create_valid_chain(2)
        proofs[1]["chain_hash"] = "tampered" + "0" * 56

        with pytest.raises(ProofValidationError) as exc:
            verify_proof_chain(proofs, strict=True)

        assert "integrity validation failed" in str(exc.value).lower()

    def _create_valid_chain(self, count: int) -> list:
        """Create a valid proof chain for testing."""
        proofs = []
        prev_chain = GENESIS_HASH

        for i in range(count):
            proof = {
                "proof_id": str(uuid4()),
                "event_id": str(uuid4()),
                "event_hash": "a" * 64,
                "event_type": "payment_request",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "decision_id": str(uuid4()),
                "decision_hash": "b" * 64,
                "decision_outcome": "approved",
                "decision_rule": "payment_threshold_v1",
                "decision_rule_version": "1.0.0",
                "decision_inputs": {"amount": 100.00},
                "decision_explanation": "Approved",
                "action_id": str(uuid4()),
                "action_type": "state_transition",
                "action_status": "success",
                "action_details": {},
                "action_error": None,
                "proof_timestamp": datetime.now(timezone.utc).isoformat(),
                "sequence_number": i + 1,
            }

            content_hash = compute_canonical_hash(proof)
            proof["content_hash"] = content_hash
            proof["chain_hash"] = compute_chain_hash(prev_chain, content_hash)
            prev_chain = proof["chain_hash"]

            proofs.append(proof)

        return proofs


class TestProofFileIntegrity:
    """Tests for CTRL-V3: Startup validation."""

    def test_valid_file_passes(self):
        """Valid JSONL proof file passes validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            proofs = TestProofChainValidation()._create_valid_chain(3)
            for proof in proofs:
                f.write(json.dumps(proof) + "\n")
            filepath = Path(f.name)

        try:
            result = verify_proof_file_integrity(filepath, strict=False)
            assert result.passed
        finally:
            filepath.unlink()

    def test_corrupted_file_fails(self):
        """Corrupted proof file fails validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            proofs = TestProofChainValidation()._create_valid_chain(3)
            # Corrupt the second proof
            proofs[1]["chain_hash"] = "corrupted" + "0" * 55
            for proof in proofs:
                f.write(json.dumps(proof) + "\n")
            filepath = Path(f.name)

        try:
            result = verify_proof_file_integrity(filepath, strict=False)
            assert not result.passed
        finally:
            filepath.unlink()

    def test_missing_file_raises_in_strict_mode(self):
        """Missing proof file raises exception in strict mode."""
        filepath = Path("/nonexistent/proofs.jsonl")

        with pytest.raises(ProofValidationError) as exc:
            verify_proof_file_integrity(filepath, strict=True)

        assert "not found" in str(exc.value).lower()

    def test_invalid_json_fails(self):
        """Invalid JSON in proof file fails validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"valid": "json"}\n')
            f.write('not valid json at all\n')
            f.write('{"another": "valid"}\n')
            filepath = Path(f.name)

        try:
            result = verify_proof_file_integrity(filepath, strict=False)
            assert not result.passed
            assert any("json parse error" in e.lower() for e in result.errors)
        finally:
            filepath.unlink()


# =============================================================================
# REPLAY GUARD TESTS
# =============================================================================


class TestReplayDetection:
    """Tests for CTRL-R1-R4: Replay attack detection."""

    @pytest.fixture
    def replay_guard(self, tmp_path):
        """Create a fresh replay guard for each test."""
        state_file = tmp_path / "replay_guard.json"
        guard = ReplayGuard(state_file=str(state_file))
        guard.load_state()
        return guard

    def test_first_event_accepted(self, replay_guard):
        """First occurrence of an event is accepted."""
        event_hash = "a" * 64
        timestamp = datetime.now(timezone.utc).isoformat()

        # Should not raise
        replay_guard.check_and_record(event_hash, timestamp)

    def test_duplicate_event_rejected(self, replay_guard):
        """Duplicate event is rejected with ReplayAttackError."""
        event_hash = "b" * 64
        timestamp = datetime.now(timezone.utc).isoformat()

        replay_guard.check_and_record(event_hash, timestamp)

        with pytest.raises(ReplayAttackError) as exc:
            replay_guard.check_and_record(event_hash, timestamp)

        assert "replay attack detected" in str(exc.value).lower()
        assert exc.value.event_hash == event_hash

    def test_expired_event_rejected(self, replay_guard):
        """Event outside replay window is rejected."""
        event_hash = "c" * 64
        # Timestamp 48 hours ago (outside 24h window)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

        with pytest.raises(ReplayAttackError) as exc:
            replay_guard.check_and_record(event_hash, old_timestamp)

        assert "outside replay window" in str(exc.value).lower()

    def test_future_event_rejected(self, replay_guard):
        """Event with future timestamp is rejected."""
        event_hash = "d" * 64
        # Timestamp 1 hour in the future
        future_timestamp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        with pytest.raises(ReplayAttackError) as exc:
            replay_guard.check_and_record(event_hash, future_timestamp)

        assert "future" in str(exc.value).lower()

    def test_nonce_reuse_rejected(self, replay_guard):
        """Reused nonce is rejected."""
        nonce = "unique-nonce-12345"
        timestamp = datetime.now(timezone.utc).isoformat()

        replay_guard.check_and_record("e" * 64, timestamp, nonce=nonce)

        with pytest.raises(ReplayAttackError) as exc:
            replay_guard.check_and_record("f" * 64, timestamp, nonce=nonce)

        assert "nonce already used" in str(exc.value).lower()

    def test_out_of_order_sequence_rejected(self, replay_guard):
        """Out-of-order sequence number is rejected."""
        timestamp = datetime.now(timezone.utc).isoformat()

        replay_guard.check_and_record("g" * 64, timestamp, sequence_number=10)

        with pytest.raises(ReplayAttackError) as exc:
            # Lower sequence number
            replay_guard.check_and_record("h" * 64, timestamp, sequence_number=5)

        assert "sequence" in str(exc.value).lower()

    def test_state_persisted_across_instances(self, tmp_path):
        """Replay guard state survives restart."""
        state_file = tmp_path / "replay_guard.json"
        event_hash = "i" * 64
        timestamp = datetime.now(timezone.utc).isoformat()

        # First instance
        guard1 = ReplayGuard(state_file=str(state_file))
        guard1.load_state()
        guard1.check_and_record(event_hash, timestamp)

        # Second instance (simulates restart)
        guard2 = ReplayGuard(state_file=str(state_file))
        guard2.load_state()

        with pytest.raises(ReplayAttackError):
            guard2.check_and_record(event_hash, timestamp)

    def test_invalid_event_hash_rejected(self, replay_guard):
        """Invalid event hash format is rejected."""
        timestamp = datetime.now(timezone.utc).isoformat()

        with pytest.raises(ValueError) as exc:
            replay_guard.check_and_record("not-a-hash", timestamp)

        assert "invalid event_hash" in str(exc.value).lower()

    def test_invalid_timestamp_rejected(self, replay_guard):
        """Invalid timestamp format is rejected."""
        with pytest.raises(ValueError) as exc:
            replay_guard.check_and_record("a" * 64, "not-a-timestamp")

        assert "invalid event_timestamp" in str(exc.value).lower()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestEndToEndIntegrity:
    """Integration tests for complete threat model coverage."""

    def test_tamper_detection_end_to_end(self):
        """Full tamper detection flow from creation to validation."""
        # Create a valid proof chain
        proofs = TestProofChainValidation()._create_valid_chain(5)

        # Validate original
        result = verify_proof_chain(proofs, strict=False)
        assert result.passed

        # ATTACK: Silently modify proof #3's decision outcome
        # Attacker modifies content but CANNOT fix chain_hash without knowing previous entries
        original_chain_hash = proofs[2]["chain_hash"]
        proofs[2]["decision_outcome"] = "rejected"  # Changed from "approved"
        # Attacker recalculates content_hash for modified content
        new_content_hash = compute_canonical_hash(proofs[2])
        proofs[2]["content_hash"] = new_content_hash
        # But the chain_hash is now wrong because it was computed with old content_hash
        # Chain integrity is broken: chain_hash = SHA256(prev_chain : old_content_hash)
        # Now content_hash doesn't match what was used to compute chain_hash

        # Detection: The validator recomputes chain_hash and finds mismatch
        result = verify_proof_chain(proofs, strict=False)
        assert not result.passed
        assert any("chain hash mismatch" in e.lower() for e in result.errors)

    def test_replay_with_integrity_combined(self, tmp_path):
        """Combined replay detection and integrity validation."""
        # Setup
        state_file = tmp_path / "replay_guard.json"
        guard = ReplayGuard(state_file=str(state_file))
        guard.load_state()

        # Create event and proof with valid hex hashes
        event_hash = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        decision_hash = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"
        timestamp = datetime.now(timezone.utc).isoformat()

        proof = {
            "proof_id": str(uuid4()),
            "event_id": str(uuid4()),
            "event_hash": event_hash,
            "event_type": "payment_request",
            "event_timestamp": timestamp,
            "decision_id": str(uuid4()),
            "decision_hash": decision_hash,
            "decision_outcome": "approved",
            "decision_rule": "payment_threshold_v1",
            "decision_rule_version": "1.0.0",
            "decision_inputs": {"amount": 100.00},
            "decision_explanation": "Approved",
            "action_id": str(uuid4()),
            "action_type": "state_transition",
            "action_status": "success",
            "action_details": {},
            "action_error": None,
            "proof_timestamp": timestamp,
        }

        # First submission: OK
        guard.check_and_record(event_hash, timestamp)
        result = validate_proof_integrity(proof)
        assert result.passed

        # Replay attempt: BLOCKED
        with pytest.raises(ReplayAttackError):
            guard.check_and_record(event_hash, timestamp)

    def test_no_silent_failure_paths(self):
        """Verify no silent failure paths exist."""
        validator = ProofValidator()

        # Empty proof should fail explicitly
        result = validator.validate_proof({})
        assert not result.passed
        assert len(result.errors) > 0

        # Partial proof should fail explicitly
        result = validator.validate_proof({"proof_id": str(uuid4())})
        assert not result.passed
        assert len(result.errors) > 0

        # No silent pass for invalid data
        result = validator.validate_proof({"invalid": "structure"})
        assert not result.passed
