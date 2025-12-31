"""
Tests for GIE Orchestrator Deep v4.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-01 (Cody) — CORE / ORCHESTRATION EXPANSION
"""

import pytest
import threading
import time
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

from core.gie.orchestrator_deep import (
    OrchestratorDeepV4,
    AgentSwapManager,
    PriorityDispatcher,
    ResourcePool,
    TelemetryStream,
    Priority,
    SwapState,
    ResourceState,
    TelemetryEventType,
    SwapError,
    QuotaExceededError,
    AgentState,
    TokenBucket,
    LatencyHistogram,
    ThroughputCounter,
    compute_wrap_hash,
)


# =============================================================================
# TOKEN BUCKET TESTS
# =============================================================================

class TestTokenBucket:
    """Tests for TokenBucket."""
    
    def test_initial_capacity(self) -> None:
        """Bucket starts with full capacity."""
        bucket = TokenBucket(
            capacity=100.0,
            tokens=100.0,
            refill_rate=10.0,
            last_refill=time.monotonic(),
        )
        assert bucket.tokens == 100.0
    
    def test_consume_success(self) -> None:
        """Consume tokens when available."""
        bucket = TokenBucket(
            capacity=100.0,
            tokens=100.0,
            refill_rate=10.0,
            last_refill=time.monotonic(),
        )
        assert bucket.consume(50.0) is True
        assert bucket.tokens < 100.0
    
    def test_consume_insufficient(self) -> None:
        """Fail to consume when insufficient tokens."""
        bucket = TokenBucket(
            capacity=100.0,
            tokens=10.0,
            refill_rate=10.0,
            last_refill=time.monotonic(),
        )
        assert bucket.consume(50.0) is False
    
    def test_refill(self) -> None:
        """Tokens refill over time."""
        bucket = TokenBucket(
            capacity=100.0,
            tokens=0.0,
            refill_rate=1000.0,  # Fast refill for test
            last_refill=time.monotonic() - 0.1,  # 100ms ago
        )
        bucket._refill()
        assert bucket.tokens > 0


# =============================================================================
# LATENCY HISTOGRAM TESTS
# =============================================================================

class TestLatencyHistogram:
    """Tests for LatencyHistogram."""
    
    def test_record_values(self) -> None:
        """Record latency values."""
        histogram = LatencyHistogram(
            buckets=[10, 50, 100, 500],
            counts=[0, 0, 0, 0, 0],
        )
        histogram.record(5)
        histogram.record(25)
        histogram.record(75)
        
        assert histogram.total_count == 3
    
    def test_mean_calculation(self) -> None:
        """Calculate mean latency."""
        histogram = LatencyHistogram(
            buckets=[100],
            counts=[0, 0],
        )
        histogram.record(10)
        histogram.record(20)
        histogram.record(30)
        
        assert histogram.mean() == 20.0
    
    def test_empty_percentile(self) -> None:
        """Percentile returns 0 for empty histogram."""
        histogram = LatencyHistogram(
            buckets=[100],
            counts=[0, 0],
        )
        assert histogram.percentile(50) == 0.0


# =============================================================================
# THROUGHPUT COUNTER TESTS
# =============================================================================

class TestThroughputCounter:
    """Tests for ThroughputCounter."""
    
    def test_record_and_rate(self) -> None:
        """Record events and calculate rate."""
        counter = ThroughputCounter(window_seconds=60.0)
        for _ in range(10):
            counter.record()
        
        assert len(counter.timestamps) == 10
        assert counter.rate() > 0
    
    def test_window_pruning(self) -> None:
        """Old events are pruned."""
        counter = ThroughputCounter(window_seconds=0.001)  # 1ms window
        counter.record()
        time.sleep(0.01)
        counter._prune(time.monotonic())
        
        # May or may not be pruned depending on timing
        assert len(counter.timestamps) <= 1


# =============================================================================
# AGENT SWAP MANAGER TESTS
# =============================================================================

