# core/risk/feature_extractors.py
"""
TRI Feature Extractors — Pure functions for all 15 risk features.

Each extractor:
- Takes structured event data (no raw governance imports)
- Returns FeatureValue with bounded [0.0, 1.0] output
- Is deterministic (same inputs → same output)
- Has no side effects (read-only)

IMPORTANT: This module does NOT import governance modules.
Event data must be passed in as structured dictionaries.

Author: MAGGIE (GID-10) — Machine Learning & Applied AI Lead
PAC: PAC-MAGGIE-RISK-IMPL-01
"""

import math
from datetime import datetime
from typing import Optional, Protocol

from core.risk.types import FeatureID, FeatureValue

# ============================================================================
# Event Data Protocol (no governance imports)
# ============================================================================


class EventData(Protocol):
    """
    Protocol for event data passed to extractors.
    This allows us to accept any dict-like object without importing governance.
    """

    def get(self, key: str, default: object = None) -> object: ...


# ============================================================================
# Configuration Constants
# ============================================================================

# Time windows for feature computation
WINDOW_24H = "24h"
WINDOW_7D = "7d"
WINDOW_30D = "30d"

# Decay half-lives (in hours)
DECAY_SCOPE_VIOLATION_HALFLIFE = 168.0  # 7 days
DECAY_DRIFT_HALFLIFE = 72.0  # 3 days
DECAY_DEFAULT_HALFLIFE = 168.0  # 7 days

# Saturation thresholds (counts beyond this → max risk)
SATURATION_SCOPE_VIOLATIONS = 10
SATURATION_FORBIDDEN_VERBS = 5
SATURATION_TOOL_DENIALS = 20
SATURATION_ARTIFACT_FAILURES = 10
SATURATION_DRCP_EVENTS = 15
SATURATION_DIGGI_CORRECTIONS = 10
SATURATION_REPLAY_DENIALS = 5
SATURATION_ENVELOPE_VIOLATIONS = 10
SATURATION_DRIFT_COUNT = 5
SATURATION_FINGERPRINT_CHANGES = 3
SATURATION_BOOT_FAILURES = 3
SATURATION_MANIFEST_DELTAS = 5

# Freshness violation threshold (hours)
FRESHNESS_THRESHOLD_HOURS = 24.0


# ============================================================================
# Helper Functions
# ============================================================================


def exponential_decay(hours_ago: float, half_life: float) -> float:
    """
    Compute exponential decay weight.

    Returns value in [0.0, 1.0] where:
    - 1.0 = just happened
    - 0.5 = one half-life ago
    - approaches 0.0 = very old
    """
    if hours_ago <= 0:
        return 1.0
    return math.pow(0.5, hours_ago / half_life)


def saturating_score(count: int, saturation: int) -> float:
    """
    Convert count to [0.0, 1.0] score with soft saturation.

    Uses tanh-like curve:
    - count=0 → 0.0
    - count=saturation → ~0.76
    - count=2*saturation → ~0.96
    """
    if count <= 0:
        return 0.0
    # Soft saturation using 1 - exp(-x/s)
    return 1.0 - math.exp(-count / saturation)


def rate_to_score(numerator: int, denominator: int) -> Optional[float]:
    """
    Convert rate (num/denom) to score.

    Returns None if denominator is 0 (undefined rate).
    """
    if denominator <= 0:
        return None
    return min(1.0, numerator / denominator)


def hours_since(timestamp: Optional[datetime], now: datetime) -> float:
    """Calculate hours since a timestamp."""
    if timestamp is None:
        return float("inf")
    delta = now - timestamp
    return delta.total_seconds() / 3600.0


# ============================================================================
# Governance Integrity Extractors (GI-01 to GI-05)
# ============================================================================


def extract_gi_denial_rate(
    denied_count: int,
    total_decisions: int,
    window: str,
    last_denial: Optional[datetime],
) -> FeatureValue:
    """
    GI-01: Decision denial rate.

    Higher denial rate → higher risk signal.
    """
    value = rate_to_score(denied_count, total_decisions)

    return FeatureValue(
        feature_id=FeatureID.GI_DENIAL_RATE,
        value=value,
        window=window,
        sample_count=total_decisions,
        last_seen=last_denial,
        raw_numerator=denied_count,
        raw_denominator=total_decisions,
    )


