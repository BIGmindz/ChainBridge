"""Tests for ChainIQ ML interfaces and dummy models."""

import pytest

from app.ml.base import BaseAnomalyModel, BaseRiskModel, ModelPrediction
from app.ml.dummy_models import DummyAnomalyModel, DummyRiskModel
from app.models.features import ShipmentFeaturesV0


def create_minimal_shipment_features() -> ShipmentFeaturesV0:
    """Create a minimal valid ShipmentFeaturesV0 for testing."""
    return ShipmentFeaturesV0(
        # Identifiers & context
        shipment_id="TEST-001",
        corridor="US-MX",
        origin_country="US",
        destination_country="MX",
        mode="truck",
        commodity_category="electronics",
        financing_type="LC",
        counterparty_risk_bucket="medium",
        # Operational / transit
        planned_transit_hours=48.0,
        actual_transit_hours=52.0,
        eta_deviation_hours=4.0,
        num_route_deviations=0,
        max_route_deviation_km=0.0,
        total_dwell_hours=2.0,
        max_single_dwell_hours=1.5,
        handoff_count=2,
        max_custody_gap_hours=0.5,
        delay_flag=0,
        # IoT / temperature
        has_iot_telemetry=1,
        temp_mean=22.0,
        temp_std=1.5,
        temp_min=20.0,
        temp_max=24.0,
        temp_out_of_range_pct=0.0,
        sensor_uptime_pct=1.0,
        # Documentation
        doc_count=10,
        missing_required_docs=0,
        duplicate_doc_flag=0,
        doc_inconsistency_flag=0,
        doc_age_days=2.0,
        collateral_value=100000.0,
        collateral_value_bucket="medium",
        # Historical performance
        shipper_on_time_pct_90d=0.95,
        carrier_on_time_pct_90d=0.93,
        corridor_disruption_index_90d=0.2,
        prior_exceptions_count_180d=0,
        prior_losses_flag=0,
        # Sentiment
        sentiment_macro_score=0.6,
        sentiment_corridor_score=0.65,
        sentiment_counterparty_score=0.7,
        sentiment_stability_metric=0.8,
        sentiment_trade_friction_index=0.3,
        lane_sentiment_score=0.65,
        macro_logistics_sentiment_score=0.6,
        sentiment_trend_7d=0.05,
        sentiment_volatility_30d=0.15,
        sentiment_provider="test_provider",
    )


def test_model_prediction_instantiation():
    """Test that ModelPrediction can be instantiated."""
    from app.models.scoring import FeatureContribution

    pred = ModelPrediction(
        score=0.42,
        explanation=[
            FeatureContribution(
                feature="delay_flag",
                reason="Shipment is delayed",
            )
        ],
        model_version="test_v1.0.0",
    )

    assert pred.score == 0.42
    assert len(pred.explanation) == 1
    assert pred.model_version == "test_v1.0.0"


def test_dummy_risk_model_basic():
    """Test that DummyRiskModel can predict on valid features."""
    model = DummyRiskModel()
    features = create_minimal_shipment_features()

    prediction = model.predict(features)

    # Check contract compliance
    assert isinstance(prediction, ModelPrediction)
    assert 0.0 <= prediction.score <= 1.0
    assert len(prediction.explanation) > 0
    assert prediction.model_version == "0.1.0"


def test_dummy_risk_model_delay_logic():
    """Test that DummyRiskModel increases score when delay_flag is set."""
    model = DummyRiskModel()
    features = create_minimal_shipment_features()

    # Baseline score (no delay, no prior losses)
    features.delay_flag = 0
    features.prior_losses_flag = 0
    baseline_pred = model.predict(features)

    # Score with delay
    features.delay_flag = 1
    delayed_pred = model.predict(features)

    assert delayed_pred.score > baseline_pred.score


def test_dummy_risk_model_prior_losses_logic():
    """Test that DummyRiskModel increases score when prior_losses_flag is set."""
    model = DummyRiskModel()
    features = create_minimal_shipment_features()

    # Baseline score
    features.delay_flag = 0
    features.prior_losses_flag = 0
    baseline_pred = model.predict(features)

    # Score with prior losses
    features.prior_losses_flag = 1
    loss_pred = model.predict(features)

    assert loss_pred.score > baseline_pred.score


def test_dummy_anomaly_model_basic():
    """Test that DummyAnomalyModel can predict on valid features."""
    model = DummyAnomalyModel()
    features = create_minimal_shipment_features()

    prediction = model.predict(features)

    # Check contract compliance
    assert isinstance(prediction, ModelPrediction)
    assert 0.0 <= prediction.score <= 1.0
    assert len(prediction.explanation) > 0
    assert prediction.model_version == "0.1.0"


def test_dummy_anomaly_model_dwell_logic():
    """Test that DummyAnomalyModel increases score for long dwell times."""
    model = DummyAnomalyModel()
    features = create_minimal_shipment_features()

    # Baseline score (normal dwell)
    features.max_single_dwell_hours = 2.0
    baseline_pred = model.predict(features)

    # Score with long dwell
    features.max_single_dwell_hours = 15.0
    dwell_pred = model.predict(features)

    assert dwell_pred.score > baseline_pred.score


def test_dummy_anomaly_model_eta_deviation_logic():
    """Test that DummyAnomalyModel increases score for large ETA deviations."""
    model = DummyAnomalyModel()
    features = create_minimal_shipment_features()

    # Baseline score (small deviation)
    features.eta_deviation_hours = 2.0
    baseline_pred = model.predict(features)

    # Score with large deviation
    features.eta_deviation_hours = 10.0
    deviation_pred = model.predict(features)

    assert deviation_pred.score > baseline_pred.score


def test_base_classes_are_abstract():
    """Test that base classes cannot be instantiated directly."""
    # BaseRiskModel is abstract, should not be instantiable
    with pytest.raises(TypeError):
        BaseRiskModel()  # type: ignore

    # BaseAnomalyModel is abstract, should not be instantiable
    with pytest.raises(TypeError):
        BaseAnomalyModel()  # type: ignore


def test_dummy_models_are_deterministic():
    """Test that dummy models return consistent predictions for same input."""
    risk_model = DummyRiskModel()
    anomaly_model = DummyAnomalyModel()
    features = create_minimal_shipment_features()

    # Get predictions twice
    risk_pred_1 = risk_model.predict(features)
    risk_pred_2 = risk_model.predict(features)

    anomaly_pred_1 = anomaly_model.predict(features)
    anomaly_pred_2 = anomaly_model.predict(features)

    # Should be identical
    assert risk_pred_1.score == risk_pred_2.score
    assert anomaly_pred_1.score == anomaly_pred_2.score
