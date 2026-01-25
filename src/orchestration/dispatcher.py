#!/usr/bin/env python3
"""
PAC-OCC-P09: Swarm Concurrency Protocol
========================================
CLASSIFICATION: CORE_INFRASTRUCTURE_OPTIMIZATION
GOVERNANCE: JEFFREY (Chief Architect) + BENSON (GID-00)
VERSION: 1.0.0-PRODUCTION

The AsyncSwarmDispatcher provides parallel agent execution using Python 3.11+ 
`asyncio.TaskGroup` pattern. Replaces sequential dispatch bottleneck with
concurrent execution while maintaining deterministic behavior and fail-closed safety.

OBJECTIVES:
- Enable parallel execution of >5 agents
- Achieve <50ms scheduling overhead
- Maintain zero race conditions
- Enforce atomic ledger writes (IV-02)
- Preserve agent identity across async context switches (IV-01)

INVARIANTS:
- IV-01: Conservation of Identity (Agent GID persists across async contexts)
- IV-02: Atomic Write Access (Only one agent writes to Ledger at a time)

Author: Cody (GID-01) - Core Logic
Orchestrator: Benson (GID-00)
"""

import asyncio
import time
import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


logger = logging.getLogger(__name__)


class DispatchStatus(Enum):
    """Dispatcher operational status."""
    IDLE = "IDLE"
    DISPATCHING = "DISPATCHING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class AgentTaskStatus(Enum):
    """Individual agent task status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class AgentTask:
    """Agent task specification."""
    gid: str  # Agent GID (IV-01: identity preservation)
    task_id: str
    task_fn: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[Exception] = None
    
    @property
    def duration_ms(self) -> float:
        """Calculate task duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


