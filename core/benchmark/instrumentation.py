# ═══════════════════════════════════════════════════════════════════════════════
# Instrumentation Module — Cost, Latency, Determinism Tracking
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: CODY (GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Instrumentation Module — Comprehensive Pipeline Instrumentation

PURPOSE:
    Instrument the Titans-ready shadow architecture for:
    - Operation timing (latency tracking)
    - Resource consumption (tokens, memory)
    - Determinism verification (hash tracking)
    - Cost attribution (per-operation costs)

COMPONENTS:
    1. InstrumentedOperation - Decorated operation wrapper
    2. InstrumentationRegistry - Central instrumentation collection
    3. CostAttributor - Per-operation cost tracking
    4. DeterminismTracker - Hash-based reproducibility
    5. LatencyProfiler - Hierarchical timing

CONSTRAINTS:
    - SHADOW MODE only (no actual inference)
    - Zero overhead target when disabled
    - Thread-safe accumulation
    - Reproducible metrics

LANE: EXECUTION (INSTRUMENTATION)
"""

from __future__ import annotations

import functools
import hashlib
import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUMENTATION ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class InstrumentationScope(Enum):
    """Scope of instrumentation."""

    GLOBAL = "GLOBAL"  # System-wide
    SERVICE = "SERVICE"  # Per-service
    OPERATION = "OPERATION"  # Per-operation
    COMPONENT = "COMPONENT"  # Per-component


class MetricType(Enum):
    """Type of metric being recorded."""

    COUNTER = "COUNTER"  # Monotonic counter
    GAUGE = "GAUGE"  # Point-in-time value
    HISTOGRAM = "HISTOGRAM"  # Distribution
    TIMER = "TIMER"  # Duration measurement
    HASH = "HASH"  # Determinism tracking


class OperationPhase(Enum):
    """Phase within an operation lifecycle."""

    INIT = "INIT"
    ROUTING = "ROUTING"
    MEMORY_ACCESS = "MEMORY_ACCESS"
    COMPUTE = "COMPUTE"
    SNAPSHOT = "SNAPSHOT"
    FINALIZE = "FINALIZE"


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC RECORDS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MetricRecord:
    """Single metric measurement."""

    name: str
    metric_type: MetricType
    value: float
    timestamp: str
    labels: Dict[str, str] = field(default_factory=dict)
    scope: InstrumentationScope = InstrumentationScope.OPERATION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "scope": self.scope.value,
        }


@dataclass
class TimingSpan:
    """A timing span for hierarchical profiling."""

    span_id: str
    name: str
    parent_id: Optional[str]
    start_time: float
    end_time: Optional[float] = None
    phase: OperationPhase = OperationPhase.COMPUTE
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    @property
    def is_complete(self) -> bool:
        return self.end_time is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "phase": self.phase.value,
            "duration_ms": round(self.duration_ms, 3),
            "is_complete": self.is_complete,
            "metadata": self.metadata,
        }


@dataclass
class CostRecord:
    """Cost attribution record."""

    operation: str
    tokens: int = 0
    memory_operations: int = 0
    routing_decisions: int = 0
    snapshots: int = 0
    computed_cost_usd: float = 0.0

    # Cost coefficients
    TOKEN_COST_PER_1K: float = 0.002
    MEMORY_OP_COST: float = 0.0001
    ROUTING_COST: float = 0.00005
    SNAPSHOT_COST: float = 0.001

    def calculate(self) -> float:
        self.computed_cost_usd = (
            (self.tokens / 1000) * self.TOKEN_COST_PER_1K
            + self.memory_operations * self.MEMORY_OP_COST
            + self.routing_decisions * self.ROUTING_COST
            + self.snapshots * self.SNAPSHOT_COST
        )
        return self.computed_cost_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "tokens": self.tokens,
            "memory_operations": self.memory_operations,
            "routing_decisions": self.routing_decisions,
            "snapshots": self.snapshots,
            "computed_cost_usd": round(self.calculate(), 8),
        }


@dataclass
class DeterminismRecord:
    """Determinism tracking record."""

    operation: str
    input_hash: str
    output_hash: str
    replay_sequence: int
    is_match: bool
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "replay_sequence": self.replay_sequence,
            "is_match": self.is_match,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUMENTATION CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class InstrumentationContext:
    """Context for an instrumented operation."""

    context_id: str
    operation_name: str
    started_at: str
    spans: List[TimingSpan] = field(default_factory=list)
    metrics: List[MetricRecord] = field(default_factory=list)
    cost: Optional[CostRecord] = None
    determinism: Optional[DeterminismRecord] = None
    completed_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.context_id.startswith("CTX-"):
            raise ValueError(f"Context ID must start with 'CTX-': {self.context_id}")
        self.cost = CostRecord(operation=self.operation_name)

    def compute_hash(self) -> str:
        """Compute hash of context state."""
        data = {
            "context_id": self.context_id,
            "operation": self.operation_name,
            "spans": [s.to_dict() for s in self.spans],
            "metrics": [m.to_dict() for m in self.metrics],
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "operation_name": self.operation_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "spans": [s.to_dict() for s in self.spans],
            "metrics": [m.to_dict() for m in self.metrics],
            "cost": self.cost.to_dict() if self.cost else None,
            "determinism": self.determinism.to_dict() if self.determinism else None,
            "context_hash": self.compute_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LATENCY PROFILER
# ═══════════════════════════════════════════════════════════════════════════════


class LatencyProfiler:
    """
    Hierarchical latency profiling with span tracking.

    Provides:
    - Nested span support
    - Phase-based timing
    - Waterfall visualization data
    """

    def __init__(self) -> None:
        self._spans: Dict[str, TimingSpan] = {}
        self._span_stack: List[str] = []
        self._span_counter = 0
        self._lock = threading.Lock()

    def start_span(
        self,
        name: str,
        phase: OperationPhase = OperationPhase.COMPUTE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new timing span."""
        with self._lock:
            self._span_counter += 1
            span_id = f"SPAN-{self._span_counter:06d}"
            parent_id = self._span_stack[-1] if self._span_stack else None

            span = TimingSpan(
                span_id=span_id,
                name=name,
                parent_id=parent_id,
                start_time=time.perf_counter(),
                phase=phase,
                metadata=metadata or {},
            )

            self._spans[span_id] = span
            self._span_stack.append(span_id)
            return span_id

    def end_span(self, span_id: str) -> Optional[TimingSpan]:
        """End a timing span."""
        with self._lock:
            span = self._spans.get(span_id)
            if span is None:
                return None

            span.end_time = time.perf_counter()

            if self._span_stack and self._span_stack[-1] == span_id:
                self._span_stack.pop()

            return span

    @contextmanager
    def span(
        self,
        name: str,
        phase: OperationPhase = OperationPhase.COMPUTE,
    ) -> Generator[str, None, None]:
        """Context manager for timing spans."""
        span_id = self.start_span(name, phase)
        try:
            yield span_id
        finally:
            self.end_span(span_id)

    def get_span(self, span_id: str) -> Optional[TimingSpan]:
        """Get a span by ID."""
        return self._spans.get(span_id)

    def get_all_spans(self) -> List[TimingSpan]:
        """Get all spans."""
        return list(self._spans.values())

    def get_waterfall(self) -> List[Dict[str, Any]]:
        """Get waterfall visualization data."""
        return [span.to_dict() for span in self._spans.values() if span.is_complete]

    def total_duration_ms(self) -> float:
        """Get total duration of all root spans."""
        root_spans = [s for s in self._spans.values() if s.parent_id is None and s.is_complete]
        return sum(s.duration_ms for s in root_spans)

    def reset(self) -> None:
        """Reset profiler state."""
        with self._lock:
            self._spans.clear()
            self._span_stack.clear()
            self._span_counter = 0


# ═══════════════════════════════════════════════════════════════════════════════
# COST ATTRIBUTOR
# ═══════════════════════════════════════════════════════════════════════════════


class CostAttributor:
    """
    Per-operation cost attribution.

    Tracks resource consumption and computes costs for:
    - Token usage
    - Memory operations
    - Routing decisions
    - Snapshot operations
    """

    def __init__(self) -> None:
        self._costs: Dict[str, CostRecord] = {}
        self._lock = threading.Lock()

    def create_record(self, operation: str) -> CostRecord:
        """Create a new cost record for an operation."""
        with self._lock:
            record = CostRecord(operation=operation)
            self._costs[operation] = record
            return record

    def record_tokens(self, operation: str, count: int) -> None:
        """Record token consumption."""
        with self._lock:
            if operation in self._costs:
                self._costs[operation].tokens += count

    def record_memory_op(self, operation: str, count: int = 1) -> None:
        """Record memory operation."""
        with self._lock:
            if operation in self._costs:
                self._costs[operation].memory_operations += count

    def record_routing(self, operation: str, count: int = 1) -> None:
        """Record routing decision."""
        with self._lock:
            if operation in self._costs:
                self._costs[operation].routing_decisions += count

    def record_snapshot(self, operation: str, count: int = 1) -> None:
        """Record snapshot operation."""
        with self._lock:
            if operation in self._costs:
                self._costs[operation].snapshots += count

    def get_cost(self, operation: str) -> Optional[CostRecord]:
        """Get cost record for an operation."""
        return self._costs.get(operation)

    def total_cost_usd(self) -> float:
        """Get total cost across all operations."""
        return sum(record.calculate() for record in self._costs.values())

    def get_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by operation."""
        return {op: record.calculate() for op, record in self._costs.items()}

    def reset(self) -> None:
        """Reset all cost records."""
        with self._lock:
            self._costs.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISM TRACKER
# ═══════════════════════════════════════════════════════════════════════════════


class DeterminismTracker:
    """
    Hash-based determinism verification.

    Ensures reproducible outputs by:
    - Hashing inputs and outputs
    - Comparing across replay sequences
    - Recording match/mismatch patterns
    """

    def __init__(self) -> None:
        self._records: List[DeterminismRecord] = []
        self._baseline_hashes: Dict[str, str] = {}
        self._replay_sequence: Dict[str, int] = {}
        self._lock = threading.Lock()

    def compute_hash(self, data: Any) -> str:
        """Compute hash of arbitrary data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def record_baseline(
        self,
        operation: str,
        input_data: Any,
        output_data: Any,
    ) -> DeterminismRecord:
        """Record baseline hashes for an operation."""
        with self._lock:
            input_hash = self.compute_hash(input_data)
            output_hash = self.compute_hash(output_data)

            key = f"{operation}:{input_hash}"
            self._baseline_hashes[key] = output_hash
            self._replay_sequence[key] = 0

            record = DeterminismRecord(
                operation=operation,
                input_hash=input_hash,
                output_hash=output_hash,
                replay_sequence=0,
                is_match=True,  # Baseline is always a match
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            self._records.append(record)
            return record

    def verify_replay(
        self,
        operation: str,
        input_data: Any,
        output_data: Any,
    ) -> DeterminismRecord:
        """Verify a replay against baseline."""
        with self._lock:
            input_hash = self.compute_hash(input_data)
            output_hash = self.compute_hash(output_data)

            key = f"{operation}:{input_hash}"
            baseline_output = self._baseline_hashes.get(key)

            sequence = self._replay_sequence.get(key, 0) + 1
            self._replay_sequence[key] = sequence

            is_match = baseline_output == output_hash if baseline_output else False

            record = DeterminismRecord(
                operation=operation,
                input_hash=input_hash,
                output_hash=output_hash,
                replay_sequence=sequence,
                is_match=is_match,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            self._records.append(record)
            return record

    def get_determinism_score(self) -> float:
        """Get overall determinism score."""
        if not self._records:
            return 0.0
        matches = sum(1 for r in self._records if r.is_match)
        return matches / len(self._records)

    def get_mismatches(self) -> List[DeterminismRecord]:
        """Get all mismatch records."""
        return [r for r in self._records if not r.is_match]

    def is_fully_deterministic(self) -> bool:
        """Check if all replays are deterministic."""
        return all(r.is_match for r in self._records)

    def reset(self) -> None:
        """Reset tracker state."""
        with self._lock:
            self._records.clear()
            self._baseline_hashes.clear()
            self._replay_sequence.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUMENTATION REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class InstrumentationRegistry:
    """
    Central instrumentation collection and management.

    Provides:
    - Context creation and tracking
    - Metric aggregation
    - Report generation
    """

    def __init__(self) -> None:
        self._contexts: Dict[str, InstrumentationContext] = {}
        self._metrics: List[MetricRecord] = []
        self._profiler = LatencyProfiler()
        self._cost_attributor = CostAttributor()
        self._determinism_tracker = DeterminismTracker()
        self._context_counter = 0
        self._enabled = True
        self._lock = threading.Lock()

    @property
    def profiler(self) -> LatencyProfiler:
        return self._profiler

    @property
    def cost(self) -> CostAttributor:
        return self._cost_attributor

    @property
    def determinism(self) -> DeterminismTracker:
        return self._determinism_tracker

    def enable(self) -> None:
        """Enable instrumentation."""
        self._enabled = True

    def disable(self) -> None:
        """Disable instrumentation."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if instrumentation is enabled."""
        return self._enabled

    def create_context(self, operation_name: str) -> InstrumentationContext:
        """Create a new instrumentation context."""
        with self._lock:
            self._context_counter += 1
            context_id = f"CTX-{self._context_counter:06d}"

            context = InstrumentationContext(
                context_id=context_id,
                operation_name=operation_name,
                started_at=datetime.now(timezone.utc).isoformat(),
            )

            self._contexts[context_id] = context
            self._cost_attributor.create_record(operation_name)
            return context

    def complete_context(self, context_id: str) -> Optional[InstrumentationContext]:
        """Mark context as complete."""
        context = self._contexts.get(context_id)
        if context:
            context.completed_at = datetime.now(timezone.utc).isoformat()
        return context

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        scope: InstrumentationScope = InstrumentationScope.OPERATION,
    ) -> MetricRecord:
        """Record a metric."""
        record = MetricRecord(
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            labels=labels or {},
            scope=scope,
        )
        with self._lock:
            self._metrics.append(record)
        return record

    def get_context(self, context_id: str) -> Optional[InstrumentationContext]:
        """Get context by ID."""
        return self._contexts.get(context_id)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive instrumentation report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "enabled": self._enabled,
            "contexts": {cid: ctx.to_dict() for cid, ctx in self._contexts.items()},
            "metrics": [m.to_dict() for m in self._metrics],
            "profiler": {
                "total_duration_ms": round(self._profiler.total_duration_ms(), 3),
                "spans": self._profiler.get_waterfall(),
            },
            "cost": {
                "total_usd": round(self._cost_attributor.total_cost_usd(), 8),
                "breakdown": self._cost_attributor.get_breakdown(),
            },
            "determinism": {
                "score": round(self._determinism_tracker.get_determinism_score(), 4),
                "is_deterministic": self._determinism_tracker.is_fully_deterministic(),
                "mismatches": len(self._determinism_tracker.get_mismatches()),
            },
        }

    def reset(self) -> None:
        """Reset all instrumentation state."""
        with self._lock:
            self._contexts.clear()
            self._metrics.clear()
            self._context_counter = 0
        self._profiler.reset()
        self._cost_attributor.reset()
        self._determinism_tracker.reset()


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUMENTED DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════


def instrumented(
    registry: InstrumentationRegistry,
    name: Optional[str] = None,
    phase: OperationPhase = OperationPhase.COMPUTE,
    track_cost: bool = True,
    track_determinism: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to instrument a function.

    Args:
        registry: InstrumentationRegistry to use
        name: Override for operation name
        phase: Operation phase for timing
        track_cost: Whether to track cost
        track_determinism: Whether to track determinism
    """

    def decorator(fn: F) -> F:
        op_name = name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not registry.is_enabled():
                return fn(*args, **kwargs)

            context = registry.create_context(op_name)

            with registry.profiler.span(op_name, phase):
                result = fn(*args, **kwargs)

            if track_cost:
                # Estimate token count from args/kwargs
                estimated_tokens = len(str(args)) + len(str(kwargs)) + len(str(result))
                registry.cost.record_tokens(op_name, estimated_tokens // 4)

            if track_determinism:
                registry.determinism.record_baseline(op_name, (args, kwargs), result)

            registry.complete_context(context.context_id)
            return result

        return wrapper  # type: ignore

    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

# Singleton global registry
_global_registry: Optional[InstrumentationRegistry] = None


def get_global_registry() -> InstrumentationRegistry:
    """Get or create the global instrumentation registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = InstrumentationRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry."""
    global _global_registry
    if _global_registry:
        _global_registry.reset()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "InstrumentationScope",
    "MetricType",
    "OperationPhase",
    # Data classes
    "MetricRecord",
    "TimingSpan",
    "CostRecord",
    "DeterminismRecord",
    "InstrumentationContext",
    # Components
    "LatencyProfiler",
    "CostAttributor",
    "DeterminismTracker",
    "InstrumentationRegistry",
    # Decorator
    "instrumented",
    # Global
    "get_global_registry",
    "reset_global_registry",
]
