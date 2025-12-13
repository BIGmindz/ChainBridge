"""
Tests for GlassBox ML Models

Deterministic fixtures + unit tests for interpretable ML models.
All tests are reproducible (fixed seeds) and don't require external services.

Test Categories:
1. Model instantiation and interfaces
2. Fallback behavior (when model files missing)
3. Prediction determinism (same input → same output)
4. Explanation structure validation
5. Training pipeline reproducibility

Run with:
    pytest tests/ml/test_glassbox_models.py -v
    pytest tests/ml/test_glassbox_models.py -v -k "test_risk"
"""

import pytest

from app.ml.base import ModelPrediction
from app.models.features import ShipmentFeaturesV0
from app.models.scoring import FeatureContribution

# ==============================================================================
# FIXTURES: Deterministic test data
# ==============================================================================


@pytest.fixture
def sample_features_low_risk() -> ShipmentFeaturesV0:
    """Low-risk shipment: on-time, no issues, good history."""
    return ShipmentFeaturesV0(
        shipment_id="TEST-LOW-001",
        corridor="US-CA",
        origin_country="US",
        destination_country="CA",
        mode="truck",
        commodity_category="electronics",
        financing_type="OA",
        counterparty_risk_bucket="low",
        planned_transit_hours=48.0,
        actual_transit_hours=46.0,
        eta_deviation_hours=2.0,
        num_route_deviations=0,
        max_route_deviation_km=0.0,
        total_dwell_hours=4.0,
        max_single_dwell_hours=2.0,
        handoff_count=2,
        max_custody_gap_hours=0.5,
        delay_flag=0,
        has_iot_telemetry=1,
        temp_mean=22.0,
        temp_std=1.0,
        temp_min=20.0,
        temp_max=24.0,
        temp_out_of_range_pct=0.0,
        sensor_uptime_pct=0.99,
        doc_count=10,
        missing_required_docs=0,
        duplicate_doc_flag=0,
        doc_inconsistency_flag=0,
        doc_age_days=1.0,
        collateral_value=100000.0,
        collateral_value_bucket="medium",
        shipper_on_time_pct_90d=0.95,
        carrier_on_time_pct_90d=0.93,
        corridor_disruption_index_90d=0.1,
        prior_exceptions_count_180d=0,
        prior_losses_flag=0,
        lane_sentiment_score=0.7,
        macro_logistics_sentiment_score=0.6,
        sentiment_trend_7d=0.05,
        sentiment_volatility_30d=0.1,
        sentiment_provider="test_provider",
    )


@pytest.fixture
def sample_features_high_risk() -> ShipmentFeaturesV0:
    """High-risk shipment: delayed, prior losses, poor history."""
    return ShipmentFeaturesV0(
        shipment_id="TEST-HIGH-001",
        corridor="CN-US",
        origin_country="CN",
        destination_country="US",
        mode="ocean",
        commodity_category="perishables",
        financing_type="LC",
        counterparty_risk_bucket="high",
        planned_transit_hours=720.0,
        actual_transit_hours=960.0,
        eta_deviation_hours=240.0,
        num_route_deviations=5,
        max_route_deviation_km=150.0,
        total_dwell_hours=120.0,
        max_single_dwell_hours=72.0,
        handoff_count=8,
        max_custody_gap_hours=24.0,
        delay_flag=1,
        has_iot_telemetry=1,
        temp_mean=8.0,
        temp_std=5.0,
        temp_min=2.0,
        temp_max=18.0,
        temp_out_of_range_pct=0.25,
        sensor_uptime_pct=0.70,
        doc_count=15,
        missing_required_docs=3,
        duplicate_doc_flag=1,
        doc_inconsistency_flag=1,
        doc_age_days=14.0,
        collateral_value=500000.0,
        collateral_value_bucket="high",
        shipper_on_time_pct_90d=0.65,
        carrier_on_time_pct_90d=0.72,
        corridor_disruption_index_90d=0.6,
        prior_exceptions_count_180d=5,
        prior_losses_flag=1,
        lane_sentiment_score=-0.3,
        macro_logistics_sentiment_score=-0.2,
        sentiment_trend_7d=-0.15,
        sentiment_volatility_30d=0.4,
        sentiment_provider="test_provider",
    )


