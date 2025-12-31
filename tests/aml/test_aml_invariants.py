# ═══════════════════════════════════════════════════════════════════════════════
# AML Invariants Tests
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for AML Invariants (INV-AML-*)

COVERAGE:
    - Invariant definitions
    - Check execution
    - Violation recording
    - Clearance decision checks
    - Fail-closed behavior
"""

import pytest

from core.governance.aml_invariants import (
    InvariantCategory,
    InvariantSeverity,
    CheckResult,
    AMLInvariant,
    InvariantCheckResult,
    InvariantViolation,
    AMLInvariantEngine,
    INV_AML_001,
    INV_AML_002,
    INV_AML_003,
    INV_AML_004,
)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAMLInvariant:
    """Tests for AMLInvariant data class."""

    def test_invariant_creation(self):
        """Test valid invariant creation."""
        inv = AMLInvariant(
            invariant_id="INV-AML-TEST",
            name="Test Invariant",
            category=InvariantCategory.DECISION,
            severity=InvariantSeverity.HIGH,
            description="Test description",
            condition="test condition",
            error_message="Test error",
        )
        assert inv.invariant_id == "INV-AML-TEST"
        assert inv.enabled is True
        assert inv.fail_closed is True

    def test_invariant_id_validation(self):
        """Test invariant ID must start with INV-AML-."""
        with pytest.raises(ValueError, match="Invariant ID must start with 'INV-AML-'"):
            AMLInvariant(
                invariant_id="INVALID",
                name="Test",
                category=InvariantCategory.DECISION,
                severity=InvariantSeverity.LOW,
                description="Test",
                condition="test",
                error_message="Test",
            )

    def test_default_invariants_exist(self):
        """Test default invariants are defined correctly."""
        assert INV_AML_001.invariant_id == "INV-AML-001"
        assert INV_AML_001.category == InvariantCategory.DECISION
        assert INV_AML_001.severity == InvariantSeverity.CRITICAL

    def test_invariant_hash_deterministic(self):
        """Test invariant hash is deterministic."""
        hash1 = INV_AML_001.compute_invariant_hash()
        hash2 = INV_AML_001.compute_invariant_hash()
        assert hash1 == hash2


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAMLInvariantEngine:
    """Tests for AMLInvariantEngine service."""

    @pytest.fixture
    def engine(self):
        """Create fresh engine instance."""
        return AMLInvariantEngine()

    def test_list_invariants(self, engine):
        """Test listing all invariants."""
        invariants = engine.list_invariants()
        assert len(invariants) >= 12  # Default count

    def test_get_invariant(self, engine):
        """Test getting invariant by ID."""
        inv = engine.get_invariant("INV-AML-001")
        assert inv is not None
        assert inv.name == "No Autonomous Tier-2+ Clearance"

    # ───────────────────────────────────────────────────────────────────────────
    # INV-AML-001: No Tier-2+ Auto-Clear
    # ───────────────────────────────────────────────────────────────────────────

    def test_inv_001_tier_0_clear_passes(self, engine):
        """Test INV-AML-001 passes for Tier-0 clearance."""
        result = engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_0", "decision": "AUTO_CLEAR"},
        )
        assert result.result == CheckResult.PASS

    def test_inv_001_tier_1_clear_passes(self, engine):
        """Test INV-AML-001 passes for Tier-1 clearance."""
        result = engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_1", "decision": "AUTO_CLEAR"},
        )
        assert result.result == CheckResult.PASS

    def test_inv_001_tier_2_clear_fails(self, engine):
        """Test INV-AML-001 fails for Tier-2 clearance."""
        result = engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_2", "decision": "AUTO_CLEAR"},
            case_id="CASE-001",
        )
        assert result.result == CheckResult.FAIL
        assert result.blocked is True

    def test_inv_001_tier_3_clear_fails(self, engine):
        """Test INV-AML-001 fails for Tier-3 clearance."""
        result = engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_3", "decision": "AUTO_CLEAR"},
        )
        assert result.result == CheckResult.FAIL

    def test_inv_001_tier_sar_clear_fails(self, engine):
        """Test INV-AML-001 fails for Tier-SAR clearance."""
        result = engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_SAR", "decision": "AUTO_CLEAR"},
        )
        assert result.result == CheckResult.FAIL

    def test_inv_001_tier_2_escalate_passes(self, engine):
        """Test INV-AML-001 passes for Tier-2 escalation."""
        result = engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_2", "decision": "ESCALATE"},
        )
        assert result.result == CheckResult.PASS

    # ───────────────────────────────────────────────────────────────────────────
    # INV-AML-002: No Auto SAR
    # ───────────────────────────────────────────────────────────────────────────

    def test_inv_002_system_sar_fails(self, engine):
        """Test INV-AML-002 fails for system SAR filing."""
        result = engine.check_invariant(
            "INV-AML-002",
            {"action": "FILE_SAR", "actor": "SYSTEM"},
        )
        assert result.result == CheckResult.FAIL
        assert result.blocked is True

    def test_inv_002_human_sar_passes(self, engine):
        """Test INV-AML-002 passes for human SAR filing."""
        result = engine.check_invariant(
            "INV-AML-002",
            {"action": "FILE_SAR", "actor": "USER-001"},
        )
        assert result.result == CheckResult.PASS

    def test_inv_002_non_sar_passes(self, engine):
        """Test INV-AML-002 passes for non-SAR actions."""
        result = engine.check_invariant(
            "INV-AML-002",
            {"action": "ESCALATE", "actor": "SYSTEM"},
        )
        assert result.result == CheckResult.PASS

    # ───────────────────────────────────────────────────────────────────────────
    # INV-AML-003: Confidence Threshold
    # ───────────────────────────────────────────────────────────────────────────

    def test_inv_003_high_confidence_passes(self, engine):
        """Test INV-AML-003 passes for high confidence."""
        result = engine.check_invariant(
            "INV-AML-003",
            {"decision": "AUTO_CLEAR", "confidence": 0.98},
        )
        assert result.result == CheckResult.PASS

    def test_inv_003_threshold_confidence_passes(self, engine):
        """Test INV-AML-003 passes at threshold."""
        result = engine.check_invariant(
            "INV-AML-003",
            {"decision": "AUTO_CLEAR", "confidence": 0.95},
        )
        assert result.result == CheckResult.PASS

    def test_inv_003_low_confidence_fails(self, engine):
        """Test INV-AML-003 fails for low confidence."""
        result = engine.check_invariant(
            "INV-AML-003",
            {"decision": "AUTO_CLEAR", "confidence": 0.80},
        )
        assert result.result == CheckResult.FAIL

    def test_inv_003_non_clear_passes(self, engine):
        """Test INV-AML-003 passes for non-clear decisions."""
        result = engine.check_invariant(
            "INV-AML-003",
            {"decision": "ESCALATE", "confidence": 0.50},
        )
        assert result.result == CheckResult.PASS

    # ───────────────────────────────────────────────────────────────────────────
    # INV-AML-004: Sanctions Block
    # ───────────────────────────────────────────────────────────────────────────

    def test_inv_004_sanctions_hit_clear_fails(self, engine):
        """Test INV-AML-004 fails for sanctions hit clearance."""
        result = engine.check_invariant(
            "INV-AML-004",
            {"sanctions_hit": True, "decision": "AUTO_CLEAR"},
        )
        assert result.result == CheckResult.FAIL

    def test_inv_004_sanctions_hit_escalate_passes(self, engine):
        """Test INV-AML-004 passes for sanctions hit escalation."""
        result = engine.check_invariant(
            "INV-AML-004",
            {"sanctions_hit": True, "decision": "ESCALATE"},
        )
        assert result.result == CheckResult.PASS

    def test_inv_004_no_sanctions_passes(self, engine):
        """Test INV-AML-004 passes with no sanctions hit."""
        result = engine.check_invariant(
            "INV-AML-004",
            {"sanctions_hit": False, "decision": "AUTO_CLEAR"},
        )
        assert result.result == CheckResult.PASS

    # ───────────────────────────────────────────────────────────────────────────
    # BATCH CHECKING
    # ───────────────────────────────────────────────────────────────────────────

    def test_check_all_passes(self, engine):
        """Test check_all when all pass."""
        result = engine.check_all({
            "tier": "TIER_0",
            "decision": "AUTO_CLEAR",
            "confidence": 0.98,
            "sanctions_hit": False,
            "pep_associated": False,
            "adverse_media_hit": False,
            "prohibited_jurisdiction": False,
            "has_decision": True,
            "evidence_count": 1,
            "audit_entry_exists": True,
            "has_narrative": True,
            "case_age_hours": 24,
        })
        assert result["all_passed"] is True
        assert result["blocked"] is False

    def test_check_all_with_violation(self, engine):
        """Test check_all with violations."""
        result = engine.check_all({
            "tier": "TIER_2",
            "decision": "AUTO_CLEAR",
            "confidence": 0.98,
        }, case_id="CASE-001")
        assert result["all_passed"] is False
        assert result["blocked"] is True
        assert len(result["blocking_violations"]) > 0

    def test_check_clearance_decision_permitted(self, engine):
        """Test clearance decision check when permitted."""
        result = engine.check_clearance_decision(
            case_id="CASE-001",
            tier="TIER_0",
            decision="AUTO_CLEAR",
            confidence=0.98,
            context={"evidence_count": 1},
        )
        assert result["decision_allowed"] is True

    def test_check_clearance_decision_blocked(self, engine):
        """Test clearance decision check when blocked."""
        result = engine.check_clearance_decision(
            case_id="CASE-001",
            tier="TIER_2",
            decision="AUTO_CLEAR",
            confidence=0.98,
            context={},
        )
        assert result["decision_allowed"] is False
        assert "INV-AML-001" in result["blocking_invariants"]

    # ───────────────────────────────────────────────────────────────────────────
    # VIOLATIONS
    # ───────────────────────────────────────────────────────────────────────────

    def test_violations_recorded(self, engine):
        """Test violations are recorded."""
        engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_2", "decision": "AUTO_CLEAR"},
            case_id="CASE-001",
        )
        violations = engine.list_violations()
        assert len(violations) > 0

    def test_get_violations_for_case(self, engine):
        """Test getting violations for specific case."""
        engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_2", "decision": "AUTO_CLEAR"},
            case_id="CASE-001",
        )
        engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_3", "decision": "AUTO_CLEAR"},
            case_id="CASE-002",
        )
        violations = engine.get_violations_for_case("CASE-001")
        assert len(violations) == 1
        assert violations[0].case_id == "CASE-001"

    def test_get_critical_violations(self, engine):
        """Test getting critical violations."""
        engine.check_invariant(
            "INV-AML-001",
            {"tier": "TIER_2", "decision": "AUTO_CLEAR"},
            case_id="CASE-001",
        )
        critical = engine.get_critical_violations()
        assert len(critical) > 0
        assert all(v.severity == InvariantSeverity.CRITICAL for v in critical)

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def test_generate_report(self, engine):
        """Test report generation."""
        report = engine.generate_report()
        assert "timestamp" in report
        assert "total_invariants" in report
        assert "violations_by_severity" in report


# ═══════════════════════════════════════════════════════════════════════════════
# CHECK RESULT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvariantCheckResult:
    """Tests for InvariantCheckResult data class."""

    def test_check_result_creation(self):
        """Test valid check result creation."""
        result = InvariantCheckResult(
            check_id="CHK-00000001",
            invariant_id="INV-AML-001",
            result=CheckResult.PASS,
            timestamp="2025-01-01T00:00:00Z",
            context={"tier": "TIER_0"},
            message="",
        )
        assert result.check_id == "CHK-00000001"
        assert result.result == CheckResult.PASS

    def test_check_id_validation(self):
        """Test check ID must start with CHK-."""
        with pytest.raises(ValueError, match="Check ID must start with 'CHK-'"):
            InvariantCheckResult(
                check_id="INVALID",
                invariant_id="INV-AML-001",
                result=CheckResult.PASS,
                timestamp="2025-01-01T00:00:00Z",
                context={},
                message="",
            )


class TestInvariantViolation:
    """Tests for InvariantViolation data class."""

    def test_violation_creation(self):
        """Test valid violation creation."""
        violation = InvariantViolation(
            violation_id="VINV-00000001",
            invariant_id="INV-AML-001",
            case_id="CASE-001",
            timestamp="2025-01-01T00:00:00Z",
            severity=InvariantSeverity.CRITICAL,
            context={"tier": "TIER_2"},
            action_blocked=True,
        )
        assert violation.violation_id == "VINV-00000001"
        assert violation.action_blocked is True

    def test_violation_id_validation(self):
        """Test violation ID must start with VINV-."""
        with pytest.raises(ValueError, match="Violation ID must start with 'VINV-'"):
            InvariantViolation(
                violation_id="INVALID",
                invariant_id="INV-AML-001",
                case_id="CASE-001",
                timestamp="2025-01-01T00:00:00Z",
                severity=InvariantSeverity.HIGH,
                context={},
                action_blocked=False,
            )
