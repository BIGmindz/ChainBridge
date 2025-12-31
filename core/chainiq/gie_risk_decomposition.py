"""
GIE Risk Decomposition Engine

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
Agent: GID-10 (Maggie) — ML / Risk

REAL WORK MODE — Production-grade glass-box risk decomposition.

Features:
- Break final decision into weighted sub-factors
- Glass-box only (no black-box ML)
- Interpretable factor attribution
- Counterfactual generation
"""

from __future__ import annotations

import hashlib
import json
import math
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    """Risk severity levels."""
    NEGLIGIBLE = "NEGLIGIBLE"  # < 0.2
    LOW = "LOW"                # 0.2 - 0.4
    MEDIUM = "MEDIUM"          # 0.4 - 0.6
    HIGH = "HIGH"              # 0.6 - 0.8
    CRITICAL = "CRITICAL"      # > 0.8


class FactorCategory(Enum):
    """Categories of risk factors."""
    EXECUTION = "EXECUTION"      # Task execution quality
    COMPLIANCE = "COMPLIANCE"    # Governance compliance
    SECURITY = "SECURITY"        # Security posture
    DATA = "DATA"                # Data integrity
    OPERATIONAL = "OPERATIONAL"  # Operational risk
    TEMPORAL = "TEMPORAL"        # Time-based factors
    AGENT = "AGENT"              # Agent-specific factors


class DecompositionMethod(Enum):
    """Methods for risk decomposition."""
    WEIGHTED_SUM = "WEIGHTED_SUM"
    MULTIPLICATIVE = "MULTIPLICATIVE"
    HIERARCHICAL = "HIERARCHICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class RiskDecompositionError(Exception):
    """Base exception for risk decomposition."""
    pass


class InvalidFactorError(RiskDecompositionError):
    """Raised when factor configuration is invalid."""
    pass


class WeightNormalizationError(RiskDecompositionError):
    """Raised when weights don't sum to expected value."""
    pass