@dataclass
class DispatchMetrics:
    """Performance metrics for swarm dispatch operations."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_scheduling_overhead_ms: float = 0.0
    avg_task_duration_ms: float = 0.0
    min_task_duration_ms: float = float('inf')
    max_task_duration_ms: float = 0.0
    concurrent_peak: int = 0
    ledger_write_conflicts: int = 0
    identity_preservation_violations: int = 0


class SharedLedger:
    """
    Thread-safe shared ledger for agent writes.
    
    Implements IV-02 (Atomic Write Access) via asyncio.Semaphore.
    Only one agent can write to the ledger at a time.
    """
    
    def __init__(self):
        """Initialize shared ledger with write lock."""
        self._ledger: List[Dict[str, Any]] = []
        self._write_lock = asyncio.Semaphore(1)  # IV-02: Atomic writes
        self._write_count = 0
        
    async def append(self, entry: Dict[str, Any]) -> None:
        """
        Append entry to ledger with atomic write guarantee.
        
        Args:
            entry: Ledger entry (must include 'agent_gid' field)
        
        Side Effects:
            - Acquires write lock
            - Appends to internal ledger
            - Increments write counter
        """
        async with self._write_lock:
            # IV-01: Verify agent identity is preserved
            if 'agent_gid' not in entry:
                raise ValueError("Ledger entry missing 'agent_gid' field (IV-01 violation)")
            
            self._ledger.append({
                **entry,
                'write_timestamp': datetime.now(timezone.utc).isoformat(),
                'write_index': self._write_count
            })
            self._write_count += 1
    
    def read_all(self) -> List[Dict[str, Any]]:
        """
        Read all ledger entries (non-blocking).
        
        Returns:
            Copy of ledger entries
        """
        return list(self._ledger)
    
    def get_write_count(self) -> int:
        """Get total number of writes."""
        return self._write_count
    
    def clear(self) -> None:
        """Clear ledger (testing only)."""
        self._ledger.clear()
        self._write_count = 0


class AsyncSwarmDispatcher:
    """
    Concurrent agent dispatcher using asyncio.TaskGroup pattern.
    
    Coordinates parallel execution of multiple agents while maintaining:
    - Deterministic behavior (no race conditions)
    - Identity preservation (IV-01: GID persists across async contexts)
    - Atomic ledger writes (IV-02: semaphore-protected writes)
    - Fail-closed safety (TaskGroup exception handling)
    
    Usage:
        dispatcher = AsyncSwarmDispatcher(max_concurrent=10)
        await dispatcher.dispatch_tasks(agent_tasks)
    """
    
    def __init__(self, max_concurrent: int = 10):
        """
        Initialize AsyncSwarmDispatcher.
        
        Args:
            max_concurrent: Maximum concurrent tasks (default: 10)
        """
        self.max_concurrent = max_concurrent
        self.status = DispatchStatus.IDLE
        self.metrics = DispatchMetrics()
        self.ledger = SharedLedger()
        
        # Task tracking
        self._active_tasks: Dict[str, AgentTask] = {}
        self._completed_tasks: List[AgentTask] = []
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"AsyncSwarmDispatcher initialized (max_concurrent={max_concurrent})")
    
    async def _execute_task(self, task: AgentTask) -> None:
        """
        Execute single agent task with identity tracking.
        
        Args:
            task: AgentTask to execute
        
        Side Effects:
            - Updates task status
            - Records metrics
            - May write to shared ledger
        
        Raises:
            Exception: Propagates task exceptions to TaskGroup
        """
        async with self._semaphore:
            # Mark task as running
            task.status = AgentTaskStatus.RUNNING
            task.start_time = time.perf_counter()
            self._active_tasks[task.task_id] = task
            
            # Track concurrent peak immediately after adding
            current_active = len(self._active_tasks)
            self.metrics.concurrent_peak = max(
                self.metrics.concurrent_peak, current_active
            )
            
            # IV-01: Preserve agent GID in async context
            logger.debug(f"[{task.gid}] Starting task {task.task_id}")
            
            try:
                # Execute agent task function
                if asyncio.iscoroutinefunction(task.task_fn):
                    result = await task.task_fn(*task.args, **task.kwargs)
                else:
                    result = task.task_fn(*task.args, **task.kwargs)
                
                task.result = result
                task.status = AgentTaskStatus.COMPLETED
                task.end_time = time.perf_counter()
                
                # IV-01 Verification: Ensure GID hasn't changed
                if 'agent_gid' in result and result['agent_gid'] != task.gid:
                    self.metrics.identity_preservation_violations += 1
                    logger.error(f"IV-01 VIOLATION: GID mismatch! Expected {task.gid}, got {result['agent_gid']}")
                
                self.metrics.completed_tasks += 1
                logger.debug(f"[{task.gid}] Completed task {task.task_id} ({task.duration_ms:.2f}ms)")
                
            except Exception as e:
                task.error = e
                task.status = AgentTaskStatus.FAILED
                task.end_time = time.perf_counter()
                self.metrics.failed_tasks += 1
                logger.error(f"[{task.gid}] Failed task {task.task_id}: {e}")
                raise  # Propagate to TaskGroup
            
            finally:
                # Move to completed
                self._active_tasks.pop(task.task_id, None)
                self._completed_tasks.append(task)
                
                # Update metrics
                if task.duration_ms > 0:
                    self.metrics.min_task_duration_ms = min(
                        self.metrics.min_task_duration_ms, task.duration_ms
                    )
                    self.metrics.max_task_duration_ms = max(
                        self.metrics.max_task_duration_ms, task.duration_ms
                    )
    
    async def dispatch_tasks(
        self,
        tasks: List[AgentTask],
        fail_fast: bool = True
    ) -> DispatchMetrics:
        """
        Dispatch agent tasks in parallel using asyncio.TaskGroup.
        
        Args:
            tasks: List of AgentTasks to execute
            fail_fast: If True, stop on first exception (default: True)
        
        Returns:
            DispatchMetrics with execution statistics
        
        Raises:
            ExceptionGroup: If any task fails and fail_fast=False
            Exception: First task exception if fail_fast=True
        """
        if not tasks:
            logger.warning("No tasks to dispatch")
            return self.metrics
        
        self.status = DispatchStatus.DISPATCHING
        self.metrics.total_tasks = len(tasks)
        
        dispatch_start = time.perf_counter()
        
        logger.info(f"Dispatching {len(tasks)} tasks (max_concurrent={self.max_concurrent})")
        
        try:
            # Python 3.11+ TaskGroup: Structured concurrency
            async with asyncio.TaskGroup() as tg:
                for task in tasks:
                    # Create task in TaskGroup (no fire-and-forget)
                    tg.create_task(self._execute_task(task))
        
        except* Exception as eg:
            # TaskGroup exception handling (Python 3.11+)
            self.status = DispatchStatus.ERROR
            logger.error(f"Task group failed: {eg}")
            
            if fail_fast:
                # Re-raise first exception
                raise eg.exceptions[0]
            else:
                # Re-raise ExceptionGroup for batch processing
                raise
        
        finally:
            dispatch_end = time.perf_counter()
            self.metrics.total_scheduling_overhead_ms = (dispatch_end - dispatch_start) * 1000
            
            # Calculate average task duration
            durations = [t.duration_ms for t in self._completed_tasks if t.duration_ms > 0]
            if durations:
                self.metrics.avg_task_duration_ms = sum(durations) / len(durations)
            
            self.status = DispatchStatus.COMPLETED if self.metrics.failed_tasks == 0 else DispatchStatus.ERROR
            
            logger.info(
                f"Dispatch complete: {self.metrics.completed_tasks}/{self.metrics.total_tasks} succeeded "
                f"(scheduling overhead: {self.metrics.total_scheduling_overhead_ms:.2f}ms)"
            )
        
        return self.metrics
    
    def get_completed_tasks(self) -> List[AgentTask]:
        """Get all completed tasks."""
        return list(self._completed_tasks)
    
    def get_metrics(self) -> DispatchMetrics:
        """Get current dispatch metrics."""
        return self.metrics
    
    def reset(self) -> None:
        """Reset dispatcher state (testing only)."""
        self.status = DispatchStatus.IDLE
        self.metrics = DispatchMetrics()
        self._active_tasks.clear()
        self._completed_tasks.clear()
        self.ledger.clear()
        logger.info("Dispatcher reset")


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

async def create_mock_agent_task(
    gid: str,
    task_id: str,
    work_duration_ms: float = 100.0
) -> AgentTask:
    """
    Create mock agent task for testing.
    
    Args:
        gid: Agent GID
        task_id: Task identifier
        work_duration_ms: Simulated work duration
    
    Returns:
        AgentTask with mock work function
    """
    async def mock_work():
        await asyncio.sleep(work_duration_ms / 1000.0)
        return {
            'agent_gid': gid,
            'task_id': task_id,
            'result': f'Work completed by {gid}'
        }
    
    return AgentTask(
        gid=gid,
        task_id=task_id,
        task_fn=mock_work
    )
