"""
Tests for Pre-Merge Scorer

PAC Reference: PAC-JEFFREY-P50
Agent: CODY (GID-01) — Test Generation

Tests the PreMergeScorer, MergeRiskScore, RiskLevel,
RiskFactor, TestSummary, and CoverageInfo components.
"""

import pytest
from datetime import datetime

from core.occ.testing.premerge_scorer import (
    PreMergeScorer,
    MergeRiskScore,
    RiskLevel,
    RiskCategory,
    RiskFactor,
    TestSummary,
    CoverageInfo,
    ScorerError,
    quick_merge_check,
    create_blocking_factor,
)


class TestRiskLevel:
    """Tests for RiskLevel enum."""
    
    def test_all_risk_levels(self):
        """Test all risk levels exist."""
        assert RiskLevel.CRITICAL.value == "CRITICAL"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MINIMAL.value == "MINIMAL"


class TestRiskCategory:
    """Tests for RiskCategory enum."""
    
    def test_all_categories(self):
        """Test all categories exist."""
        assert RiskCategory.TEST_FAILURE.value == "TEST_FAILURE"
        assert RiskCategory.CCI_REGRESSION.value == "CCI_REGRESSION"
        assert RiskCategory.COVERAGE_DROP.value == "COVERAGE_DROP"
        assert RiskCategory.SECURITY.value == "SECURITY"
        assert RiskCategory.COMPLEXITY.value == "COMPLEXITY"


class TestRiskFactor:
    """Tests for RiskFactor dataclass."""
    
    def test_risk_factor_creation(self):
        """Test risk factor creation."""
        factor = RiskFactor(
            category=RiskCategory.TEST_FAILURE,
            description="5 tests failed",
            weight=0.5,
        )
        
        assert factor.category == RiskCategory.TEST_FAILURE
        assert factor.description == "5 tests failed"
        assert factor.weight == 0.5
    
    def test_risk_factor_with_mitigation(self):
        """Test risk factor with mitigation."""
        factor = RiskFactor(
            category=RiskCategory.SECURITY,
            description="Security issue",
            weight=1.0,
            mitigation="Apply security patch",
        )
        
        assert factor.mitigation == "Apply security patch"
    
    def test_risk_factor_to_dict(self):
        """Test risk factor serialization."""
        factor = RiskFactor(
            category=RiskCategory.COVERAGE_DROP,
            description="Coverage decreased",
            weight=0.3,
        )
        
        data = factor.to_dict()
        
        assert data["category"] == "COVERAGE_DROP"
        assert data["weight"] == 0.3


class TestTestSummary:
    """Tests for TestSummary dataclass."""
    
    def test_summary_creation(self):
        """Test summary creation."""
        summary = TestSummary(
            total_tests=100,
            passed=95,
            failed=3,
            skipped=2,
            duration_seconds=30.5,
        )
        
        assert summary.total_tests == 100
        assert summary.passed == 95
        assert summary.failed == 3
    
    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        summary = TestSummary(
            total_tests=100,
            passed=90,
            failed=8,
            skipped=2,
            duration_seconds=10,
        )
        
        # 90 passed / 98 executed = ~91.8%
        assert summary.pass_rate == pytest.approx(91.8, abs=0.1)
    
    def test_pass_rate_all_skipped(self):
        """Test pass rate when all tests skipped."""
        summary = TestSummary(
            total_tests=10,
            passed=0,
            failed=0,
            skipped=10,
            duration_seconds=0,
        )
        
        assert summary.pass_rate == 0.0
    
    def test_all_passed_property(self):
        """Test all_passed property."""
        passed_summary = TestSummary(100, 98, 0, 2, 10)
        failed_summary = TestSummary(100, 95, 3, 2, 10)
        
        assert passed_summary.all_passed is True
        assert failed_summary.all_passed is False
    
    def test_summary_to_dict(self):
        """Test summary serialization."""
        summary = TestSummary(50, 48, 1, 1, 5.0)
        data = summary.to_dict()
        
        assert data["total_tests"] == 50
        assert data["all_passed"] is False


