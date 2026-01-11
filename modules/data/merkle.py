#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     DATA MERKLE - THE FINGERPRINT                            ║
║                   PAC-DATA-P340-STATE-REPLICATION                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  SHA-256 Merkle Tree for State Verification                                  ║
║                                                                              ║
║  "Truth is not what you say; it is what you can prove."                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Merkle module provides:
  - SHA-256 based Merkle Tree construction
  - Efficient state root computation
  - Inclusion proof generation and verification
  - Deterministic hashing for consistency

INVARIANTS:
  INV-DATA-001 (Universal Truth): At Index N, the State Root Hash MUST be
                                  identical on all nodes.
  INV-DATA-003 (Hash Collision): SHA-256 guarantees negligible collision.

Usage:
    from modules.data.merkle import MerkleTree, MerkleProof
    
    # Build tree from data
    tree = MerkleTree()
    tree.build(["Alice:100", "Bob:200", "Carol:300"])
    
    # Get state root
    root = tree.root_hash
    
    # Generate inclusion proof
    proof = tree.generate_proof(1)  # Proof for "Bob:200"
    
    # Verify proof
    is_valid = MerkleTree.verify_proof("Bob:200", proof, root)
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

__version__ = "3.0.0"


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

HASH_ALGORITHM = "sha256"
EMPTY_HASH = hashlib.sha256(b"").hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# MERKLE PROOF
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MerkleProof:
    """
    Proof of inclusion in a Merkle Tree.
    
    Contains the sibling hashes needed to reconstruct the root.
    """
    
    leaf_index: int
    leaf_hash: str
    proof_hashes: List[Tuple[str, str]]  # List of (hash, position: 'L' or 'R')
    root_hash: str
    tree_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "leaf_index": self.leaf_index,
            "leaf_hash": self.leaf_hash,
            "proof_hashes": self.proof_hashes,
            "root_hash": self.root_hash,
            "tree_size": self.tree_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MerkleProof":
        """Deserialize from dictionary."""
        return cls(
            leaf_index=data["leaf_index"],
            leaf_hash=data["leaf_hash"],
            proof_hashes=[tuple(p) for p in data["proof_hashes"]],
            root_hash=data["root_hash"],
            tree_size=data["tree_size"]
        )


# ══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE
# ══════════════════════════════════════════════════════════════════════════════

