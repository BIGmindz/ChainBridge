"""
OCC v1.x Stress Testing Matrix

PAC: PAC-OCC-P06
Lane: 1 — Stress & Failure Models
Agents: Research Benson (GID-03), Sam (GID-06)

Provides systematic stress testing framework for OCC hardening.
Tests concurrent operations, edge cases, and failure modes.

Invariant: INV-OCC-STRESS-001 — All stress scenarios must be deterministic and repeatable
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# STRESS SCENARIO DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


class StressCategory(Enum):
    """Categories of stress scenarios."""

    CONCURRENCY = "CONCURRENCY"  # Race conditions, deadlocks
    THROUGHPUT = "THROUGHPUT"  # Volume limits, queue overflow
    LATENCY = "LATENCY"  # Response time under load
    RESOURCE = "RESOURCE"  # Memory, CPU, disk exhaustion
    FAILURE = "FAILURE"  # Component failure, network partition
    ADVERSARIAL = "ADVERSARIAL"  # Malicious input, abuse patterns


class StressLevel(Enum):
    """Intensity levels for stress tests."""

    LOW = 1  # Normal operation baseline
    MEDIUM = 2  # Elevated load (2-5x normal)
    HIGH = 3  # Peak load (10x normal)
    EXTREME = 4  # Breaking point discovery
    CHAOS = 5  # Random fault injection


class StressOutcome(Enum):
    """Expected outcome classifications."""

    PASS = "PASS"  # System handled correctly
    DEGRADE = "DEGRADE"  # Graceful degradation observed
    FAIL_SAFE = "FAIL_SAFE"  # System failed safely (expected)
    FAIL_UNSAFE = "FAIL_UNSAFE"  # System failed unsafely (defect)
    TIMEOUT = "TIMEOUT"  # Operation timed out
    ERROR = "ERROR"  # Unexpected error


@dataclass
class StressScenario:
    """Definition of a stress test scenario."""

    scenario_id: str
    name: str
    category: StressCategory
    level: StressLevel
    description: str
    setup: Optional[Callable[[], Any]] = None
    teardown: Optional[Callable[[], Any]] = None
    expected_outcome: StressOutcome = StressOutcome.PASS
    timeout_seconds: int = 60
    tags: List[str] = field(default_factory=list)


@dataclass
class StressResult:
    """Result of a stress test execution."""

    scenario_id: str
    outcome: StressOutcome
    duration_ms: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════════════════════════
# STRESS MATRIX
# ═══════════════════════════════════════════════════════════════════════════════


class OCCStressMatrix:
    """
    Comprehensive stress testing matrix for OCC v1.x.

    Provides:
    - Pre-defined stress scenarios across all categories
    - Concurrent execution framework
    - Result aggregation and reporting
    - Failure injection hooks
    """

    def __init__(self) -> None:
        self._scenarios: Dict[str, StressScenario] = {}
        self._results: List[StressResult] = []
        self._lock = threading.Lock()
        self._register_default_scenarios()

    def _register_default_scenarios(self) -> None:
        """Register default OCC stress scenarios."""

        # ─────────────────────────────────────────────────────────────────
        # CONCURRENCY SCENARIOS
        # ─────────────────────────────────────────────────────────────────

        self.register(
            StressScenario(
                scenario_id="CONC-001",
                name="Concurrent PDO Creation",
                category=StressCategory.CONCURRENCY,
                level=StressLevel.HIGH,
                description="Create 100 PDOs concurrently from multiple threads",
                tags=["pdo", "thread-safety"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="CONC-002",
                name="Concurrent State Transitions",
                category=StressCategory.CONCURRENCY,
                level=StressLevel.HIGH,
                description="Execute state transitions on same PDO from multiple threads",
                expected_outcome=StressOutcome.FAIL_SAFE,  # Should serialize or reject
                tags=["state-machine", "thread-safety"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="CONC-003",
                name="Audit Log Race Condition",
                category=StressCategory.CONCURRENCY,
                level=StressLevel.EXTREME,
                description="Rapid audit log appends to test hash chain integrity",
                tags=["audit", "hash-chain"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="CONC-004",
                name="Kill Switch Activation Race",
                category=StressCategory.CONCURRENCY,
                level=StressLevel.HIGH,
                description="Simultaneous kill switch activation from multiple operators",
                expected_outcome=StressOutcome.PASS,  # Only one should succeed
                tags=["kill-switch", "safety"],
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # THROUGHPUT SCENARIOS
        # ─────────────────────────────────────────────────────────────────

        self.register(
            StressScenario(
                scenario_id="THRU-001",
                name="Queue Saturation",
                category=StressCategory.THROUGHPUT,
                level=StressLevel.HIGH,
                description="Fill OCC queue to capacity and verify backpressure",
                tags=["queue", "backpressure"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="THRU-002",
                name="Burst Traffic Pattern",
                category=StressCategory.THROUGHPUT,
                level=StressLevel.HIGH,
                description="Send 1000 requests in 1 second burst",
                tags=["burst", "rate-limiting"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="THRU-003",
                name="Sustained High Volume",
                category=StressCategory.THROUGHPUT,
                level=StressLevel.MEDIUM,
                description="Maintain 100 req/sec for 5 minutes",
                timeout_seconds=330,
                tags=["sustained", "endurance"],
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # LATENCY SCENARIOS
        # ─────────────────────────────────────────────────────────────────

        self.register(
            StressScenario(
                scenario_id="LAT-001",
                name="Response Time Under Load",
                category=StressCategory.LATENCY,
                level=StressLevel.HIGH,
                description="Measure P99 latency at 80% capacity",
                tags=["p99", "sla"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="LAT-002",
                name="ProofPack Generation Latency",
                category=StressCategory.LATENCY,
                level=StressLevel.MEDIUM,
                description="Time to generate proofpack with 100 artifacts",
                tags=["proofpack", "performance"],
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # RESOURCE SCENARIOS
        # ─────────────────────────────────────────────────────────────────

        self.register(
            StressScenario(
                scenario_id="RES-001",
                name="Memory Pressure",
                category=StressCategory.RESOURCE,
                level=StressLevel.HIGH,
                description="Create large PDOs to test memory handling",
                tags=["memory", "limits"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="RES-002",
                name="Storage Exhaustion Simulation",
                category=StressCategory.RESOURCE,
                level=StressLevel.EXTREME,
                description="Fill audit log until storage limit",
                expected_outcome=StressOutcome.FAIL_SAFE,
                tags=["storage", "graceful-degradation"],
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # FAILURE SCENARIOS
        # ─────────────────────────────────────────────────────────────────

        self.register(
            StressScenario(
                scenario_id="FAIL-001",
                name="Database Connection Loss",
                category=StressCategory.FAILURE,
                level=StressLevel.HIGH,
                description="Simulate database disconnect mid-transaction",
                expected_outcome=StressOutcome.FAIL_SAFE,
                tags=["database", "recovery"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="FAIL-002",
                name="Partial Commit Failure",
                category=StressCategory.FAILURE,
                level=StressLevel.HIGH,
                description="Fail after PDO create but before audit log",
                expected_outcome=StressOutcome.FAIL_SAFE,
                tags=["atomicity", "consistency"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="FAIL-003",
                name="Signature Service Unavailable",
                category=StressCategory.FAILURE,
                level=StressLevel.MEDIUM,
                description="Ed25519 signing unavailable during proofpack seal",
                expected_outcome=StressOutcome.FAIL_SAFE,
                tags=["signing", "degradation"],
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # ADVERSARIAL SCENARIOS
        # ─────────────────────────────────────────────────────────────────

        self.register(
            StressScenario(
                scenario_id="ADV-001",
                name="Malformed PDO Injection",
                category=StressCategory.ADVERSARIAL,
                level=StressLevel.HIGH,
                description="Submit PDOs with invalid/malicious payloads",
                expected_outcome=StressOutcome.FAIL_SAFE,  # Reject, don't crash
                tags=["security", "validation"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="ADV-002",
                name="Privilege Escalation Attempt",
                category=StressCategory.ADVERSARIAL,
                level=StressLevel.HIGH,
                description="T1 operator attempts T4 action",
                expected_outcome=StressOutcome.FAIL_SAFE,  # Denied
                tags=["security", "authorization"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="ADV-003",
                name="Replay Attack",
                category=StressCategory.ADVERSARIAL,
                level=StressLevel.HIGH,
                description="Replay captured action request",
                expected_outcome=StressOutcome.FAIL_SAFE,  # Detected/rejected
                tags=["security", "replay"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="ADV-004",
                name="Hash Chain Tampering",
                category=StressCategory.ADVERSARIAL,
                level=StressLevel.EXTREME,
                description="Attempt to modify historical audit entry",
                expected_outcome=StressOutcome.FAIL_SAFE,  # Detected
                tags=["security", "integrity"],
            )
        )

        self.register(
            StressScenario(
                scenario_id="ADV-005",
                name="Denial of Service via Queue",
                category=StressCategory.ADVERSARIAL,
                level=StressLevel.EXTREME,
                description="Flood queue with low-priority requests",
                expected_outcome=StressOutcome.DEGRADE,  # Should rate limit
                tags=["security", "availability"],
            )
        )

    def register(self, scenario: StressScenario) -> None:
        """Register a stress scenario."""
        self._scenarios[scenario.scenario_id] = scenario

    def get_scenario(self, scenario_id: str) -> Optional[StressScenario]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    def list_scenarios(
        self,
        category: Optional[StressCategory] = None,
        level: Optional[StressLevel] = None,
        tags: Optional[List[str]] = None,
    ) -> List[StressScenario]:
        """List scenarios matching filters."""
        results = list(self._scenarios.values())

        if category:
            results = [s for s in results if s.category == category]
        if level:
            results = [s for s in results if s.level == level]
        if tags:
            results = [s for s in results if any(t in s.tags for t in tags)]

        return results

    def record_result(self, result: StressResult) -> None:
        """Record a stress test result."""
        with self._lock:
            self._results.append(result)

    def get_results(self, scenario_id: Optional[str] = None) -> List[StressResult]:
        """Get recorded results."""
        with self._lock:
            if scenario_id:
                return [r for r in self._results if r.scenario_id == scenario_id]
            return list(self._results)

    def generate_report(self) -> Dict[str, Any]:
        """Generate stress test summary report."""
        with self._lock:
            total = len(self._results)
            if total == 0:
                return {"status": "NO_RESULTS", "total": 0}

            outcomes = {}
            for r in self._results:
                outcomes[r.outcome.value] = outcomes.get(r.outcome.value, 0) + 1

            unsafe_failures = [r for r in self._results if r.outcome == StressOutcome.FAIL_UNSAFE]

            return {
                "status": "FAIL" if unsafe_failures else "PASS",
                "total": total,
                "outcomes": outcomes,
                "unsafe_failures": [
                    {
                        "scenario_id": r.scenario_id,
                        "errors": r.errors,
                    }
                    for r in unsafe_failures
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE INJECTION FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════════


class FailureInjector:
    """
    Controlled failure injection for chaos testing.

    Supports:
    - Probabilistic failures
    - Scheduled failures
    - Component-specific failures
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._active_failures: Dict[str, float] = {}  # component -> probability
        self._lock = threading.Lock()

    def inject_failure(self, component: str, probability: float = 1.0) -> None:
        """
        Enable failure injection for a component.

        Args:
            component: Component identifier
            probability: Failure probability (0.0 - 1.0)
        """
        with self._lock:
            self._active_failures[component] = min(1.0, max(0.0, probability))

    def clear_failure(self, component: str) -> None:
        """Disable failure injection for a component."""
        with self._lock:
            self._active_failures.pop(component, None)

    def clear_all(self) -> None:
        """Disable all failure injections."""
        with self._lock:
            self._active_failures.clear()

    def should_fail(self, component: str) -> bool:
        """
        Check if a component should fail.

        Returns True if failure is injected and probability check passes.
        """
        with self._lock:
            probability = self._active_failures.get(component, 0.0)
            if probability <= 0.0:
                return False
            return self._rng.random() < probability

    def maybe_raise(self, component: str, exception: Exception) -> None:
        """Raise exception if failure is injected for component."""
        if self.should_fail(component):
            raise exception


