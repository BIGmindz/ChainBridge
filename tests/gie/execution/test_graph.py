"""
Test GIE Execution Graph

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-01 (Cody) — Senior Backend Engineer
"""

import pytest
from typing import List, Set

from core.gie.execution.graph import (
    # Enums
    NodeStatus,
    EdgeType,
    
    # Exceptions
    GraphError,
    CircularDependencyError,
    NodeNotFoundError,
    DuplicateNodeError,
    InvalidDependencyError,
    
    # Data classes
    ExecutionNode,
    DependencyEdge,
    ExecutionLevel,
    
    # Classes
    ExecutionGraph,
    DependencyResolver,
    
    # Factory
    create_execution_graph,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def empty_graph():
    """Provide empty execution graph."""
    return ExecutionGraph("TEST-GRAPH")


@pytest.fixture
def simple_graph():
    """Provide simple linear graph: A → B → C"""
    graph = ExecutionGraph("SIMPLE")
    graph.add_node("A", "task")
    graph.add_node("B", "task")
    graph.add_node("C", "task")
    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    return graph


@pytest.fixture
def diamond_graph():
    """
    Provide diamond-shaped graph:
        A
       / \
      B   C
       \ /
        D
    """
    graph = ExecutionGraph("DIAMOND")
    graph.add_node("A", "start")
    graph.add_node("B", "process")
    graph.add_node("C", "process")
    graph.add_node("D", "end")
    graph.add_dependency("A", "B")
    graph.add_dependency("A", "C")
    graph.add_dependency("B", "D")
    graph.add_dependency("C", "D")
    return graph


@pytest.fixture
def resolver():
    """Provide dependency resolver."""
    return DependencyResolver()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionNode
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionNode:
    """Tests for ExecutionNode dataclass."""

    def test_creation(self):
        """Can create execution node."""
        node = ExecutionNode(
            node_id="TEST-001",
            task_type="validate",
            payload={"key": "value"},
        )
        assert node.node_id == "TEST-001"
        assert node.task_type == "validate"
        assert node.status == NodeStatus.PENDING

    def test_to_dict(self):
        """Can convert to dictionary."""
        node = ExecutionNode("N1", "task")
        result = node.to_dict()
        assert result["node_id"] == "N1"
        assert result["status"] == "PENDING"

    def test_compute_hash_deterministic(self):
        """Hash is deterministic."""
        node1 = ExecutionNode("N1", "task", {"a": 1})
        node2 = ExecutionNode("N1", "task", {"a": 1})
        assert node1.compute_hash() == node2.compute_hash()

    def test_compute_hash_different_payloads(self):
        """Different payloads produce different hashes."""
        node1 = ExecutionNode("N1", "task", {"a": 1})
        node2 = ExecutionNode("N1", "task", {"a": 2})
        assert node1.compute_hash() != node2.compute_hash()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionGraph - Basic Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionGraphBasic:
    """Tests for basic ExecutionGraph operations."""

    def test_create_empty_graph(self, empty_graph):
        """Can create empty graph."""
        assert empty_graph.node_count == 0
        assert empty_graph.edge_count == 0

    def test_add_node(self, empty_graph):
        """Can add node to graph."""
        node = empty_graph.add_node("A", "task")
        assert node.node_id == "A"
        assert empty_graph.node_count == 1

    def test_add_duplicate_node_raises(self, empty_graph):
        """Adding duplicate node raises."""
        empty_graph.add_node("A", "task")
        with pytest.raises(DuplicateNodeError):
            empty_graph.add_node("A", "task")

    def test_get_node(self, empty_graph):
        """Can get node by ID."""
        empty_graph.add_node("A", "task")
        node = empty_graph.get_node("A")
        assert node.node_id == "A"

    def test_get_missing_node_raises(self, empty_graph):
        """Getting missing node raises."""
        with pytest.raises(NodeNotFoundError):
            empty_graph.get_node("MISSING")

    def test_remove_node(self, empty_graph):
        """Can remove node."""
        empty_graph.add_node("A", "task")
        empty_graph.remove_node("A")
        assert empty_graph.node_count == 0

    def test_list_nodes(self, simple_graph):
        """Can list all nodes."""
        nodes = simple_graph.list_nodes()
        assert set(nodes) == {"A", "B", "C"}


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ExecutionGraph - Dependencies
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionGraphDependencies:
    """Tests for dependency operations."""

    def test_add_dependency(self, empty_graph):
        """Can add dependency between nodes."""
        empty_graph.add_node("A", "task")
        empty_graph.add_node("B", "task")
        edge = empty_graph.add_dependency("A", "B")
        
        assert edge.from_node == "A"
        assert edge.to_node == "B"
        assert empty_graph.edge_count == 1

    def test_get_dependencies(self, simple_graph):
        """Can get node dependencies."""
        deps = simple_graph.get_dependencies("B")
        assert deps == {"A"}

    def test_get_dependents(self, simple_graph):
        """Can get node dependents."""
        dependents = simple_graph.get_dependents("A")
        assert dependents == {"B"}

    def test_dependency_missing_from_node_raises(self, empty_graph):
        """Dependency with missing from node raises."""
        empty_graph.add_node("B", "task")
        with pytest.raises(NodeNotFoundError):
            empty_graph.add_dependency("MISSING", "B")

    def test_dependency_missing_to_node_raises(self, empty_graph):
        """Dependency with missing to node raises."""
        empty_graph.add_node("A", "task")
        with pytest.raises(NodeNotFoundError):
            empty_graph.add_dependency("A", "MISSING")

    def test_self_loop_raises(self, empty_graph):
        """Self-loop dependency raises."""
        empty_graph.add_node("A", "task")
        with pytest.raises(CircularDependencyError):
            empty_graph.add_dependency("A", "A")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Cycle Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestCycleDetection:
    """Tests for cycle detection."""

    def test_no_cycle_in_dag(self, simple_graph):
        """DAG has no cycle."""
        assert simple_graph.has_cycle() is False

    def test_detect_simple_cycle(self, empty_graph):
        """Detects simple A → B → A cycle."""
        empty_graph.add_node("A", "task")
        empty_graph.add_node("B", "task")
        empty_graph.add_dependency("A", "B")
        
        with pytest.raises(CircularDependencyError) as exc:
            empty_graph.add_dependency("B", "A")
        
        assert "A" in exc.value.cycle
        assert "B" in exc.value.cycle

    def test_detect_longer_cycle(self, empty_graph):
        """Detects A → B → C → A cycle."""
        empty_graph.add_node("A", "task")
        empty_graph.add_node("B", "task")
        empty_graph.add_node("C", "task")
        empty_graph.add_dependency("A", "B")
        empty_graph.add_dependency("B", "C")
        
        with pytest.raises(CircularDependencyError):
            empty_graph.add_dependency("C", "A")

    def test_diamond_no_cycle(self, diamond_graph):
        """Diamond shape is not a cycle."""
        assert diamond_graph.has_cycle() is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Topological Sort
# ═══════════════════════════════════════════════════════════════════════════════

class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_simple_topo_sort(self, simple_graph):
        """Topological sort of A → B → C."""
        order = simple_graph.topological_sort()
        
        # A must come before B, B before C
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")

    def test_diamond_topo_sort(self, diamond_graph):
        """Topological sort of diamond graph."""
        order = diamond_graph.topological_sort()
        
        # A first, D last, B and C in middle
        assert order[0] == "A"
        assert order[-1] == "D"
        assert set(order[1:3]) == {"B", "C"}

    def test_empty_graph_topo_sort(self, empty_graph):
        """Empty graph returns empty list."""
        assert empty_graph.topological_sort() == []

    def test_single_node_topo_sort(self, empty_graph):
        """Single node graph returns that node."""
        empty_graph.add_node("A", "task")
        assert empty_graph.topological_sort() == ["A"]

    def test_topo_sort_cached(self, simple_graph):
        """Topological sort is cached."""
        order1 = simple_graph.topological_sort()
        order2 = simple_graph.topological_sort()
        assert order1 == order2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Execution Levels
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionLevels:
    """Tests for parallel execution levels."""

    def test_simple_levels(self, simple_graph):
        """Simple graph has 3 levels."""
        levels = simple_graph.get_execution_levels()
        assert len(levels) == 3
        assert levels[0].node_ids == ["A"]
        assert levels[1].node_ids == ["B"]
        assert levels[2].node_ids == ["C"]

    def test_diamond_levels(self, diamond_graph):
        """Diamond graph has 3 levels with parallel middle."""
        levels = diamond_graph.get_execution_levels()
        assert len(levels) == 3
        assert levels[0].node_ids == ["A"]
        assert set(levels[1].node_ids) == {"B", "C"}  # Parallel
        assert levels[2].node_ids == ["D"]

    def test_parallel_start_nodes(self, empty_graph):
        """Multiple nodes with no dependencies are parallel."""
        empty_graph.add_node("A", "task")
        empty_graph.add_node("B", "task")
        empty_graph.add_node("C", "task")
        
        levels = empty_graph.get_execution_levels()
        assert len(levels) == 1
        assert set(levels[0].node_ids) == {"A", "B", "C"}


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Ready Nodes
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadyNodes:
    """Tests for ready node detection."""

    def test_initial_ready_nodes(self, simple_graph):
        """Initially only root nodes are ready."""
        ready = simple_graph.get_ready_nodes()
        assert ready == ["A"]

    def test_ready_after_completion(self, simple_graph):
        """Next nodes become ready after completion."""
        simple_graph.mark_completed("A")
        ready = simple_graph.get_ready_nodes()
        assert ready == ["B"]

    def test_diamond_ready_nodes(self, diamond_graph):
        """Diamond: B and C ready after A completes."""
        diamond_graph.mark_completed("A")
        ready = diamond_graph.get_ready_nodes()
        assert set(ready) == {"B", "C"}

    def test_diamond_d_ready_after_bc(self, diamond_graph):
        """Diamond: D ready only after both B and C complete."""
        diamond_graph.mark_completed("A")
        diamond_graph.mark_completed("B")
        
        # C not complete, D not ready
        ready = diamond_graph.get_ready_nodes()
        assert "D" not in ready
        
        diamond_graph.mark_completed("C")
        ready = diamond_graph.get_ready_nodes()
        assert ready == ["D"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Execution State
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionState:
    """Tests for execution state tracking."""

    def test_mark_running(self, simple_graph):
        """Can mark node as running."""
        simple_graph.mark_running("A")
        node = simple_graph.get_node("A")
        assert node.status == NodeStatus.RUNNING
        assert node.started_at is not None

    def test_mark_completed(self, simple_graph):
        """Can mark node as completed."""
        simple_graph.mark_completed("A", result={"success": True})
        node = simple_graph.get_node("A")
        assert node.status == NodeStatus.COMPLETED
        assert node.result == {"success": True}

    def test_mark_failed(self, simple_graph):
        """Can mark node as failed."""
        simple_graph.mark_failed("A", "Test error")
        node = simple_graph.get_node("A")
        assert node.status == NodeStatus.FAILED
        assert node.error == "Test error"

    def test_is_complete(self, simple_graph):
        """Graph is complete when all nodes done."""
        assert simple_graph.is_complete() is False
        
        simple_graph.mark_completed("A")
        simple_graph.mark_completed("B")
        simple_graph.mark_completed("C")
        
        assert simple_graph.is_complete() is True

    def test_completion_summary(self, simple_graph):
        """Can get completion summary."""
        simple_graph.mark_completed("A")
        simple_graph.mark_failed("B", "error")
        
        summary = simple_graph.get_completion_summary()
        assert summary["COMPLETED"] == 1
        assert summary["FAILED"] == 1
        assert summary["PENDING"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Graph Hashing
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphHashing:
    """Tests for graph hashing."""

    def test_hash_deterministic(self, simple_graph):
        """Graph hash is deterministic."""
        hash1 = simple_graph.compute_graph_hash()
        hash2 = simple_graph.compute_graph_hash()
        assert hash1 == hash2

    def test_hash_starts_with_sha256(self, simple_graph):
        """Hash has sha256 prefix."""
        hash_val = simple_graph.compute_graph_hash()
        assert hash_val.startswith("sha256:")

    def test_different_graphs_different_hashes(self, simple_graph, diamond_graph):
        """Different graphs have different hashes."""
        hash1 = simple_graph.compute_graph_hash()
        hash2 = diamond_graph.compute_graph_hash()
        assert hash1 != hash2

    def test_to_dict(self, simple_graph):
        """Can convert graph to dictionary."""
        result = simple_graph.to_dict()
        assert result["graph_id"] == "SIMPLE"
        assert result["node_count"] == 3
        assert result["edge_count"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: DependencyResolver
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyResolver:
    """Tests for DependencyResolver."""

    def test_resolve_simple(self, resolver, simple_graph):
        """Can resolve simple graph."""
        levels = resolver.resolve(simple_graph)
        assert len(levels) == 3

    def test_validate_valid_graph(self, resolver, simple_graph):
        """Validates valid graph."""
        valid, errors = resolver.validate_dependencies(simple_graph)
        assert valid is True
        assert len(errors) == 0

    def test_find_critical_path_simple(self, resolver, simple_graph):
        """Finds critical path in simple graph."""
        path = resolver.find_critical_path(simple_graph)
        assert path == ["A", "B", "C"]

    def test_find_critical_path_diamond(self, resolver, diamond_graph):
        """Finds critical path in diamond graph."""
        path = resolver.find_critical_path(diamond_graph)
        # Either A→B→D or A→C→D
        assert path[0] == "A"
        assert path[-1] == "D"
        assert len(path) == 3

    def test_validate_required_types(self, resolver, simple_graph):
        """Can validate required task types."""
        # All have type "task"
        valid, errors = resolver.validate_dependencies(
            simple_graph,
            required_types={"task"},
        )
        assert valid is True
        
        # Missing type
        valid, errors = resolver.validate_dependencies(
            simple_graph,
            required_types={"task", "special"},
        )
        assert valid is False
        assert any("Missing" in e for e in errors)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Factory Function
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactory:
    """Tests for factory function."""

    def test_create_graph(self):
        """Can create graph from factory."""
        tasks = [
            {"id": "A", "type": "start"},
            {"id": "B", "type": "process"},
            {"id": "C", "type": "end"},
        ]
        deps = [("A", "B"), ("B", "C")]
        
        graph = create_execution_graph("TEST", tasks, deps)
        
        assert graph.node_count == 3
        assert graph.edge_count == 2

    def test_create_graph_with_payload(self):
        """Can create graph with payloads."""
        tasks = [
            {"id": "A", "type": "task", "payload": {"key": "value"}},
        ]
        
        graph = create_execution_graph("TEST", tasks, [])
        node = graph.get_node("A")
        assert node.payload == {"key": "value"}


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Thread Safety
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_node_operations(self, empty_graph):
        """Can handle concurrent node operations."""
        import threading
        
        errors = []
        
        def add_nodes(start: int):
            try:
                for i in range(start, start + 10):
                    empty_graph.add_node(f"N{i}", "task")
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=add_nodes, args=(i * 10,))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert empty_graph.node_count == 50


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""

    def test_remove_node_with_edges(self, simple_graph):
        """Removing node removes its edges."""
        simple_graph.remove_node("B")
        
        # A no longer has B as dependent
        assert "B" not in simple_graph.get_dependents("A")
        
        # C no longer has B as dependency
        assert "B" not in simple_graph.get_dependencies("C")

    def test_single_node_graph(self, empty_graph):
        """Single node graph works correctly."""
        empty_graph.add_node("ONLY", "task")
        
        assert empty_graph.topological_sort() == ["ONLY"]
        assert empty_graph.get_ready_nodes() == ["ONLY"]
        
        levels = empty_graph.get_execution_levels()
        assert len(levels) == 1

    def test_wide_parallel_graph(self, empty_graph):
        """Many parallel nodes at same level."""
        for i in range(100):
            empty_graph.add_node(f"N{i}", "parallel")
        
        levels = empty_graph.get_execution_levels()
        assert len(levels) == 1
        assert len(levels[0]) == 100

    def test_deep_chain_graph(self, empty_graph):
        """Long chain of dependencies."""
        for i in range(50):
            empty_graph.add_node(f"N{i}", "chain")
        
        for i in range(49):
            empty_graph.add_dependency(f"N{i}", f"N{i+1}")
        
        levels = empty_graph.get_execution_levels()
        assert len(levels) == 50
        
        path = DependencyResolver().find_critical_path(empty_graph)
        assert len(path) == 50
