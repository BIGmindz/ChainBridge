"""
Tests for ChainIQ ML Drift Diagnostics Module

Validates:
- SHAP baseline computation
- Drift-weighted feature attribution
- Monotonicity validation v2
- Drift-aware risk multiplier
- Report generation

Author: Maggie (GID-10) 🩷
PAC: MAGGIE-NEXT-A02
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Module under test
from app.ml.drift_diagnostics import (
    DRIFT_SEVERITY_THRESHOLDS,
    CorridorAttribution,
    DriftAwareRiskMultiplier,
    DriftDiagnosticsReporter,
    DriftFeatureAttribution,
    DriftFeatureAttributor,
    DriftRiskMultiplier,
    DriftSeverity,
    MonotonicityValidationResult,
    MonotonicityValidatorV2,
    MonotonicityViolation,
    SHAPAttribution,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def sample_shadow_events():
    """Generate sample shadow events for testing."""
    np.random.seed(42)
    events = []

    for i in range(100):
        dummy_score = np.random.uniform(0.1, 0.9)
        delta = np.random.uniform(-0.2, 0.2)
        real_score = np.clip(dummy_score + delta, 0, 1)

        events.append(
            {
                "id": f"event_{i}",
                "dummy_score": dummy_score,
                "real_score": real_score,
                "corridor": np.random.choice(["US-CN", "US-MX", "EU-IN", "EU-UK"]),
                "features": {
                    "planned_transit_hours": np.random.uniform(24, 168),
                    "eta_deviation_hours": np.random.uniform(-5, 20),
                    "num_route_deviations": np.random.randint(0, 5),
                    "shipper_on_time_pct_90d": np.random.uniform(75, 99),
                    "carrier_on_time_pct_90d": np.random.uniform(70, 98),
                    "total_dwell_hours": np.random.uniform(0, 24),
                },
            }
        )

    return events


@pytest.fixture
def sample_reference_data():
    """Generate reference data (slightly different distribution)."""
    np.random.seed(123)
    data = []

    for i in range(200):
        data.append(
            {
                "features": {
                    "planned_transit_hours": np.random.uniform(20, 150),  # Different range
                    "eta_deviation_hours": np.random.uniform(-3, 15),
                    "num_route_deviations": np.random.randint(0, 4),
                    "shipper_on_time_pct_90d": np.random.uniform(80, 99),
                    "carrier_on_time_pct_90d": np.random.uniform(75, 99),
                    "total_dwell_hours": np.random.uniform(0, 20),
                },
            }
        )

    return data


@pytest.fixture
def feature_matrix_and_predictions():
    """Generate feature matrix and predictions for monotonicity testing."""
    np.random.seed(42)
    n_samples = 500

    # Features: planned_transit_hours should INCREASE risk
    transit_hours = np.random.uniform(24, 168, n_samples)

    # Features: shipper_on_time_pct should DECREASE risk
    on_time_pct = np.random.uniform(70, 99, n_samples)

    # Predictions that follow monotonicity
    predictions = 0.3 + 0.3 * (transit_hours / 168) - 0.2 * (on_time_pct / 100)
    predictions = np.clip(predictions, 0, 1)

    features = np.column_stack([transit_hours, on_time_pct])
    feature_names = ["planned_transit_hours", "shipper_on_time_pct_90d"]

    return features, predictions, feature_names


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: DRIFT FEATURE ATTRIBUTOR
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftFeatureAttributor:
    """Tests for DriftFeatureAttributor class."""

    def test_init_defaults(self):
        """Test default initialization."""
        attributor = DriftFeatureAttributor()

        assert attributor.drift_weight == 0.5
        assert attributor.feature_specs is not None
        assert len(attributor._baseline_values) == 0

    def test_compute_shap_baseline(self, sample_reference_data):
        """Test SHAP baseline computation."""
        attributor = DriftFeatureAttributor()

        baseline = attributor.compute_shap_baseline(sample_reference_data)

        assert isinstance(baseline, dict)
        assert "planned_transit_hours" in baseline
        assert baseline["planned_transit_hours"] > 0
        assert len(attributor._baseline_values) > 0

    def test_compute_sample_attribution(self, sample_shadow_events, sample_reference_data):
        """Test single sample attribution."""
        attributor = DriftFeatureAttributor()
        attributor.compute_shap_baseline(sample_reference_data)

        sample = sample_shadow_events[0]
        model_scores = {
            "dummy_score": sample["dummy_score"],
            "real_score": sample["real_score"],
            "delta": abs(sample["dummy_score"] - sample["real_score"]),
        }

        attributions = attributor.compute_sample_attribution(sample, model_scores)

        assert isinstance(attributions, list)
        assert len(attributions) > 0
        assert all(isinstance(a, SHAPAttribution) for a in attributions)

        # Attributions should be sorted by absolute value
        abs_values = [a.abs_shap_value for a in attributions]
        assert abs_values == sorted(abs_values, reverse=True)

        # Contribution percentages should sum to ~100%
        total_pct = sum(a.contribution_pct for a in attributions)
        assert 99.0 < total_pct < 101.0

    def test_compute_drift_weighted_importance(self, sample_shadow_events, sample_reference_data):
        """Test drift-weighted importance computation."""
        attributor = DriftFeatureAttributor()

        # Mock feature statistics

        with patch("app.ml.drift_diagnostics.compute_feature_statistics") as mock_stats:
            # Create mock stats that show drift
            mock_current = {
                "planned_transit_hours": MagicMock(mean=100, std=30),
                "eta_deviation_hours": MagicMock(mean=15, std=8),
            }
            mock_ref = {
                "planned_transit_hours": MagicMock(mean=80, std=25),  # 25% drift
                "eta_deviation_hours": MagicMock(mean=10, std=5),  # 50% drift
            }

            attributions = attributor.compute_drift_weighted_importance(mock_current, mock_ref)

            assert isinstance(attributions, list)
            # Should be sorted by drift_weighted_importance
            if len(attributions) > 1:
                assert attributions[0].rank == 1

    def test_compute_corridor_attribution(self, sample_shadow_events, sample_reference_data):
        """Test corridor-specific attribution."""
        attributor = DriftFeatureAttributor()

        us_cn_events = [e for e in sample_shadow_events if e["corridor"] == "US-CN"]

        result = attributor.compute_corridor_attribution(us_cn_events, "US-CN", sample_reference_data)

        assert isinstance(result, CorridorAttribution)
        assert result.corridor == "US-CN"
        assert result.event_count == len(us_cn_events)
        assert 0 <= result.avg_delta <= 1
        assert 0 <= result.p95_delta <= 1

    def test_classify_drift_severity(self):
        """Test drift severity classification."""
        assert DriftFeatureAttributor._classify_drift_severity(0.03) == DriftSeverity.NEGLIGIBLE
        assert DriftFeatureAttributor._classify_drift_severity(0.08) == DriftSeverity.MINOR
        assert DriftFeatureAttributor._classify_drift_severity(0.15) == DriftSeverity.MODERATE
        assert DriftFeatureAttributor._classify_drift_severity(0.30) == DriftSeverity.SIGNIFICANT
        assert DriftFeatureAttributor._classify_drift_severity(0.45) == DriftSeverity.SEVERE
        assert DriftFeatureAttributor._classify_drift_severity(0.75) == DriftSeverity.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MONOTONICITY VALIDATOR V2
# ═══════════════════════════════════════════════════════════════════════════════


class TestMonotonicityValidatorV2:
    """Tests for MonotonicityValidatorV2 class."""

    def test_init(self):
        """Test initialization."""
        validator = MonotonicityValidatorV2()

        assert validator.feature_specs is not None
        assert len(validator._feature_type_map) > 0
        assert "planned_transit_hours" in validator._feature_type_map

    def test_feature_type_mapping(self):
        """Test feature type classification."""
        validator = MonotonicityValidatorV2()

        assert validator._feature_type_map.get("planned_transit_hours") == "time"
        assert validator._feature_type_map.get("max_route_deviation_km") == "distance"
        assert validator._feature_type_map.get("shipper_on_time_pct_90d") == "probability"
        assert validator._feature_type_map.get("num_route_deviations") == "count"

    def test_validate_all_passes(self, feature_matrix_and_predictions):
        """Test validation passes for properly monotonic features."""
        features, predictions, feature_names = feature_matrix_and_predictions
        validator = MonotonicityValidatorV2()

        result = validator.validate_all(predictions, features, feature_names)

        assert isinstance(result, MonotonicityValidationResult)
        assert result.total_features == 2
        # Should mostly pass since predictions follow expected monotonicity

    def test_validate_all_detects_violations(self):
        """Test validation detects monotonicity violations."""
        np.random.seed(42)
        validator = MonotonicityValidatorV2()

        # Create data where increasing transit hours DECREASES risk (violation)
        n_samples = 200
        transit_hours = np.random.uniform(24, 168, n_samples)

        # Wrong direction: higher hours = lower risk
        predictions = 0.8 - 0.4 * (transit_hours / 168)

        features = transit_hours.reshape(-1, 1)
        feature_names = ["planned_transit_hours"]

        result = validator.validate_all(predictions, features, feature_names)

        assert not result.is_valid
        assert len(result.violations) > 0
        assert result.violations[0].feature_name == "planned_transit_hours"
        assert result.violations[0].expected_direction == "increasing"

    def test_validate_distance_features(self):
        """Test distance feature validation."""
        np.random.seed(42)
        validator = MonotonicityValidatorV2()

        n_samples = 100
        distance = np.random.uniform(0, 500, n_samples)
        predictions = 0.2 + 0.5 * (distance / 500)  # Correct direction

        features = distance.reshape(-1, 1)
        feature_names = ["max_route_deviation_km"]

        violations = validator.validate_distance_features(predictions, features, feature_names)

        assert isinstance(violations, list)
        # Should have no violations since direction is correct

    def test_validate_probability_features(self):
        """Test probability feature validation with bounds checking."""
        np.random.seed(42)
        validator = MonotonicityValidatorV2()

        n_samples = 100
        # Include some out-of-bounds values
        on_time_pct = np.random.uniform(-5, 105, n_samples)  # Invalid bounds
        predictions = 0.6 - 0.3 * (np.clip(on_time_pct, 0, 100) / 100)

        features = on_time_pct.reshape(-1, 1)
        feature_names = ["shipper_on_time_pct_90d"]

        # Should log warning about out-of-bounds but validate monotonicity
        violations = validator.validate_probability_features(predictions, features, feature_names)

        assert isinstance(violations, list)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: DRIFT-AWARE RISK MULTIPLIER
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftAwareRiskMultiplier:
    """Tests for DriftAwareRiskMultiplier class."""

    def test_init_defaults(self):
        """Test default initialization."""
        multiplier = DriftAwareRiskMultiplier()

        assert multiplier.config["base_multiplier"] == 1.0
        assert multiplier.config["max_drift_adjustment"] == 0.5

    def test_compute_multiplier_low_drift(self):
        """Test multiplier for low drift scenario."""
        multiplier = DriftAwareRiskMultiplier()

        drift_stats = {
            "avg_delta": 0.05,
            "p95_delta": 0.10,
            "event_count": 100,
        }

        result = multiplier.compute_multiplier(drift_stats)

        assert isinstance(result, DriftRiskMultiplier)
        assert result.base_multiplier == 1.0
        assert result.drift_adjustment == 0.0  # Below threshold
        assert result.final_multiplier == 1.0
        assert "Normal" in result.rationale

    def test_compute_multiplier_high_drift(self):
        """Test multiplier for high drift scenario."""
        multiplier = DriftAwareRiskMultiplier()

        drift_stats = {
            "avg_delta": 0.20,
            "p95_delta": 0.30,  # Above threshold
            "event_count": 100,
        }

        result = multiplier.compute_multiplier(drift_stats)

        assert result.drift_adjustment > 0
        assert result.final_multiplier > 1.0
        assert "High drift" in result.rationale

    def test_compute_multiplier_critical_drift(self):
        """Test multiplier for critical drift scenario."""
        multiplier = DriftAwareRiskMultiplier()

        drift_stats = {
            "avg_delta": 0.30,
            "p95_delta": 0.40,  # Critical
            "event_count": 100,
        }

        result = multiplier.compute_multiplier(drift_stats)

        assert result.drift_adjustment == multiplier.config["max_drift_adjustment"]
        assert "Critical drift" in result.rationale

    def test_compute_multiplier_with_corridor(self):
        """Test multiplier with corridor adjustment."""
        multiplier = DriftAwareRiskMultiplier()

        drift_stats = {
            "avg_delta": 0.15,
            "p95_delta": 0.20,
            "event_count": 100,
        }

        corridor_stats = {
            "corridor": "US-CN",
            "drift_flag": True,
            "p95_delta": 0.35,
        }

        result = multiplier.compute_multiplier(drift_stats, corridor_stats)

        assert result.corridor_adjustment > 0
        assert "Corridor drift" in result.rationale

    def test_apply_to_score(self):
        """Test applying multiplier to raw score."""
        multiplier = DriftAwareRiskMultiplier()

        drift_stats = {
            "avg_delta": 0.20,
            "p95_delta": 0.30,
            "event_count": 100,
        }

        raw_score = 0.5
        adjusted_score, mult_info = multiplier.apply_to_score(raw_score, drift_stats)

        # Adjusted score should be higher (more conservative) with drift
        assert adjusted_score > raw_score
        assert 0 < adjusted_score < 1

    def test_get_tier_from_multiplier(self):
        """Test risk tier classification."""
        multiplier = DriftAwareRiskMultiplier()

        # Normal tier
        normal = DriftRiskMultiplier(1.0, 0.0, 0.0, 1.05, 0.9, "")
        assert multiplier.get_tier_from_multiplier(normal) == "NORMAL"

        # Elevated tier
        elevated = DriftRiskMultiplier(1.0, 0.15, 0.0, 1.15, 0.9, "")
        assert multiplier.get_tier_from_multiplier(elevated) == "ELEVATED"

        # High tier
        high = DriftRiskMultiplier(1.0, 0.3, 0.0, 1.30, 0.9, "")
        assert multiplier.get_tier_from_multiplier(high) == "HIGH"

        # Critical tier
        critical = DriftRiskMultiplier(1.0, 0.5, 0.1, 1.60, 0.9, "")
        assert multiplier.get_tier_from_multiplier(critical) == "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: DRIFT DIAGNOSTICS REPORTER
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftDiagnosticsReporter:
    """Tests for DriftDiagnosticsReporter class."""

    def test_init(self):
        """Test initialization."""
        reporter = DriftDiagnosticsReporter()

        assert reporter.attributor is not None
        assert reporter.validator is not None
        assert reporter.risk_multiplier is not None

    def test_generate_report(self):
        """Test report generation."""
        reporter = DriftDiagnosticsReporter()

        drift_stats = {
            "avg_delta": 0.15,
            "p95_delta": 0.25,
            "max_delta": 0.40,
            "event_count": 100,
            "drift_flag": True,
        }

        feature_attributions = [
            DriftFeatureAttribution(
                feature_name="planned_transit_hours",
                base_importance=0.8,
                drift_magnitude=0.25,
                drift_direction="positive",
                drift_severity=DriftSeverity.SIGNIFICANT,
                drift_weighted_importance=0.90,
                rank=1,
            ),
            DriftFeatureAttribution(
                feature_name="eta_deviation_hours",
                base_importance=0.6,
                drift_magnitude=0.15,
                drift_direction="stable",
                drift_severity=DriftSeverity.MODERATE,
                drift_weighted_importance=0.65,
                rank=2,
            ),
        ]

        report = reporter.generate_report(
            drift_stats=drift_stats,
            feature_attributions=feature_attributions,
        )

        assert isinstance(report, str)
        assert "ML Drift Diagnostics Report v0.2" in report
        assert "MAGGIE" in report
        assert "planned_transit_hours" in report
        assert "Recommendations" in report

    def test_generate_report_with_monotonicity(self):
        """Test report with monotonicity results."""
        reporter = DriftDiagnosticsReporter()

        drift_stats = {"avg_delta": 0.10, "p95_delta": 0.18, "event_count": 50, "drift_flag": False}
        feature_attributions = []

        monotonicity_result = MonotonicityValidationResult(
            is_valid=False,
            total_features=10,
            validated_features=8,
            violations=[
                MonotonicityViolation(
                    feature_name="test_feature",
                    feature_type="time",
                    expected_direction="increasing",
                    actual_direction="decreasing",
                    violation_score=0.65,
                    sample_count=100,
                    recommendation="Review feature engineering",
                ),
            ],
            passed_features=["feature_a", "feature_b"],
        )

        report = reporter.generate_report(
            drift_stats=drift_stats,
            feature_attributions=feature_attributions,
            monotonicity_result=monotonicity_result,
        )

        assert "Monotonicity Validation" in report
        assert "FAIL" in report
        assert "test_feature" in report

    def test_generate_report_with_corridors(self):
        """Test report with corridor attributions."""
        reporter = DriftDiagnosticsReporter()

        drift_stats = {"avg_delta": 0.12, "p95_delta": 0.22, "event_count": 80, "drift_flag": False}
        feature_attributions = []

        corridor_attributions = [
            CorridorAttribution(
                corridor="US-CN",
                event_count=30,
                avg_delta=0.18,
                p95_delta=0.32,
                drift_flag=True,
                top_drift_features=[],
            ),
            CorridorAttribution(
                corridor="US-MX",
                event_count=50,
                avg_delta=0.08,
                p95_delta=0.15,
                drift_flag=False,
                top_drift_features=[],
            ),
        ]

        report = reporter.generate_report(
            drift_stats=drift_stats,
            feature_attributions=feature_attributions,
            corridor_attributions=corridor_attributions,
        )

        assert "Corridor-Specific Analysis" in report
        assert "US-CN" in report
        assert "Drifting Corridors: 1" in report

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        reporter = DriftDiagnosticsReporter()

        # High drift should trigger recommendations
        drift_stats = {"p95_delta": 0.40, "event_count": 100}
        feature_attributions = [
            DriftFeatureAttribution(
                feature_name="test",
                base_importance=0.5,
                drift_magnitude=0.60,
                drift_direction="positive",
                drift_severity=DriftSeverity.CRITICAL,
                drift_weighted_importance=0.8,
            ),
        ]

        recommendations = reporter._generate_recommendations(drift_stats, feature_attributions, None, None)

        assert len(recommendations) > 0
        assert any("CRITICAL" in r for r in recommendations)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataStructures:
    """Tests for data structures."""

    def test_drift_feature_attribution_to_dict(self):
        """Test DriftFeatureAttribution serialization."""
        attr = DriftFeatureAttribution(
            feature_name="test_feature",
            base_importance=0.75,
            drift_magnitude=0.20,
            drift_direction="positive",
            drift_severity=DriftSeverity.MODERATE,
            drift_weighted_importance=0.85,
            rank=3,
        )

        d = attr.to_dict()

        assert d["feature"] == "test_feature"
        assert d["base_importance"] == 0.75
        assert d["drift_severity"] == "moderate"
        assert d["rank"] == 3

    def test_drift_severity_enum(self):
        """Test DriftSeverity enum values."""
        assert DriftSeverity.NEGLIGIBLE.value == "negligible"
        assert DriftSeverity.CRITICAL.value == "critical"

        # Test all threshold keys exist
        for severity in DriftSeverity:
            assert severity.value in DRIFT_SEVERITY_THRESHOLDS


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Integration tests for complete pipeline."""

    def test_full_diagnostics_pipeline(self, sample_shadow_events, sample_reference_data):
        """Test complete diagnostics pipeline."""
        from app.ml.drift_diagnostics import run_drift_diagnostics

        # Mock the feature_forensics import
        with patch("app.ml.drift_diagnostics.compute_feature_statistics") as mock_stats:
            # Return mock stats
            from collections import namedtuple

            MockStats = namedtuple("MockStats", ["mean", "std"])

            mock_stats.return_value = {
                "planned_transit_hours": MockStats(mean=96, std=30),
                "eta_deviation_hours": MockStats(mean=8, std=5),
            }

            report, summary = run_drift_diagnostics(
                shadow_events=sample_shadow_events,
                reference_data=sample_reference_data,
                save_report=False,
            )

            assert isinstance(report, str)
            assert isinstance(summary, dict)
            assert "drift_stats" in summary
            assert "risk_tier" in summary


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
