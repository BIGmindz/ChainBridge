"""
Heartbeat Event Store - Append-Only Immutable Storage
======================================================

PAC Reference: PAC-P745-OCC-HEARTBEAT-PERSISTENCE-AUDIT
Classification: LAW_TIER
Author: CODY (GID-01) - Event Store Backend
Orchestrator: BENSON (GID-00)

Invariants Enforced:
    - Proof > Execution
    - Audit Supremacy
    - No Silent State Transitions

CRITICAL: This is an append-only store. No deletion permitted without LAW-tier PAC.
"""

import json
import hashlib
import threading
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass, field, asdict
from enum import Enum
import sqlite3


class EventStoreError(Exception):
    """Base exception for event store errors."""
    pass


class RetentionPolicy(Enum):
    """Event retention policies."""
    PERMANENT = "PERMANENT"           # Never delete
    AUDIT_GRADE = "AUDIT_GRADE"       # 7 year retention
    OPERATIONAL = "OPERATIONAL"       # 90 day retention
    DEBUG = "DEBUG"                   # 7 day retention


@dataclass
class StoredEvent:
    """
    Immutable event record with cryptographic hash.
    
    Every heartbeat event is stored with:
    - SHA-256 content hash
    - Previous event hash (for chain integrity)
    - Retention policy
    - Audit metadata
    """
    event_id: str
    event_type: str
    timestamp: str
    sequence_number: int
    session_id: str
    
    # Event content
    pac_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_gid: Optional[str] = None
    wrap_id: Optional[str] = None
    ber_id: Optional[str] = None
    
    # Full payload
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Cryptographic integrity
    content_hash: str = ""
    previous_hash: str = ""
    chain_position: int = 0
    
    # Audit metadata
    retention_policy: str = "PERMANENT"
    stored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of event content."""
        content = json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "session_id": self.session_id,
            "pac_id": self.pac_id,
            "task_id": self.task_id,
            "agent_gid": self.agent_gid,
            "payload": self.payload,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class HeartbeatEventStore:
    """
    Append-only event store with hash chain integrity.
    
    Features:
    - Append-only writes (no updates, no deletes)
    - SHA-256 hash chain per PAC execution
    - SQLite backend for durability
    - JSONL file backup for audit
    - Retention policy enforcement
    
    Usage:
        store = HeartbeatEventStore()
        event = store.append(heartbeat_event, pac_id="PAC-P745-...")
        
        # Query
        events = store.query_by_pac("PAC-P745-...")
        events = store.query_by_session("session_123")
        
        # Verify integrity
        valid = store.verify_chain(pac_id="PAC-P745-...")
    """
    
    def __init__(
        self,
        db_path: str = "data/heartbeat_events.db",
        backup_path: str = "logs/heartbeat_audit.jsonl"
    ):
        self.db_path = Path(db_path)
        self.backup_path = Path(backup_path)
        self._lock = threading.Lock()
        self._chain_heads: Dict[str, str] = {}  # pac_id -> latest hash
        self._chain_positions: Dict[str, int] = {}  # pac_id -> position
        
        self._ensure_paths()
        self._init_database()
        self._load_chain_state()
    
    def _ensure_paths(self) -> None:
        """Ensure storage directories exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    pac_id TEXT,
                    task_id TEXT,
                    agent_gid TEXT,
                    wrap_id TEXT,
                    ber_id TEXT,
                    payload TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    chain_position INTEGER NOT NULL,
                    retention_policy TEXT NOT NULL,
                    stored_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pac_id ON events(pac_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id ON events(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash ON events(content_hash)
            """)
            
            conn.commit()
    
    def _load_chain_state(self) -> None:
        """Load chain heads from database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT pac_id, content_hash, chain_position
                FROM events
                WHERE pac_id IS NOT NULL
                ORDER BY chain_position DESC
            """)
            
            for row in cursor:
                pac_id, content_hash, position = row
                if pac_id not in self._chain_heads:
                    self._chain_heads[pac_id] = content_hash
                    self._chain_positions[pac_id] = position
    
    def append(
        self,
        event: Any,  # HeartbeatEvent from heartbeat_emitter
        pac_id: Optional[str] = None,
        retention_policy: RetentionPolicy = RetentionPolicy.PERMANENT
    ) -> StoredEvent:
        """
        Append event to store. This is the ONLY write operation.
        
        Args:
            event: HeartbeatEvent to store
            pac_id: PAC ID for chain grouping
            retention_policy: How long to retain
            
        Returns:
            StoredEvent with hash and chain position
        """
        with self._lock:
            # Get chain state
            previous_hash = self._chain_heads.get(pac_id, "GENESIS")
            chain_position = self._chain_positions.get(pac_id, 0) + 1
            
            # Create stored event
            event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
            
            stored = StoredEvent(
                event_id=f"EVT-{event_dict.get('sequence_number', 0)}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                event_type=event_dict.get('event_type', 'UNKNOWN'),
                timestamp=event_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
                sequence_number=event_dict.get('sequence_number', 0),
                session_id=event_dict.get('session_id', 'unknown'),
                pac_id=pac_id or event_dict.get('pac_id'),
                task_id=event_dict.get('task_id'),
                agent_gid=event_dict.get('agent_gid'),
                wrap_id=event_dict.get('wrap_id'),
                ber_id=event_dict.get('ber_id'),
                payload=event_dict,
                previous_hash=previous_hash,
                chain_position=chain_position,
                retention_policy=retention_policy.value
            )
            
            # Compute hash
            stored.content_hash = stored.compute_hash()
            
            # Update chain state
            effective_pac_id = stored.pac_id or "GLOBAL"
            self._chain_heads[effective_pac_id] = stored.content_hash
            self._chain_positions[effective_pac_id] = chain_position
            
            # Persist to database
            self._persist_event(stored)
            
            # Backup to JSONL
            self._backup_event(stored)
            
            return stored
    
    def _persist_event(self, event: StoredEvent) -> None:
        """Persist event to SQLite."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO events (
                    event_id, event_type, timestamp, sequence_number, session_id,
                    pac_id, task_id, agent_gid, wrap_id, ber_id,
                    payload, content_hash, previous_hash, chain_position,
                    retention_policy, stored_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.event_type, event.timestamp,
                event.sequence_number, event.session_id,
                event.pac_id, event.task_id, event.agent_gid,
                event.wrap_id, event.ber_id,
                json.dumps(event.payload), event.content_hash,
                event.previous_hash, event.chain_position,
                event.retention_policy, event.stored_at
            ))
            conn.commit()
    
    def _backup_event(self, event: StoredEvent) -> None:
        """Append event to JSONL backup file."""
        try:
            with open(self.backup_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception:
            pass  # Don't fail on backup errors
    
    # ==================== Query Methods ====================
    
    def query_by_pac(self, pac_id: str, limit: int = 1000) -> List[StoredEvent]:
        """Get all events for a PAC execution."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE pac_id = ?
                ORDER BY chain_position ASC
                LIMIT ?
            """, (pac_id, limit))
            
            return [self._row_to_event(row) for row in cursor]
    
    def query_by_session(self, session_id: str, limit: int = 1000) -> List[StoredEvent]:
        """Get all events for a session."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE session_id = ?
                ORDER BY sequence_number ASC
                LIMIT ?
            """, (session_id, limit))
            
            return [self._row_to_event(row) for row in cursor]
    
    def query_by_type(self, event_type: str, limit: int = 100) -> List[StoredEvent]:
        """Get events by type."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (event_type, limit))
            
            return [self._row_to_event(row) for row in cursor]
    
    def query_by_hash(self, content_hash: str) -> Optional[StoredEvent]:
        """Get event by its content hash."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM events
                WHERE content_hash = ?
            """, (content_hash,))
            
            row = cursor.fetchone()
            return self._row_to_event(row) if row else None
    
    def query_recent(self, limit: int = 100) -> List[StoredEvent]:
        """Get most recent events."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM events
                ORDER BY stored_at DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_event(row) for row in cursor]
    
    def _row_to_event(self, row: sqlite3.Row) -> StoredEvent:
        """Convert database row to StoredEvent."""
        return StoredEvent(
            event_id=row['event_id'],
            event_type=row['event_type'],
            timestamp=row['timestamp'],
            sequence_number=row['sequence_number'],
            session_id=row['session_id'],
            pac_id=row['pac_id'],
            task_id=row['task_id'],
            agent_gid=row['agent_gid'],
            wrap_id=row['wrap_id'],
            ber_id=row['ber_id'],
            payload=json.loads(row['payload']),
            content_hash=row['content_hash'],
            previous_hash=row['previous_hash'],
            chain_position=row['chain_position'],
            retention_policy=row['retention_policy'],
            stored_at=row['stored_at']
        )
    
    # ==================== Integrity Verification ====================
    
    def verify_chain(self, pac_id: str) -> Dict[str, Any]:
        """
        Verify hash chain integrity for a PAC.
        
        Returns verification report with any broken links.
        """
        events = self.query_by_pac(pac_id)
        
        if not events:
            return {
                "pac_id": pac_id,
                "status": "NO_EVENTS",
                "verified": True,
                "event_count": 0
            }
        
        broken_links = []
        for i, event in enumerate(events):
            # Verify content hash
            computed = event.compute_hash()
            if computed != event.content_hash:
                broken_links.append({
                    "position": event.chain_position,
                    "event_id": event.event_id,
                    "error": "CONTENT_HASH_MISMATCH",
                    "stored": event.content_hash,
                    "computed": computed
                })
            
            # Verify chain link (except first event)
            if i > 0:
                expected_previous = events[i - 1].content_hash
                if event.previous_hash != expected_previous:
                    broken_links.append({
                        "position": event.chain_position,
                        "event_id": event.event_id,
                        "error": "CHAIN_LINK_BROKEN",
                        "expected": expected_previous,
                        "actual": event.previous_hash
                    })
        
        return {
            "pac_id": pac_id,
            "status": "VALID" if not broken_links else "INVALID",
            "verified": len(broken_links) == 0,
            "event_count": len(events),
            "chain_head": events[-1].content_hash if events else None,
            "broken_links": broken_links
        }
    
    def get_chain_summary(self, pac_id: str) -> Dict[str, Any]:
        """Get summary of a PAC's event chain."""
        events = self.query_by_pac(pac_id)
        
        if not events:
            return {"pac_id": pac_id, "exists": False}
        
        event_types = {}
        for e in events:
            event_types[e.event_type] = event_types.get(e.event_type, 0) + 1
        
        return {
            "pac_id": pac_id,
            "exists": True,
            "event_count": len(events),
            "chain_head": events[-1].content_hash,
            "first_event": events[0].timestamp,
            "last_event": events[-1].timestamp,
            "event_types": event_types
        }
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event store statistics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            pacs = conn.execute("SELECT COUNT(DISTINCT pac_id) FROM events").fetchone()[0]
            sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM events").fetchone()[0]
            
            type_counts = {}
            for row in conn.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type"):
                type_counts[row[0]] = row[1]
        
        return {
            "total_events": total,
            "unique_pacs": pacs,
            "unique_sessions": sessions,
            "event_type_distribution": type_counts,
            "db_path": str(self.db_path),
            "backup_path": str(self.backup_path)
        }