class TestCoverageInfo:
    """Tests for CoverageInfo dataclass."""
    
    def test_coverage_info_creation(self):
        """Test coverage info creation."""
        coverage = CoverageInfo(
            line_coverage=85.5,
            branch_coverage=75.0,
            previous_line_coverage=80.0,
            previous_branch_coverage=70.0,
        )
        
        assert coverage.line_coverage == 85.5
        assert coverage.branch_coverage == 75.0
    
    def test_coverage_delta(self):
        """Test coverage delta calculation."""
        coverage = CoverageInfo(
            line_coverage=90.0,
            branch_coverage=80.0,
            previous_line_coverage=85.0,
            previous_branch_coverage=75.0,
        )
        
        assert coverage.line_coverage_delta == 5.0
        assert coverage.branch_coverage_delta == 5.0
    
    def test_regression_detection(self):
        """Test regression detection."""
        regression = CoverageInfo(
            line_coverage=80.0,
            branch_coverage=70.0,
            previous_line_coverage=85.0,
            previous_branch_coverage=75.0,
        )
        
        improvement = CoverageInfo(
            line_coverage=90.0,
            branch_coverage=80.0,
            previous_line_coverage=85.0,
            previous_branch_coverage=75.0,
        )
        
        assert regression.is_regression is True
        assert improvement.is_regression is False
    
    def test_coverage_to_dict(self):
        """Test coverage serialization."""
        coverage = CoverageInfo(85, 75, 80, 70)
        data = coverage.to_dict()
        
        assert data["line_coverage"] == 85
        assert "is_regression" in data


class TestPreMergeScorer:
    """Tests for PreMergeScorer class."""
    
    def test_scorer_creation(self):
        """Test scorer creation."""
        scorer = PreMergeScorer()
        
        assert scorer is not None
    
    def test_score_merge_request_passing(self):
        """Test scoring a passing merge request."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        
        score = scorer.score_merge_request(
            merge_request_id="MR-123",
            test_summary=summary,
            cci_before=1.0,
            cci_after=1.05,
        )
        
        assert score.can_merge is True
        assert score.risk_level in {RiskLevel.MINIMAL, RiskLevel.LOW}
    
    def test_score_merge_request_failing(self):
        """Test scoring a failing merge request."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 50, 50, 0, 10.0)
        
        score = scorer.score_merge_request(
            merge_request_id="MR-456",
            test_summary=summary,
            cci_before=1.0,
            cci_after=0.8,
        )
        
        assert score.can_merge is False
        # With test failures, risk level should be at least MEDIUM
        assert score.risk_level in {RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM}
    
    def test_cci_regression_factor(self):
        """Test CCI regression creates risk factor."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        
        score = scorer.score_merge_request(
            merge_request_id="MR",
            test_summary=summary,
            cci_before=1.0,
            cci_after=0.9,
        )
        
        assert score.is_cci_regression is True
        cci_factors = [f for f in score.risk_factors if f.category == RiskCategory.CCI_REGRESSION]
        assert len(cci_factors) > 0
    
    def test_coverage_info_analysis(self):
        """Test coverage analysis."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        coverage = CoverageInfo(70.0, 60.0, 85.0, 75.0)  # Regression
        
        score = scorer.score_merge_request(
            merge_request_id="MR",
            test_summary=summary,
            cci_before=1.0,
            cci_after=1.0,
            coverage_info=coverage,
        )
        
        coverage_factors = [f for f in score.risk_factors if f.category == RiskCategory.COVERAGE_DROP]
        assert len(coverage_factors) > 0
    
    def test_additional_factors(self):
        """Test adding additional risk factors."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        extra_factor = RiskFactor(
            category=RiskCategory.BREAKING_CHANGE,
            description="API breaking change",
            weight=0.9,
        )
        
        score = scorer.score_merge_request(
            merge_request_id="MR",
            test_summary=summary,
            cci_before=1.0,
            cci_after=1.0,
            additional_factors=[extra_factor],
        )
        
        breaking_factors = [f for f in score.risk_factors if f.category == RiskCategory.BREAKING_CHANGE]
        assert len(breaking_factors) == 1
    
    def test_quick_score(self):
        """Test quick scoring."""
        scorer = PreMergeScorer()
        
        score, level = scorer.quick_score(95, 5, -0.05)
        
        assert isinstance(score, float)
        assert isinstance(level, RiskLevel)
    
    def test_scoring_history(self):
        """Test scoring history."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        
        for i in range(5):
            scorer.score_merge_request(
                merge_request_id=f"MR-{i}",
                test_summary=summary,
                cci_before=1.0,
                cci_after=1.0,
            )
        
        history = scorer.get_scoring_history(3)
        
        assert len(history) == 3
    
    def test_get_score_by_id(self):
        """Test retrieving score by ID."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        score = scorer.score_merge_request(
            merge_request_id="MR",
            test_summary=summary,
            cci_before=1.0,
            cci_after=1.0,
        )
        
        retrieved = scorer.get_score(score.score_id)
        
        assert retrieved is not None
        assert retrieved.score_id == score.score_id
    
    def test_explain_score(self):
        """Test score explanation."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 95, 5, 0, 10.0)
        score = scorer.score_merge_request(
            merge_request_id="MR-EXPLAIN",
            test_summary=summary,
            cci_before=1.0,
            cci_after=0.95,
        )
        
        explanation = scorer.explain_score(score)
        
        assert "MR-EXPLAIN" in explanation
        assert "Risk Level" in explanation
        assert "Test Results" in explanation
    
    def test_blocking_factors(self):
        """Test blocking factors identification."""
        scorer = PreMergeScorer()
        
        summary = TestSummary(100, 100, 0, 0, 10.0)
        blocking = RiskFactor(
            category=RiskCategory.SECURITY,
            description="Critical vulnerability",
            weight=1.0,
        )
        
        score = scorer.score_merge_request(
            merge_request_id="MR",
            test_summary=summary,
            cci_before=1.0,
            cci_after=1.0,
            additional_factors=[blocking],
        )
        
        assert len(score.blocking_factors) > 0


