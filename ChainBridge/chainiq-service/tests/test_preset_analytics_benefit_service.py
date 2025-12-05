"""MAGGIE PAC-005 — AI Benefit Score Service Tests.

Tests for time-bucketed aggregation and benefit score computation.
MAGGIE-LEVEL: No mercy, comprehensive edge cases.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from app.models_preset import PresetAnalyticsSnapshot
from app.services.preset_analytics import (
    get_time_buckets,
    compute_ai_benefit_score,
    get_ai_benefit,
    TimeBucketMetrics,
    BenefitScoreResult,
)


# =============================================================================
# TIME BUCKET TESTS
# =============================================================================


def test_get_time_buckets_no_data_returns_empty_buckets(db_session: Session) -> None:
    """With no snapshots, all buckets should have zeros and interaction_count=0."""
    buckets = get_time_buckets(db_session, profile="moderate", window_days=28, buckets=7)

    assert len(buckets) == 7
    for bucket in buckets:
        assert bucket.ctr == 0.0
        assert bucket.hit_at_1 == 0.0
        assert bucket.hit_at_3 == 0.0
        assert bucket.avg_time_to_preset_ms is None
        assert bucket.interaction_count == 0


def test_get_time_buckets_with_snapshots_aggregates_correctly(db_session: Session) -> None:
    """Snapshots should be grouped into correct buckets with averaged KPIs."""
    now = datetime.now(timezone.utc)
    window_days = 28
    buckets_count = 7

    # Create snapshots in the last bucket (most recent)
    recent_time = now - timedelta(days=1)  # Within last bucket

    snap1 = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.6,
        hit_at_1=0.4,
        hit_at_3=0.7,
        avg_time_to_preset_ms=1000.0,
        interaction_count=5,
        created_at=recent_time,
    )
    snap2 = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.8,
        hit_at_1=0.6,
        hit_at_3=0.9,
        avg_time_to_preset_ms=2000.0,
        interaction_count=10,
        created_at=recent_time,
    )

    db_session.add_all([snap1, snap2])
    db_session.commit()

    buckets = get_time_buckets(db_session, profile="moderate", window_days=window_days, buckets=buckets_count)

    assert len(buckets) == buckets_count

    # Last bucket should have our data
    last_bucket = buckets[-1]
    assert last_bucket.ctr == pytest.approx((0.6 + 0.8) / 2)
    assert last_bucket.hit_at_1 == pytest.approx((0.4 + 0.6) / 2)
    assert last_bucket.hit_at_3 == pytest.approx((0.7 + 0.9) / 2)
    assert last_bucket.avg_time_to_preset_ms == pytest.approx((1000.0 + 2000.0) / 2)
    assert last_bucket.interaction_count == 15

    # Earlier buckets should be empty
    for bucket in buckets[:-1]:
        assert bucket.interaction_count == 0


def test_get_time_buckets_filters_by_profile(db_session: Session) -> None:
    """Snapshots for different profiles should not be mixed."""
    # Use naive datetime to match datetime.utcnow() used in get_time_buckets
    now = datetime.utcnow()
    # Place snapshot solidly inside the last bucket (0.5 days ago)
    recent = now - timedelta(hours=12)

    # Add moderate and aggressive snapshots
    snap_moderate = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.8,
        hit_at_1=0.6,
        hit_at_3=0.9,
        avg_time_to_preset_ms=1500.0,
        interaction_count=10,
        created_at=recent,
    )
    snap_aggressive = PresetAnalyticsSnapshot(
        profile="aggressive",
        ctr=0.5,
        hit_at_1=0.3,
        hit_at_3=0.5,
        avg_time_to_preset_ms=3000.0,
        interaction_count=5,
        created_at=recent,
    )

    db_session.add_all([snap_moderate, snap_aggressive])
    db_session.commit()

    moderate_buckets = get_time_buckets(db_session, profile="moderate", window_days=7, buckets=7)
    aggressive_buckets = get_time_buckets(db_session, profile="aggressive", window_days=7, buckets=7)

    # Check moderate results
    moderate_last = moderate_buckets[-1]
    assert moderate_last.ctr == pytest.approx(0.8)
    assert moderate_last.interaction_count == 10

    # Check aggressive results
    aggressive_last = aggressive_buckets[-1]
    assert aggressive_last.ctr == pytest.approx(0.5)
    assert aggressive_last.interaction_count == 5


def test_get_time_buckets_increasing_metrics_over_time(db_session: Session) -> None:
    """When metrics improve over time, later buckets should have higher values."""
    now = datetime.now(timezone.utc)
    window_days = 28
    buckets_count = 7
    bucket_duration_days = window_days / buckets_count

    # Create snapshots with increasing CTR over time
    snapshots = []
    for i in range(buckets_count):
        # Place one snapshot in each bucket
        bucket_center = now - timedelta(days=window_days) + timedelta(days=(i + 0.5) * bucket_duration_days)
        ctr = 0.3 + (i * 0.1)  # Increasing: 0.3, 0.4, 0.5, ...

        snap = PresetAnalyticsSnapshot(
            profile="moderate",
            ctr=ctr,
            hit_at_1=0.5,
            hit_at_3=0.7,
            avg_time_to_preset_ms=2000 - (i * 200),  # Decreasing time (faster)
            interaction_count=10,
            created_at=bucket_center,
        )
        snapshots.append(snap)

    db_session.add_all(snapshots)
    db_session.commit()

    buckets = get_time_buckets(db_session, profile="moderate", window_days=window_days, buckets=buckets_count)

    # Verify increasing CTR
    ctrs = [b.ctr for b in buckets]
    for i in range(len(ctrs) - 1):
        assert ctrs[i] < ctrs[i + 1], f"CTR should increase: {ctrs}"

    # Verify decreasing time (getting faster)
    times = [b.avg_time_to_preset_ms for b in buckets if b.avg_time_to_preset_ms is not None]
    for i in range(len(times) - 1):
        assert times[i] > times[i + 1], f"Time should decrease: {times}"


# =============================================================================
# BENEFIT SCORE COMPUTATION TESTS
# =============================================================================


def _make_bucket(
    ctr: float = 0.5,
    hit_at_1: float = 0.3,
    hit_at_3: float = 0.6,
    avg_time: Optional[float] = 1500.0,
    interactions: int = 10,
    offset_days: int = 0,
) -> TimeBucketMetrics:
    """Helper to create a TimeBucketMetrics for testing."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=offset_days + 4)
    end = now - timedelta(days=offset_days)
    return TimeBucketMetrics(
        window_start=start,
        window_end=end,
        ctr=ctr,
        hit_at_1=hit_at_1,
        hit_at_3=hit_at_3,
        avg_time_to_preset_ms=avg_time,
        interaction_count=interactions,
    )


