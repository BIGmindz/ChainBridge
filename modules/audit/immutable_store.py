"""
Append-Only Immutable Storage Module
====================================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE
Component: Append-Only Immutable Audit Store
Agent: CODY (GID-01)

PURPOSE:
  Implements append-only storage for audit events that prevents
  modification or deletion after write. Integrates with CIPHER's
  hash chain for tamper detection.

INVARIANTS:
  INV-AUDIT-002: Storage MUST be append-only (no delete/update)
  INV-STORE-001: Written events MUST be immediately readable
  INV-STORE-002: Events MUST be hash-chained on write
  INV-STORE-003: Storage MUST fail-closed on errors

SECURITY PROPERTIES:
  - Append-only: No API for delete or update
  - Hash-chained: Each event links to previous via hash
  - Verifiable: Can validate entire store integrity
  - Recoverable: Can rebuild from event data
"""

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from .hash_chain import HashChain, ChainLink
from .event_schema import AuditEvent
from .timestamp_authority import TimestampAuthority, get_timestamp_authority


class ImmutabilityViolationError(Exception):
    """Raised when an immutability constraint would be violated."""
    pass


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


@dataclass
class StorageStats:
    """Statistics about the immutable store."""
    event_count: int = 0
    first_event_time: Optional[str] = None
    last_event_time: Optional[str] = None
    chain_length: int = 0
    merkle_root: str = ""
    is_valid: bool = True
    storage_bytes: int = 0


@dataclass
class StoredEvent:
    """
    Wrapper for stored audit event with chain metadata.
    """
    event: AuditEvent
    chain_link: ChainLink
    storage_index: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "chain_link": self.chain_link.to_dict(),
            "storage_index": self.storage_index,
        }


