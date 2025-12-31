# ═══════════════════════════════════════════════════════════════════════════════
# Neural Memory Tests — Unit & Integration Tests
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Neural Memory Tests — Comprehensive Test Suite

COVERAGE:
    - core/ml/neural_memory.py (NeuralMemoryInterface, ShadowModeMemory, etc.)
    - core/ml/dualbrain_router.py (DualBrainRouter, RoutingPolicy, etc.)
    - Integration tests for memory subsystem
"""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from core.ml.neural_memory import (
    DualBrainRouterInterface,
    MemoryGateProtocol,
    MemoryMode,
    MemorySnapshot,
    MemoryStateHash,
    MemoryTier,
    MemoryUpdateRecord,
    NeuralMemoryInterface,
    ShadowModeMemory,
    SnapshotRegistry,
    SnapshotStatus,
    SurpriseLevel,
    SurpriseMetric,
)
from core.ml.dualbrain_router import (
    DualBrainRouter,
    QueryType,
    RoutingDecision,
    RoutingOutcome,
    RoutingPolicy,
    RoutingStatistics,
    RoutingStrategy,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STATE HASH TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryStateHash:
    """Tests for MemoryStateHash."""

    def test_compute_creates_valid_hash(self) -> None:
        """Test that compute creates a valid SHA-256 hash."""
        state_data = {"key": "value", "count": 42}
        hash_obj = MemoryStateHash.compute(state_data)

        assert hash_obj.hash_value is not None
        assert len(hash_obj.hash_value) == 64  # SHA-256 hex length
        assert hash_obj.algorithm == "sha256"
        assert hash_obj.entry_count == 2

    def test_compute_deterministic(self) -> None:
        """Test that same data produces same hash."""
        state_data = {"a": 1, "b": 2}
        hash1 = MemoryStateHash.compute(state_data)
        hash2 = MemoryStateHash.compute(state_data)

        assert hash1.hash_value == hash2.hash_value

    def test_compute_different_data_different_hash(self) -> None:
        """Test that different data produces different hash."""
        hash1 = MemoryStateHash.compute({"key": "value1"})
        hash2 = MemoryStateHash.compute({"key": "value2"})

        assert hash1.hash_value != hash2.hash_value

    def test_verify_correct_data(self) -> None:
        """Test verify returns True for correct data."""
        state_data = {"test": "data"}
        hash_obj = MemoryStateHash.compute(state_data)

        assert hash_obj.verify(state_data) is True

    def test_verify_incorrect_data(self) -> None:
        """Test verify returns False for incorrect data."""
        state_data = {"test": "data"}
        hash_obj = MemoryStateHash.compute(state_data)

        assert hash_obj.verify({"test": "wrong"}) is False

    def test_memory_tier_preserved(self) -> None:
        """Test that memory tier is preserved in hash."""
        state_data = {"key": "value"}
        hash_obj = MemoryStateHash.compute(state_data, MemoryTier.FAST)

        assert hash_obj.memory_tier == MemoryTier.FAST


# ═══════════════════════════════════════════════════════════════════════════════
# SURPRISE METRIC TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSurpriseMetric:
    """Tests for SurpriseMetric."""

    def test_from_value_negligible(self) -> None:
        """Test negligible surprise level."""
        metric = SurpriseMetric.from_value(0.05, "ctx-1")
        assert metric.level == SurpriseLevel.NEGLIGIBLE
        assert metric.should_update_memory() is False

    def test_from_value_low(self) -> None:
        """Test low surprise level."""
        metric = SurpriseMetric.from_value(0.2, "ctx-1")
        assert metric.level == SurpriseLevel.LOW
        assert metric.should_update_memory() is False

    def test_from_value_moderate(self) -> None:
        """Test moderate surprise level triggers update."""
        metric = SurpriseMetric.from_value(0.5, "ctx-1")
        assert metric.level == SurpriseLevel.MODERATE
        assert metric.should_update_memory() is True

    def test_from_value_high(self) -> None:
        """Test high surprise level triggers update."""
        metric = SurpriseMetric.from_value(0.8, "ctx-1")
        assert metric.level == SurpriseLevel.HIGH
        assert metric.should_update_memory() is True

    def test_from_value_critical(self) -> None:
        """Test critical surprise level."""
        metric = SurpriseMetric.from_value(0.95, "ctx-1")
        assert metric.level == SurpriseLevel.CRITICAL
        assert metric.should_update_memory() is True

    def test_value_bounds_validation(self) -> None:
        """Test that value must be in [0.0, 1.0]."""
        with pytest.raises(ValueError):
            SurpriseMetric(value=1.5, level=SurpriseLevel.HIGH, context_id="ctx")

        with pytest.raises(ValueError):
            SurpriseMetric(value=-0.1, level=SurpriseLevel.LOW, context_id="ctx")


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY SNAPSHOT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemorySnapshot:
    """Tests for MemorySnapshot."""

    def test_valid_snapshot_id_required(self) -> None:
        """Test that snapshot ID must start with MEM-SNAP-."""
        state_hash = MemoryStateHash.compute({"key": "value"})

        with pytest.raises(ValueError):
            MemorySnapshot(
                snapshot_id="INVALID-001",
                state_hash=state_hash,
                status=SnapshotStatus.COMPLETE,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

    def test_valid_snapshot_creation(self) -> None:
        """Test valid snapshot creation."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        assert snapshot.snapshot_id == "MEM-SNAP-000001"
        assert snapshot.status == SnapshotStatus.COMPLETE

    def test_is_anchored(self) -> None:
        """Test is_anchored returns correct status."""
        state_hash = MemoryStateHash.compute({"key": "value"})

        # Not anchored
        snapshot1 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert snapshot1.is_anchored() is False

        # Anchored
        snapshot2 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000002",
            state_hash=state_hash,
            status=SnapshotStatus.ANCHORED,
            created_at=datetime.now(timezone.utc).isoformat(),
            ledger_anchor="ANCHOR-001",
        )
        assert snapshot2.is_anchored() is True

    def test_compute_chain_hash(self) -> None:
        """Test chain hash computation."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at="2025-01-01T00:00:00Z",
        )

        chain_hash = snapshot.compute_chain_hash()
        assert chain_hash is not None
        assert len(chain_hash) == 64  # SHA-256


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW MODE MEMORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowModeMemory:
    """Tests for ShadowModeMemory implementation."""

    def test_initializes_in_shadow_mode(self) -> None:
        """Test that memory initializes in SHADOW mode."""
        memory = ShadowModeMemory()
        assert memory.mode == MemoryMode.SHADOW
        assert memory.tier == MemoryTier.SLOW

    def test_custom_tier(self) -> None:
        """Test memory with custom tier."""
        memory = ShadowModeMemory(tier=MemoryTier.FAST)
        assert memory.tier == MemoryTier.FAST

    def test_get_state_hash(self) -> None:
        """Test getting state hash."""
        memory = ShadowModeMemory()
        state_hash = memory.get_state_hash()

        assert state_hash is not None
        assert state_hash.memory_tier == MemoryTier.SLOW

    def test_create_snapshot(self) -> None:
        """Test creating snapshots."""
        memory = ShadowModeMemory()
        snapshot1 = memory.create_snapshot()
        snapshot2 = memory.create_snapshot()

        assert snapshot1.snapshot_id == "MEM-SNAP-000001"
        assert snapshot2.snapshot_id == "MEM-SNAP-000002"
        assert snapshot2.predecessor_id == snapshot1.snapshot_id

    def test_freeze(self) -> None:
        """Test freezing memory."""
        memory = ShadowModeMemory()
        assert memory.is_frozen() is False

        result = memory.freeze()
        assert result is True
        assert memory.is_frozen() is True
        assert memory.mode == MemoryMode.FROZEN

    def test_restore_blocked_when_frozen(self) -> None:
        """Test that restore fails when frozen."""
        memory = ShadowModeMemory()
        snapshot = memory.create_snapshot()

        memory.freeze()
        result = memory.restore_snapshot(snapshot)

        assert result is False

    def test_compute_surprise_returns_low(self) -> None:
        """Test that shadow mode returns low surprise."""
        memory = ShadowModeMemory()
        surprise = memory.compute_surprise({"query": "test"})

        assert surprise.value == 0.1
        assert surprise.context_id == "SHADOW-CTX"
        assert surprise.should_update_memory() is False


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSnapshotRegistry:
    """Tests for SnapshotRegistry."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton between tests."""
        SnapshotRegistry._instance = None
        SnapshotRegistry._initialized = False

    def test_singleton_pattern(self) -> None:
        """Test that registry is singleton."""
        registry1 = SnapshotRegistry()
        registry2 = SnapshotRegistry()
        assert registry1 is registry2

    def test_register_snapshot(self) -> None:
        """Test registering snapshots."""
        registry = SnapshotRegistry()
        state_hash = MemoryStateHash.compute({"key": "value"})

        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        result = registry.register(snapshot)
        assert result is True
        assert registry.count() == 1

    def test_duplicate_registration_fails(self) -> None:
        """Test that duplicate registration fails."""
        registry = SnapshotRegistry()
        state_hash = MemoryStateHash.compute({"key": "value"})

        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        registry.register(snapshot)
        result = registry.register(snapshot)
        assert result is False

    def test_chain_linkage_validation(self) -> None:
        """Test that chain linkage is validated."""
        registry = SnapshotRegistry()
        state_hash = MemoryStateHash.compute({"key": "value"})

        # First snapshot (genesis)
        snapshot1 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
            predecessor_id=None,
        )
        registry.register(snapshot1)

        # Second snapshot with correct predecessor
        snapshot2 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000002",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
            predecessor_id="MEM-SNAP-000001",
        )
        result = registry.register(snapshot2)
        assert result is True

    def test_verify_chain(self) -> None:
        """Test chain verification."""
        registry = SnapshotRegistry()
        state_hash = MemoryStateHash.compute({"key": "value"})

        # Register chain
        snapshot1 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        registry.register(snapshot1)

        snapshot2 = MemorySnapshot(
            snapshot_id="MEM-SNAP-000002",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
            predecessor_id="MEM-SNAP-000001",
        )
        registry.register(snapshot2)

        valid, error = registry.verify_chain()
        assert valid is True
        assert error is None

    def test_get_latest(self) -> None:
        """Test getting latest snapshot."""
        registry = SnapshotRegistry()
        state_hash = MemoryStateHash.compute({"key": "value"})

        # Empty registry
        assert registry.get_latest() is None

        # After registration
        snapshot = MemorySnapshot(
            snapshot_id="MEM-SNAP-000001",
            state_hash=state_hash,
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        registry.register(snapshot)

        latest = registry.get_latest()
        assert latest is not None
        assert latest.snapshot_id == "MEM-SNAP-000001"


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL-BRAIN ROUTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDualBrainRouter:
    """Tests for DualBrainRouter."""

    def test_default_policy(self) -> None:
        """Test router with default policy."""
        router = DualBrainRouter()
        assert router.policy.default_strategy == RoutingStrategy.SURPRISE_BASED

    def test_custom_policy(self) -> None:
        """Test router with custom policy."""
        policy = RoutingPolicy(
            default_strategy=RoutingStrategy.TYPE_BASED,
            fallback_tier=MemoryTier.SLOW,
        )
        router = DualBrainRouter(policy=policy)

        assert router.policy.default_strategy == RoutingStrategy.TYPE_BASED
        assert router.policy.fallback_tier == MemoryTier.SLOW

    def test_invalid_policy_raises(self) -> None:
        """Test that invalid policy raises error."""
        policy = RoutingPolicy(
            surprise_threshold_fast=0.8,
            surprise_threshold_slow=0.3,  # Invalid: fast > slow
        )
        with pytest.raises(ValueError):
            DualBrainRouter(policy=policy)

    def test_route_query_surprise_based_low(self) -> None:
        """Test routing with low surprise goes to FAST."""
        router = DualBrainRouter()
        fast_memory = ShadowModeMemory(tier=MemoryTier.FAST)
        slow_memory = ShadowModeMemory(tier=MemoryTier.SLOW)

        # Shadow mode returns 0.1 surprise (below fast threshold of 0.3)
        tier, metadata = router.route_query({"query": "test"}, fast_memory, slow_memory)

        assert tier == MemoryTier.FAST
        assert metadata["outcome"] == RoutingOutcome.FAST_ONLY.value

    def test_route_query_type_based(self) -> None:
        """Test type-based routing."""
        policy = RoutingPolicy(default_strategy=RoutingStrategy.TYPE_BASED)
        router = DualBrainRouter(policy=policy)
        fast_memory = ShadowModeMemory(tier=MemoryTier.FAST)
        slow_memory = ShadowModeMemory(tier=MemoryTier.SLOW)

        # Historical query should go to SLOW
        tier, metadata = router.route_query(
            {"query": "test", "is_historical": True},
            fast_memory,
            slow_memory,
        )
        assert tier == MemoryTier.SLOW

        # Recent context should go to FAST
        tier, metadata = router.route_query(
            {"query": "test", "is_recent": True},
            fast_memory,
            slow_memory,
        )
        assert tier == MemoryTier.FAST

    def test_routing_stats_tracking(self) -> None:
        """Test that routing stats are tracked."""
        router = DualBrainRouter()
        fast_memory = ShadowModeMemory(tier=MemoryTier.FAST)
        slow_memory = ShadowModeMemory(tier=MemoryTier.SLOW)

        # Make some routing decisions
        router.route_query({"query": "test1"}, fast_memory, slow_memory)
        router.route_query({"query": "test2"}, fast_memory, slow_memory)

        stats = router.get_routing_stats()
        assert stats["total"] == 2

    def test_decision_log(self) -> None:
        """Test that decision log is maintained."""
        router = DualBrainRouter()
        fast_memory = ShadowModeMemory(tier=MemoryTier.FAST)
        slow_memory = ShadowModeMemory(tier=MemoryTier.SLOW)

        router.route_query({"query": "test"}, fast_memory, slow_memory)

        log = router.get_decision_log()
        assert len(log) == 1
        assert log[0].decision_id.startswith("ROUTE-")


class TestRoutingPolicy:
    """Tests for RoutingPolicy."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        policy = RoutingPolicy()
        assert policy.surprise_threshold_fast == 0.3
        assert policy.surprise_threshold_slow == 0.6

    def test_validate_valid_policy(self) -> None:
        """Test validation of valid policy."""
        policy = RoutingPolicy(
            surprise_threshold_fast=0.2,
            surprise_threshold_slow=0.7,
        )
        valid, error = policy.validate()
        assert valid is True
        assert error is None

    def test_validate_invalid_thresholds(self) -> None:
        """Test validation catches invalid thresholds."""
        policy = RoutingPolicy(
            surprise_threshold_fast=0.8,
            surprise_threshold_slow=0.3,
        )
        valid, error = policy.validate()
        assert valid is False
        assert "fast threshold must be < slow threshold" in error


class TestRoutingStatistics:
    """Tests for RoutingStatistics."""

    def test_initial_values(self) -> None:
        """Test initial statistics values."""
        stats = RoutingStatistics()
        assert stats.total_decisions == 0
        assert stats.avg_confidence == 0.0

    def test_record_fast_decision(self) -> None:
        """Test recording FAST decision."""
        stats = RoutingStatistics()
        decision = RoutingDecision(
            decision_id="ROUTE-00000001",
            selected_tier=MemoryTier.FAST,
            outcome=RoutingOutcome.FAST_ONLY,
            strategy_used=RoutingStrategy.SURPRISE_BASED,
            query_type=QueryType.RECENT_CONTEXT,
            confidence=0.9,
        )
        stats.record(decision)

        assert stats.fast_count == 1
        assert stats.total_decisions == 1
        assert stats.avg_confidence == 0.9

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        stats = RoutingStatistics(
            fast_count=10,
            slow_count=5,
            hybrid_count=3,
            total_decisions=18,
        )
        result = stats.to_dict()

        assert result["fast_count"] == 10
        assert result["slow_count"] == 5
        assert result["total_decisions"] == 18


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemorySubsystemIntegration:
    """Integration tests for memory subsystem."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self) -> None:
        """Reset singletons between tests."""
        SnapshotRegistry._instance = None
        SnapshotRegistry._initialized = False

    def test_full_memory_lifecycle(self) -> None:
        """Test complete memory lifecycle: create, snapshot, freeze."""
        # Create memory
        memory = ShadowModeMemory()
        assert memory.mode == MemoryMode.SHADOW

        # Get initial state
        initial_hash = memory.get_state_hash()
        assert initial_hash is not None

        # Create snapshot
        snapshot = memory.create_snapshot()
        assert snapshot.status == SnapshotStatus.COMPLETE

        # Freeze memory
        memory.freeze()
        assert memory.is_frozen() is True
        assert memory.mode == MemoryMode.FROZEN

        # Verify restore fails when frozen
        result = memory.restore_snapshot(snapshot)
        assert result is False

    def test_routing_with_memory(self) -> None:
        """Test routing queries through dual-brain router."""
        # Setup
        router = DualBrainRouter()
        fast_memory = ShadowModeMemory(tier=MemoryTier.FAST)
        slow_memory = ShadowModeMemory(tier=MemoryTier.SLOW)

        # Route multiple queries
        queries = [
            {"query": "recent", "is_recent": True},
            {"query": "historical", "is_historical": True},
            {"query": "unknown"},
        ]

        for query in queries:
            tier, metadata = router.route_query(query, fast_memory, slow_memory)
            assert tier is not None
            assert "decision_id" in metadata

        # Check stats
        stats = router.get_routing_stats()
        assert stats["total"] == 3

    def test_snapshot_chain_integrity(self) -> None:
        """Test snapshot chain maintains integrity."""
        memory = ShadowModeMemory()
        registry = SnapshotRegistry()

        # Create multiple snapshots
        snapshots = []
        for _ in range(5):
            snapshot = memory.create_snapshot()
            registry.register(snapshot)
            snapshots.append(snapshot)

        # Verify chain
        valid, error = registry.verify_chain()
        assert valid is True

        # Verify linkage
        for i in range(1, len(snapshots)):
            assert snapshots[i].predecessor_id == snapshots[i - 1].snapshot_id


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryInvariants:
    """Tests for memory invariants (INV-MEM-*)."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self) -> None:
        """Reset singletons between tests."""
        SnapshotRegistry._instance = None
        SnapshotRegistry._initialized = False

    def test_inv_mem_001_snapshot_immutability(self) -> None:
        """INV-MEM-001: Memory state is immutable once snapshotted."""
        memory = ShadowModeMemory()
        snapshot = memory.create_snapshot()

        # Snapshot object is frozen (immutable)
        with pytest.raises(AttributeError):
            snapshot.status = SnapshotStatus.VERIFIED  # type: ignore

    def test_inv_mem_003_snapshot_hash_integrity(self) -> None:
        """INV-MEM-003: Memory snapshots include integrity hash."""
        memory = ShadowModeMemory()
        snapshot = memory.create_snapshot()

        assert snapshot.state_hash is not None
        assert snapshot.state_hash.hash_value is not None
        assert len(snapshot.state_hash.hash_value) == 64

    def test_inv_mem_004_frozen_protection(self) -> None:
        """INV-MEM-004: Frozen memory cannot be modified."""
        memory = ShadowModeMemory()
        snapshot = memory.create_snapshot()

        memory.freeze()
        result = memory.restore_snapshot(snapshot)

        assert result is False  # Cannot modify frozen memory

    def test_inv_mem_006_no_production_learning(self) -> None:
        """INV-MEM-006: No runtime learning in production mode."""
        memory = ShadowModeMemory()

        # Shadow mode always returns low surprise (no learning trigger)
        surprise = memory.compute_surprise({"data": "test"})

        assert surprise.value == 0.1
        assert surprise.should_update_memory() is False