def extract_gi_scope_violations(
    violations: list[dict],
    window: str,
    now: datetime,
) -> FeatureValue:
    """
    GI-02: Scope violation count with time decay.

    Recent violations weighted more heavily than old ones.
    """
    if not violations:
        return FeatureValue(
            feature_id=FeatureID.GI_SCOPE_VIOLATIONS,
            value=0.0,
            window=window,
            sample_count=0,
            last_seen=None,
        )

    # Apply exponential decay to each violation
    weighted_sum = 0.0
    last_seen = None

    for v in violations:
        ts = v.get("timestamp")
        if isinstance(ts, datetime):
            hours_ago = hours_since(ts, now)
            weight = exponential_decay(hours_ago, DECAY_SCOPE_VIOLATION_HALFLIFE)
            weighted_sum += weight
            if last_seen is None or ts > last_seen:
                last_seen = ts

    # Saturate to [0.0, 1.0]
    value = saturating_score(int(weighted_sum), SATURATION_SCOPE_VIOLATIONS)

    return FeatureValue(
        feature_id=FeatureID.GI_SCOPE_VIOLATIONS,
        value=value,
        window=window,
        sample_count=len(violations),
        last_seen=last_seen,
    )


def extract_gi_forbidden_verbs(
    forbidden_attempts: int,
    window: str,
    last_attempt: Optional[datetime],
) -> FeatureValue:
    """
    GI-03: DIGGI forbidden verb attempts.

    Any attempt to use forbidden verbs is a strong risk signal.
    """
    value = saturating_score(forbidden_attempts, SATURATION_FORBIDDEN_VERBS)

    return FeatureValue(
        feature_id=FeatureID.GI_FORBIDDEN_VERBS,
        value=value,
        window=window,
        sample_count=forbidden_attempts,
        last_seen=last_attempt,
    )


def extract_gi_tool_denials(
    tool_denials: int,
    total_tool_requests: int,
    window: str,
    last_denial: Optional[datetime],
) -> FeatureValue:
    """
    GI-04: Tool execution denials.

    Rate-based when we have enough data, count-based otherwise.
    """
    if total_tool_requests >= 10:
        # Enough data for rate calculation
        value = rate_to_score(tool_denials, total_tool_requests)
    else:
        # Fall back to count-based saturation
        value = saturating_score(tool_denials, SATURATION_TOOL_DENIALS)

    return FeatureValue(
        feature_id=FeatureID.GI_TOOL_DENIALS,
        value=value,
        window=window,
        sample_count=total_tool_requests,
        last_seen=last_denial,
        raw_numerator=tool_denials,
        raw_denominator=total_tool_requests,
    )


def extract_gi_artifact_failures(
    failures: int,
    total_verifications: int,
    window: str,
    last_failure: Optional[datetime],
) -> FeatureValue:
    """
    GI-05: Artifact verification failures.

    Failed verifications indicate potential integrity issues.
    """
    if total_verifications >= 5:
        value = rate_to_score(failures, total_verifications)
    else:
        value = saturating_score(failures, SATURATION_ARTIFACT_FAILURES)

    return FeatureValue(
        feature_id=FeatureID.GI_ARTIFACT_FAILURES,
        value=value,
        window=window,
        sample_count=total_verifications,
        last_seen=last_failure,
        raw_numerator=failures,
        raw_denominator=total_verifications,
    )


# ============================================================================
# Operational Discipline Extractors (OD-01 to OD-05)
# ============================================================================


def extract_od_drcp_rate(
    drcp_triggers: int,
    total_operations: int,
    window: str,
    last_trigger: Optional[datetime],
) -> FeatureValue:
    """
    OD-01: DRCP (Deny-Retry-Cancel Protocol) trigger rate.

    Frequent DRCP triggers indicate retry-after-deny behavior.
    """
    if total_operations >= 20:
        value = rate_to_score(drcp_triggers, total_operations)
    else:
        value = saturating_score(drcp_triggers, SATURATION_DRCP_EVENTS)

    return FeatureValue(
        feature_id=FeatureID.OD_DRCP_RATE,
        value=value,
        window=window,
        sample_count=total_operations,
        last_seen=last_trigger,
        raw_numerator=drcp_triggers,
        raw_denominator=total_operations,
    )


