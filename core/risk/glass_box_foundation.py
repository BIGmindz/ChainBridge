# core/risk/glass_box_foundation.py
"""
════════════════════════════════════════════════════════════════════════════════
Glass-Box Risk Scoring Foundation — ChainIQ / PDO Generation
════════════════════════════════════════════════════════════════════════════════

PAC ID: PAC-MAGGIE-GLASS-BOX-RISK-SCORING-FOUNDATION-01
Author: MAGGIE (GID-10) — ML & Applied AI Lead
Version: 1.0.0

PURPOSE:
Establish audit-grade risk scoring suitable for ChainIQ integration and PDO
(Payment Decision Outcome) generation.

PRIORITIES (ordered):
1. Interpretability (glass-box)
2. Calibration (probabilistic validity)
3. Regulatory defensibility
4. Predictive lift (secondary)

CONSTRAINTS (ABSOLUTE):
- No opaque models (neural nets, black-box ensembles)
- No learned weights without explicit governance approval
- Monotonic constraints where economically justified
- Full explanation provenance for every score

MODEL FAMILY: Explainable Boosting Machine (EBM) / Generalized Additive Model (GAM)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# COMMERCIAL AUDIT — Decision Monetization
# ============================================================================


class DecisionEconomics(str, Enum):
    """
    Decision types mapped to economic outcomes.

    Risk scoring ultimately translates to:
    RISK → CASH → SETTLEMENT
    """
    PAYMENT_APPROVAL = "payment_approval"        # Low risk → approve → revenue
    PAYMENT_HOLD = "payment_hold"                # Medium risk → hold → delay cost
    PAYMENT_REJECT = "payment_reject"            # High risk → reject → protection
    SETTLEMENT_ACCELERATE = "settlement_accelerate"  # Trust → faster settlement
    SETTLEMENT_STANDARD = "settlement_standard"  # Standard flow
    SETTLEMENT_DELAY = "settlement_delay"        # Distrust → delayed settlement


@dataclass(frozen=True)
class FalseOutcomeCost:
    """
    Cost structure for false positive / false negative decisions.

    FALSE POSITIVE: Flagged as risky, but was actually safe
    - Cost: Lost revenue, customer friction, operational overhead

    FALSE NEGATIVE: Flagged as safe, but was actually risky
    - Cost: Fraud loss, regulatory penalty, reputation damage

    ASYMMETRY: FN cost typically >> FP cost for financial fraud
    """
    false_positive_cost: float  # $ cost of wrongly flagging good transaction
    false_negative_cost: float  # $ cost of missing bad transaction

    @property
    def asymmetry_ratio(self) -> float:
        """FN/FP cost ratio — higher means bias toward caution."""
        if self.false_positive_cost == 0:
            return float("inf")
        return self.false_negative_cost / self.false_positive_cost

    @property
    def optimal_threshold_hint(self) -> float:
        """
        Theoretical optimal threshold given cost asymmetry.

        From decision theory: threshold = FP_cost / (FP_cost + FN_cost)
        """
        total = self.false_positive_cost + self.false_negative_cost
        if total == 0:
            return 0.5
        return self.false_positive_cost / total


# Default cost structure for payment decisions
DEFAULT_PAYMENT_COSTS = FalseOutcomeCost(
    false_positive_cost=50.0,    # $50 avg cost of manual review + delay
    false_negative_cost=5000.0,  # $5000 avg fraud loss + recovery cost
)


# ============================================================================
# DATA INTERROGATION — Feature Provenance
# ============================================================================


class FeatureProvenance(str, Enum):
    """
    Provenance classification for risk features.

    Each feature must have documented provenance to ensure:
    - No data leakage (future info bleeding into past)
    - No proxy discrimination (protected class proxies)
    - Temporal validity (feature available at decision time)
    """
    GOVERNANCE_LOG = "governance_log"       # From governance event logs
    SYSTEM_METRIC = "system_metric"         # From system telemetry
    EXTERNAL_SIGNAL = "external_signal"     # From external data sources
    DERIVED_FEATURE = "derived_feature"     # Computed from other features
    TEMPORAL_AGGREGATE = "temporal_aggregate"  # Time-windowed aggregation


class LeakageRisk(str, Enum):
    """
    Data leakage risk levels.
    """
    NONE = "none"           # Feature is causally valid
    LOW = "low"             # Minimal risk, requires monitoring
    MEDIUM = "medium"       # Potential leakage, requires justification
    HIGH = "high"           # Likely leakage, should not use
    PROHIBITED = "prohibited"  # Known leakage, must not use


@dataclass(frozen=True)
class FeatureAuditRecord:
    """
    Audit record for a single feature in the risk model.
    """
    feature_id: str
    description: str
    provenance: FeatureProvenance
    leakage_risk: LeakageRisk
    temporal_validity: str          # When this feature is available
    monotonic_direction: Optional[str]  # "increasing", "decreasing", or None
    economic_justification: str     # Why this feature matters economically

    def is_safe_to_use(self) -> bool:
        """Feature is safe if leakage risk is low or none."""
        return self.leakage_risk in (LeakageRisk.NONE, LeakageRisk.LOW)


# ============================================================================
# GLASS-BOX MODEL SPEC — EBM/GAM Structure
# ============================================================================


class MonotonicConstraint(str, Enum):
    """
    Monotonic constraint direction for interpretable models.
    """
    INCREASING = "increasing"   # Higher feature → higher risk
    DECREASING = "decreasing"   # Higher feature → lower risk
    NONE = "none"               # No constraint (allow non-monotonic)


@dataclass(frozen=True)
class ShapeFunctionSpec:
    """
    Specification for a single feature's shape function in EBM/GAM.

    Shape function: f_i(x_i) → contribution to log-odds

    For glass-box models, each feature has an independent shape function
    that can be inspected, plotted, and audited.
    """
    feature_id: str
    input_range: Tuple[float, float]    # (min, max) expected input
    monotonic: MonotonicConstraint
    smoothness: str                      # "smooth", "step", "linear"
    max_bins: int                        # Maximum discretization bins

    # Audit fields
    economic_interpretation: str         # What this shape function means
    edge_case_handling: str              # How extremes are handled


@dataclass(frozen=True)
class GlassBoxModelSpec:
    """
    Complete specification for a glass-box risk model.

    Structure: GAM/EBM with additive feature contributions

    score = sigmoid( intercept + Σ f_i(x_i) )

    Where each f_i is an inspectable, potentially monotonic shape function.
    """
    model_id: str
    version: str
    feature_specs: Tuple[ShapeFunctionSpec, ...]
    intercept: float                     # Base log-odds (prior)
    target_definition: str               # What "risk" means operationally
    calibration_method: str              # "platt", "isotonic", "none"

    # Audit metadata
    training_window: str                 # Time period of training data
    validation_window: str               # Time period of validation data
    created_at: str
    created_by: str                      # Must be "MAGGIE (GID-10)"

    @property
    def feature_count(self) -> int:
        return len(self.feature_specs)

    @property
    def is_fully_monotonic(self) -> bool:
        """Check if all features have monotonic constraints."""
        return all(
            fs.monotonic != MonotonicConstraint.NONE
            for fs in self.feature_specs
        )


# ============================================================================
# CALIBRATION — Probabilistic Validity
# ============================================================================


class CalibrationMethod(str, Enum):
    """
    Calibration methods for converting raw scores to probabilities.
    """
    NONE = "none"           # Use raw model output
    PLATT = "platt"         # Platt scaling (logistic regression on scores)
    ISOTONIC = "isotonic"   # Isotonic regression (monotonic transformation)
    BETA = "beta"           # Beta calibration


@dataclass(frozen=True)
class CalibrationBin:
    """
    Single bin in calibration analysis.
    """
    bin_lower: float
    bin_upper: float
    predicted_prob: float       # Average predicted probability in bin
    observed_rate: float        # Actual positive rate in bin
    sample_count: int           # Number of samples in bin

    @property
    def calibration_error(self) -> float:
        """Absolute calibration error for this bin."""
        return abs(self.predicted_prob - self.observed_rate)


@dataclass(frozen=True)
class CalibrationReport:
    """
    Complete calibration analysis report.
    """
    method: CalibrationMethod
    bins: Tuple[CalibrationBin, ...]
    ece: float                  # Expected Calibration Error
    mce: float                  # Maximum Calibration Error
    brier_score: float          # Brier score (mean squared error)

    # Cohort stability
    cohorts_tested: int
    worst_cohort_ece: float

    # Time stability
    time_windows_tested: int
    worst_window_ece: float

    # Metadata
    sample_count: int
    positive_rate: float        # Base rate of positive class
    computed_at: str

    @property
    def is_well_calibrated(self) -> bool:
        """
        Calibration is acceptable if ECE < 0.05 (5%).
        """
        return self.ece < 0.05

    @property
    def is_stable(self) -> bool:
        """
        Calibration is stable if worst cohort/window ECE < 0.10 (10%).
        """
        return self.worst_cohort_ece < 0.10 and self.worst_window_ece < 0.10


# ============================================================================
# EXPLANATION ARTIFACTS — PDO / OC Consumption
# ============================================================================


@dataclass(frozen=True)
class FeatureContribution:
    """
    Single feature's contribution to a risk score.
    """
    feature_id: str
    feature_name: str           # Human-readable name
    feature_value: float        # Input value
    contribution: float         # Additive contribution to log-odds
    direction: str              # "increases_risk" or "decreases_risk"
    rank: int                   # Importance rank (1 = most important)

    @property
    def contribution_description(self) -> str:
        """Human-readable contribution description."""
        direction_word = "increases" if self.direction == "increases_risk" else "decreases"
        return f"{self.feature_name} = {self.feature_value:.2f} {direction_word} risk"


@dataclass(frozen=True)
class PDOExplanation:
    """
    Payment Decision Outcome explanation artifact.

    This is the primary explanation format consumed by:
    - OC (Operator Control) for decision review
    - Trust Center for audit queries
    - PDO generation for customer-facing explanations
    """
    decision_id: str
    risk_score: float                   # [0.0, 1.0] calibrated probability
    risk_tier: str                      # MINIMAL, LOW, MODERATE, HIGH, CRITICAL
    confidence_lower: float             # Lower bound of confidence interval
    confidence_upper: float             # Upper bound of confidence interval

    # Top contributing factors (ranked)
    top_factors: Tuple[FeatureContribution, ...]

    # Decision rationale
    primary_reason: str                 # Single sentence primary reason
    secondary_reasons: Tuple[str, ...]  # Additional context

    # Provenance
    model_id: str
    model_version: str
    computed_at: str

    # MANDATORY: Advisory flag
    advisory_only: bool = True

    def __post_init__(self) -> None:
        """Enforce advisory_only is always True."""
        if not self.advisory_only:
            raise ValueError("PDOExplanation.advisory_only must always be True")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "decision_id": self.decision_id,
            "risk_score": round(self.risk_score, 4),
            "risk_tier": self.risk_tier,
            "confidence": {
                "lower": round(self.confidence_lower, 4),
                "upper": round(self.confidence_upper, 4),
            },
            "top_factors": [
                {
                    "feature": fc.feature_name,
                    "value": round(fc.feature_value, 4),
                    "contribution": round(fc.contribution, 4),
                    "direction": fc.direction,
                    "rank": fc.rank,
                }
                for fc in self.top_factors
            ],
            "rationale": {
                "primary": self.primary_reason,
                "secondary": list(self.secondary_reasons),
            },
            "provenance": {
                "model_id": self.model_id,
                "model_version": self.model_version,
                "computed_at": self.computed_at,
            },
            "advisory_only": self.advisory_only,
        }

    def to_human_readable(self) -> str:
        """Generate human-readable explanation string."""
        lines = [
            f"Risk Assessment: {self.risk_tier} ({self.risk_score:.1%})",
            f"Confidence: [{self.confidence_lower:.1%}, {self.confidence_upper:.1%}]",
            "",
            f"Primary Reason: {self.primary_reason}",
            "",
            "Contributing Factors:",
        ]

        for fc in self.top_factors[:5]:  # Top 5 factors
            lines.append(f"  {fc.rank}. {fc.contribution_description}")

        if self.secondary_reasons:
            lines.append("")
            lines.append("Additional Context:")
            for reason in self.secondary_reasons[:3]:  # Top 3 secondary
                lines.append(f"  - {reason}")

        lines.append("")
        lines.append(f"[Model: {self.model_id} v{self.model_version}]")
        lines.append("[ADVISORY ONLY - Not a governance decision]")

        return "\n".join(lines)


# ============================================================================
# EXPLANATION GENERATION — Core Functions
# ============================================================================


def generate_pdo_explanation(
    decision_id: str,
    risk_score: float,
    confidence_band: Tuple[float, float],
    feature_contributions: List[Tuple[str, str, float, float]],  # (id, name, value, contribution)
    model_id: str,
    model_version: str,
) -> PDOExplanation:
    """
    Generate PDO explanation from model output.

    Args:
        decision_id: Unique decision identifier
        risk_score: Calibrated risk probability [0.0, 1.0]
        confidence_band: (lower, upper) confidence interval
        feature_contributions: List of (feature_id, feature_name, value, contribution)
        model_id: Model identifier
        model_version: Model version

    Returns:
        PDOExplanation artifact ready for OC/Trust Center consumption
    """
    # Sort contributions by absolute magnitude
    sorted_contribs = sorted(
        feature_contributions,
        key=lambda x: abs(x[3]),
        reverse=True,
    )

    # Build FeatureContribution objects
    top_factors = []
    for rank, (fid, fname, fval, fcontrib) in enumerate(sorted_contribs[:5], 1):
        direction = "increases_risk" if fcontrib > 0 else "decreases_risk"
        top_factors.append(
            FeatureContribution(
                feature_id=fid,
                feature_name=fname,
                feature_value=fval,
                contribution=fcontrib,
                direction=direction,
                rank=rank,
            )
        )

    # Determine risk tier
    if risk_score < 0.20:
        tier = "MINIMAL"
    elif risk_score < 0.40:
        tier = "LOW"
    elif risk_score < 0.60:
        tier = "MODERATE"
    elif risk_score < 0.80:
        tier = "HIGH"
    else:
        tier = "CRITICAL"

    # Generate primary reason from top factor
    if top_factors:
        top = top_factors[0]
        if top.direction == "increases_risk":
            primary_reason = f"Elevated risk primarily due to {top.feature_name}"
        else:
            primary_reason = f"Risk mitigated by favorable {top.feature_name}"
    else:
        primary_reason = "Risk assessment based on aggregate factors"

    # Generate secondary reasons from remaining factors
    secondary_reasons = []
    for fc in top_factors[1:3]:
        secondary_reasons.append(fc.contribution_description)

    return PDOExplanation(
        decision_id=decision_id,
        risk_score=risk_score,
        risk_tier=tier,
        confidence_lower=confidence_band[0],
        confidence_upper=confidence_band[1],
        top_factors=tuple(top_factors),
        primary_reason=primary_reason,
        secondary_reasons=tuple(secondary_reasons),
        model_id=model_id,
        model_version=model_version,
        computed_at=datetime.now(timezone.utc).isoformat(),
        advisory_only=True,
    )


# ============================================================================
# RISK TIER MAPPING — Consistent Tier Definitions
# ============================================================================


RISK_TIER_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "MINIMAL": {
        "threshold": 0.20,
        "description": "Very low risk, routine processing",
        "action": "Auto-approve eligible",
        "review_required": False,
    },
    "LOW": {
        "threshold": 0.40,
        "description": "Low risk, standard processing",
        "action": "Standard approval flow",
        "review_required": False,
    },
    "MODERATE": {
        "threshold": 0.60,
        "description": "Moderate risk, enhanced monitoring",
        "action": "Flag for monitoring",
        "review_required": False,
    },
    "HIGH": {
        "threshold": 0.80,
        "description": "High risk, review recommended",
        "action": "Queue for manual review",
        "review_required": True,
    },
    "CRITICAL": {
        "threshold": 1.00,
        "description": "Critical risk, immediate attention",
        "action": "Block and escalate",
        "review_required": True,
    },
}


def get_tier_action(tier: str) -> str:
    """Get recommended action for risk tier."""
    return RISK_TIER_DEFINITIONS.get(tier, {}).get("action", "Unknown tier")


def requires_review(tier: str) -> bool:
    """Check if tier requires manual review."""
    return RISK_TIER_DEFINITIONS.get(tier, {}).get("review_required", True)
