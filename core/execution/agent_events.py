# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Agent Execution Events
# PAC-008: Agent Execution Visibility — ORDER 1 (Cody GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Agent execution event schema and emission.

This module provides canonical event types for agent execution visibility:
- AgentActivationEvent: Emitted when an agent is activated for a PAC
- AgentExecutionStateEvent: Emitted when agent state changes

GOVERNANCE INVARIANTS:
- INV-AGENT-001: Agent activation must be explicit and visible
- INV-AGENT-002: Each execution step maps to exactly one agent
- INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
- INV-AGENT-005: Missing state must be explicit (no inference)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT STATE ENUM — INV-AGENT-003
# ═══════════════════════════════════════════════════════════════════════════════

class AgentState(str, Enum):
    """
    Canonical agent execution states.
    
    INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
    No other states are permitted.
    """
    
    QUEUED = "QUEUED"       # Agent assigned but not yet executing
    ACTIVE = "ACTIVE"       # Agent currently executing
    COMPLETE = "COMPLETE"   # Agent execution finished successfully
    FAILED = "FAILED"       # Agent execution failed


class AgentExecutionMode(str, Enum):
    """Agent execution mode."""
    
    EXECUTION = "EXECUTION"   # Agent is executing code/tasks
    REVIEW = "REVIEW"         # Agent is reviewing only (read-only)


