"""
Agent Store — Real-Time Agent State Management

PAC-BENSON-P42: OCC Operationalization & Defect Remediation

Provides real-time agent state tracking:
- Agent registration and heartbeats
- Execution state management
- Health monitoring
- PAC binding

INVARIANTS:
- INV-OCC-004: All agent state transitions visible
- INV-OCC-005: State immutability (historical snapshots preserved)
- INV-OCC-006: No hidden transitions

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_AGENT_STORE_PATH = "./data/agent_states.json"

# Health check thresholds
HEARTBEAT_TIMEOUT_SECONDS = 60
DEGRADED_THRESHOLD_SECONDS = 30


class AgentLane(str, Enum):
    """Agent execution lane classification."""
    ORCHESTRATION = "orchestration"
    FRONTEND = "frontend"
    BACKEND = "backend"
    SECURITY = "security"
    GOVERNANCE = "governance"
    CI = "ci"
    INTEGRITY = "integrity"
    ML = "ml"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


class AgentHealthState(str, Enum):
    """Agent health state."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AgentExecutionState(str, Enum):
    """Agent execution state."""
    IDLE = "idle"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStateRecord(BaseModel):
    """Individual agent state record."""
    
    agent_id: str = Field(..., description="Agent GID (e.g., 'GID-00')")
    agent_name: str = Field(..., description="Agent name (e.g., 'BENSON')")
    lane: AgentLane = Field(..., description="Agent's execution lane")
    role: str = Field(..., description="Agent's role description")
    health: AgentHealthState = Field(default=AgentHealthState.UNKNOWN)
    execution_state: AgentExecutionState = Field(default=AgentExecutionState.IDLE)
    current_pac_id: Optional[str] = Field(None, description="Currently bound PAC ID")
    tasks_completed: int = Field(default=0, ge=0)
    tasks_pending: int = Field(default=0, ge=0)
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    blocked_reason: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)


class AgentStateSnapshot(BaseModel):
    """Historical snapshot of agent states."""
    
    snapshot_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pac_id: Optional[str] = None
    agents: List[AgentStateRecord] = Field(default_factory=list)


