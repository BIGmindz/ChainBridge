"""CRO Policy Module — Chief Risk Officer Policy Enforcement.

Implements deterministic, table-driven CRO policy thresholds that
convert advisory risk signals into enforceable gates.

DOCTRINE COMPLIANCE:
- PAC-RUBY-CRO-POLICY-ACTIVATION-01 (REFINED)
- PDO Enforcement Model v1 (LOCKED)
- Zero drift tolerance
- Fail-closed semantics

DESIGN PRINCIPLES:
- Deterministic, table-driven thresholds only
- No ML model changes
- No probabilistic thresholds
- No soft influence / hints
- No environment-variable overrides
- No runtime bypass flags
- All policy decisions are PDO-bound and auditable

ChainIQ recommends. Ruby decides.

Author: Ruby (GID-05) — Chief Risk Officer / Policy Authority
Authority: Benson (GID-00)
Policy Version: CRO-POLICY-V1
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CRO Decision Types (PAC-RUBY-CRO-POLICY-ACTIVATION-01)
# ---------------------------------------------------------------------------


class CRODecision(str, Enum):
    """CRO policy decision outcomes.

    These decisions are final and deterministic:
    - ALLOW: Execution may proceed normally
    - ALLOW_WITH_CONSTRAINTS: Execution with modified (more conservative) terms
    - HOLD: Execution blocked, requires manual review
    - ESCALATE: Execution blocked, requires senior escalation
    - DENY: Execution permanently blocked
    """

    ALLOW = "ALLOW"
    ALLOW_WITH_CONSTRAINTS = "ALLOW_WITH_CONSTRAINTS"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    DENY = "DENY"

    @property
    def blocks_execution(self) -> bool:
        """Returns True if this decision blocks execution."""
        return self in (CRODecision.HOLD, CRODecision.ESCALATE, CRODecision.DENY)


class CROReasonCode(str, Enum):
    """Enumerable reason codes for CRO decisions.

    All reasons are deterministic and auditable.
    """

    # Data quality reasons
    DATA_QUALITY_BELOW_THRESHOLD = "DATA_QUALITY_BELOW_THRESHOLD"
    DATA_QUALITY_CRITICAL = "DATA_QUALITY_CRITICAL"  # < 0.60 override
    DATA_QUALITY_INSUFFICIENT_FOR_BAND = "DATA_QUALITY_INSUFFICIENT_FOR_BAND"

    # Risk band reasons
    CRITICAL_RISK_BAND = "CRITICAL_RISK_BAND"
    HIGH_RISK_BAND_REQUIRES_HOLD = "HIGH_RISK_BAND_REQUIRES_HOLD"
    MEDIUM_RISK_BAND_CONSTRAINED = "MEDIUM_RISK_BAND_CONSTRAINED"

    # Profile reasons
    MISSING_CARRIER_PROFILE = "MISSING_CARRIER_PROFILE"
    MISSING_LANE_PROFILE = "MISSING_LANE_PROFILE"
    NEW_CARRIER_INSUFFICIENT_TENURE = "NEW_CARRIER_INSUFFICIENT_TENURE"
    NEW_LANE_INSUFFICIENT_HISTORY = "NEW_LANE_INSUFFICIENT_HISTORY"

    # IoT reasons
    MISSING_IOT_EVENTS_WHEN_REQUIRED = "MISSING_IOT_EVENTS_WHEN_REQUIRED"

    # Missing metadata
    MISSING_RISK_METADATA = "MISSING_RISK_METADATA"

    # Pass-through
    ALL_CHECKS_PASSED = "ALL_CHECKS_PASSED"
    LOW_RISK_APPROVED = "LOW_RISK_APPROVED"


# ---------------------------------------------------------------------------
# CRO Threshold Policy Table (LOCKED - No runtime modification)
# PAC-RUBY-CRO-POLICY-ACTIVATION-01 Section 4.2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CROThresholdPolicy:
    """Immutable CRO threshold policy configuration.

    These thresholds are LOCKED and deterministic.
    No environment variables or runtime overrides.

    CRO_POLICY_THRESHOLDS:
      LOW:      data_quality >= 0.70 → ALLOW
      MEDIUM:   data_quality >= 0.75 → ALLOW_WITH_CONSTRAINTS
      HIGH:     data_quality >= 0.80 → HOLD
      CRITICAL: ALWAYS → ESCALATE

    DATA_QUALITY_OVERRIDE:
      if data_quality < 0.60 → ESCALATE (regardless of band)
    """

    # Data quality thresholds per risk band
    data_quality_low_band_min: float = 0.70
    data_quality_medium_band_min: float = 0.75
    data_quality_high_band_min: float = 0.80

    # Critical override threshold
    data_quality_critical_override: float = 0.60

    # Tenure thresholds (retained from previous implementation)
    new_carrier_tenure_days_min: int = 90
    new_lane_history_days_min: int = 60

    # IoT requirements
    iot_required_for_temp_control: bool = True
    iot_required_for_hazmat: bool = True
    iot_required_for_high_value_threshold_usd: float = 100_000.0


# Module-level policy instance (immutable, no modification)
CRO_POLICY = CROThresholdPolicy()

# Policy version identifier
CRO_POLICY_VERSION = "CRO-POLICY-V1"


# ---------------------------------------------------------------------------
# Risk Metadata Input Schema (PAC Section 4.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CRORiskMetadata:
    """Risk metadata consumed by CRO Policy Evaluator.

    MANDATORY INPUT (PAC Section 4.1):
    - risk_score: float (0–1 normalized)
    - risk_band: LOW | MEDIUM | HIGH | CRITICAL
    - confidence: float (0–1)
    - top_factors: list
    - model_version: string
    - assessed_at: timestamp
    - data_quality_score: float (0–1)

    Absence of RiskMetadata → FAIL CLOSED
    """

    # Core risk fields (MANDATORY)
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    data_quality_score: Optional[float] = None

    # Extended risk fields
    confidence: Optional[float] = None
    top_factors: Optional[list[str]] = None
    model_version: Optional[str] = None
    assessed_at: Optional[str] = None

    # Carrier profile presence and attributes
    has_carrier_profile: bool = True
    carrier_tenure_days: Optional[int] = None

    # Lane profile presence and attributes
    has_lane_profile: bool = True
    lane_history_days: Optional[int] = None

    # IoT data
    has_iot_events: bool = True
    iot_event_count: int = 0

    # Shipment characteristics (for IoT requirement evaluation)
    is_temp_control: bool = False
    is_hazmat: bool = False
    value_usd: float = 0.0


# ---------------------------------------------------------------------------
# CRO Policy Result Schema (PAC Section 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskPolicyDecision:
    """Risk Policy Decision output contract.

    Ruby MUST emit this structure (PAC Section 5).
    This is the signed, auditable policy decision.

    Attributes:
        policy_decision: ALLOW | ALLOW_WITH_CONSTRAINTS | HOLD | ESCALATE | DENY
        policy_reason: Human-readable reason string
        applied_threshold: Threshold rule that was applied
        risk_band: The risk band from input
        data_quality_score: The data quality score from input
        issued_by: Always "Ruby (GID-05)"
        issued_at: UTC timestamp
        policy_version: Always "CRO-POLICY-V1"
    """

    policy_decision: CRODecision
    policy_reason: str
    applied_threshold: str
    risk_band: Optional[str]
    data_quality_score: Optional[float]
    issued_by: str = "Ruby (GID-05)"
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    policy_version: str = CRO_POLICY_VERSION

    @property
    def blocks_execution(self) -> bool:
        """Returns True if execution should be blocked."""
        return self.policy_decision.blocks_execution

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for PDO embedding."""
        return {
            "policy_decision": self.policy_decision.value,
            "policy_reason": self.policy_reason,
            "applied_threshold": self.applied_threshold,
            "risk_band": self.risk_band,
            "data_quality_score": self.data_quality_score,
            "issued_by": self.issued_by,
            "issued_at": self.issued_at,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class CROPolicyResult:
    """Full result from CRO Policy Evaluator.

    Immutable, auditable decision record with full context.
    """

    decision: CRODecision
    reasons: tuple[CROReasonCode, ...]
    policy_decision: RiskPolicyDecision
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    policy_version: str = CRO_POLICY_VERSION

    # Original risk band (before CRO override)
    original_risk_band: Optional[str] = None

    # Metadata for audit
    metadata_snapshot: Optional[dict[str, Any]] = None

    @property
    def blocks_execution(self) -> bool:
        """Returns True if execution should be blocked."""
        return self.decision.blocks_execution

    @property
    def human_readable_reasons(self) -> list[str]:
        """Return human-readable reason strings."""
        reason_messages = {
            CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD:
                "Data quality score below threshold for risk band",
            CROReasonCode.DATA_QUALITY_CRITICAL:
                f"Data quality score below critical threshold ({CRO_POLICY.data_quality_critical_override})",
            CROReasonCode.DATA_QUALITY_INSUFFICIENT_FOR_BAND:
                "Data quality insufficient for automated decision at this risk level",
            CROReasonCode.CRITICAL_RISK_BAND:
                "CRITICAL risk band always requires escalation",
            CROReasonCode.HIGH_RISK_BAND_REQUIRES_HOLD:
                "HIGH risk band requires manual review (HOLD)",
            CROReasonCode.MEDIUM_RISK_BAND_CONSTRAINED:
                "MEDIUM risk band requires constrained execution",
            CROReasonCode.MISSING_CARRIER_PROFILE:
                "Carrier profile is missing",
            CROReasonCode.MISSING_LANE_PROFILE:
                "Lane profile is missing",
            CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE:
                f"New carrier with tenure < {CRO_POLICY.new_carrier_tenure_days_min} days",
            CROReasonCode.NEW_LANE_INSUFFICIENT_HISTORY:
                f"New lane with history < {CRO_POLICY.new_lane_history_days_min} days",
            CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED:
                "IoT events missing when required for shipment type",
            CROReasonCode.MISSING_RISK_METADATA:
                "Risk metadata is missing - fail closed",
            CROReasonCode.ALL_CHECKS_PASSED:
                "All CRO policy checks passed",
            CROReasonCode.LOW_RISK_APPROVED:
                "LOW risk band with sufficient data quality - approved",
        }
        return [reason_messages.get(r, r.value) for r in self.reasons]


# ---------------------------------------------------------------------------
# CRO Policy Evaluator (PAC Section 4.2 & 4.3)
# ---------------------------------------------------------------------------


class CROPolicyEvaluator:
    """Deterministic CRO policy evaluator.

    ChainIQ recommends. Ruby decides.

    Evaluates risk metadata against CRO thresholds and returns
    an enforceable decision. All decisions are deterministic and auditable.

    CRO_POLICY_THRESHOLDS (PAC Section 4.2):
      LOW:      data_quality >= 0.70 → ALLOW
      MEDIUM:   data_quality >= 0.75 → ALLOW_WITH_CONSTRAINTS
      HIGH:     data_quality >= 0.80 → HOLD
      CRITICAL: ALWAYS → ESCALATE

    DATA_QUALITY_OVERRIDE (PAC Section 4.3):
      if data_quality < 0.60 → ESCALATE (regardless of band)

    FAIL-CLOSED:
      Absence of RiskMetadata → ESCALATE

    INVARIANTS:
    - evaluate() always returns CROPolicyResult
    - No exceptions for valid input
    - No soft influence paths
    - No environment-based overrides
    - Decision is MORE RESTRICTIVE than base RiskBand when triggered
    """

    def __init__(self, policy: CROThresholdPolicy = CRO_POLICY):
        """Initialize with policy configuration.

        Args:
            policy: Threshold policy (defaults to locked module policy)
        """
        self._policy = policy

    def evaluate(self, metadata: CRORiskMetadata) -> CROPolicyResult:
        """Evaluate risk metadata against CRO policy thresholds.

        PAC Section 4.2 - CRO THRESHOLD TABLE:
        - LOW + data_quality >= 0.70 → ALLOW
        - MEDIUM + data_quality >= 0.75 → ALLOW_WITH_CONSTRAINTS
        - HIGH + data_quality >= 0.80 → HOLD
        - CRITICAL → ESCALATE (always)

        PAC Section 4.3 - DATA QUALITY OVERRIDE:
        - data_quality < 0.60 → ESCALATE (regardless of band)

        Args:
            metadata: Risk metadata to evaluate

        Returns:
            CROPolicyResult with decision and reasons
        """
        reasons: list[CROReasonCode] = []

        # Capture metadata snapshot for audit
        metadata_snapshot = self._capture_metadata_snapshot(metadata)

        # ------------------------------------
        # FAIL-CLOSED: Missing risk metadata
        # ------------------------------------
        if metadata.risk_band is None or metadata.data_quality_score is None:
            return self._build_fail_closed_result(
                metadata=metadata,
                reason=CROReasonCode.MISSING_RISK_METADATA,
                metadata_snapshot=metadata_snapshot,
            )

        risk_band = metadata.risk_band.upper()
        data_quality = metadata.data_quality_score

        # ------------------------------------
        # DATA QUALITY OVERRIDE (PAC Section 4.3)
        # if data_quality < 0.60 → ESCALATE
        # ------------------------------------
        if data_quality < self._policy.data_quality_critical_override:
            return self._build_result(
                decision=CRODecision.ESCALATE,
                reasons=[CROReasonCode.DATA_QUALITY_CRITICAL],
                metadata=metadata,
                applied_threshold=f"data_quality < {self._policy.data_quality_critical_override}",
                metadata_snapshot=metadata_snapshot,
            )

        # ------------------------------------
        # BAND-BASED THRESHOLDS (PAC Section 4.2)
        # ------------------------------------

        if risk_band == "CRITICAL":
            # CRITICAL → ESCALATE (always)
            return self._build_result(
                decision=CRODecision.ESCALATE,
                reasons=[CROReasonCode.CRITICAL_RISK_BAND],
                metadata=metadata,
                applied_threshold="CRITICAL band → ESCALATE (always)",
                metadata_snapshot=metadata_snapshot,
            )

        if risk_band == "HIGH":
            # HIGH + data_quality >= 0.80 → HOLD
            if data_quality >= self._policy.data_quality_high_band_min:
                return self._build_result(
                    decision=CRODecision.HOLD,
                    reasons=[CROReasonCode.HIGH_RISK_BAND_REQUIRES_HOLD],
                    metadata=metadata,
                    applied_threshold=f"HIGH band + data_quality >= {self._policy.data_quality_high_band_min} → HOLD",
                    metadata_snapshot=metadata_snapshot,
                )
            else:
                # HIGH band but data quality below threshold → ESCALATE
                return self._build_result(
                    decision=CRODecision.ESCALATE,
                    reasons=[CROReasonCode.DATA_QUALITY_INSUFFICIENT_FOR_BAND],
                    metadata=metadata,
                    applied_threshold=f"HIGH band + data_quality < {self._policy.data_quality_high_band_min} → ESCALATE",
                    metadata_snapshot=metadata_snapshot,
                )

        if risk_band == "MEDIUM":
            # MEDIUM + data_quality >= 0.75 → ALLOW_WITH_CONSTRAINTS
            if data_quality >= self._policy.data_quality_medium_band_min:
                # Check for additional constraints
                constraint_reasons = self._check_constraints(metadata)
                if constraint_reasons:
                    reasons.extend(constraint_reasons)
                reasons.append(CROReasonCode.MEDIUM_RISK_BAND_CONSTRAINED)
                return self._build_result(
                    decision=CRODecision.ALLOW_WITH_CONSTRAINTS,
                    reasons=reasons,
                    metadata=metadata,
                    applied_threshold=f"MEDIUM band + data_quality >= {self._policy.data_quality_medium_band_min} → ALLOW_WITH_CONSTRAINTS",
                    metadata_snapshot=metadata_snapshot,
                )
            else:
                # MEDIUM band but data quality below threshold → HOLD
                return self._build_result(
                    decision=CRODecision.HOLD,
                    reasons=[CROReasonCode.DATA_QUALITY_INSUFFICIENT_FOR_BAND],
                    metadata=metadata,
                    applied_threshold=f"MEDIUM band + data_quality < {self._policy.data_quality_medium_band_min} → HOLD",
                    metadata_snapshot=metadata_snapshot,
                )

        if risk_band == "LOW":
            # LOW + data_quality >= 0.70 → ALLOW
            if data_quality >= self._policy.data_quality_low_band_min:
                return self._build_result(
                    decision=CRODecision.ALLOW,
                    reasons=[CROReasonCode.LOW_RISK_APPROVED],
                    metadata=metadata,
                    applied_threshold=f"LOW band + data_quality >= {self._policy.data_quality_low_band_min} → ALLOW",
                    metadata_snapshot=metadata_snapshot,
                )
            else:
                # LOW band but data quality below threshold → ALLOW_WITH_CONSTRAINTS
                return self._build_result(
                    decision=CRODecision.ALLOW_WITH_CONSTRAINTS,
                    reasons=[CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD],
                    metadata=metadata,
                    applied_threshold=f"LOW band + data_quality < {self._policy.data_quality_low_band_min} → ALLOW_WITH_CONSTRAINTS",
                    metadata_snapshot=metadata_snapshot,
                )

        # Unknown band → fail closed
        return self._build_fail_closed_result(
            metadata=metadata,
            reason=CROReasonCode.MISSING_RISK_METADATA,
            metadata_snapshot=metadata_snapshot,
        )

    def _check_constraints(self, metadata: CRORiskMetadata) -> list[CROReasonCode]:
        """Check for constraint-triggering conditions.

        Returns list of reasons that warrant constrained execution.
        """
        constraints: list[CROReasonCode] = []

        # New carrier (tenure < threshold)
        if (
            metadata.has_carrier_profile
            and metadata.carrier_tenure_days is not None
            and metadata.carrier_tenure_days < self._policy.new_carrier_tenure_days_min
        ):
            constraints.append(CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE)

        # New lane (history < threshold)
        if (
            metadata.has_lane_profile
            and metadata.lane_history_days is not None
            and metadata.lane_history_days < self._policy.new_lane_history_days_min
        ):
            constraints.append(CROReasonCode.NEW_LANE_INSUFFICIENT_HISTORY)

        # Missing IoT when required
        if self._is_iot_required(metadata) and not metadata.has_iot_events:
            constraints.append(CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED)

        return constraints

    def _build_result(
        self,
        decision: CRODecision,
        reasons: list[CROReasonCode],
        metadata: CRORiskMetadata,
        applied_threshold: str,
        metadata_snapshot: dict[str, Any],
    ) -> CROPolicyResult:
        """Build a CROPolicyResult with RiskPolicyDecision."""
        policy_decision = RiskPolicyDecision(
            policy_decision=decision,
            policy_reason="; ".join(r.value for r in reasons),
            applied_threshold=applied_threshold,
            risk_band=metadata.risk_band,
            data_quality_score=metadata.data_quality_score,
        )

        result = CROPolicyResult(
            decision=decision,
            reasons=tuple(reasons),
            policy_decision=policy_decision,
            original_risk_band=metadata.risk_band,
            metadata_snapshot=metadata_snapshot,
        )

        # Log the evaluation for audit
        self._log_evaluation(result)

        return result

    def _build_fail_closed_result(
        self,
        metadata: CRORiskMetadata,
        reason: CROReasonCode,
        metadata_snapshot: dict[str, Any],
    ) -> CROPolicyResult:
        """Build a fail-closed ESCALATE result."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.ESCALATE,
            policy_reason="Insufficient data quality for automated decision",
            applied_threshold="FAIL_CLOSED: missing required metadata",
            risk_band=metadata.risk_band,
            data_quality_score=metadata.data_quality_score,
        )

        result = CROPolicyResult(
            decision=CRODecision.ESCALATE,
            reasons=(reason,),
            policy_decision=policy_decision,
            original_risk_band=metadata.risk_band,
            metadata_snapshot=metadata_snapshot,
        )

        # Log the evaluation for audit
        self._log_evaluation(result)

        return result

    def _is_iot_required(self, metadata: CRORiskMetadata) -> bool:
        """Determine if IoT events are required for this shipment.

        IoT is required when:
        - Temperature control is required
        - Hazmat shipment
        - High value shipment above threshold

        Args:
            metadata: Risk metadata to evaluate

        Returns:
            True if IoT events are required
        """
        if self._policy.iot_required_for_temp_control and metadata.is_temp_control:
            return True
        if self._policy.iot_required_for_hazmat and metadata.is_hazmat:
            return True
        if metadata.value_usd >= self._policy.iot_required_for_high_value_threshold_usd:
            return True
        return False

    def _capture_metadata_snapshot(self, metadata: CRORiskMetadata) -> dict[str, Any]:
        """Capture metadata snapshot for audit."""
        return {
            "data_quality_score": metadata.data_quality_score,
            "has_carrier_profile": metadata.has_carrier_profile,
            "carrier_tenure_days": metadata.carrier_tenure_days,
            "has_lane_profile": metadata.has_lane_profile,
            "lane_history_days": metadata.lane_history_days,
            "has_iot_events": metadata.has_iot_events,
            "iot_event_count": metadata.iot_event_count,
            "is_temp_control": metadata.is_temp_control,
            "is_hazmat": metadata.is_hazmat,
            "value_usd": metadata.value_usd,
            "risk_band": metadata.risk_band,
            "risk_score": metadata.risk_score,
        }

    def _log_evaluation(self, result: CROPolicyResult) -> None:
        """Log CRO evaluation for audit trail."""
        log_data = {
            "event": "cro_policy_evaluation",
            "decision": result.decision.value,
            "reasons": [r.value for r in result.reasons],
            "blocks_execution": result.blocks_execution,
            "policy_version": result.policy_version,
            "original_risk_band": result.original_risk_band,
            "evaluated_at": result.evaluated_at,
            "metadata_snapshot": result.metadata_snapshot,
        }

        if result.blocks_execution:
            logger.warning("CRO policy blocks execution: %s", log_data)
        else:
            logger.info("CRO policy evaluation: %s", log_data)


# ---------------------------------------------------------------------------
# Module-level singleton for convenience
# ---------------------------------------------------------------------------

_evaluator = CROPolicyEvaluator()


def evaluate_cro_policy(metadata: CRORiskMetadata) -> CROPolicyResult:
    """Evaluate CRO policy using module-level evaluator.

    Convenience function for the common case.

    Args:
        metadata: Risk metadata to evaluate

    Returns:
        CROPolicyResult with decision and reasons
    """
    return _evaluator.evaluate(metadata)


# ---------------------------------------------------------------------------
# CRO Override Logic
# ---------------------------------------------------------------------------


def apply_cro_override(
    base_risk_band: str,
    cro_result: CROPolicyResult,
) -> tuple[str, CRODecision]:
    """Apply CRO override to base risk band.

    CRO decision overrides base RiskBand if more restrictive.

    Decision hierarchy (most to least restrictive) per PAC Section 4.2:
    1. DENY → maps to CRITICAL risk band (blocks execution)
    2. ESCALATE → maps to CRITICAL risk band (manual review)
    3. HOLD → maps to CRITICAL risk band (pending additional info)
    4. ALLOW_WITH_CONSTRAINTS → maps to HIGH risk band (minimum)
    5. ALLOW → preserves base risk band

    Args:
        base_risk_band: Risk band from upstream scoring
        cro_result: CRO policy evaluation result

    Returns:
        Tuple of (final_risk_band, cro_decision)
    """
    # Risk band hierarchy for comparison
    band_hierarchy = {
        "LOW": 0,
        "MEDIUM": 1,
        "HIGH": 2,
        "CRITICAL": 3,
    }

    base_level = band_hierarchy.get(base_risk_band.upper(), 0)
    final_band = base_risk_band.upper()

    if cro_result.decision == CRODecision.DENY:
        # Deny implies CRITICAL (hard block)
        final_band = "CRITICAL"
    elif cro_result.decision == CRODecision.ESCALATE:
        # Always escalate to CRITICAL
        final_band = "CRITICAL"
    elif cro_result.decision == CRODecision.HOLD:
        # Hold implies CRITICAL
        final_band = "CRITICAL"
    elif cro_result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS:
        # Constrained implies at least HIGH
        if base_level < band_hierarchy["HIGH"]:
            final_band = "HIGH"
    # ALLOW preserves base band

    return final_band, cro_result.decision


# ---------------------------------------------------------------------------
# Factory for creating CRORiskMetadata from various sources
# ---------------------------------------------------------------------------


def build_cro_metadata_from_pdo(pdo_data: Optional[dict]) -> CRORiskMetadata:
    """Build CRORiskMetadata from PDO data.

    Extracts relevant fields from PDO for CRO evaluation.

    Args:
        pdo_data: PDO dictionary (may contain risk fields)

    Returns:
        CRORiskMetadata for evaluation
    """
    if pdo_data is None:
        return CRORiskMetadata()

    # Extract risk metadata fields if present
    return CRORiskMetadata(
        data_quality_score=pdo_data.get("data_quality_score"),
        has_carrier_profile=pdo_data.get("has_carrier_profile", True),
        carrier_tenure_days=pdo_data.get("carrier_tenure_days"),
        has_lane_profile=pdo_data.get("has_lane_profile", True),
        lane_history_days=pdo_data.get("lane_history_days"),
        has_iot_events=pdo_data.get("has_iot_events", True),
        iot_event_count=pdo_data.get("iot_event_count", 0),
        is_temp_control=pdo_data.get("is_temp_control", False),
        is_hazmat=pdo_data.get("is_hazmat", False),
        value_usd=pdo_data.get("value_usd", 0.0),
        risk_band=pdo_data.get("risk_band"),
        risk_score=pdo_data.get("risk_score"),
    )


def build_cro_metadata_from_risk_response(
    risk_response: dict,
    carrier_tenure_days: Optional[int] = None,
    lane_history_days: Optional[int] = None,
    has_iot_events: bool = True,
    iot_event_count: int = 0,
    shipment_features: Optional[dict] = None,
) -> CRORiskMetadata:
    """Build CRORiskMetadata from ChainIQ risk response.

    Args:
        risk_response: Response from ChainIQ risk scoring
        carrier_tenure_days: Carrier tenure from profile lookup
        lane_history_days: Lane history from profile lookup
        has_iot_events: Whether IoT events are available
        iot_event_count: Count of IoT events
        shipment_features: Shipment characteristics

    Returns:
        CRORiskMetadata for evaluation
    """
    features = shipment_features or {}

    return CRORiskMetadata(
        data_quality_score=risk_response.get("data_quality_score"),
        has_carrier_profile=carrier_tenure_days is not None,
        carrier_tenure_days=carrier_tenure_days,
        has_lane_profile=lane_history_days is not None,
        lane_history_days=lane_history_days,
        has_iot_events=has_iot_events,
        iot_event_count=iot_event_count,
        is_temp_control=features.get("is_temp_control", False),
        is_hazmat=features.get("is_hazmat", False),
        value_usd=features.get("value_usd", 0.0),
        risk_band=risk_response.get("risk_band"),
        risk_score=risk_response.get("risk_score"),
    )
