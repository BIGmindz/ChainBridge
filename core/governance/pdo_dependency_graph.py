"""
PDO Dependency Graph Engine

Manages cross-agent dependency tracking for multi-agent PAC executions.
Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-LOAD-024.

Agent: GID-01 (Cody) — Governance Lead

Implements:
- INV-AUDIT-007: Dependency Declaration Required
- INV-AUDIT-008: Acyclic Constraint
- INV-AUDIT-009: Finalization Ordering
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "max_depth": 10,
    "cycle_check_enabled": True,
    "cross_agent_audit": True,
    "allow_self_dependency": False,
    "finalization_timeout_seconds": 300,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class NodeStatus(Enum):
    """Status of a dependency graph node."""
    PENDING = "PENDING"      # Waiting for dependencies
    READY = "READY"          # All deps satisfied, can finalize
    FINALIZED = "FINALIZED"  # Complete
    BLOCKED = "BLOCKED"      # Upstream failed


class DependencyType(Enum):
    """Type of dependency relationship."""
    DATA = "DATA"            # Output data required as input
    APPROVAL = "APPROVAL"    # Approval/sign-off required
    SEQUENCE = "SEQUENCE"    # Must execute in order


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyGraphError(Exception):
    """Base exception for dependency graph errors."""
    pass


class CyclicDependencyError(DependencyGraphError):
    """Raised when adding an edge would create a cycle (INV-AUDIT-008)."""
    pass


class DependencyNotSatisfiedError(DependencyGraphError):
    """Raised when attempting to finalize with unsatisfied deps (INV-AUDIT-009)."""
    pass


class NodeNotFoundError(DependencyGraphError):
    """Raised when referenced node does not exist."""
    pass


class DuplicateNodeError(DependencyGraphError):
    """Raised when adding a node that already exists."""
    pass


class InvalidDependencyError(DependencyGraphError):
    """Raised for invalid dependency operations."""
    pass


class EdgeRemovalForbiddenError(DependencyGraphError):
    """Raised when attempting to remove an edge (forbidden)."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DependencyNode:
    """
    A node in the dependency graph representing a PDO.
    
    Per INV-AUDIT-007: Nodes track their declared dependencies.
    """
    pdo_id: str
    agent_gid: str
    pac_id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pdo_id": self.pdo_id,
            "agent_gid": self.agent_gid,
            "pac_id": self.pac_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class DependencyEdge:
    """
    An edge in the dependency graph representing a dependency relationship.
    
    Direction: upstream_pdo_id → downstream_pdo_id
    Meaning: downstream depends on upstream
    """
    edge_id: str
    upstream_pdo_id: str
    downstream_pdo_id: str
    dependency_type: DependencyType
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "edge_id": self.edge_id,
            "upstream_pdo_id": self.upstream_pdo_id,
            "downstream_pdo_id": self.downstream_pdo_id,
            "dependency_type": self.dependency_type.value,
            "created_at": self.created_at,
        }


@dataclass
class NodeState:
    """Mutable state for a node (status and finalization time)."""
    status: NodeStatus = NodeStatus.PENDING
    finalized_at: Optional[str] = None
    blocked_reason: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

