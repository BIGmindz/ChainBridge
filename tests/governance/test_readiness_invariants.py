# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite — Readiness Invariants Tests
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for core/governance/readiness_invariants.py

Coverage:
- ReadinessGate, ReadinessLevel, InvariantCategory enums
- ReadinessInvariant dataclass
- Check functions (INV-READY-001..006)
- ReadinessInvariantRegistry
"""

from typing import Dict, Any

import pytest

from core.governance.readiness_invariants import (
    INV_READY_001,
    INV_READY_002,
    INV_READY_003,
    INV_READY_004,
    INV_READY_005,
    INV_READY_006,
    InvariantCategory,
    ReadinessGate,
    ReadinessInvariant,
    ReadinessInvariantRegistry,
    ReadinessLevel,
    check_cost_bounded,
    check_determinism_required,
    check_governance_clearance,
    check_no_live_inference,
    check_routing_coverage,
    check_snapshot_integrity,
)


class TestReadinessEnums:
    """Tests for readiness enums."""

    def test_readiness_gate_values(self) -> None:
        """Test ReadinessGate values."""
        assert ReadinessGate.OPEN.value == "OPEN"
        assert ReadinessGate.CLOSED.value == "CLOSED"
        assert ReadinessGate.PENDING.value == "PENDING"

    def test_readiness_level_values(self) -> None:
        """Test ReadinessLevel values."""
        assert ReadinessLevel.SHADOW.value == "SHADOW"
        assert ReadinessLevel.PILOT.value == "PILOT"
        assert ReadinessLevel.STAGED.value == "STAGED"
        assert ReadinessLevel.LIVE.value == "LIVE"

    def test_invariant_category_values(self) -> None:
        """Test InvariantCategory values."""
        assert InvariantCategory.DETERMINISM.value == "DETERMINISM"
        assert InvariantCategory.SAFETY.value == "SAFETY"
        assert InvariantCategory.INTEGRITY.value == "INTEGRITY"
        assert InvariantCategory.COVERAGE.value == "COVERAGE"
        assert InvariantCategory.COST.value == "COST"
        assert InvariantCategory.GOVERNANCE.value == "GOVERNANCE"


class TestReadinessInvariant:
    """Tests for ReadinessInvariant dataclass."""

    def test_valid_invariant_creation(self) -> None:
        """Test valid invariant creation."""
        invariant = ReadinessInvariant(
            invariant_id="INV-READY-TEST",
            name="Test Invariant",
            description="A test invariant",
            category=InvariantCategory.DETERMINISM,
        )

        assert invariant.invariant_id == "INV-READY-TEST"
        assert invariant.gate == ReadinessGate.PENDING

    def test_invalid_invariant_id(self) -> None:
        """Test invalid invariant ID."""
        with pytest.raises(ValueError, match="must start with 'INV-READY-'"):
            ReadinessInvariant(
                invariant_id="INVALID-001",
                name="Test",
                description="Test",
                category=InvariantCategory.DETERMINISM,
            )

    def test_invariant_properties(self) -> None:
        """Test invariant properties."""
        invariant = ReadinessInvariant(
            invariant_id="INV-READY-TEST",
            name="Test",
            description="Test",
            category=InvariantCategory.DETERMINISM,
            gate=ReadinessGate.PENDING,
        )

        assert not invariant.is_passing
        assert not invariant.is_blocking

        invariant.gate = ReadinessGate.OPEN
        assert invariant.is_passing

        invariant.gate = ReadinessGate.CLOSED
        assert invariant.is_blocking

    def test_invariant_evaluate_with_threshold(self) -> None:
        """Test invariant evaluation with threshold."""
        invariant = ReadinessInvariant(
            invariant_id="INV-READY-TEST",
            name="Test",
            description="Test",
            category=InvariantCategory.DETERMINISM,
            threshold=0.9,
        )

        invariant.actual_value = 0.95
        result = invariant.evaluate({})
        assert result
        assert invariant.gate == ReadinessGate.OPEN

        invariant.actual_value = 0.85
        result = invariant.evaluate({})
        assert not result
        assert invariant.gate == ReadinessGate.CLOSED

    def test_invariant_to_dict(self) -> None:
        """Test invariant serialization."""
        invariant = ReadinessInvariant(
            invariant_id="INV-READY-TEST",
            name="Test Invariant",
            description="A test invariant",
            category=InvariantCategory.SAFETY,
            threshold=1.0,
        )

        data = invariant.to_dict()
        assert data["invariant_id"] == "INV-READY-TEST"
        assert data["category"] == "SAFETY"
        assert data["threshold"] == 1.0


class TestCheckFunctions:
    """Tests for check functions."""

    def test_check_determinism_required_pass(self) -> None:
        """Test determinism check passing."""
        context: Dict[str, Any] = {
            "determinism_score": 1.0,
            "mismatch_count": 0,
        }
        assert check_determinism_required(context)

    def test_check_determinism_required_fail(self) -> None:
        """Test determinism check failing."""
        context: Dict[str, Any] = {
            "determinism_score": 0.95,
            "mismatch_count": 5,
        }
        assert not check_determinism_required(context)

    def test_check_no_live_inference_pass(self) -> None:
        """Test no live inference check passing."""
        context: Dict[str, Any] = {
            "mode": "SHADOW",
            "live_inference_count": 0,
        }
        assert check_no_live_inference(context)

    def test_check_no_live_inference_fail(self) -> None:
        """Test no live inference check failing."""
        context: Dict[str, Any] = {
            "mode": "LIVE",
            "live_inference_count": 5,
        }
        assert not check_no_live_inference(context)

    def test_check_snapshot_integrity_pass(self) -> None:
        """Test snapshot integrity check passing."""
        context: Dict[str, Any] = {
            "snapshot_integrity_rate": 1.0,
            "corrupted_snapshots": 0,
        }
        assert check_snapshot_integrity(context)

    def test_check_snapshot_integrity_fail(self) -> None:
        """Test snapshot integrity check failing."""
        context: Dict[str, Any] = {
            "snapshot_integrity_rate": 0.9,
            "corrupted_snapshots": 2,
        }
        assert not check_snapshot_integrity(context)

    def test_check_routing_coverage_pass(self) -> None:
        """Test routing coverage check passing."""
        context: Dict[str, Any] = {
            "routing_coverage": 0.98,
            "unhandled_routes": 0,
        }
        assert check_routing_coverage(context)

    def test_check_routing_coverage_fail(self) -> None:
        """Test routing coverage check failing."""
        context: Dict[str, Any] = {
            "routing_coverage": 0.90,
            "unhandled_routes": 5,
        }
        assert not check_routing_coverage(context)

    def test_check_cost_bounded_pass(self) -> None:
        """Test cost bounded check passing."""
        context: Dict[str, Any] = {
            "estimated_cost_usd": 0.5,
            "max_budget_usd": 1.0,
            "cost_variance": 0.05,
        }
        assert check_cost_bounded(context)

    def test_check_cost_bounded_fail(self) -> None:
        """Test cost bounded check failing."""
        context: Dict[str, Any] = {
            "estimated_cost_usd": 1.5,
            "max_budget_usd": 1.0,
            "cost_variance": 0.05,
        }
        assert not check_cost_bounded(context)

    def test_check_governance_clearance_pass(self) -> None:
        """Test governance clearance check passing."""
        context: Dict[str, Any] = {
            "governance_approved": True,
            "pending_violations": 0,
            "approval_timestamp": "2025-01-01T00:00:00Z",
        }
        assert check_governance_clearance(context)

    def test_check_governance_clearance_fail(self) -> None:
        """Test governance clearance check failing."""
        context: Dict[str, Any] = {
            "governance_approved": False,
            "pending_violations": 2,
            "approval_timestamp": None,
        }
        assert not check_governance_clearance(context)


class TestPreDefinedInvariants:
    """Tests for pre-defined invariants."""

    def test_inv_ready_001(self) -> None:
        """Test INV-READY-001 definition."""
        assert INV_READY_001.invariant_id == "INV-READY-001"
        assert INV_READY_001.category == InvariantCategory.DETERMINISM
        assert INV_READY_001.check_function is not None

    def test_inv_ready_002(self) -> None:
        """Test INV-READY-002 definition."""
        assert INV_READY_002.invariant_id == "INV-READY-002"
        assert INV_READY_002.category == InvariantCategory.SAFETY

    def test_inv_ready_003(self) -> None:
        """Test INV-READY-003 definition."""
        assert INV_READY_003.invariant_id == "INV-READY-003"
        assert INV_READY_003.category == InvariantCategory.INTEGRITY

    def test_inv_ready_004(self) -> None:
        """Test INV-READY-004 definition."""
        assert INV_READY_004.invariant_id == "INV-READY-004"
        assert INV_READY_004.category == InvariantCategory.COVERAGE

    def test_inv_ready_005(self) -> None:
        """Test INV-READY-005 definition."""
        assert INV_READY_005.invariant_id == "INV-READY-005"
        assert INV_READY_005.category == InvariantCategory.COST

    def test_inv_ready_006(self) -> None:
        """Test INV-READY-006 definition."""
        assert INV_READY_006.invariant_id == "INV-READY-006"
        assert INV_READY_006.category == InvariantCategory.GOVERNANCE


class TestReadinessInvariantRegistry:
    """Tests for ReadinessInvariantRegistry class."""

    def test_registry_creation(self) -> None:
        """Test registry creation with defaults."""
        registry = ReadinessInvariantRegistry()
        assert len(registry.list_all()) == 6  # 6 default invariants

    def test_register_invariant(self) -> None:
        """Test registering custom invariant."""
        registry = ReadinessInvariantRegistry()

        custom = ReadinessInvariant(
            invariant_id="INV-READY-CUSTOM",
            name="Custom",
            description="Custom invariant",
            category=InvariantCategory.DETERMINISM,
        )

        registry.register(custom)
        assert registry.get("INV-READY-CUSTOM") is not None

    def test_list_by_category(self) -> None:
        """Test listing by category."""
        registry = ReadinessInvariantRegistry()

        determinism_invariants = registry.list_by_category(InvariantCategory.DETERMINISM)
        assert len(determinism_invariants) >= 1

    def test_evaluate_all(self) -> None:
        """Test evaluating all invariants."""
        registry = ReadinessInvariantRegistry()

        context: Dict[str, Any] = {
            "determinism_score": 1.0,
            "mismatch_count": 0,
            "mode": "SHADOW",
            "live_inference_count": 0,
            "snapshot_integrity_rate": 1.0,
            "corrupted_snapshots": 0,
            "routing_coverage": 1.0,
            "unhandled_routes": 0,
            "estimated_cost_usd": 0.5,
            "max_budget_usd": 1.0,
            "cost_variance": 0.05,
            "governance_approved": True,
            "pending_violations": 0,
            "approval_timestamp": "2025-01-01T00:00:00Z",
        }

        results = registry.evaluate_all(context)
        assert len(results) == 6
        assert all(results.values())  # All should pass

    def test_evaluate_one(self) -> None:
        """Test evaluating single invariant."""
        registry = ReadinessInvariantRegistry()

        context: Dict[str, Any] = {
            "determinism_score": 1.0,
            "mismatch_count": 0,
        }

        result = registry.evaluate_one("INV-READY-001", context)
        assert result

    def test_readiness_score(self) -> None:
        """Test readiness score calculation."""
        registry = ReadinessInvariantRegistry()

        # No evaluation yet - all pending
        assert registry.get_readiness_score() == 0.0

    def test_get_blocking_invariants(self) -> None:
        """Test getting blocking invariants."""
        registry = ReadinessInvariantRegistry()

        # Evaluate with failing context
        context: Dict[str, Any] = {
            "determinism_score": 0.5,
            "mismatch_count": 10,
            "mode": "LIVE",
            "live_inference_count": 5,
        }

        registry.evaluate_all(context)
        blocking = registry.get_blocking_invariants()
        assert len(blocking) > 0

    def test_is_ready_for_graduation(self) -> None:
        """Test graduation readiness check."""
        registry = ReadinessInvariantRegistry()

        # Initially not ready
        assert not registry.is_ready_for_graduation()

    def test_get_current_level(self) -> None:
        """Test current level determination."""
        registry = ReadinessInvariantRegistry()

        level = registry.get_current_level()
        assert level == ReadinessLevel.SHADOW  # Default when no passes

    def test_generate_report(self) -> None:
        """Test report generation."""
        registry = ReadinessInvariantRegistry()

        report = registry.generate_report()

        assert "timestamp" in report
        assert "readiness_score" in report
        assert "current_level" in report
        assert "invariants" in report
        assert "blocking_details" in report

    def test_compute_report_hash(self) -> None:
        """Test report hash computation."""
        registry = ReadinessInvariantRegistry()

        hash1 = registry.compute_report_hash()
        hash2 = registry.compute_report_hash()
        assert hash1 == hash2


class TestIntegration:
    """Integration tests for readiness invariants."""

    def test_full_readiness_workflow(self) -> None:
        """Test complete readiness workflow."""
        registry = ReadinessInvariantRegistry()

        # Create passing context
        passing_context: Dict[str, Any] = {
            "determinism_score": 1.0,
            "mismatch_count": 0,
            "mode": "SHADOW",
            "live_inference_count": 0,
            "snapshot_integrity_rate": 1.0,
            "corrupted_snapshots": 0,
            "routing_coverage": 1.0,
            "unhandled_routes": 0,
            "estimated_cost_usd": 0.5,
            "max_budget_usd": 1.0,
            "cost_variance": 0.05,
            "governance_approved": True,
            "pending_violations": 0,
            "approval_timestamp": "2025-01-01T00:00:00Z",
        }

        # Evaluate
        results = registry.evaluate_all(passing_context)

        # All should pass
        assert all(results.values())
        assert registry.get_readiness_score() == 1.0
        assert registry.is_ready_for_graduation()
        assert registry.get_current_level() == ReadinessLevel.LIVE
        assert len(registry.get_blocking_invariants()) == 0

    def test_partial_readiness(self) -> None:
        """Test partial readiness scenario."""
        registry = ReadinessInvariantRegistry()

        # Create partially passing context
        partial_context: Dict[str, Any] = {
            "determinism_score": 1.0,
            "mismatch_count": 0,
            "mode": "SHADOW",
            "live_inference_count": 0,
            "snapshot_integrity_rate": 1.0,
            "corrupted_snapshots": 0,
            "routing_coverage": 0.80,  # Below threshold
            "unhandled_routes": 5,
            "estimated_cost_usd": 2.0,  # Over budget
            "max_budget_usd": 1.0,
            "cost_variance": 0.05,
            "governance_approved": False,  # Not approved
            "pending_violations": 2,
            "approval_timestamp": None,
        }

        results = registry.evaluate_all(partial_context)

        # Some should pass, some fail
        passing = sum(1 for v in results.values() if v)
        failing = sum(1 for v in results.values() if not v)

        assert passing > 0
        assert failing > 0
        assert not registry.is_ready_for_graduation()
        assert len(registry.get_blocking_invariants()) > 0
