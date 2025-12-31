# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Agent Execution Aggregator
# PAC-008: Agent Execution Visibility — ORDER 2 (Cindy GID-04)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Agent execution aggregation for Operator Console visibility.

Provides:
- OC_AGENT_EXECUTION_VIEW DTO
- PAC ↔ Agent ↔ State timeline aggregation
- Read-only views for OC

GOVERNANCE INVARIANTS:
- INV-AGENT-001: Agent activation must be explicit and visible
- INV-AGENT-002: Each execution step maps to exactly one agent
- INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
- INV-AGENT-004: OC is read-only; no agent control actions
- INV-AGENT-005: Missing state must be explicit (no inference)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.execution.agent_events import (
    AgentActivationEvent,
    AgentExecutionStateEvent,
    AgentState,
    UNAVAILABLE_MARKER,
    get_activation_events,
    get_state_events,
)
from core.execution.execution_ledger import (
    ExecutionEntryType,
    ExecutionLedger,
    ExecutionLedgerEntry,
    get_execution_ledger,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# OC_AGENT_EXECUTION_VIEW DTO — Section 8 Contract
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OCAgentExecutionView:
    """
    Operator Console view of agent execution.
    
    This DTO provides a read-only view of agent execution state
    for operator visibility. No control actions are permitted.
    
    INV-AGENT-004: OC is read-only; no agent control actions.
    """
    
    # Agent identity
    agent_gid: str
    agent_name: str
    agent_role: str
    agent_color: str
    
    # Current state (INV-AGENT-003)
    current_state: str  # QUEUED | ACTIVE | COMPLETE | FAILED
    
    # Execution context
    pac_id: str
    execution_mode: str  # EXECUTION | REVIEW
    execution_order: Optional[int] = None
    order_description: str = UNAVAILABLE_MARKER
    
    # Timing
    activated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Artifacts
    artifacts_created: List[str] = field(default_factory=list)
    
    # Error (if FAILED)
    error_message: Optional[str] = None
    
    # Ledger reference
    ledger_entry_hash: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "agent_gid": self.agent_gid,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_color": self.agent_color,
            "current_state": self.current_state,
            "pac_id": self.pac_id,
            "execution_mode": self.execution_mode,
            "execution_order": self.execution_order,
            "order_description": self.order_description,
            "activated_at": self.activated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "artifacts_created": self.artifacts_created,
            "error_message": self.error_message,
            "ledger_entry_hash": self.ledger_entry_hash,
        }


@dataclass
class OCAgentTimelineEvent:
    """
    Single event in agent execution timeline.
    
    Timeline events represent discrete points in the execution
    lifecycle that operators can observe.
    """
    
    event_id: str
    event_type: str  # ACTIVATION | STATE_CHANGE | ARTIFACT_CREATED
    timestamp: str
    
    # Agent context
    agent_gid: str
    agent_name: str
    
    # Event details
    description: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    
    # Ledger reference
    ledger_entry_hash: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "agent_gid": self.agent_gid,
            "agent_name": self.agent_name,
            "description": self.description,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "ledger_entry_hash": self.ledger_entry_hash,
        }


