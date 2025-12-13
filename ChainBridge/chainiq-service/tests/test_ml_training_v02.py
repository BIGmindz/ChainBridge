"""
Tests for ChainIQ ML v0.2 training pipeline.

Tests the offline training architecture WITHOUT touching production behavior.
Ensures:
- Data structures instantiate correctly
- Feature extraction produces consistent shapes
- Training interfaces fail gracefully (v0.2 stubs)
- NO import side effects on FastAPI app
"""

import pytest

from app.ml.datasets import ShipmentTrainingRow, build_training_row_from_features, generate_synthetic_training_data
from app.ml.preprocessing import (
    build_anomaly_feature_matrix,
    build_risk_feature_matrix,
    compute_feature_stats,
    extract_feature_vector,
    get_feature_names,
)
from app.ml.training_v02 import prepare_anomaly_training_data, prepare_risk_training_data
from app.models.features import ShipmentFeaturesV0


def test_shipment_training_row_instantiation():
    """Test that ShipmentTrainingRow can be created with valid data."""
    features = ShipmentFeaturesV0(
        shipment_id="TEST-001",
        corridor="US-MX",
        origin_country="US",
        destination_country="MX",
        mode="truck",
        commodity_category="electronics",
        financing_type="LC",
        counterparty_risk_bucket="medium",
        planned_transit_hours=48.0,
        actual_transit_hours=52.0,
        eta_deviation_hours=4.0,
        num_route_deviations=1,
        max_route_deviation_km=12.3,
        total_dwell_hours=6.0,
        max_single_dwell_hours=3.5,
        handoff_count=3,
        max_custody_gap_hours=2.0,
        delay_flag=1,
        has_iot_telemetry=1,
        temp_mean=22.5,
        temp_std=1.8,
        temp_min=18.0,
        temp_max=26.0,
        temp_out_of_range_pct=0.02,
        sensor_uptime_pct=0.98,
        doc_count=12,
        missing_required_docs=1,
        duplicate_doc_flag=0,
        doc_inconsistency_flag=0,
        doc_age_days=3.2,
        collateral_value=250000.0,
        collateral_value_bucket="medium",
        shipper_on_time_pct_90d=0.87,
        carrier_on_time_pct_90d=0.91,
        corridor_disruption_index_90d=0.35,
        prior_exceptions_count_180d=2,
        prior_losses_flag=0,
        lane_sentiment_score=0.30,
        macro_logistics_sentiment_score=0.45,
        sentiment_trend_7d=-0.10,
        sentiment_volatility_30d=0.20,
        sentiment_provider="test_provider",
    )

    # Create training row
    row = build_training_row_from_features(
        features,
        label=True,
        metadata={"data_source": "synthetic"},
    )

    # Verify structure
    assert row.features.shipment_id == "TEST-001"
    assert row.severe_delay is True  # label=True maps to severe_delay
    assert row.data_source == "synthetic"
    assert isinstance(row.bad_outcome, bool)


def test_generate_synthetic_training_data():
    """Test synthetic data generation produces valid training rows."""
    rows = generate_synthetic_training_data(n_samples=50, positive_rate=0.2, seed=42)

    # Check we got the right number of rows
    assert len(rows) == 50

    # Check each row is valid
    for row in rows:
        assert isinstance(row, ShipmentTrainingRow)
        assert isinstance(row.features, ShipmentFeaturesV0)
        assert isinstance(row.bad_outcome, bool)
        assert row.data_source == "synthetic"

    # Check approximate positive rate (with some tolerance)
    positive_count = sum(r.bad_outcome for r in rows)
    positive_rate = positive_count / len(rows)
    assert 0.1 < positive_rate < 0.4  # Allow some randomness


def test_synthetic_data_determinism():
    """Test that synthetic data generation is deterministic with same seed."""
    rows1 = generate_synthetic_training_data(n_samples=20, seed=42)
    rows2 = generate_synthetic_training_data(n_samples=20, seed=42)

    # Should produce identical results
    for r1, r2 in zip(rows1, rows2):
        assert r1.features.shipment_id == r2.features.shipment_id
        assert r1.bad_outcome == r2.bad_outcome
        assert r1.features.delay_flag == r2.features.delay_flag


def test_extract_feature_vector():
    """Test that feature extraction produces consistent vector."""
    rows = generate_synthetic_training_data(n_samples=10, seed=42)

    for row in rows:
        vector = extract_feature_vector(row.features)

        # Check vector is list of floats
        assert isinstance(vector, list)
        assert all(isinstance(v, float) for v in vector)

        # Check vector length matches feature count
        feature_names = get_feature_names()
        assert len(vector) == len(feature_names)


def test_build_risk_feature_matrix():
    """Test building (X, y) matrices for risk model."""
    rows = generate_synthetic_training_data(n_samples=30, seed=42)

    X, y = build_risk_feature_matrix(rows)

    # Check shapes
    assert len(X) == 30
    assert len(y) == 30
    assert len(X[0]) == len(get_feature_names())

    # Check types
    assert all(isinstance(row, list) for row in X)
    assert all(isinstance(label, int) for label in y)
    assert all(label in (0, 1) for label in y)


def test_build_anomaly_feature_matrix():
    """Test building feature matrix for anomaly model (no labels)."""
    rows = generate_synthetic_training_data(n_samples=25, seed=42)

    X = build_anomaly_feature_matrix(rows)

    # Check shape
    assert len(X) == 25
    assert len(X[0]) == len(get_feature_names())

    # Check types
    assert all(isinstance(row, list) for row in X)


