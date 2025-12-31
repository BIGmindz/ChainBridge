"""
Execution Graph Analyzer — Advanced DAG Analysis & Optimization.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-04 (Cindy) — CROSS-AGENT DEPENDENCY & EXECUTION GRAPHS
Deliverable: Graph Analyzer, Optimizer, Predictor, Visualizer

Features:
- Critical path identification
- Bottleneck detection
- Parallelism opportunity scoring
- Execution time prediction
- Graph optimization
- Multiple export formats (DOT, Mermaid, JSON)
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
)


# =============================================================================
# VERSION
# =============================================================================

GRAPH_ANALYZER_VERSION = "1.0.0"


# =============================================================================
# ENUMS
# =============================================================================

class NodeState(Enum):
    """Node execution state."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EdgeType(Enum):
    """Edge dependency type."""
    HARD = "HARD"      # Must complete successfully
    SOFT = "SOFT"      # Can continue if failed
    DATA = "DATA"      # Data dependency
    OPTIONAL = "OPTIONAL"  # Optional dependency


class OptimizationGoal(Enum):
    """Optimization goals."""
    MINIMIZE_TIME = "MINIMIZE_TIME"
    MAXIMIZE_PARALLELISM = "MAXIMIZE_PARALLELISM"
    MINIMIZE_RESOURCES = "MINIMIZE_RESOURCES"
    BALANCED = "BALANCED"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class GraphAnalyzerError(Exception):
    """Base exception for graph analyzer."""
    pass


class CyclicDependencyError(GraphAnalyzerError):
    """Cyclic dependency detected."""
    def __init__(self, cycle: List[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Cyclic dependency: {' → '.join(cycle)}")


class NodeNotFoundError(GraphAnalyzerError):
    """Node not found in graph."""
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GraphNode:
    """A node in the execution graph."""
    node_id: str
    task_type: str
    estimated_duration: float  # seconds
    resource_requirements: Dict[str, float]
    priority: int = 0
    state: NodeState = NodeState.PENDING
    actual_duration: Optional[float] = None
    failure_probability: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "task_type": self.task_type,
            "estimated_duration": self.estimated_duration,
            "resource_requirements": self.resource_requirements,
            "priority": self.priority,
            "state": self.state.value,
            "actual_duration": self.actual_duration,
            "failure_probability": self.failure_probability,
        }


@dataclass
class GraphEdge:
    """An edge in the execution graph."""
    source: str
    target: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
        }


@dataclass
class CriticalPath:
    """Critical path analysis result."""
    nodes: List[str]
    total_duration: float
    bottleneck_node: Optional[str]
    slack_times: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "nodes": self.nodes,
            "total_duration": self.total_duration,
            "bottleneck_node": self.bottleneck_node,
            "slack_times": self.slack_times,
        }


@dataclass
class ParallelismAnalysis:
    """Parallelism analysis result."""
    max_parallel_nodes: int
    parallelism_score: float  # 0.0 to 1.0
    parallel_groups: List[List[str]]
    sequential_bottlenecks: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_parallel_nodes": self.max_parallel_nodes,
            "parallelism_score": self.parallelism_score,
            "parallel_groups": self.parallel_groups,
            "sequential_bottlenecks": self.sequential_bottlenecks,
        }


@dataclass
class ExecutionPrediction:
    """Execution prediction result."""
    estimated_total_time: float
    confidence_interval: Tuple[float, float]  # (lower, upper)
    confidence_level: float  # 0.0 to 1.0
    resource_forecast: Dict[str, float]
    failure_probability: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "estimated_total_time": self.estimated_total_time,
            "confidence_interval": list(self.confidence_interval),
            "confidence_level": self.confidence_level,
            "resource_forecast": self.resource_forecast,
            "failure_probability": self.failure_probability,
        }


@dataclass
class OptimizationResult:
    """Graph optimization result."""
    original_duration: float
    optimized_duration: float
    improvement_percent: float
    reordered_nodes: List[str]
    parallelization_suggestions: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_duration": self.original_duration,
            "optimized_duration": self.optimized_duration,
            "improvement_percent": self.improvement_percent,
            "reordered_nodes": self.reordered_nodes,
            "parallelization_suggestions": self.parallelization_suggestions,
        }


