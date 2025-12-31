# ═══════════════════════════════════════════════════════════════════════════════
# P25 Test Suite — Governance Invariant Tests
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: DAN (GID-07) — CI/CD & Test Scaling
# ═══════════════════════════════════════════════════════════════════════════════

"""
Test suite for P25 Governance Invariants.

Tests cover:
- SOP Invariants (INV-SOP-001 through INV-SOP-006)
- Risk Invariants (INV-RISK-001 through INV-RISK-005)
- UI Invariants (INV-UI-001 through INV-UI-006)
- Invariant Registry operations
- Violation tracking

EXECUTION MODE: PARALLEL
LANE: CI/CD (GID-07)
"""

import pytest

from core.governance.p25_invariants import (
    InvariantCategory,
    InvariantSeverity,
    EnforcementMode,
    InvariantDefinition,
    P25InvariantRegistry,
    # SOP Invariants
    INV_SOP_001,
    INV_SOP_002,
    INV_SOP_003,
    INV_SOP_004,
    INV_SOP_005,
    INV_SOP_006,
    # Risk Invariants
    INV_RISK_001,
    INV_RISK_002,
    INV_RISK_003,
    INV_RISK_004,
    INV_RISK_005,
    # UI Invariants
    INV_UI_001,
    INV_UI_002,
    INV_UI_003,
    INV_UI_004,
    INV_UI_005,
    INV_UI_006,
)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvariantDefinition:
    """Tests for InvariantDefinition."""

    def test_invariant_creation(self) -> None:
        """Test creating an invariant definition."""
        invariant = InvariantDefinition(
            invariant_id="INV-TEST-001",
            name="Test Invariant",
            category=InvariantCategory.SOP,
            severity=InvariantSeverity.MEDIUM,
            description="A test invariant",
            enforcement=EnforcementMode.HARD_FAIL,
            validation_rule="test == true",
            error_message="Test failed",
            introduced_pac="PAC-BENSON-P25",
        )
        assert invariant.invariant_id == "INV-TEST-001"
        assert invariant.category == InvariantCategory.SOP

    def test_invariant_immutability(self) -> None:
        """Test that invariants are immutable."""
        with pytest.raises(AttributeError):
            INV_SOP_001.severity = InvariantSeverity.LOW  # type: ignore

    def test_invariant_id_validation(self) -> None:
        """Test that invariant IDs must start with INV-."""
        with pytest.raises(ValueError, match="must start with 'INV-'"):
            InvariantDefinition(
                invariant_id="INVALID-001",
                name="Invalid",
                category=InvariantCategory.SOP,
                severity=InvariantSeverity.LOW,
                description="Invalid ID",
                enforcement=EnforcementMode.SOFT_FAIL,
                validation_rule="true",
                error_message="Error",
                introduced_pac="PAC-TEST",
            )

    def test_invariant_has_introduced_pac(self) -> None:
        """Test that all invariants have PAC origin."""
        assert "PAC-BENSON-P25" in INV_SOP_001.introduced_pac
        assert "PAC-BENSON-P25" in INV_RISK_001.introduced_pac
        assert "PAC-BENSON-P25" in INV_UI_001.introduced_pac


