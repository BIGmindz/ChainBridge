"""
Governance Lineage Graph Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-08: Implement GovernanceLineageGraph primitive

Implements:
- DAG builder and ancestry tracking
- Lineage validation engine
- Authority inheritance verification
- Orphan detection and rejection
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class NodeType(Enum):
    """Node types in the governance lineage graph."""
    GENESIS = "GENESIS"
    PAC = "PAC"
    WRAP = "WRAP"
    BER = "BER"
    DOCTRINE = "DOCTRINE"
    LEDGER_COMMIT = "LEDGER_COMMIT"


class EdgeType(Enum):
    """Edge types representing relationships between nodes."""
    DERIVES_FROM = "DERIVES_FROM"
    SUPERSEDES = "SUPERSEDES"
    REFERENCES = "REFERENCES"
    AUTHORIZES = "AUTHORIZES"
    REVOKES = "REVOKES"


class AuthorityLevel(Enum):
    """Authority levels in the governance hierarchy."""
    CONSTITUTIONAL = 1000  # Highest
    LAW_TIER = 100
    POLICY_TIER = 10
    ADVISORY_TIER = 1


@dataclass
class LineageNode:
    """A node in the governance lineage graph."""
    node_id: str
    node_type: NodeType
    parent_ids: list[str]
    authority_level: AuthorityLevel
    timestamp: datetime
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    depth: int = 0
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "parent_ids": self.parent_ids,
            "authority_level": self.authority_level.value,
            "timestamp": self.timestamp.isoformat(),
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "depth": self.depth,
            "active": self.active
        }


@dataclass
class LineageEdge:
    """An edge connecting two nodes in the lineage graph."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ValidationResult:
    """Result of lineage validation."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "validated_at": self.validated_at.isoformat()
        }


class GovernanceLineageGraph:
    """
    DAG-based governance lineage tracking system.
    
    Enforces:
    - Mandatory ancestry declaration
    - Immutable lineage chain
    - Transitive authority inheritance
    - Orphan rejection
    """

    GENESIS_NODE_ID = "GENESIS-CHAINBRIDGE-001"

    def __init__(self, storage_path: Optional[Path] = None):
        self.nodes: dict[str, LineageNode] = {}
        self.edges: list[LineageEdge] = []
        self.storage_path = storage_path or Path("data/lineage_graph.json")
        self._initialize_genesis()

    def _initialize_genesis(self) -> None:
        """Initialize the GENESIS root node."""
        genesis = LineageNode(
            node_id=self.GENESIS_NODE_ID,
            node_type=NodeType.GENESIS,
            parent_ids=[],
            authority_level=AuthorityLevel.CONSTITUTIONAL,
            timestamp=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            content_hash=self._compute_hash({"type": "GENESIS", "authority": "JEFFREY"}),
            metadata={
                "authority": "JEFFREY (Architect)",
                "description": "Root authority for ChainBridge governance"
            },
            depth=0,
            active=True
        )
        self.nodes[genesis.node_id] = genesis

    def _compute_hash(self, content: Any) -> str:
        """Compute SHA3-256 hash of content."""
        content_bytes = json.dumps(content, sort_keys=True, default=str).encode()
        return f"sha3-256:{hashlib.sha3_256(content_bytes).hexdigest()}"

    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        parent_ids: list[str],
        content: Any,
        authority_level: Optional[AuthorityLevel] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> tuple[LineageNode, ValidationResult]:
        """
        Add a new node to the lineage graph with validation.
        
        Enforces:
        - Parents must exist
        - Authority cannot exceed parent authority
        - No cycles allowed
        - Path to GENESIS required
        """
        validation = self._validate_new_node(node_id, parent_ids, authority_level)
        
        if not validation.valid:
            raise ValueError(f"Lineage validation failed: {validation.errors}")

        # Calculate inherited authority (minimum of parents)
        if authority_level is None:
            parent_authorities = [
                self.nodes[pid].authority_level.value 
                for pid in parent_ids
            ]
            inherited_value = min(parent_authorities) if parent_authorities else AuthorityLevel.ADVISORY_TIER.value
            authority_level = AuthorityLevel(inherited_value)

        # Calculate depth (max of parents + 1)
        parent_depths = [self.nodes[pid].depth for pid in parent_ids]
        depth = max(parent_depths) + 1 if parent_depths else 1

        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            parent_ids=parent_ids,
            authority_level=authority_level,
            timestamp=datetime.now(timezone.utc),
            content_hash=self._compute_hash(content),
            metadata=metadata or {},
            depth=depth,
            active=True
        )

        # Add node
        self.nodes[node_id] = node

        # Create edges to parents
        for parent_id in parent_ids:
            edge = LineageEdge(
                source_id=node_id,
                target_id=parent_id,
                edge_type=EdgeType.DERIVES_FROM,
                timestamp=datetime.now(timezone.utc)
            )
            self.edges.append(edge)

        return node, validation

    def _validate_new_node(
        self,
        node_id: str,
        parent_ids: list[str],
        authority_level: Optional[AuthorityLevel]
    ) -> ValidationResult:
        """Validate a new node against lineage rules."""
        errors = []
        warnings = []

        # Check node doesn't already exist
        if node_id in self.nodes:
            errors.append(f"Node {node_id} already exists")

        # Check parents exist
        for parent_id in parent_ids:
            if parent_id not in self.nodes:
                errors.append(f"Parent node {parent_id} does not exist")

        # Check for orphan (no parents and not GENESIS)
        if not parent_ids and node_id != self.GENESIS_NODE_ID:
            errors.append("Orphan node rejected: no parents declared")

        # Validate authority inheritance
        if authority_level and parent_ids:
            for parent_id in parent_ids:
                if parent_id in self.nodes:
                    parent_authority = self.nodes[parent_id].authority_level.value
                    if authority_level.value > parent_authority:
                        errors.append(
                            f"Authority {authority_level.value} exceeds parent "
                            f"{parent_id} authority {parent_authority}"
                        )

        # Check path to GENESIS exists
        if parent_ids:
            has_genesis_path = any(
                self._has_path_to_genesis(pid) 
                for pid in parent_ids 
                if pid in self.nodes
            )
            if not has_genesis_path:
                errors.append("No valid path to GENESIS node")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _has_path_to_genesis(self, node_id: str, visited: Optional[set] = None) -> bool:
        """Check if a node has a path to GENESIS."""
        if visited is None:
            visited = set()

        if node_id == self.GENESIS_NODE_ID:
            return True

        if node_id in visited:
            return False  # Cycle detected

        visited.add(node_id)

        node = self.nodes.get(node_id)
        if not node:
            return False

        return any(
            self._has_path_to_genesis(parent_id, visited)
            for parent_id in node.parent_ids
        )

    def validate_acyclicity(self) -> ValidationResult:
        """Validate the graph is acyclic (DAG property)."""
        errors = []
        
        # DFS-based cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in self.nodes}
        
        def dfs(node_id: str) -> bool:
            color[node_id] = GRAY
            node = self.nodes[node_id]
            for parent_id in node.parent_ids:
                if parent_id in color:
                    if color[parent_id] == GRAY:
                        return True  # Cycle found
                    if color[parent_id] == WHITE and dfs(parent_id):
                        return True
            color[node_id] = BLACK
            return False

        for node_id in self.nodes:
            if color[node_id] == WHITE:
                if dfs(node_id):
                    errors.append(f"Cycle detected involving node {node_id}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def get_ancestry(self, node_id: str) -> list[LineageNode]:
        """Get all ancestors of a node."""
        ancestors = []
        visited = set()

        def collect_ancestors(nid: str) -> None:
            if nid in visited or nid not in self.nodes:
                return
            visited.add(nid)
            node = self.nodes[nid]
            ancestors.append(node)
            for parent_id in node.parent_ids:
                collect_ancestors(parent_id)

        node = self.nodes.get(node_id)
        if node:
            for parent_id in node.parent_ids:
                collect_ancestors(parent_id)

        return ancestors

    def get_authority_chain(self, node_id: str) -> list[tuple[str, AuthorityLevel]]:
        """Get the authority chain from a node to GENESIS."""
        chain = []
        visited = set()

        def trace_authority(nid: str) -> None:
            if nid in visited or nid not in self.nodes:
                return
            visited.add(nid)
            node = self.nodes[nid]
            chain.append((nid, node.authority_level))
            if node.parent_ids:
                # Follow highest authority parent
                best_parent = max(
                    node.parent_ids,
                    key=lambda pid: self.nodes[pid].authority_level.value if pid in self.nodes else 0
                )
                trace_authority(best_parent)

        trace_authority(node_id)
        return chain

    def mark_superseded(self, old_node_id: str, new_node_id: str) -> None:
        """Mark a node as superseded by another node."""
        if old_node_id not in self.nodes:
            raise ValueError(f"Node {old_node_id} not found")
        if new_node_id not in self.nodes:
            raise ValueError(f"Node {new_node_id} not found")

        self.nodes[old_node_id].active = False
        
        edge = LineageEdge(
            source_id=new_node_id,
            target_id=old_node_id,
            edge_type=EdgeType.SUPERSEDES,
            timestamp=datetime.now(timezone.utc)
        )
        self.edges.append(edge)

    def export_graph(self) -> dict[str, Any]:
        """Export the graph to a serializable format."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "statistics": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "active_nodes": sum(1 for n in self.nodes.values() if n.active),
                "max_depth": max((n.depth for n in self.nodes.values()), default=0)
            }
        }

    def save(self) -> None:
        """Persist graph to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export_graph(), f, indent=2)

    def load(self) -> None:
        """Load graph from storage."""
        if not self.storage_path.exists():
            return

        with open(self.storage_path) as f:
            data = json.load(f)

        self.nodes.clear()
        self.edges.clear()

        for node_data in data.get("nodes", []):
            node = LineageNode(
                node_id=node_data["node_id"],
                node_type=NodeType(node_data["node_type"]),
                parent_ids=node_data["parent_ids"],
                authority_level=AuthorityLevel(node_data["authority_level"]),
                timestamp=datetime.fromisoformat(node_data["timestamp"]),
                content_hash=node_data["content_hash"],
                metadata=node_data.get("metadata", {}),
                depth=node_data.get("depth", 0),
                active=node_data.get("active", True)
            )
            self.nodes[node.node_id] = node

        for edge_data in data.get("edges", []):
            edge = LineageEdge(
                source_id=edge_data["source_id"],
                target_id=edge_data["target_id"],
                edge_type=EdgeType(edge_data["edge_type"]),
                timestamp=datetime.fromisoformat(edge_data["timestamp"]),
                metadata=edge_data.get("metadata", {})
            )
            self.edges.append(edge)


# Singleton instance for global access
_lineage_graph: Optional[GovernanceLineageGraph] = None


def get_lineage_graph() -> GovernanceLineageGraph:
    """Get the global lineage graph instance."""
    global _lineage_graph
    if _lineage_graph is None:
        _lineage_graph = GovernanceLineageGraph()
    return _lineage_graph


def register_pac_lineage(
    pac_id: str,
    parent_pac_ids: list[str],
    pac_content: dict[str, Any],
    authority_level: Optional[AuthorityLevel] = None
) -> ValidationResult:
    """
    Register a PAC in the lineage graph.
    
    Called during PAC admission to ensure lineage is tracked.
    """
    graph = get_lineage_graph()
    
    # If no explicit parents, derive from GENESIS via BENSON orchestration
    if not parent_pac_ids:
        parent_pac_ids = [GovernanceLineageGraph.GENESIS_NODE_ID]

    node, validation = graph.add_node(
        node_id=pac_id,
        node_type=NodeType.PAC,
        parent_ids=parent_pac_ids,
        content=pac_content,
        authority_level=authority_level,
        metadata={
            "title": pac_content.get("title", "Unknown"),
            "classification": pac_content.get("classification", "POLICY_TIER")
        }
    )

    return validation
