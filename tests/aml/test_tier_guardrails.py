# ═══════════════════════════════════════════════════════════════════════════════
# AML Tier Guardrails Tests
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for AML Tier Guardrails

COVERAGE:
    - Tier boundary definitions
    - Guardrail enforcement
    - Clearance evaluation
    - SAR filing blocks
    - Violation recording
"""

import pytest

from core.aml.tier_guardrails import (
    GuardrailType,
    ViolationSeverity,
    ProductScope,
    Guardrail,
    GuardrailViolation,
    TierBoundary,
    GuardrailEngine,
    TIER_0_BOUNDARY,
    TIER_1_BOUNDARY,
    TIER_2_BOUNDARY,
    TIER_3_BOUNDARY,
    TIER_SAR_BOUNDARY,
    GR_NO_AUTO_CLEAR_TIER2,
    GR_NO_AUTO_SAR,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestTierBoundaries:
    """Tests for tier boundary definitions."""

    def test_tier_0_auto_clearable(self):
        """Test Tier-0 is auto-clearable."""
        assert TIER_0_BOUNDARY.auto_clearable is True
        assert TIER_0_BOUNDARY.requires_human_review is False
        assert "AUTO_CLEAR" in TIER_0_BOUNDARY.permitted_actions

    def test_tier_1_auto_clearable(self):
        """Test Tier-1 is auto-clearable."""
        assert TIER_1_BOUNDARY.auto_clearable is True
        assert TIER_1_BOUNDARY.requires_human_review is False
        assert "AUTO_CLEAR" in TIER_1_BOUNDARY.permitted_actions

    def test_tier_2_not_auto_clearable(self):
        """Test Tier-2 is NOT auto-clearable."""
        assert TIER_2_BOUNDARY.auto_clearable is False
        assert TIER_2_BOUNDARY.requires_human_review is True
        assert "AUTO_CLEAR" in TIER_2_BOUNDARY.blocked_actions

    def test_tier_3_requires_senior_review(self):
        """Test Tier-3 requires senior review."""
        assert TIER_3_BOUNDARY.auto_clearable is False
        assert TIER_3_BOUNDARY.requires_senior_review is True
        assert TIER_3_BOUNDARY.sar_eligible is True

    def test_tier_sar_no_auto_file(self):
        """Test Tier-SAR cannot auto-file SAR."""
        assert TIER_SAR_BOUNDARY.auto_clearable is False
        assert "FILE_SAR" in TIER_SAR_BOUNDARY.blocked_actions
        assert "PREPARE_SAR" in TIER_SAR_BOUNDARY.permitted_actions


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardrail:
    """Tests for Guardrail data class."""

    def test_guardrail_creation(self):
        """Test valid guardrail creation."""
        guardrail = Guardrail(
            guardrail_id="GR-AML-TEST",
            name="Test Guardrail",
            description="Test description",
            guardrail_type=GuardrailType.HARD_BLOCK,
            violation_severity=ViolationSeverity.HIGH,
            scope=ProductScope.FALSE_POSITIVE,
            condition="test condition",
            enforcement_action="Block",
        )
        assert guardrail.guardrail_id == "GR-AML-TEST"
        assert guardrail.enabled is True

    def test_guardrail_id_validation(self):
        """Test guardrail ID must start with GR-AML-."""
        with pytest.raises(ValueError, match="Guardrail ID must start with 'GR-AML-'"):
            Guardrail(
                guardrail_id="INVALID",
                name="Test",
                description="Test",
                guardrail_type=GuardrailType.WARNING,
                violation_severity=ViolationSeverity.LOW,
                scope=ProductScope.FALSE_POSITIVE,
                condition="test",
                enforcement_action="Warn",
            )

    def test_default_guardrails_exist(self):
        """Test default guardrails are defined correctly."""
        assert GR_NO_AUTO_CLEAR_TIER2.guardrail_type == GuardrailType.HARD_BLOCK
        assert GR_NO_AUTO_CLEAR_TIER2.violation_severity == ViolationSeverity.CRITICAL
        assert GR_NO_AUTO_SAR.guardrail_type == GuardrailType.HARD_BLOCK


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardrailEngine:
    """Tests for GuardrailEngine service."""

    @pytest.fixture
    def engine(self):
        """Create fresh engine instance."""
        return GuardrailEngine()

    def test_tier_boundary_lookup(self, engine):
        """Test tier boundary lookup."""
        boundary = engine.get_tier_boundary("TIER_0")
        assert boundary is not None
        assert boundary.auto_clearable is True

    def test_is_auto_clearable_tier_0(self, engine):
        """Test Tier-0 is auto-clearable."""
        assert engine.is_auto_clearable("TIER_0") is True

    def test_is_auto_clearable_tier_1(self, engine):
        """Test Tier-1 is auto-clearable."""
        assert engine.is_auto_clearable("TIER_1") is True

    def test_is_auto_clearable_tier_2(self, engine):
        """Test Tier-2 is NOT auto-clearable."""
        assert engine.is_auto_clearable("TIER_2") is False

    def test_is_auto_clearable_tier_3(self, engine):
        """Test Tier-3 is NOT auto-clearable."""
        assert engine.is_auto_clearable("TIER_3") is False

    def test_is_auto_clearable_tier_sar(self, engine):
        """Test Tier-SAR is NOT auto-clearable."""
        assert engine.is_auto_clearable("TIER_SAR") is False

    def test_check_action_permitted_tier_0_clear(self, engine):
        """Test AUTO_CLEAR is permitted for Tier-0."""
        assert engine.check_action_permitted("TIER_0", "AUTO_CLEAR") is True

    def test_check_action_permitted_tier_2_clear_blocked(self, engine):
        """Test AUTO_CLEAR is blocked for Tier-2."""
        assert engine.check_action_permitted("TIER_2", "AUTO_CLEAR") is False

    def test_evaluate_clearance_tier_0_high_confidence(self, engine):
        """Test clearance evaluation for Tier-0 with high confidence."""
        result = engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_0",
            confidence=0.98,
            context={},
        )
        assert result["clearance_permitted"] is True
        assert result["violation_count"] == 0

    def test_evaluate_clearance_tier_2_blocked(self, engine):
        """Test clearance evaluation blocks Tier-2."""
        result = engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_2",
            confidence=0.99,
            context={},
        )
        assert result["clearance_permitted"] is False
        assert result["violation_count"] > 0
        assert result["recommendation"] == "ESCALATE"

    def test_evaluate_clearance_low_confidence_blocked(self, engine):
        """Test clearance blocked for low confidence."""
        result = engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_0",
            confidence=0.80,
            context={},
        )
        assert result["clearance_permitted"] is False

    def test_evaluate_clearance_sanctions_hit_blocked(self, engine):
        """Test clearance blocked for sanctions hit."""
        result = engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_0",
            confidence=0.99,
            context={"sanctions_hit": True},
        )
        assert result["clearance_permitted"] is False

    def test_evaluate_clearance_pep_blocked(self, engine):
        """Test clearance blocked for PEP association."""
        result = engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_0",
            confidence=0.99,
            context={"pep_associated": True},
        )
        assert result["clearance_permitted"] is False

    def test_evaluate_clearance_adverse_media_blocked(self, engine):
        """Test clearance blocked for adverse media."""
        result = engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_1",
            confidence=0.99,
            context={"adverse_media_hit": True},
        )
        assert result["clearance_permitted"] is False

    def test_evaluate_sar_filing_system_blocked(self, engine):
        """Test SAR filing blocked for SYSTEM actor."""
        result = engine.evaluate_sar_filing(
            case_id="CASE-001",
            entity_id="ENT-001",
            actor="SYSTEM",
        )
        assert result["filing_permitted"] is False

    def test_evaluate_sar_filing_human_permitted(self, engine):
        """Test SAR filing permitted for human actor."""
        result = engine.evaluate_sar_filing(
            case_id="CASE-001",
            entity_id="ENT-001",
            actor="USER-001",
        )
        assert result["filing_permitted"] is True

    def test_list_guardrails(self, engine):
        """Test listing all guardrails."""
        guardrails = engine.list_guardrails()
        assert len(guardrails) >= 8  # Default guardrails

    def test_get_violations_for_case(self, engine):
        """Test getting violations for a specific case."""
        # Trigger some violations
        engine.evaluate_clearance(
            case_id="CASE-001",
            entity_id="ENT-001",
            tier="TIER_2",
            confidence=0.99,
            context={},
        )
        violations = engine.get_violations_for_case("CASE-001")
        assert len(violations) > 0

    def test_generate_report(self, engine):
        """Test report generation."""
        report = engine.generate_report()
        assert "timestamp" in report
        assert "total_guardrails" in report
        assert "tier_boundaries" in report


# ═══════════════════════════════════════════════════════════════════════════════
# VIOLATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestGuardrailViolation:
    """Tests for GuardrailViolation data class."""

    def test_violation_creation(self):
        """Test valid violation creation."""
        violation = GuardrailViolation(
            violation_id="VIOL-00000001",
            guardrail_id="GR-AML-001",
            case_id="CASE-001",
            entity_id="ENT-001",
            timestamp="2025-01-01T00:00:00Z",
            severity=ViolationSeverity.CRITICAL,
            context={"tier": "TIER_2"},
            blocked=True,
        )
        assert violation.violation_id == "VIOL-00000001"
        assert violation.blocked is True

    def test_violation_id_validation(self):
        """Test violation ID must start with VIOL-."""
        with pytest.raises(ValueError, match="Violation ID must start with 'VIOL-'"):
            GuardrailViolation(
                violation_id="INVALID",
                guardrail_id="GR-AML-001",
                case_id="CASE-001",
                entity_id="ENT-001",
                timestamp="2025-01-01T00:00:00Z",
                severity=ViolationSeverity.HIGH,
                context={},
                blocked=False,
            )
