"""Tests for ChainIQ ML observability and metrics."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.metrics import metrics

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics counters before each test."""
    metrics.risk_calls_total = 0
    metrics.anomaly_calls_total = 0
    yield
    # Clean up after test
    metrics.risk_calls_total = 0
    metrics.anomaly_calls_total = 0


def test_risk_score_increments_metrics():
    """Test that calling /iq/ml/risk-score increments metrics counter."""
    initial_count = metrics.risk_calls_total

    payload = {
        "shipment_id": "SH-OBS-001",
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
        "lane_sentiment_score": 0.65,
        "macro_logistics_sentiment_score": 0.55,
        "sentiment_trend_7d": -0.05,
        "sentiment_volatility_30d": 0.15,
        "sentiment_provider": "SentimentVendor_stub_v0",
        "geopolitical_risk_90d": 0.30,
        "recent_audit_flag": 0,
        "last_audit_score": 0.88,
    }

    response = client.post("/iq/ml/risk-score", json=payload)
    assert response.status_code == 200

    # Verify metrics counter incremented
    assert metrics.risk_calls_total == initial_count + 1
    # Verify anomaly counter did not increment
    assert metrics.anomaly_calls_total == 0


def test_anomaly_score_increments_metrics():
    """Test that calling /iq/ml/anomaly increments metrics counter."""
    initial_count = metrics.anomaly_calls_total

    payload = {
        "shipment_id": "SH-OBS-002",
        "corridor": "US-CA",
        "origin_country": "US",
        "destination_country": "CA",
        "mode": "truck",
        "commodity_category": "machinery",
        "financing_type": "OA",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 72.0,
        "actual_transit_hours": 75.0,
        "eta_deviation_hours": 3.0,
        "num_route_deviations": 3,
        "max_route_deviation_km": 45.0,
        "total_dwell_hours": 30.0,
        "max_single_dwell_hours": 26.0,
        "handoff_count": 2,
        "max_custody_gap_hours": 14.0,
        "delay_flag": 0,
        "has_iot_telemetry": 1,
        "temp_mean": 20.0,
        "temp_std": 2.5,
        "temp_min": 15.0,
        "temp_max": 25.0,
        "temp_out_of_range_pct": 0.15,
        "sensor_uptime_pct": 0.95,
        "doc_count": 10,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 2.0,
        "collateral_value": 150000.0,
        "collateral_value_bucket": "low",
        "shipper_on_time_pct_90d": 0.92,
        "carrier_on_time_pct_90d": 0.89,
        "corridor_disruption_index_90d": 0.25,
        "prior_exceptions_count_180d": 1,
        "prior_losses_flag": 0,
        "lane_sentiment_score": 0.75,
        "macro_logistics_sentiment_score": 0.70,
        "sentiment_trend_7d": 0.02,
        "sentiment_volatility_30d": 0.10,
        "sentiment_provider": "SentimentVendor_stub_v0",
        "geopolitical_risk_90d": 0.20,
        "recent_audit_flag": 1,
        "last_audit_score": 0.95,
    }

    response = client.post("/iq/ml/anomaly", json=payload)
    assert response.status_code == 200

    # Verify metrics counter incremented
    assert metrics.anomaly_calls_total == initial_count + 1
    # Verify risk counter did not increment
    assert metrics.risk_calls_total == 0


