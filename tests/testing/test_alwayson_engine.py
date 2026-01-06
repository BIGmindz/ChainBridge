"""
Tests for Always-On Test Engine Core

PAC Reference: PAC-JEFFREY-P50
Agent: CODY (GID-01) — Test Generation

Tests the AlwaysOnEngine, EngineConfig, EngineStatus,
ExecutionCycle, and EngineMetrics components.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import threading
import time

from core.occ.testing.engine import (
    AlwaysOnEngine,
    EngineConfig,
    EngineStatus,
    EngineMetrics,
    ExecutionCycle,
    CycleResult,
    EngineError,
    KillSwitchActivated,
    get_engine,
    reset_engine,
)


class TestEngineConfig:
    """Tests for EngineConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = EngineConfig()
        
        assert config.cycle_interval_seconds == 60
        assert config.max_parallel_tests == 10
        assert config.test_timeout_seconds == 300
        assert config.cci_threshold == 1.0
        assert config.cci_fail_on_decrease is True
        assert config.enable_kill_switch is True
        assert config.kill_switch_timeout_seconds == 5
        assert config.max_memory_mb == 2048
        assert config.max_cpu_percent == 80.0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = EngineConfig(
            cycle_interval_seconds=30,
            max_parallel_tests=20,
            cci_threshold=1.5,
        )
        
        assert config.cycle_interval_seconds == 30
        assert config.max_parallel_tests == 20
        assert config.cci_threshold == 1.5
    
    def test_config_to_dict(self):
        """Test config serialization."""
        config = EngineConfig()
        result = config.to_dict()
        
        assert "cycle_interval_seconds" in result
        assert "max_parallel_tests" in result
        assert "enable_kill_switch" in result
        assert isinstance(result, dict)


class TestEngineStatus:
    """Tests for EngineStatus enum."""
    
    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert EngineStatus.STOPPED.value == "STOPPED"
        assert EngineStatus.STARTING.value == "STARTING"
        assert EngineStatus.RUNNING.value == "RUNNING"
        assert EngineStatus.PAUSED.value == "PAUSED"
        assert EngineStatus.STOPPING.value == "STOPPING"
        assert EngineStatus.ERROR.value == "ERROR"
        assert EngineStatus.KILLED.value == "KILLED"
    
    def test_status_values_unique(self):
        """Test all status values are unique."""
        values = [s.value for s in EngineStatus]
        assert len(values) == len(set(values))


class TestCycleResult:
    """Tests for CycleResult enum."""
    
    def test_all_results_exist(self):
        """Test all expected results exist."""
        assert CycleResult.SUCCESS.value == "SUCCESS"
        assert CycleResult.PARTIAL.value == "PARTIAL"
        assert CycleResult.FAILURE.value == "FAILURE"
        assert CycleResult.ABORTED.value == "ABORTED"
        assert CycleResult.KILLED.value == "KILLED"


class TestExecutionCycle:
    """Tests for ExecutionCycle dataclass."""
    
    def test_cycle_creation(self):
        """Test cycle creation."""
        started = datetime.utcnow()
        cycle = ExecutionCycle(
            cycle_id="test123",
            started_at=started,
        )
        
        assert cycle.cycle_id == "test123"
        assert cycle.started_at == started
        assert cycle.completed_at is None
        assert cycle.result == CycleResult.SUCCESS
    
    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        cycle = ExecutionCycle(
            cycle_id="test",
            started_at=datetime.utcnow(),
            tests_executed=100,
            tests_passed=95,
            tests_failed=5,
        )
        
        assert cycle.pass_rate == 95.0
    
    def test_pass_rate_zero_tests(self):
        """Test pass rate with no tests."""
        cycle = ExecutionCycle(
            cycle_id="test",
            started_at=datetime.utcnow(),
            tests_executed=0,
        )
        
        assert cycle.pass_rate == 0.0
    
    def test_cci_delta_calculation(self):
        """Test CCI delta calculation."""
        cycle = ExecutionCycle(
            cycle_id="test",
            started_at=datetime.utcnow(),
            cci_before=1.0,
            cci_after=1.1,
        )
        
        assert cycle.cci_delta == pytest.approx(0.1)
    
    def test_cycle_to_dict(self):
        """Test cycle serialization."""
        started = datetime.utcnow()
        completed = started + timedelta(seconds=30)
        
        cycle = ExecutionCycle(
            cycle_id="test",
            started_at=started,
            completed_at=completed,
            tests_executed=100,
            tests_passed=95,
            tests_failed=5,
            duration_seconds=30.0,
        )
        
        result = cycle.to_dict()
        
        assert result["cycle_id"] == "test"
        assert result["tests_executed"] == 100
        assert result["pass_rate"] == 95.0
        assert isinstance(result["started_at"], str)


class TestEngineMetrics:
    """Tests for EngineMetrics dataclass."""
    
    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = EngineMetrics()
        
        assert metrics.total_cycles == 0
        assert metrics.successful_cycles == 0
        assert metrics.current_cci == 0.0
        assert metrics.last_cycle_at is None
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = EngineMetrics(
            total_cycles=100,
            successful_cycles=90,
        )
        
        assert metrics.success_rate == 90.0
    
    def test_success_rate_zero_cycles(self):
        """Test success rate with no cycles."""
        metrics = EngineMetrics(total_cycles=0)
        assert metrics.success_rate == 0.0
    
    def test_overall_pass_rate(self):
        """Test overall pass rate calculation."""
        metrics = EngineMetrics(
            total_tests_executed=1000,
            total_tests_passed=950,
        )
        
        assert metrics.overall_pass_rate == 95.0
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = EngineMetrics(
            total_cycles=10,
            current_cci=1.5,
        )
        
        result = metrics.to_dict()
        
        assert result["total_cycles"] == 10
        assert result["current_cci"] == 1.5


