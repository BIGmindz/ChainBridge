# ═══════════════════════════════════════════════════════════════════════════════
# Memory Invariants Tests — INV-MEM-* Governance Tests
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Memory Invariants Tests — Comprehensive governance rule tests for INV-MEM-*.
"""

import pytest

from core.governance.memory_invariants import (
    EnforcementMode,
    InvariantCategory,
    InvariantViolationError,
    MemoryInvariant,
    MemoryInvariantRegistry,
    ViolationRecord,
    ViolationSeverity,
    check_frozen_protection,
    check_no_production_learning,
    check_shadow_mode_inference,
    check_snapshot_immutability,
    register_default_checks,
    INV_MEM_001,
    INV_MEM_002,
    INV_MEM_003,
    INV_MEM_004,
    INV_MEM_005,
    INV_MEM_006,
    INV_MEM_007,
    INV_MEM_008,
    INV_MEM_009,
    INV_MEM_010,
    INV_MEM_011,
    INV_MEM_012,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryInvariant:
    """Tests for MemoryInvariant dataclass."""

    def test_valid_invariant_creation(self) -> None:
        """Test creating a valid invariant."""
        inv = MemoryInvariant(
            invariant_id="INV-MEM-TEST",
            name="Test Invariant",
            description="A test invariant",
            category=InvariantCategory.STATE_INTEGRITY,
            severity=ViolationSeverity.HIGH,
        )
        assert inv.invariant_id == "INV-MEM-TEST"
        assert inv.enforcement == EnforcementMode.STRICT  # default

    def test_invalid_id_raises(self) -> None:
        """Test that invalid ID format raises error."""
        with pytest.raises(ValueError):
            MemoryInvariant(
                invariant_id="INVALID-001",
                name="Test",
                description="Test",
                category=InvariantCategory.STATE_INTEGRITY,
                severity=ViolationSeverity.HIGH,
            )

    def test_pdo_bound_default_false(self) -> None:
        """Test that pdo_bound defaults to False."""
        inv = MemoryInvariant(
            invariant_id="INV-MEM-TEST",
            name="Test",
            description="Test",
            category=InvariantCategory.STATE_INTEGRITY,
            severity=ViolationSeverity.HIGH,
        )
        assert inv.pdo_bound is False


class TestPredefinedInvariants:
    """Tests for predefined INV-MEM-* invariants."""

    def test_inv_mem_001_properties(self) -> None:
        """Test INV-MEM-001 Snapshot Immutability."""
        assert INV_MEM_001.invariant_id == "INV-MEM-001"
        assert INV_MEM_001.category == InvariantCategory.STATE_INTEGRITY
        assert INV_MEM_001.severity == ViolationSeverity.CRITICAL
        assert INV_MEM_001.pdo_bound is True

    def test_inv_mem_002_properties(self) -> None:
        """Test INV-MEM-002 Update Audit Trail."""
        assert INV_MEM_002.invariant_id == "INV-MEM-002"
        assert INV_MEM_002.category == InvariantCategory.AUDIT_TRAIL
        assert INV_MEM_002.enforcement == EnforcementMode.STRICT

    def test_inv_mem_006_properties(self) -> None:
        """Test INV-MEM-006 No Production Learning."""
        assert INV_MEM_006.invariant_id == "INV-MEM-006"
        assert INV_MEM_006.category == InvariantCategory.SHADOW_MODE
        assert INV_MEM_006.severity == ViolationSeverity.CRITICAL

    def test_inv_mem_010_properties(self) -> None:
        """Test INV-MEM-010 No Inference Execution."""
        assert INV_MEM_010.invariant_id == "INV-MEM-010"
        assert INV_MEM_010.category == InvariantCategory.SHADOW_MODE

    def test_all_invariants_have_unique_ids(self) -> None:
        """Test that all predefined invariants have unique IDs."""
        invariants = [
            INV_MEM_001, INV_MEM_002, INV_MEM_003,
            INV_MEM_004, INV_MEM_005, INV_MEM_006,
            INV_MEM_007, INV_MEM_008, INV_MEM_009,
            INV_MEM_010, INV_MEM_011, INV_MEM_012,
        ]
        ids = [inv.invariant_id for inv in invariants]
        assert len(ids) == len(set(ids))


# ═══════════════════════════════════════════════════════════════════════════════
# VIOLATION RECORD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestViolationRecord:
    """Tests for ViolationRecord."""

    def test_create_violation_record(self) -> None:
        """Test creating a violation record."""
        record = ViolationRecord(
            violation_id="VIOL-MEM-000001",
            invariant_id="INV-MEM-001",
            severity=ViolationSeverity.CRITICAL,
            context={"message": "Test violation"},
        )
        assert record.resolved is False
        assert record.resolution_note is None

    def test_compute_hash(self) -> None:
        """Test violation hash computation."""
        record = ViolationRecord(
            violation_id="VIOL-MEM-000001",
            invariant_id="INV-MEM-001",
            severity=ViolationSeverity.CRITICAL,
            context={"message": "Test"},
        )
        hash_value = record.compute_hash()
        assert hash_value is not None
        assert len(hash_value) == 64


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY INVARIANT REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryInvariantRegistry:
    """Tests for MemoryInvariantRegistry."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton between tests."""
        MemoryInvariantRegistry._instance = None
        MemoryInvariantRegistry._initialized = False

    def test_singleton_pattern(self) -> None:
        """Test registry is singleton."""
        registry1 = MemoryInvariantRegistry()
        registry2 = MemoryInvariantRegistry()
        assert registry1 is registry2

    def test_p26_invariants_registered(self) -> None:
        """Test that P26 invariants are auto-registered."""
        registry = MemoryInvariantRegistry()
        assert registry.count() == 12  # INV-MEM-001 through 012

    def test_get_invariant(self) -> None:
        """Test getting invariant by ID."""
        registry = MemoryInvariantRegistry()
        inv = registry.get("INV-MEM-001")
        assert inv is not None
        assert inv.name == "Snapshot Immutability"

    def test_list_all(self) -> None:
        """Test listing all invariants."""
        registry = MemoryInvariantRegistry()
        all_invs = registry.list_all()
        assert len(all_invs) == 12

    def test_list_by_category(self) -> None:
        """Test filtering by category."""
        registry = MemoryInvariantRegistry()

        state_invs = registry.list_by_category(InvariantCategory.STATE_INTEGRITY)
        assert len(state_invs) >= 2  # INV-MEM-001, 003

        shadow_invs = registry.list_by_category(InvariantCategory.SHADOW_MODE)
        assert len(shadow_invs) == 4  # INV-MEM-006, 010, 011, 012

    def test_list_pdo_bound(self) -> None:
        """Test listing PDO-bound invariants."""
        registry = MemoryInvariantRegistry()
        pdo_invs = registry.list_pdo_bound()
        assert len(pdo_invs) >= 4  # At least 001, 002, 003, 009

    def test_register_check_function(self) -> None:
        """Test registering check function."""
        registry = MemoryInvariantRegistry()

        def custom_check(context: dict) -> tuple:
            return True, "OK"

        result = registry.register_check("INV-MEM-001", custom_check)
        assert result is True

    def test_register_check_unknown_invariant(self) -> None:
        """Test registering check for unknown invariant fails."""
        registry = MemoryInvariantRegistry()

        def custom_check(context: dict) -> tuple:
            return True, "OK"

        result = registry.register_check("INV-MEM-999", custom_check)
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# CHECK FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCheckFunctions:
    """Tests for invariant check functions."""

    def test_snapshot_immutability_pass(self) -> None:
        """Test snapshot immutability check passes."""
        context = {"snapshot": {"id": "test"}}
        passed, message = check_snapshot_immutability(context)
        assert passed is True

    def test_snapshot_immutability_fail(self) -> None:
        """Test snapshot immutability check fails on modification."""
        context = {
            "snapshot": {"id": "test"},
            "original_hash": "abc123",
            "current_hash": "def456",
        }
        passed, message = check_snapshot_immutability(context)
        assert passed is False
        assert "modified" in message.lower()

    def test_frozen_protection_pass(self) -> None:
        """Test frozen protection check passes."""
        context = {"is_frozen": True, "is_update_attempt": False}
        passed, message = check_frozen_protection(context)
        assert passed is True

    def test_frozen_protection_fail(self) -> None:
        """Test frozen protection check fails."""
        context = {"is_frozen": True, "is_update_attempt": True}
        passed, message = check_frozen_protection(context)
        assert passed is False
        assert "frozen" in message.lower()

    def test_no_production_learning_pass(self) -> None:
        """Test no production learning check passes."""
        context = {"environment": "production", "is_learning": False}
        passed, message = check_no_production_learning(context)
        assert passed is True

    def test_no_production_learning_fail(self) -> None:
        """Test no production learning check fails."""
        context = {"environment": "production", "is_learning": True}
        passed, message = check_no_production_learning(context)
        assert passed is False

    def test_shadow_mode_inference_pass(self) -> None:
        """Test shadow mode inference check passes."""
        context = {"mode": "SHADOW", "has_inference_execution": False}
        passed, message = check_shadow_mode_inference(context)
        assert passed is True

    def test_shadow_mode_inference_fail(self) -> None:
        """Test shadow mode inference check fails."""
        context = {"mode": "SHADOW", "has_inference_execution": True}
        passed, message = check_shadow_mode_inference(context)
        assert passed is False


# ═══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnforcement:
    """Tests for invariant enforcement."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton between tests."""
        MemoryInvariantRegistry._instance = None
        MemoryInvariantRegistry._initialized = False

    def test_check_with_registered_function(self) -> None:
        """Test checking invariant with registered function."""
        registry = MemoryInvariantRegistry()
        register_default_checks(registry)

        context = {"is_frozen": False, "is_update_attempt": True}
        passed, error = registry.check("INV-MEM-004", context)
        assert passed is True

    def test_check_without_function_passes(self) -> None:
        """Test that check without function defaults to pass."""
        registry = MemoryInvariantRegistry()
        # Don't register any checks

        passed, error = registry.check("INV-MEM-007", {})
        assert passed is True

    def test_check_unknown_invariant(self) -> None:
        """Test checking unknown invariant fails."""
        registry = MemoryInvariantRegistry()
        passed, error = registry.check("INV-MEM-999", {})
        assert passed is False
        assert "Unknown invariant" in error

    def test_violation_count(self) -> None:
        """Test violation counting."""
        registry = MemoryInvariantRegistry()
        assert registry.violation_count() == 0