@dataclass
class GraphDiffResult:
    """Graph comparison result."""
    added_nodes: List[str]
    removed_nodes: List[str]
    modified_nodes: List[str]
    added_edges: List[Tuple[str, str]]
    removed_edges: List[Tuple[str, str]]
    impact_score: float
    migration_steps: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "added_nodes": self.added_nodes,
            "removed_nodes": self.removed_nodes,
            "modified_nodes": self.modified_nodes,
            "added_edges": self.added_edges,
            "removed_edges": self.removed_edges,
            "impact_score": self.impact_score,
            "migration_steps": self.migration_steps,
        }


# =============================================================================
# EXECUTION GRAPH
# =============================================================================

class ExecutionGraph:
    """
    Directed Acyclic Graph for execution ordering.
    
    Provides the base graph structure for analysis.
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)  # node -> successors
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)  # node -> predecessors
    
    def add_node(self, node: GraphNode) -> None:
        """Add node to graph."""
        with self._lock:
            self._nodes[node.node_id] = node
    
    def add_edge(self, edge: GraphEdge) -> None:
        """Add edge to graph."""
        with self._lock:
            if edge.source not in self._nodes or edge.target not in self._nodes:
                raise NodeNotFoundError(
                    f"Edge references unknown node: {edge.source} → {edge.target}"
                )
            
            self._edges.append(edge)
            self._adjacency[edge.source].add(edge.target)
            self._reverse_adjacency[edge.target].add(edge.source)
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID."""
        return self._nodes.get(node_id)
    
    def get_successors(self, node_id: str) -> Set[str]:
        """Get successor node IDs."""
        return self._adjacency.get(node_id, set()).copy()
    
    def get_predecessors(self, node_id: str) -> Set[str]:
        """Get predecessor node IDs."""
        return self._reverse_adjacency.get(node_id, set()).copy()
    
    def get_all_nodes(self) -> List[GraphNode]:
        """Get all nodes."""
        return list(self._nodes.values())
    
    def get_all_edges(self) -> List[GraphEdge]:
        """Get all edges."""
        return list(self._edges)
    
    def has_cycle(self) -> Tuple[bool, Optional[List[str]]]:
        """
        Check if graph has cycles.
        
        Returns:
            Tuple of (has_cycle, cycle_nodes if found)
        """
        with self._lock:
            visited: Set[str] = set()
            rec_stack: Set[str] = set()
            path: List[str] = []
            
            def dfs(node_id: str) -> Optional[List[str]]:
                visited.add(node_id)
                rec_stack.add(node_id)
                path.append(node_id)
                
                for successor in self._adjacency.get(node_id, set()):
                    if successor not in visited:
                        cycle = dfs(successor)
                        if cycle:
                            return cycle
                    elif successor in rec_stack:
                        # Found cycle
                        cycle_start = path.index(successor)
                        return path[cycle_start:] + [successor]
                
                path.pop()
                rec_stack.remove(node_id)
                return None
            
            for node_id in self._nodes:
                if node_id not in visited:
                    cycle = dfs(node_id)
                    if cycle:
                        return True, cycle
            
            return False, None
    
    def topological_sort(self) -> List[str]:
        """
        Get topologically sorted node IDs.
        
        Raises:
            CyclicDependencyError: If graph has cycles
        """
        has_cycle, cycle = self.has_cycle()
        if has_cycle and cycle:
            raise CyclicDependencyError(cycle)
        
        with self._lock:
            in_degree = {node_id: 0 for node_id in self._nodes}
            for edge in self._edges:
                in_degree[edge.target] += 1
            
            queue = deque([n for n, d in in_degree.items() if d == 0])
            result = []
            
            while queue:
                node_id = queue.popleft()
                result.append(node_id)
                
                for successor in self._adjacency.get(node_id, set()):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.append(successor)
            
            return result
    
    def compute_hash(self) -> str:
        """Compute hash of graph structure."""
        with self._lock:
            nodes_data = sorted([n.node_id for n in self._nodes.values()])
            edges_data = sorted([(e.source, e.target) for e in self._edges])
            
            content = json.dumps({
                "nodes": nodes_data,
                "edges": edges_data,
            }, sort_keys=True)
            
            return hashlib.sha256(content.encode()).hexdigest()


