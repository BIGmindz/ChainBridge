# ═══════════════════════════════════════════════════════════════════════════════
# AML ProofPack & Ledger — Audit Trail & Integrity
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: ATLAS (GID-11)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML ProofPack & Ledger — Audit Trail & Merkle Integrity

PURPOSE:
    Provide immutable audit trails for AML decisions:
    - ProofPack generation for each case
    - Merkle tree integrity verification
    - Ledger anchoring for tamper evidence
    - Regulatory examination support

INTEGRITY:
    - All entries are hashed
    - Merkle tree for batch verification
    - Append-only ledger
    - Tamper-evident design

LANE: GOVERNANCE (AUDIT)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# PROOFPACK ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ProofPackStatus(Enum):
    """Status of proof pack."""

    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    ANCHORED = "ANCHORED"  # Anchored to ledger
    VERIFIED = "VERIFIED"  # Integrity verified


class LedgerEntryType(Enum):
    """Type of ledger entry."""

    CASE_CREATED = "CASE_CREATED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    DECISION_PROPOSED = "DECISION_PROPOSED"
    DECISION_APPROVED = "DECISION_APPROVED"
    ESCALATION = "ESCALATION"
    CASE_CLOSED = "CASE_CLOSED"
    GUARDRAIL_VIOLATION = "GUARDRAIL_VIOLATION"
    TIER_CHANGE = "TIER_CHANGE"