def test_metrics_endpoint():
    """Test that /iq/ml/debug/metrics returns current counters."""
    # Make a few calls to endpoints
    payload = {
        "shipment_id": "SH-OBS-003",
        "corridor": "US-MX",
        "origin_country": "US",
        "destination_country": "MX",
        "mode": "truck",
        "commodity_category": "textiles",
        "financing_type": "LC",
        "counterparty_risk_bucket": "high",
        "planned_transit_hours": 60.0,
        "actual_transit_hours": 62.0,
        "eta_deviation_hours": 2.0,
        "num_route_deviations": 0,
        "max_route_deviation_km": 0.0,
        "total_dwell_hours": 5.0,
        "max_single_dwell_hours": 3.0,
        "handoff_count": 2,
        "max_custody_gap_hours": 1.5,
        "delay_flag": 0,
        "has_iot_telemetry": 0,
        "temp_mean": None,
        "temp_std": None,
        "temp_min": None,
        "temp_max": None,
        "temp_out_of_range_pct": None,
        "sensor_uptime_pct": None,
        "doc_count": 15,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 1.5,
        "collateral_value": 100000.0,
        "collateral_value_bucket": "low",
        "shipper_on_time_pct_90d": 0.85,
        "carrier_on_time_pct_90d": 0.88,
        "corridor_disruption_index_90d": 0.40,
        "prior_exceptions_count_180d": 3,
        "prior_losses_flag": 1,
        "lane_sentiment_score": 0.55,
        "macro_logistics_sentiment_score": 0.50,
        "sentiment_trend_7d": -0.08,
        "sentiment_volatility_30d": 0.25,
        "sentiment_provider": "SentimentVendor_stub_v0",
        "geopolitical_risk_90d": 0.45,
        "recent_audit_flag": 0,
        "last_audit_score": 0.80,
    }

    client.post("/iq/ml/risk-score", json=payload)
    client.post("/iq/ml/risk-score", json=payload)
    client.post("/iq/ml/anomaly", json=payload)

    # Check metrics endpoint
    response = client.get("/iq/ml/debug/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "risk_calls_total" in data
    assert "anomaly_calls_total" in data
    assert data["risk_calls_total"] == 2
    assert data["anomaly_calls_total"] == 1


def test_logging_captures_prediction_events(caplog):
    """Test that prediction events are logged with structured data."""
    caplog.set_level(logging.INFO, logger="app.observability")

    payload = {
        "shipment_id": "SH-OBS-LOG",
        "corridor": "EU-US",
        "origin_country": "DE",
        "destination_country": "US",
        "mode": "ocean",
        "commodity_category": "automotive",
        "financing_type": "LC",
        "counterparty_risk_bucket": "medium",
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
        "geopolitical_risk_90d": 0.10,
        "recent_audit_flag": 1,
        "last_audit_score": 0.96,
    }

    response = client.post("/iq/ml/risk-score", json=payload)
    assert response.status_code == 200

    # Check that log records exist
    # Note: We're being lenient here - just checking that logging happened
    # Don't assert exact format since it can vary based on logging config
    assert len(caplog.records) > 0

    # Look for the iq_prediction log message
    prediction_logs = [r for r in caplog.records if "iq_prediction" in r.message]
    assert len(prediction_logs) > 0, "Expected at least one iq_prediction log record"


def test_timing_logs_are_generated(caplog):
    """Test that prediction events are logged (timing is now handled by Prometheus)."""
    caplog.set_level(logging.INFO, logger="app.observability")

    payload = {
        "shipment_id": "SH-OBS-TIME",
        "corridor": "CN-US",
        "origin_country": "CN",
        "destination_country": "US",
        "mode": "ocean",
        "commodity_category": "consumer_goods",
        "financing_type": "OA",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 300.0,
        "actual_transit_hours": 305.0,
        "eta_deviation_hours": 5.0,
        "num_route_deviations": 1,
        "max_route_deviation_km": 8.0,
        "total_dwell_hours": 20.0,
        "max_single_dwell_hours": 12.0,
        "handoff_count": 5,
        "max_custody_gap_hours": 4.0,
        "delay_flag": 0,
        "has_iot_telemetry": 1,
        "temp_mean": 19.0,
        "temp_std": 2.0,
        "temp_min": 15.0,
        "temp_max": 23.0,
        "temp_out_of_range_pct": 0.03,
        "sensor_uptime_pct": 0.97,
        "doc_count": 18,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 3.0,
        "collateral_value": 300000.0,
        "collateral_value_bucket": "medium",
        "shipper_on_time_pct_90d": 0.90,
        "carrier_on_time_pct_90d": 0.88,
        "corridor_disruption_index_90d": 0.30,
        "prior_exceptions_count_180d": 1,
        "prior_losses_flag": 0,
        "lane_sentiment_score": 0.70,
        "macro_logistics_sentiment_score": 0.65,
        "sentiment_trend_7d": -0.03,
        "sentiment_volatility_30d": 0.18,
        "sentiment_provider": "SentimentVendor_stub_v0",
        "geopolitical_risk_90d": 0.25,
        "recent_audit_flag": 0,
        "last_audit_score": 0.85,
    }

    response = client.post("/iq/ml/anomaly", json=payload)
    assert response.status_code == 200

    # Timing is now handled by Prometheus histograms, not logs
    # Verify that prediction event was still logged
    prediction_logs = [r for r in caplog.records if "iq_prediction" in r.message]
    assert len(prediction_logs) > 0, "Expected at least one iq_prediction log record"
