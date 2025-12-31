"""
GIE Execution Graph — DAG with Dependency Resolution

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-01 (Cody) — Senior Backend Engineer

Implements:
- Directed Acyclic Graph (DAG) for execution ordering
- Dependency resolution with topological sort
- Circular dependency detection
- Execution graph hashing for audit trail
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class NodeStatus(Enum):
    """Execution status of a graph node."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EdgeType(Enum):
    """Type of dependency edge."""
    HARD = "HARD"      # Must complete successfully
    SOFT = "SOFT"      # Can proceed if failed
    BLOCKING = "BLOCKING"  # Blocks entire graph if failed


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class GraphError(Exception):
    """Base exception for graph operations."""
    pass


class CircularDependencyError(GraphError):
    """Raised when circular dependency is detected."""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' → '.join(cycle)}")


class NodeNotFoundError(GraphError):
    """Raised when node is not found in graph."""
    pass


class DuplicateNodeError(GraphError):
    """Raised when node already exists."""
    pass


class InvalidDependencyError(GraphError):
    """Raised when dependency is invalid."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionNode:
    """
    A node in the execution graph.
    
    Represents a single executable task with dependencies.
    """
    node_id: str
    task_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "node_id": self.node_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of node state."""
        content = json.dumps({
            "node_id": self.node_id,
            "task_type": self.task_type,
            "payload": self.payload,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class DependencyEdge:
    """
    An edge representing a dependency between nodes.
    """
    from_node: str
    to_node: str
    edge_type: EdgeType = EdgeType.HARD
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from": self.from_node,
            "to": self.to_node,
            "type": self.edge_type.value,
        }


@dataclass
class ExecutionLevel:
    """
    A level in the topological ordering.
    
    All nodes in a level can execute in parallel.
    """
    level: int
    node_ids: List[str]
    
    def __len__(self) -> int:
        return len(self.node_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionGraph:
    """
    Directed Acyclic Graph for execution ordering.
    
    Features:
    - Topological sort for dependency resolution
    - Cycle detection
    - Parallel execution levels
    - Graph hashing for audit
    """

    def __init__(self, graph_id: Optional[str] = None):
        """Initialize empty execution graph."""
        self._graph_id = graph_id or f"GRAPH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self._lock = threading.RLock()
        
        # Node storage
        self._nodes: Dict[str, ExecutionNode] = {}
        
        # Adjacency lists
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)  # node -> depends on
        self._dependents: Dict[str, Set[str]] = defaultdict(set)    # node -> depended by
        
        # Edge metadata
        self._edges: Dict[Tuple[str, str], DependencyEdge] = {}
        
        # Cached topological order (invalidated on modification)
        self._topo_order: Optional[List[str]] = None
        self._execution_levels: Optional[List[ExecutionLevel]] = None

    @property
    def graph_id(self) -> str:
        """Get graph ID."""
        return self._graph_id

    @property
    def node_count(self) -> int:
        """Get number of nodes."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Get number of edges."""
        return len(self._edges)

    # ─────────────────────────────────────────────────────────────────────────
    # Node Operations
    # ─────────────────────────────────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        task_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ExecutionNode:
        """
        Add a node to the graph.
        
        Raises DuplicateNodeError if node exists.
        """
        with self._lock:
            if node_id in self._nodes:
                raise DuplicateNodeError(f"Node already exists: {node_id}")
            
            node = ExecutionNode(
                node_id=node_id,
                task_type=task_type,
                payload=payload or {},
            )
            self._nodes[node_id] = node
            self._invalidate_cache()
            
            return node

    def get_node(self, node_id: str) -> ExecutionNode:
        """
        Get a node by ID.
        
        Raises NodeNotFoundError if not found.
        """
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {node_id}")
            return self._nodes[node_id]

    def remove_node(self, node_id: str) -> None:
        """
        Remove a node and all its edges.
        
        Raises NodeNotFoundError if not found.
        """
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {node_id}")
            
            # Remove all edges involving this node
            for dep in list(self._dependencies[node_id]):
                self._remove_edge(dep, node_id)
            for dependent in list(self._dependents[node_id]):
                self._remove_edge(node_id, dependent)
            
            del self._nodes[node_id]
            del self._dependencies[node_id]
            del self._dependents[node_id]
            self._invalidate_cache()

    def list_nodes(self) -> List[str]:
        """List all node IDs."""
        with self._lock:
            return list(self._nodes.keys())

    # ─────────────────────────────────────────────────────────────────────────
    # Edge Operations
    # ─────────────────────────────────────────────────────────────────────────

    def add_dependency(
        self,
        from_node: str,
        to_node: str,
        edge_type: EdgeType = EdgeType.HARD,
    ) -> DependencyEdge:
        """
        Add a dependency: to_node depends on from_node.
        
        Meaning: from_node must complete before to_node can start.
        
        Raises:
        - NodeNotFoundError if either node doesn't exist
        - CircularDependencyError if this would create a cycle
        """
        with self._lock:
            if from_node not in self._nodes:
                raise NodeNotFoundError(f"From node not found: {from_node}")
            if to_node not in self._nodes:
                raise NodeNotFoundError(f"To node not found: {to_node}")
            
            # Check for self-loop
            if from_node == to_node:
                raise CircularDependencyError([from_node, to_node])
            
            # Temporarily add edge
            self._dependencies[to_node].add(from_node)
            self._dependents[from_node].add(to_node)
            
            # Check for cycle
            cycle = self._detect_cycle()
            if cycle:
                # Rollback
                self._dependencies[to_node].discard(from_node)
                self._dependents[from_node].discard(to_node)
                raise CircularDependencyError(cycle)
            
            # Create edge
            edge = DependencyEdge(from_node, to_node, edge_type)
            self._edges[(from_node, to_node)] = edge
            self._invalidate_cache()
            
            return edge

    def _remove_edge(self, from_node: str, to_node: str) -> None:
        """Remove an edge (internal helper)."""
        self._dependencies[to_node].discard(from_node)
        self._dependents[from_node].discard(to_node)
        self._edges.pop((from_node, to_node), None)

    def get_dependencies(self, node_id: str) -> Set[str]:
        """Get nodes that a node depends on."""
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {node_id}")
            return set(self._dependencies[node_id])

    def get_dependents(self, node_id: str) -> Set[str]:
        """Get nodes that depend on a node."""
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {node_id}")
            return set(self._dependents[node_id])

    # ─────────────────────────────────────────────────────────────────────────
    # Cycle Detection
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_cycle(self) -> Optional[List[str]]:
        """
        Detect cycle using DFS with coloring.
        
        Returns cycle path if found, None otherwise.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n: WHITE for n in self._nodes}
        parent: Dict[str, Optional[str]] = {n: None for n in self._nodes}
        
        def dfs(node: str) -> Optional[List[str]]:
            color[node] = GRAY
            
            for dependent in self._dependents[node]:
                if color[dependent] == GRAY:
                    # Found cycle - reconstruct path
                    cycle = [dependent, node]
                    current = node
                    while parent[current] and parent[current] != dependent:
                        current = parent[current]
                        cycle.append(current)
                    cycle.append(dependent)
                    return list(reversed(cycle))
                
                if color[dependent] == WHITE:
                    parent[dependent] = node
                    result = dfs(dependent)
                    if result:
                        return result
            
            color[node] = BLACK
            return None
        
        for node in self._nodes:
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return result
        
        return None

    def has_cycle(self) -> bool:
        """Check if graph has a cycle."""
        with self._lock:
            return self._detect_cycle() is not None

    # ─────────────────────────────────────────────────────────────────────────
    # Topological Sort
    # ─────────────────────────────────────────────────────────────────────────

    def topological_sort(self) -> List[str]:
        """
        Compute topological ordering using Kahn's algorithm.
        
        Returns list of node IDs in execution order.
        Raises CircularDependencyError if cycle exists.
        """
        with self._lock:
            if self._topo_order is not None:
                return list(self._topo_order)
            
            # Compute in-degree
            in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
            for node in self._nodes:
                for dep in self._dependencies[node]:
                    in_degree[node] += 1
            
            # Queue nodes with no dependencies
            queue = deque([n for n, d in in_degree.items() if d == 0])
            result: List[str] = []
            
            while queue:
                node = queue.popleft()
                result.append(node)
                
                for dependent in self._dependents[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            if len(result) != len(self._nodes):
                # Cycle exists
                remaining = [n for n in self._nodes if n not in result]
                raise CircularDependencyError(remaining)
            
            self._topo_order = result
            return list(result)

    def get_execution_levels(self) -> List[ExecutionLevel]:
        """
        Compute parallel execution levels.
        
        Each level contains nodes that can execute in parallel.
        """
        with self._lock:
            if self._execution_levels is not None:
                return list(self._execution_levels)
            
            # Compute in-degree
            in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
            for node in self._nodes:
                in_degree[node] = len(self._dependencies[node])
            
            # Build levels
            levels: List[ExecutionLevel] = []
            remaining = set(self._nodes.keys())
            level_num = 0
            
            while remaining:
                # Nodes with no unsatisfied dependencies
                ready = [n for n in remaining if in_degree[n] == 0]
                
                if not ready:
                    # Cycle detected
                    raise CircularDependencyError(list(remaining))
                
                levels.append(ExecutionLevel(level_num, ready))
                
                # Remove ready nodes and update in-degrees
                for node in ready:
                    remaining.discard(node)
                    for dependent in self._dependents[node]:
                        in_degree[dependent] -= 1
                
                level_num += 1
            
            self._execution_levels = levels
            return list(levels)

    def get_ready_nodes(self) -> List[str]:
        """
        Get nodes ready for execution.
        
        A node is ready if:
        - Status is PENDING
        - All dependencies are COMPLETED
        """
        with self._lock:
            ready = []
            
            for node_id, node in self._nodes.items():
                if node.status != NodeStatus.PENDING:
                    continue
                
                deps_satisfied = all(
                    self._nodes[dep].status == NodeStatus.COMPLETED
                    for dep in self._dependencies[node_id]
                )
                
                if deps_satisfied:
                    ready.append(node_id)
            
            return ready

    # ─────────────────────────────────────────────────────────────────────────
    # Execution State
    # ─────────────────────────────────────────────────────────────────────────

    def mark_running(self, node_id: str) -> None:
        """Mark node as running."""
        with self._lock:
            node = self.get_node(node_id)
            node.status = NodeStatus.RUNNING
            node.started_at = datetime.utcnow().isoformat() + "Z"

    def mark_completed(self, node_id: str, result: Any = None) -> None:
        """Mark node as completed."""
        with self._lock:
            node = self.get_node(node_id)
            node.status = NodeStatus.COMPLETED
            node.result = result
            node.completed_at = datetime.utcnow().isoformat() + "Z"

    def mark_failed(self, node_id: str, error: str) -> None:
        """Mark node as failed."""
        with self._lock:
            node = self.get_node(node_id)
            node.status = NodeStatus.FAILED
            node.error = error
            node.completed_at = datetime.utcnow().isoformat() + "Z"

    def is_complete(self) -> bool:
        """Check if all nodes are completed or failed."""
        with self._lock:
            return all(
                n.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED)
                for n in self._nodes.values()
            )

    def get_completion_summary(self) -> Dict[str, int]:
        """Get count of nodes by status."""
        with self._lock:
            summary: Dict[str, int] = defaultdict(int)
            for node in self._nodes.values():
                summary[node.status.value] += 1
            return dict(summary)

    # ─────────────────────────────────────────────────────────────────────────
    # Hashing & Serialization
    # ─────────────────────────────────────────────────────────────────────────

    def compute_graph_hash(self) -> str:
        """
        Compute deterministic hash of the entire graph.
        
        Used for audit trail and WRAP verification.
        """
        with self._lock:
            # Sort nodes for determinism
            sorted_nodes = sorted(self._nodes.keys())
            
            content = {
                "graph_id": self._graph_id,
                "nodes": [self._nodes[n].to_dict() for n in sorted_nodes],
                "edges": [
                    self._edges[k].to_dict()
                    for k in sorted(self._edges.keys())
                ],
            }
            
            json_str = json.dumps(content, sort_keys=True)
            return f"sha256:{hashlib.sha256(json_str.encode()).hexdigest()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary."""
        with self._lock:
            return {
                "graph_id": self._graph_id,
                "nodes": {n: node.to_dict() for n, node in self._nodes.items()},
                "edges": [e.to_dict() for e in self._edges.values()],
                "node_count": self.node_count,
                "edge_count": self.edge_count,
            }

    def _invalidate_cache(self) -> None:
        """Invalidate cached computations."""
        self._topo_order = None
        self._execution_levels = None


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY RESOLVER
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyResolver:
    """
    Resolves and validates dependencies for execution graphs.
    """

    def __init__(self):
        """Initialize resolver."""
        self._lock = threading.RLock()

    def resolve(self, graph: ExecutionGraph) -> List[ExecutionLevel]:
        """
        Resolve dependencies and return execution levels.
        
        Validates graph is acyclic and returns parallelizable levels.
        """
        with self._lock:
            # Validate no cycles
            if graph.has_cycle():
                cycle = graph._detect_cycle()
                raise CircularDependencyError(cycle or ["unknown"])
            
            return graph.get_execution_levels()

    def validate_dependencies(
        self,
        graph: ExecutionGraph,
        required_types: Optional[Set[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate graph dependencies.
        
        Returns (valid, errors).
        """
        errors: List[str] = []
        
        with self._lock:
            # Check for cycles
            cycle = graph._detect_cycle()
            if cycle:
                errors.append(f"Circular dependency: {' → '.join(cycle)}")
            
            # Check for orphan nodes (no dependencies and no dependents)
            for node_id in graph.list_nodes():
                deps = graph.get_dependencies(node_id)
                dependents = graph.get_dependents(node_id)
                
                if not deps and not dependents and graph.node_count > 1:
                    errors.append(f"Orphan node: {node_id}")
            
            # Check required task types
            if required_types:
                found_types = {
                    graph.get_node(n).task_type
                    for n in graph.list_nodes()
                }
                missing = required_types - found_types
                if missing:
                    errors.append(f"Missing required task types: {missing}")
        
        return len(errors) == 0, errors

    def find_critical_path(self, graph: ExecutionGraph) -> List[str]:
        """
        Find the critical path (longest path) through the graph.
        
        This is the minimum time required for execution.
        """
        with self._lock:
            topo_order = graph.topological_sort()
            
            # Distance to each node (in edges)
            dist: Dict[str, int] = {n: 0 for n in topo_order}
            parent: Dict[str, Optional[str]] = {n: None for n in topo_order}
            
            for node in topo_order:
                for dependent in graph.get_dependents(node):
                    if dist[node] + 1 > dist[dependent]:
                        dist[dependent] = dist[node] + 1
                        parent[dependent] = node
            
            # Find node with maximum distance
            if not dist:
                return []
            
            end_node = max(dist.keys(), key=lambda n: dist[n])
            
            # Reconstruct path
            path = [end_node]
            current = end_node
            while parent[current]:
                current = parent[current]
                path.append(current)
            
            return list(reversed(path))


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_execution_graph(
    graph_id: str,
    tasks: List[Dict[str, Any]],
    dependencies: List[Tuple[str, str]],
) -> ExecutionGraph:
    """
    Factory function to create an execution graph.
    
    Args:
        graph_id: Unique graph identifier
        tasks: List of {"id": str, "type": str, "payload": dict}
        dependencies: List of (from_id, to_id) tuples
    
    Returns:
        Configured ExecutionGraph
    """
    graph = ExecutionGraph(graph_id)
    
    # Add nodes
    for task in tasks:
        graph.add_node(
            task["id"],
            task["type"],
            task.get("payload", {}),
        )
    
    # Add dependencies
    for from_id, to_id in dependencies:
        graph.add_dependency(from_id, to_id)
    
    return graph
