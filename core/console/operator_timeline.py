"""
Operator Console Timeline — Session & Timeline UX Components.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-02 (Sonny) — OPERATOR CONSOLE / SESSION & TIMELINE UX
Deliverable: Timeline Renderer, Session Display, Event Stream, Alert Panel

Features:
- Visual timeline for PAC execution
- Real-time session state display
- Live event feed with filtering
- Operator alerts with escalation
- Quick intervention actions
- Export functionality
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# =============================================================================
# VERSION
# =============================================================================

OPERATOR_TIMELINE_VERSION = "1.0.0"


# =============================================================================
# ENUMS
# =============================================================================

class TimelineEventType(Enum):
    """Types of timeline events."""
    PAC_STARTED = "PAC_STARTED"
    PAC_COMPLETED = "PAC_COMPLETED"
    AGENT_ACTIVATED = "AGENT_ACTIVATED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    WRAP_SUBMITTED = "WRAP_SUBMITTED"
    BER_ISSUED = "BER_ISSUED"
    PDO_SEALED = "PDO_SEALED"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"
    DEPENDENCY_SATISFIED = "DEPENDENCY_SATISFIED"
    RESOURCE_ACQUIRED = "RESOURCE_ACQUIRED"
    ALERT_RAISED = "ALERT_RAISED"
    INTERVENTION_REQUESTED = "INTERVENTION_REQUESTED"


class AgentStatus(Enum):
    """Agent status badges."""
    PENDING = "PENDING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SWAPPED = "SWAPPED"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = 0
    WARNING = 1
    INFO = 2


class AlertState(Enum):
    """Alert states."""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class ExportFormat(Enum):
    """Export formats."""
    JSON = "JSON"
    CSV = "CSV"
    SVG = "SVG"
    PNG = "PNG"
    PDF = "PDF"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TimelineEvent:
    """An event on the timeline."""
    event_id: str
    event_type: TimelineEventType
    timestamp: datetime
    agent_id: Optional[str]
    pac_id: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    related_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "pac_id": self.pac_id,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "related_events": self.related_events,
        }


@dataclass
class TimelineMarker:
    """A marker on the timeline (WRAP, BER, PDO)."""
    marker_id: str
    marker_type: str  # "WRAP", "BER", "PDO"
    timestamp: datetime
    label: str
    agent_id: Optional[str]
    hash_value: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "marker_id": self.marker_id,
            "marker_type": self.marker_type,
            "timestamp": self.timestamp.isoformat(),
            "label": self.label,
            "agent_id": self.agent_id,
            "hash_value": self.hash_value,
            "metadata": self.metadata,
        }


@dataclass
class AgentStatusInfo:
    """Agent status information."""
    agent_id: str
    status: AgentStatus
    progress: float  # 0.0 to 1.0
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    dependencies_satisfied: int
    dependencies_total: int
    blocking_issues: List[str]
    resource_usage: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "dependencies_satisfied": self.dependencies_satisfied,
            "dependencies_total": self.dependencies_total,
            "blocking_issues": self.blocking_issues,
            "resource_usage": self.resource_usage,
        }


@dataclass
class Alert:
    """An operator alert."""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    state: AlertState
    agent_id: Optional[str]
    pac_id: str
    escalation_deadline: Optional[datetime]
    root_cause_group: Optional[str]
    actions_taken: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.name,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "state": self.state.value,
            "agent_id": self.agent_id,
            "pac_id": self.pac_id,
            "escalation_deadline": self.escalation_deadline.isoformat() if self.escalation_deadline else None,
            "root_cause_group": self.root_cause_group,
            "actions_taken": self.actions_taken,
        }


@dataclass
class SessionState:
    """Current session state."""
    session_id: str
    pac_id: str
    started_at: datetime
    agents: Dict[str, AgentStatusInfo]
    active_alerts: List[Alert]
    timeline_events: List[TimelineEvent]
    markers: List[TimelineMarker]
    resource_utilization: Dict[str, float]
    overall_progress: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "pac_id": self.pac_id,
            "started_at": self.started_at.isoformat(),
            "agents": {k: v.to_dict() for k, v in self.agents.items()},
            "active_alerts": [a.to_dict() for a in self.active_alerts],
            "timeline_events_count": len(self.timeline_events),
            "markers_count": len(self.markers),
            "resource_utilization": self.resource_utilization,
            "overall_progress": self.overall_progress,
        }


@dataclass
class QuickAction:
    """A quick action for operator intervention."""
    action_id: str
    action_type: str
    label: str
    target_agent: Optional[str]
    parameters: Dict[str, Any]
    requires_confirmation: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "label": self.label,
            "target_agent": self.target_agent,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation,
        }


# =============================================================================
# TIMELINE RENDERER
# =============================================================================

class TimelineRenderer:
    """
    Visual timeline renderer for PAC execution.
    
    Renders:
    - Agent activation/completion events
    - WRAP submission timestamps
    - BER issuance markers
    - PDO seal points
    - Exportable to JSON/SVG
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: List[TimelineEvent] = []
        self._markers: List[TimelineMarker] = []
        self._lanes: Dict[str, List[TimelineEvent]] = defaultdict(list)  # agent -> events
    
    def add_event(self, event: TimelineEvent) -> None:
        """Add event to timeline."""
        with self._lock:
            self._events.append(event)
            self._events.sort(key=lambda e: e.timestamp)
            
            if event.agent_id:
                self._lanes[event.agent_id].append(event)
                self._lanes[event.agent_id].sort(key=lambda e: e.timestamp)
    
    def add_marker(self, marker: TimelineMarker) -> None:
        """Add marker to timeline."""
        with self._lock:
            self._markers.append(marker)
            self._markers.sort(key=lambda m: m.timestamp)
    
    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> List[TimelineEvent]:
        """Get events within time range."""
        with self._lock:
            return [
                e for e in self._events
                if start <= e.timestamp <= end
            ]
    
    def get_lane_events(self, agent_id: str) -> List[TimelineEvent]:
        """Get events for specific agent lane."""
        with self._lock:
            return self._lanes.get(agent_id, []).copy()
    
    def render_to_json(self) -> str:
        """Render timeline to JSON."""
        with self._lock:
            data = {
                "version": OPERATOR_TIMELINE_VERSION,
                "rendered_at": datetime.now(timezone.utc).isoformat(),
                "events": [e.to_dict() for e in self._events],
                "markers": [m.to_dict() for m in self._markers],
                "lanes": {
                    agent_id: [e.to_dict() for e in events]
                    for agent_id, events in self._lanes.items()
                },
            }
            return json.dumps(data, indent=2)
    
    def render_to_svg(self, width: int = 1200, height: int = 600) -> str:
        """
        Render timeline to SVG.
        
        Returns:
            SVG string
        """
        with self._lock:
            if not self._events:
                return self._empty_svg(width, height)
            
            min_time = min(e.timestamp for e in self._events)
            max_time = max(e.timestamp for e in self._events)
            time_range = (max_time - min_time).total_seconds() or 1
            
            # Build SVG
            svg_parts = [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
                '<style>',
                '  .event-circle { fill: #4CAF50; stroke: #2E7D32; stroke-width: 2; }',
                '  .marker-line { stroke: #F44336; stroke-width: 3; }',
                '  .lane-label { font-family: Arial; font-size: 12px; fill: #333; }',
                '  .time-label { font-family: Arial; font-size: 10px; fill: #666; }',
                '  .wrap-marker { fill: #2196F3; }',
                '  .ber-marker { fill: #FF9800; }',
                '  .pdo-marker { fill: #9C27B0; }',
                '</style>',
                f'<rect width="{width}" height="{height}" fill="#FAFAFA"/>',
            ]
            
            # Draw lanes
            lane_height = (height - 100) / max(len(self._lanes), 1)
            y_offset = 50
            
            for i, (agent_id, events) in enumerate(self._lanes.items()):
                lane_y = y_offset + i * lane_height
                
                # Lane label
                svg_parts.append(
                    f'<text x="10" y="{lane_y + lane_height/2}" class="lane-label">'
                    f'{agent_id}</text>'
                )
                
                # Lane line
                svg_parts.append(
                    f'<line x1="100" y1="{lane_y + lane_height/2}" '
                    f'x2="{width - 50}" y2="{lane_y + lane_height/2}" '
                    f'stroke="#E0E0E0" stroke-width="1"/>'
                )
                
                # Events
                for event in events:
                    t = (event.timestamp - min_time).total_seconds() / time_range
                    x = 100 + t * (width - 150)
                    svg_parts.append(
                        f'<circle cx="{x}" cy="{lane_y + lane_height/2}" '
                        f'r="6" class="event-circle">'
                        f'<title>{event.event_type.value}</title>'
                        f'</circle>'
                    )
            
            # Draw markers
            for marker in self._markers:
                t = (marker.timestamp - min_time).total_seconds() / time_range
                x = 100 + t * (width - 150)
                marker_class = {
                    "WRAP": "wrap-marker",
                    "BER": "ber-marker",
                    "PDO": "pdo-marker",
                }.get(marker.marker_type, "wrap-marker")
                
                svg_parts.append(
                    f'<line x1="{x}" y1="30" x2="{x}" y2="{height - 30}" '
                    f'class="marker-line" stroke-dasharray="5,5"/>'
                )
                svg_parts.append(
                    f'<rect x="{x - 20}" y="10" width="40" height="20" '
                    f'class="{marker_class}" rx="3"/>'
                )
                svg_parts.append(
                    f'<text x="{x}" y="24" text-anchor="middle" '
                    f'fill="white" font-size="10">{marker.marker_type}</text>'
                )
            
            # Time axis
            svg_parts.append(
                f'<text x="100" y="{height - 10}" class="time-label">'
                f'{min_time.strftime("%H:%M:%S")}</text>'
            )
            svg_parts.append(
                f'<text x="{width - 100}" y="{height - 10}" class="time-label">'
                f'{max_time.strftime("%H:%M:%S")}</text>'
            )
            
            svg_parts.append('</svg>')
            return '\n'.join(svg_parts)
    
    def _empty_svg(self, width: int, height: int) -> str:
        """Generate empty SVG."""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f'<rect width="{width}" height="{height}" fill="#FAFAFA"/>'
            f'<text x="{width/2}" y="{height/2}" text-anchor="middle" '
            f'font-family="Arial" fill="#999">No events</text>'
            '</svg>'
        )
    
    def get_timeline_stats(self) -> Dict[str, Any]:
        """Get timeline statistics."""
        with self._lock:
            event_counts: Dict[str, int] = defaultdict(int)
            for event in self._events:
                event_counts[event.event_type.value] += 1
            
            marker_counts: Dict[str, int] = defaultdict(int)
            for marker in self._markers:
                marker_counts[marker.marker_type] += 1
            
            return {
                "total_events": len(self._events),
                "total_markers": len(self._markers),
                "lanes": len(self._lanes),
                "event_counts": dict(event_counts),
                "marker_counts": dict(marker_counts),
            }


