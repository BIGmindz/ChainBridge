# ═══════════════════════════════════════════════════════════════════════════════
# OCC Benchmark Panel — Benchmark Visualization for OCC
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agents: SONNY (GID-02), LIRA (GID-09)
# ═══════════════════════════════════════════════════════════════════════════════

"""
OCC Benchmark Panel — Operator Control Center Benchmark Visualization

PURPOSE:
    Provide real-time benchmark visualization for the Operator Control Center:
    - Latency charts (p50, p95, p99)
    - Throughput graphs
    - Cost breakdown displays
    - Determinism status indicators
    - Delta comparison views
    - Readiness scorecard

WCAG AA COMPLIANCE:
    - All colors meet 4.5:1 contrast ratio
    - Screen reader compatible labels
    - Keyboard navigable components
    - Focus indicators on interactive elements

COMPONENTS:
    1. BenchmarkDashboard - Main benchmark view
    2. LatencyChart - Latency distribution visualization
    3. ThroughputGauge - Operations/second gauge
    4. CostBreakdown - Cost attribution display
    5. DeterminismStatus - Replay verification status
    6. ReadinessScorecard - Graduation readiness display
    7. DeltaComparison - A/B comparison view

CONSTRAINTS:
    - SHADOW MODE only (no live data)
    - Render-only (no mutations)
    - Accessible color scheme

LANE: EXECUTION (UI)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# WCAG AA COLOR SCHEME
# ═══════════════════════════════════════════════════════════════════════════════


class AccessibleColors:
    """WCAG AA compliant color palette."""

    # Background colors
    BG_PRIMARY = "#1a1a2e"  # Dark blue
    BG_SECONDARY = "#16213e"  # Darker blue
    BG_CARD = "#0f3460"  # Card background

    # Text colors (4.5:1+ contrast)
    TEXT_PRIMARY = "#e4e4e4"  # Light gray
    TEXT_SECONDARY = "#b0b0b0"  # Medium gray
    TEXT_ACCENT = "#4fc3dc"  # Cyan

    # Status colors (AA compliant)
    STATUS_PASS = "#4ade80"  # Green
    STATUS_FAIL = "#f87171"  # Red
    STATUS_WARN = "#fbbf24"  # Yellow/amber
    STATUS_PENDING = "#94a3b8"  # Gray

    # Chart colors
    CHART_PRIMARY = "#4fc3dc"  # Cyan
    CHART_SECONDARY = "#a78bfa"  # Purple
    CHART_TERTIARY = "#f472b6"  # Pink

    # Focus indicator
    FOCUS_RING = "#60a5fa"  # Blue


class ChartType(Enum):
    """Type of chart visualization."""

    LINE = "LINE"
    BAR = "BAR"
    GAUGE = "GAUGE"
    PIE = "PIE"
    HISTOGRAM = "HISTOGRAM"


class StatusIndicator(Enum):
    """Status indicator state."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    PENDING = "PENDING"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA POINT STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DataPoint:
    """Single data point for charts."""

    timestamp: str
    value: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "value": self.value,
            "label": self.label,
            "metadata": self.metadata,
        }


