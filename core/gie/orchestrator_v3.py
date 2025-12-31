"""
GIE Orchestrator v3 — Production-Grade Multi-Agent Orchestration Engine.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-01 (Cody) — CORE / ORCHESTRATION
Deliverable: GIE Orchestrator v3

Features:
- Dependency resolution between agents
- Checkpointed resumability
- Fault isolation and recovery
- Parallel execution with synchronization barriers
- Hash-verified state management

This orchestrator manages the full lifecycle of multi-agent PAC execution
with deterministic state transitions and FAIL-CLOSED error handling.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed


# =============================================================================
# CONSTANTS
# =============================================================================

ORCHESTRATOR_VERSION = "3.0.0"
MAX_RETRY_ATTEMPTS = 3
CHECKPOINT_INTERVAL_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 300


# =============================================================================
# ENUMS
# =============================================================================

class AgentState(Enum):
    """Agent execution states."""
    PENDING = "PENDING"
    READY = "READY"  # Dependencies satisfied
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    CHECKPOINTED = "CHECKPOINTED"
    WRAP_RECEIVED = "WRAP_RECEIVED"
    FAILED = "FAILED"
    ISOLATED = "ISOLATED"  # Fault isolation


class ExecutionMode(Enum):
    """Orchestrator execution modes."""
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    HYBRID = "HYBRID"  # Parallel with dependency barriers


class FaultStrategy(Enum):
    """Fault handling strategies."""
    FAIL_FAST = "FAIL_FAST"  # Stop all on first failure
    FAIL_ISOLATED = "FAIL_ISOLATED"  # Isolate failed, continue others
    RETRY = "RETRY"  # Retry with backoff
    CHECKPOINT_RESUME = "CHECKPOINT_RESUME"  # Resume from checkpoint


class CheckpointState(Enum):
    """Checkpoint states."""
    NONE = "NONE"
    PENDING = "PENDING"
    SAVED = "SAVED"
    RESTORED = "RESTORED"
    CORRUPTED = "CORRUPTED"


class DependencyType(Enum):
    """Types of agent dependencies."""
    HARD = "HARD"  # Must complete before dependent starts
    SOFT = "SOFT"  # Preferred but not required
    DATA = "DATA"  # Data dependency (can share partial results)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""
    pass


class DependencyCycleError(OrchestratorError):
    """Raised when circular dependency detected."""
    
    def __init__(self, cycle: List[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle)}")


class DependencyNotSatisfiedError(OrchestratorError):
    """Raised when dependency not satisfied."""
    
    def __init__(self, agent_id: str, dependency: str) -> None:
        self.agent_id = agent_id
        self.dependency = dependency
        super().__init__(
            f"Agent '{agent_id}' has unsatisfied dependency: '{dependency}'"
        )


class AgentExecutionError(OrchestratorError):
    """Raised when agent execution fails."""
    
    def __init__(self, agent_id: str, reason: str, recoverable: bool = False) -> None:
        self.agent_id = agent_id
        self.reason = reason
        self.recoverable = recoverable
        super().__init__(f"Agent '{agent_id}' failed: {reason}")


class CheckpointError(OrchestratorError):
    """Raised when checkpoint operation fails."""
    
    def __init__(self, operation: str, reason: str) -> None:
        self.operation = operation
        self.reason = reason
        super().__init__(f"Checkpoint {operation} failed: {reason}")


class FaultIsolationError(OrchestratorError):
    """Raised when fault isolation fails."""
    
    def __init__(self, agent_id: str, cascade_agents: List[str]) -> None:
        self.agent_id = agent_id
        self.cascade_agents = cascade_agents
        super().__init__(
            f"Fault in '{agent_id}' cascaded to: {cascade_agents}"
        )


class ResumabilityError(OrchestratorError):
    """Raised when resumption fails."""
    
    def __init__(self, session_id: str, reason: str) -> None:
        self.session_id = session_id
        self.reason = reason
        super().__init__(f"Cannot resume session '{session_id}': {reason}")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class AgentDependency:
    """Defines a dependency between agents."""
    
    source_agent: str  # Agent that provides
    target_agent: str  # Agent that depends
    dependency_type: DependencyType
    required_outputs: FrozenSet[str] = frozenset()  # Specific outputs needed
    
    def __hash__(self) -> int:
        return hash((self.source_agent, self.target_agent, self.dependency_type))


@dataclass
class AgentSpec:
    """Specification for an agent in the orchestration."""
    
    agent_id: str
    role: str
    lane: str
    deliverables: List[str]
    test_requirement: int = 0  # Minimum tests required
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    retryable: bool = True
    priority: int = 0  # Higher = higher priority
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash(self.agent_id)


@dataclass
class AgentExecution:
    """Runtime state of an agent execution."""
    
    spec: AgentSpec
    state: AgentState = AgentState.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    wrap_hash: Optional[str] = None
    test_count: int = 0
    retry_count: int = 0
    error: Optional[str] = None
    checkpoint_id: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration."""
        if not self.started_at or not self.completed_at:
            return None
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.completed_at)
        return (end - start).total_seconds()
    
    @property
    def is_complete(self) -> bool:
        """Check if agent completed (success or isolated failure)."""
        return self.state in (AgentState.WRAP_RECEIVED, AgentState.ISOLATED)
    
    @property
    def is_success(self) -> bool:
        """Check if agent completed successfully."""
        return self.state == AgentState.WRAP_RECEIVED


