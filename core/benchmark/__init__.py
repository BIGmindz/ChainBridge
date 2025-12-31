# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Module — Core Benchmark Infrastructure
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benchmark Module — Infrastructure for measuring Titans-ready architecture.

Provides:
- Deterministic benchmark harness
- Latency, throughput, memory metrics
- Replay determinism verification
- Cost estimation
- Comprehensive instrumentation
"""

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

__all__ = [
    # Harness
    "BenchmarkHarness",
    # Results
    "BenchmarkResult",
    "BenchmarkScenario",
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
    # Instrumentation
    "InstrumentationScope",
    "MetricType",
    "OperationPhase",
    "MetricRecord",
    "TimingSpan",
    "CostRecord",
    "DeterminismRecord",
    "InstrumentationContext",
    "LatencyProfiler",
    "CostAttributor",
    "DeterminismTracker",
    "InstrumentationRegistry",
    "instrumented",
    "get_global_registry",
    "reset_global_registry",
]
