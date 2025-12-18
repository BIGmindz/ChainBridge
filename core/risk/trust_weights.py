# core/risk/trust_weights.py
"""
TRI Trust Weight Computation — Deterministic scalars that penalize unreliable data.

Four trust weights multiply the raw TRI score to penalize:
- Stale data (freshness)
- Unverified scenarios (gameday coverage)
- Unbound evidence (evidence binding)
- Sparse observations (density)

All weights are in [1.0, 2.0] where:
- 1.0 = fully trusted (no penalty)
- 2.0 = maximum penalty (doubles risk contribution)

Author: MAGGIE (GID-10) — Machine Learning & Applied AI Lead
PAC: PAC-MAGGIE-RISK-IMPL-01
"""

import math
from datetime import datetime
from typing import Optional

from core.risk.types import TrustWeights

# ============================================================================
# Configuration Constants
# ============================================================================

# TW-01: Freshness thresholds (hours)
FRESHNESS_IDEAL_HOURS = 1.0  # Weight = 1.0 if last event within 1 hour
FRESHNESS_MAX_PENALTY_HOURS = 48.0  # Weight = 2.0 if no events for 48+ hours

# TW-02: Gameday coverage thresholds
GAMEDAY_IDEAL_PASS_RATE = 1.0  # Weight = 1.0 if 100% pass
GAMEDAY_PENALTY_THRESHOLD = 0.8  # Start penalizing below 80% pass rate

# TW-03: Evidence binding thresholds
EVIDENCE_IDEAL_BIND_RATE = 1.0  # Weight = 1.0 if 100% bound
EVIDENCE_PENALTY_THRESHOLD = 0.9  # Start penalizing below 90% bind rate

# TW-04: Density thresholds (events per hour)
DENSITY_IDEAL_RATE = 10.0  # Weight = 1.0 if 10+ events/hour
DENSITY_MIN_RATE = 1.0  # Weight = 2.0 if < 1 event/hour


# ============================================================================
# Individual Weight Calculators
# ============================================================================


def compute_freshness_weight(
    last_event_time: Optional[datetime],
    now: datetime,
) -> float:
    """
    TW-01: Freshness weight based on time since last event.

    Returns:
        Weight in [1.0, 2.0] where:
        - 1.0 = event within FRESHNESS_IDEAL_HOURS
        - 2.0 = no event for FRESHNESS_MAX_PENALTY_HOURS or more
    """
    if last_event_time is None:
        # No events at all = maximum penalty
        return 2.0

    hours_since = (now - last_event_time).total_seconds() / 3600.0

    if hours_since <= FRESHNESS_IDEAL_HOURS:
        return 1.0

    if hours_since >= FRESHNESS_MAX_PENALTY_HOURS:
        return 2.0

    # Linear interpolation between ideal and max penalty
    progress = (hours_since - FRESHNESS_IDEAL_HOURS) / (FRESHNESS_MAX_PENALTY_HOURS - FRESHNESS_IDEAL_HOURS)
    return 1.0 + progress


def compute_gameday_weight(
    passing_scenarios: int,
    total_scenarios: int,
) -> float:
    """
    TW-02: Gameday coverage weight based on passing scenario percentage.

    Returns:
        Weight in [1.0, 2.0] where:
        - 1.0 = 100% scenarios passing
        - 2.0 = 0% scenarios passing (or no scenarios)
    """
    if total_scenarios <= 0:
        # No gameday tests = maximum penalty (unverified)
        return 2.0

    pass_rate = passing_scenarios / total_scenarios

    if pass_rate >= GAMEDAY_IDEAL_PASS_RATE:
        return 1.0

    if pass_rate <= 0:
        return 2.0

    # Below threshold: linear penalty
    if pass_rate < GAMEDAY_PENALTY_THRESHOLD:
        # Map [0, threshold] → [2.0, 1.0 + (1.0 - threshold)]
        progress = pass_rate / GAMEDAY_PENALTY_THRESHOLD
        return 2.0 - progress * (1.0 - (1.0 - GAMEDAY_PENALTY_THRESHOLD))
    else:
        # Map [threshold, 1.0] → [1.0 + (1.0 - threshold), 1.0]
        progress = (pass_rate - GAMEDAY_PENALTY_THRESHOLD) / (GAMEDAY_IDEAL_PASS_RATE - GAMEDAY_PENALTY_THRESHOLD)
        base = 1.0 + (1.0 - GAMEDAY_PENALTY_THRESHOLD)
        return base - progress * (base - 1.0)


