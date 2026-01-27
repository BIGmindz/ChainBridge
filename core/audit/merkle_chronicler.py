"""
PAC-AUDIT-P70: The Immutable Chronicle
========================================
Merkle Tree-based log anchoring system for tamper-evident audit trails.

Purpose: Convert linear JSONL logs into cryptographic Merkle trees where any
         modification to history breaks the root hash.

Created: PAC-AUDIT-P70 (Immutable Chronicle Construction)
Updated: 2026-01-25

Invariants:
- HIST-01: The Merkle Root MUST change if a single byte of log history is modified
- HIST-02: All Anchors MUST be published to the Ledger (Simulated)

Design Philosophy:
- "The past cannot be rewritten without detection"
- "Every log line is a leaf; every tree is a proof"
- "Tamper once, invalidate forever"
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class MerkleChronicler:
    """
    The Historian - Immutable Log Anchoring via Merkle Trees.
    
    Converts linear JSONL audit logs into cryptographic Merkle trees,
    ensuring that any modification to historical data is immediately detectable
    via root hash verification.
    
    Workflow:
    1. Read JSONL log files line-by-line
    2. Hash each line to create leaf nodes (double SHA3-256)
    3. Build Merkle tree bottom-up (pair-wise hashing)
    4. Compute root hash (cryptographic anchor)
    5. Publish anchor to ledger (simulated)
    6. Store anchors for future verification
    
    Tamper Detection:
    - Original root: abc123...
    - After 1 byte change: def456... (collision-resistant)
    - Probability of undetected tamper: ~2^-256 (SHA3-256 security)
    
    Usage:
        chronicler = MerkleChronicler([
            "logs/legion_audit.jsonl",
            "logs/hive_consensus.jsonl"
        ])
        anchors = chronicler.anchor_logs()
        # anchors["logs/legion_audit.jsonl"]["merkle_root"] = "abc123..."
    """
    
    def __init__(
        self,
        log_paths: List[str],
        anchor_output_path: Optional[str] = "logs/merkle_anchors.json",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Merkle Chronicler.
        
        Args:
            log_paths: List of JSONL log files to anchor
            anchor_output_path: Where to store anchor records
            logger: Logging instance
        """
        self.log_paths = log_paths
        self.anchor_output_path = anchor_output_path
        self.logger = logger or logging.getLogger("MerkleChronicler")
        self.anchors: Dict[str, Any] = {}
    
    def _hash_leaf(self, data: str) -> str:
        """
        Hash a single data item using double SHA3-256.
        
        Double hashing provides additional resistance against:
        - Length extension attacks
        - Collision attacks on first hash layer
        
        Args:
            data: String to hash (typically a JSONL line)
            
        Returns:
            64-character hex hash
        """
        # First hash
        h1 = hashlib.sha3_256(data.encode('utf-8')).digest()
        # Second hash (on raw bytes)
        h2 = hashlib.sha3_256(h1).hexdigest()
        return h2
    
    def _build_tree(self, leaves: List[str]) -> Tuple[str, List[List[str]]]:
        """
        Build Merkle tree from leaf hashes.
        
        Algorithm:
        1. Start with leaf layer (hashes of log lines)
        2. If odd count, duplicate last element
        3. Pair-wise hash: hash(left + right)
        4. Repeat until single root remains
        
        Args:
            leaves: List of leaf hashes (from _hash_leaf)
            
        Returns:
            Tuple of (root_hash, tree_layers) for proof generation
        """
        if not leaves:
            empty_hash = hashlib.sha3_256(b"EMPTY_TREE").hexdigest()
            self.logger.warning("Building tree with no leaves - returning EMPTY_TREE hash")
            return empty_hash, [[empty_hash]]
        
        # Track all layers for proof construction
        tree_layers = [leaves.copy()]
        current_layer = leaves
        
        while len(current_layer) > 1:
            # Pad with duplicate if odd count
            if len(current_layer) % 2 != 0:
                current_layer.append(current_layer[-1])
            
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1]
                # Combine and hash
                combined = left + right
                parent_hash = self._hash_leaf(combined)
                next_layer.append(parent_hash)
            
            tree_layers.append(next_layer)
            current_layer = next_layer
        
        root_hash = current_layer[0]
        return root_hash, tree_layers
    
    def anchor_logs(self) -> Dict[str, Any]:
        """
        Anchor all configured log files via Merkle tree construction.
        
        For each log file:
        1. Read all lines
        2. Hash each line (leaf nodes)
        3. Build Merkle tree
        4. Record root hash + metadata
        
        Returns:
            Dictionary mapping log paths to anchor records:
            {
                "logs/hive_consensus.jsonl": {
                    "line_count": 150,
                    "merkle_root": "abc123...",
                    "status": "ANCHORED",
                    "timestamp": "2026-01-25T12:00:00Z",
                    "leaf_count": 150,
                    "tree_depth": 8
                }
            }
        """
        self.logger.info(f"🔒 ANCHORING {len(self.log_paths)} log files via Merkle trees...")
        
        anchors = {}
        total_lines = 0
        
        for path in self.log_paths:
            self.logger.info(f"Processing: {path}")
            
            if not os.path.exists(path):
                self.logger.warning(f"⚠️  File not found: {path}")
                anchors[path] = {
                    "status": "FILE_MISSING",
                    "error": "Log file does not exist",
                    "timestamp": datetime.now().isoformat()
                }
                continue
            
            # Read log lines
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
            except Exception as e:
                self.logger.error(f"❌ Failed to read {path}: {e}")
                anchors[path] = {
                    "status": "READ_ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                continue
            
            if not lines:
                self.logger.warning(f"⚠️  File is empty: {path}")
                anchors[path] = {
                    "status": "EMPTY_FILE",
                    "line_count": 0,
                    "merkle_root": hashlib.sha3_256(b"EMPTY_TREE").hexdigest(),
                    "timestamp": datetime.now().isoformat()
                }
                continue
            
            # Hash every line to create leaf nodes
            self.logger.debug(f"  Hashing {len(lines)} lines...")
            leaves = [self._hash_leaf(line) for line in lines]
            
            # Build Merkle tree
            root_hash, tree_layers = self._build_tree(leaves)
            tree_depth = len(tree_layers)
            
            self.logger.info(
                f"  ✅ Merkle Root: {root_hash[:16]}... "
                f"({len(lines)} leaves, depth {tree_depth})"
            )
            
            # Record anchor
            anchors[path] = {
                "line_count": len(lines),
                "leaf_count": len(leaves),
                "merkle_root": root_hash,
                "tree_depth": tree_depth,
                "status": "ANCHORED",
                "timestamp": datetime.now().isoformat(),
                "file_size_bytes": os.path.getsize(path)
            }
            
            total_lines += len(lines)
        
        # Store anchors
        self.anchors = anchors
        
        # Persist to disk
        if self.anchor_output_path:
            self._save_anchors()
        
        self.logger.info(
            f"🔒 ANCHORING COMPLETE: {len(anchors)} files, "
            f"{total_lines} total lines anchored"
        )
        
        return anchors
    
    def verify_log(self, path: str, expected_root: Optional[str] = None) -> bool:
        """
        Verify that a log file has not been tampered with.
        
        Args:
            path: Path to log file
            expected_root: Expected Merkle root (from previous anchor)
                          If None, uses stored anchor
        
        Returns:
            True if log matches expected root, False if tampered
        """
        if expected_root is None:
            if path not in self.anchors:
                self.logger.error(f"No anchor found for {path}")
                return False
            expected_root = self.anchors[path]["merkle_root"]
        
        # Recompute current root
        if not os.path.exists(path):
            self.logger.error(f"File missing: {path}")
            return False
        
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        leaves = [self._hash_leaf(line) for line in lines]
        current_root, _ = self._build_tree(leaves)
        
        matches = (current_root == expected_root)
        
        if matches:
            self.logger.info(f"✅ VERIFICATION PASSED: {path} (root matches)")
        else:
            self.logger.error(
                f"❌ TAMPER DETECTED: {path}\n"
                f"   Expected: {expected_root}\n"
                f"   Current:  {current_root}\n"
                f"   HIST-01 VIOLATION: Log has been modified!"
            )
        
        return matches
    
    def _save_anchors(self) -> None:
        """
        Persist anchor records to disk.
        
        HIST-02 enforcement: Simulates ledger publication.
        """
        os.makedirs(os.path.dirname(self.anchor_output_path), exist_ok=True)
        
        anchor_record = {
            "pac_id": "PAC-AUDIT-P70",
            "generated_at": datetime.now().isoformat(),
            "total_files": len(self.anchors),
            "anchors": self.anchors
        }
        
        with open(self.anchor_output_path, 'w', encoding='utf-8') as f:
            json.dump(anchor_record, f, indent=2)
        
        self.logger.info(f"📝 Anchors persisted to {self.anchor_output_path}")
    
    def load_anchors(self, anchor_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load previously saved anchors from disk.
        
        Args:
            anchor_path: Path to anchor file (defaults to self.anchor_output_path)
        
        Returns:
            Dictionary of anchors
        """
        path = anchor_path or self.anchor_output_path
        
        if not os.path.exists(path):
            self.logger.warning(f"No anchor file found at {path}")
            return {}
        
        with open(path, 'r', encoding='utf-8') as f:
            record = json.load(f)
        
        self.anchors = record.get("anchors", {})
        self.logger.info(f"📂 Loaded {len(self.anchors)} anchors from {path}")
        
        return self.anchors
    
    def generate_merkle_proof(self, path: str, line_index: int) -> Optional[List[str]]:
        """
        Generate Merkle proof for a specific log line.
        
        Proof = path from leaf to root (sibling hashes needed for verification).
        
        Args:
            path: Log file path
            line_index: Index of line to prove (0-based)
        
        Returns:
            List of sibling hashes (proof path), or None if invalid
        """
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if line_index >= len(lines):
            self.logger.error(f"Line index {line_index} out of range (max {len(lines)-1})")
            return None
        
        leaves = [self._hash_leaf(line) for line in lines]
        root, tree_layers = self._build_tree(leaves)
        
        # Build proof path
        proof = []
        current_index = line_index
        
        for layer in tree_layers[:-1]:  # Exclude root layer
            if current_index % 2 == 0:
                # Left child - need right sibling
                sibling_index = current_index + 1
            else:
                # Right child - need left sibling
                sibling_index = current_index - 1
            
            if sibling_index < len(layer):
                proof.append(layer[sibling_index])
            else:
                # Padding case (odd count)
                proof.append(layer[current_index])
            
            current_index //= 2
        
        return proof


# Singleton instance for application-wide use
_global_chronicler: Optional[MerkleChronicler] = None


def get_global_chronicler(log_paths: Optional[List[str]] = None) -> MerkleChronicler:
    """
    Get or create the global MerkleChronicler instance.
    
    Args:
        log_paths: Paths to anchor (only used on first call)
    
    Returns:
        MerkleChronicler instance
    """
    global _global_chronicler
    if _global_chronicler is None:
        default_paths = [
            "logs/legion_audit.jsonl",
            "logs/hive_consensus.jsonl",
            "logs/context_sync.jsonl"
        ]
        paths = log_paths or default_paths
        _global_chronicler = MerkleChronicler(paths)
    return _global_chronicler