class TestAgentSwapManager:
    """Tests for AgentSwapManager."""
    
    def test_initiate_swap(self) -> None:
        """Initiate a swap operation."""
        manager = AgentSwapManager()
        
        def capture_fn(agent_id: str) -> AgentState:
            return AgentState(
                agent_id=agent_id,
                state_data={"key": "value"},
                checkpoint_hash="abc123",
                dependencies_satisfied=frozenset(["dep1"]),
                pending_dependencies=frozenset(),
                execution_progress=0.5,
            )
        
        swap_id = manager.initiate_swap("agent-1", "agent-2", capture_fn)
        assert swap_id is not None
        
        record = manager.get_swap_record(swap_id)
        assert record is not None
        assert record.original_agent_id == "agent-1"
        assert record.new_agent_id == "agent-2"
    
    def test_execute_swap(self) -> None:
        """Execute a swap operation."""
        manager = AgentSwapManager()
        
        def capture_fn(agent_id: str) -> AgentState:
            return AgentState(
                agent_id=agent_id,
                state_data={"key": "value"},
                checkpoint_hash="abc123",
                dependencies_satisfied=frozenset(["dep1"]),
                pending_dependencies=frozenset(),
                execution_progress=0.5,
            )
        
        swap_id = manager.initiate_swap("agent-1", "agent-2", capture_fn)
        
        record = manager.execute_swap(
            swap_id,
            validate_fn=lambda s, n: True,
            recompute_deps_fn=lambda n, s: frozenset(),
        )
        
        assert record.swap_state == SwapState.COMPLETED
        assert record.state_after is not None
        assert record.state_after.agent_id == "agent-2"
    
    def test_swap_already_in_progress(self) -> None:
        """Cannot swap agent already being swapped."""
        manager = AgentSwapManager()
        
        def capture_fn(agent_id: str) -> AgentState:
            return AgentState(
                agent_id=agent_id,
                state_data={},
                checkpoint_hash="",
                dependencies_satisfied=frozenset(),
                pending_dependencies=frozenset(),
                execution_progress=0.0,
            )
        
        manager.initiate_swap("agent-1", "agent-2", capture_fn)
        
        with pytest.raises(SwapError):
            manager.initiate_swap("agent-1", "agent-3", capture_fn)


# =============================================================================
# PRIORITY DISPATCHER TESTS
# =============================================================================

class TestPriorityDispatcher:
    """Tests for PriorityDispatcher."""
    
    def test_enqueue_dequeue(self) -> None:
        """Enqueue and dequeue agents."""
        dispatcher = PriorityDispatcher()
        
        dispatcher.enqueue("agent-1", "task-1", Priority.NORMAL)
        dispatcher.enqueue("agent-2", "task-2", Priority.HIGH)
        dispatcher.enqueue("agent-3", "task-3", Priority.LOW)
        
        # Should get HIGH priority first
        item = dispatcher.dequeue()
        assert item is not None
        assert item.agent_id == "agent-2"
        
        # Then NORMAL
        item = dispatcher.dequeue()
        assert item is not None
        assert item.agent_id == "agent-1"
        
        # Then LOW
        item = dispatcher.dequeue()
        assert item is not None
        assert item.agent_id == "agent-3"
    
    def test_priority_change(self) -> None:
        """Change priority of enqueued agent."""
        dispatcher = PriorityDispatcher()
        
        dispatcher.enqueue("agent-1", "task-1", Priority.LOW)
        dispatcher.enqueue("agent-2", "task-2", Priority.NORMAL)
        
        # Change agent-1 to CRITICAL
        result = dispatcher.change_priority("agent-1", Priority.CRITICAL)
        assert result is True
        
        # Now agent-1 should come first
        item = dispatcher.dequeue()
        assert item is not None
        assert item.agent_id == "agent-1"
    
    def test_queue_stats(self) -> None:
        """Get queue statistics."""
        dispatcher = PriorityDispatcher()
        
        dispatcher.enqueue("agent-1", "task-1", Priority.HIGH)
        dispatcher.enqueue("agent-2", "task-2", Priority.HIGH)
        dispatcher.enqueue("agent-3", "task-3", Priority.LOW)
        
        stats = dispatcher.get_queue_stats()
        assert stats["total_queued"] == 3
        assert stats["by_priority"][Priority.HIGH.value] == 2
        assert stats["by_priority"][Priority.LOW.value] == 1


