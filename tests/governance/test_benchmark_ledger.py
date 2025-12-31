# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite — Benchmark Ledger Tests
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for core/governance/benchmark_ledger.py

Coverage:
- AnchorStatus, ChainIntegrity, ProofType enums
- BenchmarkAnchor
- BenchmarkChain
- BenchmarkInclusionProof
- PDOBenchmarkBinding
- BenchmarkLedgerService
"""

import pytest

from core.governance.benchmark_ledger import (
    AnchorStatus,
    BenchmarkAnchor,
    BenchmarkChain,
    BenchmarkInclusionProof,
    BenchmarkLedgerService,
    ChainIntegrity,
    PDOBenchmarkBinding,
    ProofType,
)


class TestEnums:
    """Tests for ledger enums."""

    def test_anchor_status_values(self) -> None:
        """Test AnchorStatus values."""
        assert AnchorStatus.PENDING.value == "PENDING"
        assert AnchorStatus.ANCHORED.value == "ANCHORED"
        assert AnchorStatus.VERIFIED.value == "VERIFIED"

    def test_chain_integrity_values(self) -> None:
        """Test ChainIntegrity values."""
        assert ChainIntegrity.VALID.value == "VALID"
        assert ChainIntegrity.INVALID.value == "INVALID"
        assert ChainIntegrity.UNKNOWN.value == "UNKNOWN"

    def test_proof_type_values(self) -> None:
        """Test ProofType values."""
        assert ProofType.MERKLE.value == "MERKLE"
        assert ProofType.CHAIN.value == "CHAIN"


class TestBenchmarkAnchor:
    """Tests for BenchmarkAnchor."""

    def test_valid_anchor_creation(self) -> None:
        """Test valid anchor creation."""
        anchor = BenchmarkAnchor(
            anchor_id="ANCHOR-00000001",
            benchmark_id="BENCH-001",
            content_hash="abc123",
            previous_hash="0" * 64,
            sequence=0,
            timestamp="2025-01-01T00:00:00Z",
        )

        assert anchor.anchor_id == "ANCHOR-00000001"
        assert anchor.benchmark_id == "BENCH-001"
        assert anchor.status == AnchorStatus.PENDING

    def test_invalid_anchor_id(self) -> None:
        """Test invalid anchor ID."""
        with pytest.raises(ValueError, match="must start with 'ANCHOR-'"):
            BenchmarkAnchor(
                anchor_id="INVALID",
                benchmark_id="BENCH-001",
                content_hash="abc123",
                previous_hash="0" * 64,
                sequence=0,
                timestamp="2025-01-01T00:00:00Z",
            )

    def test_anchor_hash_computation(self) -> None:
        """Test anchor hash is computed."""
        anchor = BenchmarkAnchor(
            anchor_id="ANCHOR-00000001",
            benchmark_id="BENCH-001",
            content_hash="abc123",
            previous_hash="0" * 64,
            sequence=0,
            timestamp="2025-01-01T00:00:00Z",
        )

        computed_hash = anchor.compute_anchor_hash()
        assert computed_hash is not None
        assert len(computed_hash) == 64  # SHA-256 hex

    def test_anchor_hash_determinism(self) -> None:
        """Test anchor hash is deterministic."""
        anchor = BenchmarkAnchor(
            anchor_id="ANCHOR-00000001",
            benchmark_id="BENCH-001",
            content_hash="abc123",
            previous_hash="0" * 64,
            sequence=0,
            timestamp="2025-01-01T00:00:00Z",
        )

        # Same anchor's hash should be stable
        hash1 = anchor.compute_anchor_hash()
        hash2 = anchor.compute_anchor_hash()
        assert hash1 == hash2

    def test_anchor_to_dict(self) -> None:
        """Test anchor serialization."""
        anchor = BenchmarkAnchor(
            anchor_id="ANCHOR-00000001",
            benchmark_id="BENCH-001",
            content_hash="abc123",
            previous_hash="0" * 64,
            sequence=0,
            timestamp="2025-01-01T00:00:00Z",
        )

        data = anchor.to_dict()

        assert data["anchor_id"] == "ANCHOR-00000001"
        assert data["status"] == "PENDING"
        assert "anchor_hash" in data

    def test_verify_chain_link_genesis(self) -> None:
        """Test genesis anchor link verification."""
        anchor = BenchmarkAnchor(
            anchor_id="ANCHOR-00000000",
            benchmark_id="BENCH-001",
            content_hash="abc123",
            previous_hash="0" * 64,
            sequence=0,
            timestamp="2025-01-01T00:00:00Z",
        )

        assert anchor.verify_chain_link(None) is True


class TestBenchmarkChain:
    """Tests for BenchmarkChain."""

    def test_valid_chain_creation(self) -> None:
        """Test valid chain creation."""
        chain = BenchmarkChain(chain_id="CHAIN-001")

        assert chain.chain_id == "CHAIN-001"
        assert chain.length == 0
        assert chain.integrity == ChainIntegrity.UNKNOWN

    def test_invalid_chain_id(self) -> None:
        """Test invalid chain ID."""
        with pytest.raises(ValueError, match="must start with 'CHAIN-'"):
            BenchmarkChain(chain_id="INVALID")

    def test_append_anchor(self) -> None:
        """Test appending anchors via chain.append."""
        chain = BenchmarkChain(chain_id="CHAIN-001")

        anchor = chain.append("BENCH-001", "abc123")

        assert chain.length == 1
        assert anchor.status == AnchorStatus.ANCHORED

    def test_chain_linking(self) -> None:
        """Test chain links anchors."""
        chain = BenchmarkChain(chain_id="CHAIN-001")

        anchor1 = chain.append("BENCH-001", "abc123")
        anchor2 = chain.append("BENCH-002", "def456")

        assert anchor2.previous_hash == anchor1.compute_anchor_hash()

    def test_verify_integrity_valid(self) -> None:
        """Test integrity verification passes."""
        chain = BenchmarkChain(chain_id="CHAIN-001")

        for i in range(3):
            chain.append(f"BENCH-{i:03d}", f"hash{i}")

        integrity, invalid_seq = chain.verify_integrity()
        assert integrity == ChainIntegrity.VALID
        assert invalid_seq is None

    def test_get_by_id(self) -> None:
        """Test getting anchor by ID."""
        chain = BenchmarkChain(chain_id="CHAIN-001")

        anchor = chain.append("BENCH-001", "abc123")

        retrieved = chain.get_by_id(anchor.anchor_id)
        assert retrieved is not None
        assert retrieved.anchor_id == anchor.anchor_id

    def test_get_by_id_not_found(self) -> None:
        """Test getting nonexistent anchor."""
        chain = BenchmarkChain(chain_id="CHAIN-001")
        assert chain.get_by_id("ANCHOR-XXX") is None

    def test_get_by_sequence(self) -> None:
        """Test getting anchor by sequence."""
        chain = BenchmarkChain(chain_id="CHAIN-001")
        chain.append("BENCH-001", "abc123")
        chain.append("BENCH-002", "def456")

        anchor = chain.get_by_sequence(1)
        assert anchor is not None
        assert anchor.benchmark_id == "BENCH-002"

    def test_chain_to_dict(self) -> None:
        """Test chain serialization."""
        chain = BenchmarkChain(chain_id="CHAIN-001")

        data = chain.to_dict()

        assert data["chain_id"] == "CHAIN-001"
        assert data["length"] == 0
        assert "chain_hash" in data


class TestBenchmarkInclusionProof:
    """Tests for BenchmarkInclusionProof."""

    def test_valid_proof_creation(self) -> None:
        """Test valid proof creation."""
        proof = BenchmarkInclusionProof(
            proof_id="PROOF-000001",
            anchor_id="ANCHOR-001",
            benchmark_id="BENCH-001",
            proof_type=ProofType.CHAIN,
            chain_hashes=["abc123"],
            root_hash="def456",
            anchor_sequence=0,
            tip_sequence=0,
            created_at="2025-01-01T00:00:00Z",
        )

        assert proof.proof_id == "PROOF-000001"
        assert not proof.verified

    def test_invalid_proof_id(self) -> None:
        """Test invalid proof ID."""
        with pytest.raises(ValueError, match="must start with 'PROOF-'"):
            BenchmarkInclusionProof(
                proof_id="INVALID",
                anchor_id="ANCHOR-001",
                benchmark_id="BENCH-001",
                proof_type=ProofType.CHAIN,
                chain_hashes=[],
                root_hash="abc",
                anchor_sequence=0,
                tip_sequence=0,
                created_at="2025-01-01T00:00:00Z",
            )

    def test_proof_to_dict(self) -> None:
        """Test proof serialization."""
        proof = BenchmarkInclusionProof(
            proof_id="PROOF-000001",
            anchor_id="ANCHOR-001",
            benchmark_id="BENCH-001",
            proof_type=ProofType.MERKLE,
            chain_hashes=["abc123"],
            root_hash="def456",
            anchor_sequence=0,
            tip_sequence=0,
            created_at="2025-01-01T00:00:00Z",
        )

        data = proof.to_dict()

        assert data["proof_id"] == "PROOF-000001"
        assert data["proof_type"] == "MERKLE"


class TestPDOBenchmarkBinding:
    """Tests for PDOBenchmarkBinding."""

    def test_valid_binding_creation_via_factory(self) -> None:
        """Test valid binding creation via factory."""
        binding = PDOBenchmarkBinding.create(
            anchor_id="ANCHOR-001",
            pdo_id="PDO-001",
        )

        assert binding.binding_id.startswith("BIND-")
        assert binding.pdo_id == "PDO-001"
        assert binding.anchor_id == "ANCHOR-001"

    def test_invalid_binding_id(self) -> None:
        """Test invalid binding ID."""
        with pytest.raises(ValueError, match="must start with 'BIND-'"):
            PDOBenchmarkBinding(
                binding_id="INVALID",
                anchor_id="ANCHOR-001",
                pdo_id="PDO-001",
                binding_hash="abc123",
                created_at="2025-01-01T00:00:00Z",
            )

    def test_binding_to_dict(self) -> None:
        """Test binding serialization."""
        binding = PDOBenchmarkBinding.create(
            anchor_id="ANCHOR-001",
            pdo_id="PDO-001",
        )

        data = binding.to_dict()

        assert data["pdo_id"] == "PDO-001"
        assert data["anchor_id"] == "ANCHOR-001"
        assert "binding_hash" in data


class TestBenchmarkLedgerService:
    """Tests for BenchmarkLedgerService."""

    @pytest.fixture
    def service(self) -> BenchmarkLedgerService:
        """Create a fresh ledger service."""
        return BenchmarkLedgerService()

    def test_service_creation(self, service: BenchmarkLedgerService) -> None:
        """Test service creation."""
        assert service is not None
        assert service.chain is not None

    def test_anchor_benchmark(self, service: BenchmarkLedgerService) -> None:
        """Test anchoring a benchmark."""
        anchor = service.anchor_benchmark("BENCH-001", {"result": "hash-123"})

        assert anchor is not None
        assert anchor.status == AnchorStatus.ANCHORED
        assert service.chain.length == 1

    def test_get_anchor_by_id(self, service: BenchmarkLedgerService) -> None:
        """Test retrieving anchor."""
        service.anchor_benchmark("BENCH-001", {"hash": "1"})
        anchor = service.anchor_benchmark("BENCH-002", {"hash": "2"})

        retrieved = service.chain.get_by_id(anchor.anchor_id)

        assert retrieved is not None
        assert retrieved.benchmark_id == "BENCH-002"

    def test_generate_proof(self, service: BenchmarkLedgerService) -> None:
        """Test proof generation."""
        anchor = service.anchor_benchmark("BENCH-001", {"hash": "1"})

        proof = service.generate_proof(anchor.anchor_id)

        assert proof is not None
        assert proof.anchor_id == anchor.anchor_id

    def test_verify_proof(self, service: BenchmarkLedgerService) -> None:
        """Test proof verification."""
        anchor = service.anchor_benchmark("BENCH-001", {"hash": "1"})
        proof = service.generate_proof(anchor.anchor_id)

        is_valid = service.verify_proof(proof.proof_id)

        assert is_valid
        assert proof.verified

    def test_create_pdo_binding(self, service: BenchmarkLedgerService) -> None:
        """Test binding anchor to PDO."""
        anchor = service.anchor_benchmark("BENCH-001", {"hash": "1"})

        binding = service.create_pdo_binding(anchor.anchor_id, "PDO-001")

        assert binding is not None
        assert binding.pdo_id == "PDO-001"

    def test_get_bindings_for_anchor(self, service: BenchmarkLedgerService) -> None:
        """Test getting bindings for anchor."""
        anchor = service.anchor_benchmark("BENCH-001", {"hash": "1"})

        service.create_pdo_binding(anchor.anchor_id, "PDO-001")
        service.create_pdo_binding(anchor.anchor_id, "PDO-002")

        bindings = service.get_bindings_for_anchor(anchor.anchor_id)

        assert len(bindings) == 2

    def test_verify_chain_integrity(self, service: BenchmarkLedgerService) -> None:
        """Test chain integrity verification."""
        service.anchor_benchmark("BENCH-001", {"hash": "1"})
        service.anchor_benchmark("BENCH-002", {"hash": "2"})
        service.anchor_benchmark("BENCH-003", {"hash": "3"})

        integrity, invalid_seq = service.verify_chain()

        assert integrity == ChainIntegrity.VALID
        assert invalid_seq is None

    def test_generate_report(self, service: BenchmarkLedgerService) -> None:
        """Test service report generation."""
        service.anchor_benchmark("BENCH-001", {"hash": "1"})

        report = service.generate_report()

        assert report["chain"]["chain_id"] == service.chain.chain_id
        assert report["chain"]["length"] == 1
        assert report["chain"]["integrity"] == "VALID"


class TestLedgerIntegration:
    """Integration tests for ledger system."""

    def test_full_anchor_and_proof_workflow(self) -> None:
        """Test complete anchoring workflow."""
        service = BenchmarkLedgerService()

        # Anchor multiple benchmarks
        anchors = []
        for i in range(5):
            anchor = service.anchor_benchmark(f"BENCH-{i:03d}", {"result": f"hash{i}"})
            anchors.append(anchor)

        # Verify chain integrity
        integrity, _ = service.verify_chain()
        assert integrity == ChainIntegrity.VALID

        # Generate and verify proofs
        for anchor in anchors:
            proof = service.generate_proof(anchor.anchor_id)
            assert proof is not None
            assert service.verify_proof(proof.proof_id)

    def test_pdo_binding_workflow(self) -> None:
        """Test PDO binding workflow."""
        service = BenchmarkLedgerService()

        # Anchor and bind
        anchor = service.anchor_benchmark("BENCH-001", {"hash": "1"})
        binding = service.create_pdo_binding(anchor.anchor_id, "PDO-TRUST-001")

        # Verify binding
        assert binding is not None
        assert binding.pdo_id == "PDO-TRUST-001"

        # Get bindings
        bindings = service.get_bindings_for_anchor(anchor.anchor_id)
        assert len(bindings) == 1
        assert bindings[0].binding_id == binding.binding_id

    def test_multi_anchor_scenario(self) -> None:
        """Test service with multiple anchors."""
        service = BenchmarkLedgerService()

        # Current service has single chain
        initial_chain_id = service.chain.chain_id

        # Add anchors
        service.anchor_benchmark("BENCH-001", {"hash": "1"})
        service.anchor_benchmark("BENCH-002", {"hash": "2"})

        # Chain should be same
        assert service.chain.chain_id == initial_chain_id
        assert service.chain.length == 2
