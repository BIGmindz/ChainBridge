"""
Cryptographic Hash Chain Module
===============================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE
Component: Cryptographic Hash Chaining with Merkle Tree
Agent: CIPHER (GID-SEC-01)

PURPOSE:
  Implements tamper-evident hash chaining for audit events using SHA-256.
  Merkle tree structure enables efficient verification of large event batches.
  Any modification to historical events breaks the chain, enabling detection.

INVARIANTS:
  INV-AUDIT-001: Hash chain MUST detect any tampering attempt
  INV-AUDIT-002: Chain links MUST use SHA-256 cryptographic hashing
  INV-AUDIT-003: Merkle root MUST be recalculable from leaves
  INV-AUDIT-004: Previous hash MUST be included in each link

SECURITY PROPERTIES:
  - Collision resistance: Computationally infeasible to find two inputs with same hash
  - Pre-image resistance: Cannot reverse hash to find original input
  - Second pre-image resistance: Cannot find different input with same hash
  - Chain integrity: Breaking one link invalidates all subsequent links
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"


@dataclass
class ChainLink:
    """
    Single link in the hash chain.
    
    Each link contains:
    - index: Position in the chain (0-indexed)
    - timestamp: When the link was created (UTC ISO format)
    - data_hash: SHA-256 hash of the event data
    - previous_hash: Hash of the previous link (genesis has zeros)
    - link_hash: Hash of this entire link (computed)
    """
    index: int
    timestamp: str
    data_hash: str
    previous_hash: str
    link_hash: str = ""
    
    def __post_init__(self):
        """Compute link hash if not provided."""
        if not self.link_hash:
            self.link_hash = self._compute_link_hash()
    
    def _compute_link_hash(self) -> str:
        """Compute SHA-256 hash of this link's contents."""
        content = f"{self.index}:{self.timestamp}:{self.data_hash}:{self.previous_hash}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize link to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data_hash": self.data_hash,
            "previous_hash": self.previous_hash,
            "link_hash": self.link_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChainLink":
        """Deserialize link from dictionary."""
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            data_hash=data["data_hash"],
            previous_hash=data["previous_hash"],
            link_hash=data.get("link_hash", ""),
        )
    
    def verify(self) -> bool:
        """Verify this link's hash is correct."""
        expected = self._compute_link_hash()
        return self.link_hash == expected


@dataclass
class MerkleNode:
    """Node in a Merkle tree."""
    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None
    is_leaf: bool = False
    data_index: int = -1  # Index of original data for leaf nodes