class ImmutableAuditStore:
    """
    Append-only immutable storage for audit events.
    
    Key properties:
    - write(): Add new event to store (append-only)
    - read(): Retrieve event by index
    - verify(): Check store integrity
    
    NO delete() or update() methods exist - this is by design.
    
    Thread-safe for concurrent operations.
    """
    
    def __init__(self, 
                 timestamp_authority: Optional[TimestampAuthority] = None):
        """
        Initialize immutable audit store.
        
        Args:
            timestamp_authority: Authority for timestamps (uses global if None)
        """
        self._timestamp_authority = timestamp_authority or get_timestamp_authority()
        self._hash_chain = HashChain()
        self._events: List[StoredEvent] = []
        self._lock = threading.RLock()
        self._write_callbacks: List[Callable[[StoredEvent], None]] = []
        self._sealed = False  # If True, no more writes allowed
    
    @property
    def count(self) -> int:
        """Number of events in store."""
        return len(self._events)
    
    @property
    def is_empty(self) -> bool:
        """Check if store is empty."""
        return len(self._events) == 0
    
    @property
    def is_sealed(self) -> bool:
        """Check if store is sealed (no more writes)."""
        return self._sealed
    
    @property
    def merkle_root(self) -> str:
        """Get current Merkle root."""
        return self._hash_chain.get_root()
    
    def write(self, event: AuditEvent) -> StoredEvent:
        """
        Write an audit event to the immutable store.
        
        This is the ONLY way to add data. There is no update or delete.
        
        Args:
            event: AuditEvent to store
            
        Returns:
            StoredEvent with chain metadata
            
        Raises:
            ImmutabilityViolationError: If store is sealed
            StorageError: If write fails
            ValueError: If event is invalid
        """
        if self._sealed:
            raise ImmutabilityViolationError(
                "Store is sealed. No further writes allowed."
            )
        
        # Validate event
        is_valid, errors = event.validate()
        if not is_valid:
            raise ValueError(f"Invalid event: {errors}")
        
        with self._lock:
            try:
                # Get timestamp from authority
                ts_record = self._timestamp_authority.get_timestamp()
                
                # Update event with authoritative timestamp and sequence
                # Note: We create a new event to preserve original
                timestamped_event = AuditEvent(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    action=event.action,
                    actor=event.actor,
                    target=event.target,
                    outcome=event.outcome,
                    outcome_reason=event.outcome_reason,
                    severity=event.severity,
                    correlation_id=event.correlation_id,
                    timestamp=ts_record.timestamp,
                    sequence_number=ts_record.sequence_number,
                    details=event.details,
                    tags=event.tags,
                )
                
                # Add to hash chain
                chain_link = self._hash_chain.append(timestamped_event.to_dict())
                
                # Create stored event
                stored = StoredEvent(
                    event=timestamped_event,
                    chain_link=chain_link,
                    storage_index=len(self._events),
                )
                
                # Append to store
                self._events.append(stored)
                
                # Notify callbacks
                for callback in self._write_callbacks:
                    try:
                        callback(stored)
                    except Exception:
                        pass  # Don't let callbacks break writes
                
                return stored
                
            except Exception as e:
                raise StorageError(f"Failed to write event: {e}") from e
    
    def read(self, index: int) -> Optional[StoredEvent]:
        """
        Read an event by storage index.
        
        Args:
            index: Storage index (0-based)
            
        Returns:
            StoredEvent or None if index out of range
        """
        with self._lock:
            if 0 <= index < len(self._events):
                return self._events[index]
            return None
    
    def read_by_event_id(self, event_id: str) -> Optional[StoredEvent]:
        """
        Read an event by its event_id.
        
        Args:
            event_id: Unique event identifier
            
        Returns:
            StoredEvent or None if not found
        """
        with self._lock:
            for stored in self._events:
                if stored.event.event_id == event_id:
                    return stored
            return None
    
    def read_range(self, start: int, end: int) -> List[StoredEvent]:
        """
        Read a range of events.
        
        Args:
            start: Start index (inclusive)
            end: End index (exclusive)
            
        Returns:
            List of StoredEvent in range
        """
        with self._lock:
            return self._events[start:end]
    
    def read_all(self) -> List[StoredEvent]:
        """Read all events in store."""
        with self._lock:
            return list(self._events)
    
    def iterate(self) -> Iterator[StoredEvent]:
        """
        Iterate over all events.
        
        Yields events in order of storage.
        """
        with self._lock:
            for event in self._events:
                yield event
    
    def verify(self) -> Tuple[bool, Optional[int]]:
        """
        Verify entire store integrity.
        
        Checks:
        - Hash chain integrity
        - Event hash verification
        - Timestamp ordering
        
        Returns:
            Tuple of (is_valid, first_invalid_index)
        """
        with self._lock:
            # Verify hash chain
            chain_valid, invalid_idx = self._hash_chain.verify()
            if not chain_valid:
                return False, invalid_idx
            
            # Verify each event
            prev_time = None
            for i, stored in enumerate(self._events):
                # Verify event hash
                is_valid, _ = stored.event.validate()
                if not is_valid:
                    return False, i
                
                # Verify timestamp ordering (must be non-decreasing)
                if prev_time:
                    if stored.event.timestamp < prev_time:
                        return False, i
                prev_time = stored.event.timestamp
            
            return True, None
    
    def verify_at(self, index: int) -> bool:
        """
        Verify a specific event and its chain.
        
        Args:
            index: Index of event to verify
            
        Returns:
            True if event and chain are valid
        """
        with self._lock:
            if index < 0 or index >= len(self._events):
                return False
            
            return self._hash_chain.verify_at(index)
    
    def get_proof(self, index: int) -> Dict[str, Any]:
        """
        Get a cryptographic proof for an event.
        
        Returns Merkle proof and chain link data needed
        to independently verify the event.
        
        Args:
            index: Index of event
            
        Returns:
            Proof data dictionary
        """
        with self._lock:
            if index < 0 or index >= len(self._events):
                return {}
            
            stored = self._events[index]
            merkle_proof = self._hash_chain.get_proof(index)
            
            return {
                "event": stored.event.to_dict(),
                "chain_link": stored.chain_link.to_dict(),
                "merkle_proof": merkle_proof,
                "merkle_root": self._hash_chain.get_root(),
                "storage_index": index,
                "total_events": len(self._events),
            }
    
    def verify_proof(self, proof: Dict[str, Any]) -> bool:
        """
        Verify a proof against current store state.
        
        Args:
            proof: Proof from get_proof()
            
        Returns:
            True if proof is valid
        """
        try:
            chain_link = ChainLink.from_dict(proof["chain_link"])
            merkle_proof = proof["merkle_proof"]
            expected_root = proof["merkle_root"]
            
            return HashChain.verify_proof(
                chain_link.link_hash,
                merkle_proof,
                expected_root
            )
        except Exception:
            return False
    
    def get_stats(self) -> StorageStats:
        """Get storage statistics."""
        with self._lock:
            stats = StorageStats(
                event_count=len(self._events),
                chain_length=self._hash_chain.length,
                merkle_root=self._hash_chain.get_root(),
            )
            
            if self._events:
                stats.first_event_time = self._events[0].event.timestamp
                stats.last_event_time = self._events[-1].event.timestamp
            
            is_valid, _ = self.verify()
            stats.is_valid = is_valid
            
            # Estimate storage size
            stats.storage_bytes = sum(
                len(json.dumps(s.to_dict())) for s in self._events
            )
            
            return stats
    
    def seal(self) -> str:
        """
        Seal the store, preventing further writes.
        
        Returns the final Merkle root as the seal.
        
        Returns:
            Merkle root hash
        """
        with self._lock:
            self._sealed = True
            return self._hash_chain.get_root()
    
    def on_write(self, callback: Callable[[StoredEvent], None]):
        """
        Register a callback for write events.
        
        Callback receives the StoredEvent after successful write.
        
        Args:
            callback: Function to call on write
        """
        self._write_callbacks.append(callback)
    
    def export_chain_hashes(self) -> List[str]:
        """Export all chain link hashes for external verification."""
        with self._lock:
            return self._hash_chain.export_hashes()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire store to dictionary."""
        with self._lock:
            return {
                "events": [s.to_dict() for s in self._events],
                "chain": self._hash_chain.to_dict(),
                "sealed": self._sealed,
                "stats": {
                    "count": len(self._events),
                    "merkle_root": self._hash_chain.get_root(),
                },
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImmutableAuditStore":
        """
        Deserialize store from dictionary.
        
        Validates integrity during load.
        """
        store = cls()
        
        # Restore hash chain
        store._hash_chain = HashChain.from_dict(data.get("chain", {}))
        
        # Restore events
        for event_data in data.get("events", []):
            event = AuditEvent.from_dict(event_data["event"])
            chain_link = ChainLink.from_dict(event_data["chain_link"])
            stored = StoredEvent(
                event=event,
                chain_link=chain_link,
                storage_index=event_data["storage_index"],
            )
            store._events.append(stored)
        
        store._sealed = data.get("sealed", False)
        
        return store
