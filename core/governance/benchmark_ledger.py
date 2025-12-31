# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Ledger — Anchoring Benchmark Results to Immutable Ledger
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: ATLAS (GID-11)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benchmark Ledger — Immutable Benchmark Result Anchoring

PURPOSE:
    Provide tamper-evident storage for benchmark results by:
    - Anchoring results to a hash chain
    - Creating inclusion proofs for verification
    - Binding results to PDO (Proofpack Data Objects)
    - Enabling forensic audit of benchmark history

COMPONENTS:
    1. BenchmarkAnchor - Single anchored result
    2. BenchmarkChain - Hash chain of anchors
    3. BenchmarkInclusionProof - Merkle-style proof
    4. BenchmarkLedgerService - Central ledger service
    5. PDOBenchmarkBinding - Binding to proofpack

CONSTRAINTS:
    - Append-only ledger
    - Hash chain integrity required
    - No retroactive modifications
    - Shadow mode safe

LANE: EXECUTION (INTEGRITY)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class AnchorStatus(Enum):
    """Status of an anchor in the ledger."""

    PENDING = "PENDING"  # Not yet confirmed
    ANCHORED = "ANCHORED"  # In ledger
    VERIFIED = "VERIFIED"  # Verified by proof


class ChainIntegrity(Enum):
    """Integrity status of the chain."""

    VALID = "VALID"  # All hashes match
    INVALID = "INVALID"  # Chain broken
    UNKNOWN = "UNKNOWN"  # Not yet checked


