"""
PDO Scale Manager — Data Retention and Scaling Infrastructure.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-07 (Maya) — DATA/PDO RETENTION & SCALING
Deliverable: PDOShardManager, RetentionPolicyEngine, PDOCompactor,
             ReplicationManager, QueryOptimizer, ArchiveManager

Features:
- Horizontal sharding for PDO storage
- Configurable retention policies
- PDO compaction and deduplication
- Multi-region replication
- Query optimization
- Cold storage archival
"""

from __future__ import annotations

import bisect
import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# =============================================================================
# VERSION
# =============================================================================

PDO_SCALE_VERSION = "1.0.0"


# =============================================================================
# ENUMS
# =============================================================================

class ShardStatus(Enum):
    """Shard status."""
    ACTIVE = "ACTIVE"
    READONLY = "READONLY"
    MIGRATING = "MIGRATING"
    OFFLINE = "OFFLINE"
    ARCHIVED = "ARCHIVED"


class RetentionAction(Enum):
    """Retention policy actions."""
    KEEP = "KEEP"
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"
    COMPRESS = "COMPRESS"
    MOVE_TIER = "MOVE_TIER"


class StorageTier(Enum):
    """Storage tiers."""
    HOT = "HOT"           # Frequent access, SSD
    WARM = "WARM"         # Moderate access
    COLD = "COLD"         # Rare access
    GLACIER = "GLACIER"   # Archive, very rare access


class ReplicationMode(Enum):
    """Replication modes."""
    SYNCHRONOUS = "SYNCHRONOUS"
    ASYNCHRONOUS = "ASYNCHRONOUS"
    SEMI_SYNC = "SEMI_SYNC"


class ConsistencyLevel(Enum):
    """Consistency levels for reads."""
    ONE = "ONE"           # Any replica
    QUORUM = "QUORUM"     # Majority
    ALL = "ALL"           # All replicas
    LOCAL = "LOCAL"       # Local replica only


# =============================================================================
# EXCEPTIONS
# =============================================================================

class PDOScaleError(Exception):
    """Base PDO scaling exception."""
    pass


class ShardNotFoundError(PDOScaleError):
    """Shard not found."""
    pass


class ReplicationError(PDOScaleError):
    """Replication failure."""
    pass


