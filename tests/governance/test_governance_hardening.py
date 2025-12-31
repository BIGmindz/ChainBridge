# ═══════════════════════════════════════════════════════════════════════════════
# PAC-012: Governance Hardening Tests
# Comprehensive test suite for all 8 invariants
# ═══════════════════════════════════════════════════════════════════════════════

"""
Test suite for PAC-012 Governance Hardening.

Tests cover:
- INV-GOV-001: Explicit agent acknowledgment required
- INV-GOV-002: No execution without declared dependencies
- INV-GOV-003: No silent partial success
- INV-GOV-004: No undeclared capabilities
- INV-GOV-005: No human override without PDO
- INV-GOV-006: Retention & time bounds explicit
- INV-GOV-007: Training signals classified
- INV-GOV-008: Fail-closed on any violation
"""

import pytest
from datetime import datetime, timezone, timedelta

from core.governance.governance_schema import (
    GOVERNANCE_SCHEMA_VERSION,
    AcknowledgmentStatus,
    AcknowledgmentType,
    AgentAcknowledgment,
    AcknowledgmentRegistry,
    get_acknowledgment_registry,
    reset_acknowledgment_registry,
    FailureMode,
    RollbackStrategy,
    ExecutionOutcome,
    FailureSemantics,
    ExecutionFailure,
    CapabilityCategory,
    NonCapability,
    CANONICAL_NON_CAPABILITIES,
    HumanInterventionType,
    HumanBoundaryStatus,
    HumanBoundaryContract,
    HumanIntervention,
    GovernanceViolation,
)
from core.governance.dependency_graph import (
    DependencyType,
    DependencyStatus,
    ArtifactType,
    ExecutionDependency,
    ArtifactReference,
    CausalityLink,
    FailurePropagationMode,
    FailurePropagationRule,
    FailurePropagationEvent,
    DependencyGraph,
    CausalityRegistry,
    DependencyGraphRegistry,
    get_dependency_registry,
    get_causality_registry,
    reset_dependency_registry,
    reset_causality_registry,
)
from core.governance.retention_policy import (
    RETENTION_SCHEMA_VERSION,
    RetentionPeriod,
    RETENTION_DAYS,
    ArtifactStorageType,
    RetentionPolicy,
    CANONICAL_RETENTION_POLICIES,
    TrainingSignalClass,
    TrainingSignalDeclaration,
    CIGateStatus,
    CIGateCheck,
    CIGateResult,
    GovernanceCIGate,
    RetentionRegistry,
    get_retention_registry,
    reset_retention_registry,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_registries():
    """Reset all registries before each test."""
    reset_acknowledgment_registry()
    reset_dependency_registry()
    reset_causality_registry()
    reset_retention_registry()
    yield
    reset_acknowledgment_registry()
    reset_dependency_registry()
    reset_causality_registry()
    reset_retention_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-001: EXPLICIT AGENT ACKNOWLEDGMENT REQUIRED
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcknowledgmentRegistry:
    """Tests for INV-GOV-001: Explicit agent acknowledgment required."""
    
    def test_schema_version_defined(self):
        """Schema version is defined."""
        assert GOVERNANCE_SCHEMA_VERSION == "1.0.0"
    
    def test_acknowledgment_registry_singleton(self):
        """Registry is a singleton."""
        reg1 = get_acknowledgment_registry()
        reg2 = get_acknowledgment_registry()
        assert reg1 is reg2
    
    def test_request_acknowledgment_creates_pending(self):
        """Requesting acknowledgment creates pending status."""
        registry = get_acknowledgment_registry()
        ack = registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        
        assert ack.status == AcknowledgmentStatus.PENDING
        assert ack.ack_type == AcknowledgmentType.ACK_REQUIRED
        assert ack.pac_id == "PAC-012"
        assert ack.order_id == "ORDER-1"
        assert ack.agent_gid == "GID-01"
        assert ack.ack_hash  # Hash is computed
    
    def test_acknowledge_changes_status(self):
        """Acknowledging changes status to ACKNOWLEDGED."""
        registry = get_acknowledgment_registry()
        ack = registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        
        updated = registry.acknowledge(ack.ack_id, "Ready to execute")
        
        assert updated.status == AcknowledgmentStatus.ACKNOWLEDGED
        assert updated.response_message == "Ready to execute"
        assert updated.acknowledged_at is not None
    
    def test_reject_changes_status(self):
        """Rejecting changes status to REJECTED."""
        registry = get_acknowledgment_registry()
        ack = registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        
        updated = registry.reject(ack.ack_id, "Conflicting dependencies")
        
        assert updated.status == AcknowledgmentStatus.REJECTED
        assert updated.rejection_reason == "Conflicting dependencies"
    
    def test_verify_execution_allowed_after_acknowledge(self):
        """Execution allowed after acknowledgment."""
        registry = get_acknowledgment_registry()
        ack = registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        registry.acknowledge(ack.ack_id)
        
        allowed, reason = registry.verify_execution_allowed(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
        )
        
        assert allowed is True
        assert reason is None
    
    def test_verify_execution_denied_without_acknowledge(self):
        """Execution denied without acknowledgment."""
        registry = get_acknowledgment_registry()
        registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        # Don't acknowledge
        
        allowed, reason = registry.verify_execution_allowed(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
        )
        
        assert allowed is False
        assert "PENDING" in reason
    
    def test_verify_execution_denied_after_rejection(self):
        """Execution denied after rejection."""
        registry = get_acknowledgment_registry()
        ack = registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        registry.reject(ack.ack_id, "Not ready")
        
        allowed, reason = registry.verify_execution_allowed(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
        )
        
        assert allowed is False
        assert "REJECTED" in reason
    
    def test_acknowledge_nonexistent_raises_violation(self):
        """Acknowledging nonexistent ID raises GovernanceViolation."""
        registry = get_acknowledgment_registry()
        
        with pytest.raises(GovernanceViolation) as exc_info:
            registry.acknowledge("nonexistent-id")
        
        assert exc_info.value.invariant == "INV-GOV-001"


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-002: NO EXECUTION WITHOUT DECLARED DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyGraph:
    """Tests for INV-GOV-002: No execution without declared dependencies."""
    
    def test_dependency_graph_registry_singleton(self):
        """Registry is a singleton."""
        reg1 = get_dependency_registry()
        reg2 = get_dependency_registry()
        assert reg1 is reg2
    
    def test_create_dependency_graph(self):
        """Can create dependency graph for a PAC."""
        registry = get_dependency_registry()
        graph = registry.get_or_create("PAC-012")
        
        assert graph.pac_id == "PAC-012"
    
    def test_add_dependency(self):
        """Can add dependency to graph."""
        registry = get_dependency_registry()
        graph = registry.get_or_create("PAC-012")
        
        dep = ExecutionDependency(
            dependency_id="dep-001",
            pac_id="PAC-012",
            dependent_order_id="ORDER-2",
            dependent_agent_gid="GID-02",
            source_order_id="ORDER-1",
            source_agent_gid="GID-01",
            dependency_type=DependencyType.HARD,
            description="ORDER-2 requires ORDER-1",
        )
        
        graph.add_dependency(dep)
        
        deps = graph.get_dependencies_for("ORDER-2")
        assert len(deps) == 1
        assert deps[0].source_order_id == "ORDER-1"
    
    def test_circular_dependency_raises_violation(self):
        """Circular dependency raises GovernanceViolation."""
        registry = get_dependency_registry()
        graph = registry.get_or_create("PAC-012")
        
        dep1 = ExecutionDependency(
            dependency_id="dep-001",
            pac_id="PAC-012",
            dependent_order_id="ORDER-2",
            dependent_agent_gid="GID-02",
            source_order_id="ORDER-1",
            source_agent_gid="GID-01",
            dependency_type=DependencyType.HARD,
            description="ORDER-2 requires ORDER-1",
        )
        graph.add_dependency(dep1)
        
        dep2 = ExecutionDependency(
            dependency_id="dep-002",
            pac_id="PAC-012",
            dependent_order_id="ORDER-1",  # Creates cycle
            dependent_agent_gid="GID-01",
            source_order_id="ORDER-2",
            source_agent_gid="GID-02",
            dependency_type=DependencyType.HARD,
            description="ORDER-1 requires ORDER-2 (circular!)",
        )
        
        with pytest.raises(GovernanceViolation) as exc_info:
            graph.add_dependency(dep2)
        
        assert exc_info.value.invariant == "INV-GOV-002"
        assert "Circular" in exc_info.value.message
    
    def test_execution_order_topological(self):
        """Execution order is topologically sorted."""
        registry = get_dependency_registry()
        graph = registry.get_or_create("PAC-012")
        
        # ORDER-3 depends on ORDER-2, which depends on ORDER-1
        graph.add_dependency(ExecutionDependency(
            dependency_id="dep-001",
            pac_id="PAC-012",
            dependent_order_id="ORDER-2",
            dependent_agent_gid="GID-02",
            source_order_id="ORDER-1",
            source_agent_gid="GID-01",
            dependency_type=DependencyType.HARD,
            description="ORDER-2 requires ORDER-1",
        ))
        graph.add_dependency(ExecutionDependency(
            dependency_id="dep-002",
            pac_id="PAC-012",
            dependent_order_id="ORDER-3",
            dependent_agent_gid="GID-03",
            source_order_id="ORDER-2",
            source_agent_gid="GID-02",
            dependency_type=DependencyType.HARD,
            description="ORDER-3 requires ORDER-2",
        ))
        
        order = graph.get_execution_order()
        
        assert order.index("ORDER-1") < order.index("ORDER-2")
        assert order.index("ORDER-2") < order.index("ORDER-3")
    
    def test_can_execute_checks_hard_dependencies(self):
        """can_execute checks hard dependencies."""
        registry = get_dependency_registry()
        graph = registry.get_or_create("PAC-012")
        
        dep = ExecutionDependency(
            dependency_id="dep-001",
            pac_id="PAC-012",
            dependent_order_id="ORDER-2",
            dependent_agent_gid="GID-02",
            source_order_id="ORDER-1",
            source_agent_gid="GID-01",
            dependency_type=DependencyType.HARD,
            description="ORDER-2 requires ORDER-1",
        )
        graph.add_dependency(dep)
        
        can, unsatisfied = graph.can_execute("ORDER-2")
        
        assert can is False
        assert "ORDER-1" in unsatisfied
    
    def test_can_execute_after_satisfied(self):
        """can_execute returns True after dependency satisfied."""
        registry = get_dependency_registry()
        graph = registry.get_or_create("PAC-012")
        
        dep = ExecutionDependency(
            dependency_id="dep-001",
            pac_id="PAC-012",
            dependent_order_id="ORDER-2",
            dependent_agent_gid="GID-02",
            source_order_id="ORDER-1",
            source_agent_gid="GID-01",
            dependency_type=DependencyType.HARD,
            description="ORDER-2 requires ORDER-1",
        )
        graph.add_dependency(dep)
        graph.mark_satisfied("dep-001")
        
        can, unsatisfied = graph.can_execute("ORDER-2")
        
        assert can is True
        assert unsatisfied == []


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-003: NO SILENT PARTIAL SUCCESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureSemantics:
    """Tests for INV-GOV-003: No silent partial success."""
    
    def test_execution_outcome_includes_partial_success(self):
        """ExecutionOutcome enum includes PARTIAL_SUCCESS."""
        assert ExecutionOutcome.PARTIAL_SUCCESS.value == "PARTIAL_SUCCESS"
    
    def test_failure_semantics_explicit_partial_success(self):
        """FailureSemantics requires explicit partial_success_allowed."""
        semantics = FailureSemantics(
            order_id="ORDER-1",
            pac_id="PAC-012",
            failure_mode=FailureMode.FAIL_CLOSED,
            rollback_strategy=RollbackStrategy.CHECKPOINT,
            partial_success_allowed=True,
            partial_success_threshold=0.8,
        )
        
        assert semantics.partial_success_allowed is True
        assert semantics.partial_success_threshold == 0.8
    
    def test_failure_semantics_default_no_partial_success(self):
        """FailureSemantics defaults to no partial success."""
        semantics = FailureSemantics(
            order_id="ORDER-1",
            pac_id="PAC-012",
            failure_mode=FailureMode.FAIL_CLOSED,
            rollback_strategy=RollbackStrategy.NONE,
        )
        
        assert semantics.partial_success_allowed is False
        assert semantics.partial_success_threshold == 0.0
    
    def test_failure_propagation_event_tracks_impact(self):
        """Failure propagation event tracks impact."""
        event = FailurePropagationEvent(
            event_id="fprop-001",
            pac_id="PAC-012",
            source_order_id="ORDER-1",
            propagation_mode=FailurePropagationMode.CASCADING,
            orders_blocked=["ORDER-2", "ORDER-3"],
            orders_degraded=["ORDER-4"],
            total_affected=3,
            cascade_depth=2,
        )
        
        assert event.total_affected == 3
        assert len(event.orders_blocked) == 2
        assert len(event.orders_degraded) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-004: NO UNDECLARED CAPABILITIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestNonCapabilities:
    """Tests for INV-GOV-004: No undeclared capabilities."""
    
    def test_canonical_non_capabilities_exist(self):
        """Canonical non-capabilities list exists."""
        assert len(CANONICAL_NON_CAPABILITIES) >= 6
    
    def test_non_capability_categories_covered(self):
        """All capability categories have non-capabilities."""
        categories = {nc.category for nc in CANONICAL_NON_CAPABILITIES}
        
        assert CapabilityCategory.FINANCIAL_ACTION in categories
        assert CapabilityCategory.USER_IMPERSONATION in categories
        assert CapabilityCategory.DATA_MUTATION in categories
        assert CapabilityCategory.SYSTEM_CONTROL in categories
        assert CapabilityCategory.TRAINING_FEEDBACK in categories
        assert CapabilityCategory.EXTERNAL_API in categories
    
    def test_non_capabilities_enforced_by_default(self):
        """Non-capabilities are enforced by default."""
        for nc in CANONICAL_NON_CAPABILITIES:
            assert nc.enforced is True
            assert nc.violation_action == "FAIL_CLOSED"
    
    def test_non_capability_to_dict(self):
        """Non-capability serializes to dict."""
        nc = CANONICAL_NON_CAPABILITIES[0]
        d = nc.to_dict()
        
        assert "capability_id" in d
        assert "category" in d
        assert "description" in d
        assert "reason" in d
        assert "enforced" in d


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-005: NO HUMAN OVERRIDE WITHOUT PDO
# ═══════════════════════════════════════════════════════════════════════════════

class TestHumanBoundary:
    """Tests for INV-GOV-005: No human override without PDO."""
    
    def test_human_intervention_override_requires_pdo(self):
        """Override intervention requires PDO."""
        intervention = HumanIntervention(
            intervention_id="int-001",
            boundary_id="bound-001",
            pac_id="PAC-012",
            intervention_type=HumanInterventionType.OVERRIDE,
            status=HumanBoundaryStatus.APPROVED,
            actor_id="human-001",
            actor_role="admin",
            # No override_pdo_id provided
        )
        
        valid, error = intervention.validate_override()
        
        assert valid is False
        assert "INV-GOV-005" in error
        assert "PDO" in error
    
    def test_human_intervention_override_valid_with_pdo(self):
        """Override intervention valid with PDO."""
        intervention = HumanIntervention(
            intervention_id="int-001",
            boundary_id="bound-001",
            pac_id="PAC-012",
            intervention_type=HumanInterventionType.OVERRIDE,
            status=HumanBoundaryStatus.APPROVED,
            actor_id="human-001",
            actor_role="admin",
            override_pdo_id="PDO-12345",
        )
        
        valid, error = intervention.validate_override()
        
        assert valid is True
        assert error is None
    
    def test_non_override_intervention_no_pdo_required(self):
        """Non-override intervention doesn't require PDO."""
        intervention = HumanIntervention(
            intervention_id="int-001",
            boundary_id="bound-001",
            pac_id="PAC-012",
            intervention_type=HumanInterventionType.APPROVAL_REQUIRED,
            status=HumanBoundaryStatus.PENDING,
            actor_id="human-001",
            actor_role="admin",
            # No PDO required for non-override
        )
        
        valid, error = intervention.validate_override()
        
        assert valid is True
        assert error is None


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-006: RETENTION & TIME BOUNDS EXPLICIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestRetentionPolicy:
    """Tests for INV-GOV-006: Retention & time bounds explicit."""
    
    def test_retention_schema_version_defined(self):
        """Retention schema version is defined."""
        assert RETENTION_SCHEMA_VERSION == "1.0.0"
    
    def test_canonical_retention_policies_exist(self):
        """Canonical retention policies exist."""
        assert len(CANONICAL_RETENTION_POLICIES) >= 10
    
    def test_all_retention_periods_have_days(self):
        """All retention periods have defined days."""
        for period in RetentionPeriod:
            assert period in RETENTION_DAYS
    
    def test_retention_policy_computes_expiration(self):
        """Retention policy computes expiration timestamp."""
        policy = RetentionPolicy(
            policy_id="test-001",
            artifact_type="TEST_ARTIFACT",
            retention_period=RetentionPeriod.SHORT_TERM,
            storage_type=ArtifactStorageType.SNAPSHOT,
        )
        
        assert policy.expires_at is not None
    
    def test_permanent_retention_no_expiration(self):
        """Permanent retention has no expiration."""
        policy = RetentionPolicy(
            policy_id="test-002",
            artifact_type="PERMANENT_ARTIFACT",
            retention_period=RetentionPeriod.PERMANENT,
            storage_type=ArtifactStorageType.SNAPSHOT,
        )
        
        assert policy.expires_at is None
        assert policy.is_expired is False
    
    def test_retention_registry_singleton(self):
        """Retention registry is singleton."""
        reg1 = get_retention_registry()
        reg2 = get_retention_registry()
        assert reg1 is reg2
    
    def test_retention_registry_has_canonical_policies(self):
        """Retention registry loaded with canonical policies."""
        registry = get_retention_registry()
        policies = registry.list_policies()
        
        assert len(policies) >= 10


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-007: TRAINING SIGNALS CLASSIFIED
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrainingSignals:
    """Tests for INV-GOV-007: Training signals classified."""
    
    def test_training_signal_classes_defined(self):
        """Training signal classes are defined."""
        assert TrainingSignalClass.APPROVED.value == "APPROVED"
        assert TrainingSignalClass.EXCLUDED.value == "EXCLUDED"
        assert TrainingSignalClass.PENDING_REVIEW.value == "PENDING_REVIEW"
        assert TrainingSignalClass.NOT_APPLICABLE.value == "NOT_APPLICABLE"
    
    def test_register_training_signal(self):
        """Can register training signal classification."""
        registry = get_retention_registry()
        
        decl = registry.register_training_signal(
            artifact_id="artifact-001",
            artifact_type="EXECUTION_LOG",
            classification=TrainingSignalClass.APPROVED,
            rationale="Verified no PII, approved for training",
            classified_by="admin-001",
        )
        
        assert decl.classification == TrainingSignalClass.APPROVED
        assert decl.rationale == "Verified no PII, approved for training"
    
    def test_get_training_classification(self):
        """Can retrieve training classification."""
        registry = get_retention_registry()
        registry.register_training_signal(
            artifact_id="artifact-001",
            artifact_type="EXECUTION_LOG",
            classification=TrainingSignalClass.EXCLUDED,
            rationale="Contains PII",
            classified_by="admin-001",
        )
        
        classification = registry.get_training_classification("artifact-001")
        
        assert classification == TrainingSignalClass.EXCLUDED
    
    def test_unclassified_returns_none(self):
        """Unclassified artifact returns None."""
        registry = get_retention_registry()
        classification = registry.get_training_classification("nonexistent")
        assert classification is None


# ═══════════════════════════════════════════════════════════════════════════════
# INV-GOV-008: FAIL-CLOSED ON ANY VIOLATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceViolation:
    """Tests for INV-GOV-008: Fail-closed on any violation."""
    
    def test_governance_violation_exception(self):
        """GovernanceViolation is an exception."""
        with pytest.raises(GovernanceViolation):
            raise GovernanceViolation(
                invariant="INV-GOV-008",
                message="Test violation",
            )
    
    def test_governance_violation_fail_closed_default(self):
        """GovernanceViolation defaults to fail_closed=True."""
        violation = GovernanceViolation(
            invariant="INV-GOV-008",
            message="Test violation",
        )
        
        assert violation.fail_closed is True
    
    def test_governance_violation_captures_context(self):
        """GovernanceViolation captures context."""
        violation = GovernanceViolation(
            invariant="INV-GOV-001",
            message="Missing acknowledgment",
            context={"order_id": "ORDER-1", "agent_gid": "GID-01"},
        )
        
        assert violation.context["order_id"] == "ORDER-1"
        assert violation.context["agent_gid"] == "GID-01"
    
    def test_governance_violation_to_dict(self):
        """GovernanceViolation serializes to dict."""
        violation = GovernanceViolation(
            invariant="INV-GOV-002",
            message="Circular dependency",
            context={"cycle": ["ORDER-1", "ORDER-2"]},
        )
        
        d = violation.to_dict()
        
        assert d["invariant"] == "INV-GOV-002"
        assert d["message"] == "Circular dependency"
        assert d["fail_closed"] is True
        assert "timestamp" in d


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSALITY REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCausalityRegistry:
    """Tests for causality tracking."""
    
    def test_causality_registry_singleton(self):
        """Causality registry is singleton."""
        reg1 = get_causality_registry()
        reg2 = get_causality_registry()
        assert reg1 is reg2
    
    def test_record_artifact(self):
        """Can record artifact causality."""
        registry = get_causality_registry()
        
        artifact = ArtifactReference(
            artifact_id="file-001",
            artifact_type=ArtifactType.FILE,
            location="/path/to/file.py",
        )
        
        link = registry.record_artifact(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            artifact=artifact,
            caused_by_order_ids=["ORDER-0"],
        )
        
        assert link.artifact.artifact_id == "file-001"
        assert link.caused_by_order_ids == ["ORDER-0"]
        assert link.link_hash  # Hash computed
    
    def test_trace_causality(self):
        """Can trace causality chain."""
        registry = get_causality_registry()
        
        # ORDER-1 produces artifact-A
        artifact_a = ArtifactReference(
            artifact_id="artifact-a",
            artifact_type=ArtifactType.FILE,
            location="/a.py",
        )
        registry.record_artifact(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            artifact=artifact_a,
        )
        
        # ORDER-2 produces artifact-B, caused by ORDER-1
        artifact_b = ArtifactReference(
            artifact_id="artifact-b",
            artifact_type=ArtifactType.FILE,
            location="/b.py",
        )
        registry.record_artifact(
            pac_id="PAC-012",
            order_id="ORDER-2",
            agent_gid="GID-02",
            artifact=artifact_b,
            caused_by_order_ids=["ORDER-1"],
        )
        
        chain = registry.trace_causality("artifact-b")
        
        assert "ORDER-2" in chain
        assert "ORDER-1" in chain


# ═══════════════════════════════════════════════════════════════════════════════
# CI GATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCIGates:
    """Tests for CI gate enforcement."""
    
    def test_ci_gate_check_governance_files(self):
        """CI gate checks governance files."""
        gate = GovernanceCIGate()
        check = gate.check_governance_files()
        
        # At least the check runs without error
        assert check.gate_id == "GOV-FILES"
        assert check.status in {CIGateStatus.PASS, CIGateStatus.FAIL}
    
    def test_ci_gate_check_retention_declarations(self):
        """CI gate checks retention declarations."""
        gate = GovernanceCIGate()
        check = gate.check_retention_declarations()
        
        # Should pass since CANONICAL_RETENTION_POLICIES exists
        assert check.status == CIGateStatus.PASS
        assert "INV-GOV-006" in check.message
    
    def test_ci_gate_check_non_capabilities(self):
        """CI gate checks non-capabilities declarations."""
        gate = GovernanceCIGate()
        check = gate.check_non_capabilities()
        
        # Should pass since CANONICAL_NON_CAPABILITIES exists
        assert check.status == CIGateStatus.PASS
        assert "INV-GOV-004" in check.message
    
    def test_ci_gate_result_aggregation(self):
        """CI gate aggregates results correctly."""
        gate = GovernanceCIGate()
        result = gate.run_all_gates(skip_tests=True)
        
        assert isinstance(result, CIGateResult)
        assert result.total_checks >= 3
        assert result.passed_checks + result.failed_checks + result.skipped_checks == result.total_checks


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceIntegration:
    """Integration tests across governance components."""
    
    def test_full_governance_flow(self):
        """Test complete governance flow."""
        # 1. Request acknowledgment
        ack_registry = get_acknowledgment_registry()
        ack = ack_registry.request_acknowledgment(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            agent_name="Cody",
        )
        
        # 2. Declare dependency
        dep_registry = get_dependency_registry()
        graph = dep_registry.get_or_create("PAC-012")
        dep = ExecutionDependency(
            dependency_id="dep-001",
            pac_id="PAC-012",
            dependent_order_id="ORDER-2",
            dependent_agent_gid="GID-02",
            source_order_id="ORDER-1",
            source_agent_gid="GID-01",
            dependency_type=DependencyType.HARD,
            description="ORDER-2 depends on ORDER-1",
        )
        graph.add_dependency(dep)
        
        # 3. Acknowledge
        ack_registry.acknowledge(ack.ack_id, "Ready")
        
        # 4. Verify execution allowed
        allowed, _ = ack_registry.verify_execution_allowed(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
        )
        assert allowed is True
        
        # 5. Mark dependency satisfied
        graph.mark_satisfied("dep-001")
        can, _ = graph.can_execute("ORDER-2")
        assert can is True
        
        # 6. Record artifact
        causality = get_causality_registry()
        artifact = ArtifactReference(
            artifact_id="output-001",
            artifact_type=ArtifactType.FILE,
            location="/output/result.json",
        )
        link = causality.record_artifact(
            pac_id="PAC-012",
            order_id="ORDER-1",
            agent_gid="GID-01",
            artifact=artifact,
        )
        assert link.link_hash  # Integrity hash present
        
        # 7. Check retention policy
        ret_registry = get_retention_registry()
        policy = ret_registry.get_policy("EXECUTION_LOG")
        assert policy is not None
        assert policy.retention_period == RetentionPeriod.LONG_TERM