class ProofType(Enum):
    """Type of inclusion proof."""

    MERKLE = "MERKLE"  # Merkle tree proof
    CHAIN = "CHAIN"  # Sequential chain proof


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK ANCHOR
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BenchmarkAnchor:
    """
    Single anchored benchmark result.

    Represents a benchmark result bound to the ledger with:
    - Content hash
    - Previous anchor reference
    - Timestamp
    - Sequence number
    """

    anchor_id: str
    benchmark_id: str
    content_hash: str
    previous_hash: str
    sequence: int
    timestamp: str
    status: AnchorStatus = AnchorStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.anchor_id.startswith("ANCHOR-"):
            raise ValueError(f"Anchor ID must start with 'ANCHOR-': {self.anchor_id}")

    def compute_anchor_hash(self) -> str:
        """Compute hash of this anchor."""
        data = {
            "anchor_id": self.anchor_id,
            "benchmark_id": self.benchmark_id,
            "content_hash": self.content_hash,
            "previous_hash": self.previous_hash,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def verify_chain_link(self, previous_anchor: Optional["BenchmarkAnchor"]) -> bool:
        """Verify this anchor links correctly to previous."""
        if previous_anchor is None:
            # Genesis anchor - previous should be zero hash
            return self.previous_hash == "0" * 64

        return self.previous_hash == previous_anchor.compute_anchor_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "benchmark_id": self.benchmark_id,
            "content_hash": self.content_hash,
            "previous_hash": self.previous_hash,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "anchor_hash": self.compute_anchor_hash(),
            "metadata": self.metadata,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INCLUSION PROOF
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BenchmarkInclusionProof:
    """
    Proof that a benchmark result is included in the ledger.

    Provides verifiable evidence that:
    - Result exists in the chain
    - Position is correct
    - Hash chain is intact from anchor to tip
    """

    proof_id: str
    anchor_id: str
    benchmark_id: str
    proof_type: ProofType
    chain_hashes: List[str]
    root_hash: str
    anchor_sequence: int
    tip_sequence: int
    created_at: str
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.proof_id.startswith("PROOF-"):
            raise ValueError(f"Proof ID must start with 'PROOF-': {self.proof_id}")

    def verify(self, chain: "BenchmarkChain") -> bool:
        """Verify this proof against the chain."""
        if self.anchor_sequence > self.tip_sequence:
            return False

        if self.anchor_sequence >= len(chain.anchors):
            return False

        # Verify chain hashes match
        for i, expected_hash in enumerate(self.chain_hashes):
            seq = self.anchor_sequence + i
            if seq >= len(chain.anchors):
                return False
            actual_hash = chain.anchors[seq].compute_anchor_hash()
            if actual_hash != expected_hash:
                return False

        self.verified = True
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "anchor_id": self.anchor_id,
            "benchmark_id": self.benchmark_id,
            "proof_type": self.proof_type.value,
            "chain_hashes": self.chain_hashes,
            "root_hash": self.root_hash,
            "anchor_sequence": self.anchor_sequence,
            "tip_sequence": self.tip_sequence,
            "created_at": self.created_at,
            "verified": self.verified,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PDO BINDING
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PDOBenchmarkBinding:
    """
    Binding between a benchmark anchor and a Proofpack Data Object.

    Links benchmark results to the broader proofpack system for:
    - Audit trail integration
    - Cross-service verification
    - Governance compliance
    """

    binding_id: str
    anchor_id: str
    pdo_id: str
    binding_hash: str
    created_at: str
    verification_uri: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.binding_id.startswith("BIND-"):
            raise ValueError(f"Binding ID must start with 'BIND-': {self.binding_id}")

    @classmethod
    def create(cls, anchor_id: str, pdo_id: str) -> "PDOBenchmarkBinding":
        """Create a new PDO binding."""
        binding_data = {
            "anchor_id": anchor_id,
            "pdo_id": pdo_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        binding_hash = hashlib.sha256(json.dumps(binding_data, sort_keys=True).encode()).hexdigest()

        return cls(
            binding_id=f"BIND-{binding_hash[:12].upper()}",
            anchor_id=anchor_id,
            pdo_id=pdo_id,
            binding_hash=binding_hash,
            created_at=binding_data["timestamp"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "anchor_id": self.anchor_id,
            "pdo_id": self.pdo_id,
            "binding_hash": self.binding_hash,
            "created_at": self.created_at,
            "verification_uri": self.verification_uri,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK CHAIN
# ═══════════════════════════════════════════════════════════════════════════════


class BenchmarkChain:
    """
    Hash chain of benchmark anchors.

    Provides:
    - Append-only storage
    - Chain integrity verification
    - Anchor lookup by sequence or ID
    """

    def __init__(self, chain_id: str = "CHAIN-BENCH-001") -> None:
        if not chain_id.startswith("CHAIN-"):
            raise ValueError(f"Chain ID must start with 'CHAIN-': {chain_id}")

        self._chain_id = chain_id
        self._anchors: List[BenchmarkAnchor] = []
        self._anchor_index: Dict[str, int] = {}  # anchor_id -> sequence
        self._benchmark_index: Dict[str, List[int]] = {}  # benchmark_id -> sequences
        self._integrity = ChainIntegrity.UNKNOWN

    @property
    def chain_id(self) -> str:
        return self._chain_id

    @property
    def anchors(self) -> List[BenchmarkAnchor]:
        return self._anchors.copy()

    @property
    def length(self) -> int:
        return len(self._anchors)

    @property
    def tip_hash(self) -> str:
        """Get hash of the tip (latest anchor)."""
        if not self._anchors:
            return "0" * 64
        return self._anchors[-1].compute_anchor_hash()

    @property
    def integrity(self) -> ChainIntegrity:
        return self._integrity

    def append(self, benchmark_id: str, content_hash: str, metadata: Optional[Dict[str, Any]] = None) -> BenchmarkAnchor:
        """Append a new anchor to the chain."""
        sequence = len(self._anchors)
        previous_hash = self.tip_hash

        anchor = BenchmarkAnchor(
            anchor_id=f"ANCHOR-{sequence:08d}",
            benchmark_id=benchmark_id,
            content_hash=content_hash,
            previous_hash=previous_hash,
            sequence=sequence,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=AnchorStatus.ANCHORED,
            metadata=metadata or {},
        )

        self._anchors.append(anchor)
        self._anchor_index[anchor.anchor_id] = sequence

        if benchmark_id not in self._benchmark_index:
            self._benchmark_index[benchmark_id] = []
        self._benchmark_index[benchmark_id].append(sequence)

        # Mark integrity unknown after modification
        self._integrity = ChainIntegrity.UNKNOWN

        return anchor

    def get_by_sequence(self, sequence: int) -> Optional[BenchmarkAnchor]:
        """Get anchor by sequence number."""
        if 0 <= sequence < len(self._anchors):
            return self._anchors[sequence]
        return None

    def get_by_id(self, anchor_id: str) -> Optional[BenchmarkAnchor]:
        """Get anchor by ID."""
        sequence = self._anchor_index.get(anchor_id)
        if sequence is not None:
            return self._anchors[sequence]
        return None

    def get_by_benchmark(self, benchmark_id: str) -> List[BenchmarkAnchor]:
        """Get all anchors for a benchmark ID."""
        sequences = self._benchmark_index.get(benchmark_id, [])
        return [self._anchors[seq] for seq in sequences]

    def verify_integrity(self) -> Tuple[ChainIntegrity, Optional[int]]:
        """
        Verify chain integrity.

        Returns:
            Tuple of (integrity status, first invalid sequence or None)
        """
        if not self._anchors:
            self._integrity = ChainIntegrity.VALID
            return (ChainIntegrity.VALID, None)

        # Check genesis anchor
        if self._anchors[0].previous_hash != "0" * 64:
            self._integrity = ChainIntegrity.INVALID
            return (ChainIntegrity.INVALID, 0)

        # Check chain links
        for i in range(1, len(self._anchors)):
            current = self._anchors[i]
            previous = self._anchors[i - 1]

            if not current.verify_chain_link(previous):
                self._integrity = ChainIntegrity.INVALID
                return (ChainIntegrity.INVALID, i)

        self._integrity = ChainIntegrity.VALID
        return (ChainIntegrity.VALID, None)

    def compute_chain_hash(self) -> str:
        """Compute hash of entire chain state."""
        if not self._anchors:
            return hashlib.sha256(b"empty_chain").hexdigest()

        all_hashes = [a.compute_anchor_hash() for a in self._anchors]
        combined = "|".join(all_hashes)
        return hashlib.sha256(combined.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self._chain_id,
            "length": len(self._anchors),
            "tip_hash": self.tip_hash,
            "integrity": self._integrity.value,
            "chain_hash": self.compute_chain_hash(),
            "anchors": [a.to_dict() for a in self._anchors],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class BenchmarkLedgerService:
    """
    Central service for benchmark ledger operations.

    Provides:
    - Anchor creation and storage
    - Proof generation
    - PDO binding
    - Chain management
    """

    def __init__(self) -> None:
        self._chain = BenchmarkChain()
        self._proofs: Dict[str, BenchmarkInclusionProof] = {}
        self._bindings: Dict[str, PDOBenchmarkBinding] = {}
        self._proof_counter = 0

    @property
    def chain(self) -> BenchmarkChain:
        return self._chain

    def anchor_benchmark(
        self,
        benchmark_id: str,
        result_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkAnchor:
        """Anchor a benchmark result to the ledger."""
        content_hash = hashlib.sha256(json.dumps(result_data, sort_keys=True, default=str).encode()).hexdigest()
        return self._chain.append(benchmark_id, content_hash, metadata)

    def generate_proof(self, anchor_id: str) -> Optional[BenchmarkInclusionProof]:
        """Generate an inclusion proof for an anchor."""
        anchor = self._chain.get_by_id(anchor_id)
        if anchor is None:
            return None

        self._proof_counter += 1
        proof_id = f"PROOF-{self._proof_counter:06d}"

        # Collect chain hashes from anchor to tip
        chain_hashes = []
        for i in range(anchor.sequence, self._chain.length):
            chain_hashes.append(self._chain.anchors[i].compute_anchor_hash())

        proof = BenchmarkInclusionProof(
            proof_id=proof_id,
            anchor_id=anchor_id,
            benchmark_id=anchor.benchmark_id,
            proof_type=ProofType.CHAIN,
            chain_hashes=chain_hashes,
            root_hash=self._chain.tip_hash,
            anchor_sequence=anchor.sequence,
            tip_sequence=self._chain.length - 1,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._proofs[proof_id] = proof
        return proof

    def verify_proof(self, proof_id: str) -> bool:
        """Verify an inclusion proof."""
        proof = self._proofs.get(proof_id)
        if proof is None:
            return False
        return proof.verify(self._chain)

    def create_pdo_binding(self, anchor_id: str, pdo_id: str) -> Optional[PDOBenchmarkBinding]:
        """Create a binding between anchor and PDO."""
        anchor = self._chain.get_by_id(anchor_id)
        if anchor is None:
            return None

        binding = PDOBenchmarkBinding.create(anchor_id, pdo_id)
        self._bindings[binding.binding_id] = binding
        return binding

    def get_binding(self, binding_id: str) -> Optional[PDOBenchmarkBinding]:
        """Get a PDO binding by ID."""
        return self._bindings.get(binding_id)

    def get_bindings_for_anchor(self, anchor_id: str) -> List[PDOBenchmarkBinding]:
        """Get all bindings for an anchor."""
        return [b for b in self._bindings.values() if b.anchor_id == anchor_id]

    def verify_chain(self) -> Tuple[ChainIntegrity, Optional[int]]:
        """Verify chain integrity."""
        return self._chain.verify_integrity()

    def generate_report(self) -> Dict[str, Any]:
        """Generate ledger service report."""
        integrity, invalid_seq = self._chain.verify_integrity()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chain": {
                "chain_id": self._chain.chain_id,
                "length": self._chain.length,
                "tip_hash": self._chain.tip_hash,
                "integrity": integrity.value,
                "invalid_sequence": invalid_seq,
                "chain_hash": self._chain.compute_chain_hash(),
            },
            "proofs": {
                "count": len(self._proofs),
                "verified_count": sum(1 for p in self._proofs.values() if p.verified),
            },
            "bindings": {
                "count": len(self._bindings),
            },
            "statistics": {
                "benchmarks_anchored": len(set(a.benchmark_id for a in self._chain.anchors)),
                "total_anchors": self._chain.length,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "AnchorStatus",
    "ChainIntegrity",
    "ProofType",
    # Data classes
    "BenchmarkAnchor",
    "BenchmarkInclusionProof",
    "PDOBenchmarkBinding",
    # Chain
    "BenchmarkChain",
    # Service
    "BenchmarkLedgerService",
]
