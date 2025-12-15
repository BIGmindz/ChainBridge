"""
ChainIQ v0.1 - Settlement Rules Tests

Tests for the glass-box settlement policy recommendation logic.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from datetime import datetime

import pytest

from app.schemas import SettlementPolicyRecommendation, ShipmentRiskAssessment, ShipmentRiskContext, TopFactor
from app.settlement import SettlementRecommender, get_default_recommender, recommend_settlement, recommend_settlements
from app.settlement_rules import (
    RISK_BAND_TO_POLICY,
    RISK_BANDS,
    SETTLEMENT_POLICY_TEMPLATES,
    get_risk_band,
    recommend_settlement_policies,
    recommend_settlement_policy,
    validate_all_templates,
)

# =============================================================================
# FIXTURES
# =============================================================================


def make_assessment(
    risk_score: float,
    decision: str = "APPROVE",
    shipment_id: str = "TEST-001",
) -> ShipmentRiskAssessment:
    """Create a test assessment with given risk score."""
    return ShipmentRiskAssessment(
        shipment_id=shipment_id,
        assessed_at=datetime.utcnow(),
        model_version="test-v0.1",
        risk_score=risk_score,
        operational_risk=risk_score * 0.8,
        financial_risk=risk_score * 0.6,
        fraud_risk=risk_score * 0.2,
        esg_risk=0.0,
        resilience_score=100 - risk_score,
        decision=decision,
        decision_confidence=0.85,
        top_factors=[
            TopFactor(
                feature_name="lane_incident_rate",
                direction="INCREASES_RISK",
                magnitude=25.0,
                human_label="Lane has 12% historical delay rate",
            ),
            TopFactor(
                feature_name="carrier_reliability",
                direction="DECREASES_RISK",
                magnitude=15.0,
                human_label="Carrier has strong track record",
            ),
        ],
        summary_reason=f"Test assessment with risk score {risk_score}",
        tags=["TEST"],
    )


def make_context(
    shipment_id: str = "TEST-001",
    mode: str = "OCEAN",
) -> ShipmentRiskContext:
    """Create a test shipment context."""
    return ShipmentRiskContext(
        shipment_id=shipment_id,
        tenant_id="test-tenant",
        mode=mode,
        origin_country="CN",
        destination_country="US",
        planned_departure=datetime(2024, 12, 1, 8, 0, 0),
        planned_arrival=datetime(2024, 12, 21, 18, 0, 0),
    )


# =============================================================================
# TEST: RISK BAND MAPPING
# =============================================================================


class TestGetRiskBand:
    """Tests for risk band determination."""

    def test_low_risk_band(self):
        """Scores 0-29 should be LOW."""
        for score in [0, 10, 15, 29, 29.9]:
            band = get_risk_band(score)
            assert band["name"] == "LOW", f"Score {score} should be LOW"

    def test_moderate_risk_band(self):
        """Scores 30-59 should be MODERATE."""
        for score in [30, 45, 55, 59, 59.9]:
            band = get_risk_band(score)
            assert band["name"] == "MODERATE", f"Score {score} should be MODERATE"

    def test_high_risk_band(self):
        """Scores 60-79 should be HIGH."""
        for score in [60, 70, 75, 79, 79.9]:
            band = get_risk_band(score)
            assert band["name"] == "HIGH", f"Score {score} should be HIGH"

    def test_critical_risk_band(self):
        """Scores 80-100 should be CRITICAL."""
        for score in [80, 85, 95, 100]:
            band = get_risk_band(score)
            assert band["name"] == "CRITICAL", f"Score {score} should be CRITICAL"

    def test_band_boundaries(self):
        """Test exact boundary values."""
        assert get_risk_band(0)["name"] == "LOW"
        assert get_risk_band(30)["name"] == "MODERATE"
        assert get_risk_band(60)["name"] == "HIGH"
        assert get_risk_band(80)["name"] == "CRITICAL"


# =============================================================================
# TEST: POLICY TEMPLATE VALIDATION
# =============================================================================


class TestPolicyTemplates:
    """Tests for settlement policy templates."""

    def test_all_templates_have_required_fields(self):
        """All templates should have required fields."""
        required_fields = ["code", "name", "milestones", "settlement_delay_hours", "requires_manual_approval"]

        for code, template in SETTLEMENT_POLICY_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Template {code} missing {field}"

    def test_all_milestones_sum_to_100(self):
        """All template milestone percentages should sum to 100."""
        for code, template in SETTLEMENT_POLICY_TEMPLATES.items():
            total = sum(m[2] for m in template["milestones"])
            assert abs(total - 100.0) < 0.01, f"Template {code} milestones sum to {total}, expected 100"

    def test_validate_all_templates_passes(self):
        """Built-in validation should pass for all templates."""
        errors = validate_all_templates()
        assert len(errors) == 0, f"Template validation errors: {errors}"

    def test_risk_band_to_policy_mapping_complete(self):
        """All risk bands should have a policy mapping."""
        for band in RISK_BANDS:
            band_name = band["name"]
            assert band_name in RISK_BAND_TO_POLICY, f"Missing mapping for band {band_name}"
            policy_code = RISK_BAND_TO_POLICY[band_name]
            assert policy_code in SETTLEMENT_POLICY_TEMPLATES, f"Missing template for policy {policy_code}"


# =============================================================================
# TEST: SETTLEMENT RECOMMENDATION
# =============================================================================


class TestRecommendSettlementPolicy:
    """Tests for the main recommendation function."""

    def test_low_risk_gets_fast_policy(self):
        """Low risk score should get LOW_RISK_FAST policy."""
        assessment = make_assessment(risk_score=15, decision="APPROVE")
        rec = recommend_settlement_policy(assessment)

        assert rec.recommended_policy_code == "LOW_RISK_FAST"
        assert rec.risk_band == "LOW"
        assert rec.hold_percentage == 10.0
        assert rec.requires_manual_approval is False

    def test_moderate_risk_gets_balanced_policy(self):
        """Moderate risk score should get MODERATE_BALANCED policy."""
        assessment = make_assessment(risk_score=45, decision="TIGHTEN_TERMS")
        rec = recommend_settlement_policy(assessment)

        assert rec.recommended_policy_code == "MODERATE_BALANCED"
        assert rec.risk_band == "MODERATE"
        assert rec.hold_percentage == 30.0
        assert rec.requires_manual_approval is False

    def test_high_risk_gets_guarded_policy(self):
        """High risk score should get HIGH_RISK_GUARDED policy."""
        assessment = make_assessment(risk_score=70, decision="HOLD")
        rec = recommend_settlement_policy(assessment)

        assert rec.recommended_policy_code == "HIGH_RISK_GUARDED"
        assert rec.risk_band == "HIGH"
        assert rec.hold_percentage == 40.0
        assert rec.requires_manual_approval is False

    def test_critical_risk_gets_review_policy(self):
        """Critical risk score should get CRITICAL_REVIEW policy."""
        assessment = make_assessment(risk_score=90, decision="ESCALATE")
        rec = recommend_settlement_policy(assessment)

        assert rec.recommended_policy_code == "CRITICAL_REVIEW"
        assert rec.risk_band == "CRITICAL"
        assert rec.hold_percentage == 60.0
        assert rec.requires_manual_approval is True

    def test_milestones_generated_correctly(self):
        """Milestones should be generated with correct structure."""
        assessment = make_assessment(risk_score=25)
        rec = recommend_settlement_policy(assessment)

        assert len(rec.milestones) >= 1

        # Check milestone structure
        for m in rec.milestones:
            assert m.name in ["PICKUP", "DELIVERY", "CLAIM_WINDOW"]
            assert 0 <= m.percentage <= 100
            assert m.event_type is not None

    def test_milestone_percentages_sum_to_100(self):
        """Recommendation milestones should sum to 100%."""
        for score in [10, 45, 70, 90]:
            assessment = make_assessment(risk_score=score)
            rec = recommend_settlement_policy(assessment)

            total = sum(m.percentage for m in rec.milestones)
            assert abs(total - 100.0) < 0.01, f"Milestones for score {score} sum to {total}"

    def test_rationale_contains_risk_score(self):
        """Rationale should mention the risk score."""
        assessment = make_assessment(risk_score=67)
        rec = recommend_settlement_policy(assessment)

        assert "67" in rec.rationale

    def test_rationale_contains_band_label(self):
        """Rationale should mention the risk band."""
        assessment = make_assessment(risk_score=75)
        rec = recommend_settlement_policy(assessment)

        assert "High Risk" in rec.rationale

    def test_tags_include_risk_band(self):
        """Tags should include risk band identifier."""
        assessment = make_assessment(risk_score=50)
        rec = recommend_settlement_policy(assessment)

        assert any("RISK_BAND_" in tag for tag in rec.tags)

    def test_tags_include_decision(self):
        """Tags should include decision identifier."""
        assessment = make_assessment(risk_score=50, decision="TIGHTEN_TERMS")
        rec = recommend_settlement_policy(assessment)

        assert "DECISION_TIGHTEN_TERMS" in rec.tags

    def test_top_factors_included(self):
        """Top factors from assessment should be included."""
        assessment = make_assessment(risk_score=60)
        rec = recommend_settlement_policy(assessment)

        assert len(rec.top_factors) > 0
        assert rec.top_factors[0].feature_name == "lane_incident_rate"


# =============================================================================
# TEST: BATCH PROCESSING
# =============================================================================


class TestBatchRecommendation:
    """Tests for batch recommendation processing."""

    def test_batch_returns_same_count(self):
        """Batch should return same number of recommendations as inputs."""
        assessments = [
            make_assessment(10, shipment_id="S1"),
            make_assessment(45, shipment_id="S2"),
            make_assessment(75, shipment_id="S3"),
            make_assessment(90, shipment_id="S4"),
        ]

        recs = recommend_settlement_policies(assessments)

        assert len(recs) == 4

    def test_batch_preserves_order(self):
        """Batch should preserve input order."""
        assessments = [
            make_assessment(10, shipment_id="FIRST"),
            make_assessment(90, shipment_id="LAST"),
        ]

        recs = recommend_settlement_policies(assessments)

        assert recs[0].shipment_id == "FIRST"
        assert recs[1].shipment_id == "LAST"

    def test_batch_assigns_different_policies(self):
        """Batch with varied scores should get different policies."""
        assessments = [
            make_assessment(10),  # LOW
            make_assessment(90),  # CRITICAL
        ]

        recs = recommend_settlement_policies(assessments)

        assert recs[0].recommended_policy_code != recs[1].recommended_policy_code


# =============================================================================
# TEST: SETTLEMENT RECOMMENDER CLASS
# =============================================================================


class TestSettlementRecommender:
    """Tests for the SettlementRecommender class."""

    def test_recommender_initialization(self):
        """Recommender should initialize with default scorer."""
        recommender = SettlementRecommender()
        assert recommender.scorer is not None

    def test_recommend_for_context(self):
        """recommend_for_context should produce valid recommendation."""
        recommender = SettlementRecommender()
        context = make_context()

        rec = recommender.recommend_for_context(context)

        assert isinstance(rec, SettlementPolicyRecommendation)
        assert rec.shipment_id == context.shipment_id
        assert rec.recommended_policy_code in SETTLEMENT_POLICY_TEMPLATES

    def test_recommend_for_assessment(self):
        """recommend_for_assessment should work with pre-computed assessment."""
        recommender = SettlementRecommender()
        assessment = make_assessment(risk_score=55)

        rec = recommender.recommend_for_assessment(assessment)

        assert isinstance(rec, SettlementPolicyRecommendation)
        assert rec.risk_score == 55

    def test_recommend_for_batch(self):
        """recommend_for_batch should handle multiple contexts."""
        recommender = SettlementRecommender()
        contexts = [
            make_context(shipment_id="S1"),
            make_context(shipment_id="S2"),
        ]

        recs = recommender.recommend_for_batch(contexts)

        assert len(recs) == 2
        assert recs[0].shipment_id == "S1"
        assert recs[1].shipment_id == "S2"

    def test_list_risk_bands(self):
        """list_risk_bands should return all bands."""
        bands = SettlementRecommender.list_risk_bands()

        assert len(bands) == 4
        assert bands[0]["name"] == "LOW"
        assert bands[-1]["name"] == "CRITICAL"

    def test_list_policy_templates(self):
        """list_policy_templates should return all templates."""
        templates = SettlementRecommender.list_policy_templates()

        assert "LOW_RISK_FAST" in templates
        assert "CRITICAL_REVIEW" in templates

    def test_get_policy_template(self):
        """get_policy_template should return specific template."""
        template = SettlementRecommender.get_policy_template("HIGH_RISK_GUARDED")

        assert template["code"] == "HIGH_RISK_GUARDED"
        assert template["hold_percentage"] == 40.0

    def test_get_risk_band_for_score(self):
        """get_risk_band_for_score should work correctly."""
        band = SettlementRecommender.get_risk_band_for_score(65)

        assert band["name"] == "HIGH"


# =============================================================================
# TEST: MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_default_recommender(self):
        """get_default_recommender should return singleton."""
        r1 = get_default_recommender()
        r2 = get_default_recommender()

        assert r1 is r2

    def test_recommend_settlement(self):
        """recommend_settlement convenience function should work."""
        context = make_context()
        rec = recommend_settlement(context)

        assert isinstance(rec, SettlementPolicyRecommendation)

    def test_recommend_settlements(self):
        """recommend_settlements convenience function should work."""
        contexts = [make_context(shipment_id=f"S{i}") for i in range(3)]
        recs = recommend_settlements(contexts)

        assert len(recs) == 3


# =============================================================================
# TEST: EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_risk_score(self):
        """Zero risk score should be handled."""
        assessment = make_assessment(risk_score=0)
        rec = recommend_settlement_policy(assessment)

        assert rec.risk_band == "LOW"
        assert rec.recommended_policy_code == "LOW_RISK_FAST"

    def test_max_risk_score(self):
        """Maximum risk score (100) should be handled."""
        assessment = make_assessment(risk_score=100)
        rec = recommend_settlement_policy(assessment)

        assert rec.risk_band == "CRITICAL"
        assert rec.recommended_policy_code == "CRITICAL_REVIEW"

    def test_empty_top_factors(self):
        """Assessment with no top factors should still work."""
        assessment = make_assessment(risk_score=50)
        assessment.top_factors = []

        rec = recommend_settlement_policy(assessment)

        assert rec is not None
        assert len(rec.top_factors) == 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
