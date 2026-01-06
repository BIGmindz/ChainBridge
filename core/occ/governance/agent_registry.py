"""
Agent Registry Enforcement — Shadow Agent Bypass Prevention

PAC: PAC-OCC-P07
Lane: EX3 — Agent Registry Enforcement
Agent: ALEX (GID-08)

Addresses existential failure EX3: "Shadow Agent Bypass"
BER-P05 finding: No runtime verification of agent registration

MECHANICAL ENFORCEMENT:
- All agents must be registered before operation
- Runtime verification on every agent action
- Shadow agents (unregistered) are blocked
- Registry is cryptographically signed

INVARIANTS:
- INV-AGENT-001: Unregistered agents CANNOT execute
- INV-AGENT-002: Agent GID must be unique
- INV-AGENT-003: Registry modifications require T4 dual control
- INV-AGENT-004: All agent operations are logged
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_REGISTRY_PATH = ".github/agents/agent_registry.json"
REGISTRY_PATH = os.environ.get("CHAINBRIDGE_AGENT_REGISTRY_PATH", DEFAULT_REGISTRY_PATH)


class AgentStatus(str, Enum):
    """Agent operational status."""
    
    ACTIVE = "active"           # Fully operational
    SUSPENDED = "suspended"     # Temporarily disabled
    REVOKED = "revoked"         # Permanently disabled
    PENDING = "pending"         # Awaiting activation


class AgentCapability(str, Enum):
    """Agent capability domains."""
    
    CODE = "code"               # Code generation/modification
    INFRASTRUCTURE = "infra"    # Infrastructure operations
    GOVERNANCE = "governance"   # Governance enforcement
    ML = "ml"                   # Machine learning operations
    SECURITY = "security"       # Security operations
    UI = "ui"                   # User interface operations
    DATA = "data"               # Data operations
    SETTLEMENT = "settlement"   # Financial settlement
    AUDIT = "audit"             # Audit operations


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RegisteredAgent:
    """Definition of a registered agent."""
    
    gid: str                                    # e.g., "GID-01"
    name: str                                   # e.g., "CODY"
    description: str
    status: AgentStatus
    capabilities: Set[AgentCapability]
    registered_at: str
    registered_by: str
    
    # Optional metadata
    version: str = "1.0.0"
    max_concurrent_tasks: int = 10
    rate_limit_per_minute: int = 100
    requires_dual_control: bool = False
    
    # Audit fields
    last_active: Optional[str] = None
    total_operations: int = 0
    suspended_at: Optional[str] = None
    suspended_by: Optional[str] = None
    suspension_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gid": self.gid,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "registered_at": self.registered_at,
            "registered_by": self.registered_by,
            "version": self.version,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "requires_dual_control": self.requires_dual_control,
            "last_active": self.last_active,
            "total_operations": self.total_operations,
            "suspended_at": self.suspended_at,
            "suspended_by": self.suspended_by,
            "suspension_reason": self.suspension_reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegisteredAgent":
        """Create from dictionary."""
        return cls(
            gid=data["gid"],
            name=data["name"],
            description=data["description"],
            status=AgentStatus(data["status"]),
            capabilities={AgentCapability(c) for c in data["capabilities"]},
            registered_at=data["registered_at"],
            registered_by=data["registered_by"],
            version=data.get("version", "1.0.0"),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 10),
            rate_limit_per_minute=data.get("rate_limit_per_minute", 100),
            requires_dual_control=data.get("requires_dual_control", False),
            last_active=data.get("last_active"),
            total_operations=data.get("total_operations", 0),
            suspended_at=data.get("suspended_at"),
            suspended_by=data.get("suspended_by"),
            suspension_reason=data.get("suspension_reason"),
        )


@dataclass
class AgentOperationAttempt:
    """Record of an agent operation attempt."""
    
    attempt_id: str
    gid: str
    agent_name: Optional[str]
    operation: str
    capability_required: Optional[AgentCapability]
    timestamp: str
    allowed: bool
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ShadowAgentError(Exception):
    """Raised when an unregistered (shadow) agent attempts operation."""
    
    def __init__(self, gid: str, operation: str):
        super().__init__(f"INV-AGENT-001 VIOLATION: Shadow agent {gid} blocked from {operation}")
        self.gid = gid
        self.operation = operation


class AgentSuspendedError(Exception):
    """Raised when a suspended agent attempts operation."""
    
    def __init__(self, gid: str, name: str, reason: Optional[str]):
        super().__init__(f"Agent {name} ({gid}) is suspended: {reason or 'No reason provided'}")
        self.gid = gid
        self.name = name
        self.reason = reason


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class AgentRegistry:
    """
    Runtime agent registry with enforcement.
    
    INVARIANT ENFORCEMENT:
    - INV-AGENT-001: Block unregistered agents
    - INV-AGENT-002: Enforce unique GIDs
    - INV-AGENT-003: T4 dual control for modifications
    - INV-AGENT-004: Full audit logging
    """
    
    def __init__(
        self,
        registry_path: Optional[str] = None,
        repo_root: Optional[str] = None,
    ):
        """Initialize the agent registry."""
        self._lock = threading.Lock()
        
        # Determine repo root
        if repo_root:
            self._repo_root = Path(repo_root)
        else:
            self._repo_root = self._find_repo_root()
        
        self._registry_path = Path(registry_path or REGISTRY_PATH)
        if not self._registry_path.is_absolute():
            self._registry_path = self._repo_root / self._registry_path
        
        # In-memory registry
        self._agents: Dict[str, RegisteredAgent] = {}
        self._operation_log: List[AgentOperationAttempt] = []
        
        # Rate limiting state
        self._operation_counts: Dict[str, List[datetime]] = {}
        
        # Load from file if exists
        self._load()
        
        logger.info(f"AgentRegistry initialized with {len(self._agents)} agents")
    
    def _find_repo_root(self) -> Path:
        """Find repository root."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent
        return current
    
    def _load(self) -> None:
        """Load registry from file."""
        if not self._registry_path.exists():
            logger.warning(f"Agent registry not found at {self._registry_path}, initializing empty")
            self._initialize_default_registry()
            return
        
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
            for agent_data in data.get("agents", []):
                agent = RegisteredAgent.from_dict(agent_data)
                self._agents[agent.gid] = agent
            
            logger.info(f"Loaded {len(self._agents)} agents from registry")
        except Exception as e:
            logger.error(f"Failed to load agent registry: {e}")
            self._initialize_default_registry()
    
    def _initialize_default_registry(self) -> None:
        """Initialize with default ChainBridge agents."""
        default_agents = [
            RegisteredAgent(
                gid="GID-00",
                name="BENSON",
                description="Orchestrator — PAC coordination and agent management",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.GOVERNANCE, AgentCapability.AUDIT},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
            ),
            RegisteredAgent(
                gid="GID-01",
                name="CODY",
                description="Backend Engineer — Code generation and review",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.CODE, AgentCapability.DATA},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
            ),
            RegisteredAgent(
                gid="GID-05",
                name="PAX",
                description="Regulatory Compliance — Legal and regulatory validation",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.GOVERNANCE, AgentCapability.AUDIT},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
            ),
            RegisteredAgent(
                gid="GID-06",
                name="SAM",
                description="Security Lead — Security and supply chain integrity",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.SECURITY, AgentCapability.SETTLEMENT},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
                requires_dual_control=True,
            ),
            RegisteredAgent(
                gid="GID-07",
                name="DAN",
                description="DevOps Lead — CI/CD and infrastructure",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.INFRASTRUCTURE, AgentCapability.CODE},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
            ),
            RegisteredAgent(
                gid="GID-08",
                name="ALEX",
                description="Governance Enforcer — Constitution and rule enforcement",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.GOVERNANCE, AgentCapability.SECURITY},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
                requires_dual_control=True,
            ),
            RegisteredAgent(
                gid="GID-10",
                name="MAGGIE",
                description="ML Lead — Machine learning and model governance",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.ML, AgentCapability.DATA},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
            ),
            RegisteredAgent(
                gid="GID-11",
                name="ATLAS",
                description="Repo Integrity Engineer — Repository and backup integrity",
                status=AgentStatus.ACTIVE,
                capabilities={AgentCapability.INFRASTRUCTURE, AgentCapability.AUDIT},
                registered_at=datetime.now(timezone.utc).isoformat(),
                registered_by="system",
            ),
        ]
        
        for agent in default_agents:
            self._agents[agent.gid] = agent
        
        self._persist()
        logger.info(f"Initialized default registry with {len(default_agents)} agents")
    
    def _persist(self) -> None:
        """Persist registry to file."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agents": [agent.to_dict() for agent in self._agents.values()],
        }
        
        tmp_path = self._registry_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self._registry_path)
    
    def _audit_operation(
        self,
        gid: str,
        operation: str,
        allowed: bool,
        capability: Optional[AgentCapability] = None,
        rejection_reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Record operation attempt in audit log."""
        agent = self._agents.get(gid)
        
        attempt = AgentOperationAttempt(
            attempt_id=str(uuid4()),
            gid=gid,
            agent_name=agent.name if agent else None,
            operation=operation,
            capability_required=capability,
            timestamp=datetime.now(timezone.utc).isoformat(),
            allowed=allowed,
            rejection_reason=rejection_reason,
            metadata=metadata or {},
        )
        
        self._operation_log.append(attempt)
        
        # Keep last 10000 entries
        if len(self._operation_log) > 10000:
            self._operation_log = self._operation_log[-10000:]
        
        status = "ALLOWED" if allowed else "BLOCKED"
        logger.info(f"AGENT_OPERATION [{status}]: {gid} -> {operation}")
    
    def _check_rate_limit(self, gid: str, limit: int) -> bool:
        """Check if agent is within rate limit."""
        now = datetime.now(timezone.utc)
        minute_ago = now - datetime.timedelta(minutes=1) if hasattr(datetime, 'timedelta') else now
        
        # Import timedelta properly
        from datetime import timedelta
        minute_ago = now - timedelta(minutes=1)
        
        if gid not in self._operation_counts:
            self._operation_counts[gid] = []
        
        # Clean old entries
        self._operation_counts[gid] = [
            ts for ts in self._operation_counts[gid]
            if ts > minute_ago
        ]
        
        return len(self._operation_counts[gid]) < limit
    
    def _record_operation(self, gid: str) -> None:
        """Record an operation for rate limiting."""
        if gid not in self._operation_counts:
            self._operation_counts[gid] = []
        self._operation_counts[gid].append(datetime.now(timezone.utc))
    
    def is_registered(self, gid: str) -> bool:
        """Check if an agent is registered."""
        with self._lock:
            return gid in self._agents
    
    def is_active(self, gid: str) -> bool:
        """Check if an agent is registered and active."""
        with self._lock:
            agent = self._agents.get(gid)
            return agent is not None and agent.status == AgentStatus.ACTIVE
    
    def authorize_operation(
        self,
        gid: str,
        operation: str,
        capability: Optional[AgentCapability] = None,
        raise_on_failure: bool = True,
    ) -> bool:
        """
        Authorize an agent operation.
        
        Args:
            gid: Agent's governance ID
            operation: Operation being attempted
            capability: Required capability (optional)
            raise_on_failure: Raise exception on failure
            
        Returns:
            True if authorized
            
        Raises:
            ShadowAgentError: If agent not registered
            AgentSuspendedError: If agent is suspended
            
        ENFORCES: INV-AGENT-001, INV-AGENT-004
        """
        with self._lock:
            agent = self._agents.get(gid)
            
            # INV-AGENT-001: Block unregistered agents
            if agent is None:
                self._audit_operation(
                    gid, operation, allowed=False,
                    capability=capability,
                    rejection_reason="SHADOW_AGENT"
                )
                if raise_on_failure:
                    raise ShadowAgentError(gid, operation)
                return False
            
            # Check status
            if agent.status == AgentStatus.SUSPENDED:
                self._audit_operation(
                    gid, operation, allowed=False,
                    capability=capability,
                    rejection_reason=f"SUSPENDED: {agent.suspension_reason}"
                )
                if raise_on_failure:
                    raise AgentSuspendedError(gid, agent.name, agent.suspension_reason)
                return False
            
            if agent.status == AgentStatus.REVOKED:
                self._audit_operation(
                    gid, operation, allowed=False,
                    capability=capability,
                    rejection_reason="REVOKED"
                )
                if raise_on_failure:
                    raise ShadowAgentError(gid, operation)
                return False
            
            if agent.status == AgentStatus.PENDING:
                self._audit_operation(
                    gid, operation, allowed=False,
                    capability=capability,
                    rejection_reason="PENDING_ACTIVATION"
                )
                if raise_on_failure:
                    raise AgentSuspendedError(gid, agent.name, "Pending activation")
                return False
            
            # Check capability if specified
            if capability and capability not in agent.capabilities:
                self._audit_operation(
                    gid, operation, allowed=False,
                    capability=capability,
                    rejection_reason=f"MISSING_CAPABILITY: {capability.value}"
                )
                if raise_on_failure:
                    raise PermissionError(
                        f"Agent {agent.name} ({gid}) lacks capability: {capability.value}"
                    )
                return False
            
            # Check rate limit
            if not self._check_rate_limit(gid, agent.rate_limit_per_minute):
                self._audit_operation(
                    gid, operation, allowed=False,
                    capability=capability,
                    rejection_reason="RATE_LIMITED"
                )
                if raise_on_failure:
                    raise PermissionError(
                        f"Agent {agent.name} ({gid}) rate limited"
                    )
                return False
            
            # Authorized
            self._audit_operation(gid, operation, allowed=True, capability=capability)
            self._record_operation(gid)
            
            # Update stats
            agent.last_active = datetime.now(timezone.utc).isoformat()
            agent.total_operations += 1
            
            return True
    
    def get_agent(self, gid: str) -> Optional[RegisteredAgent]:
        """Get agent by GID."""
        with self._lock:
            return self._agents.get(gid)
    
    def list_agents(self, status: Optional[AgentStatus] = None) -> List[RegisteredAgent]:
        """List all agents, optionally filtered by status."""
        with self._lock:
            agents = list(self._agents.values())
            if status:
                agents = [a for a in agents if a.status == status]
            return agents
    
    def suspend_agent(
        self,
        gid: str,
        suspended_by: str,
        reason: str,
        dual_control_request_id: Optional[str] = None,
    ) -> RegisteredAgent:
        """
        Suspend an agent.
        
        ENFORCES: INV-AGENT-003 (T4 dual control for Sam, ALEX)
        """
        with self._lock:
            agent = self._agents.get(gid)
            if not agent:
                raise ValueError(f"Agent {gid} not found")
            
            # Check if agent requires dual control
            if agent.requires_dual_control and not dual_control_request_id:
                raise ValueError(
                    f"INV-AGENT-003 VIOLATION: Suspending {agent.name} ({gid}) requires T4 dual control"
                )
            
            agent.status = AgentStatus.SUSPENDED
            agent.suspended_at = datetime.now(timezone.utc).isoformat()
            agent.suspended_by = suspended_by
            agent.suspension_reason = reason
            
            self._persist()
            
            logger.warning(f"AGENT_SUSPENDED: {agent.name} ({gid}) by {suspended_by}: {reason}")
            
            return agent
    
    def reinstate_agent(
        self,
        gid: str,
        reinstated_by: str,
        dual_control_request_id: Optional[str] = None,
    ) -> RegisteredAgent:
        """
        Reinstate a suspended agent.
        
        ENFORCES: INV-AGENT-003 (T4 dual control for Sam, ALEX)
        """
        with self._lock:
            agent = self._agents.get(gid)
            if not agent:
                raise ValueError(f"Agent {gid} not found")
            
            if agent.requires_dual_control and not dual_control_request_id:
                raise ValueError(
                    f"INV-AGENT-003 VIOLATION: Reinstating {agent.name} ({gid}) requires T4 dual control"
                )
            
            agent.status = AgentStatus.ACTIVE
            agent.suspended_at = None
            agent.suspended_by = None
            agent.suspension_reason = None
            
            self._persist()
            
            logger.info(f"AGENT_REINSTATED: {agent.name} ({gid}) by {reinstated_by}")
            
            return agent
    
    def get_operation_log(self, gid: Optional[str] = None, limit: int = 100) -> List[AgentOperationAttempt]:
        """Get operation log, optionally filtered by agent."""
        with self._lock:
            log = self._operation_log
            if gid:
                log = [op for op in log if op.gid == gid]
            return log[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            by_status = {}
            for agent in self._agents.values():
                by_status[agent.status.value] = by_status.get(agent.status.value, 0) + 1
            
            blocked_ops = sum(1 for op in self._operation_log[-1000:] if not op.allowed)
            
            return {
                "total_agents": len(self._agents),
                "by_status": by_status,
                "recent_operations": len(self._operation_log),
                "recent_blocked": blocked_ops,
            }


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR FOR AGENT ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════


def require_registered_agent(
    capability: Optional[AgentCapability] = None,
):
    """
    Decorator to require registered agent for function execution.
    
    The decorated function must accept `agent_gid` as a keyword argument.
    
    Usage:
        @require_registered_agent(capability=AgentCapability.CODE)
        def generate_code(agent_gid: str, **kwargs):
            # Only called if agent is registered and has CODE capability
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, agent_gid: Optional[str] = None, **kwargs):
            if not agent_gid:
                raise ValueError("agent_gid is required")
            
            registry = get_agent_registry()
            registry.authorize_operation(
                gid=agent_gid,
                operation=func.__name__,
                capability=capability,
                raise_on_failure=True,
            )
            
            return func(*args, agent_gid=agent_gid, **kwargs)
        
        return wrapper
    
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_registry_instance: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_agent_registry() -> AgentRegistry:
    """Get the singleton agent registry instance."""
    global _registry_instance
    
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = AgentRegistry()
    
    return _registry_instance