class PDODependencyGraph:
    """
    Directed Acyclic Graph for tracking PDO dependencies.
    
    Thread-safe implementation enforcing:
    - INV-AUDIT-007: Dependency Declaration
    - INV-AUDIT-008: Acyclic Constraint
    - INV-AUDIT-009: Finalization Ordering
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the dependency graph."""
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._lock = threading.RLock()
        
        # Node storage: pdo_id -> DependencyNode
        self._nodes: Dict[str, DependencyNode] = {}
        
        # Node state: pdo_id -> NodeState
        self._states: Dict[str, NodeState] = {}
        
        # Edge storage: edge_id -> DependencyEdge
        self._edges: Dict[str, DependencyEdge] = {}
        
        # Adjacency lists for efficient traversal
        # upstream -> [downstream PDOs that depend on it]
        self._dependents: Dict[str, Set[str]] = defaultdict(set)
        # downstream -> [upstream PDOs it depends on]
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        # Edge counter for ID generation
        self._edge_counter = 0
        
        # Audit log for cross-agent dependencies
        self._cross_agent_log: List[Dict[str, Any]] = []

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    # ─────────────────────────────────────────────────────────────────────────
    # Node Operations
    # ─────────────────────────────────────────────────────────────────────────

    def add_node(
        self,
        pdo_id: str,
        agent_gid: str,
        pac_id: str,
    ) -> DependencyNode:
        """
        Add a PDO node to the graph.
        
        Per INV-AUDIT-007: Node must exist before dependencies can be declared.
        """
        with self._lock:
            if pdo_id in self._nodes:
                raise DuplicateNodeError(f"Node already exists: {pdo_id}")
            
            node = DependencyNode(
                pdo_id=pdo_id,
                agent_gid=agent_gid,
                pac_id=pac_id,
            )
            
            self._nodes[pdo_id] = node
            self._states[pdo_id] = NodeState(status=NodeStatus.PENDING)
            
            return node

    def get_node(self, pdo_id: str) -> Optional[DependencyNode]:
        """Get a node by PDO ID."""
        with self._lock:
            return self._nodes.get(pdo_id)

    def get_node_status(self, pdo_id: str) -> NodeStatus:
        """Get the status of a node."""
        with self._lock:
            if pdo_id not in self._states:
                raise NodeNotFoundError(f"Node not found: {pdo_id}")
            return self._states[pdo_id].status

    def list_nodes(self) -> List[DependencyNode]:
        """List all nodes in the graph."""
        with self._lock:
            return list(self._nodes.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Edge Operations (Dependency Declaration)
    # ─────────────────────────────────────────────────────────────────────────

    def add_dependency(
        self,
        upstream_pdo_id: str,
        downstream_pdo_id: str,
        dependency_type: DependencyType = DependencyType.DATA,
    ) -> DependencyEdge:
        """
        Add a dependency edge: downstream depends on upstream.
        
        Per INV-AUDIT-007: Dependencies must be declared.
        Per INV-AUDIT-008: Must not create cycles.
        """
        with self._lock:
            # Validate nodes exist
            if upstream_pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Upstream node not found: {upstream_pdo_id}")
            if downstream_pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Downstream node not found: {downstream_pdo_id}")
            
            # Check self-dependency
            if upstream_pdo_id == downstream_pdo_id:
                if not self._config["allow_self_dependency"]:
                    raise InvalidDependencyError("Self-dependency is not allowed")
            
            # Check for duplicate edge
            if upstream_pdo_id in self._dependencies[downstream_pdo_id]:
                raise InvalidDependencyError(
                    f"Dependency already exists: {upstream_pdo_id} → {downstream_pdo_id}"
                )
            
            # Check for cycles (INV-AUDIT-008)
            if self._config["cycle_check_enabled"]:
                if self._would_create_cycle(upstream_pdo_id, downstream_pdo_id):
                    raise CyclicDependencyError(
                        f"Adding dependency {upstream_pdo_id} → {downstream_pdo_id} "
                        "would create a cycle"
                    )
            
            # Check depth limit
            current_depth = self._get_dependency_depth(downstream_pdo_id)
            if current_depth >= self._config["max_depth"]:
                raise InvalidDependencyError(
                    f"Maximum dependency depth ({self._config['max_depth']}) exceeded"
                )
            
            # Create edge
            self._edge_counter += 1
            edge_id = f"EDGE-{self._edge_counter:06d}"
            
            edge = DependencyEdge(
                edge_id=edge_id,
                upstream_pdo_id=upstream_pdo_id,
                downstream_pdo_id=downstream_pdo_id,
                dependency_type=dependency_type,
            )
            
            self._edges[edge_id] = edge
            self._dependencies[downstream_pdo_id].add(upstream_pdo_id)
            self._dependents[upstream_pdo_id].add(downstream_pdo_id)
            
            # Log cross-agent dependencies
            if self._config["cross_agent_audit"]:
                upstream_node = self._nodes[upstream_pdo_id]
                downstream_node = self._nodes[downstream_pdo_id]
                if upstream_node.agent_gid != downstream_node.agent_gid:
                    self._cross_agent_log.append({
                        "edge_id": edge_id,
                        "upstream_agent": upstream_node.agent_gid,
                        "downstream_agent": downstream_node.agent_gid,
                        "timestamp": edge.created_at,
                    })
            
            # Update downstream status
            self._update_node_status(downstream_pdo_id)
            
            return edge

    def get_dependencies(self, pdo_id: str) -> List[DependencyNode]:
        """
        Get all upstream dependencies for a PDO.
        
        Returns nodes that this PDO depends on.
        """
        with self._lock:
            if pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {pdo_id}")
            
            dep_ids = self._dependencies.get(pdo_id, set())
            return [self._nodes[did] for did in dep_ids]

    def get_dependents(self, pdo_id: str) -> List[DependencyNode]:
        """
        Get all downstream dependents for a PDO.
        
        Returns nodes that depend on this PDO.
        """
        with self._lock:
            if pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {pdo_id}")
            
            dep_ids = self._dependents.get(pdo_id, set())
            return [self._nodes[did] for did in dep_ids]

    def get_edges(self) -> List[DependencyEdge]:
        """Get all edges in the graph."""
        with self._lock:
            return list(self._edges.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Forbidden Operations
    # ─────────────────────────────────────────────────────────────────────────

    def remove_edge(self, edge_id: str) -> None:
        """FORBIDDEN: Remove an edge from the graph."""
        raise EdgeRemovalForbiddenError(
            "remove_edge() is forbidden. Dependency edges cannot be removed "
            "per audit trail integrity requirements."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Cycle Detection (INV-AUDIT-008)
    # ─────────────────────────────────────────────────────────────────────────

    def _would_create_cycle(self, upstream_id: str, downstream_id: str) -> bool:
        """
        Check if adding edge (upstream → downstream) would create a cycle.
        
        Per INV-AUDIT-008: Graph must remain acyclic.
        """
        # If downstream can reach upstream through existing edges, adding
        # upstream → downstream would create a cycle
        visited: Set[str] = set()
        stack = [upstream_id]
        
        while stack:
            current = stack.pop()
            if current == downstream_id:
                return True  # Cycle would be created
            if current in visited:
                continue
            visited.add(current)
            
            # Check what current depends on (traverse upstream)
            for dep_id in self._dependencies.get(current, set()):
                stack.append(dep_id)
        
        return False

    def is_acyclic(self) -> bool:
        """
        Verify the graph is acyclic.
        
        Per INV-AUDIT-008: Full graph validation.
        """
        with self._lock:
            # Use Kahn's algorithm for topological sort
            # If we can process all nodes, graph is acyclic
            in_degree: Dict[str, int] = {pdo_id: 0 for pdo_id in self._nodes}
            
            for downstream_id, upstream_ids in self._dependencies.items():
                in_degree[downstream_id] = len(upstream_ids)
            
            # Start with nodes that have no dependencies
            queue = [pdo_id for pdo_id, degree in in_degree.items() if degree == 0]
            processed = 0
            
            while queue:
                current = queue.pop(0)
                processed += 1
                
                # Reduce in-degree of dependents
                for dependent_id in self._dependents.get(current, set()):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
            
            return processed == len(self._nodes)

    # ─────────────────────────────────────────────────────────────────────────
    # Finalization (INV-AUDIT-009)
    # ─────────────────────────────────────────────────────────────────────────

    def check_ready(self, pdo_id: str) -> Tuple[bool, List[str]]:
        """
        Check if a PDO is ready to be finalized.
        
        Returns (is_ready, list_of_pending_dependencies).
        Per INV-AUDIT-009: All deps must be finalized first.
        """
        with self._lock:
            if pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {pdo_id}")
            
            pending: List[str] = []
            
            for dep_id in self._dependencies.get(pdo_id, set()):
                dep_state = self._states[dep_id]
                if dep_state.status != NodeStatus.FINALIZED:
                    pending.append(dep_id)
            
            return (len(pending) == 0, pending)

    def finalize_node(self, pdo_id: str) -> None:
        """
        Mark a node as finalized.
        
        Per INV-AUDIT-009: Can only finalize if all dependencies are finalized.
        """
        with self._lock:
            if pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {pdo_id}")
            
            state = self._states[pdo_id]
            
            # Check if already finalized
            if state.status == NodeStatus.FINALIZED:
                return
            
            # Check if blocked
            if state.status == NodeStatus.BLOCKED:
                raise DependencyNotSatisfiedError(
                    f"Cannot finalize blocked node: {pdo_id}. "
                    f"Reason: {state.blocked_reason}"
                )
            
            # Check all dependencies are finalized (INV-AUDIT-009)
            is_ready, pending = self.check_ready(pdo_id)
            if not is_ready:
                raise DependencyNotSatisfiedError(
                    f"Cannot finalize {pdo_id}. "
                    f"Pending dependencies: {pending}"
                )
            
            # Finalize
            state.status = NodeStatus.FINALIZED
            state.finalized_at = datetime.utcnow().isoformat() + "Z"
            
            # Update dependents' status
            for dependent_id in self._dependents.get(pdo_id, set()):
                self._update_node_status(dependent_id)

    def block_node(self, pdo_id: str, reason: str) -> None:
        """
        Block a node (e.g., due to upstream failure).
        
        This propagates to all downstream dependents.
        """
        with self._lock:
            if pdo_id not in self._nodes:
                raise NodeNotFoundError(f"Node not found: {pdo_id}")
            
            state = self._states[pdo_id]
            if state.status == NodeStatus.FINALIZED:
                raise InvalidDependencyError(
                    f"Cannot block finalized node: {pdo_id}"
                )
            
            state.status = NodeStatus.BLOCKED
            state.blocked_reason = reason
            
            # Propagate block to dependents
            self._propagate_block(pdo_id, f"Upstream {pdo_id} blocked: {reason}")

    def _propagate_block(self, source_id: str, reason: str) -> None:
        """Propagate BLOCKED status to all downstream dependents."""
        for dependent_id in self._dependents.get(source_id, set()):
            dep_state = self._states[dependent_id]
            if dep_state.status not in (NodeStatus.FINALIZED, NodeStatus.BLOCKED):
                dep_state.status = NodeStatus.BLOCKED
                dep_state.blocked_reason = reason
                self._propagate_block(dependent_id, reason)

    def _update_node_status(self, pdo_id: str) -> None:
        """Update node status based on current dependency states."""
        state = self._states[pdo_id]
        
        if state.status in (NodeStatus.FINALIZED, NodeStatus.BLOCKED):
            return
        
        # Check for blocked dependencies
        for dep_id in self._dependencies.get(pdo_id, set()):
            if self._states[dep_id].status == NodeStatus.BLOCKED:
                state.status = NodeStatus.BLOCKED
                state.blocked_reason = f"Upstream {dep_id} is blocked"
                return
        
        # Check if all dependencies are finalized
        is_ready, _ = self.check_ready(pdo_id)
        state.status = NodeStatus.READY if is_ready else NodeStatus.PENDING

    # ─────────────────────────────────────────────────────────────────────────
    # Topological Order
    # ─────────────────────────────────────────────────────────────────────────

    def get_topological_order(self) -> List[str]:
        """
        Get a valid topological ordering of all nodes.
        
        Returns PDO IDs in an order where dependencies come before dependents.
        """
        with self._lock:
            if not self.is_acyclic():
                raise CyclicDependencyError("Graph contains cycles")
            
            in_degree: Dict[str, int] = {pdo_id: 0 for pdo_id in self._nodes}
            for downstream_id, upstream_ids in self._dependencies.items():
                in_degree[downstream_id] = len(upstream_ids)
            
            result: List[str] = []
            queue = [pdo_id for pdo_id, degree in in_degree.items() if degree == 0]
            
            while queue:
                current = queue.pop(0)
                result.append(current)
                
                for dependent_id in self._dependents.get(current, set()):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
            
            return result

    def _get_dependency_depth(self, pdo_id: str) -> int:
        """Get the maximum depth of the dependency chain for a node."""
        deps = self._dependencies.get(pdo_id, set())
        if not deps:
            return 0
        return 1 + max(self._get_dependency_depth(d) for d in deps)

    # ─────────────────────────────────────────────────────────────────────────
    # Query & Export
    # ─────────────────────────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        with self._lock:
            status_counts = {s.value: 0 for s in NodeStatus}
            for state in self._states.values():
                status_counts[state.status.value] += 1
            
            return {
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "status_distribution": status_counts,
                "cross_agent_dependencies": len(self._cross_agent_log),
                "is_acyclic": self.is_acyclic(),
            }

    def export_json(self) -> str:
        """Export graph as JSON."""
        with self._lock:
            data = {
                "nodes": [
                    {
                        **node.to_dict(),
                        "status": self._states[node.pdo_id].status.value,
                        "finalized_at": self._states[node.pdo_id].finalized_at,
                    }
                    for node in self._nodes.values()
                ],
                "edges": [edge.to_dict() for edge in self._edges.values()],
                "cross_agent_log": self._cross_agent_log,
                "statistics": self.get_statistics(),
                "exported_at": datetime.utcnow().isoformat() + "Z",
            }
            return json.dumps(data, indent=2)

    def get_cross_agent_log(self) -> List[Dict[str, Any]]:
        """Get log of cross-agent dependencies."""
        with self._lock:
            return self._cross_agent_log.copy()


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_graph: Optional[PDODependencyGraph] = None
_global_lock = threading.Lock()


def get_dependency_graph(config: Optional[Dict[str, Any]] = None) -> PDODependencyGraph:
    """Get or create the global dependency graph instance."""
    global _global_graph
    
    with _global_lock:
        if _global_graph is None:
            _global_graph = PDODependencyGraph(config)
        return _global_graph


def reset_dependency_graph() -> None:
    """Reset the global dependency graph (for testing)."""
    global _global_graph
    
    with _global_lock:
        _global_graph = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def declare_dependency(
    upstream_pdo_id: str,
    downstream_pdo_id: str,
    dependency_type: DependencyType = DependencyType.DATA,
) -> DependencyEdge:
    """
    Convenience function to declare a dependency.
    
    Usage:
        declare_dependency("PDO-A", "PDO-B")  # B depends on A
    """
    graph = get_dependency_graph()
    return graph.add_dependency(upstream_pdo_id, downstream_pdo_id, dependency_type)


def can_finalize(pdo_id: str) -> Tuple[bool, List[str]]:
    """Check if a PDO can be finalized."""
    graph = get_dependency_graph()
    return graph.check_ready(pdo_id)
