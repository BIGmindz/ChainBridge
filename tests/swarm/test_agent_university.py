"""
PAC-UNI-100: AGENT UNIVERSITY TEST SUITE
=========================================

Validates hyper-deterministic clone factory:
- UNI-01: PrimeDirective enforcement
- UNI-02: Deterministic routing algorithm
- UNI-03: Fail-closed on contamination
- Genesis Batch: 100 clone spawn
- Duplicate Replay: Output verification

Author: BENSON [GID-00]
Status: GENESIS_VALIDATION
"""

import pytest
from core.swarm.agent_university import (
    PrimeDirective,
    AgentClone,
    AgentUniversity,
    SwarmDispatcher,
    Task,
    JobManifest,
    DispatchStrategy
)


class TestPrimeDirective:
    """Test UNI-01: PrimeDirective enforcement."""
    
    def test_prime_directive_defaults(self):
        """Verify PrimeDirective has correct constitutional defaults."""
        directive = PrimeDirective()
        
        assert directive.origin == "PAC-UNI-100"
        assert directive.determinism_required is True
        assert directive.probabilistic_logic_allowed is False
        assert directive.failure_mode == "FAIL_CLOSED_IMMEDIATE"
    
    def test_prime_directive_immutability(self):
        """Verify PrimeDirective enforces strict types."""
        directive = PrimeDirective()
        
        # Should not allow mutation to probabilistic logic
        with pytest.raises(Exception):
            directive.probabilistic_logic_allowed = True


class TestAgentClone:
    """Test clone instantiation and execution."""
    
    def test_clone_genesis_check_success(self):
        """Valid PrimeDirective allows clone instantiation."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", count=1)
        clone = squad[0]
        
        assert clone.gid == "GID-01-01"
        assert clone.directive.determinism_required is True
        assert len(clone.task_queue) == 0
    
    def test_clone_genesis_check_rejects_contaminated_logic(self):
        """Contaminated PrimeDirective triggers FAIL_CLOSED_IMMEDIATE."""
        # Attempt to create directive with probabilistic logic
        with pytest.raises(Exception):
            bad_directive = PrimeDirective(probabilistic_logic_allowed=True)
    
    def test_clone_execution_deterministic(self):
        """Same input produces same output (zero entropy)."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", count=1)
        clone = squad[0]
        
        task = Task(
            id="TASK-001",
            description="Deterministic execution test",
            payload={"data": "test"}
        )
        
        # Execute twice - results MUST match
        result1 = clone.execute_task(task)
        result2 = clone.execute_task(task)
        
        assert result1 == result2  # Deterministic output
        assert clone.tasks_completed == 2  # Both executions recorded


class TestAgentUniversity:
    """Test squad spawning and factory operations."""
    
    def test_university_initialization(self):
        """University initializes with PrimeDirective standard."""
        university = AgentUniversity()
        
        assert university.standard.determinism_required is True
        assert university.standard.probabilistic_logic_allowed is False
    
    def test_spawn_squad_small(self):
        """Spawn small squad of 5 clones."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 5)
        
        assert len(squad) == 5
        assert all(isinstance(clone, AgentClone) for clone in squad)
        assert squad[0].gid == "GID-01-01"
        assert squad[4].gid == "GID-01-05"
    
    def test_spawn_squad_genesis_batch(self):
        """Genesis Batch: Spawn 100 clones (Task order 3)."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 100)
        
        assert len(squad) == 100
        assert squad[0].gid == "GID-01-01"
        assert squad[99].gid == "GID-01-100"
        
        # All clones MUST have PrimeDirective
        for clone in squad:
            assert clone.directive.determinism_required is True
            assert clone.directive.probabilistic_logic_allowed is False


class TestSwarmDispatcher:
    """Test UNI-02: Deterministic routing algorithm."""
    
    def test_deterministic_routing_modulo(self):
        """Routing uses strict modulo assignment (zero entropy)."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 3)
        
        tasks = [
            Task(id=f"TASK-{i:03d}", description=f"Test task {i}", payload={})
            for i in range(9)
        ]
        
        job = JobManifest(lane="BLUE", job_id="JOB-001", tasks=tasks)
        dispatcher = SwarmDispatcher()
        assignments = dispatcher.dispatch(job, squad, strategy=DispatchStrategy.ROUND_ROBIN)
        
        # Verify modulo distribution
        assert len(assignments["GID-01-01"]) == 3  # tasks 0, 3, 6
        assert len(assignments["GID-01-02"]) == 3  # tasks 1, 4, 7
        assert len(assignments["GID-01-03"]) == 3  # tasks 2, 5, 8
        
        # Verify specific task assignments
        assert assignments["GID-01-01"][0].id == "TASK-000"
        assert assignments["GID-01-02"][0].id == "TASK-001"
        assert assignments["GID-01-03"][0].id == "TASK-002"
    
    def test_duplicate_replay_determinism(self):
        """Task order 4: Duplicate replay produces identical output."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 5)
        
        tasks = [
            Task(id=f"TASK-{i:03d}", description=f"Determinism test {i}", payload={})
            for i in range(20)
        ]
        
        job = JobManifest(lane="BLUE", job_id="JOB-001", tasks=tasks)
        dispatcher = SwarmDispatcher()
        
        # First execution
        assignments1 = dispatcher.dispatch(job, squad, strategy=DispatchStrategy.ROUND_ROBIN)
        
        # Reset squad task queues
        for clone in squad:
            clone.task_queue = []
        
        # Second execution (DUPLICATE REPLAY)
        assignments2 = dispatcher.dispatch(job, squad, strategy=DispatchStrategy.ROUND_ROBIN)
        
        # Results MUST be identical
        assert assignments1.keys() == assignments2.keys()
        for gid in assignments1:
            tasks1 = [t.id for t in assignments1[gid]]
            tasks2 = [t.id for t in assignments2[gid]]
            assert tasks1 == tasks2


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_workflow(self, university):
        """Test complete workflow: spawn → dispatch → execute."""
        # Spawn squad
        squad = university.spawn_squad("GID-06", count=5)
        
        # Create tasks
        tasks = [
            Task(
                id=f"TASK-{i:04d}",
                description=f"Integration test task {i}",
                payload={"index": i}
            )
            for i in range(50)
        ]
        
        job = JobManifest(lane="BLUE", job_id="JOB-001", tasks=tasks)
        dispatcher = SwarmDispatcher()
        
        # Dispatch tasks to squad
        assignments = dispatcher.dispatch(job, squad, strategy=DispatchStrategy.ROUND_ROBIN)
        
        # Execute all tasks and collect results
        results = {}
        for clone in squad:
            clone_results = clone.execute_all_tasks()
            results[clone.gid] = clone_results
        
        # Verify all tasks executed
        total_completed = sum(results[clone.gid]['tasks_completed'] for clone in squad)
        assert total_completed == 50