# =============================================================================
# SESSION STATE DISPLAY
# =============================================================================

class SessionStateDisplay:
    """
    Real-time session state display.
    
    Shows:
    - Active agents with status badges
    - Dependency satisfaction indicators
    - Blocking issues highlighter
    - Resource utilization gauges
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._agents: Dict[str, AgentStatusInfo] = {}
        self._resource_pools: Dict[str, Tuple[float, float]] = {}  # type -> (used, total)
        self._blocking_chains: Dict[str, Set[str]] = defaultdict(set)
    
    def update_agent(self, info: AgentStatusInfo) -> None:
        """Update agent status."""
        with self._lock:
            self._agents[info.agent_id] = info
    
    def update_resource(self, resource_type: str, used: float, total: float) -> None:
        """Update resource utilization."""
        with self._lock:
            self._resource_pools[resource_type] = (used, total)
    
    def set_blocking(self, blocked_agent: str, blocking_agent: str) -> None:
        """Mark agent as blocked."""
        with self._lock:
            self._blocking_chains[blocked_agent].add(blocking_agent)
    
    def clear_blocking(self, blocked_agent: str, blocking_agent: str) -> None:
        """Clear blocking relationship."""
        with self._lock:
            self._blocking_chains[blocked_agent].discard(blocking_agent)
    
    def get_active_agents(self) -> List[AgentStatusInfo]:
        """Get agents that are currently executing."""
        with self._lock:
            return [
                info for info in self._agents.values()
                if info.status == AgentStatus.EXECUTING
            ]
    
    def get_blocked_agents(self) -> List[Tuple[str, Set[str]]]:
        """Get blocked agents and their blockers."""
        with self._lock:
            return [
                (agent_id, blockers.copy())
                for agent_id, blockers in self._blocking_chains.items()
                if blockers
            ]
    
    def get_resource_gauges(self) -> Dict[str, Dict[str, float]]:
        """Get resource utilization gauges."""
        with self._lock:
            gauges = {}
            for resource_type, (used, total) in self._resource_pools.items():
                gauges[resource_type] = {
                    "used": used,
                    "total": total,
                    "utilization": used / total if total > 0 else 0,
                }
            return gauges
    
    def get_dependency_status(self, agent_id: str) -> Dict[str, Any]:
        """Get dependency satisfaction status for agent."""
        with self._lock:
            info = self._agents.get(agent_id)
            if not info:
                return {"satisfied": 0, "total": 0, "ratio": 0}
            
            return {
                "satisfied": info.dependencies_satisfied,
                "total": info.dependencies_total,
                "ratio": (
                    info.dependencies_satisfied / info.dependencies_total
                    if info.dependencies_total > 0 else 1.0
                ),
            }
    
    def render_summary(self) -> Dict[str, Any]:
        """Render session state summary."""
        with self._lock:
            status_counts: Dict[str, int] = defaultdict(int)
            for info in self._agents.values():
                status_counts[info.status.value] += 1
            
            total_progress = sum(
                info.progress for info in self._agents.values()
            ) / max(len(self._agents), 1)
            
            return {
                "agent_count": len(self._agents),
                "status_counts": dict(status_counts),
                "blocked_count": len([b for b in self._blocking_chains.values() if b]),
                "overall_progress": total_progress,
                "resource_gauges": self.get_resource_gauges(),
                "agents": [info.to_dict() for info in self._agents.values()],
            }


# =============================================================================
# EVENT STREAM
# =============================================================================

class EventStream:
    """
    Live event feed with filtering.
    
    Features:
    - Filterable by agent/event type
    - Severity coloring
    - Timestamp normalization
    - Infinite scroll support
    """
    
    def __init__(self, max_events: int = 10000) -> None:
        self._lock = threading.RLock()
        self._events: List[TimelineEvent] = []
        self._max_events = max_events
        self._listeners: List[Callable[[TimelineEvent], None]] = []
    
    def push(self, event: TimelineEvent) -> None:
        """Push event to stream."""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
            
            for listener in self._listeners:
                try:
                    listener(event)
                except Exception:
                    pass
    
    def subscribe(self, callback: Callable[[TimelineEvent], None]) -> None:
        """Subscribe to event stream."""
        with self._lock:
            self._listeners.append(callback)
    
    def unsubscribe(self, callback: Callable[[TimelineEvent], None]) -> None:
        """Unsubscribe from event stream."""
        with self._lock:
            self._listeners = [l for l in self._listeners if l != callback]
    
    def query(
        self,
        agent_ids: Optional[Set[str]] = None,
        event_types: Optional[Set[TimelineEventType]] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TimelineEvent]:
        """
        Query events with filters.
        
        Args:
            agent_ids: Filter by agent IDs
            event_types: Filter by event types
            since: Only events after this time
            limit: Max events to return
            offset: Offset for pagination
            
        Returns:
            Filtered events
        """
        with self._lock:
            filtered = self._events
            
            if agent_ids:
                filtered = [e for e in filtered if e.agent_id in agent_ids]
            
            if event_types:
                filtered = [e for e in filtered if e.event_type in event_types]
            
            if since:
                filtered = [e for e in filtered if e.timestamp >= since]
            
            return filtered[offset:offset + limit]
    
    def get_severity_color(self, event: TimelineEvent) -> str:
        """Get color for event based on type."""
        severity_colors = {
            TimelineEventType.AGENT_FAILED: "#F44336",  # Red
            TimelineEventType.ALERT_RAISED: "#FF9800",  # Orange
            TimelineEventType.INTERVENTION_REQUESTED: "#FF5722",  # Deep Orange
            TimelineEventType.PAC_COMPLETED: "#4CAF50",  # Green
            TimelineEventType.WRAP_SUBMITTED: "#2196F3",  # Blue
            TimelineEventType.BER_ISSUED: "#9C27B0",  # Purple
            TimelineEventType.PDO_SEALED: "#673AB7",  # Deep Purple
        }
        return severity_colors.get(event.event_type, "#9E9E9E")  # Grey default
    
    def export_to_csv(self) -> str:
        """Export events to CSV format."""
        with self._lock:
            lines = ["event_id,event_type,timestamp,agent_id,pac_id"]
            for event in self._events:
                lines.append(
                    f'{event.event_id},{event.event_type.value},'
                    f'{event.timestamp.isoformat()},{event.agent_id or ""},'
                    f'{event.pac_id}'
                )
            return '\n'.join(lines)


# =============================================================================
# ALERT PANEL
# =============================================================================

class AlertPanel:
    """
    Operator alert panel.
    
    Features:
    - Alert severity levels
    - Acknowledgment tracking
    - Escalation timers
    - Alert grouping by root cause
    """
    
    DEFAULT_ESCALATION_MINUTES = {
        AlertSeverity.CRITICAL: 5,
        AlertSeverity.WARNING: 15,
        AlertSeverity.INFO: 60,
    }
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._alerts: Dict[str, Alert] = {}
        self._root_cause_groups: Dict[str, Set[str]] = defaultdict(set)
    
    def raise_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        pac_id: str,
        agent_id: Optional[str] = None,
        root_cause_group: Optional[str] = None,
    ) -> Alert:
        """Raise a new alert."""
        with self._lock:
            now = datetime.now(timezone.utc)
            escalation_minutes = self.DEFAULT_ESCALATION_MINUTES.get(severity, 60)
            
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                severity=severity,
                title=title,
                message=message,
                created_at=now,
                acknowledged_at=None,
                resolved_at=None,
                state=AlertState.ACTIVE,
                agent_id=agent_id,
                pac_id=pac_id,
                escalation_deadline=now + timedelta(minutes=escalation_minutes),
                root_cause_group=root_cause_group,
            )
            
            self._alerts[alert.alert_id] = alert
            
            if root_cause_group:
                self._root_cause_groups[root_cause_group].add(alert.alert_id)
            
            return alert
    
    def acknowledge(self, alert_id: str, operator: str = "operator") -> bool:
        """Acknowledge an alert."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert or alert.state != AlertState.ACTIVE:
                return False
            
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.state = AlertState.ACKNOWLEDGED
            alert.actions_taken.append(f"Acknowledged by {operator}")
            return True
    
    def resolve(self, alert_id: str, resolution: str = "") -> bool:
        """Resolve an alert."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert or alert.state == AlertState.RESOLVED:
                return False
            
            alert.resolved_at = datetime.now(timezone.utc)
            alert.state = AlertState.RESOLVED
            if resolution:
                alert.actions_taken.append(f"Resolved: {resolution}")
            return True
    
    def escalate(self, alert_id: str, reason: str = "") -> bool:
        """Escalate an alert."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert or alert.state == AlertState.RESOLVED:
                return False
            
            alert.state = AlertState.ESCALATED
            alert.actions_taken.append(f"Escalated: {reason or 'Manual escalation'}")
            return True
    
    def get_active_alerts(self) -> List[Alert]:
        """Get active (unresolved) alerts."""
        with self._lock:
            return [
                alert for alert in self._alerts.values()
                if alert.state in (AlertState.ACTIVE, AlertState.ACKNOWLEDGED, AlertState.ESCALATED)
            ]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        with self._lock:
            return [
                alert for alert in self._alerts.values()
                if alert.severity == severity and alert.state != AlertState.RESOLVED
            ]
    
    def get_alerts_by_root_cause(self, root_cause: str) -> List[Alert]:
        """Get alerts grouped by root cause."""
        with self._lock:
            alert_ids = self._root_cause_groups.get(root_cause, set())
            return [
                self._alerts[aid] for aid in alert_ids
                if aid in self._alerts
            ]
    
    def check_escalations(self) -> List[Alert]:
        """Check for alerts past escalation deadline."""
        with self._lock:
            now = datetime.now(timezone.utc)
            needs_escalation = []
            
            for alert in self._alerts.values():
                if alert.state == AlertState.ACTIVE:
                    if alert.escalation_deadline and now > alert.escalation_deadline:
                        alert.state = AlertState.ESCALATED
                        alert.actions_taken.append("Auto-escalated: deadline exceeded")
                        needs_escalation.append(alert)
            
            return needs_escalation
    
    def get_summary(self) -> Dict[str, Any]:
        """Get alert panel summary."""
        with self._lock:
            by_severity: Dict[str, int] = defaultdict(int)
            by_state: Dict[str, int] = defaultdict(int)
            
            for alert in self._alerts.values():
                by_severity[alert.severity.name] += 1
                by_state[alert.state.value] += 1
            
            return {
                "total_alerts": len(self._alerts),
                "by_severity": dict(by_severity),
                "by_state": dict(by_state),
                "root_cause_groups": len(self._root_cause_groups),
            }


