"""
GIE Execution Planner v1

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
Agent: GID-01 (Cody) — Backend / GIE Core

REAL WORK MODE — Production-grade deterministic multi-agent DAG planner.

Features:
- Deterministic execution ordering
- Fan-out / fan-in patterns
- Barrier synchronization
- Parallel lane detection
- Critical path calculation
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class TaskState(Enum):
    """State of a task in the execution plan."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class PlanPhase(Enum):
    """Phase of execution plan."""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DependencyType(Enum):
    """Type of dependency between tasks."""
    FINISH_TO_START = "FINISH_TO_START"   # B starts after A finishes (default)
    START_TO_START = "START_TO_START"     # B starts when A starts
    FINISH_TO_FINISH = "FINISH_TO_FINISH" # B finishes when A finishes
    BARRIER = "BARRIER"                    # All tasks must complete before barrier


class LaneType(Enum):
    """Type of execution lane."""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    BARRIER = "BARRIER"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class PlannerError(Exception):
    """Base exception for planner operations."""
    pass


class CyclicDependencyError(PlannerError):
    """Raised when cycle detected in task graph."""
    pass


class InvalidDependencyError(PlannerError):
    """Raised when dependency references unknown task."""
    pass


class PlanValidationError(PlannerError):
    """Raised when plan fails validation."""
    pass


class ExecutionError(PlannerError):
    """Raised when execution fails."""
    pass