def test_compute_benefit_score_empty_buckets_returns_neutral() -> None:
    """With no buckets, should return neutral score (0.0)."""
    result = compute_ai_benefit_score([], profile="moderate", window_days=28)

    assert result.ai_benefit_score == 0.0
    assert result.speed_gain == 0.0
    assert result.precision_lift == 0.0
    assert result.adoption_intensity == 0.0
    assert result.stability_score == 0.5  # Neutral when insufficient data


def test_compute_benefit_score_ai_clearly_improving() -> None:
    """When later buckets outperform early ones, ABS should be positive."""
    # Early buckets (baseline): slow, low hit@3
    early_buckets = [
        _make_bucket(hit_at_3=0.4, avg_time=3000.0, interactions=10, offset_days=24),
        _make_bucket(hit_at_3=0.4, avg_time=3000.0, interactions=10, offset_days=20),
        _make_bucket(hit_at_3=0.4, avg_time=3000.0, interactions=10, offset_days=16),
    ]

    # Recent buckets (current): fast, high hit@3
    recent_buckets = [
        _make_bucket(hit_at_3=0.8, avg_time=1500.0, interactions=15, offset_days=4),
        _make_bucket(hit_at_3=0.85, avg_time=1400.0, interactions=15, offset_days=0),
    ]

    all_buckets = early_buckets + recent_buckets
    result = compute_ai_benefit_score(all_buckets, profile="moderate", window_days=28)

    assert result.ai_benefit_score > 0, f"Expected positive ABS, got {result.ai_benefit_score}"
    assert result.speed_gain > 0, f"Expected positive speed gain, got {result.speed_gain}"
    assert result.precision_lift > 0, f"Expected positive precision lift, got {result.precision_lift}"