class VerificationResult(Enum):
    """Result of integrity verification."""

    VALID = "VALID"
    INVALID = "INVALID"
    PARTIAL = "PARTIAL"  # Some entries valid
    UNKNOWN = "UNKNOWN"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class LedgerEntry:
    """
    Single entry in the AML audit ledger.

    Represents an auditable event in case processing.
    """

    entry_id: str
    entry_type: LedgerEntryType
    case_id: str
    timestamp: str
    actor: str  # System or user ID
    description: str
    data: Dict[str, Any]
    previous_hash: str
    entry_hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.entry_id.startswith("LE-"):
            raise ValueError(f"Entry ID must start with 'LE-': {self.entry_id}")
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash of entry."""
        data = {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "description": self.description,
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
        }


@dataclass
class ProofPackArtifact:
    """
    Artifact included in a proof pack.

    Represents a piece of evidence or documentation.
    """

    artifact_id: str
    artifact_type: str
    name: str
    content_hash: str
    metadata: Dict[str, Any]
    created_at: str

    def __post_init__(self) -> None:
        if not self.artifact_id.startswith("ART-"):
            raise ValueError(f"Artifact ID must start with 'ART-': {self.artifact_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class AMLProofPack:
    """
    Complete proof pack for an AML case.

    Contains all evidence, decisions, and audit trail for a case.
    """

    proofpack_id: str
    case_id: str
    status: ProofPackStatus
    created_at: str
    finalized_at: Optional[str]
    artifacts: List[ProofPackArtifact] = field(default_factory=list)
    ledger_entries: List[str] = field(default_factory=list)  # Entry IDs
    merkle_root: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.proofpack_id.startswith("PP-AML-"):
            raise ValueError(f"ProofPack ID must start with 'PP-AML-': {self.proofpack_id}")

    def add_artifact(self, artifact: ProofPackArtifact) -> None:
        """Add artifact to proof pack."""
        if self.status != ProofPackStatus.DRAFT:
            raise ValueError("Cannot add artifacts to finalized proof pack")
        self.artifacts.append(artifact)

    def add_ledger_entry(self, entry_id: str) -> None:
        """Add ledger entry reference to proof pack."""
        if self.status != ProofPackStatus.DRAFT:
            raise ValueError("Cannot add entries to finalized proof pack")
        self.ledger_entries.append(entry_id)

    def finalize(self, merkle_root: str) -> None:
        """Finalize the proof pack."""
        self.status = ProofPackStatus.FINALIZED
        self.finalized_at = datetime.now(timezone.utc).isoformat()
        self.merkle_root = merkle_root

    def compute_proofpack_hash(self) -> str:
        """Compute hash of entire proof pack."""
        data = {
            "proofpack_id": self.proofpack_id,
            "case_id": self.case_id,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "ledger_entries": self.ledger_entries,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proofpack_id": self.proofpack_id,
            "case_id": self.case_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
            "artifact_count": len(self.artifacts),
            "ledger_entry_count": len(self.ledger_entries),
            "merkle_root": self.merkle_root,
            "summary": self.summary,
            "proofpack_hash": self.compute_proofpack_hash(),
        }


@dataclass
class MerkleNode:
    """Node in a Merkle tree."""

    hash: str
    left: Optional[MerkleNode] = None
    right: Optional[MerkleNode] = None


# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE
# ═══════════════════════════════════════════════════════════════════════════════


class MerkleTree:
    """
    Merkle tree implementation for integrity verification.

    Provides:
    - Tree construction from leaf hashes
    - Root computation
    - Proof generation for individual leaves
    - Proof verification
    """

    def __init__(self, leaf_hashes: Optional[List[str]] = None) -> None:
        self._leaves: List[str] = leaf_hashes or []
        self._root: Optional[MerkleNode] = None
        if self._leaves:
            self._build_tree()

    def _build_tree(self) -> None:
        """Build Merkle tree from leaves."""
        if not self._leaves:
            return

        # Ensure even number of leaves
        leaves = self._leaves.copy()
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])  # Duplicate last leaf

        # Create leaf nodes
        nodes = [MerkleNode(hash=h) for h in leaves]

        # Build tree bottom-up
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                combined = left.hash + right.hash
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                next_level.append(parent)
            nodes = next_level

        self._root = nodes[0] if nodes else None

    def add_leaf(self, leaf_hash: str) -> None:
        """Add a leaf and rebuild tree."""
        self._leaves.append(leaf_hash)
        self._build_tree()

    @property
    def root_hash(self) -> Optional[str]:
        """Get root hash."""
        return self._root.hash if self._root else None

    @property
    def leaf_count(self) -> int:
        """Get number of leaves."""
        return len(self._leaves)

    def get_proof(self, leaf_index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for a leaf.

        Returns list of (hash, position) tuples where position is 'L' or 'R'.
        """
        if not self._root or leaf_index >= len(self._leaves):
            return []

        proof: List[Tuple[str, str]] = []
        leaves = self._leaves.copy()
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])

        index = leaf_index
        nodes = [MerkleNode(hash=h) for h in leaves]

        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]

                # Add sibling to proof if this pair contains our target
                if i == index or i + 1 == index:
                    if index % 2 == 0:
                        proof.append((right.hash, "R"))
                    else:
                        proof.append((left.hash, "L"))

                combined = left.hash + right.hash
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                parent = MerkleNode(hash=parent_hash, left=left, right=right)
                next_level.append(parent)

            nodes = next_level
            index = index // 2

        return proof

    @staticmethod
    def verify_proof(
        leaf_hash: str,
        proof: List[Tuple[str, str]],
        root_hash: str,
    ) -> bool:
        """Verify a Merkle proof."""
        current_hash = leaf_hash
        for sibling_hash, position in proof:
            if position == "L":
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        return current_hash == root_hash


