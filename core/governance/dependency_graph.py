# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Execution Dependency Graph & Causality Mapping
# PAC-012: Governance Hardening — ORDER 2 (Cindy GID-02)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Execution dependency graph with hard/soft dependencies, order-to-artifact
causality mapping, and explicit failure propagation rules.

GOVERNANCE INVARIANTS:
- INV-GOV-002: No execution without declared dependencies
- INV-GOV-003: No silent partial success
- INV-GOV-008: Fail-closed on any violation
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY TYPES (INV-GOV-002)
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyType(str, Enum):
    """
    Type of execution dependency.
    
    INV-GOV-002: No execution without declared dependencies.
    """
    HARD = "HARD"  # Must complete successfully before dependent can start
    SOFT = "SOFT"  # Should complete, but dependent can proceed with degraded state


class DependencyStatus(str, Enum):
    """Status of a dependency resolution."""
    PENDING = "PENDING"
    SATISFIED = "SATISFIED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ArtifactType(str, Enum):
    """Types of execution artifacts."""
    FILE = "FILE"
    DATABASE_RECORD = "DATABASE_RECORD"
    API_RESPONSE = "API_RESPONSE"
    LEDGER_ENTRY = "LEDGER_ENTRY"
    LOG_ENTRY = "LOG_ENTRY"
    METRIC = "METRIC"
    CONFIG = "CONFIG"


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY DECLARATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionDependency:
    """
    Declaration of an execution dependency.
    
    INV-GOV-002: All dependencies must be declared before execution.
    """
    dependency_id: str
    pac_id: str
    
    # Dependent order (the one that requires the dependency)
    dependent_order_id: str
    dependent_agent_gid: str
    
    # Dependency source (the order being depended upon)
    source_order_id: str
    source_agent_gid: str
    
    # Dependency characteristics
    dependency_type: DependencyType
    description: str
    
    # Status
    status: DependencyStatus = DependencyStatus.PENDING
    
    # Timing
    declared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    
    # Failure handling
    on_failure_action: str = "BLOCK"  # BLOCK, DEGRADE, SKIP
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dependency_id": self.dependency_id,
            "pac_id": self.pac_id,
            "dependent_order_id": self.dependent_order_id,
            "dependent_agent_gid": self.dependent_agent_gid,
            "source_order_id": self.source_order_id,
            "source_agent_gid": self.source_agent_gid,
            "dependency_type": self.dependency_type.value,
            "description": self.description,
            "status": self.status.value,
            "declared_at": self.declared_at,
            "resolved_at": self.resolved_at,
            "on_failure_action": self.on_failure_action,
        }
    
    @property
    def is_blocking(self) -> bool:
        """Check if this dependency blocks execution."""
        return self.dependency_type == DependencyType.HARD


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSALITY MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ArtifactReference:
    """
    Reference to an execution artifact.
    """
    artifact_id: str
    artifact_type: ArtifactType
    location: str  # Path, URI, or identifier
    
    # Metadata
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "location": self.location,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
        }


@dataclass
class CausalityLink:
    """
    Link between an execution order and its produced artifacts.
    
    Maps order → artifacts for full causality tracing.
    """
    link_id: str
    pac_id: str
    order_id: str
    agent_gid: str
    
    # Produced artifact
    artifact: ArtifactReference
    
    # Causality chain
    caused_by_order_ids: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Hash for integrity
    link_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "link_id": self.link_id,
            "pac_id": self.pac_id,
            "order_id": self.order_id,
            "agent_gid": self.agent_gid,
            "artifact": self.artifact.to_dict(),
            "caused_by_order_ids": self.caused_by_order_ids,
            "created_at": self.created_at,
            "link_hash": self.link_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE PROPAGATION (INV-GOV-003, INV-GOV-008)
# ═══════════════════════════════════════════════════════════════════════════════

class FailurePropagationMode(str, Enum):
    """
    How failures propagate through the dependency graph.
    
    INV-GOV-003: No silent partial success.
    INV-GOV-008: Fail-closed on any violation.
    """
    IMMEDIATE = "IMMEDIATE"     # Fail all dependents immediately
    CASCADING = "CASCADING"     # Propagate sequentially through graph
    CONTAINED = "CONTAINED"     # Contain to affected branch only
    ISOLATED = "ISOLATED"       # No propagation (soft dependencies only)


