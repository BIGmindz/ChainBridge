"""
Test PDO Store v2 Scale

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-07 (Dan) — Data Engineer
"""

import pytest
import threading
import time
from typing import List

from core.gie.storage.pdo_store_v2 import (
    # Enums
    StorageState,
    IndexType,
    
    # Exceptions
    PDOStoreError,
    ImmutabilityViolationError,
    ShardOverflowError,
    DuplicateEntryError,
    IndexCorruptionError,
    
    # Data classes
    PDOEntry,
    ShardMetrics,
    StoreMetrics,
    
    # Classes
    PDOShard,
    PDOIndex,
    PDOStoreV2,
    
    # Singleton
    get_pdo_store_v2,
    reset_pdo_store_v2,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def store():
    """Provide fresh PDO store."""
    reset_pdo_store_v2()
    return PDOStoreV2()


@pytest.fixture
def small_store():
    """Provide small store for overflow tests."""
    reset_pdo_store_v2()
    return PDOStoreV2(config={
        "shard_count": 4,
        "max_entries_per_shard": 10,
    })


@pytest.fixture
def sample_entry():
    """Provide sample PDO entry data."""
    return {
        "pdo_id": "PDO-TEST-001",
        "pac_id": "PAC-028",
        "agent_gids": ["GID-01", "GID-02"],
        "ber_status": "APPROVE",
        "wrap_hashes": ["sha256:wrap1", "sha256:wrap2"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOEntry
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOEntry:
    """Tests for PDOEntry dataclass."""

    def test_creation(self):
        """Can create PDO entry."""
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=("sha256:wrap1",),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
        )
        assert entry.pdo_id == "PDO-001"
        assert entry.state == StorageState.PENDING

    def test_immutable_tuples(self):
        """Lists are converted to tuples."""
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=["GID-01", "GID-02"],
            ber_status="APPROVE",
            wrap_hashes=["sha256:wrap1"],
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
        )
        assert isinstance(entry.agent_gids, tuple)
        assert isinstance(entry.wrap_hashes, tuple)

    def test_compute_hash_deterministic(self):
        """Hash computation is deterministic."""
        hash1 = PDOEntry.compute_hash(
            "PDO-001", "PAC-001", ["GID-01"], "APPROVE", ["sha256:wrap"]
        )
        hash2 = PDOEntry.compute_hash(
            "PDO-001", "PAC-001", ["GID-01"], "APPROVE", ["sha256:wrap"]
        )
        assert hash1 == hash2
        assert hash1.startswith("sha256:")

    def test_compute_hash_different_inputs(self):
        """Different inputs produce different hashes."""
        hash1 = PDOEntry.compute_hash(
            "PDO-001", "PAC-001", ["GID-01"], "APPROVE", ["sha256:wrap"]
        )
        hash2 = PDOEntry.compute_hash(
            "PDO-002", "PAC-001", ["GID-01"], "APPROVE", ["sha256:wrap"]
        )
        assert hash1 != hash2

    def test_to_dict(self):
        """Can convert to dictionary."""
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=("sha256:wrap1",),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
        )
        result = entry.to_dict()
        assert result["pdo_id"] == "PDO-001"
        assert result["state"] == "PENDING"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOShard
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOShard:
    """Tests for PDOShard."""

    def test_write_read(self):
        """Can write and read entry."""
        shard = PDOShard(shard_id=0, max_entries=100)
        
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=("sha256:wrap1",),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
        )
        
        shard.write(entry)
        result = shard.read("PDO-001")
        
        assert result is not None
        assert result.pdo_id == "PDO-001"
        assert result.state == StorageState.COMMITTED

    def test_duplicate_raises(self):
        """Writing duplicate raises DuplicateEntryError."""
        shard = PDOShard(shard_id=0, max_entries=100)
        
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
        )
        
        shard.write(entry)
        
        with pytest.raises(DuplicateEntryError):
            shard.write(entry)

    def test_immutability_violation(self):
        """Modifying existing entry raises ImmutabilityViolationError."""
        shard = PDOShard(shard_id=0, max_entries=100)
        
        entry1 = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:original",
            created_at="2025-12-26T10:00:00Z",
        )
        
        entry2 = PDOEntry(
            pdo_id="PDO-001",  # Same ID
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="REJECT",  # Different status
            wrap_hashes=(),
            content_hash="sha256:modified",  # Different hash
            created_at="2025-12-26T10:00:00Z",
        )
        
        shard.write(entry1)
        
        with pytest.raises(ImmutabilityViolationError):
            shard.write(entry2)

    def test_overflow_raises(self):
        """Exceeding capacity raises ShardOverflowError."""
        shard = PDOShard(shard_id=0, max_entries=5)
        
        for i in range(5):
            entry = PDOEntry(
                pdo_id=f"PDO-{i}",
                pac_id="PAC-001",
                agent_gids=(),
                ber_status="APPROVE",
                wrap_hashes=(),
                content_hash=f"sha256:{i}",
                created_at="2025-12-26T10:00:00Z",
            )
            shard.write(entry)
        
        with pytest.raises(ShardOverflowError):
            shard.write(PDOEntry(
                pdo_id="PDO-overflow",
                pac_id="PAC-001",
                agent_gids=(),
                ber_status="APPROVE",
                wrap_hashes=(),
                content_hash="sha256:overflow",
                created_at="2025-12-26T10:00:00Z",
            ))

    def test_metrics(self):
        """Shard tracks metrics."""
        shard = PDOShard(shard_id=0, max_entries=100)
        
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=(),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
        )
        
        shard.write(entry)
        shard.read("PDO-001")
        
        metrics = shard.get_metrics()
        assert metrics.entry_count == 1
        assert metrics.total_writes == 1
        assert metrics.total_reads == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOIndex
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOIndex:
    """Tests for PDOIndex."""

    def test_index_entry(self):
        """Can index entry."""
        index = PDOIndex()
        
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01", "GID-02"),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
            shard_id=5,
        )
        
        index.index(entry)
        
        assert index.get_shard("PDO-001") == 5

    def test_find_by_pac(self):
        """Can find by PAC ID."""
        index = PDOIndex()
        
        for i in range(3):
            entry = PDOEntry(
                pdo_id=f"PDO-{i}",
                pac_id="PAC-001",
                agent_gids=(),
                ber_status="APPROVE",
                wrap_hashes=(),
                content_hash=f"sha256:{i}",
                created_at="2025-12-26T10:00:00Z",
                shard_id=0,
            )
            index.index(entry)
        
        results = index.find_by_pac("PAC-001")
        assert len(results) == 3

    def test_find_by_agent(self):
        """Can find by agent GID."""
        index = PDOIndex()
        
        entry1 = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01", "GID-02"),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:1",
            created_at="2025-12-26T10:00:00Z",
            shard_id=0,
        )
        entry2 = PDOEntry(
            pdo_id="PDO-002",
            pac_id="PAC-002",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:2",
            created_at="2025-12-26T10:00:00Z",
            shard_id=0,
        )
        
        index.index(entry1)
        index.index(entry2)
        
        results = index.find_by_agent("GID-01")
        assert len(results) == 2
        
        results = index.find_by_agent("GID-02")
        assert len(results) == 1

    def test_remove_entry(self):
        """Can remove entry from index."""
        index = PDOIndex()
        
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
            shard_id=0,
        )
        
        index.index(entry)
        assert index.get_shard("PDO-001") == 0
        
        index.remove(entry)
        assert index.get_shard("PDO-001") is None

    def test_get_sizes(self):
        """Can get index sizes."""
        index = PDOIndex()
        
        entry = PDOEntry(
            pdo_id="PDO-001",
            pac_id="PAC-001",
            agent_gids=("GID-01",),
            ber_status="APPROVE",
            wrap_hashes=(),
            content_hash="sha256:content",
            created_at="2025-12-26T10:00:00Z",
            shard_id=0,
        )
        index.index(entry)
        
        sizes = index.get_sizes()
        assert sizes["primary"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOStoreV2 - Basic Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOStoreV2Basic:
    """Tests for basic store operations."""

    def test_store_and_get(self, store, sample_entry):
        """Can store and retrieve PDO."""
        entry = store.store(**sample_entry)
        
        assert entry.pdo_id == "PDO-TEST-001"
        assert entry.state == StorageState.COMMITTED
        
        retrieved = store.get("PDO-TEST-001")
        assert retrieved is not None
        assert retrieved.pdo_id == entry.pdo_id

    def test_exists(self, store, sample_entry):
        """Can check existence."""
        assert store.exists("PDO-TEST-001") is False
        
        store.store(**sample_entry)
        
        assert store.exists("PDO-TEST-001") is True

    def test_find_by_pac(self, store):
        """Can find by PAC ID."""
        store.store("PDO-1", "PAC-001", ["GID-01"], "APPROVE", [])
        store.store("PDO-2", "PAC-001", ["GID-02"], "APPROVE", [])
        store.store("PDO-3", "PAC-002", ["GID-01"], "APPROVE", [])
        
        results = store.find_by_pac("PAC-001")
        assert len(results) == 2

    def test_find_by_agent(self, store):
        """Can find by agent GID."""
        store.store("PDO-1", "PAC-001", ["GID-01", "GID-02"], "APPROVE", [])
        store.store("PDO-2", "PAC-002", ["GID-01"], "APPROVE", [])
        store.store("PDO-3", "PAC-003", ["GID-03"], "APPROVE", [])
        
        results = store.find_by_agent("GID-01")
        assert len(results) == 2

    def test_store_batch(self, store):
        """Can store batch of entries."""
        entries = [
            {"pdo_id": f"PDO-{i}", "pac_id": "PAC-001", "agent_gids": ["GID-01"], 
             "ber_status": "APPROVE", "wrap_hashes": []}
            for i in range(10)
        ]
        
        successful, failed = store.store_batch(entries)
        
        assert len(successful) == 10
        assert len(failed) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOStoreV2 - Immutability
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOStoreV2Immutability:
    """Tests for immutability enforcement."""

    def test_duplicate_raises(self, store, sample_entry):
        """Storing duplicate raises DuplicateEntryError."""
        store.store(**sample_entry)
        
        with pytest.raises(DuplicateEntryError):
            store.store(**sample_entry)

    def test_modification_raises(self, store, sample_entry):
        """Modifying existing entry raises ImmutabilityViolationError."""
        store.store(**sample_entry)
        
        modified = sample_entry.copy()
        modified["ber_status"] = "REJECT"  # Modified
        
        with pytest.raises(ImmutabilityViolationError):
            store.store(**modified)

    def test_validate_immutability(self, store, sample_entry):
        """Can validate entry hasn't changed."""
        entry = store.store(**sample_entry)
        
        assert store.validate_immutability("PDO-TEST-001", entry.content_hash)
        assert not store.validate_immutability("PDO-TEST-001", "sha256:wrong")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOStoreV2 - Scaling
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOStoreV2Scaling:
    """Tests for scaling behavior."""

    def test_sharding_distribution(self, store):
        """Entries are distributed across shards."""
        for i in range(100):
            store.store(f"PDO-{i}", "PAC-001", ["GID-01"], "APPROVE", [])
        
        metrics = store.get_metrics()
        
        # Check entries are distributed (not all in one shard)
        non_empty_shards = sum(1 for c in metrics.shard_distribution.values() if c > 0)
        assert non_empty_shards > 1

    def test_high_write_throughput(self, store):
        """Can handle burst of writes."""
        start = time.time()
        
        for i in range(500):
            store.store(f"PDO-{i}", f"PAC-{i % 10}", [f"GID-{i % 5}"], "APPROVE", [])
        
        elapsed = time.time() - start
        throughput = 500 / elapsed
        
        # Should handle at least 100 writes/sec
        assert throughput > 100

    def test_concurrent_writes(self, store):
        """Can handle concurrent writes from multiple threads."""
        errors = []
        entries_written = []
        
        def write_entries(thread_id: int):
            try:
                for i in range(50):
                    pdo_id = f"PDO-T{thread_id}-{i}"
                    store.store(pdo_id, f"PAC-{thread_id}", [f"GID-{thread_id}"], "APPROVE", [])
                    entries_written.append(pdo_id)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=write_entries, args=(i,))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert store.total_entries == 500

    def test_index_integrity_after_load(self, store):
        """Index remains consistent after heavy load."""
        for i in range(200):
            store.store(f"PDO-{i}", f"PAC-{i % 10}", [f"GID-{i % 5}"], "APPROVE", [])
        
        valid, errors = store.validate_index_integrity()
        assert valid, f"Index errors: {errors}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDOStoreV2 - Metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOStoreV2Metrics:
    """Tests for metrics tracking."""

    def test_total_entries(self, store):
        """Tracks total entries."""
        assert store.total_entries == 0
        
        store.store("PDO-1", "PAC-1", ["GID-1"], "APPROVE", [])
        assert store.total_entries == 1
        
        store.store("PDO-2", "PAC-1", ["GID-1"], "APPROVE", [])
        assert store.total_entries == 2

    def test_aggregate_metrics(self, store):
        """Tracks aggregate metrics."""
        for i in range(10):
            store.store(f"PDO-{i}", "PAC-1", ["GID-1"], "APPROVE", [])
            store.get(f"PDO-{i}")
        
        metrics = store.get_metrics()
        
        assert metrics.total_entries == 10
        assert metrics.total_writes == 10
        assert metrics.total_reads == 10
        assert metrics.write_throughput > 0
        assert metrics.read_throughput > 0

    def test_shard_metrics(self, store):
        """Can get per-shard metrics."""
        for i in range(50):
            store.store(f"PDO-{i}", "PAC-1", ["GID-1"], "APPROVE", [])
        
        shard_metrics = store.get_shard_metrics()
        
        assert len(shard_metrics) == store.shard_count
        total_from_shards = sum(m.entry_count for m in shard_metrics)
        assert total_from_shards == 50


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton management."""

    def test_get_returns_same_instance(self):
        """get_pdo_store_v2 returns same instance."""
        reset_pdo_store_v2()
        store1 = get_pdo_store_v2()
        store2 = get_pdo_store_v2()
        assert store1 is store2
        reset_pdo_store_v2()

    def test_reset_clears_instance(self):
        """reset_pdo_store_v2 clears singleton."""
        reset_pdo_store_v2()
        store1 = get_pdo_store_v2()
        reset_pdo_store_v2()
        store2 = get_pdo_store_v2()
        assert store1 is not store2
        reset_pdo_store_v2()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_agent_list(self, store):
        """Can store PDO with no agents."""
        entry = store.store("PDO-1", "PAC-1", [], "APPROVE", [])
        assert entry.agent_gids == ()

    def test_empty_wrap_list(self, store):
        """Can store PDO with no wraps."""
        entry = store.store("PDO-1", "PAC-1", ["GID-1"], "APPROVE", [])
        assert entry.wrap_hashes == ()

    def test_get_nonexistent(self, store):
        """Getting nonexistent entry returns None."""
        assert store.get("PDO-NONEXISTENT") is None

    def test_find_by_pac_nonexistent(self, store):
        """Finding by nonexistent PAC returns empty list."""
        results = store.find_by_pac("PAC-NONEXISTENT")
        assert results == []

    def test_validate_nonexistent(self, store):
        """Validating nonexistent entry returns False."""
        assert store.validate_immutability("PDO-NONEXISTENT", "sha256:any") is False
