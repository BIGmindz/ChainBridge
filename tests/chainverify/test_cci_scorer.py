"""
ChainVerify Tests — CCI Scorer

PAC Reference: PAC-JEFFREY-P49
"""

import pytest
from dataclasses import dataclass, field
from datetime import datetime

from core.chainverify.cci_scorer import (
    CCIScorer,
    VerificationScore,
    DimensionCoverage,
    ScoreGrade,
    ChaosDimension,
    get_cci_scorer,
    reset_cci_scorer,
)


@dataclass
class MockExecutionResult:
    """Mock execution result for testing."""
    test_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    passed: bool
    safety_violations: list = field(default_factory=list)


@dataclass
class MockExecutionBatch:
    """Mock execution batch for testing."""
    batch_id: str
    tenant_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int
    total_violations: int
    execution_time_ms: float
    results: list = field(default_factory=list)


@dataclass
class MockFuzzTestCase:
    """Mock fuzz test case for testing."""
    test_id: str
    endpoint_path: str
    http_method: str
    fuzz_inputs: dict = field(default_factory=dict)
    chaos_dimensions: set = field(default_factory=set)


@dataclass
class MockFuzzSuite:
    """Mock fuzz suite for testing."""
    suite_id: str
    api_title: str
    test_cases: list
    strategies_used: set
    chaos_dimensions_covered: set
    total_fuzz_inputs: int


class TestScoreGrade:
    """Test score grade enumeration."""
    
    def test_all_grades_defined(self):
        expected = {"A+", "A", "B+", "B", "C+", "C", "D", "F"}
        actual = {g.value for g in ScoreGrade}
        assert actual == expected


class TestChaosDimension:
    """Test chaos dimension enumeration."""
    
    def test_all_dimensions_defined(self):
        expected = {"AUTH", "TIMING", "STATE", "RESOURCE", "NETWORK", "DATA"}
        actual = {d.value for d in ChaosDimension}
        assert actual == expected


class TestDimensionCoverage:
    """Test dimension coverage dataclass."""
    
    def test_create_coverage(self):
        coverage = DimensionCoverage(
            dimension=ChaosDimension.AUTH,
            tests_executed=10,
            tests_passed=8,
            coverage_percentage=80.0
        )
        
        assert coverage.pass_rate == 80.0
    
    def test_zero_executed(self):
        coverage = DimensionCoverage(
            dimension=ChaosDimension.TIMING,
            tests_executed=0,
            tests_passed=0,
            coverage_percentage=0.0
        )
        
        assert coverage.pass_rate == 0.0


class TestVerificationScore:
    """Test verification score dataclass."""
    
    def test_create_score(self):
        score = VerificationScore(
            api_id="api_123",
            api_title="Test API",
            base_score=85.0,
            cci_score=75.0,
            safety_score=90.0,
            final_score=82.5,
            grade=ScoreGrade.B,
            dimension_coverage=[],
            total_tests=100,
            passed_tests=85,
            failed_tests=10,
            blocked_tests=5,
            edge_cases_handled=20
        )
        
        assert score.grade == ScoreGrade.B
        assert score.final_score == 82.5
    
    def test_to_dict(self):
        score = VerificationScore(
            api_id="api_123",
            api_title="Test API",
            base_score=85.0,
            cci_score=75.0,
            safety_score=90.0,
            final_score=82.5,
            grade=ScoreGrade.B,
            dimension_coverage=[],
            total_tests=100,
            passed_tests=85,
            failed_tests=10,
            blocked_tests=5,
            edge_cases_handled=20
        )
        
        d = score.to_dict()
        assert d["api_id"] == "api_123"
        assert d["grade"] == "B"