class TestMergeRiskScore:
    """Tests for MergeRiskScore dataclass."""
    
    def test_score_properties(self):
        """Test score properties."""
        summary = TestSummary(100, 95, 5, 0, 10.0)
        
        score = MergeRiskScore(
            score_id="score123",
            merge_request_id="MR",
            overall_score=0.5,
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            test_summary=summary,
            coverage_info=None,
            cci_before=1.0,
            cci_after=0.95,
            can_merge=True,
            requires_approval=True,
        )
        
        assert score.cci_delta == pytest.approx(-0.05)
        assert score.is_cci_regression is True
    
    def test_score_to_dict(self):
        """Test score serialization."""
        summary = TestSummary(100, 100, 0, 0, 10.0)
        
        score = MergeRiskScore(
            score_id="id",
            merge_request_id="MR",
            overall_score=0.1,
            risk_level=RiskLevel.LOW,
            risk_factors=[],
            test_summary=summary,
            coverage_info=None,
            cci_before=1.0,
            cci_after=1.0,
            can_merge=True,
            requires_approval=False,
        )
        
        data = score.to_dict()
        
        assert data["score_id"] == "id"
        assert data["risk_level"] == "LOW"
        assert "cci_delta" in data


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_quick_merge_check_safe(self):
        """Test quick merge check for safe merge."""
        result = quick_merge_check(passed=100, failed=0, cci_delta=0.05)
        
        assert result is True
    
    def test_quick_merge_check_unsafe(self):
        """Test quick merge check for unsafe merge."""
        result = quick_merge_check(passed=50, failed=50, cci_delta=-0.1)
        
        assert result is False
    
    def test_create_blocking_factor(self):
        """Test creating blocking factor."""
        factor = create_blocking_factor("Breaking API change")
        
        assert factor.weight == 1.0
        assert factor.category == RiskCategory.BREAKING_CHANGE
        assert "Breaking API change" in factor.description
    
    def test_create_blocking_factor_custom_category(self):
        """Test creating blocking factor with custom category."""
        factor = create_blocking_factor("Security issue", RiskCategory.SECURITY)
        
        assert factor.category == RiskCategory.SECURITY