class RetentionViolationError(PDOScaleError):
    """Retention policy violation."""
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PDORecord:
    """A PDO (Persistent Data Object) record."""
    pdo_id: str
    data: bytes
    created_at: datetime
    updated_at: datetime
    tier: StorageTier = StorageTier.HOT
    compressed: bool = False
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate checksum if not provided."""
        if not self.checksum:
            self.checksum = hashlib.sha256(self.data).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pdo_id": self.pdo_id,
            "size_bytes": len(self.data),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tier": self.tier.value,
            "compressed": self.compressed,
            "checksum": self.checksum,
        }


@dataclass
class Shard:
    """A data shard."""
    shard_id: str
    hash_range_start: int
    hash_range_end: int
    status: ShardStatus
    region: str
    capacity_bytes: int
    used_bytes: int = 0
    record_count: int = 0
    
    @property
    def utilization(self) -> float:
        """Calculate utilization percentage."""
        if self.capacity_bytes == 0:
            return 0.0
        return (self.used_bytes / self.capacity_bytes) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "shard_id": self.shard_id,
            "hash_range": [self.hash_range_start, self.hash_range_end],
            "status": self.status.value,
            "region": self.region,
            "capacity_bytes": self.capacity_bytes,
            "used_bytes": self.used_bytes,
            "record_count": self.record_count,
            "utilization_percent": self.utilization,
        }


@dataclass
class RetentionPolicy:
    """Retention policy definition."""
    policy_id: str
    name: str
    tier: StorageTier
    max_age_days: int
    action: RetentionAction
    target_tier: Optional[StorageTier] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "tier": self.tier.value,
            "max_age_days": self.max_age_days,
            "action": self.action.value,
            "target_tier": self.target_tier.value if self.target_tier else None,
        }


@dataclass
class Replica:
    """A data replica."""
    replica_id: str
    shard_id: str
    region: str
    is_primary: bool
    lag_ms: float = 0.0
    status: str = "SYNCED"
    last_sync: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "replica_id": self.replica_id,
            "shard_id": self.shard_id,
            "region": self.region,
            "is_primary": self.is_primary,
            "lag_ms": self.lag_ms,
            "status": self.status,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
        }


@dataclass
class QueryPlan:
    """A query execution plan."""
    plan_id: str
    shards_accessed: List[str]
    estimated_rows: int
    estimated_cost: float
    uses_index: bool
    parallel: bool
    cache_hit: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "shards_accessed": self.shards_accessed,
            "estimated_rows": self.estimated_rows,
            "estimated_cost": self.estimated_cost,
            "uses_index": self.uses_index,
            "parallel": self.parallel,
            "cache_hit": self.cache_hit,
        }


@dataclass
class CompactionResult:
    """Result of a compaction operation."""
    records_processed: int
    records_removed: int
    bytes_freed: int
    duration_seconds: float
    errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "records_processed": self.records_processed,
            "records_removed": self.records_removed,
            "bytes_freed": self.bytes_freed,
            "duration_seconds": self.duration_seconds,
            "error_count": len(self.errors),
        }


@dataclass
class ArchiveJob:
    """An archive job."""
    job_id: str
    source_tier: StorageTier
    target_tier: StorageTier
    records_count: int
    bytes_total: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "source_tier": self.source_tier.value,
            "target_tier": self.target_tier.value,
            "records_count": self.records_count,
            "bytes_total": self.bytes_total,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# =============================================================================
# PDO SHARD MANAGER
# =============================================================================

class PDOShardManager:
    """
    Horizontal sharding manager for PDO storage.
    
    Features:
    - Consistent hashing for distribution
    - Automatic shard splitting
    - Cross-shard queries
    - Shard rebalancing
    """
    
    def __init__(self, virtual_nodes: int = 256) -> None:
        self._lock = threading.RLock()
        self._shards: Dict[str, Shard] = {}
        self._ring: List[Tuple[int, str]] = []  # (hash, shard_id)
        self._virtual_nodes = virtual_nodes
        self._data: Dict[str, Dict[str, PDORecord]] = defaultdict(dict)  # shard_id -> {pdo_id -> record}
        self._shard_counter = 0
    
    def add_shard(
        self,
        region: str,
        capacity_bytes: int,
    ) -> Shard:
        """Add a new shard to the cluster."""
        with self._lock:
            self._shard_counter += 1
            shard_id = f"shard_{self._shard_counter:04d}"
            
            # Calculate hash range
            total_shards = len(self._shards) + 1
            range_size = (2**32) // total_shards
            
            shard = Shard(
                shard_id=shard_id,
                hash_range_start=0,
                hash_range_end=range_size,
                status=ShardStatus.ACTIVE,
                region=region,
                capacity_bytes=capacity_bytes,
            )
            
            self._shards[shard_id] = shard
            
            # Add virtual nodes to ring
            for i in range(self._virtual_nodes):
                vnode_key = f"{shard_id}:{i}"
                hash_val = self._hash(vnode_key)
                bisect.insort(self._ring, (hash_val, shard_id))
            
            return shard
    
    def get_shard(self, shard_id: str) -> Optional[Shard]:
        """Get shard by ID."""
        return self._shards.get(shard_id)
    
    def get_shard_for_key(self, key: str) -> str:
        """Get shard ID for a given key using consistent hashing."""
        if not self._ring:
            raise PDOScaleError("No shards available")
        
        hash_val = self._hash(key)
        
        with self._lock:
            # Binary search for the first node >= hash_val
            idx = bisect.bisect_left(self._ring, (hash_val, ""))
            if idx >= len(self._ring):
                idx = 0
            
            return self._ring[idx][1]
    
    def store(self, pdo_id: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> PDORecord:
        """Store a PDO record."""
        shard_id = self.get_shard_for_key(pdo_id)
        
        with self._lock:
            shard = self._shards.get(shard_id)
            if not shard:
                raise ShardNotFoundError(f"Shard not found: {shard_id}")
            
            if shard.status != ShardStatus.ACTIVE:
                raise PDOScaleError(f"Shard {shard_id} is not active")
            
            now = datetime.now(timezone.utc)
            record = PDORecord(
                pdo_id=pdo_id,
                data=data,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
            
            self._data[shard_id][pdo_id] = record
            
            # Update shard stats
            shard.used_bytes += len(data)
            shard.record_count += 1
            
            return record
    
    def retrieve(self, pdo_id: str) -> Optional[PDORecord]:
        """Retrieve a PDO record."""
        shard_id = self.get_shard_for_key(pdo_id)
        
        with self._lock:
            return self._data.get(shard_id, {}).get(pdo_id)
    
    def delete(self, pdo_id: str) -> bool:
        """Delete a PDO record."""
        shard_id = self.get_shard_for_key(pdo_id)
        
        with self._lock:
            if pdo_id in self._data.get(shard_id, {}):
                record = self._data[shard_id].pop(pdo_id)
                shard = self._shards[shard_id]
                shard.used_bytes -= len(record.data)
                shard.record_count -= 1
                return True
            return False
    
    def split_shard(self, shard_id: str) -> Tuple[Shard, Shard]:
        """Split a shard into two."""
        with self._lock:
            old_shard = self._shards.get(shard_id)
            if not old_shard:
                raise ShardNotFoundError(f"Shard not found: {shard_id}")
            
            # Mark old shard as migrating
            old_shard.status = ShardStatus.MIGRATING
            
            # Create two new shards
            mid_hash = (old_shard.hash_range_start + old_shard.hash_range_end) // 2
            
            new_shard_1 = self.add_shard(old_shard.region, old_shard.capacity_bytes)
            new_shard_1.hash_range_start = old_shard.hash_range_start
            new_shard_1.hash_range_end = mid_hash
            
            new_shard_2 = self.add_shard(old_shard.region, old_shard.capacity_bytes)
            new_shard_2.hash_range_start = mid_hash
            new_shard_2.hash_range_end = old_shard.hash_range_end
            
            # Migrate data (simplified - would be async in production)
            for pdo_id, record in list(self._data.get(shard_id, {}).items()):
                new_shard_id = self.get_shard_for_key(pdo_id)
                if new_shard_id != shard_id:
                    self._data[new_shard_id][pdo_id] = record
                    del self._data[shard_id][pdo_id]
            
            # Archive old shard
            old_shard.status = ShardStatus.ARCHIVED
            
            return new_shard_1, new_shard_2
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cluster statistics."""
        with self._lock:
            total_records = sum(s.record_count for s in self._shards.values())
            total_bytes = sum(s.used_bytes for s in self._shards.values())
            total_capacity = sum(s.capacity_bytes for s in self._shards.values())
            
            return {
                "shard_count": len(self._shards),
                "total_records": total_records,
                "total_bytes": total_bytes,
                "total_capacity": total_capacity,
                "utilization_percent": (total_bytes / max(total_capacity, 1)) * 100,
                "shards": [s.to_dict() for s in self._shards.values()],
            }
    
    def _hash(self, key: str) -> int:
        """Hash a key to a 32-bit integer."""
        h = hashlib.md5(key.encode()).digest()
        return int.from_bytes(h[:4], 'big')