# =============================================================================
# GRAPH ANALYZER
# =============================================================================

class GraphAnalyzer:
    """
    Deep analysis of execution graphs.
    
    Features:
    - Critical path identification
    - Bottleneck detection
    - Parallelism opportunity scoring
    - Resource contention prediction
    """
    
    def __init__(self, graph: ExecutionGraph) -> None:
        self._graph = graph
    
    def find_critical_path(self) -> CriticalPath:
        """
        Find the critical path through the graph.
        
        Uses longest path algorithm for DAG.
        """
        nodes = self._graph.get_all_nodes()
        if not nodes:
            return CriticalPath(
                nodes=[],
                total_duration=0.0,
                bottleneck_node=None,
                slack_times={},
            )
        
        sorted_ids = self._graph.topological_sort()
        
        # Forward pass - earliest start times
        earliest_finish: Dict[str, float] = {}
        earliest_start: Dict[str, float] = {}
        
        for node_id in sorted_ids:
            node = self._graph.get_node(node_id)
            if not node:
                continue
            
            predecessors = self._graph.get_predecessors(node_id)
            if not predecessors:
                earliest_start[node_id] = 0
            else:
                earliest_start[node_id] = max(
                    earliest_finish.get(p, 0) for p in predecessors
                )
            
            earliest_finish[node_id] = earliest_start[node_id] + node.estimated_duration
        
        # Find total duration
        total_duration = max(earliest_finish.values()) if earliest_finish else 0
        
        # Backward pass - latest start times
        latest_start: Dict[str, float] = {}
        latest_finish: Dict[str, float] = {}
        
        for node_id in reversed(sorted_ids):
            node = self._graph.get_node(node_id)
            if not node:
                continue
            
            successors = self._graph.get_successors(node_id)
            if not successors:
                latest_finish[node_id] = total_duration
            else:
                latest_finish[node_id] = min(
                    latest_start.get(s, total_duration) for s in successors
                )
            
            latest_start[node_id] = latest_finish[node_id] - node.estimated_duration
        
        # Calculate slack times
        slack_times = {
            node_id: latest_start.get(node_id, 0) - earliest_start.get(node_id, 0)
            for node_id in sorted_ids
        }
        
        # Critical path has zero slack
        critical_nodes = [n for n, s in slack_times.items() if abs(s) < 0.001]
        
        # Order critical nodes by earliest start
        critical_nodes.sort(key=lambda n: earliest_start.get(n, 0))
        
        # Find bottleneck (longest task on critical path)
        bottleneck = None
        max_duration = 0
        for node_id in critical_nodes:
            node = self._graph.get_node(node_id)
            if node and node.estimated_duration > max_duration:
                max_duration = node.estimated_duration
                bottleneck = node_id
        
        return CriticalPath(
            nodes=critical_nodes,
            total_duration=total_duration,
            bottleneck_node=bottleneck,
            slack_times=slack_times,
        )
    
    def analyze_parallelism(self) -> ParallelismAnalysis:
        """
        Analyze parallelism opportunities.
        
        Identifies independent nodes that can run in parallel.
        """
        sorted_ids = self._graph.topological_sort()
        
        # Compute levels (nodes at same level can run in parallel)
        levels: Dict[str, int] = {}
        
        for node_id in sorted_ids:
            predecessors = self._graph.get_predecessors(node_id)
            if not predecessors:
                levels[node_id] = 0
            else:
                levels[node_id] = max(levels.get(p, 0) for p in predecessors) + 1
        
        # Group by level
        level_groups: Dict[int, List[str]] = defaultdict(list)
        for node_id, level in levels.items():
            level_groups[level].append(node_id)
        
        parallel_groups = [nodes for _, nodes in sorted(level_groups.items())]
        max_parallel = max(len(group) for group in parallel_groups) if parallel_groups else 0
        
        # Calculate parallelism score
        total_nodes = len(sorted_ids)
        total_levels = len(parallel_groups)
        
        if total_levels > 0:
            # Perfect parallelism would have 1 level
            # Sequential execution would have n levels
            parallelism_score = 1 - ((total_levels - 1) / max(total_nodes - 1, 1))
        else:
            parallelism_score = 1.0
        
        # Find sequential bottlenecks (levels with only 1 node)
        bottlenecks = [
            group[0] for group in parallel_groups if len(group) == 1
        ]
        
        return ParallelismAnalysis(
            max_parallel_nodes=max_parallel,
            parallelism_score=max(0, min(1, parallelism_score)),
            parallel_groups=parallel_groups,
            sequential_bottlenecks=bottlenecks,
        )
    
    def detect_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Detect bottleneck nodes.
        
        Considers:
        - Task duration
        - Resource requirements
        - Fan-in/fan-out ratio
        """
        bottlenecks = []
        nodes = self._graph.get_all_nodes()
        
        if not nodes:
            return []
        
        # Calculate average duration
        avg_duration = sum(n.estimated_duration for n in nodes) / len(nodes)
        
        for node in nodes:
            score = 0.0
            reasons = []
            
            # Long duration
            if node.estimated_duration > avg_duration * 2:
                score += 0.4
                reasons.append("Long duration")
            
            # High resource requirements
            total_resources = sum(node.resource_requirements.values())
            if total_resources > 50:
                score += 0.3
                reasons.append("High resource usage")
            
            # High fan-in (many dependencies)
            predecessors = self._graph.get_predecessors(node.node_id)
            if len(predecessors) > 3:
                score += 0.2
                reasons.append("High fan-in")
            
            # High fan-out (many dependents)
            successors = self._graph.get_successors(node.node_id)
            if len(successors) > 3:
                score += 0.1
                reasons.append("High fan-out")
            
            if score > 0.3:
                bottlenecks.append({
                    "node_id": node.node_id,
                    "score": score,
                    "reasons": reasons,
                    "duration": node.estimated_duration,
                    "predecessors": len(predecessors),
                    "successors": len(successors),
                })
        
        return sorted(bottlenecks, key=lambda x: x["score"], reverse=True)
    
    def predict_resource_contention(
        self,
        resource_limits: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Predict resource contention during execution.
        
        Args:
            resource_limits: Maximum available resources by type
        """
        parallelism = self.analyze_parallelism()
        contention_points = []
        
        for group in parallelism.parallel_groups:
            # Calculate total resources needed for parallel execution
            group_resources: Dict[str, float] = defaultdict(float)
            
            for node_id in group:
                node = self._graph.get_node(node_id)
                if node:
                    for resource, amount in node.resource_requirements.items():
                        group_resources[resource] += amount
            
            # Check for contention
            for resource, needed in group_resources.items():
                limit = resource_limits.get(resource, float('inf'))
                if needed > limit:
                    contention_points.append({
                        "resource": resource,
                        "needed": needed,
                        "available": limit,
                        "deficit": needed - limit,
                        "nodes": group,
                    })
        
        return {
            "has_contention": len(contention_points) > 0,
            "contention_points": contention_points,
            "recommendation": (
                "Consider serializing some parallel tasks"
                if contention_points else
                "No resource contention detected"
            ),
        }


