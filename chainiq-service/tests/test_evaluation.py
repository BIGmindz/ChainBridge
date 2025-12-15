"""
ChainIQ v0.1 - Evaluation Module Tests

Tests for the retrospective pilot evaluation functionality.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

import pytest

# Test imports
from app.evaluation import (
    RetrospectivePilotMetrics,
    RetrospectivePilotReport,
    build_markdown_summary,
    compute_pilot_metrics,
    is_bad_outcome,
    load_pilot_data_from_csv,
    map_row_to_context,
    run_retrospective_pilot,
    validate_pilot_dataframe,
)

# =============================================================================
# TEST: RetrospectivePilotMetrics MODEL
# =============================================================================


class TestRetrospectivePilotMetrics:
    """Tests for the canonical pilot metrics Pydantic model."""

    def test_metrics_required_fields(self):
        """Test that required fields are enforced."""
        # These are required
        metrics = RetrospectivePilotMetrics(
            total_shipments=100,
            total_bad_events=15,
            bad_event_rate=0.15,
        )

        assert metrics.total_shipments == 100
        assert metrics.total_bad_events == 15
        assert metrics.bad_event_rate == 0.15

    def test_metrics_optional_fields_default_none(self):
        """Test that optional fields default to None."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=100,
            total_bad_events=15,
            bad_event_rate=0.15,
        )

        assert metrics.auc_roc is None
        assert metrics.lift_at_top_10pct is None
        assert metrics.capture_rate_top_10pct is None
        assert metrics.confusion_matrix is None

    def test_metrics_with_all_fields(self):
        """Test metrics with all fields populated."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=1000,
            total_bad_events=150,
            bad_event_rate=0.15,
            auc_roc=0.78,
            lift_at_top_10pct=3.2,
            capture_rate_top_10pct=0.48,
            precision_at_top_10pct=0.48,
            total_loss_usd=500000.0,
            hypothetical_savings_usd=125000.0,
            confusion_matrix={"tp": 100, "fp": 50, "tn": 800, "fn": 50},
            threshold_used=60.0,
        )

        assert metrics.auc_roc == 0.78
        assert metrics.hypothetical_savings_usd == 125000.0
        assert metrics.confusion_matrix["tp"] == 100

    def test_metrics_json_serialization(self):
        """Test JSON serialization."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=100,
            total_bad_events=15,
            bad_event_rate=0.15,
            auc_roc=0.75,
        )

        json_str = metrics.model_dump_json()
        # Check key fields are present (compact JSON, no spaces)
        assert '"total_shipments":100' in json_str
        assert '"auc_roc":0.75' in json_str


# =============================================================================
# TEST: RetrospectivePilotReport MODEL
# =============================================================================


class TestRetrospectivePilotReport:
    """Tests for the full pilot report Pydantic model."""

    def test_report_structure(self):
        """Test report can be created with required fields."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=100,
            total_bad_events=15,
            bad_event_rate=0.15,
        )

        report = RetrospectivePilotReport(
            tenant_id="TEST-TENANT",
            metrics=metrics,
        )

        assert report.tenant_id == "TEST-TENANT"
        assert report.metrics.total_shipments == 100
        assert report.generated_at is not None
        assert isinstance(report.risk_distribution, dict)
        assert isinstance(report.notes, list)

    def test_report_with_distributions(self):
        """Test report with risk and decision distributions."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=100,
            total_bad_events=15,
            bad_event_rate=0.15,
        )

        report = RetrospectivePilotReport(
            tenant_id="TEST-TENANT",
            model_version="heuristic-v0",
            metrics=metrics,
            risk_distribution={"0-30": 50, "30-60": 30, "60-80": 15, "80-100": 5},
            decision_distribution={"APPROVE": 50, "TIGHTEN_TERMS": 30, "HOLD": 15, "ESCALATE": 5},
            notes=["Test note"],
        )

        assert report.risk_distribution["0-30"] == 50
        assert report.decision_distribution["APPROVE"] == 50
        assert len(report.notes) == 1