@pytest.fixture
def sample_features_anomaly() -> ShipmentFeaturesV0:
    """Anomalous shipment: unusual patterns that don't fit normal ranges."""
    return ShipmentFeaturesV0(
        shipment_id="TEST-ANOMALY-001",
        corridor="BR-DE",
        origin_country="BR",
        destination_country="DE",
        mode="air",
        commodity_category="pharmaceuticals",
        financing_type="DP",
        counterparty_risk_bucket="medium",
        planned_transit_hours=24.0,
        actual_transit_hours=24.0,
        eta_deviation_hours=0.0,
        num_route_deviations=15,  # Anomaly: too many deviations
        max_route_deviation_km=500.0,  # Anomaly: large deviation
        total_dwell_hours=200.0,  # Anomaly: excessive dwell
        max_single_dwell_hours=100.0,  # Anomaly: extreme single dwell
        handoff_count=2,
        max_custody_gap_hours=1.0,
        delay_flag=0,
        has_iot_telemetry=0,
        temp_mean=22.0,
        temp_std=0.5,
        temp_min=21.0,
        temp_max=23.0,
        temp_out_of_range_pct=0.0,
        sensor_uptime_pct=0.3,  # Anomaly: low uptime
        doc_count=5,
        missing_required_docs=5,  # Anomaly: many missing
        duplicate_doc_flag=0,
        doc_inconsistency_flag=0,
        doc_age_days=2.0,
        collateral_value=50000.0,
        collateral_value_bucket="low",
        shipper_on_time_pct_90d=0.88,
        carrier_on_time_pct_90d=0.85,
        corridor_disruption_index_90d=0.2,
        prior_exceptions_count_180d=1,
        prior_losses_flag=0,
        lane_sentiment_score=0.1,
        macro_logistics_sentiment_score=0.0,
        sentiment_trend_7d=0.0,
        sentiment_volatility_30d=0.15,
        sentiment_provider="test_provider",
    )


# ==============================================================================
# TESTS: GlassBoxRiskModel
# ==============================================================================


class TestGlassBoxRiskModel:
    """Tests for GlassBoxRiskModel."""

    def test_instantiation(self):
        """Model can be instantiated without errors."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path=None, fallback_on_error=True)

        assert model.model_id == "risk_glassbox"
        assert model.model_version == "1.0.0"
        assert model.fallback_on_error is True

    def test_fallback_prediction_low_risk(self, sample_features_low_risk):
        """Fallback produces low risk score for low-risk features."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path=None, fallback_on_error=True)
        prediction = model.predict(sample_features_low_risk)

        # Verify prediction structure
        assert isinstance(prediction, ModelPrediction)
        assert 0.0 <= prediction.score <= 1.0
        assert len(prediction.explanation) > 0
        assert "fallback" in prediction.model_version

        # Low risk: score should be low (< 0.3)
        assert prediction.score < 0.3, f"Expected low risk, got {prediction.score}"

    def test_fallback_prediction_high_risk(self, sample_features_high_risk):
        """Fallback produces high risk score for high-risk features."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path=None, fallback_on_error=True)
        prediction = model.predict(sample_features_high_risk)

        # Verify prediction structure
        assert isinstance(prediction, ModelPrediction)
        assert 0.0 <= prediction.score <= 1.0

        # High risk: score should be high (> 0.5)
        assert prediction.score > 0.5, f"Expected high risk, got {prediction.score}"

        # Explanation should mention delay_flag and prior_losses_flag
        explanation_features = [e.feature for e in prediction.explanation]
        assert "delay_flag" in explanation_features
        assert "prior_losses_flag" in explanation_features

    def test_prediction_determinism(self, sample_features_low_risk):
        """Same input produces same output (deterministic)."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path=None, fallback_on_error=True)

        # Run multiple predictions
        predictions = [model.predict(sample_features_low_risk) for _ in range(5)]

        # All scores should be identical
        scores = [p.score for p in predictions]
        assert len(set(scores)) == 1, f"Non-deterministic scores: {scores}"

    def test_explanation_structure(self, sample_features_high_risk):
        """Explanation contains valid FeatureContribution objects."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path=None, fallback_on_error=True)
        prediction = model.predict(sample_features_high_risk)

        for contrib in prediction.explanation:
            assert isinstance(contrib, FeatureContribution)
            assert isinstance(contrib.feature, str)
            assert len(contrib.feature) > 0
            assert isinstance(contrib.reason, str)
            assert len(contrib.reason) > 0

    def test_raises_without_fallback(self, sample_features_low_risk):
        """Raises RuntimeError when model missing and fallback disabled."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path="/nonexistent/path.pkl", fallback_on_error=False)

        with pytest.raises(RuntimeError, match="not available"):
            model.predict(sample_features_low_risk)

    def test_score_bounded(self, sample_features_low_risk, sample_features_high_risk):
        """All scores are bounded to [0, 1]."""
        from app.ml.glassbox_models import GlassBoxRiskModel

        model = GlassBoxRiskModel(model_path=None, fallback_on_error=True)

        for features in [sample_features_low_risk, sample_features_high_risk]:
            prediction = model.predict(features)
            assert 0.0 <= prediction.score <= 1.0


