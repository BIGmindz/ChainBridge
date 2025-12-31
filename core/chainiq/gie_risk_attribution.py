"""
GIE Risk Attribution and Explainability

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-10 (Maggie) — ML/AI Lead

Features:
- Risk attribution per agent decision
- Glass-box explanations
- PDO-aligned scoring outputs
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    """Risk level classification."""
    MINIMAL = "MINIMAL"     # 0.0 - 0.2
    LOW = "LOW"             # 0.2 - 0.4
    MODERATE = "MODERATE"   # 0.4 - 0.6
    HIGH = "HIGH"           # 0.6 - 0.8
    CRITICAL = "CRITICAL"   # 0.8 - 1.0


class RiskCategory(Enum):
    """Categories of risk factors."""
    EXECUTION = "EXECUTION"         # Task execution risk
    DEPENDENCY = "DEPENDENCY"       # Dependency chain risk
    RESOURCE = "RESOURCE"           # Resource contention
    TIMING = "TIMING"               # Timing/deadline risk
    INTEGRITY = "INTEGRITY"         # Data integrity risk
    GOVERNANCE = "GOVERNANCE"       # Governance violation risk
    EXTERNAL = "EXTERNAL"           # External system risk


class ExplanationType(Enum):
    """Types of explanations."""
    FACTOR_CONTRIBUTION = "FACTOR_CONTRIBUTION"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    FEATURE_IMPORTANCE = "FEATURE_IMPORTANCE"
    DECISION_PATH = "DECISION_PATH"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RiskFactor:
    """
    A single risk factor with attribution.
    """
    factor_id: str
    category: RiskCategory
    name: str
    description: str
    weight: float  # 0.0 to 1.0
    raw_score: float  # 0.0 to 1.0
    weighted_score: float = field(init=False)
    
    def __post_init__(self):
        self.weighted_score = self.weight * self.raw_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "raw_score": self.raw_score,
            "weighted_score": self.weighted_score,
        }


@dataclass
class RiskExplanation:
    """
    Glass-box explanation for a risk assessment.
    """
    explanation_id: str
    explanation_type: ExplanationType
    summary: str
    details: Dict[str, Any]
    contributing_factors: List[str]  # Factor IDs
    confidence: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "type": self.explanation_type.value,
            "summary": self.summary,
            "details": self.details,
            "contributing_factors": self.contributing_factors,
            "confidence": self.confidence,
        }


@dataclass
class AgentRiskProfile:
    """
    Risk profile for a single agent.
    """
    agent_gid: str
    task_type: str
    factors: List[RiskFactor]
    overall_score: float = field(init=False)
    risk_level: RiskLevel = field(init=False)
    explanation: Optional[RiskExplanation] = None
    assessed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def __post_init__(self):
        self._compute_overall_score()
    
    def _compute_overall_score(self) -> None:
        """Compute weighted overall risk score."""
        if not self.factors:
            self.overall_score = 0.0
        else:
            total_weight = sum(f.weight for f in self.factors)
            if total_weight > 0:
                self.overall_score = sum(f.weighted_score for f in self.factors) / total_weight
            else:
                self.overall_score = 0.0
        
        self.risk_level = self._score_to_level(self.overall_score)
    
    @staticmethod
    def _score_to_level(score: float) -> RiskLevel:
        """Convert score to risk level."""
        if score < 0.2:
            return RiskLevel.MINIMAL
        elif score < 0.4:
            return RiskLevel.LOW
        elif score < 0.6:
            return RiskLevel.MODERATE
        elif score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_gid": self.agent_gid,
            "task_type": self.task_type,
            "factors": [f.to_dict() for f in self.factors],
            "overall_score": self.overall_score,
            "risk_level": self.risk_level.value,
            "explanation": self.explanation.to_dict() if self.explanation else None,
            "assessed_at": self.assessed_at,
        }


@dataclass
class PDORiskAttribution:
    """
    Risk attribution aligned with PDO structure.
    
    Maps to: Proof → Decision → Outcome
    """
    pdo_id: str
    agent_profiles: List[AgentRiskProfile]
    aggregate_score: float = field(init=False)
    aggregate_level: RiskLevel = field(init=False)
    category_breakdown: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    hash_ref: str = field(default="")
    
    def __post_init__(self):
        self._compute_aggregate()
        self._compute_hash()
    
    def _compute_aggregate(self) -> None:
        """Compute aggregate risk across all agents."""
        if not self.agent_profiles:
            self.aggregate_score = 0.0
        else:
            # Use max risk as aggregate (conservative)
            self.aggregate_score = max(p.overall_score for p in self.agent_profiles)
        
        self.aggregate_level = AgentRiskProfile._score_to_level(self.aggregate_score)
        
        # Compute category breakdown
        self._compute_category_breakdown()
    
    def _compute_category_breakdown(self) -> None:
        """Compute risk by category across all agents."""
        category_scores: Dict[str, List[float]] = {}
        
        for profile in self.agent_profiles:
            for factor in profile.factors:
                cat = factor.category.value
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(factor.weighted_score)
        
        self.category_breakdown = {
            cat: sum(scores) / len(scores) if scores else 0.0
            for cat, scores in category_scores.items()
        }
    
    def _compute_hash(self) -> None:
        """Compute hash for audit trail."""
        content = json.dumps({
            "pdo_id": self.pdo_id,
            "profiles": [p.to_dict() for p in self.agent_profiles],
            "aggregate_score": self.aggregate_score,
        }, sort_keys=True)
        self.hash_ref = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "agent_profiles": [p.to_dict() for p in self.agent_profiles],
            "aggregate_score": self.aggregate_score,
            "aggregate_level": self.aggregate_level.value,
            "category_breakdown": self.category_breakdown,
            "recommendations": self.recommendations,
            "hash_ref": self.hash_ref,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# RISK ATTRIBUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GIERiskAttributionEngine:
    """
    Risk attribution and explainability engine for GIE.
    
    Provides glass-box explanations for all risk assessments.
    """

    def __init__(self):
        """Initialize the attribution engine."""
        self._factor_counter = 0
        self._explanation_counter = 0
        
        # Default risk weights by category
        self._category_weights: Dict[RiskCategory, float] = {
            RiskCategory.EXECUTION: 0.20,
            RiskCategory.DEPENDENCY: 0.15,
            RiskCategory.RESOURCE: 0.15,
            RiskCategory.TIMING: 0.10,
            RiskCategory.INTEGRITY: 0.20,
            RiskCategory.GOVERNANCE: 0.15,
            RiskCategory.EXTERNAL: 0.05,
        }

    def _next_factor_id(self) -> str:
        """Generate next factor ID."""
        self._factor_counter += 1
        return f"RF-{self._factor_counter:04d}"

    def _next_explanation_id(self) -> str:
        """Generate next explanation ID."""
        self._explanation_counter += 1
        return f"EXP-{self._explanation_counter:04d}"

    # ─────────────────────────────────────────────────────────────────────────
    # Risk Factor Assessment
    # ─────────────────────────────────────────────────────────────────────────

    def assess_execution_risk(
        self,
        task_complexity: float,
        estimated_duration: float,
        historical_success_rate: float,
    ) -> RiskFactor:
        """
        Assess execution risk for a task.
        
        Args:
            task_complexity: 0.0 (trivial) to 1.0 (highly complex)
            estimated_duration: Expected duration in seconds
            historical_success_rate: 0.0 to 1.0
        """
        # Compute raw score
        complexity_risk = task_complexity
        duration_risk = min(estimated_duration / 3600, 1.0)  # Cap at 1 hour
        failure_risk = 1.0 - historical_success_rate
        
        raw_score = (complexity_risk * 0.4 + duration_risk * 0.2 + failure_risk * 0.4)
        
        return RiskFactor(
            factor_id=self._next_factor_id(),
            category=RiskCategory.EXECUTION,
            name="Task Execution Risk",
            description=f"Complexity: {task_complexity:.2f}, Duration: {estimated_duration}s, Success Rate: {historical_success_rate:.2%}",
            weight=self._category_weights[RiskCategory.EXECUTION],
            raw_score=raw_score,
        )

    def assess_dependency_risk(
        self,
        dependency_count: int,
        critical_dependencies: int,
        parallel_factor: float,
    ) -> RiskFactor:
        """
        Assess dependency chain risk.
        
        Args:
            dependency_count: Total number of dependencies
            critical_dependencies: Number of blocking dependencies
            parallel_factor: 0.0 (serial) to 1.0 (fully parallel)
        """
        # More dependencies = higher risk
        count_risk = min(dependency_count / 10, 1.0)
        critical_risk = min(critical_dependencies / 5, 1.0)
        serial_risk = 1.0 - parallel_factor
        
        raw_score = (count_risk * 0.3 + critical_risk * 0.5 + serial_risk * 0.2)
        
        return RiskFactor(
            factor_id=self._next_factor_id(),
            category=RiskCategory.DEPENDENCY,
            name="Dependency Chain Risk",
            description=f"Dependencies: {dependency_count}, Critical: {critical_dependencies}, Parallel: {parallel_factor:.2f}",
            weight=self._category_weights[RiskCategory.DEPENDENCY],
            raw_score=raw_score,
        )

    def assess_integrity_risk(
        self,
        has_proof: bool,
        proof_freshness: float,
        validation_depth: int,
    ) -> RiskFactor:
        """
        Assess data integrity risk.
        
        Args:
            has_proof: Whether cryptographic proof exists
            proof_freshness: 0.0 (stale) to 1.0 (fresh)
            validation_depth: Number of validation layers
        """
        proof_risk = 0.0 if has_proof else 0.5
        freshness_risk = 1.0 - proof_freshness
        validation_risk = max(0, 1.0 - (validation_depth / 3))
        
        raw_score = (proof_risk * 0.4 + freshness_risk * 0.3 + validation_risk * 0.3)
        
        return RiskFactor(
            factor_id=self._next_factor_id(),
            category=RiskCategory.INTEGRITY,
            name="Data Integrity Risk",
            description=f"Proof: {has_proof}, Freshness: {proof_freshness:.2f}, Validations: {validation_depth}",
            weight=self._category_weights[RiskCategory.INTEGRITY],
            raw_score=raw_score,
        )

    def assess_governance_risk(
        self,
        policy_violations: int,
        audit_coverage: float,
        approval_status: bool,
    ) -> RiskFactor:
        """
        Assess governance compliance risk.
        
        Args:
            policy_violations: Number of detected violations
            audit_coverage: 0.0 to 1.0 coverage percentage
            approval_status: Whether approved by authority
        """
        violation_risk = min(policy_violations / 5, 1.0)
        coverage_risk = 1.0 - audit_coverage
        approval_risk = 0.0 if approval_status else 0.3
        
        raw_score = (violation_risk * 0.5 + coverage_risk * 0.3 + approval_risk * 0.2)
        
        return RiskFactor(
            factor_id=self._next_factor_id(),
            category=RiskCategory.GOVERNANCE,
            name="Governance Compliance Risk",
            description=f"Violations: {policy_violations}, Coverage: {audit_coverage:.2%}, Approved: {approval_status}",
            weight=self._category_weights[RiskCategory.GOVERNANCE],
            raw_score=raw_score,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Explanation Generation
    # ─────────────────────────────────────────────────────────────────────────

    def generate_factor_explanation(
        self,
        profile: AgentRiskProfile,
    ) -> RiskExplanation:
        """
        Generate factor contribution explanation.
        """
        # Sort factors by contribution
        sorted_factors = sorted(
            profile.factors,
            key=lambda f: f.weighted_score,
            reverse=True,
        )
        
        top_factors = sorted_factors[:3]
        
        summary = f"Risk level {profile.risk_level.value} driven by: " + ", ".join(
            f.name for f in top_factors
        )
        
        details = {
            "factor_contributions": {
                f.factor_id: {
                    "name": f.name,
                    "contribution": f.weighted_score / profile.overall_score if profile.overall_score > 0 else 0,
                }
                for f in profile.factors
            },
            "dominant_category": max(
                profile.factors,
                key=lambda f: f.weighted_score,
            ).category.value if profile.factors else None,
        }
        
        return RiskExplanation(
            explanation_id=self._next_explanation_id(),
            explanation_type=ExplanationType.FACTOR_CONTRIBUTION,
            summary=summary,
            details=details,
            contributing_factors=[f.factor_id for f in top_factors],
            confidence=0.85,  # Based on factor coverage
        )

    def generate_counterfactual(
        self,
        profile: AgentRiskProfile,
        target_level: RiskLevel = RiskLevel.LOW,
    ) -> RiskExplanation:
        """
        Generate counterfactual explanation.
        
        "What would need to change to reach target risk level?"
        """
        target_score = {
            RiskLevel.MINIMAL: 0.1,
            RiskLevel.LOW: 0.3,
            RiskLevel.MODERATE: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 0.9,
        }[target_level]
        
        current_score = profile.overall_score
        needed_reduction = current_score - target_score
        
        if needed_reduction <= 0:
            summary = f"Already at or below {target_level.value} risk level"
            changes = []
        else:
            # Find factors to reduce
            sorted_factors = sorted(
                profile.factors,
                key=lambda f: f.weighted_score,
                reverse=True,
            )
            
            changes = []
            reduction_so_far = 0.0
            
            for factor in sorted_factors:
                if reduction_so_far >= needed_reduction:
                    break
                
                max_reduction = factor.weighted_score * 0.5  # Can reduce by 50%
                changes.append({
                    "factor": factor.name,
                    "current_score": factor.raw_score,
                    "target_score": factor.raw_score * 0.5,
                    "reduction": max_reduction,
                })
                reduction_so_far += max_reduction
            
            summary = f"To reach {target_level.value}: reduce {len(changes)} factor(s)"
        
        return RiskExplanation(
            explanation_id=self._next_explanation_id(),
            explanation_type=ExplanationType.COUNTERFACTUAL,
            summary=summary,
            details={
                "current_score": current_score,
                "target_score": target_score,
                "needed_reduction": max(0, needed_reduction),
                "suggested_changes": changes,
            },
            contributing_factors=[c["factor"] for c in changes] if changes else [],
            confidence=0.75,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Profile Assessment
    # ─────────────────────────────────────────────────────────────────────────

    def assess_agent(
        self,
        agent_gid: str,
        task_type: str,
        metrics: Dict[str, Any],
    ) -> AgentRiskProfile:
        """
        Assess risk profile for an agent.
        
        Args:
            agent_gid: Agent identifier
            task_type: Type of task being executed
            metrics: Dict with keys:
                - task_complexity (float)
                - estimated_duration (float)
                - success_rate (float)
                - dependency_count (int)
                - critical_deps (int)
                - parallel_factor (float)
                - has_proof (bool)
                - proof_freshness (float)
                - validation_depth (int)
                - policy_violations (int)
                - audit_coverage (float)
                - approved (bool)
        """
        factors = []
        
        # Execution risk
        if "task_complexity" in metrics:
            factors.append(self.assess_execution_risk(
                task_complexity=metrics.get("task_complexity", 0.5),
                estimated_duration=metrics.get("estimated_duration", 60),
                historical_success_rate=metrics.get("success_rate", 0.9),
            ))
        
        # Dependency risk
        if "dependency_count" in metrics:
            factors.append(self.assess_dependency_risk(
                dependency_count=metrics.get("dependency_count", 0),
                critical_dependencies=metrics.get("critical_deps", 0),
                parallel_factor=metrics.get("parallel_factor", 0.5),
            ))
        
        # Integrity risk
        if "has_proof" in metrics:
            factors.append(self.assess_integrity_risk(
                has_proof=metrics.get("has_proof", True),
                proof_freshness=metrics.get("proof_freshness", 1.0),
                validation_depth=metrics.get("validation_depth", 1),
            ))
        
        # Governance risk
        if "policy_violations" in metrics:
            factors.append(self.assess_governance_risk(
                policy_violations=metrics.get("policy_violations", 0),
                audit_coverage=metrics.get("audit_coverage", 1.0),
                approval_status=metrics.get("approved", True),
            ))
        
        profile = AgentRiskProfile(
            agent_gid=agent_gid,
            task_type=task_type,
            factors=factors,
        )
        
        # Generate explanation
        profile.explanation = self.generate_factor_explanation(profile)
        
        return profile

    def assess_pdo(
        self,
        pdo_id: str,
        agent_profiles: List[AgentRiskProfile],
    ) -> PDORiskAttribution:
        """
        Create PDO-aligned risk attribution.
        """
        attribution = PDORiskAttribution(
            pdo_id=pdo_id,
            agent_profiles=agent_profiles,
        )
        
        # Generate recommendations
        attribution.recommendations = self._generate_recommendations(attribution)
        
        return attribution

    def _generate_recommendations(
        self,
        attribution: PDORiskAttribution,
    ) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []
        
        # Check aggregate level
        if attribution.aggregate_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recommendations.append(
                "Consider manual review before proceeding"
            )
        
        # Check category breakdown
        for category, score in attribution.category_breakdown.items():
            if score > 0.6:
                recommendations.append(
                    f"High {category.lower()} risk detected — implement additional controls"
                )
        
        # Check individual agents
        high_risk_agents = [
            p.agent_gid for p in attribution.agent_profiles
            if p.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ]
        if high_risk_agents:
            recommendations.append(
                f"Agents with elevated risk: {', '.join(high_risk_agents)}"
            )
        
        if not recommendations:
            recommendations.append("Risk levels within acceptable bounds")
        
        return recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_engine: Optional[GIERiskAttributionEngine] = None


def get_risk_engine() -> GIERiskAttributionEngine:
    """Get or create global risk engine."""
    global _engine
    if _engine is None:
        _engine = GIERiskAttributionEngine()
    return _engine


def reset_risk_engine() -> None:
    """Reset global engine."""
    global _engine
    _engine = None
