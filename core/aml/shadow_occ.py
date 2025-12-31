# ═══════════════════════════════════════════════════════════════════════════════
# AML Shadow OCC Views (SHADOW MODE)
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# Agent: SONNY (GID-02) / LIRA (GID-09)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Shadow OCC Views — Read-Only Operator Views for Shadow Pilot

PURPOSE:
    Render read-only OCC views for shadow pilot monitoring:
    - Case queue display
    - Evidence summaries
    - Decision tracking
    - Pilot metrics dashboard

CONSTRAINTS:
    - READ-ONLY: No mutation operations
    - SHADOW MODE: No production data
    - WCAG AA compliant structures

LANE: PRESENTATION (SHADOW OCC)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.occ.aml_panel import (
    AccessibilityRole,
    AlertLevel,
    MetricTrend,
    PanelConfig,
    PanelMetric,
    PanelType,
    QueueItem,
    TimelineEvent,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW VIEW ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowViewType(Enum):
    """Type of shadow OCC view."""

    PILOT_DASHBOARD = "PILOT_DASHBOARD"
    CASE_QUEUE = "CASE_QUEUE"
    EVIDENCE_PANEL = "EVIDENCE_PANEL"
    DECISION_LOG = "DECISION_LOG"
    TIER_BREAKDOWN = "TIER_BREAKDOWN"
    SCENARIO_RESULTS = "SCENARIO_RESULTS"
    GUARDRAIL_MONITOR = "GUARDRAIL_MONITOR"


class ViewRefreshMode(Enum):
    """View refresh mode."""

    MANUAL = "MANUAL"  # Manual refresh only
    POLLED = "POLLED"  # Periodic polling
    STREAMING = "STREAMING"  # Real-time stream


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ShadowCaseView:
    """
    Read-only view of a shadow case.

    Displays case information for monitoring.
    """

    case_id: str
    entity_name: str
    tier: str
    status: str
    scenario: str
    created_at: str
    alert_count: int = 0
    evidence_count: int = 0
    decision: Optional[str] = None
    decision_confidence: float = 0.0
    escalation_target: Optional[str] = None
    aria_label: str = ""

    def __post_init__(self) -> None:
        if not self.aria_label:
            self.aria_label = f"Case {self.case_id}: {self.entity_name}, Tier {self.tier}, Status {self.status}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "entity_name": self.entity_name,
            "tier": self.tier,
            "status": self.status,
            "scenario": self.scenario,
            "created_at": self.created_at,
            "alert_count": self.alert_count,
            "evidence_count": self.evidence_count,
            "decision": self.decision,
            "decision_confidence": self.decision_confidence,
            "escalation_target": self.escalation_target,
            "aria_label": self.aria_label,
        }


@dataclass
class ShadowEvidenceView:
    """
    Read-only view of case evidence.

    Displays evidence collected for a case.
    """

    evidence_id: str
    case_id: str
    evidence_type: str
    description: str
    source: str
    collected_at: str
    content_summary: str
    risk_contribution: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "case_id": self.case_id,
            "evidence_type": self.evidence_type,
            "description": self.description,
            "source": self.source,
            "collected_at": self.collected_at,
            "content_summary": self.content_summary,
            "risk_contribution": self.risk_contribution,
        }


@dataclass
class ShadowDecisionView:
    """
    Read-only view of a case decision.

    Displays decision outcome and rationale.
    """

    decision_id: str
    case_id: str
    outcome: str
    confidence: float
    rationale: str
    tier_before: str
    tier_after: str
    decided_at: str
    decided_by: str
    guardrails_checked: List[str] = field(default_factory=list)
    escalated: bool = False
    escalation_target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "tier_before": self.tier_before,
            "tier_after": self.tier_after,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "guardrails_checked": self.guardrails_checked,
            "escalated": self.escalated,
            "escalation_target": self.escalation_target,
        }


