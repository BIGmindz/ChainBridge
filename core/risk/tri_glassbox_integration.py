# core/risk/tri_glassbox_integration.py
"""
════════════════════════════════════════════════════════════════════════════════
TRI ⇄ Glass-Box Integration Contract Specification
════════════════════════════════════════════════════════════════════════════════

PAC ID: PAC-MAGGIE-TRI-GLASS-BOX-INTEGRATION-SPEC-01
Author: MAGGIE (GID-10) — ML & Applied AI Lead
Version: 1.0.0

PURPOSE:
Define and lock the integration contract between the Glass-Box Risk Foundation
and the existing TRI (Trust Risk Index) engine.

SCOPE:
- TRIRiskInput schema
- GlassBoxRiskOutput schema
- Severity tier mapping (TRI score → action tier)
- Failure modes (exhaustive enumeration)
- PDO risk embedding requirements

NEXT AGENT: CODY (GID-01, 🔵 BLUE)
PURPOSE: Implement TRI engine wiring strictly to this spec
CONSTRAINT: No interpretation allowed — spec is the source of truth

════════════════════════════════════════════════════════════════════════════════
INVARIANTS (ABSOLUTE):
════════════════════════════════════════════════════════════════════════════════

1. ACTIVATION BINDING:
   IF activation_reference IS MISSING → INTEGRATION = HARD_FAIL
   
2. MONOTONICITY:
   Higher risk_score MUST NOT yield a lower-severity TRI action
   
3. EXPLANATION COMPLETENESS:
   Every GlassBoxRiskOutput MUST include top_contributors
   
4. PDO EMBEDDING:
   IF PDO missing required risk fields → PDO = INVALID

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple


# ============================================================================
# SEVERITY TIER MAPPING — TRI Score → Action Tier
# ============================================================================

# THRESHOLD CONSTANTS — LOCKED BY PAC
SEVERITY_LOW_UPPER_BOUND: float = 0.33      # [0.00, 0.33)
SEVERITY_MEDIUM_UPPER_BOUND: float = 0.66   # [0.33, 0.66)
# HIGH: [0.66, 1.00]


class RiskSeverityTier(str, Enum):
    """
    Risk severity tiers mapped to TRI score ranges.
    
    INVARIANT: Thresholds are immutable per PAC specification.
    """
    LOW = "low"         # [0.00, 0.33) → Standard processing
    MEDIUM = "medium"   # [0.33, 0.66) → Enhanced review
    HIGH = "high"       # [0.66, 1.00] → Escalation required


class TRIAction(str, Enum):
    """
    Actions mapped to severity tiers.
    
    MONOTONICITY CONSTRAINT:
    LOW → STANDARD → no intervention
    MEDIUM → REVIEW → manual review required
    HIGH → ESCALATE → senior review + potential block
    
    INVARIANT: Action severity MUST NOT decrease as risk_score increases.
    """
    STANDARD = "standard"     # LOW tier → proceed normally
    REVIEW = "review"         # MEDIUM tier → queue for review
    ESCALATE = "escalate"     # HIGH tier → immediate escalation


# ACTION ORDERING — For monotonicity enforcement
ACTION_SEVERITY_ORDER: Dict[TRIAction, int] = {
    TRIAction.STANDARD: 0,
    TRIAction.REVIEW: 1,
    TRIAction.ESCALATE: 2,
}


def score_to_severity_tier(risk_score: float) -> RiskSeverityTier:
    """
    Map risk score to severity tier.
    
    INVARIANT: This mapping is monotonic and deterministic.
    
    Args:
        risk_score: Float in [0.0, 1.0]
        
    Returns:
        RiskSeverityTier corresponding to the score
        
    Raises:
        ValueError: If risk_score is outside [0.0, 1.0]
    """
    if not (0.0 <= risk_score <= 1.0):
        raise ValueError(
            f"risk_score must be in [0.0, 1.0], got {risk_score}"
        )
    
    if risk_score < SEVERITY_LOW_UPPER_BOUND:
        return RiskSeverityTier.LOW
    elif risk_score < SEVERITY_MEDIUM_UPPER_BOUND:
        return RiskSeverityTier.MEDIUM
    else:
        return RiskSeverityTier.HIGH


def severity_tier_to_action(tier: RiskSeverityTier) -> TRIAction:
    """
    Map severity tier to TRI action.
    
    INVARIANT: This mapping is deterministic and monotonic.
    """
    mapping = {
        RiskSeverityTier.LOW: TRIAction.STANDARD,
        RiskSeverityTier.MEDIUM: TRIAction.REVIEW,
        RiskSeverityTier.HIGH: TRIAction.ESCALATE,
    }
    return mapping[tier]


def score_to_action(risk_score: float) -> TRIAction:
    """
    Map risk score directly to TRI action.
    
    Convenience function combining tier mapping and action mapping.
    """
    tier = score_to_severity_tier(risk_score)
    return severity_tier_to_action(tier)


# ============================================================================
# FAILURE MODES — Exhaustive Enumeration
# ============================================================================


class IntegrationFailureMode(str, Enum):
    """
    Exhaustive enumeration of TRI ⇄ Glass-Box integration failure modes.
    
    INVARIANT: ALL failure modes result in HARD FAIL — no fallback.
    """
    # Activation failures
    MISSING_ACTIVATION = "missing_activation"
    INVALID_ACTIVATION = "invalid_activation"
    EXPIRED_ACTIVATION = "expired_activation"
    
    # Contract violations
    RISK_CONTRACT_VIOLATION = "risk_contract_violation"
    MONOTONICITY_VIOLATION = "monotonicity_violation"
    
    # Explanation failures
    UNEXPLAINED_DECISION = "unexplained_decision"
    MISSING_CONTRIBUTORS = "missing_contributors"
    
    # Schema violations
    INVALID_RISK_SCORE = "invalid_risk_score"
    INVALID_CONFIDENCE_BAND = "invalid_confidence_band"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    
    # Model violations
    UNKNOWN_MODEL_ID = "unknown_model_id"
    MODEL_VERSION_MISMATCH = "model_version_mismatch"


@dataclass(frozen=True)
class IntegrationFailure:
    """
    Integration failure record.
    
    INVARIANT: All failures are terminal — no recovery pathway.
    """
    mode: IntegrationFailureMode
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    
    @classmethod
    def create(
        cls,
        mode: IntegrationFailureMode,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "IntegrationFailure":
        """Factory method with automatic timestamp."""
        return cls(
            mode=mode,
            message=message,
            context=context or {},
            timestamp=datetime.now(timezone.utc),
        )


# ============================================================================
# INPUT SCHEMA — TRIRiskInput
# ============================================================================


@dataclass(frozen=True)
class ActivationReference:
    """
    Reference to the agent's activation block.
    
    INVARIANT: Every risk computation MUST have a valid activation reference.
    """
    agent_gid: str              # e.g., "GID-10"
    activation_hash: str        # Hash of the activation block
    activation_timestamp: datetime
    scope_constraints: Tuple[str, ...]  # Permitted operation scopes
    
    def is_valid(self) -> bool:
        """
        Check if activation reference is structurally valid.
        
        Note: This checks structure only, not cryptographic validity.
        """
        return bool(
            self.agent_gid
            and self.activation_hash
            and self.activation_timestamp
        )


@dataclass(frozen=True)
class TRIRiskInput:
    """
    Input schema for TRI ⇄ Glass-Box integration.
    
    REQUIRED FIELDS (all mandatory):
    - activation_reference: Agent activation context
    - event_window_start: Start of analysis window
    - event_window_end: End of analysis window
    - entity_id: Entity being scored
    - request_id: Unique request identifier
    
    OPTIONAL FIELDS:
    - domain_focus: Specific risk domain to emphasize
    - feature_overrides: Pre-computed features (for testing)
    """
    # === REQUIRED ===
    activation_reference: ActivationReference
    event_window_start: datetime
    event_window_end: datetime
    entity_id: str
    request_id: str
    
    # === OPTIONAL ===
    domain_focus: Optional[str] = None
    feature_overrides: Optional[Dict[str, float]] = None
    
    def validate(self) -> Tuple[bool, Optional[IntegrationFailure]]:
        """
        Validate input against schema requirements.
        
        Returns:
            (True, None) if valid
            (False, IntegrationFailure) if invalid
        """
        # Check activation reference
        if self.activation_reference is None:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.MISSING_ACTIVATION,
                    message="activation_reference is required",
                    context={"request_id": self.request_id},
                ),
            )
        
        if not self.activation_reference.is_valid():
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.INVALID_ACTIVATION,
                    message="activation_reference is structurally invalid",
                    context={
                        "request_id": self.request_id,
                        "activation": {
                            "agent_gid": self.activation_reference.agent_gid,
                            "has_hash": bool(self.activation_reference.activation_hash),
                        },
                    },
                ),
            )
        
        # Check temporal validity
        if self.event_window_end < self.event_window_start:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.RISK_CONTRACT_VIOLATION,
                    message="event_window_end must be >= event_window_start",
                    context={
                        "request_id": self.request_id,
                        "window_start": self.event_window_start.isoformat(),
                        "window_end": self.event_window_end.isoformat(),
                    },
                ),
            )
        
        # Check entity_id
        if not self.entity_id:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.MISSING_REQUIRED_FIELD,
                    message="entity_id is required",
                    context={"request_id": self.request_id},
                ),
            )
        
        return (True, None)


# ============================================================================
# OUTPUT SCHEMA — GlassBoxRiskOutput
# ============================================================================


@dataclass(frozen=True)
class FeatureContribution:
    """
    Single feature's contribution to the risk score.
    
    INVARIANT: Contributions must sum to risk_score (within tolerance).
    """
    feature_id: str
    feature_value: float
    contribution: float             # Contribution to final score
    contribution_direction: str     # "increasing" or "decreasing"
    explanation: str                # Human-readable explanation


@dataclass(frozen=True)
class ConfidenceBand:
    """
    Confidence interval for the risk score.
    
    INVARIANT: lower <= point_estimate <= upper
    """
    lower: float
    point_estimate: float
    upper: float
    confidence_level: float = 0.95  # 95% CI by default
    
    def is_valid(self) -> bool:
        """Check structural validity of confidence band."""
        return (
            0.0 <= self.lower <= self.point_estimate <= self.upper <= 1.0
            and 0.0 < self.confidence_level <= 1.0
        )


@dataclass(frozen=True)
class ModelIdentity:
    """
    Identity of the model that produced the score.
    
    INVARIANT: model_id + model_version must uniquely identify the model.
    """
    model_id: str               # e.g., "glassbox-ebm-v1"
    model_version: str          # e.g., "1.0.0"
    calibration_date: datetime  # When model was last calibrated
    feature_count: int          # Number of features in model


@dataclass(frozen=True)
class GlassBoxRiskOutput:
    """
    Output schema for TRI ⇄ Glass-Box integration.
    
    ALL FIELDS ARE REQUIRED — no optional fields in output.
    
    INVARIANTS:
    - risk_score in [0.0, 1.0]
    - risk_tier consistent with risk_score
    - confidence_band valid
    - top_contributors non-empty
    - model_identity present
    """
    # === CORE RISK OUTPUT ===
    risk_score: float
    risk_tier: RiskSeverityTier
    action: TRIAction
    
    # === CONFIDENCE ===
    confidence_band: ConfidenceBand
    
    # === EXPLAINABILITY ===
    top_contributors: Tuple[FeatureContribution, ...]
    explanation_summary: str
    
    # === MODEL IDENTITY ===
    model_identity: ModelIdentity
    
    # === PROVENANCE ===
    request_id: str
    computation_timestamp: datetime
    activation_hash: str  # From input activation_reference
    
    def validate(self) -> Tuple[bool, Optional[IntegrationFailure]]:
        """
        Validate output against schema requirements.
        
        Returns:
            (True, None) if valid
            (False, IntegrationFailure) if invalid
        """
        # Check risk_score bounds
        if not (0.0 <= self.risk_score <= 1.0):
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.INVALID_RISK_SCORE,
                    message=f"risk_score must be in [0.0, 1.0], got {self.risk_score}",
                    context={"request_id": self.request_id},
                ),
            )
        
        # Check risk_tier consistency
        expected_tier = score_to_severity_tier(self.risk_score)
        if self.risk_tier != expected_tier:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.RISK_CONTRACT_VIOLATION,
                    message=f"risk_tier {self.risk_tier} inconsistent with risk_score {self.risk_score}",
                    context={
                        "request_id": self.request_id,
                        "expected_tier": expected_tier.value,
                        "actual_tier": self.risk_tier.value,
                    },
                ),
            )
        
        # Check action consistency
        expected_action = severity_tier_to_action(self.risk_tier)
        if self.action != expected_action:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.MONOTONICITY_VIOLATION,
                    message=f"action {self.action} inconsistent with risk_tier {self.risk_tier}",
                    context={
                        "request_id": self.request_id,
                        "expected_action": expected_action.value,
                        "actual_action": self.action.value,
                    },
                ),
            )
        
        # Check confidence band
        if not self.confidence_band.is_valid():
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.INVALID_CONFIDENCE_BAND,
                    message="confidence_band is structurally invalid",
                    context={
                        "request_id": self.request_id,
                        "confidence_band": {
                            "lower": self.confidence_band.lower,
                            "point_estimate": self.confidence_band.point_estimate,
                            "upper": self.confidence_band.upper,
                        },
                    },
                ),
            )
        
        # Check top_contributors
        if not self.top_contributors:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.MISSING_CONTRIBUTORS,
                    message="top_contributors must be non-empty",
                    context={"request_id": self.request_id},
                ),
            )
        
        # Check model_identity
        if not self.model_identity.model_id or not self.model_identity.model_version:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.UNKNOWN_MODEL_ID,
                    message="model_identity must have model_id and model_version",
                    context={"request_id": self.request_id},
                ),
            )
        
        return (True, None)


# ============================================================================
# PDO RISK EMBEDDING — Required Fields
# ============================================================================


@dataclass(frozen=True)
class PDORiskEmbedding:
    """
    Risk data that MUST be embedded in every PDO (Payment Decision Outcome).
    
    INVARIANT: IF any field is missing → PDO = INVALID
    
    This is the minimum risk context required for audit-grade PDOs.
    """
    # === REQUIRED RISK FIELDS ===
    risk_score: float
    risk_tier: str              # RiskSeverityTier.value
    confidence_lower: float
    confidence_upper: float
    
    # === REQUIRED EXPLANATION FIELDS ===
    top_contributor_1_id: str
    top_contributor_1_value: float
    top_contributor_2_id: Optional[str]  # May be None if only 1 contributor
    top_contributor_2_value: Optional[float]
    
    # === REQUIRED MODEL FIELDS ===
    model_id: str
    model_version: str
    
    # === REQUIRED PROVENANCE ===
    computation_timestamp: str  # ISO format
    activation_hash: str
    
    @classmethod
    def from_glass_box_output(
        cls,
        output: GlassBoxRiskOutput,
    ) -> "PDORiskEmbedding":
        """
        Extract PDO embedding from GlassBoxRiskOutput.
        
        This is the canonical extraction — no other method should be used.
        """
        # Get top 2 contributors
        contributors = output.top_contributors
        top_1 = contributors[0] if len(contributors) > 0 else None
        top_2 = contributors[1] if len(contributors) > 1 else None
        
        return cls(
            risk_score=output.risk_score,
            risk_tier=output.risk_tier.value,
            confidence_lower=output.confidence_band.lower,
            confidence_upper=output.confidence_band.upper,
            top_contributor_1_id=top_1.feature_id if top_1 else "",
            top_contributor_1_value=top_1.contribution if top_1 else 0.0,
            top_contributor_2_id=top_2.feature_id if top_2 else None,
            top_contributor_2_value=top_2.contribution if top_2 else None,
            model_id=output.model_identity.model_id,
            model_version=output.model_identity.model_version,
            computation_timestamp=output.computation_timestamp.isoformat(),
            activation_hash=output.activation_hash,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for PDO embedding.
        
        INVARIANT: All required fields are present in output.
        """
        return {
            "risk_score": self.risk_score,
            "risk_tier": self.risk_tier,
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "top_contributor_1_id": self.top_contributor_1_id,
            "top_contributor_1_value": self.top_contributor_1_value,
            "top_contributor_2_id": self.top_contributor_2_id,
            "top_contributor_2_value": self.top_contributor_2_value,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "computation_timestamp": self.computation_timestamp,
            "activation_hash": self.activation_hash,
        }


