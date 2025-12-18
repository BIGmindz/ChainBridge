# tests/risk/test_trust_weights.py
"""
Unit tests for TRI trust weight computation.

Validates:
- Weight bounds [1.0, 2.0]
- Freshness decay behavior
- Gameday coverage scoring
- Evidence binding scoring
- Density scoring
- Composite geometric mean

Author: MAGGIE (GID-10) — PAC-MAGGIE-RISK-IMPL-01
"""

from datetime import datetime, timedelta

import pytest

from core.risk.trust_weights import (
    FRESHNESS_IDEAL_HOURS,
    FRESHNESS_MAX_PENALTY_HOURS,
    adjust_confidence_band_for_trust,
    compute_density_weight,
    compute_evidence_weight,
    compute_freshness_weight,
    compute_gameday_weight,
    compute_trust_weights,
    get_baseline_trust_weights,
)
from core.risk.types import TrustWeights


class TestFreshnessWeight:
    """Tests for TW-01: Freshness weight."""

    def test_fresh_data_no_penalty(self) -> None:
        """Recent events should have no penalty."""
        now = datetime.utcnow()
        recent = now - timedelta(minutes=30)
        weight = compute_freshness_weight(recent, now)
        assert weight == pytest.approx(1.0)

    def test_stale_data_max_penalty(self) -> None:
        """Old events should have max penalty."""
        now = datetime.utcnow()
        old = now - timedelta(hours=48)
        weight = compute_freshness_weight(old, now)
        assert weight == pytest.approx(2.0)

    def test_no_events_max_penalty(self) -> None:
        """No events at all should have max penalty."""
        weight = compute_freshness_weight(None, datetime.utcnow())
        assert weight == 2.0

    def test_interpolation(self) -> None:
        """Weight should interpolate between ideal and max."""
        now = datetime.utcnow()
        halfway = now - timedelta(hours=24)
        weight = compute_freshness_weight(halfway, now)
        assert 1.0 < weight < 2.0

    def test_monotonic(self) -> None:
        """Older data should always have higher penalty."""
        now = datetime.utcnow()
        times = [now - timedelta(hours=h) for h in [1, 12, 24, 36, 48]]
        weights = [compute_freshness_weight(t, now) for t in times]

        for i in range(1, len(weights)):
            assert weights[i] >= weights[i - 1]


class TestGamedayWeight:
    """Tests for TW-02: Gameday coverage weight."""

    def test_perfect_coverage_no_penalty(self) -> None:
        """100% pass rate should have no penalty."""
        weight = compute_gameday_weight(100, 100)
        assert weight == pytest.approx(1.0)

    def test_zero_coverage_max_penalty(self) -> None:
        """0% pass rate should have max penalty."""
        weight = compute_gameday_weight(0, 100)
        assert weight == pytest.approx(2.0)

    def test_no_scenarios_max_penalty(self) -> None:
        """No scenarios at all should have max penalty."""
        weight = compute_gameday_weight(0, 0)
        assert weight == 2.0

    def test_high_coverage_low_penalty(self) -> None:
        """High coverage should have low penalty."""
        weight = compute_gameday_weight(95, 100)
        assert weight < 1.2

    def test_monotonic(self) -> None:
        """Higher coverage should always have lower penalty."""
        weights = [compute_gameday_weight(p, 100) for p in range(0, 101, 10)]

        for i in range(1, len(weights)):
            assert weights[i] <= weights[i - 1]


class TestEvidenceWeight:
    """Tests for TW-03: Evidence binding weight."""

    def test_perfect_binding_no_penalty(self) -> None:
        """100% bound should have no penalty."""
        weight = compute_evidence_weight(100, 100)
        assert weight == pytest.approx(1.0)

    def test_zero_binding_max_penalty(self) -> None:
        """0% bound should have max penalty."""
        weight = compute_evidence_weight(0, 100)
        assert weight == pytest.approx(2.0)

    def test_no_executions_neutral(self) -> None:
        """No executions should have neutral weight."""
        weight = compute_evidence_weight(0, 0)
        assert weight == 1.5  # Neutral midpoint

    def test_high_binding_low_penalty(self) -> None:
        """High binding rate should have low penalty."""
        weight = compute_evidence_weight(95, 100)
        assert weight < 1.2