@dataclass
class Checkpoint:
    """Orchestration checkpoint for resumability."""
    
    checkpoint_id: str
    session_id: str
    pac_id: str
    created_at: str
    agent_states: Dict[str, AgentState]
    completed_wraps: Dict[str, str]  # agent_id -> wrap_hash
    pending_agents: List[str]
    execution_order: List[str]
    checkpoint_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize checkpoint."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "pac_id": self.pac_id,
            "created_at": self.created_at,
            "agent_states": {k: v.value for k, v in self.agent_states.items()},
            "completed_wraps": self.completed_wraps,
            "pending_agents": self.pending_agents,
            "execution_order": self.execution_order,
            "checkpoint_hash": self.checkpoint_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Deserialize checkpoint."""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            session_id=data["session_id"],
            pac_id=data["pac_id"],
            created_at=data["created_at"],
            agent_states={k: AgentState(v) for k, v in data["agent_states"].items()},
            completed_wraps=data["completed_wraps"],
            pending_agents=data["pending_agents"],
            execution_order=data["execution_order"],
            checkpoint_hash=data["checkpoint_hash"],
        )


@dataclass
class ExecutionResult:
    """Result of orchestration execution."""
    
    session_id: str
    pac_id: str
    success: bool
    agent_results: Dict[str, AgentExecution]
    total_tests: int
    wrap_hashes: List[str]
    started_at: str
    completed_at: str
    checkpoints_created: int
    faults_isolated: int
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate total execution duration."""
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.completed_at)
        return (end - start).total_seconds()
    
    @property
    def successful_agents(self) -> int:
        """Count successful agents."""
        return sum(1 for a in self.agent_results.values() if a.is_success)
    
    @property
    def failed_agents(self) -> int:
        """Count failed agents."""
        return sum(1 for a in self.agent_results.values() if a.state == AgentState.FAILED)


# =============================================================================
# DEPENDENCY GRAPH
# =============================================================================

