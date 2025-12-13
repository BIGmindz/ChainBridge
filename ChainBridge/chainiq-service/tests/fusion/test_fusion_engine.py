"""
Fusion Engine Unit Tests

Tests for FusionEngine v1.2 core scoring algorithms.
Covers drift/shadow/stability components and feature attribution.

PAC: PAC-CODY-NEXT-035
Author: Cody (GID-01)
"""

import os
import sys
import time
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ml.fusion_engine import (
    FUSION_WEIGHTS,
    CorridorFusionSummary,
    FusionCache,
    FusionSeverity,
    StabilityClass,
    TrendDirection,
    classify_fusion_severity,
    compute_drift_component,
    compute_feature_attributions,
    compute_fusion_score,
    compute_multi_corridor_fusion,
    compute_shadow_component,
    compute_stability_component,
    generate_recommendations,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def stable_drift_stats():
    """Stable corridor with minimal drift."""
    return {
        "US-MX": {
            "baseline": {
                "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 10000},
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 10000},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 10000},
            },
            "current": {
                "eta_deviation_hours": {"mean": 5.1, "std": 2.0, "count": 500},
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 500},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 500},
            },
        }
    }


@pytest.fixture
def drifted_drift_stats():
    """Corridor with significant drift."""
    return {
        "US-CN": {
            "baseline": {
                "eta_deviation_hours": {"mean": 5.0, "std": 2.0, "count": 10000},
                "num_route_deviations": {"mean": 1.5, "std": 1.2, "count": 10000},
                "delay_flag": {"mean": 0.15, "std": 0.36, "count": 10000},
            },
            "current": {
                "eta_deviation_hours": {"mean": 10.0, "std": 4.0, "count": 500},  # 2.5 std drift
                "num_route_deviations": {"mean": 3.0, "std": 2.0, "count": 500},
                "delay_flag": {"mean": 0.35, "std": 0.48, "count": 500},
            },
        }
    }


@pytest.fixture
def stable_shadow_stats():
    """Shadow stats with low delta."""
    return {
        "count": 500,
        "mean_delta": 0.05,
        "p95_delta": 0.12,
        "max_delta": 0.22,
        "drift_flag": False,
    }


@pytest.fixture
def drifted_shadow_stats():
    """Shadow stats with high delta (drift flagged)."""
    return {
        "count": 500,
        "mean_delta": 0.18,
        "p95_delta": 0.35,
        "max_delta": 0.55,
        "drift_flag": True,
    }


@pytest.fixture
def stable_historical_scores():
    """Stable historical scores (low variance)."""
    return [0.15 + (i * 0.001) for i in range(30)]  # Slowly increasing


@pytest.fixture
def volatile_historical_scores():
    """Volatile historical scores (high variance)."""
    import random

    random.seed(42)
    return [0.25 + random.uniform(-0.15, 0.15) for _ in range(30)]