@dataclass
class DataSeries:
    """Data series for charts."""

    series_id: str
    name: str
    color: str
    points: List[DataPoint] = field(default_factory=list)
    unit: str = ""

    def add_point(self, value: float, label: Optional[str] = None) -> None:
        point = DataPoint(
            timestamp=datetime.now(timezone.utc).isoformat(),
            value=value,
            label=label,
        )
        self.points.append(point)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "series_id": self.series_id,
            "name": self.name,
            "color": self.color,
            "points": [p.to_dict() for p in self.points],
            "unit": self.unit,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHART COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class LatencyChart:
    """
    Latency distribution chart.

    Displays p50, p95, p99 latency percentiles.
    WCAG AA: Uses distinct colors and patterns for accessibility.
    """

    chart_id: str
    title: str = "Latency Distribution"
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    unit: str = "ms"
    threshold_warn: float = 100.0  # ms
    threshold_fail: float = 500.0  # ms
    aria_label: str = "Latency percentile chart"

    def __post_init__(self) -> None:
        if not self.chart_id.startswith("CHART-"):
            raise ValueError(f"Chart ID must start with 'CHART-': {self.chart_id}")

    @property
    def status(self) -> StatusIndicator:
        if self.p99 >= self.threshold_fail:
            return StatusIndicator.FAIL
        elif self.p95 >= self.threshold_warn:
            return StatusIndicator.WARN
        return StatusIndicator.PASS

    def render(self) -> Dict[str, Any]:
        """Render chart data for frontend."""
        return {
            "chart_id": self.chart_id,
            "type": ChartType.BAR.value,
            "title": self.title,
            "aria_label": self.aria_label,
            "data": {
                "p50": {"value": round(self.p50, 2), "color": AccessibleColors.CHART_PRIMARY},
                "p95": {"value": round(self.p95, 2), "color": AccessibleColors.CHART_SECONDARY},
                "p99": {"value": round(self.p99, 2), "color": AccessibleColors.CHART_TERTIARY},
            },
            "unit": self.unit,
            "thresholds": {
                "warn": self.threshold_warn,
                "fail": self.threshold_fail,
            },
            "status": self.status.value,
            "accessibility": {
                "focus_ring": AccessibleColors.FOCUS_RING,
                "contrast_ratio": "4.5:1",
            },
        }


@dataclass
class ThroughputGauge:
    """
    Throughput gauge display.

    Shows operations per second with status coloring.
    """

    gauge_id: str
    title: str = "Throughput"
    current_ops: float = 0.0
    target_ops: float = 1000.0
    unit: str = "ops/sec"
    aria_label: str = "Throughput gauge showing operations per second"

    def __post_init__(self) -> None:
        if not self.gauge_id.startswith("GAUGE-"):
            raise ValueError(f"Gauge ID must start with 'GAUGE-': {self.gauge_id}")

    @property
    def percentage(self) -> float:
        return (self.current_ops / self.target_ops * 100) if self.target_ops > 0 else 0.0

    @property
    def status(self) -> StatusIndicator:
        pct = self.percentage
        if pct >= 90:
            return StatusIndicator.PASS
        elif pct >= 70:
            return StatusIndicator.WARN
        return StatusIndicator.FAIL

    def render(self) -> Dict[str, Any]:
        return {
            "gauge_id": self.gauge_id,
            "type": ChartType.GAUGE.value,
            "title": self.title,
            "aria_label": self.aria_label,
            "data": {
                "current": round(self.current_ops, 2),
                "target": round(self.target_ops, 2),
                "percentage": round(self.percentage, 1),
            },
            "unit": self.unit,
            "status": self.status.value,
            "colors": {
                "pass": AccessibleColors.STATUS_PASS,
                "warn": AccessibleColors.STATUS_WARN,
                "fail": AccessibleColors.STATUS_FAIL,
            },
        }


@dataclass
class CostBreakdown:
    """
    Cost attribution breakdown display.

    Shows cost by category with pie/donut visualization.
    """

    breakdown_id: str
    title: str = "Cost Breakdown"
    token_cost: float = 0.0
    memory_cost: float = 0.0
    routing_cost: float = 0.0
    snapshot_cost: float = 0.0
    budget_limit: float = 1.0  # USD
    aria_label: str = "Cost breakdown by operation category"

    def __post_init__(self) -> None:
        if not self.breakdown_id.startswith("COST-"):
            raise ValueError(f"Cost breakdown ID must start with 'COST-': {self.breakdown_id}")

    @property
    def total_cost(self) -> float:
        return self.token_cost + self.memory_cost + self.routing_cost + self.snapshot_cost

    @property
    def budget_percentage(self) -> float:
        return (self.total_cost / self.budget_limit * 100) if self.budget_limit > 0 else 0.0

    @property
    def status(self) -> StatusIndicator:
        pct = self.budget_percentage
        if pct <= 70:
            return StatusIndicator.PASS
        elif pct <= 90:
            return StatusIndicator.WARN
        return StatusIndicator.FAIL

    def render(self) -> Dict[str, Any]:
        return {
            "breakdown_id": self.breakdown_id,
            "type": ChartType.PIE.value,
            "title": self.title,
            "aria_label": self.aria_label,
            "data": {
                "tokens": {"value": round(self.token_cost, 6), "color": AccessibleColors.CHART_PRIMARY, "label": "Tokens"},
                "memory": {"value": round(self.memory_cost, 6), "color": AccessibleColors.CHART_SECONDARY, "label": "Memory"},
                "routing": {"value": round(self.routing_cost, 6), "color": AccessibleColors.CHART_TERTIARY, "label": "Routing"},
                "snapshots": {"value": round(self.snapshot_cost, 6), "color": AccessibleColors.TEXT_ACCENT, "label": "Snapshots"},
            },
            "total": round(self.total_cost, 6),
            "budget": round(self.budget_limit, 2),
            "budget_percentage": round(self.budget_percentage, 1),
            "unit": "USD",
            "status": self.status.value,
        }