@dataclass
class FailurePropagationRule:
    """
    Rule defining how failure propagates in the dependency graph.
    """
    rule_id: str
    pac_id: str
    
    # Source of failure
    failing_order_id: str
    
    # Propagation behavior
    mode: FailurePropagationMode
    
    # Affected dependents
    affected_order_ids: List[str] = field(default_factory=list)
    
    # Override behavior
    allow_partial_success: bool = False
    required_success_ratio: float = 1.0
    
    # Actions
    notification_required: bool = True
    human_review_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "pac_id": self.pac_id,
            "failing_order_id": self.failing_order_id,
            "mode": self.mode.value,
            "affected_order_ids": self.affected_order_ids,
            "allow_partial_success": self.allow_partial_success,
            "required_success_ratio": self.required_success_ratio,
            "notification_required": self.notification_required,
            "human_review_required": self.human_review_required,
        }


@dataclass
class FailurePropagationEvent:
    """
    Record of a failure propagation event.
    """
    event_id: str
    pac_id: str
    source_order_id: str
    
    # Propagation details
    propagation_mode: FailurePropagationMode
    orders_blocked: List[str]
    orders_degraded: List[str]
    
    # Impact
    total_affected: int
    cascade_depth: int
    
    # Timestamps
    propagated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyGraph:
    """
    Execution dependency graph with topological ordering and cycle detection.
    
    INV-GOV-002: No execution without declared dependencies.
    """
    
    def __init__(self, pac_id: str):
        """Initialize empty graph for a PAC."""
        self.pac_id = pac_id
        self._dependencies: Dict[str, ExecutionDependency] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # source -> dependents
        self._reverse_adjacency: Dict[str, Set[str]] = {}  # dependent -> sources
        self._lock = threading.Lock()
    
    def add_dependency(self, dependency: ExecutionDependency) -> None:
        """
        Add a dependency to the graph.
        
        INV-GOV-002: Validates no circular dependencies.
        """
        with self._lock:
            # Validate PAC ID
            if dependency.pac_id != self.pac_id:
                from core.governance.governance_schema import GovernanceViolation
                raise GovernanceViolation(
                    invariant="INV-GOV-002",
                    message=f"Dependency PAC ID mismatch: {dependency.pac_id} != {self.pac_id}",
                )
            
            # Check for cycles before adding
            if self._would_create_cycle(
                dependency.source_order_id,
                dependency.dependent_order_id,
            ):
                from core.governance.governance_schema import GovernanceViolation
                raise GovernanceViolation(
                    invariant="INV-GOV-002",
                    message=f"Circular dependency detected: {dependency.source_order_id} -> {dependency.dependent_order_id}",
                    context={
                        "source": dependency.source_order_id,
                        "dependent": dependency.dependent_order_id,
                    },
                )
            
            # Store dependency
            self._dependencies[dependency.dependency_id] = dependency
            
            # Update adjacency lists
            source = dependency.source_order_id
            dependent = dependency.dependent_order_id
            
            if source not in self._adjacency:
                self._adjacency[source] = set()
            self._adjacency[source].add(dependent)
            
            if dependent not in self._reverse_adjacency:
                self._reverse_adjacency[dependent] = set()
            self._reverse_adjacency[dependent].add(source)
            
            logger.debug(
                f"DEPENDENCY: Added {source} -> {dependent} ({dependency.dependency_type.value})"
            )
    
    def get_dependencies_for(self, order_id: str) -> List[ExecutionDependency]:
        """Get all dependencies that must be satisfied before an order can execute."""
        with self._lock:
            source_ids = self._reverse_adjacency.get(order_id, set())
            return [
                dep for dep in self._dependencies.values()
                if dep.source_order_id in source_ids
                and dep.dependent_order_id == order_id
            ]
    
    def get_dependents_of(self, order_id: str) -> List[str]:
        """Get all orders that depend on the given order."""
        with self._lock:
            return list(self._adjacency.get(order_id, set()))
    
    def get_execution_order(self) -> List[str]:
        """
        Get topologically sorted execution order.
        
        Returns list of order IDs in valid execution sequence.
        """
        with self._lock:
            # Collect all nodes
            all_nodes: Set[str] = set()
            for dep in self._dependencies.values():
                all_nodes.add(dep.source_order_id)
                all_nodes.add(dep.dependent_order_id)
            
            # Kahn's algorithm for topological sort
            in_degree: Dict[str, int] = {node: 0 for node in all_nodes}
            for node in all_nodes:
                for source in self._reverse_adjacency.get(node, set()):
                    in_degree[node] += 1
            
            # Start with nodes that have no dependencies
            queue = [node for node, degree in in_degree.items() if degree == 0]
            result: List[str] = []
            
            while queue:
                node = queue.pop(0)
                result.append(node)
                
                for dependent in self._adjacency.get(node, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            # Check for cycles (should not happen if add_dependency validates)
            if len(result) != len(all_nodes):
                from core.governance.governance_schema import GovernanceViolation
                raise GovernanceViolation(
                    invariant="INV-GOV-002",
                    message="Cycle detected in dependency graph",
                )
            
            return result
    
    def can_execute(self, order_id: str) -> Tuple[bool, List[str]]:
        """
        Check if an order can execute given current dependency states.
        
        Returns (can_execute, list of unsatisfied dependencies).
        """
        with self._lock:
            unsatisfied: List[str] = []
            
            for dep in self._dependencies.values():
                if dep.dependent_order_id != order_id:
                    continue
                
                if dep.dependency_type == DependencyType.HARD:
                    if dep.status != DependencyStatus.SATISFIED:
                        unsatisfied.append(dep.source_order_id)
            
            return len(unsatisfied) == 0, unsatisfied
    
    def mark_satisfied(self, dependency_id: str) -> None:
        """Mark a dependency as satisfied."""
        with self._lock:
            if dependency_id in self._dependencies:
                self._dependencies[dependency_id].status = DependencyStatus.SATISFIED
                self._dependencies[dependency_id].resolved_at = datetime.now(timezone.utc).isoformat()
    
    def mark_failed(self, dependency_id: str) -> None:
        """Mark a dependency as failed."""
        with self._lock:
            if dependency_id in self._dependencies:
                self._dependencies[dependency_id].status = DependencyStatus.FAILED
                self._dependencies[dependency_id].resolved_at = datetime.now(timezone.utc).isoformat()
    
    def propagate_failure(self, order_id: str, mode: FailurePropagationMode) -> FailurePropagationEvent:
        """
        Propagate failure through the dependency graph.
        
        INV-GOV-003: No silent partial success.
        """
        with self._lock:
            blocked: List[str] = []
            degraded: List[str] = []
            
            def propagate_recursive(node: str, depth: int):
                dependents = self._adjacency.get(node, set())
                for dep in dependents:
                    dep_obj = next(
                        (d for d in self._dependencies.values() if d.dependent_order_id == dep),
                        None
                    )
                    if dep_obj:
                        if dep_obj.dependency_type == DependencyType.HARD:
                            blocked.append(dep)
                            if mode == FailurePropagationMode.CASCADING:
                                propagate_recursive(dep, depth + 1)
                        else:
                            degraded.append(dep)
            
            if mode in {FailurePropagationMode.IMMEDIATE, FailurePropagationMode.CASCADING}:
                propagate_recursive(order_id, 0)
            
            event = FailurePropagationEvent(
                event_id=f"fprop_{uuid.uuid4().hex[:12]}",
                pac_id=self.pac_id,
                source_order_id=order_id,
                propagation_mode=mode,
                orders_blocked=blocked,
                orders_degraded=degraded,
                total_affected=len(blocked) + len(degraded),
                cascade_depth=self._calculate_cascade_depth(order_id),
            )
            
            logger.warning(
                f"FAILURE PROPAGATION: {order_id} affected {event.total_affected} orders"
            )
            
            return event
    
    def _would_create_cycle(self, source: str, dependent: str) -> bool:
        """Check if adding source -> dependent would create a cycle."""
        # If dependent can reach source, adding this edge creates a cycle
        visited: Set[str] = set()
        
        def dfs(node: str) -> bool:
            if node == source:
                return True
            if node in visited:
                return False
            visited.add(node)
            
            for next_node in self._adjacency.get(node, set()):
                if dfs(next_node):
                    return True
            return False
        
        return dfs(dependent)
    
    def _calculate_cascade_depth(self, order_id: str) -> int:
        """Calculate maximum cascade depth from an order."""
        def max_depth(node: str, visited: Set[str]) -> int:
            if node in visited:
                return 0
            visited.add(node)
            
            dependents = self._adjacency.get(node, set())
            if not dependents:
                return 0
            
            return 1 + max(max_depth(dep, visited) for dep in dependents)
        
        return max_depth(order_id, set())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary representation."""
        with self._lock:
            return {
                "pac_id": self.pac_id,
                "dependencies": [dep.to_dict() for dep in self._dependencies.values()],
                "adjacency": {k: list(v) for k, v in self._adjacency.items()},
                "execution_order": self.get_execution_order() if self._dependencies else [],
            }


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSALITY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class CausalityRegistry:
    """
    Registry for tracking order-to-artifact causality.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._links: List[CausalityLink] = []
        self._by_order_id: Dict[str, List[CausalityLink]] = {}
        self._by_artifact_id: Dict[str, CausalityLink] = {}
        self._lock = threading.Lock()
    
    def record_artifact(
        self,
        pac_id: str,
        order_id: str,
        agent_gid: str,
        artifact: ArtifactReference,
        caused_by_order_ids: Optional[List[str]] = None,
    ) -> CausalityLink:
        """Record an artifact produced by an order."""
        with self._lock:
            link_id = f"causal_{uuid.uuid4().hex[:12]}"
            
            # Compute hash
            content = f"{link_id}|{pac_id}|{order_id}|{artifact.artifact_id}"
            link_hash = hashlib.sha256(content.encode()).hexdigest()
            
            link = CausalityLink(
                link_id=link_id,
                pac_id=pac_id,
                order_id=order_id,
                agent_gid=agent_gid,
                artifact=artifact,
                caused_by_order_ids=caused_by_order_ids or [],
                link_hash=link_hash,
            )
            
            self._links.append(link)
            
            if order_id not in self._by_order_id:
                self._by_order_id[order_id] = []
            self._by_order_id[order_id].append(link)
            
            self._by_artifact_id[artifact.artifact_id] = link
            
            logger.debug(f"CAUSALITY: Recorded artifact {artifact.artifact_id} from order {order_id}")
            
            return link
    
    def get_artifacts_by_order(self, order_id: str) -> List[CausalityLink]:
        """Get all artifacts produced by an order."""
        with self._lock:
            return self._by_order_id.get(order_id, []).copy()
    
    def trace_causality(self, artifact_id: str) -> List[str]:
        """Trace causality chain for an artifact back to originating orders."""
        with self._lock:
            result: List[str] = []
            
            link = self._by_artifact_id.get(artifact_id)
            if not link:
                return result
            
            visited: Set[str] = set()
            
            def trace(order_id: str):
                if order_id in visited:
                    return
                visited.add(order_id)
                result.append(order_id)
                
                # Find artifacts from this order and trace their causes
                for l in self._by_order_id.get(order_id, []):
                    for caused_by in l.caused_by_order_ids:
                        trace(caused_by)
            
            trace(link.order_id)
            return result
    
    def __len__(self) -> int:
        """Return number of causality links."""
        with self._lock:
            return len(self._links)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY GRAPH REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyGraphRegistry:
    """
    Registry managing dependency graphs per PAC.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._graphs: Dict[str, DependencyGraph] = {}
        self._lock = threading.Lock()
    
    def get_or_create(self, pac_id: str) -> DependencyGraph:
        """Get or create dependency graph for a PAC."""
        with self._lock:
            if pac_id not in self._graphs:
                self._graphs[pac_id] = DependencyGraph(pac_id)
                logger.info(f"Created dependency graph for PAC {pac_id}")
            return self._graphs[pac_id]
    
    def get(self, pac_id: str) -> Optional[DependencyGraph]:
        """Get dependency graph for a PAC if it exists."""
        with self._lock:
            return self._graphs.get(pac_id)
    
    def list_pac_ids(self) -> List[str]:
        """List all PAC IDs with dependency graphs."""
        with self._lock:
            return list(self._graphs.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_DEPENDENCY_REGISTRY: Optional[DependencyGraphRegistry] = None
_CAUSALITY_REGISTRY: Optional[CausalityRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_dependency_registry() -> DependencyGraphRegistry:
    """Get singleton dependency graph registry."""
    global _DEPENDENCY_REGISTRY
    
    if _DEPENDENCY_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _DEPENDENCY_REGISTRY is None:
                _DEPENDENCY_REGISTRY = DependencyGraphRegistry()
                logger.info("Dependency graph registry initialized")
    
    return _DEPENDENCY_REGISTRY


def get_causality_registry() -> CausalityRegistry:
    """Get singleton causality registry."""
    global _CAUSALITY_REGISTRY
    
    if _CAUSALITY_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _CAUSALITY_REGISTRY is None:
                _CAUSALITY_REGISTRY = CausalityRegistry()
                logger.info("Causality registry initialized")
    
    return _CAUSALITY_REGISTRY


def reset_dependency_registry() -> None:
    """Reset dependency registry singleton. For testing only."""
    global _DEPENDENCY_REGISTRY
    with _REGISTRY_LOCK:
        _DEPENDENCY_REGISTRY = None


def reset_causality_registry() -> None:
    """Reset causality registry singleton. For testing only."""
    global _CAUSALITY_REGISTRY
    with _REGISTRY_LOCK:
        _CAUSALITY_REGISTRY = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Dependency types
    "DependencyType",
    "DependencyStatus",
    "ArtifactType",
    # Dependency declaration
    "ExecutionDependency",
    # Causality
    "ArtifactReference",
    "CausalityLink",
    # Failure propagation
    "FailurePropagationMode",
    "FailurePropagationRule",
    "FailurePropagationEvent",
    # Graph
    "DependencyGraph",
    # Registries
    "CausalityRegistry",
    "DependencyGraphRegistry",
    "get_dependency_registry",
    "get_causality_registry",
    "reset_dependency_registry",
    "reset_causality_registry",
]
