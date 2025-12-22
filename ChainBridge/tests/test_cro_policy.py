"""CRO Policy Enforcement Tests.

Tests the CRO Policy Evaluator and enforcement integration per
PAC-RUBY-CRO-POLICY-ACTIVATION-01 (REFINED).

Requirements validated per PAC Section 4.2 (CRO THRESHOLD TABLE):
1. LOW + data_quality >= 0.70 → ALLOW
2. MEDIUM + data_quality >= 0.75 → ALLOW_WITH_CONSTRAINTS
3. HIGH + data_quality >= 0.80 → HOLD
4. CRITICAL → ESCALATE (always)
5. Data quality < 0.60 override → ESCALATE (PAC Section 4.3)
6. CRO override beats RiskBand (more restrictive wins)
7. CRO decision included in RiskPolicyDecision (PAC Section 5)
8. Fail-closed semantics for missing metadata

DOCTRINE: PAC-RUBY-CRO-POLICY-ACTIVATION-01 (REFINED)
- Band-based threshold enforcement
- Deterministic, table-driven thresholds only
- Fail-closed semantics
- All decisions are PDO-bound and auditable

Author: Ruby (GID-05) — Chief Risk Officer
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pytest

# Import from chainiq-service
import sys
from pathlib import Path

# Add chainiq-service to path for imports
chainiq_path = Path(__file__).parent.parent / "chainiq-service"
sys.path.insert(0, str(chainiq_path))

from app.risk.cro_policy import (
    CRODecision,
    CROPolicyEvaluator,
    CROPolicyResult,
    CRORiskMetadata,
    CROReasonCode,
    CROThresholdPolicy,
    CRO_POLICY,
    RiskPolicyDecision,
    evaluate_cro_policy,
    apply_cro_override,
    build_cro_metadata_from_pdo,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evaluator() -> CROPolicyEvaluator:
    """Create a CRO policy evaluator with default policy."""
    return CROPolicyEvaluator()


@pytest.fixture
def metadata_low_risk_good_quality() -> CRORiskMetadata:
    """Create metadata for LOW risk band with good data quality."""
    return CRORiskMetadata(
        data_quality_score=0.85,
        has_carrier_profile=True,
        carrier_tenure_days=200,
        has_lane_profile=True,
        lane_history_days=120,
        has_iot_events=True,
        iot_event_count=5,
        is_temp_control=False,
        is_hazmat=False,
        value_usd=50000.0,
        risk_band="LOW",
        risk_score=0.25,
    )


# ---------------------------------------------------------------------------
# CRO Policy Threshold Tests
# ---------------------------------------------------------------------------


class TestCROThresholdPolicy:
    """Tests for CRO threshold policy configuration."""

    def test_policy_is_immutable(self):
        """CRO policy is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            CRO_POLICY.data_quality_min_score = 0.5

    def test_default_thresholds_match_pac(self):
        """Default thresholds match PAC Section 4.2 specification."""
        # Band-specific thresholds
        assert CRO_POLICY.data_quality_low_band_min == 0.70
        assert CRO_POLICY.data_quality_medium_band_min == 0.75
        assert CRO_POLICY.data_quality_high_band_min == 0.80
        # Critical override
        assert CRO_POLICY.data_quality_critical_override == 0.60
        # Constraint thresholds
        assert CRO_POLICY.new_carrier_tenure_days_min == 90
        assert CRO_POLICY.new_lane_history_days_min == 60
        # IoT requirements
        assert CRO_POLICY.iot_required_for_temp_control is True
        assert CRO_POLICY.iot_required_for_hazmat is True
        assert CRO_POLICY.iot_required_for_high_value_threshold_usd == 100_000.0


# ---------------------------------------------------------------------------
# CRO Decision Tests
# ---------------------------------------------------------------------------


