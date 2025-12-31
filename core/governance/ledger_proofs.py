# ═══════════════════════════════════════════════════════════════════════════════
# Ledger Integrity Proofs — Enhanced Ordering and Verification
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: ATLAS (GID-11) — Ledger & Integrity
# ═══════════════════════════════════════════════════════════════════════════════

"""
Ledger Integrity Proofs — Enterprise Verification System

PURPOSE:
    Provide cryptographic integrity proofs for ledger entries including
    Merkle proofs, audit checkpoints, and tamper detection.

FEATURES:
    - Merkle tree construction and proof generation
    - Chain integrity verification
    - Audit checkpoint creation and verification
    - Inclusion proofs for individual entries

INVARIANTS:
    INV-LEDGER-PROOF-001: All entries must have valid inclusion proofs
    INV-LEDGER-PROOF-002: Checkpoint hashes must match computed values
    INV-LEDGER-PROOF-003: Chain links must be cryptographically valid
    INV-LEDGER-PROOF-004: Proof verification must be deterministic
    INV-LEDGER-PROOF-005: Audit trail must be append-only

EXECUTION MODE: PARALLEL
LANE: INTEGRITY (GID-11)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# PROOF TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class ProofType(Enum):
    """Types of integrity proofs."""

    MERKLE_INCLUSION = "MERKLE_INCLUSION"  # Entry is in Merkle tree
    CHAIN_LINK = "CHAIN_LINK"  # Entry links to previous
    CHECKPOINT = "CHECKPOINT"  # Checkpoint verification
    RANGE = "RANGE"  # Range of entries proof
    CONSISTENCY = "CONSISTENCY"  # Tree consistency proof


class VerificationStatus(Enum):
    """Status of proof verification."""

    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"
    ERROR = "ERROR"


# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════


def compute_sha256(data: str) -> str:
    """Compute SHA256 hash of string data."""
    return hashlib.sha256(data.encode()).hexdigest()


def compute_node_hash(left: str, right: str) -> str:
    """Compute hash of two child nodes."""
    combined = left + right
    return compute_sha256(combined)


@dataclass(frozen=True)
class MerkleNode:
    """Node in the Merkle tree."""

    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None
    leaf_index: Optional[int] = None  # Only for leaf nodes

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


@dataclass(frozen=True)
class MerkleProof:
    """
    Proof of inclusion in a Merkle tree.

    Contains the path from leaf to root with sibling hashes.
    """

    leaf_hash: str
    leaf_index: int
    path: tuple[tuple[str, str], ...]  # (hash, direction) pairs
    root_hash: str
    tree_size: int

    def verify(self, leaf_data: str) -> bool:
        """
        Verify that leaf_data is included in the tree.

        INV-LEDGER-PROOF-004: Proof verification must be deterministic
        """
        computed_hash = compute_sha256(leaf_data)
        if computed_hash != self.leaf_hash:
            return False

        current = computed_hash
        for sibling_hash, direction in self.path:
            if direction == "L":
                current = compute_node_hash(sibling_hash, current)
            else:  # direction == "R"
                current = compute_node_hash(current, sibling_hash)

        return current == self.root_hash


class MerkleTree:
    """
    Merkle tree for ledger entries.

    Provides efficient inclusion proofs and tamper detection.
    """

    def __init__(self) -> None:
        self._leaves: List[str] = []
        self._root: Optional[MerkleNode] = None

    def add_leaf(self, data: str) -> int:
        """
        Add a leaf to the tree.

        Returns the leaf index.
        """
        leaf_hash = compute_sha256(data)
        self._leaves.append(leaf_hash)
        self._rebuild_tree()
        return len(self._leaves) - 1

    def _rebuild_tree(self) -> None:
        """Rebuild the tree from leaves."""
        if not self._leaves:
            self._root = None
            return

        # Create leaf nodes
        nodes: List[MerkleNode] = [
            MerkleNode(hash=h, leaf_index=i)
            for i, h in enumerate(self._leaves)
        ]

        # Pad to power of 2 if needed
        while len(nodes) > 1 and (len(nodes) & (len(nodes) - 1)) != 0:
            nodes.append(MerkleNode(hash=nodes[-1].hash))

        # Build tree bottom-up
        while len(nodes) > 1:
            next_level: List[MerkleNode] = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                parent_hash = compute_node_hash(left.hash, right.hash)
                next_level.append(MerkleNode(hash=parent_hash, left=left, right=right))
            nodes = next_level

        self._root = nodes[0] if nodes else None

    @property
    def root_hash(self) -> Optional[str]:
        """Get the root hash of the tree."""
        return self._root.hash if self._root else None

    @property
    def size(self) -> int:
        """Get the number of leaves."""
        return len(self._leaves)

    def get_proof(self, index: int) -> Optional[MerkleProof]:
        """
        Get inclusion proof for leaf at index.

        INV-LEDGER-PROOF-001: All entries must have valid inclusion proofs
        """
        if index < 0 or index >= len(self._leaves):
            return None

        if self._root is None:
            return None

        path: List[Tuple[str, str]] = []
        self._collect_path(self._root, index, len(self._leaves), path)

        return MerkleProof(
            leaf_hash=self._leaves[index],
            leaf_index=index,
            path=tuple(path),
            root_hash=self._root.hash,
            tree_size=len(self._leaves),
        )

    def _collect_path(
        self,
        node: MerkleNode,
        target_index: int,
        subtree_size: int,
        path: List[Tuple[str, str]],
    ) -> bool:
        """Recursively collect proof path."""
        if node.is_leaf:
            return node.leaf_index == target_index

        if node.left is None or node.right is None:
            return False

        left_size = subtree_size // 2

        if target_index < left_size:
            # Target is in left subtree
            if self._collect_path(node.left, target_index, left_size, path):
                path.append((node.right.hash, "R"))
                return True
        else:
            # Target is in right subtree
            if self._collect_path(node.right, target_index - left_size, subtree_size - left_size, path):
                path.append((node.left.hash, "L"))
                return True

        return False

    def verify_proof(self, proof: MerkleProof, leaf_data: str) -> bool:
        """Verify an inclusion proof."""
        return proof.verify(leaf_data)


# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN LINK PROOFS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ChainLinkProof:
    """
    Proof that an entry links to its predecessor.

    INV-LEDGER-PROOF-003: Chain links must be cryptographically valid
    """

    entry_sequence: int
    entry_hash: str
    prev_sequence: int
    prev_hash: str
    link_valid: bool

    @classmethod
    def create(
        cls,
        entry_sequence: int,
        entry_hash: str,
        prev_sequence: int,
        prev_hash: str,
        expected_prev_hash: str,
    ) -> "ChainLinkProof":
        """Create a chain link proof."""
        link_valid = prev_hash == expected_prev_hash
        return cls(
            entry_sequence=entry_sequence,
            entry_hash=entry_hash,
            prev_sequence=prev_sequence,
            prev_hash=prev_hash,
            link_valid=link_valid,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT PROOFS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CheckpointProof:
    """
    Proof of checkpoint integrity.

    INV-LEDGER-PROOF-002: Checkpoint hashes must match computed values
    """

    checkpoint_id: str
    checkpoint_sequence: int
    merkle_root: str
    entry_count: int
    computed_root: str
    valid: bool
    created_at: datetime

    @classmethod
    def verify_checkpoint(
        cls,
        checkpoint_id: str,
        checkpoint_sequence: int,
        claimed_root: str,
        entry_count: int,
        tree: MerkleTree,
    ) -> "CheckpointProof":
        """Verify a checkpoint against the Merkle tree."""
        computed_root = tree.root_hash or ""
        valid = (
            computed_root == claimed_root
            and tree.size == entry_count
        )

        return cls(
            checkpoint_id=checkpoint_id,
            checkpoint_sequence=checkpoint_sequence,
            merkle_root=claimed_root,
            entry_count=entry_count,
            computed_root=computed_root,
            valid=valid,
            created_at=datetime.now(timezone.utc),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRITY PROOF SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class EntryProofBundle:
    """Complete proof bundle for a ledger entry."""

    entry_sequence: int
    entry_id: str
    merkle_proof: Optional[MerkleProof]
    chain_proof: Optional[ChainLinkProof]
    verification_status: VerificationStatus
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IntegrityProofService:
    """
    Service for generating and verifying ledger integrity proofs.

    Provides comprehensive proof generation, verification, and
    audit trail capabilities for ledger entries.
    """

    _instance: Optional["IntegrityProofService"] = None
    _initialized: bool = False

    def __new__(cls) -> "IntegrityProofService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if IntegrityProofService._initialized:
            return
        IntegrityProofService._initialized = True

        self._merkle_tree = MerkleTree()
        self._entry_data: Dict[int, str] = {}  # sequence -> data
        self._entry_hashes: Dict[int, str] = {}  # sequence -> hash
        self._checkpoints: List[Tuple[int, str]] = []  # (sequence, root)
        self._proof_cache: Dict[int, EntryProofBundle] = {}

    def add_entry(
        self,
        sequence: int,
        entry_id: str,
        data: str,
        prev_hash: Optional[str] = None,
    ) -> EntryProofBundle:
        """
        Add an entry and generate its proof bundle.

        INV-LEDGER-PROOF-005: Audit trail must be append-only
        """
        if sequence in self._entry_data:
            raise ValueError(f"Entry {sequence} already exists (append-only)")

        # Compute entry hash
        entry_hash = compute_sha256(data)

        # Add to Merkle tree
        leaf_index = self._merkle_tree.add_leaf(data)

        # Store entry data
        self._entry_data[sequence] = data
        self._entry_hashes[sequence] = entry_hash

        # Generate Merkle proof
        merkle_proof = self._merkle_tree.get_proof(leaf_index)

        # Generate chain link proof
        chain_proof = None
        if sequence > 0 and prev_hash is not None:
            prev_sequence = sequence - 1
            expected_prev_hash = self._entry_hashes.get(prev_sequence, "0" * 64)
            chain_proof = ChainLinkProof.create(
                entry_sequence=sequence,
                entry_hash=entry_hash,
                prev_sequence=prev_sequence,
                prev_hash=prev_hash,
                expected_prev_hash=expected_prev_hash,
            )

        # Determine verification status
        merkle_valid = merkle_proof is not None
        chain_valid = chain_proof is None or chain_proof.link_valid
        status = (
            VerificationStatus.VALID
            if merkle_valid and chain_valid
            else VerificationStatus.INVALID
        )

        # Create and cache proof bundle
        bundle = EntryProofBundle(
            entry_sequence=sequence,
            entry_id=entry_id,
            merkle_proof=merkle_proof,
            chain_proof=chain_proof,
            verification_status=status,
        )
        self._proof_cache[sequence] = bundle

        return bundle

    def get_proof(self, sequence: int) -> Optional[EntryProofBundle]:
        """Get proof bundle for an entry."""
        return self._proof_cache.get(sequence)

    def verify_entry(self, sequence: int) -> Tuple[bool, str]:
        """
        Verify an entry's integrity.

        Returns (valid, message).
        """
        bundle = self._proof_cache.get(sequence)
        if bundle is None:
            return False, f"No proof found for sequence {sequence}"

        data = self._entry_data.get(sequence)
        if data is None:
            return False, f"No data found for sequence {sequence}"

        # Verify Merkle proof
        if bundle.merkle_proof is None:
            return False, "Missing Merkle proof"

        if not bundle.merkle_proof.verify(data):
            return False, "Merkle proof verification failed"

        # Verify chain link
        if bundle.chain_proof is not None and not bundle.chain_proof.link_valid:
            return False, "Chain link verification failed"

        return True, "Entry integrity verified"

    def create_checkpoint(self, checkpoint_id: str) -> CheckpointProof:
        """
        Create a checkpoint at current state.

        INV-LEDGER-PROOF-002: Checkpoint hashes must match computed values
        """
        current_sequence = len(self._entry_data) - 1
        root_hash = self._merkle_tree.root_hash or "0" * 64

        self._checkpoints.append((current_sequence, root_hash))

        return CheckpointProof(
            checkpoint_id=checkpoint_id,
            checkpoint_sequence=current_sequence,
            merkle_root=root_hash,
            entry_count=self._merkle_tree.size,
            computed_root=root_hash,
            valid=True,
            created_at=datetime.now(timezone.utc),
        )

    def verify_checkpoint(
        self, checkpoint_id: str, claimed_root: str, claimed_count: int
    ) -> CheckpointProof:
        """Verify a checkpoint against current state."""
        current_sequence = len(self._entry_data) - 1

        return CheckpointProof.verify_checkpoint(
            checkpoint_id=checkpoint_id,
            checkpoint_sequence=current_sequence,
            claimed_root=claimed_root,
            entry_count=claimed_count,
            tree=self._merkle_tree,
        )

    def get_audit_trail(self, start_seq: int, end_seq: int) -> List[EntryProofBundle]:
        """Get proof bundles for a range of entries."""
        bundles = []
        for seq in range(start_seq, end_seq + 1):
            bundle = self._proof_cache.get(seq)
            if bundle:
                bundles.append(bundle)
        return bundles

    @property
    def entry_count(self) -> int:
        """Get total entry count."""
        return len(self._entry_data)

    @property
    def checkpoint_count(self) -> int:
        """Get checkpoint count."""
        return len(self._checkpoints)

    @property
    def current_root(self) -> Optional[str]:
        """Get current Merkle root."""
        return self._merkle_tree.root_hash

    def generate_integrity_report(self) -> Dict[str, Any]:
        """Generate comprehensive integrity report."""
        valid_count = sum(
            1 for b in self._proof_cache.values()
            if b.verification_status == VerificationStatus.VALID
        )

        return {
            "total_entries": self.entry_count,
            "verified_entries": valid_count,
            "verification_rate": valid_count / self.entry_count if self.entry_count > 0 else 1.0,
            "checkpoints": self.checkpoint_count,
            "current_root": self.current_root,
            "chain_intact": all(
                b.chain_proof is None or b.chain_proof.link_valid
                for b in self._proof_cache.values()
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "assessor": "ATLAS (GID-11)",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ProofType",
    "VerificationStatus",
    # Data classes
    "MerkleNode",
    "MerkleProof",
    "ChainLinkProof",
    "CheckpointProof",
    "EntryProofBundle",
    # Classes
    "MerkleTree",
    "IntegrityProofService",
    # Functions
    "compute_sha256",
    "compute_node_hash",
]
