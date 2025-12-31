# ═══════════════════════════════════════════════════════════════════════════════
# P25 Test Suite — SOP Library & Execution Tests
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: DAN (GID-07) — CI/CD & Test Scaling
# ═══════════════════════════════════════════════════════════════════════════════

"""
Test suite for SOP Library and Execution Engine.

Tests cover:
- SOP definition validation
- SOP registry operations
- Execution workflow
- Approval management
- Read-only OCC facade

EXECUTION MODE: PARALLEL
LANE: CI/CD (GID-07)
"""

import pytest
from datetime import datetime, timezone

from core.sop.sop_library import (
    SOPCategory,
    SOPSeverity,
    SOPReversibility,
    SOPExecutionState,
    SOPPrecondition,
    SOPPostcondition,
    SOPDefinition,
    SOPApproval,
    SOPExecutionRecord,
    SOPRegistry,
    TrustDimension,
    TrustScore,
    AgentTrustIndex,
    SOP_SHIP_001_HOLD,
    SOP_PAY_001_SETTLE,
    SOP_GOV_001_AGENT_SUSPEND,
)

from core.sop.sop_execution import (
    SOPValidationError,
    SOPApprovalError,
    SOPReadOnlyViolationError,
    SOPExecutionView,
    PreconditionValidator,
    ApprovalManager,
    SOPExecutionStore,
    SOPExecutionEngine,
    OCCSOPFacade,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SOP DEFINITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSOPPrecondition:
    """Tests for SOPPrecondition."""

    def test_precondition_creation(self) -> None:
        """Test creating a precondition."""
        precondition = SOPPrecondition(
            condition_id="PRE-TEST-001",
            description="Test precondition",
            validation_rule="entity.status == 'ACTIVE'",
            error_message="Entity must be active",
        )
        assert precondition.condition_id == "PRE-TEST-001"
        assert "active" in precondition.error_message.lower()

    def test_precondition_immutability(self) -> None:
        """Test that preconditions are immutable."""
        precondition = SOPPrecondition(
            condition_id="PRE-TEST-002",
            description="Test",
            validation_rule="rule",
            error_message="error",
        )
        with pytest.raises(AttributeError):
            precondition.condition_id = "MODIFIED"  # type: ignore


class TestSOPDefinition:
    """Tests for SOPDefinition."""

    def test_sop_definition_creation(self) -> None:
        """Test creating an SOP definition."""
        sop = SOPDefinition(
            sop_id="SOP-TEST-001",
            name="Test SOP",
            description="A test SOP",
            category=SOPCategory.SYSTEM,
            severity=SOPSeverity.LOW,
            reversibility=SOPReversibility.REVERSIBLE,
            version="1.0.0",
            preconditions=(
                SOPPrecondition(
                    condition_id="PRE-TEST-001",
                    description="Test",
                    validation_rule="true",
                    error_message="Always passes",
                ),
            ),
            postconditions=(
                SOPPostcondition(
                    condition_id="POST-TEST-001",
                    description="Test",
                    validation_rule="true",
                ),
            ),
            estimated_duration_seconds=10,
            requires_maintenance_window=False,
        )
        assert sop.sop_id == "SOP-TEST-001"
        assert sop.category == SOPCategory.SYSTEM

    def test_sop_id_validation(self) -> None:
        """Test that SOP ID must start with 'SOP-'."""
        with pytest.raises(ValueError, match="must start with 'SOP-'"):
            SOPDefinition(
                sop_id="INVALID-001",
                name="Invalid SOP",
                description="Invalid",
                category=SOPCategory.SYSTEM,
                severity=SOPSeverity.LOW,
                reversibility=SOPReversibility.REVERSIBLE,
                version="1.0.0",
                preconditions=(
                    SOPPrecondition(
                        condition_id="PRE",
                        description="Test",
                        validation_rule="true",
                        error_message="error",
                    ),
                ),
                postconditions=(),
                estimated_duration_seconds=10,
                requires_maintenance_window=False,
            )

    def test_sop_requires_preconditions(self) -> None:
        """Test that SOP must have at least one precondition."""
        with pytest.raises(ValueError, match="at least one precondition"):
            SOPDefinition(
                sop_id="SOP-TEST-002",
                name="Test",
                description="Test",
                category=SOPCategory.SYSTEM,
                severity=SOPSeverity.LOW,
                reversibility=SOPReversibility.REVERSIBLE,
                version="1.0.0",
                preconditions=(),  # Empty preconditions
                postconditions=(),
                estimated_duration_seconds=10,
                requires_maintenance_window=False,
            )

    def test_sop_hash_computation(self) -> None:
        """Test SOP definition hash computation."""
        hash1 = SOP_SHIP_001_HOLD.compute_definition_hash()
        hash2 = SOP_SHIP_001_HOLD.compute_definition_hash()
        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 16


# ═══════════════════════════════════════════════════════════════════════════════
# SOP REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSOPRegistry:
    """Tests for SOPRegistry."""

    def test_registry_singleton(self) -> None:
        """Test that registry is a singleton."""
        reg1 = SOPRegistry()
        reg2 = SOPRegistry()
        assert reg1 is reg2

    def test_registry_has_10_sops(self) -> None:
        """Test that registry has 10 default SOPs."""
        registry = SOPRegistry()
        assert registry.count() == 10

    def test_get_sop_by_id(self) -> None:
        """Test getting SOP by ID."""
        registry = SOPRegistry()
        sop = registry.get("SOP-SHIP-001")
        assert sop is not None
        assert sop.name == "Place Shipment on Hold"

    def test_get_unknown_sop(self) -> None:
        """Test getting unknown SOP returns None."""
        registry = SOPRegistry()
        sop = registry.get("SOP-UNKNOWN-999")
        assert sop is None

    def test_get_by_category(self) -> None:
        """Test filtering SOPs by category."""
        registry = SOPRegistry()
        shipment_sops = registry.get_by_category(SOPCategory.SHIPMENT)
        assert len(shipment_sops) == 2
        assert all(s.category == SOPCategory.SHIPMENT for s in shipment_sops)

    def test_get_by_severity(self) -> None:
        """Test filtering SOPs by severity."""
        registry = SOPRegistry()
        critical_sops = registry.get_by_severity(SOPSeverity.CRITICAL)
        assert len(critical_sops) >= 3
        assert all(s.severity == SOPSeverity.CRITICAL for s in critical_sops)

    def test_requires_dual_approval(self) -> None:
        """Test dual approval requirement check."""
        registry = SOPRegistry()
        # HIGH/CRITICAL require dual approval
        assert registry.requires_dual_approval("SOP-PAY-001")
        assert registry.requires_dual_approval("SOP-GOV-001")
        # MEDIUM does not require dual approval
        assert not registry.requires_dual_approval("SOP-SHIP-001")
        # Unknown SOPs fail-safe to require dual approval
        assert registry.requires_dual_approval("SOP-UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════════════
# SOP EXECUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSOPExecutionRecord:
    """Tests for SOPExecutionRecord."""

    def test_execution_record_creation(self) -> None:
        """Test creating an execution record."""
        record = SOPExecutionRecord(
            execution_id="EXEC-TEST-001",
            sop_id="SOP-SHIP-001",
            sop_version="1.0.0",
            initiator_id="operator@test.com",
            initiated_at=datetime.now(timezone.utc),
            state=SOPExecutionState.PENDING,
        )
        assert record.execution_id == "EXEC-TEST-001"
        assert record.state == SOPExecutionState.PENDING
        assert len(record.approvals) == 0

    def test_execution_record_hash(self) -> None:
        """Test execution record audit hash."""
        record = SOPExecutionRecord(
            execution_id="EXEC-TEST-002",
            sop_id="SOP-SHIP-001",
            sop_version="1.0.0",
            initiator_id="operator@test.com",
            initiated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            state=SOPExecutionState.PENDING,
        )
        hash1 = record.compute_audit_hash()
        hash2 = record.compute_audit_hash()
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex


class TestSOPExecutionView:
    """Tests for SOPExecutionView."""

    def test_view_from_record(self) -> None:
        """Test creating view from record."""
        record = SOPExecutionRecord(
            execution_id="EXEC-TEST-003",
            sop_id="SOP-SHIP-001",
            sop_version="1.0.0",
            initiator_id="operator@test.com",
            initiated_at=datetime.now(timezone.utc),
            state=SOPExecutionState.COMPLETED,
        )
        view = SOPExecutionView.from_record(record, SOP_SHIP_001_HOLD)
        assert view.execution_id == "EXEC-TEST-003"
        assert view.state == SOPExecutionState.COMPLETED
        assert view.progress_percent == 100.0

    def test_view_approval_requirement(self) -> None:
        """Test approval requirement calculation."""
        # LOW severity = 0 approvals
        assert SOPExecutionView._get_approval_requirement(SOPSeverity.LOW) == 0
        # MEDIUM = 1
        assert SOPExecutionView._get_approval_requirement(SOPSeverity.MEDIUM) == 1
        # HIGH = 2
        assert SOPExecutionView._get_approval_requirement(SOPSeverity.HIGH) == 2
        # CRITICAL = 3
        assert SOPExecutionView._get_approval_requirement(SOPSeverity.CRITICAL) == 3


class TestApprovalManager:
    """Tests for ApprovalManager."""

    def test_add_approval(self) -> None:
        """Test adding an approval."""
        manager = ApprovalManager()
        approval = manager.add_approval(
            execution_id="EXEC-001",
            approver_id="approver@test.com",
            approver_role="OPERATOR",
        )
        assert approval.approver_id == "approver@test.com"
        assert approval.approver_role == "OPERATOR"

    def test_duplicate_approver_blocked(self) -> None:
        """Test that duplicate approver is blocked."""
        manager = ApprovalManager()
        manager.add_approval("EXEC-002", "approver@test.com", "OPERATOR")
        with pytest.raises(SOPApprovalError, match="already approved"):
            manager.add_approval("EXEC-002", "approver@test.com", "OPERATOR")

    def test_sufficient_approvals(self) -> None:
        """Test sufficient approvals check."""
        manager = ApprovalManager()
        # Add 2 approvals for HIGH severity SOP
        manager.add_approval("EXEC-003", "approver1@test.com", "OPERATOR")
        manager.add_approval("EXEC-003", "approver2@test.com", "SUPERVISOR")

        assert manager.has_sufficient_approvals("EXEC-003", SOP_PAY_001_SETTLE)


class TestSOPExecutionEngine:
    """Tests for SOPExecutionEngine."""

    def test_initiate_execution(self) -> None:
        """Test initiating an execution."""
        engine = SOPExecutionEngine()
        record = engine.initiate(
            sop_id="SOP-SHIP-001",
            initiator_id="operator@test.com",
        )
        assert record.state == SOPExecutionState.PENDING
        assert record.sop_id == "SOP-SHIP-001"

    def test_initiate_unknown_sop(self) -> None:
        """Test initiating unknown SOP fails."""
        engine = SOPExecutionEngine()
        with pytest.raises(SOPValidationError, match="Unknown SOP"):
            engine.initiate("SOP-UNKNOWN", "operator@test.com")

    def test_full_execution_workflow(self) -> None:
        """Test full execution workflow."""
        engine = SOPExecutionEngine()

        # 1. Initiate
        record = engine.initiate("SOP-SHIP-001", "operator@test.com")
        assert record.state == SOPExecutionState.PENDING

        # 2. Approve (MEDIUM severity needs 1 approval)
        approved = engine.approve(
            record.execution_id,
            "supervisor@test.com",
            "SUPERVISOR",
        )
        assert approved  # Should now be approved

        # 3. Execute
        result = engine.execute(record.execution_id)
        assert result.state == SOPExecutionState.COMPLETED


# ═══════════════════════════════════════════════════════════════════════════════
# OCC FACADE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOCCSOPFacade:
    """Tests for OCCSOPFacade read-only enforcement."""

    def test_list_sops_allowed(self) -> None:
        """Test that listing SOPs is allowed."""
        facade = OCCSOPFacade()
        sops = facade.list_sops()
        assert len(sops) == 10
        assert all("sop_id" in s for s in sops)

    def test_get_sop_allowed(self) -> None:
        """Test that getting SOP details is allowed."""
        facade = OCCSOPFacade()
        sop = facade.get_sop("SOP-SHIP-001")
        assert sop is not None
        assert sop["name"] == "Place Shipment on Hold"

    def test_initiate_blocked(self) -> None:
        """Test that initiating SOP is blocked."""
        facade = OCCSOPFacade()
        with pytest.raises(SOPReadOnlyViolationError, match="cannot perform write"):
            facade.initiate_sop("SOP-SHIP-001", "operator@test.com")

    def test_approve_blocked(self) -> None:
        """Test that approving SOP is blocked."""
        facade = OCCSOPFacade()
        with pytest.raises(SOPReadOnlyViolationError, match="cannot perform write"):
            facade.approve_sop("EXEC-001", "approver@test.com")

    def test_execute_blocked(self) -> None:
        """Test that executing SOP is blocked."""
        facade = OCCSOPFacade()
        with pytest.raises(SOPReadOnlyViolationError, match="cannot perform write"):
            facade.execute_sop("EXEC-001")


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST INDEX TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentTrustIndex:
    """Tests for AgentTrustIndex."""

    def test_trust_index_creation(self) -> None:
        """Test creating a trust index."""
        trust = AgentTrustIndex(
            agent_id="GID-01",
            agent_name="CODY",
        )
        assert trust.overall_trust == 1.0
        assert trust.trust_tier == "STANDARD"

    def test_update_score(self) -> None:
        """Test updating a trust dimension score."""
        trust = AgentTrustIndex(agent_id="GID-01", agent_name="CODY")
        trust.update_score(TrustDimension.EXECUTION_ACCURACY, 0.95, 100)

        assert TrustDimension.EXECUTION_ACCURACY in trust.scores
        assert trust.scores[TrustDimension.EXECUTION_ACCURACY].score == 0.95

    def test_tier_calculation(self) -> None:
        """Test trust tier calculation."""
        trust = AgentTrustIndex(agent_id="GID-01", agent_name="CODY")

        # High trust -> TRUSTED
        trust.update_score(TrustDimension.GOVERNANCE_ADHERENCE, 0.98, 100)
        trust.update_score(TrustDimension.INVARIANT_COMPLIANCE, 0.99, 100)
        assert trust.trust_tier == "TRUSTED"

        # Lower trust -> PROBATION
        trust.update_score(TrustDimension.ERROR_RATE, 0.30, 100)
        # Check tier updated
        assert trust.trust_tier in ("STANDARD", "ELEVATED", "PROBATION")

    def test_get_summary(self) -> None:
        """Test getting trust summary."""
        trust = AgentTrustIndex(agent_id="GID-01", agent_name="CODY")
        trust.update_score(TrustDimension.EXECUTION_ACCURACY, 0.95, 100)

        summary = trust.get_summary()
        assert summary["agent_id"] == "GID-01"
        assert summary["agent_name"] == "CODY"
        assert "overall_trust" in summary
        assert "dimensions" in summary


class TestTrustScore:
    """Tests for TrustScore."""

    def test_score_bounds(self) -> None:
        """Test that score must be in [0.0, 1.0]."""
        # Valid score
        score = TrustScore(
            dimension=TrustDimension.EXECUTION_ACCURACY,
            score=0.85,
            sample_count=100,
            last_updated=datetime.now(timezone.utc),
        )
        assert score.score == 0.85

        # Invalid score
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            TrustScore(
                dimension=TrustDimension.EXECUTION_ACCURACY,
                score=1.5,
                sample_count=100,
                last_updated=datetime.now(timezone.utc),
            )
