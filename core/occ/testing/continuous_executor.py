"""
Always-On Test Engine — Continuous Executor

PAC Reference: PAC-JEFFREY-P50
Agent: BENSON (GID-00)

Manages continuous execution of chaos, fuzz, and standard tests
with configurable scheduling and priority.

INVARIANTS:
- Execution is observable at all times
- Resource limits enforced
- Kill-switch respected immediately
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
import random
import threading
import hashlib


class ExecutionMode(Enum):
    """Mode of test execution."""
    STANDARD = "STANDARD"
    CHAOS = "CHAOS"
    FUZZ = "FUZZ"
    MIXED = "MIXED"
    SMOKE = "SMOKE"
    FULL = "FULL"


class ExecutionPriority(Enum):
    """Priority level for test execution."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class ExecutionSchedule:
    """Schedule configuration for continuous execution."""
    mode: ExecutionMode = ExecutionMode.MIXED
    interval_seconds: int = 60
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    max_duration_seconds: int = 300
    enabled: bool = True
    
    # Mode-specific settings
    chaos_percentage: float = 0.2  # % of tests run as chaos
    fuzz_percentage: float = 0.1   # % of tests run as fuzz
    smoke_only_on_commit: bool = True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "interval_seconds": self.interval_seconds,
            "priority": self.priority.value,
            "max_duration_seconds": self.max_duration_seconds,
            "enabled": self.enabled,
            "chaos_percentage": self.chaos_percentage,
            "fuzz_percentage": self.fuzz_percentage,
            "smoke_only_on_commit": self.smoke_only_on_commit,
        }


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_id: str
    test_name: str
    mode: ExecutionMode
    passed: bool
    duration_ms: float
    error_message: str = ""
    stdout: str = ""
    stderr: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "mode": self.mode.value,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


@dataclass
class ExecutionBatch:
    """A batch of tests to execute together."""
    batch_id: str
    mode: ExecutionMode
    tests: list[str]
    started_at: datetime
    completed_at: datetime | None = None
    results: list[TestResult] = field(default_factory=list)
    
    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)
    
    @property
    def duration_seconds(self) -> float:
        if not self.completed_at:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "mode": self.mode.value,
            "test_count": len(self.tests),
            "passed": self.passed_count,
            "failed": self.failed_count,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class ExecutorError(Exception):
    """Error during test execution."""
    pass


class ResourceLimitExceeded(Exception):
    """Resource limits have been exceeded."""
    pass


