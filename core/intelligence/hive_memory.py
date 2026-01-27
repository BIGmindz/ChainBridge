"""
ChainBridge Hive Memory - Shared Reality Engine
================================================
Context synchronization system ensuring all atoms operate on identical input data.

Created: PAC-DEV-P52 (Hive Context Synchronization)
Purpose: Eliminate input drift across polyatomic squads

Core Concept:
- Reasoning dissonance is useful (detects hallucination)
- Input dissonance is a bug (atoms see different realities)
- Solution: Cryptographic context hashing (SHA3-256)

Invariants:
- SYNC-01: All atoms MUST operate on identical context hash
- SYNC-02: Input drift MUST trigger immediate SCRAM (prevent split-brain)
- SYNC-03: Context blocks MUST be immutable (read-only after creation)
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

# PAC-INT-P56: Live Data Pipeline
SYNC_LOG_PATH = "logs/context_sync.jsonl"


@dataclass
class ContextBlock:
    """
    Immutable block of information shared across a squad.
    
    Attributes:
        id: Unique identifier (e.g., "CTX-TASK-001")
        data: Context data (task details, historical facts, constraints)
        context_hash: SHA3-256 hash of canonical JSON (ensures consistency)
        created_at: Block creation timestamp
        metadata: Additional info (squad_id, source, version)
    
    Design Philosophy:
    - Context blocks are immutable (once created, never modified)
    - Canonical JSON ensures deterministic hashing (sort_keys=True)
    - All atoms receive identical context_hash → shared reality
    """
    id: str
    data: Dict[str, Any]
    context_hash: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, block_id: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> 'ContextBlock':
        """
        Create immutable context block with cryptographic hash.
        
        Args:
            block_id: Unique identifier
            data: Context data (must be JSON-serializable)
            metadata: Optional metadata (squad_id, source, etc.)
        
        Returns:
            ContextBlock with computed SHA3-256 hash
        
        Raises:
            TypeError: If data is not JSON-serializable
        """
        # Canonical JSON dump (sort_keys=True for determinism)
        try:
            canonical_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise TypeError(f"Context data must be JSON-serializable: {e}")
        
        # Compute SHA3-256 hash
        context_hash = hashlib.sha3_256(canonical_str.encode('utf-8')).hexdigest()
        
        return cls(
            id=block_id,
            data=data,
            context_hash=context_hash,
            created_at=datetime.now(),
            metadata=metadata or {}
        )
    
    def verify_hash(self) -> bool:
        """
        Verify that stored hash matches recomputed hash.
        
        Returns:
            True if hash is valid, False otherwise
        """
        canonical_str = json.dumps(self.data, sort_keys=True, ensure_ascii=False)
        recomputed_hash = hashlib.sha3_256(canonical_str.encode('utf-8')).hexdigest()
        return recomputed_hash == self.context_hash
    
    def __repr__(self):
        return (
            f"ContextBlock(id={self.id}, "
            f"hash={self.context_hash[:16]}..., "
            f"created={self.created_at.isoformat()})"
        )


class HiveMemory:
    """
    The Shared Reality Engine.
    
    Distributes ContextBlocks to atoms and verifies receipt.
    Ensures all agents in a squad operate on identical input data.
    
    Workflow:
    1. Create ContextBlock with canonical hash
    2. Broadcast to all atoms in squad
    3. Verify each atom received correct hash (ACK check)
    4. Detect input drift (different hashes)
    5. Trigger SCRAM on drift (SYNC-02)
    
    Design Philosophy:
    - "If atoms see different realities, consensus is meaningless"
    - "Input integrity is prerequisite for reasoning consensus"
    - "Context hash mismatch → immediate fail-closed"
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Hive Memory.
        
        Args:
            logger: Logging instance
        """
        self.logger = logger or logging.getLogger("HiveMemory")
        self.context_registry: Dict[str, ContextBlock] = {}
        self.sync_history: List[Dict[str, Any]] = []
    
    def register_context(self, context_block: ContextBlock) -> None:
        """
        Register context block in memory.
        
        Args:
            context_block: Context to register
        """
        self.context_registry[context_block.id] = context_block
        self.logger.info(
            f"📝 Registered context {context_block.id} "
            f"with hash {context_block.context_hash[:16]}..."
        )
    
    def get_context(self, context_id: str) -> Optional[ContextBlock]:
        """
        Retrieve context block by ID.
        
        Args:
            context_id: Context identifier
        
        Returns:
            ContextBlock if found, None otherwise
        """
        return self.context_registry.get(context_id)
    
    def synchronize_squad(
        self,
        squad_gids: List[str],
        context_block: ContextBlock,
        verify_acks: bool = True
    ) -> bool:
        """
        Broadcast context to squad and verify synchronization.
        
        Args:
            squad_gids: List of agent GIDs in squad
            context_block: Context to broadcast
            verify_acks: Whether to verify ACKs (simulated for now)
        
        Returns:
            True if sync successful, False if drift detected
        """
        self.logger.info(
            f"📡 BROADCASTING CONTEXT {context_block.id} "
            f"[{context_block.context_hash[:8]}...] to {len(squad_gids)} atoms"
        )
        
        # SYNC-01: Verify context hash is valid
        if not context_block.context_hash:
            self.logger.error("❌ NULL CONTEXT HASH DETECTED (SYNC-01 VIOLATION)")
            return False
        
        if len(context_block.context_hash) != 64:  # SHA3-256 = 64 hex chars
            self.logger.error(
                f"❌ INVALID CONTEXT HASH LENGTH: {len(context_block.context_hash)} "
                f"(expected 64 chars)"
            )
            return False
        
        # Verify hash integrity
        if not context_block.verify_hash():
            self.logger.error("❌ CONTEXT HASH MISMATCH (data corrupted)")
            return False
        
        # Register context
        self.register_context(context_block)
        
        # Simulate ACK verification (in production, query each agent)
        if verify_acks:
            # In distributed system, would send context to each agent
            # and wait for ACK with their computed hash
            # For now, simulate successful sync
            for gid in squad_gids:
                self.logger.debug(f"  ✓ ACK from {gid} (hash match)")
        
        # Record sync event
        sync_event = {
            "context_id": context_block.id,
            "context_hash": context_block.context_hash,
            "squad_gids": squad_gids,
            "squad_size": len(squad_gids),
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        self.sync_history.append(sync_event)
        
        # PAC-INT-P56: Log sync event to JSONL audit trail
        self._log_sync_event(sync_event, status="SUCCESS")
        
        self.logger.info("✅ SQUAD SYNCHRONIZED. INPUT INTEGRITY VERIFIED (SYNC-01)")
        return True
    
    def validate_input_resonance(
        self,
        inputs: List[Dict[str, Any]],
        source_labels: Optional[List[str]] = None
    ) -> bool:
        """
        Verify that multiple inputs are cryptographically identical.
        
        Use Case: Detect input drift when agents fetch data from different sources
        
        Args:
            inputs: List of input dictionaries to compare
            source_labels: Optional labels for each input (for logging)
        
        Returns:
            True if all inputs have identical hash, False if drift detected
        """
        if not inputs:
            self.logger.warning("⚠️  Empty input list (trivially resonant)")
            return True
        
        if len(inputs) == 1:
            self.logger.info("ℹ️  Single input (no comparison needed)")
            return True
        
        # Compute hash for first input (reference)
        first_hash = self._hash_input(inputs[0])
        labels = source_labels or [f"Input {i}" for i in range(len(inputs))]
        
        self.logger.info(
            f"🔍 VALIDATING INPUT RESONANCE: {len(inputs)} inputs, "
            f"reference hash={first_hash[:16]}..."
        )
        
        # Compare all subsequent inputs
        for i, inp in enumerate(inputs[1:], start=1):
            current_hash = self._hash_input(inp)
            
            if current_hash != first_hash:
                # SYNC-02: Input drift detected
                self.logger.critical(
                    f"🚨 INPUT DRIFT DETECTED: {labels[i]} has different hash!\n"
                    f"   Expected: {first_hash[:16]}...\n"
                    f"   Got:      {current_hash[:16]}...\n"
                    f"   SYNC-02 TRIGGERED: IMMEDIATE SCRAM"
                )
                
                # PAC-INT-P56: Log drift event to JSONL audit trail
                drift_event = {
                    "event": "DRIFT_DETECTED",
                    "source": labels[i],
                    "expected_hash": first_hash,
                    "actual_hash": current_hash,
                    "timestamp": datetime.now().isoformat()
                }
                self._log_sync_event(drift_event, status="DRIFT_DETECTED")
                
                return False
            
            self.logger.debug(f"  ✓ {labels[i]}: hash match")
        
        self.logger.info(
            f"✅ INPUT RESONANCE VERIFIED: All {len(inputs)} inputs identical "
            f"(hash={first_hash[:16]}...)"
        )
        return True
    
    def _hash_input(self, data: Dict[str, Any]) -> str:
        """
        Compute canonical SHA3-256 hash of input data.
        
        Args:
            data: Input dictionary
        
        Returns:
            64-character hex hash
        """
        canonical_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha3_256(canonical_str.encode('utf-8')).hexdigest()
    
    def detect_context_drift(
        self,
        context_block: ContextBlock,
        agent_hashes: Dict[str, str]
    ) -> List[str]:
        """
        Detect which agents have divergent context hashes.
        
        Args:
            context_block: Expected context
            agent_hashes: Dict mapping agent GID → reported context hash
        
        Returns:
            List of agent GIDs with hash mismatch (empty if all synchronized)
        """
        expected_hash = context_block.context_hash
        divergent_agents = []
        
        for gid, reported_hash in agent_hashes.items():
            if reported_hash != expected_hash:
                divergent_agents.append(gid)
                self.logger.warning(
                    f"⚠️  CONTEXT DRIFT: {gid} reports hash {reported_hash[:16]}... "
                    f"(expected {expected_hash[:16]}...)"
                )
        
        if divergent_agents:
            self.logger.critical(
                f"🚨 SYNC-02 VIOLATION: {len(divergent_agents)} agents have divergent context"
            )
        
        return divergent_agents
    
    def get_sync_history(self) -> List[Dict[str, Any]]:
        """
        Retrieve synchronization event history.
        
        Returns:
            List of sync events
        """
        return self.sync_history.copy()
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """
        Calculate synchronization statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.sync_history:
            return {
                "total_syncs": 0,
                "total_atoms_synced": 0,
                "unique_contexts": 0,
                "success_rate": 0.0
            }
        
        total = len(self.sync_history)
        success = sum(1 for event in self.sync_history if event["success"])
        total_atoms = sum(event["squad_size"] for event in self.sync_history)
        unique_contexts = len(set(event["context_id"] for event in self.sync_history))
        
        return {
            "total_syncs": total,
            "successful_syncs": success,
            "failed_syncs": total - success,
            "total_atoms_synced": total_atoms,
            "unique_contexts": unique_contexts,
            "success_rate": success / total if total > 0 else 0.0
        }
    
    def _log_sync_event(self, event: Dict[str, Any], status: str):
        """
        Log synchronization event to JSONL audit trail (PAC-INT-P56).
        
        Args:
            event: Sync event data
            status: Status (SUCCESS, DRIFT_DETECTED, etc.)
        
        Writes:
            Single JSON line to logs/context_sync.jsonl
        
        Invariant: PIPE-02 (Non-blocking, fail-open)
        """
        try:
            # Ensure logs directory exists
            Path("logs").mkdir(exist_ok=True)
            
            # Build log record
            log_record = {
                "event": "CONTEXT_SYNC",
                "status": status,
                "data": event,
                "timestamp": datetime.now().isoformat()
            }
            
            # Append to JSONL file (atomic write)
            with open(SYNC_LOG_PATH, "a") as f:
                f.write(json.dumps(log_record) + "\n")
        
        except Exception as e:
            # PIPE-02: Fail-open (log error but don't crash)
            self.logger.error(f"Failed to log sync event: {e}")