class BarrierTimeoutError(PlannerError):
    """Raised when barrier wait times out."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TaskDefinition:
    """
    Definition of a task in the execution plan.
    
    Immutable after creation.
    """
    task_id: str
    agent_gid: str
    name: str
    description: str = ""
    estimated_duration_ms: int = 1000
    priority: int = 0  # Higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.task_id)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaskDefinition):
            return False
        return self.task_id == other.task_id


@dataclass
class Dependency:
    """
    A dependency between two tasks.
    """
    from_task_id: str
    to_task_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_ms: int = 0  # Delay after dependency satisfied
    
    def __hash__(self) -> int:
        return hash((self.from_task_id, self.to_task_id, self.dependency_type))


@dataclass
class Barrier:
    """
    A synchronization barrier requiring multiple tasks to complete.
    """
    barrier_id: str
    name: str
    required_tasks: FrozenSet[str]
    successor_tasks: FrozenSet[str] = frozenset()
    timeout_ms: int = 30000
    
    def __hash__(self) -> int:
        return hash(self.barrier_id)


@dataclass
class ExecutionLevel:
    """
    A level of tasks that can execute in parallel.
    """
    level: int
    task_ids: List[str]
    is_barrier: bool = False
    barrier_id: Optional[str] = None


@dataclass
class TaskExecution:
    """
    Runtime state of a task execution.
    """
    task: TaskDefinition
    state: TaskState = TaskState.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0


@dataclass
class PlanMetrics:
    """
    Metrics for an execution plan.
    """
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    total_levels: int = 0
    critical_path_length: int = 0
    critical_path_duration_ms: int = 0
    parallelism_factor: float = 0.0
    elapsed_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION PLAN
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionPlan:
    """
    A deterministic multi-agent execution plan.
    
    Supports:
    - Fan-out: One task triggers multiple parallel tasks
    - Fan-in: Multiple tasks converge to one
    - Barriers: Synchronization points
    - Critical path analysis
    """

    def __init__(self, plan_id: str, pac_id: str):
        """Initialize execution plan."""
        self._plan_id = plan_id
        self._pac_id = pac_id
        self._phase = PlanPhase.DRAFT
        self._created_at = datetime.utcnow().isoformat() + "Z"
        
        # Task registry
        self._tasks: Dict[str, TaskDefinition] = {}
        self._task_states: Dict[str, TaskExecution] = {}
        
        # Dependencies
        self._dependencies: List[Dependency] = []
        self._successors: Dict[str, Set[str]] = defaultdict(set)
        self._predecessors: Dict[str, Set[str]] = defaultdict(set)
        
        # Barriers
        self._barriers: Dict[str, Barrier] = {}
        
        # Execution levels (computed after validation)
        self._levels: List[ExecutionLevel] = []
        
        # Critical path
        self._critical_path: List[str] = []
        
        # Thread safety
        self._lock = threading.RLock()

    # ─────────────────────────────────────────────────────────────────────────
    # Properties
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def plan_id(self) -> str:
        return self._plan_id

    @property
    def pac_id(self) -> str:
        return self._pac_id

    @property
    def phase(self) -> PlanPhase:
        return self._phase

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def level_count(self) -> int:
        return len(self._levels)

    @property
    def critical_path(self) -> List[str]:
        return list(self._critical_path)

    # ─────────────────────────────────────────────────────────────────────────
    # Task Management
    # ─────────────────────────────────────────────────────────────────────────

    def add_task(self, task: TaskDefinition) -> None:
        """
        Add a task to the plan.
        
        Must be in DRAFT phase.
        """
        with self._lock:
            if self._phase != PlanPhase.DRAFT:
                raise PlannerError(f"Cannot add tasks in {self._phase.value} phase")
            
            if task.task_id in self._tasks:
                raise PlannerError(f"Task {task.task_id} already exists")
            
            self._tasks[task.task_id] = task
            self._task_states[task.task_id] = TaskExecution(task=task)

    def add_tasks(self, tasks: List[TaskDefinition]) -> None:
        """Add multiple tasks."""
        for task in tasks:
            self.add_task(task)

    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[TaskDefinition]:
        """List all tasks."""
        return list(self._tasks.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Dependency Management
    # ─────────────────────────────────────────────────────────────────────────

    def add_dependency(
        self,
        from_task_id: str,
        to_task_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_ms: int = 0,
    ) -> None:
        """
        Add a dependency: to_task depends on from_task.
        
        The to_task will not start until from_task completes (FINISH_TO_START).
        """
        with self._lock:
            if self._phase != PlanPhase.DRAFT:
                raise PlannerError(f"Cannot add dependencies in {self._phase.value} phase")
            
            dep = Dependency(
                from_task_id=from_task_id,
                to_task_id=to_task_id,
                dependency_type=dependency_type,
                lag_ms=lag_ms,
            )
            
            self._dependencies.append(dep)
            self._successors[from_task_id].add(to_task_id)
            self._predecessors[to_task_id].add(from_task_id)

    def add_fan_out(self, source_task_id: str, target_task_ids: List[str]) -> None:
        """
        Add fan-out: source triggers multiple targets in parallel.
        """
        for target_id in target_task_ids:
            self.add_dependency(source_task_id, target_id)

    def add_fan_in(self, source_task_ids: List[str], target_task_id: str) -> None:
        """
        Add fan-in: target waits for all sources.
        """
        for source_id in source_task_ids:
            self.add_dependency(source_id, target_task_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Barrier Management
    # ─────────────────────────────────────────────────────────────────────────

    def add_barrier(
        self,
        barrier_id: str,
        name: str,
        required_tasks: List[str],
        successor_tasks: Optional[List[str]] = None,
        timeout_ms: int = 30000,
    ) -> None:
        """
        Add a barrier synchronization point.
        
        All required_tasks must complete before any successor_tasks can start.
        """
        with self._lock:
            if self._phase != PlanPhase.DRAFT:
                raise PlannerError(f"Cannot add barriers in {self._phase.value} phase")
            
            barrier = Barrier(
                barrier_id=barrier_id,
                name=name,
                required_tasks=frozenset(required_tasks),
                successor_tasks=frozenset(successor_tasks or []),
                timeout_ms=timeout_ms,
            )
            
            self._barriers[barrier_id] = barrier
            
            # Add implicit dependencies for barrier
            for successor_id in barrier.successor_tasks:
                for required_id in barrier.required_tasks:
                    self.add_dependency(
                        required_id,
                        successor_id,
                        DependencyType.BARRIER,
                    )

    # ─────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the execution plan.
        
        Checks:
        - All dependency references exist
        - No cyclic dependencies
        - All barrier tasks exist
        
        Returns (valid, errors).
        """
        errors = []
        
        with self._lock:
            # Check dependency references
            for dep in self._dependencies:
                if dep.from_task_id not in self._tasks:
                    errors.append(f"Unknown dependency source: {dep.from_task_id}")
                if dep.to_task_id not in self._tasks:
                    errors.append(f"Unknown dependency target: {dep.to_task_id}")
            
            # Check barrier task references
            for barrier in self._barriers.values():
                for task_id in barrier.required_tasks:
                    if task_id not in self._tasks:
                        errors.append(f"Barrier {barrier.barrier_id} references unknown task: {task_id}")
                for task_id in barrier.successor_tasks:
                    if task_id not in self._tasks:
                        errors.append(f"Barrier {barrier.barrier_id} references unknown successor: {task_id}")
            
            # Check for cycles
            cycle = self._detect_cycle()
            if cycle:
                errors.append(f"Cyclic dependency detected: {' -> '.join(cycle)}")
            
            if not errors:
                self._compute_execution_levels()
                self._compute_critical_path()
                self._phase = PlanPhase.VALIDATED
            
            return len(errors) == 0, errors

    def _detect_cycle(self) -> Optional[List[str]]:
        """
        Detect cycles using DFS with three-color marking.
        
        Returns cycle path if found, None otherwise.
        """
        WHITE = 0  # Unvisited
        GRAY = 1   # In progress
        BLACK = 2  # Complete
        
        color: Dict[str, int] = {tid: WHITE for tid in self._tasks}
        parent: Dict[str, Optional[str]] = {tid: None for tid in self._tasks}
        
        def dfs(task_id: str) -> Optional[List[str]]:
            color[task_id] = GRAY
            
            for succ_id in self._successors.get(task_id, set()):
                if succ_id not in color:
                    continue
                    
                if color[succ_id] == GRAY:
                    # Found cycle - reconstruct path
                    cycle = [succ_id, task_id]
                    current = task_id
                    while parent[current] and parent[current] != succ_id:
                        current = parent[current]
                        cycle.append(current)
                    cycle.append(succ_id)
                    return list(reversed(cycle))
                
                if color[succ_id] == WHITE:
                    parent[succ_id] = task_id
                    result = dfs(succ_id)
                    if result:
                        return result
            
            color[task_id] = BLACK
            return None
        
        for task_id in self._tasks:
            if color[task_id] == WHITE:
                cycle = dfs(task_id)
                if cycle:
                    return cycle
        
        return None

    def _compute_execution_levels(self) -> None:
        """
        Compute execution levels using topological sort.
        
        Tasks at the same level can execute in parallel.
        """
        self._levels.clear()
        
        # Compute in-degree for each task
        in_degree: Dict[str, int] = {tid: 0 for tid in self._tasks}
        for dep in self._dependencies:
            if dep.to_task_id in in_degree:
                in_degree[dep.to_task_id] += 1
        
        # Start with tasks that have no dependencies
        current_level: List[str] = [
            tid for tid, deg in in_degree.items() if deg == 0
        ]
        level_num = 0
        
        while current_level:
            # Check if this level is a barrier
            is_barrier = False
            barrier_id = None
            for barrier in self._barriers.values():
                if barrier.required_tasks == frozenset(current_level):
                    is_barrier = True
                    barrier_id = barrier.barrier_id
                    break
            
            self._levels.append(ExecutionLevel(
                level=level_num,
                task_ids=current_level,
                is_barrier=is_barrier,
                barrier_id=barrier_id,
            ))
            
            # Find next level
            next_level: List[str] = []
            for task_id in current_level:
                for succ_id in self._successors.get(task_id, set()):
                    in_degree[succ_id] -= 1
                    if in_degree[succ_id] == 0:
                        next_level.append(succ_id)
            
            current_level = next_level
            level_num += 1

    def _compute_critical_path(self) -> None:
        """
        Compute the critical path (longest duration path).
        """
        self._critical_path.clear()
        
        if not self._tasks:
            return
        
        # Compute earliest start times
        earliest: Dict[str, int] = {}
        predecessor_on_path: Dict[str, Optional[str]] = {}
        
        for level in self._levels:
            for task_id in level.task_ids:
                task = self._tasks[task_id]
                pred_ids = self._predecessors.get(task_id, set())
                
                if not pred_ids:
                    earliest[task_id] = 0
                    predecessor_on_path[task_id] = None
                else:
                    max_time = 0
                    max_pred = None
                    for pred_id in pred_ids:
                        pred_task = self._tasks[pred_id]
                        end_time = earliest.get(pred_id, 0) + pred_task.estimated_duration_ms
                        if end_time > max_time:
                            max_time = end_time
                            max_pred = pred_id
                    earliest[task_id] = max_time
                    predecessor_on_path[task_id] = max_pred
        
        # Find the task with the longest path
        end_times: Dict[str, int] = {}
        for task_id, task in self._tasks.items():
            end_times[task_id] = earliest[task_id] + task.estimated_duration_ms
        
        if not end_times:
            return
        
        # Start from task with maximum end time
        current_id = max(end_times, key=lambda tid: end_times[tid])
        
        # Trace back to build critical path
        path = []
        while current_id:
            path.append(current_id)
            current_id = predecessor_on_path.get(current_id)
        
        self._critical_path = list(reversed(path))

    # ─────────────────────────────────────────────────────────────────────────
    # Execution
    # ─────────────────────────────────────────────────────────────────────────

    def get_ready_tasks(self) -> List[str]:
        """
        Get tasks that are ready to execute.
        
        A task is ready if all its predecessors are completed.
        """
        with self._lock:
            ready = []
            
            for task_id, execution in self._task_states.items():
                if execution.state != TaskState.PENDING:
                    continue
                
                pred_ids = self._predecessors.get(task_id, set())
                all_complete = all(
                    self._task_states[pid].state == TaskState.COMPLETED
                    for pid in pred_ids
                )
                
                if all_complete:
                    ready.append(task_id)
            
            return ready

    def mark_started(self, task_id: str) -> None:
        """Mark task as started."""
        with self._lock:
            if task_id not in self._task_states:
                raise PlannerError(f"Unknown task: {task_id}")
            
            execution = self._task_states[task_id]
            execution.state = TaskState.RUNNING
            execution.started_at = datetime.utcnow().isoformat() + "Z"

    def mark_completed(
        self,
        task_id: str,
        result: Optional[Any] = None,
    ) -> None:
        """Mark task as completed."""
        with self._lock:
            if task_id not in self._task_states:
                raise PlannerError(f"Unknown task: {task_id}")
            
            execution = self._task_states[task_id]
            execution.state = TaskState.COMPLETED
            execution.completed_at = datetime.utcnow().isoformat() + "Z"
            execution.result = result
            
            if execution.started_at:
                start = datetime.fromisoformat(execution.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(execution.completed_at.replace("Z", "+00:00"))
                execution.duration_ms = (end - start).total_seconds() * 1000

    def mark_failed(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        with self._lock:
            if task_id not in self._task_states:
                raise PlannerError(f"Unknown task: {task_id}")
            
            execution = self._task_states[task_id]
            execution.state = TaskState.FAILED
            execution.completed_at = datetime.utcnow().isoformat() + "Z"
            execution.error = error

    def get_task_state(self, task_id: str) -> Optional[TaskExecution]:
        """Get current state of a task."""
        return self._task_states.get(task_id)

    def is_complete(self) -> bool:
        """Check if all tasks are complete."""
        with self._lock:
            return all(
                ex.state in (TaskState.COMPLETED, TaskState.SKIPPED)
                for ex in self._task_states.values()
            )

    def has_failures(self) -> bool:
        """Check if any task failed."""
        with self._lock:
            return any(
                ex.state == TaskState.FAILED
                for ex in self._task_states.values()
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Metrics
    # ─────────────────────────────────────────────────────────────────────────

    def get_metrics(self) -> PlanMetrics:
        """Get plan execution metrics."""
        with self._lock:
            completed = sum(
                1 for ex in self._task_states.values()
                if ex.state == TaskState.COMPLETED
            )
            failed = sum(
                1 for ex in self._task_states.values()
                if ex.state == TaskState.FAILED
            )
            skipped = sum(
                1 for ex in self._task_states.values()
                if ex.state == TaskState.SKIPPED
            )
            
            # Calculate critical path duration
            cp_duration = sum(
                self._tasks[tid].estimated_duration_ms
                for tid in self._critical_path
            )
            
            # Calculate parallelism factor
            total_duration = sum(t.estimated_duration_ms for t in self._tasks.values())
            parallelism = total_duration / cp_duration if cp_duration > 0 else 1.0
            
            return PlanMetrics(
                total_tasks=len(self._tasks),
                completed_tasks=completed,
                failed_tasks=failed,
                skipped_tasks=skipped,
                total_levels=len(self._levels),
                critical_path_length=len(self._critical_path),
                critical_path_duration_ms=cp_duration,
                parallelism_factor=parallelism,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Serialization
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize plan to dictionary."""
        with self._lock:
            return {
                "plan_id": self._plan_id,
                "pac_id": self._pac_id,
                "phase": self._phase.value,
                "created_at": self._created_at,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "agent_gid": t.agent_gid,
                        "name": t.name,
                        "description": t.description,
                        "estimated_duration_ms": t.estimated_duration_ms,
                        "priority": t.priority,
                    }
                    for t in self._tasks.values()
                ],
                "dependencies": [
                    {
                        "from": d.from_task_id,
                        "to": d.to_task_id,
                        "type": d.dependency_type.value,
                    }
                    for d in self._dependencies
                ],
                "barriers": [
                    {
                        "barrier_id": b.barrier_id,
                        "name": b.name,
                        "required_tasks": list(b.required_tasks),
                        "successor_tasks": list(b.successor_tasks),
                    }
                    for b in self._barriers.values()
                ],
                "levels": [
                    {
                        "level": lv.level,
                        "task_ids": lv.task_ids,
                        "is_barrier": lv.is_barrier,
                    }
                    for lv in self._levels
                ],
                "critical_path": self._critical_path,
            }

    def compute_hash(self) -> str:
        """Compute deterministic hash of plan."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNER
# ═══════════════════════════════════════════════════════════════════════════════

class GIEExecutionPlanner:
    """
    High-level planner for creating and managing execution plans.
    """

    def __init__(self):
        """Initialize planner."""
        self._plans: Dict[str, ExecutionPlan] = {}
        self._lock = threading.RLock()
        self._plan_counter = 0

    def create_plan(self, pac_id: str, plan_id: Optional[str] = None) -> ExecutionPlan:
        """
        Create a new execution plan.
        """
        with self._lock:
            if plan_id is None:
                self._plan_counter += 1
                plan_id = f"PLAN-{pac_id}-{self._plan_counter:04d}"
            
            plan = ExecutionPlan(plan_id=plan_id, pac_id=pac_id)
            self._plans[plan_id] = plan
            return plan

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self) -> List[str]:
        """List all plan IDs."""
        return list(self._plans.keys())

    def create_parallel_agent_plan(
        self,
        pac_id: str,
        agent_tasks: List[Tuple[str, str, str]],  # (agent_gid, task_name, description)
        barrier_name: str = "ALL_AGENTS_COMPLETE",
    ) -> ExecutionPlan:
        """
        Create a plan where multiple agents execute in parallel with a final barrier.
        
        This is the canonical GIE multi-agent pattern.
        """
        plan = self.create_plan(pac_id)
        
        task_ids = []
        for i, (agent_gid, task_name, description) in enumerate(agent_tasks):
            task_id = f"TASK-{agent_gid}-{i:03d}"
            task = TaskDefinition(
                task_id=task_id,
                agent_gid=agent_gid,
                name=task_name,
                description=description,
            )
            plan.add_task(task)
            task_ids.append(task_id)
        
        # Add barrier if multiple tasks
        if len(task_ids) > 1:
            plan.add_barrier(
                barrier_id=f"BARRIER-{pac_id}-FINAL",
                name=barrier_name,
                required_tasks=task_ids,
            )
        
        return plan

    def create_sequential_plan(
        self,
        pac_id: str,
        agent_tasks: List[Tuple[str, str, str]],
    ) -> ExecutionPlan:
        """
        Create a plan where agents execute sequentially.
        """
        plan = self.create_plan(pac_id)
        
        prev_task_id = None
        for i, (agent_gid, task_name, description) in enumerate(agent_tasks):
            task_id = f"TASK-{agent_gid}-{i:03d}"
            task = TaskDefinition(
                task_id=task_id,
                agent_gid=agent_gid,
                name=task_name,
                description=description,
            )
            plan.add_task(task)
            
            if prev_task_id:
                plan.add_dependency(prev_task_id, task_id)
            
            prev_task_id = task_id
        
        return plan

    def create_fan_out_fan_in_plan(
        self,
        pac_id: str,
        start_task: Tuple[str, str, str],
        parallel_tasks: List[Tuple[str, str, str]],
        end_task: Tuple[str, str, str],
    ) -> ExecutionPlan:
        """
        Create a plan with fan-out -> parallel -> fan-in pattern.
        
        start_task -> [parallel_tasks...] -> end_task
        """
        plan = self.create_plan(pac_id)
        
        # Start task
        start_id = f"TASK-{start_task[0]}-START"
        plan.add_task(TaskDefinition(
            task_id=start_id,
            agent_gid=start_task[0],
            name=start_task[1],
            description=start_task[2],
        ))
        
        # Parallel tasks
        parallel_ids = []
        for i, (agent_gid, task_name, description) in enumerate(parallel_tasks):
            task_id = f"TASK-{agent_gid}-PARALLEL-{i:03d}"
            plan.add_task(TaskDefinition(
                task_id=task_id,
                agent_gid=agent_gid,
                name=task_name,
                description=description,
            ))
            parallel_ids.append(task_id)
        
        # End task
        end_id = f"TASK-{end_task[0]}-END"
        plan.add_task(TaskDefinition(
            task_id=end_id,
            agent_gid=end_task[0],
            name=end_task[1],
            description=end_task[2],
        ))
        
        # Fan-out from start
        plan.add_fan_out(start_id, parallel_ids)
        
        # Fan-in to end
        plan.add_fan_in(parallel_ids, end_id)
        
        return plan


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_planner: Optional[GIEExecutionPlanner] = None
_planner_lock = threading.Lock()


def get_planner() -> GIEExecutionPlanner:
    """Get or create global planner instance."""
    global _planner
    
    with _planner_lock:
        if _planner is None:
            _planner = GIEExecutionPlanner()
        return _planner


def reset_planner() -> None:
    """Reset global planner."""
    global _planner
    
    with _planner_lock:
        _planner = None
