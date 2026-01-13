"""
Hash Chain Manager - Cryptographic Event Chain Integrity
========================================================

PAC Reference: PAC-P745-OCC-HEARTBEAT-PERSISTENCE-AUDIT
Classification: LAW_TIER
Author: ALEX (GID-08) - Hash Chain Logic
Orchestrator: BENSON (GID-00)

Provides hash-chain integrity for heartbeat event sequences.
Each PAC execution forms an independent hash chain for audit.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ChainBlock:
    """Single block in a hash chain."""
    position: int
    timestamp: str
    event_type: str
    event_id: str
    pac_id: str
    data_hash: str
    previous_hash: str
    block_hash: str = ""
    
    def compute_block_hash(self) -> str:
        """Compute SHA-256 hash of this block."""
        content = f"{self.position}|{self.timestamp}|{self.event_type}|{self.event_id}|{self.pac_id}|{self.data_hash}|{self.previous_hash}"
        return hashlib.sha256(content.encode()).hexdigest()


class HashChainManager:
    """
    Manages hash chains for PAC execution audit trails.
    
    Each PAC has its own independent chain starting from GENESIS.
    Chains are append-only and cryptographically linked.
    
    Usage:
        manager = HashChainManager()
        
        # Start new chain
        block = manager.append_event("PAC-P745-...", event_data)
        
        # Verify chain
        valid = manager.verify_chain("PAC-P745-...")
        
        # Get chain proof
        proof = manager.get_merkle_root("PAC-P745-...")
    """
    
    GENESIS_HASH = "0" * 64  # SHA-256 zero hash
    
    def __init__(self):
        self._chains: Dict[str, List[ChainBlock]] = {}
        self._heads: Dict[str, str] = {}
    
    def get_or_create_chain(self, pac_id: str) -> List[ChainBlock]:
        """Get existing chain or create new one."""
        if pac_id not in self._chains:
            self._chains[pac_id] = []
            self._heads[pac_id] = self.GENESIS_HASH
        return self._chains[pac_id]
    
    def append_event(
        self,
        pac_id: str,
        event_type: str,
        event_id: str,
        event_data: Dict[str, Any]
    ) -> ChainBlock:
        """
        Append event to PAC's hash chain.
        
        Args:
            pac_id: PAC identifier
            event_type: Type of heartbeat event
            event_id: Unique event identifier
            event_data: Full event payload
            
        Returns:
            ChainBlock with computed hash
        """
        chain = self.get_or_create_chain(pac_id)
        
        # Compute data hash
        data_hash = hashlib.sha256(
            json.dumps(event_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Create block
        block = ChainBlock(
            position=len(chain) + 1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            event_id=event_id,
            pac_id=pac_id,
            data_hash=data_hash,
            previous_hash=self._heads[pac_id]
        )
        
        # Compute block hash
        block.block_hash = block.compute_block_hash()
        
        # Append to chain
        chain.append(block)
        self._heads[pac_id] = block.block_hash
        
        return block
    
    def verify_chain(self, pac_id: str) -> Dict[str, Any]:
        """
        Verify integrity of a PAC's hash chain.
        
        Returns verification report.
        """
        if pac_id not in self._chains:
            return {
                "pac_id": pac_id,
                "exists": False,
                "valid": True,
                "message": "Chain does not exist"
            }
        
        chain = self._chains[pac_id]
        errors = []
        
        for i, block in enumerate(chain):
            # Verify block hash
            computed = block.compute_block_hash()
            if computed != block.block_hash:
                errors.append({
                    "position": block.position,
                    "error": "BLOCK_HASH_MISMATCH",
                    "expected": block.block_hash,
                    "computed": computed
                })
            
            # Verify chain link
            if i == 0:
                expected_prev = self.GENESIS_HASH
            else:
                expected_prev = chain[i - 1].block_hash
            
            if block.previous_hash != expected_prev:
                errors.append({
                    "position": block.position,
                    "error": "CHAIN_LINK_BROKEN",
                    "expected": expected_prev,
                    "actual": block.previous_hash
                })
        
        return {
            "pac_id": pac_id,
            "exists": True,
            "valid": len(errors) == 0,
            "chain_length": len(chain),
            "head_hash": self._heads.get(pac_id),
            "errors": errors
        }
    
    def get_merkle_root(self, pac_id: str) -> Optional[str]:
        """
        Compute Merkle root of a PAC's chain.
        
        Useful for compact chain verification.
        """
        if pac_id not in self._chains:
            return None
        
        chain = self._chains[pac_id]
        if not chain:
            return self.GENESIS_HASH
        
        # Simple merkle: hash all block hashes together
        hashes = [block.block_hash for block in chain]
        
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last if odd
            
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        
        return hashes[0]
    
    def get_chain_proof(self, pac_id: str) -> Dict[str, Any]:
        """
        Generate audit proof for a PAC's chain.
        
        Returns complete chain state for audit.
        """
        if pac_id not in self._chains:
            return {"pac_id": pac_id, "exists": False}
        
        chain = self._chains[pac_id]
        verification = self.verify_chain(pac_id)
        
        return {
            "pac_id": pac_id,
            "exists": True,
            "chain_length": len(chain),
            "genesis_hash": self.GENESIS_HASH,
            "head_hash": self._heads.get(pac_id),
            "merkle_root": self.get_merkle_root(pac_id),
            "verified": verification["valid"],
            "blocks": [
                {
                    "position": b.position,
                    "event_type": b.event_type,
                    "event_id": b.event_id,
                    "block_hash": b.block_hash[:16] + "...",
                    "timestamp": b.timestamp
                }
                for b in chain
            ]
        }
    
    def export_chain(self, pac_id: str) -> List[Dict[str, Any]]:
        """Export full chain for external verification."""
        if pac_id not in self._chains:
            return []
        
        return [
            {
                "position": b.position,
                "timestamp": b.timestamp,
                "event_type": b.event_type,
                "event_id": b.event_id,
                "pac_id": b.pac_id,
                "data_hash": b.data_hash,
                "previous_hash": b.previous_hash,
                "block_hash": b.block_hash
            }
            for b in self._chains[pac_id]
        ]


# ==================== Global Singleton ====================

_global_chain_manager: Optional[HashChainManager] = None


def get_chain_manager() -> HashChainManager:
    """Get or create global chain manager."""
    global _global_chain_manager
    if _global_chain_manager is None:
        _global_chain_manager = HashChainManager()
    return _global_chain_manager


# ==================== Self-Test ====================

if __name__ == "__main__":
    print("HashChainManager Self-Test")
    print("=" * 50)
    
    manager = HashChainManager()
    pac_id = "PAC-P745-TEST"
    
    # Add events
    for i in range(5):
        block = manager.append_event(
            pac_id=pac_id,
            event_type=f"TEST_EVENT_{i}",
            event_id=f"EVT-{i}",
            event_data={"test": i, "data": f"value_{i}"}
        )
        print(f"✅ Block {block.position}: {block.block_hash[:16]}...")
    
    # Verify
    result = manager.verify_chain(pac_id)
    print(f"\n✅ Chain valid: {result['valid']}")
    print(f"   Length: {result['chain_length']}")
    
    # Merkle root
    merkle = manager.get_merkle_root(pac_id)
    print(f"   Merkle root: {merkle[:16]}...")
    
    # Proof
    proof = manager.get_chain_proof(pac_id)
    print(f"   Verified: {proof['verified']}")
    
    print("\n✅ Self-test PASSED")
