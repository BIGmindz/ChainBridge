"""
Tests for Cross-Agent Dependency Graph.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-04 (Cindy)
Target: ≥30 tests

Test Coverage:
- Enums
- Exceptions  
- Data classes
- Graph operations
- Cycle detection
- Topological sort
- Execution batches
- Validation
- Impact analysis
- Health checks
"""

import pytest
from datetime import datetime
from core.spine.dependency_graph import (
    # Constants
    MODULE_VERSION,
    MAX_DEPENDENCY_DEPTH,
    # Enums
    DependencyScope,
    DependencyStrength,
    DependencyStatus,
    NodeState,
    HealthStatus,
    # Exceptions
    DependencyError,
    CyclicDependencyError,
    DependencyNotFoundError,
    MaxDepthExceededError,
    UnsatisfiedDependencyError,
    # Data Classes
    Dependency,
    AgentNode,
    DependencyPath,
    ImpactAnalysis,
    DependencyHealth,
    # Core Classes
    CrossAgentDependencyGraph,
    # Factory Functions
    create_dependency_graph,
    create_dependency,
)


# =============================================================================
# TEST: MODULE
# =============================================================================

class TestModule:
    """Test module-level attributes."""
    
    def test_module_version(self):
        """Test module version."""
        assert MODULE_VERSION == "1.0.0"
    
    def test_max_depth_constant(self):
        """Test max depth constant."""
        assert MAX_DEPENDENCY_DEPTH == 10


# =============================================================================
# TEST: ENUMS
# =============================================================================

class TestEnums:
    """Test enumeration types."""
    
    def test_dependency_scope_values(self):
        """Test dependency scope enum."""
        assert DependencyScope.STATIC.value == "STATIC"
        assert DependencyScope.RUNTIME.value == "RUNTIME"
        assert DependencyScope.INFERRED.value == "INFERRED"
    
    def test_dependency_strength_values(self):
        """Test dependency strength enum."""
        assert DependencyStrength.REQUIRED.value == "REQUIRED"
        assert DependencyStrength.OPTIONAL.value == "OPTIONAL"
        assert DependencyStrength.WEAK.value == "WEAK"
    
    def test_dependency_status_values(self):
        """Test dependency status enum."""
        assert DependencyStatus.PENDING.value == "PENDING"
        assert DependencyStatus.SATISFIED.value == "SATISFIED"
        assert DependencyStatus.FAILED.value == "FAILED"
        assert DependencyStatus.SKIPPED.value == "SKIPPED"
    
    def test_node_state_values(self):
        """Test node state enum."""
        assert NodeState.UNVISITED.value == "UNVISITED"
        assert NodeState.VISITING.value == "VISITING"
        assert NodeState.VISITED.value == "VISITED"
    
    def test_health_status_values(self):
        """Test health status enum."""
        assert HealthStatus.HEALTHY.value == "HEALTHY"
        assert HealthStatus.DEGRADED.value == "DEGRADED"
        assert HealthStatus.UNHEALTHY.value == "UNHEALTHY"


# =============================================================================
# TEST: EXCEPTIONS
# =============================================================================

class TestExceptions:
    """Test custom exceptions."""
    
    def test_cyclic_dependency_error(self):
        """Test cyclic dependency exception."""
        cycle = ["A", "B", "A"]
        error = CyclicDependencyError(cycle)
        assert error.cycle == cycle
        assert "A → B → A" in str(error)
    
    def test_dependency_not_found_error(self):
        """Test dependency not found exception."""
        error = DependencyNotFoundError("A", "B")
        assert error.source == "A"
        assert error.target == "B"
        assert "A → B" in str(error)
    
    def test_max_depth_exceeded_error(self):
        """Test max depth exceeded exception."""
        error = MaxDepthExceededError("A", 15)
        assert error.agent_id == "A"
        assert error.depth == 15
        # Message shows the max limit (10), not the actual depth
        assert "10" in str(error)
        assert "A" in str(error)
    
    def test_unsatisfied_dependency_error(self):
        """Test unsatisfied dependency exception."""
        error = UnsatisfiedDependencyError("B", ["A", "C"])
        assert error.agent_id == "B"
        assert error.dependencies == ["A", "C"]


