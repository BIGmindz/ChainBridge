"""
Always-On Test Engine — Pre-Merge Scorer

PAC Reference: PAC-JEFFREY-P50
Agent: BENSON (GID-00)

Scores merge requests based on test results, CCI impact, and risk
factors to provide pre-merge risk assessment.

INVARIANTS:
- Scoring is deterministic and explainable
- No mutation of repository or merge state
- Risk factors are auditable
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import hashlib


class RiskLevel(Enum):
    """Risk level for merge requests."""
    CRITICAL = "CRITICAL"  # Block merge
    HIGH = "HIGH"          # Require approval
    MEDIUM = "MEDIUM"      # Advisory warning
    LOW = "LOW"            # Safe to merge
    MINIMAL = "MINIMAL"    # No concerns


class RiskCategory(Enum):
    """Category of risk factor."""
    TEST_FAILURE = "TEST_FAILURE"
    CCI_REGRESSION = "CCI_REGRESSION"
    COVERAGE_DROP = "COVERAGE_DROP"
    SECURITY = "SECURITY"
    COMPLEXITY = "COMPLEXITY"
    DEPENDENCY = "DEPENDENCY"
    BREAKING_CHANGE = "BREAKING_CHANGE"


@dataclass
class RiskFactor:
    """A single risk factor affecting merge score."""
    category: RiskCategory
    description: str
    weight: float  # 0.0 to 1.0
    details: dict[str, Any] = field(default_factory=dict)
    mitigation: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "description": self.description,
            "weight": self.weight,
            "details": self.details,
            "mitigation": self.mitigation,
        }


@dataclass
class TestSummary:
    """Summary of test results for merge request."""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    new_tests: int = 0
    removed_tests: int = 0
    
    @property
    def pass_rate(self) -> float:
        executed = self.total_tests - self.skipped
        if executed == 0:
            return 0.0
        return (self.passed / executed) * 100
    
    @property
    def all_passed(self) -> bool:
        return self.failed == 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "duration_seconds": self.duration_seconds,
            "new_tests": self.new_tests,
            "removed_tests": self.removed_tests,
            "all_passed": self.all_passed,
        }


@dataclass
class CoverageInfo:
    """Coverage information for merge request."""
    line_coverage: float
    branch_coverage: float
    previous_line_coverage: float
    previous_branch_coverage: float
    
    @property
    def line_coverage_delta(self) -> float:
        return self.line_coverage - self.previous_line_coverage
    
    @property
    def branch_coverage_delta(self) -> float:
        return self.branch_coverage - self.previous_branch_coverage
    
    @property
    def is_regression(self) -> bool:
        return self.line_coverage_delta < -1.0 or self.branch_coverage_delta < -1.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "line_coverage": self.line_coverage,
            "branch_coverage": self.branch_coverage,
            "previous_line_coverage": self.previous_line_coverage,
            "previous_branch_coverage": self.previous_branch_coverage,
            "line_coverage_delta": self.line_coverage_delta,
            "branch_coverage_delta": self.branch_coverage_delta,
            "is_regression": self.is_regression,
        }


@dataclass
class MergeRiskScore:
    """Complete risk score for a merge request."""
    score_id: str
    merge_request_id: str
    overall_score: float  # 0.0 (safe) to 1.0 (critical)
    risk_level: RiskLevel
    risk_factors: list[RiskFactor]
    test_summary: TestSummary
    coverage_info: CoverageInfo | None
    cci_before: float
    cci_after: float
    can_merge: bool
    requires_approval: bool
    scored_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def cci_delta(self) -> float:
        return self.cci_after - self.cci_before
    
    @property
    def is_cci_regression(self) -> bool:
        return self.cci_delta < 0
    
    @property
    def blocking_factors(self) -> list[RiskFactor]:
        return [f for f in self.risk_factors if f.weight >= 0.8]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id": self.score_id,
            "merge_request_id": self.merge_request_id,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level.value,
            "risk_factors": [f.to_dict() for f in self.risk_factors],
            "blocking_factors_count": len(self.blocking_factors),
            "test_summary": self.test_summary.to_dict(),
            "coverage_info": self.coverage_info.to_dict() if self.coverage_info else None,
            "cci_before": self.cci_before,
            "cci_after": self.cci_after,
            "cci_delta": self.cci_delta,
            "is_cci_regression": self.is_cci_regression,
            "can_merge": self.can_merge,
            "requires_approval": self.requires_approval,
            "scored_at": self.scored_at.isoformat(),
        }


class ScorerError(Exception):
    """Error during merge scoring."""
    pass


class PreMergeScorer:
    """
    Pre-Merge Risk Scorer.
    
    Scores merge requests based on:
    - Test results (pass/fail, coverage)
    - CCI impact (delta, trends)
    - Risk factors (security, breaking changes)
    
    INVARIANTS:
    - Scoring is deterministic
    - No mutation of merge state
    - All factors are explainable
    """
    
    # Thresholds
    CRITICAL_THRESHOLD = 0.8
    HIGH_THRESHOLD = 0.6
    MEDIUM_THRESHOLD = 0.3
    
    # Weights for risk categories
    CATEGORY_WEIGHTS = {
        RiskCategory.TEST_FAILURE: 1.0,
        RiskCategory.CCI_REGRESSION: 0.7,
        RiskCategory.COVERAGE_DROP: 0.5,
        RiskCategory.SECURITY: 1.0,
        RiskCategory.COMPLEXITY: 0.3,
        RiskCategory.DEPENDENCY: 0.4,
        RiskCategory.BREAKING_CHANGE: 0.9,
    }
    
    def __init__(self):
        self._scoring_history: list[MergeRiskScore] = []
        self._base_cci = 1.0
    
    def score_merge_request(
        self,
        merge_request_id: str,
        test_summary: TestSummary,
        cci_before: float,
        cci_after: float,
        coverage_info: CoverageInfo | None = None,
        additional_factors: list[RiskFactor] | None = None,
    ) -> MergeRiskScore:
        """
        Score a merge request.
        
        Args:
            merge_request_id: ID of the merge request
            test_summary: Summary of test results
            cci_before: CCI before merge
            cci_after: CCI after merge
            coverage_info: Optional coverage information
            additional_factors: Additional risk factors to consider
        
        Returns:
            Complete risk score
        """
        score_id = self._generate_score_id(merge_request_id)
        risk_factors = []
        
        # Analyze test results
        test_factors = self._analyze_tests(test_summary)
        risk_factors.extend(test_factors)
        
        # Analyze CCI
        cci_factors = self._analyze_cci(cci_before, cci_after)
        risk_factors.extend(cci_factors)
        
        # Analyze coverage
        if coverage_info:
            coverage_factors = self._analyze_coverage(coverage_info)
            risk_factors.extend(coverage_factors)
        
        # Add additional factors
        if additional_factors:
            risk_factors.extend(additional_factors)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(risk_factors)
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Determine merge eligibility
        can_merge = self._can_merge(risk_level, test_summary, risk_factors)
        requires_approval = risk_level in {RiskLevel.HIGH, RiskLevel.MEDIUM}
        
        result = MergeRiskScore(
            score_id=score_id,
            merge_request_id=merge_request_id,
            overall_score=overall_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            test_summary=test_summary,
            coverage_info=coverage_info,
            cci_before=cci_before,
            cci_after=cci_after,
            can_merge=can_merge,
            requires_approval=requires_approval,
        )
        
        self._scoring_history.append(result)
        return result
    
    def quick_score(
        self,
        passed: int,
        failed: int,
        cci_delta: float
    ) -> tuple[float, RiskLevel]:
        """
        Quick scoring for simple cases.
        
        Returns:
            (score, risk_level)
        """
        # Test failure weight
        total = passed + failed
        fail_rate = (failed / total) if total > 0 else 0
        test_score = fail_rate * 0.6
        
        # CCI weight
        cci_score = max(0, -cci_delta) * 0.4
        
        overall = test_score + cci_score
        risk_level = self._determine_risk_level(overall)
        
        return overall, risk_level
    
    def get_scoring_history(self, count: int = 20) -> list[MergeRiskScore]:
        """Get recent scoring history."""
        return self._scoring_history[-count:]
    
    def get_score(self, score_id: str) -> MergeRiskScore | None:
        """Get a specific score by ID."""
        for score in self._scoring_history:
            if score.score_id == score_id:
                return score
        return None
    
    def explain_score(self, score: MergeRiskScore) -> str:
        """Generate human-readable explanation of score."""
        lines = [
            f"## Merge Risk Assessment: {score.merge_request_id}",
            f"",
            f"**Risk Level:** {score.risk_level.value}",
            f"**Overall Score:** {score.overall_score:.2f}",
            f"**Can Merge:** {'Yes' if score.can_merge else 'No'}",
            f"",
            "### Test Results",
            f"- Passed: {score.test_summary.passed}",
            f"- Failed: {score.test_summary.failed}",
            f"- Pass Rate: {score.test_summary.pass_rate:.1f}%",
            f"",
            "### CCI Impact",
            f"- Before: {score.cci_before:.4f}",
            f"- After: {score.cci_after:.4f}",
            f"- Delta: {score.cci_delta:+.4f}",
            f"",
        ]
        
        if score.risk_factors:
            lines.append("### Risk Factors")
            for factor in score.risk_factors:
                lines.append(f"- **{factor.category.value}** ({factor.weight:.2f}): {factor.description}")
                if factor.mitigation:
                    lines.append(f"  - Mitigation: {factor.mitigation}")
            lines.append("")
        
        if score.blocking_factors:
            lines.append("### ⚠️ Blocking Factors")
            for factor in score.blocking_factors:
                lines.append(f"- {factor.description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _analyze_tests(self, summary: TestSummary) -> list[RiskFactor]:
        """Analyze test results for risk factors."""
        factors = []
        
        # Test failures
        if summary.failed > 0:
            weight = min(1.0, summary.failed / max(summary.total_tests, 1))
            factors.append(RiskFactor(
                category=RiskCategory.TEST_FAILURE,
                description=f"{summary.failed} test(s) failed out of {summary.total_tests}",
                weight=weight,
                details={"failed": summary.failed, "total": summary.total_tests},
                mitigation="Fix failing tests before merging",
            ))
        
        # Low pass rate
        if summary.pass_rate < 90 and summary.total_tests > 0:
            weight = (100 - summary.pass_rate) / 100 * 0.5
            factors.append(RiskFactor(
                category=RiskCategory.TEST_FAILURE,
                description=f"Pass rate is {summary.pass_rate:.1f}%, below 90% threshold",
                weight=weight,
                details={"pass_rate": summary.pass_rate},
                mitigation="Improve test pass rate",
            ))
        
        # Removed tests
        if summary.removed_tests > summary.new_tests:
            weight = 0.3
            factors.append(RiskFactor(
                category=RiskCategory.COVERAGE_DROP,
                description=f"Net reduction in tests: {summary.removed_tests - summary.new_tests}",
                weight=weight,
                details={"new": summary.new_tests, "removed": summary.removed_tests},
                mitigation="Ensure removed tests are no longer needed",
            ))
        
        return factors
    
    def _analyze_cci(self, before: float, after: float) -> list[RiskFactor]:
        """Analyze CCI impact for risk factors."""
        factors = []
        delta = after - before
        
        if delta < 0:
            # CCI regression
            severity = min(1.0, abs(delta) * 2)
            factors.append(RiskFactor(
                category=RiskCategory.CCI_REGRESSION,
                description=f"CCI decreased by {abs(delta):.4f} ({delta / before * 100:.1f}%)",
                weight=severity * 0.7,
                details={"before": before, "after": after, "delta": delta},
                mitigation="Review changes causing CCI regression",
            ))
        
        return factors
    
    def _analyze_coverage(self, coverage: CoverageInfo) -> list[RiskFactor]:
        """Analyze coverage for risk factors."""
        factors = []
        
        if coverage.is_regression:
            weight = min(0.6, abs(coverage.line_coverage_delta) / 10)
            factors.append(RiskFactor(
                category=RiskCategory.COVERAGE_DROP,
                description=f"Coverage dropped by {abs(coverage.line_coverage_delta):.1f}%",
                weight=weight,
                details={
                    "line_delta": coverage.line_coverage_delta,
                    "branch_delta": coverage.branch_coverage_delta,
                },
                mitigation="Add tests for uncovered code",
            ))
        
        if coverage.line_coverage < 80:
            weight = (80 - coverage.line_coverage) / 100 * 0.4
            factors.append(RiskFactor(
                category=RiskCategory.COVERAGE_DROP,
                description=f"Line coverage is {coverage.line_coverage:.1f}%, below 80% threshold",
                weight=weight,
                details={"line_coverage": coverage.line_coverage},
                mitigation="Increase test coverage",
            ))
        
        return factors
    
    def _calculate_overall_score(self, factors: list[RiskFactor]) -> float:
        """Calculate overall risk score from factors."""
        if not factors:
            return 0.0
        
        # Weighted sum with category weights
        weighted_sum = 0.0
        weight_total = 0.0
        
        for factor in factors:
            category_weight = self.CATEGORY_WEIGHTS.get(factor.category, 0.5)
            weighted_sum += factor.weight * category_weight
            weight_total += category_weight
        
        if weight_total == 0:
            return 0.0
        
        # Normalize to 0-1 range
        score = weighted_sum / weight_total
        return min(1.0, score)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score."""
        if score >= self.CRITICAL_THRESHOLD:
            return RiskLevel.CRITICAL
        elif score >= self.HIGH_THRESHOLD:
            return RiskLevel.HIGH
        elif score >= self.MEDIUM_THRESHOLD:
            return RiskLevel.MEDIUM
        elif score > 0.1:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    def _can_merge(
        self,
        risk_level: RiskLevel,
        test_summary: TestSummary,
        factors: list[RiskFactor]
    ) -> bool:
        """Determine if merge is allowed."""
        # Block on critical risk
        if risk_level == RiskLevel.CRITICAL:
            return False
        
        # Block on test failures
        if test_summary.failed > 0:
            return False
        
        # Block on high-weight blocking factors
        for factor in factors:
            if factor.weight >= 0.9 and factor.category in {
                RiskCategory.SECURITY,
                RiskCategory.BREAKING_CHANGE,
            }:
                return False
        
        return True
    
    def _generate_score_id(self, merge_request_id: str) -> str:
        """Generate unique score ID."""
        data = f"{merge_request_id}:{datetime.utcnow().isoformat()}"
        return f"score_{hashlib.sha256(data.encode()).hexdigest()[:12]}"


# Convenience functions

def quick_merge_check(passed: int, failed: int, cci_delta: float = 0.0) -> bool:
    """
    Quick check if merge is likely safe.
    
    Returns True if merge appears safe.
    """
    scorer = PreMergeScorer()
    score, level = scorer.quick_score(passed, failed, cci_delta)
    return level in {RiskLevel.MINIMAL, RiskLevel.LOW} and failed == 0


def create_blocking_factor(description: str, category: RiskCategory = RiskCategory.BREAKING_CHANGE) -> RiskFactor:
    """Create a blocking risk factor."""
    return RiskFactor(
        category=category,
        description=description,
        weight=1.0,
        mitigation="Address this blocking issue before merging",
    )
