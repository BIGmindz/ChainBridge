# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite — Instrumentation Module Tests
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for core/benchmark/instrumentation.py

Coverage:
- InstrumentationScope, MetricType, OperationPhase enums
- MetricRecord, TimingSpan, CostRecord, DeterminismRecord dataclasses
- InstrumentationContext
- LatencyProfiler
- CostAttributor
- DeterminismTracker
- InstrumentationRegistry
- @instrumented decorator
- Global registry functions
"""

import time

import pytest

from core.benchmark.instrumentation import (
    CostAttributor,
    CostRecord,
    DeterminismRecord,
    DeterminismTracker,
    InstrumentationContext,
    InstrumentationRegistry,
    InstrumentationScope,
    LatencyProfiler,
    MetricRecord,
    MetricType,
    OperationPhase,
    TimingSpan,
    get_global_registry,
    instrumented,
    reset_global_registry,
)


class TestInstrumentationEnums:
    """Tests for instrumentation enums."""

    def test_instrumentation_scope_values(self) -> None:
        """Test InstrumentationScope values."""
        assert InstrumentationScope.GLOBAL.value == "GLOBAL"
        assert InstrumentationScope.SERVICE.value == "SERVICE"
        assert InstrumentationScope.OPERATION.value == "OPERATION"
        assert InstrumentationScope.COMPONENT.value == "COMPONENT"

    def test_metric_type_values(self) -> None:
        """Test MetricType values."""
        assert MetricType.COUNTER.value == "COUNTER"
        assert MetricType.GAUGE.value == "GAUGE"
        assert MetricType.HISTOGRAM.value == "HISTOGRAM"
        assert MetricType.TIMER.value == "TIMER"
        assert MetricType.HASH.value == "HASH"

    def test_operation_phase_values(self) -> None:
        """Test OperationPhase values."""
        assert OperationPhase.INIT.value == "INIT"
        assert OperationPhase.ROUTING.value == "ROUTING"
        assert OperationPhase.MEMORY_ACCESS.value == "MEMORY_ACCESS"
        assert OperationPhase.COMPUTE.value == "COMPUTE"
        assert OperationPhase.SNAPSHOT.value == "SNAPSHOT"
        assert OperationPhase.FINALIZE.value == "FINALIZE"


class TestMetricRecord:
    """Tests for MetricRecord dataclass."""

    def test_metric_record_creation(self) -> None:
        """Test metric record creation."""
        record = MetricRecord(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            value=42.5,
            timestamp="2025-01-01T00:00:00Z",
        )

        assert record.name == "test_metric"
        assert record.value == 42.5

    def test_metric_record_to_dict(self) -> None:
        """Test metric record serialization."""
        record = MetricRecord(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            value=100,
            timestamp="2025-01-01T00:00:00Z",
            labels={"service": "test"},
        )

        data = record.to_dict()
        assert data["name"] == "test_metric"
        assert data["type"] == "COUNTER"
        assert data["labels"]["service"] == "test"


class TestTimingSpan:
    """Tests for TimingSpan dataclass."""

    def test_timing_span_creation(self) -> None:
        """Test timing span creation."""
        span = TimingSpan(
            span_id="SPAN-000001",
            name="test_span",
            parent_id=None,
            start_time=time.perf_counter(),
        )

        assert span.span_id == "SPAN-000001"
        assert span.parent_id is None
        assert not span.is_complete

    def test_timing_span_duration(self) -> None:
        """Test timing span duration calculation."""
        start = time.perf_counter()
        span = TimingSpan(
            span_id="SPAN-000001",
            name="test_span",
            parent_id=None,
            start_time=start,
        )

        time.sleep(0.01)
        span.end_time = time.perf_counter()

        assert span.is_complete
        assert span.duration_ms > 0

    def test_timing_span_to_dict(self) -> None:
        """Test timing span serialization."""
        span = TimingSpan(
            span_id="SPAN-000001",
            name="test_span",
            parent_id=None,
            start_time=time.perf_counter(),
            phase=OperationPhase.COMPUTE,
        )

        data = span.to_dict()
        assert data["span_id"] == "SPAN-000001"
        assert data["phase"] == "COMPUTE"


class TestCostRecord:
    """Tests for CostRecord dataclass."""

    def test_cost_record_creation(self) -> None:
        """Test cost record creation."""
        record = CostRecord(operation="test_op")
        assert record.operation == "test_op"
        assert record.tokens == 0

    def test_cost_record_calculation(self) -> None:
        """Test cost calculation."""
        record = CostRecord(
            operation="test_op",
            tokens=10000,
            memory_operations=100,
            routing_decisions=50,
            snapshots=10,
        )

        cost = record.calculate()
        assert cost > 0

    def test_cost_record_to_dict(self) -> None:
        """Test cost record serialization."""
        record = CostRecord(operation="test_op", tokens=5000)
        data = record.to_dict()

        assert data["operation"] == "test_op"
        assert "computed_cost_usd" in data


class TestDeterminismRecord:
    """Tests for DeterminismRecord dataclass."""

    def test_determinism_record_creation(self) -> None:
        """Test determinism record creation."""
        record = DeterminismRecord(
            operation="test_op",
            input_hash="abc123",
            output_hash="xyz789",
            replay_sequence=1,
            is_match=True,
            timestamp="2025-01-01T00:00:00Z",
        )

        assert record.operation == "test_op"
        assert record.is_match

    def test_determinism_record_to_dict(self) -> None:
        """Test determinism record serialization."""
        record = DeterminismRecord(
            operation="test_op",
            input_hash="abc",
            output_hash="xyz",
            replay_sequence=0,
            is_match=False,
            timestamp="2025-01-01T00:00:00Z",
        )

        data = record.to_dict()
        assert data["is_match"] is False


class TestInstrumentationContext:
    """Tests for InstrumentationContext dataclass."""

    def test_context_creation(self) -> None:
        """Test context creation."""
        context = InstrumentationContext(
            context_id="CTX-000001",
            operation_name="test_op",
            started_at="2025-01-01T00:00:00Z",
        )

        assert context.context_id == "CTX-000001"
        assert context.cost is not None

    def test_invalid_context_id(self) -> None:
        """Test invalid context ID."""
        with pytest.raises(ValueError, match="must start with 'CTX-'"):
            InstrumentationContext(
                context_id="INVALID",
                operation_name="test",
                started_at="2025-01-01T00:00:00Z",
            )

    def test_context_hash(self) -> None:
        """Test context hash computation."""
        context = InstrumentationContext(
            context_id="CTX-000001",
            operation_name="test_op",
            started_at="2025-01-01T00:00:00Z",
        )

        hash1 = context.compute_hash()
        hash2 = context.compute_hash()
        assert hash1 == hash2


class TestLatencyProfiler:
    """Tests for LatencyProfiler class."""

    def test_profiler_creation(self) -> None:
        """Test profiler creation."""
        profiler = LatencyProfiler()
        assert len(profiler.get_all_spans()) == 0

    def test_start_end_span(self) -> None:
        """Test starting and ending spans."""
        profiler = LatencyProfiler()

        span_id = profiler.start_span("test_span")
        assert span_id.startswith("SPAN-")

        span = profiler.end_span(span_id)
        assert span is not None
        assert span.is_complete

    def test_nested_spans(self) -> None:
        """Test nested spans."""
        profiler = LatencyProfiler()

        parent_id = profiler.start_span("parent")
        child_id = profiler.start_span("child")

        child = profiler.get_span(child_id)
        assert child.parent_id == parent_id

        profiler.end_span(child_id)
        profiler.end_span(parent_id)

    def test_span_context_manager(self) -> None:
        """Test span context manager."""
        profiler = LatencyProfiler()

        with profiler.span("test_span") as span_id:
            time.sleep(0.01)

        span = profiler.get_span(span_id)
        assert span.is_complete
        assert span.duration_ms > 0

    def test_total_duration(self) -> None:
        """Test total duration calculation."""
        profiler = LatencyProfiler()

        with profiler.span("span1"):
            time.sleep(0.01)

        with profiler.span("span2"):
            time.sleep(0.01)

        assert profiler.total_duration_ms() > 0

    def test_profiler_reset(self) -> None:
        """Test profiler reset."""
        profiler = LatencyProfiler()

        profiler.start_span("test")
        profiler.reset()

        assert len(profiler.get_all_spans()) == 0


class TestCostAttributor:
    """Tests for CostAttributor class."""

    def test_attributor_creation(self) -> None:
        """Test attributor creation."""
        attributor = CostAttributor()
        assert attributor.total_cost_usd() == 0

    def test_create_record(self) -> None:
        """Test creating cost record."""
        attributor = CostAttributor()
        record = attributor.create_record("test_op")

        assert record.operation == "test_op"

    def test_record_tokens(self) -> None:
        """Test recording tokens."""
        attributor = CostAttributor()
        attributor.create_record("test_op")
        attributor.record_tokens("test_op", 1000)

        record = attributor.get_cost("test_op")
        assert record.tokens == 1000

    def test_record_memory_op(self) -> None:
        """Test recording memory operations."""
        attributor = CostAttributor()
        attributor.create_record("test_op")
        attributor.record_memory_op("test_op", 5)

        record = attributor.get_cost("test_op")
        assert record.memory_operations == 5

    def test_total_cost(self) -> None:
        """Test total cost calculation."""
        attributor = CostAttributor()
        attributor.create_record("op1")
        attributor.create_record("op2")
        attributor.record_tokens("op1", 10000)
        attributor.record_tokens("op2", 5000)

        assert attributor.total_cost_usd() > 0

    def test_cost_breakdown(self) -> None:
        """Test cost breakdown."""
        attributor = CostAttributor()
        attributor.create_record("op1")
        attributor.create_record("op2")
        attributor.record_tokens("op1", 1000)

        breakdown = attributor.get_breakdown()
        assert "op1" in breakdown
        assert "op2" in breakdown


class TestDeterminismTracker:
    """Tests for DeterminismTracker class."""

    def test_tracker_creation(self) -> None:
        """Test tracker creation."""
        tracker = DeterminismTracker()
        assert tracker.get_determinism_score() == 0.0

    def test_compute_hash(self) -> None:
        """Test hash computation."""
        tracker = DeterminismTracker()

        hash1 = tracker.compute_hash({"key": "value"})
        hash2 = tracker.compute_hash({"key": "value"})
        assert hash1 == hash2

    def test_record_baseline(self) -> None:
        """Test recording baseline."""
        tracker = DeterminismTracker()
        record = tracker.record_baseline("test_op", {"input": 1}, {"output": 2})

        assert record.operation == "test_op"
        assert record.is_match  # Baseline is always a match

    def test_verify_replay_match(self) -> None:
        """Test matching replay verification."""
        tracker = DeterminismTracker()
        tracker.record_baseline("test_op", {"input": 1}, {"output": 2})

        record = tracker.verify_replay("test_op", {"input": 1}, {"output": 2})
        assert record.is_match

    def test_verify_replay_mismatch(self) -> None:
        """Test mismatching replay verification."""
        tracker = DeterminismTracker()
        tracker.record_baseline("test_op", {"input": 1}, {"output": 2})

        record = tracker.verify_replay("test_op", {"input": 1}, {"output": 999})
        assert not record.is_match

    def test_determinism_score(self) -> None:
        """Test determinism score calculation."""
        tracker = DeterminismTracker()
        tracker.record_baseline("op", {"in": 1}, {"out": 1})
        tracker.verify_replay("op", {"in": 1}, {"out": 1})
        tracker.verify_replay("op", {"in": 1}, {"out": 1})

        assert tracker.get_determinism_score() == 1.0
        assert tracker.is_fully_deterministic()


class TestInstrumentationRegistry:
    """Tests for InstrumentationRegistry class."""

    def test_registry_creation(self) -> None:
        """Test registry creation."""
        registry = InstrumentationRegistry()
        assert registry.is_enabled()

    def test_enable_disable(self) -> None:
        """Test enable/disable."""
        registry = InstrumentationRegistry()
        registry.disable()
        assert not registry.is_enabled()

        registry.enable()
        assert registry.is_enabled()

    def test_create_context(self) -> None:
        """Test context creation."""
        registry = InstrumentationRegistry()
        context = registry.create_context("test_op")

        assert context.operation_name == "test_op"

    def test_record_metric(self) -> None:
        """Test metric recording."""
        registry = InstrumentationRegistry()
        record = registry.record_metric("test_metric", 42.0)

        assert record.name == "test_metric"
        assert record.value == 42.0

    def test_generate_report(self) -> None:
        """Test report generation."""
        registry = InstrumentationRegistry()
        registry.create_context("test_op")
        registry.record_metric("metric1", 10.0)

        report = registry.generate_report()

        assert "timestamp" in report
        assert "contexts" in report
        assert "metrics" in report
        assert "profiler" in report
        assert "cost" in report
        assert "determinism" in report

    def test_registry_reset(self) -> None:
        """Test registry reset."""
        registry = InstrumentationRegistry()
        registry.create_context("test_op")
        registry.reset()

        report = registry.generate_report()
        assert len(report["contexts"]) == 0


class TestInstrumentedDecorator:
    """Tests for @instrumented decorator."""

    def test_instrumented_function(self) -> None:
        """Test instrumented function."""
        registry = InstrumentationRegistry()

        @instrumented(registry)
        def test_fn(x: int) -> int:
            return x * 2

        result = test_fn(5)
        assert result == 10

    def test_instrumented_tracking(self) -> None:
        """Test instrumentation tracking."""
        registry = InstrumentationRegistry()

        @instrumented(registry, name="custom_name")
        def test_fn() -> str:
            return "result"

        test_fn()

        report = registry.generate_report()
        assert len(report["contexts"]) > 0

    def test_instrumented_disabled(self) -> None:
        """Test instrumentation when disabled."""
        registry = InstrumentationRegistry()
        registry.disable()

        @instrumented(registry)
        def test_fn() -> str:
            return "result"

        result = test_fn()
        assert result == "result"

        # No contexts created when disabled
        report = registry.generate_report()
        assert len(report["contexts"]) == 0


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_global_registry(self) -> None:
        """Test getting global registry."""
        reset_global_registry()
        registry = get_global_registry()

        assert registry is not None
        assert isinstance(registry, InstrumentationRegistry)

    def test_global_registry_singleton(self) -> None:
        """Test global registry is singleton."""
        reset_global_registry()
        reg1 = get_global_registry()
        reg2 = get_global_registry()

        assert reg1 is reg2

    def test_reset_global_registry(self) -> None:
        """Test resetting global registry."""
        registry = get_global_registry()
        registry.create_context("test_op")

        reset_global_registry()

        report = registry.generate_report()
        assert len(report["contexts"]) == 0


class TestIntegration:
    """Integration tests for instrumentation."""

    def test_full_instrumentation_workflow(self) -> None:
        """Test complete instrumentation workflow."""
        registry = InstrumentationRegistry()

        # Create context
        context = registry.create_context("full_workflow")

        # Use profiler
        with registry.profiler.span("step1", OperationPhase.INIT):
            pass

        with registry.profiler.span("step2", OperationPhase.COMPUTE):
            # Track costs
            registry.cost.record_tokens(context.operation_name, 5000)
            registry.cost.record_memory_op(context.operation_name, 10)

        # Track determinism
        registry.determinism.record_baseline("full_workflow", {"in": 1}, {"out": 1})
        registry.determinism.verify_replay("full_workflow", {"in": 1}, {"out": 1})

        # Record metrics
        registry.record_metric("custom_metric", 100.0, MetricType.GAUGE)

        # Complete context
        registry.complete_context(context.context_id)

        # Generate report
        report = registry.generate_report()

        assert report["enabled"]
        assert len(report["contexts"]) == 1
        assert report["profiler"]["total_duration_ms"] >= 0
        assert report["cost"]["total_usd"] > 0
        assert report["determinism"]["score"] == 1.0
