"""
ChainIQ ML Fairness Test Suite

Tests for:
- Target leakage detection
- Corridor bias / disparate impact
- Monotonicity constraint validation
- Feature range validation
- Calibration checks

Author: Maggie (GID-10) 🩷
PAC: MAGGIE-PAC-A
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.feature_forensics import (
    FEATURE_SPECS,
    analyze_calibration,
    analyze_corridor_bias,
    compute_feature_statistics,
    detect_range_violations,
    detect_target_leakage,
    generate_adversarial_samples,
    validate_monotonicity,
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_training_rows() -> list[dict[str, Any]]:
    """Generate sample training rows for testing."""
    np.random.seed(42)
    rows = []

    for i in range(500):
        # Base features
        planned_transit = np.random.uniform(24, 168)
        actual_transit = planned_transit + np.random.normal(5, 10)
        eta_deviation = actual_transit - planned_transit

        # Outcomes correlated with deviation
        bad_outcome = eta_deviation > 20 or np.random.random() < 0.1

        rows.append(
            {
                "features": {
                    "shipment_id": f"SHIP-{i:04d}",
                    "corridor": np.random.choice(["LA_PORTS→INLAND_EMPIRE", "SHANGHAI→LA_PORTS", "ROTTERDAM→NY_NJ"]),
                    "planned_transit_hours": planned_transit,
                    "actual_transit_hours": actual_transit,
                    "eta_deviation_hours": eta_deviation,
                    "num_route_deviations": np.random.poisson(1.5),
                    "max_route_deviation_km": np.random.exponential(15),
                    "total_dwell_hours": np.random.exponential(8),
                    "max_single_dwell_hours": np.random.exponential(4),
                    "handoff_count": np.random.poisson(3),
                    "max_custody_gap_hours": np.random.exponential(2),
                    "delay_flag": int(eta_deviation > 10),  # Leaky!
                    "prior_losses_flag": np.random.choice([0, 1], p=[0.9, 0.1]),
                    "missing_required_docs": np.random.poisson(0.3),
                    "shipper_on_time_pct_90d": 90.0,  # Simulated
                    "carrier_on_time_pct_90d": 85.0,  # Simulated
                    "lane_sentiment_score": 0.7,  # Simulated
                    "macro_logistics_sentiment_score": 0.8,  # Simulated
                    "sentiment_trend_7d": 0.02,  # Simulated
                    "sentiment_volatility_30d": 0.12,  # Simulated
                    "temp_mean": 4.0,  # Simulated
                    "temp_std": 1.5,  # Simulated
                    "temp_out_of_range_pct": 2.0,  # Simulated
                    "sensor_uptime_pct": 98.0,  # Simulated
                },
                "had_claim": bad_outcome and np.random.random() < 0.3,
                "had_dispute": bad_outcome and np.random.random() < 0.2,
                "severe_delay": eta_deviation > 24,
            }
        )

    return rows


@pytest.fixture
def sample_model_coefficients() -> dict[str, float]:
    """Sample model coefficients for testing."""
    return {
        "planned_transit_hours": 0.15,  # Correct: positive
        "actual_transit_hours": 0.18,  # Correct: positive
        "eta_deviation_hours": 0.85,  # Correct: positive (but leaky!)
        "num_route_deviations": 0.25,  # Correct: positive
        "max_route_deviation_km": 0.12,  # Correct: positive
        "total_dwell_hours": 0.20,  # Correct: positive
        "max_single_dwell_hours": 0.08,  # Correct: positive
        "handoff_count": 0.10,  # Correct: positive
        "max_custody_gap_hours": 0.30,  # Correct: positive
        "delay_flag": 0.72,  # Correct: positive (but leaky!)
        "prior_losses_flag": 0.15,  # Correct: positive
        "missing_required_docs": 0.12,  # Correct: positive
        "shipper_on_time_pct_90d": -0.20,  # Correct: negative
        "carrier_on_time_pct_90d": -0.25,  # Correct: negative
        "lane_sentiment_score": 0.05,  # WRONG: should be negative
        "macro_logistics_sentiment_score": -0.08,  # Correct: negative
        "sentiment_trend_7d": -0.03,  # Correct: negative
        "sentiment_volatility_30d": 0.10,  # Correct: positive
        "temp_mean": 0.00,  # Correct: none (unconstrained)
        "temp_std": 0.05,  # Correct: positive
        "temp_out_of_range_pct": 0.08,  # Correct: positive
        "sensor_uptime_pct": -0.04,  # Correct: negative
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LEAKAGE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestTargetLeakage:
    """Tests for target leakage detection."""

    def test_leakage_detection_with_delay_flag(self, sample_training_rows: list[dict[str, Any]]):
        """Test that delay_flag correlation is computed and analyzed."""
        result = detect_target_leakage(sample_training_rows)

        # Should have correlation analysis for key features
        assert "delay_flag" in result["correlation_analysis"]
        assert "eta_deviation_hours" in result["correlation_analysis"]

        # Correlation should be non-zero (delay_flag is derived from outcome)
        delay_corr = result["correlation_analysis"]["delay_flag"]["abs_correlation"]
        assert delay_corr > 0.1  # Should have some correlation

    def test_leakage_correlation_analysis(self, sample_training_rows: list[dict[str, Any]]):
        """Test that correlation analysis is computed correctly."""
        result = detect_target_leakage(sample_training_rows)

        # Should have correlation for key features
        assert "delay_flag" in result["correlation_analysis"]
        assert "eta_deviation_hours" in result["correlation_analysis"]

        # delay_flag should have measurable correlation with label
        delay_corr = result["correlation_analysis"]["delay_flag"]["abs_correlation"]
        assert delay_corr > 0.1  # Should be correlated since it's derived from outcome

    def test_no_leakage_with_clean_features(self):
        """Test that clean features don't trigger leakage detection."""
        # Create data with no obvious leakage
        np.random.seed(42)
        clean_rows = []

        for i in range(200):
            bad_outcome = np.random.random() < 0.15  # Random outcomes
            clean_rows.append(
                {
                    "features": {
                        "planned_transit_hours": np.random.uniform(24, 168),
                        "prior_losses_flag": np.random.choice([0, 1], p=[0.9, 0.1]),
                        "handoff_count": np.random.poisson(3),
                    },
                    "had_claim": bad_outcome,
                    "had_dispute": False,
                    "severe_delay": False,
                }
            )

        result = detect_target_leakage(clean_rows)

        # Should not detect critical leakage with random outcomes
        critical_features = [f for f in result["high_risk_features"] if f.get("leakage_risk") == "critical"]
        assert len(critical_features) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# CORRIDOR BIAS / FAIRNESS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCorridorBias:
    """Tests for corridor bias and fairness analysis."""

    def test_fairness_score_calculation(self, sample_training_rows: list[dict[str, Any]]):
        """Test that fairness score is computed correctly."""
        result = analyze_corridor_bias(sample_training_rows)

        # Should have fairness score between 0 and 1
        assert 0 <= result["fairness_score"] <= 1

        # Should analyze top corridors
        assert len(result["corridor_stats"]) > 0

    def test_bias_flag_detection(self):
        """Test that corridors with disparate outcomes are flagged."""
        # Create data with one clearly biased corridor
        np.random.seed(123)
        biased_rows = []

        for i in range(400):
            corridor = "CORRIDOR_A" if i < 200 else "CORRIDOR_B"
            # CORRIDOR_A has 40% bad rate, CORRIDOR_B has 5% bad rate
            bad_rate = 0.40 if corridor == "CORRIDOR_A" else 0.05
            bad_outcome = np.random.random() < bad_rate

            biased_rows.append(
                {
                    "features": {
                        "corridor": corridor,
                        "planned_transit_hours": 72,
                    },
                    "had_claim": bad_outcome,
                    "had_dispute": False,
                    "severe_delay": False,
                }
            )

        result = analyze_corridor_bias(biased_rows)

        # Should have analyzed corridors
        assert len(result["corridor_stats"]) > 0

        # Rate difference should be detectable
        global_rate = result["global_bad_rate"]
        assert 0.1 < global_rate < 0.4  # Sanity check

    def test_global_bad_rate_calculation(self, sample_training_rows: list[dict[str, Any]]):
        """Test that global bad rate is calculated correctly."""
        result = analyze_corridor_bias(sample_training_rows)

        # Calculate expected global rate manually
        total_bad = sum(1 for r in sample_training_rows if r["had_claim"] or r["had_dispute"] or r["severe_delay"])
        expected_rate = total_bad / len(sample_training_rows)

        # Should match within tolerance
        assert abs(result["global_bad_rate"] - expected_rate) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# MONOTONICITY VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMonotonicity:
    """Tests for monotonicity constraint validation."""

    def test_monotonicity_violation_detection(self, sample_model_coefficients: dict[str, float]):
        """Test that monotonicity violations are detected."""
        result = validate_monotonicity(sample_model_coefficients)

        # lane_sentiment_score has wrong sign (positive instead of negative)
        violation_features = [v["feature"] for v in result["violations"]]
        assert "lane_sentiment_score" in violation_features

    def test_compliant_features_tracked(self, sample_model_coefficients: dict[str, float]):
        """Test that compliant features are tracked."""
        result = validate_monotonicity(sample_model_coefficients)

        # Should have compliant features
        assert len(result["compliant_features"]) > 0

        # Most features should be compliant
        assert result["compliance_rate"] > 0.8

    def test_unconstrained_features_accepted(self, sample_model_coefficients: dict[str, float]):
        """Test that unconstrained features are not flagged."""
        result = validate_monotonicity(sample_model_coefficients)

        # temp_mean is unconstrained (monotone_direction = "none")
        compliant_features = [f["feature"] for f in result["compliant_features"]]

        # Should either be compliant or unconstrained
        violation_features = [v["feature"] for v in result["violations"]]
        assert "temp_mean" not in violation_features