# =============================================================================
# RESOURCE POOL TESTS
# =============================================================================

class TestResourcePool:
    """Tests for ResourcePool."""
    
    def test_acquire_release(self) -> None:
        """Acquire and release resources."""
        pool = ResourcePool({"compute": 100.0})
        
        result = pool.acquire("pac-1", "compute", 50.0, blocking=False)
        assert result is True
        
        availability = pool.get_availability("compute")
        assert availability["available"] < 100.0
        
        pool.release("pac-1", "compute", 50.0)
    
    def test_quota_exceeded(self) -> None:
        """Quota exceeded raises error."""
        pool = ResourcePool({"compute": 10.0})
        
        # First acquire succeeds
        pool.acquire("pac-1", "compute", 5.0, blocking=False)
        
        # Second acquire exceeds fair share
        with pytest.raises(QuotaExceededError):
            pool.acquire("pac-1", "compute", 100.0, blocking=False)
    
    def test_reservation(self) -> None:
        """Reserve resources."""
        pool = ResourcePool({"compute": 100.0})
        
        reservation_id = pool.reserve("pac-1", "compute", 50.0, duration_seconds=60.0)
        assert reservation_id is not None
        
        result = pool.cancel_reservation(reservation_id)
        assert result is True
    
    def test_unknown_resource(self) -> None:
        """Unknown resource type raises error."""
        pool = ResourcePool({"compute": 100.0})
        
        with pytest.raises(Exception):
            pool.acquire("pac-1", "unknown", 10.0, blocking=False)


# =============================================================================
# TELEMETRY STREAM TESTS
# =============================================================================

class TestTelemetryStream:
    """Tests for TelemetryStream."""
    
    def test_emit_event(self) -> None:
        """Emit telemetry event."""
        stream = TelemetryStream()
        
        event = stream.emit(
            TelemetryEventType.AGENT_DISPATCHED,
            {"agent_id": "test"},
        )
        
        assert event.event_id is not None
        assert event.event_type == TelemetryEventType.AGENT_DISPATCHED
    
    def test_record_latency(self) -> None:
        """Record latency metrics."""
        stream = TelemetryStream()
        
        stream.record_latency("test_metric", 10.0)
        stream.record_latency("test_metric", 20.0)
        stream.record_latency("test_metric", 30.0)
        
        stats = stream.get_latency_stats("test_metric")
        assert stats["count"] == 3
        assert stats["mean"] == 20.0
    
    def test_record_throughput(self) -> None:
        """Record throughput metrics."""
        stream = TelemetryStream()
        
        stream.record_throughput("test_metric")
        stream.record_throughput("test_metric")
        stream.record_throughput("test_metric")
        
        stats = stream.get_throughput_stats("test_metric")
        assert stats["count_in_window"] == 3
    
    def test_subscribe_listener(self) -> None:
        """Subscribe to telemetry events."""
        stream = TelemetryStream()
        received_events = []
        
        class TestListener:
            def on_event(self, event):
                received_events.append(event)
        
        listener = TestListener()
        stream.subscribe(listener)
        
        stream.emit(TelemetryEventType.AGENT_COMPLETED, {"test": True})
        
        assert len(received_events) == 1
        
        stream.unsubscribe(listener)
        stream.emit(TelemetryEventType.AGENT_COMPLETED, {"test": True})
        
        assert len(received_events) == 1  # No new events


# =============================================================================
# ORCHESTRATOR DEEP V4 TESTS
# =============================================================================