def test_compute_benefit_score_ai_clearly_hurting() -> None:
    """When later buckets underperform early ones, ABS should be negative."""
    # Early buckets (baseline): good performance
    early_buckets = [
        _make_bucket(hit_at_3=0.8, avg_time=1000.0, interactions=10, offset_days=24),
        _make_bucket(hit_at_3=0.8, avg_time=1000.0, interactions=10, offset_days=20),
        _make_bucket(hit_at_3=0.8, avg_time=1000.0, interactions=10, offset_days=16),
    ]

    # Recent buckets (current): degraded performance
    recent_buckets = [
        _make_bucket(hit_at_3=0.3, avg_time=3000.0, interactions=5, offset_days=4),
        _make_bucket(hit_at_3=0.25, avg_time=3500.0, interactions=5, offset_days=0),
    ]

    all_buckets = early_buckets + recent_buckets
    result = compute_ai_benefit_score(all_buckets, profile="moderate", window_days=28)

    assert result.ai_benefit_score < 0, f"Expected negative ABS, got {result.ai_benefit_score}"
    assert result.speed_gain < 0, f"Expected negative speed gain, got {result.speed_gain}"
    assert result.precision_lift < 0, f"Expected negative precision lift, got {result.precision_lift}"


def test_compute_benefit_score_flat_performance_near_zero() -> None:
    """When performance is flat, ABS should be near zero."""
    # All buckets have same performance
    buckets = [
        _make_bucket(hit_at_3=0.5, avg_time=2000.0, interactions=10, offset_days=24),
        _make_bucket(hit_at_3=0.5, avg_time=2000.0, interactions=10, offset_days=20),
        _make_bucket(hit_at_3=0.5, avg_time=2000.0, interactions=10, offset_days=16),
        _make_bucket(hit_at_3=0.5, avg_time=2000.0, interactions=10, offset_days=4),
        _make_bucket(hit_at_3=0.5, avg_time=2000.0, interactions=10, offset_days=0),
    ]

    result = compute_ai_benefit_score(buckets, profile="moderate", window_days=28)

    # Speed gain and precision lift should be 0
    assert result.speed_gain == pytest.approx(0.0, abs=0.01)
    assert result.precision_lift == pytest.approx(0.0, abs=0.01)

    # Stability should be high (consistent)
    assert result.stability_score > 0.8, f"Expected high stability, got {result.stability_score}"


def test_compute_benefit_score_bounds_respected() -> None:
    """All scores should be within their defined bounds."""
    # Extreme case: massive improvement
    extreme_buckets = [
        _make_bucket(hit_at_3=0.0, avg_time=10000.0, interactions=10, offset_days=20),
        _make_bucket(hit_at_3=0.0, avg_time=10000.0, interactions=10, offset_days=16),
        _make_bucket(hit_at_3=1.0, avg_time=100.0, interactions=100, offset_days=4),
        _make_bucket(hit_at_3=1.0, avg_time=100.0, interactions=100, offset_days=0),
    ]

    result = compute_ai_benefit_score(extreme_buckets, profile="moderate", window_days=28)

    assert -1.0 <= result.ai_benefit_score <= 1.0
    assert -1.0 <= result.speed_gain <= 1.0
    assert -1.0 <= result.precision_lift <= 1.0
    assert 0.0 <= result.adoption_intensity <= 1.0
    assert 0.0 <= result.stability_score <= 1.0


def test_compute_benefit_score_insufficient_baseline_data() -> None:
    """With insufficient baseline data, should return neutral-ish scores."""
    # Only recent buckets with data
    buckets = [
        _make_bucket(hit_at_3=0.0, avg_time=None, interactions=0, offset_days=20),
        _make_bucket(hit_at_3=0.0, avg_time=None, interactions=0, offset_days=16),
        _make_bucket(hit_at_3=0.8, avg_time=1500.0, interactions=10, offset_days=4),
        _make_bucket(hit_at_3=0.9, avg_time=1400.0, interactions=10, offset_days=0),
    ]

    result = compute_ai_benefit_score(buckets, profile="moderate", window_days=28)

    # With no baseline, deltas should be 0
    assert result.speed_gain == 0.0
    assert result.precision_lift == 0.0