@dataclass
class ShadowPilotMetrics:
    """
    Metrics for shadow pilot dashboard.

    Aggregated statistics for pilot monitoring.
    """

    pilot_id: str
    started_at: str
    duration_minutes: float
    scenarios_run: int = 0
    cases_processed: int = 0
    tier0_count: int = 0
    tier1_count: int = 0
    tier2_plus_count: int = 0
    auto_clears: int = 0
    escalations: int = 0
    guardrail_violations: int = 0
    error_count: int = 0

    @property
    def auto_clear_rate(self) -> float:
        """Calculate auto-clear rate."""
        if self.cases_processed == 0:
            return 0.0
        return self.auto_clears / self.cases_processed

    @property
    def escalation_rate(self) -> float:
        """Calculate escalation rate."""
        if self.cases_processed == 0:
            return 0.0
        return self.escalations / self.cases_processed

    @property
    def tier_distribution(self) -> Dict[str, float]:
        """Calculate tier distribution percentages."""
        total = self.tier0_count + self.tier1_count + self.tier2_plus_count
        if total == 0:
            return {"TIER_0": 0.0, "TIER_1": 0.0, "TIER_2+": 0.0}
        return {
            "TIER_0": self.tier0_count / total,
            "TIER_1": self.tier1_count / total,
            "TIER_2+": self.tier2_plus_count / total,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pilot_id": self.pilot_id,
            "started_at": self.started_at,
            "duration_minutes": self.duration_minutes,
            "scenarios_run": self.scenarios_run,
            "cases_processed": self.cases_processed,
            "tier0_count": self.tier0_count,
            "tier1_count": self.tier1_count,
            "tier2_plus_count": self.tier2_plus_count,
            "auto_clears": self.auto_clears,
            "escalations": self.escalations,
            "guardrail_violations": self.guardrail_violations,
            "error_count": self.error_count,
            "auto_clear_rate": self.auto_clear_rate,
            "escalation_rate": self.escalation_rate,
            "tier_distribution": self.tier_distribution,
        }