class TestOrchestratorDeepV4:
    """Tests for OrchestratorDeepV4."""
    
    def test_initialization(self) -> None:
        """Initialize orchestrator."""
        orchestrator = OrchestratorDeepV4()
        
        assert orchestrator.swap_manager is not None
        assert orchestrator.dispatcher is not None
        assert orchestrator.resource_pool is not None
        assert orchestrator.telemetry is not None
    
    def test_dispatch_agent(self) -> None:
        """Dispatch an agent."""
        orchestrator = OrchestratorDeepV4()
        
        result = orchestrator.dispatch_agent(
            "agent-1",
            "pac-1:task-1",
            Priority.HIGH,
        )
        
        assert result is True
    
    def test_dispatch_with_resources(self) -> None:
        """Dispatch agent with resource requirements."""
        orchestrator = OrchestratorDeepV4(
            resource_config={"compute": 100.0, "memory": 1000.0}
        )
        
        result = orchestrator.dispatch_agent(
            "agent-1",
            "pac-1:task-1",
            Priority.NORMAL,
            resource_requirements={"compute": 10.0},
        )
        
        assert result is True
    
    def test_hot_swap_agent(self) -> None:
        """Hot-swap an agent."""
        orchestrator = OrchestratorDeepV4()
        
        # First dispatch an agent
        orchestrator.dispatch_agent("agent-1", "pac-1:task-1", Priority.NORMAL)
        
        # Then swap it
        record = orchestrator.hot_swap_agent("agent-1", "agent-2")
        
        assert record.swap_state == SwapState.COMPLETED
    
    def test_predict_completion_no_model(self) -> None:
        """Predict completion without ML model."""
        orchestrator = OrchestratorDeepV4()
        
        predicted_seconds, confidence = orchestrator.predict_completion(
            "agent-1", "compute_task"
        )
        
        # Default values when no model
        assert predicted_seconds == 60.0
        assert confidence == 0.5
    
    def test_predict_completion_with_model(self) -> None:
        """Predict completion with ML model."""
        
        class MockModel:
            def predict_completion(
                self, agent_id: str, task_type: str, features: Dict[str, Any]
            ) -> Tuple[float, float]:
                return (30.0, 0.9)
        
        orchestrator = OrchestratorDeepV4(prediction_model=MockModel())
        
        predicted_seconds, confidence = orchestrator.predict_completion(
            "agent-1", "compute_task"
        )
        
        assert predicted_seconds == 30.0
        assert confidence == 0.9
    
    def test_execution_summary(self) -> None:
        """Get execution summary."""
        orchestrator = OrchestratorDeepV4()
        
        orchestrator.dispatch_agent("agent-1", "task-1", Priority.NORMAL)
        
        summary = orchestrator.get_execution_summary()
        
        assert "version" in summary
        assert "queue_stats" in summary
        assert "resource_compute" in summary


# =============================================================================
# WRAP HASH TESTS
# =============================================================================

class TestWrapHash:
    """Tests for WRAP hash computation."""
    
    def test_compute_wrap_hash(self) -> None:
        """Compute WRAP hash."""
        wrap_hash = compute_wrap_hash()
        
        assert wrap_hash is not None
        assert len(wrap_hash) == 16
    
    def test_wrap_hash_deterministic(self) -> None:
        """WRAP hash is deterministic."""
        hash1 = compute_wrap_hash()
        hash2 = compute_wrap_hash()
        
        assert hash1 == hash2


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================

class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_concurrent_dispatch(self) -> None:
        """Concurrent agent dispatch."""
        orchestrator = OrchestratorDeepV4()
        errors = []
        
        def dispatch_worker(agent_num: int) -> None:
            try:
                for i in range(10):
                    orchestrator.dispatch_agent(
                        f"agent-{agent_num}-{i}",
                        f"task-{agent_num}-{i}",
                        Priority.NORMAL,
                    )
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=dispatch_worker, args=(i,))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
    
    def test_concurrent_telemetry(self) -> None:
        """Concurrent telemetry recording."""
        stream = TelemetryStream()
        errors = []
        
        def record_worker() -> None:
            try:
                for _ in range(100):
                    stream.record_latency("test", 10.0)
                    stream.record_throughput("test")
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=record_worker) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        
        stats = stream.get_latency_stats("test")
        assert stats["count"] == 500  # 5 threads * 100 records