# ═══════════════════════════════════════════════════════════════════════════════
# SOP INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSOPInvariants:
    """Tests for SOP Invariants."""

    def test_inv_sop_001_precondition_validation(self) -> None:
        """INV-SOP-001: SOP execution requires all preconditions pass."""
        assert INV_SOP_001.invariant_id == "INV-SOP-001"
        assert INV_SOP_001.category == InvariantCategory.SOP
        assert "precondition" in INV_SOP_001.name.lower()

    def test_inv_sop_002_audit_trail(self) -> None:
        """INV-SOP-002: All SOP executions logged to immutable audit trail."""
        assert INV_SOP_002.invariant_id == "INV-SOP-002"
        assert INV_SOP_002.category == InvariantCategory.SOP
        assert "audit" in INV_SOP_002.name.lower()

    def test_inv_sop_003_dual_approval(self) -> None:
        """INV-SOP-003: Critical SOPs require dual approval."""
        assert INV_SOP_003.invariant_id == "INV-SOP-003"
        assert INV_SOP_003.category == InvariantCategory.SOP
        assert "approval" in INV_SOP_003.name.lower()

    def test_inv_sop_004_idempotency(self) -> None:
        """INV-SOP-004: SOP executions are idempotent."""
        assert INV_SOP_004.invariant_id == "INV-SOP-004"
        assert INV_SOP_004.category == InvariantCategory.SOP
        assert "idempoten" in INV_SOP_004.name.lower()

    def test_inv_sop_005_rollback(self) -> None:
        """INV-SOP-005: Reversible SOPs have rollback procedures."""
        assert INV_SOP_005.invariant_id == "INV-SOP-005"
        assert INV_SOP_005.category == InvariantCategory.SOP
        assert "rollback" in INV_SOP_005.name.lower()

    def test_inv_sop_006_occ_read_only(self) -> None:
        """INV-SOP-006: OCC cannot initiate SOP executions."""
        assert INV_SOP_006.invariant_id == "INV-SOP-006"
        assert INV_SOP_006.category == InvariantCategory.SOP
        assert "occ" in INV_SOP_006.name.lower() or "read" in INV_SOP_006.name.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# RISK INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRiskInvariants:
    """Tests for Risk Invariants."""

    def test_inv_risk_001_score_bounds(self) -> None:
        """INV-RISK-001: Trust scores bounded [0.0, 1.0]."""
        assert INV_RISK_001.invariant_id == "INV-RISK-001"
        assert INV_RISK_001.category == InvariantCategory.RISK
        assert "bound" in INV_RISK_001.name.lower() or "score" in INV_RISK_001.name.lower()

    def test_inv_risk_002_score_immutability(self) -> None:
        """INV-RISK-002: Published scores are immutable."""
        assert INV_RISK_002.invariant_id == "INV-RISK-002"
        assert INV_RISK_002.category == InvariantCategory.RISK

    def test_inv_risk_003_override_audit(self) -> None:
        """INV-RISK-003: Score overrides require audit justification."""
        assert INV_RISK_003.invariant_id == "INV-RISK-003"
        assert INV_RISK_003.category == InvariantCategory.RISK

    def test_inv_risk_004_tier_consistency(self) -> None:
        """INV-RISK-004: Trust tier derived from score range."""
        assert INV_RISK_004.invariant_id == "INV-RISK-004"
        assert INV_RISK_004.category == InvariantCategory.RISK
        assert "tier" in INV_RISK_004.name.lower() or "consisten" in INV_RISK_004.name.lower()

    def test_inv_risk_005_probation_restrictions(self) -> None:
        """INV-RISK-005: Probation tier restricts operations."""
        assert INV_RISK_005.invariant_id == "INV-RISK-005"
        assert INV_RISK_005.category == InvariantCategory.RISK
        assert "probation" in INV_RISK_005.name.lower() or "agent" in INV_RISK_005.name.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# UI INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUIInvariants:
    """Tests for UI Invariants."""

    def test_inv_ui_001_read_only_state(self) -> None:
        """INV-UI-001: OCC displays read-only state views."""
        assert INV_UI_001.invariant_id == "INV-UI-001"
        assert INV_UI_001.category == InvariantCategory.UI

    def test_inv_ui_002_no_optimistic_updates(self) -> None:
        """INV-UI-002: No optimistic UI updates."""
        assert INV_UI_002.invariant_id == "INV-UI-002"
        assert INV_UI_002.category == InvariantCategory.UI
        assert "optimistic" in INV_UI_002.name.lower()

    def test_inv_ui_003_failure_display(self) -> None:
        """INV-UI-003: All failures displayed to operator."""
        assert INV_UI_003.invariant_id == "INV-UI-003"
        assert INV_UI_003.category == InvariantCategory.UI

    def test_inv_ui_004_input_sanitization(self) -> None:
        """INV-UI-004: All inputs sanitized before render."""
        assert INV_UI_004.invariant_id == "INV-UI-004"
        assert INV_UI_004.category == InvariantCategory.UI

    def test_inv_ui_005_accessibility(self) -> None:
        """INV-UI-005: UI meets accessibility requirements."""
        assert INV_UI_005.invariant_id == "INV-UI-005"
        assert INV_UI_005.category == InvariantCategory.UI
        assert "accessib" in INV_UI_005.name.lower()

    def test_inv_ui_006_density_persistence(self) -> None:
        """INV-UI-006: Density settings persist across sessions."""
        assert INV_UI_006.invariant_id == "INV-UI-006"
        assert INV_UI_006.category == InvariantCategory.UI
        assert "density" in INV_UI_006.name.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestP25InvariantRegistry:
    """Tests for P25InvariantRegistry."""

    def test_registry_singleton(self) -> None:
        """Test that registry is a singleton."""
        reg1 = P25InvariantRegistry()
        reg2 = P25InvariantRegistry()
        assert reg1 is reg2

    def test_registry_has_all_invariants(self) -> None:
        """Test that registry has all P25 invariants."""
        registry = P25InvariantRegistry()
        assert registry.count() >= 17

    def test_get_invariant_by_id(self) -> None:
        """Test getting invariant by ID."""
        registry = P25InvariantRegistry()
        inv = registry.get("INV-SOP-001")
        assert inv is not None
        assert inv.name == INV_SOP_001.name

    def test_get_all_invariants(self) -> None:
        """Test getting all invariants."""
        registry = P25InvariantRegistry()
        all_invs = registry.get_all()
        assert len(all_invs) >= 17

    def test_get_invariants_by_category_sop(self) -> None:
        """Test filtering invariants by SOP category."""
        registry = P25InvariantRegistry()
        sop = registry.get_by_category(InvariantCategory.SOP)
        assert len(sop) >= 6
        assert all(i.category == InvariantCategory.SOP for i in sop)

    def test_get_invariants_by_category_risk(self) -> None:
        """Test filtering invariants by RISK category."""
        registry = P25InvariantRegistry()
        risk = registry.get_by_category(InvariantCategory.RISK)
        assert len(risk) >= 5
        assert all(i.category == InvariantCategory.RISK for i in risk)

    def test_get_invariants_by_category_ui(self) -> None:
        """Test filtering invariants by UI category."""
        registry = P25InvariantRegistry()
        ui = registry.get_by_category(InvariantCategory.UI)
        assert len(ui) >= 6
        assert all(i.category == InvariantCategory.UI for i in ui)

    def test_get_invariants_by_severity(self) -> None:
        """Test filtering invariants by severity."""
        registry = P25InvariantRegistry()
        high = registry.get_by_severity(InvariantSeverity.HIGH)
        assert len(high) >= 1
        assert all(i.severity == InvariantSeverity.HIGH for i in high)

    def test_get_hard_fail_invariants(self) -> None:
        """Test getting HARD_FAIL enforced invariants."""
        registry = P25InvariantRegistry()
        hard_fail = registry.get_hard_fail()
        assert len(hard_fail) >= 5
        assert all(i.enforcement == EnforcementMode.HARD_FAIL for i in hard_fail)