def extract_od_diggi_corrections(
    corrections: int,
    window: str,
    last_correction: Optional[datetime],
) -> FeatureValue:
    """
    OD-02: DIGGI correction count.

    Corrections indicate agents were nudged back to compliance.
    """
    value = saturating_score(corrections, SATURATION_DIGGI_CORRECTIONS)

    return FeatureValue(
        feature_id=FeatureID.OD_DIGGI_CORRECTIONS,
        value=value,
        window=window,
        sample_count=corrections,
        last_seen=last_correction,
    )


def extract_od_replay_denials(
    replay_denials: int,
    window: str,
    last_denial: Optional[datetime],
) -> FeatureValue:
    """
    OD-03: Replay attack denials (from persistent denial registry).

    Any replay denial is a serious operational concern.
    """
    # Replay denials are binary serious - low saturation threshold
    value = saturating_score(replay_denials, SATURATION_REPLAY_DENIALS)

    return FeatureValue(
        feature_id=FeatureID.OD_REPLAY_DENIALS,
        value=value,
        window=window,
        sample_count=replay_denials,
        last_seen=last_denial,
    )


def extract_od_envelope_violations(
    violations: int,
    window: str,
    last_violation: Optional[datetime],
) -> FeatureValue:
    """
    OD-04: Envelope / boundary violations.

    Operations outside permitted boundaries.
    """
    value = saturating_score(violations, SATURATION_ENVELOPE_VIOLATIONS)

    return FeatureValue(
        feature_id=FeatureID.OD_ENVELOPE_VIOLATIONS,
        value=value,
        window=window,
        sample_count=violations,
        last_seen=last_violation,
    )


def extract_od_escalation_recoveries(
    recoveries: int,
    escalations: int,
    window: str,
    last_recovery: Optional[datetime],
) -> FeatureValue:
    """
    OD-05: Escalation recovery rate.

    This is an INVERSE signal: high recovery rate = LOWER risk.
    We invert it so higher value = higher risk (monotonic).
    """
    if escalations <= 0:
        # No escalations = no data, return null
        return FeatureValue(
            feature_id=FeatureID.OD_ESCALATION_RECOVERIES,
            value=None,
            window=window,
            sample_count=0,
            last_seen=None,
        )

    # Recovery rate (higher = better)
    recovery_rate = min(1.0, recoveries / escalations)
    # Invert: high recovery = low risk
    value = 1.0 - recovery_rate

    return FeatureValue(
        feature_id=FeatureID.OD_ESCALATION_RECOVERIES,
        value=value,
        window=window,
        sample_count=escalations,
        last_seen=last_recovery,
        raw_numerator=recoveries,
        raw_denominator=escalations,
    )


# ============================================================================
# System Drift Extractors (SD-01 to SD-05)
# ============================================================================


def extract_sd_drift_count(
    drift_events: list[dict],
    window: str,
    now: datetime,
) -> FeatureValue:
    """
    SD-01: Governance drift event count with time decay.

    Recent drift weighted more heavily.
    """
    if not drift_events:
        return FeatureValue(
            feature_id=FeatureID.SD_DRIFT_COUNT,
            value=0.0,
            window=window,
            sample_count=0,
            last_seen=None,
        )

    weighted_sum = 0.0
    last_seen = None

    for event in drift_events:
        ts = event.get("timestamp")
        if isinstance(ts, datetime):
            hours_ago = hours_since(ts, now)
            weight = exponential_decay(hours_ago, DECAY_DRIFT_HALFLIFE)
            weighted_sum += weight
            if last_seen is None or ts > last_seen:
                last_seen = ts

    value = saturating_score(int(weighted_sum), SATURATION_DRIFT_COUNT)

    return FeatureValue(
        feature_id=FeatureID.SD_DRIFT_COUNT,
        value=value,
        window=window,
        sample_count=len(drift_events),
        last_seen=last_seen,
    )


def extract_sd_fingerprint_changes(
    changes: int,
    window: str,
    last_change: Optional[datetime],
) -> FeatureValue:
    """
    SD-02: Governance fingerprint changes.

    Unexpected fingerprint changes indicate potential tampering.
    """
    value = saturating_score(changes, SATURATION_FINGERPRINT_CHANGES)

    return FeatureValue(
        feature_id=FeatureID.SD_FINGERPRINT_CHANGES,
        value=value,
        window=window,
        sample_count=changes,
        last_seen=last_change,
    )


