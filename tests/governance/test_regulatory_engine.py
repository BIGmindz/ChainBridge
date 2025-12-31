"""
Tests for Regulatory Intelligence Engine.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-03 (Mira-R) — COMPETITIVE & REGULATORY INTELLIGENCE
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from core.governance.regulatory_engine import (
    RegulatoryFrameworkRegistry,
    ComplianceChecker,
    JurisdictionRouter,
    AuditTrailGenerator,
    ComplianceReportGenerator,
    RegulatoryFramework,
    Jurisdiction,
    ComplianceStatus,
    AlertPriority,
    RequirementCategory,
    RetentionPeriod,
    Requirement,
    ComplianceCheckResult,
    compute_wrap_hash,
)


# =============================================================================
# REGULATORY FRAMEWORK REGISTRY TESTS
# =============================================================================

class TestRegulatoryFrameworkRegistry:
    """Tests for RegulatoryFrameworkRegistry."""
    
    def test_initialization(self) -> None:
        """Registry initializes with core requirements."""
        registry = RegulatoryFrameworkRegistry()
        
        # Should have MiCA requirements
        mica_reqs = registry.get_requirements_for_framework(RegulatoryFramework.MICA)
        assert len(mica_reqs) >= 2
    
    def test_register_requirement(self) -> None:
        """Register custom requirement."""
        registry = RegulatoryFrameworkRegistry()
        
        req = Requirement(
            requirement_id="CUSTOM-001",
            framework=RegulatoryFramework.CUSTOM,
            category=RequirementCategory.GOVERNANCE,
            title="Custom Governance Rule",
            description="Internal governance requirement",
            effective_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.GLOBAL]),
            mandatory=True,
            remediation_guidance="Implement governance framework",
        )
        
        registry.register_requirement(req)
        
        retrieved = registry.get_requirement("CUSTOM-001")
        assert retrieved is not None
        assert retrieved.title == "Custom Governance Rule"
    
    def test_get_requirements_for_jurisdiction(self) -> None:
        """Get requirements for specific jurisdiction."""
        registry = RegulatoryFrameworkRegistry()
        
        eu_reqs = registry.get_requirements_for_jurisdiction(Jurisdiction.EU)
        
        # Should have MiCA and DORA requirements
        assert len(eu_reqs) >= 4
        
        frameworks = {req.framework for req in eu_reqs}
        assert RegulatoryFramework.MICA in frameworks
        assert RegulatoryFramework.DORA in frameworks
    
    def test_get_effective_requirements(self) -> None:
        """Get requirements effective as of date."""
        registry = RegulatoryFrameworkRegistry()
        
        # Future date - should include all
        future = datetime(2026, 1, 1, tzinfo=timezone.utc)
        reqs = registry.get_effective_requirements(as_of=future)
        assert len(reqs) >= 5
        
        # Past date - should exclude future requirements
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        reqs = registry.get_effective_requirements(as_of=past)
        # Only older requirements should be included
        for req in reqs:
            assert req.effective_date <= past


# =============================================================================
# COMPLIANCE CHECKER TESTS
# =============================================================================

class TestComplianceChecker:
    """Tests for ComplianceChecker."""
    
    def test_check_pre_execution(self) -> None:
        """Check compliance before execution."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        
        results = checker.check_pre_execution(
            operation_id="op-001",
            operation_type="trade",
            context={"amount": 1000},
            jurisdictions={Jurisdiction.EU},
        )
        
        assert len(results) > 0
        assert all(isinstance(r, ComplianceCheckResult) for r in results)
    
    def test_custom_check_handler(self) -> None:
        """Register and use custom check handler."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        
        def custom_handler(operation_id: str, context: Dict[str, Any]) -> ComplianceCheckResult:
            return ComplianceCheckResult(
                check_id="custom-check-001",
                requirement_id="MICA-001",
                operation_id=operation_id,
                status=ComplianceStatus.COMPLIANT,
                checked_at=datetime.now(timezone.utc),
                details={"custom": True},
                evidence=["evidence-1"],
                remediation_steps=[],
            )
        
        checker.register_check_handler("MICA-001", custom_handler)
        
        results = checker.check_pre_execution(
            operation_id="op-002",
            operation_type="trade",
            context={},
            jurisdictions={Jurisdiction.EU},
        )
        
        # Find the MICA-001 result
        mica_result = next((r for r in results if r.requirement_id == "MICA-001"), None)
        assert mica_result is not None
        assert mica_result.status == ComplianceStatus.COMPLIANT
        assert mica_result.details.get("custom") is True
    
    def test_fail_closed_on_handler_error(self) -> None:
        """Handler errors result in non-compliant status."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        
        def failing_handler(operation_id: str, context: Dict[str, Any]) -> ComplianceCheckResult:
            raise ValueError("Handler error")
        
        checker.register_check_handler("MICA-001", failing_handler)
        
        results = checker.check_pre_execution(
            operation_id="op-003",
            operation_type="trade",
            context={},
            jurisdictions={Jurisdiction.EU},
        )
        
        mica_result = next((r for r in results if r.requirement_id == "MICA-001"), None)
        assert mica_result is not None
        assert mica_result.status == ComplianceStatus.NON_COMPLIANT
        assert mica_result.details.get("fail_closed") is True
    
    def test_calculate_compliance_score(self) -> None:
        """Calculate compliance score."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        
        # Run some checks first
        checker.check_pre_execution(
            operation_id="op-004",
            operation_type="trade",
            context={},
            jurisdictions={Jurisdiction.EU},
        )
        
        score = checker.calculate_compliance_score("entity-001", RegulatoryFramework.MICA)
        
        assert score.entity_id == "entity-001"
        assert score.framework == RegulatoryFramework.MICA
        assert 0.0 <= score.score <= 1.0
    
    def test_remediation_suggestions(self) -> None:
        """Get remediation suggestions."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        
        result = ComplianceCheckResult(
            check_id="check-001",
            requirement_id="MICA-001",
            operation_id="op-005",
            status=ComplianceStatus.NON_COMPLIANT,
            checked_at=datetime.now(timezone.utc),
            details={},
            evidence=[],
            remediation_steps=["Step 1", "Step 2"],
        )
        
        suggestions = checker.get_remediation_suggestions(result)
        
        assert len(suggestions) >= 2
        assert "Step 1" in suggestions