# =============================================================================
# DEPENDENCY RESOLVER
# =============================================================================

class DependencyResolver:
    """
    Advanced dependency handling.
    
    Features:
    - Transitive dependency computation
    - Diamond dependency detection
    - Optional dependency handling
    """
    
    def __init__(self, graph: ExecutionGraph) -> None:
        self._graph = graph
        self._transitive_cache: Dict[str, Set[str]] = {}
    
    def get_transitive_dependencies(self, node_id: str) -> Set[str]:
        """Get all transitive dependencies of a node."""
        if node_id in self._transitive_cache:
            return self._transitive_cache[node_id].copy()
        
        result: Set[str] = set()
        visited: Set[str] = set()
        queue = deque([node_id])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            predecessors = self._graph.get_predecessors(current)
            for pred in predecessors:
                result.add(pred)
                if pred not in visited:
                    queue.append(pred)
        
        self._transitive_cache[node_id] = result
        return result.copy()
    
    def detect_diamond_dependencies(self) -> List[Dict[str, Any]]:
        """
        Detect diamond dependency patterns.
        
        A diamond occurs when two paths from A to D exist:
        A → B → D and A → C → D
        """
        diamonds = []
        nodes = [n.node_id for n in self._graph.get_all_nodes()]
        
        for node_id in nodes:
            predecessors = list(self._graph.get_predecessors(node_id))
            
            if len(predecessors) < 2:
                continue
            
            # Check if any pair of predecessors share a common ancestor
            for i, pred1 in enumerate(predecessors):
                for pred2 in predecessors[i+1:]:
                    ancestors1 = self.get_transitive_dependencies(pred1)
                    ancestors2 = self.get_transitive_dependencies(pred2)
                    
                    common = ancestors1 & ancestors2
                    if common:
                        diamonds.append({
                            "target": node_id,
                            "paths": [pred1, pred2],
                            "common_ancestors": list(common),
                        })
        
        return diamonds
    
    def get_optional_dependencies(self, node_id: str) -> List[str]:
        """Get optional dependencies of a node."""
        edges = self._graph.get_all_edges()
        return [
            e.source for e in edges
            if e.target == node_id and e.edge_type == EdgeType.OPTIONAL
        ]
    
    def can_execute(
        self,
        node_id: str,
        completed_nodes: Set[str],
    ) -> Tuple[bool, List[str]]:
        """
        Check if node can execute given completed nodes.
        
        Returns:
            Tuple of (can_execute, blocking_dependencies)
        """
        edges = self._graph.get_all_edges()
        blocking = []
        
        for edge in edges:
            if edge.target != node_id:
                continue
            
            if edge.source not in completed_nodes:
                if edge.edge_type in (EdgeType.HARD, EdgeType.DATA):
                    blocking.append(edge.source)
        
        return len(blocking) == 0, blocking