def extract_sd_boot_failures(
    failures: int,
    total_boots: int,
    window: str,
    last_failure: Optional[datetime],
) -> FeatureValue:
    """
    SD-03: Boot integrity check failures.

    Failed boot checks indicate governance initialization issues.
    """
    if total_boots >= 3:
        value = rate_to_score(failures, total_boots)
    else:
        value = saturating_score(failures, SATURATION_BOOT_FAILURES)

    return FeatureValue(
        feature_id=FeatureID.SD_BOOT_FAILURES,
        value=value,
        window=window,
        sample_count=total_boots,
        last_seen=last_failure,
        raw_numerator=failures,
        raw_denominator=total_boots,
    )


def extract_sd_manifest_deltas(
    deltas: int,
    window: str,
    last_delta: Optional[datetime],
) -> FeatureValue:
    """
    SD-04: Manifest/configuration changes.

    Frequent manifest changes may indicate instability or tampering.
    """
    value = saturating_score(deltas, SATURATION_MANIFEST_DELTAS)

    return FeatureValue(
        feature_id=FeatureID.SD_MANIFEST_DELTAS,
        value=value,
        window=window,
        sample_count=deltas,
        last_seen=last_delta,
    )


def extract_sd_freshness_violation(
    last_event_time: Optional[datetime],
    now: datetime,
    threshold_hours: float = FRESHNESS_THRESHOLD_HOURS,
) -> FeatureValue:
    """
    SD-05: Data freshness violation.

    Returns risk signal if no events within threshold window.
    This is a meta-feature: silence itself is suspicious.
    """
    if last_event_time is None:
        # No events at all = maximum freshness violation
        return FeatureValue(
            feature_id=FeatureID.SD_FRESHNESS_VIOLATION,
            value=1.0,
            window=f"{threshold_hours}h",
            sample_count=0,
            last_seen=None,
        )

    hours_ago = hours_since(last_event_time, now)

    if hours_ago <= threshold_hours:
        # Fresh data = no violation
        value = 0.0
    else:
        # Violation severity increases with staleness
        # Saturates at 2x threshold
        excess_hours = hours_ago - threshold_hours
        value = min(1.0, excess_hours / threshold_hours)

    return FeatureValue(
        feature_id=FeatureID.SD_FRESHNESS_VIOLATION,
        value=value,
        window=f"{threshold_hours}h",
        sample_count=1 if last_event_time else 0,
        last_seen=last_event_time,
    )


# ============================================================================
# Extractor Registry
# ============================================================================

# Map feature IDs to their extractor functions (for documentation/introspection)
EXTRACTOR_REGISTRY: dict[FeatureID, str] = {
    FeatureID.GI_DENIAL_RATE: "extract_gi_denial_rate",
    FeatureID.GI_SCOPE_VIOLATIONS: "extract_gi_scope_violations",
    FeatureID.GI_FORBIDDEN_VERBS: "extract_gi_forbidden_verbs",
    FeatureID.GI_TOOL_DENIALS: "extract_gi_tool_denials",
    FeatureID.GI_ARTIFACT_FAILURES: "extract_gi_artifact_failures",
    FeatureID.OD_DRCP_RATE: "extract_od_drcp_rate",
    FeatureID.OD_DIGGI_CORRECTIONS: "extract_od_diggi_corrections",
    FeatureID.OD_REPLAY_DENIALS: "extract_od_replay_denials",
    FeatureID.OD_ENVELOPE_VIOLATIONS: "extract_od_envelope_violations",
    FeatureID.OD_ESCALATION_RECOVERIES: "extract_od_escalation_recoveries",
    FeatureID.SD_DRIFT_COUNT: "extract_sd_drift_count",
    FeatureID.SD_FINGERPRINT_CHANGES: "extract_sd_fingerprint_changes",
    FeatureID.SD_BOOT_FAILURES: "extract_sd_boot_failures",
    FeatureID.SD_MANIFEST_DELTAS: "extract_sd_manifest_deltas",
    FeatureID.SD_FRESHNESS_VIOLATION: "extract_sd_freshness_violation",
}