# Global failure injector instance (disabled by default)
_failure_injector: Optional[FailureInjector] = None


def get_failure_injector() -> FailureInjector:
    """Get global failure injector instance."""
    global _failure_injector
    if _failure_injector is None:
        _failure_injector = FailureInjector()
    return _failure_injector


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENT STRESS RUNNER
# ═══════════════════════════════════════════════════════════════════════════════


class ConcurrentStressRunner:
    """
    Run stress scenarios concurrently with controlled parallelism.
    """

    def __init__(self, max_workers: int = 10) -> None:
        self._max_workers = max_workers
        self._matrix = OCCStressMatrix()

    def run_scenario(
        self,
        scenario: StressScenario,
        test_func: Callable[[StressScenario], StressResult],
    ) -> StressResult:
        """Run a single stress scenario."""
        start = time.monotonic()
        try:
            if scenario.setup:
                scenario.setup()

            result = test_func(scenario)
            result.duration_ms = (time.monotonic() - start) * 1000
            return result

        except Exception as e:
            return StressResult(
                scenario_id=scenario.scenario_id,
                outcome=StressOutcome.ERROR,
                duration_ms=(time.monotonic() - start) * 1000,
                errors=[str(e)],
            )
        finally:
            if scenario.teardown:
                try:
                    scenario.teardown()
                except Exception:
                    pass

    def run_batch(
        self,
        scenarios: List[StressScenario],
        test_func: Callable[[StressScenario], StressResult],
    ) -> List[StressResult]:
        """Run multiple scenarios concurrently."""
        results = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self.run_scenario, s, test_func): s for s in scenarios
            }
            for future in as_completed(futures):
                result = future.result()
                self._matrix.record_result(result)
                results.append(result)
        return results

    def get_matrix(self) -> OCCStressMatrix:
        """Get the stress matrix."""
        return self._matrix


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "StressCategory",
    "StressLevel",
    "StressOutcome",
    "StressScenario",
    "StressResult",
    "OCCStressMatrix",
    "FailureInjector",
    "get_failure_injector",
    "ConcurrentStressRunner",
]
