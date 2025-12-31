"""
Test GIE Execution Planner

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
Agent: GID-01 (Cody) — Backend / GIE Core

REAL WORK MODE — Production-grade tests.
"""

import pytest
import time
import threading
from typing import List

from core.gie.execution.planner import (
    # Enums
    TaskState,
    PlanPhase,
    DependencyType,
    LaneType,
    
    # Exceptions
    PlannerError,
    CyclicDependencyError,
    InvalidDependencyError,
    PlanValidationError,
    ExecutionError,
    
    # Data classes
    TaskDefinition,
    Dependency,
    Barrier,
    ExecutionLevel,
    TaskExecution,
    PlanMetrics,
    
    # Classes
    ExecutionPlan,
    GIEExecutionPlanner,
    
    # Factory
    get_planner,
    reset_planner,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def planner():
    """Provide fresh planner."""
    reset_planner()
    return GIEExecutionPlanner()


@pytest.fixture
def plan(planner):
    """Provide fresh execution plan."""
    return planner.create_plan("PAC-TEST")


@pytest.fixture
def sample_tasks():
    """Provide sample task definitions."""
    return [
        TaskDefinition(
            task_id="TASK-001",
            agent_gid="GID-01",
            name="Task A",
            description="First task",
            estimated_duration_ms=1000,
        ),
        TaskDefinition(
            task_id="TASK-002",
            agent_gid="GID-02",
            name="Task B",
            description="Second task",
            estimated_duration_ms=2000,
        ),
        TaskDefinition(
            task_id="TASK-003",
            agent_gid="GID-03",
            name="Task C",
            description="Third task",
            estimated_duration_ms=1500,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: TaskDefinition
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskDefinition:
    """Tests for TaskDefinition dataclass."""

    def test_creation(self):
        """Can create task definition."""
        task = TaskDefinition(
            task_id="TASK-001",
            agent_gid="GID-01",
            name="Test Task",
        )
        assert task.task_id == "TASK-001"
        assert task.agent_gid == "GID-01"

    def test_equality(self):
        """Tasks with same ID are equal."""
        task1 = TaskDefinition(task_id="TASK-001", agent_gid="GID-01", name="A")
        task2 = TaskDefinition(task_id="TASK-001", agent_gid="GID-02", name="B")
        assert task1 == task2

    def test_hashable(self):
        """Tasks are hashable."""
        task = TaskDefinition(task_id="TASK-001", agent_gid="GID-01", name="A")
        task_set = {task}
        assert task in task_set


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Basic Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionPlanBasic:
    """Tests for basic ExecutionPlan operations."""

    def test_create_plan(self, plan):
        """Can create execution plan."""
        assert plan.plan_id is not None
        assert plan.pac_id == "PAC-TEST"
        assert plan.phase == PlanPhase.DRAFT

    def test_add_task(self, plan, sample_tasks):
        """Can add tasks to plan."""
        plan.add_task(sample_tasks[0])
        assert plan.task_count == 1
        assert plan.get_task("TASK-001") is not None

    def test_add_multiple_tasks(self, plan, sample_tasks):
        """Can add multiple tasks."""
        plan.add_tasks(sample_tasks)
        assert plan.task_count == 3

    def test_duplicate_task_raises(self, plan, sample_tasks):
        """Adding duplicate task raises error."""
        plan.add_task(sample_tasks[0])
        with pytest.raises(PlannerError):
            plan.add_task(sample_tasks[0])

    def test_list_tasks(self, plan, sample_tasks):
        """Can list all tasks."""
        plan.add_tasks(sample_tasks)
        tasks = plan.list_tasks()
        assert len(tasks) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Dependencies
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionPlanDependencies:
    """Tests for dependency management."""

    def test_add_dependency(self, plan, sample_tasks):
        """Can add dependency between tasks."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        
        valid, errors = plan.validate()
        assert valid

    def test_fan_out(self, plan, sample_tasks):
        """Can add fan-out pattern."""
        plan.add_tasks(sample_tasks)
        plan.add_fan_out("TASK-001", ["TASK-002", "TASK-003"])
        
        valid, errors = plan.validate()
        assert valid
        assert plan.level_count == 2

    def test_fan_in(self, plan, sample_tasks):
        """Can add fan-in pattern."""
        plan.add_tasks(sample_tasks)
        plan.add_fan_in(["TASK-001", "TASK-002"], "TASK-003")
        
        valid, errors = plan.validate()
        assert valid
        assert plan.level_count == 2

    def test_dependency_chain(self, plan, sample_tasks):
        """Sequential dependencies create multiple levels."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.add_dependency("TASK-002", "TASK-003")
        
        valid, errors = plan.validate()
        assert valid
        assert plan.level_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Barriers
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionPlanBarriers:
    """Tests for barrier synchronization."""

    def test_add_barrier(self, plan, sample_tasks):
        """Can add barrier."""
        plan.add_tasks(sample_tasks)
        plan.add_barrier(
            barrier_id="BARRIER-001",
            name="Sync Point",
            required_tasks=["TASK-001", "TASK-002"],
        )
        
        valid, errors = plan.validate()
        assert valid

    def test_barrier_with_successors(self, plan):
        """Barrier creates dependencies to successors."""
        tasks = [
            TaskDefinition(task_id="TASK-A", agent_gid="GID-01", name="A"),
            TaskDefinition(task_id="TASK-B", agent_gid="GID-02", name="B"),
            TaskDefinition(task_id="TASK-C", agent_gid="GID-03", name="C"),
        ]
        plan.add_tasks(tasks)
        
        plan.add_barrier(
            barrier_id="BARRIER-001",
            name="Sync",
            required_tasks=["TASK-A", "TASK-B"],
            successor_tasks=["TASK-C"],
        )
        
        valid, errors = plan.validate()
        assert valid
        # Level 0: A, B; Level 1: C
        assert plan.level_count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionPlanValidation:
    """Tests for plan validation."""

    def test_empty_plan_valid(self, plan):
        """Empty plan is valid."""
        valid, errors = plan.validate()
        assert valid

    def test_unknown_dependency_source(self, plan, sample_tasks):
        """Unknown dependency source fails validation."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("UNKNOWN", "TASK-001")
        
        valid, errors = plan.validate()
        assert not valid
        assert any("Unknown dependency source" in e for e in errors)

    def test_unknown_dependency_target(self, plan, sample_tasks):
        """Unknown dependency target fails validation."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "UNKNOWN")
        
        valid, errors = plan.validate()
        assert not valid
        assert any("Unknown dependency target" in e for e in errors)

    def test_cyclic_dependency_detected(self, plan, sample_tasks):
        """Cyclic dependencies are detected."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.add_dependency("TASK-002", "TASK-003")
        plan.add_dependency("TASK-003", "TASK-001")  # Cycle!
        
        valid, errors = plan.validate()
        assert not valid
        assert any("Cyclic dependency" in e for e in errors)

    def test_self_dependency_detected(self, plan, sample_tasks):
        """Self-dependency is a cycle."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-001")
        
        valid, errors = plan.validate()
        assert not valid

    def test_validation_sets_phase(self, plan, sample_tasks):
        """Successful validation sets phase to VALIDATED."""
        plan.add_tasks(sample_tasks)
        valid, _ = plan.validate()
        
        assert valid
        assert plan.phase == PlanPhase.VALIDATED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Execution Levels
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionLevels:
    """Tests for execution level computation."""

    def test_parallel_tasks_same_level(self, plan, sample_tasks):
        """Independent tasks are in same level."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        # All tasks are independent, should be level 0
        assert plan.level_count == 1

    def test_sequential_tasks_different_levels(self, plan, sample_tasks):
        """Dependent tasks are in different levels."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.add_dependency("TASK-002", "TASK-003")
        plan.validate()
        
        assert plan.level_count == 3

    def test_diamond_pattern(self, plan):
        """Diamond dependency pattern."""
        tasks = [
            TaskDefinition(task_id="A", agent_gid="GID-01", name="A"),
            TaskDefinition(task_id="B", agent_gid="GID-02", name="B"),
            TaskDefinition(task_id="C", agent_gid="GID-03", name="C"),
            TaskDefinition(task_id="D", agent_gid="GID-04", name="D"),
        ]
        plan.add_tasks(tasks)
        
        # A -> B, A -> C, B -> D, C -> D
        plan.add_fan_out("A", ["B", "C"])
        plan.add_fan_in(["B", "C"], "D")
        
        plan.validate()
        
        # Level 0: A; Level 1: B, C; Level 2: D
        assert plan.level_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Critical Path
# ═══════════════════════════════════════════════════════════════════════════════

class TestCriticalPath:
    """Tests for critical path computation."""

    def test_single_task_critical_path(self, plan):
        """Single task is its own critical path."""
        plan.add_task(TaskDefinition(
            task_id="TASK-001",
            agent_gid="GID-01",
            name="Only Task",
            estimated_duration_ms=1000,
        ))
        plan.validate()
        
        assert plan.critical_path == ["TASK-001"]

    def test_sequential_critical_path(self, plan, sample_tasks):
        """Sequential tasks form critical path."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.add_dependency("TASK-002", "TASK-003")
        plan.validate()
        
        assert plan.critical_path == ["TASK-001", "TASK-002", "TASK-003"]

    def test_parallel_paths_longest_wins(self, plan):
        """Critical path is the longest duration path."""
        tasks = [
            TaskDefinition(task_id="A", agent_gid="GID-01", name="A", estimated_duration_ms=100),
            TaskDefinition(task_id="B", agent_gid="GID-02", name="B", estimated_duration_ms=5000),  # Slow
            TaskDefinition(task_id="C", agent_gid="GID-03", name="C", estimated_duration_ms=100),
            TaskDefinition(task_id="D", agent_gid="GID-04", name="D", estimated_duration_ms=100),
        ]
        plan.add_tasks(tasks)
        
        plan.add_fan_out("A", ["B", "C"])
        plan.add_fan_in(["B", "C"], "D")
        
        plan.validate()
        
        # B is the bottleneck
        assert "B" in plan.critical_path


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Task Execution
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskExecution:
    """Tests for task execution tracking."""

    def test_get_ready_tasks_initial(self, plan, sample_tasks):
        """All independent tasks are ready initially."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        ready = plan.get_ready_tasks()
        assert len(ready) == 3

    def test_get_ready_tasks_with_deps(self, plan, sample_tasks):
        """Only tasks with satisfied deps are ready."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.add_dependency("TASK-001", "TASK-003")
        plan.validate()
        
        ready = plan.get_ready_tasks()
        assert ready == ["TASK-001"]

    def test_mark_started(self, plan, sample_tasks):
        """Can mark task as started."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        plan.mark_started("TASK-001")
        
        state = plan.get_task_state("TASK-001")
        assert state.state == TaskState.RUNNING
        assert state.started_at is not None

    def test_mark_completed(self, plan, sample_tasks):
        """Can mark task as completed."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        plan.mark_started("TASK-001")
        plan.mark_completed("TASK-001", result={"success": True})
        
        state = plan.get_task_state("TASK-001")
        assert state.state == TaskState.COMPLETED
        assert state.result == {"success": True}

    def test_mark_failed(self, plan, sample_tasks):
        """Can mark task as failed."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        plan.mark_started("TASK-001")
        plan.mark_failed("TASK-001", "Something went wrong")
        
        state = plan.get_task_state("TASK-001")
        assert state.state == TaskState.FAILED
        assert state.error == "Something went wrong"

    def test_completed_deps_unlock_successors(self, plan, sample_tasks):
        """Completing deps unlocks successor tasks."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.validate()
        
        # Initially only TASK-001 and TASK-003 ready
        ready = plan.get_ready_tasks()
        assert "TASK-001" in ready
        assert "TASK-002" not in ready
        
        # Complete TASK-001
        plan.mark_started("TASK-001")
        plan.mark_completed("TASK-001")
        
        # Now TASK-002 should be ready
        ready = plan.get_ready_tasks()
        assert "TASK-002" in ready

    def test_is_complete(self, plan, sample_tasks):
        """Can check if plan is complete."""
        plan.add_tasks(sample_tasks[:1])  # Just one task
        plan.validate()
        
        assert not plan.is_complete()
        
        plan.mark_started("TASK-001")
        plan.mark_completed("TASK-001")
        
        assert plan.is_complete()

    def test_has_failures(self, plan, sample_tasks):
        """Can check if plan has failures."""
        plan.add_tasks(sample_tasks[:1])
        plan.validate()
        
        assert not plan.has_failures()
        
        plan.mark_started("TASK-001")
        plan.mark_failed("TASK-001", "Error")
        
        assert plan.has_failures()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlanMetrics:
    """Tests for plan metrics."""

    def test_initial_metrics(self, plan, sample_tasks):
        """Initial metrics reflect plan state."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        metrics = plan.get_metrics()
        assert metrics.total_tasks == 3
        assert metrics.completed_tasks == 0
        assert metrics.failed_tasks == 0

    def test_metrics_after_completion(self, plan, sample_tasks):
        """Metrics update after task completion."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        plan.mark_started("TASK-001")
        plan.mark_completed("TASK-001")
        
        metrics = plan.get_metrics()
        assert metrics.completed_tasks == 1

    def test_parallelism_factor(self, plan, sample_tasks):
        """Parallelism factor computed correctly."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        metrics = plan.get_metrics()
        # All parallel, so factor should be > 1
        assert metrics.parallelism_factor >= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionPlan — Serialization
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlanSerialization:
    """Tests for plan serialization."""

    def test_to_dict(self, plan, sample_tasks):
        """Can serialize plan to dict."""
        plan.add_tasks(sample_tasks)
        plan.add_dependency("TASK-001", "TASK-002")
        plan.validate()
        
        data = plan.to_dict()
        
        assert data["pac_id"] == "PAC-TEST"
        assert len(data["tasks"]) == 3
        assert len(data["dependencies"]) == 1

    def test_compute_hash(self, plan, sample_tasks):
        """Can compute plan hash."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        hash1 = plan.compute_hash()
        assert hash1.startswith("sha256:")
        
        # Hash is deterministic
        hash2 = plan.compute_hash()
        assert hash1 == hash2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GIEExecutionPlanner
# ═══════════════════════════════════════════════════════════════════════════════

class TestGIEExecutionPlanner:
    """Tests for high-level planner."""

    def test_create_plan(self, planner):
        """Can create plan."""
        plan = planner.create_plan("PAC-001")
        assert plan is not None
        assert plan.pac_id == "PAC-001"

    def test_get_plan(self, planner):
        """Can retrieve plan by ID."""
        plan = planner.create_plan("PAC-001")
        retrieved = planner.get_plan(plan.plan_id)
        assert retrieved is plan

    def test_list_plans(self, planner):
        """Can list all plans."""
        planner.create_plan("PAC-001")
        planner.create_plan("PAC-002")
        
        plans = planner.list_plans()
        assert len(plans) == 2

    def test_create_parallel_agent_plan(self, planner):
        """Can create parallel agent plan."""
        agent_tasks = [
            ("GID-01", "Task A", "First agent"),
            ("GID-02", "Task B", "Second agent"),
            ("GID-03", "Task C", "Third agent"),
        ]
        
        plan = planner.create_parallel_agent_plan("PAC-001", agent_tasks)
        valid, errors = plan.validate()
        
        assert valid
        assert plan.task_count == 3
        assert plan.level_count == 1  # All parallel

    def test_create_sequential_plan(self, planner):
        """Can create sequential plan."""
        agent_tasks = [
            ("GID-01", "Task A", "First"),
            ("GID-02", "Task B", "Second"),
            ("GID-03", "Task C", "Third"),
        ]
        
        plan = planner.create_sequential_plan("PAC-001", agent_tasks)
        valid, errors = plan.validate()
        
        assert valid
        assert plan.level_count == 3  # Sequential

    def test_create_fan_out_fan_in_plan(self, planner):
        """Can create fan-out/fan-in plan."""
        start = ("GID-01", "Start", "Initial task")
        parallel = [
            ("GID-02", "Worker A", "Parallel A"),
            ("GID-03", "Worker B", "Parallel B"),
        ]
        end = ("GID-04", "End", "Final task")
        
        plan = planner.create_fan_out_fan_in_plan("PAC-001", start, parallel, end)
        valid, errors = plan.validate()
        
        assert valid
        assert plan.task_count == 4
        assert plan.level_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Factory
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactory:
    """Tests for factory functions."""

    def test_get_planner_singleton(self):
        """get_planner returns singleton."""
        reset_planner()
        p1 = get_planner()
        p2 = get_planner()
        assert p1 is p2
        reset_planner()

    def test_reset_planner(self):
        """reset_planner clears singleton."""
        reset_planner()
        p1 = get_planner()
        reset_planner()
        p2 = get_planner()
        assert p1 is not p2
        reset_planner()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Thread Safety
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_task_updates(self, plan, sample_tasks):
        """Can update tasks from multiple threads."""
        plan.add_tasks(sample_tasks)
        plan.validate()
        
        errors = []
        
        def update_task(task_id: str):
            try:
                plan.mark_started(task_id)
                time.sleep(0.01)
                plan.mark_completed(task_id)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=update_task, args=(t.task_id,))
            for t in sample_tasks
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert plan.is_complete()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Complex Scenarios
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplexScenarios:
    """Tests for complex execution scenarios."""

    def test_six_agent_parallel_plan(self, planner):
        """Test 6-agent parallel execution (PAC-029 pattern)."""
        agent_tasks = [
            ("GID-01", "Execution Planner", "GIE Core"),
            ("GID-02", "Checkpoint Timeline", "Frontend"),
            ("GID-10", "Risk Decomposition", "ML/Risk"),
            ("GID-07", "PDO Retention", "Data/Storage"),
            ("GID-06", "Attack Simulator", "Security"),
            ("GID-03", "Competitive Analysis", "Research"),
        ]
        
        plan = planner.create_parallel_agent_plan(
            "PAC-029",
            agent_tasks,
            barrier_name="ALL_WRAPS_RECEIVED",
        )
        
        valid, errors = plan.validate()
        assert valid, f"Validation errors: {errors}"
        
        assert plan.task_count == 6
        assert plan.level_count == 1  # All parallel
        
        # All tasks should be ready
        ready = plan.get_ready_tasks()
        assert len(ready) == 6

    def test_multi_phase_execution(self, planner):
        """Test multi-phase execution with barriers."""
        plan = planner.create_plan("PAC-MULTI")
        
        # Phase 1: Parallel preparation
        for i in range(3):
            plan.add_task(TaskDefinition(
                task_id=f"PREP-{i}",
                agent_gid=f"GID-{i}",
                name=f"Prepare {i}",
            ))
        
        # Phase 2: Processing (after barrier)
        for i in range(2):
            plan.add_task(TaskDefinition(
                task_id=f"PROC-{i}",
                agent_gid=f"GID-{i}",
                name=f"Process {i}",
            ))
        
        # Phase 3: Finalize
        plan.add_task(TaskDefinition(
            task_id="FINAL",
            agent_gid="GID-00",
            name="Finalize",
        ))
        
        # Barrier 1: All prep must complete
        plan.add_barrier(
            barrier_id="B1",
            name="Prep Complete",
            required_tasks=["PREP-0", "PREP-1", "PREP-2"],
            successor_tasks=["PROC-0", "PROC-1"],
        )
        
        # Barrier 2: All processing must complete
        plan.add_barrier(
            barrier_id="B2",
            name="Processing Complete",
            required_tasks=["PROC-0", "PROC-1"],
            successor_tasks=["FINAL"],
        )
        
        valid, errors = plan.validate()
        assert valid
        
        # Should have 3 levels: Prep -> Proc -> Final
        assert plan.level_count == 3
