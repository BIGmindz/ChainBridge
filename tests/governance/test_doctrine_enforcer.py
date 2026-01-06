"""
Doctrine Enforcer Tests

PAC Reference: PAC-JEFFREY-P47
Tests verify mechanical enforcement of Structural Advantage Doctrine.
"""

import pytest
from datetime import datetime

from core.occ.governance.doctrine_enforcer import (
    DoctrineEnforcer,
    DoctrineID,
    ViolationSeverity,
    EnforcementAction,
    DoctrineViolation,
    DoctrineCheckResult,
    get_doctrine_enforcer,
    reset_doctrine_enforcer,
    check_doctrine_gate,
    get_compliance_report,
)


class TestDoctrineID:
    """Test doctrine enumeration."""
    
    def test_all_doctrines_defined(self):
        """Verify all 7 doctrines from P47 exist."""
        expected = {
            "DOC-001", "DOC-002", "DOC-003", "DOC-004",
            "DOC-005", "DOC-006", "DOC-007"
        }
        actual = {d.value for d in DoctrineID}
        assert actual == expected
    
    def test_doctrine_count(self):
        """Verify exactly 7 doctrines."""
        assert len(DoctrineID) == 7


class TestDoctrineEnforcer:
    """Test doctrine enforcer core functionality."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_empty_enforcer_allows_execution(self):
        """Empty enforcer should allow execution."""
        enforcer = DoctrineEnforcer()
        allowed, msg = enforcer.is_execution_allowed()
        assert allowed is True
    
    def test_no_violations_initially(self):
        """No violations recorded initially."""
        enforcer = DoctrineEnforcer()
        violations = enforcer.get_violations()
        assert len(violations) == 0


class TestDOC001InfiniteTestSuite:
    """Test DOC-001: Infinite Test Suite - No test regression."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_no_baseline_passes(self):
        """No baseline set should pass."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_test_regression(100)
        assert result.passed is True
    
    def test_test_count_maintained(self):
        """Test count maintained should pass."""
        enforcer = DoctrineEnforcer()
        enforcer.set_test_baseline(100)
        
        result = enforcer.check_test_regression(100)
        assert result.passed is True
        assert result.doctrine_id == DoctrineID.DOC_001
    
    def test_test_count_increased(self):
        """Test count increased should pass."""
        enforcer = DoctrineEnforcer()
        enforcer.set_test_baseline(100)
        
        result = enforcer.check_test_regression(150)
        assert result.passed is True
    
    def test_test_regression_detected(self):
        """Test regression should fail and record violation."""
        enforcer = DoctrineEnforcer()
        enforcer.set_test_baseline(100)
        
        result = enforcer.check_test_regression(95)
        
        assert result.passed is False
        assert "REGRESSION" in result.message
        assert result.details["baseline"] == 100
        assert result.details["current"] == 95
        
        # Verify violation recorded
        violations = enforcer.get_violations()
        assert len(violations) == 1
        assert violations[0].doctrine_id == DoctrineID.DOC_001
        assert violations[0].action == EnforcementAction.BLOCK_MERGE
    
    def test_test_regression_blocks_execution(self):
        """Test regression should block execution."""
        enforcer = DoctrineEnforcer()
        enforcer.set_test_baseline(100)
        enforcer.check_test_regression(50)  # 50% regression
        
        allowed, msg = enforcer.is_execution_allowed()
        assert allowed is False


class TestDOC003AuditZeroSampling:
    """Test DOC-003: 100% Audit Zero Sampling."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_full_audit_coverage(self):
        """100% audit coverage should pass."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_audit_coverage(audited_count=100, total_count=100)
        
        assert result.passed is True
        assert result.doctrine_id == DoctrineID.DOC_003
    
    def test_no_transactions_passes(self):
        """No transactions should pass."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_audit_coverage(audited_count=0, total_count=0)
        assert result.passed is True
    
    def test_audit_gap_detected(self):
        """Audit gap should fail and record violation."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_audit_coverage(audited_count=95, total_count=100)
        
        assert result.passed is False
        assert "AUDIT GAP" in result.message
        assert result.details["gap"] == 5
        
        # Verify violation recorded
        violations = enforcer.get_violations()
        assert len(violations) == 1
        assert violations[0].doctrine_id == DoctrineID.DOC_003
        assert violations[0].action == EnforcementAction.BLOCK_EXECUTION
    
    def test_audit_gap_blocks_execution(self):
        """Audit gap should block execution."""
        enforcer = DoctrineEnforcer()
        enforcer.check_audit_coverage(audited_count=99, total_count=100)
        
        allowed, msg = enforcer.is_execution_allowed()
        assert allowed is False


class TestDOC005OperatorConsoleSupremacy:
    """Test DOC-005: Operator Console Supremacy - 100% visibility."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_full_visibility(self):
        """100% visibility should pass."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_visibility(visible_states=50, total_states=50)
        
        assert result.passed is True
        assert result.doctrine_id == DoctrineID.DOC_005
    
    def test_no_states_passes(self):
        """No states should pass."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_visibility(visible_states=0, total_states=0)
        assert result.passed is True
    
    def test_visibility_gap_detected(self):
        """Visibility gap should fail and record violation."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_visibility(visible_states=45, total_states=50)
        
        assert result.passed is False
        assert "VISIBILITY GAP" in result.message
        assert result.details["hidden"] == 5
        
        # Verify violation recorded
        violations = enforcer.get_violations()
        assert len(violations) == 1
        assert violations[0].doctrine_id == DoctrineID.DOC_005
        assert violations[0].action == EnforcementAction.BLOCK_EXECUTION


class TestDOC006FailClosed:
    """Test DOC-006: Fail-Closed as Revenue Strategy."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_no_ambiguous_outcomes(self):
        """No ambiguous outcomes should pass."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_fail_closed(ambiguous_outcomes=0)
        
        assert result.passed is True
        assert result.doctrine_id == DoctrineID.DOC_006
    
    def test_ambiguous_outcomes_detected(self):
        """Ambiguous outcomes should fail and record violation."""
        enforcer = DoctrineEnforcer()
        result = enforcer.check_fail_closed(ambiguous_outcomes=3)
        
        assert result.passed is False
        assert "AMBIGUOUS" in result.message
        
        # Verify violation recorded
        violations = enforcer.get_violations()
        assert len(violations) == 1
        assert violations[0].doctrine_id == DoctrineID.DOC_006
        assert violations[0].action == EnforcementAction.ROLLBACK


class TestViolationSeverity:
    """Test violation severity levels."""
    
    def test_all_severity_levels(self):
        """Verify all severity levels exist."""
        expected = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        actual = {s.value for s in ViolationSeverity}
        assert actual == expected


class TestEnforcementAction:
    """Test enforcement actions."""
    
    def test_all_actions_defined(self):
        """Verify all enforcement actions exist."""
        expected = {
            "BLOCK_MERGE", "BLOCK_EXECUTION", "ROLLBACK",
            "ALERT", "INCIDENT_REPORT", "LOG"
        }
        actual = {a.value for a in EnforcementAction}
        assert actual == expected


class TestBlockingViolations:
    """Test blocking violation detection."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_get_blocking_violations(self):
        """Test retrieval of blocking violations."""
        enforcer = DoctrineEnforcer()
        
        # Create test regression (BLOCK_MERGE)
        enforcer.set_test_baseline(100)
        enforcer.check_test_regression(50)
        
        # Create audit gap (BLOCK_EXECUTION)
        enforcer.check_audit_coverage(50, 100)
        
        blocking = enforcer.get_blocking_violations()
        assert len(blocking) == 2
    
    def test_non_blocking_violations_excluded(self):
        """Non-blocking violations should not be in blocking list."""
        enforcer = DoctrineEnforcer()
        
        # Manually add a LOG-level violation
        enforcer._record_violation(
            doctrine_id=DoctrineID.DOC_007,
            description="Test",
            severity=ViolationSeverity.LOW,
            action=EnforcementAction.LOG,
            context={}
        )
        
        blocking = enforcer.get_blocking_violations()
        assert len(blocking) == 0