def validate_pdo_risk_embedding(embedding_dict: Dict[str, Any]) -> Tuple[bool, Optional[IntegrationFailure]]:
    """
    Validate that a PDO has all required risk embedding fields.
    
    INVARIANT: IF any required field is missing → PDO = INVALID
    
    Args:
        embedding_dict: Dictionary from PDO risk_context field
        
    Returns:
        (True, None) if valid
        (False, IntegrationFailure) if invalid
    """
    required_fields = [
        "risk_score",
        "risk_tier",
        "confidence_lower",
        "confidence_upper",
        "top_contributor_1_id",
        "top_contributor_1_value",
        "model_id",
        "model_version",
        "computation_timestamp",
        "activation_hash",
    ]
    
    for field in required_fields:
        if field not in embedding_dict:
            return (
                False,
                IntegrationFailure.create(
                    mode=IntegrationFailureMode.MISSING_REQUIRED_FIELD,
                    message=f"PDO missing required risk field: {field}",
                    context={"missing_field": field},
                ),
            )
    
    # Validate risk_score bounds
    risk_score = embedding_dict.get("risk_score")
    if risk_score is not None and not (0.0 <= risk_score <= 1.0):
        return (
            False,
            IntegrationFailure.create(
                mode=IntegrationFailureMode.INVALID_RISK_SCORE,
                message=f"PDO risk_score must be in [0.0, 1.0], got {risk_score}",
                context={"risk_score": risk_score},
            ),
        )
    
    return (True, None)


