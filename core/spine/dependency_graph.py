"""
Cross-Agent Dependency Graph — Static + Runtime Dependency Validation.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-04 (Cindy) — BACKEND
Deliverable: Cross-Agent Dependency Graph with Validation

Features:
- Static dependency analysis
- Runtime dependency tracking
- Cycle detection and prevention
- Dependency health monitoring
- Impact analysis for changes

This module provides comprehensive dependency management between
agents to ensure clean execution ordering and detect issues early.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple


# =============================================================================
# CONSTANTS
# =============================================================================

MODULE_VERSION = "1.0.0"
MAX_DEPENDENCY_DEPTH = 10


# =============================================================================
# ENUMS
# =============================================================================

class DependencyScope(Enum):
    """Scope of dependency."""
    STATIC = "STATIC"    # Declared at definition time
    RUNTIME = "RUNTIME"  # Discovered at runtime
    INFERRED = "INFERRED"  # Inferred from data flow


class DependencyStrength(Enum):
    """Strength of dependency relationship."""
    REQUIRED = "REQUIRED"  # Must complete before dependent
    OPTIONAL = "OPTIONAL"  # Preferred but not mandatory
    WEAK = "WEAK"          # Nice to have


class DependencyStatus(Enum):
    """Status of a dependency relationship."""
    PENDING = "PENDING"
    SATISFIED = "SATISFIED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NodeState(Enum):
    """State of a dependency graph node."""
    UNVISITED = "UNVISITED"
    VISITING = "VISITING"  # Currently in DFS path
    VISITED = "VISITED"


class HealthStatus(Enum):
    """Health status of dependency graph."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DependencyError(Exception):
    """Base exception for dependency errors."""
    pass


class CyclicDependencyError(DependencyError):
    """Raised when cyclic dependency detected."""
    
    def __init__(self, cycle: List[str]) -> None:
        self.cycle = cycle
        cycle_str = " → ".join(cycle)
        super().__init__(f"Cyclic dependency detected: {cycle_str}")


class DependencyNotFoundError(DependencyError):
    """Raised when dependency not found."""
    
    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target
        super().__init__(f"Dependency not found: {source} → {target}")


class MaxDepthExceededError(DependencyError):
    """Raised when dependency chain too deep."""
    
    def __init__(self, agent_id: str, depth: int) -> None:
        self.agent_id = agent_id
        self.depth = depth
        super().__init__(
            f"Max dependency depth ({MAX_DEPENDENCY_DEPTH}) exceeded for {agent_id}"
        )


class UnsatisfiedDependencyError(DependencyError):
    """Raised when required dependency not satisfied."""
    
    def __init__(self, agent_id: str, dependencies: List[str]) -> None:
        self.agent_id = agent_id
        self.dependencies = dependencies
        super().__init__(
            f"Agent {agent_id} has unsatisfied dependencies: {dependencies}"
        )


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Dependency:
    """Represents a dependency between two agents."""
    
    dependency_id: str
    source_agent: str  # Provider
    target_agent: str  # Dependent
    scope: DependencyScope
    strength: DependencyStrength
    status: DependencyStatus = DependencyStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    satisfied_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash((self.source_agent, self.target_agent))
    
    def satisfy(self) -> None:
        """Mark dependency as satisfied."""
        self.status = DependencyStatus.SATISFIED
        self.satisfied_at = datetime.now(timezone.utc).isoformat()
    
    def fail(self) -> None:
        """Mark dependency as failed."""
        self.status = DependencyStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize dependency."""
        return {
            "dependency_id": self.dependency_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "scope": self.scope.value,
            "strength": self.strength.value,
            "status": self.status.value,
        }


@dataclass
class AgentNode:
    """Represents an agent in the dependency graph."""
    
    agent_id: str
    name: str
    state: NodeState = NodeState.UNVISITED
    dependencies: Set[str] = field(default_factory=set)  # Agents this depends on
    dependents: Set[str] = field(default_factory=set)    # Agents depending on this
    depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.agent_id)
    
    @property
    def is_root(self) -> bool:
        """Check if node is a root (no dependencies)."""
        return len(self.dependencies) == 0
    
    @property
    def is_leaf(self) -> bool:
        """Check if node is a leaf (no dependents)."""
        return len(self.dependents) == 0


@dataclass
class DependencyPath:
    """A path through the dependency graph."""
    
    path: List[str]
    total_depth: int
    
    def __len__(self) -> int:
        return len(self.path)
    
    @property
    def start(self) -> str:
        """Start of path."""
        return self.path[0] if self.path else ""
    
    @property
    def end(self) -> str:
        """End of path."""
        return self.path[-1] if self.path else ""
    
    def contains(self, agent_id: str) -> bool:
        """Check if path contains agent."""
        return agent_id in self.path


@dataclass
class ImpactAnalysis:
    """Impact analysis for a change."""
    
    analysis_id: str
    changed_agent: str
    directly_affected: Set[str]
    transitively_affected: Set[str]
    total_affected: int
    critical_paths: List[DependencyPath]
    generated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize analysis."""
        return {
            "analysis_id": self.analysis_id,
            "changed_agent": self.changed_agent,
            "directly_affected": list(self.directly_affected),
            "transitively_affected": list(self.transitively_affected),
            "total_affected": self.total_affected,
        }


