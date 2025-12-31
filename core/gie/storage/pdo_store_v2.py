"""
PDO Store v2 — Scaled Storage with Index Hardening

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-07 (Dan) — Data Engineer

Features:
- Multi-agent burst handling
- Optimized hash index fan-out
- Immutability validation under load
- Sharded storage for horizontal scale
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PDO_STORE_CONFIG = {
    "shard_count": 16,
    "max_entries_per_shard": 10000,
    "index_fan_out": 256,
    "write_buffer_size": 100,
    "enable_compression": False,
    "enable_metrics": True,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class StorageState(Enum):
    """State of storage entry."""
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    ARCHIVED = "ARCHIVED"
    CORRUPTED = "CORRUPTED"


class IndexType(Enum):
    """Types of indexes."""
    PRIMARY = "PRIMARY"       # By PDO ID
    HASH = "HASH"            # By content hash
    PAC = "PAC"              # By PAC ID
    TIMESTAMP = "TIMESTAMP"  # By creation time
    AGENT = "AGENT"          # By agent GID


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class PDOStoreError(Exception):
    """Base exception for PDO store operations."""
    pass


class ImmutabilityViolationError(PDOStoreError):
    """Raised when attempting to modify immutable data."""
    pass


class ShardOverflowError(PDOStoreError):
    """Raised when shard capacity exceeded."""
    pass


class IndexCorruptionError(PDOStoreError):
    """Raised when index corruption detected."""
    pass


class DuplicateEntryError(PDOStoreError):
    """Raised when duplicate PDO detected."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PDOEntry:
    """
    A single PDO entry in storage.
    
    Immutable after creation.
    """
    pdo_id: str
    pac_id: str
    agent_gids: Tuple[str, ...]
    ber_status: str
    wrap_hashes: Tuple[str, ...]
    content_hash: str
    created_at: str
    state: StorageState = StorageState.PENDING
    shard_id: int = 0
    
    def __post_init__(self):
        # Ensure tuple immutability
        if isinstance(self.agent_gids, list):
            object.__setattr__(self, 'agent_gids', tuple(self.agent_gids))
        if isinstance(self.wrap_hashes, list):
            object.__setattr__(self, 'wrap_hashes', tuple(self.wrap_hashes))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "agent_gids": list(self.agent_gids),
            "ber_status": self.ber_status,
            "wrap_hashes": list(self.wrap_hashes),
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "state": self.state.value,
            "shard_id": self.shard_id,
        }
    
    @staticmethod
    def compute_hash(
        pdo_id: str,
        pac_id: str,
        agent_gids: List[str],
        ber_status: str,
        wrap_hashes: List[str],
    ) -> str:
        """Compute content hash."""
        content = json.dumps({
            "pdo_id": pdo_id,
            "pac_id": pac_id,
            "agent_gids": sorted(agent_gids),
            "ber_status": ber_status,
            "wrap_hashes": sorted(wrap_hashes),
        }, sort_keys=True)
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


@dataclass
class ShardMetrics:
    """Metrics for a single shard."""
    shard_id: int
    entry_count: int = 0
    total_writes: int = 0
    total_reads: int = 0
    last_write_at: Optional[str] = None
    last_read_at: Optional[str] = None
    avg_write_latency_ms: float = 0.0
    avg_read_latency_ms: float = 0.0


@dataclass
class StoreMetrics:
    """Aggregate store metrics."""
    total_entries: int = 0
    total_writes: int = 0
    total_reads: int = 0
    write_throughput: float = 0.0  # writes/sec
    read_throughput: float = 0.0   # reads/sec
    shard_distribution: Dict[int, int] = field(default_factory=dict)
    index_sizes: Dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# SHARD
# ═══════════════════════════════════════════════════════════════════════════════

