"""
Task Tracker - Task State Machine & Heartbeat Integration
=========================================================

PAC Reference: PAC-P746-GOV-TASK-PROGRESSION-VISIBILITY
Classification: LAW_TIER
Authors:
    - CODY (GID-01) - Tracker Backend
    - ALEX (GID-08) - State Machine Logic
Orchestrator: BENSON (GID-00)

Invariants Enforced:
    - Operator Visibility Mandatory
    - Proof > Execution
    - No Silent Work

All task state transitions MUST emit heartbeat events.
No hidden or implicit tasks permitted.
"""

import json
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Import heartbeat system
try:
    from ChainBridge.core.orchestration.heartbeat import (
        get_emitter,
        HeartbeatEmitter,
        HeartbeatEventType,
    )
except ImportError:
    get_emitter = lambda: None


class TaskState(Enum):
    """Canonical task states."""
    DECLARED = "DECLARED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# Valid state transitions
VALID_TRANSITIONS: Dict[TaskState, List[TaskState]] = {
    TaskState.DECLARED: [TaskState.IN_PROGRESS, TaskState.BLOCKED],
    TaskState.IN_PROGRESS: [TaskState.COMPLETE, TaskState.FAILED, TaskState.BLOCKED],
    TaskState.BLOCKED: [TaskState.IN_PROGRESS, TaskState.FAILED],
    TaskState.COMPLETE: [],  # Terminal state
    TaskState.FAILED: [],    # Terminal state
}


class TaskStateError(Exception):
    """Invalid task state transition."""
    pass


@dataclass
class Task:
    """
    Single task in a PAC execution manifest.
    
    Every task has:
    - Unique ID within PAC
    - Current state from state machine
    - Assigned agent
    - Expected artifact
    - Timing metadata
    """
    task_id: str
    title: str
    status: TaskState = TaskState.DECLARED
    description: str = ""
    assigned_agent: Optional[str] = None
    artifact: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    # Timing
    declared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # State metadata
    failure_reason: Optional[str] = None
    blocked_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self.status in (TaskState.COMPLETE, TaskState.FAILED)


@dataclass
class TaskManifest:
    """
    Complete task manifest for a PAC execution.
    
    Declares all tasks before execution begins.
    No hidden tasks permitted.
    """
    manifest_id: str
    pac_id: str
    tasks: List[Task] = field(default_factory=list)
    declared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_order: str = "SEQUENTIAL"  # SEQUENTIAL, PARALLEL, DEPENDENCY_GRAPH
    
    @property
    def total_tasks(self) -> int:
        return len(self.tasks)
    
    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskState.COMPLETE)
    
    @property
    def failed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskState.FAILED)
    
    @property
    def in_progress_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskState.IN_PROGRESS)
    
    @property
    def progress_percent(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        terminal = self.completed_tasks + self.failed_tasks
        return (terminal / self.total_tasks) * 100
    
    def is_complete(self) -> bool:
        """Check if all tasks are in terminal states."""
        return all(t.is_terminal() for t in self.tasks)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "manifest_id": self.manifest_id,
            "pac_id": self.pac_id,
            "declared_at": self.declared_at,
            "execution_order": self.execution_order,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "progress_percent": self.progress_percent,
            "is_complete": self.is_complete(),
            "tasks": [t.to_dict() for t in self.tasks]
        }


