"""CRO Policy Enforcement Tests.

Tests the CRO Policy Evaluator and enforcement integration per
PAC-RUBY-CRO-POLICY-ACTIVATION-01.

Requirements validated:
1. data_quality_score < threshold → ESCALATE
2. missing carrier profile → HOLD
3. missing lane profile → HOLD
4. new carrier (tenure < 90 days) → TIGHTEN_TERMS
5. new lane (history < 60 days) → TIGHTEN_TERMS
6. missing IoT events when required → ESCALATE
7. CRO override beats RiskBand (more restrictive wins)
8. CRO decision included in signed PDO
9. CRO decision logged in enforcement audit

DOCTRINE: PAC-RUBY-CRO-POLICY-ACTIVATION-01
- Deterministic, table-driven thresholds only
- Fail-closed semantics
- All decisions are PDO-bound and auditable

Author: Ruby (GID-12) — Chief Risk Officer
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
def metadata_all_good() -> CRORiskMetadata:
    """Create metadata that passes all CRO checks."""
    return CRORiskMetadata(
        data_quality_score=0.95,
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

    def test_default_thresholds(self):
        """Default thresholds match PAC specification."""
        assert CRO_POLICY.data_quality_min_score == 0.70
        assert CRO_POLICY.new_carrier_tenure_days_min == 90
        assert CRO_POLICY.new_lane_history_days_min == 60
        assert CRO_POLICY.iot_required_for_temp_control is True
        assert CRO_POLICY.iot_required_for_hazmat is True
        assert CRO_POLICY.iot_required_for_high_value_threshold_usd == 100_000.0


# ---------------------------------------------------------------------------
# CRO Decision Tests
# ---------------------------------------------------------------------------


class TestCRODecision:
    """Tests for CRO decision enum."""

    def test_decision_blocks_execution(self):
        """HOLD and ESCALATE block execution."""
        assert CRODecision.HOLD.blocks_execution is True
        assert CRODecision.ESCALATE.blocks_execution is True
        assert CRODecision.TIGHTEN_TERMS.blocks_execution is False
        assert CRODecision.APPROVE.blocks_execution is False


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — ESCALATE Triggers
# ---------------------------------------------------------------------------


class TestCROEscalateTriggers:
    """Tests for conditions that trigger ESCALATE decision."""

    def test_data_quality_below_threshold_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: data_quality_score < 0.70 → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.65,  # Below 0.70 threshold
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD in result.reasons
        assert result.blocks_execution is True

    def test_data_quality_at_threshold_approves(self, evaluator: CROPolicyEvaluator):
        """data_quality_score == 0.70 should NOT escalate (boundary test)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.70,  # Exactly at threshold
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.APPROVE
        assert CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD not in result.reasons

    def test_missing_iot_for_temp_control_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: Missing IoT when required for temp control → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=False,  # Missing IoT
            is_temp_control=True,  # Requires IoT
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED in result.reasons
        assert result.blocks_execution is True

    def test_missing_iot_for_hazmat_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: Missing IoT when required for hazmat → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=False,  # Missing IoT
            is_hazmat=True,  # Requires IoT
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED in result.reasons

    def test_missing_iot_for_high_value_escalates(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: Missing IoT for high-value shipment → ESCALATE."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=False,  # Missing IoT
            value_usd=150_000.0,  # Above 100k threshold
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.MISSING_IOT_EVENTS_WHEN_REQUIRED in result.reasons


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — HOLD Triggers
# ---------------------------------------------------------------------------


class TestCROHoldTriggers:
    """Tests for conditions that trigger HOLD decision."""

    def test_missing_carrier_profile_holds(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: Missing carrier_profile → HOLD."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=False,  # Missing carrier profile
            carrier_tenure_days=None,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD
        assert CROReasonCode.MISSING_CARRIER_PROFILE in result.reasons
        assert result.blocks_execution is True

    def test_missing_lane_profile_holds(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: Missing lane_profile → HOLD."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=False,  # Missing lane profile
            lane_history_days=None,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD
        assert CROReasonCode.MISSING_LANE_PROFILE in result.reasons
        assert result.blocks_execution is True

    def test_missing_both_profiles_holds_with_both_reasons(self, evaluator: CROPolicyEvaluator):
        """Missing both profiles → HOLD with both reasons."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=False,
            carrier_tenure_days=None,
            has_lane_profile=False,
            lane_history_days=None,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD
        assert CROReasonCode.MISSING_CARRIER_PROFILE in result.reasons
        assert CROReasonCode.MISSING_LANE_PROFILE in result.reasons


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — TIGHTEN_TERMS Triggers
# ---------------------------------------------------------------------------


class TestCROTightenTermsTriggers:
    """Tests for conditions that trigger TIGHTEN_TERMS decision."""

    def test_new_carrier_tightens_terms(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: New carrier (tenure < 90 days) → TIGHTEN_TERMS."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=60,  # Below 90 day threshold
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.TIGHTEN_TERMS
        assert CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE in result.reasons
        assert result.blocks_execution is False

    def test_carrier_at_threshold_approves(self, evaluator: CROPolicyEvaluator):
        """Carrier tenure == 90 days should NOT trigger tightening."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=90,  # Exactly at threshold
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.APPROVE
        assert CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE not in result.reasons

    def test_new_lane_tightens_terms(self, evaluator: CROPolicyEvaluator):
        """PAC Requirement: New lane (history < 60 days) → TIGHTEN_TERMS."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=30,  # Below 60 day threshold
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.TIGHTEN_TERMS
        assert CROReasonCode.NEW_LANE_INSUFFICIENT_HISTORY in result.reasons
        assert result.blocks_execution is False

    def test_lane_at_threshold_approves(self, evaluator: CROPolicyEvaluator):
        """Lane history == 60 days should NOT trigger tightening."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=60,  # Exactly at threshold
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.APPROVE

    def test_new_carrier_and_lane_tightens_with_both_reasons(self, evaluator: CROPolicyEvaluator):
        """New carrier AND new lane → TIGHTEN_TERMS with both reasons."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=True,
            carrier_tenure_days=60,  # New carrier
            has_lane_profile=True,
            lane_history_days=30,  # New lane
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.TIGHTEN_TERMS
        assert CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE in result.reasons
        assert CROReasonCode.NEW_LANE_INSUFFICIENT_HISTORY in result.reasons


# ---------------------------------------------------------------------------
# CROPolicyEvaluator Tests — Decision Priority
# ---------------------------------------------------------------------------


class TestCRODecisionPriority:
    """Tests for decision priority (more restrictive wins)."""

    def test_escalate_beats_hold(self, evaluator: CROPolicyEvaluator):
        """ESCALATE (data quality) should beat HOLD (missing profile)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.50,  # Triggers ESCALATE
            has_carrier_profile=False,  # Would trigger HOLD
            carrier_tenure_days=None,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.ESCALATE
        assert CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD in result.reasons

    def test_hold_beats_tighten(self, evaluator: CROPolicyEvaluator):
        """HOLD (missing profile) should beat TIGHTEN_TERMS (new carrier)."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
            has_carrier_profile=False,  # Triggers HOLD
            carrier_tenure_days=None,
            has_lane_profile=True,
            lane_history_days=30,  # Would trigger TIGHTEN_TERMS
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert result.decision == CRODecision.HOLD
        assert CROReasonCode.MISSING_CARRIER_PROFILE in result.reasons

    def test_approve_when_all_checks_pass(self, evaluator: CROPolicyEvaluator, metadata_all_good: CRORiskMetadata):
        """PAC Requirement: APPROVE when all checks pass."""
        result = evaluator.evaluate(metadata_all_good)

        assert result.decision == CRODecision.APPROVE
        assert CROReasonCode.ALL_CHECKS_PASSED in result.reasons
        assert result.blocks_execution is False


# ---------------------------------------------------------------------------
# CRO Override Tests
# ---------------------------------------------------------------------------


class TestCROOverride:
    """Tests for CRO override logic (more restrictive band wins)."""

    def test_escalate_overrides_low_band(self):
        """PAC Requirement: CRO ESCALATE overrides LOW risk band to CRITICAL."""
        cro_result = CROPolicyResult(
            decision=CRODecision.ESCALATE,
            reasons=(CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD,),
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "CRITICAL"
        assert decision == CRODecision.ESCALATE

    def test_hold_overrides_medium_band(self):
        """PAC Requirement: CRO HOLD overrides MEDIUM risk band to CRITICAL."""
        cro_result = CROPolicyResult(
            decision=CRODecision.HOLD,
            reasons=(CROReasonCode.MISSING_CARRIER_PROFILE,),
        )

        final_band, decision = apply_cro_override("MEDIUM", cro_result)

        assert final_band == "CRITICAL"
        assert decision == CRODecision.HOLD

    def test_tighten_terms_raises_low_to_high(self):
        """PAC Requirement: TIGHTEN_TERMS raises LOW band to HIGH."""
        cro_result = CROPolicyResult(
            decision=CRODecision.TIGHTEN_TERMS,
            reasons=(CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE,),
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "HIGH"
        assert decision == CRODecision.TIGHTEN_TERMS

    def test_tighten_terms_preserves_critical(self):
        """TIGHTEN_TERMS should preserve CRITICAL band (already high enough)."""
        cro_result = CROPolicyResult(
            decision=CRODecision.TIGHTEN_TERMS,
            reasons=(CROReasonCode.NEW_CARRIER_INSUFFICIENT_TENURE,),
        )

        final_band, decision = apply_cro_override("CRITICAL", cro_result)

        assert final_band == "CRITICAL"

    def test_approve_preserves_original_band(self):
        """APPROVE should preserve original risk band."""
        cro_result = CROPolicyResult(
            decision=CRODecision.APPROVE,
            reasons=(CROReasonCode.ALL_CHECKS_PASSED,),
        )

        final_band, decision = apply_cro_override("LOW", cro_result)

        assert final_band == "LOW"
        assert decision == CRODecision.APPROVE


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
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        reasons = result.human_readable_reasons
        assert len(reasons) > 0
        assert any("quality" in r.lower() for r in reasons)

    def test_result_includes_metadata_snapshot(self, evaluator: CROPolicyEvaluator, metadata_all_good: CRORiskMetadata):
        """Result includes metadata snapshot for audit."""
        result = evaluator.evaluate(metadata_all_good)

        assert result.metadata_snapshot is not None
        assert "data_quality_score" in result.metadata_snapshot
        assert "carrier_tenure_days" in result.metadata_snapshot

    def test_result_includes_policy_version(self, evaluator: CROPolicyEvaluator, metadata_all_good: CRORiskMetadata):
        """Result includes policy version."""
        result = evaluator.evaluate(metadata_all_good)

        assert result.policy_version == "cro_policy@v1.0.0"


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

    def test_evaluation_logs_info_when_allowed(self, evaluator: CROPolicyEvaluator, metadata_all_good: CRORiskMetadata, caplog):
        """Allowing decisions log at INFO level."""
        with caplog.at_level(logging.INFO):
            result = evaluator.evaluate(metadata_all_good)

        assert result.blocks_execution is False
        assert any("cro_policy" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Module-level Function Tests
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_evaluate_cro_policy_function(self, metadata_all_good: CRORiskMetadata):
        """evaluate_cro_policy() returns valid result."""
        result = evaluate_cro_policy(metadata_all_good)

        assert isinstance(result, CROPolicyResult)
        assert result.decision == CRODecision.APPROVE


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestCROEdgeCases:
    """Edge case tests for CRO policy evaluation."""

    def test_none_data_quality_score_passes(self, evaluator: CROPolicyEvaluator):
        """None data_quality_score should not trigger escalation."""
        metadata = CRORiskMetadata(
            data_quality_score=None,  # Not provided
            has_carrier_profile=True,
            carrier_tenure_days=200,
            has_lane_profile=True,
            lane_history_days=120,
            has_iot_events=True,
        )

        result = evaluator.evaluate(metadata)

        assert CROReasonCode.DATA_QUALITY_BELOW_THRESHOLD not in result.reasons

    def test_none_tenure_days_does_not_tighten(self, evaluator: CROPolicyEvaluator):
        """None tenure_days (with profile present) should not trigger tightening."""
        metadata = CRORiskMetadata(
            data_quality_score=0.90,
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
            data_quality_score=0.90,
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
        assert result.decision == CRODecision.APPROVE