class TestComplianceReport:
    """Test compliance report generation."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_report_structure(self):
        """Test report contains required fields."""
        enforcer = DoctrineEnforcer()
        report = enforcer.get_compliance_report()
        
        assert "timestamp" in report
        assert "execution_allowed" in report
        assert "total_violations" in report
        assert "blocking_violations" in report
        assert "violations" in report
        assert "doctrine_status" in report
    
    def test_report_accuracy(self):
        """Test report values are accurate."""
        enforcer = DoctrineEnforcer()
        enforcer.set_test_baseline(100)
        enforcer.check_test_regression(50)
        
        report = enforcer.get_compliance_report()
        
        assert report["execution_allowed"] is False
        assert report["total_violations"] == 1
        assert report["blocking_violations"] == 1
        assert report["doctrine_status"]["DOC-001"] == "VIOLATION"


class TestGlobalEnforcerFunctions:
    """Test global enforcer convenience functions."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_get_doctrine_enforcer_singleton(self):
        """Test get_doctrine_enforcer returns singleton."""
        e1 = get_doctrine_enforcer()
        e2 = get_doctrine_enforcer()
        assert e1 is e2
    
    def test_check_doctrine_gate(self):
        """Test doctrine gate check function."""
        # Initially should pass
        passed, msg = check_doctrine_gate()
        assert passed is True
        
        # Add violation
        enforcer = get_doctrine_enforcer()
        enforcer.set_test_baseline(100)
        enforcer.check_test_regression(50)
        
        passed, msg = check_doctrine_gate()
        assert passed is False
    
    def test_get_compliance_report(self):
        """Test compliance report retrieval."""
        report = get_compliance_report()
        assert isinstance(report, dict)
        assert "execution_allowed" in report


class TestMultipleViolations:
    """Test handling of multiple violations."""
    
    def setup_method(self):
        reset_doctrine_enforcer()
    
    def test_multiple_violations_all_recorded(self):
        """Multiple violations should all be recorded."""
        enforcer = DoctrineEnforcer()
        
        # Create multiple violations
        enforcer.set_test_baseline(100)
        enforcer.check_test_regression(50)      # DOC-001
        enforcer.check_audit_coverage(50, 100)   # DOC-003
        enforcer.check_visibility(50, 100)       # DOC-005
        enforcer.check_fail_closed(5)            # DOC-006
        
        violations = enforcer.get_violations()
        assert len(violations) == 4
        
        doctrine_ids = {v.doctrine_id for v in violations}
        expected = {
            DoctrineID.DOC_001,
            DoctrineID.DOC_003,
            DoctrineID.DOC_005,
            DoctrineID.DOC_006
        }
        assert doctrine_ids == expected
    
    def test_multiple_blocking_violations_block_execution(self):
        """Multiple blocking violations should block execution."""
        enforcer = DoctrineEnforcer()
        
        enforcer.set_test_baseline(100)
        enforcer.check_test_regression(50)
        enforcer.check_audit_coverage(50, 100)
        
        allowed, msg = enforcer.is_execution_allowed()
        assert allowed is False
        assert "blocked" in msg.lower()
