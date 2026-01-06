"""
CCI Scorer — Chaos Coverage Index Scoring for ChainVerify

PAC Reference: PAC-JEFFREY-P49
Agent: DAN (GID-07)

Computes CCI-based verification scores for external APIs.
Integrates P48's test intelligence with P49's verification service.

SCORING MODEL:
- Base score from test pass rate
- CCI multiplier for chaos dimension coverage
- Penalty for safety violations
- Bonus for edge case handling
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import math


class ScoreGrade(Enum):
    """Verification score grades."""
    A_PLUS = "A+"   # 95-100
    A = "A"         # 90-94
    B_PLUS = "B+"   # 85-89
    B = "B"         # 80-84
    C_PLUS = "C+"   # 75-79
    C = "C"         # 70-74
    D = "D"         # 60-69
    F = "F"         # <60


class ChaosDimension(Enum):
    """Chaos dimensions for CCI calculation."""
    AUTH = "AUTH"
    TIMING = "TIMING"
    STATE = "STATE"
    RESOURCE = "RESOURCE"
    NETWORK = "NETWORK"
    DATA = "DATA"


@dataclass
class DimensionCoverage:
    """Coverage metrics for a single chaos dimension."""
    dimension: ChaosDimension
    tests_executed: int
    tests_passed: int
    coverage_percentage: float
    edge_cases_found: int = 0
    
    @property
    def pass_rate(self) -> float:
        if self.tests_executed == 0:
            return 0.0
        return (self.tests_passed / self.tests_executed) * 100
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "tests_executed": self.tests_executed,
            "tests_passed": self.tests_passed,
            "pass_rate": self.pass_rate,
            "coverage_percentage": self.coverage_percentage,
            "edge_cases_found": self.edge_cases_found,
        }


@dataclass
class VerificationScore:
    """
    Complete verification score for an API.
    
    Components:
    - base_score: Raw test pass rate (0-100)
    - cci_score: Chaos Coverage Index (0-100)
    - safety_score: Safety compliance (0-100)
    - final_score: Weighted composite (0-100)
    """
    api_id: str
    api_title: str
    base_score: float
    cci_score: float
    safety_score: float
    final_score: float
    grade: ScoreGrade
    dimension_coverage: list[DimensionCoverage]
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int
    edge_cases_handled: int
    computed_at: datetime = field(default_factory=datetime.utcnow)
    
    # Breakdown
    endpoints_tested: int = 0
    unique_fuzz_patterns: int = 0
    chaos_scenarios_executed: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "api_id": self.api_id,
            "api_title": self.api_title,
            "scores": {
                "base": round(self.base_score, 2),
                "cci": round(self.cci_score, 2),
                "safety": round(self.safety_score, 2),
                "final": round(self.final_score, 2),
            },
            "grade": self.grade.value,
            "dimension_coverage": [d.to_dict() for d in self.dimension_coverage],
            "test_summary": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "blocked": self.blocked_tests,
            },
            "edge_cases_handled": self.edge_cases_handled,
            "endpoints_tested": self.endpoints_tested,
            "unique_fuzz_patterns": self.unique_fuzz_patterns,
            "chaos_scenarios_executed": self.chaos_scenarios_executed,
            "computed_at": self.computed_at.isoformat(),
        }


class CCIScorer:
    """
    Computes Chaos Coverage Index scores for API verification.
    
    SCORING WEIGHTS:
    - Base test pass rate: 40%
    - CCI (chaos coverage): 35%
    - Safety compliance: 25%
    
    BONUSES/PENALTIES:
    - Edge case handling: +5 max
    - Safety violations: -10 per violation (capped at -50)
    """
    
    # Scoring weights
    WEIGHT_BASE = 0.40
    WEIGHT_CCI = 0.35
    WEIGHT_SAFETY = 0.25
    
    # Bonus/penalty caps
    MAX_EDGE_CASE_BONUS = 5.0
    MAX_VIOLATION_PENALTY = 50.0
    PENALTY_PER_VIOLATION = 10.0
    
    def __init__(self):
        self._cached_scores: dict[str, VerificationScore] = {}
    
    def compute_score(
        self,
        api_id: str,
        api_title: str,
        execution_batch: Any,  # ExecutionBatch
        fuzz_suite: Any,       # FuzzSuite
    ) -> VerificationScore:
        """
        Compute verification score for an API.
        
        Args:
            api_id: Unique identifier for this API
            api_title: Human-readable API title
            execution_batch: Results from test execution
            fuzz_suite: The fuzz suite that was executed
            
        Returns:
            VerificationScore with all metrics
        """
        # Compute base score (pass rate)
        base_score = self._compute_base_score(execution_batch)
        
        # Compute CCI score (chaos dimension coverage)
        cci_score, dimension_coverage = self._compute_cci_score(
            execution_batch,
            fuzz_suite
        )
        
        # Compute safety score
        safety_score = self._compute_safety_score(execution_batch)
        
        # Compute weighted final score
        raw_final = (
            base_score * self.WEIGHT_BASE +
            cci_score * self.WEIGHT_CCI +
            safety_score * self.WEIGHT_SAFETY
        )
        
        # Apply bonuses/penalties
        edge_cases = self._count_edge_cases_handled(execution_batch)
        edge_bonus = min(edge_cases * 0.5, self.MAX_EDGE_CASE_BONUS)
        
        violation_penalty = min(
            execution_batch.total_violations * self.PENALTY_PER_VIOLATION,
            self.MAX_VIOLATION_PENALTY
        )
        
        final_score = max(0, min(100, raw_final + edge_bonus - violation_penalty))
        
        # Determine grade
        grade = self._score_to_grade(final_score)
        
        score = VerificationScore(
            api_id=api_id,
            api_title=api_title,
            base_score=base_score,
            cci_score=cci_score,
            safety_score=safety_score,
            final_score=final_score,
            grade=grade,
            dimension_coverage=dimension_coverage,
            total_tests=execution_batch.total_tests,
            passed_tests=execution_batch.passed_tests,
            failed_tests=execution_batch.failed_tests,
            blocked_tests=execution_batch.blocked_tests,
            edge_cases_handled=edge_cases,
            endpoints_tested=len(set(r.endpoint for r in execution_batch.results)),
            unique_fuzz_patterns=fuzz_suite.total_fuzz_inputs,
            chaos_scenarios_executed=len([
                r for r in execution_batch.results
                if hasattr(r, 'chaos_dimensions') and r.chaos_dimensions
            ]),
        )
        
        self._cached_scores[api_id] = score
        return score
    
    def get_cached_score(self, api_id: str) -> VerificationScore | None:
        """Get a previously computed score."""
        return self._cached_scores.get(api_id)
    
    def _compute_base_score(self, batch: Any) -> float:
        """Compute base score from pass rate."""
        if batch.total_tests == 0:
            return 0.0
        return (batch.passed_tests / batch.total_tests) * 100
    
    def _compute_cci_score(
        self,
        batch: Any,
        suite: Any,
    ) -> tuple[float, list[DimensionCoverage]]:
        """
        Compute CCI score from chaos dimension coverage.
        
        CCI = (covered_dimensions / total_dimensions) * dimension_pass_rate
        """
        dimensions_covered: dict[ChaosDimension, dict[str, int]] = {}
        
        # Initialize all dimensions
        for dim in ChaosDimension:
            dimensions_covered[dim] = {
                "executed": 0,
                "passed": 0,
            }
        
        # Count coverage per dimension
        for test_case in suite.test_cases:
            if hasattr(test_case, 'chaos_dimensions'):
                for dim in test_case.chaos_dimensions:
                    if isinstance(dim, str):
                        dim = ChaosDimension(dim)
                    dimensions_covered[dim]["executed"] += 1
        
        # Map results to dimensions
        for result in batch.results:
            # Find matching test case
            for test_case in suite.test_cases:
                if test_case.test_id == result.test_id:
                    if hasattr(test_case, 'chaos_dimensions'):
                        for dim in test_case.chaos_dimensions:
                            if isinstance(dim, str):
                                dim = ChaosDimension(dim)
                            if result.passed:
                                dimensions_covered[dim]["passed"] += 1
                    break
        
        # Build dimension coverage list
        coverage_list = []
        total_coverage = 0.0
        covered_count = 0
        
        for dim in ChaosDimension:
            data = dimensions_covered[dim]
            executed = data["executed"]
            passed = data["passed"]
            
            if executed > 0:
                coverage_pct = (passed / executed) * 100
                covered_count += 1
            else:
                coverage_pct = 0.0
            
            coverage_list.append(DimensionCoverage(
                dimension=dim,
                tests_executed=executed,
                tests_passed=passed,
                coverage_percentage=coverage_pct,
            ))
            
            total_coverage += coverage_pct
        
        # CCI score is average of covered dimensions
        total_dimensions = len(ChaosDimension)
        if covered_count > 0:
            dimension_breadth = (covered_count / total_dimensions) * 100
            dimension_depth = total_coverage / total_dimensions
            cci_score = (dimension_breadth + dimension_depth) / 2
        else:
            cci_score = 0.0
        
        return cci_score, coverage_list
    
    def _compute_safety_score(self, batch: Any) -> float:
        """Compute safety compliance score."""
        if batch.total_tests == 0:
            return 100.0
        
        # Safety score = tests without violations / total tests
        tests_with_violations = batch.blocked_tests
        safe_tests = batch.total_tests - tests_with_violations
        
        return (safe_tests / batch.total_tests) * 100
    
    def _count_edge_cases_handled(self, batch: Any) -> int:
        """Count edge cases that were handled gracefully."""
        # An edge case is "handled" if it passed or failed gracefully
        # (not crashed, not caused security violation)
        edge_cases = 0
        
        for result in batch.results:
            # Check for edge case indicators
            if result.status_code in {400, 422}:  # Proper validation errors
                edge_cases += 1
            elif result.status_code == 200 and result.passed:
                # Successfully handled potentially malicious input
                edge_cases += 1
        
        return edge_cases
    
    def _score_to_grade(self, score: float) -> ScoreGrade:
        """Convert numeric score to letter grade."""
        if score >= 95:
            return ScoreGrade.A_PLUS
        elif score >= 90:
            return ScoreGrade.A
        elif score >= 85:
            return ScoreGrade.B_PLUS
        elif score >= 80:
            return ScoreGrade.B
        elif score >= 75:
            return ScoreGrade.C_PLUS
        elif score >= 70:
            return ScoreGrade.C
        elif score >= 60:
            return ScoreGrade.D
        else:
            return ScoreGrade.F


# Module-level singleton
_cci_scorer: CCIScorer | None = None


def get_cci_scorer() -> CCIScorer:
    """Get the singleton scorer."""
    global _cci_scorer
    if _cci_scorer is None:
        _cci_scorer = CCIScorer()
    return _cci_scorer


def reset_cci_scorer() -> None:
    """Reset the singleton (for testing)."""
    global _cci_scorer
    _cci_scorer = None


def compute_verification_score(
    api_id: str,
    api_title: str,
    execution_batch: Any,
    fuzz_suite: Any,
) -> VerificationScore:
    """Convenience function to compute verification score."""
    return get_cci_scorer().compute_score(api_id, api_title, execution_batch, fuzz_suite)