# =============================================================================
# TEST: compute_pilot_metrics()
# =============================================================================


class TestComputePilotMetrics:
    """Tests for metrics computation function."""

    def test_basic_metrics_computation(self):
        """Test basic metrics are computed correctly."""
        risk_scores = [80, 70, 60, 50, 40, 30, 20, 10, 90, 85]
        actuals = [True, True, True, False, False, False, False, False, True, True]
        values = [10000.0] * 10
        losses = [5000.0, 4000.0, 3000.0, 0, 0, 0, 0, 0, 6000.0, 5500.0]

        metrics = compute_pilot_metrics(risk_scores, actuals, values, losses, threshold=60.0)

        assert metrics.total_shipments == 10
        assert metrics.total_bad_events == 5
        assert metrics.bad_event_rate == 0.5

    def test_metrics_with_zero_bad_events(self):
        """Test metrics when no bad events exist."""
        risk_scores = [50, 40, 30, 20]
        actuals = [False, False, False, False]
        values = [10000.0] * 4
        losses = [0.0] * 4

        metrics = compute_pilot_metrics(risk_scores, actuals, values, losses)

        assert metrics.total_shipments == 4
        assert metrics.total_bad_events == 0
        assert metrics.bad_event_rate == 0.0

    def test_metrics_with_empty_data(self):
        """Test metrics with empty input."""
        metrics = compute_pilot_metrics([], [], [], [])

        assert metrics.total_shipments == 0
        assert metrics.total_bad_events == 0

    def test_confusion_matrix_values(self):
        """Test confusion matrix is computed correctly."""
        # Scores above 60 = predicted bad
        risk_scores = [80, 70, 65, 55, 40, 30]
        actuals = [True, True, False, True, False, False]
        values = [10000.0] * 6
        losses = [0.0] * 6

        metrics = compute_pilot_metrics(risk_scores, actuals, values, losses, threshold=60.0)

        # TP: 80, 70 (predicted bad, actually bad)
        # FP: 65 (predicted bad, actually good)
        # FN: 55 (predicted good, actually bad)
        # TN: 40, 30 (predicted good, actually good)
        assert metrics.confusion_matrix["tp"] == 2
        assert metrics.confusion_matrix["fp"] == 1
        assert metrics.confusion_matrix["fn"] == 1
        assert metrics.confusion_matrix["tn"] == 2


# =============================================================================
# TEST: run_retrospective_pilot()
# =============================================================================


class TestRunRetrospectivePilot:
    """Tests for the main pilot runner."""

    def test_pilot_with_list_of_dicts(self):
        """Test pilot runs with list of dictionaries input."""
        data = [
            {"shipment_id": "S001", "event_bad": True, "mode": "TRUCK", "value_usd": 10000},
            {"shipment_id": "S002", "event_bad": False, "mode": "OCEAN", "value_usd": 50000},
            {"shipment_id": "S003", "event_bad": True, "mode": "AIR", "value_usd": 5000},
            {"shipment_id": "S004", "event_bad": False, "mode": "TRUCK", "value_usd": 15000},
            {"shipment_id": "S005", "event_bad": False, "mode": "RAIL", "value_usd": 25000},
        ]

        report = run_retrospective_pilot(data, tenant_id="TEST-CORP")

        assert report.tenant_id == "TEST-CORP"
        assert report.metrics.total_shipments == 5
        assert report.metrics.total_bad_events == 2
        assert isinstance(report.risk_distribution, dict)
        assert isinstance(report.decision_distribution, dict)

    def test_pilot_distributions_sum_correctly(self):
        """Test that distributions sum to total shipments."""
        data = [{"shipment_id": f"S{i:03d}", "event_bad": i % 5 == 0, "mode": "TRUCK"} for i in range(100)]

        report = run_retrospective_pilot(data, tenant_id="TEST")

        # Risk distribution should sum to total
        risk_sum = sum(report.risk_distribution.values())
        assert risk_sum == report.metrics.total_shipments

        # Decision distribution should sum to total
        decision_sum = sum(report.decision_distribution.values())
        assert decision_sum == report.metrics.total_shipments