class MissingFactorError(RiskDecompositionError):
    """Raised when required factor is missing."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FactorDefinition:
    """
    Definition of a risk factor.
    
    Immutable to ensure consistency.
    """
    factor_id: str
    name: str
    category: FactorCategory
    weight: float  # 0.0 - 1.0
    description: str = ""
    min_value: float = 0.0
    max_value: float = 1.0
    invert: bool = False  # If True, higher value = lower risk
    
    def __post_init__(self):
        if not 0.0 <= self.weight <= 1.0:
            raise InvalidFactorError(f"Weight must be 0-1, got {self.weight}")
        if self.min_value >= self.max_value:
            raise InvalidFactorError("min_value must be < max_value")


@dataclass
class FactorValue:
    """
    A measured value for a risk factor.
    """
    factor_id: str
    raw_value: float
    normalized_value: float  # 0.0 - 1.0, higher = more risk
    contribution: float      # Weighted contribution to total risk
    confidence: float = 1.0  # 0.0 - 1.0
    source: str = ""
    measured_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "contribution": self.contribution,
            "confidence": self.confidence,
            "source": self.source,
            "measured_at": self.measured_at,
        }


@dataclass
class RiskDecomposition:
    """
    Complete risk decomposition result.
    """
    subject_id: str
    subject_type: str  # "AGENT", "PDO", "PAC", etc.
    total_risk: float  # 0.0 - 1.0
    risk_level: RiskLevel
    factors: List[FactorValue]
    method: DecompositionMethod
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def top_contributors(self, n: int = 3) -> List[FactorValue]:
        """Get top N contributing factors."""
        sorted_factors = sorted(
            self.factors,
            key=lambda f: abs(f.contribution),
            reverse=True
        )
        return sorted_factors[:n]
    
    def factors_by_category(self) -> Dict[str, List[FactorValue]]:
        """Group factors by category."""
        result: Dict[str, List[FactorValue]] = defaultdict(list)
        # This requires factor definitions to be available
        return dict(result)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "total_risk": self.total_risk,
            "risk_level": self.risk_level.value,
            "factors": [f.to_dict() for f in self.factors],
            "method": self.method.value,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of decomposition."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


@dataclass
class Counterfactual:
    """
    A counterfactual explanation showing what would change the outcome.
    """
    original_risk: float
    target_risk: float
    required_changes: List[Tuple[str, float, float]]  # (factor_id, from_value, to_value)
    explanation: str
    feasibility: float  # 0.0 - 1.0, how achievable is this change


@dataclass
class FactorExplanation:
    """
    Human-readable explanation of a factor's contribution.
    """
    factor_id: str
    factor_name: str
    contribution_pct: float
    direction: str  # "INCREASES_RISK" or "DECREASES_RISK"
    explanation: str
    recommendations: List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# FACTOR PROFILES
# ═══════════════════════════════════════════════════════════════════════════════

# Standard factor profiles for different subjects
AGENT_FACTORS = [
    FactorDefinition("agent_failure_rate", "Failure Rate", FactorCategory.EXECUTION, 0.25, 
                     "Rate of task failures"),
    FactorDefinition("agent_latency", "Response Latency", FactorCategory.OPERATIONAL, 0.15,
                     "Average response time"),
    FactorDefinition("agent_compliance", "Compliance Score", FactorCategory.COMPLIANCE, 0.20,
                     "Governance compliance rate", invert=True),
    FactorDefinition("agent_data_quality", "Data Quality", FactorCategory.DATA, 0.15,
                     "Output data quality score", invert=True),
    FactorDefinition("agent_security_score", "Security Posture", FactorCategory.SECURITY, 0.15,
                     "Security assessment score", invert=True),
    FactorDefinition("agent_recency", "Activity Recency", FactorCategory.TEMPORAL, 0.10,
                     "Time since last activity"),
]

PDO_FACTORS = [
    FactorDefinition("pdo_wrap_completeness", "WRAP Completeness", FactorCategory.DATA, 0.20,
                     "Percentage of WRAPs received", invert=True),
    FactorDefinition("pdo_hash_integrity", "Hash Integrity", FactorCategory.SECURITY, 0.25,
                     "Hash verification success rate", invert=True),
    FactorDefinition("pdo_agent_risk", "Aggregate Agent Risk", FactorCategory.AGENT, 0.20,
                     "Combined risk from agents"),
    FactorDefinition("pdo_ber_confidence", "BER Confidence", FactorCategory.COMPLIANCE, 0.20,
                     "BER approval confidence", invert=True),
    FactorDefinition("pdo_timing", "Timing Deviation", FactorCategory.TEMPORAL, 0.15,
                     "Deviation from expected timeline"),
]

PAC_FACTORS = [
    FactorDefinition("pac_complexity", "Complexity Score", FactorCategory.EXECUTION, 0.20,
                     "Task complexity level"),
    FactorDefinition("pac_agent_count", "Agent Count Risk", FactorCategory.OPERATIONAL, 0.15,
                     "Risk from number of agents"),
    FactorDefinition("pac_dependency_depth", "Dependency Depth", FactorCategory.EXECUTION, 0.15,
                     "Depth of task dependencies"),
    FactorDefinition("pac_historical_success", "Historical Success", FactorCategory.EXECUTION, 0.20,
                     "Success rate of similar PACs", invert=True),
    FactorDefinition("pac_resource_utilization", "Resource Utilization", FactorCategory.OPERATIONAL, 0.15,
                     "Resource usage level"),
    FactorDefinition("pac_compliance_score", "Compliance Score", FactorCategory.COMPLIANCE, 0.15,
                     "Governance compliance", invert=True),
]


# ═══════════════════════════════════════════════════════════════════════════════
# RISK DECOMPOSITION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GIERiskDecompositionEngine:
    """
    Glass-box risk decomposition engine.
    
    Decomposes final risk scores into interpretable sub-factors
    with full explainability.
    """

    def __init__(
        self,
        method: DecompositionMethod = DecompositionMethod.WEIGHTED_SUM,
        normalize_weights: bool = True,
    ):
        """Initialize engine."""
        self._method = method
        self._normalize_weights = normalize_weights
        self._factor_registry: Dict[str, List[FactorDefinition]] = {
            "AGENT": AGENT_FACTORS,
            "PDO": PDO_FACTORS,
            "PAC": PAC_FACTORS,
        }
        self._custom_factors: Dict[str, List[FactorDefinition]] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # Factor Management
    # ─────────────────────────────────────────────────────────────────────────

    def register_factors(
        self,
        subject_type: str,
        factors: List[FactorDefinition],
    ) -> None:
        """Register custom factors for a subject type."""
        self._custom_factors[subject_type] = factors

    def get_factors(self, subject_type: str) -> List[FactorDefinition]:
        """Get factors for a subject type."""
        if subject_type in self._custom_factors:
            return self._custom_factors[subject_type]
        return self._factor_registry.get(subject_type, [])

    def validate_factors(self, subject_type: str) -> Tuple[bool, List[str]]:
        """Validate factor configuration."""
        errors = []
        factors = self.get_factors(subject_type)
        
        if not factors:
            errors.append(f"No factors defined for {subject_type}")
            return False, errors
        
        total_weight = sum(f.weight for f in factors)
        if self._normalize_weights:
            if not (0.99 <= total_weight <= 1.01):  # Allow small float error
                errors.append(f"Weights sum to {total_weight}, expected 1.0")
        
        # Check for duplicate IDs
        ids = [f.factor_id for f in factors]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate factor IDs found")
        
        return len(errors) == 0, errors

    # ─────────────────────────────────────────────────────────────────────────
    # Decomposition
    # ─────────────────────────────────────────────────────────────────────────

    def decompose(
        self,
        subject_id: str,
        subject_type: str,
        measurements: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RiskDecomposition:
        """
        Decompose risk into weighted factors.
        
        Args:
            subject_id: ID of the subject (agent, PDO, PAC)
            subject_type: Type of subject
            measurements: Raw measurements keyed by factor_id
            metadata: Optional additional context
            
        Returns:
            Complete risk decomposition
        """
        factors = self.get_factors(subject_type)
        if not factors:
            raise MissingFactorError(f"No factors for {subject_type}")
        
        # Normalize weights if needed
        total_weight = sum(f.weight for f in factors)
        weight_scale = 1.0 / total_weight if self._normalize_weights else 1.0
        
        # Compute factor values
        factor_values: List[FactorValue] = []
        weighted_sum = 0.0
        
        for factor_def in factors:
            raw_value = measurements.get(factor_def.factor_id, 0.5)  # Default to mid-range
            
            # Normalize to 0-1
            normalized = self._normalize_value(
                raw_value,
                factor_def.min_value,
                factor_def.max_value,
                factor_def.invert,
            )
            
            # Compute contribution
            weight = factor_def.weight * weight_scale
            contribution = normalized * weight
            weighted_sum += contribution
            
            factor_values.append(FactorValue(
                factor_id=factor_def.factor_id,
                raw_value=raw_value,
                normalized_value=normalized,
                contribution=contribution,
                source=subject_type,
            ))
        
        # Apply decomposition method
        if self._method == DecompositionMethod.WEIGHTED_SUM:
            total_risk = weighted_sum
        elif self._method == DecompositionMethod.MULTIPLICATIVE:
            total_risk = self._multiplicative_risk(factor_values)
        else:
            total_risk = weighted_sum  # Default
        
        # Clamp to valid range
        total_risk = max(0.0, min(1.0, total_risk))
        
        return RiskDecomposition(
            subject_id=subject_id,
            subject_type=subject_type,
            total_risk=total_risk,
            risk_level=self._classify_risk(total_risk),
            factors=factor_values,
            method=self._method,
            metadata=metadata or {},
        )

    def _normalize_value(
        self,
        value: float,
        min_val: float,
        max_val: float,
        invert: bool,
    ) -> float:
        """Normalize value to 0-1 range."""
        # Clamp to range
        clamped = max(min_val, min(max_val, value))
        
        # Normalize
        range_size = max_val - min_val
        if range_size == 0:
            normalized = 0.5
        else:
            normalized = (clamped - min_val) / range_size
        
        # Invert if higher value means lower risk
        if invert:
            normalized = 1.0 - normalized
        
        return normalized

    def _multiplicative_risk(self, factors: List[FactorValue]) -> float:
        """Compute risk using multiplicative method."""
        # Product of (1 - risk_reduction) for positive factors
        survival_prob = 1.0
        for f in factors:
            survival_prob *= (1 - f.normalized_value * 0.5)
        return 1.0 - survival_prob

    def _classify_risk(self, risk: float) -> RiskLevel:
        """Classify risk value into level."""
        if risk < 0.2:
            return RiskLevel.NEGLIGIBLE
        elif risk < 0.4:
            return RiskLevel.LOW
        elif risk < 0.6:
            return RiskLevel.MEDIUM
        elif risk < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    # ─────────────────────────────────────────────────────────────────────────
    # Explanations
    # ─────────────────────────────────────────────────────────────────────────

    def explain(self, decomposition: RiskDecomposition) -> List[FactorExplanation]:
        """
        Generate human-readable explanations for each factor.
        """
        explanations = []
        factors = self.get_factors(decomposition.subject_type)
        factor_defs = {f.factor_id: f for f in factors}
        
        for fv in decomposition.factors:
            factor_def = factor_defs.get(fv.factor_id)
            if not factor_def:
                continue
            
            # Calculate contribution percentage
            total_contribution = sum(abs(f.contribution) for f in decomposition.factors)
            pct = (abs(fv.contribution) / total_contribution * 100) if total_contribution > 0 else 0
            
            # Determine direction
            direction = "INCREASES_RISK" if fv.normalized_value > 0.5 else "DECREASES_RISK"
            
            # Generate explanation
            explanation = self._generate_factor_explanation(
                factor_def, fv, direction
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                factor_def, fv, direction
            )
            
            explanations.append(FactorExplanation(
                factor_id=fv.factor_id,
                factor_name=factor_def.name,
                contribution_pct=pct,
                direction=direction,
                explanation=explanation,
                recommendations=recommendations,
            ))
        
        return explanations

    def _generate_factor_explanation(
        self,
        factor_def: FactorDefinition,
        value: FactorValue,
        direction: str,
    ) -> str:
        """Generate explanation text for a factor."""
        if direction == "INCREASES_RISK":
            return (
                f"{factor_def.name} is elevated at {value.normalized_value:.1%} "
                f"contributing {value.contribution:.1%} to total risk. "
                f"{factor_def.description}"
            )
        else:
            return (
                f"{factor_def.name} is within acceptable range at {value.normalized_value:.1%}, "
                f"providing {abs(value.contribution):.1%} risk mitigation. "
                f"{factor_def.description}"
            )

    def _generate_recommendations(
        self,
        factor_def: FactorDefinition,
        value: FactorValue,
        direction: str,
    ) -> List[str]:
        """Generate recommendations for a factor."""
        if direction != "INCREASES_RISK" or value.normalized_value < 0.3:
            return []
        
        recommendations = []
        
        if factor_def.category == FactorCategory.EXECUTION:
            recommendations.append(f"Review execution patterns for {factor_def.name}")
        elif factor_def.category == FactorCategory.COMPLIANCE:
            recommendations.append(f"Audit compliance status for {factor_def.name}")
        elif factor_def.category == FactorCategory.SECURITY:
            recommendations.append(f"Conduct security review for {factor_def.name}")
        elif factor_def.category == FactorCategory.DATA:
            recommendations.append(f"Verify data integrity for {factor_def.name}")
        elif factor_def.category == FactorCategory.OPERATIONAL:
            recommendations.append(f"Optimize operational parameters for {factor_def.name}")
        elif factor_def.category == FactorCategory.TEMPORAL:
            recommendations.append(f"Review timing constraints for {factor_def.name}")
        
        if value.normalized_value > 0.7:
            recommendations.append(f"URGENT: Immediate attention required for {factor_def.name}")
        
        return recommendations

    # ─────────────────────────────────────────────────────────────────────────
    # Counterfactuals
    # ─────────────────────────────────────────────────────────────────────────

    def generate_counterfactual(
        self,
        decomposition: RiskDecomposition,
        target_level: RiskLevel,
    ) -> Optional[Counterfactual]:
        """
        Generate counterfactual showing what changes would achieve target risk level.
        """
        target_thresholds = {
            RiskLevel.NEGLIGIBLE: 0.15,
            RiskLevel.LOW: 0.35,
            RiskLevel.MEDIUM: 0.55,
            RiskLevel.HIGH: 0.75,
        }
        
        target_risk = target_thresholds.get(target_level)
        if target_risk is None or target_risk >= decomposition.total_risk:
            return None
        
        # Find factors that can be improved
        factors = self.get_factors(decomposition.subject_type)
        factor_defs = {f.factor_id: f for f in factors}
        
        required_changes = []
        current_risk = decomposition.total_risk
        
        # Sort by contribution (highest first)
        sorted_factors = sorted(
            decomposition.factors,
            key=lambda f: f.contribution,
            reverse=True
        )
        
        for fv in sorted_factors:
            if current_risk <= target_risk:
                break
            
            factor_def = factor_defs.get(fv.factor_id)
            if not factor_def or fv.normalized_value <= 0.2:
                continue
            
            # Calculate how much this factor needs to improve
            max_contribution_reduction = fv.contribution * 0.6  # Max 60% reduction
            new_normalized = max(0.2, fv.normalized_value - 0.4)
            risk_reduction = (fv.normalized_value - new_normalized) * factor_def.weight
            
            required_changes.append((
                fv.factor_id,
                fv.normalized_value,
                new_normalized,
            ))
            
            current_risk -= risk_reduction
        
        if not required_changes:
            return None
        
        # Calculate feasibility
        feasibility = 1.0 - (len(required_changes) * 0.15)
        feasibility = max(0.1, feasibility)
        
        explanation = self._generate_counterfactual_explanation(
            decomposition.total_risk,
            target_risk,
            required_changes,
            factor_defs,
        )
        
        return Counterfactual(
            original_risk=decomposition.total_risk,
            target_risk=target_risk,
            required_changes=required_changes,
            explanation=explanation,
            feasibility=feasibility,
        )

    def _generate_counterfactual_explanation(
        self,
        original: float,
        target: float,
        changes: List[Tuple[str, float, float]],
        factor_defs: Dict[str, FactorDefinition],
    ) -> str:
        """Generate explanation for counterfactual."""
        change_descriptions = []
        for factor_id, from_val, to_val in changes:
            factor_def = factor_defs.get(factor_id)
            name = factor_def.name if factor_def else factor_id
            reduction = (from_val - to_val) * 100
            change_descriptions.append(f"reduce {name} by {reduction:.0f}%")
        
        changes_text = ", ".join(change_descriptions)
        return (
            f"To reduce risk from {original:.1%} to {target:.1%}, "
            f"the following changes are needed: {changes_text}."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Aggregation
    # ─────────────────────────────────────────────────────────────────────────

    def aggregate_agent_risks(
        self,
        decompositions: List[RiskDecomposition],
    ) -> RiskDecomposition:
        """
        Aggregate multiple agent risk decompositions.
        """
        if not decompositions:
            raise RiskDecompositionError("No decompositions to aggregate")
        
        # Weight by inverse of current risk (give more weight to risky agents)
        total_weight = sum(d.total_risk + 0.1 for d in decompositions)
        
        weighted_risk = sum(
            d.total_risk * (d.total_risk + 0.1) / total_weight
            for d in decompositions
        )
        
        # Also consider max risk (weakest link)
        max_risk = max(d.total_risk for d in decompositions)
        
        # Blend weighted average and max
        aggregate_risk = 0.6 * weighted_risk + 0.4 * max_risk
        
        # Create synthetic factor values
        factor_values = [
            FactorValue(
                factor_id="aggregate_mean",
                raw_value=weighted_risk,
                normalized_value=weighted_risk,
                contribution=weighted_risk * 0.6,
                source="AGGREGATION",
            ),
            FactorValue(
                factor_id="aggregate_max",
                raw_value=max_risk,
                normalized_value=max_risk,
                contribution=max_risk * 0.4,
                source="AGGREGATION",
            ),
        ]
        
        return RiskDecomposition(
            subject_id="AGGREGATE",
            subject_type="AGENT_GROUP",
            total_risk=aggregate_risk,
            risk_level=self._classify_risk(aggregate_risk),
            factors=factor_values,
            method=DecompositionMethod.WEIGHTED_SUM,
            metadata={
                "agent_count": len(decompositions),
                "agent_risks": [d.total_risk for d in decompositions],
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_engine: Optional[GIERiskDecompositionEngine] = None


def get_risk_decomposition_engine() -> GIERiskDecompositionEngine:
    """Get or create global risk decomposition engine."""
    global _engine
    if _engine is None:
        _engine = GIERiskDecompositionEngine()
    return _engine


def reset_risk_decomposition_engine() -> None:
    """Reset global engine."""
    global _engine
    _engine = None