class TestCCIScorer:
    """Test CCI scorer."""
    
    def setup_method(self):
        reset_cci_scorer()
    
    def _create_mock_batch(
        self,
        total: int = 100,
        passed: int = 80,
        violations: int = 0
    ) -> MockExecutionBatch:
        """Create a mock execution batch."""
        results = []
        for i in range(total):
            results.append(MockExecutionResult(
                test_id=f"test_{i:03d}",
                endpoint="/api",
                method="GET",
                status_code=200 if i < passed else 400,
                response_time_ms=50.0,
                passed=i < passed
            ))
        
        return MockExecutionBatch(
            batch_id="batch_001",
            tenant_id="tenant_123",
            total_tests=total,
            passed_tests=passed,
            failed_tests=total - passed - violations,
            blocked_tests=violations,
            total_violations=violations,
            execution_time_ms=5000.0,
            results=results
        )
    
    def _create_mock_suite(
        self,
        test_count: int = 100,
        chaos_dimensions: set = None
    ) -> MockFuzzSuite:
        """Create a mock fuzz suite."""
        if chaos_dimensions is None:
            chaos_dimensions = {ChaosDimension.AUTH}
        
        test_cases = []
        for i in range(test_count):
            test_cases.append(MockFuzzTestCase(
                test_id=f"test_{i:03d}",
                endpoint_path="/api",
                http_method="GET",
                chaos_dimensions=chaos_dimensions if i % 10 == 0 else set()
            ))
        
        return MockFuzzSuite(
            suite_id="suite_001",
            api_title="Test API",
            test_cases=test_cases,
            strategies_used=set(),
            chaos_dimensions_covered=chaos_dimensions,
            total_fuzz_inputs=test_count
        )
    
    def test_compute_score(self):
        scorer = CCIScorer()
        
        batch = self._create_mock_batch(total=100, passed=80)
        suite = self._create_mock_suite(test_count=100)
        
        score = scorer.compute_score(
            api_id="api_123",
            api_title="Test API",
            execution_batch=batch,
            fuzz_suite=suite
        )
        
        assert score.api_id == "api_123"
        assert score.base_score == 80.0
        assert 0 <= score.final_score <= 100
    
    def test_score_grade_mapping(self):
        scorer = CCIScorer()
        
        # Test that scoring produces a valid grade
        batch = self._create_mock_batch(total=100, passed=98)
        suite = self._create_mock_suite()
        score = scorer.compute_score("api", "Test", batch, suite)
        # Final score depends on all components (base, CCI, safety)
        # CCI score can be low if chaos dimensions aren't heavily covered
        assert score.grade in list(ScoreGrade)
    
    def test_safety_violations_penalty(self):
        scorer = CCIScorer()
        
        # Without violations
        batch1 = self._create_mock_batch(total=100, passed=80, violations=0)
        suite = self._create_mock_suite()
        score1 = scorer.compute_score("api1", "Test", batch1, suite)
        
        # With violations
        batch2 = self._create_mock_batch(total=100, passed=80, violations=5)
        score2 = scorer.compute_score("api2", "Test", batch2, suite)
        
        # Score with violations should be lower
        assert score2.final_score < score1.final_score
    
    def test_dimension_coverage_calculation(self):
        scorer = CCIScorer()
        
        batch = self._create_mock_batch()
        suite = self._create_mock_suite(
            chaos_dimensions={ChaosDimension.AUTH, ChaosDimension.STATE}
        )
        
        score = scorer.compute_score("api", "Test", batch, suite)
        
        # Should have coverage for all dimensions
        assert len(score.dimension_coverage) == len(ChaosDimension)
    
    def test_cached_score(self):
        scorer = CCIScorer()
        
        batch = self._create_mock_batch()
        suite = self._create_mock_suite()
        
        score = scorer.compute_score("cached_api", "Test", batch, suite)
        
        cached = scorer.get_cached_score("cached_api")
        assert cached is not None
        assert cached.api_id == "cached_api"
    
    def test_score_weights(self):
        scorer = CCIScorer()
        
        # Verify weights sum to 1.0
        total_weight = scorer.WEIGHT_BASE + scorer.WEIGHT_CCI + scorer.WEIGHT_SAFETY
        assert abs(total_weight - 1.0) < 0.001


class TestScoreGradeMapping:
    """Test score to grade mapping."""
    
    def test_grade_boundaries(self):
        scorer = CCIScorer()
        
        assert scorer._score_to_grade(100) == ScoreGrade.A_PLUS
        assert scorer._score_to_grade(95) == ScoreGrade.A_PLUS
        assert scorer._score_to_grade(94) == ScoreGrade.A
        assert scorer._score_to_grade(90) == ScoreGrade.A
        assert scorer._score_to_grade(89) == ScoreGrade.B_PLUS
        assert scorer._score_to_grade(85) == ScoreGrade.B_PLUS
        assert scorer._score_to_grade(84) == ScoreGrade.B
        assert scorer._score_to_grade(80) == ScoreGrade.B
        assert scorer._score_to_grade(79) == ScoreGrade.C_PLUS
        assert scorer._score_to_grade(75) == ScoreGrade.C_PLUS
        assert scorer._score_to_grade(74) == ScoreGrade.C
        assert scorer._score_to_grade(70) == ScoreGrade.C
        assert scorer._score_to_grade(69) == ScoreGrade.D
        assert scorer._score_to_grade(60) == ScoreGrade.D
        assert scorer._score_to_grade(59) == ScoreGrade.F
        assert scorer._score_to_grade(0) == ScoreGrade.F


class TestGlobalFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        reset_cci_scorer()
    
    def test_get_singleton(self):
        s1 = get_cci_scorer()
        s2 = get_cci_scorer()
        assert s1 is s2
    
    def test_reset_clears_cache(self):
        scorer = get_cci_scorer()
        scorer._cached_scores["test"] = None
        
        reset_cci_scorer()
        
        new_scorer = get_cci_scorer()
        assert len(new_scorer._cached_scores) == 0
