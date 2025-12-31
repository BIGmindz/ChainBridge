# ═══════════════════════════════════════════════════════════════════════════════
# AML OCC Panel — Read-Only Operator Control Center
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: SONNY (GID-02) / LIRA (GID-09)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML OCC Panel — Operator Control Center for AML Monitoring

PURPOSE:
    Provide read-only visibility into AML system state:
    - Case queue status
    - Tier distribution
    - Decision metrics
    - Guardrail violations
    - Signal patterns

ACCESSIBILITY:
    - WCAG AA compliant data structures
    - Screen reader friendly outputs
    - High contrast color schemes
    - Keyboard navigation support

CONSTRAINTS:
    - READ-ONLY: No mutation operations
    - Real-time data refresh
    - Exportable reports

LANE: PRESENTATION (OCC)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class PanelType(Enum):
    """Type of OCC panel."""

    QUEUE_STATUS = "QUEUE_STATUS"
    TIER_DISTRIBUTION = "TIER_DISTRIBUTION"
    DECISION_METRICS = "DECISION_METRICS"
    GUARDRAIL_STATUS = "GUARDRAIL_STATUS"
    SIGNAL_PATTERNS = "SIGNAL_PATTERNS"
    CASE_TIMELINE = "CASE_TIMELINE"
    RISK_HEATMAP = "RISK_HEATMAP"


class AlertLevel(Enum):
    """Alert level for panel indicators."""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class MetricTrend(Enum):
    """Trend direction for metrics."""

    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class AccessibilityRole(Enum):
    """ARIA roles for accessibility."""

    STATUS = "status"
    ALERT = "alert"
    LOG = "log"
    REGION = "region"
    TABLE = "table"
    PROGRESSBAR = "progressbar"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PanelMetric:
    """
    Single metric displayed in a panel.

    Includes accessibility attributes for screen readers.
    """

    metric_id: str
    label: str
    value: Any
    unit: str
    trend: MetricTrend
    trend_value: float
    alert_level: AlertLevel
    aria_label: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "trend": self.trend.value,
            "trend_value": self.trend_value,
            "alert_level": self.alert_level.value,
            "aria_label": self.aria_label,
            "description": self.description,
        }


@dataclass
class QueueItem:
    """
    Item in the case queue display.

    Represents a case awaiting action.
    """

    case_id: str
    entity_name: str
    tier: str
    age_hours: float
    alert_count: int
    priority_score: float
    status: str
    assignee: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "entity_name": self.entity_name,
            "tier": self.tier,
            "age_hours": self.age_hours,
            "alert_count": self.alert_count,
            "priority_score": self.priority_score,
            "status": self.status,
            "assignee": self.assignee,
        }


@dataclass
class TimelineEvent:
    """
    Event in a case timeline.

    Shows chronological case history.
    """

    event_id: str
    timestamp: str
    event_type: str
    description: str
    actor: str
    icon: str  # Icon name for visual display

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "description": self.description,
            "actor": self.actor,
            "icon": self.icon,
        }


@dataclass
class PanelConfig:
    """
    Configuration for an OCC panel.

    Defines display and accessibility settings.
    """

    panel_id: str
    panel_type: PanelType
    title: str
    refresh_seconds: int
    aria_role: AccessibilityRole
    aria_label: str
    visible: bool = True
    collapsed: bool = False
    position: Dict[str, int] = field(default_factory=lambda: {"row": 0, "col": 0})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "panel_type": self.panel_type.value,
            "title": self.title,
            "refresh_seconds": self.refresh_seconds,
            "aria_role": self.aria_role.value,
            "aria_label": self.aria_label,
            "visible": self.visible,
            "collapsed": self.collapsed,
            "position": self.position,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PANEL DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class QueueStatusPanel:
    """
    Panel showing case queue status.

    Displays pending cases by tier and age.
    """

    config: PanelConfig
    total_cases: int
    by_tier: Dict[str, int]
    by_age: Dict[str, int]  # "< 1h", "1-4h", "4-24h", "> 24h"
    oldest_case_hours: float
    queue_items: List[QueueItem]
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "total_cases": self.total_cases,
            "by_tier": self.by_tier,
            "by_age": self.by_age,
            "oldest_case_hours": self.oldest_case_hours,
            "queue_items": [item.to_dict() for item in self.queue_items],
            "updated_at": self.updated_at,
        }


