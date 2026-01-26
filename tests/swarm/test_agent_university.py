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
    Task
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
        directive = PrimeDirective()
        clone = AgentClone("GID-01", 1, directive)
        
        assert clone.gid == "GID-01-001"
        assert clone.directive.determinism_required is True
        assert len(clone.memory) == 0
    
    def test_clone_genesis_check_rejects_contaminated_logic(self):
        """Contaminated PrimeDirective triggers FAIL_CLOSED_IMMEDIATE."""
        # Attempt to create directive with probabilistic logic
        with pytest.raises(Exception):
            bad_directive = PrimeDirective(probabilistic_logic_allowed=True)
    
    def test_clone_execution_deterministic(self):
        """Same input produces same output (zero entropy)."""
        directive = PrimeDirective()
        clone = AgentClone("GID-01", 1, directive)
        
        task = Task(
            id="TASK-001",
            lane="BLUE",
            job_id="JOB-001",
            payload={"data": "test"}
        )
        
        # Execute twice - results MUST match
        result1 = clone.execute(task)
        result2 = clone.execute(task)
        
        assert result1 == "RESULT_TASK-001_VERIFIED"
        assert result1 == result2
        assert len(clone.memory) == 2  # Both executions recorded


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
        assert squad[0].gid == "GID-01-001"
        assert squad[4].gid == "GID-01-005"
    
    def test_spawn_squad_genesis_batch(self):
        """Genesis Batch: Spawn 100 clones (Task order 3)."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 100)
        
        assert len(squad) == 100
        assert squad[0].gid == "GID-01-001"
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
            Task(id=f"TASK-{i:03d}", lane="BLUE", job_id="JOB-001", payload={})
            for i in range(9)
        ]
        
        assignments = SwarmDispatcher.dispatch_job("JOB-001", tasks, squad)
        
        # Verify modulo distribution
        assert len(assignments["GID-01-001"]) == 3  # tasks 0, 3, 6
        assert len(assignments["GID-01-002"]) == 3  # tasks 1, 4, 7
        assert len(assignments["GID-01-003"]) == 3  # tasks 2, 5, 8
        
        # Verify specific task assignments
        assert assignments["GID-01-001"][0].id == "TASK-000"
        assert assignments["GID-01-002"][0].id == "TASK-001"
        assert assignments["GID-01-003"][0].id == "TASK-002"
    
    def test_duplicate_replay_determinism(self):
        """Task order 4: Duplicate replay produces identical output."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 5)
        
        tasks = [
            Task(id=f"TASK-{i:03d}", lane="BLUE", job_id="JOB-001", payload={})
            for i in range(20)
        ]
        
        # First execution
        assignments1 = SwarmDispatcher.dispatch_job("JOB-001", tasks, squad)
        
        # Second execution (DUPLICATE REPLAY)
        assignments2 = SwarmDispatcher.dispatch_job("JOB-001", tasks, squad)
        
        # Results MUST be identical
        assert assignments1.keys() == assignments2.keys()
        for gid in assignments1:
            tasks1 = [t.id for t in assignments1[gid]]
            tasks2 = [t.id for t in assignments2[gid]]
            assert tasks1 == tasks2


class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_squad_job_execution(self):
        """Complete workflow: spawn -> dispatch -> execute."""
        university = AgentUniversity()
        squad = university.spawn_squad("GID-01", 10)
        
        # Create job with 50 tasks
        tasks = [
            Task(id=f"TASK-{i:03d}", lane="BLUE", job_id="JOB-001", payload={"index": i})
            for i in range(50)
        ]
        
        # Dispatch tasks to squad
        assignments = SwarmDispatcher.dispatch_job("JOB-001", tasks, squad)
        
        # Execute all tasks and collect results
        results = {}
        for clone in squad:
            clone_results = [clone.execute(task) for task in assignments[clone.gid]]
            results[clone.gid] = clone_results
        
        # Verify all tasks executed
        total_results = sum(len(r) for r in results.values())
        assert total_results == 50
        
        # Verify deterministic result format
        assert all("VERIFIED" in result for result_list in results.values() for result in result_list)