# =============================================================================
# JURISDICTION ROUTER TESTS
# =============================================================================

class TestJurisdictionRouter:
    """Tests for JurisdictionRouter."""
    
    def test_register_entity(self) -> None:
        """Register entity with jurisdictions."""
        router = JurisdictionRouter()
        
        router.register_entity("entity-001", {Jurisdiction.EU, Jurisdiction.US})
        
        jurisdictions = router.get_jurisdictions("entity-001")
        
        assert Jurisdiction.EU in jurisdictions
        assert Jurisdiction.US in jurisdictions
    
    def test_default_jurisdiction(self) -> None:
        """Unknown entity gets global jurisdiction."""
        router = JurisdictionRouter()
        
        jurisdictions = router.get_jurisdictions("unknown-entity")
        
        assert Jurisdiction.GLOBAL in jurisdictions
    
    def test_resolve_jurisdiction_with_context(self) -> None:
        """Resolve jurisdiction with operation context."""
        router = JurisdictionRouter()
        
        router.register_entity("entity-001", {Jurisdiction.EU})
        
        # Operation specifies additional jurisdiction
        jurisdictions = router.resolve_jurisdiction(
            "entity-001",
            {"jurisdiction": Jurisdiction.US},
        )
        
        assert Jurisdiction.EU in jurisdictions
        assert Jurisdiction.US in jurisdictions
    
    def test_route_operation(self) -> None:
        """Route operation to handlers."""
        router = JurisdictionRouter()
        handled_jurisdictions = []
        
        def eu_handler(op_type: str, data: Dict[str, Any]) -> bool:
            handled_jurisdictions.append(Jurisdiction.EU)
            return True
        
        router._jurisdiction_handlers[Jurisdiction.EU] = eu_handler
        router.register_entity("entity-001", {Jurisdiction.EU})
        
        results = router.route_operation("entity-001", "trade", {})
        
        assert Jurisdiction.EU in results
        assert results[Jurisdiction.EU] is True
        assert Jurisdiction.EU in handled_jurisdictions


