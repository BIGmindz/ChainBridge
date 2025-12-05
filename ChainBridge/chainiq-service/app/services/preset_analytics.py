"""MAGGIE PAC-005 — AI Benefit Scoring & Trend Analytics.

This module extends preset analytics with:
1. Time-bucketed aggregation for trend analysis
2. AI Benefit Score computation (glass-box formula)
3. Supporting metrics: Speed Gain, Precision Lift, Adoption Intensity, Stability

Design Principles:
- All metrics are interpretable and formula-based (no black-box ML)
- Scores are bounded to [-1.0, 1.0] for easy interpretation
- Missing data yields neutral scores (0.0), not errors
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models_preset import PresetAnalyticsSnapshot
from app.schemas_ai_presets import (
    PresetAnalyticsPayload,
    PresetAnalyticsSummary,
)


# =============================================================================
# PAC-005 DATA STRUCTURES
# =============================================================================


@dataclass
class TimeBucketMetrics:
    """Metrics for a single time bucket (window slice).

    Used to track how KPIs evolve over time for trend analysis.
    """

    window_start: datetime
    window_end: datetime
    ctr: float
    hit_at_1: float
    hit_at_3: float
    avg_time_to_preset_ms: Optional[float]
    interaction_count: int


@dataclass
class BenefitScoreResult:
    """Result of AI benefit score computation.

    All scores are glass-box interpretable:
    - ai_benefit_score: Net benefit in [-1.0, 1.0]. Positive = AI helping.
    - speed_gain: How much faster AI makes preset selection vs baseline.
    - precision_lift: Improvement in Hit@3 vs baseline.
    - adoption_intensity: Fraction of recent activity vs total.
    - stability_score: How consistent the metrics are (low variance = high).
    """

    profile: str
    window_days: int
    ai_benefit_score: float
    speed_gain: float
    precision_lift: float
    adoption_intensity: float
    stability_score: float


# =============================================================================
# PAC-005 CONFIGURATION
# =============================================================================

# Weights for AI Benefit Score composite
# ABS = w_sg * SG + w_pl * PL + w_ai * AIx + w_st * ST
BENEFIT_WEIGHTS = {
    "speed_gain": 0.40,
    "precision_lift": 0.30,
    "adoption_intensity": 0.20,
    "stability": 0.10,
}

# Minimum interactions needed for reliable metrics
MIN_INTERACTIONS_FOR_BASELINE = 3
MIN_INTERACTIONS_FOR_CURRENT = 1


def ingest_preset_analytics(
    db: Session,
    payload: PresetAnalyticsPayload,
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
) -> PresetAnalyticsSnapshot:
    """Persist a single analytics snapshot from the frontend.

    This stores only high-level KPIs; detailed per-preset stats live
    elsewhere (behavior stats, Supabase raw events).
    """

    snapshot = PresetAnalyticsSnapshot(
        profile=payload.profile,
        ctr=payload.kpis.ctr,
        hit_at_1=payload.kpis.hit_at_1,
        hit_at_3=payload.kpis.hit_at_3,
        avg_time_to_preset_ms=payload.kpis.avg_time_to_preset_ms,
        interaction_count=payload.stats.get("interactionCount"),
        tenant_id=tenant_id,
        console_id=console_id,
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot


def get_preset_analytics_summary(
    db: Session,
    profile: str,
    window_days: int = 7,
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
) -> PresetAnalyticsSummary:
    """Aggregate recent analytics snapshots into a summary window."""

    now = datetime.utcnow()
    since = now - timedelta(days=window_days)

    q = db.query(PresetAnalyticsSnapshot).filter(
        PresetAnalyticsSnapshot.profile == profile,
        PresetAnalyticsSnapshot.created_at >= since,
    )

    if tenant_id is not None:
        q = q.filter(PresetAnalyticsSnapshot.tenant_id == tenant_id)
    if console_id is not None:
        q = q.filter(PresetAnalyticsSnapshot.console_id == console_id)

    snapshots = q.all()
    if not snapshots:
        # Always return 200 with zeroed summary if no data
        return PresetAnalyticsSummary(
            profile=profile,
            window_days=window_days,
            ctr=0.0,
            hit_at_1=0.0,
            hit_at_3=0.0,
            avg_time_to_preset_ms=None,
            snapshots=0,
        )

    n = len(snapshots)
    ctr = sum(s.ctr for s in snapshots) / n
    hit1 = sum(s.hit_at_1 for s in snapshots) / n
    hit3 = sum(s.hit_at_3 for s in snapshots) / n

    times = [s.avg_time_to_preset_ms for s in snapshots if s.avg_time_to_preset_ms is not None]
    avg_time = sum(times) / len(times) if times else None

    return PresetAnalyticsSummary(
        profile=profile,
        window_days=window_days,
        ctr=ctr,
        hit_at_1=hit1,
        hit_at_3=hit3,
        avg_time_to_preset_ms=avg_time,
        snapshots=n,
    )


# =============================================================================
# PAC-005 TIME-BUCKETED AGGREGATION
# =============================================================================


def get_time_buckets(
    db: Session,
    profile: str,
    window_days: int = 28,
    buckets: int = 7,
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
) -> List[TimeBucketMetrics]:
    """Aggregate snapshots into time buckets for trend analysis.

    Splits the window into `buckets` equal time slices and computes
    average KPIs for each. Empty buckets return zeros with interaction_count=0.

    Args:
        db: Database session
        profile: Profile name (conservative/moderate/aggressive)
        window_days: Total lookback window in days
        buckets: Number of time slices to create
        tenant_id: Optional tenant filter
        console_id: Optional console filter

    Returns:
        List of TimeBucketMetrics, oldest first
    """
    now = datetime.utcnow()
    window_start = now - timedelta(days=window_days)
    bucket_duration = timedelta(days=window_days) / buckets

    # Query all snapshots in window
    q = db.query(PresetAnalyticsSnapshot).filter(
        PresetAnalyticsSnapshot.profile == profile,
        PresetAnalyticsSnapshot.created_at >= window_start,
    )

    if tenant_id is not None:
        q = q.filter(PresetAnalyticsSnapshot.tenant_id == tenant_id)
    if console_id is not None:
        q = q.filter(PresetAnalyticsSnapshot.console_id == console_id)

    all_snapshots = q.all()

    # Build buckets
    result: List[TimeBucketMetrics] = []

    for i in range(buckets):
        bucket_start = window_start + (i * bucket_duration)
        bucket_end = window_start + ((i + 1) * bucket_duration)

        # Filter snapshots for this bucket
        bucket_snaps = [s for s in all_snapshots if bucket_start <= s.created_at < bucket_end]

        if not bucket_snaps:
            # Empty bucket
            result.append(
                TimeBucketMetrics(
                    window_start=bucket_start,
                    window_end=bucket_end,
                    ctr=0.0,
                    hit_at_1=0.0,
                    hit_at_3=0.0,
                    avg_time_to_preset_ms=None,
                    interaction_count=0,
                )
            )
        else:
            n = len(bucket_snaps)
            ctr = sum(s.ctr for s in bucket_snaps) / n
            hit1 = sum(s.hit_at_1 for s in bucket_snaps) / n
            hit3 = sum(s.hit_at_3 for s in bucket_snaps) / n

            times = [s.avg_time_to_preset_ms for s in bucket_snaps if s.avg_time_to_preset_ms is not None]
            avg_time = sum(times) / len(times) if times else None

            total_interactions = sum(s.interaction_count or 0 for s in bucket_snaps)

            result.append(
                TimeBucketMetrics(
                    window_start=bucket_start,
                    window_end=bucket_end,
                    ctr=ctr,
                    hit_at_1=hit1,
                    hit_at_3=hit3,
                    avg_time_to_preset_ms=avg_time,
                    interaction_count=total_interactions,
                )
            )

    return result


# =============================================================================
# PAC-005 BENEFIT SCORE COMPUTATION
# =============================================================================


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def _safe_mean(values: List[float]) -> float:
    """Compute mean, returning 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


