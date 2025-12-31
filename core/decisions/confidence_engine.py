"""
Decision Confidence Engine — Proof-Weighted Confidence + Explanation Generation.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-10 (Maggie) — ML / RISK
Deliverable: Decision Confidence Engine

Features:
- Proof-weighted confidence scoring
- Multi-factor confidence calculation
- Natural language explanation generation
- Confidence interval estimation
- Audit trail with reasoning chain

This engine provides quantified confidence for governance decisions
with full explainability for compliance and audit requirements.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# CONSTANTS
# =============================================================================

ENGINE_VERSION = "1.0.0"
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


# =============================================================================
# ENUMS
# =============================================================================

class ConfidenceLevel(Enum):
    """Categorical confidence levels."""
    VERY_LOW = "VERY_LOW"      # 0.0 - 0.2
    LOW = "LOW"                 # 0.2 - 0.4
    MEDIUM = "MEDIUM"           # 0.4 - 0.6
    HIGH = "HIGH"               # 0.6 - 0.8
    VERY_HIGH = "VERY_HIGH"     # 0.8 - 1.0


class ProofType(Enum):
    """Types of proof artifacts."""
    TEST_RESULT = "TEST_RESULT"
    HASH_VERIFICATION = "HASH_VERIFICATION"
    SIGNATURE = "SIGNATURE"
    TIMESTAMP = "TIMESTAMP"
    PEER_REVIEW = "PEER_REVIEW"
    AUDIT_LOG = "AUDIT_LOG"
    EXTERNAL_ATTESTATION = "EXTERNAL_ATTESTATION"


class FactorCategory(Enum):
    """Categories of confidence factors."""
    PROOF = "PROOF"             # Evidence-based
    CONTEXT = "CONTEXT"         # Environmental
    HISTORY = "HISTORY"         # Historical performance
    AUTHORITY = "AUTHORITY"     # Source credibility
    CONSENSUS = "CONSENSUS"     # Agreement level


class DecisionType(Enum):
    """Types of decisions being evaluated."""
    PAC_APPROVAL = "PAC_APPROVAL"
    WRAP_ACCEPTANCE = "WRAP_ACCEPTANCE"
    BER_ISSUANCE = "BER_ISSUANCE"
    PDO_EMISSION = "PDO_EMISSION"
    CLOSURE_VALIDATION = "CLOSURE_VALIDATION"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ConfidenceError(Exception):
    """Base exception for confidence engine errors."""
    pass


class InsufficientEvidenceError(ConfidenceError):
    """Raised when evidence is insufficient for calculation."""
    
    def __init__(self, required: int, provided: int) -> None:
        self.required = required
        self.provided = provided
        super().__init__(
            f"Insufficient evidence: required {required}, provided {provided}"
        )


class InvalidProofError(ConfidenceError):
    """Raised when proof artifact is invalid."""
    
    def __init__(self, proof_id: str, reason: str) -> None:
        self.proof_id = proof_id
        self.reason = reason
        super().__init__(f"Invalid proof '{proof_id}': {reason}")


class CalculationError(ConfidenceError):
    """Raised when confidence calculation fails."""
    
    def __init__(self, stage: str, reason: str) -> None:
        self.stage = stage
        self.reason = reason
        super().__init__(f"Calculation failed at '{stage}': {reason}")


class ThresholdNotMetError(ConfidenceError):
    """Raised when confidence threshold not met."""
    
    def __init__(self, threshold: float, actual: float) -> None:
        self.threshold = threshold
        self.actual = actual
        super().__init__(
            f"Confidence threshold not met: required {threshold:.2f}, actual {actual:.2f}"
        )


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProofArtifact:
    """A piece of evidence for confidence calculation."""
    
    proof_id: str
    proof_type: ProofType
    source: str
    timestamp: str
    weight: float = 1.0  # 0.0 to 1.0
    verified: bool = False
    hash_value: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate weight bounds."""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be 0.0-1.0, got {self.weight}")
    
    def verify(self, content: str) -> bool:
        """Verify proof hash matches content."""
        if not self.hash_value:
            return False
        computed = hashlib.sha256(content.encode()).hexdigest()
        self.verified = (computed == self.hash_value)
        return self.verified


