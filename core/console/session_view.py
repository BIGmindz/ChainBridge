"""
Operator Console Live GIE Session View — Timeline + State + Closure Visualization.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-02 (Sonny) — FRONTEND
Deliverable: Operator Console Live GIE Session View

Features:
- Real-time session timeline visualization
- Agent state monitoring
- PDO/BER/WRAP closure tracking
- Live metrics dashboard
- Session playback capability

This module provides the data layer and rendering engine for
the GIE Operator Console session visualization.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# CONSTANTS
# =============================================================================

MODULE_VERSION = "1.0.0"
MAX_TIMELINE_EVENTS = 10000
REFRESH_INTERVAL_MS = 250


# =============================================================================
# ENUMS
# =============================================================================

class SessionState(Enum):
    """State of a GIE session."""
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EventType(Enum):
    """Types of timeline events."""
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    PAC_RECEIVED = "PAC_RECEIVED"
    BER_EMITTED = "BER_EMITTED"
    PDO_CREATED = "PDO_CREATED"
    WRAP_EXECUTED = "WRAP_EXECUTED"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"
    DEPENDENCY_SATISFIED = "DEPENDENCY_SATISFIED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    METRIC_RECORDED = "METRIC_RECORDED"


class AgentVisualState(Enum):
    """Visual state for agent rendering."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    BLOCKED = "BLOCKED"


class ClosureStatus(Enum):
    """Status of governance closure."""
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ViewMode(Enum):
    """Visualization mode."""
    TIMELINE = "TIMELINE"
    GRAPH = "GRAPH"
    METRICS = "METRICS"
    COMBINED = "COMBINED"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TimelineEvent:
    """An event in the session timeline."""
    
    event_id: str
    event_type: EventType
    timestamp: str
    agent_id: Optional[str] = None
    title: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    
    @property
    def time(self) -> datetime:
        """Parse timestamp to datetime."""
        return datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AgentView:
    """Visual representation of an agent."""
    
    agent_id: str
    name: str
    state: AgentVisualState = AgentVisualState.IDLE
    progress: float = 0.0  # 0.0 to 1.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: int = 0
    output_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Check if agent is active."""
        return self.state == AgentVisualState.RUNNING
    
    @property
    def is_complete(self) -> bool:
        """Check if agent completed."""
        return self.state in (AgentVisualState.SUCCESS, AgentVisualState.FAILURE)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize view."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "progress": self.progress,
            "duration_ms": self.duration_ms,
            "output_count": self.output_count,
            "error_count": self.error_count,
        }


@dataclass
class ClosureView:
    """Visual representation of governance closure status."""
    
    session_id: str
    ber_status: ClosureStatus = ClosureStatus.PENDING
    pdo_status: ClosureStatus = ClosureStatus.PENDING
    wrap_status: ClosureStatus = ClosureStatus.PENDING
    positive_closure: bool = False
    ber_count: int = 0
    pdo_count: int = 0
    wrap_count: int = 0
    
    @property
    def is_complete(self) -> bool:
        """Check if all closures complete."""
        return (
            self.ber_status == ClosureStatus.COMPLETE
            and self.pdo_status == ClosureStatus.COMPLETE
            and self.positive_closure
        )
    
    @property
    def completion_percentage(self) -> float:
        """Calculate overall completion percentage."""
        total = 4  # BER, PDO, WRAP, POSITIVE_CLOSURE
        complete = 0
        if self.ber_status == ClosureStatus.COMPLETE:
            complete += 1
        if self.pdo_status == ClosureStatus.COMPLETE:
            complete += 1
        if self.wrap_status == ClosureStatus.COMPLETE:
            complete += 1
        if self.positive_closure:
            complete += 1
        return complete / total
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize view."""
        return {
            "session_id": self.session_id,
            "ber_status": self.ber_status.value,
            "pdo_status": self.pdo_status.value,
            "wrap_status": self.wrap_status.value,
            "positive_closure": self.positive_closure,
            "completion_percentage": f"{self.completion_percentage:.0%}",
        }


@dataclass
class MetricPoint:
    """A metric data point."""
    
    metric_id: str
    name: str
    value: float
    timestamp: str
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metric."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "unit": self.unit,
        }


