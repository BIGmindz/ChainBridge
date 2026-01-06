"""
Chaos Coverage Index (CCI) Tests

PAC Reference: PAC-JEFFREY-P47
Doctrine: DOC-002 - Chaos Coverage Index
Tests verify CCI monotonicity and threshold enforcement.
"""

import pytest
from datetime import datetime

from core.occ.governance.chaos_coverage_index import (
    ChaosCoverageIndex,
    ChaosDimension,
    ChaosTest,
    get_cci,
    reset_cci,
    register_chaos_test,
    check_cci_gate,
    get_cci_report,
)


class TestChaosDimension:
    """Test chaos dimension enumeration."""
    
    def test_all_dimensions_defined(self):
        """Verify all canonical dimensions exist."""
        expected = {"AUTH", "STATE", "CONC", "TIME", "DATA", "GOV"}
        actual = {d.value for d in ChaosDimension}
        assert actual == expected
    
    def test_dimension_count(self):
        """Verify exactly 6 canonical dimensions."""
        assert len(ChaosDimension) == 6


class TestChaosCoverageIndex:
    """Test CCI core functionality."""
    
    def setup_method(self):
        """Reset CCI before each test."""
        reset_cci()
    
    def test_empty_cci_is_zero(self):
        """Empty CCI should be 0."""
        cci = ChaosCoverageIndex()
        assert cci.calculate_cci() == 0.0
    
    def test_register_chaos_test(self):
        """Test registering a chaos test."""
        cci = ChaosCoverageIndex()
        test = cci.register_chaos_test(
            test_id="CT-001",
            dimension=ChaosDimension.AUTH,
            description="Test auth failure",
            test_path="tests/chaos/test_auth.py",
            pac_reference="PAC-TEST"
        )
        assert test.test_id == "CT-001"
        assert test.dimension == ChaosDimension.AUTH
        assert cci.get_dimension_count(ChaosDimension.AUTH) == 1
    
    def test_cci_calculation(self):
        """Test CCI calculation formula."""
        cci = ChaosCoverageIndex()
        
        # Register 6 tests, one per dimension
        for i, dim in enumerate(ChaosDimension):
            cci.register_chaos_test(
                test_id=f"CT-{i:03d}",
                dimension=dim,
                description=f"Test {dim.value}",
                test_path=f"tests/chaos/test_{dim.value.lower()}.py",
                pac_reference="PAC-TEST"
            )
        
        # CCI = 6 tests / 6 dimensions = 1.0
        assert cci.calculate_cci() == 1.0
    
    def test_cci_calculation_uneven(self):
        """Test CCI with uneven distribution."""
        cci = ChaosCoverageIndex()
        
        # Register 12 tests for AUTH only
        for i in range(12):
            cci.register_chaos_test(
                test_id=f"CT-AUTH-{i:03d}",
                dimension=ChaosDimension.AUTH,
                description=f"Auth test {i}",
                test_path="tests/chaos/test_auth.py",
                pac_reference="PAC-TEST"
            )
        
        # CCI = 12 tests / 6 dimensions = 2.0
        assert cci.calculate_cci() == 2.0
    
    def test_uncovered_dimensions(self):
        """Test identifying uncovered dimensions."""
        cci = ChaosCoverageIndex()
        
        # Register tests for AUTH and DATA only
        cci.register_chaos_test("CT-001", ChaosDimension.AUTH, "Auth", "test.py", "PAC")
        cci.register_chaos_test("CT-002", ChaosDimension.DATA, "Data", "test.py", "PAC")
        
        uncovered = cci.get_uncovered_dimensions()
        expected = {ChaosDimension.STATE, ChaosDimension.CONC, ChaosDimension.TIME, ChaosDimension.GOV}
        assert uncovered == expected


class TestCCIMonotonicity:
    """Test CCI monotonicity enforcement per DOC-002."""
    
    def setup_method(self):
        reset_cci()
    
    def test_monotonicity_no_baseline(self):
        """Monotonicity check passes with no baseline."""
        cci = ChaosCoverageIndex()
        is_valid, msg = cci.check_monotonicity()
        assert is_valid is True
    
    def test_monotonicity_maintained(self):
        """Monotonicity check passes when CCI increases."""
        cci = ChaosCoverageIndex()
        
        # Set baseline with 6 tests
        for i, dim in enumerate(ChaosDimension):
            cci.register_chaos_test(f"CT-{i}", dim, "Test", "test.py", "PAC")
        cci.set_baseline("PAC-BASELINE")
        
        # Add more tests
        cci.register_chaos_test("CT-NEW-1", ChaosDimension.AUTH, "New", "test.py", "PAC")
        cci.register_chaos_test("CT-NEW-2", ChaosDimension.AUTH, "New", "test.py", "PAC")
        
        is_valid, msg = cci.check_monotonicity()
        assert is_valid is True
        assert "maintained" in msg.lower()
    
    def test_monotonicity_violation_detected(self):
        """Monotonicity violation detected when CCI would decrease."""
        cci = ChaosCoverageIndex()
        
        # Set high baseline
        cci._baseline_cci = 10.0
        
        # Current CCI is 0
        is_valid, msg = cci.check_monotonicity()
        assert is_valid is False
        assert "DECREASE" in msg
        assert "DOC-002" in msg