class TestAlwaysOnEngine:
    """Tests for AlwaysOnEngine class."""
    
    def setup_method(self):
        """Reset singleton between tests."""
        reset_engine()
    
    def test_engine_creation(self):
        """Test engine creation."""
        engine = AlwaysOnEngine()
        
        assert engine.status == EngineStatus.STOPPED
        assert engine.is_running is False
        assert engine.kill_switch_armed is False
    
    def test_engine_with_custom_config(self):
        """Test engine with custom configuration."""
        config = EngineConfig(cycle_interval_seconds=30)
        engine = AlwaysOnEngine(config)
        
        assert engine.config.cycle_interval_seconds == 30
    
    def test_engine_start_stop(self):
        """Test engine start and stop."""
        engine = AlwaysOnEngine()
        
        # Start
        result = engine.start()
        assert result is True
        time.sleep(0.1)  # Allow thread to start
        assert engine.status == EngineStatus.RUNNING
        
        # Stop
        result = engine.stop()
        assert result is True
        assert engine.status == EngineStatus.STOPPED
    
    def test_engine_double_start(self):
        """Test starting already running engine."""
        engine = AlwaysOnEngine()
        
        engine.start()
        time.sleep(0.1)
        
        # Second start should fail
        result = engine.start()
        assert result is False
        
        engine.stop()
    
    def test_engine_pause_resume(self):
        """Test pause and resume."""
        engine = AlwaysOnEngine()
        engine.start()
        time.sleep(0.1)
        
        # Pause
        result = engine.pause()
        assert result is True
        assert engine.status == EngineStatus.PAUSED
        
        # Resume
        result = engine.resume()
        assert result is True
        assert engine.status == EngineStatus.RUNNING
        
        engine.stop()
    
    def test_kill_switch(self):
        """Test kill switch activation."""
        engine = AlwaysOnEngine()
        engine.start()
        time.sleep(0.1)
        
        # Arm kill switch
        engine.arm_kill_switch("Emergency stop")
        
        assert engine.kill_switch_armed is True
        assert engine.status == EngineStatus.KILLED
    
    def test_start_blocked_after_kill_switch(self):
        """Test that start is blocked after kill switch."""
        engine = AlwaysOnEngine()
        engine.arm_kill_switch("Test")
        
        result = engine.start()
        assert result is False
    
    def test_execute_cycle(self):
        """Test manual cycle execution."""
        engine = AlwaysOnEngine()
        
        cycle = engine.execute_cycle()
        
        assert cycle.cycle_id is not None
        assert cycle.completed_at is not None
        assert cycle.tests_executed > 0
    
    def test_execute_cycle_blocked_by_kill_switch(self):
        """Test cycle execution blocked by kill switch."""
        engine = AlwaysOnEngine()
        engine.arm_kill_switch("Test")
        
        with pytest.raises(KillSwitchActivated):
            engine.execute_cycle()
    
    def test_metrics_update_after_cycle(self):
        """Test metrics update after cycle."""
        engine = AlwaysOnEngine()
        
        engine.execute_cycle()
        
        assert engine.metrics.total_cycles == 1
        assert engine.metrics.last_cycle_at is not None
    
    def test_get_recent_cycles(self):
        """Test retrieving recent cycles."""
        engine = AlwaysOnEngine()
        
        for _ in range(5):
            engine.execute_cycle()
        
        cycles = engine.get_recent_cycles(3)
        assert len(cycles) == 3
    
    def test_get_cycle_by_id(self):
        """Test retrieving cycle by ID."""
        engine = AlwaysOnEngine()
        
        cycle = engine.execute_cycle()
        
        retrieved = engine.get_cycle(cycle.cycle_id)
        assert retrieved is not None
        assert retrieved.cycle_id == cycle.cycle_id
    
    def test_status_change_callback(self):
        """Test status change callback."""
        engine = AlwaysOnEngine()
        statuses = []
        
        engine.set_on_status_change(lambda s: statuses.append(s))
        
        engine.start()
        time.sleep(0.1)
        engine.stop()
        
        assert EngineStatus.STARTING in statuses or EngineStatus.RUNNING in statuses
    
    def test_cycle_complete_callback(self):
        """Test cycle complete callback."""
        engine = AlwaysOnEngine()
        cycles = []
        
        engine.set_on_cycle_complete(lambda c: cycles.append(c))
        
        engine.execute_cycle()
        
        assert len(cycles) == 1


class TestEngineSingleton:
    """Tests for engine singleton functions."""
    
    def setup_method(self):
        reset_engine()
    
    def test_get_engine_singleton(self):
        """Test singleton pattern."""
        engine1 = get_engine()
        engine2 = get_engine()
        
        assert engine1 is engine2
    
    def test_get_engine_with_config(self):
        """Test singleton with config."""
        config = EngineConfig(cycle_interval_seconds=30)
        engine = get_engine(config)
        
        assert engine.config.cycle_interval_seconds == 30
    
    def test_reset_engine(self):
        """Test engine reset."""
        engine1 = get_engine()
        reset_engine()
        engine2 = get_engine()
        
        assert engine1 is not engine2
