# core/risk/types.py
"""
TRI Type Definitions — Data structures for Trust Risk Index computation.

All types are immutable dataclasses with explicit fields.
No governance imports. No authority. Advisory only.

Author: MAGGIE (GID-10) — Machine Learning & Applied AI Lead
PAC: PAC-MAGGIE-RISK-IMPL-01
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RiskDomain(Enum):
    """Three risk domains for TRI computation."""

    GOVERNANCE_INTEGRITY = "governance_integrity"
    OPERATIONAL_DISCIPLINE = "operational_discipline"
    SYSTEM_DRIFT = "system_drift"


class FeatureID(Enum):
    """All 15 TRI features by domain."""

    # Governance Integrity (GI-01 to GI-05)
    GI_DENIAL_RATE = "gi_denial_rate"
    GI_SCOPE_VIOLATIONS = "gi_scope_violations"
    GI_FORBIDDEN_VERBS = "gi_forbidden_verbs"
    GI_TOOL_DENIALS = "gi_tool_denials"
    GI_ARTIFACT_FAILURES = "gi_artifact_failures"

    # Operational Discipline (OD-01 to OD-05)
    OD_DRCP_RATE = "od_drcp_rate"
    OD_DIGGI_CORRECTIONS = "od_diggi_corrections"
    OD_REPLAY_DENIALS = "od_replay_denials"
    OD_ENVELOPE_VIOLATIONS = "od_envelope_violations"
    OD_ESCALATION_RECOVERIES = "od_escalation_recoveries"

    # System Drift (SD-01 to SD-05)
    SD_DRIFT_COUNT = "sd_drift_count"
    SD_FINGERPRINT_CHANGES = "sd_fingerprint_changes"
    SD_BOOT_FAILURES = "sd_boot_failures"
    SD_MANIFEST_DELTAS = "sd_manifest_deltas"
    SD_FRESHNESS_VIOLATION = "sd_freshness_violation"


# Domain membership mapping
FEATURE_DOMAINS: dict[FeatureID, RiskDomain] = {
    # Governance Integrity
    FeatureID.GI_DENIAL_RATE: RiskDomain.GOVERNANCE_INTEGRITY,
    FeatureID.GI_SCOPE_VIOLATIONS: RiskDomain.GOVERNANCE_INTEGRITY,
    FeatureID.GI_FORBIDDEN_VERBS: RiskDomain.GOVERNANCE_INTEGRITY,
    FeatureID.GI_TOOL_DENIALS: RiskDomain.GOVERNANCE_INTEGRITY,
    FeatureID.GI_ARTIFACT_FAILURES: RiskDomain.GOVERNANCE_INTEGRITY,
    # Operational Discipline
    FeatureID.OD_DRCP_RATE: RiskDomain.OPERATIONAL_DISCIPLINE,
    FeatureID.OD_DIGGI_CORRECTIONS: RiskDomain.OPERATIONAL_DISCIPLINE,
    FeatureID.OD_REPLAY_DENIALS: RiskDomain.OPERATIONAL_DISCIPLINE,
    FeatureID.OD_ENVELOPE_VIOLATIONS: RiskDomain.OPERATIONAL_DISCIPLINE,
    FeatureID.OD_ESCALATION_RECOVERIES: RiskDomain.OPERATIONAL_DISCIPLINE,
    # System Drift
    FeatureID.SD_DRIFT_COUNT: RiskDomain.SYSTEM_DRIFT,
    FeatureID.SD_FINGERPRINT_CHANGES: RiskDomain.SYSTEM_DRIFT,
    FeatureID.SD_BOOT_FAILURES: RiskDomain.SYSTEM_DRIFT,
    FeatureID.SD_MANIFEST_DELTAS: RiskDomain.SYSTEM_DRIFT,
    FeatureID.SD_FRESHNESS_VIOLATION: RiskDomain.SYSTEM_DRIFT,
}

# Domain weights (sum to 1.0)
DOMAIN_WEIGHTS: dict[RiskDomain, float] = {
    RiskDomain.GOVERNANCE_INTEGRITY: 0.40,
    RiskDomain.OPERATIONAL_DISCIPLINE: 0.35,
    RiskDomain.SYSTEM_DRIFT: 0.25,
}

# Feature weights within each domain (relative, normalized internally)
FEATURE_WEIGHTS: dict[FeatureID, float] = {
    # GI features
    FeatureID.GI_DENIAL_RATE: 0.30,
    FeatureID.GI_SCOPE_VIOLATIONS: 0.25,
    FeatureID.GI_FORBIDDEN_VERBS: 0.20,
    FeatureID.GI_TOOL_DENIALS: 0.15,
    FeatureID.GI_ARTIFACT_FAILURES: 0.10,
    # OD features
    FeatureID.OD_DRCP_RATE: 0.30,
    FeatureID.OD_DIGGI_CORRECTIONS: 0.25,
    FeatureID.OD_REPLAY_DENIALS: 0.20,
    FeatureID.OD_ENVELOPE_VIOLATIONS: 0.15,
    FeatureID.OD_ESCALATION_RECOVERIES: 0.10,
    # SD features
    FeatureID.SD_DRIFT_COUNT: 0.30,
    FeatureID.SD_FINGERPRINT_CHANGES: 0.25,
    FeatureID.SD_BOOT_FAILURES: 0.20,
    FeatureID.SD_MANIFEST_DELTAS: 0.15,
    FeatureID.SD_FRESHNESS_VIOLATION: 0.10,
}


@dataclass(frozen=True)
class FeatureValue:
    """
    A single extracted feature value with metadata.

    All feature values are bounded [0.0, 1.0] where:
    - 0.0 = no risk signal observed
    - 1.0 = maximum risk signal

    Higher values always indicate higher risk (monotonic).
    """

    feature_id: FeatureID
    value: Optional[float]  # None if feature cannot be computed
    window: str  # e.g., "24h", "7d", "30d"
    sample_count: int  # Number of events in window
    last_seen: Optional[datetime]  # Most recent event timestamp
    raw_numerator: Optional[int] = None  # For rate calculations
    raw_denominator: Optional[int] = None  # For rate calculations

    def __post_init__(self) -> None:
        """Validate feature value bounds."""
        if self.value is not None:
            if not (0.0 <= self.value <= 1.0):
                raise ValueError(f"Feature value must be in [0.0, 1.0], got {self.value}")


@dataclass(frozen=True)
class ConfidenceBand:
    """
    Confidence interval for TRI score.

    Width depends on data quality:
    - High event volume + fresh data → narrow band
    - Low event volume + stale data → wide band
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        """Validate bounds."""
        if not (0.0 <= self.lower <= self.upper <= 1.0):
            raise ValueError(f"Invalid confidence band: [{self.lower}, {self.upper}]")

    @property
    def width(self) -> float:
        """Band width (uncertainty measure)."""
        return self.upper - self.lower