@dataclass
class TierDistributionPanel:
    """
    Panel showing tier distribution.

    Displays case counts and percentages by tier.
    """

    config: PanelConfig
    distribution: Dict[str, int]  # TIER_0, TIER_1, TIER_2, TIER_3, TIER_SAR
    percentages: Dict[str, float]
    auto_clearable_count: int
    requires_review_count: int
    trend: Dict[str, MetricTrend]  # Trend by tier
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "distribution": self.distribution,
            "percentages": self.percentages,
            "auto_clearable_count": self.auto_clearable_count,
            "requires_review_count": self.requires_review_count,
            "trend": {k: v.value for k, v in self.trend.items()},
            "updated_at": self.updated_at,
        }


@dataclass
class DecisionMetricsPanel:
    """
    Panel showing decision metrics.

    Displays clearance rates, accuracy, and timing.
    """

    config: PanelConfig
    metrics: List[PanelMetric]
    decisions_today: int
    auto_cleared_today: int
    escalated_today: int
    average_decision_time_minutes: float
    false_positive_rate: float
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "metrics": [m.to_dict() for m in self.metrics],
            "decisions_today": self.decisions_today,
            "auto_cleared_today": self.auto_cleared_today,
            "escalated_today": self.escalated_today,
            "average_decision_time_minutes": self.average_decision_time_minutes,
            "false_positive_rate": self.false_positive_rate,
            "updated_at": self.updated_at,
        }


@dataclass
class GuardrailStatusPanel:
    """
    Panel showing guardrail status.

    Displays active guardrails and recent violations.
    """

    config: PanelConfig
    active_guardrails: int
    violations_today: int
    violations_by_guardrail: Dict[str, int]
    blocked_actions_today: int
    recent_violations: List[Dict[str, Any]]
    alert_level: AlertLevel
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "active_guardrails": self.active_guardrails,
            "violations_today": self.violations_today,
            "violations_by_guardrail": self.violations_by_guardrail,
            "blocked_actions_today": self.blocked_actions_today,
            "recent_violations": self.recent_violations,
            "alert_level": self.alert_level.value,
            "updated_at": self.updated_at,
        }


@dataclass
class SignalPatternsPanel:
    """
    Panel showing detected signal patterns.

    Displays pattern detection summary.
    """

    config: PanelConfig
    total_signals: int
    signals_by_type: Dict[str, int]
    signals_by_severity: Dict[str, int]
    top_patterns: List[Dict[str, Any]]
    actionable_signals: int
    suppressed_signals: int
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "total_signals": self.total_signals,
            "signals_by_type": self.signals_by_type,
            "signals_by_severity": self.signals_by_severity,
            "top_patterns": self.top_patterns,
            "actionable_signals": self.actionable_signals,
            "suppressed_signals": self.suppressed_signals,
            "updated_at": self.updated_at,
        }


@dataclass
class CaseTimelinePanel:
    """
    Panel showing case timeline.

    Displays chronological events for a specific case.
    """

    config: PanelConfig
    case_id: str
    entity_name: str
    tier: str
    status: str
    events: List[TimelineEvent]
    created_at: str
    last_activity: str
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "case_id": self.case_id,
            "entity_name": self.entity_name,
            "tier": self.tier,
            "status": self.status,
            "events": [e.to_dict() for e in self.events],
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OCC PANEL SERVICE
# ═══════════════════════════════════════════════════════════════════════════════