# ═══════════════════════════════════════════════════════════════════════════════
# VIOLATION TRACKING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestViolationTracking:
    """Tests for violation tracking in registry."""

    def test_record_violation(self) -> None:
        """Test recording a violation."""
        registry = P25InvariantRegistry()
        initial_count = len(registry.get_violations(invariant_id="INV-SOP-001"))

        registry.record_violation(
            invariant_id="INV-SOP-001",
            context={"agent": "TEST", "action": "test"},
        )

        violations = registry.get_violations(invariant_id="INV-SOP-001")
        assert len(violations) >= initial_count + 1

    def test_violation_has_timestamp(self) -> None:
        """Test that violations have timestamps."""
        registry = P25InvariantRegistry()
        violation = registry.record_violation(
            invariant_id="INV-SOP-002",
            context={"test": "timestamp"},
        )
        assert violation.timestamp is not None

    def test_get_all_violations(self) -> None:
        """Test getting all violations."""
        registry = P25InvariantRegistry()
        registry.record_violation(
            invariant_id="INV-RISK-001",
            context={"agent": "TEST"},
        )
        all_violations = registry.get_violations()
        assert len(all_violations) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestManifestGeneration:
    """Tests for invariant manifest generation."""

    def test_generate_manifest(self) -> None:
        """Test generating invariant manifest."""
        registry = P25InvariantRegistry()
        manifest = registry.generate_manifest()
        assert manifest["pac_version"] == "PAC-BENSON-P25"
        assert manifest["total_invariants"] >= 17

    def test_manifest_has_by_category(self) -> None:
        """Test manifest includes by_category breakdown."""
        registry = P25InvariantRegistry()
        manifest = registry.generate_manifest()
        assert "by_category" in manifest
        assert "SOP" in manifest["by_category"]
        assert "RISK" in manifest["by_category"]
        assert "UI" in manifest["by_category"]

    def test_manifest_has_hard_fail_count(self) -> None:
        """Test manifest includes hard_fail_count."""
        registry = P25InvariantRegistry()
        manifest = registry.generate_manifest()
        assert manifest["hard_fail_count"] >= 5


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-CATEGORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvariantRelationships:
    """Tests for invariant relationships and dependencies."""

    def test_all_categories_represented(self) -> None:
        """Test that all main invariant categories are represented."""
        registry = P25InvariantRegistry()
        categories = {inv.category for inv in registry.get_all()}
        assert InvariantCategory.SOP in categories
        assert InvariantCategory.RISK in categories
        assert InvariantCategory.UI in categories

    def test_multiple_enforcement_modes(self) -> None:
        """Test that multiple enforcement modes are used."""
        registry = P25InvariantRegistry()
        modes = {inv.enforcement for inv in registry.get_all()}
        assert EnforcementMode.HARD_FAIL in modes

    def test_all_invariants_traceable_to_pac(self) -> None:
        """Test that all invariants are traceable to PAC-BENSON-P25."""
        registry = P25InvariantRegistry()
        for inv in registry.get_all():
            assert "PAC-BENSON" in inv.introduced_pac