# =============================================================================
# TEST: DATA CLASSES
# =============================================================================

class TestDependency:
    """Test Dependency data class."""
    
    def test_dependency_creation(self):
        """Test creating dependency."""
        dep = Dependency(
            dependency_id="DEP-001",
            source_agent="A",
            target_agent="B",
            scope=DependencyScope.STATIC,
            strength=DependencyStrength.REQUIRED,
        )
        assert dep.dependency_id == "DEP-001"
        assert dep.source_agent == "A"
        assert dep.target_agent == "B"
        assert dep.status == DependencyStatus.PENDING
    
    def test_dependency_satisfy(self):
        """Test satisfying dependency."""
        dep = Dependency(
            dependency_id="DEP-001",
            source_agent="A",
            target_agent="B",
            scope=DependencyScope.STATIC,
            strength=DependencyStrength.REQUIRED,
        )
        dep.satisfy()
        assert dep.status == DependencyStatus.SATISFIED
        assert dep.satisfied_at is not None
    
    def test_dependency_fail(self):
        """Test failing dependency."""
        dep = Dependency(
            dependency_id="DEP-001",
            source_agent="A",
            target_agent="B",
            scope=DependencyScope.STATIC,
            strength=DependencyStrength.REQUIRED,
        )
        dep.fail()
        assert dep.status == DependencyStatus.FAILED
    
    def test_dependency_hash(self):
        """Test dependency is hashable."""
        dep = Dependency(
            dependency_id="DEP-001",
            source_agent="A",
            target_agent="B",
            scope=DependencyScope.STATIC,
            strength=DependencyStrength.REQUIRED,
        )
        assert hash(dep) == hash(("A", "B"))
    
    def test_dependency_to_dict(self):
        """Test dependency serialization."""
        dep = Dependency(
            dependency_id="DEP-001",
            source_agent="A",
            target_agent="B",
            scope=DependencyScope.STATIC,
            strength=DependencyStrength.REQUIRED,
        )
        data = dep.to_dict()
        assert data["source_agent"] == "A"
        assert data["target_agent"] == "B"


class TestAgentNode:
    """Test AgentNode data class."""
    
    def test_agent_node_creation(self):
        """Test creating agent node."""
        node = AgentNode(agent_id="A", name="Agent A")
        assert node.agent_id == "A"
        assert node.name == "Agent A"
        assert node.state == NodeState.UNVISITED
    
    def test_is_root(self):
        """Test is_root property."""
        node = AgentNode(agent_id="A", name="Agent A")
        assert node.is_root is True
        node.dependencies.add("B")
        assert node.is_root is False
    
    def test_is_leaf(self):
        """Test is_leaf property."""
        node = AgentNode(agent_id="A", name="Agent A")
        assert node.is_leaf is True
        node.dependents.add("B")
        assert node.is_leaf is False


class TestDependencyPath:
    """Test DependencyPath data class."""
    
    def test_path_creation(self):
        """Test creating path."""
        path = DependencyPath(path=["A", "B", "C"], total_depth=2)
        assert len(path) == 3
    
    def test_path_start_end(self):
        """Test path start and end."""
        path = DependencyPath(path=["A", "B", "C"], total_depth=2)
        assert path.start == "A"
        assert path.end == "C"
    
    def test_path_contains(self):
        """Test path contains."""
        path = DependencyPath(path=["A", "B", "C"], total_depth=2)
        assert path.contains("B") is True
        assert path.contains("D") is False


