"""
Multi-Agent Execution Graph (MAEG) Schema Definition

Authority: PAC-BENSON-P66-MULTI-AGENT-ORCHESTRATION-GOVERNED-EXECUTION-MODEL-01
Doctrine Reference: GOVERNANCE_DOCTRINE_V1.3

This module defines the schema and types for Multi-Agent Execution Graphs (MAEGs),
which specify the topology and execution order for governed parallel agent execution.

PROPERTIES:
  - Directed Acyclic Graph (DAG)
  - Every node has exactly one Sub-PAC
  - Every node produces exactly one BER
  - All paths converge to single PDO-ORCH

INVARIANTS:
  - No cycles (DAG property)
  - Every node produces independent BER
  - All nodes must complete for WRAP
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .sub_pac import SubPAC, SubPACStatus, create_sub_pac


class NodeType(str, Enum):
    """Types of nodes in the MAEG."""
    
    ORCH_ROOT = "ORCH_ROOT"      # Orchestration PAC (parent)
    AGENT_NODE = "AGENT_NODE"    # Individual agent execution
    SYNC_POINT = "SYNC_POINT"    # Barrier synchronization
    AGGREGATION = "AGGREGATION"  # PDO combination point
    TERMINAL = "TERMINAL"        # WRAP emission


class EdgeType(str, Enum):
    """Types of edges in the MAEG."""
    
    DEPENDENCY = "DEPENDENCY"    # A must complete before B
    DATA_FLOW = "DATA_FLOW"      # A's output feeds B's input
    BARRIER = "BARRIER"          # All predecessors must complete


class MAEGStatus(str, Enum):
    """Status of the MAEG execution."""
    
    CREATED = "CREATED"
    DISPATCHING = "DISPATCHING"
    EXECUTING = "EXECUTING"
    AGGREGATING = "AGGREGATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class MAEGNode:
    """
    A node in the Multi-Agent Execution Graph.
    
    Each AGENT_NODE corresponds to a Sub-PAC assigned to a specific agent.
    """
    
    node_id: str  # e.g., "A1", "A2", "SYNC-1", "AGG"
    node_type: NodeType
    
    # Agent details (only for AGENT_NODE)
    agent_gid: Optional[str] = None
    agent_name: Optional[str] = None
    execution_lane: Optional[str] = None
    task_descriptor: Optional[str] = None
    
    # Associated Sub-PAC (populated when MAEG is built)
    sub_pac: Optional[SubPAC] = None
    
    # Execution state
    dispatched: bool = False
    completed: bool = False
    failed: bool = False
    
    def is_agent_node(self) -> bool:
        """Check if this is an agent execution node."""
        return self.node_type == NodeType.AGENT_NODE
    
    def is_ready_for_dispatch(self, completed_nodes: set[str]) -> bool:
        """
        Check if this node is ready for dispatch based on completed predecessors.
        
        This is evaluated by the MAEG using edge information.
        """
        return not self.dispatched and not self.failed
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "agent_gid": self.agent_gid,
            "agent_name": self.agent_name,
            "execution_lane": self.execution_lane,
            "task_descriptor": self.task_descriptor,
            "sub_pac_id": self.sub_pac.sub_pac_id if self.sub_pac else None,
            "dispatched": self.dispatched,
            "completed": self.completed,
            "failed": self.failed,
        }


@dataclass
class MAEGEdge:
    """
    An edge in the Multi-Agent Execution Graph.
    
    Edges define dependencies and data flow between nodes.
    """
    
    from_node: str  # Source node ID
    to_node: str    # Target node ID
    edge_type: EdgeType
    constraint: str = "BER_PASS_REQUIRED"  # Default constraint
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "from": self.from_node,
            "to": self.to_node,
            "type": self.edge_type.value,
            "constraint": self.constraint,
        }


@dataclass
class MAEGSyncPoint:
    """
    A synchronization point in the MAEG.
    
    Sync points are barriers where all predecessor nodes must complete
    before the successor can proceed.
    """
    
    sync_id: str  # e.g., "SYNC-1"
    predecessors: list[str]  # Node IDs that must complete
    successor: str  # Node ID that waits
    
    def all_predecessors_complete(self, completed_nodes: set[str]) -> bool:
        """Check if all predecessors have completed."""
        return all(pred in completed_nodes for pred in self.predecessors)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sync_id": self.sync_id,
            "predecessors": self.predecessors,
            "successor": self.successor,
        }


@dataclass
class PDOAggregation:
    """PDO aggregation specification for the MAEG."""
    
    aggregation_type: str = "MERKLE_AGGREGATION"
    input_pdo_ids: list[str] = field(default_factory=list)
    output_pdo_id: Optional[str] = None
    merkle_root: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": self.aggregation_type,
            "inputs": self.input_pdo_ids,
            "output": self.output_pdo_id,
            "merkle_root": self.merkle_root,
        }


@dataclass
class MultiAgentExecutionGraph:
    """
    Multi-Agent Execution Graph (MAEG).
    
    A MAEG is a Directed Acyclic Graph that specifies:
      1. Which agents participate in execution
      2. Dependencies between agent tasks
      3. Data flow between agents
      4. Synchronization points
    
    Authority: PAC-BENSON-P66
    """
    
    # Identity
    maeg_id: str  # e.g., "MAEG-BENSON-P66"
    parent_pac_id: str  # e.g., "PAC-BENSON-P66-..."
    
    # Graph structure
    nodes: dict[str, MAEGNode] = field(default_factory=dict)
    edges: list[MAEGEdge] = field(default_factory=list)
    sync_points: list[MAEGSyncPoint] = field(default_factory=list)
    
    # Aggregation
    aggregation: PDOAggregation = field(default_factory=PDOAggregation)
    
    # State
    status: MAEGStatus = MAEGStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Tracking
    completed_nodes: set[str] = field(default_factory=set)
    failed_nodes: set[str] = field(default_factory=set)
    
    # Hash for integrity
    maeg_hash: Optional[str] = None
    
    def __post_init__(self):
        """Initialize and validate the MAEG."""
        if self.nodes:
            self._validate_dag()
            self.maeg_hash = self._compute_hash()
    
    # --- Graph Construction ---
    
    def add_agent_node(
        self,
        node_id: str,
        agent_gid: str,
        agent_name: str,
        execution_lane: str,
        task_descriptor: str,
    ) -> MAEGNode:
        """
        Add an agent node to the MAEG.
        
        Args:
            node_id: Unique identifier for the node (e.g., "A1").
            agent_gid: The agent's GID.
            agent_name: The agent's name.
            execution_lane: The execution lane.
            task_descriptor: Short descriptor for the task.
        
        Returns:
            The created MAEGNode.
        """
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists in MAEG")
        
        node = MAEGNode(
            node_id=node_id,
            node_type=NodeType.AGENT_NODE,
            agent_gid=agent_gid,
            agent_name=agent_name,
            execution_lane=execution_lane,
            task_descriptor=task_descriptor,
        )
        self.nodes[node_id] = node
        return node
    
    def add_sync_point(
        self,
        sync_id: str,
        predecessors: list[str],
        successor: str,
    ) -> MAEGSyncPoint:
        """
        Add a synchronization point to the MAEG.
        
        Args:
            sync_id: Unique identifier for the sync point.
            predecessors: Node IDs that must complete.
            successor: Node ID that waits for all predecessors.
        
        Returns:
            The created MAEGSyncPoint.
        """
        # Validate predecessors exist
        for pred in predecessors:
            if pred not in self.nodes:
                raise ValueError(f"Predecessor node {pred} not found in MAEG")
        
        # Validate successor exists
        if successor not in self.nodes:
            raise ValueError(f"Successor node {successor} not found in MAEG")
        
        sync_point = MAEGSyncPoint(
            sync_id=sync_id,
            predecessors=predecessors,
            successor=successor,
        )
        self.sync_points.append(sync_point)
        
        # Add barrier edges
        for pred in predecessors:
            self.add_edge(pred, successor, EdgeType.BARRIER)
        
        return sync_point
    
    def add_edge(
        self,
        from_node: str,
        to_node: str,
        edge_type: EdgeType = EdgeType.DEPENDENCY,
        constraint: str = "BER_PASS_REQUIRED",
    ) -> MAEGEdge:
        """
        Add an edge to the MAEG.
        
        Args:
            from_node: Source node ID.
            to_node: Target node ID.
            edge_type: Type of edge.
            constraint: Constraint on the edge.
        
        Returns:
            The created MAEGEdge.
        """
        if from_node not in self.nodes:
            raise ValueError(f"Source node {from_node} not found in MAEG")
        if to_node not in self.nodes:
            raise ValueError(f"Target node {to_node} not found in MAEG")
        
        edge = MAEGEdge(
            from_node=from_node,
            to_node=to_node,
            edge_type=edge_type,
            constraint=constraint,
        )
        self.edges.append(edge)
        
        # Re-validate DAG property
        self._validate_dag()
        
        return edge
    
    # --- Validation ---
    
    def _validate_dag(self) -> None:
        """
        Validate that the graph is a DAG (no cycles).
        
        Raises GS_202 (MAEG_CYCLE_DETECTED) if a cycle is found.
        """
        # Build adjacency list
        adj: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            adj[edge.from_node].append(edge.to_node)
        
        # Topological sort using Kahn's algorithm
        in_degree: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            in_degree[edge.to_node] += 1
        
        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        sorted_count = 0
        
        while queue:
            node = queue.popleft()
            sorted_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if sorted_count != len(self.nodes):
            raise ValueError(
                "GS_202: MAEG_CYCLE_DETECTED - Graph contains a cycle"
            )
    
    def _compute_hash(self) -> str:
        """Compute the MAEG hash for integrity verification."""
        content = {
            "maeg_id": self.maeg_id,
            "parent_pac_id": self.parent_pac_id,
            "nodes": [n.node_id for n in sorted(self.nodes.values(), key=lambda x: x.node_id)],
            "edges": [(e.from_node, e.to_node) for e in self.edges],
            "created_at": self.created_at.isoformat(),
        }
        canonical = json.dumps(content, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    # --- Sub-PAC Generation ---
    
    def generate_sub_pacs(self) -> list[SubPAC]:
        """
        Generate Sub-PACs for all agent nodes in the MAEG.
        
        Each agent node receives a Sub-PAC with:
          - Dependencies derived from incoming edges
          - Lane restriction to the assigned agent
          - Inherited scope from parent PAC
        
        Returns:
            List of generated SubPACs.
        """
        sub_pacs: list[SubPAC] = []
        
        # Build dependency map from edges
        dependencies: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            if edge.edge_type in (EdgeType.DEPENDENCY, EdgeType.BARRIER):
                dependencies[edge.to_node].append(edge.from_node)
        
        # Generate Sub-PACs for agent nodes
        sequence = 0
        for node_id in self._topological_order():
            node = self.nodes[node_id]
            if not node.is_agent_node():
                continue
            
            sequence += 1
            
            # Map node dependencies to Sub-PAC IDs
            dep_sub_pac_ids = []
            for dep_node_id in dependencies[node_id]:
                dep_node = self.nodes.get(dep_node_id)
                if dep_node and dep_node.sub_pac:
                    dep_sub_pac_ids.append(dep_node.sub_pac.sub_pac_id)
            
            sub_pac = create_sub_pac(
                parent_pac_id=self.parent_pac_id,
                sequence=sequence,
                agent_gid=node.agent_gid,
                agent_name=node.agent_name,
                execution_lane=node.execution_lane,
                task_descriptor=node.task_descriptor,
                dependencies=dep_sub_pac_ids,
            )
            
            node.sub_pac = sub_pac
            sub_pacs.append(sub_pac)
        
        return sub_pacs
    
    def _topological_order(self) -> list[str]:
        """Return nodes in topological order."""
        # Build adjacency list
        adj: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            adj[edge.from_node].append(edge.to_node)
        
        # Kahn's algorithm
        in_degree: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            in_degree[edge.to_node] += 1
        
        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        result: list[str] = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    # --- Dispatch Logic ---
    
    def get_dispatchable_nodes(self) -> list[MAEGNode]:
        """
        Get all nodes that are ready for dispatch.
        
        A node is dispatchable if:
          1. It has not been dispatched yet
          2. All its predecessor nodes have completed
          3. It has not failed
        
        Returns:
            List of dispatchable MAEGNodes.
        """
        dispatchable: list[MAEGNode] = []
        
        # Build dependency map
        dependencies: dict[str, set[str]] = {node_id: set() for node_id in self.nodes}
        for edge in self.edges:
            dependencies[edge.to_node].add(edge.from_node)
        
        for node_id, node in self.nodes.items():
            if not node.is_agent_node():
                continue
            if node.dispatched or node.failed:
                continue
            
            # Check if all dependencies are complete
            if dependencies[node_id].issubset(self.completed_nodes):
                dispatchable.append(node)
        
        return dispatchable
    
    def get_root_nodes(self) -> list[MAEGNode]:
        """
        Get all root nodes (no incoming edges).
        
        These nodes can be dispatched immediately.
        """
        # Find nodes with no incoming edges
        has_incoming: set[str] = set()
        for edge in self.edges:
            has_incoming.add(edge.to_node)
        
        roots: list[MAEGNode] = []
        for node_id, node in self.nodes.items():
            if node.is_agent_node() and node_id not in has_incoming:
                roots.append(node)
        
        return roots
    
    # --- State Management ---
    
    def mark_node_dispatched(self, node_id: str) -> None:
        """Mark a node as dispatched."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in MAEG")
        self.nodes[node_id].dispatched = True
        
        if self.status == MAEGStatus.CREATED:
            self.status = MAEGStatus.DISPATCHING
    
    def mark_node_completed(self, node_id: str) -> None:
        """Mark a node as completed."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in MAEG")
        
        self.nodes[node_id].completed = True
        self.completed_nodes.add(node_id)
        
        # Check if all agent nodes are complete
        agent_nodes = [n for n in self.nodes.values() if n.is_agent_node()]
        if all(n.completed for n in agent_nodes):
            self.status = MAEGStatus.AGGREGATING
    
    def mark_node_failed(self, node_id: str) -> None:
        """
        Mark a node as failed.
        
        This cascades to block all dependent nodes.
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found in MAEG")
        
        self.nodes[node_id].failed = True
        self.failed_nodes.add(node_id)
        
        # Cascade failure to dependents
        self._cascade_failure(node_id)
        
        self.status = MAEGStatus.FAILED
    
    def _cascade_failure(self, failed_node_id: str) -> None:
        """Cascade failure to all dependent nodes."""
        # Find all nodes that depend on the failed node
        dependents: set[str] = set()
        
        def find_dependents(node_id: str) -> None:
            for edge in self.edges:
                if edge.from_node == node_id and edge.to_node not in dependents:
                    dependents.add(edge.to_node)
                    find_dependents(edge.to_node)
        
        find_dependents(failed_node_id)
        
        # Block all dependents
        for dep_id in dependents:
            node = self.nodes.get(dep_id)
            if node and node.sub_pac:
                node.sub_pac.block(
                    f"Blocked due to failure of predecessor {failed_node_id}"
                )
                node.failed = True
                self.failed_nodes.add(dep_id)
    
    def finalize(self, pdo_orch_id: str, merkle_root: str) -> None:
        """
        Finalize the MAEG after successful aggregation.
        
        Args:
            pdo_orch_id: The PDO-ORCH ID.
            merkle_root: The merkle root of all child PDOs.
        """
        self.aggregation.output_pdo_id = pdo_orch_id
        self.aggregation.merkle_root = merkle_root
        self.aggregation.input_pdo_ids = [
            n.sub_pac.outputs.pdo_id
            for n in self.nodes.values()
            if n.sub_pac and n.sub_pac.outputs.pdo_id
        ]
        self.completed_at = datetime.utcnow()
        self.status = MAEGStatus.COMPLETE
    
    # --- Queries ---
    
    def is_complete(self) -> bool:
        """Check if the MAEG has completed successfully."""
        return self.status == MAEGStatus.COMPLETE
    
    def is_failed(self) -> bool:
        """Check if the MAEG has failed."""
        return self.status == MAEGStatus.FAILED
    
    def get_agent_count(self) -> int:
        """Get the number of agent nodes in the MAEG."""
        return sum(1 for n in self.nodes.values() if n.is_agent_node())
    
    def get_all_sub_pacs(self) -> list[SubPAC]:
        """Get all Sub-PACs from the MAEG."""
        return [
            n.sub_pac for n in self.nodes.values()
            if n.sub_pac is not None
        ]
    
    def get_all_bers(self) -> list[str]:
        """Get all BER IDs from completed Sub-PACs."""
        return [
            n.sub_pac.outputs.ber_id
            for n in self.nodes.values()
            if n.sub_pac and n.sub_pac.outputs.ber_id
        ]
    
    def get_all_pdos(self) -> list[str]:
        """Get all PDO IDs from completed Sub-PACs."""
        return [
            n.sub_pac.outputs.pdo_id
            for n in self.nodes.values()
            if n.sub_pac and n.sub_pac.outputs.pdo_id
        ]
    
    # --- Serialization ---
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "maeg_id": self.maeg_id,
            "parent_pac_id": self.parent_pac_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "sync_points": [s.to_dict() for s in self.sync_points],
            "aggregation": self.aggregation.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_nodes": list(self.completed_nodes),
            "failed_nodes": list(self.failed_nodes),
            "maeg_hash": self.maeg_hash,
        }