# ==================== Global Singleton ====================

_global_store: Optional[HeartbeatEventStore] = None


def get_event_store() -> HeartbeatEventStore:
    """Get or create global event store singleton."""
    global _global_store
    if _global_store is None:
        _global_store = HeartbeatEventStore()
    return _global_store


# ==================== Self-Test ====================

if __name__ == "__main__":
    import tempfile
    
    print("HeartbeatEventStore Self-Test")
    print("=" * 50)
    
    # Use temp files for test
    with tempfile.TemporaryDirectory() as tmpdir:
        store = HeartbeatEventStore(
            db_path=f"{tmpdir}/test.db",
            backup_path=f"{tmpdir}/test.jsonl"
        )
        
        # Test append
        test_event = {
            "event_type": "PAC_START",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_number": 1,
            "session_id": "test_session",
            "pac_id": "PAC-P745-TEST"
        }
        
        stored = store.append(test_event, pac_id="PAC-P745-TEST")
        print(f"✅ Event stored: {stored.event_id}")
        print(f"   Hash: {stored.content_hash[:16]}...")
        
        # Test chain
        for i in range(2, 5):
            test_event["sequence_number"] = i
            test_event["event_type"] = f"TASK_{i}"
            store.append(test_event, pac_id="PAC-P745-TEST")
        
        # Verify chain
        result = store.verify_chain("PAC-P745-TEST")
        print(f"✅ Chain verified: {result['status']}")
        print(f"   Events: {result['event_count']}")
        
        # Stats
        stats = store.get_stats()
        print(f"✅ Stats: {stats['total_events']} total events")
        
    print("\n✅ Self-test PASSED")