# =============================================================================
# TEST: build_markdown_summary()
# =============================================================================


class TestBuildMarkdownSummary:
    """Tests for markdown report generation."""

    def test_markdown_contains_key_sections(self):
        """Test markdown has required sections."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=1000,
            total_bad_events=150,
            bad_event_rate=0.15,
            auc_roc=0.78,
            lift_at_top_10pct=3.2,
            capture_rate_top_10pct=0.48,
            hypothetical_savings_usd=125000.0,
            confusion_matrix={"tp": 100, "fp": 50, "tn": 800, "fn": 50},
            threshold_used=60.0,
        )

        report = RetrospectivePilotReport(
            tenant_id="ACME-Corp",
            model_version="heuristic-v0",
            metrics=metrics,
            risk_distribution={"0-30": 500, "30-60": 300, "60-80": 150, "80-100": 50},
            decision_distribution={"APPROVE": 500, "TIGHTEN_TERMS": 300, "HOLD": 150, "ESCALATE": 50},
        )

        markdown = build_markdown_summary(report)

        # Check key sections exist
        assert "# ChainIQ Retrospective Pilot Report" in markdown
        assert "ACME-Corp" in markdown
        assert "## Overview" in markdown
        assert "## Key Metrics" in markdown
        assert "## Risk Score Distribution" in markdown
        assert "## Recommended Actions Distribution" in markdown
        assert "## What This Means for You" in markdown

        # Check metrics are rendered
        assert "1,000" in markdown  # total shipments
        assert "0.78" in markdown  # AUC-ROC
        assert "3.2x" in markdown  # lift
        assert "$125,000" in markdown  # savings

    def test_markdown_handles_missing_metrics(self):
        """Test markdown gracefully handles missing optional metrics."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=50,
            total_bad_events=0,
            bad_event_rate=0.0,
        )

        report = RetrospectivePilotReport(
            tenant_id="TEST",
            metrics=metrics,
        )

        # Should not raise
        markdown = build_markdown_summary(report)

        assert "# ChainIQ Retrospective Pilot Report" in markdown
        assert "50" in markdown

    def test_markdown_includes_notes(self):
        """Test markdown includes warning notes."""
        metrics = RetrospectivePilotMetrics(
            total_shipments=30,
            total_bad_events=3,
            bad_event_rate=0.1,
        )

        report = RetrospectivePilotReport(
            tenant_id="TEST",
            metrics=metrics,
            notes=["Small dataset (30 shipments) — metrics may be unreliable"],
        )

        markdown = build_markdown_summary(report)

        assert "## Notes & Caveats" in markdown
        assert "Small dataset" in markdown


# =============================================================================
# TEST: map_row_to_context()
# =============================================================================


class TestMapRowToContext:
    """Tests for CSV row to context mapping."""

    def test_basic_mapping(self):
        """Test basic row mapping."""
        row = {
            "shipment_id": "SHIP-001",
            "mode": "OCEAN",
            "origin_country": "CN",
            "destination_country": "US",
            "value_usd": 50000.0,
        }

        ctx = map_row_to_context(row, tenant_id="TEST")

        assert ctx.shipment_id == "SHIP-001"
        assert ctx.mode == "OCEAN"
        assert ctx.origin_country == "CN"
        assert ctx.destination_country == "US"
        assert ctx.value_usd == 50000.0
        assert ctx.tenant_id == "TEST"

    def test_handles_column_variations(self):
        """Test mapping handles common column name variations."""
        row = {
            "id": "ALT-001",  # Alternative to shipment_id
            "shipper_country": "DE",  # Alternative to origin_country
            "dest_country": "FR",  # Alternative to destination_country
            "carrier": "MAERSK",  # Alternative to carrier_code
        }

        ctx = map_row_to_context(row)

        assert ctx.shipment_id == "ALT-001"
        assert ctx.origin_country == "DE"
        assert ctx.destination_country == "FR"
        assert ctx.carrier_code == "MAERSK"

    def test_handles_missing_fields(self):
        """Test mapping handles missing fields gracefully."""
        row = {}  # Empty row

        ctx = map_row_to_context(row)

        # Should use defaults
        assert ctx.mode == "TRUCK"
        assert ctx.origin_country == "US"
        assert ctx.destination_country == "US"
        assert ctx.shipment_id.startswith("pilot-")

    def test_normalizes_mode(self):
        """Test mode is normalized to valid values."""
        for mode in ["ocean", "OCEAN", "Ocean"]:
            row = {"shipment_id": "S1", "mode": mode}
            ctx = map_row_to_context(row)
            assert ctx.mode == "OCEAN"

        # Invalid mode should default to TRUCK
        row = {"shipment_id": "S1", "mode": "CARRIER_PIGEON"}
        ctx = map_row_to_context(row)
        assert ctx.mode == "TRUCK"


