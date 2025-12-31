# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite — Benchmark Harness Tests
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for core/benchmark/benchmark_harness.py

Coverage:
- BenchmarkType enum
- LatencyMetrics calculations
- ThroughputMetrics calculations
- DeterminismMetrics tracking
- CostMetrics estimation
- BenchmarkResult creation and hashing
- BenchmarkScenario registration
- BenchmarkHarness execution
"""

import time
from typing import Any

import pytest

from core.benchmark.benchmark_harness import (
    BenchmarkHarness,
    BenchmarkResult,
    BenchmarkScenario,
    BenchmarkStatus,
    BenchmarkType,
    ComparisonTarget,
    CostMetrics,
    DeterminismMetrics,
    LatencyMetrics,
    MemoryMetrics,
    ThroughputMetrics,
)


class TestBenchmarkEnums:
    """Tests for benchmark enums."""

    def test_benchmark_type_values(self) -> None:
        """Test BenchmarkType enum values."""
        assert BenchmarkType.LATENCY.value == "LATENCY"
        assert BenchmarkType.THROUGHPUT.value == "THROUGHPUT"
        assert BenchmarkType.MEMORY.value == "MEMORY"
        assert BenchmarkType.DETERMINISM.value == "DETERMINISM"
        assert BenchmarkType.COST.value == "COST"
        assert BenchmarkType.END_TO_END.value == "END_TO_END"

    def test_benchmark_status_values(self) -> None:
        """Test BenchmarkStatus enum values."""
        assert BenchmarkStatus.PENDING.value == "PENDING"
        assert BenchmarkStatus.RUNNING.value == "RUNNING"
        assert BenchmarkStatus.COMPLETED.value == "COMPLETED"
        assert BenchmarkStatus.FAILED.value == "FAILED"
        assert BenchmarkStatus.CANCELLED.value == "CANCELLED"

    def test_comparison_target_values(self) -> None:
        """Test ComparisonTarget enum values."""
        assert ComparisonTarget.RAG_BASELINE.value == "RAG_BASELINE"
        assert ComparisonTarget.SHADOW_MEMORY.value == "SHADOW_MEMORY"
        assert ComparisonTarget.FAST_BRAIN.value == "FAST_BRAIN"
        assert ComparisonTarget.SLOW_BRAIN.value == "SLOW_BRAIN"
        assert ComparisonTarget.HYBRID.value == "HYBRID"


class TestLatencyMetrics:
    """Tests for LatencyMetrics class."""

    def test_empty_metrics(self) -> None:
        """Test empty latency metrics."""
        metrics = LatencyMetrics()
        assert metrics.count == 0
        assert metrics.min == 0.0
        assert metrics.max == 0.0
        assert metrics.mean == 0.0
        assert metrics.p50 == 0.0
        assert metrics.p95 == 0.0
        assert metrics.p99 == 0.0

    def test_add_samples(self) -> None:
        """Test adding samples."""
        metrics = LatencyMetrics()
        metrics.add_sample(10.0)
        metrics.add_sample(20.0)
        metrics.add_sample(30.0)

        assert metrics.count == 3
        assert metrics.min == 10.0
        assert metrics.max == 30.0
        assert metrics.mean == 20.0

    def test_percentiles(self) -> None:
        """Test percentile calculations."""
        metrics = LatencyMetrics()
        for i in range(100):
            metrics.add_sample(float(i + 1))

        assert metrics.p50 >= 50.0
        assert metrics.p95 >= 95.0
        assert metrics.p99 >= 99.0

    def test_stddev(self) -> None:
        """Test standard deviation."""
        metrics = LatencyMetrics()
        metrics.add_sample(10.0)
        metrics.add_sample(20.0)
        metrics.add_sample(30.0)

        assert metrics.stddev > 0

    def test_to_dict(self) -> None:
        """Test serialization."""
        metrics = LatencyMetrics()
        metrics.add_sample(10.0)
        metrics.add_sample(20.0)

        data = metrics.to_dict()
        assert "count" in data
        assert "mean" in data
        assert "p50" in data
        assert "unit" in data
        assert data["unit"] == "ms"


class TestThroughputMetrics:
    """Tests for ThroughputMetrics class."""

    def test_ops_per_second(self) -> None:
        """Test operations per second calculation."""
        metrics = ThroughputMetrics(operations=1000, duration_seconds=10.0)
        assert metrics.ops_per_second == 100.0

    def test_zero_duration(self) -> None:
        """Test zero duration handling."""
        metrics = ThroughputMetrics(operations=100, duration_seconds=0.0)
        assert metrics.ops_per_second == 0.0

    def test_to_dict(self) -> None:
        """Test serialization."""
        metrics = ThroughputMetrics(operations=500, duration_seconds=5.0)
        data = metrics.to_dict()

        assert data["operations"] == 500
        assert data["ops_per_second"] == 100.0


class TestMemoryMetrics:
    """Tests for MemoryMetrics class."""

    def test_memory_metrics(self) -> None:
        """Test memory metrics."""
        metrics = MemoryMetrics(
            peak_bytes=1024 * 1024 * 100,  # 100 MB
            allocated_bytes=1024 * 1024 * 50,  # 50 MB
            snapshot_count=5,
            entry_count=1000,
        )

        data = metrics.to_dict()
        assert data["peak_mb"] == 100.0
        assert data["allocated_mb"] == 50.0
        assert data["snapshot_count"] == 5
        assert data["entry_count"] == 1000


class TestDeterminismMetrics:
    """Tests for DeterminismMetrics class."""

    def test_empty_determinism(self) -> None:
        """Test empty determinism metrics."""
        metrics = DeterminismMetrics()
        assert metrics.determinism_score == 0.0
        assert not metrics.is_deterministic

    def test_verify_replay_match(self) -> None:
        """Test matching replay verification."""
        metrics = DeterminismMetrics()
        assert metrics.verify_replay("abc123", "abc123")
        assert metrics.matches == 1
        assert metrics.mismatches == 0

    def test_verify_replay_mismatch(self) -> None:
        """Test mismatching replay verification."""
        metrics = DeterminismMetrics()
        assert not metrics.verify_replay("abc123", "xyz789")
        assert metrics.matches == 0
        assert metrics.mismatches == 1

    def test_determinism_score(self) -> None:
        """Test determinism score calculation."""
        metrics = DeterminismMetrics()
        metrics.verify_replay("a", "a")
        metrics.verify_replay("b", "b")
        metrics.verify_replay("c", "c")
        metrics.verify_replay("d", "x")  # Mismatch

        assert metrics.determinism_score == 0.75
        assert not metrics.is_deterministic

    def test_fully_deterministic(self) -> None:
        """Test fully deterministic scenario."""
        metrics = DeterminismMetrics()
        metrics.verify_replay("a", "a")
        metrics.verify_replay("b", "b")
        metrics.verify_replay("c", "c")

        assert metrics.determinism_score == 1.0
        assert metrics.is_deterministic


class TestCostMetrics:
    """Tests for CostMetrics class."""

    def test_cost_calculation(self) -> None:
        """Test cost calculation."""
        metrics = CostMetrics(
            token_count=10000,
            memory_calls=100,
            snapshot_operations=10,
            routing_decisions=50,
        )

        cost = metrics.calculate_cost()
        assert cost > 0

        # Verify cost components
        expected = (10000 / 1000 * 0.002) + (100 * 0.0001) + (10 * 0.001)
        assert abs(cost - expected) < 0.0001

    def test_to_dict(self) -> None:
        """Test serialization."""
        metrics = CostMetrics(token_count=5000, memory_calls=50)
        data = metrics.to_dict()

        assert "token_count" in data
        assert "estimated_cost_usd" in data


class TestBenchmarkResult:
    """Tests for BenchmarkResult class."""

    def test_valid_result_creation(self) -> None:
        """Test valid result creation."""
        result = BenchmarkResult(
            benchmark_id="BENCH-000001",
            benchmark_type=BenchmarkType.LATENCY,
            status=BenchmarkStatus.COMPLETED,
            started_at="2025-01-01T00:00:00Z",
        )

        assert result.benchmark_id == "BENCH-000001"
        assert result.benchmark_type == BenchmarkType.LATENCY

    def test_invalid_benchmark_id(self) -> None:
        """Test invalid benchmark ID."""
        with pytest.raises(ValueError, match="must start with 'BENCH-'"):
            BenchmarkResult(
                benchmark_id="INVALID-001",
                benchmark_type=BenchmarkType.LATENCY,
                status=BenchmarkStatus.PENDING,
                started_at="2025-01-01T00:00:00Z",
            )

    def test_result_hash(self) -> None:
        """Test result hash computation."""
        result = BenchmarkResult(
            benchmark_id="BENCH-000001",
            benchmark_type=BenchmarkType.LATENCY,
            status=BenchmarkStatus.COMPLETED,
            started_at="2025-01-01T00:00:00Z",
        )

        hash1 = result.compute_result_hash()
        hash2 = result.compute_result_hash()
        assert hash1 == hash2  # Deterministic

    def test_to_dict(self) -> None:
        """Test serialization."""
        result = BenchmarkResult(
            benchmark_id="BENCH-000001",
            benchmark_type=BenchmarkType.LATENCY,
            status=BenchmarkStatus.COMPLETED,
            started_at="2025-01-01T00:00:00Z",
            latency=LatencyMetrics(),
        )

        data = result.to_dict()
        assert "benchmark_id" in data
        assert "result_hash" in data


class TestBenchmarkScenario:
    """Tests for BenchmarkScenario class."""

    def test_valid_scenario(self) -> None:
        """Test valid scenario creation."""
        scenario = BenchmarkScenario(
            scenario_id="SCENARIO-001",
            name="test_scenario",
            description="Test scenario",
            benchmark_type=BenchmarkType.LATENCY,
            target=ComparisonTarget.SHADOW_MEMORY,
            iterations=100,
        )

        assert scenario.scenario_id == "SCENARIO-001"
        assert scenario.iterations == 100

    def test_invalid_scenario_id(self) -> None:
        """Test invalid scenario ID."""
        with pytest.raises(ValueError, match="must start with 'SCENARIO-'"):
            BenchmarkScenario(
                scenario_id="INVALID",
                name="test",
                description="Test",
                benchmark_type=BenchmarkType.LATENCY,
                target=ComparisonTarget.SHADOW_MEMORY,
            )


class TestBenchmarkHarness:
    """Tests for BenchmarkHarness class."""

    def test_harness_creation(self) -> None:
        """Test harness creation."""
        harness = BenchmarkHarness()
        assert harness.result_count() == 0
        assert harness.scenario_count() == 0

    def test_latency_benchmark(self) -> None:
        """Test latency benchmark execution."""
        harness = BenchmarkHarness()

        def fast_operation() -> None:
            time.sleep(0.001)

        result = harness.run_latency_benchmark(fast_operation, iterations=10, warmup=2)

        assert result.status == BenchmarkStatus.COMPLETED
        assert result.latency is not None
        assert result.latency.count == 10
        assert result.latency.mean > 0

    def test_throughput_benchmark(self) -> None:
        """Test throughput benchmark execution."""
        harness = BenchmarkHarness()

        counter = {"ops": 0}

        def fast_operation() -> None:
            counter["ops"] += 1

        result = harness.run_throughput_benchmark(fast_operation, duration_seconds=0.1)

        assert result.status == BenchmarkStatus.COMPLETED
        assert result.throughput is not None
        assert result.throughput.operations > 0

    def test_determinism_benchmark(self) -> None:
        """Test determinism benchmark execution."""
        harness = BenchmarkHarness()

        def deterministic_fn() -> str:
            return "fixed_hash_abc123"

        result = harness.run_determinism_benchmark(deterministic_fn, replay_count=5)

        assert result.status == BenchmarkStatus.COMPLETED
        assert result.determinism is not None
        assert result.determinism.is_deterministic

    def test_non_deterministic_detection(self) -> None:
        """Test detection of non-deterministic function."""
        harness = BenchmarkHarness()

        counter = {"value": 0}

        def non_deterministic_fn() -> str:
            counter["value"] += 1
            return f"hash_{counter['value']}"

        result = harness.run_determinism_benchmark(non_deterministic_fn, replay_count=5)

        assert result.status == BenchmarkStatus.COMPLETED
        assert result.determinism is not None
        assert not result.determinism.is_deterministic

    def test_scenario_registration(self) -> None:
        """Test scenario registration."""
        harness = BenchmarkHarness()

        scenario = BenchmarkScenario(
            scenario_id="SCENARIO-001",
            name="test_fn",
            description="Test scenario",
            benchmark_type=BenchmarkType.LATENCY,
            target=ComparisonTarget.SHADOW_MEMORY,
        )

        harness.register_scenario(scenario)
        assert harness.scenario_count() == 1

    def test_run_scenario(self) -> None:
        """Test running a registered scenario."""
        harness = BenchmarkHarness()

        def test_fn() -> None:
            pass

        harness.register_benchmark("test_fn", test_fn)

        scenario = BenchmarkScenario(
            scenario_id="SCENARIO-001",
            name="test_fn",
            description="Test scenario",
            benchmark_type=BenchmarkType.LATENCY,
            target=ComparisonTarget.SHADOW_MEMORY,
            iterations=5,
            warmup_iterations=1,
        )

        harness.register_scenario(scenario)
        result = harness.run_scenario("SCENARIO-001")

        assert result.status == BenchmarkStatus.COMPLETED

    def test_get_comparison(self) -> None:
        """Test benchmark comparison."""
        harness = BenchmarkHarness()

        def fast_fn() -> None:
            pass

        def slow_fn() -> None:
            time.sleep(0.002)

        result1 = harness.run_latency_benchmark(fast_fn, iterations=10, warmup=2)
        result2 = harness.run_latency_benchmark(slow_fn, iterations=10, warmup=2)

        comparison = harness.get_comparison(result1.benchmark_id, result2.benchmark_id)

        assert "baseline_id" in comparison
        assert "latency_comparison" in comparison

    def test_benchmark_failure_handling(self) -> None:
        """Test benchmark failure handling."""
        harness = BenchmarkHarness()

        def failing_fn() -> None:
            raise RuntimeError("Simulated failure")

        result = harness.run_latency_benchmark(failing_fn, iterations=5, warmup=1)

        assert result.status == BenchmarkStatus.FAILED
        assert result.error_message is not None

    def test_list_results(self) -> None:
        """Test listing results."""
        harness = BenchmarkHarness()

        def noop() -> None:
            pass

        harness.run_latency_benchmark(noop, iterations=5, warmup=1)
        harness.run_latency_benchmark(noop, iterations=5, warmup=1)

        results = harness.list_results()
        assert len(results) == 2


class TestIntegration:
    """Integration tests for benchmark harness."""

    def test_full_benchmark_workflow(self) -> None:
        """Test complete benchmark workflow."""
        harness = BenchmarkHarness()

        # Run latency benchmark
        def test_operation() -> Any:
            return sum(range(100))

        latency_result = harness.run_latency_benchmark(
            test_operation,
            iterations=20,
            warmup=5,
            target=ComparisonTarget.SHADOW_MEMORY,
        )

        assert latency_result.status == BenchmarkStatus.COMPLETED
        assert latency_result.latency.count == 20
        assert latency_result.target == ComparisonTarget.SHADOW_MEMORY

        # Verify result retrieval
        retrieved = harness.get_result(latency_result.benchmark_id)
        assert retrieved is not None
        assert retrieved.benchmark_id == latency_result.benchmark_id

        # Verify result hash
        hash1 = latency_result.compute_result_hash()
        hash2 = retrieved.compute_result_hash()
        assert hash1 == hash2