class ContinuousExecutor:
    """
    Continuous Test Executor.
    
    Executes tests continuously with configurable modes:
    - STANDARD: Regular pytest execution
    - CHAOS: Random failure injection, timing chaos
    - FUZZ: Input fuzzing with adversarial data
    - MIXED: Combination of all modes
    - SMOKE: Quick critical path tests only
    - FULL: Complete test suite
    
    INVARIANTS:
    - All execution is observable
    - Resource limits enforced
    - Respects kill-switch immediately
    """
    
    def __init__(self, schedule: ExecutionSchedule | None = None):
        self.schedule = schedule or ExecutionSchedule()
        self._is_running = False
        self._current_batch: ExecutionBatch | None = None
        self._history: list[ExecutionBatch] = []
        self._lock = threading.Lock()
        self._kill_requested = False
        
        # Resource tracking
        self._memory_used_mb = 0.0
        self._cpu_percent = 0.0
        
        # Limits
        self._max_memory_mb = 2048.0
        self._max_cpu_percent = 80.0
        
        # Callbacks
        self._on_test_complete: Callable[[TestResult], None] | None = None
        self._on_batch_complete: Callable[[ExecutionBatch], None] | None = None
    
    @property
    def is_running(self) -> bool:
        """Check if executor is currently running."""
        return self._is_running
    
    @property
    def current_batch(self) -> ExecutionBatch | None:
        """Get currently executing batch."""
        return self._current_batch
    
    def execute_batch(
        self,
        tests: list[str],
        mode: ExecutionMode | None = None
    ) -> ExecutionBatch:
        """
        Execute a batch of tests.
        
        Args:
            tests: List of test paths/names to execute
            mode: Execution mode (defaults to schedule mode)
        
        Returns:
            ExecutionBatch with results
        """
        if self._kill_requested:
            raise ExecutorError("Kill switch activated")
        
        mode = mode or self.schedule.mode
        batch_id = self._generate_batch_id()
        
        batch = ExecutionBatch(
            batch_id=batch_id,
            mode=mode,
            tests=tests,
            started_at=datetime.utcnow(),
        )
        
        self._current_batch = batch
        self._is_running = True
        
        try:
            for test in tests:
                if self._kill_requested:
                    break
                
                self._check_resource_limits()
                result = self._execute_single_test(test, mode)
                batch.results.append(result)
                
                if self._on_test_complete:
                    self._on_test_complete(result)
        
        finally:
            batch.completed_at = datetime.utcnow()
            self._current_batch = None
            self._is_running = False
            self._history.append(batch)
            
            if self._on_batch_complete:
                self._on_batch_complete(batch)
        
        return batch
    
    def execute_mode(self, mode: ExecutionMode, max_tests: int = 100) -> ExecutionBatch:
        """
        Execute tests in a specific mode.
        
        Args:
            mode: The execution mode
            max_tests: Maximum tests to run
        
        Returns:
            ExecutionBatch with results
        """
        tests = self._select_tests_for_mode(mode, max_tests)
        return self.execute_batch(tests, mode)
    
    def execute_chaos_round(self, intensity: float = 1.0) -> ExecutionBatch:
        """
        Execute a chaos testing round.
        
        Args:
            intensity: Chaos intensity 0.0-1.0
        
        Returns:
            ExecutionBatch with results
        """
        tests = self._select_tests_for_mode(ExecutionMode.CHAOS, int(50 * intensity))
        return self.execute_batch(tests, ExecutionMode.CHAOS)
    
    def execute_fuzz_round(self, iterations: int = 100) -> ExecutionBatch:
        """
        Execute a fuzz testing round.
        
        Args:
            iterations: Number of fuzz iterations
        
        Returns:
            ExecutionBatch with results
        """
        tests = self._generate_fuzz_tests(iterations)
        return self.execute_batch(tests, ExecutionMode.FUZZ)
    
    def request_kill(self) -> None:
        """Request immediate stop of all execution."""
        self._kill_requested = True
    
    def reset_kill(self) -> None:
        """Reset kill switch (for recovery)."""
        self._kill_requested = False
    
    def get_history(self, count: int = 20) -> list[ExecutionBatch]:
        """Get recent execution history."""
        return self._history[-count:]
    
    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        total_tests = sum(len(b.tests) for b in self._history)
        total_passed = sum(b.passed_count for b in self._history)
        total_failed = sum(b.failed_count for b in self._history)
        total_duration = sum(b.duration_seconds for b in self._history)
        
        return {
            "total_batches": len(self._history),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "pass_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
            "total_duration_seconds": total_duration,
            "memory_used_mb": self._memory_used_mb,
            "cpu_percent": self._cpu_percent,
        }
    
    def set_on_test_complete(self, callback: Callable[[TestResult], None]) -> None:
        """Set callback for test completion."""
        self._on_test_complete = callback
    
    def set_on_batch_complete(self, callback: Callable[[ExecutionBatch], None]) -> None:
        """Set callback for batch completion."""
        self._on_batch_complete = callback
    
    def _execute_single_test(self, test: str, mode: ExecutionMode) -> TestResult:
        """Execute a single test."""
        test_id = self._generate_test_id(test)
        start = datetime.utcnow()
        
        # In production, this would invoke PyTest
        # For now, simulate execution
        passed, duration_ms, error = self._simulate_test_execution(test, mode)
        
        return TestResult(
            test_id=test_id,
            test_name=test,
            mode=mode,
            passed=passed,
            duration_ms=duration_ms,
            error_message=error,
        )
    
    def _simulate_test_execution(
        self,
        test: str,
        mode: ExecutionMode
    ) -> tuple[bool, float, str]:
        """
        Simulate test execution.
        
        In production, would run actual PyTest.
        """
        # Base pass rate
        base_pass_rate = 0.98
        
        # Mode adjustments
        if mode == ExecutionMode.CHAOS:
            base_pass_rate = 0.85  # Chaos tests more likely to fail
        elif mode == ExecutionMode.FUZZ:
            base_pass_rate = 0.90  # Fuzz tests find edge cases
        elif mode == ExecutionMode.SMOKE:
            base_pass_rate = 0.99  # Smoke tests rarely fail
        
        passed = random.random() < base_pass_rate
        duration_ms = random.uniform(10, 500)
        error = "" if passed else f"Assertion error in {test}"
        
        return passed, duration_ms, error
    
    def _select_tests_for_mode(self, mode: ExecutionMode, max_tests: int) -> list[str]:
        """Select tests appropriate for the execution mode."""
        # In production, would scan test directory
        # For now, generate sample test names
        test_prefixes = {
            ExecutionMode.STANDARD: "test_",
            ExecutionMode.CHAOS: "test_chaos_",
            ExecutionMode.FUZZ: "test_fuzz_",
            ExecutionMode.SMOKE: "test_smoke_",
            ExecutionMode.FULL: "test_",
            ExecutionMode.MIXED: "test_",
        }
        
        prefix = test_prefixes.get(mode, "test_")
        return [f"{prefix}case_{i}" for i in range(max_tests)]
    
    def _generate_fuzz_tests(self, iterations: int) -> list[str]:
        """Generate fuzz test cases."""
        return [f"test_fuzz_iteration_{i}" for i in range(iterations)]
    
    def _check_resource_limits(self) -> None:
        """Check and enforce resource limits."""
        # In production, would check actual resource usage
        if self._memory_used_mb > self._max_memory_mb:
            raise ResourceLimitExceeded(f"Memory limit exceeded: {self._memory_used_mb}MB")
        if self._cpu_percent > self._max_cpu_percent:
            raise ResourceLimitExceeded(f"CPU limit exceeded: {self._cpu_percent}%")
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID."""
        data = f"{datetime.utcnow().isoformat()}:{len(self._history)}"
        return f"batch_{hashlib.sha256(data.encode()).hexdigest()[:8]}"
    
    def _generate_test_id(self, test: str) -> str:
        """Generate unique test ID."""
        data = f"{test}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]


# Convenience functions

def create_standard_executor() -> ContinuousExecutor:
    """Create executor with standard settings."""
    return ContinuousExecutor(ExecutionSchedule(mode=ExecutionMode.STANDARD))


def create_chaos_executor(intensity: float = 0.5) -> ContinuousExecutor:
    """Create executor optimized for chaos testing."""
    schedule = ExecutionSchedule(
        mode=ExecutionMode.CHAOS,
        chaos_percentage=intensity,
        interval_seconds=30,
    )
    return ContinuousExecutor(schedule)


def create_fuzz_executor() -> ContinuousExecutor:
    """Create executor optimized for fuzz testing."""
    schedule = ExecutionSchedule(
        mode=ExecutionMode.FUZZ,
        fuzz_percentage=1.0,
        interval_seconds=60,
    )
    return ContinuousExecutor(schedule)
