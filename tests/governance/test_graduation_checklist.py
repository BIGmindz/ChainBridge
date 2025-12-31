# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite — Graduation Checklist Tests
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for core/governance/graduation_checklist.py

Coverage:
- ChecklistStatus, ChecklistCategory, GraduationPhase enums
- ChecklistItem dataclass
- GraduationResult dataclass
- Pre-defined checklist items (GC-001..GC-010)
- GraduationChecklist class
"""

import pytest

from core.governance.graduation_checklist import (
    GC_001,
    GC_002,
    GC_003,
    GC_004,
    GC_005,
    GC_006,
    GC_007,
    GC_008,
    GC_009,
    GC_010,
    ChecklistCategory,
    ChecklistItem,
    ChecklistStatus,
    GraduationChecklist,
    GraduationPhase,
    GraduationResult,
)


class TestChecklistEnums:
    """Tests for checklist enums."""

    def test_checklist_status_values(self) -> None:
        """Test ChecklistStatus values."""
        assert ChecklistStatus.HOLD.value == "HOLD"
        assert ChecklistStatus.FROZEN.value == "FROZEN"
        assert ChecklistStatus.PASSED.value == "PASSED"
        assert ChecklistStatus.WAIVED.value == "WAIVED"

    def test_checklist_category_values(self) -> None:
        """Test ChecklistCategory values."""
        assert ChecklistCategory.INVARIANT.value == "INVARIANT"
        assert ChecklistCategory.BENCHMARK.value == "BENCHMARK"
        assert ChecklistCategory.SECURITY.value == "SECURITY"
        assert ChecklistCategory.OPERATIONS.value == "OPERATIONS"
        assert ChecklistCategory.GOVERNANCE.value == "GOVERNANCE"

    def test_graduation_phase_values(self) -> None:
        """Test GraduationPhase values."""
        assert GraduationPhase.PRE_CHECK.value == "PRE_CHECK"
        assert GraduationPhase.EVALUATION.value == "EVALUATION"
        assert GraduationPhase.APPROVAL.value == "APPROVAL"
        assert GraduationPhase.EXECUTION.value == "EXECUTION"
        assert GraduationPhase.COMPLETE.value == "COMPLETE"
        assert GraduationPhase.ABORTED.value == "ABORTED"


class TestChecklistItem:
    """Tests for ChecklistItem dataclass."""

    def test_valid_item_creation(self) -> None:
        """Test valid item creation."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test Item",
            description="A test checklist item",
            category=ChecklistCategory.BENCHMARK,
        )

        assert item.item_id == "GC-TEST"
        assert item.status == ChecklistStatus.HOLD

    def test_invalid_item_id(self) -> None:
        """Test invalid item ID."""
        with pytest.raises(ValueError, match="must start with 'GC-'"):
            ChecklistItem(
                item_id="INVALID",
                name="Test",
                description="Test",
                category=ChecklistCategory.BENCHMARK,
            )

    def test_item_properties(self) -> None:
        """Test item properties."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test",
            description="Test",
            category=ChecklistCategory.BENCHMARK,
            required=True,
        )

        # HOLD is blocking
        assert item.is_blocking
        assert not item.is_cleared

        # PASSED is cleared
        item.status = ChecklistStatus.PASSED
        assert not item.is_blocking
        assert item.is_cleared

        # WAIVED is also cleared
        item.status = ChecklistStatus.WAIVED
        assert not item.is_blocking
        assert item.is_cleared

    def test_mark_passed(self) -> None:
        """Test marking item as passed."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test",
            description="Test",
            category=ChecklistCategory.BENCHMARK,
        )

        item.mark_passed("evaluator@example.com", {"evidence": "test"}, "Verified")

        assert item.status == ChecklistStatus.PASSED
        assert item.evaluator == "evaluator@example.com"
        assert item.evaluated_at is not None
        assert item.evidence["evidence"] == "test"
        assert item.notes == "Verified"

    def test_mark_frozen(self) -> None:
        """Test freezing item."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test",
            description="Test",
            category=ChecklistCategory.BENCHMARK,
        )

        item.mark_frozen("Blocking issue found")

        assert item.status == ChecklistStatus.FROZEN
        assert item.notes == "Blocking issue found"

    def test_mark_waived(self) -> None:
        """Test waiving item."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test",
            description="Test",
            category=ChecklistCategory.BENCHMARK,
        )

        item.mark_waived("approver@example.com", "Not applicable")

        assert item.status == ChecklistStatus.WAIVED
        assert "WAIVED" in item.notes
        assert item.evaluator == "approver@example.com"

    def test_reset(self) -> None:
        """Test resetting item."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test",
            description="Test",
            category=ChecklistCategory.BENCHMARK,
        )

        item.mark_passed("eval", {})
        item.reset()

        assert item.status == ChecklistStatus.HOLD
        assert item.evaluator is None
        assert item.evaluated_at is None

    def test_to_dict(self) -> None:
        """Test item serialization."""
        item = ChecklistItem(
            item_id="GC-TEST",
            name="Test Item",
            description="A test item",
            category=ChecklistCategory.SECURITY,
            invariant_ref="INV-READY-001",
        )

        data = item.to_dict()

        assert data["item_id"] == "GC-TEST"
        assert data["category"] == "SECURITY"
        assert data["invariant_ref"] == "INV-READY-001"


class TestGraduationResult:
    """Tests for GraduationResult dataclass."""

    def test_valid_result_creation(self) -> None:
        """Test valid result creation."""
        result = GraduationResult(
            result_id="GRAD-000001",
            phase=GraduationPhase.COMPLETE,
            success=True,
            timestamp="2025-01-01T00:00:00Z",
            from_level="SHADOW",
            to_level="PILOT",
        )

        assert result.result_id == "GRAD-000001"
        assert result.success

    def test_invalid_result_id(self) -> None:
        """Test invalid result ID."""
        with pytest.raises(ValueError, match="must start with 'GRAD-'"):
            GraduationResult(
                result_id="INVALID",
                phase=GraduationPhase.COMPLETE,
                success=True,
                timestamp="2025-01-01T00:00:00Z",
                from_level="SHADOW",
                to_level="PILOT",
            )

    def test_result_hash(self) -> None:
        """Test result hash computation."""
        result = GraduationResult(
            result_id="GRAD-000001",
            phase=GraduationPhase.COMPLETE,
            success=True,
            timestamp="2025-01-01T00:00:00Z",
            from_level="SHADOW",
            to_level="PILOT",
            cleared_items=["GC-001", "GC-002"],
        )

        hash1 = result.compute_hash()
        hash2 = result.compute_hash()
        assert hash1 == hash2

    def test_to_dict(self) -> None:
        """Test result serialization."""
        result = GraduationResult(
            result_id="GRAD-000001",
            phase=GraduationPhase.ABORTED,
            success=False,
            timestamp="2025-01-01T00:00:00Z",
            from_level="SHADOW",
            to_level="SHADOW",
            blocking_items=["GC-003"],
        )

        data = result.to_dict()

        assert data["result_id"] == "GRAD-000001"
        assert data["success"] is False
        assert "GC-003" in data["blocking_items"]
        assert "result_hash" in data


class TestPreDefinedItems:
    """Tests for pre-defined checklist items."""

    def test_gc_001(self) -> None:
        """Test GC-001 definition."""
        assert GC_001.item_id == "GC-001"
        assert GC_001.invariant_ref == "INV-READY-001"
        assert GC_001.category == ChecklistCategory.INVARIANT

    def test_gc_002(self) -> None:
        """Test GC-002 definition."""
        assert GC_002.item_id == "GC-002"
        assert GC_002.invariant_ref == "INV-READY-002"

    def test_gc_003(self) -> None:
        """Test GC-003 definition."""
        assert GC_003.item_id == "GC-003"
        assert GC_003.invariant_ref == "INV-READY-003"

    def test_gc_004(self) -> None:
        """Test GC-004 definition."""
        assert GC_004.item_id == "GC-004"
        assert GC_004.invariant_ref == "INV-READY-004"

    def test_gc_005(self) -> None:
        """Test GC-005 definition."""
        assert GC_005.item_id == "GC-005"
        assert GC_005.invariant_ref == "INV-READY-005"

    def test_gc_006(self) -> None:
        """Test GC-006 definition."""
        assert GC_006.item_id == "GC-006"
        assert GC_006.invariant_ref == "INV-READY-006"

    def test_gc_007(self) -> None:
        """Test GC-007 definition."""
        assert GC_007.item_id == "GC-007"
        assert GC_007.category == ChecklistCategory.BENCHMARK

    def test_gc_008(self) -> None:
        """Test GC-008 definition."""
        assert GC_008.item_id == "GC-008"
        assert GC_008.category == ChecklistCategory.SECURITY

    def test_gc_009(self) -> None:
        """Test GC-009 definition."""
        assert GC_009.item_id == "GC-009"
        assert GC_009.category == ChecklistCategory.OPERATIONS

    def test_gc_010(self) -> None:
        """Test GC-010 definition."""
        assert GC_010.item_id == "GC-010"
        assert GC_010.category == ChecklistCategory.GOVERNANCE


class TestGraduationChecklist:
    """Tests for GraduationChecklist class."""

    def test_checklist_creation(self) -> None:
        """Test checklist creation with defaults."""
        checklist = GraduationChecklist()
        assert len(checklist.list_all()) == 10  # 10 default items

    def test_register_item(self) -> None:
        """Test registering custom item."""
        checklist = GraduationChecklist()

        custom = ChecklistItem(
            item_id="GC-CUSTOM",
            name="Custom Item",
            description="A custom item",
            category=ChecklistCategory.GOVERNANCE,
        )

        checklist.register(custom)
        assert checklist.get("GC-CUSTOM") is not None

    def test_list_blocking(self) -> None:
        """Test listing blocking items."""
        checklist = GraduationChecklist()

        blocking = checklist.list_blocking()
        # All defaults start as HOLD (blocking)
        assert len(blocking) == 10

    def test_list_cleared(self) -> None:
        """Test listing cleared items."""
        checklist = GraduationChecklist()

        cleared = checklist.list_cleared()
        # None cleared initially
        assert len(cleared) == 0

    def test_list_by_category(self) -> None:
        """Test listing by category."""
        checklist = GraduationChecklist()

        invariant_items = checklist.list_by_category(ChecklistCategory.INVARIANT)
        assert len(invariant_items) == 6  # GC-001 through GC-006

    def test_completion_rate(self) -> None:
        """Test completion rate calculation."""
        checklist = GraduationChecklist()

        # Initially 0%
        assert checklist.get_completion_rate() == 0.0

        # Pass one item
        item = checklist.get("GC-001")
        item.mark_passed("evaluator", {})

        # 10% (1 of 10)
        assert checklist.get_completion_rate() == 0.1

    def test_is_ready_to_graduate(self) -> None:
        """Test graduation readiness."""
        checklist = GraduationChecklist()

        # Initially not ready
        assert not checklist.is_ready_to_graduate()

    def test_attempt_graduation_blocked(self) -> None:
        """Test graduation attempt when blocked."""
        checklist = GraduationChecklist()

        result = checklist.attempt_graduation("SHADOW", "PILOT", "operator")

        assert not result.success
        assert result.phase == GraduationPhase.ABORTED
        assert len(result.blocking_items) == 10

    def test_attempt_graduation_success(self) -> None:
        """Test graduation attempt when ready."""
        checklist = GraduationChecklist()

        # Pass all items
        for item in checklist.list_all():
            item.mark_passed("evaluator", {})

        result = checklist.attempt_graduation("SHADOW", "PILOT", "operator")

        assert result.success
        assert result.phase == GraduationPhase.COMPLETE
        assert result.to_level == "PILOT"
        assert len(result.cleared_items) == 10
        assert len(result.blocking_items) == 0

    def test_reset_all(self) -> None:
        """Test resetting all items."""
        checklist = GraduationChecklist()

        # Pass some items
        checklist.get("GC-001").mark_passed("eval", {})
        checklist.get("GC-002").mark_passed("eval", {})

        checklist.reset_all()

        assert checklist.get_completion_rate() == 0.0
        assert len(checklist.list_blocking()) == 10

    def test_freeze_all(self) -> None:
        """Test freezing all items."""
        checklist = GraduationChecklist()

        checklist.freeze_all("Emergency freeze")

        for item in checklist.list_all():
            assert item.status == ChecklistStatus.FROZEN

    def test_generate_report(self) -> None:
        """Test report generation."""
        checklist = GraduationChecklist()

        report = checklist.generate_report()

        assert "timestamp" in report
        assert "completion_rate" in report
        assert "items" in report
        assert "blocking_details" in report
        assert report["total_items"] == 10

    def test_compute_state_hash(self) -> None:
        """Test state hash computation."""
        checklist = GraduationChecklist()

        hash1 = checklist.compute_state_hash()

        # Change state
        checklist.get("GC-001").mark_passed("eval", {})
        hash2 = checklist.compute_state_hash()

        # Hashes should differ
        assert hash1 != hash2


class TestIntegration:
    """Integration tests for graduation checklist."""

    def test_full_graduation_workflow(self) -> None:
        """Test complete graduation workflow."""
        checklist = GraduationChecklist()

        # Initial state - blocked
        assert not checklist.is_ready_to_graduate()
        assert checklist.get_completion_rate() == 0.0

        # Pass invariant items
        for item_id in ["GC-001", "GC-002", "GC-003", "GC-004", "GC-005", "GC-006"]:
            item = checklist.get(item_id)
            item.mark_passed("alex", {"verified": True})

        # Still blocked - need benchmark, security, ops, governance
        assert not checklist.is_ready_to_graduate()
        assert checklist.get_completion_rate() == 0.6

        # Pass remaining items
        checklist.get("GC-007").mark_passed("dan", {})  # Benchmark
        checklist.get("GC-008").mark_passed("sam", {})  # Security
        checklist.get("GC-009").mark_passed("pax", {})  # Operations
        checklist.get("GC-010").mark_passed("operator", {})  # Signoff

        # Now ready
        assert checklist.is_ready_to_graduate()
        assert checklist.get_completion_rate() == 1.0

        # Attempt graduation
        result = checklist.attempt_graduation("SHADOW", "PILOT", "benson")

        assert result.success
        assert result.to_level == "PILOT"
        assert len(result.cleared_items) == 10

    def test_partial_waiver_scenario(self) -> None:
        """Test scenario with waived items."""
        checklist = GraduationChecklist()

        # Pass most items
        for item_id in ["GC-001", "GC-002", "GC-003", "GC-004", "GC-005", "GC-006", "GC-007", "GC-008", "GC-010"]:
            checklist.get(item_id).mark_passed("evaluator", {})

        # Waive ops item
        checklist.get("GC-009").mark_waived("cto", "Rollback handled by K8s")

        # Should be ready (waived counts as cleared)
        assert checklist.is_ready_to_graduate()

        result = checklist.attempt_graduation("SHADOW", "PILOT")
        assert result.success
        assert "GC-009" in result.waived_items