# --- Factory Functions ---

def create_maeg(parent_pac_id: str) -> MultiAgentExecutionGraph:
    """
    Factory function to create an empty MAEG.
    
    Args:
        parent_pac_id: The parent PAC ID.
    
    Returns:
        A new MultiAgentExecutionGraph instance.
    """
    # Extract short form for MAEG ID
    parts = parent_pac_id.replace("PAC-", "").split("-")
    pac_short = "-".join(parts[:2]) if len(parts) >= 2 else parts[0]
    maeg_id = f"MAEG-{pac_short}"
    
    return MultiAgentExecutionGraph(
        maeg_id=maeg_id,
        parent_pac_id=parent_pac_id,
    )


def build_linear_maeg(
    parent_pac_id: str,
    agents: list[tuple[str, str, str, str]],  # (gid, name, lane, task)
) -> MultiAgentExecutionGraph:
    """
    Build a linear MAEG where agents execute in sequence.
    
    A1 → A2 → A3 → ...
    
    Args:
        parent_pac_id: The parent PAC ID.
        agents: List of (agent_gid, agent_name, execution_lane, task_descriptor).
    
    Returns:
        A MultiAgentExecutionGraph with linear dependencies.
    """
    maeg = create_maeg(parent_pac_id)
    
    prev_node_id: Optional[str] = None
    for i, (gid, name, lane, task) in enumerate(agents, start=1):
        node_id = f"A{i}"
        maeg.add_agent_node(
            node_id=node_id,
            agent_gid=gid,
            agent_name=name,
            execution_lane=lane,
            task_descriptor=task,
        )
        
        if prev_node_id:
            maeg.add_edge(prev_node_id, node_id, EdgeType.DEPENDENCY)
        
        prev_node_id = node_id
    
    maeg.maeg_hash = maeg._compute_hash()
    return maeg