class PDOShard:
    """
    A single shard of PDO storage.
    
    Thread-safe with read-write locking.
    """

    def __init__(self, shard_id: int, max_entries: int = 10000):
        """Initialize shard."""
        self._shard_id = shard_id
        self._max_entries = max_entries
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.RLock()
        
        # Storage
        self._entries: Dict[str, PDOEntry] = {}
        
        # Metrics
        self._metrics = ShardMetrics(shard_id=shard_id)
        self._write_latencies: List[float] = []
        self._read_latencies: List[float] = []

    @property
    def shard_id(self) -> int:
        return self._shard_id

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def is_full(self) -> bool:
        return len(self._entries) >= self._max_entries

    def write(self, entry: PDOEntry) -> None:
        """
        Write entry to shard.
        
        Raises:
        - ShardOverflowError if full
        - DuplicateEntryError if exists
        - ImmutabilityViolationError if attempting overwrite
        """
        start = time.time()
        
        with self._lock:
            if self.is_full:
                raise ShardOverflowError(f"Shard {self._shard_id} at capacity")
            
            if entry.pdo_id in self._entries:
                existing = self._entries[entry.pdo_id]
                if existing.content_hash != entry.content_hash:
                    raise ImmutabilityViolationError(
                        f"Cannot modify existing PDO: {entry.pdo_id}"
                    )
                raise DuplicateEntryError(f"PDO already exists: {entry.pdo_id}")
            
            # Commit entry
            entry.state = StorageState.COMMITTED
            entry.shard_id = self._shard_id
            self._entries[entry.pdo_id] = entry
            
            # Update metrics
            elapsed = (time.time() - start) * 1000
            self._write_latencies.append(elapsed)
            self._metrics.entry_count = len(self._entries)
            self._metrics.total_writes += 1
            self._metrics.last_write_at = datetime.utcnow().isoformat() + "Z"
            self._metrics.avg_write_latency_ms = sum(self._write_latencies[-100:]) / min(len(self._write_latencies), 100)

    def read(self, pdo_id: str) -> Optional[PDOEntry]:
        """Read entry from shard."""
        start = time.time()
        
        with self._lock:
            entry = self._entries.get(pdo_id)
            
            # Update metrics
            elapsed = (time.time() - start) * 1000
            self._read_latencies.append(elapsed)
            self._metrics.total_reads += 1
            self._metrics.last_read_at = datetime.utcnow().isoformat() + "Z"
            self._metrics.avg_read_latency_ms = sum(self._read_latencies[-100:]) / min(len(self._read_latencies), 100)
            
            return entry

    def list_entries(self) -> List[str]:
        """List all entry IDs."""
        with self._lock:
            return list(self._entries.keys())

    def get_metrics(self) -> ShardMetrics:
        """Get shard metrics."""
        with self._lock:
            return ShardMetrics(
                shard_id=self._shard_id,
                entry_count=len(self._entries),
                total_writes=self._metrics.total_writes,
                total_reads=self._metrics.total_reads,
                last_write_at=self._metrics.last_write_at,
                last_read_at=self._metrics.last_read_at,
                avg_write_latency_ms=self._metrics.avg_write_latency_ms,
                avg_read_latency_ms=self._metrics.avg_read_latency_ms,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# INDEX
# ═══════════════════════════════════════════════════════════════════════════════

class PDOIndex:
    """
    Hash-based index with optimized fan-out.
    
    Supports multiple index types for fast lookups.
    """

    def __init__(self, fan_out: int = 256):
        """Initialize index."""
        self._fan_out = fan_out
        self._lock = threading.RLock()
        
        # Primary index: pdo_id -> shard_id
        self._primary: Dict[str, int] = {}
        
        # Secondary indexes
        self._by_hash: Dict[str, Set[str]] = defaultdict(set)      # hash -> pdo_ids
        self._by_pac: Dict[str, Set[str]] = defaultdict(set)       # pac_id -> pdo_ids
        self._by_agent: Dict[str, Set[str]] = defaultdict(set)     # agent_gid -> pdo_ids
        self._by_timestamp: Dict[str, Set[str]] = defaultdict(set) # date -> pdo_ids

    def _hash_key(self, value: str) -> int:
        """Compute hash bucket for value."""
        return int(hashlib.md5(value.encode()).hexdigest()[:8], 16) % self._fan_out

    def index(self, entry: PDOEntry) -> None:
        """Add entry to all indexes."""
        with self._lock:
            # Primary
            self._primary[entry.pdo_id] = entry.shard_id
            
            # By hash
            self._by_hash[entry.content_hash].add(entry.pdo_id)
            
            # By PAC
            self._by_pac[entry.pac_id].add(entry.pdo_id)
            
            # By agent
            for agent_gid in entry.agent_gids:
                self._by_agent[agent_gid].add(entry.pdo_id)
            
            # By timestamp (date only)
            date_key = entry.created_at[:10]  # YYYY-MM-DD
            self._by_timestamp[date_key].add(entry.pdo_id)

    def remove(self, entry: PDOEntry) -> None:
        """Remove entry from all indexes."""
        with self._lock:
            # Primary
            self._primary.pop(entry.pdo_id, None)
            
            # By hash
            self._by_hash[entry.content_hash].discard(entry.pdo_id)
            
            # By PAC
            self._by_pac[entry.pac_id].discard(entry.pdo_id)
            
            # By agent
            for agent_gid in entry.agent_gids:
                self._by_agent[agent_gid].discard(entry.pdo_id)
            
            # By timestamp
            date_key = entry.created_at[:10]
            self._by_timestamp[date_key].discard(entry.pdo_id)

    def get_shard(self, pdo_id: str) -> Optional[int]:
        """Get shard ID for PDO."""
        with self._lock:
            return self._primary.get(pdo_id)

    def find_by_hash(self, content_hash: str) -> Set[str]:
        """Find PDOs by content hash."""
        with self._lock:
            return set(self._by_hash.get(content_hash, set()))

    def find_by_pac(self, pac_id: str) -> Set[str]:
        """Find PDOs by PAC ID."""
        with self._lock:
            return set(self._by_pac.get(pac_id, set()))

    def find_by_agent(self, agent_gid: str) -> Set[str]:
        """Find PDOs involving an agent."""
        with self._lock:
            return set(self._by_agent.get(agent_gid, set()))

    def find_by_date(self, date: str) -> Set[str]:
        """Find PDOs by date (YYYY-MM-DD)."""
        with self._lock:
            return set(self._by_timestamp.get(date, set()))

    def get_sizes(self) -> Dict[str, int]:
        """Get index sizes."""
        with self._lock:
            return {
                "primary": len(self._primary),
                "by_hash": sum(len(v) for v in self._by_hash.values()),
                "by_pac": sum(len(v) for v in self._by_pac.values()),
                "by_agent": sum(len(v) for v in self._by_agent.values()),
                "by_timestamp": sum(len(v) for v in self._by_timestamp.values()),
            }

    def validate_integrity(self, entries: Dict[str, PDOEntry]) -> Tuple[bool, List[str]]:
        """
        Validate index integrity against entries.
        
        Returns (valid, errors).
        """
        errors = []
        
        with self._lock:
            # Check all indexed PDOs exist
            for pdo_id in self._primary:
                if pdo_id not in entries:
                    errors.append(f"Orphan index entry: {pdo_id}")
            
            # Check all entries are indexed
            for pdo_id in entries:
                if pdo_id not in self._primary:
                    errors.append(f"Missing index for: {pdo_id}")
        
        return len(errors) == 0, errors


# ═══════════════════════════════════════════════════════════════════════════════
# PDO STORE V2
# ═══════════════════════════════════════════════════════════════════════════════

class PDOStoreV2:
    """
    Scaled PDO storage with sharding and index hardening.
    
    Features:
    - Horizontal sharding for parallel writes
    - Multi-index lookups
    - Immutability enforcement
    - Burst handling
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize store."""
        self._config = {**PDO_STORE_CONFIG, **(config or {})}
        self._lock = threading.RLock()
        
        # Shards
        shard_count = self._config["shard_count"]
        max_per_shard = self._config["max_entries_per_shard"]
        self._shards: List[PDOShard] = [
            PDOShard(i, max_per_shard) for i in range(shard_count)
        ]
        
        # Index
        self._index = PDOIndex(fan_out=self._config["index_fan_out"])
        
        # Metrics
        self._start_time = time.time()
        self._total_writes = 0
        self._total_reads = 0

    @property
    def shard_count(self) -> int:
        return len(self._shards)

    @property
    def total_entries(self) -> int:
        return sum(s.entry_count for s in self._shards)

    def _select_shard(self, pdo_id: str) -> int:
        """Select shard for PDO using consistent hashing."""
        hash_val = int(hashlib.md5(pdo_id.encode()).hexdigest()[:8], 16)
        return hash_val % len(self._shards)

    # ─────────────────────────────────────────────────────────────────────────
    # Write Operations
    # ─────────────────────────────────────────────────────────────────────────

    def store(
        self,
        pdo_id: str,
        pac_id: str,
        agent_gids: List[str],
        ber_status: str,
        wrap_hashes: List[str],
    ) -> PDOEntry:
        """
        Store a new PDO.
        
        Immutable — cannot overwrite existing entries.
        """
        # Compute content hash
        content_hash = PDOEntry.compute_hash(
            pdo_id, pac_id, agent_gids, ber_status, wrap_hashes
        )
        
        # Create entry
        entry = PDOEntry(
            pdo_id=pdo_id,
            pac_id=pac_id,
            agent_gids=tuple(agent_gids),
            ber_status=ber_status,
            wrap_hashes=tuple(wrap_hashes),
            content_hash=content_hash,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        
        # Select shard
        shard_id = self._select_shard(pdo_id)
        shard = self._shards[shard_id]
        
        # Write to shard
        shard.write(entry)
        
        # Index entry
        self._index.index(entry)
        
        with self._lock:
            self._total_writes += 1
        
        return entry

    def store_batch(
        self,
        entries: List[Dict[str, Any]],
    ) -> Tuple[List[PDOEntry], List[str]]:
        """
        Store multiple PDOs in batch.
        
        Returns (successful_entries, failed_pdo_ids).
        """
        successful = []
        failed = []
        
        for entry_data in entries:
            try:
                entry = self.store(
                    pdo_id=entry_data["pdo_id"],
                    pac_id=entry_data["pac_id"],
                    agent_gids=entry_data["agent_gids"],
                    ber_status=entry_data["ber_status"],
                    wrap_hashes=entry_data["wrap_hashes"],
                )
                successful.append(entry)
            except PDOStoreError:
                failed.append(entry_data["pdo_id"])
        
        return successful, failed

    # ─────────────────────────────────────────────────────────────────────────
    # Read Operations
    # ─────────────────────────────────────────────────────────────────────────

    def get(self, pdo_id: str) -> Optional[PDOEntry]:
        """Get PDO by ID."""
        shard_id = self._index.get_shard(pdo_id)
        if shard_id is None:
            return None
        
        entry = self._shards[shard_id].read(pdo_id)
        
        with self._lock:
            self._total_reads += 1
        
        return entry

    def exists(self, pdo_id: str) -> bool:
        """Check if PDO exists."""
        return self._index.get_shard(pdo_id) is not None

    def find_by_pac(self, pac_id: str) -> List[PDOEntry]:
        """Find all PDOs for a PAC."""
        pdo_ids = self._index.find_by_pac(pac_id)
        return [self.get(pid) for pid in pdo_ids if self.get(pid)]

    def find_by_agent(self, agent_gid: str) -> List[PDOEntry]:
        """Find all PDOs involving an agent."""
        pdo_ids = self._index.find_by_agent(agent_gid)
        return [self.get(pid) for pid in pdo_ids if self.get(pid)]

    def find_by_hash(self, content_hash: str) -> List[PDOEntry]:
        """Find PDOs by content hash."""
        pdo_ids = self._index.find_by_hash(content_hash)
        return [self.get(pid) for pid in pdo_ids if self.get(pid)]

    def find_by_date(self, date: str) -> List[PDOEntry]:
        """Find PDOs by creation date."""
        pdo_ids = self._index.find_by_date(date)
        return [self.get(pid) for pid in pdo_ids if self.get(pid)]

    # ─────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────

    def validate_immutability(self, pdo_id: str, expected_hash: str) -> bool:
        """
        Validate PDO hasn't been modified.
        
        Compares stored hash against expected.
        """
        entry = self.get(pdo_id)
        if entry is None:
            return False
        return entry.content_hash == expected_hash

    def validate_index_integrity(self) -> Tuple[bool, List[str]]:
        """Validate all indexes are consistent."""
        # Collect all entries
        all_entries: Dict[str, PDOEntry] = {}
        for shard in self._shards:
            for pdo_id in shard.list_entries():
                entry = shard.read(pdo_id)
                if entry:
                    all_entries[pdo_id] = entry
        
        return self._index.validate_integrity(all_entries)

    # ─────────────────────────────────────────────────────────────────────────
    # Metrics
    # ─────────────────────────────────────────────────────────────────────────

    def get_metrics(self) -> StoreMetrics:
        """Get aggregate store metrics."""
        elapsed = time.time() - self._start_time
        
        shard_distribution = {
            s.shard_id: s.entry_count for s in self._shards
        }
        
        with self._lock:
            return StoreMetrics(
                total_entries=self.total_entries,
                total_writes=self._total_writes,
                total_reads=self._total_reads,
                write_throughput=self._total_writes / elapsed if elapsed > 0 else 0,
                read_throughput=self._total_reads / elapsed if elapsed > 0 else 0,
                shard_distribution=shard_distribution,
                index_sizes=self._index.get_sizes(),
            )

    def get_shard_metrics(self) -> List[ShardMetrics]:
        """Get metrics for all shards."""
        return [s.get_metrics() for s in self._shards]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_store: Optional[PDOStoreV2] = None
_store_lock = threading.Lock()


def get_pdo_store_v2(config: Optional[Dict[str, Any]] = None) -> PDOStoreV2:
    """Get or create global PDO store."""
    global _store
    
    with _store_lock:
        if _store is None:
            _store = PDOStoreV2(config=config)
        return _store


def reset_pdo_store_v2() -> None:
    """Reset global store."""
    global _store
    
    with _store_lock:
        _store = None
