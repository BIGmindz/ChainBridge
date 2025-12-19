"""
Tests for Proof Storage - PAC-DAN-PROOF-PERSISTENCE-01

Tests verify:
1. Append-only behavior
2. Hash validation
3. Chain integrity
4. Startup validation
5. Corruption detection
6. Restart persistence
"""

import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from core.proof_storage import (
    ProofIntegrityError,
    ProofStorageV1,
    compute_chain_hash,
    compute_content_hash,
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for proof storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def proof_storage(temp_storage_dir):
    """Create a ProofStorageV1 instance with temp storage."""
    log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
    manifest_path = os.path.join(temp_storage_dir, "proofs_manifest.json")
    storage = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
    storage.validate_on_startup()
    return storage


class TestContentHash:
    """Test content hash computation."""

    def test_deterministic_hash(self):
        """Hash of same content should be identical."""
        payload = {"foo": "bar", "num": 123}
        hash1 = compute_content_hash(payload)
        hash2 = compute_content_hash(payload)
        assert hash1 == hash2

    def test_order_independent(self):
        """Hash should be order-independent due to sort_keys."""
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        assert compute_content_hash(payload1) == compute_content_hash(payload2)

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        hash1 = compute_content_hash({"x": 1})
        hash2 = compute_content_hash({"x": 2})
        assert hash1 != hash2

    def test_hash_length(self):
        """SHA-256 produces 64 hex characters."""
        h = compute_content_hash({"test": True})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestChainHash:
    """Test chain hash computation."""

    def test_chain_links_previous(self):
        """Chain hash should depend on previous hash."""
        prev = "a" * 64
        content = "b" * 64
        chain = compute_chain_hash(prev, content)
        
        # Same inputs should give same chain hash
        assert chain == compute_chain_hash(prev, content)
        
        # Different previous should change chain hash
        assert chain != compute_chain_hash("c" * 64, content)

    def test_chain_hash_format(self):
        """Chain hash should be valid SHA-256."""
        chain = compute_chain_hash("0" * 64, "1" * 64)
        assert len(chain) == 64
        assert all(c in "0123456789abcdef" for c in chain)


class TestProofStorageV1:
    """Test ProofStorageV1 functionality."""

    def test_init_creates_directories(self, temp_storage_dir):
        """Storage should create parent directories."""
        nested_path = os.path.join(temp_storage_dir, "deep", "nested", "proofs.jsonl")
        storage = ProofStorageV1(log_path=nested_path)
        assert Path(nested_path).parent.exists()

    def test_fresh_start_validation_passes(self, temp_storage_dir):
        """Validation should pass on fresh start (no log file)."""
        log_path = os.path.join(temp_storage_dir, "new_proofs.jsonl")
        storage = ProofStorageV1(log_path=log_path)
        report = storage.validate_on_startup()
        
        assert report["status"] == "PASS"
        assert report["validated_count"] == 0
        assert report["error_count"] == 0

    def test_append_proof(self, proof_storage):
        """Should append proof to log."""
        payload = {"action": "test", "value": 42}
        record = proof_storage.append_proof(proof_type="test", payload=payload)
        
        assert record["proof_type"] == "test"
        assert record["payload"] == payload
        assert record["sequence_number"] == 1
        assert "content_hash" in record
        assert "chain_hash" in record
        assert "timestamp" in record

    def test_append_increments_sequence(self, proof_storage):
        """Sequence numbers should increment."""
        r1 = proof_storage.append_proof(proof_type="test", payload={"n": 1})
        r2 = proof_storage.append_proof(proof_type="test", payload={"n": 2})
        r3 = proof_storage.append_proof(proof_type="test", payload={"n": 3})
        
        assert r1["sequence_number"] == 1
        assert r2["sequence_number"] == 2
        assert r3["sequence_number"] == 3

    def test_append_updates_chain_hash(self, proof_storage):
        """Each append should update the chain hash."""
        r1 = proof_storage.append_proof(proof_type="test", payload={"n": 1})
        r2 = proof_storage.append_proof(proof_type="test", payload={"n": 2})
        
        # Chain hashes should differ
        assert r1["chain_hash"] != r2["chain_hash"]
        
        # r2 chain should link to r1
        expected_chain = compute_chain_hash(r1["chain_hash"], r2["content_hash"])
        assert r2["chain_hash"] == expected_chain

    def test_iter_proofs(self, proof_storage):
        """Should iterate over all proofs."""
        for i in range(5):
            proof_storage.append_proof(proof_type="test", payload={"i": i})
        
        proofs = list(proof_storage.iter_proofs())
        assert len(proofs) == 5
        assert [p["payload"]["i"] for p in proofs] == [0, 1, 2, 3, 4]

    def test_get_stats(self, proof_storage):
        """Should return accurate stats."""
        proof_storage.append_proof(proof_type="test", payload={"x": 1})
        proof_storage.append_proof(proof_type="test", payload={"x": 2})
        
        stats = proof_storage.get_stats()
        assert stats["proof_count"] == 2
        assert stats["validated"] is True
        assert stats["file_size_bytes"] > 0

    def test_requires_validation_before_append(self, temp_storage_dir):
        """Should raise error if validation wasn't called."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        storage = ProofStorageV1(log_path=log_path)
        
        with pytest.raises(RuntimeError, match="validate_on_startup"):
            storage.append_proof(proof_type="test", payload={})


class TestProofPersistence:
    """Test proof persistence across restarts."""

    def test_proofs_survive_restart(self, temp_storage_dir):
        """Proofs should persist across storage instances."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        manifest_path = os.path.join(temp_storage_dir, "manifest.json")
        
        # First instance: write proofs
        storage1 = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
        storage1.validate_on_startup()
        storage1.append_proof(proof_type="test", payload={"msg": "hello"})
        storage1.append_proof(proof_type="test", payload={"msg": "world"})
        
        last_hash_1 = storage1.get_last_hash()
        chain_hash_1 = storage1.get_chain_hash()
        
        # Simulate restart: new instance
        storage2 = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
        report = storage2.validate_on_startup()
        
        # Verify persistence
        assert report["status"] == "PASS"
        assert report["validated_count"] == 2
        assert storage2.get_proof_count() == 2
        assert storage2.get_last_hash() == last_hash_1
        assert storage2.get_chain_hash() == chain_hash_1

    def test_continue_appending_after_restart(self, temp_storage_dir):
        """Should continue appending after restart."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # First instance
        storage1 = ProofStorageV1(log_path=log_path)
        storage1.validate_on_startup()
        storage1.append_proof(proof_type="test", payload={"n": 1})
        storage1.append_proof(proof_type="test", payload={"n": 2})
        
        # Restart
        storage2 = ProofStorageV1(log_path=log_path)
        storage2.validate_on_startup()
        storage2.append_proof(proof_type="test", payload={"n": 3})
        
        assert storage2.get_proof_count() == 3
        
        proofs = list(storage2.iter_proofs())
        assert proofs[2]["sequence_number"] == 3


class TestIntegrityValidation:
    """Test corruption detection and integrity validation."""

    def test_detects_content_hash_tampering(self, temp_storage_dir):
        """Should detect when content hash is tampered."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Create valid proofs
        storage = ProofStorageV1(log_path=log_path)
        storage.validate_on_startup()
        storage.append_proof(proof_type="test", payload={"secret": "original"})
        
        # Tamper with the file: change content hash
        with open(log_path, "r") as f:
            line = f.read()
        record = json.loads(line)
        record["content_hash"] = "0" * 64  # Invalid hash
        with open(log_path, "w") as f:
            f.write(json.dumps(record))
        
        # New instance should detect tampering
        storage2 = ProofStorageV1(log_path=log_path)
        with pytest.raises(ProofIntegrityError, match="Content hash mismatch"):
            storage2.validate_on_startup()

    def test_detects_payload_tampering(self, temp_storage_dir):
        """Should detect when payload is modified."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Create valid proofs
        storage = ProofStorageV1(log_path=log_path)
        storage.validate_on_startup()
        storage.append_proof(proof_type="test", payload={"amount": 100})
        
        # Tamper: modify payload but keep original hash
        with open(log_path, "r") as f:
            line = f.read()
        record = json.loads(line)
        record["payload"]["amount"] = 999999  # Tampered!
        with open(log_path, "w") as f:
            f.write(json.dumps(record))
        
        # Should detect the tampering
        storage2 = ProofStorageV1(log_path=log_path)
        with pytest.raises(ProofIntegrityError, match="Content hash mismatch"):
            storage2.validate_on_startup()

    def test_detects_chain_hash_tampering(self, temp_storage_dir):
        """Should detect when chain hash is tampered."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Create multiple proofs
        storage = ProofStorageV1(log_path=log_path)
        storage.validate_on_startup()
        storage.append_proof(proof_type="test", payload={"n": 1})
        storage.append_proof(proof_type="test", payload={"n": 2})
        
        # Tamper: break the chain hash
        with open(log_path, "r") as f:
            lines = f.readlines()
        record = json.loads(lines[1])
        record["chain_hash"] = "f" * 64  # Broken chain
        lines[1] = json.dumps(record) + "\n"
        with open(log_path, "w") as f:
            f.writelines(lines)
        
        # Should detect broken chain
        storage2 = ProofStorageV1(log_path=log_path)
        with pytest.raises(ProofIntegrityError, match="Chain hash mismatch"):
            storage2.validate_on_startup()

    def test_detects_deleted_entry(self, temp_storage_dir):
        """Should detect when an entry is deleted."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Create multiple proofs
        storage = ProofStorageV1(log_path=log_path)
        storage.validate_on_startup()
        storage.append_proof(proof_type="test", payload={"n": 1})
        storage.append_proof(proof_type="test", payload={"n": 2})
        storage.append_proof(proof_type="test", payload={"n": 3})
        
        # Delete the middle entry
        with open(log_path, "r") as f:
            lines = f.readlines()
        with open(log_path, "w") as f:
            f.write(lines[0])  # Keep first
            f.write(lines[2])  # Skip second, keep third
        
        # Chain will be broken
        storage2 = ProofStorageV1(log_path=log_path)
        with pytest.raises(ProofIntegrityError, match="Chain hash mismatch"):
            storage2.validate_on_startup()

    def test_detects_malformed_json(self, temp_storage_dir):
        """Should detect malformed JSON lines."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Create valid proof
        storage = ProofStorageV1(log_path=log_path)
        storage.validate_on_startup()
        storage.append_proof(proof_type="test", payload={"ok": True})
        
        # Corrupt the JSON
        with open(log_path, "a") as f:
            f.write("this is not json\n")
        
        storage2 = ProofStorageV1(log_path=log_path)
        with pytest.raises(ProofIntegrityError):
            storage2.validate_on_startup()

    def test_detects_missing_required_fields(self, temp_storage_dir):
        """Should detect records missing required fields."""
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Write incomplete record directly
        incomplete = {"proof_id": str(uuid4())}  # Missing content_hash, payload, etc.
        with open(log_path, "w") as f:
            f.write(json.dumps(incomplete) + "\n")
        
        storage = ProofStorageV1(log_path=log_path)
        with pytest.raises(ProofIntegrityError, match="Missing fields"):
            storage.validate_on_startup()


class TestAppendOnlyEnforcement:
    """Test that append-only semantics are enforced."""

    def test_no_update_method(self, proof_storage):
        """Storage should not have update methods."""
        assert not hasattr(proof_storage, "update_proof")
        assert not hasattr(proof_storage, "modify_proof")
        assert not hasattr(proof_storage, "edit_proof")

    def test_no_delete_method(self, proof_storage):
        """Storage should not have delete methods."""
        assert not hasattr(proof_storage, "delete_proof")
        assert not hasattr(proof_storage, "remove_proof")
        assert not hasattr(proof_storage, "clear_proofs")

    def test_custom_proof_id_accepted(self, proof_storage):
        """Should accept custom proof IDs."""
        custom_id = str(uuid4())
        record = proof_storage.append_proof(
            proof_type="test",
            payload={"custom": True},
            proof_id=custom_id
        )
        assert record["proof_id"] == custom_id


class TestManifest:
    """Test manifest file behavior."""

    def test_manifest_created_after_validation(self, temp_storage_dir):
        """Manifest should be created after validation."""
        manifest_path = os.path.join(temp_storage_dir, "manifest.json")
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        storage = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
        assert not Path(manifest_path).exists()
        
        storage.validate_on_startup()
        assert Path(manifest_path).exists()

    def test_manifest_updated_on_append(self, temp_storage_dir):
        """Manifest should update on each append."""
        manifest_path = os.path.join(temp_storage_dir, "manifest.json")
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        storage = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
        storage.validate_on_startup()
        
        with open(manifest_path) as f:
            m1 = json.load(f)
        assert m1["proof_count"] == 0
        
        storage.append_proof(proof_type="test", payload={"x": 1})
        
        with open(manifest_path) as f:
            m2 = json.load(f)
        assert m2["proof_count"] == 1

    def test_manifest_is_advisory_not_authoritative(self, temp_storage_dir):
        """Manifest corruption should not block startup."""
        manifest_path = os.path.join(temp_storage_dir, "manifest.json")
        log_path = os.path.join(temp_storage_dir, "proofs.jsonl")
        
        # Create storage with proofs
        storage1 = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
        storage1.validate_on_startup()
        storage1.append_proof(proof_type="test", payload={"x": 1})
        
        # Corrupt manifest
        with open(manifest_path, "w") as f:
            f.write("corrupted!")
        
        # Should still work (manifest is advisory)
        storage2 = ProofStorageV1(log_path=log_path, manifest_path=manifest_path)
        report = storage2.validate_on_startup()
        assert report["status"] == "PASS"
        assert report["validated_count"] == 1
