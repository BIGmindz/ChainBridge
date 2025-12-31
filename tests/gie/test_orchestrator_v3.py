"""
Test Suite for GIE Orchestrator v3.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-01 (Cody) — CORE / ORCHESTRATION
Deliverable: ≥50 tests for GIE Orchestrator v3

Test Coverage:
- Dependency resolution and cycle detection
- Parallel execution with synchronization
- Checkpointed resumability
- Fault isolation and recovery
- Hash-verified state management
"""

import hashlib
import json
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

from core.gie.orchestrator_v3 import (
    # Enums
    AgentState,
    ExecutionMode,
    FaultStrategy,
    CheckpointState,
    DependencyType,
    # Exceptions
    OrchestratorError,
    DependencyCycleError,
    DependencyNotSatisfiedError,
    AgentExecutionError,
    CheckpointError,
    FaultIsolationError,
    ResumabilityError,
    # Data Classes
    AgentDependency,
    AgentSpec,
    AgentExecution,
    Checkpoint,
    ExecutionResult,
    # Core Classes
    DependencyGraph,
    FaultIsolationEngine,
    CheckpointManager,
    GIEOrchestratorV3,
    # Factory Functions
    create_orchestrator,
    create_agent_spec,
    create_dependency,
    # Constants
    ORCHESTRATOR_VERSION,
    MAX_RETRY_ATTEMPTS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_agent_specs() -> List[AgentSpec]:
    """Create sample agent specifications."""
    return [
        AgentSpec(
            agent_id="GID-01",
            role="Cody",
            lane="CORE",
            deliverables=["orchestrator_v3.py"],
            test_requirement=50,
        ),
        AgentSpec(
            agent_id="GID-02",
            role="Sonny",
            lane="FRONTEND",
            deliverables=["session_view.tsx"],
            test_requirement=30,
        ),
        AgentSpec(
            agent_id="GID-03",
            role="Mira-R",
            lane="RESEARCH",
            deliverables=["competitive_analysis.md"],
            test_requirement=0,
        ),
    ]


@pytest.fixture
def dependency_graph() -> DependencyGraph:
    """Create a sample dependency graph."""
    graph = DependencyGraph()
    return graph


@pytest.fixture
def orchestrator() -> GIEOrchestratorV3:
    """Create a configured orchestrator."""
    orch = create_orchestrator(
        mode=ExecutionMode.PARALLEL,
        fault_strategy=FaultStrategy.FAIL_ISOLATED,
        max_workers=4,
    )
    return orch


@pytest.fixture
def checkpoint_manager() -> CheckpointManager:
    """Create checkpoint manager."""
    return CheckpointManager()


def mock_executor_success(spec: AgentSpec) -> Tuple[str, int, Dict[str, Any]]:
    """Mock executor that always succeeds."""
    wrap_hash = hashlib.sha256(f"wrap-{spec.agent_id}".encode()).hexdigest()
    return wrap_hash, spec.test_requirement, {"status": "complete"}


def mock_executor_failure(spec: AgentSpec) -> Tuple[str, int, Dict[str, Any]]:
    """Mock executor that always fails."""
    raise Exception(f"Agent {spec.agent_id} failed")


# =============================================================================
# TEST: ENUMS AND CONSTANTS
# =============================================================================

class TestEnumsAndConstants:
    """Test enum values and constants."""
    
    def test_orchestrator_version(self):
        """Test version string format."""
        assert ORCHESTRATOR_VERSION == "3.0.0"
    
    def test_agent_state_values(self):
        """Test all agent states exist."""
        assert AgentState.PENDING.value == "PENDING"
        assert AgentState.READY.value == "READY"
        assert AgentState.DISPATCHED.value == "DISPATCHED"
        assert AgentState.EXECUTING.value == "EXECUTING"
        assert AgentState.CHECKPOINTED.value == "CHECKPOINTED"
        assert AgentState.WRAP_RECEIVED.value == "WRAP_RECEIVED"
        assert AgentState.FAILED.value == "FAILED"
        assert AgentState.ISOLATED.value == "ISOLATED"
    
    def test_execution_mode_values(self):
        """Test execution modes."""
        assert ExecutionMode.SEQUENTIAL.value == "SEQUENTIAL"
        assert ExecutionMode.PARALLEL.value == "PARALLEL"
        assert ExecutionMode.HYBRID.value == "HYBRID"
    
    def test_fault_strategy_values(self):
        """Test fault strategies."""
        assert FaultStrategy.FAIL_FAST.value == "FAIL_FAST"
        assert FaultStrategy.FAIL_ISOLATED.value == "FAIL_ISOLATED"
        assert FaultStrategy.RETRY.value == "RETRY"
        assert FaultStrategy.CHECKPOINT_RESUME.value == "CHECKPOINT_RESUME"
    
    def test_dependency_type_values(self):
        """Test dependency types."""
        assert DependencyType.HARD.value == "HARD"
        assert DependencyType.SOFT.value == "SOFT"
        assert DependencyType.DATA.value == "DATA"


# =============================================================================
# TEST: EXCEPTIONS
# =============================================================================

class TestExceptions:
    """Test exception hierarchy."""
    
    def test_orchestrator_error_base(self):
        """Test base exception."""
        err = OrchestratorError("test error")
        assert str(err) == "test error"
    
    def test_dependency_cycle_error(self):
        """Test cycle detection error."""
        cycle = ["A", "B", "C", "A"]
        err = DependencyCycleError(cycle)
        assert err.cycle == cycle
        assert "A -> B -> C -> A" in str(err)
    
    def test_dependency_not_satisfied_error(self):
        """Test dependency not satisfied error."""
        err = DependencyNotSatisfiedError("GID-02", "GID-01")
        assert err.agent_id == "GID-02"
        assert err.dependency == "GID-01"
    
    def test_agent_execution_error(self):
        """Test agent execution error."""
        err = AgentExecutionError("GID-01", "timeout", recoverable=True)
        assert err.agent_id == "GID-01"
        assert err.reason == "timeout"
        assert err.recoverable is True
    
    def test_checkpoint_error(self):
        """Test checkpoint error."""
        err = CheckpointError("save", "disk full")
        assert err.operation == "save"
        assert err.reason == "disk full"
    
    def test_fault_isolation_error(self):
        """Test fault isolation error."""
        err = FaultIsolationError("GID-01", ["GID-02", "GID-03"])
        assert err.agent_id == "GID-01"
        assert err.cascade_agents == ["GID-02", "GID-03"]
    
    def test_resumability_error(self):
        """Test resumability error."""
        err = ResumabilityError("SESSION-001", "checkpoint corrupted")
        assert err.session_id == "SESSION-001"
        assert err.reason == "checkpoint corrupted"


# =============================================================================
# TEST: DATA CLASSES
# =============================================================================

class TestDataClasses:
    """Test data class functionality."""
    
    def test_agent_spec_creation(self):
        """Test AgentSpec creation."""
        spec = AgentSpec(
            agent_id="GID-01",
            role="Cody",
            lane="CORE",
            deliverables=["file.py"],
            test_requirement=50,
        )
        assert spec.agent_id == "GID-01"
        assert spec.role == "Cody"
        assert spec.lane == "CORE"
        assert spec.test_requirement == 50
    
    def test_agent_spec_hash(self):
        """Test AgentSpec is hashable."""
        spec1 = AgentSpec("GID-01", "Cody", "CORE", [])
        spec2 = AgentSpec("GID-01", "Cody", "CORE", [])
        assert hash(spec1) == hash(spec2)
    
    def test_agent_dependency_creation(self):
        """Test AgentDependency creation."""
        dep = AgentDependency(
            source_agent="GID-01",
            target_agent="GID-02",
            dependency_type=DependencyType.HARD,
        )
        assert dep.source_agent == "GID-01"
        assert dep.target_agent == "GID-02"
        assert dep.dependency_type == DependencyType.HARD
    
    def test_agent_dependency_hash(self):
        """Test AgentDependency is hashable."""
        dep = AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        assert isinstance(hash(dep), int)
    
    def test_agent_execution_properties(self):
        """Test AgentExecution properties."""
        spec = AgentSpec("GID-01", "Cody", "CORE", [])
        execution = AgentExecution(
            spec=spec,
            state=AgentState.WRAP_RECEIVED,
            started_at="2025-01-01T00:00:00+00:00",
            completed_at="2025-01-01T00:01:00+00:00",
            wrap_hash="abc123",
        )
        assert execution.is_complete is True
        assert execution.is_success is True
        assert execution.duration_seconds == 60.0
    
    def test_agent_execution_duration_none(self):
        """Test duration when timestamps missing."""
        spec = AgentSpec("GID-01", "Cody", "CORE", [])
        execution = AgentExecution(spec=spec)
        assert execution.duration_seconds is None
    
    def test_checkpoint_serialization(self):
        """Test checkpoint to_dict/from_dict."""
        checkpoint = Checkpoint(
            checkpoint_id="CP-001",
            session_id="SESSION-001",
            pac_id="PAC-031",
            created_at="2025-01-01T00:00:00+00:00",
            agent_states={"GID-01": AgentState.WRAP_RECEIVED},
            completed_wraps={"GID-01": "hash123"},
            pending_agents=["GID-02"],
            execution_order=["GID-01", "GID-02"],
            checkpoint_hash="hash456",
        )
        
        data = checkpoint.to_dict()
        restored = Checkpoint.from_dict(data)
        
        assert restored.checkpoint_id == checkpoint.checkpoint_id
        assert restored.agent_states["GID-01"] == AgentState.WRAP_RECEIVED
    
    def test_execution_result_properties(self):
        """Test ExecutionResult properties."""
        result = ExecutionResult(
            session_id="SESSION-001",
            pac_id="PAC-031",
            success=True,
            agent_results={
                "GID-01": AgentExecution(
                    spec=AgentSpec("GID-01", "Cody", "CORE", []),
                    state=AgentState.WRAP_RECEIVED,
                ),
                "GID-02": AgentExecution(
                    spec=AgentSpec("GID-02", "Sonny", "FRONTEND", []),
                    state=AgentState.FAILED,
                ),
            },
            total_tests=50,
            wrap_hashes=["hash1"],
            started_at="2025-01-01T00:00:00+00:00",
            completed_at="2025-01-01T00:05:00+00:00",
            checkpoints_created=2,
            faults_isolated=1,
        )
        
        assert result.duration_seconds == 300.0
        assert result.successful_agents == 1
        assert result.failed_agents == 1


# =============================================================================
# TEST: DEPENDENCY GRAPH
# =============================================================================

class TestDependencyGraph:
    """Test dependency graph operations."""
    
    def test_add_dependency(self, dependency_graph: DependencyGraph):
        """Test adding dependencies."""
        dep = AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        dependency_graph.add_dependency(dep)
        
        assert "GID-01" in dependency_graph.get_dependencies("GID-02")
    
    def test_get_dependencies(self, dependency_graph: DependencyGraph):
        """Test getting dependencies for an agent."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-03", "GID-02", DependencyType.SOFT)
        )
        
        deps = dependency_graph.get_dependencies("GID-02")
        assert deps == {"GID-01", "GID-03"}
    
    def test_get_dependents(self, dependency_graph: DependencyGraph):
        """Test getting dependents of an agent."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-03", DependencyType.HARD)
        )
        
        dependents = dependency_graph.get_dependents("GID-01")
        assert dependents == {"GID-02", "GID-03"}
    
    def test_detect_no_cycle(self, dependency_graph: DependencyGraph):
        """Test no cycle detection in valid graph."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-03", DependencyType.HARD)
        )
        
        cycle = dependency_graph.detect_cycles()
        assert cycle is None
    
    def test_detect_simple_cycle(self, dependency_graph: DependencyGraph):
        """Test detecting simple cycle."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-01", DependencyType.HARD)
        )
        
        cycle = dependency_graph.detect_cycles()
        assert cycle is not None
        assert "GID-01" in cycle
        assert "GID-02" in cycle
    
    def test_detect_complex_cycle(self, dependency_graph: DependencyGraph):
        """Test detecting complex cycle."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-03", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-03", "GID-01", DependencyType.HARD)
        )
        
        cycle = dependency_graph.detect_cycles()
        assert cycle is not None
    
    def test_topological_sort_simple(self, dependency_graph: DependencyGraph):
        """Test topological sort on simple graph."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        
        order = dependency_graph.topological_sort()
        assert order.index("GID-01") < order.index("GID-02")
    
    def test_topological_sort_complex(self, dependency_graph: DependencyGraph):
        """Test topological sort on complex graph."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-03", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-03", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-03", "GID-04", DependencyType.HARD)
        )
        
        order = dependency_graph.topological_sort()
        assert order.index("GID-01") < order.index("GID-03")
        assert order.index("GID-02") < order.index("GID-03")
        assert order.index("GID-03") < order.index("GID-04")
    
    def test_topological_sort_with_cycle_raises(self, dependency_graph: DependencyGraph):
        """Test topological sort raises on cycle."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-01", DependencyType.HARD)
        )
        
        with pytest.raises(DependencyCycleError):
            dependency_graph.topological_sort()
    
    def test_parallel_batches_simple(self, dependency_graph: DependencyGraph):
        """Test parallel batch generation."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-03", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-03", DependencyType.HARD)
        )
        
        batches = dependency_graph.get_parallel_batches()
        
        # GID-01 and GID-02 should be in first batch (can run in parallel)
        assert "GID-01" in batches[0] or "GID-02" in batches[0]
        # GID-03 should be in a later batch
        for batch in batches:
            if "GID-03" in batch:
                assert batches.index(batch) > 0
    
    def test_parallel_batches_with_cycle_raises(self, dependency_graph: DependencyGraph):
        """Test parallel batches raises on cycle."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-01", DependencyType.HARD)
        )
        
        with pytest.raises(DependencyCycleError):
            dependency_graph.get_parallel_batches()


