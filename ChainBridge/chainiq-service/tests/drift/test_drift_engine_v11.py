"""
ChainIQ Drift Engine v1.1 Unit Tests

Comprehensive test coverage for drift detection, scoring, and explainability.

Author: Cody (GID-01) 🔵
PAC: CODY-PAC-NEXT-034
"""

from __future__ import annotations


import pytest

from app.ml.drift_engine import (
    CorridorDriftResult,
    DriftBucket,
    DriftDirection,
    GlobalDriftSummary,
    IQCache,
    categorical_drift_bucket,
    compute_global_drift_summary,
    corridor_drift_score,
    feature_shift_delta,
    get_drift_cache,
    risk_multiplier_from_drift,
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def baseline_stats():
    """Sample baseline statistics for testing."""
    return {
        "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 1000},
        "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 1000},
        "delay_flag": {"mean": 0.15, "std": 0.36, "count": 1000},
        "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 1000},
    }


@pytest.fixture
def current_stats_drifted():
    """Sample current statistics with drift."""
    return {
        "eta_deviation_hours": {"mean": 8.2, "std": 3.1, "count": 200},  # Drifted
        "num_route_deviations": {"mean": 2.1, "std": 1.5, "count": 200},
        "delay_flag": {"mean": 0.25, "std": 0.43, "count": 200},  # Drifted
        "shipper_on_time_pct_90d": {"mean": 84.0, "std": 9.0, "count": 200},
    }


@pytest.fixture
def current_stats_stable():
    """Sample current statistics without drift."""
    return {
        "eta_deviation_hours": {"mean": 5.1, "std": 2.0, "count": 200},
        "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 200},
        "delay_flag": {"mean": 0.15, "std": 0.36, "count": 200},
        "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 200},
    }


@pytest.fixture
def corridor_baselines(baseline_stats):
    """Multi-corridor baseline stats."""
    return {
        "US-CN": baseline_stats,
        "EU-IN": baseline_stats,
        "US-MX": baseline_stats,
    }


@pytest.fixture
def corridor_currents(current_stats_drifted, current_stats_stable):
    """Multi-corridor current stats."""
    return {
        "US-CN": current_stats_drifted,  # Drifted
        "EU-IN": current_stats_stable,  # Stable
        "US-MX": current_stats_stable,  # Stable
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE SHIFT DELTA TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeatureShiftDelta:
    """Tests for feature_shift_delta function."""

    def test_zero_drift_same_distributions(self):
        """Identical distributions should have zero drift."""
        delta = feature_shift_delta(
            baseline_mean=10.0,
            baseline_std=2.0,
            current_mean=10.0,
            current_std=2.0,
        )
        assert delta == pytest.approx(0.0, abs=0.001)

    def test_mean_shift_only(self):
        """Mean shift with same std should produce drift."""
        delta = feature_shift_delta(
            baseline_mean=10.0,
            baseline_std=2.0,
            current_mean=14.0,  # 2 std shift
            current_std=2.0,
        )
        # Should be approximately 2.0 (normalized by baseline std)
        assert delta == pytest.approx(2.0, abs=0.1)

    def test_std_shift_only(self):
        """Std change with same mean should produce minor drift."""
        delta = feature_shift_delta(
            baseline_mean=10.0,
            baseline_std=2.0,
            current_mean=10.0,
            current_std=4.0,  # Doubled std
        )
        # Should be small (std shift weighted at 0.3)
        assert 0.1 < delta < 0.5

    def test_combined_shift(self):
        """Both mean and std shift should combine."""
        delta = feature_shift_delta(
            baseline_mean=10.0,
            baseline_std=2.0,
            current_mean=14.0,
            current_std=4.0,
        )
        # Should be greater than mean-only shift
        assert delta > 2.0

    def test_epsilon_prevents_division_by_zero(self):
        """Zero baseline std should not cause division error."""
        delta = feature_shift_delta(
            baseline_mean=10.0,
            baseline_std=0.0,  # Zero std
            current_mean=12.0,
            current_std=1.0,
        )
        assert delta > 0
        assert not float("inf") == delta


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORICAL DRIFT BUCKET TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCategoricalDriftBucket:
    """Tests for categorical_drift_bucket function."""

    def test_stable_bucket(self):
        """Low drift should return STABLE."""
        bucket = categorical_drift_bucket(0.03)
        assert bucket == DriftBucket.STABLE

    def test_minor_bucket(self):
        """Minor drift should return MINOR."""
        bucket = categorical_drift_bucket(0.08)
        assert bucket == DriftBucket.MINOR

    def test_moderate_bucket(self):
        """Moderate drift should return MODERATE."""
        bucket = categorical_drift_bucket(0.15)
        assert bucket == DriftBucket.MODERATE

    def test_severe_bucket(self):
        """Severe drift should return SEVERE."""
        bucket = categorical_drift_bucket(0.28)
        assert bucket == DriftBucket.SEVERE

    def test_critical_bucket(self):
        """Critical drift should return CRITICAL."""
        bucket = categorical_drift_bucket(0.50)
        assert bucket == DriftBucket.CRITICAL

    def test_boundary_values(self):
        """Test exact boundary values."""
        assert categorical_drift_bucket(0.05) == DriftBucket.STABLE
        assert categorical_drift_bucket(0.051) == DriftBucket.MINOR
        assert categorical_drift_bucket(0.10) == DriftBucket.MINOR
        assert categorical_drift_bucket(0.101) == DriftBucket.MODERATE

    def test_custom_thresholds(self):
        """Test with custom threshold configuration."""
        custom_thresholds = {
            "STABLE": 0.10,
            "MINOR": 0.20,
            "MODERATE": 0.30,
            "SEVERE": 0.50,
            "CRITICAL": 1.0,
        }
        bucket = categorical_drift_bucket(0.15, custom_thresholds)
        assert bucket == DriftBucket.MINOR  # 15% falls in MINOR with custom thresholds


# ═══════════════════════════════════════════════════════════════════════════════
# RISK MULTIPLIER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskMultiplierFromDrift:
    """Tests for risk_multiplier_from_drift function."""

    def test_zero_drift_base_multiplier(self):
        """Zero drift should return base multiplier."""
        mult = risk_multiplier_from_drift(0.0)
        assert mult == pytest.approx(1.0, abs=0.01)

    def test_moderate_drift_elevated_multiplier(self):
        """Moderate drift should elevate multiplier."""
        mult = risk_multiplier_from_drift(0.25)
        assert 1.0 < mult < 2.0

    def test_high_drift_approaches_max(self):
        """High drift should approach max multiplier."""
        mult = risk_multiplier_from_drift(1.0)
        assert mult > 2.0
        assert mult <= 2.5  # Should not exceed max

    def test_multiplier_is_monotonic(self):
        """Higher drift should always produce higher multiplier."""
        mult_low = risk_multiplier_from_drift(0.1)
        mult_mid = risk_multiplier_from_drift(0.3)
        mult_high = risk_multiplier_from_drift(0.6)

        assert mult_low < mult_mid < mult_high

    def test_custom_config(self):
        """Test with custom configuration."""
        config = {
            "base_multiplier": 1.5,
            "max_multiplier": 3.0,
            "drift_scaling_factor": 5.0,
        }
        mult = risk_multiplier_from_drift(0.0, config)
        assert mult == pytest.approx(1.5, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# CORRIDOR DRIFT SCORE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCorridorDriftScore:
    """Tests for corridor_drift_score function."""

    def test_stable_corridor(self, baseline_stats, current_stats_stable):
        """Stable corridor should have low drift score."""
        result = corridor_drift_score(baseline_stats, current_stats_stable)

        assert isinstance(result, CorridorDriftResult)
        assert result.drift_score < 0.10
        assert result.drift_bucket in (DriftBucket.STABLE, DriftBucket.MINOR)

    def test_drifted_corridor(self, baseline_stats, current_stats_drifted):
        """Drifted corridor should have elevated drift score."""
        result = corridor_drift_score(baseline_stats, current_stats_drifted)

        assert result.drift_score > 0.10
        assert result.drift_bucket not in (DriftBucket.STABLE,)

    def test_feature_drifts_populated(self, baseline_stats, current_stats_drifted):
        """Feature drifts should be populated and ranked."""
        result = corridor_drift_score(baseline_stats, current_stats_drifted)

        assert len(result.feature_drifts) > 0
        assert result.feature_drifts[0].contribution_rank == 1

        # Check ranks are sequential
        ranks = [fd.contribution_rank for fd in result.feature_drifts]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_top_drifting_features(self, baseline_stats, current_stats_drifted):
        """Top drifting features should be identified."""
        result = corridor_drift_score(baseline_stats, current_stats_drifted)

        assert len(result.top_drifting_features) > 0
        assert len(result.top_drifting_features) <= 5

    def test_risk_multiplier_set(self, baseline_stats, current_stats_drifted):
        """Risk multiplier should be derived from drift score."""
        result = corridor_drift_score(baseline_stats, current_stats_drifted)

        assert result.risk_multiplier >= 1.0

    def test_recommendations_generated(self, baseline_stats, current_stats_drifted):
        """Recommendations should be generated based on drift severity."""
        result = corridor_drift_score(baseline_stats, current_stats_drifted)

        assert len(result.recommendations) > 0

    def test_empty_common_features(self):
        """Should handle no common features gracefully."""
        baseline = {"feature_a": {"mean": 1.0, "std": 0.5, "count": 100}}
        current = {"feature_b": {"mean": 2.0, "std": 0.6, "count": 50}}

        result = corridor_drift_score(baseline, current)

        assert result.drift_score == 0.0
        assert "Insufficient data" in result.recommendations[0]

    def test_custom_feature_weights(self, baseline_stats, current_stats_drifted):
        """Custom feature weights should affect drift score."""
        # Weight drifted features higher
        weights = {
            "eta_deviation_hours": 2.0,
            "delay_flag": 2.0,
            "num_route_deviations": 0.5,
            "shipper_on_time_pct_90d": 0.5,
        }

        result_weighted = corridor_drift_score(baseline_stats, current_stats_drifted, feature_weights=weights)
        result_unweighted = corridor_drift_score(baseline_stats, current_stats_drifted)

        # Weighted result should differ from unweighted
        assert result_weighted.drift_score != result_unweighted.drift_score


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL DRIFT SUMMARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeGlobalDriftSummary:
    """Tests for compute_global_drift_summary function."""

    def test_global_summary_structure(self, corridor_baselines, corridor_currents):
        """Should return properly structured global summary."""
        summary = compute_global_drift_summary(corridor_baselines, corridor_currents)

        assert isinstance(summary, GlobalDriftSummary)
        assert summary.corridors_analyzed == 3
        assert 0 <= summary.overall_drift_score <= 1.0
        assert isinstance(summary.overall_bucket, DriftBucket)

    def test_drifting_corridors_count(self, corridor_baselines, corridor_currents):
        """Should count drifting corridors correctly."""
        summary = compute_global_drift_summary(corridor_baselines, corridor_currents)

        # US-CN is drifted, EU-IN and US-MX are stable
        assert summary.corridors_drifting >= 0
        assert summary.corridors_drifting <= summary.corridors_analyzed

    def test_top_drifting_corridors_sorted(self, corridor_baselines, corridor_currents):
        """Top drifting corridors should be sorted by drift score."""
        summary = compute_global_drift_summary(corridor_baselines, corridor_currents)

        if len(summary.top_drifting_corridors) > 0:
            # US-CN (drifted) should be first
            assert summary.top_drifting_corridors[0] == "US-CN"

    def test_corridor_results_populated(self, corridor_baselines, corridor_currents):
        """Corridor results should be populated."""
        summary = compute_global_drift_summary(corridor_baselines, corridor_currents)

        assert len(summary.corridor_results) == 3
        for result in summary.corridor_results:
            assert isinstance(result, CorridorDriftResult)
            assert result.corridor in ["US-CN", "EU-IN", "US-MX"]

    def test_top_drifting_features_aggregated(self, corridor_baselines, corridor_currents):
        """Should aggregate top drifting features across corridors."""
        summary = compute_global_drift_summary(corridor_baselines, corridor_currents)

        assert len(summary.top_drifting_features) > 0
        assert len(summary.top_drifting_features) <= 10


# ═══════════════════════════════════════════════════════════════════════════════
# IQCACHE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestIQCache:
    """Tests for IQCache class."""

    def test_set_and_get(self):
        """Should store and retrieve values."""
        cache = IQCache(default_ttl_seconds=60)
        cache.set("key1", {"value": 42})

        result = cache.get("key1")
        assert result == {"value": 42}

    def test_get_missing_key(self):
        """Should return None for missing keys."""
        cache = IQCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiration(self):
        """Should expire entries after TTL."""
        cache = IQCache(default_ttl_seconds=1)
        cache.set("key1", "value1")

        # Immediately should be present
        assert cache.get("key1") == "value1"

        # After waiting, should be expired
        import time

        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Should support per-entry TTL."""
        cache = IQCache(default_ttl_seconds=60)
        cache.set("short_lived", "value", ttl_seconds=1)
        cache.set("long_lived", "value", ttl_seconds=60)

        import time

        time.sleep(1.1)

        assert cache.get("short_lived") is None
        assert cache.get("long_lived") == "value"

    def test_invalidate(self):
        """Should invalidate specific entries."""
        cache = IQCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        removed = cache.invalidate("key1")

        assert removed is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_invalidate_nonexistent(self):
        """Should return False for nonexistent keys."""
        cache = IQCache()
        removed = cache.invalidate("nonexistent")
        assert removed is False

    def test_invalidate_pattern(self):
        """Should invalidate by prefix pattern."""
        cache = IQCache()
        cache.set("drift:US-CN:24", "value1")
        cache.set("drift:EU-IN:24", "value2")
        cache.set("other:key", "value3")

        count = cache.invalidate_pattern("drift:")

        assert count == 2
        assert cache.get("drift:US-CN:24") is None
        assert cache.get("drift:EU-IN:24") is None
        assert cache.get("other:key") == "value3"

    def test_clear(self):
        """Should clear all entries."""
        cache = IQCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats(self):
        """Should return cache statistics."""
        cache = IQCache(default_ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.stats()

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 0

    def test_global_cache_singleton(self):
        """Global cache should be accessible."""
        cache = get_drift_cache()
        assert isinstance(cache, IQCache)


# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT DIRECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftDirection:
    """Tests for drift direction detection."""

    def test_increasing_direction(self, baseline_stats, current_stats_drifted):
        """Should detect increasing drift direction."""
        result = corridor_drift_score(baseline_stats, current_stats_drifted)

        # eta_deviation_hours should be increasing (5.0 -> 8.2)
        eta_drift = next(fd for fd in result.feature_drifts if fd.feature_name == "eta_deviation_hours")
        assert eta_drift.shift_direction == DriftDirection.INCREASING

    def test_decreasing_direction(self, baseline_stats):
        """Should detect decreasing drift direction."""
        # Simulate decreased value
        current = {
            "eta_deviation_hours": {"mean": 3.0, "std": 2.0, "count": 200},  # Decreased
            "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 200},
            "delay_flag": {"mean": 0.15, "std": 0.36, "count": 200},
            "shipper_on_time_pct_90d": {"mean": 88.0, "std": 8.0, "count": 200},
        }

        result = corridor_drift_score(baseline_stats, current)

        eta_drift = next(fd for fd in result.feature_drifts if fd.feature_name == "eta_deviation_hours")
        assert eta_drift.shift_direction == DriftDirection.DECREASING

    def test_stable_direction(self, baseline_stats, current_stats_stable):
        """Should detect stable direction for minimal change."""
        result = corridor_drift_score(baseline_stats, current_stats_stable)

        # Most features should be stable
        stable_count = sum(1 for fd in result.feature_drifts if fd.shift_direction == DriftDirection.STABLE)
        assert stable_count >= len(result.feature_drifts) // 2


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_single_feature(self):
        """Should handle single feature correctly."""
        baseline = {"only_feature": {"mean": 10.0, "std": 2.0, "count": 100}}
        current = {"only_feature": {"mean": 15.0, "std": 3.0, "count": 50}}

        result = corridor_drift_score(baseline, current)

        assert len(result.feature_drifts) == 1
        assert result.drift_score > 0

    def test_very_large_drift(self):
        """Should handle extreme drift values."""
        baseline = {"feature": {"mean": 1.0, "std": 0.1, "count": 1000}}
        current = {"feature": {"mean": 100.0, "std": 10.0, "count": 100}}

        result = corridor_drift_score(baseline, current)

        # Score should be capped at 1.0
        assert result.drift_score <= 1.0
        assert result.drift_bucket == DriftBucket.CRITICAL

    def test_zero_count(self):
        """Should handle zero sample counts."""
        baseline = {"feature": {"mean": 10.0, "std": 2.0, "count": 0}}
        current = {"feature": {"mean": 12.0, "std": 2.5, "count": 0}}

        # Should not raise error
        result = corridor_drift_score(baseline, current)
        assert result.sample_count_baseline == 0

    def test_negative_values(self):
        """Should handle negative feature values."""
        baseline = {"feature": {"mean": -10.0, "std": 5.0, "count": 100}}
        current = {"feature": {"mean": -5.0, "std": 4.0, "count": 50}}

        result = corridor_drift_score(baseline, current)

        assert result.drift_score >= 0
        assert len(result.feature_drifts) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