@dataclass
class DeterminismStatus:
    """
    Determinism verification status indicator.

    Shows replay match/mismatch status.
    """

    status_id: str
    title: str = "Determinism Status"
    replay_count: int = 0
    matches: int = 0
    mismatches: int = 0
    aria_label: str = "Determinism verification status"

    def __post_init__(self) -> None:
        if not self.status_id.startswith("DET-"):
            raise ValueError(f"Determinism status ID must start with 'DET-': {self.status_id}")

    @property
    def score(self) -> float:
        total = self.matches + self.mismatches
        return (self.matches / total) if total > 0 else 0.0

    @property
    def is_deterministic(self) -> bool:
        return self.mismatches == 0 and self.replay_count > 0

    @property
    def status(self) -> StatusIndicator:
        if self.replay_count == 0:
            return StatusIndicator.PENDING
        elif self.is_deterministic:
            return StatusIndicator.PASS
        return StatusIndicator.FAIL

    def render(self) -> Dict[str, Any]:
        return {
            "status_id": self.status_id,
            "title": self.title,
            "aria_label": self.aria_label,
            "data": {
                "replay_count": self.replay_count,
                "matches": self.matches,
                "mismatches": self.mismatches,
                "score": round(self.score, 4),
                "is_deterministic": self.is_deterministic,
            },
            "status": self.status.value,
            "status_color": {
                "PASS": AccessibleColors.STATUS_PASS,
                "FAIL": AccessibleColors.STATUS_FAIL,
                "PENDING": AccessibleColors.STATUS_PENDING,
            }[self.status.value],
        }


@dataclass
class ReadinessScorecard:
    """
    Graduation readiness scorecard.

    Shows status of all readiness invariants.
    """

    scorecard_id: str
    title: str = "Readiness Scorecard"
    invariants: List[Dict[str, Any]] = field(default_factory=list)
    overall_score: float = 0.0
    current_level: str = "SHADOW"
    target_level: str = "PILOT"
    aria_label: str = "Graduation readiness scorecard"

    def __post_init__(self) -> None:
        if not self.scorecard_id.startswith("SCORE-"):
            raise ValueError(f"Scorecard ID must start with 'SCORE-': {self.scorecard_id}")

    @property
    def is_ready(self) -> bool:
        return all(inv.get("is_passing", False) for inv in self.invariants)

    @property
    def status(self) -> StatusIndicator:
        if not self.invariants:
            return StatusIndicator.PENDING
        if self.is_ready:
            return StatusIndicator.PASS
        if self.overall_score >= 0.5:
            return StatusIndicator.WARN
        return StatusIndicator.FAIL

    def add_invariant(self, invariant_id: str, name: str, is_passing: bool, message: Optional[str] = None) -> None:
        self.invariants.append({
            "invariant_id": invariant_id,
            "name": name,
            "is_passing": is_passing,
            "message": message,
        })

    def render(self) -> Dict[str, Any]:
        return {
            "scorecard_id": self.scorecard_id,
            "title": self.title,
            "aria_label": self.aria_label,
            "data": {
                "invariants": self.invariants,
                "overall_score": round(self.overall_score, 4),
                "is_ready": self.is_ready,
                "current_level": self.current_level,
                "target_level": self.target_level,
                "passing_count": sum(1 for inv in self.invariants if inv.get("is_passing", False)),
                "total_count": len(self.invariants),
            },
            "status": self.status.value,
            "colors": {
                "pass": AccessibleColors.STATUS_PASS,
                "fail": AccessibleColors.STATUS_FAIL,
                "warn": AccessibleColors.STATUS_WARN,
                "pending": AccessibleColors.STATUS_PENDING,
            },
        }