# =============================================================================
# RETENTION POLICY ENGINE
# =============================================================================

class RetentionPolicyEngine:
    """
    Configurable retention policy management.
    
    Features:
    - Age-based retention
    - Tier-based policies
    - Conditional retention
    - Policy enforcement
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._policies: Dict[str, RetentionPolicy] = {}
        self._policy_counter = 0
    
    def create_policy(
        self,
        name: str,
        tier: StorageTier,
        max_age_days: int,
        action: RetentionAction,
        target_tier: Optional[StorageTier] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> RetentionPolicy:
        """Create a retention policy."""
        with self._lock:
            self._policy_counter += 1
            policy = RetentionPolicy(
                policy_id=f"RET-{self._policy_counter:04d}",
                name=name,
                tier=tier,
                max_age_days=max_age_days,
                action=action,
                target_tier=target_tier,
                conditions=conditions or {},
            )
            
            self._policies[policy.policy_id] = policy
            return policy
    
    def evaluate(
        self,
        record: PDORecord,
        current_time: Optional[datetime] = None,
    ) -> Tuple[RetentionAction, Optional[StorageTier]]:
        """
        Evaluate retention policies for a record.
        
        Returns:
            Tuple of (action, target_tier if applicable)
        """
        now = current_time or datetime.now(timezone.utc)
        record_age_days = (now - record.created_at).days
        
        with self._lock:
            # Find applicable policies
            applicable = [
                p for p in self._policies.values()
                if p.tier == record.tier and record_age_days >= p.max_age_days
            ]
            
            if not applicable:
                return RetentionAction.KEEP, None
            
            # Sort by age requirement (most restrictive first)
            applicable.sort(key=lambda p: p.max_age_days)
            
            # Apply first matching policy
            for policy in applicable:
                if self._check_conditions(record, policy.conditions):
                    return policy.action, policy.target_tier
            
            return RetentionAction.KEEP, None
    
    def apply_policies(
        self,
        shard_manager: PDOShardManager,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Apply retention policies to all records.
        
        Args:
            shard_manager: The shard manager containing records
            dry_run: If True, only report what would happen
        """
        results = {
            "kept": 0,
            "archived": 0,
            "deleted": 0,
            "compressed": 0,
            "moved": 0,
            "actions": [],
        }
        
        now = datetime.now(timezone.utc)
        
        with self._lock:
            stats = shard_manager.get_stats()
            
            for shard_data in stats["shards"]:
                shard_id = shard_data["shard_id"]
                records = shard_manager._data.get(shard_id, {})
                
                for pdo_id, record in list(records.items()):
                    action, target_tier = self.evaluate(record, now)
                    
                    if action == RetentionAction.KEEP:
                        results["kept"] += 1
                    elif action == RetentionAction.DELETE:
                        results["deleted"] += 1
                        results["actions"].append({
                            "pdo_id": pdo_id,
                            "action": "DELETE",
                        })
                        if not dry_run:
                            shard_manager.delete(pdo_id)
                    elif action == RetentionAction.ARCHIVE:
                        results["archived"] += 1
                        results["actions"].append({
                            "pdo_id": pdo_id,
                            "action": "ARCHIVE",
                            "target_tier": target_tier.value if target_tier else None,
                        })
                    elif action == RetentionAction.MOVE_TIER:
                        results["moved"] += 1
                        if not dry_run and target_tier:
                            record.tier = target_tier
        
        return results
    
    def _check_conditions(
        self,
        record: PDORecord,
        conditions: Dict[str, Any],
    ) -> bool:
        """Check if record meets policy conditions."""
        if not conditions:
            return True
        
        # Check size condition
        min_size = conditions.get("min_size_bytes")
        if min_size and len(record.data) < min_size:
            return False
        
        max_size = conditions.get("max_size_bytes")
        if max_size and len(record.data) > max_size:
            return False
        
        # Check metadata conditions
        required_tags = conditions.get("required_tags", [])
        for tag in required_tags:
            if tag not in record.metadata.get("tags", []):
                return False
        
        return True
    
    def get_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Get policy by ID."""
        return self._policies.get(policy_id)
    
    def get_all_policies(self) -> List[RetentionPolicy]:
        """Get all policies."""
        return list(self._policies.values())


# =============================================================================
# PDO COMPACTOR
# =============================================================================

class PDOCompactor:
    """
    PDO compaction and deduplication.
    
    Features:
    - Tombstone cleanup
    - Duplicate detection
    - Data compression
    - Space reclamation
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._compaction_history: List[CompactionResult] = []
    
    def compact(
        self,
        shard_manager: PDOShardManager,
        shard_id: Optional[str] = None,
        deduplicate: bool = True,
        compress: bool = False,
    ) -> CompactionResult:
        """
        Compact a shard or all shards.
        
        Args:
            shard_manager: The shard manager
            shard_id: Specific shard to compact, or None for all
            deduplicate: Remove duplicates
            compress: Compress data
        """
        start_time = time.time()
        processed = 0
        removed = 0
        bytes_freed = 0
        errors: List[str] = []
        
        with self._lock:
            stats = shard_manager.get_stats()
            
            # Determine shards to compact
            if shard_id:
                shard_ids = [shard_id]
            else:
                shard_ids = [s["shard_id"] for s in stats["shards"]]
            
            # Track checksums for deduplication
            seen_checksums: Dict[str, str] = {}  # checksum -> pdo_id
            
            for sid in shard_ids:
                records = shard_manager._data.get(sid, {})
                
                for pdo_id, record in list(records.items()):
                    processed += 1
                    
                    try:
                        # Deduplicate by checksum
                        if deduplicate:
                            if record.checksum in seen_checksums:
                                # Duplicate found
                                bytes_freed += len(record.data)
                                shard_manager.delete(pdo_id)
                                removed += 1
                                continue
                            seen_checksums[record.checksum] = pdo_id
                        
                        # Compress if requested
                        if compress and not record.compressed:
                            import zlib
                            original_size = len(record.data)
                            compressed_data = zlib.compress(record.data)
                            if len(compressed_data) < original_size:
                                record.data = compressed_data
                                record.compressed = True
                                bytes_freed += original_size - len(compressed_data)
                    
                    except Exception as e:
                        errors.append(f"Error processing {pdo_id}: {str(e)}")
        
        duration = time.time() - start_time
        
        result = CompactionResult(
            records_processed=processed,
            records_removed=removed,
            bytes_freed=bytes_freed,
            duration_seconds=duration,
            errors=errors,
        )
        
        with self._lock:
            self._compaction_history.append(result)
        
        return result
    
    def find_duplicates(
        self,
        shard_manager: PDOShardManager,
    ) -> List[Dict[str, Any]]:
        """Find duplicate records across shards."""
        duplicates = []
        checksums: Dict[str, List[str]] = defaultdict(list)
        
        with self._lock:
            stats = shard_manager.get_stats()
            
            for shard_data in stats["shards"]:
                shard_id = shard_data["shard_id"]
                records = shard_manager._data.get(shard_id, {})
                
                for pdo_id, record in records.items():
                    checksums[record.checksum].append(pdo_id)
            
            for checksum, pdo_ids in checksums.items():
                if len(pdo_ids) > 1:
                    duplicates.append({
                        "checksum": checksum,
                        "pdo_ids": pdo_ids,
                        "count": len(pdo_ids),
                    })
        
        return duplicates
    
    def get_compaction_history(self, limit: int = 10) -> List[CompactionResult]:
        """Get compaction history."""
        with self._lock:
            return list(reversed(self._compaction_history))[:limit]