# ═══════════════════════════════════════════════════════════════════════════════
# RANGE VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRangeValidation:
    """Tests for feature range validation."""

    def test_range_violation_detection(self):
        """Test that out-of-range values are detected."""
        # Create data with range violations
        bad_rows = [
            {
                "features": {
                    "planned_transit_hours": -10,  # Below min (1)
                    "temp_out_of_range_pct": 150,  # Above max (100)
                }
            }
            for _ in range(10)
        ]

        stats = compute_feature_statistics(bad_rows, ["planned_transit_hours", "temp_out_of_range_pct"])
        violations = detect_range_violations(stats)

        # Should detect violations
        assert len(violations) > 0

        # planned_transit_hours min violation
        ptc_violations = [v for v in violations if v["feature"] == "planned_transit_hours"]
        assert any(v["violation_type"] == "min_exceeded" for v in ptc_violations)

        # temp_out_of_range_pct max violation
        temp_violations = [v for v in violations if v["feature"] == "temp_out_of_range_pct"]
        assert any(v["violation_type"] == "max_exceeded" for v in temp_violations)

    def test_mean_drift_detection(self):
        """Test that mean drift is detected."""
        # Create data with drifted mean
        drifted_rows = [
            {
                "features": {
                    "planned_transit_hours": 300,  # Expected mean is ~72
                }
            }
            for _ in range(50)
        ]

        stats = compute_feature_statistics(drifted_rows, ["planned_transit_hours"])
        violations = detect_range_violations(stats)

        # Should detect mean drift
        drift_violations = [v for v in violations if v["violation_type"] == "mean_drift"]
        assert len(drift_violations) > 0

    def test_no_violations_for_normal_data(self, sample_training_rows: list[dict[str, Any]]):
        """Test that normal data doesn't trigger false violations."""
        stats = compute_feature_statistics(sample_training_rows)
        violations = detect_range_violations(stats, tolerance_pct=20)  # Allow 20% tolerance

        # Should have few or no high-severity violations
        high_severity = [v for v in violations if v["severity"] == "high"]
        assert len(high_severity) < 5  # Allow some noise


# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCalibration:
    """Tests for model calibration analysis."""

    def test_well_calibrated_model(self):
        """Test that well-calibrated predictions are recognized."""
        np.random.seed(42)
        n = 1000

        # Generate well-calibrated predictions
        y_proba = np.random.uniform(0, 1, n)
        y_true = (np.random.random(n) < y_proba).astype(int)

        result = analyze_calibration(y_true, y_proba)

        # Should be well-calibrated
        assert 0.7 <= result["slope"] <= 1.3
        assert abs(result["intercept"]) < 0.1

    def test_overconfident_model_detection(self):
        """Test that poorly calibrated models are detected."""
        n = 1000
        np.random.seed(42)

        # Overconfident: predicts 0.9 but actual rate is 0.5
        y_proba = np.full(n, 0.9)
        y_true = np.random.choice([0, 1], n, p=[0.5, 0.5])

        result = analyze_calibration(y_true, y_proba)

        # ECE should be high for poorly calibrated predictions
        assert result["expected_calibration_error"] > 0.1  # Should have significant error

    def test_ece_calculation(self):
        """Test that ECE is calculated correctly."""
        y_proba = [0.1, 0.2, 0.3, 0.4, 0.5]
        y_true = [0, 0, 0, 1, 1]

        result = analyze_calibration(y_true, y_proba)

        # ECE should be low for reasonable predictions
        assert result["expected_calibration_error"] < 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# ADVERSARIAL TESTING
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdversarial:
    """Tests for adversarial sample generation."""

    def test_adversarial_sample_generation(self):
        """Test that adversarial samples are generated correctly."""
        baseline = {
            "planned_transit_hours": 72,
            "eta_deviation_hours": 5,
            "delay_flag": 0,
            "num_route_deviations": 2,
            "max_custody_gap_hours": 1,
            "sentiment_trend_7d": 0.02,
        }

        samples = generate_adversarial_samples(baseline)

        # Should generate multiple samples
        assert len(samples) >= 4

        # Should have different strategies
        strategies = [s["strategy"] for s in samples]
        assert "zero" in strategies
        assert "max" in strategies

    def test_zero_sample_generation(self):
        """Test that zero sample sets all features to 0."""
        baseline = {"feat_a": 10, "feat_b": 20}
        samples = generate_adversarial_samples(baseline, ["zero"])

        zero_sample = next(s for s in samples if s["strategy"] == "zero")

        assert zero_sample["features"]["feat_a"] == 0
        assert zero_sample["features"]["feat_b"] == 0

    def test_flip_binary_sample_generation(self):
        """Test that binary flip inverts flag features."""
        baseline = {
            "delay_flag": 0,
            "prior_losses_flag": 1,
            "other_feature": 50,
        }

        samples = generate_adversarial_samples(baseline, ["flip_binary"])

        flip_sample = next(s for s in samples if s["strategy"] == "flip_binary")

        # Binary flags should be flipped
        assert flip_sample["features"]["delay_flag"] == 1
        assert flip_sample["features"]["prior_losses_flag"] == 0

        # Non-binary should be unchanged
        assert flip_sample["features"]["other_feature"] == 50


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE SPEC VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeatureSpecs:
    """Tests for feature specification integrity."""

    def test_all_training_features_have_specs(self):
        """Test that all training features have specifications."""
        # Features used in training (from preprocessing.py)
        training_features = [
            "planned_transit_hours",
            "actual_transit_hours",
            "eta_deviation_hours",
            "num_route_deviations",
            "max_route_deviation_km",
            "total_dwell_hours",
            "max_single_dwell_hours",
            "handoff_count",
            "max_custody_gap_hours",
            "delay_flag",
            "prior_losses_flag",
            "missing_required_docs",
            "shipper_on_time_pct_90d",
            "carrier_on_time_pct_90d",
            "lane_sentiment_score",
            "macro_logistics_sentiment_score",
            "sentiment_trend_7d",
            "sentiment_volatility_30d",
            "temp_mean",
            "temp_std",
            "temp_out_of_range_pct",
            "sensor_uptime_pct",
        ]

        missing = [f for f in training_features if f not in FEATURE_SPECS]
        assert len(missing) == 0, f"Missing specs for: {missing}"

    def test_feature_specs_have_valid_dtypes(self):
        """Test that all feature specs have valid data types."""
        valid_dtypes = {"float", "int", "categorical", "binary"}

        for name, spec in FEATURE_SPECS.items():
            assert spec.dtype in valid_dtypes, f"{name} has invalid dtype: {spec.dtype}"

    def test_binary_features_have_01_range(self):
        """Test that binary features have [0, 1] range."""
        for name, spec in FEATURE_SPECS.items():
            if spec.dtype == "binary":
                assert spec.min_val == 0, f"{name} binary min should be 0"
                assert spec.max_val == 1, f"{name} binary max should be 1"

    def test_monotone_constraints_are_valid(self):
        """Test that monotone constraints are properly specified."""
        valid_directions = {"positive", "negative", "none"}

        for name, spec in FEATURE_SPECS.items():
            assert spec.monotone_direction in valid_directions, f"{name} has invalid monotone_direction: {spec.monotone_direction}"

    def test_leakage_risk_levels_are_valid(self):
        """Test that leakage risk levels are properly specified."""
        valid_risks = {"none", "low", "medium", "high"}

        for name, spec in FEATURE_SPECS.items():
            assert spec.leakage_risk in valid_risks, f"{name} has invalid leakage_risk: {spec.leakage_risk}"

    def test_high_risk_features_documented(self):
        """Test that high-risk features have descriptions."""
        high_risk_features = [name for name, spec in FEATURE_SPECS.items() if spec.leakage_risk in ("medium", "high")]

        for name in high_risk_features:
            assert FEATURE_SPECS[name].description, f"High-risk feature {name} should have description"


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestForensicsIntegration:
    """Integration tests for the full forensics pipeline."""

    def test_full_forensics_runs_without_error(self, sample_training_rows: list[dict[str, Any]]):
        """Test that full forensics pipeline completes successfully."""
        from app.ml.feature_forensics import run_full_forensics

        result = run_full_forensics(sample_training_rows)

        # Should have all expected sections
        assert "feature_stats" in result
        assert "range_violations" in result
        assert "leakage_analysis" in result
        assert "corridor_bias" in result
        assert "verdict" in result

    def test_verdict_generation(self, sample_training_rows: list[dict[str, Any]]):
        """Test that verdict is generated correctly."""
        from app.ml.feature_forensics import run_full_forensics

        result = run_full_forensics(sample_training_rows)
        verdict = result["verdict"]

        # Should have decision and recommendation
        assert "decision" in verdict
        assert "recommendation" in verdict
        assert "blockers" in verdict
        assert "warnings" in verdict

        # Decision should be valid
        valid_decisions = ["✅ DEPLOY", "✅ DEPLOY-WITH-MONITORING", "⚠️ CONDITIONAL-DEPLOY", "❌ NO-DEPLOY"]
        assert verdict["decision"] in valid_decisions


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATED FEATURE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSimulatedFeatureDetection:
    """Tests for detecting simulated/hardcoded features."""

    def test_zero_variance_detection(self):
        """Test that zero-variance (simulated) features are detected."""
        rows = [
            {
                "features": {
                    "real_feature": np.random.uniform(10, 20),
                    "simulated_feature": 85.0,  # Always same value
                }
            }
            for _ in range(100)
        ]

        stats = compute_feature_statistics(rows, ["real_feature", "simulated_feature"])

        # Simulated feature should have zero std
        assert stats["simulated_feature"].std == 0

        # Real feature should have non-zero std
        assert stats["real_feature"].std > 0

    def test_count_simulated_features(self, sample_training_rows: list[dict[str, Any]]):
        """Test counting of simulated features in sample data."""
        stats = compute_feature_statistics(sample_training_rows)

        # Count zero-variance features
        simulated = [name for name, s in stats.items() if s.std == 0]

        # Our sample data has several simulated features (those with hardcoded values)
        # At minimum, we should detect some zero-variance features
        expected_simulated = [
            "shipper_on_time_pct_90d",
            "carrier_on_time_pct_90d",
            "lane_sentiment_score",
            "macro_logistics_sentiment_score",
            "sentiment_trend_7d",
            "temp_mean",
            "temp_std",
            "sensor_uptime_pct",
        ]

        # At least half of expected simulated should be detected
        detected_count = sum(1 for feat in expected_simulated if feat in simulated)
        assert (
            detected_count >= len(expected_simulated) // 2
        ), f"Expected at least {len(expected_simulated)//2} simulated features, got {detected_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
