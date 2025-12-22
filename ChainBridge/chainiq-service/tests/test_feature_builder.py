"""Tests for feature builder."""

import pytest

from app.models.features import ShipmentFeaturesV0
from app.services.feature_builder import FeatureBuilder
from app.services.sentiment_adapter import SentimentAdapter


def test_feature_builder_basic():
    """Test that feature builder creates valid ShipmentFeaturesV0."""
    raw_shipment = {
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
    }

    builder = FeatureBuilder()
    features = builder.build_features(raw_shipment)

    # Verify it's the right type
    assert isinstance(features, ShipmentFeaturesV0)

    # Verify base fields are copied correctly
    assert features.shipment_id == "SH-TEST-001"
    assert features.corridor == "US-MX"
    assert features.mode == "truck"
    assert features.delay_flag == 1
    assert features.missing_required_docs == 1


def test_feature_builder_sentiment_injection():
    """Test that sentiment fields are correctly injected from adapter."""
    raw_shipment = {
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
    }

    builder = FeatureBuilder()
    features = builder.build_features(raw_shipment)

    # Verify sentiment fields are populated (US-MX should have negative sentiment)
    assert features.lane_sentiment_score is not None
    assert features.lane_sentiment_score == pytest.approx(0.30, abs=0.01)
    assert features.macro_logistics_sentiment_score == pytest.approx(0.45, abs=0.01)
    assert features.sentiment_trend_7d == pytest.approx(-0.10, abs=0.01)
    assert features.sentiment_volatility_30d == pytest.approx(0.20, abs=0.01)
    assert features.sentiment_provider == "SentimentVendor_stub_v0"


def test_feature_builder_different_corridor():
    """Test that different corridors get different sentiment values."""
    raw_shipment = {
        "shipment_id": "SH-TEST-003",
        "corridor": "CN-NL",  # Different corridor
        "origin_country": "CN",
        "destination_country": "NL",
        "mode": "ocean",
        "commodity_category": "textiles",
        "financing_type": "OA",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 720.0,
        "eta_deviation_hours": 0.0,
        "num_route_deviations": 0,
        "max_route_deviation_km": 0.0,
        "total_dwell_hours": 12.0,
        "max_single_dwell_hours": 8.0,
        "handoff_count": 5,
        "max_custody_gap_hours": 1.0,
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
    }

    builder = FeatureBuilder()
    features = builder.build_features(raw_shipment)

    # CN-NL should have more positive sentiment
    assert features.lane_sentiment_score == pytest.approx(0.55, abs=0.01)
    assert features.macro_logistics_sentiment_score == pytest.approx(0.60, abs=0.01)
    assert features.sentiment_trend_7d == pytest.approx(0.05, abs=0.01)


def test_feature_builder_custom_adapter():
    """Test that feature builder can use a custom sentiment adapter."""
    custom_adapter = SentimentAdapter(provider_name="CustomProvider_v2")

    raw_shipment = {
        "shipment_id": "SH-TEST-004",
        "corridor": "DE-US",
        "origin_country": "DE",
        "destination_country": "US",
        "mode": "air",
        "commodity_category": "machinery",
        "financing_type": "DP",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 24.0,
        "eta_deviation_hours": 0.0,
        "num_route_deviations": 0,
        "max_route_deviation_km": 0.0,
        "total_dwell_hours": 2.0,
        "max_single_dwell_hours": 1.0,
        "handoff_count": 2,
        "max_custody_gap_hours": 0.5,
        "delay_flag": 0,
        "has_iot_telemetry": 0,
        "doc_count": 10,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 1.5,
        "collateral_value": 750000.0,
        "collateral_value_bucket": "high",
        "shipper_on_time_pct_90d": 0.98,
        "carrier_on_time_pct_90d": 0.96,
        "corridor_disruption_index_90d": 0.10,
        "prior_exceptions_count_180d": 0,
        "prior_losses_flag": 0,
    }

    builder = FeatureBuilder(sentiment_adapter=custom_adapter)
    features = builder.build_features(raw_shipment)

    # Verify custom provider name is used
    assert features.sentiment_provider == "CustomProvider_v2"


def test_feature_builder_optional_fields():
    """Test that optional fields can be None."""
    raw_shipment = {
        "shipment_id": "SH-TEST-005",
        "corridor": "US-CA",
        "origin_country": "US",
        "destination_country": "CA",
        "mode": "truck",
        "commodity_category": "food",
        "financing_type": "OA",
        "counterparty_risk_bucket": "low",
        "planned_transit_hours": 36.0,
        "actual_transit_hours": None,  # Still in transit
        "eta_deviation_hours": 0.0,
        "num_route_deviations": 0,
        "max_route_deviation_km": 0.0,
        "total_dwell_hours": 1.0,
        "max_single_dwell_hours": 1.0,
        "handoff_count": 2,
        "max_custody_gap_hours": 0.5,
        "delay_flag": 0,
        "has_iot_telemetry": 0,  # No IoT, so temp fields will be None
        "doc_count": 8,
        "missing_required_docs": 0,
        "duplicate_doc_flag": 0,
        "doc_inconsistency_flag": 0,
        "doc_age_days": 1.0,
        "collateral_value": 100000.0,
        "collateral_value_bucket": "low",
        "shipper_on_time_pct_90d": 0.92,
        "carrier_on_time_pct_90d": 0.94,
        "corridor_disruption_index_90d": 0.12,
        "prior_exceptions_count_180d": 0,
        "prior_losses_flag": 0,
    }

    builder = FeatureBuilder()
    features = builder.build_features(raw_shipment)

    # Verify optional fields can be None
    assert features.actual_transit_hours is None
    assert features.temp_mean is None
    assert features.temp_std is None
    assert features.realized_loss_flag is None
    assert features.fraud_confirmed is None