@dataclass
class ConfidenceFactor:
    """A factor contributing to confidence score."""
    
    factor_id: str
    name: str
    category: FactorCategory
    value: float  # 0.0 to 1.0
    weight: float  # Relative importance
    explanation: str
    supporting_proofs: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate value bounds."""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Value must be 0.0-1.0, got {self.value}")


@dataclass
class ConfidenceInterval:
    """Confidence interval with lower and upper bounds."""
    
    lower: float
    point_estimate: float
    upper: float
    confidence_percentage: float = 95.0
    
    def __post_init__(self) -> None:
        """Validate interval ordering."""
        if not self.lower <= self.point_estimate <= self.upper:
            raise ValueError("Invalid interval: lower <= point <= upper required")
    
    @property
    def width(self) -> float:
        """Width of confidence interval."""
        return self.upper - self.lower
    
    def contains(self, value: float) -> bool:
        """Check if value is within interval."""
        return self.lower <= value <= self.upper


@dataclass
class ReasoningStep:
    """A step in the reasoning chain."""
    
    step_number: int
    description: str
    input_values: Dict[str, float]
    output_value: float
    formula: str
    
    def to_explanation(self) -> str:
        """Generate natural language explanation."""
        inputs_str = ", ".join(f"{k}={v:.3f}" for k, v in self.input_values.items())
        return f"Step {self.step_number}: {self.description} ({inputs_str}) → {self.output_value:.3f}"


@dataclass
class ConfidenceResult:
    """Complete confidence calculation result."""
    
    result_id: str
    decision_type: DecisionType
    subject_id: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    interval: ConfidenceInterval
    factors: List[ConfidenceFactor]
    reasoning_chain: List[ReasoningStep]
    explanation: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def meets_threshold(self) -> bool:
        """Check if confidence meets default threshold."""
        return self.confidence_score >= DEFAULT_CONFIDENCE_THRESHOLD
    
    def check_threshold(self, threshold: float) -> bool:
        """Check if confidence meets specific threshold."""
        return self.confidence_score >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "result_id": self.result_id,
            "decision_type": self.decision_type.value,
            "subject_id": self.subject_id,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level.value,
            "interval": {
                "lower": self.interval.lower,
                "point_estimate": self.interval.point_estimate,
                "upper": self.interval.upper,
            },
            "explanation": self.explanation,
            "timestamp": self.timestamp,
        }


# =============================================================================
# CONFIDENCE CALCULATOR
# =============================================================================

class ConfidenceCalculator:
    """
    Calculates confidence scores from proof artifacts and factors.
    """
    
    def __init__(self, min_evidence: int = 1) -> None:
        self._min_evidence = min_evidence
    
    def calculate_weighted_average(
        self,
        factors: List[ConfidenceFactor],
    ) -> float:
        """
        Calculate weighted average of factors.
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not factors:
            return 0.0
        
        total_weight = sum(f.weight for f in factors)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(f.value * f.weight for f in factors)
        return weighted_sum / total_weight
    
    def calculate_bayesian(
        self,
        prior: float,
        proofs: List[ProofArtifact],
    ) -> float:
        """
        Calculate Bayesian posterior from prior and evidence.
        
        P(H|E) = P(E|H) * P(H) / P(E)
        
        Simplified: Update prior based on verified proofs.
        """
        if not proofs:
            return prior
        
        # Each verified proof increases confidence
        verified_count = sum(1 for p in proofs if p.verified)
        total_count = len(proofs)
        
        if total_count == 0:
            return prior
        
        verification_rate = verified_count / total_count
        
        # Bayesian-like update
        likelihood = 0.9 if verification_rate > 0.8 else 0.5 + 0.4 * verification_rate
        
        # Simplified posterior
        posterior = (likelihood * prior) / (
            likelihood * prior + (1 - likelihood) * (1 - prior)
        )
        
        return min(max(posterior, 0.0), 1.0)
    
    def calculate_dempster_shafer(
        self,
        beliefs: List[Tuple[float, float]],  # (belief, plausibility)
    ) -> Tuple[float, float]:
        """
        Calculate Dempster-Shafer belief and plausibility.
        
        Returns:
            (combined_belief, combined_plausibility)
        """
        if not beliefs:
            return (0.0, 1.0)
        
        combined_belief = beliefs[0][0]
        combined_plausibility = beliefs[0][1]
        
        for belief, plausibility in beliefs[1:]:
            # Combine beliefs using Dempster's rule (simplified)
            k = combined_belief * (1 - plausibility) + belief * (1 - combined_plausibility)
            
            if k >= 1.0:
                # Conflict - use average
                combined_belief = (combined_belief + belief) / 2
                combined_plausibility = (combined_plausibility + plausibility) / 2
            else:
                combined_belief = (combined_belief * belief) / (1 - k) if k < 1 else 0.5
                combined_plausibility = min(combined_plausibility, plausibility)
        
        return (min(max(combined_belief, 0.0), 1.0),
                min(max(combined_plausibility, 0.0), 1.0))
    
    def calculate_confidence_interval(
        self,
        point_estimate: float,
        sample_size: int,
        confidence_pct: float = 95.0,
    ) -> ConfidenceInterval:
        """
        Calculate confidence interval using normal approximation.
        """
        # Z-score for confidence level
        z_scores = {90.0: 1.645, 95.0: 1.96, 99.0: 2.576}
        z = z_scores.get(confidence_pct, 1.96)
        
        # Standard error (using binomial approximation)
        if sample_size <= 0:
            se = 0.25  # Maximum uncertainty
        else:
            p = point_estimate
            se = math.sqrt(p * (1 - p) / sample_size) if 0 < p < 1 else 0.25 / math.sqrt(sample_size)
        
        margin = z * se
        
        lower = max(0.0, point_estimate - margin)
        upper = min(1.0, point_estimate + margin)
        
        return ConfidenceInterval(
            lower=lower,
            point_estimate=point_estimate,
            upper=upper,
            confidence_percentage=confidence_pct,
        )
    
    def score_to_level(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to categorical level."""
        if score < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif score < 0.4:
            return ConfidenceLevel.LOW
        elif score < 0.6:
            return ConfidenceLevel.MEDIUM
        elif score < 0.8:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH


# =============================================================================
# EXPLANATION GENERATOR
# =============================================================================

class ExplanationGenerator:
    """
    Generates natural language explanations for confidence results.
    """
    
    TEMPLATES = {
        ConfidenceLevel.VERY_HIGH: (
            "The analysis shows VERY HIGH confidence ({score:.1%}) in this decision. "
            "This is supported by {proof_count} verified proofs and {factor_count} positive factors."
        ),
        ConfidenceLevel.HIGH: (
            "The analysis indicates HIGH confidence ({score:.1%}). "
            "{positive_factors} contribute positively, with {proof_count} supporting proofs."
        ),
        ConfidenceLevel.MEDIUM: (
            "The analysis shows MEDIUM confidence ({score:.1%}). "
            "While there is supporting evidence, some factors reduce certainty: {concerns}."
        ),
        ConfidenceLevel.LOW: (
            "The analysis indicates LOW confidence ({score:.1%}). "
            "Key concerns: {concerns}. Only {proof_count} proofs were verified."
        ),
        ConfidenceLevel.VERY_LOW: (
            "The analysis shows VERY LOW confidence ({score:.1%}). "
            "Insufficient evidence or significant concerns exist: {concerns}."
        ),
    }
    
    def generate_explanation(
        self,
        score: float,
        level: ConfidenceLevel,
        factors: List[ConfidenceFactor],
        proofs: List[ProofArtifact],
    ) -> str:
        """Generate natural language explanation."""
        template = self.TEMPLATES[level]
        
        # Gather statistics
        proof_count = sum(1 for p in proofs if p.verified)
        factor_count = len(factors)
        
        # Identify positive factors
        positive = [f for f in factors if f.value >= 0.6]
        positive_factors = ", ".join(f.name for f in positive[:3]) or "No strong factors"
        
        # Identify concerns
        concerns_list = [f for f in factors if f.value < 0.5]
        concerns = ", ".join(f.name for f in concerns_list[:3]) or "None identified"
        
        return template.format(
            score=score,
            proof_count=proof_count,
            factor_count=factor_count,
            positive_factors=positive_factors,
            concerns=concerns,
        )
    
    def generate_reasoning_chain(
        self,
        factors: List[ConfidenceFactor],
        final_score: float,
    ) -> List[ReasoningStep]:
        """Generate step-by-step reasoning chain."""
        steps = []
        step_num = 1
        
        # Step 1: Category aggregation
        categories: Dict[FactorCategory, List[ConfidenceFactor]] = {}
        for f in factors:
            categories.setdefault(f.category, []).append(f)
        
        category_scores = {}
        for cat, cat_factors in categories.items():
            avg = sum(f.value for f in cat_factors) / len(cat_factors)
            category_scores[cat.value] = avg
            
            steps.append(ReasoningStep(
                step_number=step_num,
                description=f"Aggregate {cat.value} factors",
                input_values={f.name: f.value for f in cat_factors},
                output_value=avg,
                formula="mean(factor_values)",
            ))
            step_num += 1
        
        # Step 2: Weight application
        weighted_inputs = {k: v * 0.2 for k, v in category_scores.items()}
        
        steps.append(ReasoningStep(
            step_number=step_num,
            description="Apply category weights",
            input_values=category_scores,
            output_value=sum(weighted_inputs.values()),
            formula="sum(category_score * weight)",
        ))
        step_num += 1
        
        # Step 3: Final score
        steps.append(ReasoningStep(
            step_number=step_num,
            description="Compute final confidence score",
            input_values={"weighted_sum": sum(weighted_inputs.values())},
            output_value=final_score,
            formula="normalize(weighted_sum)",
        ))
        
        return steps


# =============================================================================
# DECISION CONFIDENCE ENGINE
# =============================================================================

class DecisionConfidenceEngine:
    """
    Main engine for computing decision confidence with full explainability.
    
    Features:
    - Multi-method confidence calculation
    - Proof verification and weighting
    - Natural language explanations
    - Audit-ready reasoning chains
    """
    
    def __init__(
        self,
        min_evidence: int = 1,
        default_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._min_evidence = min_evidence
        self._default_threshold = default_threshold
        self._calculator = ConfidenceCalculator(min_evidence)
        self._explainer = ExplanationGenerator()
        self._proofs: Dict[str, ProofArtifact] = {}
        self._factors: List[ConfidenceFactor] = []
    
    # -------------------------------------------------------------------------
    # PROOF MANAGEMENT
    # -------------------------------------------------------------------------
    
    def add_proof(self, proof: ProofArtifact) -> None:
        """Add a proof artifact."""
        self._proofs[proof.proof_id] = proof
    
    def verify_proof(self, proof_id: str, content: str) -> bool:
        """Verify a proof against content."""
        if proof_id not in self._proofs:
            raise InvalidProofError(proof_id, "Proof not found")
        return self._proofs[proof_id].verify(content)
    
    def get_verified_proofs(self) -> List[ProofArtifact]:
        """Get all verified proofs."""
        return [p for p in self._proofs.values() if p.verified]
    
    # -------------------------------------------------------------------------
    # FACTOR MANAGEMENT
    # -------------------------------------------------------------------------
    
    def add_factor(self, factor: ConfidenceFactor) -> None:
        """Add a confidence factor."""
        self._factors.append(factor)
    
    def create_factor_from_proofs(
        self,
        name: str,
        category: FactorCategory,
        proof_ids: List[str],
    ) -> ConfidenceFactor:
        """Create a factor from proof verification results."""
        matching_proofs = [
            self._proofs[pid] for pid in proof_ids
            if pid in self._proofs
        ]
        
        if not matching_proofs:
            value = 0.0
        else:
            verified = sum(1 for p in matching_proofs if p.verified)
            weighted = sum(p.weight for p in matching_proofs if p.verified)
            total_weight = sum(p.weight for p in matching_proofs)
            value = weighted / total_weight if total_weight > 0 else 0.0
        
        return ConfidenceFactor(
            factor_id=f"F-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            category=category,
            value=value,
            weight=1.0,
            explanation=f"Based on {len(matching_proofs)} proofs",
            supporting_proofs=proof_ids,
        )
    
    # -------------------------------------------------------------------------
    # CONFIDENCE CALCULATION
    # -------------------------------------------------------------------------
    
    def calculate_confidence(
        self,
        decision_type: DecisionType,
        subject_id: str,
        method: str = "weighted",
    ) -> ConfidenceResult:
        """
        Calculate confidence for a decision.
        
        Args:
            decision_type: Type of decision being evaluated
            subject_id: ID of the subject (PAC, WRAP, etc.)
            method: Calculation method ('weighted', 'bayesian', 'dempster_shafer')
        
        Returns:
            ConfidenceResult with full explanation
        """
        # Check minimum evidence
        total_evidence = len(self._proofs) + len(self._factors)
        if total_evidence < self._min_evidence:
            raise InsufficientEvidenceError(self._min_evidence, total_evidence)
        
        # Calculate score based on method
        proofs = list(self._proofs.values())
        
        if method == "bayesian":
            prior = 0.5  # Neutral prior
            score = self._calculator.calculate_bayesian(prior, proofs)
        elif method == "dempster_shafer":
            beliefs = [
                (f.value, min(f.value + 0.2, 1.0))
                for f in self._factors
            ]
            belief, _ = self._calculator.calculate_dempster_shafer(beliefs)
            score = belief
        else:  # weighted (default)
            score = self._calculator.calculate_weighted_average(self._factors)
        
        # Boost score based on verified proofs
        verified_ratio = len(self.get_verified_proofs()) / max(len(proofs), 1)
        score = score * 0.7 + verified_ratio * 0.3
        score = min(max(score, 0.0), 1.0)
        
        # Determine confidence level
        level = self._calculator.score_to_level(score)
        
        # Calculate interval
        interval = self._calculator.calculate_confidence_interval(
            score, total_evidence
        )
        
        # Generate explanation
        explanation = self._explainer.generate_explanation(
            score, level, self._factors, proofs
        )
        
        # Generate reasoning chain
        reasoning_chain = self._explainer.generate_reasoning_chain(
            self._factors, score
        )
        
        return ConfidenceResult(
            result_id=f"CR-{uuid.uuid4().hex[:12].upper()}",
            decision_type=decision_type,
            subject_id=subject_id,
            confidence_score=score,
            confidence_level=level,
            interval=interval,
            factors=list(self._factors),
            reasoning_chain=reasoning_chain,
            explanation=explanation,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    def require_confidence(
        self,
        decision_type: DecisionType,
        subject_id: str,
        threshold: Optional[float] = None,
    ) -> ConfidenceResult:
        """
        Calculate confidence and raise if below threshold.
        
        Raises:
            ThresholdNotMetError: If confidence below threshold
        """
        result = self.calculate_confidence(decision_type, subject_id)
        threshold = threshold or self._default_threshold
        
        if not result.check_threshold(threshold):
            raise ThresholdNotMetError(threshold, result.confidence_score)
        
        return result
    
    # -------------------------------------------------------------------------
    # RESET
    # -------------------------------------------------------------------------
    
    def reset(self) -> None:
        """Reset engine state for new calculation."""
        self._proofs.clear()
        self._factors.clear()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_engine(
    min_evidence: int = 1,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> DecisionConfidenceEngine:
    """Create a configured confidence engine."""
    return DecisionConfidenceEngine(
        min_evidence=min_evidence,
        default_threshold=threshold,
    )


def create_proof(
    proof_type: ProofType,
    source: str,
    weight: float = 1.0,
    content: Optional[str] = None,
) -> ProofArtifact:
    """Create a proof artifact."""
    proof_id = f"P-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    hash_value = None
    if content:
        hash_value = hashlib.sha256(content.encode()).hexdigest()
    
    return ProofArtifact(
        proof_id=proof_id,
        proof_type=proof_type,
        source=source,
        timestamp=timestamp,
        weight=weight,
        hash_value=hash_value,
    )


def create_factor(
    name: str,
    category: FactorCategory,
    value: float,
    weight: float = 1.0,
    explanation: str = "",
) -> ConfidenceFactor:
    """Create a confidence factor."""
    return ConfidenceFactor(
        factor_id=f"F-{uuid.uuid4().hex[:8].upper()}",
        name=name,
        category=category,
        value=value,
        weight=weight,
        explanation=explanation or f"Factor: {name}",
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version
    "ENGINE_VERSION",
    # Constants
    "DEFAULT_CONFIDENCE_THRESHOLD",
    # Enums
    "ConfidenceLevel",
    "ProofType",
    "FactorCategory",
    "DecisionType",
    # Exceptions
    "ConfidenceError",
    "InsufficientEvidenceError",
    "InvalidProofError",
    "CalculationError",
    "ThresholdNotMetError",
    # Data Classes
    "ProofArtifact",
    "ConfidenceFactor",
    "ConfidenceInterval",
    "ReasoningStep",
    "ConfidenceResult",
    # Core Classes
    "ConfidenceCalculator",
    "ExplanationGenerator",
    "DecisionConfidenceEngine",
    # Factory Functions
    "create_engine",
    "create_proof",
    "create_factor",
]