# =============================================================================
# EXECUTION PREDICTOR
# =============================================================================

class ExecutionPredictor:
    """
    Predict execution characteristics.
    
    Features:
    - Estimated completion time
    - Resource requirement forecast
    - Failure probability estimation
    - Confidence intervals
    """
    
    def __init__(self, graph: ExecutionGraph) -> None:
        self._graph = graph
        self._historical_data: List[Dict[str, float]] = []
    
    def add_historical_data(
        self,
        task_type: str,
        actual_duration: float,
        estimated_duration: float,
    ) -> None:
        """Add historical execution data for calibration."""
        self._historical_data.append({
            "task_type": task_type,
            "actual": actual_duration,
            "estimated": estimated_duration,
            "ratio": actual_duration / estimated_duration if estimated_duration > 0 else 1.0,
        })
    
    def predict(self) -> ExecutionPrediction:
        """Predict execution characteristics."""
        analyzer = GraphAnalyzer(self._graph)
        critical_path = analyzer.find_critical_path()
        
        # Base estimate is critical path duration
        base_estimate = critical_path.total_duration
        
        # Apply calibration from historical data
        calibration_factor = self._calculate_calibration_factor()
        calibrated_estimate = base_estimate * calibration_factor
        
        # Calculate confidence interval
        variance = self._calculate_variance()
        confidence_interval = (
            calibrated_estimate * (1 - variance),
            calibrated_estimate * (1 + variance),
        )
        
        # Resource forecast
        resource_forecast = self._forecast_resources()
        
        # Failure probability
        failure_prob = self._calculate_failure_probability()
        
        # Confidence level based on data quality
        confidence = min(0.95, 0.5 + len(self._historical_data) * 0.05)
        
        return ExecutionPrediction(
            estimated_total_time=calibrated_estimate,
            confidence_interval=confidence_interval,
            confidence_level=confidence,
            resource_forecast=resource_forecast,
            failure_probability=failure_prob,
        )
    
    def _calculate_calibration_factor(self) -> float:
        """Calculate calibration factor from historical data."""
        if not self._historical_data:
            return 1.0
        
        ratios = [d["ratio"] for d in self._historical_data[-20:]]
        return sum(ratios) / len(ratios)
    
    def _calculate_variance(self) -> float:
        """Calculate prediction variance."""
        if len(self._historical_data) < 2:
            return 0.3  # Default 30% variance
        
        ratios = [d["ratio"] for d in self._historical_data[-20:]]
        mean = sum(ratios) / len(ratios)
        variance = sum((r - mean) ** 2 for r in ratios) / len(ratios)
        
        return min(0.5, math.sqrt(variance))
    
    def _forecast_resources(self) -> Dict[str, float]:
        """Forecast resource requirements."""
        total: Dict[str, float] = defaultdict(float)
        
        for node in self._graph.get_all_nodes():
            for resource, amount in node.resource_requirements.items():
                total[resource] = max(total[resource], amount)
        
        return dict(total)
    
    def _calculate_failure_probability(self) -> float:
        """Calculate overall failure probability."""
        nodes = self._graph.get_all_nodes()
        if not nodes:
            return 0.0
        
        # Probability of success is product of individual success probabilities
        success_prob = 1.0
        for node in nodes:
            success_prob *= (1 - node.failure_probability)
        
        return 1 - success_prob