# ═══════════════════════════════════════════════════════════════════════════════
# FUSION WEIGHT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFusionWeights:
    """Tests for fusion weight configuration."""

    def test_weights_sum_to_one(self):
        """Verify weights sum to 1.0."""
        total = sum(FUSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_weight_keys_present(self):
        """Verify all required weight keys exist."""
        required = {"drift_magnitude", "shadow_delta", "stability_index"}
        assert set(FUSION_WEIGHTS.keys()) == required

    def test_drift_weight_highest(self):
        """Verify drift has highest weight (40%)."""
        assert FUSION_WEIGHTS["drift_magnitude"] >= 0.4

    def test_shadow_weight_significant(self):
        """Verify shadow weight is significant (35%)."""
        assert FUSION_WEIGHTS["shadow_delta"] >= 0.35

    def test_stability_weight_present(self):
        """Verify stability has some weight."""
        assert FUSION_WEIGHTS["stability_index"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT COMPONENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDriftComponent:
    """Tests for drift component computation."""

    def test_stable_drift_returns_low_score(self, stable_drift_stats):
        """Stable data should have low drift score."""
        result = compute_drift_component(stable_drift_stats)
        assert result.score < 0.2, f"Score {result.score} too high for stable data"
        assert result.bucket in ("STABLE", "MINOR")

    def test_drifted_data_returns_high_score(self, drifted_drift_stats):
        """Drifted data should have high drift score."""
        result = compute_drift_component(drifted_drift_stats)
        assert result.score > 0.5, f"Score {result.score} too low for drifted data"
        assert result.bucket in ("MODERATE", "SEVERE", "CRITICAL")

    def test_drift_returns_top_features(self, drifted_drift_stats):
        """Should return top drifting features."""
        result = compute_drift_component(drifted_drift_stats)
        assert len(result.top_features) > 0
        assert "eta_deviation_hours" in result.top_features

    def test_drift_returns_feature_deltas(self, drifted_drift_stats):
        """Should return feature delta mapping."""
        result = compute_drift_component(drifted_drift_stats)
        assert len(result.feature_deltas) > 0
        assert "eta_deviation_hours" in result.feature_deltas

    def test_drift_score_bounded_zero_one(self, drifted_drift_stats):
        """Drift score must be in [0, 1]."""
        result = compute_drift_component(drifted_drift_stats)
        assert 0.0 <= result.score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW COMPONENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowComponent:
    """Tests for shadow mode component computation."""

    def test_stable_shadow_returns_low_delta(self, stable_shadow_stats):
        """Stable shadow should have low p95 delta."""
        result = compute_shadow_component(stable_shadow_stats)
        assert result.p95_delta < 0.25
        assert result.drift_flag is False

    def test_drifted_shadow_returns_high_delta(self, drifted_shadow_stats):
        """Drifted shadow should have high p95 delta."""
        result = compute_shadow_component(drifted_shadow_stats)
        assert result.p95_delta > 0.25
        assert result.drift_flag is True

    def test_shadow_preserves_event_count(self, stable_shadow_stats):
        """Should preserve event count from input."""
        result = compute_shadow_component(stable_shadow_stats)
        assert result.event_count == 500

    def test_shadow_max_delta_bounded(self, drifted_shadow_stats):
        """Max delta should be in [0, 1]."""
        result = compute_shadow_component(drifted_shadow_stats)
        assert 0.0 <= result.max_delta <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# STABILITY COMPONENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestStabilityComponent:
    """Tests for stability index computation."""

    def test_stable_history_returns_high_stability(self, stable_historical_scores):
        """Stable history should have high stability index."""
        result = compute_stability_component(stable_historical_scores)
        assert result.stability_index > 0.7
        assert result.stability_class in (StabilityClass.HIGHLY_STABLE, StabilityClass.STABLE)

    def test_volatile_history_returns_low_stability(self, volatile_historical_scores):
        """Volatile history should have low stability index."""
        result = compute_stability_component(volatile_historical_scores)
        assert result.stability_index < 0.5
        assert result.stability_class in (StabilityClass.VOLATILE, StabilityClass.HIGHLY_VOLATILE)

    def test_stability_computes_variance(self, stable_historical_scores):
        """Should compute 30d and 7d variance."""
        result = compute_stability_component(stable_historical_scores)
        assert result.variance_30d >= 0.0
        assert result.variance_7d >= 0.0

    def test_stability_detects_trend(self, stable_historical_scores):
        """Should detect improving/degrading/stable trend."""
        result = compute_stability_component(stable_historical_scores)
        assert result.trend in (TrendDirection.IMPROVING, TrendDirection.STABLE, TrendDirection.DEGRADING)

    def test_empty_history_returns_moderate(self):
        """Empty history should default to moderate stability."""
        result = compute_stability_component([])
        assert result.stability_class == StabilityClass.MODERATE


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ATTRIBUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeatureAttribution:
    """Tests for feature attribution computation."""

    def test_attribution_returns_list(self, drifted_drift_stats, drifted_shadow_stats):
        """Should return list of attributions."""
        result = compute_feature_attributions(drifted_drift_stats, drifted_shadow_stats, 0.5)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_attribution_has_required_fields(self, drifted_drift_stats, drifted_shadow_stats):
        """Each attribution should have required fields."""
        result = compute_feature_attributions(drifted_drift_stats, drifted_shadow_stats, 0.5)
        attr = result[0]
        assert hasattr(attr, "feature_name")
        assert hasattr(attr, "contribution_score")
        assert hasattr(attr, "contribution_pct")
        assert hasattr(attr, "rank")

    def test_attributions_sorted_by_contribution(self, drifted_drift_stats, drifted_shadow_stats):
        """Attributions should be sorted by contribution (desc)."""
        result = compute_feature_attributions(drifted_drift_stats, drifted_shadow_stats, 0.5)
        for i in range(len(result) - 1):
            assert result[i].contribution_score >= result[i + 1].contribution_score

    def test_attribution_percentages_sum_to_100(self, drifted_drift_stats, drifted_shadow_stats):
        """Attribution percentages should sum close to 100%."""
        result = compute_feature_attributions(drifted_drift_stats, drifted_shadow_stats, 0.5)
        total_pct = sum(a.contribution_pct for a in result)
        assert 95.0 <= total_pct <= 105.0  # Allow small rounding error

    def test_attribution_ranks_sequential(self, drifted_drift_stats, drifted_shadow_stats):
        """Ranks should be sequential from 1."""
        result = compute_feature_attributions(drifted_drift_stats, drifted_shadow_stats, 0.5)
        for i, attr in enumerate(result):
            assert attr.rank == i + 1


# ═══════════════════════════════════════════════════════════════════════════════
# SEVERITY CLASSIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSeverityClassification:
    """Tests for fusion severity classification."""

    def test_healthy_threshold(self):
        """Score < 0.2 should be HEALTHY."""
        assert classify_fusion_severity(0.15) == FusionSeverity.HEALTHY

    def test_elevated_threshold(self):
        """Score 0.2-0.4 should be ELEVATED."""
        assert classify_fusion_severity(0.3) == FusionSeverity.ELEVATED

    def test_warning_threshold(self):
        """Score 0.4-0.6 should be WARNING."""
        assert classify_fusion_severity(0.5) == FusionSeverity.WARNING

    def test_critical_threshold(self):
        """Score 0.6-0.8 should be CRITICAL."""
        assert classify_fusion_severity(0.7) == FusionSeverity.CRITICAL

    def test_severe_threshold(self):
        """Score > 0.8 should be SEVERE."""
        assert classify_fusion_severity(0.9) == FusionSeverity.SEVERE

    def test_boundary_healthy_elevated(self):
        """Boundary at 0.2 should be ELEVATED."""
        assert classify_fusion_severity(0.2) == FusionSeverity.ELEVATED


# ═══════════════════════════════════════════════════════════════════════════════
# FUSION SCORE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFusionScoreIntegration:
    """Integration tests for compute_fusion_score."""

    def test_stable_corridor_healthy_score(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Stable corridor should have healthy fusion score."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="US-MX",
            lookback_hours=24,
            use_cache=False,
        )
        assert result.fusion_score < 0.3
        assert result.severity in (FusionSeverity.HEALTHY, FusionSeverity.ELEVATED)

    def test_drifted_corridor_elevated_score(self, drifted_drift_stats, drifted_shadow_stats, volatile_historical_scores):
        """Drifted corridor should have elevated fusion score."""
        result = compute_fusion_score(
            drift_stats=drifted_drift_stats,
            shadow_stats=drifted_shadow_stats,
            historical_scores=volatile_historical_scores,
            corridor="US-CN",
            lookback_hours=24,
            use_cache=False,
        )
        assert result.fusion_score > 0.4
        assert result.severity in (FusionSeverity.WARNING, FusionSeverity.CRITICAL, FusionSeverity.SEVERE)

    def test_result_contains_all_components(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Result should contain all component scores."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="US-MX",
            lookback_hours=24,
            use_cache=False,
        )
        assert result.drift_component is not None
        assert result.shadow_component is not None
        assert result.stability_component is not None

    def test_result_contains_attributions(self, drifted_drift_stats, drifted_shadow_stats, volatile_historical_scores):
        """Result should contain feature attributions."""
        result = compute_fusion_score(
            drift_stats=drifted_drift_stats,
            shadow_stats=drifted_shadow_stats,
            historical_scores=volatile_historical_scores,
            corridor="US-CN",
            lookback_hours=24,
            use_cache=False,
        )
        assert len(result.top_attributions) > 0

    def test_result_has_recommendations(self, drifted_drift_stats, drifted_shadow_stats, volatile_historical_scores):
        """Drifted result should have recommendations."""
        result = compute_fusion_score(
            drift_stats=drifted_drift_stats,
            shadow_stats=drifted_shadow_stats,
            historical_scores=volatile_historical_scores,
            corridor="US-CN",
            lookback_hours=24,
            use_cache=False,
        )
        assert len(result.recommendations) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-CORRIDOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultiCorridorFusion:
    """Tests for multi-corridor fusion computation."""

    @pytest.fixture
    def multi_corridor_data(self, stable_drift_stats, drifted_drift_stats):
        """Multi-corridor test data."""
        drift = {**stable_drift_stats, **drifted_drift_stats}
        shadow = {
            "US-MX": {"count": 500, "mean_delta": 0.05, "p95_delta": 0.12, "max_delta": 0.22, "drift_flag": False},
            "US-CN": {"count": 500, "mean_delta": 0.18, "p95_delta": 0.35, "max_delta": 0.55, "drift_flag": True},
        }
        histories = {
            "US-MX": [0.15 + (i * 0.001) for i in range(30)],
            "US-CN": [0.35 + (i * 0.005) for i in range(30)],
        }
        return drift, shadow, histories

    def test_returns_corridor_summary(self, multi_corridor_data):
        """Should return CorridorFusionSummary."""
        drift, shadow, histories = multi_corridor_data
        result = compute_multi_corridor_fusion(drift, shadow, histories, 24)
        assert isinstance(result, CorridorFusionSummary)

    def test_counts_correct_corridors(self, multi_corridor_data):
        """Should count correct number of corridors."""
        drift, shadow, histories = multi_corridor_data
        result = compute_multi_corridor_fusion(drift, shadow, histories, 24)
        assert result.total_corridors == 2

    def test_computes_average_score(self, multi_corridor_data):
        """Should compute average fusion score."""
        drift, shadow, histories = multi_corridor_data
        result = compute_multi_corridor_fusion(drift, shadow, histories, 24)
        assert 0.0 <= result.avg_fusion_score <= 1.0

    def test_identifies_top_corridors(self, multi_corridor_data):
        """Should identify top corridors by score."""
        drift, shadow, histories = multi_corridor_data
        result = compute_multi_corridor_fusion(drift, shadow, histories, 24)
        assert len(result.top_corridors) > 0
        # US-CN should be top (more drift)
        assert result.top_corridors[0][0] == "US-CN"


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFusionCache:
    """Tests for FusionCache behavior."""

    def test_cache_miss_returns_none(self):
        """Cache miss should return None."""
        cache = FusionCache(max_size=100, ttl_seconds=60)
        result = cache.get("nonexistent", "fusion", 24)
        assert result is None

    def test_cache_hit_returns_result(self):
        """Cache hit should return stored result."""
        cache = FusionCache(max_size=100, ttl_seconds=60)
        mock_result = MagicMock()
        cache.put("US-MX", "fusion", 24, mock_result)
        result = cache.get("US-MX", "fusion", 24)
        assert result is mock_result

    def test_cache_invalidation(self):
        """Should invalidate cache entries."""
        cache = FusionCache(max_size=100, ttl_seconds=60)
        mock_result = MagicMock()
        cache.put("US-MX", "fusion", 24, mock_result)
        cache.invalidate("US-MX")
        result = cache.get("US-MX", "fusion", 24)
        assert result is None

    def test_cache_stats(self):
        """Should track cache statistics."""
        cache = FusionCache(max_size=100, ttl_seconds=60)
        mock_result = MagicMock()
        cache.put("US-MX", "fusion", 24, mock_result)
        cache.get("US-MX", "fusion", 24)  # Hit
        cache.get("nonexistent", "fusion", 24)  # Miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# LATENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestLatencyRequirements:
    """Tests for ALEX p95 latency requirements (<45ms)."""

    def test_fusion_score_latency_cached(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Cached fusion score should be < 5ms."""
        # Warm cache
        compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="latency-test",
            lookback_hours=24,
            use_cache=True,
        )

        # Measure cached call
        start = time.perf_counter()
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="latency-test",
            lookback_hours=24,
            use_cache=True,
        )
        latency = (time.perf_counter() - start) * 1000

        assert latency < 5.0, f"Cached latency {latency}ms exceeds 5ms"

    def test_fusion_score_latency_fresh(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Fresh fusion score should be < 45ms."""
        start = time.perf_counter()
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="latency-test-fresh",
            lookback_hours=24,
            use_cache=False,
        )
        latency = (time.perf_counter() - start) * 1000

        assert latency < 45.0, f"Fresh latency {latency}ms exceeds 45ms"

    def test_result_reports_latency(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Result should include latency measurement."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="US-MX",
            lookback_hours=24,
            use_cache=False,
        )
        assert result.latency_ms >= 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# RECOMMENDATIONS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRecommendations:
    """Tests for recommendation generation."""

    def test_healthy_has_minimal_recommendations(self):
        """Healthy status should have minimal recommendations."""
        recs = generate_recommendations(FusionSeverity.HEALTHY, [], 0.1, False)
        assert len(recs) <= 2

    def test_critical_has_many_recommendations(self):
        """Critical status should have multiple recommendations."""
        recs = generate_recommendations(
            FusionSeverity.CRITICAL,
            ["eta_deviation_hours", "delay_flag"],
            0.7,
            True,
        )
        assert len(recs) >= 3

    def test_shadow_drift_generates_recommendation(self):
        """Shadow drift flag should generate recommendation."""
        recs = generate_recommendations(FusionSeverity.WARNING, [], 0.5, True)
        shadow_rec = any("shadow" in r.lower() for r in recs)
        assert shadow_rec


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_drift_stats(self, stable_shadow_stats, stable_historical_scores):
        """Should handle empty drift stats."""
        result = compute_fusion_score(
            drift_stats={},
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor=None,
            lookback_hours=24,
            use_cache=False,
        )
        assert result.drift_component.score == 0.0

    def test_empty_shadow_stats(self, stable_drift_stats, stable_historical_scores):
        """Should handle empty shadow stats."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats={},
            historical_scores=stable_historical_scores,
            corridor="US-MX",
            lookback_hours=24,
            use_cache=False,
        )
        assert result.shadow_component.event_count == 0

    def test_empty_history(self, stable_drift_stats, stable_shadow_stats):
        """Should handle empty historical scores."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=[],
            corridor="US-MX",
            lookback_hours=24,
            use_cache=False,
        )
        assert result.stability_component.stability_class == StabilityClass.MODERATE

    def test_null_corridor_computes_global(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Null corridor should compute global score."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor=None,
            lookback_hours=24,
            use_cache=False,
        )
        assert result.corridor is None

    def test_confidence_bounded(self, stable_drift_stats, stable_shadow_stats, stable_historical_scores):
        """Confidence should be in [0, 1]."""
        result = compute_fusion_score(
            drift_stats=stable_drift_stats,
            shadow_stats=stable_shadow_stats,
            historical_scores=stable_historical_scores,
            corridor="US-MX",
            lookback_hours=24,
            use_cache=False,
        )
        assert 0.0 <= result.confidence <= 1.0