# =============================================================================
# QUICK ACTIONS
# =============================================================================

class QuickActions:
    """
    Quick operator intervention actions.
    
    Supports:
    - Agent restart
    - Priority override
    - Manual checkpoint trigger
    - Emergency session termination
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pending_actions: Dict[str, QuickAction] = {}
        self._action_history: List[Dict[str, Any]] = []
        self._handlers: Dict[str, Callable[[QuickAction], bool]] = {}
    
    def register_handler(
        self,
        action_type: str,
        handler: Callable[[QuickAction], bool],
    ) -> None:
        """Register action handler."""
        with self._lock:
            self._handlers[action_type] = handler
    
    def create_restart_action(self, agent_id: str) -> QuickAction:
        """Create agent restart action."""
        return QuickAction(
            action_id=str(uuid.uuid4()),
            action_type="RESTART_AGENT",
            label=f"Restart {agent_id}",
            target_agent=agent_id,
            parameters={"preserve_state": True},
            requires_confirmation=True,
        )
    
    def create_priority_override(
        self,
        agent_id: str,
        new_priority: str,
    ) -> QuickAction:
        """Create priority override action."""
        return QuickAction(
            action_id=str(uuid.uuid4()),
            action_type="PRIORITY_OVERRIDE",
            label=f"Set {agent_id} to {new_priority}",
            target_agent=agent_id,
            parameters={"new_priority": new_priority},
            requires_confirmation=False,
        )
    
    def create_checkpoint_action(self) -> QuickAction:
        """Create manual checkpoint action."""
        return QuickAction(
            action_id=str(uuid.uuid4()),
            action_type="MANUAL_CHECKPOINT",
            label="Create Checkpoint",
            target_agent=None,
            parameters={},
            requires_confirmation=False,
        )
    
    def create_terminate_action(self, reason: str = "") -> QuickAction:
        """Create emergency termination action."""
        return QuickAction(
            action_id=str(uuid.uuid4()),
            action_type="EMERGENCY_TERMINATE",
            label="Emergency Terminate Session",
            target_agent=None,
            parameters={"reason": reason},
            requires_confirmation=True,
        )
    
    def queue_action(self, action: QuickAction) -> str:
        """Queue action for execution."""
        with self._lock:
            self._pending_actions[action.action_id] = action
            return action.action_id
    
    def execute_action(
        self,
        action_id: str,
        confirmed: bool = False,
    ) -> Tuple[bool, str]:
        """
        Execute a queued action.
        
        Returns:
            Tuple of (success, message)
        """
        with self._lock:
            action = self._pending_actions.get(action_id)
            if not action:
                return False, "Action not found"
            
            if action.requires_confirmation and not confirmed:
                return False, "Action requires confirmation"
            
            handler = self._handlers.get(action.action_type)
            if not handler:
                return False, f"No handler for {action.action_type}"
            
            try:
                success = handler(action)
                self._action_history.append({
                    "action": action.to_dict(),
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "success": success,
                })
                del self._pending_actions[action_id]
                return success, "Action executed"
            except Exception as e:
                return False, str(e)
    
    def get_available_actions(self, agent_id: Optional[str] = None) -> List[QuickAction]:
        """Get available actions for context."""
        actions = [
            self.create_checkpoint_action(),
            self.create_terminate_action(),
        ]
        
        if agent_id:
            actions.extend([
                self.create_restart_action(agent_id),
                self.create_priority_override(agent_id, "CRITICAL"),
            ])
        
        return actions
    
    def get_action_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent action history."""
        with self._lock:
            return self._action_history[-limit:]


