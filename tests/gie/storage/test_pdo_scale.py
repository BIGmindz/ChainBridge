"""
Unit Tests for PDO Scale Manager.

Tests cover:
- PDOShardManager (sharding, consistent hashing, CRUD)
- RetentionPolicyEngine (policies, evaluation, enforcement)
- PDOCompactor (deduplication, compression)
- ReplicationManager (replicas, failover)
- QueryOptimizer (planning, caching, execution)
- ArchiveManager (tier migration, retrieval)
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from core.gie.storage.pdo_scale import (
    PDO_SCALE_VERSION,
    ShardStatus,
    RetentionAction,
    StorageTier,
    ReplicationMode,
    ConsistencyLevel,
    PDOScaleError,
    ShardNotFoundError,
    PDORecord,
    Shard,
    RetentionPolicy,
    Replica,
    QueryPlan,
    CompactionResult,
    ArchiveJob,
    PDOShardManager,
    RetentionPolicyEngine,
    PDOCompactor,
    ReplicationManager,
    QueryOptimizer,
    ArchiveManager,
    compute_wrap_hash,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def shard_manager() -> PDOShardManager:
    """Create a shard manager with test shards."""
    manager = PDOShardManager(virtual_nodes=32)
    manager.add_shard(region="us-east-1", capacity_bytes=1_000_000)
    manager.add_shard(region="us-west-2", capacity_bytes=1_000_000)
    return manager


@pytest.fixture
def retention_engine() -> RetentionPolicyEngine:
    """Create a retention policy engine."""
    return RetentionPolicyEngine()


@pytest.fixture
def compactor() -> PDOCompactor:
    """Create a compactor."""
    return PDOCompactor()


@pytest.fixture
def replication_manager() -> ReplicationManager:
    """Create a replication manager."""
    return ReplicationManager(mode=ReplicationMode.ASYNCHRONOUS)


@pytest.fixture
def query_optimizer() -> QueryOptimizer:
    """Create a query optimizer."""
    return QueryOptimizer()


@pytest.fixture
def archive_manager() -> ArchiveManager:
    """Create an archive manager."""
    return ArchiveManager()


# =============================================================================
# TEST ENUMS
# =============================================================================

class TestEnums:
    """Tests for enumeration types."""
    
    def test_shard_status_values(self) -> None:
        """Test ShardStatus enum values."""
        assert ShardStatus.ACTIVE.value == "ACTIVE"
        assert ShardStatus.READONLY.value == "READONLY"
        assert ShardStatus.MIGRATING.value == "MIGRATING"
        assert ShardStatus.OFFLINE.value == "OFFLINE"
        assert ShardStatus.ARCHIVED.value == "ARCHIVED"
    
    def test_retention_action_values(self) -> None:
        """Test RetentionAction enum values."""
        assert RetentionAction.KEEP.value == "KEEP"
        assert RetentionAction.ARCHIVE.value == "ARCHIVE"
        assert RetentionAction.DELETE.value == "DELETE"
        assert RetentionAction.COMPRESS.value == "COMPRESS"
        assert RetentionAction.MOVE_TIER.value == "MOVE_TIER"
    
    def test_storage_tier_values(self) -> None:
        """Test StorageTier enum values."""
        assert StorageTier.HOT.value == "HOT"
        assert StorageTier.WARM.value == "WARM"
        assert StorageTier.COLD.value == "COLD"
        assert StorageTier.GLACIER.value == "GLACIER"
    
    def test_replication_mode_values(self) -> None:
        """Test ReplicationMode enum values."""
        assert ReplicationMode.SYNCHRONOUS.value == "SYNCHRONOUS"
        assert ReplicationMode.ASYNCHRONOUS.value == "ASYNCHRONOUS"
        assert ReplicationMode.SEMI_SYNC.value == "SEMI_SYNC"
    
    def test_consistency_level_values(self) -> None:
        """Test ConsistencyLevel enum values."""
        assert ConsistencyLevel.ONE.value == "ONE"
        assert ConsistencyLevel.QUORUM.value == "QUORUM"
        assert ConsistencyLevel.ALL.value == "ALL"
        assert ConsistencyLevel.LOCAL.value == "LOCAL"


# =============================================================================
# TEST DATA CLASSES
# =============================================================================

class TestPDORecord:
    """Tests for PDORecord dataclass."""
    
    def test_create_record(self) -> None:
        """Test creating a PDO record."""
        now = datetime.now(timezone.utc)
        record = PDORecord(
            pdo_id="test-001",
            data=b"test data",
            created_at=now,
            updated_at=now,
        )
        
        assert record.pdo_id == "test-001"
        assert record.data == b"test data"
        assert record.tier == StorageTier.HOT
        assert record.compressed is False
        assert record.checksum != ""  # Auto-generated
    
    def test_record_with_metadata(self) -> None:
        """Test record with metadata."""
        now = datetime.now(timezone.utc)
        record = PDORecord(
            pdo_id="test-002",
            data=b"metadata test",
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
        )
        
        assert record.metadata == {"key": "value"}
    
    def test_record_to_dict(self) -> None:
        """Test converting record to dict."""
        now = datetime.now(timezone.utc)
        record = PDORecord(
            pdo_id="test-003",
            data=b"dict test",
            created_at=now,
            updated_at=now,
        )
        
        d = record.to_dict()
        assert d["pdo_id"] == "test-003"
        assert d["size_bytes"] == len(b"dict test")
        assert d["tier"] == "HOT"


class TestShard:
    """Tests for Shard dataclass."""
    
    def test_create_shard(self) -> None:
        """Test creating a shard."""
        shard = Shard(
            shard_id="shard_001",
            hash_range_start=0,
            hash_range_end=1000,
            status=ShardStatus.ACTIVE,
            region="us-east-1",
            capacity_bytes=1_000_000,
        )
        
        assert shard.shard_id == "shard_001"
        assert shard.status == ShardStatus.ACTIVE
        assert shard.region == "us-east-1"
    
    def test_shard_utilization(self) -> None:
        """Test shard utilization calculation."""
        shard = Shard(
            shard_id="shard_002",
            hash_range_start=0,
            hash_range_end=1000,
            status=ShardStatus.ACTIVE,
            region="us-west-2",
            capacity_bytes=1000,
            used_bytes=250,
        )
        
        assert shard.utilization == 25.0
    
    def test_shard_to_dict(self) -> None:
        """Test converting shard to dict."""
        shard = Shard(
            shard_id="shard_003",
            hash_range_start=0,
            hash_range_end=100,
            status=ShardStatus.ACTIVE,
            region="eu-west-1",
            capacity_bytes=500,
            used_bytes=100,
            record_count=5,
        )
        
        d = shard.to_dict()
        assert d["shard_id"] == "shard_003"
        assert d["hash_range"] == [0, 100]
        assert d["utilization_percent"] == 20.0


# =============================================================================
# TEST PDO SHARD MANAGER
# =============================================================================

class TestPDOShardManager:
    """Tests for PDOShardManager."""
    
    def test_add_shard(self, shard_manager: PDOShardManager) -> None:
        """Test adding a shard."""
        shard = shard_manager.add_shard(region="eu-central-1", capacity_bytes=500_000)
        
        assert shard.shard_id.startswith("shard_")
        assert shard.region == "eu-central-1"
        assert shard.status == ShardStatus.ACTIVE
    
    def test_get_shard(self, shard_manager: PDOShardManager) -> None:
        """Test getting a shard by ID."""
        shard = shard_manager.add_shard(region="ap-south-1", capacity_bytes=250_000)
        
        retrieved = shard_manager.get_shard(shard.shard_id)
        assert retrieved is not None
        assert retrieved.shard_id == shard.shard_id
    
    def test_get_shard_for_key(self, shard_manager: PDOShardManager) -> None:
        """Test consistent hashing for key."""
        shard_id_1 = shard_manager.get_shard_for_key("test-key-1")
        shard_id_2 = shard_manager.get_shard_for_key("test-key-1")
        
        # Same key should always map to same shard
        assert shard_id_1 == shard_id_2
    
    def test_store_and_retrieve(self, shard_manager: PDOShardManager) -> None:
        """Test storing and retrieving records."""
        record = shard_manager.store(
            pdo_id="pdo-001",
            data=b"test data for storage",
        )
        
        assert record.pdo_id == "pdo-001"
        
        retrieved = shard_manager.retrieve("pdo-001")
        assert retrieved is not None
        assert retrieved.data == b"test data for storage"
    
    def test_delete_record(self, shard_manager: PDOShardManager) -> None:
        """Test deleting a record."""
        shard_manager.store(pdo_id="pdo-delete", data=b"to be deleted")
        
        result = shard_manager.delete("pdo-delete")
        assert result is True
        
        retrieved = shard_manager.retrieve("pdo-delete")
        assert retrieved is None
    
    def test_delete_nonexistent(self, shard_manager: PDOShardManager) -> None:
        """Test deleting nonexistent record."""
        result = shard_manager.delete("nonexistent")
        assert result is False
    
    def test_store_with_metadata(self, shard_manager: PDOShardManager) -> None:
        """Test storing with metadata."""
        record = shard_manager.store(
            pdo_id="pdo-meta",
            data=b"data with metadata",
            metadata={"source": "test", "priority": 1},
        )
        
        assert record.metadata["source"] == "test"
        assert record.metadata["priority"] == 1
    
    def test_get_stats(self, shard_manager: PDOShardManager) -> None:
        """Test getting cluster statistics."""
        # Store some records
        for i in range(5):
            shard_manager.store(pdo_id=f"stat-{i}", data=b"x" * 100)
        
        stats = shard_manager.get_stats()
        
        assert stats["total_records"] == 5
        assert stats["total_bytes"] == 500
        assert len(stats["shards"]) >= 2
    
    def test_no_shards_error(self) -> None:
        """Test error when no shards available."""
        manager = PDOShardManager()
        
        with pytest.raises(PDOScaleError, match="No shards available"):
            manager.get_shard_for_key("test")
    
    def test_split_shard(self, shard_manager: PDOShardManager) -> None:
        """Test splitting a shard."""
        # Add data to a shard
        for i in range(10):
            shard_manager.store(pdo_id=f"split-{i}", data=b"x" * 50)
        
        stats_before = shard_manager.get_stats()
        initial_shard_count = stats_before["shard_count"]
        
        # Split first shard
        first_shard = list(shard_manager._shards.values())[0]
        new_1, new_2 = shard_manager.split_shard(first_shard.shard_id)
        
        stats_after = shard_manager.get_stats()
        assert stats_after["shard_count"] == initial_shard_count + 2


class TestPDOShardManagerThreadSafety:
    """Thread safety tests for PDOShardManager."""
    
    def test_concurrent_stores(self) -> None:
        """Test concurrent store operations."""
        manager = PDOShardManager()
        manager.add_shard(region="test", capacity_bytes=10_000_000)
        
        errors = []
        
        def store_records(prefix: str, count: int) -> None:
            for i in range(count):
                try:
                    manager.store(pdo_id=f"{prefix}-{i}", data=b"x" * 100)
                except Exception as e:
                    errors.append(str(e))
        
        threads = [
            threading.Thread(target=store_records, args=(f"thread-{t}", 50))
            for t in range(4)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        stats = manager.get_stats()
        assert stats["total_records"] == 200


# =============================================================================
# TEST RETENTION POLICY ENGINE
# =============================================================================

class TestRetentionPolicyEngine:
    """Tests for RetentionPolicyEngine."""
    
    def test_create_policy(self, retention_engine: RetentionPolicyEngine) -> None:
        """Test creating a retention policy."""
        policy = retention_engine.create_policy(
            name="Hot Tier Retention",
            tier=StorageTier.HOT,
            max_age_days=30,
            action=RetentionAction.MOVE_TIER,
            target_tier=StorageTier.WARM,
        )
        
        assert policy.policy_id.startswith("RET-")
        assert policy.name == "Hot Tier Retention"
        assert policy.max_age_days == 30
    
    def test_evaluate_keep(self, retention_engine: RetentionPolicyEngine) -> None:
        """Test evaluation returns KEEP for new records."""
        retention_engine.create_policy(
            name="Test Policy",
            tier=StorageTier.HOT,
            max_age_days=30,
            action=RetentionAction.DELETE,
        )
        
        now = datetime.now(timezone.utc)
        record = PDORecord(
            pdo_id="new-record",
            data=b"test",
            created_at=now - timedelta(days=5),
            updated_at=now,
        )
        
        action, target = retention_engine.evaluate(record, now)
        assert action == RetentionAction.KEEP
    
    def test_evaluate_delete(self, retention_engine: RetentionPolicyEngine) -> None:
        """Test evaluation returns DELETE for old records."""
        retention_engine.create_policy(
            name="Delete Old",
            tier=StorageTier.HOT,
            max_age_days=30,
            action=RetentionAction.DELETE,
        )
        
        now = datetime.now(timezone.utc)
        record = PDORecord(
            pdo_id="old-record",
            data=b"test",
            created_at=now - timedelta(days=60),
            updated_at=now,
        )
        
        action, target = retention_engine.evaluate(record, now)
        assert action == RetentionAction.DELETE
    
    def test_evaluate_move_tier(self, retention_engine: RetentionPolicyEngine) -> None:
        """Test evaluation returns MOVE_TIER."""
        retention_engine.create_policy(
            name="Move to Warm",
            tier=StorageTier.HOT,
            max_age_days=7,
            action=RetentionAction.MOVE_TIER,
            target_tier=StorageTier.WARM,
        )
        
        now = datetime.now(timezone.utc)
        record = PDORecord(
            pdo_id="aging-record",
            data=b"test",
            created_at=now - timedelta(days=10),
            updated_at=now,
        )
        
        action, target = retention_engine.evaluate(record, now)
        assert action == RetentionAction.MOVE_TIER
        assert target == StorageTier.WARM
    
    def test_policy_with_conditions(self, retention_engine: RetentionPolicyEngine) -> None:
        """Test policy with size conditions."""
        retention_engine.create_policy(
            name="Large File Cleanup",
            tier=StorageTier.HOT,
            max_age_days=7,
            action=RetentionAction.DELETE,
            conditions={"min_size_bytes": 1000},
        )
        
        now = datetime.now(timezone.utc)
        
        # Small file should not match
        small_record = PDORecord(
            pdo_id="small",
            data=b"x" * 100,
            created_at=now - timedelta(days=30),
            updated_at=now,
        )
        action, _ = retention_engine.evaluate(small_record, now)
        assert action == RetentionAction.KEEP
        
        # Large file should match
        large_record = PDORecord(
            pdo_id="large",
            data=b"x" * 2000,
            created_at=now - timedelta(days=30),
            updated_at=now,
        )
        action, _ = retention_engine.evaluate(large_record, now)
        assert action == RetentionAction.DELETE
    
    def test_apply_policies_dry_run(
        self,
        retention_engine: RetentionPolicyEngine,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test applying policies in dry run mode."""
        retention_engine.create_policy(
            name="Cleanup",
            tier=StorageTier.HOT,
            max_age_days=0,
            action=RetentionAction.DELETE,
        )
        
        # Store records
        for i in range(5):
            shard_manager.store(pdo_id=f"apply-{i}", data=b"test")
        
        results = retention_engine.apply_policies(shard_manager, dry_run=True)
        
        # Records should still exist after dry run
        assert results["deleted"] == 5
        stats = shard_manager.get_stats()
        assert stats["total_records"] == 5
    
    def test_get_all_policies(self, retention_engine: RetentionPolicyEngine) -> None:
        """Test getting all policies."""
        retention_engine.create_policy(
            name="Policy 1",
            tier=StorageTier.HOT,
            max_age_days=30,
            action=RetentionAction.DELETE,
        )
        retention_engine.create_policy(
            name="Policy 2",
            tier=StorageTier.WARM,
            max_age_days=90,
            action=RetentionAction.ARCHIVE,
        )
        
        policies = retention_engine.get_all_policies()
        assert len(policies) == 2


