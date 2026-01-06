"""
Tests for Continuous Test Executor

PAC Reference: PAC-JEFFREY-P50
Agent: CODY (GID-01) — Test Generation

Tests the ContinuousExecutor, ExecutionMode, ExecutionSchedule,
ExecutionBatch, and TestResult components.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from core.occ.testing.continuous_executor import (
    ContinuousExecutor,
    ExecutionMode,
    ExecutionPriority,
    ExecutionSchedule,
    ExecutionBatch,
    TestResult,
    ExecutorError,
    ResourceLimitExceeded,
    create_standard_executor,
    create_chaos_executor,
    create_fuzz_executor,
)


class TestExecutionMode:
    """Tests for ExecutionMode enum."""
    
    def test_all_modes_exist(self):
        """Test all expected modes exist."""
        assert ExecutionMode.STANDARD.value == "STANDARD"
        assert ExecutionMode.CHAOS.value == "CHAOS"
        assert ExecutionMode.FUZZ.value == "FUZZ"
        assert ExecutionMode.MIXED.value == "MIXED"
        assert ExecutionMode.SMOKE.value == "SMOKE"
        assert ExecutionMode.FULL.value == "FULL"
    
    def test_mode_count(self):
        """Test correct number of modes."""
        assert len(ExecutionMode) == 6


class TestExecutionPriority:
    """Tests for ExecutionPriority enum."""
    
    def test_priority_ordering(self):
        """Test priority values are ordered correctly."""
        assert ExecutionPriority.CRITICAL.value < ExecutionPriority.HIGH.value
        assert ExecutionPriority.HIGH.value < ExecutionPriority.NORMAL.value
        assert ExecutionPriority.NORMAL.value < ExecutionPriority.LOW.value
        assert ExecutionPriority.LOW.value < ExecutionPriority.BACKGROUND.value


class TestExecutionSchedule:
    """Tests for ExecutionSchedule dataclass."""
    
    def test_default_schedule(self):
        """Test default schedule values."""
        schedule = ExecutionSchedule()
        
        assert schedule.mode == ExecutionMode.MIXED
        assert schedule.interval_seconds == 60
        assert schedule.priority == ExecutionPriority.NORMAL
        assert schedule.max_duration_seconds == 300
        assert schedule.enabled is True
    
    def test_custom_schedule(self):
        """Test custom schedule."""
        schedule = ExecutionSchedule(
            mode=ExecutionMode.CHAOS,
            interval_seconds=30,
            chaos_percentage=0.5,
        )
        
        assert schedule.mode == ExecutionMode.CHAOS
        assert schedule.interval_seconds == 30
        assert schedule.chaos_percentage == 0.5
    
    def test_schedule_to_dict(self):
        """Test schedule serialization."""
        schedule = ExecutionSchedule()
        result = schedule.to_dict()
        
        assert "mode" in result
        assert "interval_seconds" in result
        assert result["mode"] == "MIXED"


class TestTestResult:
    """Tests for TestResult dataclass."""
    
    def test_result_creation(self):
        """Test result creation."""
        result = TestResult(
            test_id="test123",
            test_name="test_example",
            mode=ExecutionMode.STANDARD,
            passed=True,
            duration_ms=100.5,
        )
        
        assert result.test_id == "test123"
        assert result.test_name == "test_example"
        assert result.passed is True
        assert result.duration_ms == 100.5
        assert result.error_message == ""
    
    def test_failed_result(self):
        """Test failed result with error."""
        result = TestResult(
            test_id="test456",
            test_name="test_failing",
            mode=ExecutionMode.CHAOS,
            passed=False,
            duration_ms=50.0,
            error_message="Assertion failed",
        )
        
        assert result.passed is False
        assert result.error_message == "Assertion failed"
    
    def test_result_to_dict(self):
        """Test result serialization."""
        result = TestResult(
            test_id="test",
            test_name="test_name",
            mode=ExecutionMode.FUZZ,
            passed=True,
            duration_ms=10.0,
        )
        
        data = result.to_dict()
        
        assert data["test_id"] == "test"
        assert data["mode"] == "FUZZ"
        assert data["passed"] is True


class TestExecutionBatch:
    """Tests for ExecutionBatch dataclass."""
    
    def test_batch_creation(self):
        """Test batch creation."""
        batch = ExecutionBatch(
            batch_id="batch123",
            mode=ExecutionMode.STANDARD,
            tests=["test1", "test2", "test3"],
            started_at=datetime.utcnow(),
        )
        
        assert batch.batch_id == "batch123"
        assert len(batch.tests) == 3
        assert batch.completed_at is None
    
    def test_batch_pass_count(self):
        """Test batch passed count."""
        batch = ExecutionBatch(
            batch_id="batch",
            mode=ExecutionMode.STANDARD,
            tests=["t1", "t2", "t3"],
            started_at=datetime.utcnow(),
            results=[
                TestResult("1", "t1", ExecutionMode.STANDARD, True, 10),
                TestResult("2", "t2", ExecutionMode.STANDARD, True, 10),
                TestResult("3", "t3", ExecutionMode.STANDARD, False, 10),
            ],
        )
        
        assert batch.passed_count == 2
        assert batch.failed_count == 1
    
    def test_batch_duration(self):
        """Test batch duration calculation."""
        started = datetime.utcnow()
        from datetime import timedelta
        completed = started + timedelta(seconds=30)
        
        batch = ExecutionBatch(
            batch_id="batch",
            mode=ExecutionMode.STANDARD,
            tests=[],
            started_at=started,
            completed_at=completed,
        )
        
        assert batch.duration_seconds == pytest.approx(30.0, abs=0.1)
    
    def test_batch_to_dict(self):
        """Test batch serialization."""
        batch = ExecutionBatch(
            batch_id="batch",
            mode=ExecutionMode.CHAOS,
            tests=["t1", "t2"],
            started_at=datetime.utcnow(),
        )
        
        data = batch.to_dict()
        
        assert data["batch_id"] == "batch"
        assert data["mode"] == "CHAOS"
        assert data["test_count"] == 2


class TestContinuousExecutor:
    """Tests for ContinuousExecutor class."""
    
    def test_executor_creation(self):
        """Test executor creation."""
        executor = ContinuousExecutor()
        
        assert executor.is_running is False
        assert executor.current_batch is None
    
    def test_executor_with_schedule(self):
        """Test executor with custom schedule."""
        schedule = ExecutionSchedule(mode=ExecutionMode.CHAOS)
        executor = ContinuousExecutor(schedule)
        
        assert executor.schedule.mode == ExecutionMode.CHAOS
    
    def test_execute_batch(self):
        """Test batch execution."""
        executor = ContinuousExecutor()
        tests = ["test_a", "test_b", "test_c"]
        
        batch = executor.execute_batch(tests)
        
        assert batch.batch_id is not None
        assert batch.completed_at is not None
        assert len(batch.results) == len(tests)
    
    def test_execute_batch_with_mode(self):
        """Test batch execution with specific mode."""
        executor = ContinuousExecutor()
        
        batch = executor.execute_batch(["test"], ExecutionMode.FUZZ)
        
        assert batch.mode == ExecutionMode.FUZZ
    
    def test_execute_mode(self):
        """Test execution by mode."""
        executor = ContinuousExecutor()
        
        batch = executor.execute_mode(ExecutionMode.SMOKE, max_tests=10)
        
        assert batch.mode == ExecutionMode.SMOKE
        assert len(batch.tests) == 10
    
    def test_execute_chaos_round(self):
        """Test chaos execution round."""
        executor = ContinuousExecutor()
        
        batch = executor.execute_chaos_round(intensity=0.5)
        
        assert batch.mode == ExecutionMode.CHAOS
    
    def test_execute_fuzz_round(self):
        """Test fuzz execution round."""
        executor = ContinuousExecutor()
        
        batch = executor.execute_fuzz_round(iterations=50)
        
        assert batch.mode == ExecutionMode.FUZZ
        assert len(batch.tests) == 50
    
    def test_kill_request(self):
        """Test kill request."""
        executor = ContinuousExecutor()
        executor.request_kill()
        
        with pytest.raises(ExecutorError):
            executor.execute_batch(["test"])
    
    def test_kill_reset(self):
        """Test kill reset."""
        executor = ContinuousExecutor()
        executor.request_kill()
        executor.reset_kill()
        
        # Should work after reset
        batch = executor.execute_batch(["test"])
        assert batch is not None
    
    def test_execution_history(self):
        """Test execution history retrieval."""
        executor = ContinuousExecutor()
        
        for i in range(5):
            executor.execute_batch([f"test_{i}"])
        
        history = executor.get_history(3)
        assert len(history) == 3
    
    def test_stats(self):
        """Test statistics retrieval."""
        executor = ContinuousExecutor()
        executor.execute_batch(["t1", "t2", "t3"])
        
        stats = executor.get_stats()
        
        assert stats["total_batches"] == 1
        assert stats["total_tests"] == 3
        assert "pass_rate" in stats
    
    def test_test_complete_callback(self):
        """Test callback on test completion."""
        executor = ContinuousExecutor()
        results = []
        
        executor.set_on_test_complete(lambda r: results.append(r))
        executor.execute_batch(["test"])
        
        assert len(results) == 1
    
    def test_batch_complete_callback(self):
        """Test callback on batch completion."""
        executor = ContinuousExecutor()
        batches = []
        
        executor.set_on_batch_complete(lambda b: batches.append(b))
        executor.execute_batch(["test"])
        
        assert len(batches) == 1


class TestExecutorFactories:
    """Tests for executor factory functions."""
    
    def test_create_standard_executor(self):
        """Test standard executor factory."""
        executor = create_standard_executor()
        
        assert executor.schedule.mode == ExecutionMode.STANDARD
    
    def test_create_chaos_executor(self):
        """Test chaos executor factory."""
        executor = create_chaos_executor(intensity=0.7)
        
        assert executor.schedule.mode == ExecutionMode.CHAOS
        assert executor.schedule.chaos_percentage == 0.7
    
    def test_create_fuzz_executor(self):
        """Test fuzz executor factory."""
        executor = create_fuzz_executor()
        
        assert executor.schedule.mode == ExecutionMode.FUZZ
        assert executor.schedule.fuzz_percentage == 1.0