# =============================================================================
# EXPORT FUNCTIONALITY
# =============================================================================

class ExportManager:
    """
    Export functionality for timeline and session data.
    
    Formats:
    - Timeline to PNG/SVG
    - Session log to PDF (data only)
    - Event stream to CSV
    """
    
    def __init__(
        self,
        timeline: TimelineRenderer,
        session_display: SessionStateDisplay,
        event_stream: EventStream,
    ) -> None:
        self._timeline = timeline
        self._session_display = session_display
        self._event_stream = event_stream
    
    def export_timeline_json(self) -> str:
        """Export timeline to JSON."""
        return self._timeline.render_to_json()
    
    def export_timeline_svg(self, width: int = 1200, height: int = 600) -> str:
        """Export timeline to SVG."""
        return self._timeline.render_to_svg(width, height)
    
    def export_events_csv(self) -> str:
        """Export events to CSV."""
        return self._event_stream.export_to_csv()
    
    def export_session_json(self) -> str:
        """Export session state to JSON."""
        summary = self._session_display.render_summary()
        return json.dumps(summary, indent=2)
    
    def export_full_report(self) -> Dict[str, Any]:
        """Export full report data."""
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "version": OPERATOR_TIMELINE_VERSION,
            "timeline_stats": self._timeline.get_timeline_stats(),
            "session_summary": self._session_display.render_summary(),
            "events_csv": self._event_stream.export_to_csv(),
        }


# =============================================================================
# WRAP HASH COMPUTATION
# =============================================================================

def compute_wrap_hash() -> str:
    """Compute WRAP hash for GID-02 deliverable."""
    content = f"GID-02:operator_timeline:v{OPERATOR_TIMELINE_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "OPERATOR_TIMELINE_VERSION",
    "TimelineEventType",
    "AgentStatus",
    "AlertSeverity",
    "AlertState",
    "ExportFormat",
    "TimelineEvent",
    "TimelineMarker",
    "AgentStatusInfo",
    "Alert",
    "SessionState",
    "QuickAction",
    "TimelineRenderer",
    "SessionStateDisplay",
    "EventStream",
    "AlertPanel",
    "QuickActions",
    "ExportManager",
    "compute_wrap_hash",
]