class DependencyGraph:
    """
    Manages agent dependencies with cycle detection and topological ordering.
    """
    
    def __init__(self) -> None:
        self._edges: Dict[str, Set[str]] = defaultdict(set)  # source -> targets
        self._reverse: Dict[str, Set[str]] = defaultdict(set)  # target -> sources
        self._types: Dict[Tuple[str, str], DependencyType] = {}
    
    def add_dependency(self, dependency: AgentDependency) -> None:
        """Add a dependency to the graph."""
        source = dependency.source_agent
        target = dependency.target_agent
        
        self._edges[source].add(target)
        self._reverse[target].add(source)
        self._types[(source, target)] = dependency.dependency_type
    
    def get_dependencies(self, agent_id: str) -> Set[str]:
        """Get agents that must complete before this agent."""
        return self._reverse.get(agent_id, set())
    
    def get_dependents(self, agent_id: str) -> Set[str]:
        """Get agents that depend on this agent."""
        return self._edges.get(agent_id, set())
    
    def detect_cycles(self) -> Optional[List[str]]:
        """
        Detect cycles in dependency graph using DFS.
        
        Returns:
            List of agents forming cycle, or None if no cycle.
        """
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._edges.get(node, set()):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Cycle found
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        all_nodes = set(self._edges.keys()) | set(self._reverse.keys())
        for node in all_nodes:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle
        
        return None
    
    def topological_sort(self) -> List[str]:
        """
        Return agents in topological order (dependencies first).
        
        Raises:
            DependencyCycleError: If cycle detected.
        """
        cycle = self.detect_cycles()
        if cycle:
            raise DependencyCycleError(cycle)
        
        in_degree = defaultdict(int)
        all_nodes = set(self._edges.keys()) | set(self._reverse.keys())
        
        for node in all_nodes:
            in_degree[node] = len(self._reverse.get(node, set()))
        
        # Start with nodes that have no dependencies
        queue = [n for n in all_nodes if in_degree[n] == 0]
        result = []
        
        while queue:
            # Sort by in_degree to ensure deterministic ordering
            queue.sort()
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self._edges.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def get_parallel_batches(self) -> List[List[str]]:
        """
        Group agents into parallel execution batches respecting dependencies.
        
        Returns:
            List of batches, where agents in each batch can run in parallel.
        """
        cycle = self.detect_cycles()
        if cycle:
            raise DependencyCycleError(cycle)
        
        batches = []
        remaining = set(self._edges.keys()) | set(self._reverse.keys())
        completed = set()
        
        while remaining:
            # Find agents whose dependencies are all satisfied
            batch = []
            for agent in remaining:
                deps = self._reverse.get(agent, set())
                if deps <= completed:  # All deps completed
                    batch.append(agent)
            
            if not batch:
                # Should not happen if no cycles
                raise OrchestratorError("Dependency resolution deadlock")
            
            batch.sort()  # Deterministic ordering
            batches.append(batch)
            completed.update(batch)
            remaining -= set(batch)
        
        return batches


# =============================================================================
# FAULT ISOLATION ENGINE
# =============================================================================

class FaultIsolationEngine:
    """
    Manages fault isolation to prevent cascade failures.
    """
    
    def __init__(self, dependency_graph: DependencyGraph) -> None:
        self._graph = dependency_graph
        self._isolated: Set[str] = set()
        self._cascade_map: Dict[str, List[str]] = {}
    
    def isolate_fault(self, failed_agent: str) -> List[str]:
        """
        Isolate a failed agent and identify cascade impacts.
        
        Returns:
            List of agents that must be isolated due to cascade.
        """
        self._isolated.add(failed_agent)
        
        # Find all dependents that cannot proceed
        cascade = []
        to_check = list(self._graph.get_dependents(failed_agent))
        checked = {failed_agent}
        
        while to_check:
            agent = to_check.pop(0)
            if agent in checked:
                continue
            checked.add(agent)
            
            # Check if all dependencies can be satisfied
            deps = self._graph.get_dependencies(agent)
            unsatisfied = deps & self._isolated
            
            if unsatisfied:
                # This agent cannot proceed
                cascade.append(agent)
                self._isolated.add(agent)
                # Add its dependents for checking
                to_check.extend(self._graph.get_dependents(agent))
        
        self._cascade_map[failed_agent] = cascade
        return cascade
    
    def is_isolated(self, agent_id: str) -> bool:
        """Check if agent is isolated."""
        return agent_id in self._isolated
    
    def get_viable_agents(self, all_agents: Set[str]) -> Set[str]:
        """Get agents that can still execute."""
        return all_agents - self._isolated
    
    def get_isolation_report(self) -> Dict[str, Any]:
        """Generate isolation report."""
        return {
            "isolated_count": len(self._isolated),
            "isolated_agents": list(self._isolated),
            "cascade_map": self._cascade_map,
        }


# =============================================================================
# CHECKPOINT MANAGER
# =============================================================================