# ============================================================================
# MONOTONICITY ENFORCEMENT
# ============================================================================


def enforce_monotonicity(
    score_a: float,
    action_a: TRIAction,
    score_b: float,
    action_b: TRIAction,
) -> Tuple[bool, Optional[IntegrationFailure]]:
    """
    Enforce monotonicity constraint between two score-action pairs.
    
    INVARIANT: IF score_a < score_b THEN action_severity(a) <= action_severity(b)
    
    Args:
        score_a, action_a: First score-action pair
        score_b, action_b: Second score-action pair
        
    Returns:
        (True, None) if monotonicity holds
        (False, IntegrationFailure) if violated
    """
    # Order by score
    if score_a > score_b:
        score_a, action_a, score_b, action_b = score_b, action_b, score_a, action_a
    
    # Check action severity ordering
    severity_a = ACTION_SEVERITY_ORDER[action_a]
    severity_b = ACTION_SEVERITY_ORDER[action_b]
    
    if severity_a > severity_b:
        return (
            False,
            IntegrationFailure.create(
                mode=IntegrationFailureMode.MONOTONICITY_VIOLATION,
                message=(
                    f"Monotonicity violated: score {score_a} → {action_a.value} "
                    f"but score {score_b} → {action_b.value}"
                ),
                context={
                    "score_a": score_a,
                    "action_a": action_a.value,
                    "severity_a": severity_a,
                    "score_b": score_b,
                    "action_b": action_b.value,
                    "severity_b": severity_b,
                },
            ),
        )
    
    return (True, None)


