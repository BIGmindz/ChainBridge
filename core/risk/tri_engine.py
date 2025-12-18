# core/risk/tri_engine.py
"""
TRI Engine — Trust Risk Index Computation Engine.

This is the main entry point for computing TRI scores from event data.
The engine:
- Orchestrates feature extraction
- Computes trust weights
- Aggregates domain scores
- Produces confidence bands
- Returns fully explainable TRIResult

ZERO AUTHORITY: This engine has no authority over governance decisions.
All outputs are ADVISORY ONLY.

Author: MAGGIE (GID-10) — Machine Learning & Applied AI Lead
PAC: PAC-MAGGIE-RISK-IMPL-01
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from core.risk.feature_extractors import (
    extract_gi_artifact_failures,
    extract_gi_denial_rate,
    extract_gi_forbidden_verbs,
    extract_gi_scope_violations,
    extract_gi_tool_denials,
    extract_od_diggi_corrections,
    extract_od_drcp_rate,
    extract_od_envelope_violations,
    extract_od_escalation_recoveries,
    extract_od_replay_denials,
    extract_sd_boot_failures,
    extract_sd_drift_count,
    extract_sd_fingerprint_changes,
    extract_sd_freshness_violation,
    extract_sd_manifest_deltas,
)
from core.risk.trust_weights import adjust_confidence_band_for_trust, compute_trust_weights
from core.risk.types import (
    DOMAIN_WEIGHTS,
    FEATURE_DOMAINS,
    FEATURE_WEIGHTS,
    ConfidenceBand,
    DomainScore,
    FeatureID,
    FeatureValue,
    RiskDomain,
    TRIResult,
    get_risk_tier,
)

# ============================================================================
# Configuration
# ============================================================================

MODEL_VERSION = "1.0.0"
DEFAULT_WINDOW = "24h"
DEFAULT_WINDOW_HOURS = 24.0

# Confidence band base widths (narrower = more data)
CONFIDENCE_BASE_WIDTH = 0.10  # ±5% with good data
CONFIDENCE_MAX_WIDTH = 0.40  # ±20% with poor data

# Minimum events for reliable scoring
MIN_EVENTS_FOR_NARROW_CONFIDENCE = 100
MIN_EVENTS_FOR_VALID_SCORE = 10


# ============================================================================
# Event Data Container (No Governance Imports)
# ============================================================================


@dataclass
class EventSummary:
    """
    Summarized event data for TRI computation.

    This is the interface between governance event stores and the TRI engine.
    The governance layer must populate this structure; TRI engine does not
    query governance stores directly.
    """

    # Time context
    window_start: datetime
    window_end: datetime

    # Governance Integrity events
    total_decisions: int = 0
    denied_decisions: int = 0
    last_denial: Optional[datetime] = None

    scope_violations: list[dict] = None  # [{"timestamp": datetime, ...}]
    forbidden_verb_attempts: int = 0
    last_forbidden_verb: Optional[datetime] = None

    tool_requests: int = 0
    tool_denials: int = 0
    last_tool_denial: Optional[datetime] = None

    artifact_verifications: int = 0
    artifact_failures: int = 0
    last_artifact_failure: Optional[datetime] = None

    # Operational Discipline events
    total_operations: int = 0
    drcp_triggers: int = 0
    last_drcp: Optional[datetime] = None

    diggi_corrections: int = 0
    last_diggi_correction: Optional[datetime] = None

    replay_denials: int = 0
    last_replay_denial: Optional[datetime] = None

    envelope_violations: int = 0
    last_envelope_violation: Optional[datetime] = None

    escalations: int = 0
    escalation_recoveries: int = 0
    last_escalation_recovery: Optional[datetime] = None

    # System Drift events
    drift_events: list[dict] = None  # [{"timestamp": datetime, ...}]
    fingerprint_changes: int = 0
    last_fingerprint_change: Optional[datetime] = None

    boot_attempts: int = 0
    boot_failures: int = 0
    last_boot_failure: Optional[datetime] = None

    manifest_deltas: int = 0
    last_manifest_delta: Optional[datetime] = None

    last_event_time: Optional[datetime] = None

    # Trust weight inputs
    gameday_passing: int = 0
    gameday_total: int = 0

    bound_executions: int = 0
    total_executions: int = 0

    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.scope_violations is None:
            self.scope_violations = []
        if self.drift_events is None:
            self.drift_events = []

    @property
    def total_events(self) -> int:
        """Total event count for density calculation."""
        return (
            self.total_decisions
            + len(self.scope_violations)
            + self.forbidden_verb_attempts
            + self.tool_requests
            + self.artifact_verifications
            + self.total_operations
            + self.diggi_corrections
            + self.replay_denials
            + self.envelope_violations
            + self.escalations
            + len(self.drift_events)
            + self.fingerprint_changes
            + self.boot_attempts
            + self.manifest_deltas
        )

    @property
    def window_hours(self) -> float:
        """Window size in hours."""
        delta = self.window_end - self.window_start
        return delta.total_seconds() / 3600.0


# ============================================================================
# TRI Engine
# ============================================================================


class TRIEngine:
    """
    Trust Risk Index computation engine.

    ADVISORY ONLY: This engine has no authority over governance.
    All outputs are for information purposes only.
    """

    def __init__(self, model_version: str = MODEL_VERSION) -> None:
        """Initialize TRI engine."""
        self.model_version = model_version

    def compute(
        self,
        events: EventSummary,
        now: Optional[datetime] = None,
    ) -> TRIResult:
        """
        Compute Trust Risk Index from event summary.

        Args:
            events: Summarized event data
            now: Current timestamp (defaults to window_end)

        Returns:
            TRIResult with full score decomposition
        """
        if now is None:
            now = events.window_end

        window = f"{int(events.window_hours)}h"

        # Step 1: Extract all features
        features = self._extract_all_features(events, now, window)

        # Step 2: Compute domain scores
        domain_scores = self._compute_domain_scores(features)

        # Step 3: Compute trust weights
        trust_weights = compute_trust_weights(
            last_event_time=events.last_event_time,
            now=now,
            passing_scenarios=events.gameday_passing,
            total_scenarios=events.gameday_total,
            bound_executions=events.bound_executions,
            total_executions=events.total_executions,
            event_count=events.total_events,
            window_hours=events.window_hours,
        )

        # Step 4: Compute raw TRI score
        raw_score = self._compute_raw_score(domain_scores)

        # Step 5: Apply sigmoid normalization
        normalized_score = self._sigmoid(raw_score)

        # Step 6: Apply trust weight multiplier
        # Trust weights > 1.0 increase the score (more risk)
        # But we cap at 1.0 since TRI is bounded
        final_tri = min(1.0, normalized_score * trust_weights.composite)

        # Step 7: Compute confidence band
        confidence = self._compute_confidence_band(events.total_events, trust_weights, final_tri)

        # Step 8: Determine risk tier
        tier = get_risk_tier(final_tri)

        # Step 9: Collect null features
        null_features = [fv.feature_id.value for fv in features if fv.value is None]

        # Step 10: Build result
        return TRIResult(
            tri=final_tri,
            confidence=confidence,
            tier=tier,
            domains={ds.domain.value: ds for ds in domain_scores},
            trust_weights=trust_weights,
            computed_at=now,
            window=window,
            event_count=events.total_events,
            feature_count=len(features) - len(null_features),
            null_features=null_features,
            advisory_only=True,  # MANDATORY
            model_version=self.model_version,
        )

    def _extract_all_features(
        self,
        events: EventSummary,
        now: datetime,
        window: str,
    ) -> list[FeatureValue]:
        """Extract all 15 features from event summary."""
        features = []

        # Governance Integrity (GI-01 to GI-05)
        features.append(
            extract_gi_denial_rate(
                events.denied_decisions,
                events.total_decisions,
                window,
                events.last_denial,
            )
        )
        features.append(
            extract_gi_scope_violations(
                events.scope_violations,
                window,
                now,
            )
        )
        features.append(
            extract_gi_forbidden_verbs(
                events.forbidden_verb_attempts,
                window,
                events.last_forbidden_verb,
            )
        )
        features.append(
            extract_gi_tool_denials(
                events.tool_denials,
                events.tool_requests,
                window,
                events.last_tool_denial,
            )
        )
        features.append(
            extract_gi_artifact_failures(
                events.artifact_failures,
                events.artifact_verifications,
                window,
                events.last_artifact_failure,
            )
        )

        # Operational Discipline (OD-01 to OD-05)
        features.append(
            extract_od_drcp_rate(
                events.drcp_triggers,
                events.total_operations,
                window,
                events.last_drcp,
            )
        )
        features.append(
            extract_od_diggi_corrections(
                events.diggi_corrections,
                window,
                events.last_diggi_correction,
            )
        )
        features.append(
            extract_od_replay_denials(
                events.replay_denials,
                window,
                events.last_replay_denial,
            )
        )
        features.append(
            extract_od_envelope_violations(
                events.envelope_violations,
                window,
                events.last_envelope_violation,
            )
        )
        features.append(
            extract_od_escalation_recoveries(
                events.escalation_recoveries,
                events.escalations,
                window,
                events.last_escalation_recovery,
            )
        )

        # System Drift (SD-01 to SD-05)
        features.append(
            extract_sd_drift_count(
                events.drift_events,
                window,
                now,
            )
        )
        features.append(
            extract_sd_fingerprint_changes(
                events.fingerprint_changes,
                window,
                events.last_fingerprint_change,
            )
        )
        features.append(
            extract_sd_boot_failures(
                events.boot_failures,
                events.boot_attempts,
                window,
                events.last_boot_failure,
            )
        )
        features.append(
            extract_sd_manifest_deltas(
                events.manifest_deltas,
                window,
                events.last_manifest_delta,
            )
        )
        features.append(
            extract_sd_freshness_violation(
                events.last_event_time,
                now,
            )
        )

        return features

    def _compute_domain_scores(
        self,
        features: list[FeatureValue],
    ) -> list[DomainScore]:
        """Aggregate features into domain scores."""
        # Group features by domain
        domain_features: dict[RiskDomain, list[FeatureValue]] = {domain: [] for domain in RiskDomain}

        for fv in features:
            domain = FEATURE_DOMAINS[fv.feature_id]
            domain_features[domain].append(fv)

        # Compute score for each domain
        domain_scores = []

        for domain, domain_fvs in domain_features.items():
            score, null_count = self._aggregate_domain_features(domain_fvs)
            domain_scores.append(
                DomainScore(
                    domain=domain,
                    score=score,
                    weight=DOMAIN_WEIGHTS[domain],
                    features=tuple(domain_fvs),
                    null_count=null_count,
                )
            )

        return domain_scores

    def _aggregate_domain_features(
        self,
        features: list[FeatureValue],
    ) -> tuple[float, int]:
        """
        Aggregate features within a domain.

        Returns (score, null_count) where score is weighted average
        of non-null features.
        """
        weighted_sum = 0.0
        weight_sum = 0.0
        null_count = 0

        for fv in features:
            weight = FEATURE_WEIGHTS.get(fv.feature_id, 0.0)

            if fv.value is not None:
                weighted_sum += fv.value * weight
                weight_sum += weight
            else:
                null_count += 1

        if weight_sum > 0:
            score = weighted_sum / weight_sum
        else:
            # All features null = return neutral baseline
            score = 0.5

        return (score, null_count)

    def _compute_raw_score(
        self,
        domain_scores: list[DomainScore],
    ) -> float:
        """
        Compute raw TRI score from domain scores.

        Raw score = Σ (domain_weight × domain_score)
        """
        raw = 0.0
        for ds in domain_scores:
            raw += ds.weighted_contribution
        return raw

    def _sigmoid(self, x: float, steepness: float = 4.0) -> float:
        """
        Sigmoid normalization.

        Maps raw score to [0.0, 1.0] with smooth transitions.
        Steepness controls how sharp the transition is around 0.5.
        """
        # Shift and scale so that raw=0.5 → sigmoid=0.5
        shifted = (x - 0.5) * steepness
        return 1.0 / (1.0 + math.exp(-shifted))

    def _compute_confidence_band(
        self,
        event_count: int,
        trust_weights,
        tri: float,
    ) -> ConfidenceBand:
        """
        Compute confidence band based on data quality.

        More events + better trust weights → narrower band.
        """
        # Base width depends on event count
        if event_count >= MIN_EVENTS_FOR_NARROW_CONFIDENCE:
            base_width = CONFIDENCE_BASE_WIDTH
        elif event_count >= MIN_EVENTS_FOR_VALID_SCORE:
            # Linear interpolation
            progress = (event_count - MIN_EVENTS_FOR_VALID_SCORE) / (MIN_EVENTS_FOR_NARROW_CONFIDENCE - MIN_EVENTS_FOR_VALID_SCORE)
            base_width = CONFIDENCE_MAX_WIDTH - progress * (CONFIDENCE_MAX_WIDTH - CONFIDENCE_BASE_WIDTH)
        else:
            base_width = CONFIDENCE_MAX_WIDTH

        # Initial band
        half_width = base_width / 2
        lower = max(0.0, tri - half_width)
        upper = min(1.0, tri + half_width)

        # Adjust for trust weights
        lower, upper = adjust_confidence_band_for_trust(lower, upper, trust_weights)

        return ConfidenceBand(lower=lower, upper=upper)


# ============================================================================
# Factory / Demo Functions
# ============================================================================


def create_empty_event_summary(
    window_hours: float = DEFAULT_WINDOW_HOURS,
    now: Optional[datetime] = None,
) -> EventSummary:
    """
    Create an empty event summary for testing or baseline.

    Returns EventSummary with all zeros, representing "no data".
    """
    if now is None:
        now = datetime.utcnow()

    window_start = now - timedelta(hours=window_hours)

    return EventSummary(
        window_start=window_start,
        window_end=now,
    )


def demo_tri_computation() -> dict:
    """
    Demonstrate TRI computation with sample data.

    Returns dict representation of TRIResult.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(hours=24)

    # Create sample event data
    events = EventSummary(
        window_start=window_start,
        window_end=now,
        # Some denials
        total_decisions=100,
        denied_decisions=5,
        last_denial=now - timedelta(hours=2),
        # A few scope violations
        scope_violations=[
            {"timestamp": now - timedelta(hours=4)},
            {"timestamp": now - timedelta(hours=12)},
        ],
        # One forbidden verb attempt
        forbidden_verb_attempts=1,
        last_forbidden_verb=now - timedelta(hours=6),
        # Tool requests
        tool_requests=50,
        tool_denials=2,
        last_tool_denial=now - timedelta(hours=3),
        # Artifact verifications
        artifact_verifications=20,
        artifact_failures=0,
        # Operations
        total_operations=200,
        drcp_triggers=3,
        last_drcp=now - timedelta(hours=5),
        # DIGGI corrections
        diggi_corrections=2,
        last_diggi_correction=now - timedelta(hours=8),
        # No replay denials (good)
        replay_denials=0,
        # Some envelope violations
        envelope_violations=1,
        last_envelope_violation=now - timedelta(hours=10),
        # Escalations
        escalations=5,
        escalation_recoveries=4,
        last_escalation_recovery=now - timedelta(hours=1),
        # No drift events
        drift_events=[],
        # No fingerprint changes
        fingerprint_changes=0,
        # Boot checks
        boot_attempts=3,
        boot_failures=0,
        # Manifest deltas
        manifest_deltas=1,
        last_manifest_delta=now - timedelta(hours=20),
        # Recent event
        last_event_time=now - timedelta(minutes=30),
        # Good gameday coverage
        gameday_passing=130,
        gameday_total=133,
        # Good evidence binding
        bound_executions=180,
        total_executions=200,
    )

    # Compute TRI
    engine = TRIEngine()
    result = engine.compute(events, now)

    return result.to_dict()


# ============================================================================
# CLI Entry Point
# ============================================================================


if __name__ == "__main__":
    import json
    import sys

    if "--demo" in sys.argv:
        result = demo_tri_computation()
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python -m core.risk.tri_engine --demo")
        print("\nTrust Risk Index (TRI) Engine")
        print("  Version:", MODEL_VERSION)
        print("  Features:", len(FeatureID))
        print("  Domains:", len(RiskDomain))
        print("\nRun with --demo to see sample output.")