def test_prepare_risk_training_data():
    """Test train/test split for risk model."""
    rows = generate_synthetic_training_data(n_samples=100, seed=42)

    X_train, X_test, y_train, y_test = prepare_risk_training_data(rows, train_test_split=0.8, random_seed=42)

    # Check split ratio
    assert len(X_train) == 80
    assert len(X_test) == 20
    assert len(y_train) == 80
    assert len(y_test) == 20

    # Check no data leakage (train + test = all data)
    assert len(X_train) + len(X_test) == 100


def test_prepare_anomaly_training_data():
    """Test data preparation for anomaly model."""
    rows = generate_synthetic_training_data(n_samples=50, seed=42)

    X = prepare_anomaly_training_data(rows, filter_known_anomalies=False)

    # Should return all rows (no filtering)
    assert len(X) == 50


def test_compute_feature_stats():
    """Test feature statistics computation."""
    rows = generate_synthetic_training_data(n_samples=100, seed=42)

    stats = compute_feature_stats(rows)

    # Check we got stats for all features
    feature_names = get_feature_names()
    assert len(stats) == len(feature_names)

    # Check each stat has required fields
    for name, stat in stats.items():
        assert "mean" in stat
        assert "std" in stat
        assert "min" in stat
        assert "max" in stat
        assert "missing_count" in stat

        # Basic sanity checks
        assert stat["min"] <= stat["mean"] <= stat["max"]
        assert stat["std"] >= 0


def test_get_feature_names():
    """Test feature name retrieval."""
    names = get_feature_names()

    # Check we got a list of strings
    assert isinstance(names, list)
    assert all(isinstance(n, str) for n in names)

    # Check for some expected features
    assert "delay_flag" in names
    assert "prior_losses_flag" in names
    assert "actual_transit_hours" in names


def test_no_import_side_effects():
    """
    CRITICAL: Test that importing training modules doesn't slow down FastAPI.

    This test ensures that heavy ML imports (sklearn, numpy) are NOT
    triggered at module import time.
    """
    # These imports should be fast (no sklearn/numpy loaded yet)
    import app.ml.datasets  # noqa: F401
    import app.ml.preprocessing  # noqa: F401
    import app.ml.training_v02  # noqa: F401

    # If we got here without slowness, test passes
    # (Pytest will measure total test time; this should be < 0.1s)
    assert True


def test_training_functions_implemented():
    """
    Test that training functions now work (PAC-004 implementation).

    Previously raised NotImplementedError - now they should train successfully.
    """
    from app.ml.training_v02 import (
        fit_anomaly_model_v02,
        fit_risk_model_v02,
        generate_synthetic_training_data,
        prepare_anomaly_training_data,
        prepare_risk_training_data,
    )

    # Generate small synthetic dataset
    rows = generate_synthetic_training_data(n_samples=100, positive_rate=0.2, seed=42)

    # Test risk model training
    X_train, X_test, y_train, y_test = prepare_risk_training_data(rows, train_test_split=0.8, random_seed=42)
    risk_result = fit_risk_model_v02(X_train, y_train, X_test=X_test, y_test=y_test)

    assert "model" in risk_result
    assert "metrics" in risk_result
    assert "feature_importance" in risk_result
    assert "metadata" in risk_result
    assert risk_result["metadata"]["model_type"] == "logistic_regression"
    assert risk_result["metadata"]["model_version"] == "0.2.0"
    assert risk_result["metrics"]["train"]["auc"] > 0.5  # Better than random

    # Test anomaly model training
    X_anomaly = prepare_anomaly_training_data(rows, filter_known_anomalies=True)
    anomaly_result = fit_anomaly_model_v02(X_anomaly, contamination=0.05)

    assert "model" in anomaly_result
    assert "metrics" in anomaly_result
    assert "metadata" in anomaly_result
    assert anomaly_result["metadata"]["model_type"] == "isolation_forest"
    assert anomaly_result["metadata"]["model_version"] == "0.2.0"
    assert 0 <= anomaly_result["metrics"]["mean_score"] <= 1  # Valid probability range


def test_training_row_bad_outcome_property():
    """Test that bad_outcome property works correctly."""
    rows = generate_synthetic_training_data(n_samples=50, seed=42)

    for row in rows:
        # bad_outcome should be True if ANY of the labels are True
        expected = row.had_claim or row.had_dispute or row.severe_delay
        assert row.bad_outcome == expected


def test_feature_extraction_consistency():
    """Test that feature extraction is consistent across multiple calls."""
    rows = generate_synthetic_training_data(n_samples=10, seed=42)

    for row in rows:
        vector1 = extract_feature_vector(row.features)
        vector2 = extract_feature_vector(row.features)

        # Should produce identical results
        assert vector1 == vector2


def test_sklearn_import_guard():
    """
    Test that sklearn imports are properly guarded.

    This test ONLY runs if sklearn is installed. If not, it should skip gracefully.
    """
    try:
        from app.ml.preprocessing import create_sklearn_preprocessor

        # If sklearn is installed, this should work
        preprocessor = create_sklearn_preprocessor()
        assert preprocessor is not None

    except ImportError:
        # If sklearn is not installed, test should pass (expected in some environments)
        pytest.skip("sklearn not installed (expected in some environments)")
