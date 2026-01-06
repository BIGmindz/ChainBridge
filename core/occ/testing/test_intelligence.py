"""
Test Intelligence Scoring Module

PAC Reference: PAC-JEFFREY-P48
Objective: Convert PyTest from validation tooling into structural competitive moat

Ranks tests by:
- Failure probability (historical + structural)
- Blast radius (affected code surface)
- Chaos dimension coverage
- Runtime cost

This module is ADVISORY ONLY - no autonomous decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import json
import hashlib


class RiskTier(Enum):
    """Test risk classification tiers."""
    
    CRITICAL = "CRITICAL"    # High failure prob + high blast radius
    HIGH = "HIGH"            # Either high failure or high blast
    MEDIUM = "MEDIUM"        # Moderate risk indicators
    LOW = "LOW"              # Stable, low-impact tests
    BASELINE = "BASELINE"    # New tests without history


class BlastRadiusCategory(Enum):
    """Categories of code impact."""
    
    SYSTEM = "SYSTEM"        # Affects entire system
    SERVICE = "SERVICE"      # Affects a service boundary
    MODULE = "MODULE"        # Affects a module
    FUNCTION = "FUNCTION"    # Affects single function
    ISOLATED = "ISOLATED"    # No external dependencies


@dataclass
class TestExecutionRecord:
    """Historical execution record for a test."""
    
    test_id: str
    timestamp: datetime
    passed: bool
    duration_ms: float
    error_type: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type
        }


@dataclass
class TestIntelligenceScore:
    """Comprehensive intelligence score for a test."""
    
    test_id: str
    test_path: str
    
    # Probability metrics
    failure_probability: float  # 0.0 - 1.0
    historical_failure_rate: float  # 0.0 - 1.0
    structural_risk_score: float  # 0.0 - 1.0
    
    # Blast radius
    blast_radius: BlastRadiusCategory
    affected_modules: List[str]
    dependency_depth: int
    
    # Chaos coverage
    chaos_dimensions: Set[str]
    cci_contribution: float
    
    # Runtime
    avg_duration_ms: float
    variance_ms: float
    
    # Classification
    risk_tier: RiskTier
    priority_rank: int  # Lower = higher priority
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    execution_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_path": self.test_path,
            "failure_probability": self.failure_probability,
            "historical_failure_rate": self.historical_failure_rate,
            "structural_risk_score": self.structural_risk_score,
            "blast_radius": self.blast_radius.value,
            "affected_modules": self.affected_modules,
            "dependency_depth": self.dependency_depth,
            "chaos_dimensions": list(self.chaos_dimensions),
            "cci_contribution": self.cci_contribution,
            "avg_duration_ms": self.avg_duration_ms,
            "variance_ms": self.variance_ms,
            "risk_tier": self.risk_tier.value,
            "priority_rank": self.priority_rank,
            "last_updated": self.last_updated.isoformat(),
            "execution_count": self.execution_count
        }


class TestIntelligenceEngine:
    """
    Engine for computing and managing test intelligence scores.
    
    ADVISORY ONLY - generates signals for human/orchestrator review.
    Does not make autonomous execution decisions.
    """
    
    # Weights for combined risk calculation
    FAILURE_WEIGHT = 0.4
    BLAST_WEIGHT = 0.3
    STRUCTURAL_WEIGHT = 0.2
    CHAOS_WEIGHT = 0.1
    
    # Blast radius multipliers
    BLAST_MULTIPLIERS = {
        BlastRadiusCategory.SYSTEM: 1.0,
        BlastRadiusCategory.SERVICE: 0.75,
        BlastRadiusCategory.MODULE: 0.5,
        BlastRadiusCategory.FUNCTION: 0.25,
        BlastRadiusCategory.ISOLATED: 0.1
    }
    
    def __init__(self):
        self._scores: Dict[str, TestIntelligenceScore] = {}
        self._history: Dict[str, List[TestExecutionRecord]] = {}
        self._structural_map: Dict[str, Set[str]] = {}  # test -> affected modules
    
    def register_test(
        self,
        test_id: str,
        test_path: str,
        affected_modules: List[str],
        chaos_dimensions: Optional[Set[str]] = None,
        blast_radius: BlastRadiusCategory = BlastRadiusCategory.FUNCTION
    ) -> TestIntelligenceScore:
        """Register a test for intelligence tracking."""
        
        score = TestIntelligenceScore(
            test_id=test_id,
            test_path=test_path,
            failure_probability=0.5,  # Default neutral
            historical_failure_rate=0.0,
            structural_risk_score=self._compute_structural_risk(affected_modules),
            blast_radius=blast_radius,
            affected_modules=affected_modules,
            dependency_depth=len(affected_modules),
            chaos_dimensions=chaos_dimensions or set(),
            cci_contribution=len(chaos_dimensions or set()) / 6.0,  # 6 canonical dimensions
            avg_duration_ms=0.0,
            variance_ms=0.0,
            risk_tier=RiskTier.BASELINE,
            priority_rank=0
        )
        
        self._scores[test_id] = score
        self._structural_map[test_id] = set(affected_modules)
        self._history[test_id] = []
        
        return score
    
    def record_execution(
        self,
        test_id: str,
        passed: bool,
        duration_ms: float,
        error_type: Optional[str] = None
    ) -> None:
        """Record a test execution result."""
        
        if test_id not in self._history:
            self._history[test_id] = []
        
        record = TestExecutionRecord(
            test_id=test_id,
            timestamp=datetime.utcnow(),
            passed=passed,
            duration_ms=duration_ms,
            error_type=error_type
        )
        
        self._history[test_id].append(record)
        
        # Update score if test is registered
        if test_id in self._scores:
            self._update_score(test_id)
    
    def _compute_structural_risk(self, affected_modules: List[str]) -> float:
        """Compute structural risk based on module dependencies."""
        if not affected_modules:
            return 0.1
        
        # More affected modules = higher structural risk
        depth = len(affected_modules)
        
        # Check for critical modules
        critical_modules = {"core", "api", "auth", "governance", "occ"}
        critical_count = sum(1 for m in affected_modules if any(c in m.lower() for c in critical_modules))
        
        base_risk = min(depth / 10.0, 0.5)  # Cap at 0.5 from depth alone
        critical_risk = critical_count * 0.1  # 0.1 per critical module
        
        return min(base_risk + critical_risk, 1.0)
    
    def _update_score(self, test_id: str) -> None:
        """Update intelligence score based on history."""
        
        if test_id not in self._scores or test_id not in self._history:
            return
        
        score = self._scores[test_id]
        history = self._history[test_id]
        
        if not history:
            return
        
        # Update execution count
        score.execution_count = len(history)
        
        # Calculate historical failure rate
        failures = sum(1 for r in history if not r.passed)
        score.historical_failure_rate = failures / len(history)
        
        # Calculate average duration
        durations = [r.duration_ms for r in history]
        score.avg_duration_ms = sum(durations) / len(durations)
        
        # Calculate variance
        if len(durations) > 1:
            mean = score.avg_duration_ms
            score.variance_ms = sum((d - mean) ** 2 for d in durations) / len(durations)
        
        # Update failure probability (weighted recent + historical)
        recent_history = history[-10:]  # Last 10 executions
        recent_failures = sum(1 for r in recent_history if not r.passed)
        recent_rate = recent_failures / len(recent_history) if recent_history else 0.0
        
        # Weight recent history more heavily
        score.failure_probability = (0.7 * recent_rate) + (0.3 * score.historical_failure_rate)
        
        # Update risk tier
        score.risk_tier = self._classify_risk_tier(score)
        
        # Update timestamp
        score.last_updated = datetime.utcnow()
    
    def _classify_risk_tier(self, score: TestIntelligenceScore) -> RiskTier:
        """Classify test into risk tier."""
        
        combined_risk = (
            self.FAILURE_WEIGHT * score.failure_probability +
            self.BLAST_WEIGHT * self.BLAST_MULTIPLIERS[score.blast_radius] +
            self.STRUCTURAL_WEIGHT * score.structural_risk_score +
            self.CHAOS_WEIGHT * (1.0 - score.cci_contribution)  # Inverse: less chaos coverage = more risk
        )
        
        if combined_risk >= 0.7:
            return RiskTier.CRITICAL
        elif combined_risk >= 0.5:
            return RiskTier.HIGH
        elif combined_risk >= 0.3:
            return RiskTier.MEDIUM
        elif score.execution_count == 0:
            return RiskTier.BASELINE
        else:
            return RiskTier.LOW
    
    def compute_priority_rankings(self) -> List[TestIntelligenceScore]:
        """
        Compute priority rankings for all tests.
        
        Returns tests sorted by priority (highest priority first).
        """
        # Update all scores
        for test_id in self._scores:
            self._update_score(test_id)
        
        # Compute combined priority score for each test
        scored_tests = []
        for test_id, score in self._scores.items():
            priority_value = (
                self.FAILURE_WEIGHT * score.failure_probability +
                self.BLAST_WEIGHT * self.BLAST_MULTIPLIERS[score.blast_radius] +
                self.STRUCTURAL_WEIGHT * score.structural_risk_score
            )
            scored_tests.append((priority_value, score))
        
        # Sort by priority (descending)
        scored_tests.sort(key=lambda x: x[0], reverse=True)
        
        # Assign ranks
        for rank, (_, score) in enumerate(scored_tests, 1):
            score.priority_rank = rank
        
        return [score for _, score in scored_tests]
    
    def get_critical_tests(self) -> List[TestIntelligenceScore]:
        """Get all tests classified as CRITICAL."""
        return [s for s in self._scores.values() if s.risk_tier == RiskTier.CRITICAL]
    
    def get_high_risk_tests(self) -> List[TestIntelligenceScore]:
        """Get tests classified as CRITICAL or HIGH."""
        return [s for s in self._scores.values() if s.risk_tier in {RiskTier.CRITICAL, RiskTier.HIGH}]
    
    def get_tests_by_chaos_dimension(self, dimension: str) -> List[TestIntelligenceScore]:
        """Get tests covering a specific chaos dimension."""
        return [s for s in self._scores.values() if dimension in s.chaos_dimensions]
    
    def get_optimized_test_order(self, time_budget_ms: Optional[float] = None) -> List[str]:
        """
        Get optimized test execution order.
        
        Prioritizes:
        1. Critical/high risk tests first
        2. Fast tests within each tier
        3. Diverse chaos coverage
        
        If time_budget_ms is provided, returns tests that fit within budget.
        """
        rankings = self.compute_priority_rankings()
        
        if time_budget_ms is None:
            return [s.test_id for s in rankings]
        
        # Select tests within budget, prioritizing high-risk
        selected = []
        remaining_budget = time_budget_ms
        
        for score in rankings:
            if score.avg_duration_ms <= remaining_budget:
                selected.append(score.test_id)
                remaining_budget -= score.avg_duration_ms
        
        return selected
    
    def get_cci_impact_report(self) -> dict:
        """Generate report on CCI coverage by test."""
        
        dimension_coverage: Dict[str, int] = {}
        for score in self._scores.values():
            for dim in score.chaos_dimensions:
                dimension_coverage[dim] = dimension_coverage.get(dim, 0) + 1
        
        return {
            "total_tests": len(self._scores),
            "tests_with_chaos_coverage": sum(1 for s in self._scores.values() if s.chaos_dimensions),
            "dimension_coverage": dimension_coverage,
            "avg_cci_contribution": (
                sum(s.cci_contribution for s in self._scores.values()) / len(self._scores)
                if self._scores else 0.0
            )
        }
    
    def generate_risk_brief(self) -> dict:
        """
        Generate Pre-BER Risk Brief for BENSON.
        
        ADVISORY ONLY - no autonomous decisions.
        """
        rankings = self.compute_priority_rankings()
        
        critical = self.get_critical_tests()
        high_risk = self.get_high_risk_tests()
        
        # Find tests with recent failures
        recent_failures = []
        for test_id, history in self._history.items():
            recent = history[-5:] if history else []
            if any(not r.passed for r in recent):
                recent_failures.append(test_id)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "advisory_only": True,
            "total_tests_tracked": len(self._scores),
            "critical_tests": len(critical),
            "high_risk_tests": len(high_risk),
            "recent_failures": recent_failures,
            "top_10_priority": [s.test_id for s in rankings[:10]],
            "cci_report": self.get_cci_impact_report(),
            "recommendations": self._generate_recommendations(rankings, recent_failures)
        }
    
    def _generate_recommendations(
        self,
        rankings: List[TestIntelligenceScore],
        recent_failures: List[str]
    ) -> List[str]:
        """Generate advisory recommendations."""
        recommendations = []
        
        critical_count = len([s for s in rankings if s.risk_tier == RiskTier.CRITICAL])
        if critical_count > 0:
            recommendations.append(f"ADVISORY: {critical_count} critical-tier tests require attention")
        
        if recent_failures:
            recommendations.append(f"ADVISORY: {len(recent_failures)} tests have recent failures")
        
        # Check for uncovered chaos dimensions
        covered_dimensions = set()
        for score in self._scores.values():
            covered_dimensions.update(score.chaos_dimensions)
        
        all_dimensions = {"AUTH", "STATE", "CONC", "TIME", "DATA", "GOV"}
        uncovered = all_dimensions - covered_dimensions
        if uncovered:
            recommendations.append(f"ADVISORY: Chaos dimensions uncovered: {', '.join(uncovered)}")
        
        return recommendations
    
    def to_json(self) -> str:
        """Serialize engine state to JSON."""
        return json.dumps({
            "scores": {k: v.to_dict() for k, v in self._scores.items()},
            "history_count": {k: len(v) for k, v in self._history.items()}
        }, indent=2)


# Global instance
_engine_instance: Optional[TestIntelligenceEngine] = None


def get_test_intelligence_engine() -> TestIntelligenceEngine:
    """Get or create the global test intelligence engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TestIntelligenceEngine()
    return _engine_instance


def reset_test_intelligence_engine() -> None:
    """Reset the global engine (for testing)."""
    global _engine_instance
    _engine_instance = None


def generate_pre_ber_risk_brief() -> dict:
    """Generate Pre-BER Risk Brief for BENSON review."""
    engine = get_test_intelligence_engine()
    return engine.generate_risk_brief()