# =============================================================================
# GRAPH OPTIMIZER
# =============================================================================

class GraphOptimizer:
    """
    Optimize execution order.
    
    Features:
    - Minimize total execution time
    - Maximize parallelism
    - Respect resource constraints
    """
    
    def __init__(self, graph: ExecutionGraph) -> None:
        self._graph = graph
    
    def optimize(
        self,
        goal: OptimizationGoal = OptimizationGoal.BALANCED,
        resource_limits: Optional[Dict[str, float]] = None,
    ) -> OptimizationResult:
        """
        Optimize graph execution.
        
        Args:
            goal: Optimization goal
            resource_limits: Optional resource constraints
        """
        analyzer = GraphAnalyzer(self._graph)
        original_critical_path = analyzer.find_critical_path()
        original_duration = original_critical_path.total_duration
        
        # Get topological order
        topo_order = self._graph.topological_sort()
        
        # Apply optimization strategy
        if goal == OptimizationGoal.MAXIMIZE_PARALLELISM:
            optimized_order = self._optimize_for_parallelism(topo_order)
        elif goal == OptimizationGoal.MINIMIZE_RESOURCES:
            optimized_order = self._optimize_for_resources(topo_order, resource_limits)
        else:
            optimized_order = self._optimize_balanced(topo_order, resource_limits)
        
        # Calculate optimized duration (simulated)
        # In reality, this would simulate execution with new order
        parallelism = analyzer.analyze_parallelism()
        
        # Estimate improvement
        improvement_factor = parallelism.parallelism_score
        optimized_duration = original_duration * (1 - improvement_factor * 0.1)
        
        improvement_percent = (
            (original_duration - optimized_duration) / original_duration * 100
            if original_duration > 0 else 0
        )
        
        # Generate parallelization suggestions
        suggestions = self._generate_suggestions(analyzer)
        
        return OptimizationResult(
            original_duration=original_duration,
            optimized_duration=optimized_duration,
            improvement_percent=improvement_percent,
            reordered_nodes=optimized_order,
            parallelization_suggestions=suggestions,
        )
    
    def _optimize_for_parallelism(self, topo_order: List[str]) -> List[str]:
        """Optimize for maximum parallelism."""
        # Sort by number of dependents (more dependents first)
        def score(node_id: str) -> int:
            return -len(self._graph.get_successors(node_id))
        
        # Stable sort maintaining topological order when scores equal
        return sorted(topo_order, key=score)
    
    def _optimize_for_resources(
        self,
        topo_order: List[str],
        limits: Optional[Dict[str, float]],
    ) -> List[str]:
        """Optimize for minimal resource usage."""
        if not limits:
            return topo_order
        
        # Sort by resource requirements (lower first)
        def resource_score(node_id: str) -> float:
            node = self._graph.get_node(node_id)
            if not node:
                return 0
            return sum(node.resource_requirements.values())
        
        return sorted(topo_order, key=resource_score)
    
    def _optimize_balanced(
        self,
        topo_order: List[str],
        limits: Optional[Dict[str, float]],
    ) -> List[str]:
        """Balanced optimization."""
        # Combine parallelism and resource scores
        def combined_score(node_id: str) -> float:
            node = self._graph.get_node(node_id)
            if not node:
                return 0
            
            parallelism_score = len(self._graph.get_successors(node_id))
            resource_score = sum(node.resource_requirements.values())
            
            return parallelism_score * 2 - resource_score * 0.1
        
        return sorted(topo_order, key=combined_score, reverse=True)
    
    def _generate_suggestions(
        self,
        analyzer: GraphAnalyzer,
    ) -> List[Dict[str, Any]]:
        """Generate optimization suggestions."""
        suggestions = []
        
        bottlenecks = analyzer.detect_bottlenecks()
        for bottleneck in bottlenecks[:3]:
            suggestions.append({
                "type": "BOTTLENECK",
                "node_id": bottleneck["node_id"],
                "suggestion": f"Consider breaking down task or adding resources",
                "reasons": bottleneck["reasons"],
            })
        
        parallelism = analyzer.analyze_parallelism()
        if parallelism.parallelism_score < 0.5:
            suggestions.append({
                "type": "LOW_PARALLELISM",
                "suggestion": "Consider restructuring dependencies to enable more parallel execution",
                "current_score": parallelism.parallelism_score,
            })
        
        return suggestions