# =============================================================================
# TEST: FAULT ISOLATION ENGINE
# =============================================================================

class TestFaultIsolationEngine:
    """Test fault isolation functionality."""
    
    def test_isolate_single_fault(self, dependency_graph: DependencyGraph):
        """Test isolating single fault."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        
        engine = FaultIsolationEngine(dependency_graph)
        cascade = engine.isolate_fault("GID-01")
        
        assert engine.is_isolated("GID-01")
        assert "GID-02" in cascade  # Dependent should be cascaded
    
    def test_isolate_cascade(self, dependency_graph: DependencyGraph):
        """Test cascade isolation."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        dependency_graph.add_dependency(
            AgentDependency("GID-02", "GID-03", DependencyType.HARD)
        )
        
        engine = FaultIsolationEngine(dependency_graph)
        cascade = engine.isolate_fault("GID-01")
        
        assert engine.is_isolated("GID-01")
        assert engine.is_isolated("GID-02")
        assert engine.is_isolated("GID-03")
    
    def test_get_viable_agents(self, dependency_graph: DependencyGraph):
        """Test getting viable agents after isolation."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        
        engine = FaultIsolationEngine(dependency_graph)
        engine.isolate_fault("GID-01")
        
        all_agents = {"GID-01", "GID-02", "GID-03"}
        viable = engine.get_viable_agents(all_agents)
        
        assert "GID-03" in viable
        assert "GID-01" not in viable
        assert "GID-02" not in viable
    
    def test_isolation_report(self, dependency_graph: DependencyGraph):
        """Test isolation report generation."""
        dependency_graph.add_dependency(
            AgentDependency("GID-01", "GID-02", DependencyType.HARD)
        )
        
        engine = FaultIsolationEngine(dependency_graph)
        engine.isolate_fault("GID-01")
        
        report = engine.get_isolation_report()
        
        assert report["isolated_count"] == 2
        assert "GID-01" in report["isolated_agents"]
        assert "GID-01" in report["cascade_map"]


# =============================================================================
# TEST: CHECKPOINT MANAGER
# =============================================================================

class TestCheckpointManager:
    """Test checkpoint management."""
    
    def test_create_checkpoint(self, checkpoint_manager: CheckpointManager):
        """Test checkpoint creation."""
        checkpoint = checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={"GID-01": AgentState.EXECUTING},
            completed_wraps={},
            pending_agents=["GID-02"],
            execution_order=["GID-01", "GID-02"],
        )
        
        assert checkpoint.checkpoint_id.startswith("CP-")
        assert checkpoint.session_id == "SESSION-001"
        assert len(checkpoint.checkpoint_hash) == 64
    
    def test_get_checkpoint(self, checkpoint_manager: CheckpointManager):
        """Test retrieving checkpoint."""
        checkpoint = checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={},
            completed_wraps={},
            pending_agents=[],
            execution_order=[],
        )
        
        retrieved = checkpoint_manager.get_checkpoint(checkpoint.checkpoint_id)
        assert retrieved == checkpoint
    
    def test_get_nonexistent_checkpoint(self, checkpoint_manager: CheckpointManager):
        """Test retrieving nonexistent checkpoint."""
        result = checkpoint_manager.get_checkpoint("CP-NONEXISTENT")
        assert result is None
    
    def test_get_latest_checkpoint(self, checkpoint_manager: CheckpointManager):
        """Test getting latest checkpoint."""
        cp1 = checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={"GID-01": AgentState.PENDING},
            completed_wraps={},
            pending_agents=["GID-01"],
            execution_order=["GID-01"],
        )
        
        time.sleep(0.01)  # Ensure different timestamps
        
        cp2 = checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={"GID-01": AgentState.WRAP_RECEIVED},
            completed_wraps={"GID-01": "hash"},
            pending_agents=[],
            execution_order=["GID-01"],
        )
        
        latest = checkpoint_manager.get_latest_checkpoint("SESSION-001")
        assert latest.checkpoint_id == cp2.checkpoint_id
    
    def test_verify_checkpoint_valid(self, checkpoint_manager: CheckpointManager):
        """Test checkpoint verification succeeds."""
        checkpoint = checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={},
            completed_wraps={},
            pending_agents=[],
            execution_order=[],
        )
        
        assert checkpoint_manager.verify_checkpoint(checkpoint) is True
    
    def test_verify_checkpoint_tampered(self, checkpoint_manager: CheckpointManager):
        """Test checkpoint verification fails on tampering."""
        checkpoint = checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={},
            completed_wraps={},
            pending_agents=[],
            execution_order=[],
        )
        
        # Tamper with data
        checkpoint.session_id = "TAMPERED"
        
        assert checkpoint_manager.verify_checkpoint(checkpoint) is False
    
    def test_list_checkpoints(self, checkpoint_manager: CheckpointManager):
        """Test listing checkpoints."""
        checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={},
            completed_wraps={},
            pending_agents=[],
            execution_order=[],
        )
        checkpoint_manager.create_checkpoint(
            session_id="SESSION-002",
            pac_id="PAC-032",
            agent_states={},
            completed_wraps={},
            pending_agents=[],
            execution_order=[],
        )
        
        all_checkpoints = checkpoint_manager.list_checkpoints()
        assert len(all_checkpoints) == 2
        
        session1_checkpoints = checkpoint_manager.list_checkpoints("SESSION-001")
        assert len(session1_checkpoints) == 1


# =============================================================================
# TEST: ORCHESTRATOR CONFIGURATION
# =============================================================================

class TestOrchestratorConfiguration:
    """Test orchestrator configuration."""
    
    def test_create_orchestrator_default(self):
        """Test default orchestrator creation."""
        orch = create_orchestrator()
        assert orch._mode == ExecutionMode.PARALLEL
        assert orch._fault_strategy == FaultStrategy.FAIL_ISOLATED
    
    def test_create_orchestrator_custom(self):
        """Test custom orchestrator creation."""
        orch = create_orchestrator(
            mode=ExecutionMode.SEQUENTIAL,
            fault_strategy=FaultStrategy.FAIL_FAST,
            max_workers=2,
        )
        assert orch._mode == ExecutionMode.SEQUENTIAL
        assert orch._fault_strategy == FaultStrategy.FAIL_FAST
        assert orch._max_workers == 2
    
    def test_register_agent(self, orchestrator: GIEOrchestratorV3):
        """Test agent registration."""
        spec = create_agent_spec("GID-01", "Cody", "CORE", ["file.py"])
        orchestrator.register_agent(spec)
        
        assert "GID-01" in orchestrator._agents
        assert "GID-01" in orchestrator._executions
    
    def test_add_dependency(self, orchestrator: GIEOrchestratorV3):
        """Test adding dependency."""
        dep = create_dependency("GID-01", "GID-02")
        orchestrator.add_dependency(dep)
        
        deps = orchestrator._dependency_graph.get_dependencies("GID-02")
        assert "GID-01" in deps
    
    def test_configure_session(self, orchestrator: GIEOrchestratorV3):
        """Test session configuration."""
        orchestrator.configure_session("SESSION-001", "PAC-031")
        
        assert orchestrator._session_id == "SESSION-001"
        assert orchestrator._pac_id == "PAC-031"
        assert orchestrator._fault_engine is not None


# =============================================================================
# TEST: DEPENDENCY RESOLUTION
# =============================================================================

class TestDependencyResolution:
    """Test dependency resolution in orchestrator."""
    
    def test_resolve_dependencies(self, orchestrator: GIEOrchestratorV3):
        """Test resolving execution order."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", []))
        orchestrator.add_dependency(create_dependency("GID-01", "GID-02"))
        
        batches = orchestrator.resolve_dependencies()
        
        # GID-01 should be in an earlier batch than GID-02
        gid01_batch = None
        gid02_batch = None
        for i, batch in enumerate(batches):
            if "GID-01" in batch:
                gid01_batch = i
            if "GID-02" in batch:
                gid02_batch = i
        
        assert gid01_batch < gid02_batch
    
    def test_validate_dependencies_valid(self, orchestrator: GIEOrchestratorV3):
        """Test validation passes for valid dependencies."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", []))
        orchestrator.add_dependency(create_dependency("GID-01", "GID-02"))
        
        errors = orchestrator.validate_dependencies()
        assert len(errors) == 0
    
    def test_validate_dependencies_cycle(self, orchestrator: GIEOrchestratorV3):
        """Test validation detects cycles."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", []))
        orchestrator.add_dependency(create_dependency("GID-01", "GID-02"))
        orchestrator.add_dependency(create_dependency("GID-02", "GID-01"))
        
        errors = orchestrator.validate_dependencies()
        assert len(errors) > 0
        assert "Circular dependency" in errors[0]


