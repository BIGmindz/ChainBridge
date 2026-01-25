#!/usr/bin/env python3
"""
PAC-OCC-P09: Swarm Load Testing
================================
CLASSIFICATION: PERFORMANCE_VALIDATION
GOVERNANCE: FORGE (GID-04) Pipeline Stress + BENSON (GID-00)

Validates AsyncSwarmDispatcher under high-load conditions:
- 50+ concurrent agent tasks
- <50ms scheduling overhead requirement
- <1.5s total test duration
- Zero race conditions
- IV-01 and IV-02 invariant enforcement

Author: Forge (GID-04) - Pipeline Stress
Orchestrator: Benson (GID-00)
"""

import pytest
import asyncio
import time
from typing import List

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.orchestration.dispatcher import (
    AsyncSwarmDispatcher,
    AgentTask,
    SharedLedger,
    DispatchStatus,
    AgentTaskStatus,
    create_mock_agent_task
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST IV-01: CONSERVATION OF IDENTITY
# ═══════════════════════════════════════════════════════════════════════════

class TestIV01_IdentityPreservation:
    """
    IV-01: Agent GID must persist across async context switches.
    """
    
    @pytest.mark.asyncio
    async def test_single_agent_identity_preserved(self):
        """IV-01: Single agent GID remains unchanged after async execution."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=1)
        
        task = await create_mock_agent_task(gid="GID-TEST-001", task_id="task-001")
        
        await dispatcher.dispatch_tasks([task])
        
        completed = dispatcher.get_completed_tasks()
        assert len(completed) == 1
        assert completed[0].gid == "GID-TEST-001"
        assert completed[0].status == AgentTaskStatus.COMPLETED
        assert dispatcher.metrics.identity_preservation_violations == 0
    
    @pytest.mark.asyncio
    async def test_multiple_agents_identity_preserved(self):
        """IV-01: All agent GIDs preserved across parallel execution."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=10)
        
        # Create 10 agents with unique GIDs
        tasks = [
            await create_mock_agent_task(gid=f"GID-{i:03d}", task_id=f"task-{i:03d}")
            for i in range(10)
        ]
        
        await dispatcher.dispatch_tasks(tasks)
        
        completed = dispatcher.get_completed_tasks()
        assert len(completed) == 10
        
        # Verify all GIDs match original
        for i, task in enumerate(completed):
            assert task.gid == f"GID-{i:03d}"
        
        assert dispatcher.metrics.identity_preservation_violations == 0


# ═══════════════════════════════════════════════════════════════════════════
# TEST IV-02: ATOMIC WRITE ACCESS
# ═══════════════════════════════════════════════════════════════════════════

class TestIV02_AtomicWrites:
    """
    IV-02: Only one agent writes to Ledger at a time.
    """
    
    @pytest.mark.asyncio
    async def test_shared_ledger_atomic_writes(self):
        """IV-02: Shared ledger enforces atomic writes via semaphore."""
        ledger = SharedLedger()
        
        async def writer_task(agent_gid: str, count: int):
            for i in range(count):
                await ledger.append({
                    'agent_gid': agent_gid,
                    'entry_id': f'{agent_gid}-{i}'
                })
        
        # Spawn 5 concurrent writers, 10 writes each
        tasks = [
            asyncio.create_task(writer_task(f"GID-{i:02d}", 10))
            for i in range(5)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all 50 writes recorded
        all_entries = ledger.read_all()
        assert len(all_entries) == 50
        assert ledger.get_write_count() == 50
        
        # Verify write indices are sequential (atomic writes)
        write_indices = [entry['write_index'] for entry in all_entries]
        assert write_indices == list(range(50))
    
    @pytest.mark.asyncio
    async def test_ledger_missing_gid_raises_error(self):
        """IV-02: Ledger rejects entries missing 'agent_gid' field."""
        ledger = SharedLedger()
        
        with pytest.raises(ValueError, match="missing 'agent_gid'"):
            await ledger.append({'data': 'invalid_entry'})


# ═══════════════════════════════════════════════════════════════════════════
# TEST SWARM LOAD (50+ AGENTS)
# ═══════════════════════════════════════════════════════════════════════════

class TestSwarmLoad:
    """
    Swarm load testing with 50+ concurrent agents.
    
    Requirements:
    - <50ms scheduling overhead
    - <1.5s total test duration
    - 100% task completion rate
    """
    
    @pytest.mark.asyncio
    async def test_50_agent_swarm_load(self):
        """Load test: 50 agents with <50ms scheduling overhead."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=50)
        
        # Create 50 agent tasks (10ms work each)
        tasks = [
            await create_mock_agent_task(
                gid=f"GID-SWARM-{i:03d}",
                task_id=f"swarm-task-{i:03d}",
                work_duration_ms=10.0
            )
            for i in range(50)
        ]
        
        test_start = time.perf_counter()
        metrics = await dispatcher.dispatch_tasks(tasks)
        test_duration = (time.perf_counter() - test_start) * 1000
        
        # Verify all tasks completed
        assert metrics.completed_tasks == 50
        assert metrics.failed_tasks == 0
        
        # Verify <50ms scheduling overhead
        assert metrics.total_scheduling_overhead_ms < 50.0, \
            f"Scheduling overhead {metrics.total_scheduling_overhead_ms:.2f}ms exceeds 50ms limit"
        
        # Verify <1.5s total duration
        assert test_duration < 1500.0, \
            f"Test duration {test_duration:.2f}ms exceeds 1500ms limit"
        
        # Verify concurrent execution
        assert metrics.concurrent_peak >= 10, \
            f"Peak concurrency {metrics.concurrent_peak} too low (expected >=10)"
    
    @pytest.mark.asyncio
    async def test_100_agent_swarm_stress(self):
        """Stress test: 100 agents with <100ms scheduling overhead."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=100)
        
        tasks = [
            await create_mock_agent_task(
                gid=f"GID-STRESS-{i:04d}",
                task_id=f"stress-task-{i:04d}",
                work_duration_ms=5.0
            )
            for i in range(100)
        ]
        
        metrics = await dispatcher.dispatch_tasks(tasks)
        
        assert metrics.completed_tasks == 100
        assert metrics.failed_tasks == 0
        assert metrics.total_scheduling_overhead_ms < 100.0


# ═══════════════════════════════════════════════════════════════════════════
# TEST ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """
    Fail-closed behavior and exception handling.
    """
    
    @pytest.mark.asyncio
    async def test_task_exception_propagates(self):
        """TaskGroup propagates exceptions in fail-fast mode."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=5)
        
        async def failing_task():
            raise RuntimeError("Task failure simulation")
        
        tasks = [
            AgentTask(
                gid="GID-FAIL-001",
                task_id="fail-task-001",
                task_fn=failing_task
            )
        ]
        
        with pytest.raises(RuntimeError, match="Task failure simulation"):
            await dispatcher.dispatch_tasks(tasks, fail_fast=True)
        
        assert dispatcher.status == DispatchStatus.ERROR
        assert dispatcher.metrics.failed_tasks == 1
    
    @pytest.mark.asyncio
    async def test_no_tasks_handled_gracefully(self):
        """Dispatcher handles empty task list gracefully."""
        dispatcher = AsyncSwarmDispatcher()
        
        metrics = await dispatcher.dispatch_tasks([])
        
        assert metrics.total_tasks == 0
        assert dispatcher.status == DispatchStatus.IDLE


# ═══════════════════════════════════════════════════════════════════════════
# TEST PERFORMANCE METRICS
# ═══════════════════════════════════════════════════════════════════════════

class TestPerformanceMetrics:
    """
    Metrics tracking and reporting.
    """
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Verify metrics are accurately tracked."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=5)
        
        tasks = [
            await create_mock_agent_task(
                gid=f"GID-METRIC-{i:02d}",
                task_id=f"metric-task-{i:02d}",
                work_duration_ms=50.0
            )
            for i in range(5)
        ]
        
        metrics = await dispatcher.dispatch_tasks(tasks)
        
        # Verify counts
        assert metrics.total_tasks == 5
        assert metrics.completed_tasks == 5
        assert metrics.failed_tasks == 0
        
        # Verify duration metrics
        assert metrics.avg_task_duration_ms > 0
        assert metrics.min_task_duration_ms <= metrics.avg_task_duration_ms
        assert metrics.avg_task_duration_ms <= metrics.max_task_duration_ms
        
        # Verify concurrent peak
        assert metrics.concurrent_peak >= 1
        assert metrics.concurrent_peak <= 5
    
    @pytest.mark.asyncio
    async def test_task_duration_tracking(self):
        """Verify individual task durations are tracked."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=3)
        
        tasks = [
            await create_mock_agent_task(
                gid="GID-DUR-001",
                task_id="dur-task-001",
                work_duration_ms=100.0
            )
        ]
        
        await dispatcher.dispatch_tasks(tasks)
        
        completed = dispatcher.get_completed_tasks()
        assert len(completed) == 1
        assert completed[0].duration_ms >= 100.0  # Account for overhead
        assert completed[0].duration_ms < 200.0   # Should not be 2x


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TEST
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """
    End-to-end integration tests.
    """
    
    @pytest.mark.asyncio
    async def test_full_dispatch_lifecycle(self):
        """Complete dispatch lifecycle: create → execute → verify."""
        dispatcher = AsyncSwarmDispatcher(max_concurrent=10)
        
        # Create diverse task set
        tasks = [
            await create_mock_agent_task(
                gid=f"GID-FULL-{i:02d}",
                task_id=f"full-task-{i:02d}",
                work_duration_ms=20.0
            )
            for i in range(20)
        ]
        
        # Dispatch
        initial_status = dispatcher.status
        assert initial_status == DispatchStatus.IDLE
        
        metrics = await dispatcher.dispatch_tasks(tasks)
        
        final_status = dispatcher.status
        assert final_status == DispatchStatus.COMPLETED
        
        # Verify results
        assert metrics.completed_tasks == 20
        assert metrics.failed_tasks == 0
        assert dispatcher.metrics.identity_preservation_violations == 0
        
        # Verify all tasks have results
        completed = dispatcher.get_completed_tasks()
        for task in completed:
            assert task.result is not None
            assert 'agent_gid' in task.result
            assert task.result['agent_gid'] == task.gid
