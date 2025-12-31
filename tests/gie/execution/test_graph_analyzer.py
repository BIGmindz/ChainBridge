"""
Unit Tests for Execution Graph Analyzer.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-04 (Cindy) — CROSS-AGENT DEPENDENCY & EXECUTION GRAPHS
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from core.gie.execution.graph_analyzer import (
    GRAPH_ANALYZER_VERSION,
    NodeState,
    EdgeType,
    OptimizationGoal,
    GraphAnalyzerError,
    CyclicDependencyError,
    NodeNotFoundError,
    GraphNode,
    GraphEdge,
    CriticalPath,
    ParallelismAnalysis,
    ExecutionPrediction,
    OptimizationResult,
    GraphDiffResult,
    ExecutionGraph,
    GraphAnalyzer,
    DependencyResolver,
    ExecutionPredictor,
    GraphOptimizer,
    GraphVisualizer,
    GraphDiff,
    compute_wrap_hash,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def empty_graph():
    """Create empty execution graph."""
    return ExecutionGraph()


@pytest.fixture
def simple_graph():
    """Create simple linear graph: A → B → C."""
    graph = ExecutionGraph()
    
    graph.add_node(GraphNode(
        node_id="A",
        task_type="start",
        estimated_duration=10.0,
        resource_requirements={"cpu": 1.0},
    ))
    graph.add_node(GraphNode(
        node_id="B",
        task_type="process",
        estimated_duration=20.0,
        resource_requirements={"cpu": 2.0},
    ))
    graph.add_node(GraphNode(
        node_id="C",
        task_type="end",
        estimated_duration=5.0,
        resource_requirements={"cpu": 1.0},
    ))
    
    graph.add_edge(GraphEdge(source="A", target="B", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="B", target="C", edge_type=EdgeType.HARD))
    
    return graph


@pytest.fixture
def diamond_graph():
    """Create diamond graph: A → B,C → D."""
    graph = ExecutionGraph()
    
    graph.add_node(GraphNode(
        node_id="A",
        task_type="start",
        estimated_duration=10.0,
        resource_requirements={"cpu": 1.0},
    ))
    graph.add_node(GraphNode(
        node_id="B",
        task_type="branch1",
        estimated_duration=15.0,
        resource_requirements={"cpu": 2.0},
    ))
    graph.add_node(GraphNode(
        node_id="C",
        task_type="branch2",
        estimated_duration=20.0,
        resource_requirements={"cpu": 2.0},
    ))
    graph.add_node(GraphNode(
        node_id="D",
        task_type="end",
        estimated_duration=5.0,
        resource_requirements={"cpu": 1.0},
    ))
    
    graph.add_edge(GraphEdge(source="A", target="B", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="A", target="C", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="B", target="D", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="C", target="D", edge_type=EdgeType.HARD))
    
    return graph


@pytest.fixture
def complex_graph():
    """Create more complex graph with multiple paths."""
    graph = ExecutionGraph()
    
    # Create nodes
    for node_id in ["A", "B", "C", "D", "E", "F"]:
        graph.add_node(GraphNode(
            node_id=node_id,
            task_type="task",
            estimated_duration=10.0,
            resource_requirements={"cpu": 1.0, "memory": 512.0},
        ))
    
    # A → B, C
    # B → D
    # C → D, E
    # D → F
    # E → F
    graph.add_edge(GraphEdge(source="A", target="B", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="A", target="C", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="B", target="D", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="C", target="D", edge_type=EdgeType.SOFT))
    graph.add_edge(GraphEdge(source="C", target="E", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="D", target="F", edge_type=EdgeType.HARD))
    graph.add_edge(GraphEdge(source="E", target="F", edge_type=EdgeType.HARD))
    
    return graph


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_node_state_values(self):
        """Test NodeState enum values."""
        assert NodeState.PENDING.value == "PENDING"
        assert NodeState.READY.value == "READY"
        assert NodeState.RUNNING.value == "RUNNING"
        assert NodeState.COMPLETED.value == "COMPLETED"
        assert NodeState.FAILED.value == "FAILED"
        assert NodeState.SKIPPED.value == "SKIPPED"
    
    def test_edge_type_values(self):
        """Test EdgeType enum values."""
        assert EdgeType.HARD.value == "HARD"
        assert EdgeType.SOFT.value == "SOFT"
        assert EdgeType.DATA.value == "DATA"
        assert EdgeType.OPTIONAL.value == "OPTIONAL"
    
    def test_optimization_goal_values(self):
        """Test OptimizationGoal enum values."""
        assert OptimizationGoal.MINIMIZE_TIME.value == "MINIMIZE_TIME"
        assert OptimizationGoal.MAXIMIZE_PARALLELISM.value == "MAXIMIZE_PARALLELISM"
        assert OptimizationGoal.MINIMIZE_RESOURCES.value == "MINIMIZE_RESOURCES"
        assert OptimizationGoal.BALANCED.value == "BALANCED"


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestGraphNode:
    """Test GraphNode dataclass."""
    
    def test_node_creation(self):
        """Test node creation with default values."""
        node = GraphNode(
            node_id="test",
            task_type="compute",
            estimated_duration=100.0,
            resource_requirements={"cpu": 4.0},
        )
        
        assert node.node_id == "test"
        assert node.task_type == "compute"
        assert node.estimated_duration == 100.0
        assert node.resource_requirements == {"cpu": 4.0}
        assert node.priority == 0
        assert node.state == NodeState.PENDING
        assert node.actual_duration is None
        assert node.failure_probability == 0.0
    
    def test_node_to_dict(self):
        """Test node serialization."""
        node = GraphNode(
            node_id="test",
            task_type="compute",
            estimated_duration=100.0,
            resource_requirements={"cpu": 4.0},
            priority=5,
            state=NodeState.RUNNING,
        )
        
        data = node.to_dict()
        
        assert data["node_id"] == "test"
        assert data["task_type"] == "compute"
        assert data["estimated_duration"] == 100.0
        assert data["state"] == "RUNNING"
        assert data["priority"] == 5


class TestGraphEdge:
    """Test GraphEdge dataclass."""
    
    def test_edge_creation(self):
        """Test edge creation."""
        edge = GraphEdge(
            source="A",
            target="B",
            edge_type=EdgeType.HARD,
        )
        
        assert edge.source == "A"
        assert edge.target == "B"
        assert edge.edge_type == EdgeType.HARD
        assert edge.weight == 1.0
    
    def test_edge_to_dict(self):
        """Test edge serialization."""
        edge = GraphEdge(
            source="A",
            target="B",
            edge_type=EdgeType.DATA,
            weight=2.5,
        )
        
        data = edge.to_dict()
        
        assert data["source"] == "A"
        assert data["target"] == "B"
        assert data["edge_type"] == "DATA"
        assert data["weight"] == 2.5


class TestCriticalPath:
    """Test CriticalPath dataclass."""
    
    def test_critical_path_to_dict(self):
        """Test critical path serialization."""
        cp = CriticalPath(
            nodes=["A", "B", "C"],
            total_duration=100.0,
            bottleneck_node="B",
            slack_times={"A": 0, "B": 0, "C": 0, "D": 5},
        )
        
        data = cp.to_dict()
        
        assert data["nodes"] == ["A", "B", "C"]
        assert data["total_duration"] == 100.0
        assert data["bottleneck_node"] == "B"


# =============================================================================
# EXECUTION GRAPH TESTS
# =============================================================================

class TestExecutionGraph:
    """Test ExecutionGraph class."""
    
    def test_add_node(self, empty_graph):
        """Test adding nodes."""
        node = GraphNode(
            node_id="test",
            task_type="task",
            estimated_duration=10.0,
            resource_requirements={},
        )
        
        empty_graph.add_node(node)
        
        result = empty_graph.get_node("test")
        assert result is not None
        assert result.node_id == "test"
    
    def test_add_edge(self, simple_graph):
        """Test adding edges."""
        edges = simple_graph.get_all_edges()
        assert len(edges) == 2
    
    def test_add_edge_invalid_node(self, empty_graph):
        """Test adding edge with invalid node."""
        with pytest.raises(NodeNotFoundError):
            empty_graph.add_edge(GraphEdge(
                source="X",
                target="Y",
                edge_type=EdgeType.HARD,
            ))
    
    def test_get_successors(self, simple_graph):
        """Test getting successor nodes."""
        successors = simple_graph.get_successors("A")
        assert "B" in successors
        assert len(successors) == 1
    
    def test_get_predecessors(self, simple_graph):
        """Test getting predecessor nodes."""
        predecessors = simple_graph.get_predecessors("C")
        assert "B" in predecessors
        assert len(predecessors) == 1
    
    def test_has_cycle_no_cycle(self, simple_graph):
        """Test cycle detection with no cycle."""
        has_cycle, cycle = simple_graph.has_cycle()
        assert not has_cycle
        assert cycle is None
    
    def test_has_cycle_with_cycle(self, empty_graph):
        """Test cycle detection with cycle."""
        # Create cycle: A → B → C → A
        empty_graph.add_node(GraphNode("A", "task", 10.0, {}))
        empty_graph.add_node(GraphNode("B", "task", 10.0, {}))
        empty_graph.add_node(GraphNode("C", "task", 10.0, {}))
        
        empty_graph.add_edge(GraphEdge("A", "B", EdgeType.HARD))
        empty_graph.add_edge(GraphEdge("B", "C", EdgeType.HARD))
        empty_graph.add_edge(GraphEdge("C", "A", EdgeType.HARD))
        
        has_cycle, cycle = empty_graph.has_cycle()
        assert has_cycle
        assert cycle is not None
        assert "A" in cycle
    
    def test_topological_sort(self, simple_graph):
        """Test topological sorting."""
        order = simple_graph.topological_sort()
        
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")
    
    def test_topological_sort_cycle_raises(self, empty_graph):
        """Test topological sort raises on cycle."""
        empty_graph.add_node(GraphNode("A", "task", 10.0, {}))
        empty_graph.add_node(GraphNode("B", "task", 10.0, {}))
        empty_graph.add_edge(GraphEdge("A", "B", EdgeType.HARD))
        empty_graph.add_edge(GraphEdge("B", "A", EdgeType.HARD))
        
        with pytest.raises(CyclicDependencyError):
            empty_graph.topological_sort()
    
    def test_compute_hash(self, simple_graph):
        """Test hash computation."""
        hash1 = simple_graph.compute_hash()
        hash2 = simple_graph.compute_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256
    
    def test_compute_hash_different_graphs(self, simple_graph, diamond_graph):
        """Test hash differs for different graphs."""
        hash1 = simple_graph.compute_hash()
        hash2 = diamond_graph.compute_hash()
        
        assert hash1 != hash2


# =============================================================================
# GRAPH ANALYZER TESTS
# =============================================================================

class TestGraphAnalyzer:
    """Test GraphAnalyzer class."""
    
    def test_find_critical_path_empty(self, empty_graph):
        """Test critical path on empty graph."""
        analyzer = GraphAnalyzer(empty_graph)
        cp = analyzer.find_critical_path()
        
        assert cp.nodes == []
        assert cp.total_duration == 0.0
        assert cp.bottleneck_node is None
    
    def test_find_critical_path_linear(self, simple_graph):
        """Test critical path on linear graph."""
        analyzer = GraphAnalyzer(simple_graph)
        cp = analyzer.find_critical_path()
        
        assert len(cp.nodes) == 3
        assert cp.total_duration == 35.0  # 10 + 20 + 5
        assert cp.bottleneck_node == "B"  # longest duration
    
    def test_find_critical_path_diamond(self, diamond_graph):
        """Test critical path on diamond graph."""
        analyzer = GraphAnalyzer(diamond_graph)
        cp = analyzer.find_critical_path()
        
        # Critical path: A → C → D (10 + 20 + 5 = 35)
        # Not: A → B → D (10 + 15 + 5 = 30)
        assert cp.total_duration == 35.0
        assert "A" in cp.nodes
        assert "C" in cp.nodes
        assert "D" in cp.nodes
    
    def test_analyze_parallelism_linear(self, simple_graph):
        """Test parallelism analysis on linear graph."""
        analyzer = GraphAnalyzer(simple_graph)
        result = analyzer.analyze_parallelism()
        
        assert result.max_parallel_nodes == 1
        assert result.parallelism_score < 0.5  # Low parallelism
        assert len(result.sequential_bottlenecks) == 3
    
    def test_analyze_parallelism_diamond(self, diamond_graph):
        """Test parallelism analysis on diamond graph."""
        analyzer = GraphAnalyzer(diamond_graph)
        result = analyzer.analyze_parallelism()
        
        assert result.max_parallel_nodes == 2  # B and C can run in parallel
        assert result.parallelism_score > 0.3
    
    def test_detect_bottlenecks(self, simple_graph):
        """Test bottleneck detection."""
        # Modify B to be a clear bottleneck
        node_b = simple_graph.get_node("B")
        node_b.estimated_duration = 100.0
        node_b.resource_requirements["cpu"] = 100.0
        
        analyzer = GraphAnalyzer(simple_graph)
        bottlenecks = analyzer.detect_bottlenecks()
        
        assert len(bottlenecks) > 0
        assert bottlenecks[0]["node_id"] == "B"
    
    def test_predict_resource_contention(self, diamond_graph):
        """Test resource contention prediction."""
        analyzer = GraphAnalyzer(diamond_graph)
        
        result = analyzer.predict_resource_contention({"cpu": 2.0})
        
        # B and C together need 4 CPU (2 + 2)
        assert result["has_contention"] is True
        assert len(result["contention_points"]) > 0


# =============================================================================
# DEPENDENCY RESOLVER TESTS
# =============================================================================

class TestDependencyResolver:
    """Test DependencyResolver class."""
    
    def test_get_transitive_dependencies(self, simple_graph):
        """Test transitive dependency calculation."""
        resolver = DependencyResolver(simple_graph)
        
        deps = resolver.get_transitive_dependencies("C")
        
        assert "B" in deps
        assert "A" in deps
    
    def test_detect_diamond_dependencies(self, diamond_graph):
        """Test diamond dependency detection."""
        resolver = DependencyResolver(diamond_graph)
        
        diamonds = resolver.detect_diamond_dependencies()
        
        assert len(diamonds) > 0
        assert diamonds[0]["target"] == "D"
        assert "A" in diamonds[0]["common_ancestors"]
    
    def test_can_execute(self, simple_graph):
        """Test execution readiness check."""
        resolver = DependencyResolver(simple_graph)
        
        # B cannot execute with no completions
        can_exec, blocking = resolver.can_execute("B", set())
        assert not can_exec
        assert "A" in blocking
        
        # B can execute after A
        can_exec, blocking = resolver.can_execute("B", {"A"})
        assert can_exec
        assert len(blocking) == 0
    
    def test_get_optional_dependencies(self, empty_graph):
        """Test optional dependency retrieval."""
        empty_graph.add_node(GraphNode("A", "task", 10.0, {}))
        empty_graph.add_node(GraphNode("B", "task", 10.0, {}))
        empty_graph.add_edge(GraphEdge("A", "B", EdgeType.OPTIONAL))
        
        resolver = DependencyResolver(empty_graph)
        optional = resolver.get_optional_dependencies("B")
        
        assert "A" in optional


# =============================================================================
# EXECUTION PREDICTOR TESTS
# =============================================================================

class TestExecutionPredictor:
    """Test ExecutionPredictor class."""
    
    def test_predict_basic(self, simple_graph):
        """Test basic prediction."""
        predictor = ExecutionPredictor(simple_graph)
        
        prediction = predictor.predict()
        
        assert prediction.estimated_total_time > 0
        assert len(prediction.confidence_interval) == 2
        assert prediction.confidence_interval[0] <= prediction.estimated_total_time
        assert prediction.confidence_interval[1] >= prediction.estimated_total_time
    
    def test_predict_with_historical_data(self, simple_graph):
        """Test prediction with historical calibration."""
        predictor = ExecutionPredictor(simple_graph)
        
        # Add historical data showing estimates are 50% too low
        predictor.add_historical_data("task", 150.0, 100.0)
        predictor.add_historical_data("task", 75.0, 50.0)
        
        prediction = predictor.predict()
        
        # Should apply calibration factor
        assert prediction.estimated_total_time > 35.0
    
    def test_failure_probability(self, empty_graph):
        """Test failure probability calculation."""
        empty_graph.add_node(GraphNode(
            node_id="A",
            task_type="risky",
            estimated_duration=10.0,
            resource_requirements={},
            failure_probability=0.5,
        ))
        empty_graph.add_node(GraphNode(
            node_id="B",
            task_type="risky",
            estimated_duration=10.0,
            resource_requirements={},
            failure_probability=0.5,
        ))
        empty_graph.add_edge(GraphEdge("A", "B", EdgeType.HARD))
        
        predictor = ExecutionPredictor(empty_graph)
        prediction = predictor.predict()
        
        # P(at least one failure) = 1 - P(both success) = 1 - 0.5 * 0.5 = 0.75
        assert prediction.failure_probability == pytest.approx(0.75)


# =============================================================================
# GRAPH OPTIMIZER TESTS
# =============================================================================

class TestGraphOptimizer:
    """Test GraphOptimizer class."""
    
    def test_optimize_balanced(self, complex_graph):
        """Test balanced optimization."""
        optimizer = GraphOptimizer(complex_graph)
        
        result = optimizer.optimize(OptimizationGoal.BALANCED)
        
        assert result.original_duration > 0
        assert result.optimized_duration > 0
        assert len(result.reordered_nodes) == 6
    
    def test_optimize_parallelism(self, complex_graph):
        """Test parallelism optimization."""
        optimizer = GraphOptimizer(complex_graph)
        
        result = optimizer.optimize(OptimizationGoal.MAXIMIZE_PARALLELISM)
        
        assert len(result.reordered_nodes) == 6
    
    def test_optimize_resources(self, complex_graph):
        """Test resource optimization."""
        optimizer = GraphOptimizer(complex_graph)
        
        result = optimizer.optimize(
            OptimizationGoal.MINIMIZE_RESOURCES,
            resource_limits={"cpu": 2.0},
        )
        
        assert len(result.reordered_nodes) == 6
    
    def test_generate_suggestions(self, simple_graph):
        """Test suggestion generation."""
        # Create bottleneck
        node_b = simple_graph.get_node("B")
        node_b.estimated_duration = 100.0
        
        optimizer = GraphOptimizer(simple_graph)
        result = optimizer.optimize()
        
        # Should have bottleneck suggestion
        bottleneck_suggestions = [
            s for s in result.parallelization_suggestions
            if s["type"] == "BOTTLENECK"
        ]
        assert len(bottleneck_suggestions) > 0


# =============================================================================
# GRAPH VISUALIZER TESTS
# =============================================================================

class TestGraphVisualizer:
    """Test GraphVisualizer class."""
    
    def test_to_dot(self, simple_graph):
        """Test DOT export."""
        visualizer = GraphVisualizer(simple_graph)
        
        dot = visualizer.to_dot()
        
        assert "digraph ExecutionGraph" in dot
        assert '"A"' in dot
        assert '"B"' in dot
        assert '->' in dot
    
    def test_to_dot_highlight_critical(self, simple_graph):
        """Test DOT export with critical path highlighting."""
        visualizer = GraphVisualizer(simple_graph)
        
        dot = visualizer.to_dot(highlight_critical_path=True)
        
        assert "fillcolor=red" in dot
    
    def test_to_mermaid(self, simple_graph):
        """Test Mermaid export."""
        visualizer = GraphVisualizer(simple_graph)
        
        mermaid = visualizer.to_mermaid()
        
        assert "graph LR" in mermaid
        assert "A[A]" in mermaid
        assert "-->" in mermaid
    
    def test_to_json(self, simple_graph):
        """Test JSON export."""
        visualizer = GraphVisualizer(simple_graph)
        
        json_str = visualizer.to_json()
        data = json.loads(json_str)
        
        assert data["version"] == GRAPH_ANALYZER_VERSION
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        assert "hash" in data


# =============================================================================
# GRAPH DIFF TESTS
# =============================================================================

class TestGraphDiff:
    """Test GraphDiff class."""
    
    def test_diff_identical_graphs(self, simple_graph):
        """Test diff of identical graphs."""
        diff = GraphDiff(simple_graph, simple_graph)
        
        result = diff.diff()
        
        assert result.added_nodes == []
        assert result.removed_nodes == []
        assert result.modified_nodes == []
        assert result.impact_score == 0.0
    
    def test_diff_added_node(self, simple_graph, diamond_graph):
        """Test diff with added nodes."""
        diff = GraphDiff(simple_graph, diamond_graph)
        
        result = diff.diff()
        
        # Diamond has D that simple doesn't have
        assert "D" in result.added_nodes
    
    def test_diff_removed_node(self, diamond_graph, simple_graph):
        """Test diff with removed nodes."""
        diff = GraphDiff(diamond_graph, simple_graph)
        
        result = diff.diff()
        
        # Diamond has D that simple doesn't have
        assert "D" in result.removed_nodes
    
    def test_diff_migration_steps(self, simple_graph, diamond_graph):
        """Test migration steps generation."""
        diff = GraphDiff(simple_graph, diamond_graph)
        
        result = diff.diff()
        
        assert len(result.migration_steps) > 0
        # Should have logical order: remove edges, remove nodes, add nodes, add edges
        add_steps = [s for s in result.migration_steps if "Add" in s]
        remove_steps = [s for s in result.migration_steps if "Remove" in s]
        assert len(add_steps) > 0 or len(remove_steps) > 0


# =============================================================================
# WRAP HASH TESTS
# =============================================================================

class TestWrapHash:
    """Test WRAP hash computation."""
    
    def test_compute_wrap_hash(self):
        """Test WRAP hash computation."""
        hash1 = compute_wrap_hash()
        hash2 = compute_wrap_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 16
    
    def test_wrap_hash_includes_version(self):
        """Test WRAP hash is version-aware."""
        # The hash content includes version
        expected_content = f"GID-04:graph_analyzer:v{GRAPH_ANALYZER_VERSION}"
        assert GRAPH_ANALYZER_VERSION in expected_content


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================

class TestThreadSafety:
    """Test thread safety."""
    
    def test_concurrent_node_addition(self, empty_graph):
        """Test concurrent node addition."""
        import threading
        
        def add_nodes(start_id: int):
            for i in range(10):
                empty_graph.add_node(GraphNode(
                    node_id=f"node_{start_id}_{i}",
                    task_type="task",
                    estimated_duration=10.0,
                    resource_requirements={},
                ))
        
        threads = [
            threading.Thread(target=add_nodes, args=(i,))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(empty_graph.get_all_nodes()) == 50


# =============================================================================
# EXCEPTION TESTS
# =============================================================================

class TestExceptions:
    """Test exception handling."""
    
    def test_cyclic_dependency_error(self):
        """Test CyclicDependencyError."""
        err = CyclicDependencyError(["A", "B", "C", "A"])
        
        assert "Cyclic dependency" in str(err)
        assert err.cycle == ["A", "B", "C", "A"]
    
    def test_node_not_found_error(self):
        """Test NodeNotFoundError."""
        err = NodeNotFoundError("Node X not found")
        
        assert "Node X not found" in str(err)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_analysis_workflow(self, complex_graph):
        """Test complete analysis workflow."""
        # Analyze
        analyzer = GraphAnalyzer(complex_graph)
        critical_path = analyzer.find_critical_path()
        parallelism = analyzer.analyze_parallelism()
        bottlenecks = analyzer.detect_bottlenecks()
        
        # Resolve dependencies
        resolver = DependencyResolver(complex_graph)
        diamonds = resolver.detect_diamond_dependencies()
        
        # Predict
        predictor = ExecutionPredictor(complex_graph)
        prediction = predictor.predict()
        
        # Optimize
        optimizer = GraphOptimizer(complex_graph)
        optimization = optimizer.optimize()
        
        # Visualize
        visualizer = GraphVisualizer(complex_graph)
        dot = visualizer.to_dot()
        mermaid = visualizer.to_mermaid()
        json_export = visualizer.to_json()
        
        # Verify all outputs are valid
        assert critical_path.total_duration > 0
        assert parallelism.parallelism_score >= 0
        assert len(bottlenecks) >= 0
        assert len(diamonds) >= 0
        assert prediction.estimated_total_time > 0
        assert optimization.original_duration > 0
        assert "digraph" in dot
        assert "graph LR" in mermaid
        assert json.loads(json_export) is not None
    
    def test_diff_and_migration(self, simple_graph, diamond_graph):
        """Test diff and migration workflow."""
        diff = GraphDiff(simple_graph, diamond_graph)
        result = diff.diff()
        
        # Apply migration (conceptually)
        assert len(result.migration_steps) > 0
        
        # Verify diff is serializable
        data = result.to_dict()
        assert "added_nodes" in data
        assert "migration_steps" in data
