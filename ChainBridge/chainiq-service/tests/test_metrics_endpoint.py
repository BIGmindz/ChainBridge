"""Tests for Prometheus /metrics endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_metrics_endpoint_exists():
    """Test that /metrics endpoint exists and returns Prometheus format."""
    response = client.get("/metrics")
    assert response.status_code == 200

    # Verify it's Prometheus format (should start with # HELP or have metrics)
    content = response.text
    assert "# HELP" in content or "# TYPE" in content, "Expected Prometheus exposition format"


def test_metrics_endpoint_content_type():
    """Test that /metrics returns correct content type."""
    response = client.get("/metrics")
    assert response.status_code == 200

    # Prometheus uses text/plain with version parameter
    assert "text/plain" in response.headers.get("content-type", "")


def test_custom_metrics_present_after_call():
    """Test that custom ChainIQ metrics appear in /metrics after making requests."""
    # Make a risk-score call first
    payload = {
        "shipment_id": "SH-PROM-001",
        "corridor": "US-MX",
        "origin_country": "US",
        "destination_country": "MX",
        "mode": "truck",
        "commodity_category": "electronics",
        "financing_type": "LC",
        "counterparty_risk_bucket": "medium",
        "planned_transit_hours": 48.0,
        "actual_transit_hours": 52.5,
        "eta_deviation_hours": 4.5,
        "num_route_deviations": 1,
        "max_route_deviation_km": 12.3,
        "total_dwell_hours": 6.0,
        "max_single_dwell_hours": 3.5,
        "handoff_count": 3,
        "max_custody_gap_hours": 2.0,
        "delay_flag": 1,
        "has_iot_telemetry": 1,
        "temp_mean": 22.5,
        "temp_std": 1.8,
        "temp_min": 18.0,
        "temp_max": 26.0,
        "temp_out_of_range_pct": 0.02,
        "sensor_uptime_pct": 0.98,
        "doc_count": 12,
        "missing_required_docs": 1,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 3.2,
        "collateral_value": 250000.0,
        "collateral_value_bucket": "medium",
        "shipper_on_time_pct_90d": 0.87,
        "carrier_on_time_pct_90d": 0.91,
        "corridor_disruption_index_90d": 0.35,
        "prior_exceptions_count_180d": 2,
        "prior_losses_flag": 0,
        "lane_sentiment_score": 0.30,
        "macro_logistics_sentiment_score": 0.45,
        "sentiment_trend_7d": -0.10,
        "sentiment_volatility_30d": 0.20,
        "sentiment_provider": "SentimentVendor_stub_v0",
    }

    risk_response = client.post("/iq/ml/risk-score", json=payload)
    assert risk_response.status_code == 200

    # Now check /metrics
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200

    content = metrics_response.text

    # Verify our custom metrics are present
    assert "chainiq_risk_requests_total" in content, "Expected chainiq_risk_requests_total metric"
    assert "chainiq_anomaly_requests_total" in content, "Expected chainiq_anomaly_requests_total metric"
    assert "chainiq_risk_request_duration_seconds" in content, "Expected chainiq_risk_request_duration_seconds metric"
    assert "chainiq_anomaly_request_duration_seconds" in content, "Expected chainiq_anomaly_request_duration_seconds metric"


def test_metrics_includes_corridor_label():
    """Test that metrics include corridor label."""
    # Make an anomaly call with a specific corridor
    payload = {
        "shipment_id": "SH-PROM-002",
        "corridor": "EU-US",
        "origin_country": "DE",
        "destination_country": "US",
        "mode": "ocean",
        "commodity_category": "automotive",
        "financing_type": "LC",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 240.0,
        "actual_transit_hours": 245.0,
        "eta_deviation_hours": 5.0,
        "num_route_deviations": 0,
        "max_route_deviation_km": 0.0,
        "total_dwell_hours": 12.0,
        "max_single_dwell_hours": 8.0,
        "handoff_count": 4,
        "max_custody_gap_hours": 3.0,
        "delay_flag": 0,
        "has_iot_telemetry": 1,
        "temp_mean": 21.0,
        "temp_std": 1.5,
        "temp_min": 18.0,
        "temp_max": 24.0,
        "temp_out_of_range_pct": 0.01,
        "sensor_uptime_pct": 0.99,
        "doc_count": 20,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 2.5,
        "collateral_value": 500000.0,
        "collateral_value_bucket": "high",
        "shipper_on_time_pct_90d": 0.94,
        "carrier_on_time_pct_90d": 0.92,
        "corridor_disruption_index_90d": 0.15,
        "prior_exceptions_count_180d": 0,
        "prior_losses_flag": 0,
        "lane_sentiment_score": 0.85,
        "macro_logistics_sentiment_score": 0.80,
        "sentiment_trend_7d": 0.05,
        "sentiment_volatility_30d": 0.08,
        "sentiment_provider": "SentimentVendor_stub_v0",
    }

    anomaly_response = client.post("/iq/ml/anomaly", json=payload)
    assert anomaly_response.status_code == 200

    # Check metrics
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200

    content = metrics_response.text

    # Verify corridor label is present in metrics
    assert 'corridor="EU-US"' in content or 'corridor="US-MX"' in content, "Expected corridor label in metrics"


def test_debug_metrics_still_works():
    """Test that legacy /iq/ml/debug/metrics endpoint still works."""
    response = client.get("/iq/ml/debug/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "risk_calls_total" in data
    assert "anomaly_calls_total" in data
    assert isinstance(data["risk_calls_total"], int)
    assert isinstance(data["anomaly_calls_total"], int)