# =============================================================================
# REPLICATION MANAGER
# =============================================================================

class ReplicationManager:
    """
    Multi-region data replication.
    
    Features:
    - Sync/async replication
    - Replica lag monitoring
    - Failover support
    - Consistency levels
    """
    
    def __init__(self, mode: ReplicationMode = ReplicationMode.ASYNCHRONOUS) -> None:
        self._lock = threading.RLock()
        self._mode = mode
        self._replicas: Dict[str, List[Replica]] = defaultdict(list)  # shard_id -> replicas
        self._replica_counter = 0
    
    def add_replica(
        self,
        shard_id: str,
        region: str,
        is_primary: bool = False,
    ) -> Replica:
        """Add a replica for a shard."""
        with self._lock:
            self._replica_counter += 1
            replica = Replica(
                replica_id=f"rep_{self._replica_counter:04d}",
                shard_id=shard_id,
                region=region,
                is_primary=is_primary,
                last_sync=datetime.now(timezone.utc),
            )
            
            self._replicas[shard_id].append(replica)
            return replica
    
    def get_replicas(self, shard_id: str) -> List[Replica]:
        """Get all replicas for a shard."""
        return list(self._replicas.get(shard_id, []))
    
    def get_primary(self, shard_id: str) -> Optional[Replica]:
        """Get primary replica for a shard."""
        for replica in self._replicas.get(shard_id, []):
            if replica.is_primary:
                return replica
        return None
    
    def replicate(
        self,
        shard_id: str,
        data: bytes,
        consistency: ConsistencyLevel = ConsistencyLevel.QUORUM,
    ) -> Dict[str, Any]:
        """
        Replicate data to replicas.
        
        Args:
            shard_id: Shard to replicate
            data: Data to replicate
            consistency: Required consistency level
        """
        replicas = self._replicas.get(shard_id, [])
        if not replicas:
            return {"success": False, "error": "No replicas"}
        
        results = {"success": True, "acks": 0, "failed": []}
        required_acks = self._get_required_acks(len(replicas), consistency)
        
        with self._lock:
            for replica in replicas:
                try:
                    # Simulate replication (would be network call in production)
                    if self._mode == ReplicationMode.SYNCHRONOUS:
                        # Wait for each replica
                        replica.last_sync = datetime.now(timezone.utc)
                        replica.lag_ms = 0.0
                        replica.status = "SYNCED"
                    else:
                        # Async - just queue
                        replica.lag_ms = 50.0  # Simulated lag
                        replica.status = "PENDING"
                    
                    results["acks"] += 1
                    
                except Exception as e:
                    results["failed"].append({
                        "replica_id": replica.replica_id,
                        "error": str(e),
                    })
            
            if results["acks"] < required_acks:
                results["success"] = False
                results["error"] = "Insufficient acknowledgments"
        
        return results
    
    def promote_replica(
        self,
        replica_id: str,
    ) -> Optional[Replica]:
        """Promote a replica to primary."""
        with self._lock:
            for shard_id, replicas in self._replicas.items():
                for replica in replicas:
                    if replica.replica_id == replica_id:
                        # Demote current primary
                        for r in replicas:
                            if r.is_primary:
                                r.is_primary = False
                        
                        # Promote new primary
                        replica.is_primary = True
                        return replica
        
        return None
    
    def get_lag_report(self) -> Dict[str, Any]:
        """Get replication lag report."""
        with self._lock:
            total_lag = 0.0
            replica_count = 0
            lagging = []
            
            for shard_id, replicas in self._replicas.items():
                for replica in replicas:
                    if not replica.is_primary:
                        total_lag += replica.lag_ms
                        replica_count += 1
                        if replica.lag_ms > 100:
                            lagging.append(replica.to_dict())
            
            return {
                "average_lag_ms": total_lag / max(replica_count, 1),
                "replica_count": replica_count,
                "lagging_replicas": lagging,
                "mode": self._mode.value,
            }
    
    def _get_required_acks(
        self,
        total_replicas: int,
        consistency: ConsistencyLevel,
    ) -> int:
        """Calculate required acknowledgments for consistency level."""
        if consistency == ConsistencyLevel.ONE:
            return 1
        elif consistency == ConsistencyLevel.QUORUM:
            return (total_replicas // 2) + 1
        elif consistency == ConsistencyLevel.ALL:
            return total_replicas
        else:
            return 1


# =============================================================================
# QUERY OPTIMIZER
# =============================================================================

class QueryOptimizer:
    """
    Query optimization for distributed PDO queries.
    
    Features:
    - Shard pruning
    - Parallel execution
    - Query caching
    - Cost estimation
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._query_cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._plan_counter = 0
    
    def optimize(
        self,
        query: Dict[str, Any],
        shard_manager: PDOShardManager,
    ) -> QueryPlan:
        """
        Optimize a query and generate execution plan.
        
        Args:
            query: Query specification
            shard_manager: The shard manager
        """
        with self._lock:
            self._plan_counter += 1
            
            # Check cache
            query_hash = hashlib.md5(json.dumps(query, sort_keys=True).encode()).hexdigest()
            if query_hash in self._query_cache:
                self._cache_hits += 1
                cached = self._query_cache[query_hash]
                # Return a copy with cache_hit=True to preserve original
                return replace(cached, cache_hit=True)
            
            self._cache_misses += 1
            
            # Determine required shards
            shards_needed = self._identify_shards(query, shard_manager)
            
            # Estimate cost
            estimated_rows = self._estimate_rows(query, shard_manager)
            cost = self._calculate_cost(shards_needed, estimated_rows)
            
            # Determine if parallel execution is beneficial
            parallel = len(shards_needed) > 1 and estimated_rows > 100
            
            plan = QueryPlan(
                plan_id=f"QP-{self._plan_counter:06d}",
                shards_accessed=shards_needed,
                estimated_rows=estimated_rows,
                estimated_cost=cost,
                uses_index=self._can_use_index(query),
                parallel=parallel,
                cache_hit=False,
            )
            
            # Cache the plan
            self._query_cache[query_hash] = plan
            
            return plan
    
    def execute(
        self,
        plan: QueryPlan,
        shard_manager: PDOShardManager,
        query: Dict[str, Any],
    ) -> List[PDORecord]:
        """
        Execute a query using the optimized plan.
        
        Args:
            plan: The query plan
            shard_manager: The shard manager
            query: The original query
        """
        results: List[PDORecord] = []
        
        with self._lock:
            for shard_id in plan.shards_accessed:
                records = shard_manager._data.get(shard_id, {})
                
                for pdo_id, record in records.items():
                    if self._matches_query(record, query):
                        results.append(record)
        
        # Apply limit if specified
        limit = query.get("limit")
        if limit:
            results = results[:limit]
        
        return results
    
    def _identify_shards(
        self,
        query: Dict[str, Any],
        shard_manager: PDOShardManager,
    ) -> List[str]:
        """Identify shards needed for query."""
        # If specific PDO ID, only need one shard
        pdo_id = query.get("pdo_id")
        if pdo_id:
            shard_id = shard_manager.get_shard_for_key(pdo_id)
            return [shard_id]
        
        # Otherwise, need all active shards
        return [
            s["shard_id"] for s in shard_manager.get_stats()["shards"]
            if s["status"] == "ACTIVE"
        ]
    
    def _estimate_rows(
        self,
        query: Dict[str, Any],
        shard_manager: PDOShardManager,
    ) -> int:
        """Estimate number of rows returned."""
        stats = shard_manager.get_stats()
        total_records = stats["total_records"]
        
        # Apply selectivity estimates
        if query.get("pdo_id"):
            return 1
        
        # Generic estimate based on filters
        selectivity = 1.0
        if query.get("tier"):
            selectivity *= 0.25
        if query.get("created_after"):
            selectivity *= 0.5
        
        return max(1, int(total_records * selectivity))
    
    def _calculate_cost(
        self,
        shards: List[str],
        estimated_rows: int,
    ) -> float:
        """Calculate query cost."""
        # Simple cost model: shards * rows * factor
        return len(shards) * estimated_rows * 0.001
    
    def _can_use_index(self, query: Dict[str, Any]) -> bool:
        """Check if query can use an index."""
        # PDO ID queries can use index
        return "pdo_id" in query
    
    def _matches_query(
        self,
        record: PDORecord,
        query: Dict[str, Any],
    ) -> bool:
        """Check if record matches query criteria."""
        if query.get("pdo_id") and record.pdo_id != query["pdo_id"]:
            return False
        
        if query.get("tier") and record.tier.value != query["tier"]:
            return False
        
        created_after = query.get("created_after")
        if created_after and record.created_at < created_after:
            return False
        
        created_before = query.get("created_before")
        if created_before and record.created_at > created_before:
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        with self._lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / max(total, 1)) * 100
            
            return {
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate_percent": hit_rate,
                "cached_plans": len(self._query_cache),
            }


# =============================================================================
# ARCHIVE MANAGER
# =============================================================================

class ArchiveManager:
    """
    Cold storage archival management.
    
    Features:
    - Tier migration
    - Archive jobs
    - Retrieval queue
    - Storage cost optimization
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: Dict[str, ArchiveJob] = {}
        self._job_counter = 0
        self._archives: Dict[str, Dict[str, PDORecord]] = defaultdict(dict)  # tier -> {pdo_id -> record}
    
    def archive(
        self,
        shard_manager: PDOShardManager,
        source_tier: StorageTier,
        target_tier: StorageTier,
        max_records: int = 1000,
    ) -> ArchiveJob:
        """
        Archive records from one tier to another.
        
        Args:
            shard_manager: The shard manager
            source_tier: Source storage tier
            target_tier: Target storage tier
            max_records: Maximum records to archive
        """
        with self._lock:
            self._job_counter += 1
            job = ArchiveJob(
                job_id=f"ARC-{self._job_counter:04d}",
                source_tier=source_tier,
                target_tier=target_tier,
                records_count=0,
                bytes_total=0,
                status="RUNNING",
                started_at=datetime.now(timezone.utc),
            )
            
            self._jobs[job.job_id] = job
        
        # Find and archive records
        archived = 0
        bytes_total = 0
        
        stats = shard_manager.get_stats()
        for shard_data in stats["shards"]:
            if archived >= max_records:
                break
            
            shard_id = shard_data["shard_id"]
            records = shard_manager._data.get(shard_id, {})
            
            for pdo_id, record in list(records.items()):
                if archived >= max_records:
                    break
                
                if record.tier == source_tier:
                    # Move to archive
                    with self._lock:
                        self._archives[target_tier.value][pdo_id] = record
                        record.tier = target_tier
                    
                    archived += 1
                    bytes_total += len(record.data)
        
        with self._lock:
            job.records_count = archived
            job.bytes_total = bytes_total
            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
        
        return job
    
    def retrieve(
        self,
        pdo_id: str,
        tier: StorageTier,
    ) -> Optional[PDORecord]:
        """Retrieve a record from archive."""
        with self._lock:
            return self._archives.get(tier.value, {}).get(pdo_id)
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get archive statistics."""
        with self._lock:
            stats = {}
            for tier in StorageTier:
                tier_records = self._archives.get(tier.value, {})
                total_bytes = sum(len(r.data) for r in tier_records.values())
                stats[tier.value] = {
                    "record_count": len(tier_records),
                    "total_bytes": total_bytes,
                }
            
            return {
                "tiers": stats,
                "total_jobs": len(self._jobs),
                "completed_jobs": len([j for j in self._jobs.values() if j.status == "COMPLETED"]),
            }
    
    def get_job(self, job_id: str) -> Optional[ArchiveJob]:
        """Get archive job by ID."""
        return self._jobs.get(job_id)
    
    def get_jobs(self, limit: int = 10) -> List[ArchiveJob]:
        """Get recent archive jobs."""
        with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.started_at,
                reverse=True,
            )
            return jobs[:limit]


# =============================================================================
# WRAP HASH COMPUTATION
# =============================================================================

def compute_wrap_hash() -> str:
    """Compute WRAP hash for GID-07 deliverable."""
    content = f"GID-07:pdo_scale:v{PDO_SCALE_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "PDO_SCALE_VERSION",
    "ShardStatus",
    "RetentionAction",
    "StorageTier",
    "ReplicationMode",
    "ConsistencyLevel",
    "PDOScaleError",
    "ShardNotFoundError",
    "ReplicationError",
    "RetentionViolationError",
    "PDORecord",
    "Shard",
    "RetentionPolicy",
    "Replica",
    "QueryPlan",
    "CompactionResult",
    "ArchiveJob",
    "PDOShardManager",
    "RetentionPolicyEngine",
    "PDOCompactor",
    "ReplicationManager",
    "QueryOptimizer",
    "ArchiveManager",
    "compute_wrap_hash",
]