# ═══════════════════════════════════════════════════════════════════════════════
# AML LEDGER SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class AMLLedger:
    """
    Append-only AML audit ledger.

    Provides:
    - Entry recording with hash chaining
    - Integrity verification
    - Case-specific audit trails
    - Merkle tree anchoring
    """

    def __init__(self) -> None:
        self._entries: Dict[str, LedgerEntry] = {}
        self._chain: List[str] = []  # Entry IDs in order
        self._entry_counter = 0
        self._genesis_hash = hashlib.sha256(b"AML_LEDGER_GENESIS").hexdigest()

    @property
    def last_hash(self) -> str:
        """Get hash of last entry."""
        if not self._chain:
            return self._genesis_hash
        last_id = self._chain[-1]
        return self._entries[last_id].entry_hash

    def record_entry(
        self,
        entry_type: LedgerEntryType,
        case_id: str,
        actor: str,
        description: str,
        data: Dict[str, Any],
    ) -> LedgerEntry:
        """Record a new ledger entry."""
        self._entry_counter += 1
        entry_id = f"LE-{self._entry_counter:08d}"

        entry = LedgerEntry(
            entry_id=entry_id,
            entry_type=entry_type,
            case_id=case_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            description=description,
            data=data,
            previous_hash=self.last_hash,
        )

        self._entries[entry_id] = entry
        self._chain.append(entry_id)
        return entry

    def get_entry(self, entry_id: str) -> Optional[LedgerEntry]:
        """Get entry by ID."""
        return self._entries.get(entry_id)

    def get_entries_for_case(self, case_id: str) -> List[LedgerEntry]:
        """Get all entries for a case in order."""
        return [
            self._entries[entry_id]
            for entry_id in self._chain
            if self._entries[entry_id].case_id == case_id
        ]

    def get_entries_by_type(self, entry_type: LedgerEntryType) -> List[LedgerEntry]:
        """Get entries by type."""
        return [e for e in self._entries.values() if e.entry_type == entry_type]

    def verify_chain(self) -> Tuple[VerificationResult, List[str]]:
        """
        Verify entire chain integrity.

        Returns (result, list of invalid entry IDs).
        """
        invalid_entries: List[str] = []
        expected_hash = self._genesis_hash

        for entry_id in self._chain:
            entry = self._entries[entry_id]

            # Verify previous hash link
            if entry.previous_hash != expected_hash:
                invalid_entries.append(entry_id)

            # Verify entry's own hash
            if not entry.verify_hash():
                invalid_entries.append(entry_id)

            expected_hash = entry.entry_hash

        if not invalid_entries:
            return VerificationResult.VALID, []
        elif len(invalid_entries) < len(self._chain):
            return VerificationResult.PARTIAL, invalid_entries
        else:
            return VerificationResult.INVALID, invalid_entries

    def build_merkle_tree(self, entry_ids: Optional[List[str]] = None) -> MerkleTree:
        """Build Merkle tree from entries."""
        if entry_ids is None:
            entry_ids = self._chain

        hashes = [self._entries[eid].entry_hash for eid in entry_ids if eid in self._entries]
        return MerkleTree(hashes)

    def get_chain_length(self) -> int:
        """Get number of entries in chain."""
        return len(self._chain)

    def list_entries(self, limit: int = 100, offset: int = 0) -> List[LedgerEntry]:
        """List entries with pagination."""
        entry_ids = self._chain[offset : offset + limit]
        return [self._entries[eid] for eid in entry_ids]


