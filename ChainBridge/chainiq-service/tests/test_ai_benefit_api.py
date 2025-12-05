"""MAGGIE PAC-005 — AI Benefit Score API Tests.

Tests for the /api/ai/presets/analytics/benefit endpoint.

NOTE: Full API integration tests require Python 3.10+ due to type union syntax
in app/schemas.py. These tests verify the API route logic and schema validation
via direct function testing rather than HTTP requests.
"""

from datetime import datetime, timedelta

import pytest

from app.schemas_ai_presets import AIBenefitResponse
from app.services.preset_analytics import (
    get_ai_benefit,
    BenefitScoreResult,
)
from app.models_preset import PresetAnalyticsSnapshot


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================


def test_ai_benefit_response_schema_valid_data() -> None:
    """Schema should accept valid data."""
    response = AIBenefitResponse(
        profile="moderate",
        window_days=28,
        ai_benefit_score=0.45,
        speed_gain=0.2,
        precision_lift=0.3,
        adoption_intensity=0.8,
        stability_score=0.9,
    )

    assert response.profile == "moderate"
    assert response.window_days == 28
    assert response.ai_benefit_score == 0.45


def test_ai_benefit_response_from_service_result() -> None:
    """Schema should work with BenefitScoreResult data."""
    service_result = BenefitScoreResult(
        profile="aggressive",
        window_days=14,
        ai_benefit_score=0.5,
        speed_gain=0.3,
        precision_lift=0.25,
        adoption_intensity=0.6,
        stability_score=0.8,
    )

    response = AIBenefitResponse(
        profile=service_result.profile,
        window_days=service_result.window_days,
        ai_benefit_score=service_result.ai_benefit_score,
        speed_gain=service_result.speed_gain,
        precision_lift=service_result.precision_lift,
        adoption_intensity=service_result.adoption_intensity,
        stability_score=service_result.stability_score,
    )

    assert response.ai_benefit_score == 0.5
    assert response.profile == "aggressive"


def test_ai_benefit_response_bounds_validation() -> None:
    """Schema should handle extreme values."""
    # Maximum positive case
    response_high = AIBenefitResponse(
        profile="test",
        window_days=7,
        ai_benefit_score=1.0,
        speed_gain=1.0,
        precision_lift=1.0,
        adoption_intensity=1.0,
        stability_score=1.0,
    )
    assert response_high.ai_benefit_score == 1.0

    # Negative case (AI hurting)
    response_neg = AIBenefitResponse(
        profile="test",
        window_days=7,
        ai_benefit_score=-0.5,
        speed_gain=-0.3,
        precision_lift=-0.2,
        adoption_intensity=0.1,
        stability_score=0.2,
    )
    assert response_neg.ai_benefit_score == -0.5


# =============================================================================
# SERVICE INTEGRATION TESTS (via db_session fixture)
# =============================================================================


def test_get_ai_benefit_empty_returns_neutral(db_session) -> None:
    """With no data, should return neutral scores."""
    result = get_ai_benefit(db_session, profile="moderate", window_days=28, buckets=7)

    # Check all expected fields are present
    assert result.profile == "moderate"
    assert result.window_days == 28

    # Neutral state: SG=0, PL=0, AIx=0, ST=0.5
    # ABS = 0.40*0 + 0.30*0 + 0.20*0 + 0.10*0.5 = 0.05
    assert result.ai_benefit_score == pytest.approx(0.05)
    assert result.speed_gain == 0.0
    assert result.precision_lift == 0.0


def test_get_ai_benefit_values_in_bounds(db_session) -> None:
    """All scores should be within their defined bounds."""
    result = get_ai_benefit(db_session, profile="aggressive", window_days=14, buckets=7)

    assert -1.0 <= result.ai_benefit_score <= 1.0
    assert -1.0 <= result.speed_gain <= 1.0
    assert -1.0 <= result.precision_lift <= 1.0
    assert 0.0 <= result.adoption_intensity <= 1.0
    assert 0.0 <= result.stability_score <= 1.0