class TestCRODecision:
    """Tests for CRO decision enum."""

    def test_decision_blocks_execution(self):
        """HOLD, ESCALATE, and DENY block execution."""
        assert CRODecision.DENY.blocks_execution is True
        assert CRODecision.ESCALATE.blocks_execution is True
        assert CRODecision.HOLD.blocks_execution is True
        assert CRODecision.ALLOW_WITH_CONSTRAINTS.blocks_execution is False
        assert CRODecision.ALLOW.blocks_execution is False

    def test_decision_values(self):
        """Decision values match PAC specification."""
        assert CRODecision.ALLOW.value == "ALLOW"
        assert CRODecision.ALLOW_WITH_CONSTRAINTS.value == "ALLOW_WITH_CONSTRAINTS"
        assert CRODecision.HOLD.value == "HOLD"
        assert CRODecision.ESCALATE.value == "ESCALATE"
        assert CRODecision.DENY.value == "DENY"


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — LOW Band (PAC Section 4.2)
# ---------------------------------------------------------------------------


class TestCROLowBand:
    """Tests for LOW risk band evaluation per PAC Section 4.2."""

    def test_low_band_high_quality_allows(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: LOW + data_quality >= 0.70 → ALLOW."""
        metadata = CRORiskMetadata(
            data_quality_score=0.85,
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW
        assert CROReasonCode.LOW_RISK_APPROVED in result.reasons
        assert result.blocks_execution is False

    def test_low_band_at_threshold_allows(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: LOW + data_quality == 0.70 → ALLOW (boundary)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.70,
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW

    def test_low_band_below_threshold_constrains(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: LOW + data_quality < 0.70 → ALLOW_WITH_CONSTRAINTS."""
        metadata = CRORiskMetadata(
            data_quality_score=0.65,  # Below 0.70, above 0.60
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS
        assert CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD in result.reasons


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — MEDIUM Band (PAC Section 4.2)
# ---------------------------------------------------------------------------


class TestCROMediumBand:
    """Tests for MEDIUM risk band evaluation per PAC Section 4.2."""

    def test_medium_band_high_quality_allows_constrained(
        self, evaluator: CROPolicyEvaluator
    ):
        """PAC 4.2: MEDIUM + data_quality >= 0.75 → ALLOW_WITH_CONSTRAINTS."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS
        assert CROReasonCode.MEDIUM_RISK_BAND_CONSTRAINED in result.reasons
        assert result.blocks_execution is False

    def test_medium_band_at_threshold_allows_constrained(
        self, evaluator: CROPolicyEvaluator
    ):
        """PAC 4.2: MEDIUM + data_quality == 0.75 → ALLOW_WITH_CONSTRAINTS."""
        metadata = CRORiskMetadata(
            data_quality_score=0.75,
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS

    def test_medium_band_below_threshold_holds(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: MEDIUM + data_quality < 0.75 → HOLD."""
        metadata = CRORiskMetadata(
            data_quality_score=0.72,  # Below 0.75, above 0.60
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD
        assert CROReasonCode.DATA_QUALITY_INSUFFICIENT_FOR_BAND in result.reasons
        assert result.blocks_execution is True


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — HIGH Band (PAC Section 4.2)
# ---------------------------------------------------------------------------


class TestCROHighBand:
    """Tests for HIGH risk band evaluation per PAC Section 4.2."""

    def test_high_band_high_quality_holds(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: HIGH + data_quality >= 0.80 → HOLD."""
        metadata = CRORiskMetadata(
            data_quality_score=0.85,
            risk_band="HIGH",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD
        assert CROReasonCode.HIGH_RISK_BAND_REQUIRES_HOLD in result.reasons
        assert result.blocks_execution is True

    def test_high_band_at_threshold_holds(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: HIGH + data_quality == 0.80 → HOLD (boundary)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="HIGH",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD

    def test_high_band_below_threshold_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: HIGH + data_quality < 0.80 → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.75,  # Below 0.80, above 0.60
            risk_band="HIGH",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.DATA_QUALITY_INSUFFICIENT_FOR_BAND in result.reasons
        assert result.blocks_execution is True


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — CRITICAL Band (PAC Section 4.2)
# ---------------------------------------------------------------------------


class TestCROCriticalBand:
    """Tests for CRITICAL risk band evaluation per PAC Section 4.2."""

    def test_critical_band_always_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC 4.2: CRITICAL → ESCALATE (always, regardless of data quality)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.95,  # Even with perfect quality
            risk_band="CRITICAL",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.CRITICAL_RISK_BAND in result.reasons
        assert result.blocks_execution is True

    def test_critical_band_with_low_quality_escalates(
        self, evaluator: CROPolicyEvaluator
    ):
        """PAC 4.2: CRITICAL + low quality → ESCALATE (still critical reason)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.55,  # Below critical override
            risk_band="CRITICAL",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        # Data quality override fires first, but decision is same
        assert result.decision == CRODecision.ESCALATE
        assert result.blocks_execution is True


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — Data Quality Override (PAC Section 4.3)
# ---------------------------------------------------------------------------


class TestCRODataQualityOverride:
    """Tests for data quality critical override per PAC Section 4.3."""

    def test_data_quality_below_critical_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC 4.3: data_quality < 0.60 → ESCALATE (regardless of band)."""
        # Even LOW band with very low quality should escalate
        metadata = CRORiskMetadata(
            data_quality_score=0.55,
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.DATA_QUALITY_CRITICAL in result.reasons
        assert result.blocks_execution is True

    def test_data_quality_at_critical_boundary_no_override(
        self, evaluator: CROPolicyEvaluator
    ):
        """PAC 4.3: data_quality == 0.60 should NOT trigger critical override."""
        metadata = CRORiskMetadata(
            data_quality_score=0.60,
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        # Should proceed to band evaluation (LOW + 0.60 < 0.70 → ALLOW_WITH_CONSTRAINTS)
        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS
        assert CROReasonCode.DATA_QUALITY_CRITICAL not in result.reasons

    def test_data_quality_override_beats_any_band(self, evaluator: CROPolicyEvaluator):
        """PAC 4.3: Critical override applies to ALL bands."""
        for band in ["LOW", "MEDIUM", "HIGH"]:
            metadata = CRORiskMetadata(
                data_quality_score=0.50,  # Below 0.60
                risk_band=band,
                has_carrier_profile=True,
                carrier_tenure_days=200,
                has_lane_profile=True,
                lane_history_days=120,
                has_iot_events=True,
            )

            result = evaluator.evaluate(metadata)

            assert result.decision == CRODecision.ESCALATE
            assert CROReasonCode.DATA_QUALITY_CRITICAL in result.reasons


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — Fail-Closed Semantics
# ---------------------------------------------------------------------------


class TestCROFailClosed:
    """Tests for fail-closed semantics."""

    def test_missing_risk_band_escalates(self, evaluator: CROPolicyEvaluator):
        """FAIL-CLOSED: Missing risk_band → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            risk_band=None,  # Missing
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.MISSING_RISK_METADATA in result.reasons
        assert result.blocks_execution is True

    def test_missing_data_quality_escalates(self, evaluator: CROPolicyEvaluator):
        """FAIL-CLOSED: Missing data_quality_score → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=None,  # Missing
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.MISSING_RISK_METADATA in result.reasons

    def test_unknown_band_escalates(self, evaluator: CROPolicyEvaluator):
        """FAIL-CLOSED: Unknown risk band → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            risk_band="INVALID_BAND",  # Unknown
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — Constraints (Additional factors)
# ---------------------------------------------------------------------------


class TestCROConstraints:
    """Tests for constraint-triggering conditions."""

    def test_new_carrier_adds_constraint(self, evaluator: CROPolicyEvaluator):
        """New carrier (tenure < 90 days) adds constraint to decision."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=60,  # Below 90 day threshold
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS
        assert CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE in result.reasons

    def test_new_lane_adds_constraint(self, evaluator: CROPolicyEvaluator):
        """New lane (history < 60 days) adds constraint to decision."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=30,  # Below 60 day threshold
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS
        assert CROReasonCode.NEW_LANE_INSUFFICIENT_HISTORY in result.reasons

    def test_missing_iot_for_temp_control_adds_constraint(
        self, evaluator: CROPolicyEvaluator
    ):
        """Missing IoT for temp control adds constraint."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=False,  # Missing IoT
            is_temp_control=True,  # Requires IoT
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ALLOW_WITH_CONSTRAINTS
        assert CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED in result.reasons


# ---------------------------------------------------------------------------
# RiskPolicyDecision Tests (PAC Section 5)
# ---------------------------------------------------------------------------


class TestRiskPolicyDecision:
    """Tests for RiskPolicyDecision output contract per PAC Section 5."""

    def test_policy_decision_included_in_result(self, evaluator: CROPolicyEvaluator):
        """CROPolicyResult includes RiskPolicyDecision."""
        metadata = CRORiskMetadata(
            data_quality_score=0.85,
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.policy_decision is not None
        assert isinstance(result.policy_decision, RiskPolicyDecision)
        assert result.policy_decision.policy_decision == CRODecision.ALLOW
        assert result.policy_decision.risk_band == "LOW"
        assert result.policy_decision.data_quality_score == 0.85

    def test_policy_decision_to_dict(self, evaluator: CROPolicyEvaluator):
        """RiskPolicyDecision.to_dict() produces correct structure."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="HIGH",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)
        pd_dict = result.policy_decision.to_dict()

        assert "policy_decision" in pd_dict
        assert "policy_reason" in pd_dict
        assert "applied_threshold" in pd_dict
        assert "risk_band" in pd_dict
        assert "data_quality_score" in pd_dict
        assert "issued_at" in pd_dict
        assert pd_dict["policy_decision"] == "HOLD"


# ---------------------------------------------------------------------------
# CRO Override Tests
# ---------------------------------------------------------------------------


class TestCROOverride:
    """Tests for CRO override logic (more restrictive band wins)."""

    def test_deny_overrides_any_band(self):
        """PAC: CRO DENY overrides any risk band to CRITICAL."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.DENY,
            policy_reason="test",
            applied_threshold="test",
            risk_band="LOW",
            data_quality_score=0.5,
        )
        cro_result = CROPolicyResult(
            decision=CRODecision.DENY,
            reasons=(CROReasonCode.DATA_QUALITY_CRITICAL,),
            policy_decision=policy_decision,
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "CRITICAL"
        assert decision == CRODecision.DENY

    def test_escalate_overrides_low_band(self):
        """PAC: CRO ESCALATE overrides LOW risk band to CRITICAL."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.ESCALATE,
            policy_reason="test",
            applied_threshold="test",
            risk_band="LOW",
            data_quality_score=0.5,
        )
        cro_result = CROPolicyResult(
            decision=CRODecision.ESCALATE,
            reasons=(CROReasonCode.DATA_QUALITY_CRITICAL,),
            policy_decision=policy_decision,
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "CRITICAL"
        assert decision == CRODecision.ESCALATE

    def test_hold_overrides_medium_band(self):
        """PAC: CRO HOLD overrides MEDIUM risk band to CRITICAL."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.HOLD,
            policy_reason="test",
            applied_threshold="test",
            risk_band="MEDIUM",
            data_quality_score=0.8,
        )
        cro_result = CROPolicyResult(
            decision=CRODecision.HOLD,
            reasons=(CROReasonCode.HIGH_RISK_BAND_REQUIRES_HOLD,),
            policy_decision=policy_decision,
        )

        final_band, decision = apply_cro_override("MEDIUM", cro_result)

        assert final_band == "CRITICAL"
        assert decision == CRODecision.HOLD

    def test_allow_with_constraints_raises_low_to_high(self):
        """PAC: ALLOW_WITH_CONSTRAINTS raises LOW band to HIGH."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.ALLOW_WITH_CONSTRAINTS,
            policy_reason="test",
            applied_threshold="test",
            risk_band="LOW",
            data_quality_score=0.75,
        )
        cro_result = CROPolicyResult(
            decision=CRODecision.ALLOW_WITH_CONSTRAINTS,
            reasons=(CROReasonCode.MEDIUM_RISK_BAND_CONSTRAINED,),
            policy_decision=policy_decision,
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "HIGH"
        assert decision == CRODecision.ALLOW_WITH_CONSTRAINTS

    def test_allow_with_constraints_preserves_critical(self):
        """ALLOW_WITH_CONSTRAINTS should preserve CRITICAL band."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.ALLOW_WITH_CONSTRAINTS,
            policy_reason="test",
            applied_threshold="test",
            risk_band="CRITICAL",
            data_quality_score=0.75,
        )
        cro_result = CROPolicyResult(
            decision=CRODecision.ALLOW_WITH_CONSTRAINTS,
            reasons=(CROReasonCode.MEDIUM_RISK_BAND_CONSTRAINED,),
            policy_decision=policy_decision,
        )

        final_band, decision = apply_cro_override("CRITICAL", cro_result)

        assert final_band == "CRITICAL"

    def test_allow_preserves_original_band(self):
        """ALLOW should preserve original risk band."""
        policy_decision = RiskPolicyDecision(
            policy_decision=CRODecision.ALLOW,
            policy_reason="test",
            applied_threshold="test",
            risk_band="LOW",
            data_quality_score=0.85,
        )
        cro_result = CROPolicyResult(
            decision=CRODecision.ALLOW,
            reasons=(CROReasonCode.LOW_RISK_APPROVED,),
            policy_decision=policy_decision,
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "LOW"
        assert decision == CRODecision.ALLOW


# ---------------------------------------------------------------------------
# CRO Metadata Builder Tests
# ---------------------------------------------------------------------------


class TestCROMetadataBuilder:
    """Tests for CRO metadata builders."""

    def test_build_from_pdo_with_all_fields(self):
        """Build CRO metadata from PDO with all fields present."""
        pdo_data = {
            "data_quality_score": 0.85,
            "has_carrier_profile": True,
            "carrier_tenure_days": 180,
            "has_lane_profile": True,
            "lane_history_days": 90,
            "has_iot_events": True,
            "iot_event_count": 10,
            "is_temp_control": True,
            "is_hazmat": False,
            "value_usd": 75000.0,
            "risk_band": "MEDIUM",
            "risk_score": 0.55,
        }

        metadata = build_cro_metadata_from_pdo(pdo_data)

        assert metadata.data_quality_score == 0.85
        assert metadata.has_carrier_profile is True
        assert metadata.carrier_tenure_days == 180
        assert metadata.has_lane_profile is True
        assert metadata.lane_history_days == 90
        assert metadata.has_iot_events is True
        assert metadata.iot_event_count == 10
        assert metadata.is_temp_control is True
        assert metadata.is_hazmat is False
        assert metadata.value_usd == 75000.0
        assert metadata.risk_band == "MEDIUM"
        assert metadata.risk_score == 0.55

    def test_build_from_none_pdo(self):
        """Build CRO metadata from None PDO returns defaults."""
        metadata = build_cro_metadata_from_pdo(None)

        assert metadata.data_quality_score is None
        assert metadata.has_carrier_profile is True  # Default
        assert metadata.has_lane_profile is True  # Default

    def test_build_from_empty_pdo(self):
        """Build CRO metadata from empty PDO returns defaults."""
        metadata = build_cro_metadata_from_pdo({})

        assert metadata.data_quality_score is None
        assert metadata.has_carrier_profile is True


# ---------------------------------------------------------------------------
# CRO Result Properties Tests
# ---------------------------------------------------------------------------


class TestCROPolicyResult:
    """Tests for CROPolicyResult properties."""

    def test_human_readable_reasons(self, evaluator: CROPolicyEvaluator):
        """Human-readable reasons are properly formatted."""
        metadata = CRORiskMetadata(
            data_quality_score=0.50,
            risk_band="LOW",  # Required for evaluation
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        reasons = result.human_readable_reasons
        assert len(reasons) > 0
        assert any("quality" in r.lower() or "critical" in r.lower() for r in reasons)

    def test_result_includes_metadata_snapshot(self, evaluator: CROPolicyEvaluator, metadata_low_risk_good_quality: CRORiskMetadata):
        """Result includes metadata snapshot for audit."""
        result = evaluator.evaluate(metadata_low_risk_good_quality)

        assert result.metadata_snapshot is not None
        assert "data_quality_score" in result.metadata_snapshot
        assert "carrier_tenure_days" in result.metadata_snapshot

    def test_result_includes_policy_version(self, evaluator: CROPolicyEvaluator, metadata_low_risk_good_quality: CRORiskMetadata):
        """Result includes policy version."""
        result = evaluator.evaluate(metadata_low_risk_good_quality)

        assert result.policy_version == "CRO-POLICY-V1"


# ---------------------------------------------------------------------------
# CRO Audit Logging Tests
# ---------------------------------------------------------------------------


class TestCROAuditLogging:
    """Tests for CRO audit logging."""

    def test_evaluation_logs_warning_when_blocked(self, evaluator: CROPolicyEvaluator, caplog):
        """Blocking decisions log at WARNING level."""
        metadata = CRORiskMetadata(
            data_quality_score=0.50,  # Triggers ESCALATE
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        with caplog.at_level(logging.WARNING):
            result = evaluator.evaluate(metadata)

        assert result.blocks_execution is True
        assert any("cro_policy" in r.message.lower() for r in caplog.records)

    def test_evaluation_logs_info_when_allowed(self, evaluator: CROPolicyEvaluator, metadata_low_risk_good_quality: CRORiskMetadata, caplog):
        """Allowing decisions log at INFO level."""
        with caplog.at_level(logging.INFO):
            result = evaluator.evaluate(metadata_low_risk_good_quality)

        assert result.blocks_execution is False
        assert any("cro_policy" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Module-level Function Tests
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_evaluate_cro_policy_function(self, metadata_low_risk_good_quality: CRORiskMetadata):
        """evaluate_cro_policy() returns valid result."""
        result = evaluate_cro_policy(metadata_low_risk_good_quality)

        assert isinstance(result, CROPolicyResult)
        assert result.decision == CRODecision.ALLOW


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestCROEdgeCases:
    """Edge case tests for CRO policy evaluation."""

    def test_none_data_quality_score_fails_closed(self, evaluator: CROPolicyEvaluator):
        """None data_quality_score should trigger fail-closed (ESCALATE)."""
        metadata = CRORiskMetadata(
            data_quality_score=None,  # Not provided
            risk_band="LOW",  # Required for new logic
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        # Per fail-closed semantics, missing data_quality triggers ESCALATE
        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.MISSING_RISK_METADATA in result.reasons

    def test_none_tenure_days_does_not_add_constraint(self, evaluator: CROPolicyEvaluator):
        """None tenure_days (with profile present) should not add constraint."""
        metadata = CRORiskMetadata(
            data_quality_score=0.80,
            risk_band="MEDIUM",
            has_carrier_profile=True,
            carrier_tenure_days=None,  # Not provided
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE not in result.reasons

    def test_iot_not_required_for_low_value_normal_shipment(self, evaluator: CROPolicyEvaluator):
        """IoT not required for low-value, non-hazmat, non-temp-control shipment."""
        metadata = CRORiskMetadata(
            data_quality_score=0.85,
            risk_band="LOW",
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=False,  # No IoT
            is_temp_control=False,
            is_hazmat=False,
            value_usd=50000.0,  # Below 100k threshold
        )

        result = evaluator.evaluate(metadata)

        assert CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED not in result.reasons
        assert result.decision == CRODecision.ALLOW