def compute_evidence_weight(
    bound_executions: int,
    total_executions: int,
) -> float:
    """
    TW-03: Evidence binding weight based on bound execution rate.

    Returns:
        Weight in [1.0, 2.0] where:
        - 1.0 = 100% executions bound to evidence
        - 2.0 = 0% executions bound (or no executions)
    """
    if total_executions <= 0:
        # No executions = baseline (not penalized, not trusted)
        return 1.5  # Neutral midpoint

    bind_rate = bound_executions / total_executions

    if bind_rate >= EVIDENCE_IDEAL_BIND_RATE:
        return 1.0

    if bind_rate <= 0:
        return 2.0

    # Below threshold: quadratic penalty (faster ramp-up)
    if bind_rate < EVIDENCE_PENALTY_THRESHOLD:
        progress = bind_rate / EVIDENCE_PENALTY_THRESHOLD
        return 2.0 - progress * 0.8  # [0, threshold] → [2.0, 1.2]
    else:
        # Map [threshold, 1.0] → [1.2, 1.0]
        progress = (bind_rate - EVIDENCE_PENALTY_THRESHOLD) / (EVIDENCE_IDEAL_BIND_RATE - EVIDENCE_PENALTY_THRESHOLD)
        return 1.2 - progress * 0.2


def compute_density_weight(
    event_count: int,
    window_hours: float,
) -> float:
    """
    TW-04: Observation density weight based on events per hour.

    Returns:
        Weight in [1.0, 2.0] where:
        - 1.0 = DENSITY_IDEAL_RATE or more events/hour
        - 2.0 = DENSITY_MIN_RATE or fewer events/hour
    """
    if window_hours <= 0:
        # Invalid window = cannot assess density
        return 1.5  # Neutral midpoint

    events_per_hour = event_count / window_hours

    if events_per_hour >= DENSITY_IDEAL_RATE:
        return 1.0

    if events_per_hour <= DENSITY_MIN_RATE:
        return 2.0

    # Log-scale interpolation (density perception is logarithmic)
    log_rate = math.log(events_per_hour)
    log_min = math.log(DENSITY_MIN_RATE)
    log_ideal = math.log(DENSITY_IDEAL_RATE)

    progress = (log_rate - log_min) / (log_ideal - log_min)
    return 2.0 - progress


# ============================================================================
# Composite Weight Calculator
# ============================================================================


def compute_trust_weights(
    last_event_time: Optional[datetime],
    now: datetime,
    passing_scenarios: int,
    total_scenarios: int,
    bound_executions: int,
    total_executions: int,
    event_count: int,
    window_hours: float,
) -> TrustWeights:
    """
    Compute all four trust weights and return as TrustWeights object.

    The composite trust weight is the geometric mean of all four weights,
    ensuring no single weight can dominate the final multiplier.

    Args:
        last_event_time: Timestamp of most recent event
        now: Current timestamp
        passing_scenarios: Number of gameday scenarios passing
        total_scenarios: Total number of gameday scenarios
        bound_executions: Number of executions with evidence binding
        total_executions: Total number of executions
        event_count: Number of events in observation window
        window_hours: Size of observation window in hours

    Returns:
        TrustWeights with all four weights computed
    """
    freshness = compute_freshness_weight(last_event_time, now)
    gameday = compute_gameday_weight(passing_scenarios, total_scenarios)
    evidence = compute_evidence_weight(bound_executions, total_executions)
    density = compute_density_weight(event_count, window_hours)

    return TrustWeights(
        freshness=freshness,
        gameday=gameday,
        evidence=evidence,
        density=density,
    )


# ============================================================================
# Confidence Band Adjustment
# ============================================================================


def adjust_confidence_band_for_trust(
    base_lower: float,
    base_upper: float,
    trust_weights: TrustWeights,
) -> tuple[float, float]:
    """
    Widen confidence band based on trust weight composite.

    Poor trust weights → wider confidence band (more uncertainty).

    Args:
        base_lower: Base confidence lower bound
        base_upper: Base confidence upper bound
        trust_weights: Computed trust weights

    Returns:
        Adjusted (lower, upper) tuple, clamped to [0.0, 1.0]
    """
    composite = trust_weights.composite

    # Composite > 1.0 means some data quality issues
    # Widen band proportionally
    if composite > 1.0:
        expansion = (composite - 1.0) * 0.5  # 50% of excess as expansion

        adjusted_lower = max(0.0, base_lower - expansion)
        adjusted_upper = min(1.0, base_upper + expansion)

        return (adjusted_lower, adjusted_upper)

    return (base_lower, base_upper)


# ============================================================================
# Default / Baseline Trust Weights
# ============================================================================


def get_baseline_trust_weights() -> TrustWeights:
    """
    Return baseline trust weights when no data is available.

    These represent maximum uncertainty without claiming risk.
    """
    return TrustWeights(
        freshness=2.0,  # No events = stale
        gameday=2.0,  # No tests = unverified
        evidence=1.5,  # No executions = neutral
        density=2.0,  # No events = sparse
    )