@dataclass
class ScenarioResultView:
    """
    View of scenario execution results.

    Shows outcome for each test scenario.
    """

    scenario_name: str
    scenario_type: str
    cases_generated: int
    expected_outcome: str
    actual_outcomes: Dict[str, int]  # outcome -> count
    success_rate: float
    failures: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if scenario passed."""
        return self.success_rate >= 1.0 and not self.failures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type,
            "cases_generated": self.cases_generated,
            "expected_outcome": self.expected_outcome,
            "actual_outcomes": self.actual_outcomes,
            "success_rate": self.success_rate,
            "failures": self.failures,
            "passed": self.passed,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW OCC VIEW RENDERER
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowOCCViewRenderer:
    """
    Renderer for shadow pilot OCC views.

    Generates read-only views for monitoring shadow pilot execution.
    All views are WCAG AA compliant structures.
    """

    def __init__(self, pilot_id: str) -> None:
        """
        Initialize renderer.

        Args:
            pilot_id: Shadow pilot identifier
        """
        self._pilot_id = pilot_id
        self._cases: Dict[str, ShadowCaseView] = {}
        self._evidence: Dict[str, List[ShadowEvidenceView]] = {}
        self._decisions: Dict[str, ShadowDecisionView] = {}
        self._metrics = ShadowPilotMetrics(
            pilot_id=pilot_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            duration_minutes=0.0,
        )
        self._shadow_mode = True  # ALWAYS TRUE

    @property
    def is_shadow_mode(self) -> bool:
        """Verify shadow mode is enabled (always true)."""
        return self._shadow_mode

    def register_case(self, case: ShadowCaseView) -> None:
        """Register a case for view tracking."""
        self._cases[case.case_id] = case
        self._metrics.cases_processed += 1

        # Update tier counts
        if case.tier == "TIER_0":
            self._metrics.tier0_count += 1
        elif case.tier == "TIER_1":
            self._metrics.tier1_count += 1
        else:
            self._metrics.tier2_plus_count += 1

    def register_evidence(self, evidence: ShadowEvidenceView) -> None:
        """Register evidence for a case."""
        if evidence.case_id not in self._evidence:
            self._evidence[evidence.case_id] = []
        self._evidence[evidence.case_id].append(evidence)

    def register_decision(self, decision: ShadowDecisionView) -> None:
        """Register a decision."""
        self._decisions[decision.case_id] = decision

        if decision.outcome == "AUTO_CLEAR":
            self._metrics.auto_clears += 1
        if decision.escalated:
            self._metrics.escalations += 1

    def register_guardrail_violation(self) -> None:
        """Register a guardrail violation."""
        self._metrics.guardrail_violations += 1

    def register_error(self) -> None:
        """Register an error."""
        self._metrics.error_count += 1

    def render_pilot_dashboard(self) -> Dict[str, Any]:
        """
        Render the main pilot dashboard view.

        Returns:
            Dashboard view data
        """
        # Update duration
        start_time = datetime.fromisoformat(self._metrics.started_at.replace("Z", "+00:00"))
        duration = datetime.now(timezone.utc) - start_time
        self._metrics.duration_minutes = duration.total_seconds() / 60

        # Build metrics panels
        metrics = [
            PanelMetric(
                metric_id="cases_processed",
                label="Cases Processed",
                value=self._metrics.cases_processed,
                unit="cases",
                trend=MetricTrend.UP,
                trend_value=self._metrics.cases_processed,
                alert_level=AlertLevel.NORMAL,
                aria_label=f"{self._metrics.cases_processed} cases processed in shadow pilot",
                description="Total cases processed in this pilot run",
            ),
            PanelMetric(
                metric_id="auto_clear_rate",
                label="Auto-Clear Rate",
                value=f"{self._metrics.auto_clear_rate:.1%}",
                unit="percent",
                trend=MetricTrend.STABLE,
                trend_value=self._metrics.auto_clear_rate,
                alert_level=AlertLevel.NORMAL,
                aria_label=f"Auto-clear rate is {self._metrics.auto_clear_rate:.1%}",
                description="Percentage of cases automatically cleared",
            ),
            PanelMetric(
                metric_id="escalation_rate",
                label="Escalation Rate",
                value=f"{self._metrics.escalation_rate:.1%}",
                unit="percent",
                trend=MetricTrend.STABLE,
                trend_value=self._metrics.escalation_rate,
                alert_level=AlertLevel.NORMAL if self._metrics.escalation_rate < 0.5 else AlertLevel.WARNING,
                aria_label=f"Escalation rate is {self._metrics.escalation_rate:.1%}",
                description="Percentage of cases escalated for review",
            ),
            PanelMetric(
                metric_id="guardrail_violations",
                label="Guardrail Violations",
                value=self._metrics.guardrail_violations,
                unit="violations",
                trend=MetricTrend.STABLE,
                trend_value=self._metrics.guardrail_violations,
                alert_level=AlertLevel.NORMAL if self._metrics.guardrail_violations == 0 else AlertLevel.CRITICAL,
                aria_label=f"{self._metrics.guardrail_violations} guardrail violations detected",
                description="Number of guardrail violations during pilot",
            ),
        ]

        return {
            "view_type": ShadowViewType.PILOT_DASHBOARD.value,
            "pilot_id": self._pilot_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "metrics": self._metrics.to_dict(),
            "panels": [m.to_dict() for m in metrics],
            "aria_role": AccessibilityRole.REGION.value,
            "aria_label": f"Shadow pilot {self._pilot_id} dashboard",
            "shadow_mode": self._shadow_mode,
        }

    def render_case_queue(self) -> Dict[str, Any]:
        """
        Render the case queue view.

        Returns:
            Case queue view data
        """
        queue_items = []
        for case in self._cases.values():
            # Calculate age
            created = datetime.fromisoformat(case.created_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600

            queue_items.append(QueueItem(
                case_id=case.case_id,
                entity_name=case.entity_name,
                tier=case.tier,
                age_hours=age_hours,
                alert_count=case.alert_count,
                priority_score=case.decision_confidence,
                status=case.status,
                assignee=case.escalation_target,
            ))

        # Sort by tier (higher first) then age
        tier_order = {"TIER_SAR": 0, "TIER_3": 1, "TIER_2": 2, "TIER_1": 3, "TIER_0": 4}
        queue_items.sort(key=lambda x: (tier_order.get(x.tier, 5), -x.age_hours))

        return {
            "view_type": ShadowViewType.CASE_QUEUE.value,
            "pilot_id": self._pilot_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "total_cases": len(queue_items),
            "cases": [item.to_dict() for item in queue_items],
            "aria_role": AccessibilityRole.TABLE.value,
            "aria_label": f"Shadow pilot case queue with {len(queue_items)} cases",
            "shadow_mode": self._shadow_mode,
        }

    def render_evidence_panel(self, case_id: str) -> Dict[str, Any]:
        """
        Render evidence panel for a case.

        Args:
            case_id: Case identifier

        Returns:
            Evidence panel view data
        """
        evidence_list = self._evidence.get(case_id, [])

        return {
            "view_type": ShadowViewType.EVIDENCE_PANEL.value,
            "pilot_id": self._pilot_id,
            "case_id": case_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "evidence_count": len(evidence_list),
            "evidence": [e.to_dict() for e in evidence_list],
            "aria_role": AccessibilityRole.REGION.value,
            "aria_label": f"Evidence panel for case {case_id} with {len(evidence_list)} items",
            "shadow_mode": self._shadow_mode,
        }

    def render_decision_log(self) -> Dict[str, Any]:
        """
        Render decision log view.

        Returns:
            Decision log view data
        """
        decisions = sorted(
            self._decisions.values(),
            key=lambda d: d.decided_at,
            reverse=True,
        )

        return {
            "view_type": ShadowViewType.DECISION_LOG.value,
            "pilot_id": self._pilot_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "total_decisions": len(decisions),
            "decisions": [d.to_dict() for d in decisions],
            "aria_role": AccessibilityRole.LOG.value,
            "aria_label": f"Decision log with {len(decisions)} entries",
            "shadow_mode": self._shadow_mode,
        }

    def render_tier_breakdown(self) -> Dict[str, Any]:
        """
        Render tier distribution breakdown.

        Returns:
            Tier breakdown view data
        """
        distribution = self._metrics.tier_distribution

        # Build breakdown with progress bars
        breakdown = []
        for tier, percentage in distribution.items():
            breakdown.append({
                "tier": tier,
                "count": getattr(self._metrics, f"tier{tier.replace('TIER_', '').replace('+', '_plus')}_count", 0)
                if "+" not in tier else self._metrics.tier2_plus_count,
                "percentage": percentage,
                "aria_label": f"{tier}: {percentage:.1%} of cases",
            })

        return {
            "view_type": ShadowViewType.TIER_BREAKDOWN.value,
            "pilot_id": self._pilot_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "total_cases": self._metrics.cases_processed,
            "breakdown": breakdown,
            "aria_role": AccessibilityRole.REGION.value,
            "aria_label": "Tier distribution breakdown",
            "shadow_mode": self._shadow_mode,
        }

    def render_scenario_results(
        self,
        scenarios: List[ScenarioResultView],
    ) -> Dict[str, Any]:
        """
        Render scenario execution results.

        Args:
            scenarios: List of scenario results

        Returns:
            Scenario results view data
        """
        passed = sum(1 for s in scenarios if s.passed)
        total = len(scenarios)

        return {
            "view_type": ShadowViewType.SCENARIO_RESULTS.value,
            "pilot_id": self._pilot_id,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "total_scenarios": total,
            "passed_scenarios": passed,
            "failed_scenarios": total - passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "scenarios": [s.to_dict() for s in scenarios],
            "aria_role": AccessibilityRole.TABLE.value,
            "aria_label": f"Scenario results: {passed} of {total} passed",
            "shadow_mode": self._shadow_mode,
        }

    def export_all_views(self) -> Dict[str, Any]:
        """
        Export all views for analysis.

        Returns:
            Complete view export
        """
        return {
            "pilot_id": self._pilot_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "dashboard": self.render_pilot_dashboard(),
            "case_queue": self.render_case_queue(),
            "decision_log": self.render_decision_log(),
            "tier_breakdown": self.render_tier_breakdown(),
            "shadow_mode": self._shadow_mode,
        }