@dataclass
class DeltaComparison:
    """
    A/B delta comparison view.

    Shows performance delta between two benchmark runs.
    """

    comparison_id: str
    title: str = "Performance Delta"
    baseline_id: str = ""
    comparison_id_ref: str = ""
    latency_delta_ms: float = 0.0
    throughput_delta_ops: float = 0.0
    cost_delta_usd: float = 0.0
    aria_label: str = "Performance comparison between benchmark runs"

    def __post_init__(self) -> None:
        if not self.comparison_id.startswith("DELTA-"):
            raise ValueError(f"Comparison ID must start with 'DELTA-': {self.comparison_id}")

    @property
    def latency_improved(self) -> bool:
        return self.latency_delta_ms < 0

    @property
    def throughput_improved(self) -> bool:
        return self.throughput_delta_ops > 0

    @property
    def cost_improved(self) -> bool:
        return self.cost_delta_usd < 0

    @property
    def overall_status(self) -> StatusIndicator:
        improvements = sum([self.latency_improved, self.throughput_improved, self.cost_improved])
        if improvements >= 2:
            return StatusIndicator.PASS
        elif improvements >= 1:
            return StatusIndicator.WARN
        return StatusIndicator.FAIL

    def render(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "title": self.title,
            "aria_label": self.aria_label,
            "baseline_id": self.baseline_id,
            "comparison_id_ref": self.comparison_id_ref,
            "deltas": {
                "latency": {
                    "value": round(self.latency_delta_ms, 3),
                    "unit": "ms",
                    "improved": self.latency_improved,
                    "direction": "↓" if self.latency_improved else "↑",
                },
                "throughput": {
                    "value": round(self.throughput_delta_ops, 2),
                    "unit": "ops/sec",
                    "improved": self.throughput_improved,
                    "direction": "↑" if self.throughput_improved else "↓",
                },
                "cost": {
                    "value": round(self.cost_delta_usd, 6),
                    "unit": "USD",
                    "improved": self.cost_improved,
                    "direction": "↓" if self.cost_improved else "↑",
                },
            },
            "status": self.overall_status.value,
            "colors": {
                "improved": AccessibleColors.STATUS_PASS,
                "regressed": AccessibleColors.STATUS_FAIL,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════


class OCCBenchmarkPanel:
    """
    Main OCC Benchmark Panel.

    Aggregates all benchmark visualizations into a cohesive dashboard.
    """

    def __init__(self, panel_id: str = "PANEL-BENCH-001") -> None:
        if not panel_id.startswith("PANEL-"):
            raise ValueError(f"Panel ID must start with 'PANEL-': {panel_id}")

        self._panel_id = panel_id
        self._latency_chart: Optional[LatencyChart] = None
        self._throughput_gauge: Optional[ThroughputGauge] = None
        self._cost_breakdown: Optional[CostBreakdown] = None
        self._determinism_status: Optional[DeterminismStatus] = None
        self._readiness_scorecard: Optional[ReadinessScorecard] = None
        self._delta_comparisons: List[DeltaComparison] = []
        self._last_updated: Optional[str] = None

    @property
    def panel_id(self) -> str:
        return self._panel_id

    def set_latency_data(self, p50: float, p95: float, p99: float) -> None:
        """Set latency chart data."""
        self._latency_chart = LatencyChart(
            chart_id="CHART-LAT-001",
            p50=p50,
            p95=p95,
            p99=p99,
        )
        self._mark_updated()

    def set_throughput_data(self, current_ops: float, target_ops: float = 1000.0) -> None:
        """Set throughput gauge data."""
        self._throughput_gauge = ThroughputGauge(
            gauge_id="GAUGE-THR-001",
            current_ops=current_ops,
            target_ops=target_ops,
        )
        self._mark_updated()

    def set_cost_data(
        self,
        token_cost: float,
        memory_cost: float,
        routing_cost: float,
        snapshot_cost: float,
        budget: float = 1.0,
    ) -> None:
        """Set cost breakdown data."""
        self._cost_breakdown = CostBreakdown(
            breakdown_id="COST-BRK-001",
            token_cost=token_cost,
            memory_cost=memory_cost,
            routing_cost=routing_cost,
            snapshot_cost=snapshot_cost,
            budget_limit=budget,
        )
        self._mark_updated()

    def set_determinism_data(self, replay_count: int, matches: int, mismatches: int) -> None:
        """Set determinism status data."""
        self._determinism_status = DeterminismStatus(
            status_id="DET-STA-001",
            replay_count=replay_count,
            matches=matches,
            mismatches=mismatches,
        )
        self._mark_updated()

    def set_readiness_data(
        self,
        invariants: List[Dict[str, Any]],
        overall_score: float,
        current_level: str,
    ) -> None:
        """Set readiness scorecard data."""
        self._readiness_scorecard = ReadinessScorecard(
            scorecard_id="SCORE-RDY-001",
            invariants=invariants,
            overall_score=overall_score,
            current_level=current_level,
        )
        self._mark_updated()

    def add_delta_comparison(
        self,
        baseline_id: str,
        comparison_id_ref: str,
        latency_delta: float,
        throughput_delta: float,
        cost_delta: float,
    ) -> None:
        """Add a delta comparison."""
        delta = DeltaComparison(
            comparison_id=f"DELTA-{len(self._delta_comparisons) + 1:03d}",
            baseline_id=baseline_id,
            comparison_id_ref=comparison_id_ref,
            latency_delta_ms=latency_delta,
            throughput_delta_ops=throughput_delta,
            cost_delta_usd=cost_delta,
        )
        self._delta_comparisons.append(delta)
        self._mark_updated()

    def _mark_updated(self) -> None:
        """Mark panel as updated."""
        self._last_updated = datetime.now(timezone.utc).isoformat()

    def render(self) -> Dict[str, Any]:
        """Render complete dashboard."""
        return {
            "panel_id": self._panel_id,
            "type": "BENCHMARK_DASHBOARD",
            "title": "Benchmark & Readiness Dashboard",
            "last_updated": self._last_updated,
            "aria_label": "Operator Control Center benchmark dashboard",
            "theme": {
                "background": AccessibleColors.BG_PRIMARY,
                "card_background": AccessibleColors.BG_CARD,
                "text_primary": AccessibleColors.TEXT_PRIMARY,
                "text_secondary": AccessibleColors.TEXT_SECONDARY,
                "focus_ring": AccessibleColors.FOCUS_RING,
            },
            "components": {
                "latency": self._latency_chart.render() if self._latency_chart else None,
                "throughput": self._throughput_gauge.render() if self._throughput_gauge else None,
                "cost": self._cost_breakdown.render() if self._cost_breakdown else None,
                "determinism": self._determinism_status.render() if self._determinism_status else None,
                "readiness": self._readiness_scorecard.render() if self._readiness_scorecard else None,
                "deltas": [d.render() for d in self._delta_comparisons],
            },
            "wcag_compliance": {
                "level": "AA",
                "contrast_ratio": "4.5:1",
                "keyboard_navigable": True,
                "screen_reader_compatible": True,
            },
        }

    def compute_panel_hash(self) -> str:
        """Compute hash of panel state."""
        data = self.render()
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Colors
    "AccessibleColors",
    # Enums
    "ChartType",
    "StatusIndicator",
    # Data structures
    "DataPoint",
    "DataSeries",
    # Chart components
    "LatencyChart",
    "ThroughputGauge",
    "CostBreakdown",
    "DeterminismStatus",
    "ReadinessScorecard",
    "DeltaComparison",
    # Dashboard
    "OCCBenchmarkPanel",
]