@dataclass
class OCPACExecutionView:
    """
    Operator Console view of a PAC's execution status.
    
    Aggregates all agent execution information for a single PAC.
    """
    
    pac_id: str
    
    # Agents involved
    agents: List[OCAgentExecutionView] = field(default_factory=list)
    
    # Timeline
    timeline: List[OCAgentTimelineEvent] = field(default_factory=list)
    
    # Summary
    total_agents: int = 0
    agents_queued: int = 0
    agents_active: int = 0
    agents_complete: int = 0
    agents_failed: int = 0
    
    # Timing
    execution_started_at: Optional[str] = None
    execution_completed_at: Optional[str] = None
    
    # Status
    execution_status: str = "PENDING"  # PENDING | IN_PROGRESS | COMPLETE | FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "pac_id": self.pac_id,
            "agents": [a.to_dict() for a in self.agents],
            "timeline": [e.to_dict() for e in self.timeline],
            "total_agents": self.total_agents,
            "agents_queued": self.agents_queued,
            "agents_active": self.agents_active,
            "agents_complete": self.agents_complete,
            "agents_failed": self.agents_failed,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "execution_status": self.execution_status,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGGREGATOR CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class AgentExecutionAggregator:
    """
    Aggregates agent execution data for Operator Console visibility.
    
    This class provides read-only views of agent execution state.
    No control actions are permitted (INV-AGENT-004).
    """
    
    def __init__(self, ledger: Optional[ExecutionLedger] = None):
        """
        Initialize aggregator.
        
        Args:
            ledger: Optional execution ledger instance.
                   If not provided, uses the singleton.
        """
        self._ledger = ledger or get_execution_ledger()
    
    # ───────────────────────────────────────────────────────────────────────────
    # AGENT VIEWS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_agent_view(
        self,
        pac_id: str,
        agent_gid: str,
    ) -> Optional[OCAgentExecutionView]:
        """
        Get OC view of a specific agent's execution.
        
        Args:
            pac_id: PAC identifier
            agent_gid: Agent GID
        
        Returns:
            OCAgentExecutionView or None if not found
        """
        # Get activation event
        activations = [
            e for e in get_activation_events(pac_id)
            if e.agent_gid == agent_gid
        ]
        
        if not activations:
            return None
        
        activation = activations[0]
        
        # Get state events
        state_events = get_state_events(pac_id=pac_id, agent_gid=agent_gid)
        
        # Determine current state
        current_state = AgentState.QUEUED.value
        started_at = None
        completed_at = None
        duration_ms = None
        error_message = None
        artifacts_created = []
        
        for event in sorted(state_events, key=lambda e: e.timestamp):
            current_state = event.new_state
            
            if event.new_state == AgentState.ACTIVE.value:
                started_at = event.started_at or event.timestamp
            
            if event.new_state in (AgentState.COMPLETE.value, AgentState.FAILED.value):
                completed_at = event.completed_at or event.timestamp
                duration_ms = event.duration_ms
                error_message = event.error_message
            
            if event.artifacts_created:
                artifacts_created.extend(event.artifacts_created)
        
        # Get ledger entry hash
        ledger_entries = self._ledger.get_by_agent_gid(agent_gid)
        ledger_hash = UNAVAILABLE_MARKER
        if ledger_entries:
            ledger_hash = ledger_entries[-1].entry_hash
        
        return OCAgentExecutionView(
            agent_gid=activation.agent_gid,
            agent_name=activation.agent_name,
            agent_role=activation.agent_role,
            agent_color=activation.agent_color,
            current_state=current_state,
            pac_id=pac_id,
            execution_mode=activation.execution_mode,
            execution_order=activation.execution_order,
            order_description=activation.order_description,
            activated_at=activation.timestamp,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            artifacts_created=list(set(artifacts_created)),
            error_message=error_message,
            ledger_entry_hash=ledger_hash,
        )
    
    def get_all_agent_views(self, pac_id: str) -> List[OCAgentExecutionView]:
        """
        Get OC views for all agents in a PAC.
        
        Args:
            pac_id: PAC identifier
        
        Returns:
            List of OCAgentExecutionView sorted by execution order
        """
        # Get all activation events for this PAC
        activations = get_activation_events(pac_id)
        
        views = []
        for activation in activations:
            view = self.get_agent_view(pac_id, activation.agent_gid)
            if view:
                views.append(view)
        
        # Sort by execution order
        return sorted(
            views,
            key=lambda v: (v.execution_order or 999, v.agent_gid)
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # TIMELINE VIEWS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_agent_timeline(
        self,
        pac_id: str,
        agent_gid: Optional[str] = None,
    ) -> List[OCAgentTimelineEvent]:
        """
        Get execution timeline events.
        
        Args:
            pac_id: PAC identifier
            agent_gid: Optional filter by agent GID
        
        Returns:
            List of timeline events in chronological order
        """
        events = []
        
        # Get ledger entries
        ledger_entries = self._ledger.get_agent_timeline(pac_id, agent_gid)
        
        for entry in ledger_entries:
            if entry.entry_type == ExecutionEntryType.AGENT_ACTIVATION:
                payload = entry.payload
                events.append(OCAgentTimelineEvent(
                    event_id=entry.entry_id,
                    event_type="ACTIVATION",
                    timestamp=entry.timestamp,
                    agent_gid=payload.get("agent_gid", UNAVAILABLE_MARKER),
                    agent_name=payload.get("agent_name", UNAVAILABLE_MARKER),
                    description=f"Agent {payload.get('agent_name', 'Unknown')} activated for {payload.get('order_description', 'execution')}",
                    ledger_entry_hash=entry.entry_hash,
                ))
            
            elif entry.entry_type == ExecutionEntryType.AGENT_STATE_CHANGE:
                payload = entry.payload
                events.append(OCAgentTimelineEvent(
                    event_id=entry.entry_id,
                    event_type="STATE_CHANGE",
                    timestamp=entry.timestamp,
                    agent_gid=payload.get("agent_gid", UNAVAILABLE_MARKER),
                    agent_name=payload.get("agent_name", UNAVAILABLE_MARKER),
                    description=f"State: {payload.get('previous_state', '?')} → {payload.get('new_state', '?')}",
                    previous_state=payload.get("previous_state"),
                    new_state=payload.get("new_state"),
                    ledger_entry_hash=entry.entry_hash,
                ))
        
        return sorted(events, key=lambda e: e.timestamp)
    
    # ───────────────────────────────────────────────────────────────────────────
    # PAC EXECUTION VIEW
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_pac_execution_view(self, pac_id: str) -> OCPACExecutionView:
        """
        Get comprehensive execution view for a PAC.
        
        Args:
            pac_id: PAC identifier
        
        Returns:
            OCPACExecutionView with all agent states and timeline
        """
        agents = self.get_all_agent_views(pac_id)
        timeline = self.get_agent_timeline(pac_id)
        
        # Count states
        agents_queued = sum(1 for a in agents if a.current_state == AgentState.QUEUED.value)
        agents_active = sum(1 for a in agents if a.current_state == AgentState.ACTIVE.value)
        agents_complete = sum(1 for a in agents if a.current_state == AgentState.COMPLETE.value)
        agents_failed = sum(1 for a in agents if a.current_state == AgentState.FAILED.value)
        
        # Determine overall status
        execution_status = "PENDING"
        if agents_active > 0:
            execution_status = "IN_PROGRESS"
        elif agents_failed > 0:
            execution_status = "FAILED"
        elif agents_complete == len(agents) and len(agents) > 0:
            execution_status = "COMPLETE"
        elif agents_queued < len(agents):
            execution_status = "IN_PROGRESS"
        
        # Get timing from timeline
        execution_started_at = None
        execution_completed_at = None
        
        if timeline:
            execution_started_at = timeline[0].timestamp
            
            # Check if all agents complete
            if execution_status == "COMPLETE":
                execution_completed_at = timeline[-1].timestamp
        
        return OCPACExecutionView(
            pac_id=pac_id,
            agents=agents,
            timeline=timeline,
            total_agents=len(agents),
            agents_queued=agents_queued,
            agents_active=agents_active,
            agents_complete=agents_complete,
            agents_failed=agents_failed,
            execution_started_at=execution_started_at,
            execution_completed_at=execution_completed_at,
            execution_status=execution_status,
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # ACTIVE AGENTS VIEW
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_active_agents(self) -> List[OCAgentExecutionView]:
        """
        Get all currently active agents across all PACs.
        
        Returns:
            List of agents with state=ACTIVE
        """
        active_agents = []
        
        # Get all PAC IDs from ledger
        pac_ids = set()
        for entry in self._ledger:
            pac_ids.add(entry.pac_id)
        
        # Check each PAC for active agents
        for pac_id in pac_ids:
            for agent in self.get_all_agent_views(pac_id):
                if agent.current_state == AgentState.ACTIVE.value:
                    active_agents.append(agent)
        
        return active_agents
    
    # ───────────────────────────────────────────────────────────────────────────
    # PAC LIST VIEW
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_pac_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all PACs with execution summary.
        
        Returns:
            List of PAC summaries
        """
        pac_ids = set()
        for entry in self._ledger:
            pac_ids.add(entry.pac_id)
        
        pacs = []
        for pac_id in sorted(pac_ids):
            view = self.get_pac_execution_view(pac_id)
            pacs.append({
                "pac_id": pac_id,
                "total_agents": view.total_agents,
                "agents_complete": view.agents_complete,
                "agents_failed": view.agents_failed,
                "execution_status": view.execution_status,
                "execution_started_at": view.execution_started_at,
            })
        
        return pacs


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

_AGGREGATOR: Optional[AgentExecutionAggregator] = None


def get_agent_aggregator() -> AgentExecutionAggregator:
    """Get the singleton aggregator instance."""
    global _AGGREGATOR
    if _AGGREGATOR is None:
        _AGGREGATOR = AgentExecutionAggregator()
    return _AGGREGATOR


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "OCAgentExecutionView",
    "OCAgentTimelineEvent",
    "OCPACExecutionView",
    "AgentExecutionAggregator",
    "get_agent_aggregator",
    "UNAVAILABLE_MARKER",
]
