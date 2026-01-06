"""
Test Intelligence Engine Tests

PAC Reference: PAC-JEFFREY-P48
Tests for test intelligence scoring and risk prediction.
"""

import pytest
from datetime import datetime

from core.occ.testing.test_intelligence import (
    TestIntelligenceEngine,
    TestIntelligenceScore,
    TestExecutionRecord,
    RiskTier,
    BlastRadiusCategory,
    get_test_intelligence_engine,
    reset_test_intelligence_engine,
    generate_pre_ber_risk_brief,
)


class TestRiskTier:
    """Test risk tier enumeration."""
    
    def test_all_tiers_defined(self):
        """Verify all risk tiers exist."""
        expected = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "BASELINE"}
        actual = {t.value for t in RiskTier}
        assert actual == expected


class TestBlastRadiusCategory:
    """Test blast radius categories."""
    
    def test_all_categories_defined(self):
        """Verify all blast radius categories exist."""
        expected = {"SYSTEM", "SERVICE", "MODULE", "FUNCTION", "ISOLATED"}
        actual = {c.value for c in BlastRadiusCategory}
        assert actual == expected


class TestTestIntelligenceEngine:
    """Test the core intelligence engine."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_register_test(self):
        """Test registering a test."""
        engine = TestIntelligenceEngine()
        
        score = engine.register_test(
            test_id="test_example",
            test_path="tests/test_example.py",
            affected_modules=["core/module"],
            chaos_dimensions={"AUTH"},
            blast_radius=BlastRadiusCategory.MODULE
        )
        
        assert score.test_id == "test_example"
        assert score.blast_radius == BlastRadiusCategory.MODULE
        assert "AUTH" in score.chaos_dimensions
    
    def test_record_execution_pass(self):
        """Test recording a passing execution."""
        engine = TestIntelligenceEngine()
        engine.register_test(
            test_id="test_pass",
            test_path="tests/test_pass.py",
            affected_modules=["core"]
        )
        
        engine.record_execution("test_pass", passed=True, duration_ms=10.0)
        
        score = engine._scores["test_pass"]
        assert score.execution_count == 1
        assert score.avg_duration_ms == 10.0
    
    def test_record_execution_fail(self):
        """Test recording a failing execution."""
        engine = TestIntelligenceEngine()
        engine.register_test(
            test_id="test_fail",
            test_path="tests/test_fail.py",
            affected_modules=["core"]
        )
        
        engine.record_execution("test_fail", passed=False, duration_ms=15.0, error_type="AssertionError")
        
        score = engine._scores["test_fail"]
        assert score.historical_failure_rate == 1.0
    
    def test_failure_probability_calculation(self):
        """Test failure probability updates with history."""
        engine = TestIntelligenceEngine()
        engine.register_test(
            test_id="test_mixed",
            test_path="tests/test_mixed.py",
            affected_modules=["core"]
        )
        
        # Record 10 executions: 3 failures
        for i in range(7):
            engine.record_execution("test_mixed", passed=True, duration_ms=10.0)
        for i in range(3):
            engine.record_execution("test_mixed", passed=False, duration_ms=12.0)
        
        score = engine._scores["test_mixed"]
        assert score.historical_failure_rate == 0.3
        assert score.execution_count == 10


class TestRiskClassification:
    """Test risk tier classification."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_baseline_for_new_tests(self):
        """New tests should be classified as BASELINE."""
        engine = TestIntelligenceEngine()
        score = engine.register_test(
            test_id="test_new",
            test_path="tests/test_new.py",
            affected_modules=["core"]
        )
        
        assert score.risk_tier == RiskTier.BASELINE
    
    def test_critical_classification(self):
        """High failure + high blast radius = CRITICAL."""
        engine = TestIntelligenceEngine()
        engine.register_test(
            test_id="test_critical",
            test_path="tests/test_critical.py",
            affected_modules=["core", "api", "auth"],
            blast_radius=BlastRadiusCategory.SYSTEM
        )
        
        # Record many failures
        for i in range(10):
            engine.record_execution("test_critical", passed=False, duration_ms=100.0)
        
        score = engine._scores["test_critical"]
        assert score.risk_tier == RiskTier.CRITICAL
    
    def test_low_classification(self):
        """Low failure + isolated = LOW."""
        engine = TestIntelligenceEngine()
        engine.register_test(
            test_id="test_stable",
            test_path="tests/test_stable.py",
            affected_modules=[],
            blast_radius=BlastRadiusCategory.ISOLATED
        )
        
        # Record many passes
        for i in range(20):
            engine.record_execution("test_stable", passed=True, duration_ms=5.0)
        
        score = engine._scores["test_stable"]
        assert score.risk_tier == RiskTier.LOW


