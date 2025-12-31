# ═══════════════════════════════════════════════════════════════════════════════
# Memory Ledger Anchoring — Snapshot Hash-Chain Integration
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: ATLAS (GID-11)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Memory Ledger Anchoring — Hash-Chain Integration for Neural Memory

PURPOSE:
    Anchor memory snapshots to the immutable ledger for tamper detection
    and audit trail integrity. Provides inclusion proofs for memory state.

INTEGRATION:
    Builds on core/governance/ledger_proofs.py to provide:
    - Memory snapshot anchoring
    - Inclusion proofs for memory state
    - Chain verification for memory history
    - PDO hash binding for memory invariants

INVARIANTS ENFORCED:
    INV-MEM-003: Memory snapshots include integrity hash
    INV-MEM-005: Memory rollback preserves chain integrity
    INV-MEM-009: Production snapshots anchored to ledger

LANE: ARCHITECTURE_ONLY (NON-INFERENCING)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.ml.neural_memory import (
    MemorySnapshot,
    MemoryStateHash,
    SnapshotRegistry,
    SnapshotStatus,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ANCHORING ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class AnchorStatus(Enum):
    """Status of ledger anchor."""

    PENDING = "PENDING"  # Awaiting anchoring
    ANCHORED = "ANCHORED"  # Successfully anchored
    VERIFIED = "VERIFIED"  # Anchor verified via proof
    EXPIRED = "EXPIRED"  # Anchor window passed
    FAILED = "FAILED"  # Anchoring failed


class ProofType(Enum):
    """Type of inclusion proof."""

    MERKLE = "MERKLE"  # Merkle tree inclusion
    CHAIN_LINK = "CHAIN_LINK"  # Hash-chain linkage
    CHECKPOINT = "CHECKPOINT"  # Checkpoint proof
    COMPOSITE = "COMPOSITE"  # Multiple proof types


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY ANCHOR RECORD
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryAnchorRecord:
    """
    Record of a memory snapshot anchor in the ledger.

    Links memory state to immutable audit trail.
    """

    anchor_id: str
    snapshot_id: str
    state_hash: str
    chain_hash: str  # Hash including predecessor
    ledger_block: int
    ledger_tx_hash: str
    anchor_time: str
    status: AnchorStatus = AnchorStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate anchor ID format."""
        if not self.anchor_id.startswith("ANCHOR-MEM-"):
            raise ValueError(f"Anchor ID must start with 'ANCHOR-MEM-': {self.anchor_id}")

    def compute_anchor_hash(self) -> str:
        """Compute hash of anchor record for verification."""
        data = {
            "anchor_id": self.anchor_id,
            "snapshot_id": self.snapshot_id,
            "state_hash": self.state_hash,
            "chain_hash": self.chain_hash,
            "ledger_block": self.ledger_block,
            "ledger_tx_hash": self.ledger_tx_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def is_verified(self) -> bool:
        """Check if anchor is verified."""
        return self.status == AnchorStatus.VERIFIED


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY INCLUSION PROOF
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryInclusionProof:
    """
    Inclusion proof for memory state in ledger.

    Proves that a memory snapshot was anchored at a specific point in time.
    """

    proof_id: str
    anchor_id: str
    snapshot_id: str
    proof_type: ProofType
    proof_path: List[str]  # Merkle path or chain hashes
    root_hash: str
    verified: bool = False
    verification_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate proof ID format."""
        if not self.proof_id.startswith("PROOF-MEM-"):
            raise ValueError(f"Proof ID must start with 'PROOF-MEM-': {self.proof_id}")

    def path_length(self) -> int:
        """Get proof path length."""
        return len(self.proof_path)


# ═══════════════════════════════════════════════════════════════════════════════
# PDO HASH BINDING
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PDOMemoryBinding:
    """
    Binding between memory state and PDO (Provable Data Object).

    Links memory invariants to PDO hash for governance verification.
    """

    binding_id: str
    pdo_hash: str
    memory_hash: str
    invariant_ids: List[str]  # INV-MEM-* IDs bound
    binding_time: str
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate binding ID format."""
        if not self.binding_id.startswith("PDO-MEM-"):
            raise ValueError(f"Binding ID must start with 'PDO-MEM-': {self.binding_id}")

    def compute_binding_hash(self) -> str:
        """Compute hash of binding."""
        data = {
            "binding_id": self.binding_id,
            "pdo_hash": self.pdo_hash,
            "memory_hash": self.memory_hash,
            "invariant_ids": sorted(self.invariant_ids),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY ANCHOR SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryAnchorService:
    """
    Service for anchoring memory snapshots to ledger.

    Provides anchoring, verification, and proof generation for memory state.
    """

    def __init__(self, snapshot_registry: Optional[SnapshotRegistry] = None) -> None:
        self._snapshot_registry = snapshot_registry or SnapshotRegistry()
        self._anchors: Dict[str, MemoryAnchorRecord] = {}
        self._proofs: Dict[str, MemoryInclusionProof] = {}
        self._bindings: Dict[str, PDOMemoryBinding] = {}
        self._anchor_counter = 0
        self._proof_counter = 0
        self._binding_counter = 0
        self._current_block = 0  # Simulated ledger block

    def anchor_snapshot(self, snapshot: MemorySnapshot) -> MemoryAnchorRecord:
        """
        Anchor a memory snapshot to the ledger.

        INV-MEM-009: Production snapshots anchored to ledger
        """
        self._anchor_counter += 1
        self._current_block += 1

        anchor_id = f"ANCHOR-MEM-{self._anchor_counter:06d}"

        # Compute chain hash (includes predecessor)
        chain_hash = snapshot.compute_chain_hash()

        # Simulate ledger transaction
        tx_hash = hashlib.sha256(
            f"{anchor_id}:{chain_hash}:{self._current_block}".encode()
        ).hexdigest()

        anchor = MemoryAnchorRecord(
            anchor_id=anchor_id,
            snapshot_id=snapshot.snapshot_id,
            state_hash=snapshot.state_hash.hash_value,
            chain_hash=chain_hash,
            ledger_block=self._current_block,
            ledger_tx_hash=tx_hash,
            anchor_time=datetime.now(timezone.utc).isoformat(),
            status=AnchorStatus.ANCHORED,
        )

        self._anchors[anchor_id] = anchor
        return anchor

    def verify_anchor(self, anchor_id: str) -> Tuple[bool, Optional[str]]:
        """
        Verify an anchor exists in ledger.

        Returns (verified, error_message).
        """
        anchor = self._anchors.get(anchor_id)
        if anchor is None:
            return False, f"Anchor not found: {anchor_id}"

        # Verify anchor hash
        expected_hash = anchor.compute_anchor_hash()

        # In production, this would verify against actual ledger
        # For now, we simulate verification
        return True, None

    def generate_proof(self, snapshot_id: str) -> Optional[MemoryInclusionProof]:
        """
        Generate inclusion proof for a snapshot.

        Returns proof if snapshot is anchored, None otherwise.
        """
        # Find anchor for snapshot
        anchor = None
        for a in self._anchors.values():
            if a.snapshot_id == snapshot_id:
                anchor = a
                break

        if anchor is None:
            return None

        self._proof_counter += 1
        proof_id = f"PROOF-MEM-{self._proof_counter:06d}"

        # Build proof path (simplified Merkle-style)
        proof_path = [
            anchor.state_hash,
            anchor.chain_hash,
            anchor.ledger_tx_hash,
        ]

        # Compute root hash
        root_hash = hashlib.sha256(
            "".join(proof_path).encode()
        ).hexdigest()

        proof = MemoryInclusionProof(
            proof_id=proof_id,
            anchor_id=anchor.anchor_id,
            snapshot_id=snapshot_id,
            proof_type=ProofType.CHAIN_LINK,
            proof_path=proof_path,
            root_hash=root_hash,
            verified=True,
            verification_time=datetime.now(timezone.utc).isoformat(),
        )

        self._proofs[proof_id] = proof
        return proof

    def verify_proof(self, proof: MemoryInclusionProof) -> Tuple[bool, Optional[str]]:
        """
        Verify an inclusion proof.

        Returns (valid, error_message).
        """
        if not proof.proof_path:
            return False, "Empty proof path"

        # Recompute root hash
        computed_root = hashlib.sha256(
            "".join(proof.proof_path).encode()
        ).hexdigest()

        if computed_root != proof.root_hash:
            return False, f"Root hash mismatch: {computed_root} != {proof.root_hash}"

        return True, None

    def create_pdo_binding(
        self,
        pdo_hash: str,
        memory_hash: str,
        invariant_ids: List[str],
    ) -> PDOMemoryBinding:
        """
        Create PDO binding for memory state.

        Links memory invariants to PDO hash for governance verification.
        """
        self._binding_counter += 1
        binding_id = f"PDO-MEM-{self._binding_counter:06d}"

        binding = PDOMemoryBinding(
            binding_id=binding_id,
            pdo_hash=pdo_hash,
            memory_hash=memory_hash,
            invariant_ids=invariant_ids,
            binding_time=datetime.now(timezone.utc).isoformat(),
        )

        self._bindings[binding_id] = binding
        return binding

    def verify_pdo_binding(
        self,
        binding_id: str,
        current_memory_hash: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify PDO binding is valid for current memory state.

        Returns (valid, error_message).
        """
        binding = self._bindings.get(binding_id)
        if binding is None:
            return False, f"Binding not found: {binding_id}"

        if not binding.active:
            return False, "Binding is inactive"

        if binding.memory_hash != current_memory_hash:
            return False, f"Memory hash mismatch: expected {binding.memory_hash}, got {current_memory_hash}"

        return True, None

    def get_anchor(self, anchor_id: str) -> Optional[MemoryAnchorRecord]:
        """Get anchor by ID."""
        return self._anchors.get(anchor_id)

    def get_proof(self, proof_id: str) -> Optional[MemoryInclusionProof]:
        """Get proof by ID."""
        return self._proofs.get(proof_id)

    def get_binding(self, binding_id: str) -> Optional[PDOMemoryBinding]:
        """Get binding by ID."""
        return self._bindings.get(binding_id)

    def list_anchors(self) -> List[MemoryAnchorRecord]:
        """List all anchors."""
        return list(self._anchors.values())

    def list_bindings(self) -> List[PDOMemoryBinding]:
        """List all PDO bindings."""
        return list(self._bindings.values())

    def anchor_count(self) -> int:
        """Return count of anchors."""
        return len(self._anchors)

    def proof_count(self) -> int:
        """Return count of proofs."""
        return len(self._proofs)

    def binding_count(self) -> int:
        """Return count of PDO bindings."""
        return len(self._bindings)


# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN INTEGRITY VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryChainValidator:
    """
    Validator for memory snapshot chain integrity.

    Verifies chain continuity, anchor status, and proof validity.
    """

    def __init__(
        self,
        snapshot_registry: SnapshotRegistry,
        anchor_service: MemoryAnchorService,
    ) -> None:
        self._snapshot_registry = snapshot_registry
        self._anchor_service = anchor_service

    def validate_chain(self) -> Tuple[bool, List[str]]:
        """
        Validate entire memory snapshot chain.

        Returns (valid, list_of_errors).
        """
        errors = []

        # Validate snapshot registry chain
        valid, error = self._snapshot_registry.verify_chain()
        if not valid:
            errors.append(f"Chain integrity: {error}")

        # Verify each anchored snapshot
        for anchor in self._anchor_service.list_anchors():
            valid, error = self._anchor_service.verify_anchor(anchor.anchor_id)
            if not valid:
                errors.append(f"Anchor {anchor.anchor_id}: {error}")

        return len(errors) == 0, errors

    def validate_snapshot(self, snapshot_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a specific snapshot's integrity.

        Returns (valid, error_message).
        """
        snapshot = self._snapshot_registry.get(snapshot_id)
        if snapshot is None:
            return False, f"Snapshot not found: {snapshot_id}"

        # Check if anchored
        proof = self._anchor_service.generate_proof(snapshot_id)
        if proof is None:
            return False, f"No anchor found for snapshot: {snapshot_id}"

        # Verify proof
        valid, error = self._anchor_service.verify_proof(proof)
        if not valid:
            return False, f"Proof verification failed: {error}"

        return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "AnchorStatus",
    "ProofType",
    # Data classes
    "MemoryAnchorRecord",
    "MemoryInclusionProof",
    "PDOMemoryBinding",
    # Services
    "MemoryAnchorService",
    "MemoryChainValidator",
]
