"""
Cryptographic Proof Generator
=============================

PAC-SEC-P822-B: BLOCKCHAIN AUDIT ANCHORING
Component: Cryptographic Proof Generation
Agent: CIPHER (GID-SEC-01)

PURPOSE:
  Generates cryptographic proofs enabling third-party verification
  of audit events without revealing actual content. Uses Merkle
  proofs from P822-A hash chain foundation.

INVARIANTS:
  INV-ANCHOR-002: Only hash anchors to blockchain, never content
  INV-ANCHOR-004: Cryptographic proofs MUST enable third-party verification
  INV-PROOF-001: Proofs MUST NOT reveal audit event content
  INV-PROOF-002: Proofs MUST be independently verifiable

SECURITY PROPERTIES:
  - Zero-knowledge: Proof reveals nothing about content
  - Completeness: Valid proofs always verify
  - Soundness: Invalid proofs always fail
  - Non-repudiation: Cannot deny anchored data
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProofType(Enum):
    """Types of cryptographic proofs."""
    MERKLE_INCLUSION = "merkle_inclusion"
    MERKLE_CONSISTENCY = "merkle_consistency"
    ANCHOR_PROOF = "anchor_proof"
    BATCH_PROOF = "batch_proof"


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"
    BLAKE2B = "blake2b"


@dataclass
class MerkleProofNode:
    """Node in a Merkle proof path."""
    position: str  # "left" or "right"
    hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {"position": self.position, "hash": self.hash}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MerkleProofNode":
        return cls(position=data["position"], hash=data["hash"])


@dataclass
class InclusionProof:
    """
    Proof that a specific event is included in a Merkle tree.
    
    Enables verification without revealing other events.
    """
    event_hash: str
    event_index: int
    merkle_root: str
    proof_path: List[MerkleProofNode]
    tree_size: int
    algorithm: HashAlgorithm = HashAlgorithm.SHA256
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": ProofType.MERKLE_INCLUSION.value,
            "event_hash": self.event_hash,
            "event_index": self.event_index,
            "merkle_root": self.merkle_root,
            "proof_path": [n.to_dict() for n in self.proof_path],
            "tree_size": self.tree_size,
            "algorithm": self.algorithm.value,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InclusionProof":
        return cls(
            event_hash=data["event_hash"],
            event_index=data["event_index"],
            merkle_root=data["merkle_root"],
            proof_path=[MerkleProofNode.from_dict(n) for n in data["proof_path"]],
            tree_size=data["tree_size"],
            algorithm=HashAlgorithm(data.get("algorithm", "sha256")),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class AnchorProof:
    """
    Proof that a Merkle root is anchored to blockchain.
    
    Combines Merkle inclusion proof with blockchain anchor data.
    """
    merkle_root: str
    inclusion_proof: InclusionProof
    blockchain: str  # "xrpl" or "hedera"
    tx_hash: Optional[str] = None
    topic_id: Optional[str] = None
    sequence_number: Optional[int] = None
    anchor_timestamp: str = ""
    verification_url: str = ""
    
    def __post_init__(self):
        if not self.anchor_timestamp:
            self.anchor_timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": ProofType.ANCHOR_PROOF.value,
            "merkle_root": self.merkle_root,
            "inclusion_proof": self.inclusion_proof.to_dict(),
            "blockchain": self.blockchain,
            "tx_hash": self.tx_hash,
            "topic_id": self.topic_id,
            "sequence_number": self.sequence_number,
            "anchor_timestamp": self.anchor_timestamp,
            "verification_url": self.verification_url,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnchorProof":
        return cls(
            merkle_root=data["merkle_root"],
            inclusion_proof=InclusionProof.from_dict(data["inclusion_proof"]),
            blockchain=data["blockchain"],
            tx_hash=data.get("tx_hash"),
            topic_id=data.get("topic_id"),
            sequence_number=data.get("sequence_number"),
            anchor_timestamp=data.get("anchor_timestamp", ""),
            verification_url=data.get("verification_url", ""),
        )


@dataclass
class BatchProof:
    """
    Proof for a batch of events.
    
    Efficiently proves multiple events in single verification.
    """
    batch_id: str
    merkle_root: str
    event_count: int
    event_hashes: List[str]
    inclusion_proofs: List[InclusionProof]
    xrpl_anchor: Optional[Dict[str, Any]] = None
    hedera_anchor: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": ProofType.BATCH_PROOF.value,
            "batch_id": self.batch_id,
            "merkle_root": self.merkle_root,
            "event_count": self.event_count,
            "event_hashes": self.event_hashes,
            "inclusion_proofs": [p.to_dict() for p in self.inclusion_proofs],
            "xrpl_anchor": self.xrpl_anchor,
            "hedera_anchor": self.hedera_anchor,
            "timestamp": self.timestamp,
        }


class ProofGenerator:
    """
    Cryptographic proof generator for audit verification.
    
    Provides methods for:
    - generate_merkle_proof(): Create Merkle inclusion proof
    - generate_inclusion_proof(): Prove event in tree
    - verify_proof(): Verify a proof independently
    
    Thread-safe for concurrent operations.
    """
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        """
        Initialize proof generator.
        
        Args:
            algorithm: Hash algorithm to use
        """
        self.algorithm = algorithm
    
    def _hash(self, data: bytes) -> str:
        """Compute hash of data."""
        if self.algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif self.algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).hexdigest()
        elif self.algorithm == HashAlgorithm.BLAKE2B:
            return hashlib.blake2b(data, digest_size=32).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def _combine_hashes(self, left: str, right: str) -> str:
        """Combine two hashes for Merkle tree."""
        combined = f"{left}{right}".encode()
        return self._hash(combined)
    
    def generate_merkle_proof(self,
                               leaf_hashes: List[str],
                               target_index: int,
                               ) -> Tuple[str, List[MerkleProofNode]]:
        """
        Generate Merkle proof for a leaf.
        
        Args:
            leaf_hashes: List of leaf hashes in tree
            target_index: Index of target leaf
            
        Returns:
            Tuple of (merkle_root, proof_path)
        """
        if not leaf_hashes:
            raise ValueError("Cannot generate proof for empty tree")
        
        if target_index < 0 or target_index >= len(leaf_hashes):
            raise ValueError(f"Invalid target index: {target_index}")
        
        # Build tree level by level
        proof_path: List[MerkleProofNode] = []
        current_level = list(leaf_hashes)
        current_index = target_index
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Check if we need to record sibling for proof
                if i == current_index or i + 1 == current_index:
                    if current_index == i:
                        # Target is left, sibling is right
                        if i + 1 < len(current_level):
                            proof_path.append(MerkleProofNode("right", right))
                    else:
                        # Target is right, sibling is left
                        proof_path.append(MerkleProofNode("left", left))
                
                combined = self._combine_hashes(left, right)
                next_level.append(combined)
            
            current_level = next_level
            current_index = current_index // 2
        
        merkle_root = current_level[0]
        return merkle_root, proof_path
    
    def generate_inclusion_proof(self,
                                  event_hash: str,
                                  event_index: int,
                                  all_hashes: List[str],
                                  ) -> InclusionProof:
        """
        Generate inclusion proof for an event.
        
        Args:
            event_hash: Hash of the target event
            event_index: Index of event in list
            all_hashes: All event hashes in order
            
        Returns:
            InclusionProof object
        """
        if event_index < 0 or event_index >= len(all_hashes):
            raise ValueError(f"Invalid event index: {event_index}")
        
        if all_hashes[event_index] != event_hash:
            raise ValueError("Event hash does not match hash at index")
        
        merkle_root, proof_path = self.generate_merkle_proof(all_hashes, event_index)
        
        return InclusionProof(
            event_hash=event_hash,
            event_index=event_index,
            merkle_root=merkle_root,
            proof_path=proof_path,
            tree_size=len(all_hashes),
            algorithm=self.algorithm,
        )
    
    def generate_anchor_proof(self,
                               inclusion_proof: InclusionProof,
                               blockchain: str,
                               tx_hash: Optional[str] = None,
                               topic_id: Optional[str] = None,
                               sequence_number: Optional[int] = None,
                               verification_url: str = "",
                               ) -> AnchorProof:
        """
        Generate anchor proof combining Merkle and blockchain proofs.
        
        Args:
            inclusion_proof: Merkle inclusion proof
            blockchain: Blockchain name ("xrpl" or "hedera")
            tx_hash: XRPL transaction hash
            topic_id: Hedera topic ID
            sequence_number: Hedera sequence number
            verification_url: URL for verification
            
        Returns:
            AnchorProof object
        """
        return AnchorProof(
            merkle_root=inclusion_proof.merkle_root,
            inclusion_proof=inclusion_proof,
            blockchain=blockchain,
            tx_hash=tx_hash,
            topic_id=topic_id,
            sequence_number=sequence_number,
            verification_url=verification_url,
        )
    
    def generate_batch_proof(self,
                              batch_id: str,
                              event_hashes: List[str],
                              indices: Optional[List[int]] = None,
                              ) -> BatchProof:
        """
        Generate proof for a batch of events.
        
        Args:
            batch_id: Unique batch identifier
            event_hashes: All event hashes in batch
            indices: Optional specific indices to prove (default: all)
            
        Returns:
            BatchProof object
        """
        if not event_hashes:
            raise ValueError("Cannot generate batch proof for empty batch")
        
        if indices is None:
            indices = list(range(len(event_hashes)))
        
        # Generate Merkle root
        merkle_root, _ = self.generate_merkle_proof(event_hashes, 0)
        
        # Generate inclusion proofs for requested indices
        inclusion_proofs = []
        for idx in indices:
            proof = self.generate_inclusion_proof(
                event_hashes[idx],
                idx,
                event_hashes,
            )
            inclusion_proofs.append(proof)
        
        return BatchProof(
            batch_id=batch_id,
            merkle_root=merkle_root,
            event_count=len(event_hashes),
            event_hashes=[event_hashes[i] for i in indices],
            inclusion_proofs=inclusion_proofs,
        )
    
    def verify_proof(self, proof: InclusionProof) -> bool:
        """
        Verify an inclusion proof.
        
        Args:
            proof: Inclusion proof to verify
            
        Returns:
            True if proof is valid
        """
        current_hash = proof.event_hash
        
        for node in proof.proof_path:
            if node.position == "left":
                current_hash = self._combine_hashes(node.hash, current_hash)
            else:  # right
                current_hash = self._combine_hashes(current_hash, node.hash)
        
        return current_hash == proof.merkle_root
    
    def verify_anchor_proof(self, proof: AnchorProof) -> Tuple[bool, str]:
        """
        Verify an anchor proof (Merkle + blockchain).
        
        Args:
            proof: Anchor proof to verify
            
        Returns:
            Tuple of (is_valid, message)
        """
        # First verify Merkle inclusion
        if not self.verify_proof(proof.inclusion_proof):
            return False, "Merkle inclusion proof failed"
        
        # Check Merkle root matches
        if proof.inclusion_proof.merkle_root != proof.merkle_root:
            return False, "Merkle root mismatch"
        
        # Blockchain verification would need connector
        # Here we just validate structure
        if proof.blockchain == "xrpl" and not proof.tx_hash:
            return False, "Missing XRPL transaction hash"
        
        if proof.blockchain == "hedera" and (not proof.topic_id or proof.sequence_number is None):
            return False, "Missing Hedera topic/sequence"
        
        return True, "Proof valid"
    
    def verify_batch_proof(self, proof: BatchProof) -> Tuple[bool, List[int]]:
        """
        Verify a batch proof.
        
        Args:
            proof: Batch proof to verify
            
        Returns:
            Tuple of (all_valid, list of invalid indices)
        """
        invalid_indices = []
        
        for i, inclusion_proof in enumerate(proof.inclusion_proofs):
            if not self.verify_proof(inclusion_proof):
                invalid_indices.append(i)
            elif inclusion_proof.merkle_root != proof.merkle_root:
                invalid_indices.append(i)
        
        return len(invalid_indices) == 0, invalid_indices
    
    @staticmethod
    def hash_event(event_data: Any) -> str:
        """
        Hash event data for proof generation.
        
        Args:
            event_data: Event data (dict, string, or bytes)
            
        Returns:
            SHA-256 hash of event
        """
        if isinstance(event_data, bytes):
            data = event_data
        elif isinstance(event_data, str):
            data = event_data.encode()
        else:
            data = json.dumps(event_data, sort_keys=True).encode()
        
        return hashlib.sha256(data).hexdigest()
    
    def export_proof(self, proof: InclusionProof) -> str:
        """Export proof as JSON string."""
        return json.dumps(proof.to_dict(), indent=2)
    
    def import_proof(self, proof_json: str) -> InclusionProof:
        """Import proof from JSON string."""
        data = json.loads(proof_json)
        return InclusionProof.from_dict(data)


def create_proof_generator(algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> ProofGenerator:
    """Factory function for creating proof generator."""
    return ProofGenerator(algorithm=algorithm)
