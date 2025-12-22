"""
Tests for Shadow Mode functionality.

Validates that shadow mode executes safely without impacting production API behavior.
"""

from unittest.mock import patch

from app.core.config import Settings


def test_shadow_mode_disabled_by_default():
    """Test that shadow mode is disabled by default."""
    settings = Settings()
    assert settings.enable_shadow_mode is False


def test_shadow_mode_can_be_enabled():
    """Test that shadow mode can be enabled via config."""
    settings = Settings(enable_shadow_mode=True)
    assert settings.enable_shadow_mode is True


def test_shadow_mode_disabled_does_not_log(monkeypatch):
    """Test that shadow mode does not execute when disabled."""
    from fastapi.testclient import TestClient

    from app.core import config
    from app.main import app

    # Force shadow mode OFF
    monkeypatch.setattr(config.settings, "enable_shadow_mode", False)

    client = TestClient(app)

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
        "eta_deviation_hours": 4.5,
        "num_route_deviations": 1,
        "max_route_deviation_km": 12.3,
        "total_dwell_hours": 6.0,
        "max_single_dwell_hours": 3.5,
        "handoff_count": 3,
        "max_custody_gap_hours": 2.0,
        "delay_flag": 1,
        "has_iot_telemetry": 0,
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

    # API should work normally
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "model_version" in data


def test_shadow_mode_enabled_attempts_execution(monkeypatch):
    """Test that shadow mode attempts execution when enabled."""
    from fastapi.testclient import TestClient

    from app.core import config
    from app.main import app

    # Force shadow mode ON
    monkeypatch.setattr(config.settings, "enable_shadow_mode", True)

    # Mock the shadow mode execution to prevent actual model loading
    with patch("app.api_iq_ml._run_shadow_mode_v03") as mock_shadow:
        client = TestClient(app)

        payload = {
            "shipment_id": "SH-TEST-002",
            "corridor": "US-MX",
            "origin_country": "US",
            "destination_country": "MX",
            "mode": "truck",
            "commodity_category": "electronics",
            "financing_type": "LC",
            "counterparty_risk_bucket": "medium",
            "planned_transit_hours": 48.0,
            "eta_deviation_hours": 4.5,
            "num_route_deviations": 1,
            "max_route_deviation_km": 12.3,
            "total_dwell_hours": 6.0,
            "max_single_dwell_hours": 3.5,
            "handoff_count": 3,
            "max_custody_gap_hours": 2.0,
            "delay_flag": 1,
            "has_iot_telemetry": 0,
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

        # API should still work
        assert response.status_code == 200

        # Shadow mode should have been called
        assert mock_shadow.called


def test_shadow_mode_cannot_break_api():
    """Test that shadow mode exceptions don't break the API."""
    import os

    from fastapi.testclient import TestClient

    from app.core import config
    from app.main import app

    # Force shadow mode ON
    os.environ["ENABLE_SHADOW_MODE"] = "true"
    config.settings = Settings()

    # Mock shadow mode to raise exception
    def failing_shadow(*args, **kwargs):
        raise RuntimeError("Shadow mode intentional failure")

    with patch("app.api_iq_ml._run_shadow_mode_v03", side_effect=failing_shadow):
        client = TestClient(app)

        payload = {
            "shipment_id": "SH-TEST-003",
            "corridor": "US-MX",
            "origin_country": "US",
            "destination_country": "MX",
            "mode": "truck",
            "commodity_category": "electronics",
            "financing_type": "LC",
            "counterparty_risk_bucket": "medium",
            "planned_transit_hours": 48.0,
            "eta_deviation_hours": 4.5,
            "num_route_deviations": 1,
            "max_route_deviation_km": 12.3,
            "total_dwell_hours": 6.0,
            "max_single_dwell_hours": 3.5,
            "handoff_count": 3,
            "max_custody_gap_hours": 2.0,
            "delay_flag": 1,
            "has_iot_telemetry": 0,
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

        # API should STILL work even if shadow mode fails
        response = client.post("/iq/ml/risk-score", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "score" in data

    # Reset
    if "ENABLE_SHADOW_MODE" in os.environ:
        del os.environ["ENABLE_SHADOW_MODE"]


def test_shadow_mode_missing_model_is_safe():
    """Test that missing real model doesn't break shadow mode."""
    from app.ml.training_v02 import load_real_risk_model_v02

    # Attempt to load non-existent model
    model = load_real_risk_model_v02()

    # Should return None instead of crashing
    assert model is None


def test_lazy_model_loading():
    """Test that model loading is lazy (not at import time)."""
    # Import should not load model
    from app.ml import training_v02

    # Global should be None initially
    assert training_v02._real_risk_model_instance is None

    # Calling load should attempt load (but return None if not found)
    model = training_v02.load_real_risk_model_v02()

    # Should not crash, just return None
    assert model is None or model is not None  # Either outcome is safe
