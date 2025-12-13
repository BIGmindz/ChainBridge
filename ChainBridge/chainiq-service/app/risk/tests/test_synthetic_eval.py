import csv

from app.risk.synthetic_eval import run_synthetic_eval


def test_synthetic_eval_core_generation(tmp_path):
    """Test basic CSV generation in core mode."""
    output_file = tmp_path / "core.csv"

    # Run with a small max_rows to keep it fast, but enough to get variety
    run_synthetic_eval(mode="core", output_path=output_file, max_rows=300)

    assert output_file.exists()

    with open(output_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 20

    # Check headers
    expected_headers = {
        "scenario_id",
        "origin",
        "destination",
        "value_usd",
        "is_hazmat",
        "is_temp_control",
        "expected_transit_days",
        "iot_alert_count",
        "recent_delay_events",
        "lane_risk_index",
        "border_crossing_count",
        "carrier_incident_rate_90d",
        "carrier_tenure_days",
        "risk_score",
        "risk_band",
    }
    assert set(reader.fieldnames) == expected_headers

    # Check for band variety (assuming grid produces at least LOW and HIGH)
    bands = {row["risk_band"] for row in rows}
    assert "LOW" in bands
    assert "HIGH" in bands


def test_synthetic_eval_determinism(tmp_path):
    """Test that two runs with the same config produce identical output."""
    file1 = tmp_path / "run1.csv"
    file2 = tmp_path / "run2.csv"

    run_synthetic_eval(mode="core", output_path=file1, max_rows=50)
    run_synthetic_eval(mode="core", output_path=file2, max_rows=50)

    with open(file1, "r") as f1, open(file2, "r") as f2:
        assert f1.read() == f2.read()


def test_synthetic_eval_extended_mode_safety(tmp_path):
    """Test extended mode with max_rows cap."""
    output_file = tmp_path / "extended.csv"
    max_rows = 50

    run_synthetic_eval(mode="extended", output_path=output_file, max_rows=max_rows)

    with open(output_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == max_rows

    # Check structure matches core
    expected_headers = {
        "scenario_id",
        "origin",
        "destination",
        "value_usd",
        "is_hazmat",
        "is_temp_control",
        "expected_transit_days",
        "iot_alert_count",
        "recent_delay_events",
        "lane_risk_index",
        "border_crossing_count",
        "carrier_incident_rate_90d",
        "carrier_tenure_days",
        "risk_score",
        "risk_band",
    }
    assert set(reader.fieldnames) == expected_headers
