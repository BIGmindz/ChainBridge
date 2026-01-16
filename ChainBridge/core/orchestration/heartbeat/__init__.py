"""
ChainBridge Heartbeat System
============================

Real-time execution visibility for OCC governance.

PAC Reference: PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM
PAC Reference: PAC-P745-OCC-HEARTBEAT-PERSISTENCE-AUDIT
Classification: LAW_TIER
Invariant: Operator Visibility Mandatory

Exports:
    - HeartbeatEmitter: Core heartbeat generation
    - HeartbeatEvent: Event data structure
    - HeartbeatStream: SSE stream manager
    - LifecycleBindings: WRAP/BER event bindings
    - HeartbeatEventStore: Append-only persistent storage
    - HashChainManager: Cryptographic chain integrity
    - AuditBindingManager: BER/Ledger audit bindings
"""

from .heartbeat_emitter import (
    HeartbeatEmitter,
    HeartbeatEvent,
    HeartbeatEventType,
    HeartbeatStream,
    get_emitter,
)
from .lifecycle_bindings import LifecycleBindings
from .event_store import (
    HeartbeatEventStore,
    StoredEvent,
    RetentionPolicy,
    get_event_store,
)
from .hash_chain import (
    HashChainManager,
    ChainBlock,
    get_chain_manager,
)
from .audit_bindings import (
    AuditBindingManager,
    AuditSnapshot,
    get_binding_manager,
)

__all__ = [
    # Core heartbeat
    "HeartbeatEmitter",
    "HeartbeatEvent",
    "HeartbeatEventType",
    "HeartbeatStream",
    "get_emitter",
    "LifecycleBindings",
    # Persistence
    "HeartbeatEventStore",
    "StoredEvent",
    "RetentionPolicy",
    "get_event_store",
    # Hash chain
    "HashChainManager",
    "ChainBlock",
    "get_chain_manager",
    # Audit bindings
    "AuditBindingManager",
    "AuditSnapshot",
    "get_binding_manager",
]
