"""
PAC-UNI-100: SWARM DISPATCHER DETERMINISM TESTS
================================================

Validates UNI-01/UNI-02 invariants for deterministic task allocation.

Test Coverage:
- Round-robin dispatch (task[i] → agent[i % N])
- Hash-modulo dispatch (hash(task.id) % N → agent)
- Clone inheritance (UNI-02)
- Reproducibility (same input → same output)
- Edge cases (empty squad, single clone, 1000+ tasks)

Author: BENSON (GID-00) via PAC-UNI-100
Version: 1.0.0
"""

import pytest
import logging
from typing import List, Dict
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.swarm.agent_university import (
    AgentUniversity,
    AgentClone,
    SwarmDispatcher,
    Task,
    JobManifest,
    GIDPersona,
    DispatchStrategy,
    create_test_job
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestDispatcherDeterminism")


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def university():
    """Create Agent University instance."""
    return AgentUniversity()


@pytest.fixture
def sam_squad_3(university):
    """Create squad of 3 SAM clones."""
    return university.spawn_squad("GID-06", count=3)


@pytest.fixture
def sam_squad_5(university):
    """Create squad of 5 SAM clones."""
    return university.spawn_squad("GID-06", count=5)


@pytest.fixture
def sam_squad_10(university):
    """Create squad of 10 SAM clones."""
    return university.spawn_squad("GID-06", count=10)


@pytest.fixture
def test_job_10():
    """Create test job with 10 tasks."""
    return create_test_job(lane="SECURITY", task_count=10)


@pytest.fixture
def test_job_100():
    """Create test job with 100 tasks."""
    return create_test_job(lane="SECURITY", task_count=100)


@pytest.fixture
def test_job_1000():
    """Create test job with 1000 tasks."""
    return create_test_job(lane="SECURITY", task_count=1000)


@pytest.fixture
def dispatcher():
    """Create SwarmDispatcher instance."""
    return SwarmDispatcher()


# ============================================================================
# TEST 1: ROUND-ROBIN DETERMINISM (UNI-01)
# ============================================================================

def test_01_round_robin_deterministic_allocation(dispatcher, sam_squad_3, test_job_10):
    """
    UNI-01: Round-robin allocation MUST be deterministic.
    
    Expected:
    - Task[0, 3, 6, 9] → GID-06-01
    - Task[1, 4, 7] → GID-06-02
    - Task[2, 5, 8] → GID-06-03
    """
    logger.info("TEST 1: Round-Robin Deterministic Allocation")
    
    # First allocation
    allocations_1 = dispatcher.dispatch(test_job_10, sam_squad_3, DispatchStrategy.ROUND_ROBIN)
    
    # Recreate job (same task IDs)
    test_job_10_copy = create_test_job(lane="SECURITY", task_count=10)
    
    # Recreate squad
    university = AgentUniversity()
    sam_squad_3_copy = university.spawn_squad("GID-06", count=3)
    
    # Second allocation (should be identical)
    allocations_2 = dispatcher.dispatch(test_job_10_copy, sam_squad_3_copy, DispatchStrategy.ROUND_ROBIN)
    
    # Verify determinism
    for gid in allocations_1:
        tasks_1 = [t.id for t in allocations_1[gid]]
        tasks_2 = [t.id for t in allocations_2[gid]]
        assert tasks_1 == tasks_2, f"Round-robin allocation not deterministic for {gid}"
    
    # Verify expected distribution
    expected_gid_01 = ["TASK-0001", "TASK-0004", "TASK-0007", "TASK-0010"]
    expected_gid_02 = ["TASK-0002", "TASK-0005", "TASK-0008"]
    expected_gid_03 = ["TASK-0003", "TASK-0006", "TASK-0009"]
    
    actual_gid_01 = [t.id for t in allocations_1["GID-06-01"]]
    actual_gid_02 = [t.id for t in allocations_1["GID-06-02"]]
    actual_gid_03 = [t.id for t in allocations_1["GID-06-03"]]
    
    assert actual_gid_01 == expected_gid_01, f"GID-06-01 allocation incorrect: {actual_gid_01}"
    assert actual_gid_02 == expected_gid_02, f"GID-06-02 allocation incorrect: {actual_gid_02}"
    assert actual_gid_03 == expected_gid_03, f"GID-06-03 allocation incorrect: {actual_gid_03}"
    
    logger.info("✅ Round-robin allocation is deterministic (UNI-01 validated)")


def test_02_round_robin_balanced_distribution(dispatcher, sam_squad_5, test_job_100):
    """
    UNI-01: Round-robin MUST distribute tasks evenly.
    
    With 100 tasks and 5 agents:
    - Each agent should receive exactly 20 tasks
    """
    logger.info("TEST 2: Round-Robin Balanced Distribution")
    
    allocations = dispatcher.dispatch(test_job_100, sam_squad_5, DispatchStrategy.ROUND_ROBIN)
    stats = dispatcher.get_allocation_stats(allocations)
    
    # Verify balanced distribution
    assert stats["total_tasks"] == 100, f"Expected 100 tasks, got {stats['total_tasks']}"
    assert stats["agents"] == 5, f"Expected 5 agents, got {stats['agents']}"
    assert stats["min_tasks"] == 20, f"Min tasks should be 20, got {stats['min_tasks']}"
    assert stats["max_tasks"] == 20, f"Max tasks should be 20, got {stats['max_tasks']}"
    assert stats["avg_tasks"] == 20.0, f"Avg tasks should be 20.0, got {stats['avg_tasks']}"
    
    # Verify every agent has exactly 20 tasks
    for gid, tasks in allocations.items():
        assert len(tasks) == 20, f"{gid} should have 20 tasks, got {len(tasks)}"
    
    logger.info("✅ Round-robin distribution is balanced (UNI-01 validated)")


# ============================================================================
# TEST 3: HASH-MODULO DETERMINISM (UNI-01)
# ============================================================================

def test_03_hash_modulo_deterministic_allocation(dispatcher, sam_squad_3, test_job_10):
    """
    UNI-01: Hash-modulo allocation MUST be deterministic.
    
    Same task IDs → Same agent allocation (stateless).
    """
    logger.info("TEST 3: Hash-Modulo Deterministic Allocation")
    
    # First allocation
    allocations_1 = dispatcher.dispatch(test_job_10, sam_squad_3, DispatchStrategy.HASH_MODULO)
    
    # Recreate job (same task IDs)
    test_job_10_copy = create_test_job(lane="SECURITY", task_count=10)
    
    # Recreate squad
    university = AgentUniversity()
    sam_squad_3_copy = university.spawn_squad("GID-06", count=3)
    
    # Second allocation (should be identical)
    allocations_2 = dispatcher.dispatch(test_job_10_copy, sam_squad_3_copy, DispatchStrategy.HASH_MODULO)
    
    # Verify determinism
    for gid in allocations_1:
        tasks_1 = [t.id for t in allocations_1[gid]]
        tasks_2 = [t.id for t in allocations_2[gid]]
        assert tasks_1 == tasks_2, f"Hash-modulo allocation not deterministic for {gid}"
    
    logger.info("✅ Hash-modulo allocation is deterministic (UNI-01 validated)")


def test_04_hash_modulo_stateless_allocation(dispatcher, sam_squad_5):
    """
    UNI-01: Hash-modulo MUST be stateless.
    
    Same task ID → Same agent (independent of task order).
    """
    logger.info("TEST 4: Hash-Modulo Stateless Allocation")
    
    # Job 1: Tasks in order TASK-0001, TASK-0002, TASK-0003
    job_1 = JobManifest(
        lane="TEST",
        job_id="JOB-1",
        tasks=[
            Task(id="TASK-0001", description="Task 1"),
            Task(id="TASK-0002", description="Task 2"),
            Task(id="TASK-0003", description="Task 3")
        ]
    )
    
    # Job 2: Tasks in reverse order TASK-0003, TASK-0002, TASK-0001
    job_2 = JobManifest(
        lane="TEST",
        job_id="JOB-2",
        tasks=[
            Task(id="TASK-0003", description="Task 3"),
            Task(id="TASK-0002", description="Task 2"),
            Task(id="TASK-0001", description="Task 1")
        ]
    )
    
    # Recreate squads
    university = AgentUniversity()
    squad_1 = university.spawn_squad("GID-06", count=5)
    squad_2 = university.spawn_squad("GID-06", count=5)
    
    # Allocate
    allocations_1 = dispatcher.dispatch(job_1, squad_1, DispatchStrategy.HASH_MODULO)
    allocations_2 = dispatcher.dispatch(job_2, squad_2, DispatchStrategy.HASH_MODULO)
    
    # Find which agent TASK-0001 was assigned to in both jobs
    def find_task_agent(allocations, task_id):
        for gid, tasks in allocations.items():
            if any(t.id == task_id for t in tasks):
                return gid
        return None
    
    for task_id in ["TASK-0001", "TASK-0002", "TASK-0003"]:
        agent_1 = find_task_agent(allocations_1, task_id)
        agent_2 = find_task_agent(allocations_2, task_id)
        
        assert agent_1 == agent_2, f"{task_id} assigned to different agents: {agent_1} vs {agent_2}"
    
    logger.info("✅ Hash-modulo allocation is stateless (UNI-01 validated)")


# ============================================================================
# TEST 5: CLONE INHERITANCE (UNI-02)
# ============================================================================

def test_05_clone_inheritance_from_parent(university):
    """
    UNI-02: Clones MUST inherit strict properties from parent GID.
    
    Inherited properties:
    - Role
    - Skills
    - Scope
    """
    logger.info("TEST 5: Clone Inheritance from Parent")
    
    # Get parent persona
    sam_persona = university.get_persona("GID-06")
    assert sam_persona is not None, "SAM persona not found in registry"
    
    # Spawn squad
    squad = university.spawn_squad("GID-06", count=3)
    
    # Verify each clone inherited properties
    for clone in squad:
        assert clone.parent_gid == "GID-06", f"Clone {clone.gid} has wrong parent_gid"
        assert clone.role == sam_persona.role, f"Clone {clone.gid} role mismatch"
        assert clone.skills == sam_persona.skills, f"Clone {clone.gid} skills mismatch"
        assert clone.scope == sam_persona.scope, f"Clone {clone.gid} scope mismatch"
        
        logger.info(f"   ✅ {clone.gid}: role={clone.role}, skills={len(clone.skills)}")
    
    logger.info("✅ Clone inheritance validated (UNI-02 validated)")


def test_06_clone_gid_format_compliance(university):
    """
    UNI-02: Clone GID format MUST be {PARENT_GID}-{CLONE_ID:02d}.
    
    Example: GID-06-01, GID-06-02, ..., GID-06-10
    """
    logger.info("TEST 6: Clone GID Format Compliance")
    
    squad = university.spawn_squad("GID-06", count=10)
    
    expected_gids = [f"GID-06-{i:02d}" for i in range(1, 11)]
    actual_gids = [clone.gid for clone in squad]
    
    assert actual_gids == expected_gids, f"GID format mismatch: {actual_gids}"
    
    logger.info(f"   Expected: {expected_gids}")
    logger.info(f"   Actual:   {actual_gids}")
    logger.info("✅ Clone GID format compliant (UNI-02 validated)")


# ============================================================================
# TEST 7: REPRODUCIBILITY
# ============================================================================

def test_07_full_workflow_reproducibility(dispatcher):
    """
    UNI-01 + UNI-02: Full workflow MUST be reproducible.
    
    Same parent GID + same task count → same allocation results.
    """
    logger.info("TEST 7: Full Workflow Reproducibility")
    
    def execute_workflow():
        """Execute complete workflow and return allocation."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-06", count=5)
        job = create_test_job(lane="SECURITY", task_count=50)
        allocations = dispatcher.dispatch(job, squad, DispatchStrategy.ROUND_ROBIN)
        return {gid: [t.id for t in tasks] for gid, tasks in allocations.items()}
    
    # Execute workflow 3 times
    result_1 = execute_workflow()
    result_2 = execute_workflow()
    result_3 = execute_workflow()
    
    # Verify identical results
    assert result_1 == result_2 == result_3, "Workflow not reproducible"
    
    logger.info("✅ Workflow is reproducible (UNI-01 + UNI-02 validated)")


# ============================================================================
# TEST 8: EDGE CASES
# ============================================================================

def test_08_single_clone_squad(dispatcher, university):
    """
    Edge case: Squad with single clone.
    
    All tasks should go to one clone.
    """
    logger.info("TEST 8: Single Clone Squad")
    
    squad = university.spawn_squad("GID-06", count=1)
    job = create_test_job(lane="SECURITY", task_count=10)
    
    allocations = dispatcher.dispatch(job, squad, DispatchStrategy.ROUND_ROBIN)
    
    assert len(allocations["GID-06-01"]) == 10, "Single clone should receive all tasks"
    
    logger.info("✅ Single clone squad handled correctly")


def test_09_large_task_batch(dispatcher, sam_squad_10, test_job_1000):
    """
    Edge case: 1000 tasks dispatched to 10 clones.
    
    Each clone should receive exactly 100 tasks.
    """
    logger.info("TEST 9: Large Task Batch (1000 tasks)")
    
    allocations = dispatcher.dispatch(test_job_1000, sam_squad_10, DispatchStrategy.ROUND_ROBIN)
    stats = dispatcher.get_allocation_stats(allocations)
    
    assert stats["total_tasks"] == 1000, f"Expected 1000 tasks, got {stats['total_tasks']}"
    assert stats["min_tasks"] == 100, f"Min tasks should be 100, got {stats['min_tasks']}"
    assert stats["max_tasks"] == 100, f"Max tasks should be 100, got {stats['max_tasks']}"
    assert stats["avg_tasks"] == 100.0, f"Avg tasks should be 100.0, got {stats['avg_tasks']}"
    
    logger.info("✅ Large task batch distributed correctly")


def test_10_empty_task_list(dispatcher, sam_squad_3):
    """
    Edge case: Job with no tasks.
    
    Should return empty allocations for all agents.
    """
    logger.info("TEST 10: Empty Task List")
    
    job = JobManifest(lane="SECURITY", job_id="JOB-EMPTY", tasks=[])
    
    allocations = dispatcher.dispatch(job, sam_squad_3, DispatchStrategy.ROUND_ROBIN)
    
    for gid, tasks in allocations.items():
        assert len(tasks) == 0, f"{gid} should have no tasks"
    
    logger.info("✅ Empty task list handled correctly")


# ============================================================================
# TEST 11: TASK EXECUTION
# ============================================================================

def test_11_clone_task_execution(university):
    """
    Validate clone task execution.
    
    Clones should execute assigned tasks and track completion.
    """
    logger.info("TEST 11: Clone Task Execution")
    
    squad = university.spawn_squad("GID-06", count=1)
    clone = squad[0]
    
    # Assign tasks
    task1 = Task(id="TASK-001", description="Test task 1")
    task2 = Task(id="TASK-002", description="Test task 2")
    
    clone.assign_task(task1)
    clone.assign_task(task2)
    
    assert len(clone.task_queue) == 2, "Task queue should have 2 tasks"
    
    # Execute tasks
    result = clone.execute_all_tasks()
    
    assert result["tasks_completed"] == 2, "Should complete 2 tasks"
    assert result["tasks_failed"] == 0, "Should have 0 failures"
    
    logger.info(f"   ✅ {result['clone_gid']}: {result['tasks_completed']}/{result['tasks_executed']} completed")
    logger.info("✅ Clone task execution validated")


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

def deterministic_dispatcher_test_execution():
    """
    Standalone execution function for PAC-UNI-100 validation.
    
    Runs all tests and generates summary report.
    """
    print("=" * 70)
    print("⚔️  PAC-UNI-100: DETERMINISTIC SWARM DISPATCHER TESTS")
    print("=" * 70)
    print()
    print("INVARIANTS UNDER TEST:")
    print("  - UNI-01: Task allocation MUST be deterministic")
    print("  - UNI-02: Clones MUST inherit strict properties from parent")
    print()
    print("=" * 70)
    
    # Run pytest
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode == 0:
        print()
        print("=" * 70)
        print("🏆 DETERMINISTIC SWARM DISPATCHER TESTS")
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("VALIDATED INVARIANTS:")
        print("  ✅ UNI-01: Deterministic allocation (Round Robin + Hash Modulo)")
        print("  ✅ UNI-02: Clone inheritance (Role + Skills + Scope)")
        print()
        print("SWARM INFRASTRUCTURE: OPERATIONAL")
        print("=" * 70)
    else:
        print()
        print("=" * 70)
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        return False
    
    return True


if __name__ == "__main__":
    deterministic_dispatcher_test_execution()