@dataclass(frozen=True)
class TrustWeights:
    """
    Four trust weight multipliers that penalize unreliable data.

    Each weight is in [1.0, 2.0]:
    - 1.0 = fully trusted (no penalty)
    - 2.0 = maximum penalty (doubles risk contribution)
    """

    freshness: float  # TW-01: Time since last event
    gameday: float  # TW-02: % of scenarios passing
    evidence: float  # TW-03: Bound execution rate
    density: float  # TW-04: Events per hour

    def __post_init__(self) -> None:
        """Validate weight bounds."""
        for name, val in [
            ("freshness", self.freshness),
            ("gameday", self.gameday),
            ("evidence", self.evidence),
            ("density", self.density),
        ]:
            if not (1.0 <= val <= 2.0):
                raise ValueError(f"Trust weight {name} must be in [1.0, 2.0], got {val}")

    @property
    def composite(self) -> float:
        """Geometric mean of all weights."""
        product = self.freshness * self.gameday * self.evidence * self.density
        return product**0.25  # 4th root


@dataclass(frozen=True)
class DomainScore:
    """
    Aggregated score for a single risk domain.
    """

    domain: RiskDomain
    score: float  # [0.0, 1.0] domain-level score
    weight: float  # Domain weight in final TRI
    features: tuple[FeatureValue, ...]  # Contributing features
    null_count: int  # Number of features that couldn't be computed

    @property
    def weighted_contribution(self) -> float:
        """This domain's contribution to raw TRI."""
        return self.score * self.weight


