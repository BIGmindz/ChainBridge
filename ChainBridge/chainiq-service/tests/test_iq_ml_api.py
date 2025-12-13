"""Tests for ChainIQ ML API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_risk_score_endpoint_basic():
    """Test that /iq/ml/risk-score accepts valid payload and returns expected structure."""
    payload = {
        "shipment_id": "SH-TEST-001",
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

    response = client.post("/iq/ml/risk-score", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "score" in data
    assert "explanation" in data
    assert "model_version" in data

    # Verify types
    assert isinstance(data["score"], float)
    assert isinstance(data["explanation"], list)
    assert isinstance(data["model_version"], str)

    # Verify score is in valid range
    assert 0.0 <= data["score"] <= 1.0

    # Verify explanation is non-empty and has correct structure
    assert len(data["explanation"]) > 0
    for contrib in data["explanation"]:
        assert "feature" in contrib
        assert "reason" in contrib
        assert isinstance(contrib["feature"], str)
        assert isinstance(contrib["reason"], str)

    # Verify model version
    assert data["model_version"] == "0.1.0"  # DummyRiskModel version


def test_risk_score_high_risk_scenario():
    """
    Test that high-risk shipments get appropriately high scores.

    DummyRiskModel logic:
    - Base: 0.2
    - +0.3 if delay_flag = 1
    - +0.3 if prior_losses_flag = 1
    - Max: 0.8 (both flags set)
    """
    payload = {
        "shipment_id": "SH-HIGHRISK-001",
        "corridor": "US-MX",
        "origin_country": "US",
        "destination_country": "MX",
        "mode": "truck",
        "commodity_category": "electronics",
        "financing_type": "OA",
        "counterparty_risk_bucket": "high",
        "planned_transit_hours": 48.0,
        "actual_transit_hours": 96.0,
        "eta_deviation_hours": 48.0,
        "num_route_deviations": 5,
        "max_route_deviation_km": 150.0,
        "total_dwell_hours": 72.0,
        "max_single_dwell_hours": 48.0,
        "handoff_count": 8,
        "max_custody_gap_hours": 24.0,
        "delay_flag": 1,
        "has_iot_telemetry": 0,
        "doc_count": 5,
        "missing_required_docs": 3,
        "duplicate_doc_flag": 1,
        "doc_inconsistency_flag": 1,
        "doc_age_days": 15.0,
        "collateral_value": 50000.0,
        "collateral_value_bucket": "low",
        "shipper_on_time_pct_90d": 0.45,
        "carrier_on_time_pct_90d": 0.50,
        "corridor_disruption_index_90d": 0.85,
        "prior_exceptions_count_180d": 12,
        "prior_losses_flag": 1,
        "lane_sentiment_score": 0.15,
        "macro_logistics_sentiment_score": 0.25,
        "sentiment_trend_7d": -0.30,
        "sentiment_volatility_30d": 0.50,
        "sentiment_provider": "SentimentVendor_stub_v0",
    }

    response = client.post("/iq/ml/risk-score", json=payload)

    assert response.status_code == 200
    data = response.json()

    # High-risk scenario: both delay_flag and prior_losses_flag set
    # DummyRiskModel: 0.2 + 0.3 + 0.3 = 0.8
    assert data["score"] == 0.8


def test_anomaly_endpoint_basic():
    """Test that /iq/ml/anomaly accepts valid payload and returns expected structure."""
    payload = {
        "shipment_id": "SH-TEST-002",
        "corridor": "CN-NL",
        "origin_country": "CN",
        "destination_country": "NL",
        "mode": "ocean",
        "commodity_category": "textiles",
        "financing_type": "LC",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 720.0,
        "actual_transit_hours": 725.0,
        "eta_deviation_hours": 5.0,
        "num_route_deviations": 0,
        "max_route_deviation_km": 0.0,
        "total_dwell_hours": 12.0,
        "max_single_dwell_hours": 8.0,
        "handoff_count": 5,
        "max_custody_gap_hours": 2.0,
        "delay_flag": 0,
        "has_iot_telemetry": 1,
        "temp_mean": 20.0,
        "temp_std": 1.0,
        "temp_min": 18.0,
        "temp_max": 22.0,
        "temp_out_of_range_pct": 0.0,
        "sensor_uptime_pct": 1.0,
        "doc_count": 15,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 2.0,
        "collateral_value": 500000.0,
        "collateral_value_bucket": "high",
        "shipper_on_time_pct_90d": 0.95,
        "carrier_on_time_pct_90d": 0.93,
        "corridor_disruption_index_90d": 0.15,
        "prior_exceptions_count_180d": 0,
        "prior_losses_flag": 0,
        "lane_sentiment_score": 0.55,
        "macro_logistics_sentiment_score": 0.60,
        "sentiment_trend_7d": 0.05,
        "sentiment_volatility_30d": 0.12,
        "sentiment_provider": "SentimentVendor_stub_v0",
    }

    response = client.post("/iq/ml/anomaly", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "score" in data
    assert "explanation" in data
    assert "model_version" in data

    # Verify types
    assert isinstance(data["score"], float)
    assert isinstance(data["explanation"], list)
    assert isinstance(data["model_version"], str)

    # Verify score is in valid range
    assert 0.0 <= data["score"] <= 1.0

    # Verify explanation is non-empty and has correct structure
    assert len(data["explanation"]) > 0
    for contrib in data["explanation"]:
        assert "feature" in contrib
        assert "reason" in contrib
        assert isinstance(contrib["feature"], str)
        assert isinstance(contrib["reason"], str)

    # Verify model version
    assert data["model_version"] == "0.1.0"  # DummyAnomalyModel version


def test_anomaly_high_anomaly_scenario():
    """
    Test that highly anomalous shipments get high anomaly scores.

    DummyAnomalyModel logic:
    - Base: 0.1
    - +0.4 if max_single_dwell_hours > 12
    - +0.3 if eta_deviation_hours > 6
    - Max: 0.8 (both conditions met)
    """
    payload = {
        "shipment_id": "SH-ANOMALOUS-001",
        "corridor": "US-CA",
        "origin_country": "US",
        "destination_country": "CA",
        "mode": "truck",
        "commodity_category": "food",
        "financing_type": "LC",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 24.0,
        "actual_transit_hours": 96.0,
        "eta_deviation_hours": 72.0,  # > 6, triggers +0.3
        "num_route_deviations": 8,
        "max_route_deviation_km": 500.0,
        "total_dwell_hours": 120.0,
        "max_single_dwell_hours": 96.0,  # > 12, triggers +0.4
        "handoff_count": 15,
        "max_custody_gap_hours": 48.0,
        "delay_flag": 1,
        "has_iot_telemetry": 1,
        "temp_mean": 35.0,
        "temp_std": 10.0,
        "temp_min": 5.0,
        "temp_max": 50.0,
        "temp_out_of_range_pct": 0.75,
        "sensor_uptime_pct": 0.50,
        "doc_count": 3,
        "missing_required_docs": 2,
        "duplicate_doc_flag": 1,
        "doc_inconsistency_flag": 1,
        "doc_age_days": 30.0,
        "collateral_value": 10000.0,
        "collateral_value_bucket": "low",
        "shipper_on_time_pct_90d": 0.30,
        "carrier_on_time_pct_90d": 0.35,
        "corridor_disruption_index_90d": 0.90,
        "prior_exceptions_count_180d": 20,
        "prior_losses_flag": 1,
        "lane_sentiment_score": 0.10,
        "macro_logistics_sentiment_score": 0.15,
        "sentiment_trend_7d": -0.40,
        "sentiment_volatility_30d": 0.80,
        "sentiment_provider": "SentimentVendor_stub_v0",
    }

    response = client.post("/iq/ml/anomaly", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Highly anomalous scenario: both dwell > 12h and eta_deviation > 6h
    # DummyAnomalyModel: 0.1 + 0.4 + 0.3 = 0.8
    assert data["score"] == 0.8


def test_risk_score_missing_required_field():
    """Test that endpoint returns 422 for missing required fields."""
    payload = {
        "shipment_id": "SH-INCOMPLETE-001",
        "corridor": "US-MX",
        # Missing many required fields
    }

    response = client.post("/iq/ml/risk-score", json=payload)

    assert response.status_code == 422  # Validation error


def test_anomaly_missing_required_field():
    """Test that anomaly endpoint returns 422 for missing required fields."""
    payload = {
        "shipment_id": "SH-INCOMPLETE-002",
        # Missing all other required fields
    }

    response = client.post("/iq/ml/anomaly", json=payload)

    assert response.status_code == 422  # Validation error