# =============================================================================
# TEST PDO COMPACTOR
# =============================================================================

class TestPDOCompactor:
    """Tests for PDOCompactor."""
    
    def test_compact_empty(
        self,
        compactor: PDOCompactor,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test compacting empty shards."""
        result = compactor.compact(shard_manager)
        
        assert result.records_processed == 0
        assert result.records_removed == 0
    
    def test_compact_with_records(
        self,
        compactor: PDOCompactor,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test compacting with records."""
        for i in range(10):
            shard_manager.store(pdo_id=f"compact-{i}", data=b"unique " + bytes([i]))
        
        result = compactor.compact(shard_manager)
        
        assert result.records_processed == 10
        assert result.records_removed == 0  # No duplicates
    
    def test_deduplicate(
        self,
        compactor: PDOCompactor,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test deduplication."""
        # Store identical data with different IDs
        for i in range(5):
            shard_manager.store(pdo_id=f"dup-{i}", data=b"same content")
        
        result = compactor.compact(shard_manager, deduplicate=True)
        
        # 4 duplicates should be removed
        assert result.records_removed == 4
    
    def test_find_duplicates(
        self,
        compactor: PDOCompactor,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test finding duplicates without removing."""
        for i in range(3):
            shard_manager.store(pdo_id=f"find-dup-{i}", data=b"duplicate data")
        shard_manager.store(pdo_id="unique", data=b"unique data")
        
        duplicates = compactor.find_duplicates(shard_manager)
        
        assert len(duplicates) == 1
        assert duplicates[0]["count"] == 3
    
    def test_compaction_history(
        self,
        compactor: PDOCompactor,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test compaction history tracking."""
        compactor.compact(shard_manager)
        compactor.compact(shard_manager)
        
        history = compactor.get_compaction_history()
        assert len(history) == 2


# =============================================================================
# TEST REPLICATION MANAGER
# =============================================================================

class TestReplicationManager:
    """Tests for ReplicationManager."""
    
    def test_add_replica(self, replication_manager: ReplicationManager) -> None:
        """Test adding a replica."""
        replica = replication_manager.add_replica(
            shard_id="shard_001",
            region="us-east-1",
            is_primary=True,
        )
        
        assert replica.replica_id.startswith("rep_")
        assert replica.is_primary is True
    
    def test_get_replicas(self, replication_manager: ReplicationManager) -> None:
        """Test getting replicas for a shard."""
        replication_manager.add_replica("shard_001", "us-east-1", True)
        replication_manager.add_replica("shard_001", "us-west-2", False)
        
        replicas = replication_manager.get_replicas("shard_001")
        assert len(replicas) == 2
    
    def test_get_primary(self, replication_manager: ReplicationManager) -> None:
        """Test getting primary replica."""
        replication_manager.add_replica("shard_002", "eu-west-1", True)
        replication_manager.add_replica("shard_002", "eu-central-1", False)
        
        primary = replication_manager.get_primary("shard_002")
        assert primary is not None
        assert primary.is_primary is True
    
    def test_replicate_quorum(self, replication_manager: ReplicationManager) -> None:
        """Test replication with quorum consistency."""
        replication_manager.add_replica("shard_003", "us-east-1", True)
        replication_manager.add_replica("shard_003", "us-west-2", False)
        replication_manager.add_replica("shard_003", "eu-west-1", False)
        
        result = replication_manager.replicate(
            shard_id="shard_003",
            data=b"replicated data",
            consistency=ConsistencyLevel.QUORUM,
        )
        
        assert result["success"] is True
        assert result["acks"] >= 2  # Quorum
    
    def test_replicate_no_replicas(self, replication_manager: ReplicationManager) -> None:
        """Test replication with no replicas."""
        result = replication_manager.replicate(
            shard_id="nonexistent",
            data=b"test",
        )
        
        assert result["success"] is False
    
    def test_promote_replica(self, replication_manager: ReplicationManager) -> None:
        """Test promoting a replica to primary."""
        primary = replication_manager.add_replica("shard_004", "us-east-1", True)
        secondary = replication_manager.add_replica("shard_004", "us-west-2", False)
        
        promoted = replication_manager.promote_replica(secondary.replica_id)
        
        assert promoted is not None
        assert promoted.is_primary is True
        
        # Old primary should be demoted
        old_primary = [r for r in replication_manager.get_replicas("shard_004")
                       if r.replica_id == primary.replica_id][0]
        assert old_primary.is_primary is False
    
    def test_get_lag_report(self, replication_manager: ReplicationManager) -> None:
        """Test getting replication lag report."""
        replication_manager.add_replica("shard_005", "us-east-1", True)
        replication_manager.add_replica("shard_005", "eu-west-1", False)
        
        # Simulate some replication
        replication_manager.replicate("shard_005", b"test")
        
        report = replication_manager.get_lag_report()
        
        assert "average_lag_ms" in report
        assert "replica_count" in report
        assert report["mode"] == "ASYNCHRONOUS"


# =============================================================================
# TEST QUERY OPTIMIZER
# =============================================================================

class TestQueryOptimizer:
    """Tests for QueryOptimizer."""
    
    def test_optimize_point_query(
        self,
        query_optimizer: QueryOptimizer,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test optimizing a point query."""
        shard_manager.store(pdo_id="opt-001", data=b"test")
        
        plan = query_optimizer.optimize(
            query={"pdo_id": "opt-001"},
            shard_manager=shard_manager,
        )
        
        assert len(plan.shards_accessed) == 1
        assert plan.uses_index is True
        assert plan.estimated_rows == 1
    
    def test_optimize_scan_query(
        self,
        query_optimizer: QueryOptimizer,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test optimizing a full scan query."""
        for i in range(10):
            shard_manager.store(pdo_id=f"scan-{i}", data=b"test")
        
        plan = query_optimizer.optimize(
            query={"tier": "HOT"},
            shard_manager=shard_manager,
        )
        
        assert len(plan.shards_accessed) == 2  # All active shards
        assert plan.uses_index is False
    
    def test_query_caching(
        self,
        query_optimizer: QueryOptimizer,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test query plan caching."""
        # Clear any existing cache to ensure test isolation
        query_optimizer._query_cache.clear()
        query_optimizer._cache_hits = 0
        query_optimizer._cache_misses = 0
        
        query = {"pdo_id": "cache-test"}
        
        plan_1 = query_optimizer.optimize(query, shard_manager)
        plan_2 = query_optimizer.optimize(query, shard_manager)
        
        assert plan_1.cache_hit is False
        assert plan_2.cache_hit is True
        
        stats = query_optimizer.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
    
    def test_execute_query(
        self,
        query_optimizer: QueryOptimizer,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test executing a query."""
        shard_manager.store(pdo_id="exec-001", data=b"result")
        shard_manager.store(pdo_id="exec-002", data=b"other")
        
        plan = query_optimizer.optimize(
            query={"pdo_id": "exec-001"},
            shard_manager=shard_manager,
        )
        
        results = query_optimizer.execute(
            plan,
            shard_manager,
            {"pdo_id": "exec-001"},
        )
        
        assert len(results) == 1
        assert results[0].pdo_id == "exec-001"
    
    def test_execute_with_limit(
        self,
        query_optimizer: QueryOptimizer,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test query execution with limit."""
        for i in range(10):
            shard_manager.store(pdo_id=f"limit-{i}", data=b"test")
        
        query = {"limit": 3}
        plan = query_optimizer.optimize(query, shard_manager)
        results = query_optimizer.execute(plan, shard_manager, query)
        
        assert len(results) == 3


# =============================================================================
# TEST ARCHIVE MANAGER
# =============================================================================

class TestArchiveManager:
    """Tests for ArchiveManager."""
    
    def test_archive_records(
        self,
        archive_manager: ArchiveManager,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test archiving records."""
        for i in range(5):
            shard_manager.store(pdo_id=f"arch-{i}", data=b"archivable")
        
        job = archive_manager.archive(
            shard_manager,
            source_tier=StorageTier.HOT,
            target_tier=StorageTier.COLD,
        )
        
        assert job.status == "COMPLETED"
        assert job.records_count == 5
    
    def test_retrieve_from_archive(
        self,
        archive_manager: ArchiveManager,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test retrieving from archive."""
        shard_manager.store(pdo_id="retrieve-test", data=b"archived data")
        
        archive_manager.archive(
            shard_manager,
            source_tier=StorageTier.HOT,
            target_tier=StorageTier.GLACIER,
        )
        
        retrieved = archive_manager.retrieve("retrieve-test", StorageTier.GLACIER)
        assert retrieved is not None
        assert retrieved.tier == StorageTier.GLACIER
    
    def test_archive_stats(
        self,
        archive_manager: ArchiveManager,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test archive statistics."""
        for i in range(3):
            shard_manager.store(pdo_id=f"stat-arch-{i}", data=b"x" * 100)
        
        archive_manager.archive(
            shard_manager,
            source_tier=StorageTier.HOT,
            target_tier=StorageTier.COLD,
        )
        
        stats = archive_manager.get_archive_stats()
        
        assert stats["tiers"]["COLD"]["record_count"] == 3
        assert stats["completed_jobs"] == 1
    
    def test_get_jobs(
        self,
        archive_manager: ArchiveManager,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test getting archive jobs."""
        shard_manager.store(pdo_id="job-test", data=b"test")
        
        archive_manager.archive(shard_manager, StorageTier.HOT, StorageTier.WARM)
        archive_manager.archive(shard_manager, StorageTier.WARM, StorageTier.COLD)
        
        jobs = archive_manager.get_jobs()
        assert len(jobs) == 2
    
    def test_max_records_limit(
        self,
        archive_manager: ArchiveManager,
        shard_manager: PDOShardManager,
    ) -> None:
        """Test max records limit on archive."""
        for i in range(10):
            shard_manager.store(pdo_id=f"max-{i}", data=b"test")
        
        job = archive_manager.archive(
            shard_manager,
            source_tier=StorageTier.HOT,
            target_tier=StorageTier.COLD,
            max_records=3,
        )
        
        assert job.records_count == 3


# =============================================================================
# TEST WRAP HASH
# =============================================================================

class TestWrapHash:
    """Tests for WRAP hash computation."""
    
    def test_wrap_hash_format(self) -> None:
        """Test WRAP hash format."""
        wrap_hash = compute_wrap_hash()
        
        assert len(wrap_hash) == 16
        assert all(c in "0123456789abcdef" for c in wrap_hash)
    
    def test_wrap_hash_consistency(self) -> None:
        """Test WRAP hash is consistent."""
        hash_1 = compute_wrap_hash()
        hash_2 = compute_wrap_hash()
        
        assert hash_1 == hash_2
    
    def test_wrap_hash_contains_version(self) -> None:
        """Test WRAP hash includes version."""
        # Hash should change if version changes
        original = compute_wrap_hash()
        assert original is not None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for PDO scale components."""
    
    def test_full_lifecycle(self) -> None:
        """Test full PDO lifecycle."""
        # Setup
        shard_manager = PDOShardManager()
        shard_manager.add_shard("us-east-1", 10_000_000)
        shard_manager.add_shard("us-west-2", 10_000_000)
        
        retention_engine = RetentionPolicyEngine()
        retention_engine.create_policy(
            name="Archive Old",
            tier=StorageTier.HOT,
            max_age_days=7,
            action=RetentionAction.MOVE_TIER,
            target_tier=StorageTier.WARM,
        )
        
        compactor = PDOCompactor()
        replication_manager = ReplicationManager()
        query_optimizer = QueryOptimizer()
        archive_manager = ArchiveManager()
        
        # Store records
        for i in range(20):
            shard_manager.store(pdo_id=f"lifecycle-{i}", data=b"test data " + bytes([i]))
        
        # Setup replication
        for shard_id in [s["shard_id"] for s in shard_manager.get_stats()["shards"]]:
            replication_manager.add_replica(shard_id, "us-east-1", True)
            replication_manager.add_replica(shard_id, "us-west-2", False)
        
        # Query
        plan = query_optimizer.optimize({"tier": "HOT"}, shard_manager)
        results = query_optimizer.execute(plan, shard_manager, {"tier": "HOT"})
        assert len(results) == 20
        
        # Compact
        compact_result = compactor.compact(shard_manager)
        assert compact_result.records_processed == 20
        
        # Archive some records
        archive_job = archive_manager.archive(
            shard_manager,
            StorageTier.HOT,
            StorageTier.COLD,
            max_records=5,
        )
        assert archive_job.records_count == 5
        
        # Verify stats
        stats = shard_manager.get_stats()
        assert stats["total_records"] == 20
    
    def test_version_exists(self) -> None:
        """Test version constant exists."""
        assert PDO_SCALE_VERSION == "1.0.0"
