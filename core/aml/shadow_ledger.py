# ═══════════════════════════════════════════════════════════════════════════════
# AML Shadow ProofPack Ledger (SHADOW MODE)
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# Agent: ATLAS (GID-11)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Shadow ProofPack Ledger — Merkle-Bound Audit Trail for Shadow Pilot

PURPOSE:
    Anchor ProofPacks to shadow ledger with Merkle integrity:
    - Generate shadow ProofPacks for all pilot decisions
    - Compute Merkle roots for batch verification
    - Provide audit trail for pilot analysis

CONSTRAINTS:
    - SHADOW MODE: No production ledger writes
    - All anchoring is local/in-memory
    - Deterministic for reproducibility

LANE: GOVERNANCE (SHADOW AUDIT)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.governance.aml_proofpack import (
    AMLProofPack,
    LedgerEntry,
    LedgerEntryType,
    ProofPackArtifact,
    ProofPackStatus,
    VerificationResult,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW LEDGER ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowLedgerStatus(Enum):
    """Status of shadow ledger."""

    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"  # No more writes
    EXPORTED = "EXPORTED"  # Exported for analysis


class ShadowAnchorType(Enum):
    """Type of ledger anchor."""

    PROOFPACK = "PROOFPACK"  # Single ProofPack anchor
    BATCH = "BATCH"  # Batch of ProofPacks
    CHECKPOINT = "CHECKPOINT"  # Periodic checkpoint


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ShadowLedgerEntry:
    """
    Entry in the shadow audit ledger.

    Extends base LedgerEntry with shadow pilot metadata.
    """

    entry_id: str
    entry_type: LedgerEntryType
    case_id: str
    timestamp: str
    actor: str
    description: str
    data: Dict[str, Any]
    previous_hash: str
    entry_hash: str = ""
    shadow_mode: bool = True
    pilot_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.entry_id.startswith("SHLE-"):
            raise ValueError(f"Entry ID must start with 'SHLE-': {self.entry_id}")
        if not self.shadow_mode:
            raise ValueError("FAIL-CLOSED: Shadow mode must be enabled")
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute deterministic hash of entry."""
        data = {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "data": self.data,
            "previous_hash": self.previous_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def verify_hash(self) -> bool:
        """Verify entry hash integrity."""
        return self.entry_hash == self._compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "description": self.description,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
            "shadow_mode": self.shadow_mode,
            "pilot_id": self.pilot_id,
        }


@dataclass
class ShadowAnchor:
    """
    Anchor point in shadow ledger.

    Represents a Merkle root for a set of entries.
    """

    anchor_id: str
    anchor_type: ShadowAnchorType
    merkle_root: str
    entry_count: int
    entry_ids: List[str]
    anchored_at: str
    pilot_id: str

    def __post_init__(self) -> None:
        if not self.anchor_id.startswith("SHANC-"):
            raise ValueError(f"Anchor ID must start with 'SHANC-': {self.anchor_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "anchor_type": self.anchor_type.value,
            "merkle_root": self.merkle_root,
            "entry_count": self.entry_count,
            "entry_ids": self.entry_ids,
            "anchored_at": self.anchored_at,
            "pilot_id": self.pilot_id,
        }


@dataclass
class ShadowProofPack:
    """
    Shadow pilot ProofPack.

    Contains all evidence and audit trail for a shadow case.
    """

    proofpack_id: str
    case_id: str
    pilot_id: str
    status: ProofPackStatus
    created_at: str
    finalized_at: Optional[str] = None
    artifacts: List[ProofPackArtifact] = field(default_factory=list)
    ledger_entry_ids: List[str] = field(default_factory=list)
    merkle_root: Optional[str] = None
    anchor_id: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    shadow_mode: bool = True

    def __post_init__(self) -> None:
        if not self.proofpack_id.startswith("SHPP-"):
            raise ValueError(f"ProofPack ID must start with 'SHPP-': {self.proofpack_id}")
        if not self.shadow_mode:
            raise ValueError("FAIL-CLOSED: Shadow mode must be enabled")

    def add_artifact(self, artifact: ProofPackArtifact) -> None:
        """Add artifact to proof pack."""
        if self.status != ProofPackStatus.DRAFT:
            raise ValueError("Cannot add artifacts to finalized proof pack")
        self.artifacts.append(artifact)

    def add_ledger_entry(self, entry_id: str) -> None:
        """Add ledger entry reference."""
        if self.status != ProofPackStatus.DRAFT:
            raise ValueError("Cannot add entries to finalized proof pack")
        self.ledger_entry_ids.append(entry_id)

    def finalize(self, merkle_root: str) -> None:
        """Finalize the proof pack."""
        self.status = ProofPackStatus.FINALIZED
        self.finalized_at = datetime.now(timezone.utc).isoformat()
        self.merkle_root = merkle_root

    def anchor(self, anchor_id: str) -> None:
        """Anchor proof pack to ledger."""
        if self.status != ProofPackStatus.FINALIZED:
            raise ValueError("Can only anchor finalized proof packs")
        self.status = ProofPackStatus.ANCHORED
        self.anchor_id = anchor_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proofpack_id": self.proofpack_id,
            "case_id": self.case_id,
            "pilot_id": self.pilot_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
            "artifact_count": len(self.artifacts),
            "ledger_entry_count": len(self.ledger_entry_ids),
            "merkle_root": self.merkle_root,
            "anchor_id": self.anchor_id,
            "summary": self.summary,
            "shadow_mode": self.shadow_mode,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE FOR SHADOW LEDGER
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowMerkleTree:
    """
    Merkle tree for shadow ledger integrity.

    Provides hash-based integrity verification for ledger entries.
    """

    def __init__(self) -> None:
        """Initialize empty Merkle tree."""
        self._leaves: List[str] = []
        self._root: Optional[str] = None

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        """Hash a pair of nodes."""
        combined = left + right
        return hashlib.sha256(combined.encode()).hexdigest()

    def add_leaf(self, data_hash: str) -> int:
        """
        Add a leaf to the tree.

        Args:
            data_hash: Hash of the data to add

        Returns:
            Index of added leaf
        """
        self._leaves.append(data_hash)
        self._root = None  # Invalidate cached root
        return len(self._leaves) - 1

    def compute_root(self) -> str:
        """
        Compute the Merkle root.

        Returns:
            Merkle root hash
        """
        if not self._leaves:
            return hashlib.sha256(b"EMPTY").hexdigest()

        if self._root is not None:
            return self._root

        # Build tree
        level = self._leaves.copy()

        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                next_level.append(self._hash_pair(left, right))
            level = next_level

        self._root = level[0]
        return self._root

    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for a leaf.

        Args:
            index: Index of leaf

        Returns:
            List of (sibling_hash, direction) tuples
        """
        if index >= len(self._leaves):
            raise IndexError(f"Index {index} out of range")

        proof = []
        level = self._leaves.copy()
        idx = index

        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                next_level.append(self._hash_pair(left, right))

                if i == idx - (idx % 2):
                    if idx % 2 == 0:
                        sibling = right
                        direction = "R"
                    else:
                        sibling = left
                        direction = "L"
                    proof.append((sibling, direction))

            idx = idx // 2
            level = next_level

        return proof

    def verify_proof(
        self,
        leaf_hash: str,
        proof: List[Tuple[str, str]],
        root: str,
    ) -> bool:
        """
        Verify a Merkle proof.

        Args:
            leaf_hash: Hash of the leaf
            proof: Merkle proof
            root: Expected root hash

        Returns:
            True if proof is valid
        """
        current = leaf_hash

        for sibling, direction in proof:
            if direction == "L":
                current = self._hash_pair(sibling, current)
            else:
                current = self._hash_pair(current, sibling)

        return current == root

    @property
    def leaf_count(self) -> int:
        """Number of leaves in tree."""
        return len(self._leaves)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW LEDGER SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowLedgerService:
    """
    Service for managing shadow pilot ledger.

    Provides:
    - Entry creation and storage
    - ProofPack generation
    - Merkle anchoring
    - Integrity verification
    """

    def __init__(self, pilot_id: str) -> None:
        """
        Initialize ledger service.

        Args:
            pilot_id: Shadow pilot identifier
        """
        self._pilot_id = pilot_id
        self._status = ShadowLedgerStatus.ACTIVE
        self._entries: Dict[str, ShadowLedgerEntry] = {}
        self._proofpacks: Dict[str, ShadowProofPack] = {}
        self._anchors: Dict[str, ShadowAnchor] = {}
        self._merkle_tree = ShadowMerkleTree()

        self._entry_counter = 0
        self._proofpack_counter = 0
        self._anchor_counter = 0
        self._artifact_counter = 0

        self._genesis_hash = self._create_genesis()
        self._shadow_mode = True  # ALWAYS TRUE

    def _create_genesis(self) -> str:
        """Create genesis entry hash."""
        genesis_data = {
            "pilot_id": self._pilot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "GENESIS",
        }
        return hashlib.sha256(json.dumps(genesis_data, sort_keys=True).encode()).hexdigest()

    @property
    def is_shadow_mode(self) -> bool:
        """Verify shadow mode is enabled (always true)."""
        return self._shadow_mode

    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        self._entry_counter += 1
        return f"SHLE-{self._entry_counter:08d}"

    def _generate_proofpack_id(self) -> str:
        """Generate unique proofpack ID."""
        self._proofpack_counter += 1
        return f"SHPP-{self._proofpack_counter:08d}"

    def _generate_anchor_id(self) -> str:
        """Generate unique anchor ID."""
        self._anchor_counter += 1
        return f"SHANC-{self._anchor_counter:08d}"

    def _generate_artifact_id(self) -> str:
        """Generate unique artifact ID."""
        self._artifact_counter += 1
        return f"ART-SH-{self._artifact_counter:08d}"

    def _get_previous_hash(self) -> str:
        """Get hash of most recent entry."""
        if not self._entries:
            return self._genesis_hash
        latest_entry = max(self._entries.values(), key=lambda e: e.timestamp)
        return latest_entry.entry_hash

    def create_entry(
        self,
        entry_type: LedgerEntryType,
        case_id: str,
        actor: str,
        description: str,
        data: Dict[str, Any],
    ) -> ShadowLedgerEntry:
        """
        Create a new ledger entry.

        Args:
            entry_type: Type of entry
            case_id: Associated case ID
            actor: Actor creating entry
            description: Human-readable description
            data: Entry data

        Returns:
            Created entry
        """
        if self._status != ShadowLedgerStatus.ACTIVE:
            raise RuntimeError("Ledger is not active")

        entry = ShadowLedgerEntry(
            entry_id=self._generate_entry_id(),
            entry_type=entry_type,
            case_id=case_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            description=description,
            data=data,
            previous_hash=self._get_previous_hash(),
            pilot_id=self._pilot_id,
        )

        self._entries[entry.entry_id] = entry
        self._merkle_tree.add_leaf(entry.entry_hash)

        return entry

    def create_proofpack(self, case_id: str) -> ShadowProofPack:
        """
        Create a new ProofPack for a case.

        Args:
            case_id: Case identifier

        Returns:
            Created ProofPack
        """
        proofpack = ShadowProofPack(
            proofpack_id=self._generate_proofpack_id(),
            case_id=case_id,
            pilot_id=self._pilot_id,
            status=ProofPackStatus.DRAFT,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._proofpacks[proofpack.proofpack_id] = proofpack
        return proofpack

    def add_artifact_to_proofpack(
        self,
        proofpack_id: str,
        artifact_type: str,
        name: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> ProofPackArtifact:
        """
        Add artifact to ProofPack.

        Args:
            proofpack_id: ProofPack identifier
            artifact_type: Type of artifact
            name: Artifact name
            content: Artifact content
            metadata: Additional metadata

        Returns:
            Created artifact
        """
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            raise ValueError(f"ProofPack not found: {proofpack_id}")

        content_hash = hashlib.sha256(content.encode()).hexdigest()

        artifact = ProofPackArtifact(
            artifact_id=self._generate_artifact_id(),
            artifact_type=artifact_type,
            name=name,
            content_hash=content_hash,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        proofpack.add_artifact(artifact)
        return artifact

    def finalize_proofpack(self, proofpack_id: str) -> str:
        """
        Finalize a ProofPack and compute Merkle root.

        Args:
            proofpack_id: ProofPack identifier

        Returns:
            Merkle root of ProofPack
        """
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            raise ValueError(f"ProofPack not found: {proofpack_id}")

        # Build Merkle tree from artifacts
        pp_tree = ShadowMerkleTree()
        for artifact in proofpack.artifacts:
            pp_tree.add_leaf(artifact.content_hash)

        for entry_id in proofpack.ledger_entry_ids:
            entry = self._entries.get(entry_id)
            if entry:
                pp_tree.add_leaf(entry.entry_hash)

        merkle_root = pp_tree.compute_root()
        proofpack.finalize(merkle_root)

        return merkle_root

    def anchor_proofpack(self, proofpack_id: str) -> ShadowAnchor:
        """
        Anchor ProofPack to ledger.

        Args:
            proofpack_id: ProofPack identifier

        Returns:
            Created anchor
        """
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            raise ValueError(f"ProofPack not found: {proofpack_id}")

        if proofpack.status != ProofPackStatus.FINALIZED:
            raise ValueError("Can only anchor finalized ProofPacks")

        # Create anchor entry
        anchor_entry = self.create_entry(
            entry_type=LedgerEntryType.CASE_CLOSED,
            case_id=proofpack.case_id,
            actor="SHADOW_LEDGER",
            description=f"Anchored ProofPack {proofpack_id}",
            data={
                "proofpack_id": proofpack_id,
                "merkle_root": proofpack.merkle_root,
            },
        )

        anchor = ShadowAnchor(
            anchor_id=self._generate_anchor_id(),
            anchor_type=ShadowAnchorType.PROOFPACK,
            merkle_root=proofpack.merkle_root,
            entry_count=len(proofpack.ledger_entry_ids) + len(proofpack.artifacts),
            entry_ids=[anchor_entry.entry_id],
            anchored_at=datetime.now(timezone.utc).isoformat(),
            pilot_id=self._pilot_id,
        )

        self._anchors[anchor.anchor_id] = anchor
        proofpack.anchor(anchor.anchor_id)

        return anchor

    def create_checkpoint(self) -> ShadowAnchor:
        """
        Create a checkpoint anchor for all entries since last checkpoint.

        Returns:
            Checkpoint anchor
        """
        # Compute current Merkle root
        merkle_root = self._merkle_tree.compute_root()

        anchor = ShadowAnchor(
            anchor_id=self._generate_anchor_id(),
            anchor_type=ShadowAnchorType.CHECKPOINT,
            merkle_root=merkle_root,
            entry_count=len(self._entries),
            entry_ids=list(self._entries.keys()),
            anchored_at=datetime.now(timezone.utc).isoformat(),
            pilot_id=self._pilot_id,
        )

        self._anchors[anchor.anchor_id] = anchor
        return anchor

    def verify_ledger_integrity(self) -> VerificationResult:
        """
        Verify integrity of entire ledger.

        Returns:
            Verification result
        """
        if not self._entries:
            return VerificationResult.VALID

        # Verify each entry's hash
        invalid_entries = []
        for entry_id, entry in self._entries.items():
            if not entry.verify_hash():
                invalid_entries.append(entry_id)

        # Verify chain integrity
        entries_sorted = sorted(self._entries.values(), key=lambda e: e.timestamp)
        chain_valid = True
        prev_hash = self._genesis_hash

        for entry in entries_sorted:
            if entry.previous_hash != prev_hash:
                chain_valid = False
                break
            prev_hash = entry.entry_hash

        if invalid_entries or not chain_valid:
            return VerificationResult.INVALID
        return VerificationResult.VALID

    def get_ledger_summary(self) -> Dict[str, Any]:
        """Get summary of ledger state."""
        return {
            "pilot_id": self._pilot_id,
            "status": self._status.value,
            "entry_count": len(self._entries),
            "proofpack_count": len(self._proofpacks),
            "anchor_count": len(self._anchors),
            "merkle_root": self._merkle_tree.compute_root(),
            "integrity": self.verify_ledger_integrity().value,
            "shadow_mode": self._shadow_mode,
        }

    def export_ledger(self) -> Dict[str, Any]:
        """Export complete ledger for analysis."""
        return {
            "pilot_id": self._pilot_id,
            "genesis_hash": self._genesis_hash,
            "entries": [e.to_dict() for e in self._entries.values()],
            "proofpacks": [p.to_dict() for p in self._proofpacks.values()],
            "anchors": [a.to_dict() for a in self._anchors.values()],
            "summary": self.get_ledger_summary(),
        }
