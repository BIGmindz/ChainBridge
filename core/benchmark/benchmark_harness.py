# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Harness — Deterministic Replay & Performance Measurement
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agents: CODY (GID-01), MAGGIE (GID-10)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benchmark Harness — Deterministic Performance Benchmarking

PURPOSE:
    Provide reproducible benchmark infrastructure for measuring:
    - Latency (p50, p95, p99)
    - Token/memory usage
    - Replay determinism
    - Cost estimation
    - Memory routing decisions

BENCHMARK TYPES:
    1. RAG vs Shadow Memory comparison
    2. Routing decision latency
    3. Snapshot creation/restore performance
    4. Invariant check overhead
    5. End-to-end pipeline latency

CONSTRAINTS:
    - SHADOW MODE only (no actual inference)
    - Deterministic replay required
    - All results must be reproducible
    - No model weights involved

LANE: EXECUTION (BENCHMARK)
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class BenchmarkType(Enum):
    """Type of benchmark being executed."""

    LATENCY = "LATENCY"  # Response time measurement
    THROUGHPUT = "THROUGHPUT"  # Operations per second
    MEMORY = "MEMORY"  # Memory consumption
    DETERMINISM = "DETERMINISM"  # Replay reproducibility
    COST = "COST"  # Resource cost estimation
    END_TO_END = "END_TO_END"  # Full pipeline