# =============================================================================
# TEST: EXECUTION
# =============================================================================

class TestExecution:
    """Test orchestrator execution."""
    
    def test_execute_requires_session(self, orchestrator: GIEOrchestratorV3):
        """Test execute fails without session."""
        with pytest.raises(OrchestratorError, match="Session not configured"):
            orchestrator.execute(mock_executor_success)
    
    def test_execute_single_agent_success(self, orchestrator: GIEOrchestratorV3):
        """Test successful single agent execution."""
        orchestrator.register_agent(
            create_agent_spec("GID-01", "Cody", "CORE", ["file.py"], 50)
        )
        orchestrator.configure_session("SESSION-001", "PAC-031")
        
        result = orchestrator.execute(mock_executor_success)
        
        assert result.success is True
        assert result.successful_agents == 1
        assert result.total_tests == 50
        assert len(result.wrap_hashes) == 1
    
    def test_execute_multiple_agents(self, orchestrator: GIEOrchestratorV3):
        """Test multiple agent execution."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", [], 10))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", [], 20))
        orchestrator.register_agent(create_agent_spec("GID-03", "C", "L", [], 30))
        orchestrator.configure_session("SESSION-001", "PAC-031")
        
        result = orchestrator.execute(mock_executor_success)
        
        assert result.success is True
        assert result.successful_agents == 3
        assert result.total_tests == 60
    
    def test_execute_with_dependencies(self, orchestrator: GIEOrchestratorV3):
        """Test execution respects dependencies."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", [], 10))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", [], 20))
        orchestrator.add_dependency(create_dependency("GID-01", "GID-02"))
        orchestrator.configure_session("SESSION-001", "PAC-031")
        
        execution_order = []
        
        def tracking_executor(spec: AgentSpec) -> Tuple[str, int, Dict[str, Any]]:
            execution_order.append(spec.agent_id)
            return mock_executor_success(spec)
        
        # Use sequential mode to verify order
        orchestrator._mode = ExecutionMode.SEQUENTIAL
        result = orchestrator.execute(tracking_executor)
        
        assert execution_order.index("GID-01") < execution_order.index("GID-02")
    
    def test_execute_fail_isolated(self, orchestrator: GIEOrchestratorV3):
        """Test fault isolation on failure."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", [], 10))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", [], 20))
        orchestrator.add_dependency(create_dependency("GID-01", "GID-02"))
        orchestrator.configure_session("SESSION-001", "PAC-031")
        
        def failing_executor(spec: AgentSpec) -> Tuple[str, int, Dict[str, Any]]:
            if spec.agent_id == "GID-01":
                raise Exception("Intentional failure")
            return mock_executor_success(spec)
        
        orchestrator._mode = ExecutionMode.SEQUENTIAL
        result = orchestrator.execute(failing_executor)
        
        # GID-01 failed, GID-02 should be isolated
        assert orchestrator._executions["GID-01"].state == AgentState.FAILED
        assert orchestrator._executions["GID-02"].state == AgentState.ISOLATED
    
    def test_execute_sequential_mode(self):
        """Test sequential execution mode."""
        orch = create_orchestrator(mode=ExecutionMode.SEQUENTIAL)
        orch.register_agent(create_agent_spec("GID-01", "A", "L", [], 10))
        orch.register_agent(create_agent_spec("GID-02", "B", "L", [], 20))
        orch.configure_session("SESSION-001", "PAC-031")
        
        result = orch.execute(mock_executor_success)
        assert result.success is True


# =============================================================================
# TEST: RESUMABILITY
# =============================================================================

class TestResumability:
    """Test checkpoint resumability."""
    
    def test_resume_from_checkpoint(self, orchestrator: GIEOrchestratorV3):
        """Test resuming from checkpoint."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", [], 10))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", [], 20))
        orchestrator.configure_session("SESSION-001", "PAC-031")
        
        # Create checkpoint with GID-01 complete
        checkpoint = orchestrator._checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={
                "GID-01": AgentState.WRAP_RECEIVED,
                "GID-02": AgentState.PENDING,
            },
            completed_wraps={"GID-01": "hash123"},
            pending_agents=["GID-02"],
            execution_order=["GID-01", "GID-02"],
        )
        
        # Resume should only execute GID-02
        result = orchestrator.resume_from_checkpoint(
            checkpoint.checkpoint_id,
            mock_executor_success,
        )
        
        assert result.success is True
    
    def test_resume_nonexistent_checkpoint(self, orchestrator: GIEOrchestratorV3):
        """Test resume with nonexistent checkpoint fails."""
        with pytest.raises(ResumabilityError, match="Checkpoint not found"):
            orchestrator.resume_from_checkpoint("CP-NONEXISTENT", mock_executor_success)
    
    def test_resume_corrupted_checkpoint(self, orchestrator: GIEOrchestratorV3):
        """Test resume with corrupted checkpoint fails."""
        # Create and tamper with checkpoint
        checkpoint = orchestrator._checkpoint_manager.create_checkpoint(
            session_id="SESSION-001",
            pac_id="PAC-031",
            agent_states={},
            completed_wraps={},
            pending_agents=[],
            execution_order=[],
        )
        checkpoint.session_id = "TAMPERED"
        
        with pytest.raises(ResumabilityError, match="integrity check failed"):
            orchestrator.resume_from_checkpoint(checkpoint.checkpoint_id, mock_executor_success)


