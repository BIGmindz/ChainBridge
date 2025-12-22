"""ChainIQ Canonical Model Specification.

Defines the locked model architecture, contracts, and constraints
for enterprise-grade, regulator-defensible risk scoring.

════════════════════════════════════════════════════════════════════════════════
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
GID-10 — MAGGIE (ML & APPLIED AI)
PAC-MAGGIE-A10-RISK-MODEL-CANONICALIZATION-LOCK-01
🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
════════════════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: MAGGIE
GID: GID-10
EXECUTING COLOR: 🩷 PINK — ML & Applied AI Lane

⸻

II. DOCTRINE (LOCKED)

- Glass-box models ONLY at decision boundary
- Neural networks for feature generation ONLY
- Deterministic outputs given same inputs
- Monotonic constraints on risk signals
- Every score must be explainable, replayable, auditable

⸻

III. PROHIBITED ACTIONS

- Using black-box models at decision boundary
- Auto-correcting drift
- Silent fallback scoring
- Modifying locked constraints

⸻
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

# =============================================================================
# MODEL ARCHITECTURE CONSTANTS (LOCKED)
# =============================================================================


class ModelType(str, Enum):
    """Allowed model types at decision boundary.
    
    LOCKED: Only glass-box models permitted.
    """
    
    # ✅ ALLOWED — Glass-box models
    ADDITIVE_WEIGHTED_RULES = "additive_weighted_rules"
    EBM = "ebm"  # Explainable Boosting Machine
    GAM = "gam"  # Generalized Additive Model
    MONOTONIC_LOGISTIC = "monotonic_logistic"
    LINEAR_MODEL = "linear_model"
    
    # ❌ FORBIDDEN — These raise errors if instantiated at decision boundary
    # (Listed for documentation; actual forbidden types raise at validation)


class ForbiddenModelType(str, Enum):
    """Forbidden model types at decision boundary.
    
    These models may ONLY be used for upstream feature generation.
    Using them at decision boundary raises CanonicalModelViolation.
    """
    
    NEURAL_NETWORK = "neural_network"
    DEEP_LEARNING = "deep_learning"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    TRANSFORMER = "transformer"
    BLACK_BOX_ENSEMBLE = "black_box_ensemble"


class RiskBand(str, Enum):
    """Canonical risk band classifications.
    
    Derived from risk_score via fixed thresholds.
    NEVER learned or predicted directly.
    """
    
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DriftAction(str, Enum):
    """Actions for drift response.
    
    CRITICAL: Auto-correction is FORBIDDEN.
    """
    
    CONTINUE = "CONTINUE"
    MONITOR = "MONITOR"
    ALERT = "ALERT"
    ESCALATE = "ESCALATE"
    HALT = "HALT"


# =============================================================================
# RISK BAND THRESHOLDS (LOCKED)
# =============================================================================

RISK_BAND_THRESHOLDS: Dict[str, Tuple[int, int]] = {
    "LOW": (0, 40),
    "MEDIUM": (40, 70),
    "HIGH": (70, 85),
    "CRITICAL": (85, 101),  # 101 to include 100
}


def derive_risk_band(risk_score: float) -> RiskBand:
    """Derive risk band from score using fixed thresholds.
    
    This is a pure lookup — no learning, no model inference.
    
    Args:
        risk_score: Numeric risk score (0-100)
        
    Returns:
        RiskBand enumeration value
        
    Raises:
        ValueError: If risk_score outside [0, 100]
    """
    if not 0 <= risk_score <= 100:
        raise ValueError(f"risk_score must be in [0, 100], got {risk_score}")
    
    for band_name, (low, high) in RISK_BAND_THRESHOLDS.items():
        if low <= risk_score < high:
            return RiskBand(band_name)
    
    return RiskBand.CRITICAL  # Fallback for edge case


# =============================================================================
# MONOTONIC CONSTRAINTS (LOCKED)
# =============================================================================

@dataclass(frozen=True)
class MonotonicConstraint:
    """Definition of a monotonic constraint on a feature.
    
    Enforces that higher values of the feature MUST NOT decrease risk score.
    """
    
    feature_name: str
    direction: Literal["increasing", "decreasing"] = "increasing"
    description: str = ""
    
    def validate(self, old_value: float, new_value: float, 
                 old_score: float, new_score: float) -> bool:
        """Validate monotonicity is preserved.
        
        Returns:
            True if constraint satisfied, False if violated
        """
        if self.direction == "increasing":
            # Higher feature value should not decrease score
            if new_value > old_value and new_score < old_score:
                return False
        else:
            # Lower feature value should not decrease score
            if new_value < old_value and new_score < old_score:
                return False
        return True


# Canonical monotonic features (LOCKED)
MONOTONIC_FEATURES: List[MonotonicConstraint] = [
    MonotonicConstraint(
        feature_name="carrier_incident_rate_90d",
        direction="increasing",
        description="Higher incident rate MUST increase risk"
    ),
    MonotonicConstraint(
        feature_name="recent_delay_events",
        direction="increasing",
        description="More delays MUST increase risk"
    ),
    MonotonicConstraint(
        feature_name="iot_alert_count",
        direction="increasing",
        description="More IoT alerts MUST increase risk"
    ),
    MonotonicConstraint(
        feature_name="border_crossing_count",
        direction="increasing",
        description="More border crossings MUST increase risk"
    ),
    MonotonicConstraint(
        feature_name="value_usd",
        direction="increasing",
        description="Higher cargo value MUST increase risk"
    ),
    MonotonicConstraint(
        feature_name="lane_risk_index",
        direction="increasing",
        description="Higher lane risk MUST increase score"
    ),
]


# =============================================================================
# RISK INPUT/OUTPUT CONTRACTS (LOCKED)
# =============================================================================

@dataclass(frozen=True)
class RiskFactor:
    """Single factor contributing to risk score.
    
    Required for explainability — every score must have factors.
    """
    
    feature: str
    contribution: float
    direction: Literal["INCREASES_RISK", "DECREASES_RISK"]
    human_label: str = ""


@dataclass
class RiskInput:
    """Canonical risk scoring input contract.
    
    All fields documented and bounded.
    """
    
    # === Shipment Facts (REQUIRED) ===
    shipment_id: str
    value_usd: float
    is_hazmat: bool = False
    is_temp_control: bool = False
    expected_transit_days: int = 0
    
    # === Counterparty History (REQUIRED) ===
    carrier_id: str = ""
    carrier_incident_rate_90d: float = 0.0
    carrier_tenure_days: int = 0
    
    # === Lane/Route Context (REQUIRED) ===
    origin: str = ""
    destination: str = ""
    lane_risk_index: float = 0.0
    border_crossing_count: int = 0
    
    # === Real-time Signals (OPTIONAL) ===
    recent_delay_events: int = 0
    iot_alert_count: int = 0
    
    # === External Signals (BOUNDED) ===
    external_signals: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate input constraints."""
        if len(self.external_signals) > 10:
            raise ValueError("external_signals limited to 10 max")
        if self.value_usd < 0:
            raise ValueError("value_usd cannot be negative")
        if not 0.0 <= self.carrier_incident_rate_90d <= 1.0:
            raise ValueError("carrier_incident_rate_90d must be in [0, 1]")
        if not 0.0 <= self.lane_risk_index <= 1.0:
            raise ValueError("lane_risk_index must be in [0, 1]")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "shipment_id": self.shipment_id,
            "value_usd": self.value_usd,
            "is_hazmat": self.is_hazmat,
            "is_temp_control": self.is_temp_control,
            "expected_transit_days": self.expected_transit_days,
            "carrier_id": self.carrier_id,
            "carrier_incident_rate_90d": self.carrier_incident_rate_90d,
            "carrier_tenure_days": self.carrier_tenure_days,
            "origin": self.origin,
            "destination": self.destination,
            "lane_risk_index": self.lane_risk_index,
            "border_crossing_count": self.border_crossing_count,
            "recent_delay_events": self.recent_delay_events,
            "iot_alert_count": self.iot_alert_count,
            "external_signals": self.external_signals,
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of inputs for replay verification."""
        serialized = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


@dataclass
class RiskOutput:
    """Canonical risk scoring output contract.
    
    INVARIANTS:
    - risk_score monotonic with negative signals
    - risk_band derived from risk_score (not predicted)
    - reason_codes NEVER empty
    - top_factors MUST have at least 1 factor
    - Same inputs + model_version = identical output
    """
    
    # === Core Scores (REQUIRED) ===
    risk_score: float  # 0-100 scale
    risk_band: RiskBand
    confidence: float  # 0.0-1.0
    
    # === Explainability (REQUIRED — NEVER EMPTY) ===
    reason_codes: List[str]
    top_factors: List[RiskFactor]
    
    # === Versioning (REQUIRED) ===
    model_version: str
    data_version: str
    
    # === Audit (REQUIRED) ===
    assessed_at: str  # ISO-8601 UTC
    evaluation_id: str
    
    # === Replay Support ===
    input_hash: str = ""  # Hash of inputs for replay verification
    
    def __post_init__(self) -> None:
        """Validate output contract invariants."""
        # INV-RISK-001: Score in valid range
        if not 0 <= self.risk_score <= 100:
            raise ValueError(f"risk_score must be in [0, 100], got {self.risk_score}")
        
        # INV-RISK-002: Band matches score (derived, not predicted)
        expected_band = derive_risk_band(self.risk_score)
        if self.risk_band != expected_band:
            raise ValueError(
                f"risk_band must be derived from score. "
                f"Score {self.risk_score} should be {expected_band}, got {self.risk_band}"
            )
        
        # INV-RISK-003: Reason codes not empty
        if not self.reason_codes:
            raise ValueError("reason_codes MUST NOT be empty")
        
        # INV-RISK-004: Top factors not empty
        if not self.top_factors:
            raise ValueError("top_factors MUST contain at least 1 factor")
        
        # Confidence in valid range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "risk_score": self.risk_score,
            "risk_band": self.risk_band.value,
            "confidence": self.confidence,
            "reason_codes": self.reason_codes,
            "top_factors": [
                {
                    "feature": f.feature,
                    "contribution": f.contribution,
                    "direction": f.direction,
                    "human_label": f.human_label,
                }
                for f in self.top_factors
            ],
            "model_version": self.model_version,
            "data_version": self.data_version,
            "assessed_at": self.assessed_at,
            "evaluation_id": self.evaluation_id,
            "input_hash": self.input_hash,
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of output for replay verification."""
        # Exclude mutable fields from hash
        hashable = {
            "risk_score": self.risk_score,
            "risk_band": self.risk_band.value,
            "confidence": self.confidence,
            "reason_codes": sorted(self.reason_codes),
            "model_version": self.model_version,
            "input_hash": self.input_hash,
        }
        serialized = json.dumps(hashable, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


# =============================================================================
# MODEL SPECIFICATION (LOCKED)
# =============================================================================

@dataclass(frozen=True)
class CanonicalModelSpec:
    """Specification for a canonical risk model.
    
    This defines what a compliant model must provide.
    """
    
    model_type: ModelType
    model_version: str
    data_version: str
    
    # Monotonic features enforced
    monotonic_features: Tuple[str, ...] = tuple(f.feature_name for f in MONOTONIC_FEATURES)
    
    # Explainability requirements
    requires_reason_codes: bool = True
    requires_top_factors: bool = True
    min_factors: int = 1
    
    # Determinism guarantee
    deterministic: bool = True
    
    # Calibration reference
    calibration_artifact: Optional[str] = None
    
    def validate_model_type(self) -> None:
        """Ensure model type is allowed at decision boundary."""
        if self.model_type.value in [ft.value for ft in ForbiddenModelType]:
            raise CanonicalModelViolation(
                f"Model type {self.model_type} is FORBIDDEN at decision boundary. "
                "Only glass-box models (EBM, GAM, Additive Rules, etc.) are allowed."
            )


class CanonicalModelViolation(Exception):
    """Raised when a model violates canonical specification."""
    pass


# =============================================================================
# REPLAY CONTRACT (LOCKED)
# =============================================================================

@dataclass
class ReplayResult:
    """Result of a replay verification."""
    
    original_output_hash: str
    replay_output_hash: str
    inputs_match: bool
    outputs_match: bool
    model_version_match: bool
    replay_timestamp: str
    
    @property
    def verified(self) -> bool:
        """Check if replay verified successfully."""
        return (
            self.inputs_match and 
            self.outputs_match and 
            self.model_version_match
        )


def verify_replay(
    original_input: RiskInput,
    original_output: RiskOutput,
    replay_output: RiskOutput,
) -> ReplayResult:
    """Verify that replay produces identical output.
    
    GUARANTEE: Given same inputs + model_version → byte-for-byte identical output.
    
    Args:
        original_input: The original risk input
        original_output: The original risk output
        replay_output: The output from replay scoring
        
    Returns:
        ReplayResult with verification status
    """
    original_hash = original_output.compute_hash()
    replay_hash = replay_output.compute_hash()
    
    return ReplayResult(
        original_output_hash=original_hash,
        replay_output_hash=replay_hash,
        inputs_match=original_input.compute_hash() == replay_output.input_hash,
        outputs_match=original_hash == replay_hash,
        model_version_match=original_output.model_version == replay_output.model_version,
        replay_timestamp=datetime.now(timezone.utc).isoformat(),
    )


# =============================================================================
# CRO OVERRIDE PROOF (LOCKED)
# =============================================================================

@dataclass
class CROOverrideProof:
    """Proof artifact for CRO risk override.
    
    When CRO overrides a risk assessment, this proof MUST be emitted.
    """
    
    # Original assessment
    original_risk_score: float
    original_risk_band: RiskBand
    original_evaluation_id: str
    
    # Override details
    override_risk_score: float
    override_risk_band: RiskBand
    override_reason: str
    
    # Authority
    cro_agent_id: str
    override_timestamp: str
    approval_chain: List[str]  # List of approver IDs
    
    # Proof integrity
    proof_id: str = ""
    
    def __post_init__(self) -> None:
        """Generate proof ID if not provided."""
        if not self.proof_id:
            content = f"{self.original_evaluation_id}:{self.cro_agent_id}:{self.override_timestamp}"
            self.proof_id = f"OVERRIDE-{hashlib.sha256(content.encode()).hexdigest()[:16].upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit trail."""
        return {
            "proof_type": "CRO_OVERRIDE",
            "proof_id": self.proof_id,
            "original_risk_score": self.original_risk_score,
            "original_risk_band": self.original_risk_band.value,
            "original_evaluation_id": self.original_evaluation_id,
            "override_risk_score": self.override_risk_score,
            "override_risk_band": self.override_risk_band.value,
            "override_reason": self.override_reason,
            "cro_agent_id": self.cro_agent_id,
            "override_timestamp": self.override_timestamp,
            "approval_chain": self.approval_chain,
        }


# =============================================================================
# FAILURE MODES (LOCKED)
# =============================================================================

class FailureMode(str, Enum):
    """Canonical failure modes for risk scoring."""
    
    DEGRADE_GRACEFULLY = "DEGRADE_GRACEFULLY"  # Missing data
    ESCALATE = "ESCALATE"  # Low confidence
    FAIL_CLOSED = "FAIL_CLOSED"  # Model error


@dataclass
class FailureResponse:
    """Response to a failure condition."""
    
    mode: FailureMode
    can_emit_score: bool
    requires_escalation: bool
    message: str


FAILURE_RESPONSES: Dict[str, FailureResponse] = {
    "missing_data": FailureResponse(
        mode=FailureMode.DEGRADE_GRACEFULLY,
        can_emit_score=True,
        requires_escalation=False,
        message="Missing data — score emitted with increased uncertainty"
    ),
    "low_confidence": FailureResponse(
        mode=FailureMode.ESCALATE,
        can_emit_score=True,
        requires_escalation=True,
        message="Low confidence — score emitted with escalation flag"
    ),
    "model_error": FailureResponse(
        mode=FailureMode.FAIL_CLOSED,
        can_emit_score=False,
        requires_escalation=True,
        message="Model error — NO score emitted, immediate escalation"
    ),
}


# =============================================================================
# CANONICAL MODEL REGISTRY
# =============================================================================

# Current production model specification
CANONICAL_MODEL_V1 = CanonicalModelSpec(
    model_type=ModelType.ADDITIVE_WEIGHTED_RULES,
    model_version="chainiq_v1_maggie",
    data_version="chainiq_data_v1_2025",
)

# Alias for verification scripts
CANONICAL_MODEL_SPEC = CANONICAL_MODEL_V1

# Validate on import
CANONICAL_MODEL_V1.validate_model_type()


# =============================================================================
# INVARIANTS LIST (LOCKED)
# =============================================================================

@dataclass(frozen=True)
class Invariant:
    """A locked model invariant that must hold."""
    
    id: str
    description: str
    enforcement: str  # "runtime" or "test"


INVARIANTS: List[Invariant] = [
    Invariant(
        id="INV-RISK-001",
        description="Risk score must be in [0, 100] range",
        enforcement="runtime"
    ),
    Invariant(
        id="INV-RISK-002",
        description="Risk band must be derived from score (not predicted)",
        enforcement="runtime"
    ),
    Invariant(
        id="INV-RISK-003",
        description="Reason codes must never be empty",
        enforcement="runtime"
    ),
    Invariant(
        id="INV-RISK-004",
        description="Top factors must have at least one entry",
        enforcement="runtime"
    ),
    Invariant(
        id="INV-RISK-005",
        description="Same inputs + model_version must yield identical output",
        enforcement="test"
    ),
    Invariant(
        id="INV-RISK-006",
        description="Monotonic constraints must hold (higher risk → higher score)",
        enforcement="test"
    ),
    Invariant(
        id="INV-RISK-007",
        description="Glass-box models only at decision boundary",
        enforcement="runtime"
    ),
]


# END — Maggie (GID-10) — 🩷 PINK