class MerkleTree:
    """
    SHA-256 Merkle Tree for state verification.
    
    INV-DATA-001: Same leaves in same order produce identical root.
    
    The tree is built bottom-up:
      1. Hash each leaf
      2. Pair adjacent hashes
      3. Hash pairs to create parent
      4. Repeat until root
    
    If odd number of nodes at a level, duplicate the last one.
    """
    
    def __init__(self):
        """Initialize empty Merkle Tree."""
        self._leaves: List[str] = []          # Original leaf data
        self._leaf_hashes: List[str] = []     # Hashed leaves
        self._tree: List[List[str]] = []      # Full tree structure (levels)
        self._root_hash: str = EMPTY_HASH
    
    @staticmethod
    def hash(data: Union[str, bytes]) -> str:
        """
        Compute SHA-256 hash of data.
        
        Deterministic: same input always produces same output.
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def hash_pair(left: str, right: str) -> str:
        """Hash two children to create parent node."""
        combined = left + right
        return MerkleTree.hash(combined)
    
    @property
    def root_hash(self) -> str:
        """Get the Merkle root hash."""
        return self._root_hash
    
    @property
    def leaf_count(self) -> int:
        """Get number of leaves."""
        return len(self._leaves)
    
    @property
    def height(self) -> int:
        """Get tree height (number of levels)."""
        return len(self._tree)
    
    def build(self, leaves: List[str]) -> str:
        """
        Build Merkle Tree from leaf data.
        
        INV-DATA-001: Deterministic build - same leaves = same root.
        
        Args:
            leaves: List of data strings to include
            
        Returns:
            Root hash of the tree
        """
        if not leaves:
            self._leaves = []
            self._leaf_hashes = []
            self._tree = []
            self._root_hash = EMPTY_HASH
            return self._root_hash
        
        # Store original leaves
        self._leaves = list(leaves)
        
        # Hash all leaves
        self._leaf_hashes = [self.hash(leaf) for leaf in leaves]
        
        # Build tree bottom-up
        self._tree = [self._leaf_hashes[:]]
        current_level = self._leaf_hashes[:]
        
        while len(current_level) > 1:
            next_level = []
            
            # Pad with duplicate if odd
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])
            
            # Hash pairs
            for i in range(0, len(current_level), 2):
                parent = self.hash_pair(current_level[i], current_level[i + 1])
                next_level.append(parent)
            
            self._tree.append(next_level)
            current_level = next_level
        
        self._root_hash = current_level[0] if current_level else EMPTY_HASH
        return self._root_hash
    
    def build_from_dict(self, state: Dict[str, Any], sort_keys: bool = True) -> str:
        """
        Build Merkle Tree from a state dictionary.
        
        Deterministic: keys are sorted for consistent ordering.
        
        Args:
            state: Dictionary of key-value pairs
            sort_keys: Whether to sort keys (default True for determinism)
            
        Returns:
            Root hash
        """
        if sort_keys:
            keys = sorted(state.keys())
        else:
            keys = list(state.keys())
        
        leaves = [f"{k}:{json.dumps(state[k], sort_keys=True)}" for k in keys]
        return self.build(leaves)
    
    def generate_proof(self, leaf_index: int) -> MerkleProof:
        """
        Generate inclusion proof for a leaf.
        
        Args:
            leaf_index: Index of leaf to prove
            
        Returns:
            MerkleProof object
            
        Raises:
            IndexError: If index out of range
        """
        if leaf_index < 0 or leaf_index >= len(self._leaves):
            raise IndexError(f"Leaf index {leaf_index} out of range [0, {len(self._leaves)})")
        
        proof_hashes = []
        current_index = leaf_index
        
        # Walk up the tree
        for level in range(len(self._tree) - 1):
            level_hashes = self._tree[level]
            
            # Handle padding
            if len(level_hashes) % 2 == 1:
                level_hashes = level_hashes + [level_hashes[-1]]
            
            # Get sibling
            if current_index % 2 == 0:
                # Current is left, sibling is right
                sibling_index = current_index + 1
                position = "R"
            else:
                # Current is right, sibling is left
                sibling_index = current_index - 1
                position = "L"
            
            sibling_hash = level_hashes[sibling_index]
            proof_hashes.append((sibling_hash, position))
            
            # Move to parent index
            current_index = current_index // 2
        
        return MerkleProof(
            leaf_index=leaf_index,
            leaf_hash=self._leaf_hashes[leaf_index],
            proof_hashes=proof_hashes,
            root_hash=self._root_hash,
            tree_size=len(self._leaves)
        )
    
    @staticmethod
    def verify_proof(
        leaf_data: str,
        proof: MerkleProof,
        expected_root: Optional[str] = None
    ) -> bool:
        """
        Verify an inclusion proof.
        
        Args:
            leaf_data: Original leaf data
            proof: MerkleProof to verify
            expected_root: Optional root to verify against (uses proof.root_hash if None)
            
        Returns:
            True if proof is valid
        """
        # Hash the leaf
        current_hash = MerkleTree.hash(leaf_data)
        
        # Verify leaf hash matches
        if current_hash != proof.leaf_hash:
            return False
        
        # Walk up the proof
        for sibling_hash, position in proof.proof_hashes:
            if position == "L":
                # Sibling is on left
                current_hash = MerkleTree.hash_pair(sibling_hash, current_hash)
            else:
                # Sibling is on right
                current_hash = MerkleTree.hash_pair(current_hash, sibling_hash)
        
        # Check against expected root
        target_root = expected_root if expected_root else proof.root_hash
        return current_hash == target_root
    
    def get_leaf(self, index: int) -> str:
        """Get leaf data at index."""
        return self._leaves[index]
    
    def get_leaf_hash(self, index: int) -> str:
        """Get leaf hash at index."""
        return self._leaf_hashes[index]
    
    def get_level(self, level: int) -> List[str]:
        """Get all hashes at a level (0 = leaves)."""
        return self._tree[level] if level < len(self._tree) else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tree to dictionary."""
        return {
            "root_hash": self._root_hash,
            "leaf_count": len(self._leaves),
            "height": len(self._tree),
            "leaves": self._leaves,
            "tree": self._tree
        }
    
    def __repr__(self) -> str:
        return f"MerkleTree(root={self._root_hash[:16]}..., leaves={len(self._leaves)})"


# ══════════════════════════════════════════════════════════════════════════════
# STATE ROOT CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