# =============================================================================
# TEST: is_bad_outcome()
# =============================================================================


class TestIsBadOutcome:
    """Tests for bad outcome determination."""

    def test_event_bad_column_takes_precedence(self):
        """Test that event_bad column is used when present."""
        row = {"event_bad": True, "late_days": 0}
        assert is_bad_outcome(row) is True

        row = {"event_bad": False, "late_days": 10}
        assert is_bad_outcome(row) is False

    def test_late_delivery_detection(self):
        """Test late delivery triggers bad outcome."""
        row = {"late_days": 5}
        assert is_bad_outcome(row) is True

        row = {"late_days": 2}
        assert is_bad_outcome(row) is False

    def test_damage_claim_detection(self):
        """Test damage claim triggers bad outcome."""
        row = {"has_damage_claim": True}
        assert is_bad_outcome(row) is True

        row = {"claim_amount_usd": 1000}
        assert is_bad_outcome(row) is True


# =============================================================================
# TEST: CSV LOADER (requires pandas)
# =============================================================================


class TestCSVLoader:
    """Tests for CSV loading functionality."""

    @pytest.fixture
    def sample_csv_path(self, tmp_path):
        """Create a sample CSV file for testing."""
        csv_content = """shipment_id,event_bad,mode,origin_country,destination_country,value_usd
S001,1,TRUCK,US,US,10000
S002,0,OCEAN,CN,US,50000
S003,1,AIR,DE,US,5000
S004,0,TRUCK,US,CA,15000
S005,0,RAIL,US,MX,25000
"""
        csv_path = tmp_path / "test_pilot.csv"
        csv_path.write_text(csv_content)
        return csv_path

    def test_load_valid_csv(self, sample_csv_path):
        """Test loading a valid CSV file."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not available")

        df = load_pilot_data_from_csv(sample_csv_path)

        assert len(df) == 5
        assert "shipment_id" in df.columns
        assert "event_bad" in df.columns
        assert df["event_bad"].dtype == bool

    def test_missing_required_columns(self, tmp_path):
        """Test error on missing required columns."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not available")

        csv_content = "mode,value_usd\nTRUCK,10000\n"
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text(csv_content)

        with pytest.raises(ValueError) as excinfo:
            load_pilot_data_from_csv(csv_path)

        assert "Missing required columns" in str(excinfo.value)

    def test_file_not_found(self):
        """Test error on missing file."""
        with pytest.raises(FileNotFoundError):
            load_pilot_data_from_csv("/nonexistent/path.csv")

    def test_validate_warnings(self, tmp_path):
        """Test validation warnings."""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not available")

        # Small dataset without value column
        csv_content = """shipment_id,event_bad
S001,1
S002,0
S003,1
"""
        csv_path = tmp_path / "small.csv"
        csv_path.write_text(csv_content)

        df = load_pilot_data_from_csv(csv_path)
        warnings = validate_pilot_dataframe(df)

        assert any("Small dataset" in w for w in warnings)
        assert any("value_usd" in w for w in warnings)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