@dataclass
class DependencyHealth:
    """Health status of dependency graph."""
    
    status: HealthStatus
    total_agents: int
    total_dependencies: int
    satisfied_dependencies: int
    failed_dependencies: int
    pending_dependencies: int
    has_cycles: bool
    max_depth: int
    orphaned_agents: int
    issues: List[str] = field(default_factory=list)
    
    @property
    def satisfaction_rate(self) -> float:
        """Calculate dependency satisfaction rate."""
        total = self.satisfied_dependencies + self.failed_dependencies
        if total == 0:
            return 1.0
        return self.satisfied_dependencies / total
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize health report."""
        return {
            "status": self.status.value,
            "total_agents": self.total_agents,
            "total_dependencies": self.total_dependencies,
            "satisfaction_rate": f"{self.satisfaction_rate:.1%}",
            "has_cycles": self.has_cycles,
            "max_depth": self.max_depth,
            "issues": self.issues,
        }


# =============================================================================
# DEPENDENCY GRAPH
# =============================================================================

class CrossAgentDependencyGraph:
    """
    Manages cross-agent dependencies with validation.
    """
    
    def __init__(self) -> None:
        self._nodes: Dict[str, AgentNode] = {}
        self._dependencies: Dict[Tuple[str, str], Dependency] = {}
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)  # source -> targets
        self._reverse: Dict[str, Set[str]] = defaultdict(set)    # target -> sources
    
    # -------------------------------------------------------------------------
    # NODE MANAGEMENT
    # -------------------------------------------------------------------------
    
    def add_agent(
        self,
        agent_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentNode:
        """Add an agent to the graph."""
        if agent_id in self._nodes:
            return self._nodes[agent_id]
        
        node = AgentNode(
            agent_id=agent_id,
            name=name,
            metadata=metadata or {},
        )
        self._nodes[agent_id] = node
        return node
    
    def get_agent(self, agent_id: str) -> Optional[AgentNode]:
        """Get agent node by ID."""
        return self._nodes.get(agent_id)
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent and all its dependencies."""
        if agent_id not in self._nodes:
            return
        
        # Remove all dependencies involving this agent
        to_remove = [
            key for key in self._dependencies
            if agent_id in key
        ]
        for key in to_remove:
            del self._dependencies[key]
        
        # Update adjacency lists
        for target in self._adjacency.get(agent_id, set()):
            self._reverse[target].discard(agent_id)
        for source in self._reverse.get(agent_id, set()):
            self._adjacency[source].discard(agent_id)
        
        self._adjacency.pop(agent_id, None)
        self._reverse.pop(agent_id, None)
        del self._nodes[agent_id]
    
    # -------------------------------------------------------------------------
    # DEPENDENCY MANAGEMENT
    # -------------------------------------------------------------------------
    
    def add_dependency(
        self,
        source_agent: str,
        target_agent: str,
        scope: DependencyScope = DependencyScope.STATIC,
        strength: DependencyStrength = DependencyStrength.REQUIRED,
    ) -> Dependency:
        """
        Add a dependency: source must complete before target.
        
        Args:
            source_agent: Agent that provides (runs first)
            target_agent: Agent that depends (runs after)
            scope: Scope of dependency
            strength: Strength of dependency
        
        Returns:
            Created Dependency object
            
        Raises:
            CyclicDependencyError: If adding creates a cycle
        """
        # Ensure both agents exist
        if source_agent not in self._nodes:
            self.add_agent(source_agent, source_agent)
        if target_agent not in self._nodes:
            self.add_agent(target_agent, target_agent)
        
        # Check for cycle
        if self._would_create_cycle(source_agent, target_agent):
            raise CyclicDependencyError([target_agent, source_agent, target_agent])
        
        dependency_id = f"DEP-{uuid.uuid4().hex[:8].upper()}"
        
        dep = Dependency(
            dependency_id=dependency_id,
            source_agent=source_agent,
            target_agent=target_agent,
            scope=scope,
            strength=strength,
        )
        
        key = (source_agent, target_agent)
        self._dependencies[key] = dep
        
        # Update adjacency
        self._adjacency[source_agent].add(target_agent)
        self._reverse[target_agent].add(source_agent)
        
        # Update node references
        self._nodes[target_agent].dependencies.add(source_agent)
        self._nodes[source_agent].dependents.add(target_agent)
        
        # Update depths
        self._recalculate_depths()
        
        return dep
    
    def remove_dependency(self, source_agent: str, target_agent: str) -> None:
        """Remove a dependency."""
        key = (source_agent, target_agent)
        if key not in self._dependencies:
            raise DependencyNotFoundError(source_agent, target_agent)
        
        del self._dependencies[key]
        
        self._adjacency[source_agent].discard(target_agent)
        self._reverse[target_agent].discard(source_agent)
        
        if source_agent in self._nodes:
            self._nodes[source_agent].dependents.discard(target_agent)
        if target_agent in self._nodes:
            self._nodes[target_agent].dependencies.discard(source_agent)
        
        self._recalculate_depths()
    
    def get_dependency(
        self,
        source_agent: str,
        target_agent: str,
    ) -> Optional[Dependency]:
        """Get dependency between two agents."""
        return self._dependencies.get((source_agent, target_agent))
    
    def satisfy_dependency(self, source_agent: str, target_agent: str) -> None:
        """Mark a dependency as satisfied."""
        dep = self.get_dependency(source_agent, target_agent)
        if dep:
            dep.satisfy()
    
    def fail_dependency(self, source_agent: str, target_agent: str) -> None:
        """Mark a dependency as failed."""
        dep = self.get_dependency(source_agent, target_agent)
        if dep:
            dep.fail()
    
    # -------------------------------------------------------------------------
    # CYCLE DETECTION
    # -------------------------------------------------------------------------
    
    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Check if adding dependency would create cycle."""
        # A cycle would be created if target can reach source
        visited = set()
        stack = [target]
        
        while stack:
            current = stack.pop()
            if current == source:
                return True
            
            if current in visited:
                continue
            visited.add(current)
            
            # Add all agents that depend on current
            stack.extend(self._adjacency.get(current, set()))
        
        return False
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect all cycles in the graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._adjacency.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        for node in self._nodes:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def has_cycles(self) -> bool:
        """Check if graph has any cycles."""
        return len(self.detect_cycles()) > 0
    
    # -------------------------------------------------------------------------
    # DEPENDENCY QUERIES
    # -------------------------------------------------------------------------
    
    def get_dependencies(self, agent_id: str) -> Set[str]:
        """Get agents that must complete before this agent."""
        return self._reverse.get(agent_id, set()).copy()
    
    def get_dependents(self, agent_id: str) -> Set[str]:
        """Get agents that depend on this agent."""
        return self._adjacency.get(agent_id, set()).copy()
    
    def get_all_dependencies(self, agent_id: str) -> Set[str]:
        """Get all transitive dependencies."""
        all_deps = set()
        stack = list(self.get_dependencies(agent_id))
        
        while stack:
            dep = stack.pop()
            if dep not in all_deps:
                all_deps.add(dep)
                stack.extend(self.get_dependencies(dep))
        
        return all_deps
    
    def get_all_dependents(self, agent_id: str) -> Set[str]:
        """Get all transitive dependents."""
        all_deps = set()
        stack = list(self.get_dependents(agent_id))
        
        while stack:
            dep = stack.pop()
            if dep not in all_deps:
                all_deps.add(dep)
                stack.extend(self.get_dependents(dep))
        
        return all_deps
    
    # -------------------------------------------------------------------------
    # EXECUTION ORDER
    # -------------------------------------------------------------------------
    
    def topological_sort(self) -> List[str]:
        """
        Return agents in topological order (dependencies first).
        
        Raises:
            CyclicDependencyError: If graph has cycles
        """
        cycles = self.detect_cycles()
        if cycles:
            raise CyclicDependencyError(cycles[0])
        
        in_degree = {node: len(self._reverse.get(node, set())) for node in self._nodes}
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            queue.sort()  # Deterministic ordering
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self._adjacency.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def get_execution_batches(self) -> List[List[str]]:
        """
        Get agents grouped into parallel execution batches.
        
        Returns:
            List of batches, where agents in each batch can run in parallel.
        """
        if self.has_cycles():
            raise CyclicDependencyError(self.detect_cycles()[0])
        
        batches = []
        remaining = set(self._nodes.keys())
        completed = set()
        
        while remaining:
            # Find agents whose dependencies are all satisfied
            batch = []
            for agent in remaining:
                deps = self.get_dependencies(agent)
                if deps <= completed:
                    batch.append(agent)
            
            if not batch:
                raise DependencyError("Dependency resolution deadlock")
            
            batch.sort()
            batches.append(batch)
            completed.update(batch)
            remaining -= set(batch)
        
        return batches
    
    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------
    
    def validate_ready(self, agent_id: str) -> List[str]:
        """
        Validate if agent is ready to execute.
        
        Returns:
            List of unsatisfied dependencies (empty if ready)
        """
        unsatisfied = []
        
        for dep_agent in self.get_dependencies(agent_id):
            dep = self.get_dependency(dep_agent, agent_id)
            if dep and dep.strength == DependencyStrength.REQUIRED:
                if dep.status != DependencyStatus.SATISFIED:
                    unsatisfied.append(dep_agent)
        
        return unsatisfied
    
    def require_ready(self, agent_id: str) -> None:
        """
        Require agent to be ready for execution.
        
        Raises:
            UnsatisfiedDependencyError: If dependencies not satisfied
        """
        unsatisfied = self.validate_ready(agent_id)
        if unsatisfied:
            raise UnsatisfiedDependencyError(agent_id, unsatisfied)
    
    # -------------------------------------------------------------------------
    # DEPTH CALCULATION
    # -------------------------------------------------------------------------
    
    def _recalculate_depths(self) -> None:
        """Recalculate depths for all nodes."""
        # Reset depths
        for node in self._nodes.values():
            node.depth = 0
        
        # Calculate depth from roots
        def calculate_depth(agent_id: str, depth: int, visited: Set[str]) -> None:
            if depth > MAX_DEPENDENCY_DEPTH:
                return
            
            if agent_id in visited:
                return
            visited.add(agent_id)
            
            node = self._nodes.get(agent_id)
            if node:
                node.depth = max(node.depth, depth)
                
                for dependent in self.get_dependents(agent_id):
                    calculate_depth(dependent, depth + 1, visited)
        
        # Start from roots
        roots = [a for a, node in self._nodes.items() if node.is_root]
        for root in roots:
            calculate_depth(root, 0, set())
    
    def get_max_depth(self) -> int:
        """Get maximum dependency depth."""
        if not self._nodes:
            return 0
        return max(node.depth for node in self._nodes.values())
    
    # -------------------------------------------------------------------------
    # IMPACT ANALYSIS
    # -------------------------------------------------------------------------
    
    def analyze_impact(self, agent_id: str) -> ImpactAnalysis:
        """Analyze impact of changes to an agent."""
        directly_affected = self.get_dependents(agent_id)
        transitively_affected = self.get_all_dependents(agent_id) - directly_affected
        
        # Find critical paths
        critical_paths = []
        for dependent in directly_affected:
            path = DependencyPath(
                path=[agent_id, dependent],
                total_depth=1,
            )
            critical_paths.append(path)
        
        return ImpactAnalysis(
            analysis_id=f"IA-{uuid.uuid4().hex[:8].upper()}",
            changed_agent=agent_id,
            directly_affected=directly_affected,
            transitively_affected=transitively_affected,
            total_affected=len(directly_affected) + len(transitively_affected),
            critical_paths=critical_paths,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    
    # -------------------------------------------------------------------------
    # HEALTH CHECK
    # -------------------------------------------------------------------------
    
    def check_health(self) -> DependencyHealth:
        """Perform health check on dependency graph."""
        issues = []
        
        # Count dependencies by status
        satisfied = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.SATISFIED)
        failed = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.FAILED)
        pending = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.PENDING)
        
        # Check for cycles
        has_cycles = self.has_cycles()
        if has_cycles:
            issues.append("Cyclic dependencies detected")
        
        # Find orphaned agents (no deps or dependents)
        orphaned = sum(
            1 for node in self._nodes.values()
            if node.is_root and node.is_leaf and len(self._nodes) > 1
        )
        if orphaned > 0:
            issues.append(f"{orphaned} orphaned agents")
        
        # Check depth
        max_depth = self.get_max_depth()
        if max_depth > MAX_DEPENDENCY_DEPTH:
            issues.append(f"Max depth ({max_depth}) exceeds limit ({MAX_DEPENDENCY_DEPTH})")
        
        # Determine status
        if has_cycles or failed > 0:
            status = HealthStatus.UNHEALTHY
        elif issues:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        return DependencyHealth(
            status=status,
            total_agents=len(self._nodes),
            total_dependencies=len(self._dependencies),
            satisfied_dependencies=satisfied,
            failed_dependencies=failed,
            pending_dependencies=pending,
            has_cycles=has_cycles,
            max_depth=max_depth,
            orphaned_agents=orphaned,
            issues=issues,
        )
    
    # -------------------------------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "agents": list(self._nodes.keys()),
            "dependencies": [
                dep.to_dict() for dep in self._dependencies.values()
            ],
            "stats": {
                "total_agents": len(self._nodes),
                "total_dependencies": len(self._dependencies),
                "max_depth": self.get_max_depth(),
            },
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_dependency_graph() -> CrossAgentDependencyGraph:
    """Create a new dependency graph."""
    return CrossAgentDependencyGraph()


def create_dependency(
    source: str,
    target: str,
    strength: DependencyStrength = DependencyStrength.REQUIRED,
) -> Dependency:
    """Create a dependency object."""
    return Dependency(
        dependency_id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
        source_agent=source,
        target_agent=target,
        scope=DependencyScope.STATIC,
        strength=strength,
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version
    "MODULE_VERSION",
    # Constants
    "MAX_DEPENDENCY_DEPTH",
    # Enums
    "DependencyScope",
    "DependencyStrength",
    "DependencyStatus",
    "NodeState",
    "HealthStatus",
    # Exceptions
    "DependencyError",
    "CyclicDependencyError",
    "DependencyNotFoundError",
    "MaxDepthExceededError",
    "UnsatisfiedDependencyError",
    # Data Classes
    "Dependency",
    "AgentNode",
    "DependencyPath",
    "ImpactAnalysis",
    "DependencyHealth",
    # Core Classes
    "CrossAgentDependencyGraph",
    # Factory Functions
    "create_dependency_graph",
    "create_dependency",
]