class StateRootCalculator:
    """
    Calculates deterministic state root from account balances.
    
    INV-DATA-001: Same balances = same root on every node.
    """
    
    @staticmethod
    def calculate_root(balances: Dict[str, int]) -> str:
        """
        Calculate state root from account balances.
        
        Deterministic: accounts are sorted alphabetically.
        
        Args:
            balances: Dict mapping account_id → balance
            
        Returns:
            State root hash
        """
        if not balances:
            return EMPTY_HASH
        
        # Sort accounts for determinism
        sorted_accounts = sorted(balances.keys())
        
        # Build leaves: "account:balance"
        leaves = [f"{account}:{balances[account]}" for account in sorted_accounts]
        
        # Build tree and get root
        tree = MerkleTree()
        return tree.build(leaves)
    
    @staticmethod
    def calculate_root_with_proof(
        balances: Dict[str, int],
        account: str
    ) -> Tuple[str, Optional[MerkleProof]]:
        """
        Calculate state root and generate proof for an account.
        
        Args:
            balances: Dict mapping account_id → balance
            account: Account to generate proof for
            
        Returns:
            Tuple of (root_hash, proof or None if account not found)
        """
        if not balances:
            return EMPTY_HASH, None
        
        sorted_accounts = sorted(balances.keys())
        leaves = [f"{acc}:{balances[acc]}" for acc in sorted_accounts]
        
        tree = MerkleTree()
        root = tree.build(leaves)
        
        # Find account index
        try:
            index = sorted_accounts.index(account)
            proof = tree.generate_proof(index)
            return root, proof
        except ValueError:
            return root, None


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate merkle module."""
    print("=" * 70)
    print("DATA MERKLE v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Basic tree construction
    print("\n[1/6] Testing basic tree construction...")
    tree = MerkleTree()
    leaves = ["Alice:100", "Bob:200", "Carol:300", "Dave:400"]
    root = tree.build(leaves)
    
    assert root != EMPTY_HASH, "Root should not be empty"
    assert tree.leaf_count == 4, "Should have 4 leaves"
    assert tree.height > 0, "Should have height > 0"
    
    print(f"      ✓ Built tree with {tree.leaf_count} leaves")
    print(f"      ✓ Root: {root[:32]}...")
    print(f"      ✓ Height: {tree.height}")
    
    # Test 2: Determinism
    print("\n[2/6] Testing determinism (INV-DATA-001)...")
    tree2 = MerkleTree()
    root2 = tree2.build(leaves)
    
    assert root == root2, "Same leaves should produce same root"
    
    # Different order = different root
    tree3 = MerkleTree()
    root3 = tree3.build(["Bob:200", "Alice:100", "Carol:300", "Dave:400"])
    assert root != root3, "Different order should produce different root"
    
    print(f"      ✓ Same leaves → same root: VERIFIED")
    print(f"      ✓ Different order → different root: VERIFIED")
    
    # Test 3: Proof generation
    print("\n[3/6] Testing proof generation...")
    proof = tree.generate_proof(1)  # Bob's proof
    
    assert proof.leaf_index == 1
    assert proof.root_hash == root
    assert len(proof.proof_hashes) > 0
    
    print(f"      ✓ Generated proof for leaf 1")
    print(f"      ✓ Proof has {len(proof.proof_hashes)} hashes")
    
    # Test 4: Proof verification
    print("\n[4/6] Testing proof verification...")
    is_valid = MerkleTree.verify_proof("Bob:200", proof)
    assert is_valid, "Valid proof should verify"
    
    # Tampered data should fail
    is_invalid = MerkleTree.verify_proof("Bob:201", proof)
    assert not is_invalid, "Tampered data should fail"
    
    print(f"      ✓ Valid proof verified: True")
    print(f"      ✓ Tampered data rejected: True")
    
    # Test 5: State root calculation
    print("\n[5/6] Testing state root calculation...")
    balances = {
        "ACCT-001": 1000,
        "ACCT-002": 2000,
        "ACCT-003": 500
    }
    
    state_root = StateRootCalculator.calculate_root(balances)
    
    # Same balances on different "node" should produce same root
    state_root_2 = StateRootCalculator.calculate_root(balances.copy())
    assert state_root == state_root_2, "Same balances should produce same root"
    
    print(f"      ✓ State root: {state_root[:32]}...")
    print(f"      ✓ Deterministic across nodes: VERIFIED")
    
    # Test 6: Odd number of leaves
    print("\n[6/6] Testing odd number of leaves...")
    tree_odd = MerkleTree()
    root_odd = tree_odd.build(["A", "B", "C"])
    
    assert root_odd != EMPTY_HASH
    
    # Proofs should still work
    for i in range(3):
        proof = tree_odd.generate_proof(i)
        is_valid = MerkleTree.verify_proof(["A", "B", "C"][i], proof)
        assert is_valid, f"Proof for leaf {i} should verify"
    
    print(f"      ✓ Odd leaves handled correctly")
    print(f"      ✓ All proofs valid for odd tree")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-DATA-001 (Universal Truth): ENFORCED")
    print("INV-DATA-003 (Hash Collision): SHA-256 ACTIVE")
    print("=" * 70)
    print("\n🌳 The Fingerprint is ready. Every state has a unique identity.")


if __name__ == "__main__":
    _self_test()
