"""
PAC-AUDIT-P70: Merkle Chronicler Tests
========================================
Tamper-evidence tests for immutable log anchoring.

Tests:
1. Basic Merkle tree construction
2. Tamper detection (HIST-01 enforcement)
3. Empty file handling
4. Multi-file anchoring
5. Merkle proof generation
"""

import pytest
import os
import json
import tempfile
from pathlib import Path

from core.audit.merkle_chronicler import MerkleChronicler


class TestMerkleChronicler:
    """Test suite for Merkle-based log anchoring."""
    
    def test_hash_leaf_deterministic(self):
        """Test that identical inputs produce identical hashes."""
        chronicler = MerkleChronicler([])
        
        data = '{"event": "TEST", "timestamp": "2026-01-25"}'
        hash1 = chronicler._hash_leaf(data)
        hash2 = chronicler._hash_leaf(data)
        
        assert hash1 == hash2, "Same input must produce same hash"
        assert len(hash1) == 64, "SHA3-256 hash must be 64 hex characters"
    
    def test_hash_leaf_collision_resistance(self):
        """Test that different inputs produce different hashes."""
        chronicler = MerkleChronicler([])
        
        data1 = '{"event": "EVENT_A"}'
        data2 = '{"event": "EVENT_B"}'
        
        hash1 = chronicler._hash_leaf(data1)
        hash2 = chronicler._hash_leaf(data2)
        
        assert hash1 != hash2, "Different inputs must produce different hashes"
    
    def test_build_tree_single_leaf(self):
        """Test Merkle tree with single leaf."""
        chronicler = MerkleChronicler([])
        leaves = ["abc123def456"]
        
        root, layers = chronicler._build_tree(leaves)
        
        assert root is not None
        assert len(root) == 64  # SHA3-256 hash
        assert len(layers) == 2  # [leaves, root]
    
    def test_build_tree_multiple_leaves(self):
        """Test Merkle tree with multiple leaves."""
        chronicler = MerkleChronicler([])
        leaves = ["hash1", "hash2", "hash3", "hash4"]
        
        root, layers = chronicler._build_tree(leaves)
        
        assert root is not None
        assert len(layers) == 3  # [4 leaves, 2 intermediate, 1 root]
    
    def test_build_tree_odd_count_padding(self):
        """Test Merkle tree with odd number of leaves (requires padding)."""
        chronicler = MerkleChronicler([])
        leaves = ["hash1", "hash2", "hash3"]  # Odd count
        
        root, layers = chronicler._build_tree(leaves)
        
        assert root is not None
        # Should handle padding gracefully
        assert len(layers) >= 2
    
    def test_build_tree_empty(self):
        """Test Merkle tree with no leaves."""
        chronicler = MerkleChronicler([])
        leaves = []
        
        root, layers = chronicler._build_tree(leaves)
        
        # Should return EMPTY_TREE hash
        assert root is not None
        assert len(root) == 64
    
    def test_anchor_logs_basic(self, tmp_path):
        """Test basic log anchoring."""
        # Create test log file
        log_file = tmp_path / "test_audit.jsonl"
        with open(log_file, 'w') as f:
            f.write('{"event": "TEST_1"}\n')
            f.write('{"event": "TEST_2"}\n')
        
        chronicler = MerkleChronicler([str(log_file)])
        anchors = chronicler.anchor_logs()
        
        assert str(log_file) in anchors
        assert anchors[str(log_file)]["status"] == "ANCHORED"
        assert anchors[str(log_file)]["line_count"] == 2
        assert "merkle_root" in anchors[str(log_file)]
        assert len(anchors[str(log_file)]["merkle_root"]) == 64
    
    def test_anchor_logs_missing_file(self):
        """Test anchoring non-existent file."""
        chronicler = MerkleChronicler(["nonexistent.jsonl"])
        anchors = chronicler.anchor_logs()
        
        assert "nonexistent.jsonl" in anchors
        assert anchors["nonexistent.jsonl"]["status"] == "FILE_MISSING"
    
    def test_anchor_logs_empty_file(self, tmp_path):
        """Test anchoring empty log file."""
        log_file = tmp_path / "empty.jsonl"
        log_file.touch()  # Create empty file
        
        chronicler = MerkleChronicler([str(log_file)])
        anchors = chronicler.anchor_logs()
        
        assert anchors[str(log_file)]["status"] == "EMPTY_FILE"
        assert anchors[str(log_file)]["line_count"] == 0
    
    def test_tamper_detection_hist01(self, tmp_path):
        """
        Test HIST-01: The Merkle Root MUST change if a single byte is modified.
        
        This is the critical tamper-evidence test.
        """
        # Create original log
        log_file = tmp_path / "tamper_test.jsonl"
        with open(log_file, 'w') as f:
            f.write('{"event": "ORIGINAL_EVENT"}\n')
        
        # Anchor original
        chronicler = MerkleChronicler([str(log_file)])
        original_anchors = chronicler.anchor_logs()
        original_root = original_anchors[str(log_file)]["merkle_root"]
        
        # Tamper: Change 1 byte
        with open(log_file, 'w') as f:
            f.write('{"event": "TAMPERED_EVENT"}\n')  # Changed ORIGINAL → TAMPERED
        
        # Re-anchor tampered log
        chronicler2 = MerkleChronicler([str(log_file)])
        tampered_anchors = chronicler2.anchor_logs()
        tampered_root = tampered_anchors[str(log_file)]["merkle_root"]
        
        # HIST-01: Roots MUST differ
        assert original_root != tampered_root, \
            "HIST-01 VIOLATION: Merkle root did not change after tampering!"
    
    def test_verify_log_valid(self, tmp_path):
        """Test verification of untampered log."""
        log_file = tmp_path / "verify_test.jsonl"
        with open(log_file, 'w') as f:
            f.write('{"event": "VALID"}\n')
        
        chronicler = MerkleChronicler([str(log_file)])
        anchors = chronicler.anchor_logs()
        
        # Verify immediately (should pass)
        is_valid = chronicler.verify_log(str(log_file))
        assert is_valid, "Verification should pass for untampered log"
    
    def test_verify_log_tampered(self, tmp_path):
        """Test verification detects tampering."""
        log_file = tmp_path / "tamper_verify.jsonl"
        with open(log_file, 'w') as f:
            f.write('{"event": "ORIGINAL"}\n')
        
        chronicler = MerkleChronicler([str(log_file)])
        anchors = chronicler.anchor_logs()
        
        # Tamper the log
        with open(log_file, 'w') as f:
            f.write('{"event": "MODIFIED"}\n')
        
        # Verify (should fail)
        is_valid = chronicler.verify_log(str(log_file))
        assert not is_valid, "Verification should fail for tampered log"
    
    def test_multi_file_anchoring(self, tmp_path):
        """Test anchoring multiple files simultaneously."""
        files = []
        for i in range(3):
            log_file = tmp_path / f"log_{i}.jsonl"
            with open(log_file, 'w') as f:
                f.write(f'{{"event": "LOG_{i}"}}\n')
            files.append(str(log_file))
        
        chronicler = MerkleChronicler(files)
        anchors = chronicler.anchor_logs()
        
        assert len(anchors) == 3
        for path in files:
            assert anchors[path]["status"] == "ANCHORED"
            assert anchors[path]["line_count"] == 1
    
    def test_save_and_load_anchors(self, tmp_path):
        """Test anchor persistence."""
        log_file = tmp_path / "persist_test.jsonl"
        with open(log_file, 'w') as f:
            f.write('{"event": "PERSIST"}\n')
        
        anchor_file = tmp_path / "anchors.json"
        
        # Create and save anchors
        chronicler = MerkleChronicler(
            [str(log_file)],
            anchor_output_path=str(anchor_file)
        )
        original_anchors = chronicler.anchor_logs()
        
        # Load anchors in new instance
        chronicler2 = MerkleChronicler(
            [str(log_file)],
            anchor_output_path=str(anchor_file)
        )
        loaded_anchors = chronicler2.load_anchors()
        
        assert str(log_file) in loaded_anchors
        assert loaded_anchors[str(log_file)]["merkle_root"] == \
               original_anchors[str(log_file)]["merkle_root"]
    
    def test_merkle_proof_generation(self, tmp_path):
        """Test Merkle proof generation for specific log line."""
        log_file = tmp_path / "proof_test.jsonl"
        with open(log_file, 'w') as f:
            for i in range(4):
                f.write(f'{{"event": "LINE_{i}"}}\n')
        
        chronicler = MerkleChronicler([str(log_file)])
        chronicler.anchor_logs()
        
        # Generate proof for line 2 (index 2)
        proof = chronicler.generate_merkle_proof(str(log_file), 2)
        
        assert proof is not None
        assert isinstance(proof, list)
        assert len(proof) > 0  # Should have sibling hashes
    
    def test_double_hashing_security(self):
        """Test that double SHA3-256 is applied."""
        import hashlib
        
        chronicler = MerkleChronicler([])
        data = "test_data"
        
        # Compute expected double hash manually
        h1 = hashlib.sha3_256(data.encode('utf-8')).digest()
        expected = hashlib.sha3_256(h1).hexdigest()
        
        # Compare with chronicler output
        actual = chronicler._hash_leaf(data)
        
        assert actual == expected, "Double hashing not correctly implemented"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