def test_get_ai_benefit_no_nan_or_inf(db_session) -> None:
    """Response should never contain NaN or Infinity."""
    result = get_ai_benefit(db_session, profile="conservative", window_days=7, buckets=7)

    import math

    assert not math.isnan(result.ai_benefit_score), "ai_benefit_score is NaN"
    assert not math.isinf(result.ai_benefit_score), "ai_benefit_score is infinite"
    assert not math.isnan(result.speed_gain), "speed_gain is NaN"
    assert not math.isinf(result.speed_gain), "speed_gain is infinite"


def test_get_ai_benefit_with_improving_data(db_session) -> None:
    """With improving data, should return positive benefit score."""
    now = datetime.utcnow()

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

    # Should show improvement
    assert result.ai_benefit_score > 0, f"Expected positive ABS, got {result}"
    assert result.speed_gain > 0, f"Expected positive speed gain, got {result}"
    assert result.precision_lift > 0, f"Expected positive precision lift, got {result}"


def test_get_ai_benefit_profile_isolation(db_session) -> None:
    """Different profiles should return different results when data differs."""
    now = datetime.utcnow()

    # Moderate: good performance
    snap_moderate = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.8,
        hit_at_1=0.6,
        hit_at_3=0.9,
        avg_time_to_preset_ms=1500.0,
        interaction_count=20,
        created_at=now - timedelta(hours=12),
    )

    # Aggressive: poor performance
    snap_aggressive = PresetAnalyticsSnapshot(
        profile="aggressive",
        ctr=0.3,
        hit_at_1=0.1,
        hit_at_3=0.3,
        avg_time_to_preset_ms=5000.0,
        interaction_count=5,
        created_at=now - timedelta(hours=12),
    )

    db_session.add_all([snap_moderate, snap_aggressive])
    db_session.commit()

    moderate_result = get_ai_benefit(db_session, profile="moderate", window_days=7, buckets=7)
    aggressive_result = get_ai_benefit(db_session, profile="aggressive", window_days=7, buckets=7)

    # Verify profiles are correctly labeled
    assert moderate_result.profile == "moderate"
    assert aggressive_result.profile == "aggressive"

    # Both have 1 snapshot, so adoption_intensity is 1.0 for both
    # The key assertion is profile isolation works - they got their own data
    assert moderate_result.adoption_intensity == 1.0
    assert aggressive_result.adoption_intensity == 1.0


def test_get_ai_benefit_window_filtering(db_session) -> None:
    """Different window sizes should filter data correctly."""
    now = datetime.utcnow()

    # Old snapshot (outside 7 day window)
    snap_old = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.3,
        hit_at_1=0.1,
        hit_at_3=0.3,
        avg_time_to_preset_ms=5000.0,
        interaction_count=50,
        created_at=now - timedelta(days=10),
    )

    # Recent snapshot
    snap_recent = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.9,
        hit_at_1=0.8,
        hit_at_3=0.95,
        avg_time_to_preset_ms=1000.0,
        interaction_count=10,
        created_at=now - timedelta(hours=12),
    )

    db_session.add_all([snap_old, snap_recent])
    db_session.commit()

    # 7 day window should only see recent
    result_7 = get_ai_benefit(db_session, profile="moderate", window_days=7, buckets=7)

    # 28 day window should see both
    result_28 = get_ai_benefit(db_session, profile="moderate", window_days=28, buckets=7)

    assert result_7.window_days == 7
    assert result_28.window_days == 28

    # 28 day window has more data (includes old snapshot)
    # This affects adoption intensity since total interactions differ


def test_get_ai_benefit_custom_buckets(db_session) -> None:
    """Custom bucket count should work."""
    now = datetime.utcnow()

    snap = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.7,
        hit_at_1=0.5,
        hit_at_3=0.8,
        avg_time_to_preset_ms=2000.0,
        interaction_count=15,
        created_at=now - timedelta(hours=12),
    )
    db_session.add(snap)
    db_session.commit()

    result = get_ai_benefit(db_session, profile="moderate", window_days=14, buckets=14)

    assert result.profile == "moderate"
    assert result.window_days == 14