class CheckpointManager:
    """
    Manages checkpointing for resumability.
    """
    
    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._storage_path = storage_path
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._lock = threading.Lock()
    
    def create_checkpoint(
        self,
        session_id: str,
        pac_id: str,
        agent_states: Dict[str, AgentState],
        completed_wraps: Dict[str, str],
        pending_agents: List[str],
        execution_order: List[str],
    ) -> Checkpoint:
        """Create a new checkpoint."""
        checkpoint_id = f"CP-{uuid.uuid4().hex[:12].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        
        # Compute checkpoint hash
        content = {
            "session_id": session_id,
            "pac_id": pac_id,
            "agent_states": {k: v.value for k, v in agent_states.items()},
            "completed_wraps": completed_wraps,
            "pending_agents": pending_agents,
            "created_at": created_at,
        }
        canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
        checkpoint_hash = hashlib.sha256(canonical.encode()).hexdigest()
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            pac_id=pac_id,
            created_at=created_at,
            agent_states=agent_states,
            completed_wraps=completed_wraps,
            pending_agents=pending_agents,
            execution_order=execution_order,
            checkpoint_hash=checkpoint_hash,
        )
        
        with self._lock:
            self._checkpoints[checkpoint_id] = checkpoint
        
        return checkpoint
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Retrieve a checkpoint."""
        return self._checkpoints.get(checkpoint_id)
    
    def get_latest_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """Get most recent checkpoint for session."""
        session_checkpoints = [
            cp for cp in self._checkpoints.values()
            if cp.session_id == session_id
        ]
        if not session_checkpoints:
            return None
        return max(session_checkpoints, key=lambda cp: cp.created_at)
    
    def verify_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """Verify checkpoint integrity."""
        content = {
            "session_id": checkpoint.session_id,
            "pac_id": checkpoint.pac_id,
            "agent_states": {k: v.value for k, v in checkpoint.agent_states.items()},
            "completed_wraps": checkpoint.completed_wraps,
            "pending_agents": checkpoint.pending_agents,
            "created_at": checkpoint.created_at,
        }
        canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
        computed_hash = hashlib.sha256(canonical.encode()).hexdigest()
        return computed_hash == checkpoint.checkpoint_hash
    
    def list_checkpoints(self, session_id: Optional[str] = None) -> List[Checkpoint]:
        """List checkpoints, optionally filtered by session."""
        if session_id:
            return [cp for cp in self._checkpoints.values() if cp.session_id == session_id]
        return list(self._checkpoints.values())


# =============================================================================
# GIE ORCHESTRATOR v3
# =============================================================================

class GIEOrchestratorV3:
    """
    Production-grade multi-agent orchestration engine.
    
    Features:
    - Dependency resolution with cycle detection
    - Parallel execution with synchronization barriers
    - Checkpointed resumability
    - Fault isolation and recovery
    - Hash-verified state management
    """
    
    def __init__(
        self,
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        fault_strategy: FaultStrategy = FaultStrategy.FAIL_ISOLATED,
        max_workers: int = 8,
        checkpoint_interval: int = CHECKPOINT_INTERVAL_SECONDS,
    ) -> None:
        self._mode = execution_mode
        self._fault_strategy = fault_strategy
        self._max_workers = max_workers
        self._checkpoint_interval = checkpoint_interval
        
        self._dependency_graph = DependencyGraph()
        self._checkpoint_manager = CheckpointManager()
        self._fault_engine: Optional[FaultIsolationEngine] = None
        
        self._agents: Dict[str, AgentSpec] = {}
        self._executions: Dict[str, AgentExecution] = {}
        self._session_id: Optional[str] = None
        self._pac_id: Optional[str] = None
        
        self._lock = threading.Lock()
        self._checkpoints_created = 0
    
    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------
    
    def register_agent(self, spec: AgentSpec) -> None:
        """Register an agent for orchestration."""
        self._agents[spec.agent_id] = spec
        self._executions[spec.agent_id] = AgentExecution(spec=spec)
    
    def add_dependency(self, dependency: AgentDependency) -> None:
        """Add a dependency between agents."""
        self._dependency_graph.add_dependency(dependency)
    
    def configure_session(self, session_id: str, pac_id: str) -> None:
        """Configure session for execution."""
        self._session_id = session_id
        self._pac_id = pac_id
        self._fault_engine = FaultIsolationEngine(self._dependency_graph)
    
    # -------------------------------------------------------------------------
    # DEPENDENCY RESOLUTION
    # -------------------------------------------------------------------------
    
    def resolve_dependencies(self) -> List[List[str]]:
        """
        Resolve execution order based on dependencies.
        
        Returns:
            List of parallel batches for execution.
        """
        return self._dependency_graph.get_parallel_batches()
    
    def validate_dependencies(self) -> List[str]:
        """
        Validate all dependencies can be satisfied.
        
        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        
        # Check for cycles
        cycle = self._dependency_graph.detect_cycles()
        if cycle:
            errors.append(f"Circular dependency: {' -> '.join(cycle)}")
        
        # Check all referenced agents exist
        all_referenced = set()
        for agent_id in self._agents:
            deps = self._dependency_graph.get_dependencies(agent_id)
            all_referenced.update(deps)
            dependents = self._dependency_graph.get_dependents(agent_id)
            all_referenced.update(dependents)
        
        missing = all_referenced - set(self._agents.keys())
        for m in missing:
            errors.append(f"Unknown agent referenced in dependency: {m}")
        
        return errors
    
    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------
    
    def execute(
        self,
        agent_executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> ExecutionResult:
        """
        Execute all registered agents.
        
        Args:
            agent_executor: Function that executes an agent and returns
                           (wrap_hash, test_count, outputs)
        
        Returns:
            ExecutionResult with full execution summary.
        """
        if not self._session_id or not self._pac_id:
            raise OrchestratorError("Session not configured")
        
        # Validate dependencies
        errors = self.validate_dependencies()
        if errors:
            raise OrchestratorError(f"Dependency validation failed: {errors}")
        
        started_at = datetime.now(timezone.utc).isoformat()
        execution_errors = []
        
        try:
            if self._mode == ExecutionMode.SEQUENTIAL:
                self._execute_sequential(agent_executor)
            elif self._mode == ExecutionMode.PARALLEL:
                self._execute_parallel(agent_executor)
            else:  # HYBRID
                self._execute_hybrid(agent_executor)
        except Exception as e:
            execution_errors.append(str(e))
        
        completed_at = datetime.now(timezone.utc).isoformat()
        
        # Collect results
        wrap_hashes = [
            ex.wrap_hash for ex in self._executions.values()
            if ex.wrap_hash
        ]
        total_tests = sum(ex.test_count for ex in self._executions.values())
        
        success = all(
            ex.is_success or ex.state == AgentState.ISOLATED
            for ex in self._executions.values()
        ) and len(execution_errors) == 0
        
        faults_isolated = sum(
            1 for ex in self._executions.values()
            if ex.state == AgentState.ISOLATED
        )
        
        return ExecutionResult(
            session_id=self._session_id,
            pac_id=self._pac_id,
            success=success,
            agent_results=dict(self._executions),
            total_tests=total_tests,
            wrap_hashes=wrap_hashes,
            started_at=started_at,
            completed_at=completed_at,
            checkpoints_created=self._checkpoints_created,
            faults_isolated=faults_isolated,
            errors=execution_errors,
        )
    
    def _execute_sequential(
        self,
        executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> None:
        """Execute agents sequentially in dependency order."""
        order = self._dependency_graph.topological_sort()
        
        # Add agents with no dependencies
        all_agents = set(self._agents.keys())
        ordered = set(order)
        standalone = all_agents - ordered
        order = list(standalone) + order
        
        for agent_id in order:
            if self._fault_engine and self._fault_engine.is_isolated(agent_id):
                continue
            self._execute_agent(agent_id, executor)
    
    def _execute_parallel(
        self,
        executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> None:
        """Execute agents in parallel batches."""
        batches = self.resolve_dependencies()
        
        # Add standalone agents to first batch
        all_agents = set(self._agents.keys())
        batched = set()
        for batch in batches:
            batched.update(batch)
        standalone = list(all_agents - batched)
        
        if standalone:
            if batches:
                batches[0] = standalone + batches[0]
            else:
                batches = [standalone]
        
        for batch_idx, batch in enumerate(batches):
            # Filter out isolated agents
            viable = [
                a for a in batch
                if not (self._fault_engine and self._fault_engine.is_isolated(a))
            ]
            
            if not viable:
                continue
            
            # Execute batch in parallel
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                futures = {
                    pool.submit(self._execute_agent, agent_id, executor): agent_id
                    for agent_id in viable
                }
                
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self._handle_agent_failure(agent_id, str(e))
            
            # Create checkpoint after each batch
            self._create_checkpoint()
    
    def _execute_hybrid(
        self,
        executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> None:
        """Execute with hybrid strategy (parallel with barriers)."""
        # Same as parallel for now
        self._execute_parallel(executor)
    
    def _execute_agent(
        self,
        agent_id: str,
        executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> None:
        """Execute a single agent."""
        execution = self._executions[agent_id]
        spec = execution.spec
        
        with self._lock:
            execution.state = AgentState.EXECUTING
            execution.started_at = datetime.now(timezone.utc).isoformat()
        
        try:
            wrap_hash, test_count, outputs = executor(spec)
            
            with self._lock:
                execution.wrap_hash = wrap_hash
                execution.test_count = test_count
                execution.outputs = outputs
                execution.state = AgentState.WRAP_RECEIVED
                execution.completed_at = datetime.now(timezone.utc).isoformat()
                
        except Exception as e:
            with self._lock:
                execution.error = str(e)
                execution.state = AgentState.FAILED
                execution.completed_at = datetime.now(timezone.utc).isoformat()
            
            if self._fault_strategy == FaultStrategy.FAIL_FAST:
                raise AgentExecutionError(agent_id, str(e))
            elif self._fault_strategy == FaultStrategy.FAIL_ISOLATED:
                self._handle_agent_failure(agent_id, str(e))
            elif self._fault_strategy == FaultStrategy.RETRY:
                self._retry_agent(agent_id, executor)
    
    def _handle_agent_failure(self, agent_id: str, reason: str) -> None:
        """Handle agent failure with isolation."""
        if self._fault_engine:
            cascade = self._fault_engine.isolate_fault(agent_id)
            
            # Mark cascaded agents as isolated
            for cascaded in cascade:
                if cascaded in self._executions:
                    self._executions[cascaded].state = AgentState.ISOLATED
                    self._executions[cascaded].error = f"Isolated due to {agent_id} failure"
    
    def _retry_agent(
        self,
        agent_id: str,
        executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> None:
        """Retry failed agent execution."""
        execution = self._executions[agent_id]
        
        while execution.retry_count < MAX_RETRY_ATTEMPTS:
            execution.retry_count += 1
            execution.state = AgentState.PENDING
            execution.error = None
            
            try:
                self._execute_agent(agent_id, executor)
                return  # Success
            except Exception:
                pass
        
        # Max retries exceeded
        self._handle_agent_failure(agent_id, f"Max retries ({MAX_RETRY_ATTEMPTS}) exceeded")
    
    # -------------------------------------------------------------------------
    # CHECKPOINTING
    # -------------------------------------------------------------------------
    
    def _create_checkpoint(self) -> Checkpoint:
        """Create a checkpoint of current state."""
        agent_states = {
            agent_id: ex.state
            for agent_id, ex in self._executions.items()
        }
        
        completed_wraps = {
            agent_id: ex.wrap_hash
            for agent_id, ex in self._executions.items()
            if ex.wrap_hash
        }
        
        pending_agents = [
            agent_id for agent_id, ex in self._executions.items()
            if ex.state in (AgentState.PENDING, AgentState.READY)
        ]
        
        execution_order = self._dependency_graph.topological_sort()
        
        checkpoint = self._checkpoint_manager.create_checkpoint(
            session_id=self._session_id,
            pac_id=self._pac_id,
            agent_states=agent_states,
            completed_wraps=completed_wraps,
            pending_agents=pending_agents,
            execution_order=execution_order,
        )
        
        self._checkpoints_created += 1
        return checkpoint
    
    # -------------------------------------------------------------------------
    # RESUMABILITY
    # -------------------------------------------------------------------------
    
    def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        agent_executor: Callable[[AgentSpec], Tuple[str, int, Dict[str, Any]]],
    ) -> ExecutionResult:
        """
        Resume execution from a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to resume from
            agent_executor: Agent execution function
            
        Returns:
            ExecutionResult from resumed execution
        """
        checkpoint = self._checkpoint_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ResumabilityError(checkpoint_id, "Checkpoint not found")
        
        if not self._checkpoint_manager.verify_checkpoint(checkpoint):
            raise ResumabilityError(checkpoint_id, "Checkpoint integrity check failed")
        
        # Restore state
        self._session_id = checkpoint.session_id
        self._pac_id = checkpoint.pac_id
        
        for agent_id, state in checkpoint.agent_states.items():
            if agent_id in self._executions:
                self._executions[agent_id].state = state
        
        for agent_id, wrap_hash in checkpoint.completed_wraps.items():
            if agent_id in self._executions:
                self._executions[agent_id].wrap_hash = wrap_hash
        
        # Continue execution for pending agents only
        return self.execute(agent_executor)
    
    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------
    
    def get_execution_state(self, agent_id: str) -> Optional[AgentExecution]:
        """Get execution state for an agent."""
        return self._executions.get(agent_id)
    
    def get_all_states(self) -> Dict[str, AgentExecution]:
        """Get all agent execution states."""
        return dict(self._executions)
    
    def get_pending_agents(self) -> List[str]:
        """Get agents pending execution."""
        return [
            agent_id for agent_id, ex in self._executions.items()
            if ex.state == AgentState.PENDING
        ]
    
    def get_completed_agents(self) -> List[str]:
        """Get completed agents."""
        return [
            agent_id for agent_id, ex in self._executions.items()
            if ex.is_complete
        ]
    
    def get_isolation_report(self) -> Optional[Dict[str, Any]]:
        """Get fault isolation report."""
        if self._fault_engine:
            return self._fault_engine.get_isolation_report()
        return None


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_orchestrator(
    mode: ExecutionMode = ExecutionMode.PARALLEL,
    fault_strategy: FaultStrategy = FaultStrategy.FAIL_ISOLATED,
    max_workers: int = 8,
) -> GIEOrchestratorV3:
    """Create a configured orchestrator instance."""
    return GIEOrchestratorV3(
        execution_mode=mode,
        fault_strategy=fault_strategy,
        max_workers=max_workers,
    )


def create_agent_spec(
    agent_id: str,
    role: str,
    lane: str,
    deliverables: List[str],
    test_requirement: int = 0,
) -> AgentSpec:
    """Create an agent specification."""
    return AgentSpec(
        agent_id=agent_id,
        role=role,
        lane=lane,
        deliverables=deliverables,
        test_requirement=test_requirement,
    )


def create_dependency(
    source: str,
    target: str,
    dep_type: DependencyType = DependencyType.HARD,
) -> AgentDependency:
    """Create a dependency between agents."""
    return AgentDependency(
        source_agent=source,
        target_agent=target,
        dependency_type=dep_type,
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version
    "ORCHESTRATOR_VERSION",
    # Enums
    "AgentState",
    "ExecutionMode",
    "FaultStrategy",
    "CheckpointState",
    "DependencyType",
    # Exceptions
    "OrchestratorError",
    "DependencyCycleError",
    "DependencyNotSatisfiedError",
    "AgentExecutionError",
    "CheckpointError",
    "FaultIsolationError",
    "ResumabilityError",
    # Data Classes
    "AgentDependency",
    "AgentSpec",
    "AgentExecution",
    "Checkpoint",
    "ExecutionResult",
    # Core Classes
    "DependencyGraph",
    "FaultIsolationEngine",
    "CheckpointManager",
    "GIEOrchestratorV3",
    # Factory Functions
    "create_orchestrator",
    "create_agent_spec",
    "create_dependency",
]