class AgentStore:
    """
    Thread-safe agent state store.
    
    Provides:
    - Real-time agent state tracking
    - Health computation based on heartbeats
    - Historical state snapshots
    - PAC binding management
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the agent store."""
        self._lock = threading.Lock()
        self._agents: Dict[str, AgentStateRecord] = {}
        self._snapshots: List[AgentStateSnapshot] = []
        
        self._storage_path = Path(
            storage_path or os.environ.get("CHAINBRIDGE_AGENT_STORE_PATH", DEFAULT_AGENT_STORE_PATH)
        )
        
        # Initialize with known agents
        self._initialize_agents()
        self._load()
    
    def _initialize_agents(self) -> None:
        """Initialize with known agent registry."""
        known_agents = [
            ("GID-00", "BENSON", AgentLane.ORCHESTRATION, "Orchestrator"),
            ("GID-01", "CODY", AgentLane.BACKEND, "Backend Lead"),
            ("GID-02", "SONNY", AgentLane.FRONTEND, "Frontend Lead"),
            ("GID-03", "LIRA", AgentLane.FRONTEND, "UX/Accessibility Lead"),
            ("GID-04", "CINDY", AgentLane.BACKEND, "Backend Support"),
            ("GID-05", "ZAK", AgentLane.SECURITY, "Security Tester"),
            ("GID-06", "SAM", AgentLane.SECURITY, "Security Hardener"),
            ("GID-07", "DAN", AgentLane.CI, "DevOps/CI Lead"),
            ("GID-08", "ALEX", AgentLane.GOVERNANCE, "Governance Enforcer"),
            ("GID-09", "RILEY", AgentLane.GOVERNANCE, "Governance Support"),
            ("GID-10", "MAGGIE", AgentLane.ML, "ML/Data Lead"),
            ("GID-11", "ATLAS", AgentLane.INTEGRITY, "Repo Integrity Engineer"),
        ]
        
        now = datetime.now(timezone.utc)
        for agent_id, name, lane, role in known_agents:
            self._agents[agent_id] = AgentStateRecord(
                agent_id=agent_id,
                agent_name=name,
                lane=lane,
                role=role,
                health=AgentHealthState.UNKNOWN,
                execution_state=AgentExecutionState.IDLE,
                last_heartbeat=now,
                registered_at=now,
            )
    
    def _load(self) -> None:
        """Load agent states from persistence."""
        if not self._storage_path.exists():
            logger.info(f"Agent store not found at {self._storage_path}; using defaults.")
            return
        
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for item in data.get("agents", []):
                record = AgentStateRecord.model_validate(item)
                self._agents[record.agent_id] = record
            
            for snap in data.get("snapshots", [])[-100:]:  # Keep last 100
                self._snapshots.append(AgentStateSnapshot.model_validate(snap))
            
            logger.info(f"Loaded {len(self._agents)} agents from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load agent store: {e}")
    
    def _persist(self) -> None:
        """Persist agent states atomically."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "agents": [a.model_dump(mode="json") for a in self._agents.values()],
            "snapshots": [s.model_dump(mode="json") for s in self._snapshots[-100:]],
        }
        
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="agent_states_",
            dir=self._storage_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, self._storage_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.error(f"Failed to persist agent store: {e}")
            raise
    
    def _compute_health(self, agent: AgentStateRecord) -> AgentHealthState:
        """Compute agent health based on heartbeat freshness."""
        now = datetime.now(timezone.utc)
        age = (now - agent.last_heartbeat).total_seconds()
        
        if age > HEARTBEAT_TIMEOUT_SECONDS:
            return AgentHealthState.CRITICAL
        elif age > DEGRADED_THRESHOLD_SECONDS:
            return AgentHealthState.DEGRADED
        elif agent.error_message:
            return AgentHealthState.DEGRADED
        else:
            return AgentHealthState.HEALTHY
    
    def heartbeat(self, agent_id: str) -> Optional[AgentStateRecord]:
        """Record agent heartbeat, updating health."""
        with self._lock:
            if agent_id not in self._agents:
                return None
            
            agent = self._agents[agent_id]
            updated = AgentStateRecord(
                agent_id=agent.agent_id,
                agent_name=agent.agent_name,
                lane=agent.lane,
                role=agent.role,
                health=AgentHealthState.HEALTHY,
                execution_state=agent.execution_state,
                current_pac_id=agent.current_pac_id,
                tasks_completed=agent.tasks_completed,
                tasks_pending=agent.tasks_pending,
                last_heartbeat=datetime.now(timezone.utc),
                registered_at=agent.registered_at,
                blocked_reason=agent.blocked_reason,
                error_message=None,  # Clear error on heartbeat
            )
            self._agents[agent_id] = updated
            self._persist()
            return updated
    
    def update_execution_state(
        self,
        agent_id: str,
        execution_state: AgentExecutionState,
        pac_id: Optional[str] = None,
        tasks_completed: Optional[int] = None,
        tasks_pending: Optional[int] = None,
        blocked_reason: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[AgentStateRecord]:
        """Update agent execution state."""
        with self._lock:
            if agent_id not in self._agents:
                return None
            
            agent = self._agents[agent_id]
            updated = AgentStateRecord(
                agent_id=agent.agent_id,
                agent_name=agent.agent_name,
                lane=agent.lane,
                role=agent.role,
                health=self._compute_health(agent),
                execution_state=execution_state,
                current_pac_id=pac_id if pac_id is not None else agent.current_pac_id,
                tasks_completed=tasks_completed if tasks_completed is not None else agent.tasks_completed,
                tasks_pending=tasks_pending if tasks_pending is not None else agent.tasks_pending,
                last_heartbeat=datetime.now(timezone.utc),
                registered_at=agent.registered_at,
                blocked_reason=blocked_reason,
                error_message=error_message,
            )
            self._agents[agent_id] = updated
            self._persist()
            
            logger.info(
                f"Agent {agent_id} state updated: {execution_state.value}, "
                f"pac={pac_id}, tasks={tasks_completed}/{tasks_pending}"
            )
            return updated
    
    def get(self, agent_id: str) -> Optional[AgentStateRecord]:
        """Get agent state by ID."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                # Recompute health on read
                return AgentStateRecord(
                    **{**agent.model_dump(), "health": self._compute_health(agent).value}
                )
            return None
    
    def list_all(
        self,
        lane: Optional[AgentLane] = None,
        health: Optional[AgentHealthState] = None,
        execution_state: Optional[AgentExecutionState] = None,
    ) -> List[AgentStateRecord]:
        """List all agents with optional filtering."""
        with self._lock:
            results = []
            for agent in self._agents.values():
                # Recompute health
                current_health = self._compute_health(agent)
                record = AgentStateRecord(
                    **{**agent.model_dump(), "health": current_health.value}
                )
                
                # Apply filters
                if lane and record.lane != lane:
                    continue
                if health and record.health != health:
                    continue
                if execution_state and record.execution_state != execution_state:
                    continue
                
                results.append(record)
            
            return results
    
    def create_snapshot(self, pac_id: Optional[str] = None) -> AgentStateSnapshot:
        """Create a historical snapshot of current agent states."""
        with self._lock:
            snapshot = AgentStateSnapshot(
                pac_id=pac_id,
                agents=[
                    AgentStateRecord(
                        **{**a.model_dump(), "health": self._compute_health(a).value}
                    )
                    for a in self._agents.values()
                ],
            )
            self._snapshots.append(snapshot)
            self._persist()
            return snapshot
    
    def get_snapshots(
        self,
        pac_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[AgentStateSnapshot]:
        """Get historical snapshots."""
        with self._lock:
            results = self._snapshots
            if pac_id:
                results = [s for s in results if s.pac_id == pac_id]
            return results[-limit:]
    
    def bind_to_pac(self, agent_ids: List[str], pac_id: str) -> int:
        """Bind agents to a PAC, setting them to executing."""
        with self._lock:
            count = 0
            for agent_id in agent_ids:
                if agent_id in self._agents:
                    agent = self._agents[agent_id]
                    self._agents[agent_id] = AgentStateRecord(
                        agent_id=agent.agent_id,
                        agent_name=agent.agent_name,
                        lane=agent.lane,
                        role=agent.role,
                        health=AgentHealthState.HEALTHY,
                        execution_state=AgentExecutionState.EXECUTING,
                        current_pac_id=pac_id,
                        tasks_completed=0,
                        tasks_pending=0,
                        last_heartbeat=datetime.now(timezone.utc),
                        registered_at=agent.registered_at,
                    )
                    count += 1
            self._persist()
            return count
    
    def unbind_from_pac(self, pac_id: str) -> int:
        """Unbind all agents from a PAC, resetting to idle."""
        with self._lock:
            count = 0
            for agent_id, agent in self._agents.items():
                if agent.current_pac_id == pac_id:
                    self._agents[agent_id] = AgentStateRecord(
                        agent_id=agent.agent_id,
                        agent_name=agent.agent_name,
                        lane=agent.lane,
                        role=agent.role,
                        health=self._compute_health(agent),
                        execution_state=AgentExecutionState.IDLE,
                        current_pac_id=None,
                        tasks_completed=agent.tasks_completed,
                        tasks_pending=0,
                        last_heartbeat=datetime.now(timezone.utc),
                        registered_at=agent.registered_at,
                    )
                    count += 1
            self._persist()
            return count


# Module-level singleton
_default_store: Optional[AgentStore] = None


def get_agent_store() -> AgentStore:
    """Get the default agent store singleton."""
    global _default_store
    if _default_store is None:
        _default_store = AgentStore()
    return _default_store


def reset_agent_store() -> None:
    """Reset the default agent store (for testing only)."""
    global _default_store
    _default_store = None