class TestCCIThreshold:
    """Test CCI threshold enforcement per DOC-002."""
    
    def setup_method(self):
        reset_cci()
    
    def test_threshold_met(self):
        """Threshold check passes when CCI >= threshold."""
        cci = ChaosCoverageIndex()
        
        # Add enough tests to meet threshold (1.0)
        for i, dim in enumerate(ChaosDimension):
            cci.register_chaos_test(f"CT-{i}", dim, "Test", "test.py", "PAC")
        
        meets, msg = cci.check_threshold()
        assert meets is True
    
    def test_threshold_not_met(self):
        """Threshold check fails when CCI < threshold."""
        cci = ChaosCoverageIndex()
        
        # Only add 1 test (CCI = 1/6 ≈ 0.17)
        cci.register_chaos_test("CT-001", ChaosDimension.AUTH, "Test", "test.py", "PAC")
        
        meets, msg = cci.check_threshold()
        assert meets is False
        assert "BELOW THRESHOLD" in msg
        assert "DOC-002" in msg


class TestCCIExecutionGate:
    """Test CCI execution gate per DOC-002."""
    
    def setup_method(self):
        reset_cci()
    
    def test_execution_allowed_when_compliant(self):
        """Execution allowed when CCI meets all requirements."""
        cci = ChaosCoverageIndex()
        
        # Meet threshold
        for i, dim in enumerate(ChaosDimension):
            cci.register_chaos_test(f"CT-{i}", dim, "Test", "test.py", "PAC")
        
        allowed, msg = cci.verify_execution_allowed()
        assert allowed is True
    
    def test_execution_blocked_below_threshold(self):
        """Execution blocked when CCI below threshold."""
        cci = ChaosCoverageIndex()
        
        # Only 1 test (below threshold)
        cci.register_chaos_test("CT-001", ChaosDimension.AUTH, "Test", "test.py", "PAC")
        
        allowed, msg = cci.verify_execution_allowed()
        assert allowed is False


class TestCCISnapshot:
    """Test CCI snapshot functionality."""
    
    def setup_method(self):
        reset_cci()
    
    def test_take_snapshot(self):
        """Test snapshot captures current state."""
        cci = ChaosCoverageIndex()
        
        for i, dim in enumerate(ChaosDimension):
            cci.register_chaos_test(f"CT-{i}", dim, "Test", "test.py", "PAC-TEST")
        
        snapshot = cci.take_snapshot("PAC-SNAPSHOT")
        
        assert snapshot.pac_reference == "PAC-SNAPSHOT"
        assert snapshot.total_chaos_tests == 6
        assert snapshot.cci_value == 1.0
        assert snapshot.timestamp is not None


class TestCCICoverageReport:
    """Test CCI coverage report generation."""
    
    def setup_method(self):
        reset_cci()
    
    def test_coverage_report_structure(self):
        """Test report contains required fields."""
        cci = ChaosCoverageIndex()
        
        for i, dim in enumerate(ChaosDimension):
            cci.register_chaos_test(f"CT-{i}", dim, "Test", "test.py", "PAC")
        
        report = cci.get_coverage_report()
        
        assert "cci_value" in report
        assert "cci_threshold" in report
        assert "threshold_met" in report
        assert "dimensions" in report
        assert "uncovered_dimensions" in report
        assert "execution_allowed" in report
        assert "coverage_percentage" in report
    
    def test_coverage_report_accuracy(self):
        """Test report values are accurate."""
        cci = ChaosCoverageIndex()
        
        # Cover only AUTH dimension
        cci.register_chaos_test("CT-001", ChaosDimension.AUTH, "Test", "test.py", "PAC")
        
        report = cci.get_coverage_report()
        
        assert report["total_chaos_tests"] == 1
        assert report["dimensions"]["AUTH"]["count"] == 1
        assert report["dimensions"]["AUTH"]["covered"] is True
        assert len(report["uncovered_dimensions"]) == 5
        assert report["coverage_percentage"] == pytest.approx(16.67, rel=0.1)


class TestGlobalCCIFunctions:
    """Test global CCI convenience functions."""
    
    def setup_method(self):
        reset_cci()
    
    def test_get_cci_singleton(self):
        """Test get_cci returns singleton."""
        cci1 = get_cci()
        cci2 = get_cci()
        assert cci1 is cci2
    
    def test_register_chaos_test_convenience(self):
        """Test convenience registration function."""
        test = register_chaos_test(
            test_id="CT-CONV-001",
            dimension="AUTH",
            description="Convenience test",
            test_path="test.py",
            pac_reference="PAC-CONV"
        )
        
        assert test.test_id == "CT-CONV-001"
        assert test.dimension == ChaosDimension.AUTH
    
    def test_check_cci_gate(self):
        """Test CCI gate check function."""
        # Empty CCI should fail threshold
        passed, msg = check_cci_gate()
        assert passed is False
        
        # Add enough tests
        for i, dim in enumerate(ChaosDimension):
            register_chaos_test(f"CT-{i}", dim.value, "Test", "test.py", "PAC")
        
        passed, msg = check_cci_gate()
        assert passed is True
    
    def test_get_cci_report(self):
        """Test CCI report retrieval."""
        report = get_cci_report()
        assert isinstance(report, dict)
        assert "cci_value" in report
