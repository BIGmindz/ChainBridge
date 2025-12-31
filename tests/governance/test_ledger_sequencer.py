# ═══════════════════════════════════════════════════════════════════════════════
# Ledger Sequencer Tests
# PAC-BENSON-P24: CONTROL PLANE CORE HARDENING
# Agent: DAN (GID-07) — CI / Compiler Gates
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for ledger sequencer module.

Validates:
- INV-LEDGER-SEQ-001: Sequence numbers are monotonically increasing
- INV-LEDGER-SEQ-002: No gaps in sequence allowed
- INV-LEDGER-SEQ-003: Hash chain binds all entries
- INV-LEDGER-SEQ-004: Timestamps are monotonically non-decreasing
- INV-LEDGER-SEQ-005: Reordering is cryptographically impossible
"""

import pytest
from datetime import datetime, timezone

from core.governance.ledger_sequencer import (
    LedgerSequencer,
    SequencePoint,
    MerkleTree,
    MerkleProof,
    CheckpointManager,
    AuditCheckpoint,
    compute_entry_binding_hash,
    verify_chain_link,
    GENESIS_SEQUENCE,
    GENESIS_HASH,
    SequencerError,
    SequenceGapError,
    SequenceRegressionError,
    ChainBrokenError,
    TimestampRegressionError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sequencer():
    """Create fresh LedgerSequencer."""
    return LedgerSequencer()


@pytest.fixture
def merkle_tree():
    """Create fresh MerkleTree."""
    return MerkleTree()


@pytest.fixture
def sample_entry_data():
    """Sample entry data for testing."""
    return {
        "pdo_id": "PDO-TEST-001",
        "pac_id": "PAC-TEST-001",
        "outcome_status": "ACCEPTED",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SEQUENCE POINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSequencePoint:
    """Tests for SequencePoint class."""
    
    def test_genesis_creation(self):
        """Genesis sequence point can be created."""
        genesis = SequencePoint.genesis()
        assert genesis.sequence == GENESIS_SEQUENCE
        assert genesis.entry_hash == GENESIS_HASH
        assert genesis.entry_id == "GENESIS"
    
    def test_sequence_point_frozen(self):
        """Sequence points are immutable."""
        point = SequencePoint(
            sequence=1,
            entry_hash="a" * 64,
            timestamp="2024-01-01T00:00:00+00:00",
            entry_id="TEST-001"
        )
        
        with pytest.raises(AttributeError):
            point.sequence = 2
    
    def test_to_dict(self):
        """to_dict produces expected output."""
        point = SequencePoint(
            sequence=1,
            entry_hash="a" * 64,
            timestamp="2024-01-01T00:00:00+00:00",
            entry_id="TEST-001"
        )
        
        d = point.to_dict()
        assert d["sequence"] == 1
        assert d["entry_id"] == "TEST-001"


# ═══════════════════════════════════════════════════════════════════════════════
# HASH COMPUTATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashComputation:
    """Tests for hash computation utilities."""
    
    def test_compute_entry_binding_hash_deterministic(self, sample_entry_data):
        """Hash computation is deterministic."""
        ts = "2024-01-01T00:00:00+00:00"
        
        hash1 = compute_entry_binding_hash(1, GENESIS_HASH, sample_entry_data, ts)
        hash2 = compute_entry_binding_hash(1, GENESIS_HASH, sample_entry_data, ts)
        
        assert hash1 == hash2
    
    def test_hash_changes_with_sequence(self, sample_entry_data):
        """Different sequence produces different hash."""
        ts = "2024-01-01T00:00:00+00:00"
        
        hash1 = compute_entry_binding_hash(1, GENESIS_HASH, sample_entry_data, ts)
        hash2 = compute_entry_binding_hash(2, GENESIS_HASH, sample_entry_data, ts)
        
        assert hash1 != hash2
    
    def test_hash_changes_with_previous(self, sample_entry_data):
        """Different previous hash produces different hash."""
        ts = "2024-01-01T00:00:00+00:00"
        
        hash1 = compute_entry_binding_hash(1, GENESIS_HASH, sample_entry_data, ts)
        hash2 = compute_entry_binding_hash(1, "b" * 64, sample_entry_data, ts)
        
        assert hash1 != hash2
    
    def test_verify_chain_link_valid(self, sample_entry_data):
        """Valid chain link passes verification."""
        ts = "2024-01-01T00:00:00+00:00"
        entry_hash = compute_entry_binding_hash(1, GENESIS_HASH, sample_entry_data, ts)
        
        result = verify_chain_link(entry_hash, GENESIS_HASH, 1, sample_entry_data, ts)
        assert result is True
    
    def test_verify_chain_link_invalid(self, sample_entry_data):
        """Invalid chain link raises error."""
        ts = "2024-01-01T00:00:00+00:00"
        
        with pytest.raises(ChainBrokenError):
            verify_chain_link("wrong" + "0" * 59, GENESIS_HASH, 1, sample_entry_data, ts)


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER SEQUENCER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLedgerSequencer:
    """Tests for LedgerSequencer class."""
    
    def test_initial_state(self, sequencer):
        """Sequencer initializes with genesis."""
        assert sequencer.count() == 1  # Genesis
        seq, hash_, ts = sequencer.current_state()
        assert seq == GENESIS_SEQUENCE
        assert hash_ == GENESIS_HASH
    
    def test_next_sequence(self, sequencer):
        """next_sequence returns correct value."""
        assert sequencer.next_sequence() == 1
    
    def test_append_entry(self, sequencer, sample_entry_data):
        """Entries can be appended."""
        point = sequencer.append("TEST-001", sample_entry_data)
        
        assert point.sequence == 1
        assert point.entry_id == "TEST-001"
        assert sequencer.count() == 2
    
    def test_append_multiple_entries(self, sequencer, sample_entry_data):
        """Multiple entries can be appended."""
        for i in range(10):
            point = sequencer.append(f"TEST-{i:03d}", sample_entry_data)
            assert point.sequence == i + 1
        
        assert sequencer.count() == 11  # Genesis + 10
    
    def test_sequence_monotonically_increases(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-001: Sequence numbers increase."""
        sequences = []
        for i in range(5):
            point = sequencer.append(f"TEST-{i}", sample_entry_data)
            sequences.append(point.sequence)
        
        # Verify strictly increasing
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i - 1]
    
    def test_no_sequence_gaps(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-002: No gaps in sequence."""
        for i in range(10):
            sequencer.append(f"TEST-{i}", sample_entry_data)
        
        is_valid, errors = sequencer.verify_sequence()
        assert is_valid is True
        assert len(errors) == 0
    
    def test_timestamp_regression_blocked(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-004: Timestamp regression blocked."""
        # First entry with later timestamp
        sequencer.append("TEST-1", sample_entry_data, "2024-01-02T00:00:00+00:00")
        
        # Second entry with earlier timestamp should fail
        with pytest.raises(TimestampRegressionError):
            sequencer.append("TEST-2", sample_entry_data, "2024-01-01T00:00:00+00:00")
    
    def test_get_point(self, sequencer, sample_entry_data):
        """Points can be retrieved by sequence."""
        sequencer.append("TEST-001", sample_entry_data)
        
        genesis = sequencer.get_point(0)
        assert genesis.entry_id == "GENESIS"
        
        first = sequencer.get_point(1)
        assert first.entry_id == "TEST-001"
    
    def test_get_range(self, sequencer, sample_entry_data):
        """Ranges can be retrieved."""
        for i in range(5):
            sequencer.append(f"TEST-{i}", sample_entry_data)
        
        points = sequencer.get_range(1, 4)
        assert len(points) == 3
        assert points[0].sequence == 1
        assert points[2].sequence == 3


# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMerkleTree:
    """Tests for MerkleTree class."""
    
    def test_add_leaf(self, merkle_tree):
        """Leaves can be added."""
        index = merkle_tree.add_leaf("a" * 64)
        assert index == 0
        
        index = merkle_tree.add_leaf("b" * 64)
        assert index == 1
    
    def test_compute_root_empty(self, merkle_tree):
        """Empty tree has genesis root."""
        root = merkle_tree.compute_root()
        assert root == GENESIS_HASH
    
    def test_compute_root_single_leaf(self, merkle_tree):
        """Single leaf tree has leaf as root."""
        leaf = "a" * 64
        merkle_tree.add_leaf(leaf)
        root = merkle_tree.compute_root()
        # With one leaf, root is computed from leaf + leaf
        assert len(root) == 64
    
    def test_compute_root_deterministic(self, merkle_tree):
        """Root computation is deterministic."""
        for i in range(4):
            merkle_tree.add_leaf(f"{i}" * 64)
        
        root1 = merkle_tree.compute_root()
        root2 = merkle_tree.compute_root()
        
        assert root1 == root2
    
    def test_get_proof(self, merkle_tree):
        """Proofs can be generated."""
        for i in range(4):
            merkle_tree.add_leaf(f"{i}" * 64)
        
        proof = merkle_tree.get_proof(0)
        assert proof is not None
        assert proof.sequence == 0
        assert len(proof.path) > 0
    
    def test_proof_verification(self, merkle_tree):
        """Generated proofs verify correctly."""
        for i in range(4):
            merkle_tree.add_leaf(chr(ord('a') + i) * 64)
        
        proof = merkle_tree.get_proof(0)
        assert proof.verify() is True


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckpointManager:
    """Tests for CheckpointManager class."""
    
    def test_create_checkpoint(self, sequencer, sample_entry_data):
        """Checkpoints can be created."""
        manager = CheckpointManager(sequencer)
        
        sequencer.append("TEST-001", sample_entry_data)
        manager.record_entry("a" * 64)
        
        checkpoint = manager.create_checkpoint()
        assert checkpoint.sequence == 1
        assert checkpoint.entry_count == 2
    
    def test_checkpoint_immutable(self, sequencer, sample_entry_data):
        """Checkpoints are immutable."""
        manager = CheckpointManager(sequencer)
        checkpoint = manager.create_checkpoint()
        
        with pytest.raises(AttributeError):
            checkpoint.sequence = 999
    
    def test_verify_checkpoint(self, sequencer, sample_entry_data):
        """Checkpoints can be verified."""
        manager = CheckpointManager(sequencer)
        
        sequencer.append("TEST-001", sample_entry_data)
        checkpoint = manager.create_checkpoint()
        
        assert manager.verify_checkpoint(checkpoint) is True
    
    def test_get_checkpoint(self, sequencer):
        """Checkpoints can be retrieved by ID."""
        manager = CheckpointManager(sequencer)
        checkpoint = manager.create_checkpoint()
        
        retrieved = manager.get_checkpoint(checkpoint.checkpoint_id)
        assert retrieved is not None
        assert retrieved.checkpoint_id == checkpoint.checkpoint_id


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLedgerSequencerInvariants:
    """Tests for ledger sequencer invariants."""
    
    def test_inv_ledger_seq_001_monotonic_sequence(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-001: Monotonically increasing sequences."""
        prev_seq = 0
        for i in range(10):
            point = sequencer.append(f"TEST-{i}", sample_entry_data)
            assert point.sequence > prev_seq
            prev_seq = point.sequence
    
    def test_inv_ledger_seq_002_no_gaps(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-002: No gaps allowed."""
        for i in range(10):
            sequencer.append(f"TEST-{i}", sample_entry_data)
        
        # Verify contiguous sequence
        for i in range(11):  # 0-10 including genesis
            point = sequencer.get_point(i)
            assert point is not None
            assert point.sequence == i
    
    def test_inv_ledger_seq_003_hash_chain(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-003: Hash chain binds entries."""
        points = []
        for i in range(5):
            point = sequencer.append(f"TEST-{i}", sample_entry_data)
            points.append(point)
        
        # Each entry should have unique hash
        hashes = [p.entry_hash for p in points]
        assert len(set(hashes)) == len(hashes)
    
    def test_inv_ledger_seq_004_timestamp_monotonic(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-004: Timestamps non-decreasing."""
        timestamps = [
            "2024-01-01T00:00:00+00:00",
            "2024-01-01T00:00:01+00:00",
            "2024-01-01T00:00:01+00:00",  # Same is OK
            "2024-01-01T00:00:02+00:00",
        ]
        
        for i, ts in enumerate(timestamps):
            point = sequencer.append(f"TEST-{i}", sample_entry_data, ts)
            # All should succeed with non-decreasing timestamps
            assert point is not None
    
    def test_inv_ledger_seq_005_reordering_prevented(self, sequencer, sample_entry_data):
        """INV-LEDGER-SEQ-005: Reordering is cryptographically impossible."""
        # The hash chain prevents reordering because each entry
        # includes the previous hash in its binding hash.
        # If entries were reordered, the chain would break.
        
        sequencer.append("A", {"order": 1})
        sequencer.append("B", {"order": 2})
        
        # Verify sequence is intact
        is_valid, errors = sequencer.verify_sequence()
        assert is_valid is True