# ============================================================================
# INTEGRATION CONTRACT SUMMARY
# ============================================================================

INTEGRATION_CONTRACT_VERSION = "1.0.0"

INTEGRATION_CONTRACT_SUMMARY = """
════════════════════════════════════════════════════════════════════════════════
TRI ⇄ GLASS-BOX INTEGRATION CONTRACT — v1.0.0
════════════════════════════════════════════════════════════════════════════════

INPUT: TRIRiskInput
  ├── activation_reference: ActivationReference (REQUIRED)
  ├── event_window_start: datetime (REQUIRED)
  ├── event_window_end: datetime (REQUIRED)
  ├── entity_id: str (REQUIRED)
  ├── request_id: str (REQUIRED)
  ├── domain_focus: Optional[str]
  └── feature_overrides: Optional[Dict[str, float]]

OUTPUT: GlassBoxRiskOutput
  ├── risk_score: float [0.0, 1.0] (REQUIRED)
  ├── risk_tier: RiskSeverityTier (REQUIRED)
  ├── action: TRIAction (REQUIRED)
  ├── confidence_band: ConfidenceBand (REQUIRED)
  ├── top_contributors: Tuple[FeatureContribution, ...] (REQUIRED, non-empty)
  ├── explanation_summary: str (REQUIRED)
  ├── model_identity: ModelIdentity (REQUIRED)
  ├── request_id: str (REQUIRED)
  ├── computation_timestamp: datetime (REQUIRED)
  └── activation_hash: str (REQUIRED)

SEVERITY MAPPING:
  ├── LOW:    [0.00, 0.33) → STANDARD action
  ├── MEDIUM: [0.33, 0.66) → REVIEW action
  └── HIGH:   [0.66, 1.00] → ESCALATE action

FAILURE MODES (all → HARD FAIL):
  ├── MISSING_ACTIVATION
  ├── INVALID_ACTIVATION
  ├── EXPIRED_ACTIVATION
  ├── RISK_CONTRACT_VIOLATION
  ├── MONOTONICITY_VIOLATION
  ├── UNEXPLAINED_DECISION
  ├── MISSING_CONTRIBUTORS
  ├── INVALID_RISK_SCORE
  ├── INVALID_CONFIDENCE_BAND
  ├── MISSING_REQUIRED_FIELD
  ├── UNKNOWN_MODEL_ID
  └── MODEL_VERSION_MISMATCH

PDO EMBEDDING (all required):
  ├── risk_score
  ├── risk_tier
  ├── confidence_lower
  ├── confidence_upper
  ├── top_contributor_1_id
  ├── top_contributor_1_value
  ├── model_id
  ├── model_version
  ├── computation_timestamp
  └── activation_hash

════════════════════════════════════════════════════════════════════════════════
NEXT AGENT: CODY (GID-01, 🔵 BLUE)
DIRECTIVE: Implement TRI engine wiring to this spec — NO INTERPRETATION ALLOWED
════════════════════════════════════════════════════════════════════════════════
"""


# Export public API
__all__ = [
    # Constants
    "SEVERITY_LOW_UPPER_BOUND",
    "SEVERITY_MEDIUM_UPPER_BOUND",
    "ACTION_SEVERITY_ORDER",
    "INTEGRATION_CONTRACT_VERSION",
    "INTEGRATION_CONTRACT_SUMMARY",
    # Enums
    "RiskSeverityTier",
    "TRIAction",
    "IntegrationFailureMode",
    # Dataclasses
    "IntegrationFailure",
    "ActivationReference",
    "TRIRiskInput",
    "FeatureContribution",
    "ConfidenceBand",
    "ModelIdentity",
    "GlassBoxRiskOutput",
    "PDORiskEmbedding",
    # Functions
    "score_to_severity_tier",
    "severity_tier_to_action",
    "score_to_action",
    "validate_pdo_risk_embedding",
    "enforce_monotonicity",
]