class TestPriorityRanking:
    """Test priority ranking computation."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_compute_rankings(self):
        """Test priority ranking computation."""
        engine = TestIntelligenceEngine()
        
        # Register tests with different risk profiles
        engine.register_test("test_high", "tests/high.py", ["core", "api"], 
                           blast_radius=BlastRadiusCategory.SYSTEM)
        engine.register_test("test_low", "tests/low.py", [],
                           blast_radius=BlastRadiusCategory.ISOLATED)
        
        # Make high-risk test fail
        engine.record_execution("test_high", passed=False, duration_ms=100.0)
        engine.record_execution("test_low", passed=True, duration_ms=5.0)
        
        rankings = engine.compute_priority_rankings()
        
        assert len(rankings) == 2
        assert rankings[0].test_id == "test_high"  # Higher priority
        assert rankings[0].priority_rank == 1
    
    def test_get_critical_tests(self):
        """Test retrieval of critical tests."""
        engine = TestIntelligenceEngine()
        
        engine.register_test("test_crit", "tests/crit.py", ["core", "api", "auth"],
                           blast_radius=BlastRadiusCategory.SYSTEM)
        
        for i in range(10):
            engine.record_execution("test_crit", passed=False, duration_ms=100.0)
        
        critical = engine.get_critical_tests()
        assert len(critical) == 1
        assert critical[0].test_id == "test_crit"


class TestChaosIntegration:
    """Test chaos dimension tracking."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_cci_contribution(self):
        """Test CCI contribution calculation."""
        engine = TestIntelligenceEngine()
        
        # Test covering 3 of 6 dimensions
        score = engine.register_test(
            test_id="test_chaos",
            test_path="tests/test_chaos.py",
            affected_modules=["core"],
            chaos_dimensions={"AUTH", "STATE", "DATA"}
        )
        
        assert score.cci_contribution == 0.5  # 3/6
    
    def test_get_tests_by_dimension(self):
        """Test filtering by chaos dimension."""
        engine = TestIntelligenceEngine()
        
        engine.register_test("test_auth", "tests/auth.py", ["auth"],
                           chaos_dimensions={"AUTH"})
        engine.register_test("test_data", "tests/data.py", ["data"],
                           chaos_dimensions={"DATA"})
        
        auth_tests = engine.get_tests_by_chaos_dimension("AUTH")
        assert len(auth_tests) == 1
        assert auth_tests[0].test_id == "test_auth"
    
    def test_cci_impact_report(self):
        """Test CCI impact report generation."""
        engine = TestIntelligenceEngine()
        
        engine.register_test("test_1", "tests/1.py", [], chaos_dimensions={"AUTH", "STATE"})
        engine.register_test("test_2", "tests/2.py", [], chaos_dimensions={"AUTH", "DATA"})
        
        report = engine.get_cci_impact_report()
        
        assert report["total_tests"] == 2
        assert report["dimension_coverage"]["AUTH"] == 2
        assert report["dimension_coverage"]["STATE"] == 1
        assert report["dimension_coverage"]["DATA"] == 1


class TestOptimizedTestOrder:
    """Test optimized execution ordering."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_optimized_order_without_budget(self):
        """Test ordering without time budget."""
        engine = TestIntelligenceEngine()
        
        engine.register_test("test_1", "tests/1.py", ["core"])
        engine.register_test("test_2", "tests/2.py", ["api"])
        
        order = engine.get_optimized_test_order()
        assert len(order) == 2
    
    def test_optimized_order_with_budget(self):
        """Test ordering with time budget."""
        engine = TestIntelligenceEngine()
        
        engine.register_test("test_fast", "tests/fast.py", [])
        engine.register_test("test_slow", "tests/slow.py", [])
        
        # Record durations
        engine.record_execution("test_fast", passed=True, duration_ms=10.0)
        engine.record_execution("test_slow", passed=True, duration_ms=100.0)
        
        # Budget only allows fast test
        order = engine.get_optimized_test_order(time_budget_ms=50.0)
        assert "test_fast" in order
        assert "test_slow" not in order


class TestPreBERRiskBrief:
    """Test Pre-BER Risk Brief generation."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_risk_brief_structure(self):
        """Test risk brief contains required fields."""
        engine = TestIntelligenceEngine()
        engine.register_test("test_1", "tests/1.py", ["core"])
        
        brief = engine.generate_risk_brief()
        
        assert "timestamp" in brief
        assert "advisory_only" in brief
        assert brief["advisory_only"] is True
        assert "total_tests_tracked" in brief
        assert "recommendations" in brief
    
    def test_risk_brief_recommendations(self):
        """Test risk brief generates recommendations."""
        engine = TestIntelligenceEngine()
        
        # Create critical test with failures
        engine.register_test("test_crit", "tests/crit.py", ["core", "api", "auth"],
                           blast_radius=BlastRadiusCategory.SYSTEM)
        for i in range(10):
            engine.record_execution("test_crit", passed=False, duration_ms=100.0)
        
        brief = engine.generate_risk_brief()
        
        assert len(brief["recommendations"]) > 0
        assert "critical" in brief["recommendations"][0].lower()


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def setup_method(self):
        reset_test_intelligence_engine()
    
    def test_get_engine_singleton(self):
        """Test singleton behavior."""
        e1 = get_test_intelligence_engine()
        e2 = get_test_intelligence_engine()
        assert e1 is e2
    
    def test_generate_pre_ber_risk_brief(self):
        """Test global brief generation."""
        brief = generate_pre_ber_risk_brief()
        assert isinstance(brief, dict)
        assert brief["advisory_only"] is True
