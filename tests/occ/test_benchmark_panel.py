# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite — OCC Benchmark Panel Tests
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for core/occ/benchmark_panel.py

Coverage:
- AccessibleColors
- ChartType, StatusIndicator enums
- DataPoint, DataSeries dataclasses
- LatencyChart, ThroughputGauge, CostBreakdown
- DeterminismStatus, ReadinessScorecard, DeltaComparison
- OCCBenchmarkPanel
"""

import pytest

from core.occ.benchmark_panel import (
    AccessibleColors,
    ChartType,
    CostBreakdown,
    DataPoint,
    DataSeries,
    DeltaComparison,
    DeterminismStatus,
    LatencyChart,
    OCCBenchmarkPanel,
    ReadinessScorecard,
    StatusIndicator,
    ThroughputGauge,
)


class TestAccessibleColors:
    """Tests for AccessibleColors."""

    def test_color_values_defined(self) -> None:
        """Test that all color values are defined."""
        assert AccessibleColors.BG_PRIMARY is not None
        assert AccessibleColors.TEXT_PRIMARY is not None
        assert AccessibleColors.STATUS_PASS is not None
        assert AccessibleColors.FOCUS_RING is not None

    def test_color_format(self) -> None:
        """Test color format is hex."""
        assert AccessibleColors.BG_PRIMARY.startswith("#")
        assert len(AccessibleColors.BG_PRIMARY) == 7


class TestChartEnums:
    """Tests for chart enums."""

    def test_chart_type_values(self) -> None:
        """Test ChartType values."""
        assert ChartType.LINE.value == "LINE"
        assert ChartType.BAR.value == "BAR"
        assert ChartType.GAUGE.value == "GAUGE"
        assert ChartType.PIE.value == "PIE"
        assert ChartType.HISTOGRAM.value == "HISTOGRAM"

    def test_status_indicator_values(self) -> None:
        """Test StatusIndicator values."""
        assert StatusIndicator.PASS.value == "PASS"
        assert StatusIndicator.FAIL.value == "FAIL"
        assert StatusIndicator.WARN.value == "WARN"
        assert StatusIndicator.PENDING.value == "PENDING"


class TestDataStructures:
    """Tests for data point and series."""

    def test_data_point_creation(self) -> None:
        """Test DataPoint creation."""
        point = DataPoint(
            timestamp="2025-01-01T00:00:00Z",
            value=42.5,
            label="test",
        )

        assert point.value == 42.5
        assert point.label == "test"

    def test_data_point_to_dict(self) -> None:
        """Test DataPoint serialization."""
        point = DataPoint(
            timestamp="2025-01-01T00:00:00Z",
            value=100.0,
        )

        data = point.to_dict()
        assert data["value"] == 100.0

    def test_data_series_creation(self) -> None:
        """Test DataSeries creation."""
        series = DataSeries(
            series_id="S001",
            name="Test Series",
            color="#ff0000",
        )

        assert series.series_id == "S001"
        assert len(series.points) == 0

    def test_data_series_add_point(self) -> None:
        """Test adding points to series."""
        series = DataSeries(
            series_id="S001",
            name="Test Series",
            color="#ff0000",
        )

        series.add_point(10.0, "first")
        series.add_point(20.0, "second")

        assert len(series.points) == 2


class TestLatencyChart:
    """Tests for LatencyChart."""

    def test_valid_chart_creation(self) -> None:
        """Test valid chart creation."""
        chart = LatencyChart(
            chart_id="CHART-001",
            p50=10.0,
            p95=50.0,
            p99=100.0,
        )

        assert chart.chart_id == "CHART-001"
        assert chart.p50 == 10.0

    def test_invalid_chart_id(self) -> None:
        """Test invalid chart ID."""
        with pytest.raises(ValueError, match="must start with 'CHART-'"):
            LatencyChart(chart_id="INVALID")

    def test_chart_status_pass(self) -> None:
        """Test chart status when passing."""
        chart = LatencyChart(
            chart_id="CHART-001",
            p50=10.0,
            p95=50.0,
            p99=80.0,
            threshold_warn=100.0,
            threshold_fail=500.0,
        )

        assert chart.status == StatusIndicator.PASS

    def test_chart_status_warn(self) -> None:
        """Test chart status when warning."""
        chart = LatencyChart(
            chart_id="CHART-001",
            p50=10.0,
            p95=150.0,
            p99=200.0,
            threshold_warn=100.0,
            threshold_fail=500.0,
        )

        assert chart.status == StatusIndicator.WARN

    def test_chart_status_fail(self) -> None:
        """Test chart status when failing."""
        chart = LatencyChart(
            chart_id="CHART-001",
            p50=100.0,
            p95=400.0,
            p99=600.0,
            threshold_warn=100.0,
            threshold_fail=500.0,
        )

        assert chart.status == StatusIndicator.FAIL

    def test_chart_render(self) -> None:
        """Test chart rendering."""
        chart = LatencyChart(
            chart_id="CHART-001",
            p50=10.0,
            p95=50.0,
            p99=100.0,
        )

        data = chart.render()

        assert data["chart_id"] == "CHART-001"
        assert data["type"] == "BAR"
        assert "p50" in data["data"]
        assert "accessibility" in data


class TestThroughputGauge:
    """Tests for ThroughputGauge."""

    def test_valid_gauge_creation(self) -> None:
        """Test valid gauge creation."""
        gauge = ThroughputGauge(
            gauge_id="GAUGE-001",
            current_ops=800.0,
            target_ops=1000.0,
        )

        assert gauge.gauge_id == "GAUGE-001"
        assert gauge.percentage == 80.0

    def test_invalid_gauge_id(self) -> None:
        """Test invalid gauge ID."""
        with pytest.raises(ValueError, match="must start with 'GAUGE-'"):
            ThroughputGauge(gauge_id="INVALID")

    def test_gauge_status_pass(self) -> None:
        """Test gauge status when passing."""
        gauge = ThroughputGauge(
            gauge_id="GAUGE-001",
            current_ops=950.0,
            target_ops=1000.0,
        )

        assert gauge.status == StatusIndicator.PASS

    def test_gauge_status_warn(self) -> None:
        """Test gauge status when warning."""
        gauge = ThroughputGauge(
            gauge_id="GAUGE-001",
            current_ops=750.0,
            target_ops=1000.0,
        )

        assert gauge.status == StatusIndicator.WARN

    def test_gauge_render(self) -> None:
        """Test gauge rendering."""
        gauge = ThroughputGauge(
            gauge_id="GAUGE-001",
            current_ops=500.0,
            target_ops=1000.0,
        )

        data = gauge.render()

        assert data["gauge_id"] == "GAUGE-001"
        assert data["type"] == "GAUGE"
        assert data["data"]["percentage"] == 50.0


class TestCostBreakdown:
    """Tests for CostBreakdown."""

    def test_valid_breakdown_creation(self) -> None:
        """Test valid breakdown creation."""
        breakdown = CostBreakdown(
            breakdown_id="COST-001",
            token_cost=0.01,
            memory_cost=0.005,
            routing_cost=0.002,
            snapshot_cost=0.001,
        )

        assert breakdown.breakdown_id == "COST-001"

    def test_invalid_breakdown_id(self) -> None:
        """Test invalid breakdown ID."""
        with pytest.raises(ValueError, match="must start with 'COST-'"):
            CostBreakdown(breakdown_id="INVALID")

    def test_total_cost(self) -> None:
        """Test total cost calculation."""
        breakdown = CostBreakdown(
            breakdown_id="COST-001",
            token_cost=0.10,
            memory_cost=0.05,
            routing_cost=0.02,
            snapshot_cost=0.01,
        )

        assert abs(breakdown.total_cost - 0.18) < 0.0001  # Floating point tolerance

    def test_budget_percentage(self) -> None:
        """Test budget percentage calculation."""
        breakdown = CostBreakdown(
            breakdown_id="COST-001",
            token_cost=0.50,
            budget_limit=1.0,
        )

        assert breakdown.budget_percentage == 50.0

    def test_breakdown_render(self) -> None:
        """Test breakdown rendering."""
        breakdown = CostBreakdown(breakdown_id="COST-001")
        data = breakdown.render()

        assert data["breakdown_id"] == "COST-001"
        assert data["type"] == "PIE"
        assert "tokens" in data["data"]


class TestDeterminismStatus:
    """Tests for DeterminismStatus."""

    def test_valid_status_creation(self) -> None:
        """Test valid status creation."""
        status = DeterminismStatus(
            status_id="DET-001",
            replay_count=10,
            matches=10,
            mismatches=0,
        )

        assert status.status_id == "DET-001"
        assert status.is_deterministic

    def test_invalid_status_id(self) -> None:
        """Test invalid status ID."""
        with pytest.raises(ValueError, match="must start with 'DET-'"):
            DeterminismStatus(status_id="INVALID")

    def test_determinism_score(self) -> None:
        """Test determinism score."""
        status = DeterminismStatus(
            status_id="DET-001",
            replay_count=10,
            matches=8,
            mismatches=2,
        )

        assert status.score == 0.8
        assert not status.is_deterministic

    def test_status_indicator(self) -> None:
        """Test status indicator values."""
        # Pending when no replays
        status = DeterminismStatus(status_id="DET-001")
        assert status.status == StatusIndicator.PENDING

        # Pass when deterministic
        status = DeterminismStatus(
            status_id="DET-001",
            replay_count=5,
            matches=5,
            mismatches=0,
        )
        assert status.status == StatusIndicator.PASS

        # Fail when not deterministic
        status = DeterminismStatus(
            status_id="DET-001",
            replay_count=5,
            matches=3,
            mismatches=2,
        )
        assert status.status == StatusIndicator.FAIL


class TestReadinessScorecard:
    """Tests for ReadinessScorecard."""

    def test_valid_scorecard_creation(self) -> None:
        """Test valid scorecard creation."""
        scorecard = ReadinessScorecard(
            scorecard_id="SCORE-001",
            overall_score=0.8,
            current_level="SHADOW",
        )

        assert scorecard.scorecard_id == "SCORE-001"

    def test_invalid_scorecard_id(self) -> None:
        """Test invalid scorecard ID."""
        with pytest.raises(ValueError, match="must start with 'SCORE-'"):
            ReadinessScorecard(scorecard_id="INVALID")

    def test_add_invariant(self) -> None:
        """Test adding invariants."""
        scorecard = ReadinessScorecard(scorecard_id="SCORE-001")

        scorecard.add_invariant("INV-001", "Test", True)
        scorecard.add_invariant("INV-002", "Test2", False, "Failed check")

        assert len(scorecard.invariants) == 2

    def test_is_ready(self) -> None:
        """Test is_ready property."""
        scorecard = ReadinessScorecard(scorecard_id="SCORE-001")

        scorecard.add_invariant("INV-001", "Test", True)
        scorecard.add_invariant("INV-002", "Test2", True)

        assert scorecard.is_ready

        scorecard.add_invariant("INV-003", "Test3", False)
        assert not scorecard.is_ready

    def test_scorecard_render(self) -> None:
        """Test scorecard rendering."""
        scorecard = ReadinessScorecard(
            scorecard_id="SCORE-001",
            overall_score=0.75,
        )

        data = scorecard.render()

        assert data["scorecard_id"] == "SCORE-001"
        assert "invariants" in data["data"]


class TestDeltaComparison:
    """Tests for DeltaComparison."""

    def test_valid_comparison_creation(self) -> None:
        """Test valid comparison creation."""
        delta = DeltaComparison(
            comparison_id="DELTA-001",
            baseline_id="BENCH-001",
            comparison_id_ref="BENCH-002",
            latency_delta_ms=-10.0,
            throughput_delta_ops=100.0,
            cost_delta_usd=-0.01,
        )

        assert delta.comparison_id == "DELTA-001"

    def test_invalid_comparison_id(self) -> None:
        """Test invalid comparison ID."""
        with pytest.raises(ValueError, match="must start with 'DELTA-'"):
            DeltaComparison(comparison_id="INVALID")

    def test_improvement_detection(self) -> None:
        """Test improvement detection."""
        delta = DeltaComparison(
            comparison_id="DELTA-001",
            latency_delta_ms=-10.0,  # Improved (lower)
            throughput_delta_ops=100.0,  # Improved (higher)
            cost_delta_usd=-0.01,  # Improved (lower)
        )

        assert delta.latency_improved
        assert delta.throughput_improved
        assert delta.cost_improved
        assert delta.overall_status == StatusIndicator.PASS

    def test_regression_detection(self) -> None:
        """Test regression detection."""
        delta = DeltaComparison(
            comparison_id="DELTA-001",
            latency_delta_ms=50.0,  # Regressed
            throughput_delta_ops=-100.0,  # Regressed
            cost_delta_usd=0.05,  # Regressed
        )

        assert not delta.latency_improved
        assert not delta.throughput_improved
        assert not delta.cost_improved
        assert delta.overall_status == StatusIndicator.FAIL

    def test_comparison_render(self) -> None:
        """Test comparison rendering."""
        delta = DeltaComparison(
            comparison_id="DELTA-001",
            latency_delta_ms=-5.0,
        )

        data = delta.render()

        assert data["comparison_id"] == "DELTA-001"
        assert "latency" in data["deltas"]
        assert data["deltas"]["latency"]["direction"] == "↓"


class TestOCCBenchmarkPanel:
    """Tests for OCCBenchmarkPanel."""

    def test_valid_panel_creation(self) -> None:
        """Test valid panel creation."""
        panel = OCCBenchmarkPanel("PANEL-001")
        assert panel.panel_id == "PANEL-001"

    def test_invalid_panel_id(self) -> None:
        """Test invalid panel ID."""
        with pytest.raises(ValueError, match="must start with 'PANEL-'"):
            OCCBenchmarkPanel("INVALID")

    def test_set_latency_data(self) -> None:
        """Test setting latency data."""
        panel = OCCBenchmarkPanel()
        panel.set_latency_data(10.0, 50.0, 100.0)

        data = panel.render()
        assert data["components"]["latency"] is not None
        assert data["components"]["latency"]["data"]["p50"]["value"] == 10.0

    def test_set_throughput_data(self) -> None:
        """Test setting throughput data."""
        panel = OCCBenchmarkPanel()
        panel.set_throughput_data(800.0, 1000.0)

        data = panel.render()
        assert data["components"]["throughput"] is not None

    def test_set_cost_data(self) -> None:
        """Test setting cost data."""
        panel = OCCBenchmarkPanel()
        panel.set_cost_data(0.01, 0.005, 0.002, 0.001)

        data = panel.render()
        assert data["components"]["cost"] is not None

    def test_set_determinism_data(self) -> None:
        """Test setting determinism data."""
        panel = OCCBenchmarkPanel()
        panel.set_determinism_data(10, 10, 0)

        data = panel.render()
        assert data["components"]["determinism"] is not None

    def test_set_readiness_data(self) -> None:
        """Test setting readiness data."""
        panel = OCCBenchmarkPanel()
        panel.set_readiness_data(
            [{"invariant_id": "INV-001", "is_passing": True}],
            0.8,
            "SHADOW",
        )

        data = panel.render()
        assert data["components"]["readiness"] is not None

    def test_add_delta_comparison(self) -> None:
        """Test adding delta comparison."""
        panel = OCCBenchmarkPanel()
        panel.add_delta_comparison("BENCH-001", "BENCH-002", -5.0, 50.0, -0.001)

        data = panel.render()
        assert len(data["components"]["deltas"]) == 1

    def test_render_complete_panel(self) -> None:
        """Test rendering complete panel."""
        panel = OCCBenchmarkPanel()
        panel.set_latency_data(10.0, 50.0, 100.0)
        panel.set_throughput_data(900.0)
        panel.set_cost_data(0.01, 0.005, 0.002, 0.001)
        panel.set_determinism_data(5, 5, 0)
        panel.set_readiness_data([], 1.0, "SHADOW")

        data = panel.render()

        assert data["type"] == "BENCHMARK_DASHBOARD"
        assert data["last_updated"] is not None
        assert "theme" in data
        assert "wcag_compliance" in data
        assert data["wcag_compliance"]["level"] == "AA"

    def test_panel_hash(self) -> None:
        """Test panel hash computation."""
        panel = OCCBenchmarkPanel()
        panel.set_latency_data(10.0, 50.0, 100.0)

        hash1 = panel.compute_panel_hash()
        hash2 = panel.compute_panel_hash()
        assert hash1 == hash2


class TestIntegration:
    """Integration tests for OCC benchmark panel."""

    def test_full_dashboard_workflow(self) -> None:
        """Test complete dashboard workflow."""
        panel = OCCBenchmarkPanel("PANEL-BENCH-001")

        # Set all data
        panel.set_latency_data(15.0, 45.0, 90.0)
        panel.set_throughput_data(950.0, 1000.0)
        panel.set_cost_data(0.02, 0.01, 0.005, 0.002, budget=0.1)
        panel.set_determinism_data(20, 20, 0)
        panel.set_readiness_data(
            [
                {"invariant_id": "INV-READY-001", "name": "Determinism", "is_passing": True},
                {"invariant_id": "INV-READY-002", "name": "No Live Inference", "is_passing": True},
            ],
            1.0,
            "SHADOW",
        )

        # Add comparison
        panel.add_delta_comparison("BENCH-001", "BENCH-002", -5.0, 100.0, -0.005)

        # Render
        data = panel.render()

        # Verify structure
        assert data["panel_id"] == "PANEL-BENCH-001"
        assert all(
            key in data["components"]
            for key in ["latency", "throughput", "cost", "determinism", "readiness", "deltas"]
        )

        # Verify accessibility
        assert data["wcag_compliance"]["contrast_ratio"] == "4.5:1"
        assert data["wcag_compliance"]["keyboard_navigable"]
        assert data["wcag_compliance"]["screen_reader_compatible"]