def _compute_variance(values: List[float]) -> float:
    """Compute population variance, returning 0.0 for insufficient data."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def compute_ai_benefit_score(
    buckets: List[TimeBucketMetrics],
    profile: str = "unknown",
    window_days: int = 28,
) -> BenefitScoreResult:
    """Compute the AI Benefit Score from time-bucketed metrics.

    Glass-box formula:
        ABS = 0.40 * SG_normalized + 0.30 * PL_normalized
            + 0.20 * AIx + 0.10 * stability_bonus

    Where:
    - SG (Speed Gain): (baseline_time - current_time) / baseline_time
      Positive = AI is faster, clamped to [-1, 1]
    - PL (Precision Lift): current_hit@3 - baseline_hit@3
      Clamped to [-1, 1]
    - AIx (Adoption Intensity): recent_interactions / total_interactions
    - Stability: 1.0 - normalized_variance (rewards consistency)

    Baseline = first half of buckets with data
    Current = last 1-2 buckets with data

    Args:
        buckets: Time-ordered list of metrics (oldest first)
        profile: Profile name for result labeling
        window_days: Window size for result labeling

    Returns:
        BenefitScoreResult with all component scores
    """
    if not buckets:
        return BenefitScoreResult(
            profile=profile,
            window_days=window_days,
            ai_benefit_score=0.0,
            speed_gain=0.0,
            precision_lift=0.0,
            adoption_intensity=0.0,
            stability_score=0.5,
        )

    n_buckets = len(buckets)
    midpoint = n_buckets // 2

    # Split into baseline (early) and current (late) buckets
    baseline_buckets = buckets[:midpoint] if midpoint > 0 else []
    current_buckets = buckets[-2:] if n_buckets >= 2 else buckets

    # Filter to buckets with meaningful data
    baseline_with_data = [b for b in baseline_buckets if b.interaction_count >= MIN_INTERACTIONS_FOR_BASELINE]
    current_with_data = [b for b in current_buckets if b.interaction_count >= MIN_INTERACTIONS_FOR_CURRENT]

    # ---------------------
    # Speed Gain (SG)
    # ---------------------
    baseline_times = [b.avg_time_to_preset_ms for b in baseline_with_data if b.avg_time_to_preset_ms is not None]
    current_times = [b.avg_time_to_preset_ms for b in current_with_data if b.avg_time_to_preset_ms is not None]

    baseline_avg_time = _safe_mean(baseline_times)
    current_avg_time = _safe_mean(current_times)

    if baseline_avg_time > 0 and current_times:
        # Positive SG = faster (lower time is better)
        speed_gain = (baseline_avg_time - current_avg_time) / baseline_avg_time
    else:
        speed_gain = 0.0

    speed_gain = _clamp(speed_gain, -1.0, 1.0)

    # ---------------------
    # Precision Lift (PL)
    # ---------------------
    baseline_hit3 = [b.hit_at_3 for b in baseline_with_data]
    current_hit3 = [b.hit_at_3 for b in current_with_data]

    baseline_avg_hit3 = _safe_mean(baseline_hit3)
    current_avg_hit3 = _safe_mean(current_hit3)

    if baseline_hit3 and current_hit3:
        precision_lift = current_avg_hit3 - baseline_avg_hit3
    else:
        precision_lift = 0.0

    precision_lift = _clamp(precision_lift, -1.0, 1.0)

    # ---------------------
    # Adoption Intensity (AIx)
    # ---------------------
    total_interactions = sum(b.interaction_count for b in buckets)
    recent_interactions = sum(b.interaction_count for b in current_buckets)

    if total_interactions > 0:
        adoption_intensity = recent_interactions / total_interactions
    else:
        adoption_intensity = 0.0

    adoption_intensity = _clamp(adoption_intensity, 0.0, 1.0)

    # ---------------------
    # Stability Score (ST)
    # ---------------------
    # Use variance of hit@3 across all buckets with data
    all_hit3_values = [b.hit_at_3 for b in buckets if b.interaction_count > 0]

    if len(all_hit3_values) >= 2:
        variance = _compute_variance(all_hit3_values)
        # Normalize variance: assume max reasonable variance is 0.25 (hit@3 in [0,1])
        # stability = 1 - (variance / max_variance), clamped to [0, 1]
        max_variance = 0.25
        stability_score = 1.0 - min(variance / max_variance, 1.0)
    else:
        stability_score = 0.5  # Neutral when insufficient data

    # ---------------------
    # Composite AI Benefit Score
    # ---------------------
    ai_benefit_score = (
        BENEFIT_WEIGHTS["speed_gain"] * speed_gain
        + BENEFIT_WEIGHTS["precision_lift"] * precision_lift
        + BENEFIT_WEIGHTS["adoption_intensity"] * adoption_intensity
        + BENEFIT_WEIGHTS["stability"] * stability_score
    )

    # Final clamp to [-1, 1]
    ai_benefit_score = _clamp(ai_benefit_score, -1.0, 1.0)

    return BenefitScoreResult(
        profile=profile,
        window_days=window_days,
        ai_benefit_score=round(ai_benefit_score, 4),
        speed_gain=round(speed_gain, 4),
        precision_lift=round(precision_lift, 4),
        adoption_intensity=round(adoption_intensity, 4),
        stability_score=round(stability_score, 4),
    )


# =============================================================================
# PAC-005 SERVICE ENTRYPOINT
# =============================================================================


def get_ai_benefit(
    db: Session,
    profile: str,
    window_days: int = 28,
    buckets: int = 7,
    tenant_id: Optional[str] = None,
    console_id: Optional[str] = None,
) -> BenefitScoreResult:
    """Compute AI benefit score for a profile.

    This is the main entry point for PAC-005 benefit scoring.

    Args:
        db: Database session
        profile: Profile name (conservative/moderate/aggressive)
        window_days: Lookback window in days (default 28)
        buckets: Number of time slices for trend analysis (default 7)
        tenant_id: Optional tenant filter
        console_id: Optional console filter

    Returns:
        BenefitScoreResult with ai_benefit_score in [-1.0, 1.0]

    Interpretation:
        - ai_benefit_score > 0.3: AI is clearly helping
        - ai_benefit_score in [-0.1, 0.1]: Neutral / insufficient data
        - ai_benefit_score < -0.3: AI may be hurting performance
    """
    bucket_data = get_time_buckets(db, profile, window_days, buckets, tenant_id, console_id)
    return compute_ai_benefit_score(bucket_data, profile, window_days)