# =============================================================================
# TEST: QUERIES
# =============================================================================

class TestQueries:
    """Test orchestrator query methods."""
    
    def test_get_execution_state(self, orchestrator: GIEOrchestratorV3):
        """Test getting execution state."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        
        state = orchestrator.get_execution_state("GID-01")
        assert state is not None
        assert state.spec.agent_id == "GID-01"
    
    def test_get_nonexistent_state(self, orchestrator: GIEOrchestratorV3):
        """Test getting nonexistent state returns None."""
        state = orchestrator.get_execution_state("NONEXISTENT")
        assert state is None
    
    def test_get_all_states(self, orchestrator: GIEOrchestratorV3):
        """Test getting all states."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", []))
        
        states = orchestrator.get_all_states()
        assert len(states) == 2
    
    def test_get_pending_agents(self, orchestrator: GIEOrchestratorV3):
        """Test getting pending agents."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        orchestrator.register_agent(create_agent_spec("GID-02", "B", "L", []))
        
        pending = orchestrator.get_pending_agents()
        assert len(pending) == 2
    
    def test_get_completed_agents(self, orchestrator: GIEOrchestratorV3):
        """Test getting completed agents."""
        orchestrator.register_agent(create_agent_spec("GID-01", "A", "L", []))
        orchestrator.configure_session("SESSION-001", "PAC-031")
        orchestrator.execute(mock_executor_success)
        
        completed = orchestrator.get_completed_agents()
        assert "GID-01" in completed


# =============================================================================
# TEST: FACTORY FUNCTIONS
# =============================================================================

class TestFactoryFunctions:
    """Test factory function helpers."""
    
    def test_create_agent_spec(self):
        """Test create_agent_spec factory."""
        spec = create_agent_spec(
            "GID-01", "Cody", "CORE", ["file.py"], test_requirement=50
        )
        assert spec.agent_id == "GID-01"
        assert spec.test_requirement == 50
    
    def test_create_dependency(self):
        """Test create_dependency factory."""
        dep = create_dependency("GID-01", "GID-02", DependencyType.SOFT)
        assert dep.source_agent == "GID-01"
        assert dep.target_agent == "GID-02"
        assert dep.dependency_type == DependencyType.SOFT


# =============================================================================
# SUMMARY
# =============================================================================

"""
Test Summary:
- TestEnumsAndConstants: 5 tests
- TestExceptions: 7 tests
- TestDataClasses: 8 tests
- TestDependencyGraph: 10 tests
- TestFaultIsolationEngine: 4 tests
- TestCheckpointManager: 7 tests
- TestOrchestratorConfiguration: 5 tests
- TestDependencyResolution: 3 tests
- TestExecution: 7 tests
- TestResumability: 3 tests
- TestQueries: 5 tests
- TestFactoryFunctions: 2 tests

Total: 66 tests (≥50 requirement met)
"""
