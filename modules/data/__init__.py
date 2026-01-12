"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE DATA MODULE                                  ║
║                   PAC-DATA-P340-STATE-REPLICATION                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Phase 3: THE MESH - Data Integrity Layer                                    ║
║                                                                              ║
║  "Truth is not what you say; it is what you can prove."                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Data Module ensures:
  - Merkle Tree verification of state
  - State replication across the federation
  - Deterministic transaction application
  - Root hash consistency

Components:
  - merkle.py: The Fingerprint (SHA-256 Merkle Trees)
  - replication.py: The Bridge (Raft Log → Ledger State)

INVARIANTS:
  INV-DATA-001 (Universal Truth): State Root must match across all nodes
  INV-DATA-002 (Atomic Application): Log entries fully applied or not at all

TRAINING SIGNAL:
  "The Parliament's Laws are now written in Stone across the Realm."
"""

__version__ = "3.2.0"
__phase__ = "THE_MESH"

from .merkle import MerkleTree, MerkleProof
from .replication import ReplicationEngine, StateSnapshot
from .sharding import TenantShard, ShardManager, ShardConfig, ShardState
from .schemas import (
    TransactionSchema, AuditLogSchema, ProofReceipt,
    PIIHasher, SchemaRegistry, SchemaVersion,
)
from .sxt_bridge import (
    SxTBridge, SxTConfig, AsyncAnchor, AnchorRequest, AnchorState,
    create_sxt_bridge,
)

__all__ = [
    "MerkleTree",
    "MerkleProof",
    "ReplicationEngine",
    "StateSnapshot",
    # P920 Sharding
    "TenantShard",
    "ShardManager",
    "ShardConfig",
    "ShardState",
    # P930 SxT Bridge
    "SxTBridge",
    "SxTConfig",
    "AsyncAnchor",
    "AnchorRequest",
    "AnchorState",
    "create_sxt_bridge",
    # Schemas
    "TransactionSchema",
    "AuditLogSchema",
    "ProofReceipt",
    "PIIHasher",
    "SchemaRegistry",
    "SchemaVersion",
]