# ═══════════════════════════════════════════════════════════════════════════════
# PROOFPACK SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class ProofPackService:
    """
    AML ProofPack management service.

    Provides:
    - ProofPack creation and finalization
    - Artifact management
    - Ledger integration
    - Verification
    """

    def __init__(self, ledger: Optional[AMLLedger] = None) -> None:
        self._proofpacks: Dict[str, AMLProofPack] = {}
        self._proofpack_counter = 0
        self._artifact_counter = 0
        self._ledger = ledger or AMLLedger()

    @property
    def ledger(self) -> AMLLedger:
        """Get associated ledger."""
        return self._ledger

    def create_proofpack(self, case_id: str) -> AMLProofPack:
        """Create a new proof pack for a case."""
        self._proofpack_counter += 1
        proofpack_id = f"PP-AML-{self._proofpack_counter:08d}"

        proofpack = AMLProofPack(
            proofpack_id=proofpack_id,
            case_id=case_id,
            status=ProofPackStatus.DRAFT,
            created_at=datetime.now(timezone.utc).isoformat(),
            finalized_at=None,
        )

        self._proofpacks[proofpack_id] = proofpack
        return proofpack

    def add_artifact(
        self,
        proofpack_id: str,
        artifact_type: str,
        name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProofPackArtifact:
        """Add artifact to proof pack."""
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            raise ValueError(f"ProofPack not found: {proofpack_id}")

        self._artifact_counter += 1
        artifact_id = f"ART-{self._artifact_counter:08d}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        artifact = ProofPackArtifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            content_hash=content_hash,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        proofpack.add_artifact(artifact)
        return artifact

    def record_event(
        self,
        proofpack_id: str,
        entry_type: LedgerEntryType,
        actor: str,
        description: str,
        data: Dict[str, Any],
    ) -> LedgerEntry:
        """Record event to ledger and proof pack."""
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            raise ValueError(f"ProofPack not found: {proofpack_id}")

        entry = self._ledger.record_entry(
            entry_type=entry_type,
            case_id=proofpack.case_id,
            actor=actor,
            description=description,
            data=data,
        )

        proofpack.add_ledger_entry(entry.entry_id)
        return entry

    def finalize_proofpack(
        self,
        proofpack_id: str,
        summary: Optional[Dict[str, Any]] = None,
    ) -> AMLProofPack:
        """Finalize proof pack with Merkle root."""
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            raise ValueError(f"ProofPack not found: {proofpack_id}")

        # Build Merkle tree from ledger entries
        merkle_tree = self._ledger.build_merkle_tree(proofpack.ledger_entries)

        if summary:
            proofpack.summary = summary

        proofpack.finalize(merkle_tree.root_hash or "")
        return proofpack

    def verify_proofpack(self, proofpack_id: str) -> Dict[str, Any]:
        """Verify proof pack integrity."""
        proofpack = self._proofpacks.get(proofpack_id)
        if proofpack is None:
            return {"proofpack_id": proofpack_id, "status": "NOT_FOUND"}

        # Verify ledger entries
        entries_valid = True
        for entry_id in proofpack.ledger_entries:
            entry = self._ledger.get_entry(entry_id)
            if entry is None or not entry.verify_hash():
                entries_valid = False
                break

        # Verify Merkle root
        merkle_tree = self._ledger.build_merkle_tree(proofpack.ledger_entries)
        merkle_valid = merkle_tree.root_hash == proofpack.merkle_root

        overall_valid = entries_valid and merkle_valid

        return {
            "proofpack_id": proofpack_id,
            "case_id": proofpack.case_id,
            "status": proofpack.status.value,
            "entries_valid": entries_valid,
            "merkle_valid": merkle_valid,
            "overall_valid": overall_valid,
            "verification_result": VerificationResult.VALID.value if overall_valid else VerificationResult.INVALID.value,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_proofpack(self, proofpack_id: str) -> Optional[AMLProofPack]:
        """Get proof pack by ID."""
        return self._proofpacks.get(proofpack_id)

    def get_proofpack_for_case(self, case_id: str) -> Optional[AMLProofPack]:
        """Get proof pack for a case."""
        for pp in self._proofpacks.values():
            if pp.case_id == case_id:
                return pp
        return None

    def list_proofpacks(self) -> List[AMLProofPack]:
        """List all proof packs."""
        return list(self._proofpacks.values())

    def generate_report(self) -> Dict[str, Any]:
        """Generate service status report."""
        by_status: Dict[str, int] = {}
        for status in ProofPackStatus:
            by_status[status.value] = len([
                pp for pp in self._proofpacks.values() if pp.status == status
            ])

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_proofpacks": len(self._proofpacks),
            "total_artifacts": self._artifact_counter,
            "ledger_entries": self._ledger.get_chain_length(),
            "proofpacks_by_status": by_status,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ProofPackStatus",
    "LedgerEntryType",
    "VerificationResult",
    # Data Classes
    "LedgerEntry",
    "ProofPackArtifact",
    "AMLProofPack",
    "MerkleNode",
    # Services
    "MerkleTree",
    "AMLLedger",
    "ProofPackService",
]