class TestDependencyHealth:
    """Test DependencyHealth data class."""
    
    def test_health_creation(self):
        """Test creating health report."""
        health = DependencyHealth(
            status=HealthStatus.HEALTHY,
            total_agents=5,
            total_dependencies=4,
            satisfied_dependencies=4,
            failed_dependencies=0,
            pending_dependencies=0,
            has_cycles=False,
            max_depth=2,
            orphaned_agents=0,
        )
        assert health.status == HealthStatus.HEALTHY
        assert health.satisfaction_rate == 1.0
    
    def test_satisfaction_rate(self):
        """Test satisfaction rate calculation."""
        health = DependencyHealth(
            status=HealthStatus.DEGRADED,
            total_agents=5,
            total_dependencies=4,
            satisfied_dependencies=3,
            failed_dependencies=1,
            pending_dependencies=0,
            has_cycles=False,
            max_depth=2,
            orphaned_agents=0,
        )
        assert health.satisfaction_rate == 0.75


# =============================================================================
# TEST: GRAPH BASIC OPERATIONS
# =============================================================================

class TestGraphBasicOperations:
    """Test basic graph operations."""
    
    def test_create_empty_graph(self):
        """Test creating empty graph."""
        graph = create_dependency_graph()
        assert isinstance(graph, CrossAgentDependencyGraph)
    
    def test_add_agent(self):
        """Test adding agent to graph."""
        graph = create_dependency_graph()
        node = graph.add_agent("A", "Agent A")
        assert node.agent_id == "A"
        assert graph.get_agent("A") is not None
    
    def test_add_duplicate_agent(self):
        """Test adding duplicate agent returns existing."""
        graph = create_dependency_graph()
        node1 = graph.add_agent("A", "Agent A")
        node2 = graph.add_agent("A", "Agent A")
        assert node1 is node2
    
    def test_remove_agent(self):
        """Test removing agent."""
        graph = create_dependency_graph()
        graph.add_agent("A", "Agent A")
        graph.remove_agent("A")
        assert graph.get_agent("A") is None
    
    def test_add_dependency(self):
        """Test adding dependency."""
        graph = create_dependency_graph()
        dep = graph.add_dependency("A", "B")
        assert dep.source_agent == "A"
        assert dep.target_agent == "B"
    
    def test_get_dependency(self):
        """Test getting dependency."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        dep = graph.get_dependency("A", "B")
        assert dep is not None
    
    def test_remove_dependency(self):
        """Test removing dependency."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.remove_dependency("A", "B")
        assert graph.get_dependency("A", "B") is None


# =============================================================================
# TEST: CYCLE DETECTION
# =============================================================================

class TestCycleDetection:
    """Test cycle detection."""
    
    def test_no_cycle(self):
        """Test graph without cycles."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        assert graph.has_cycles() is False
    
    def test_detect_simple_cycle(self):
        """Test detecting simple cycle."""
        graph = create_dependency_graph()
        graph.add_agent("A", "Agent A")
        graph.add_agent("B", "Agent B")
        
        # Add first dependency
        graph.add_dependency("A", "B")
        
        # Try to add cycle - should raise
        with pytest.raises(CyclicDependencyError):
            graph.add_dependency("B", "A")
    
    def test_prevent_cycle_creation(self):
        """Test cycle prevention."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        
        with pytest.raises(CyclicDependencyError):
            graph.add_dependency("C", "A")


# =============================================================================
# TEST: DEPENDENCY QUERIES
# =============================================================================

class TestDependencyQueries:
    """Test dependency query methods."""
    
    def test_get_dependencies(self):
        """Test getting dependencies."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        
        deps = graph.get_dependencies("B")
        assert "A" in deps
    
    def test_get_dependents(self):
        """Test getting dependents."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("A", "C")
        
        deps = graph.get_dependents("A")
        assert "B" in deps
        assert "C" in deps
    
    def test_get_all_dependencies(self):
        """Test getting transitive dependencies."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        
        all_deps = graph.get_all_dependencies("C")
        assert "A" in all_deps
        assert "B" in all_deps
    
    def test_get_all_dependents(self):
        """Test getting transitive dependents."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        
        all_deps = graph.get_all_dependents("A")
        assert "B" in all_deps
        assert "C" in all_deps