def test_compute_benefit_score_adoption_intensity_calculation() -> None:
    """Adoption intensity should reflect recent vs total interactions."""
    # Early: lots of activity, Recent: less activity
    buckets = [
        _make_bucket(interactions=100, offset_days=20),
        _make_bucket(interactions=100, offset_days=16),
        _make_bucket(interactions=100, offset_days=12),
        _make_bucket(interactions=10, offset_days=4),
        _make_bucket(interactions=10, offset_days=0),
    ]

    result = compute_ai_benefit_score(buckets, profile="moderate", window_days=28)

    # Recent interactions (last 2 buckets) = 20, total = 320
    # AIx = 20 / 320 = 0.0625
    expected_aix = 20 / 320
    assert result.adoption_intensity == pytest.approx(expected_aix, abs=0.01)


def test_compute_benefit_score_stability_high_variance() -> None:
    """High variance in hit@3 should result in low stability score."""
    # Extreme alternating high/low performance (0.0 to 1.0)
    # This creates maximum variance = 0.25, so stability = 0.0
    buckets = [
        _make_bucket(hit_at_3=0.0, interactions=10, offset_days=24),
        _make_bucket(hit_at_3=1.0, interactions=10, offset_days=20),
        _make_bucket(hit_at_3=0.0, interactions=10, offset_days=16),
        _make_bucket(hit_at_3=1.0, interactions=10, offset_days=4),
        _make_bucket(hit_at_3=0.0, interactions=10, offset_days=0),
    ]

    result = compute_ai_benefit_score(buckets, profile="moderate", window_days=28)

    # Maximum variance (0.0 to 1.0) should give very low stability
    # variance = 0.24 (nearly max), stability = 1 - 0.24/0.25 = ~0.04
    assert result.stability_score < 0.2, f"Expected very low stability, got {result.stability_score}"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


def test_get_ai_benefit_integration(db_session: Session) -> None:
    """Integration test: full pipeline from DB to benefit score."""
    now = datetime.now(timezone.utc)

    # Create improving trend
    snapshots = [
        # Early snapshots (baseline)
        PresetAnalyticsSnapshot(
            profile="moderate",
            ctr=0.5,
            hit_at_1=0.3,
            hit_at_3=0.5,
            avg_time_to_preset_ms=3000.0,
            interaction_count=10,
            created_at=now - timedelta(days=20),
        ),
        PresetAnalyticsSnapshot(
            profile="moderate",
            ctr=0.5,
            hit_at_1=0.3,
            hit_at_3=0.5,
            avg_time_to_preset_ms=3000.0,
            interaction_count=10,
            created_at=now - timedelta(days=15),
        ),
        # Recent snapshots (improved)
        PresetAnalyticsSnapshot(
            profile="moderate",
            ctr=0.8,
            hit_at_1=0.6,
            hit_at_3=0.85,
            avg_time_to_preset_ms=1500.0,
            interaction_count=20,
            created_at=now - timedelta(days=3),
        ),
        PresetAnalyticsSnapshot(
            profile="moderate",
            ctr=0.85,
            hit_at_1=0.7,
            hit_at_3=0.9,
            avg_time_to_preset_ms=1400.0,
            interaction_count=25,
            created_at=now - timedelta(days=1),
        ),
    ]

    db_session.add_all(snapshots)
    db_session.commit()

    result = get_ai_benefit(db_session, profile="moderate", window_days=28, buckets=7)

    assert isinstance(result, BenefitScoreResult)
    assert result.profile == "moderate"
    assert result.window_days == 28

    # Should show improvement
    assert result.ai_benefit_score > 0, f"Expected positive ABS, got {result}"
    assert result.speed_gain > 0
    assert result.precision_lift > 0


def test_get_ai_benefit_empty_db_returns_neutral(db_session: Session) -> None:
    """With no data, should return neutral scores."""
    result = get_ai_benefit(db_session, profile="moderate", window_days=28, buckets=7)

    # With empty data: SG=0, PL=0, AIx=0, stability=0.5 (neutral)
    # ABS = 0.40*0 + 0.30*0 + 0.20*0 + 0.10*0.5 = 0.05
    assert result.ai_benefit_score == pytest.approx(0.05)
    assert result.speed_gain == 0.0
    assert result.precision_lift == 0.0
    assert result.adoption_intensity == 0.0
    assert result.stability_score == 0.5  # Neutral when no data