# =============================================================================
# AUDIT TRAIL GENERATOR TESTS
# =============================================================================

class TestAuditTrailGenerator:
    """Tests for AuditTrailGenerator."""
    
    def test_record_audit(self) -> None:
        """Record audit entry."""
        generator = AuditTrailGenerator()
        
        record = generator.record(
            operation_type="trade",
            operation_id="op-001",
            actor_id="user-001",
            action="EXECUTE",
            jurisdictions=frozenset([Jurisdiction.EU]),
            data_before={"status": "pending"},
            data_after={"status": "completed"},
        )
        
        assert record.record_id is not None
        assert record.hash_value != ""
        assert record.previous_hash == generator.GENESIS_HASH
    
    def test_chain_integrity(self) -> None:
        """Verify chain integrity."""
        generator = AuditTrailGenerator()
        
        # Create multiple records
        for i in range(5):
            generator.record(
                operation_type="trade",
                operation_id=f"op-{i}",
                actor_id="user-001",
                action="EXECUTE",
                jurisdictions=frozenset([Jurisdiction.EU]),
            )
        
        is_valid, error = generator.verify_chain_integrity()
        
        assert is_valid is True
        assert error is None
    
    def test_get_records_with_filters(self) -> None:
        """Get records with filters."""
        generator = AuditTrailGenerator()
        
        # Create records for different operation types
        generator.record(
            operation_type="trade",
            operation_id="op-001",
            actor_id="user-001",
            action="EXECUTE",
            jurisdictions=frozenset([Jurisdiction.EU]),
        )
        generator.record(
            operation_type="settlement",
            operation_id="op-002",
            actor_id="user-001",
            action="SETTLE",
            jurisdictions=frozenset([Jurisdiction.US]),
        )
        
        # Filter by operation type
        trade_records = generator.get_records(operation_type="trade")
        assert len(trade_records) == 1
        
        # Filter by jurisdiction
        us_records = generator.get_records(jurisdiction=Jurisdiction.US)
        assert len(us_records) == 1
    
    def test_export_for_regulator(self) -> None:
        """Export audit trail for regulator."""
        generator = AuditTrailGenerator()
        now = datetime.now(timezone.utc)
        
        generator.record(
            operation_type="trade",
            operation_id="op-001",
            actor_id="user-001",
            action="EXECUTE",
            jurisdictions=frozenset([Jurisdiction.EU]),
        )
        
        export = generator.export_for_regulator(
            framework=RegulatoryFramework.MICA,
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        
        assert export["framework"] == "MiCA"
        assert export["jurisdiction"] == "EU"
        assert export["record_count"] >= 1
    
    def test_chain_tampering_detected(self) -> None:
        """Detect chain tampering."""
        generator = AuditTrailGenerator()
        
        generator.record(
            operation_type="trade",
            operation_id="op-001",
            actor_id="user-001",
            action="EXECUTE",
            jurisdictions=frozenset([Jurisdiction.EU]),
        )
        
        # Tamper with chain
        if generator._records:
            generator._records[0].hash_value = "tampered"
        
        is_valid, error = generator.verify_chain_integrity()
        
        assert is_valid is False
        assert error is not None


# =============================================================================
# COMPLIANCE REPORT GENERATOR TESTS
# =============================================================================

class TestComplianceReportGenerator:
    """Tests for ComplianceReportGenerator."""
    
    def test_generate_report(self) -> None:
        """Generate compliance report."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        audit_trail = AuditTrailGenerator()
        generator = ComplianceReportGenerator(registry, checker, audit_trail)
        
        now = datetime.now(timezone.utc)
        
        # Run some checks
        checker.check_pre_execution(
            operation_id="op-001",
            operation_type="trade",
            context={},
            jurisdictions={Jurisdiction.EU},
        )
        
        report = generator.generate_report(
            entity_id="entity-001",
            framework=RegulatoryFramework.MICA,
            period_start=now - timedelta(days=30),
            period_end=now,
        )
        
        assert report.report_id is not None
        assert report.entity_id == "entity-001"
        assert report.framework == RegulatoryFramework.MICA
        assert report.overall_score is not None
    
    def test_gap_analysis(self) -> None:
        """Report includes gap analysis."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        audit_trail = AuditTrailGenerator()
        generator = ComplianceReportGenerator(registry, checker, audit_trail)
        
        now = datetime.now(timezone.utc)
        
        report = generator.generate_report(
            entity_id="entity-001",
            framework=RegulatoryFramework.MICA,
            period_start=now - timedelta(days=30),
            period_end=now,
        )
        
        # Should have gaps for mandatory requirements without passing checks
        assert isinstance(report.gaps, list)
    
    def test_trends_calculation(self) -> None:
        """Report includes trends."""
        registry = RegulatoryFrameworkRegistry()
        checker = ComplianceChecker(registry)
        audit_trail = AuditTrailGenerator()
        generator = ComplianceReportGenerator(registry, checker, audit_trail)
        
        now = datetime.now(timezone.utc)
        
        # Generate multiple reports to build trend data
        for _ in range(3):
            checker.check_pre_execution(
                operation_id=f"op-{_}",
                operation_type="trade",
                context={},
                jurisdictions={Jurisdiction.EU},
            )
            
            generator.generate_report(
                entity_id="entity-001",
                framework=RegulatoryFramework.MICA,
                period_start=now - timedelta(days=30),
                period_end=now,
            )
        
        report = generator.generate_report(
            entity_id="entity-001",
            framework=RegulatoryFramework.MICA,
            period_start=now - timedelta(days=30),
            period_end=now,
        )
        
        assert "compliance_score" in report.trends
        assert len(report.trends["compliance_score"]) >= 1


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestDataClasses:
    """Tests for data class serialization."""
    
    def test_requirement_to_dict(self) -> None:
        """Requirement serializes to dict."""
        req = Requirement(
            requirement_id="TEST-001",
            framework=RegulatoryFramework.CUSTOM,
            category=RequirementCategory.GOVERNANCE,
            title="Test Requirement",
            description="Test description",
            effective_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            jurisdictions=frozenset([Jurisdiction.GLOBAL]),
            mandatory=True,
            remediation_guidance="Fix it",
        )
        
        data = req.to_dict()
        
        assert data["requirement_id"] == "TEST-001"
        assert data["framework"] == "CUSTOM"
        assert "GLOBAL" in data["jurisdictions"]
    
    def test_compliance_check_result_to_dict(self) -> None:
        """ComplianceCheckResult serializes to dict."""
        result = ComplianceCheckResult(
            check_id="check-001",
            requirement_id="REQ-001",
            operation_id="op-001",
            status=ComplianceStatus.COMPLIANT,
            checked_at=datetime.now(timezone.utc),
            details={"key": "value"},
            evidence=["evidence-1"],
            remediation_steps=[],
        )
        
        data = result.to_dict()
        
        assert data["check_id"] == "check-001"
        assert data["status"] == "COMPLIANT"


# =============================================================================
# WRAP HASH TESTS
# =============================================================================

class TestWrapHash:
    """Tests for WRAP hash computation."""
    
    def test_compute_wrap_hash(self) -> None:
        """Compute WRAP hash."""
        wrap_hash = compute_wrap_hash()
        
        assert wrap_hash is not None
        assert len(wrap_hash) == 16
    
    def test_wrap_hash_deterministic(self) -> None:
        """WRAP hash is deterministic."""
        hash1 = compute_wrap_hash()
        hash2 = compute_wrap_hash()
        
        assert hash1 == hash2