def build_parallel_maeg(
    parent_pac_id: str,
    agents: list[tuple[str, str, str, str]],  # (gid, name, lane, task)
) -> MultiAgentExecutionGraph:
    """
    Build a parallel MAEG where all agents can execute concurrently.
    
    A1 ─┐
    A2 ─┤ (no dependencies)
    A3 ─┘
    
    Args:
        parent_pac_id: The parent PAC ID.
        agents: List of (agent_gid, agent_name, execution_lane, task_descriptor).
    
    Returns:
        A MultiAgentExecutionGraph with no inter-dependencies.
    """
    maeg = create_maeg(parent_pac_id)
    
    for i, (gid, name, lane, task) in enumerate(agents, start=1):
        node_id = f"A{i}"
        maeg.add_agent_node(
            node_id=node_id,
            agent_gid=gid,
            agent_name=name,
            execution_lane=lane,
            task_descriptor=task,
        )
    
    maeg.maeg_hash = maeg._compute_hash()
    return maeg


def build_fanout_fanin_maeg(
    parent_pac_id: str,
    root_agent: tuple[str, str, str, str],
    parallel_agents: list[tuple[str, str, str, str]],
    final_agent: tuple[str, str, str, str],
) -> MultiAgentExecutionGraph:
    """
    Build a fan-out/fan-in MAEG.
    
           A1 ──┐
    ROOT → A2 ──┼──→ FINAL
           A3 ──┘
    
    Args:
        parent_pac_id: The parent PAC ID.
        root_agent: The initial agent (gid, name, lane, task).
        parallel_agents: Agents that execute in parallel after root.
        final_agent: The final agent that waits for all parallel agents.
    
    Returns:
        A MultiAgentExecutionGraph with fan-out/fan-in topology.
    """
    maeg = create_maeg(parent_pac_id)
    
    # Add root node
    gid, name, lane, task = root_agent
    maeg.add_agent_node("A0", gid, name, lane, task)
    
    # Add parallel nodes
    parallel_node_ids: list[str] = []
    for i, (gid, name, lane, task) in enumerate(parallel_agents, start=1):
        node_id = f"A{i}"
        maeg.add_agent_node(node_id, gid, name, lane, task)
        maeg.add_edge("A0", node_id, EdgeType.DEPENDENCY)
        parallel_node_ids.append(node_id)
    
    # Add final node
    final_idx = len(parallel_agents) + 1
    gid, name, lane, task = final_agent
    maeg.add_agent_node(f"A{final_idx}", gid, name, lane, task)
    
    # Add sync point
    maeg.add_sync_point(
        sync_id="SYNC-FINAL",
        predecessors=parallel_node_ids,
        successor=f"A{final_idx}",
    )
    
    maeg.maeg_hash = maeg._compute_hash()
    return maeg