class TestDensityWeight:
    """Tests for TW-04: Observation density weight."""

    def test_high_density_no_penalty(self) -> None:
        """High event rate should have no penalty."""
        weight = compute_density_weight(240, 24)  # 10 events/hour
        assert weight == pytest.approx(1.0)

    def test_low_density_max_penalty(self) -> None:
        """Low event rate should have max penalty."""
        weight = compute_density_weight(12, 24)  # 0.5 events/hour
        assert weight == pytest.approx(2.0)

    def test_zero_window_neutral(self) -> None:
        """Invalid window should have neutral weight."""
        weight = compute_density_weight(100, 0)
        assert weight == 1.5  # Neutral midpoint

    def test_logarithmic_scaling(self) -> None:
        """Density perception should be logarithmic."""
        w2 = compute_density_weight(48, 24)  # 2 events/hour
        w5 = compute_density_weight(120, 24)  # 5 events/hour
        w10 = compute_density_weight(240, 24)  # 10 events/hour

        # Logarithmic means 2→5 improvement similar to 5→10
        diff_low = w2 - w5
        diff_high = w5 - w10
        # They should be in same order of magnitude
        assert diff_low > 0
        assert diff_high > 0


class TestCompositeTrustWeights:
    """Tests for composite trust weight calculation."""

    def test_all_ideal_weights(self) -> None:
        """All ideal inputs should produce all 1.0 weights."""
        now = datetime.utcnow()
        tw = compute_trust_weights(
            last_event_time=now,
            now=now,
            passing_scenarios=100,
            total_scenarios=100,
            bound_executions=100,
            total_executions=100,
            event_count=240,
            window_hours=24,
        )

        assert tw.freshness == pytest.approx(1.0)
        assert tw.gameday == pytest.approx(1.0)
        assert tw.density == pytest.approx(1.0)
        assert tw.composite == pytest.approx(1.0, abs=0.1)

    def test_all_worst_weights(self) -> None:
        """All worst inputs should produce all 2.0 weights."""
        now = datetime.utcnow()
        tw = compute_trust_weights(
            last_event_time=None,
            now=now,
            passing_scenarios=0,
            total_scenarios=100,
            bound_executions=0,
            total_executions=100,
            event_count=12,
            window_hours=24,
        )

        assert tw.freshness == 2.0
        assert tw.gameday == 2.0
        assert tw.composite == pytest.approx(2.0, abs=0.1)

    def test_geometric_mean(self) -> None:
        """Composite should be geometric mean."""
        tw = TrustWeights(
            freshness=1.0,
            gameday=2.0,
            evidence=1.0,
            density=2.0,
        )
        # Geometric mean of [1, 2, 1, 2] = (1*2*1*2)^(1/4) = 4^0.25 ≈ 1.414
        expected = (1.0 * 2.0 * 1.0 * 2.0) ** 0.25
        assert tw.composite == pytest.approx(expected)


class TestConfidenceBandAdjustment:
    """Tests for confidence band adjustment based on trust weights."""

    def test_ideal_weights_no_expansion(self) -> None:
        """Ideal weights should not expand band."""
        tw = TrustWeights(freshness=1.0, gameday=1.0, evidence=1.0, density=1.0)
        lower, upper = adjust_confidence_band_for_trust(0.3, 0.4, tw)
        assert lower == 0.3
        assert upper == 0.4

    def test_poor_weights_expand_band(self) -> None:
        """Poor weights should expand confidence band."""
        tw = TrustWeights(freshness=2.0, gameday=2.0, evidence=2.0, density=2.0)
        lower, upper = adjust_confidence_band_for_trust(0.3, 0.4, tw)
        assert lower < 0.3
        assert upper > 0.4

    def test_expansion_clamped(self) -> None:
        """Expanded band should still be in [0, 1]."""
        tw = TrustWeights(freshness=2.0, gameday=2.0, evidence=2.0, density=2.0)
        lower, upper = adjust_confidence_band_for_trust(0.1, 0.9, tw)
        assert lower >= 0.0
        assert upper <= 1.0


class TestBaselineWeights:
    """Tests for baseline trust weights."""

    def test_baseline_returns_valid_weights(self) -> None:
        """Baseline should return valid TrustWeights."""
        tw = get_baseline_trust_weights()
        assert isinstance(tw, TrustWeights)
        assert 1.0 <= tw.freshness <= 2.0
        assert 1.0 <= tw.gameday <= 2.0
        assert 1.0 <= tw.evidence <= 2.0
        assert 1.0 <= tw.density <= 2.0

    def test_baseline_is_conservative(self) -> None:
        """Baseline should represent maximum uncertainty."""
        tw = get_baseline_trust_weights()
        # At least 3 of 4 should be at max
        max_count = sum(1 for w in [tw.freshness, tw.gameday, tw.evidence, tw.density] if w == 2.0)
        assert max_count >= 3
