"""
Always-On Test Engine — Core Engine

PAC Reference: PAC-JEFFREY-P50
Agent: BENSON (GID-00)

The core engine that orchestrates continuous test execution, manages
execution cycles, and coordinates between chaos, fuzz, and standard tests.

INVARIANTS:
- Engine state is always observable
- Kill-switch stops all execution immediately
- No mutation of external systems
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
import hashlib
import threading
import time


class EngineStatus(Enum):
    """Current status of the always-on engine."""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"
    KILLED = "KILLED"


class CycleResult(Enum):
    """Result of an execution cycle."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILURE = "FAILURE"
    ABORTED = "ABORTED"
    KILLED = "KILLED"


@dataclass
class EngineConfig:
    """Configuration for the always-on engine."""
    # Execution settings
    cycle_interval_seconds: int = 60
    max_parallel_tests: int = 10
    test_timeout_seconds: int = 300
    
    # CCI settings
    cci_threshold: float = 1.0
    cci_fail_on_decrease: bool = True
    
    # Kill-switch settings
    enable_kill_switch: bool = True
    kill_switch_timeout_seconds: int = 5
    
    # Resource limits
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_interval_seconds": self.cycle_interval_seconds,
            "max_parallel_tests": self.max_parallel_tests,
            "test_timeout_seconds": self.test_timeout_seconds,
            "cci_threshold": self.cci_threshold,
            "cci_fail_on_decrease": self.cci_fail_on_decrease,
            "enable_kill_switch": self.enable_kill_switch,
            "kill_switch_timeout_seconds": self.kill_switch_timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
        }


@dataclass
class ExecutionCycle:
    """Record of a single execution cycle."""
    cycle_id: str
    started_at: datetime
    completed_at: datetime | None = None
    result: CycleResult = CycleResult.SUCCESS
    tests_executed: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    cci_before: float = 0.0
    cci_after: float = 0.0
    duration_seconds: float = 0.0
    error_message: str = ""
    
    @property
    def pass_rate(self) -> float:
        if self.tests_executed == 0:
            return 0.0
        return (self.tests_passed / self.tests_executed) * 100
    
    @property
    def cci_delta(self) -> float:
        return self.cci_after - self.cci_before
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.value,
            "tests_executed": self.tests_executed,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "pass_rate": self.pass_rate,
            "cci_before": self.cci_before,
            "cci_after": self.cci_after,
            "cci_delta": self.cci_delta,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }


@dataclass
class EngineMetrics:
    """Aggregate metrics for the engine."""
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    total_tests_executed: int = 0
    total_tests_passed: int = 0
    total_runtime_seconds: float = 0.0
    current_cci: float = 0.0
    peak_cci: float = 0.0
    last_cycle_at: datetime | None = None
    
    @property
    def success_rate(self) -> float:
        if self.total_cycles == 0:
            return 0.0
        return (self.successful_cycles / self.total_cycles) * 100
    
    @property
    def overall_pass_rate(self) -> float:
        if self.total_tests_executed == 0:
            return 0.0
        return (self.total_tests_passed / self.total_tests_executed) * 100
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cycles": self.total_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "success_rate": self.success_rate,
            "total_tests_executed": self.total_tests_executed,
            "total_tests_passed": self.total_tests_passed,
            "overall_pass_rate": self.overall_pass_rate,
            "total_runtime_seconds": self.total_runtime_seconds,
            "current_cci": self.current_cci,
            "peak_cci": self.peak_cci,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
        }


class EngineError(Exception):
    """Error in the always-on engine."""
    pass


class KillSwitchActivated(Exception):
    """Kill switch has been activated."""
    pass