@dataclass
class SessionMetrics:
    """Aggregated session metrics."""
    
    total_agents: int = 0
    completed_agents: int = 0
    failed_agents: int = 0
    total_events: int = 0
    total_pdo_count: int = 0
    total_ber_count: int = 0
    avg_agent_duration_ms: float = 0.0
    session_duration_ms: int = 0
    throughput_events_per_sec: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics."""
        return {
            "total_agents": self.total_agents,
            "completed_agents": self.completed_agents,
            "failed_agents": self.failed_agents,
            "total_events": self.total_events,
            "total_pdo_count": self.total_pdo_count,
            "total_ber_count": self.total_ber_count,
            "avg_agent_duration_ms": int(self.avg_agent_duration_ms),
            "session_duration_ms": self.session_duration_ms,
        }


@dataclass
class SessionSnapshot:
    """Complete snapshot of session state for rendering."""
    
    session_id: str
    state: SessionState
    timeline_events: List[TimelineEvent]
    agent_views: Dict[str, AgentView]
    closure_view: ClosureView
    metrics: SessionMetrics
    captured_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot."""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "timeline_events": [e.to_dict() for e in self.timeline_events[-50:]],
            "agents": {k: v.to_dict() for k, v in self.agent_views.items()},
            "closure": self.closure_view.to_dict(),
            "metrics": self.metrics.to_dict(),
            "captured_at": self.captured_at,
        }


# =============================================================================
# TIMELINE MANAGER
# =============================================================================

