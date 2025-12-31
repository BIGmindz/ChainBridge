# ═══════════════════════════════════════════════════════════════════════════════
# Memory Ledger Tests — Anchoring and Proof Tests
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Memory Ledger Tests — Tests for memory anchoring and proofs.
"""

import pytest
from datetime import datetime, timezone

from core.governance.memory_ledger import (
    AnchorStatus,
    MemoryAnchorRecord,
    MemoryAnchorService,
    MemoryChainValidator,
    MemoryInclusionProof,
    PDOMemoryBinding,
    ProofType,
)
from core.ml.neural_memory import (
    MemorySnapshot,
    MemoryStateHash,
    SnapshotRegistry,
    SnapshotStatus,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY ANCHOR RECORD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryAnchorRecord:
    """Tests for MemoryAnchorRecord."""

    def test_valid_anchor_creation(self) -> None:
        """Test creating a valid anchor record."""
        anchor = MemoryAnchorRecord(
            anchor_id="ANCHOR-MEM-000001",
            snapshot_id="MEM-SNAP-000001",
            state_hash="abc123",
            chain_hash="def456",
            ledger_block=100,
            ledger_tx_hash="tx123",
            anchor_time=datetime.now(timezone.utc).isoformat(),
        )
        assert anchor.anchor_id == "ANCHOR-MEM-000001"
        assert anchor.status == AnchorStatus.PENDING  # default

    def test_invalid_id_raises(self) -> None:
        """Test that invalid ID format raises error."""
        with pytest.raises(ValueError):
            MemoryAnchorRecord(
                anchor_id="INVALID-001",
                snapshot_id="MEM-SNAP-000001",
                state_hash="abc",
                chain_hash="def",
                ledger_block=1,
                ledger_tx_hash="tx",
                anchor_time=datetime.now(timezone.utc).isoformat(),
            )

    def test_compute_anchor_hash(self) -> None:
        """Test anchor hash computation."""
        anchor = MemoryAnchorRecord(
            anchor_id="ANCHOR-MEM-000001",
            snapshot_id="MEM-SNAP-000001",
            state_hash="abc123",
            chain_hash="def456",
            ledger_block=100,
            ledger_tx_hash="tx123",
            anchor_time=datetime.now(timezone.utc).isoformat(),
        )
        hash_value = anchor.compute_anchor_hash()
        assert hash_value is not None
        assert len(hash_value) == 64

    def test_is_verified(self) -> None:
        """Test is_verified status check."""
        anchor_pending = MemoryAnchorRecord(
            anchor_id="ANCHOR-MEM-000001",
            snapshot_id="MEM-SNAP-000001",
            state_hash="abc",
            chain_hash="def",
            ledger_block=1,
            ledger_tx_hash="tx",
            anchor_time=datetime.now(timezone.utc).isoformat(),
            status=AnchorStatus.PENDING,
        )
        assert anchor_pending.is_verified() is False

        anchor_verified = MemoryAnchorRecord(
            anchor_id="ANCHOR-MEM-000002",
            snapshot_id="MEM-SNAP-000002",
            state_hash="abc",
            chain_hash="def",
            ledger_block=1,
            ledger_tx_hash="tx",
            anchor_time=datetime.now(timezone.utc).isoformat(),
            status=AnchorStatus.VERIFIED,
        )
        assert anchor_verified.is_verified() is True


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY INCLUSION PROOF TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryInclusionProof:
    """Tests for MemoryInclusionProof."""

    def test_valid_proof_creation(self) -> None:
        """Test creating a valid proof."""
        proof = MemoryInclusionProof(
            proof_id="PROOF-MEM-000001",
            anchor_id="ANCHOR-MEM-000001",
            snapshot_id="MEM-SNAP-000001",
            proof_type=ProofType.MERKLE,
            proof_path=["hash1", "hash2", "hash3"],
            root_hash="root123",
        )
        assert proof.proof_id == "PROOF-MEM-000001"
        assert proof.path_length() == 3

    def test_invalid_id_raises(self) -> None:
        """Test that invalid ID format raises error."""
        with pytest.raises(ValueError):
            MemoryInclusionProof(
                proof_id="INVALID-001",
                anchor_id="ANCHOR-MEM-000001",
                snapshot_id="MEM-SNAP-000001",
                proof_type=ProofType.MERKLE,
                proof_path=[],
                root_hash="root",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PDO MEMORY BINDING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPDOMemoryBinding:
    """Tests for PDOMemoryBinding."""

    def test_valid_binding_creation(self) -> None:
        """Test creating a valid binding."""
        binding = PDOMemoryBinding(
            binding_id="PDO-MEM-000001",
            pdo_hash="pdo123",
            memory_hash="mem456",
            invariant_ids=["INV-MEM-001", "INV-MEM-002"],
            binding_time=datetime.now(timezone.utc).isoformat(),
        )
        assert binding.binding_id == "PDO-MEM-000001"
        assert binding.active is True

    def test_invalid_id_raises(self) -> None:
        """Test that invalid ID format raises error."""
        with pytest.raises(ValueError):
            PDOMemoryBinding(
                binding_id="INVALID-001",
                pdo_hash="pdo",
                memory_hash="mem",
                invariant_ids=[],
                binding_time=datetime.now(timezone.utc).isoformat(),
            )

    def test_compute_binding_hash(self) -> None:
        """Test binding hash computation."""
        binding = PDOMemoryBinding(
            binding_id="PDO-MEM-000001",
            pdo_hash="pdo123",
            memory_hash="mem456",
            invariant_ids=["INV-MEM-001"],
            binding_time=datetime.now(timezone.utc).isoformat(),
        )
        hash_value = binding.compute_binding_hash()
        assert hash_value is not None
        assert len(hash_value) == 64


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY ANCHOR SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryAnchorService:
    """Tests for MemoryAnchorService."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton between tests."""
        SnapshotRegistry._instance = None
        SnapshotRegistry._initialized = False

    def test_anchor_snapshot(self) -> None:
        """Test anchoring a snapshot."""
        service = MemoryAnchorService()
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        anchor = service.anchor_snapshot(snapshot)
        assert anchor.anchor_id.startswith("ANCHOR-MEM-")
        assert anchor.status == AnchorStatus.ANCHORED
        assert anchor.snapshot_id == snapshot.snapshot_id

    def test_verify_anchor(self) -> None:
        """Test verifying an anchor."""
        service = MemoryAnchorService()
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        anchor = service.anchor_snapshot(snapshot)
        valid, error = service.verify_anchor(anchor.anchor_id)
        assert valid is True

    def test_verify_unknown_anchor(self) -> None:
        """Test verifying unknown anchor fails."""
        service = MemoryAnchorService()
        valid, error = service.verify_anchor("ANCHOR-MEM-999999")
        assert valid is False
        assert "not found" in error.lower()

    def test_generate_proof(self) -> None:
        """Test generating inclusion proof."""
        service = MemoryAnchorService()
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        service.anchor_snapshot(snapshot)
        proof = service.generate_proof(snapshot.snapshot_id)

        assert proof is not None
        assert proof.snapshot_id == snapshot.snapshot_id
        assert len(proof.proof_path) > 0

    def test_generate_proof_unanchored(self) -> None:
        """Test generating proof for unanchored snapshot returns None."""
        service = MemoryAnchorService()
        proof = service.generate_proof("MEM-SNAP-UNKNOWN")
        assert proof is None

    def test_verify_proof(self) -> None:
        """Test verifying inclusion proof."""
        service = MemoryAnchorService()
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        service.anchor_snapshot(snapshot)
        proof = service.generate_proof(snapshot.snapshot_id)

        valid, error = service.verify_proof(proof)
        assert valid is True

    def test_create_pdo_binding(self) -> None:
        """Test creating PDO binding."""
        service = MemoryAnchorService()
        binding = service.create_pdo_binding(
            pdo_hash="pdo123",
            memory_hash="mem456",
            invariant_ids=["INV-MEM-001", "INV-MEM-003"],
        )

        assert binding.binding_id.startswith("PDO-MEM-")
        assert binding.pdo_hash == "pdo123"
        assert "INV-MEM-001" in binding.invariant_ids

    def test_verify_pdo_binding(self) -> None:
        """Test verifying PDO binding."""
        service = MemoryAnchorService()
        binding = service.create_pdo_binding(
            pdo_hash="pdo123",
            memory_hash="mem456",
            invariant_ids=["INV-MEM-001"],
        )

        valid, error = service.verify_pdo_binding(binding.binding_id, "mem456")
        assert valid is True

        valid, error = service.verify_pdo_binding(binding.binding_id, "wrong_hash")
        assert valid is False

    def test_counts(self) -> None:
        """Test count methods."""
        service = MemoryAnchorService()
        assert service.anchor_count() == 0
        assert service.proof_count() == 0
        assert service.binding_count() == 0

        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        service.anchor_snapshot(snapshot)
        assert service.anchor_count() == 1

        service.generate_proof(snapshot.snapshot_id)
        assert service.proof_count() == 1

        service.create_pdo_binding("pdo", "mem", [])
        assert service.binding_count() == 1


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY CHAIN VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryChainValidator:
    """Tests for MemoryChainValidator."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton between tests."""
        SnapshotRegistry._instance = None
        SnapshotRegistry._initialized = False

    def test_validate_empty_chain(self) -> None:
        """Test validating empty chain passes."""
        registry = SnapshotRegistry()
        service = MemoryAnchorService(registry)
        validator = MemoryChainValidator(registry, service)

        valid, errors = validator.validate_chain()
        assert valid is True
        assert len(errors) == 0

    def test_validate_chain_with_anchors(self) -> None:
        """Test validating chain with anchored snapshots."""
        registry = SnapshotRegistry()
        service = MemoryAnchorService(registry)
        validator = MemoryChainValidator(registry, service)

        # Create and anchor snapshots
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot1 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        registry.register(snapshot1)
        service.anchor_snapshot(snapshot1)

        valid, errors = validator.validate_chain()
        assert valid is True

    def test_validate_snapshot(self) -> None:
        """Test validating specific snapshot."""
        registry = SnapshotRegistry()
        service = MemoryAnchorService(registry)
        validator = MemoryChainValidator(registry, service)

        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        registry.register(snapshot)
        service.anchor_snapshot(snapshot)

        valid, error = validator.validate_snapshot(snapshot.snapshot_id)
        assert valid is True

    def test_validate_unknown_snapshot(self) -> None:
        """Test validating unknown snapshot fails."""
        registry = SnapshotRegistry()
        service = MemoryAnchorService(registry)
        validator = MemoryChainValidator(registry, service)

        valid, error = validator.validate_snapshot("MEM-SNAP-UNKNOWN")
        assert valid is False
        assert "not found" in error.lower()
