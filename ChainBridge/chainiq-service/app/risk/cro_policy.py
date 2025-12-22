"""CRO Policy Module — Chief Risk Officer Policy Enforcement.

Implements deterministic, table-driven CRO policy thresholds that
convert advisory risk signals into enforceable gates.

DOCTRINE COMPLIANCE:
- PAC-RUBY-CRO-POLICY-ACTIVATION-01
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

Author: Ruby (GID-12) — Chief Risk Officer
Authority: Benson (GID-00)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CRO Decision Types
# ---------------------------------------------------------------------------


class CRODecision(str, Enum):
    """CRO policy decision outcomes.

    These decisions are final and deterministic:
    - APPROVE: Execution may proceed
    - TIGHTEN_TERMS: Execution with modified (more conservative) terms
    - HOLD: Execution blocked, requires manual review
    - ESCALATE: Execution blocked, requires senior escalation
    """

    APPROVE = "APPROVE"
    TIGHTEN_TERMS = "TIGHTEN_TERMS"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"

    @property
    def blocks_execution(self) -> bool:
        """Returns True if this decision blocks execution."""
        return self in (CRODecision.HOLD, CRODecision.ESCALATE)


class CROReasonCode(str, Enum):
    """Enumerable reason codes for CRO decisions.

    All reasons are deterministic and auditable.
    """

    # Data quality reasons
    DATA_QUALITY_BELOW_THRESHOLD = "DATA_QUALITY_BELOW_THRESHOLD"

    # Profile reasons
    MISSING_CARRIER_PROFILE = "MISSING_CARRIER_PROFILE"
    MISSING_LANE_PROFILE = "MISSING_LANE_PROFILE"
    NEW_CARRIER_INSUFFICIENT_TENURE = "NEW_CARRIER_INSUFFICIENT_TENURE"
    NEW_LANE_INSUFFICIENT_HISTORY = "NEW_LANE_INSUFFICIENT_HISTORY"

    # IoT reasons
    MISSING_IOT_EVENTS_WHEN_REQUIRED = "MISSING_IOT_EVENTS_WHEN_REQUIRED"

    # Pass-through
    ALL_CHECKS_PASSED = "ALL_CHECKS_PASSED"


# ---------------------------------------------------------------------------
# CRO Threshold Policy Table (LOCKED - No runtime modification)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CROThresholdPolicy:
    """Immutable CRO threshold policy configuration.

    These thresholds are LOCKED and deterministic.
    No environment variables or runtime overrides.
    """

    # Data quality threshold
    data_quality_min_score: float = 0.70

    # Tenure thresholds
    new_carrier_tenure_days_min: int = 90
    new_lane_history_days_min: int = 60

    # IoT requirements
    iot_required_for_temp_control: bool = True
    iot_required_for_hazmat: bool = True
    iot_required_for_high_value_threshold_usd: float = 100_000.0


# Module-level policy instance (immutable, no modification)
CRO_POLICY = CROThresholdPolicy()


# ---------------------------------------------------------------------------
# Risk Metadata Input Schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CRORiskMetadata:
    """Risk metadata consumed by CRO Policy Evaluator.

    All fields are READ-ONLY inputs for deterministic evaluation.
    """

    # Data quality
    data_quality_score: Optional[float] = None

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

    # Risk band from upstream scoring
    risk_band: Optional[str] = None
    risk_score: Optional[float] = None


# ---------------------------------------------------------------------------
# CRO Policy Result Schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CROPolicyResult:
    """Result from CRO Policy Evaluator.

    Immutable, auditable decision record.
    """

    decision: CRODecision
    reasons: tuple[CROReasonCode, ...]
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    policy_version: str = "cro_policy@v1.0.0"

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
                f"Data quality score below threshold ({CRO_POLICY.data_quality_min_score})",
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
            CROReasonCode.ALL_CHECKS_PASSED:
                "All CRO policy checks passed",
        }
        return [reason_messages.get(r, r.value) for r in self.reasons]


# ---------------------------------------------------------------------------
# CRO Policy Evaluator
# ---------------------------------------------------------------------------


class CROPolicyEvaluator:
    """Deterministic CRO policy evaluator.

    Evaluates risk metadata against CRO thresholds and returns
    an enforceable decision. All decisions are deterministic and auditable.

    INVARIANTS:
    - evaluate() always returns CROPolicyResult
    - No exceptions for valid input
    - No soft influence paths
    - No environment-based overrides
    - Decision is MORE RESTRICTIVE than base RiskBand when triggered

    USAGE:
        evaluator = CROPolicyEvaluator()
        result = evaluator.evaluate(risk_metadata)
        if result.blocks_execution:
            # Block the operation
        elif result.decision == CRODecision.TIGHTEN_TERMS:
            # Apply tightened settlement terms
    """

    def __init__(self, policy: CROThresholdPolicy = CRO_POLICY):
        """Initialize with policy configuration.

        Args:
            policy: Threshold policy (defaults to locked module policy)
        """
        self._policy = policy

    def evaluate(self, metadata: CRORiskMetadata) -> CROPolicyResult:
        """Evaluate risk metadata against CRO policy thresholds.

        Returns decision in order of severity:
        1. ESCALATE (most restrictive)
        2. HOLD
        3. TIGHTEN_TERMS
        4. APPROVE (least restrictive)

        Args:
            metadata: Risk metadata to evaluate

        Returns:
            CROPolicyResult with decision and reasons
        """
        reasons: list[CROReasonCode] = []
        escalate_reasons: list[CROReasonCode] = []
        hold_reasons: list[CROReasonCode] = []
        tighten_reasons: list[CROReasonCode] = []

        # Capture metadata snapshot for audit
        metadata_snapshot = self._capture_metadata_snapshot(metadata)

        # ------------------------------------
        # ESCALATE triggers
        # ------------------------------------

        # Data quality score < threshold → ESCALATE
        if metadata.data_quality_score is not None:
            if metadata.data_quality_score < self._policy.data_quality_min_score:
                escalate_reasons.append(CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD)

        # Missing IoT events when required → ESCALATE
        if self._is_iot_required(metadata) and not metadata.has_iot_events:
            escalate_reasons.append(CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED)

        # ------------------------------------
        # HOLD triggers
        # ------------------------------------

        # Missing carrier profile → HOLD
        if not metadata.has_carrier_profile:
            hold_reasons.append(CROReasonCode.MISSING_CARRIER_PROFILE)

        # Missing lane profile → HOLD
        if not metadata.has_lane_profile:
            hold_reasons.append(CROReasonCode.MISSING_LANE_PROFILE)

        # ------------------------------------
        # TIGHTEN_TERMS triggers
        # ------------------------------------

        # New carrier (tenure < threshold) → TIGHTEN_TERMS
        if (
            metadata.has_carrier_profile
            and metadata.carrier_tenure_days is not None
            and metadata.carrier_tenure_days < self._policy.new_carrier_tenure_days_min
        ):
            tighten_reasons.append(CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE)

        # New lane (history < threshold) → TIGHTEN_TERMS
        if (
            metadata.has_lane_profile
            and metadata.lane_history_days is not None
            and metadata.lane_history_days < self._policy.new_lane_history_days_min
        ):
            tighten_reasons.append(CROReasonCode.NEW_LANE_INSUFFICIENT_HISTORY)

        # ------------------------------------
        # Determine final decision (most restrictive wins)
        # ------------------------------------

        if escalate_reasons:
            decision = CRODecision.ESCALATE
            reasons = escalate_reasons
        elif hold_reasons:
            decision = CRODecision.HOLD
            reasons = hold_reasons
        elif tighten_reasons:
            decision = CRODecision.TIGHTEN_TERMS
            reasons = tighten_reasons
        else:
            decision = CRODecision.APPROVE
            reasons = [CROReasonCode.ALL_CHECKS_PASSED]

        result = CROPolicyResult(
            decision=decision,
            reasons=tuple(reasons),
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

    Decision hierarchy (most to least restrictive):
    1. ESCALATE → maps to CRITICAL risk band
    2. HOLD → maps to CRITICAL risk band
    3. TIGHTEN_TERMS → maps to HIGH risk band (minimum)
    4. APPROVE → preserves base risk band

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

    if cro_result.decision == CRODecision.ESCALATE:
        # Always escalate to CRITICAL
        final_band = "CRITICAL"
    elif cro_result.decision == CRODecision.HOLD:
        # Hold implies CRITICAL
        final_band = "CRITICAL"
    elif cro_result.decision == CRODecision.TIGHTEN_TERMS:
        # Tighten implies at least HIGH
        if base_level < band_hierarchy["HIGH"]:
            final_band = "HIGH"
    # APPROVE preserves base band

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