# =============================================================================
# TEST: TOPOLOGICAL SORT
# =============================================================================

class TestTopologicalSort:
    """Test topological sorting."""
    
    def test_simple_topo_sort(self):
        """Test simple topological sort."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        
        order = graph.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")
    
    def test_parallel_topo_sort(self):
        """Test topological sort with parallel nodes."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "C")
        
        order = graph.topological_sort()
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("C")
    
    def test_execution_batches(self):
        """Test getting execution batches."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "C")
        graph.add_dependency("B", "C")
        
        batches = graph.get_execution_batches()
        assert len(batches) == 2
        # First batch has A and B (parallel)
        assert set(batches[0]) == {"A", "B"}
        # Second batch has C
        assert batches[1] == ["C"]


# =============================================================================
# TEST: VALIDATION
# =============================================================================

class TestValidation:
    """Test validation methods."""
    
    def test_validate_ready_satisfied(self):
        """Test validating ready with satisfied deps."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.satisfy_dependency("A", "B")
        
        unsatisfied = graph.validate_ready("B")
        assert len(unsatisfied) == 0
    
    def test_validate_ready_unsatisfied(self):
        """Test validating ready with unsatisfied deps."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        
        unsatisfied = graph.validate_ready("B")
        assert "A" in unsatisfied
    
    def test_require_ready_raises(self):
        """Test require_ready raises on unsatisfied."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        
        with pytest.raises(UnsatisfiedDependencyError):
            graph.require_ready("B")


# =============================================================================
# TEST: IMPACT ANALYSIS
# =============================================================================

class TestImpactAnalysis:
    """Test impact analysis."""
    
    def test_analyze_impact(self):
        """Test impact analysis."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        
        analysis = graph.analyze_impact("A")
        assert "B" in analysis.directly_affected
        assert "C" in analysis.transitively_affected
        assert analysis.total_affected == 2
    
    def test_impact_analysis_serialization(self):
        """Test impact analysis serialization."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        
        analysis = graph.analyze_impact("A")
        data = analysis.to_dict()
        assert "changed_agent" in data
        assert data["changed_agent"] == "A"


# =============================================================================
# TEST: HEALTH CHECK
# =============================================================================

class TestHealthCheck:
    """Test health check functionality."""
    
    def test_healthy_graph(self):
        """Test healthy graph check."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.satisfy_dependency("A", "B")
        
        health = graph.check_health()
        assert health.status == HealthStatus.HEALTHY
    
    def test_unhealthy_failed_dependencies(self):
        """Test unhealthy due to failed deps."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        graph.fail_dependency("A", "B")
        
        health = graph.check_health()
        assert health.status == HealthStatus.UNHEALTHY
    
    def test_health_serialization(self):
        """Test health report serialization."""
        graph = create_dependency_graph()
        health = graph.check_health()
        data = health.to_dict()
        assert "status" in data
        assert "total_agents" in data


# =============================================================================
# TEST: SERIALIZATION
# =============================================================================

class TestSerialization:
    """Test graph serialization."""
    
    def test_graph_to_dict(self):
        """Test graph serialization."""
        graph = create_dependency_graph()
        graph.add_dependency("A", "B")
        
        data = graph.to_dict()
        assert "agents" in data
        assert "dependencies" in data
        assert "stats" in data


# =============================================================================
# TEST: FACTORY FUNCTIONS
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_dependency_graph(self):
        """Test creating graph via factory."""
        graph = create_dependency_graph()
        assert isinstance(graph, CrossAgentDependencyGraph)
    
    def test_create_dependency(self):
        """Test creating dependency via factory."""
        dep = create_dependency("A", "B")
        assert dep.source_agent == "A"
        assert dep.target_agent == "B"
        assert dep.strength == DependencyStrength.REQUIRED