# ═══════════════════════════════════════════════════════════════════════════════
# UNAVAILABLE MARKER — INV-AGENT-005
# ═══════════════════════════════════════════════════════════════════════════════

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""
INV-AGENT-005: Missing state must be explicit (no inference).
Use this marker for any field where data is not available.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_event_id(prefix: str = "agent") -> str:
    """Generate unique event ID."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVATION EVENT — INV-AGENT-001
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentActivationEvent:
    """
    Agent activation event — emitted when an agent is bound to a PAC.
    
    INV-AGENT-001: Agent activation must be explicit and visible.
    
    This event is emitted BEFORE execution begins and represents
    the explicit binding of an agent to a PAC execution context.
    """
    
    # Event identity
    event_id: str = field(default_factory=lambda: _generate_event_id("actv"))
    event_type: str = "AGENT_ACTIVATION"
    timestamp: str = field(default_factory=_utc_now_iso)
    
    # Agent identity
    agent_gid: str = UNAVAILABLE_MARKER
    agent_name: str = UNAVAILABLE_MARKER
    agent_role: str = UNAVAILABLE_MARKER
    agent_color: str = UNAVAILABLE_MARKER
    
    # Execution context
    pac_id: str = UNAVAILABLE_MARKER
    execution_mode: str = "EXECUTION"  # EXECUTION or REVIEW
    permissions_accepted: bool = False
    runtime_bound: bool = False
    
    # Order assignment (INV-AGENT-002)
    execution_order: Optional[int] = None
    order_description: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def validate(self) -> bool:
        """
        Validate activation event meets invariants.
        
        Returns:
            True if valid, False otherwise
        """
        # INV-AGENT-001: Agent GID must be explicit
        if self.agent_gid == UNAVAILABLE_MARKER:
            logger.error("INV-AGENT-001 violation: agent_gid is UNAVAILABLE")
            return False
        
        # PAC ID must be explicit
        if self.pac_id == UNAVAILABLE_MARKER:
            logger.error("INV-AGENT-001 violation: pac_id is UNAVAILABLE")
            return False
        
        # Permissions and runtime binding must be true for execution
        if self.execution_mode == "EXECUTION":
            if not self.permissions_accepted:
                logger.error("INV-AGENT-001 violation: permissions not accepted for EXECUTION mode")
                return False
            if not self.runtime_bound:
                logger.error("INV-AGENT-001 violation: runtime not bound for EXECUTION mode")
                return False
        
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT EXECUTION STATE EVENT — INV-AGENT-003
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentExecutionStateEvent:
    """
    Agent execution state change event.
    
    INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
    
    Emitted whenever an agent's execution state changes.
    """
    
    # Event identity
    event_id: str = field(default_factory=lambda: _generate_event_id("state"))
    event_type: str = "AGENT_STATE_CHANGE"
    timestamp: str = field(default_factory=_utc_now_iso)
    
    # Agent identity
    agent_gid: str = UNAVAILABLE_MARKER
    agent_name: str = UNAVAILABLE_MARKER
    
    # State transition
    previous_state: str = UNAVAILABLE_MARKER
    new_state: str = UNAVAILABLE_MARKER
    
    # Execution context
    pac_id: str = UNAVAILABLE_MARKER
    execution_order: Optional[int] = None
    
    # Execution details
    step_description: str = UNAVAILABLE_MARKER
    artifacts_created: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def validate(self) -> bool:
        """
        Validate state event meets invariants.
        
        Returns:
            True if valid, False otherwise
        """
        # INV-AGENT-003: new_state must be in allowed set
        allowed_states = {s.value for s in AgentState}
        if self.new_state not in allowed_states:
            logger.error(
                f"INV-AGENT-003 violation: state '{self.new_state}' not in {allowed_states}"
            )
            return False
        
        # Agent GID must be explicit
        if self.agent_gid == UNAVAILABLE_MARKER:
            logger.error("INV-AGENT-002 violation: agent_gid is UNAVAILABLE")
            return False
        
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT EMISSION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Global event store for in-memory tracking
_ACTIVATION_EVENTS: List[AgentActivationEvent] = []
_STATE_EVENTS: List[AgentExecutionStateEvent] = []


def emit_agent_activation(
    agent_gid: str,
    agent_name: str,
    pac_id: str,
    execution_mode: AgentExecutionMode = AgentExecutionMode.EXECUTION,
    agent_role: str = UNAVAILABLE_MARKER,
    agent_color: str = UNAVAILABLE_MARKER,
    execution_order: Optional[int] = None,
    order_description: str = UNAVAILABLE_MARKER,
) -> AgentActivationEvent:
    """
    Emit an agent activation event.
    
    INV-AGENT-001: Agent activation must be explicit and visible.
    
    Args:
        agent_gid: Agent's GID (e.g., "GID-01")
        agent_name: Agent's name (e.g., "Cody")
        pac_id: PAC identifier
        execution_mode: EXECUTION or REVIEW
        agent_role: Agent's role description
        agent_color: Agent's color designation
        execution_order: Order number in execution sequence
        order_description: Description of the order task
    
    Returns:
        The created AgentActivationEvent
    """
    event = AgentActivationEvent(
        agent_gid=agent_gid,
        agent_name=agent_name,
        pac_id=pac_id,
        execution_mode=execution_mode.value if isinstance(execution_mode, AgentExecutionMode) else execution_mode,
        agent_role=agent_role,
        agent_color=agent_color,
        execution_order=execution_order,
        order_description=order_description,
        permissions_accepted=True,
        runtime_bound=True,
    )
    
    # Validate before storing
    if not event.validate():
        logger.warning(f"Agent activation event validation failed: {event.agent_gid}")
    
    # Store event
    _ACTIVATION_EVENTS.append(event)
    
    logger.info(
        f"AGENT_ACTIVATION: {agent_name} ({agent_gid}) activated for {pac_id} "
        f"[mode={execution_mode}, order={execution_order}]"
    )
    
    return event


def emit_agent_state_change(
    agent_gid: str,
    agent_name: str,
    pac_id: str,
    new_state: AgentState,
    previous_state: AgentState = AgentState.QUEUED,
    execution_order: Optional[int] = None,
    step_description: str = UNAVAILABLE_MARKER,
    artifacts_created: Optional[List[str]] = None,
    error_message: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> AgentExecutionStateEvent:
    """
    Emit an agent state change event.
    
    INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
    
    Args:
        agent_gid: Agent's GID
        agent_name: Agent's name
        pac_id: PAC identifier
        new_state: New agent state
        previous_state: Previous agent state
        execution_order: Order number in execution sequence
        step_description: Description of the execution step
        artifacts_created: List of artifacts created during execution
        error_message: Error message if state is FAILED
        started_at: ISO timestamp when execution started
        completed_at: ISO timestamp when execution completed
        duration_ms: Duration of execution in milliseconds
    
    Returns:
        The created AgentExecutionStateEvent
    """
    event = AgentExecutionStateEvent(
        agent_gid=agent_gid,
        agent_name=agent_name,
        pac_id=pac_id,
        new_state=new_state.value if isinstance(new_state, AgentState) else new_state,
        previous_state=previous_state.value if isinstance(previous_state, AgentState) else previous_state,
        execution_order=execution_order,
        step_description=step_description,
        artifacts_created=artifacts_created or [],
        error_message=error_message,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )
    
    # Validate before storing
    if not event.validate():
        logger.warning(f"Agent state event validation failed: {event.agent_gid}")
    
    # Store event
    _STATE_EVENTS.append(event)
    
    logger.info(
        f"AGENT_STATE_CHANGE: {agent_name} ({agent_gid}) "
        f"{previous_state} → {new_state} "
        f"[pac={pac_id}, order={execution_order}]"
    )
    
    return event


def get_activation_events(pac_id: Optional[str] = None) -> List[AgentActivationEvent]:
    """
    Get agent activation events.
    
    Args:
        pac_id: Optional filter by PAC ID
    
    Returns:
        List of activation events
    """
    if pac_id:
        return [e for e in _ACTIVATION_EVENTS if e.pac_id == pac_id]
    return _ACTIVATION_EVENTS.copy()


def get_state_events(
    pac_id: Optional[str] = None,
    agent_gid: Optional[str] = None,
) -> List[AgentExecutionStateEvent]:
    """
    Get agent state change events.
    
    Args:
        pac_id: Optional filter by PAC ID
        agent_gid: Optional filter by agent GID
    
    Returns:
        List of state events
    """
    events = _STATE_EVENTS.copy()
    
    if pac_id:
        events = [e for e in events if e.pac_id == pac_id]
    if agent_gid:
        events = [e for e in events if e.agent_gid == agent_gid]
    
    return events


def get_current_agent_state(
    agent_gid: str,
    pac_id: str,
) -> Optional[AgentState]:
    """
    Get the current state of an agent for a PAC.
    
    Returns the most recent state, or None if no state events exist.
    """
    events = get_state_events(pac_id=pac_id, agent_gid=agent_gid)
    
    if not events:
        return None
    
    # Get most recent event
    latest = max(events, key=lambda e: e.timestamp)
    
    try:
        return AgentState(latest.new_state)
    except ValueError:
        return None


def clear_events() -> None:
    """Clear all stored events. Used for testing."""
    global _ACTIVATION_EVENTS, _STATE_EVENTS
    _ACTIVATION_EVENTS = []
    _STATE_EVENTS = []


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "AgentState",
    "AgentExecutionMode",
    "AgentActivationEvent",
    "AgentExecutionStateEvent",
    "UNAVAILABLE_MARKER",
    "emit_agent_activation",
    "emit_agent_state_change",
    "get_activation_events",
    "get_state_events",
    "get_current_agent_state",
    "clear_events",
]
