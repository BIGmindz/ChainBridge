"""
Unit Tests for Immutable Audit Storage
======================================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE
Component: Unit Test Suite
Agent: SENTINEL (GID-10)

Test Coverage Requirements:
- INV-AUDIT-001: Hash chain detects tampering
- INV-AUDIT-002: Storage is append-only
- INV-AUDIT-003: Timestamps increase monotonically
- INV-AUDIT-004: Events serialize without data loss
- INV-STORE-001: Written events immediately readable
- INV-STORE-002: Events hash-chained on write
- INV-STORE-003: Storage fails closed on errors

Target: 15+ tests, 100% module coverage
"""

import json
import pytest
import threading
import time
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, patch

# Import modules under test
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.audit.hash_chain import (
    HashChain,
    ChainLink,
    MerkleNode,
    HashAlgorithm,
)
from modules.audit.timestamp_authority import (
    TimestampAuthority,
    TimestampRecord,
    TimestampFormat,
    get_timestamp_authority,
)
from modules.audit.event_schema import (
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
from modules.audit.immutable_store import (
    ImmutableAuditStore,
    StoredEvent,
    StorageStats,
    ImmutabilityViolationError,
    StorageError,
)


# =============================================================================
# TEST: Hash Chain (CIPHER)
# =============================================================================

class TestHashChain:
    """Tests for HashChain tamper-evident structure."""
    
    def test_hash_chain_append(self):
        """Test appending data to hash chain."""
        chain = HashChain()
        
        link1 = chain.append({"action": "login", "user": "alice"})
        link2 = chain.append({"action": "logout", "user": "alice"})
        
        assert chain.length == 2
        assert link1.index == 0
        assert link2.index == 1
        assert link2.previous_hash == link1.link_hash
    
    def test_hash_chain_verify_intact(self):
        """Test verification of intact chain."""
        chain = HashChain()
        
        for i in range(10):
            chain.append({"event_id": i, "data": f"event_{i}"})
        
        is_valid, invalid_idx = chain.verify()
        assert is_valid
        assert invalid_idx is None
    
    def test_hash_chain_detect_tampering(self):
        """INV-AUDIT-001: Hash chain MUST detect tampering."""
        chain = HashChain()
        
        chain.append({"action": "deposit", "amount": 100})
        chain.append({"action": "deposit", "amount": 200})
        chain.append({"action": "withdrawal", "amount": 50})
        
        # Simulate tampering by modifying internal data
        # Note: In production, chain data is immutable
        original_hash = chain._chain[1].link_hash
        chain._chain[1] = ChainLink(
            index=1,
            timestamp=chain._chain[1].timestamp,
            data_hash="tampered_hash",
            previous_hash=chain._chain[0].link_hash,
            link_hash="tampered_link_hash",
        )
        
        is_valid, invalid_idx = chain.verify()
        assert not is_valid
        assert invalid_idx == 1 or invalid_idx == 2  # Detects at tampered or next
    
    def test_merkle_root(self):
        """Test Merkle root computation."""
        chain = HashChain()
        
        chain.append({"id": 1})
        root1 = chain.get_root()
        
        chain.append({"id": 2})
        root2 = chain.get_root()
        
        assert root1 != root2  # Root changes with new data
        assert len(root1) == 64  # SHA-256 hex
    
    def test_merkle_proof(self):
        """Test Merkle proof generation and verification."""
        chain = HashChain()
        
        for i in range(8):
            chain.append({"index": i})
        
        root = chain.get_root()
        proof = chain.get_proof(3)
        
        # Verify proof
        is_valid = HashChain.verify_proof(
            chain._chain[3].link_hash,
            proof,
            root
        )
        assert is_valid


# =============================================================================
# TEST: Timestamp Authority (CHRONOS)
# =============================================================================

class TestTimestampAuthority:
    """Tests for monotonic timestamp generation."""
    
    def test_timestamp_monotonic(self):
        """INV-AUDIT-003: Timestamps MUST increase monotonically."""
        authority = TimestampAuthority()
        
        timestamps = []
        for _ in range(100):
            record = authority.get_timestamp()
            timestamps.append(record.timestamp)
        
        # Verify strictly increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i-1], \
                f"Timestamp at {i} not greater than {i-1}"
    
    def test_timestamp_sequence_numbers(self):
        """Test sequence number increments."""
        authority = TimestampAuthority()
        
        seq_nums = []
        for _ in range(50):
            record = authority.get_timestamp()
            seq_nums.append(record.sequence_number)
        
        # Verify sequential
        for i in range(1, len(seq_nums)):
            assert seq_nums[i] == seq_nums[i-1] + 1
    
    def test_timestamp_thread_safety(self):
        """Test thread-safe timestamp generation."""
        authority = TimestampAuthority()
        records: List[TimestampRecord] = []
        lock = threading.Lock()
        
        def get_timestamps(count: int):
            for _ in range(count):
                record = authority.get_timestamp()
                with lock:
                    records.append(record)
        
        threads = [
            threading.Thread(target=get_timestamps, args=(100,))
            for _ in range(4)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify unique sequence numbers
        seq_nums = [r.sequence_number for r in records]
        assert len(seq_nums) == len(set(seq_nums))


# =============================================================================
# TEST: Event Schema (FORGE)
# =============================================================================

class TestEventSchema:
    """Tests for AuditEvent serialization."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        actor = EventActor(
            actor_id="user-123",
            actor_type="user",
            actor_name="Alice",
        )
        
        event = AuditEvent(
            event_id="evt-001",
            event_type=EventType.AUTHENTICATION,
            action="login",
            actor=actor,
            outcome=EventOutcome.SUCCESS,
            severity=EventSeverity.INFO,
        )
        
        assert event.event_id == "evt-001"
        assert event.event_type == EventType.AUTHENTICATION
        assert event.actor.actor_id == "user-123"
    
    def test_event_serialization_roundtrip(self):
        """INV-AUDIT-004: Events MUST serialize without data loss."""
        original = create_auth_event(
            action="mfa_verify",
            actor_id="user-456",
            outcome=EventOutcome.SUCCESS,
            details={"method": "totp", "device": "mobile"},
        )
        
        # Serialize
        event_dict = original.to_dict()
        json_str = original.to_json()
        
        # Deserialize
        from_dict = AuditEvent.from_dict(event_dict)
        from_json = AuditEvent.from_json(json_str)
        
        # Verify lossless
        assert from_dict.event_id == original.event_id
        assert from_dict.action == original.action
        assert from_dict.details == original.details
        
        assert from_json.event_id == original.event_id
        assert from_json.details["method"] == "totp"
    
    def test_event_validation(self):
        """Test event validation."""
        actor = EventActor(actor_id="user-1", actor_type="user")
        
        valid_event = AuditEvent(
            event_id="evt-valid",
            event_type=EventType.AUTHENTICATION,
            action="login",
            actor=actor,
            severity=EventSeverity.INFO,
        )
        
        is_valid, errors = valid_event.validate()
        assert is_valid
        assert not errors
    
    def test_factory_functions(self):
        """Test event factory functions."""
        auth_event = create_auth_event(
            action="login",
            actor_id="user-1",
            outcome=EventOutcome.SUCCESS,
        )
        assert auth_event.event_type == EventType.AUTHENTICATION
        
        access_event = create_access_event(
            action="read",
            actor_id="user-2",
            target_id="doc-123",
            target_type="document",
        )
        assert access_event.event_type == EventType.DATA_ACCESS
        
        security_event = create_security_event(
            action="intrusion_detected",
            actor_id="system",
            severity=EventSeverity.CRITICAL,
        )
        assert security_event.event_type == EventType.SECURITY


# =============================================================================
# TEST: Immutable Store (CODY)
# =============================================================================

class TestImmutableStore:
    """Tests for append-only immutable storage."""
    
    def test_store_write_read(self):
        """INV-STORE-001: Written events MUST be immediately readable."""
        store = ImmutableAuditStore()
        
        event = create_auth_event(
            action="login",
            actor_id="user-1",
            outcome=EventOutcome.SUCCESS,
        )
        
        stored = store.write(event)
        
        # Immediately readable
        read_back = store.read(stored.storage_index)
        assert read_back is not None
        assert read_back.event.event_id == event.event_id
    
    def test_store_append_only(self):
        """INV-AUDIT-002: Storage MUST be append-only."""
        store = ImmutableAuditStore()
        
        # Write 3 events
        for i in range(3):
            event = create_auth_event(
                action=f"action_{i}",
                actor_id=f"user-{i}",
                outcome=EventOutcome.SUCCESS,
            )
            store.write(event)
        
        # Verify no delete method
        assert not hasattr(store, 'delete')
        
        # Verify no update method
        assert not hasattr(store, 'update')
        
        # Can only read
        assert store.read(0) is not None
        assert store.read(1) is not None
        assert store.read(2) is not None
    
    def test_store_hash_chained(self):
        """INV-STORE-002: Events MUST be hash-chained on write."""
        store = ImmutableAuditStore()
        
        stored_events = []
        for i in range(5):
            event = create_auth_event(
                action=f"action_{i}",
                actor_id=f"user-{i}",
                outcome=EventOutcome.SUCCESS,
            )
            stored = store.write(event)
            stored_events.append(stored)
        
        # Verify chain links reference previous
        for i in range(1, len(stored_events)):
            current = stored_events[i].chain_link
            previous = stored_events[i-1].chain_link
            assert current.previous_hash == previous.link_hash
    
    def test_store_verify_integrity(self):
        """Test store integrity verification."""
        store = ImmutableAuditStore()
        
        for i in range(10):
            event = create_auth_event(
                action=f"action_{i}",
                actor_id=f"user-{i}",
                outcome=EventOutcome.SUCCESS,
            )
            store.write(event)
        
        is_valid, invalid_idx = store.verify()
        assert is_valid
        assert invalid_idx is None
    
    def test_store_seal(self):
        """Test sealing store prevents writes."""
        store = ImmutableAuditStore()
        
        event = create_auth_event(
            action="login",
            actor_id="user-1",
            outcome=EventOutcome.SUCCESS,
        )
        store.write(event)
        
        # Seal the store
        root = store.seal()
        assert root  # Returns merkle root
        assert store.is_sealed
        
        # Further writes should fail
        with pytest.raises(ImmutabilityViolationError):
            store.write(event)
    
    def test_store_proof_generation(self):
        """Test cryptographic proof generation."""
        store = ImmutableAuditStore()
        
        for i in range(8):
            event = create_auth_event(
                action=f"action_{i}",
                actor_id=f"user-{i}",
                outcome=EventOutcome.SUCCESS,
            )
            store.write(event)
        
        # Get proof for event at index 3
        proof = store.get_proof(3)
        
        assert "event" in proof
        assert "chain_link" in proof
        assert "merkle_proof" in proof
        assert "merkle_root" in proof
        
        # Verify proof
        is_valid = store.verify_proof(proof)
        assert is_valid
    
    def test_store_serialization(self):
        """Test store serialization/deserialization."""
        store = ImmutableAuditStore()
        
        for i in range(5):
            event = create_auth_event(
                action=f"action_{i}",
                actor_id=f"user-{i}",
                outcome=EventOutcome.SUCCESS,
            )
            store.write(event)
        
        # Serialize
        data = store.to_dict()
        
        # Deserialize
        restored = ImmutableAuditStore.from_dict(data)
        
        # Verify
        assert restored.count == store.count
        assert restored.merkle_root == store.merkle_root


# =============================================================================
# TEST: Integration
# =============================================================================

class TestIntegration:
    """Integration tests for complete audit pipeline."""
    
    def test_full_audit_pipeline(self):
        """Test complete audit event lifecycle."""
        store = ImmutableAuditStore()
        
        # 1. Create authentication event
        auth_event = create_auth_event(
            action="login",
            actor_id="user-integration",
            outcome=EventOutcome.SUCCESS,
            ip_address="192.168.1.1",
            details={"user_agent": "test-browser"},
        )
        
        # 2. Write to store
        stored_auth = store.write(auth_event)
        
        # 3. Create access event
        access_event = create_access_event(
            action="read",
            actor_id="user-integration",
            target_id="doc-123",
            target_type="document",
        )
        
        # 4. Write to store
        stored_access = store.write(access_event)
        
        # 5. Verify chain integrity
        is_valid, _ = store.verify()
        assert is_valid
        
        # 6. Get proof for auth event
        proof = store.get_proof(stored_auth.storage_index)
        assert store.verify_proof(proof)
        
        # 7. Get stats
        stats = store.get_stats()
        assert stats.event_count == 2
        assert stats.is_valid
    
    def test_concurrent_writes(self):
        """Test concurrent write safety."""
        store = ImmutableAuditStore()
        errors = []
        
        def write_events(count: int, prefix: str):
            try:
                for i in range(count):
                    event = create_auth_event(
                        action=f"{prefix}_action_{i}",
                        actor_id=f"{prefix}-user-{i}",
                        outcome=EventOutcome.SUCCESS,
                    )
                    store.write(event)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=write_events, args=(50, f"thread_{t}"))
            for t in range(4)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors
        assert store.count == 200
        
        # Verify integrity after concurrent writes
        is_valid, _ = store.verify()
        assert is_valid


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