# =============================================================================
# GRAPH VISUALIZER
# =============================================================================

class GraphVisualizer:
    """
    Graph visualization.
    
    Export formats:
    - DOT (Graphviz)
    - Mermaid
    - JSON
    """
    
    def __init__(self, graph: ExecutionGraph) -> None:
        self._graph = graph
    
    def to_dot(
        self,
        highlight_critical_path: bool = True,
    ) -> str:
        """Export to DOT format."""
        lines = ["digraph ExecutionGraph {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box];")
        
        # Get critical path for highlighting
        critical_nodes: Set[str] = set()
        if highlight_critical_path:
            analyzer = GraphAnalyzer(self._graph)
            critical_path = analyzer.find_critical_path()
            critical_nodes = set(critical_path.nodes)
        
        # Nodes
        for node in self._graph.get_all_nodes():
            style = 'style=filled fillcolor=red' if node.node_id in critical_nodes else ''
            label = f"{node.node_id}\\n({node.estimated_duration:.1f}s)"
            lines.append(f'  "{node.node_id}" [label="{label}" {style}];')
        
        # Edges
        for edge in self._graph.get_all_edges():
            style = "bold" if edge.edge_type == EdgeType.HARD else "dashed"
            lines.append(f'  "{edge.source}" -> "{edge.target}" [style={style}];')
        
        lines.append("}")
        return "\n".join(lines)
    
    def to_mermaid(self) -> str:
        """Export to Mermaid diagram format."""
        lines = ["graph LR"]
        
        for node in self._graph.get_all_nodes():
            lines.append(f"  {node.node_id}[{node.node_id}]")
        
        for edge in self._graph.get_all_edges():
            arrow = "-->" if edge.edge_type == EdgeType.HARD else "-..->"
            lines.append(f"  {edge.source} {arrow} {edge.target}")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Export to JSON format."""
        data = {
            "version": GRAPH_ANALYZER_VERSION,
            "nodes": [n.to_dict() for n in self._graph.get_all_nodes()],
            "edges": [e.to_dict() for e in self._graph.get_all_edges()],
            "hash": self._graph.compute_hash(),
        }
        return json.dumps(data, indent=2)


# =============================================================================
# GRAPH DIFF
# =============================================================================

class GraphDiff:
    """
    Compare execution graphs.
    
    Features:
    - Node differences
    - Edge differences
    - Impact analysis
    - Migration path
    """
    
    def __init__(self, graph_a: ExecutionGraph, graph_b: ExecutionGraph) -> None:
        self._graph_a = graph_a
        self._graph_b = graph_b
    
    def diff(self) -> GraphDiffResult:
        """Compare the two graphs."""
        nodes_a = {n.node_id for n in self._graph_a.get_all_nodes()}
        nodes_b = {n.node_id for n in self._graph_b.get_all_nodes()}
        
        added_nodes = list(nodes_b - nodes_a)
        removed_nodes = list(nodes_a - nodes_b)
        
        # Check for modified nodes (same ID, different properties)
        modified_nodes = []
        for node_id in nodes_a & nodes_b:
            node_a = self._graph_a.get_node(node_id)
            node_b = self._graph_b.get_node(node_id)
            if node_a and node_b:
                if (node_a.estimated_duration != node_b.estimated_duration or
                    node_a.task_type != node_b.task_type):
                    modified_nodes.append(node_id)
        
        edges_a = {(e.source, e.target) for e in self._graph_a.get_all_edges()}
        edges_b = {(e.source, e.target) for e in self._graph_b.get_all_edges()}
        
        added_edges = list(edges_b - edges_a)
        removed_edges = list(edges_a - edges_b)
        
        # Calculate impact score
        total_changes = (
            len(added_nodes) + len(removed_nodes) + len(modified_nodes) +
            len(added_edges) + len(removed_edges)
        )
        total_elements = len(nodes_a) + len(nodes_b) + len(edges_a) + len(edges_b)
        impact_score = total_changes / max(total_elements, 1)
        
        # Generate migration steps
        migration_steps = self._generate_migration_steps(
            added_nodes, removed_nodes, modified_nodes,
            added_edges, removed_edges,
        )
        
        return GraphDiffResult(
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            modified_nodes=modified_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            impact_score=impact_score,
            migration_steps=migration_steps,
        )
    
    def _generate_migration_steps(
        self,
        added_nodes: List[str],
        removed_nodes: List[str],
        modified_nodes: List[str],
        added_edges: List[Tuple[str, str]],
        removed_edges: List[Tuple[str, str]],
    ) -> List[str]:
        """Generate migration steps."""
        steps = []
        
        # Remove edges first (before removing nodes)
        for source, target in removed_edges:
            steps.append(f"Remove edge: {source} → {target}")
        
        # Remove nodes
        for node_id in removed_nodes:
            steps.append(f"Remove node: {node_id}")
        
        # Add nodes
        for node_id in added_nodes:
            steps.append(f"Add node: {node_id}")
        
        # Modify nodes
        for node_id in modified_nodes:
            steps.append(f"Update node: {node_id}")
        
        # Add edges (after adding nodes)
        for source, target in added_edges:
            steps.append(f"Add edge: {source} → {target}")
        
        return steps


# =============================================================================
# WRAP HASH COMPUTATION
# =============================================================================

def compute_wrap_hash() -> str:
    """Compute WRAP hash for GID-04 deliverable."""
    content = f"GID-04:graph_analyzer:v{GRAPH_ANALYZER_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "GRAPH_ANALYZER_VERSION",
    "NodeState",
    "EdgeType",
    "OptimizationGoal",
    "GraphAnalyzerError",
    "CyclicDependencyError",
    "NodeNotFoundError",
    "GraphNode",
    "GraphEdge",
    "CriticalPath",
    "ParallelismAnalysis",
    "ExecutionPrediction",
    "OptimizationResult",
    "GraphDiffResult",
    "ExecutionGraph",
    "GraphAnalyzer",
    "DependencyResolver",
    "ExecutionPredictor",
    "GraphOptimizer",
    "GraphVisualizer",
    "GraphDiff",
    "compute_wrap_hash",
]
