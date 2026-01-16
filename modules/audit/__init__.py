"""
Immutable Audit Storage Module
==============================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE

Provides tamper-evident, append-only audit logging with cryptographic
hash chaining for compliance and security requirements.

COMPONENTS:
- hash_chain: SHA-256 hash chaining with Merkle tree support
- timestamp_authority: Monotonic trusted timestamp generation
- event_schema: Canonical AuditEvent dataclass with serialization
- immutable_store: Append-only storage with chain integration
- storage_backend: File system persistence with rotation/archival

INVARIANTS ENFORCED:
- INV-AUDIT-001: Hash chain detects any tampering
- INV-AUDIT-002: Storage is append-only (no delete/update)
- INV-AUDIT-003: Timestamps increase monotonically
- INV-AUDIT-004: Events serialize without data loss
- INV-AUDIT-005: Backend handles rotation and archival

COMPLIANCE:
- SOC2 Type II AU-11: 90-day minimum retention
- GDPR Article 30: Processing activity records
- HIPAA 164.312(b): Audit controls

Example usage:
    from modules.audit import (
        ImmutableAuditStore,
        AuditEvent,
        EventType,
        EventSeverity,
        create_auth_event,
    )
    
    # Create store
    store = ImmutableAuditStore()
    
    # Log authentication event
    event = create_auth_event(
        action="login",
        actor_id="user-123",
        actor_type="user",
        success=True,
    )
    
    stored = store.write(event)
    print(f"Stored at index {stored.storage_index}")
    print(f"Merkle root: {store.merkle_root}")
    
    # Verify integrity
    is_valid, _ = store.verify()
    assert is_valid
"""

from .hash_chain import (
    HashChain,
    ChainLink,
    MerkleNode,
    HashAlgorithm,
)

from .timestamp_authority import (
    TimestampAuthority,
    TimestampRecord,
    TimestampFormat,
    get_timestamp_authority,
)

from .event_schema import (
    AuditEvent,
    EventActor,
    EventTarget,
    EventType,
    EventSeverity,
    EventOutcome,
    create_auth_event,
    create_access_event,
    create_security_event,
)

from .immutable_store import (
    ImmutableAuditStore,
    StoredEvent,
    StorageStats,
    ImmutabilityViolationError,
    StorageError,
)

from .storage_backend import (
    FileSystemBackend,
    StorageConfig,
    FileManifest,
    BackendError,
    RotationError,
)

__all__ = [
    # Hash Chain
    "HashChain",
    "ChainLink",
    "MerkleNode",
    "HashAlgorithm",
    
    # Timestamp
    "TimestampAuthority",
    "TimestampRecord",
    "TimestampFormat",
    "get_timestamp_authority",
    
    # Event Schema
    "AuditEvent",
    "EventActor",
    "EventTarget",
    "EventType",
    "EventSeverity",
    "EventOutcome",
    "create_auth_event",
    "create_access_event",
    "create_security_event",
    
    # Immutable Store
    "ImmutableAuditStore",
    "StoredEvent",
    "StorageStats",
    "ImmutabilityViolationError",
    "StorageError",
    
    # Storage Backend
    "FileSystemBackend",
    "StorageConfig",
    "FileManifest",
    "BackendError",
    "RotationError",
]

__version__ = "1.0.0"
__pac__ = "PAC-SEC-P822-A"
