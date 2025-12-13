"""
Test suite for validation_real_data module.

Validates that the model evaluation pipeline works correctly.
"""

from app.ml.validation_real_data import (
    detect_drift,
    evaluate_anomaly_model_on_real_data,
    evaluate_risk_model_on_real_data,
    load_ingested_training_rows,
    validate_feature_ranges,
)


def test_load_synthetic_data():
    """Test synthetic data generation."""
    rows = load_ingested_training_rows(limit=100)

    assert len(rows) == 100
    assert all("features" in row for row in rows)
    assert all("had_claim" in row for row in rows)
    assert all("recorded_at" in row for row in rows)

    print("✓ test_load_synthetic_data passed")


def test_validate_feature_ranges():
    """Test feature range validation."""
    rows = load_ingested_training_rows(limit=50)
    results = validate_feature_ranges(rows)

    assert "real_stats" in results
    assert "drift_results" in results
    assert "high_drift_features" in results
    assert results["drift_threshold_pct"] == 30.0

    print("✓ test_validate_feature_ranges passed")


def test_evaluate_risk_model():
    """Test risk model evaluation."""
    rows = load_ingested_training_rows(limit=50)
    results = evaluate_risk_model_on_real_data(rows)

    assert "auc" in results
    assert "precision_at_10pct" in results
    assert "bad_outcome_rate" in results
    assert 0 <= results["auc"] <= 1

    print("✓ test_evaluate_risk_model passed")


def test_evaluate_anomaly_model():
    """Test anomaly model evaluation."""
    rows = load_ingested_training_rows(limit=50)
    results = evaluate_anomaly_model_on_real_data(rows)

    assert "score_mean" in results
    assert "score_std" in results
    assert "corridor_stats" in results

    print("✓ test_evaluate_anomaly_model passed")


def test_detect_drift():
    """Test drift detection."""
    rows = load_ingested_training_rows(limit=50)
    results = detect_drift(rows)

    assert "total_features" in results
    assert "high_drift_count" in results
    assert "top_10_drift" in results

    print("✓ test_detect_drift passed")


def test_end_to_end_validation():
    """Test full validation pipeline."""
    from app.ml.validation_real_data import full_evaluation

    results = full_evaluation(data_path=None, limit=100)

    assert "risk_results" in results
    assert "anomaly_results" in results
    assert "drift_results" in results
    assert "readiness_score" in results
    assert 0 <= results["readiness_score"] <= 100

    print("✓ test_end_to_end_validation passed")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("VALIDATION MODULE TEST SUITE")
    print("=" * 70 + "\n")

    test_load_synthetic_data()
    test_validate_feature_ranges()
    test_evaluate_risk_model()
    test_evaluate_anomaly_model()
    test_detect_drift()
    test_end_to_end_validation()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