class BenchmarkStatus(Enum):
    """Status of benchmark execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ComparisonTarget(Enum):
    """Target for A/B comparison benchmarks."""

    RAG_BASELINE = "RAG_BASELINE"  # Traditional RAG
    SHADOW_MEMORY = "SHADOW_MEMORY"  # Titans shadow mode
    FAST_BRAIN = "FAST_BRAIN"  # Attention-based
    SLOW_BRAIN = "SLOW_BRAIN"  # Persistent memory
    HYBRID = "HYBRID"  # Combined routing


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK METRICS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class LatencyMetrics:
    """Latency measurement results."""

    samples: List[float] = field(default_factory=list)
    unit: str = "ms"

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def min(self) -> float:
        return min(self.samples) if self.samples else 0.0

    @property
    def max(self) -> float:
        return max(self.samples) if self.samples else 0.0

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def p50(self) -> float:
        return self._percentile(50)

    @property
    def p95(self) -> float:
        return self._percentile(95)

    @property
    def p99(self) -> float:
        return self._percentile(99)

    @property
    def stddev(self) -> float:
        return statistics.stdev(self.samples) if len(self.samples) > 1 else 0.0

    def _percentile(self, p: int) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * p / 100)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def add_sample(self, value: float) -> None:
        self.samples.append(value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "min": round(self.min, 3),
            "max": round(self.max, 3),
            "mean": round(self.mean, 3),
            "median": round(self.median, 3),
            "p50": round(self.p50, 3),
            "p95": round(self.p95, 3),
            "p99": round(self.p99, 3),
            "stddev": round(self.stddev, 3),
            "unit": self.unit,
        }


@dataclass
class ThroughputMetrics:
    """Throughput measurement results."""

    operations: int = 0
    duration_seconds: float = 0.0
    unit: str = "ops/sec"

    @property
    def ops_per_second(self) -> float:
        return self.operations / self.duration_seconds if self.duration_seconds > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operations": self.operations,
            "duration_seconds": round(self.duration_seconds, 3),
            "ops_per_second": round(self.ops_per_second, 2),
            "unit": self.unit,
        }


@dataclass
class MemoryMetrics:
    """Memory usage measurement results."""

    peak_bytes: int = 0
    allocated_bytes: int = 0
    snapshot_count: int = 0
    entry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peak_mb": round(self.peak_bytes / (1024 * 1024), 2),
            "allocated_mb": round(self.allocated_bytes / (1024 * 1024), 2),
            "snapshot_count": self.snapshot_count,
            "entry_count": self.entry_count,
        }


@dataclass
class DeterminismMetrics:
    """Determinism verification results."""

    replay_count: int = 0
    matches: int = 0
    mismatches: int = 0
    hash_sequence: List[str] = field(default_factory=list)

    @property
    def determinism_score(self) -> float:
        total = self.matches + self.mismatches
        return self.matches / total if total > 0 else 0.0

    @property
    def is_deterministic(self) -> bool:
        return self.mismatches == 0 and self.replay_count > 0

    def record_hash(self, hash_value: str) -> None:
        self.hash_sequence.append(hash_value)

    def verify_replay(self, expected_hash: str, actual_hash: str) -> bool:
        self.replay_count += 1
        if expected_hash == actual_hash:
            self.matches += 1
            return True
        else:
            self.mismatches += 1
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "replay_count": self.replay_count,
            "matches": self.matches,
            "mismatches": self.mismatches,
            "determinism_score": round(self.determinism_score, 4),
            "is_deterministic": self.is_deterministic,
        }


@dataclass
class CostMetrics:
    """Cost estimation metrics."""

    token_count: int = 0
    memory_calls: int = 0
    snapshot_operations: int = 0
    routing_decisions: int = 0
    estimated_cost_usd: float = 0.0

    # Cost coefficients (shadow mode estimates)
    TOKEN_COST_PER_1K: float = 0.002
    MEMORY_CALL_COST: float = 0.0001
    SNAPSHOT_COST: float = 0.001

    def calculate_cost(self) -> float:
        token_cost = (self.token_count / 1000) * self.TOKEN_COST_PER_1K
        memory_cost = self.memory_calls * self.MEMORY_CALL_COST
        snapshot_cost = self.snapshot_operations * self.SNAPSHOT_COST
        self.estimated_cost_usd = token_cost + memory_cost + snapshot_cost
        return self.estimated_cost_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_count": self.token_count,
            "memory_calls": self.memory_calls,
            "snapshot_operations": self.snapshot_operations,
            "routing_decisions": self.routing_decisions,
            "estimated_cost_usd": round(self.calculate_cost(), 6),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BenchmarkResult:
    """Complete benchmark execution result."""

    benchmark_id: str
    benchmark_type: BenchmarkType
    status: BenchmarkStatus
    started_at: str
    completed_at: Optional[str] = None
    target: ComparisonTarget = ComparisonTarget.SHADOW_MEMORY
    latency: Optional[LatencyMetrics] = None
    throughput: Optional[ThroughputMetrics] = None
    memory: Optional[MemoryMetrics] = None
    determinism: Optional[DeterminismMetrics] = None
    cost: Optional[CostMetrics] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.benchmark_id.startswith("BENCH-"):
            raise ValueError(f"Benchmark ID must start with 'BENCH-': {self.benchmark_id}")

    def compute_result_hash(self) -> str:
        """Compute hash of benchmark result for verification."""
        data = {
            "benchmark_id": self.benchmark_id,
            "benchmark_type": self.benchmark_type.value,
            "status": self.status.value,
            "latency": self.latency.to_dict() if self.latency else None,
            "throughput": self.throughput.to_dict() if self.throughput else None,
            "determinism": self.determinism.to_dict() if self.determinism else None,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_type": self.benchmark_type.value,
            "status": self.status.value,
            "target": self.target.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency": self.latency.to_dict() if self.latency else None,
            "throughput": self.throughput.to_dict() if self.throughput else None,
            "memory": self.memory.to_dict() if self.memory else None,
            "determinism": self.determinism.to_dict() if self.determinism else None,
            "cost": self.cost.to_dict() if self.cost else None,
            "result_hash": self.compute_result_hash(),
            "metadata": self.metadata,
            "error_message": self.error_message,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK SCENARIO
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BenchmarkScenario:
    """Definition of a benchmark scenario."""

    scenario_id: str
    name: str
    description: str
    benchmark_type: BenchmarkType
    target: ComparisonTarget
    iterations: int = 100
    warmup_iterations: int = 10
    timeout_seconds: float = 60.0
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scenario_id.startswith("SCENARIO-"):
            raise ValueError(f"Scenario ID must start with 'SCENARIO-': {self.scenario_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK HARNESS
# ═══════════════════════════════════════════════════════════════════════════════


class BenchmarkHarness:
    """
    Core benchmark execution harness.

    Provides deterministic, reproducible benchmarking with:
    - Warmup phase
    - Multiple iterations
    - Statistical aggregation
    - Replay verification
    """

    def __init__(self) -> None:
        self._results: Dict[str, BenchmarkResult] = {}
        self._scenarios: Dict[str, BenchmarkScenario] = {}
        self._benchmark_counter = 0
        self._registered_benchmarks: Dict[str, Callable[..., Any]] = {}

    def register_scenario(self, scenario: BenchmarkScenario) -> None:
        """Register a benchmark scenario."""
        self._scenarios[scenario.scenario_id] = scenario

    def register_benchmark(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a benchmark function."""
        self._registered_benchmarks[name] = fn

    def run_latency_benchmark(
        self,
        fn: Callable[[], Any],
        iterations: int = 100,
        warmup: int = 10,
        target: ComparisonTarget = ComparisonTarget.SHADOW_MEMORY,
    ) -> BenchmarkResult:
        """Run a latency benchmark."""
        self._benchmark_counter += 1
        benchmark_id = f"BENCH-{self._benchmark_counter:06d}"

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.LATENCY,
            status=BenchmarkStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
            target=target,
            latency=LatencyMetrics(),
        )

        try:
            # Warmup phase
            for _ in range(warmup):
                fn()

            # Measurement phase
            for _ in range(iterations):
                start = time.perf_counter()
                fn()
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                result.latency.add_sample(elapsed)

            result.status = BenchmarkStatus.COMPLETED
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        self._results[benchmark_id] = result
        return result

    def run_throughput_benchmark(
        self,
        fn: Callable[[], Any],
        duration_seconds: float = 10.0,
        target: ComparisonTarget = ComparisonTarget.SHADOW_MEMORY,
    ) -> BenchmarkResult:
        """Run a throughput benchmark."""
        self._benchmark_counter += 1
        benchmark_id = f"BENCH-{self._benchmark_counter:06d}"

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.THROUGHPUT,
            status=BenchmarkStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
            target=target,
            throughput=ThroughputMetrics(),
        )

        try:
            operations = 0
            start = time.perf_counter()
            end_time = start + duration_seconds

            while time.perf_counter() < end_time:
                fn()
                operations += 1

            actual_duration = time.perf_counter() - start
            result.throughput.operations = operations
            result.throughput.duration_seconds = actual_duration
            result.status = BenchmarkStatus.COMPLETED
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        self._results[benchmark_id] = result
        return result

    def run_determinism_benchmark(
        self,
        fn: Callable[[], str],  # Function must return hash of result
        replay_count: int = 5,
        target: ComparisonTarget = ComparisonTarget.SHADOW_MEMORY,
    ) -> BenchmarkResult:
        """Run a determinism verification benchmark."""
        self._benchmark_counter += 1
        benchmark_id = f"BENCH-{self._benchmark_counter:06d}"

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=BenchmarkType.DETERMINISM,
            status=BenchmarkStatus.RUNNING,
            started_at=datetime.now(timezone.utc).isoformat(),
            target=target,
            determinism=DeterminismMetrics(),
        )

        try:
            # Get baseline hash
            baseline_hash = fn()
            result.determinism.record_hash(baseline_hash)

            # Replay and verify
            for _ in range(replay_count):
                replay_hash = fn()
                result.determinism.verify_replay(baseline_hash, replay_hash)
                result.determinism.record_hash(replay_hash)

            result.status = BenchmarkStatus.COMPLETED
        except Exception as e:
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        self._results[benchmark_id] = result
        return result

    def run_scenario(self, scenario_id: str) -> BenchmarkResult:
        """Run a registered benchmark scenario."""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        benchmark_fn = self._registered_benchmarks.get(scenario.name)
        if benchmark_fn is None:
            raise ValueError(f"No benchmark registered for: {scenario.name}")

        if scenario.benchmark_type == BenchmarkType.LATENCY:
            return self.run_latency_benchmark(
                benchmark_fn,
                iterations=scenario.iterations,
                warmup=scenario.warmup_iterations,
                target=scenario.target,
            )
        elif scenario.benchmark_type == BenchmarkType.THROUGHPUT:
            return self.run_throughput_benchmark(
                benchmark_fn,
                duration_seconds=scenario.timeout_seconds,
                target=scenario.target,
            )
        elif scenario.benchmark_type == BenchmarkType.DETERMINISM:
            return self.run_determinism_benchmark(
                benchmark_fn,
                replay_count=scenario.iterations,
                target=scenario.target,
            )
        else:
            raise ValueError(f"Unsupported benchmark type: {scenario.benchmark_type}")

    def get_result(self, benchmark_id: str) -> Optional[BenchmarkResult]:
        """Get a benchmark result by ID."""
        return self._results.get(benchmark_id)

    def list_results(self) -> List[BenchmarkResult]:
        """List all benchmark results."""
        return list(self._results.values())

    def get_comparison(
        self,
        baseline_id: str,
        comparison_id: str,
    ) -> Dict[str, Any]:
        """Compare two benchmark results."""
        baseline = self._results.get(baseline_id)
        comparison = self._results.get(comparison_id)

        if baseline is None or comparison is None:
            return {"error": "One or both benchmarks not found"}

        result = {
            "baseline_id": baseline_id,
            "comparison_id": comparison_id,
            "baseline_target": baseline.target.value,
            "comparison_target": comparison.target.value,
        }

        # Compare latency if available
        if baseline.latency and comparison.latency:
            delta_mean = comparison.latency.mean - baseline.latency.mean
            delta_p95 = comparison.latency.p95 - baseline.latency.p95
            improvement = ((baseline.latency.mean - comparison.latency.mean) / baseline.latency.mean * 100) if baseline.latency.mean > 0 else 0

            result["latency_comparison"] = {
                "baseline_mean_ms": round(baseline.latency.mean, 3),
                "comparison_mean_ms": round(comparison.latency.mean, 3),
                "delta_mean_ms": round(delta_mean, 3),
                "delta_p95_ms": round(delta_p95, 3),
                "improvement_percent": round(improvement, 2),
            }

        # Compare throughput if available
        if baseline.throughput and comparison.throughput:
            delta_ops = comparison.throughput.ops_per_second - baseline.throughput.ops_per_second
            improvement = ((comparison.throughput.ops_per_second - baseline.throughput.ops_per_second) / baseline.throughput.ops_per_second * 100) if baseline.throughput.ops_per_second > 0 else 0

            result["throughput_comparison"] = {
                "baseline_ops": round(baseline.throughput.ops_per_second, 2),
                "comparison_ops": round(comparison.throughput.ops_per_second, 2),
                "delta_ops": round(delta_ops, 2),
                "improvement_percent": round(improvement, 2),
            }

        return result

    def result_count(self) -> int:
        """Return count of benchmark results."""
        return len(self._results)

    def scenario_count(self) -> int:
        """Return count of registered scenarios."""
        return len(self._scenarios)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "BenchmarkType",
    "BenchmarkStatus",
    "ComparisonTarget",
    # Metrics
    "LatencyMetrics",
    "ThroughputMetrics",
    "MemoryMetrics",
    "DeterminismMetrics",
    "CostMetrics",
    # Data classes
    "BenchmarkResult",
    "BenchmarkScenario",
    # Harness
    "BenchmarkHarness",
]