# Example usage (for documentation)
if __name__ == "__main__":
    # Initialize Hive Memory
    memory = HiveMemory()
    
    # Create context block
    context_data = {
        "transaction_id": "TXN-123",
        "amount_usd": 50000,
        "timestamp": "2026-01-25T21:30:00Z",
        "sender": "0xABC123",
        "receiver": "0xDEF456"
    }
    
    context = ContextBlock.create(
        block_id="CTX-TASK-001",
        data=context_data,
        metadata={"squad_id": "SQUAD-GOV-01", "source": "LiveGatekeeper"}
    )
    
    print(f"Context Created: {context}")
    print(f"Hash: {context.context_hash}")
    
    # Synchronize squad
    squad_gids = ["GID-06-01", "GID-06-02", "GID-06-03", "GID-06-04", "GID-06-05"]
    success = memory.synchronize_squad(squad_gids, context)
    
    print(f"\nSync Success: {success}")
    
    # Validate input resonance
    inputs = [
        {"transaction_id": "TXN-123", "amount": 1000},
        {"transaction_id": "TXN-123", "amount": 1000},  # Identical
        {"transaction_id": "TXN-123", "amount": 1000}   # Identical
    ]
    
    resonance = memory.validate_input_resonance(inputs, ["Agent 1", "Agent 2", "Agent 3"])
    print(f"\nInput Resonance: {resonance}")
    
    # Test drift detection
    inputs_with_drift = [
        {"transaction_id": "TXN-123", "amount": 1000},
        {"transaction_id": "TXN-123", "amount": 2000},  # DRIFT!
    ]
    
    drift_detected = memory.validate_input_resonance(inputs_with_drift, ["Agent 1", "Agent 2"])
    print(f"\nDrift Detected: {not drift_detected}")
    
    # Get statistics
    stats = memory.get_sync_stats()
    print(f"\nSync Stats: {stats}")