class TestGlassBoxAnomalyModel:
    """Tests for GlassBoxAnomalyModel."""

    def test_instantiation(self):
        """Model can be instantiated without errors."""
        from app.ml.glassbox_models import GlassBoxAnomalyModel

        model = GlassBoxAnomalyModel(model_path=None, fallback_on_error=True)

        assert model.model_id == "anomaly_glassbox"
        assert model.model_version == "1.0.0"

    def test_fallback_prediction_normal(self, sample_features_low_risk):
        """Fallback produces low anomaly score for normal features."""
        from app.ml.glassbox_models import GlassBoxAnomalyModel

        model = GlassBoxAnomalyModel(model_path=None, fallback_on_error=True)
        prediction = model.predict(sample_features_low_risk)

        assert isinstance(prediction, ModelPrediction)
        assert 0.0 <= prediction.score <= 1.0

        # Normal shipment: low anomaly score
        assert prediction.score < 0.3, f"Expected low anomaly, got {prediction.score}"

    def test_fallback_prediction_anomaly(self, sample_features_anomaly):
        """Fallback produces high anomaly score for anomalous features."""
        from app.ml.glassbox_models import GlassBoxAnomalyModel

        model = GlassBoxAnomalyModel(model_path=None, fallback_on_error=True)
        prediction = model.predict(sample_features_anomaly)

        assert isinstance(prediction, ModelPrediction)

        # Anomalous shipment: high anomaly score
        assert prediction.score > 0.5, f"Expected high anomaly, got {prediction.score}"

        # Should flag unusual dwell and route deviations
        explanation_features = [e.feature for e in prediction.explanation]
        assert "max_single_dwell_hours" in explanation_features or "num_route_deviations" in explanation_features

    def test_prediction_determinism(self, sample_features_anomaly):
        """Same input produces same output (deterministic)."""
        from app.ml.glassbox_models import GlassBoxAnomalyModel

        model = GlassBoxAnomalyModel(model_path=None, fallback_on_error=True)

        predictions = [model.predict(sample_features_anomaly) for _ in range(5)]
        scores = [p.score for p in predictions]

        assert len(set(scores)) == 1, f"Non-deterministic scores: {scores}"


class TestMLRegistry:
    """Tests for ML model registry."""

    def test_registry_contains_glassbox_models(self):
        """Registry includes GlassBox model entries."""
        from app.ml import MODEL_REGISTRY

        assert "risk_glassbox" in MODEL_REGISTRY
        assert "anomaly_glassbox" in MODEL_REGISTRY

        # Check metadata
        assert MODEL_REGISTRY["risk_glassbox"]["interpretable"] is True
        assert MODEL_REGISTRY["risk_glassbox"]["requires_training"] is True

    def test_get_glassbox_risk_model(self):
        """get_glassbox_risk_model returns valid model."""
        from app.ml import get_glassbox_risk_model
        from app.ml.base import BaseRiskModel

        model = get_glassbox_risk_model(fallback_on_error=True)

        assert isinstance(model, BaseRiskModel)
        assert model.model_id == "risk_glassbox"

    def test_get_glassbox_anomaly_model(self):
        """get_glassbox_anomaly_model returns valid model."""
        from app.ml import get_glassbox_anomaly_model
        from app.ml.base import BaseAnomalyModel

        model = get_glassbox_anomaly_model(fallback_on_error=True)

        assert isinstance(model, BaseAnomalyModel)
        assert model.model_id == "anomaly_glassbox"


class TestPreprocessing:
    """Tests for feature preprocessing (used by GlassBox models)."""

    def test_extract_feature_vector(self, sample_features_low_risk):
        """Feature extraction produces consistent vector."""
        from app.ml.preprocessing import extract_feature_vector, get_feature_names

        vector = extract_feature_vector(sample_features_low_risk)
        names = get_feature_names()

        # Vector should match feature names
        assert len(vector) == len(names)
        assert all(isinstance(v, (int, float)) for v in vector)

    def test_feature_vector_determinism(self, sample_features_low_risk):
        """Same features produce same vector."""
        from app.ml.preprocessing import extract_feature_vector

        vectors = [extract_feature_vector(sample_features_low_risk) for _ in range(3)]

        # All vectors should be identical
        for v in vectors[1:]:
            assert v == vectors[0]