class AlwaysOnEngine:
    """
    The Always-On Test Engine.
    
    Orchestrates continuous test execution with:
    - Automatic cycle scheduling
    - CCI tracking and enforcement
    - Kill-switch for emergency stop
    - Observable state at all times
    
    INVARIANTS:
    - Status is always queryable
    - Kill-switch response < 5 seconds
    - No external mutation
    """
    
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self._status = EngineStatus.STOPPED
        self._metrics = EngineMetrics()
        self._cycles: list[ExecutionCycle] = []
        self._kill_switch_armed = False
        self._kill_switch_reason = ""
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._execution_thread: threading.Thread | None = None
        
        # Callbacks
        self._on_cycle_complete: Callable[[ExecutionCycle], None] | None = None
        self._on_status_change: Callable[[EngineStatus], None] | None = None
    
    @property
    def status(self) -> EngineStatus:
        """Get current engine status."""
        return self._status
    
    @property
    def metrics(self) -> EngineMetrics:
        """Get current engine metrics."""
        return self._metrics
    
    @property
    def is_running(self) -> bool:
        """Check if engine is actively running."""
        return self._status == EngineStatus.RUNNING
    
    @property
    def kill_switch_armed(self) -> bool:
        """Check if kill switch is armed."""
        return self._kill_switch_armed
    
    def start(self) -> bool:
        """
        Start the always-on engine.
        
        Returns True if started successfully.
        """
        with self._lock:
            if self._status in {EngineStatus.RUNNING, EngineStatus.STARTING}:
                return False
            
            if self._kill_switch_armed:
                return False
            
            self._set_status(EngineStatus.STARTING)
            self._stop_event.clear()
        
        # Start execution thread
        self._execution_thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="AlwaysOnEngine"
        )
        self._execution_thread.start()
        
        return True
    
    def stop(self) -> bool:
        """
        Stop the engine gracefully.
        
        Returns True if stop was initiated.
        """
        with self._lock:
            if self._status == EngineStatus.STOPPED:
                return True
            
            self._set_status(EngineStatus.STOPPING)
            self._stop_event.set()
        
        # Wait for thread to finish
        if self._execution_thread and self._execution_thread.is_alive():
            self._execution_thread.join(timeout=10.0)
        
        with self._lock:
            self._set_status(EngineStatus.STOPPED)
        
        return True
    
    def pause(self) -> bool:
        """Pause execution (can be resumed)."""
        with self._lock:
            if self._status != EngineStatus.RUNNING:
                return False
            self._set_status(EngineStatus.PAUSED)
            return True
    
    def resume(self) -> bool:
        """Resume paused execution."""
        with self._lock:
            if self._status != EngineStatus.PAUSED:
                return False
            self._set_status(EngineStatus.RUNNING)
            return True
    
    def arm_kill_switch(self, reason: str) -> None:
        """
        Arm the kill switch — immediately stops all execution.
        
        This is an EMERGENCY action and cannot be undone without
        manual intervention.
        """
        with self._lock:
            self._kill_switch_armed = True
            self._kill_switch_reason = reason
            self._set_status(EngineStatus.KILLED)
            self._stop_event.set()
    
    def execute_cycle(self) -> ExecutionCycle:
        """
        Execute a single test cycle.
        
        Can be called manually or automatically by the run loop.
        """
        # Check kill switch
        if self._kill_switch_armed:
            raise KillSwitchActivated(self._kill_switch_reason)
        
        cycle_id = self._generate_cycle_id()
        started_at = datetime.utcnow()
        
        cycle = ExecutionCycle(
            cycle_id=cycle_id,
            started_at=started_at,
            cci_before=self._metrics.current_cci,
        )
        
        try:
            # Simulate test execution (in production, would run actual tests)
            result = self._execute_tests()
            
            cycle.tests_executed = result["executed"]
            cycle.tests_passed = result["passed"]
            cycle.tests_failed = result["failed"]
            cycle.cci_after = result["cci"]
            cycle.result = CycleResult.SUCCESS if result["passed"] == result["executed"] else CycleResult.PARTIAL
            
        except KillSwitchActivated:
            cycle.result = CycleResult.KILLED
            cycle.error_message = "Kill switch activated"
        except Exception as e:
            cycle.result = CycleResult.FAILURE
            cycle.error_message = str(e)
        
        # Complete cycle
        cycle.completed_at = datetime.utcnow()
        cycle.duration_seconds = (cycle.completed_at - started_at).total_seconds()
        
        # Update metrics
        self._update_metrics(cycle)
        
        # Store cycle
        self._cycles.append(cycle)
        
        # Callback
        if self._on_cycle_complete:
            self._on_cycle_complete(cycle)
        
        return cycle
    
    def get_recent_cycles(self, count: int = 10) -> list[ExecutionCycle]:
        """Get most recent execution cycles."""
        return self._cycles[-count:]
    
    def get_cycle(self, cycle_id: str) -> ExecutionCycle | None:
        """Get a specific cycle by ID."""
        for cycle in self._cycles:
            if cycle.cycle_id == cycle_id:
                return cycle
        return None
    
    def set_on_cycle_complete(self, callback: Callable[[ExecutionCycle], None]) -> None:
        """Set callback for cycle completion."""
        self._on_cycle_complete = callback
    
    def set_on_status_change(self, callback: Callable[[EngineStatus], None]) -> None:
        """Set callback for status changes."""
        self._on_status_change = callback
    
    def _run_loop(self) -> None:
        """Main execution loop."""
        with self._lock:
            self._set_status(EngineStatus.RUNNING)
        
        while not self._stop_event.is_set():
            if self._status == EngineStatus.RUNNING:
                try:
                    self.execute_cycle()
                except KillSwitchActivated:
                    break
                except Exception:
                    with self._lock:
                        self._set_status(EngineStatus.ERROR)
                    break
            
            # Wait for next cycle or stop signal
            self._stop_event.wait(timeout=self.config.cycle_interval_seconds)
    
    def _execute_tests(self) -> dict[str, Any]:
        """
        Execute tests for this cycle.
        
        In production, this would invoke PyTest.
        For now, simulates execution.
        """
        # Simulation - in production would run actual tests
        import random
        
        executed = random.randint(100, 200)
        passed = int(executed * random.uniform(0.95, 1.0))
        failed = executed - passed
        cci = self._metrics.current_cci + random.uniform(-0.01, 0.05)
        
        return {
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "cci": max(0, cci),
        }
    
    def _update_metrics(self, cycle: ExecutionCycle) -> None:
        """Update engine metrics after a cycle."""
        self._metrics.total_cycles += 1
        self._metrics.total_tests_executed += cycle.tests_executed
        self._metrics.total_tests_passed += cycle.tests_passed
        self._metrics.total_runtime_seconds += cycle.duration_seconds
        self._metrics.current_cci = cycle.cci_after
        self._metrics.peak_cci = max(self._metrics.peak_cci, cycle.cci_after)
        self._metrics.last_cycle_at = cycle.completed_at
        
        if cycle.result == CycleResult.SUCCESS:
            self._metrics.successful_cycles += 1
        else:
            self._metrics.failed_cycles += 1
    
    def _set_status(self, status: EngineStatus) -> None:
        """Set status and trigger callback."""
        self._status = status
        if self._on_status_change:
            self._on_status_change(status)
    
    def _generate_cycle_id(self) -> str:
        """Generate unique cycle ID."""
        data = f"{datetime.utcnow().isoformat()}:{self._metrics.total_cycles}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]


# Module-level singleton
_engine: AlwaysOnEngine | None = None


def get_engine(config: EngineConfig | None = None) -> AlwaysOnEngine:
    """Get the singleton engine."""
    global _engine
    if _engine is None:
        _engine = AlwaysOnEngine(config)
    return _engine


def reset_engine() -> None:
    """Reset the singleton (for testing)."""
    global _engine
    if _engine and _engine.is_running:
        _engine.stop()
    _engine = None