class TimelineManager:
    """Manages session timeline events."""
    
    def __init__(self, max_events: int = MAX_TIMELINE_EVENTS) -> None:
        self._events: List[TimelineEvent] = []
        self._max_events = max_events
        self._event_index: Dict[str, TimelineEvent] = {}
    
    def add_event(
        self,
        event_type: EventType,
        title: str,
        description: str = "",
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimelineEvent:
        """Add event to timeline."""
        event = TimelineEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
            title=title,
            description=description,
            metadata=metadata or {},
        )
        
        self._events.append(event)
        self._event_index[event.event_id] = event
        
        # Trim if needed
        if len(self._events) > self._max_events:
            removed = self._events.pop(0)
            self._event_index.pop(removed.event_id, None)
        
        return event
    
    def get_events(
        self,
        since: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """Get filtered events."""
        events = self._events
        
        if since:
            events = [e for e in events if e.time >= since]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        
        return events[-limit:]
    
    def get_event(self, event_id: str) -> Optional[TimelineEvent]:
        """Get event by ID."""
        return self._event_index.get(event_id)
    
    @property
    def event_count(self) -> int:
        """Total event count."""
        return len(self._events)
    
    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()
        self._event_index.clear()


# =============================================================================
# SESSION VIEW
# =============================================================================

class SessionView:
    """
    Live GIE Session View for Operator Console.
    
    Provides real-time visualization of:
    - Timeline of all session events
    - Individual agent states and progress
    - Governance closure status (BER/PDO/WRAP)
    - Aggregated session metrics
    """
    
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._state = SessionState.INITIALIZING
        self._timeline = TimelineManager()
        self._agents: Dict[str, AgentView] = {}
        self._closure = ClosureView(session_id=session_id)
        self._metrics = SessionMetrics()
        self._metric_points: List[MetricPoint] = []
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._listeners: List[Callable[[SessionSnapshot], None]] = []
    
    # -------------------------------------------------------------------------
    # STATE MANAGEMENT
    # -------------------------------------------------------------------------
    
    @property
    def state(self) -> SessionState:
        """Current session state."""
        return self._state
    
    def start(self) -> None:
        """Start the session."""
        self._state = SessionState.ACTIVE
        self._start_time = datetime.now(timezone.utc)
        self._timeline.add_event(
            EventType.SESSION_START,
            "Session Started",
            f"Session {self.session_id} initialized",
        )
        self._notify_listeners()
    
    def pause(self) -> None:
        """Pause the session."""
        self._state = SessionState.PAUSED
    
    def resume(self) -> None:
        """Resume paused session."""
        if self._state == SessionState.PAUSED:
            self._state = SessionState.ACTIVE
    
    def complete(self) -> None:
        """Complete the session."""
        self._state = SessionState.COMPLETED
        self._end_time = datetime.now(timezone.utc)
        self._timeline.add_event(
            EventType.SESSION_END,
            "Session Completed",
            f"Session {self.session_id} completed successfully",
        )
        self._update_metrics()
        self._notify_listeners()
    
    def fail(self, reason: str = "") -> None:
        """Mark session as failed."""
        self._state = SessionState.FAILED
        self._end_time = datetime.now(timezone.utc)
        self._timeline.add_event(
            EventType.ERROR_OCCURRED,
            "Session Failed",
            reason,
        )
        self._notify_listeners()
    
    # -------------------------------------------------------------------------
    # AGENT MANAGEMENT
    # -------------------------------------------------------------------------
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentView:
        """Register an agent for tracking."""
        view = AgentView(
            agent_id=agent_id,
            name=name,
            metadata=metadata or {},
        )
        self._agents[agent_id] = view
        self._metrics.total_agents += 1
        return view
    
    def start_agent(self, agent_id: str) -> None:
        """Mark agent as started."""
        if agent_id in self._agents:
            view = self._agents[agent_id]
            view.state = AgentVisualState.RUNNING
            view.start_time = datetime.now(timezone.utc).isoformat()
            
            self._timeline.add_event(
                EventType.AGENT_STARTED,
                f"Agent {view.name} Started",
                agent_id=agent_id,
            )
            self._notify_listeners()
    
    def update_agent_progress(self, agent_id: str, progress: float) -> None:
        """Update agent progress (0.0 to 1.0)."""
        if agent_id in self._agents:
            self._agents[agent_id].progress = min(1.0, max(0.0, progress))
            self._notify_listeners()
    
    def complete_agent(
        self,
        agent_id: str,
        outputs: int = 0,
        success: bool = True,
    ) -> None:
        """Mark agent as completed."""
        if agent_id in self._agents:
            view = self._agents[agent_id]
            view.state = AgentVisualState.SUCCESS if success else AgentVisualState.FAILURE
            view.progress = 1.0
            view.end_time = datetime.now(timezone.utc).isoformat()
            view.output_count = outputs
            
            # Calculate duration
            if view.start_time:
                start = datetime.fromisoformat(view.start_time.replace("Z", "+00:00"))
                end = datetime.fromisoformat(view.end_time.replace("Z", "+00:00"))
                view.duration_ms = int((end - start).total_seconds() * 1000)
            
            if success:
                self._metrics.completed_agents += 1
                self._timeline.add_event(
                    EventType.AGENT_COMPLETED,
                    f"Agent {view.name} Completed",
                    f"Produced {outputs} outputs",
                    agent_id=agent_id,
                )
            else:
                self._metrics.failed_agents += 1
                self._timeline.add_event(
                    EventType.AGENT_FAILED,
                    f"Agent {view.name} Failed",
                    agent_id=agent_id,
                )
            
            self._update_metrics()
            self._notify_listeners()
    
    def block_agent(self, agent_id: str, reason: str = "") -> None:
        """Mark agent as blocked."""
        if agent_id in self._agents:
            self._agents[agent_id].state = AgentVisualState.BLOCKED
            self._notify_listeners()
    
    def get_agent(self, agent_id: str) -> Optional[AgentView]:
        """Get agent view."""
        return self._agents.get(agent_id)
    
    # -------------------------------------------------------------------------
    # GOVERNANCE CLOSURE TRACKING
    # -------------------------------------------------------------------------
    
    def record_ber(self, ber_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record BER emission."""
        self._closure.ber_count += 1
        self._closure.ber_status = ClosureStatus.PARTIAL
        self._metrics.total_ber_count += 1
        
        self._timeline.add_event(
            EventType.BER_EMITTED,
            f"BER Emitted: {ber_id}",
            metadata=metadata or {},
        )
        self._notify_listeners()
    
    def complete_ber(self) -> None:
        """Mark BER closure as complete."""
        self._closure.ber_status = ClosureStatus.COMPLETE
        self._notify_listeners()
    
    def record_pdo(self, pdo_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record PDO creation."""
        self._closure.pdo_count += 1
        self._closure.pdo_status = ClosureStatus.PARTIAL
        self._metrics.total_pdo_count += 1
        
        self._timeline.add_event(
            EventType.PDO_CREATED,
            f"PDO Created: {pdo_id}",
            metadata=metadata or {},
        )
        self._notify_listeners()
    
    def complete_pdo(self) -> None:
        """Mark PDO closure as complete."""
        self._closure.pdo_status = ClosureStatus.COMPLETE
        self._notify_listeners()
    
    def record_wrap(self, wrap_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record WRAP execution."""
        self._closure.wrap_count += 1
        self._closure.wrap_status = ClosureStatus.PARTIAL
        
        self._timeline.add_event(
            EventType.WRAP_EXECUTED,
            f"WRAP Executed: {wrap_id}",
            metadata=metadata or {},
        )
        self._notify_listeners()
    
    def complete_wrap(self) -> None:
        """Mark WRAP closure as complete."""
        self._closure.wrap_status = ClosureStatus.COMPLETE
        self._notify_listeners()
    
    def set_positive_closure(self, achieved: bool = True) -> None:
        """Set positive closure status."""
        self._closure.positive_closure = achieved
        self._notify_listeners()
    
    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> MetricPoint:
        """Record a metric data point."""
        point = MetricPoint(
            metric_id=f"MET-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            unit=unit,
            tags=tags or {},
        )
        self._metric_points.append(point)
        
        self._timeline.add_event(
            EventType.METRIC_RECORDED,
            f"Metric: {name}={value}{unit}",
        )
        
        return point
    
    def _update_metrics(self) -> None:
        """Update aggregated metrics."""
        self._metrics.total_events = self._timeline.event_count
        
        # Calculate average agent duration
        durations = [
            a.duration_ms for a in self._agents.values()
            if a.is_complete and a.duration_ms > 0
        ]
        if durations:
            self._metrics.avg_agent_duration_ms = sum(durations) / len(durations)
        
        # Calculate session duration
        if self._start_time:
            end = self._end_time or datetime.now(timezone.utc)
            self._metrics.session_duration_ms = int(
                (end - self._start_time).total_seconds() * 1000
            )
        
        # Calculate throughput
        if self._metrics.session_duration_ms > 0:
            self._metrics.throughput_events_per_sec = (
                self._metrics.total_events / (self._metrics.session_duration_ms / 1000)
            )
    
    @property
    def metrics(self) -> SessionMetrics:
        """Get current metrics."""
        self._update_metrics()
        return self._metrics
    
    # -------------------------------------------------------------------------
    # LISTENERS
    # -------------------------------------------------------------------------
    
    def add_listener(self, callback: Callable[[SessionSnapshot], None]) -> None:
        """Add snapshot listener."""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[SessionSnapshot], None]) -> None:
        """Remove snapshot listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        """Notify all listeners with current snapshot."""
        snapshot = self.get_snapshot()
        for listener in self._listeners:
            try:
                listener(snapshot)
            except Exception:
                pass  # Don't let listener errors affect view
    
    # -------------------------------------------------------------------------
    # SNAPSHOT
    # -------------------------------------------------------------------------
    
    def get_snapshot(self) -> SessionSnapshot:
        """Get current session snapshot."""
        self._update_metrics()
        return SessionSnapshot(
            session_id=self.session_id,
            state=self._state,
            timeline_events=list(self._timeline.get_events()),
            agent_views=dict(self._agents),
            closure_view=self._closure,
            metrics=self._metrics,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def get_timeline_events(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """Get timeline events."""
        return self._timeline.get_events(since=since, limit=limit)
    
    def to_json(self) -> str:
        """Export session view as JSON."""
        return json.dumps(self.get_snapshot().to_dict(), indent=2)


# =============================================================================
# SESSION VIEW RENDERER
# =============================================================================

class SessionViewRenderer:
    """
    Renders session view to various formats.
    """
    
    def __init__(self, view: SessionView) -> None:
        self._view = view
    
    def render_timeline_text(self, limit: int = 20) -> str:
        """Render timeline as text."""
        events = self._view.get_timeline_events(limit=limit)
        lines = ["═" * 60, "  TIMELINE", "═" * 60]
        
        for event in events:
            time_str = event.time.strftime("%H:%M:%S")
            lines.append(f"  [{time_str}] {event.title}")
        
        lines.append("═" * 60)
        return "\n".join(lines)
    
    def render_agents_text(self) -> str:
        """Render agent states as text."""
        snapshot = self._view.get_snapshot()
        lines = ["═" * 60, "  AGENTS", "═" * 60]
        
        for agent_id, view in snapshot.agent_views.items():
            state_icon = {
                AgentVisualState.IDLE: "○",
                AgentVisualState.RUNNING: "●",
                AgentVisualState.SUCCESS: "✓",
                AgentVisualState.FAILURE: "✗",
                AgentVisualState.BLOCKED: "⊘",
            }.get(view.state, "?")
            
            progress_bar = self._render_progress_bar(view.progress)
            lines.append(f"  {state_icon} {view.name:<20} {progress_bar} {view.progress:.0%}")
        
        lines.append("═" * 60)
        return "\n".join(lines)
    
    def render_closure_text(self) -> str:
        """Render closure status as text."""
        closure = self._view.get_snapshot().closure_view
        lines = ["═" * 60, "  GOVERNANCE CLOSURE", "═" * 60]
        
        def status_icon(status: ClosureStatus) -> str:
            return {
                ClosureStatus.PENDING: "○",
                ClosureStatus.PARTIAL: "◐",
                ClosureStatus.COMPLETE: "●",
                ClosureStatus.FAILED: "✗",
            }.get(status, "?")
        
        lines.append(f"  BER:              {status_icon(closure.ber_status)} ({closure.ber_count})")
        lines.append(f"  PDO:              {status_icon(closure.pdo_status)} ({closure.pdo_count})")
        lines.append(f"  WRAP:             {status_icon(closure.wrap_status)} ({closure.wrap_count})")
        lines.append(f"  POSITIVE_CLOSURE: {'●' if closure.positive_closure else '○'}")
        lines.append(f"  Overall:          {closure.completion_percentage:.0%}")
        lines.append("═" * 60)
        return "\n".join(lines)
    
    def render_metrics_text(self) -> str:
        """Render metrics as text."""
        metrics = self._view.metrics
        lines = ["═" * 60, "  METRICS", "═" * 60]
        
        lines.append(f"  Total Agents:      {metrics.total_agents}")
        lines.append(f"  Completed:         {metrics.completed_agents}")
        lines.append(f"  Failed:            {metrics.failed_agents}")
        lines.append(f"  Total Events:      {metrics.total_events}")
        lines.append(f"  PDO Count:         {metrics.total_pdo_count}")
        lines.append(f"  BER Count:         {metrics.total_ber_count}")
        lines.append(f"  Avg Duration:      {int(metrics.avg_agent_duration_ms)}ms")
        lines.append(f"  Session Duration:  {metrics.session_duration_ms}ms")
        lines.append("═" * 60)
        return "\n".join(lines)
    
    def render_full_dashboard(self) -> str:
        """Render complete dashboard."""
        parts = [
            self.render_timeline_text(),
            "",
            self.render_agents_text(),
            "",
            self.render_closure_text(),
            "",
            self.render_metrics_text(),
        ]
        return "\n".join(parts)
    
    def _render_progress_bar(self, progress: float, width: int = 20) -> str:
        """Render ASCII progress bar."""
        filled = int(progress * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_session_view(session_id: Optional[str] = None) -> SessionView:
    """Create a new session view."""
    if session_id is None:
        session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
    return SessionView(session_id)


def create_renderer(view: SessionView) -> SessionViewRenderer:
    """Create a renderer for a session view."""
    return SessionViewRenderer(view)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version
    "MODULE_VERSION",
    # Constants
    "MAX_TIMELINE_EVENTS",
    "REFRESH_INTERVAL_MS",
    # Enums
    "SessionState",
    "EventType",
    "AgentVisualState",
    "ClosureStatus",
    "ViewMode",
    # Data Classes
    "TimelineEvent",
    "AgentView",
    "ClosureView",
    "MetricPoint",
    "SessionMetrics",
    "SessionSnapshot",
    # Classes
    "TimelineManager",
    "SessionView",
    "SessionViewRenderer",
    # Factory Functions
    "create_session_view",
    "create_renderer",
]