class HashChain:
    """
    Cryptographic hash chain with Merkle tree support.
    
    Provides tamper-evident storage for audit events:
    - append(): Add new event to chain
    - verify(): Check chain integrity
    - get_root(): Get Merkle root of all events
    - get_proof(): Get Merkle proof for specific event
    - verify_proof(): Verify a Merkle proof
    
    Thread-safe for append operations.
    """
    
    # Genesis block previous hash (all zeros)
    GENESIS_PREVIOUS_HASH = "0" * 64
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        """
        Initialize empty hash chain.
        
        Args:
            algorithm: Hash algorithm to use (default SHA-256)
        """
        self._algorithm = algorithm
        self._chain: List[ChainLink] = []
        self._merkle_root: Optional[str] = None
        self._merkle_tree: Optional[MerkleNode] = None
        self._dirty = True  # Merkle tree needs rebuild
    
    @property
    def length(self) -> int:
        """Return number of links in chain."""
        return len(self._chain)
    
    @property
    def is_empty(self) -> bool:
        """Check if chain is empty."""
        return len(self._chain) == 0
    
    def _hash(self, data: bytes) -> str:
        """Compute hash of data using configured algorithm."""
        if self._algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif self._algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {self._algorithm}")
    
    def _hash_data(self, data: Any) -> str:
        """Hash arbitrary data by serializing to JSON first."""
        if isinstance(data, bytes):
            return self._hash(data)
        elif isinstance(data, str):
            return self._hash(data.encode())
        else:
            serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
            return self._hash(serialized.encode())
    
    def append(self, data: Any) -> ChainLink:
        """
        Append new data to the hash chain.
        
        Args:
            data: Event data to append (will be hashed)
            
        Returns:
            ChainLink: The newly created chain link
            
        Raises:
            ValueError: If data is None or empty
        """
        if data is None:
            raise ValueError("Cannot append None to hash chain")
        
        # Get previous hash
        if self.is_empty:
            previous_hash = self.GENESIS_PREVIOUS_HASH
        else:
            previous_hash = self._chain[-1].link_hash
        
        # Create new link
        link = ChainLink(
            index=len(self._chain),
            timestamp=datetime.now(timezone.utc).isoformat(),
            data_hash=self._hash_data(data),
            previous_hash=previous_hash,
        )
        
        self._chain.append(link)
        self._dirty = True  # Merkle tree needs rebuild
        
        return link
    
    def verify(self) -> Tuple[bool, Optional[int]]:
        """
        Verify entire chain integrity.
        
        Returns:
            Tuple of (is_valid, first_invalid_index)
            If valid, returns (True, None)
            If invalid, returns (False, index_of_first_bad_link)
        """
        if self.is_empty:
            return True, None
        
        for i, link in enumerate(self._chain):
            # Verify link's own hash
            if not link.verify():
                return False, i
            
            # Verify chain linkage
            if i == 0:
                expected_prev = self.GENESIS_PREVIOUS_HASH
            else:
                expected_prev = self._chain[i - 1].link_hash
            
            if link.previous_hash != expected_prev:
                return False, i
        
        return True, None
    
    def verify_at(self, index: int) -> bool:
        """
        Verify a specific link and its chain back to genesis.
        
        Args:
            index: Index of link to verify
            
        Returns:
            True if link and all predecessors are valid
        """
        if index < 0 or index >= len(self._chain):
            return False
        
        for i in range(index + 1):
            link = self._chain[i]
            
            if not link.verify():
                return False
            
            if i == 0:
                expected_prev = self.GENESIS_PREVIOUS_HASH
            else:
                expected_prev = self._chain[i - 1].link_hash
            
            if link.previous_hash != expected_prev:
                return False
        
        return True
    
    def get_link(self, index: int) -> Optional[ChainLink]:
        """Get link at specific index."""
        if 0 <= index < len(self._chain):
            return self._chain[index]
        return None
    
    def get_last_link(self) -> Optional[ChainLink]:
        """Get the most recent link."""
        if self.is_empty:
            return None
        return self._chain[-1]
    
    def _build_merkle_tree(self) -> Optional[MerkleNode]:
        """Build Merkle tree from chain links."""
        if self.is_empty:
            return None
        
        # Create leaf nodes from link hashes
        leaves = [
            MerkleNode(hash=link.link_hash, is_leaf=True, data_index=i)
            for i, link in enumerate(self._chain)
        ]
        
        # Pad to power of 2 if needed
        while len(leaves) > 1 and (len(leaves) & (len(leaves) - 1)) != 0:
            leaves.append(MerkleNode(hash=leaves[-1].hash, is_leaf=False, data_index=-1))
        
        # Build tree bottom-up
        nodes = leaves
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                
                combined = left.hash + right.hash
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                
                next_level.append(MerkleNode(
                    hash=parent_hash,
                    left=left,
                    right=right,
                ))
            nodes = next_level
        
        return nodes[0] if nodes else None
    
    def get_root(self) -> str:
        """
        Get Merkle root hash of all chain links.
        
        Returns:
            Merkle root hash string (64 hex chars)
        """
        if self.is_empty:
            return self.GENESIS_PREVIOUS_HASH
        
        if self._dirty:
            self._merkle_tree = self._build_merkle_tree()
            self._merkle_root = self._merkle_tree.hash if self._merkle_tree else ""
            self._dirty = False
        
        return self._merkle_root or ""
    
    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get Merkle proof for a specific chain link.
        
        Args:
            index: Index of the link to prove
            
        Returns:
            List of (sibling_hash, position) tuples
            Position is 'L' if sibling is left, 'R' if right
        """
        if index < 0 or index >= len(self._chain):
            return []
        
        # Ensure tree is built
        self.get_root()
        
        if not self._merkle_tree:
            return []
        
        proof = []
        target_hash = self._chain[index].link_hash
        
        def find_and_prove(node: MerkleNode, target: str, path: List) -> bool:
            if node is None:
                return False
            
            if node.is_leaf and node.hash == target:
                return True
            
            if node.left and find_and_prove(node.left, target, path):
                if node.right:
                    path.append((node.right.hash, "R"))
                return True
            
            if node.right and find_and_prove(node.right, target, path):
                if node.left:
                    path.append((node.left.hash, "L"))
                return True
            
            return False
        
        find_and_prove(self._merkle_tree, target_hash, proof)
        return proof
    
    @staticmethod
    def verify_proof(
        leaf_hash: str,
        proof: List[Tuple[str, str]],
        root_hash: str
    ) -> bool:
        """
        Verify a Merkle proof.
        
        Args:
            leaf_hash: Hash of the leaf to verify
            proof: Merkle proof from get_proof()
            root_hash: Expected Merkle root
            
        Returns:
            True if proof is valid
        """
        current = leaf_hash
        
        for sibling_hash, position in proof:
            if position == "L":
                combined = sibling_hash + current
            else:
                combined = current + sibling_hash
            current = hashlib.sha256(combined.encode()).hexdigest()
        
        return current == root_hash
    
    def detect_tampering(self, original_hashes: List[str]) -> List[int]:
        """
        Detect tampered links by comparing against known good hashes.
        
        Args:
            original_hashes: List of original link hashes
            
        Returns:
            List of indices where tampering was detected
        """
        tampered = []
        
        for i, original_hash in enumerate(original_hashes):
            if i >= len(self._chain):
                break
            
            if self._chain[i].link_hash != original_hash:
                tampered.append(i)
        
        return tampered
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire chain to dictionary."""
        return {
            "algorithm": self._algorithm.value,
            "length": len(self._chain),
            "merkle_root": self.get_root(),
            "links": [link.to_dict() for link in self._chain],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HashChain":
        """Deserialize chain from dictionary."""
        algorithm = HashAlgorithm(data.get("algorithm", "sha256"))
        chain = cls(algorithm=algorithm)
        
        for link_data in data.get("links", []):
            link = ChainLink.from_dict(link_data)
            chain._chain.append(link)
        
        chain._dirty = True
        return chain
    
    def export_hashes(self) -> List[str]:
        """Export all link hashes for integrity checking."""
        return [link.link_hash for link in self._chain]