class AMLOCCPanel:
    """
    AML Operator Control Center panel service.

    Provides:
    - Panel configuration management
    - Data aggregation for panels
    - Accessibility-compliant outputs
    - Export functionality

    NOTE: This is READ-ONLY. No mutation operations.
    """

    def __init__(self) -> None:
        self._panel_configs: Dict[str, PanelConfig] = {}
        self._setup_default_panels()

    def _setup_default_panels(self) -> None:
        """Setup default panel configurations."""
        defaults = [
            PanelConfig(
                panel_id="queue-status",
                panel_type=PanelType.QUEUE_STATUS,
                title="Case Queue",
                refresh_seconds=30,
                aria_role=AccessibilityRole.STATUS,
                aria_label="AML case queue status showing pending cases by tier",
                position={"row": 0, "col": 0},
            ),
            PanelConfig(
                panel_id="tier-distribution",
                panel_type=PanelType.TIER_DISTRIBUTION,
                title="Tier Distribution",
                refresh_seconds=60,
                aria_role=AccessibilityRole.STATUS,
                aria_label="Distribution of cases across tier classifications",
                position={"row": 0, "col": 1},
            ),
            PanelConfig(
                panel_id="decision-metrics",
                panel_type=PanelType.DECISION_METRICS,
                title="Decision Metrics",
                refresh_seconds=60,
                aria_role=AccessibilityRole.STATUS,
                aria_label="Key performance metrics for AML decisions",
                position={"row": 1, "col": 0},
            ),
            PanelConfig(
                panel_id="guardrail-status",
                panel_type=PanelType.GUARDRAIL_STATUS,
                title="Guardrail Status",
                refresh_seconds=15,
                aria_role=AccessibilityRole.ALERT,
                aria_label="Status of AML guardrails and recent violations",
                position={"row": 1, "col": 1},
            ),
            PanelConfig(
                panel_id="signal-patterns",
                panel_type=PanelType.SIGNAL_PATTERNS,
                title="Signal Patterns",
                refresh_seconds=60,
                aria_role=AccessibilityRole.LOG,
                aria_label="Detected behavioral patterns and signals",
                position={"row": 2, "col": 0},
            ),
        ]

        for config in defaults:
            self._panel_configs[config.panel_id] = config

    # ───────────────────────────────────────────────────────────────────────────
    # PANEL DATA BUILDERS
    # ───────────────────────────────────────────────────────────────────────────

    def build_queue_status_panel(
        self,
        cases: List[Dict[str, Any]],
    ) -> QueueStatusPanel:
        """
        Build queue status panel from case data.

        Args:
            cases: List of case dictionaries with tier, age, status

        Returns:
            Populated QueueStatusPanel
        """
        config = self._panel_configs.get("queue-status")
        if config is None:
            config = PanelConfig(
                panel_id="queue-status",
                panel_type=PanelType.QUEUE_STATUS,
                title="Case Queue",
                refresh_seconds=30,
                aria_role=AccessibilityRole.STATUS,
                aria_label="AML case queue status",
            )

        # Aggregate by tier
        by_tier: Dict[str, int] = {"TIER_0": 0, "TIER_1": 0, "TIER_2": 0, "TIER_3": 0, "TIER_SAR": 0}
        for case in cases:
            tier = case.get("tier", "TIER_0")
            if tier in by_tier:
                by_tier[tier] += 1

        # Aggregate by age
        by_age: Dict[str, int] = {"< 1h": 0, "1-4h": 0, "4-24h": 0, "> 24h": 0}
        oldest_hours = 0.0
        for case in cases:
            age = case.get("age_hours", 0)
            oldest_hours = max(oldest_hours, age)
            if age < 1:
                by_age["< 1h"] += 1
            elif age < 4:
                by_age["1-4h"] += 1
            elif age < 24:
                by_age["4-24h"] += 1
            else:
                by_age["> 24h"] += 1

        # Build queue items
        queue_items = [
            QueueItem(
                case_id=c.get("case_id", ""),
                entity_name=c.get("entity_name", "Unknown"),
                tier=c.get("tier", "TIER_0"),
                age_hours=c.get("age_hours", 0),
                alert_count=c.get("alert_count", 0),
                priority_score=c.get("priority_score", 0.0),
                status=c.get("status", "OPEN"),
                assignee=c.get("assignee"),
            )
            for c in cases[:50]  # Limit to 50 items
        ]

        return QueueStatusPanel(
            config=config,
            total_cases=len(cases),
            by_tier=by_tier,
            by_age=by_age,
            oldest_case_hours=oldest_hours,
            queue_items=queue_items,
        )

    def build_tier_distribution_panel(
        self,
        distribution: Dict[str, int],
    ) -> TierDistributionPanel:
        """Build tier distribution panel."""
        config = self._panel_configs.get("tier-distribution")
        if config is None:
            config = PanelConfig(
                panel_id="tier-distribution",
                panel_type=PanelType.TIER_DISTRIBUTION,
                title="Tier Distribution",
                refresh_seconds=60,
                aria_role=AccessibilityRole.STATUS,
                aria_label="Tier distribution",
            )

        total = sum(distribution.values())
        percentages = {
            tier: (count / total * 100) if total > 0 else 0.0
            for tier, count in distribution.items()
        }

        auto_clearable = distribution.get("TIER_0", 0) + distribution.get("TIER_1", 0)
        requires_review = total - auto_clearable

        return TierDistributionPanel(
            config=config,
            distribution=distribution,
            percentages=percentages,
            auto_clearable_count=auto_clearable,
            requires_review_count=requires_review,
            trend={tier: MetricTrend.STABLE for tier in distribution},
        )

    def build_decision_metrics_panel(
        self,
        decisions_today: int,
        auto_cleared: int,
        escalated: int,
        avg_decision_time: float,
        false_positive_rate: float,
    ) -> DecisionMetricsPanel:
        """Build decision metrics panel."""
        config = self._panel_configs.get("decision-metrics")
        if config is None:
            config = PanelConfig(
                panel_id="decision-metrics",
                panel_type=PanelType.DECISION_METRICS,
                title="Decision Metrics",
                refresh_seconds=60,
                aria_role=AccessibilityRole.STATUS,
                aria_label="Decision metrics",
            )

        metrics = [
            PanelMetric(
                metric_id="decisions-today",
                label="Decisions Today",
                value=decisions_today,
                unit="cases",
                trend=MetricTrend.STABLE,
                trend_value=0.0,
                alert_level=AlertLevel.NORMAL,
                aria_label=f"{decisions_today} decisions made today",
                description="Total decisions (auto-clear + escalations)",
            ),
            PanelMetric(
                metric_id="auto-clear-rate",
                label="Auto-Clear Rate",
                value=round(auto_cleared / decisions_today * 100, 1) if decisions_today > 0 else 0,
                unit="%",
                trend=MetricTrend.STABLE,
                trend_value=0.0,
                alert_level=AlertLevel.NORMAL,
                aria_label=f"{auto_cleared} of {decisions_today} cases auto-cleared",
                description="Percentage of cases auto-cleared",
            ),
            PanelMetric(
                metric_id="avg-decision-time",
                label="Avg Decision Time",
                value=round(avg_decision_time, 1),
                unit="min",
                trend=MetricTrend.STABLE,
                trend_value=0.0,
                alert_level=AlertLevel.NORMAL if avg_decision_time < 30 else AlertLevel.WARNING,
                aria_label=f"Average decision time is {avg_decision_time:.1f} minutes",
                description="Average time from case creation to decision",
            ),
            PanelMetric(
                metric_id="fp-rate",
                label="FP Rate",
                value=round(false_positive_rate * 100, 2),
                unit="%",
                trend=MetricTrend.STABLE,
                trend_value=0.0,
                alert_level=AlertLevel.NORMAL if false_positive_rate > 0.9 else AlertLevel.WARNING,
                aria_label=f"False positive rate is {false_positive_rate * 100:.2f}%",
                description="Rate of alerts that are false positives",
            ),
        ]

        return DecisionMetricsPanel(
            config=config,
            metrics=metrics,
            decisions_today=decisions_today,
            auto_cleared_today=auto_cleared,
            escalated_today=escalated,
            average_decision_time_minutes=avg_decision_time,
            false_positive_rate=false_positive_rate,
        )

    def build_guardrail_status_panel(
        self,
        active_guardrails: int,
        violations_today: int,
        violations_by_guardrail: Dict[str, int],
        blocked_actions: int,
        recent_violations: List[Dict[str, Any]],
    ) -> GuardrailStatusPanel:
        """Build guardrail status panel."""
        config = self._panel_configs.get("guardrail-status")
        if config is None:
            config = PanelConfig(
                panel_id="guardrail-status",
                panel_type=PanelType.GUARDRAIL_STATUS,
                title="Guardrail Status",
                refresh_seconds=15,
                aria_role=AccessibilityRole.ALERT,
                aria_label="Guardrail status",
            )

        # Determine alert level
        alert_level = AlertLevel.NORMAL
        if violations_today > 0:
            alert_level = AlertLevel.WARNING
        if blocked_actions > 5:
            alert_level = AlertLevel.CRITICAL

        return GuardrailStatusPanel(
            config=config,
            active_guardrails=active_guardrails,
            violations_today=violations_today,
            violations_by_guardrail=violations_by_guardrail,
            blocked_actions_today=blocked_actions,
            recent_violations=recent_violations[:10],
            alert_level=alert_level,
        )

    def build_signal_patterns_panel(
        self,
        total_signals: int,
        by_type: Dict[str, int],
        by_severity: Dict[str, int],
        actionable: int,
        suppressed: int,
    ) -> SignalPatternsPanel:
        """Build signal patterns panel."""
        config = self._panel_configs.get("signal-patterns")
        if config is None:
            config = PanelConfig(
                panel_id="signal-patterns",
                panel_type=PanelType.SIGNAL_PATTERNS,
                title="Signal Patterns",
                refresh_seconds=60,
                aria_role=AccessibilityRole.LOG,
                aria_label="Signal patterns",
            )

        # Build top patterns list
        top_patterns = [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return SignalPatternsPanel(
            config=config,
            total_signals=total_signals,
            signals_by_type=by_type,
            signals_by_severity=by_severity,
            top_patterns=top_patterns,
            actionable_signals=actionable,
            suppressed_signals=suppressed,
        )

    def build_case_timeline_panel(
        self,
        case_id: str,
        entity_name: str,
        tier: str,
        status: str,
        events: List[Dict[str, Any]],
        created_at: str,
    ) -> CaseTimelinePanel:
        """Build case timeline panel."""
        config = PanelConfig(
            panel_id=f"timeline-{case_id}",
            panel_type=PanelType.CASE_TIMELINE,
            title=f"Case Timeline: {case_id}",
            refresh_seconds=30,
            aria_role=AccessibilityRole.LOG,
            aria_label=f"Timeline for case {case_id}",
        )

        timeline_events = [
            TimelineEvent(
                event_id=e.get("event_id", f"evt-{i}"),
                timestamp=e.get("timestamp", ""),
                event_type=e.get("event_type", "UNKNOWN"),
                description=e.get("description", ""),
                actor=e.get("actor", "SYSTEM"),
                icon=e.get("icon", "circle"),
            )
            for i, e in enumerate(events)
        ]

        last_activity = events[-1].get("timestamp", created_at) if events else created_at

        return CaseTimelinePanel(
            config=config,
            case_id=case_id,
            entity_name=entity_name,
            tier=tier,
            status=status,
            events=timeline_events,
            created_at=created_at,
            last_activity=last_activity,
        )

    # ───────────────────────────────────────────────────────────────────────────
    # CONFIGURATION
    # ───────────────────────────────────────────────────────────────────────────

    def get_panel_config(self, panel_id: str) -> Optional[PanelConfig]:
        """Get panel configuration."""
        return self._panel_configs.get(panel_id)

    def list_panel_configs(self) -> List[PanelConfig]:
        """List all panel configurations."""
        return list(self._panel_configs.values())

    def get_dashboard_layout(self) -> Dict[str, Any]:
        """Get full dashboard layout configuration."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "panels": [config.to_dict() for config in self._panel_configs.values()],
            "accessibility": {
                "wcag_level": "AA",
                "high_contrast_supported": True,
                "screen_reader_optimized": True,
                "keyboard_navigation": True,
            },
        }

    # ───────────────────────────────────────────────────────────────────────────
    # EXPORT
    # ───────────────────────────────────────────────────────────────────────────

    def export_panel_data(
        self,
        panel: Any,  # Any of the panel types
        format: str = "json",
    ) -> str:
        """Export panel data in specified format."""
        import json as json_module

        data = panel.to_dict()

        if format == "json":
            return json_module.dumps(data, indent=2)
        elif format == "csv":
            # Simple CSV for tabular data
            lines = []
            for key, value in data.items():
                if not isinstance(value, (dict, list)):
                    lines.append(f"{key},{value}")
            return "\n".join(lines)
        else:
            return str(data)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "PanelType",
    "AlertLevel",
    "MetricTrend",
    "AccessibilityRole",
    # Data Classes
    "PanelMetric",
    "QueueItem",
    "TimelineEvent",
    "PanelConfig",
    # Panel Types
    "QueueStatusPanel",
    "TierDistributionPanel",
    "DecisionMetricsPanel",
    "GuardrailStatusPanel",
    "SignalPatternsPanel",
    "CaseTimelinePanel",
    # Service
    "AMLOCCPanel",
]