@dataclass(frozen=True)
class ContributionRow:
    """
    Human-readable contribution for audit/explanation tables.
    """

    feature_name: str
    feature_id: str
    domain: str
    value: Optional[float]
    weight: float
    contribution: Optional[float]
    evidence: str  # Human-readable evidence description


@dataclass(frozen=True)
class TRIResult:
    """
    Complete Trust Risk Index computation result.

    ADVISORY ONLY — This score has no authority over governance.
    """

    # Core score
    tri: float  # Final TRI in [0.0, 1.0]
    confidence: ConfidenceBand
    tier: str  # MINIMAL, LOW, MODERATE, HIGH, CRITICAL

    # Decomposition
    domains: dict[str, DomainScore]
    trust_weights: TrustWeights

    # Metadata
    computed_at: datetime
    window: str  # Primary time window
    event_count: int  # Total events considered
    feature_count: int  # Features successfully computed
    null_features: list[str]  # Features that returned null

    # MANDATORY: Advisory flag
    advisory_only: bool = field(default=True)

    # Version for reproducibility
    model_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Enforce advisory_only is always True."""
        if not self.advisory_only:
            raise ValueError("TRIResult.advisory_only must always be True")

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "tri": round(self.tri, 4),
            "confidence": {
                "lower": round(self.confidence.lower, 4),
                "upper": round(self.confidence.upper, 4),
            },
            "tier": self.tier,
            "domains": {
                name: {
                    "score": round(ds.score, 4),
                    "weight": ds.weight,
                    "weighted_contribution": round(ds.weighted_contribution, 4),
                    "null_count": ds.null_count,
                }
                for name, ds in self.domains.items()
            },
            "trust_weights": {
                "freshness": round(self.trust_weights.freshness, 4),
                "gameday": round(self.trust_weights.gameday, 4),
                "evidence": round(self.trust_weights.evidence, 4),
                "density": round(self.trust_weights.density, 4),
                "composite": round(self.trust_weights.composite, 4),
            },
            "metadata": {
                "computed_at": self.computed_at.isoformat(),
                "window": self.window,
                "event_count": self.event_count,
                "feature_count": self.feature_count,
                "null_features": self.null_features,
                "model_version": self.model_version,
            },
            "advisory_only": self.advisory_only,
        }

    def contribution_table(self) -> list[ContributionRow]:
        """Generate human-readable contribution table."""
        rows: list[ContributionRow] = []

        for domain_name, domain_score in self.domains.items():
            for fv in domain_score.features:
                # Calculate contribution
                if fv.value is not None:
                    feature_weight = FEATURE_WEIGHTS.get(fv.feature_id, 0.0)
                    contribution = fv.value * feature_weight * domain_score.weight
                else:
                    contribution = None

                # Build evidence string
                if fv.raw_numerator is not None and fv.raw_denominator is not None:
                    evidence = f"{fv.raw_numerator}/{fv.raw_denominator} in {fv.window}"
                elif fv.sample_count > 0:
                    evidence = f"{fv.sample_count} events in {fv.window}"
                else:
                    evidence = "No data"

                rows.append(
                    ContributionRow(
                        feature_name=fv.feature_id.name.replace("_", " ").title(),
                        feature_id=fv.feature_id.value,
                        domain=domain_name,
                        value=round(fv.value, 4) if fv.value is not None else None,
                        weight=FEATURE_WEIGHTS.get(fv.feature_id, 0.0),
                        contribution=(round(contribution, 4) if contribution is not None else None),
                        evidence=evidence,
                    )
                )

        return rows


# Risk tier thresholds (from TRUST_RISK_MODEL.md)
RISK_TIERS: list[tuple[float, str]] = [
    (0.20, "MINIMAL"),
    (0.40, "LOW"),
    (0.60, "MODERATE"),
    (0.80, "HIGH"),
    (1.01, "CRITICAL"),  # 1.01 to catch 1.0 exactly
]


def get_risk_tier(tri: float) -> str:
    """
    Map TRI score to risk tier.

    NOTE: No tier is called "safe" — this is intentional per governance contract.
    """
    for threshold, tier in RISK_TIERS:
        if tri < threshold:
            return tier
    return "CRITICAL"