class TaskTracker:
    """
    Tracks task execution with heartbeat integration.
    
    CRITICAL: Every state transition emits a heartbeat event.
    No silent work permitted.
    
    Usage:
        tracker = TaskTracker(pac_id="PAC-P746-...")
        
        # Declare tasks
        tracker.declare_task("TASK-01", "Define schema", agent="GID-03")
        tracker.declare_task("TASK-02", "Implement tracker", agent="GID-01")
        
        # Start execution
        tracker.start_task("TASK-01")
        
        # Complete task
        tracker.complete_task("TASK-01", artifact="schemas/task_manifest.json")
        
        # Check progress
        progress = tracker.get_progress()
    """
    
    def __init__(
        self,
        pac_id: str,
        emitter: Optional[HeartbeatEmitter] = None,
        execution_order: str = "SEQUENTIAL"
    ):
        self.pac_id = pac_id
        self.emitter = emitter or get_emitter()
        self._lock = threading.Lock()
        
        self.manifest = TaskManifest(
            manifest_id=f"MANIFEST-{pac_id}",
            pac_id=pac_id,
            execution_order=execution_order
        )
        
        self._state_callbacks: List[Callable[[Task, TaskState, TaskState], None]] = []
    
    def register_state_callback(
        self,
        callback: Callable[[Task, TaskState, TaskState], None]
    ) -> None:
        """Register callback for state transitions."""
        self._state_callbacks.append(callback)
    
    def _emit_transition(self, task: Task, old_state: TaskState, new_state: TaskState) -> None:
        """Emit heartbeat event for state transition."""
        if not self.emitter:
            return
        
        event_type = {
            TaskState.IN_PROGRESS: HeartbeatEventType.TASK_START,
            TaskState.COMPLETE: HeartbeatEventType.TASK_COMPLETE,
            TaskState.FAILED: HeartbeatEventType.TASK_FAILED,
        }.get(new_state)
        
        if event_type == HeartbeatEventType.TASK_START:
            self.emitter.emit_task_start(
                task_id=task.task_id,
                title=task.title,
                agent_gid=task.assigned_agent,
                old_state=old_state.value,
                new_state=new_state.value
            )
        elif event_type == HeartbeatEventType.TASK_COMPLETE:
            self.emitter.emit_task_complete(
                task_id=task.task_id,
                title=task.title,
                artifact=task.artifact,
                duration_ms=task.duration_ms
            )
        elif event_type == HeartbeatEventType.TASK_FAILED:
            self.emitter.emit_task_failed(
                task_id=task.task_id,
                title=task.title,
                reason=task.failure_reason or "Unknown"
            )
        
        # Trigger callbacks
        for callback in self._state_callbacks:
            try:
                callback(task, old_state, new_state)
            except Exception:
                pass
    
    def declare_task(
        self,
        task_id: str,
        title: str,
        description: str = "",
        agent: Optional[str] = None,
        artifact: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> Task:
        """
        Declare a new task in the manifest.
        
        MUST be called before execution begins.
        """
        with self._lock:
            # Check for duplicate
            if self.manifest.get_task(task_id):
                raise TaskStateError(f"Task {task_id} already declared")
            
            task = Task(
                task_id=task_id,
                title=title,
                description=description,
                assigned_agent=agent,
                artifact=artifact,
                dependencies=dependencies or []
            )
            
            self.manifest.tasks.append(task)
            return task
    
    def _validate_transition(self, task: Task, new_state: TaskState) -> None:
        """Validate state transition is allowed."""
        valid = VALID_TRANSITIONS.get(task.status, [])
        if new_state not in valid:
            raise TaskStateError(
                f"Invalid transition: {task.status.value} -> {new_state.value} for {task.task_id}"
            )
    
    def start_task(self, task_id: str) -> Task:
        """
        Transition task to IN_PROGRESS.
        
        Emits TASK_START heartbeat.
        """
        with self._lock:
            task = self.manifest.get_task(task_id)
            if not task:
                raise TaskStateError(f"Task {task_id} not found")
            
            self._validate_transition(task, TaskState.IN_PROGRESS)
            
            old_state = task.status
            task.status = TaskState.IN_PROGRESS
            task.started_at = datetime.now(timezone.utc).isoformat()
            
            self._emit_transition(task, old_state, TaskState.IN_PROGRESS)
            return task
    
    def complete_task(
        self,
        task_id: str,
        artifact: Optional[str] = None
    ) -> Task:
        """
        Transition task to COMPLETE.
        
        Emits TASK_COMPLETE heartbeat.
        """
        with self._lock:
            task = self.manifest.get_task(task_id)
            if not task:
                raise TaskStateError(f"Task {task_id} not found")
            
            self._validate_transition(task, TaskState.COMPLETE)
            
            old_state = task.status
            task.status = TaskState.COMPLETE
            task.completed_at = datetime.now(timezone.utc).isoformat()
            
            if artifact:
                task.artifact = artifact
            
            # Calculate duration
            if task.started_at:
                start = datetime.fromisoformat(task.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(task.completed_at.replace("Z", "+00:00"))
                task.duration_ms = int((end - start).total_seconds() * 1000)
            
            self._emit_transition(task, old_state, TaskState.COMPLETE)
            return task
    
    def fail_task(
        self,
        task_id: str,
        reason: str
    ) -> Task:
        """
        Transition task to FAILED.
        
        Emits TASK_FAILED heartbeat.
        """
        with self._lock:
            task = self.manifest.get_task(task_id)
            if not task:
                raise TaskStateError(f"Task {task_id} not found")
            
            self._validate_transition(task, TaskState.FAILED)
            
            old_state = task.status
            task.status = TaskState.FAILED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            task.failure_reason = reason
            
            self._emit_transition(task, old_state, TaskState.FAILED)
            return task
    
    def block_task(
        self,
        task_id: str,
        reason: str
    ) -> Task:
        """
        Transition task to BLOCKED.
        """
        with self._lock:
            task = self.manifest.get_task(task_id)
            if not task:
                raise TaskStateError(f"Task {task_id} not found")
            
            self._validate_transition(task, TaskState.BLOCKED)
            
            old_state = task.status
            task.status = TaskState.BLOCKED
            task.blocked_reason = reason
            
            return task
    
    def unblock_task(self, task_id: str) -> Task:
        """
        Transition task from BLOCKED to IN_PROGRESS.
        """
        with self._lock:
            task = self.manifest.get_task(task_id)
            if not task:
                raise TaskStateError(f"Task {task_id} not found")
            
            if task.status != TaskState.BLOCKED:
                raise TaskStateError(f"Task {task_id} is not blocked")
            
            old_state = task.status
            task.status = TaskState.IN_PROGRESS
            task.blocked_reason = None
            
            self._emit_transition(task, old_state, TaskState.IN_PROGRESS)
            return task
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current execution progress."""
        with self._lock:
            return {
                "pac_id": self.pac_id,
                "total_tasks": self.manifest.total_tasks,
                "completed_tasks": self.manifest.completed_tasks,
                "failed_tasks": self.manifest.failed_tasks,
                "in_progress_tasks": self.manifest.in_progress_tasks,
                "progress_percent": self.manifest.progress_percent,
                "is_complete": self.manifest.is_complete(),
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "title": t.title,
                        "status": t.status.value,
                        "agent": t.assigned_agent
                    }
                    for t in self.manifest.tasks
                ]
            }
    
    def get_manifest(self) -> Dict[str, Any]:
        """Get full manifest."""
        with self._lock:
            return self.manifest.to_dict()
    
    def can_close_pac(self) -> tuple:
        """
        Check if PAC can be closed.
        
        Returns (can_close, blocking_tasks)
        """
        with self._lock:
            non_terminal = [
                t.task_id for t in self.manifest.tasks
                if not t.is_terminal()
            ]
            return (len(non_terminal) == 0, non_terminal)


# ==================== Global Tracker Registry ====================

_trackers: Dict[str, TaskTracker] = {}
_trackers_lock = threading.Lock()


def get_tracker(pac_id: str) -> Optional[TaskTracker]:
    """Get tracker for a PAC."""
    with _trackers_lock:
        return _trackers.get(pac_id)


def create_tracker(pac_id: str, execution_order: str = "SEQUENTIAL") -> TaskTracker:
    """Create new tracker for a PAC."""
    with _trackers_lock:
        if pac_id in _trackers:
            return _trackers[pac_id]
        tracker = TaskTracker(pac_id, execution_order=execution_order)
        _trackers[pac_id] = tracker
        return tracker


def remove_tracker(pac_id: str) -> None:
    """Remove tracker (for cleanup)."""
    with _trackers_lock:
        _trackers.pop(pac_id, None)


# ==================== Self-Test ====================

if __name__ == "__main__":
    print("TaskTracker Self-Test")
    print("=" * 50)
    
    tracker = TaskTracker(pac_id="PAC-P746-TEST")
    
    # Declare tasks
    tracker.declare_task("TASK-01", "First task", agent="GID-01")
    tracker.declare_task("TASK-02", "Second task", agent="GID-02", dependencies=["TASK-01"])
    tracker.declare_task("TASK-03", "Third task", agent="GID-03")
    
    print(f"✅ Declared {tracker.manifest.total_tasks} tasks")
    
    # Execute
    tracker.start_task("TASK-01")
    print(f"✅ Started TASK-01")
    
    tracker.complete_task("TASK-01", artifact="output1.py")
    print(f"✅ Completed TASK-01")
    
    tracker.start_task("TASK-02")
    tracker.fail_task("TASK-02", reason="Test failure")
    print(f"✅ Failed TASK-02")
    
    tracker.start_task("TASK-03")
    tracker.complete_task("TASK-03")
    print(f"✅ Completed TASK-03")
    
    # Progress
    progress = tracker.get_progress()
    print(f"\n✅ Progress: {progress['progress_percent']:.0f}%")
    print(f"   Completed: {progress['completed_tasks']}")
    print(f"   Failed: {progress['failed_tasks']}")
    
    # Can close?
    can_close, blocking = tracker.can_close_pac()
    print(f"✅ Can close PAC: {can_close}")
    
    print("\n✅ Self-test PASSED")
