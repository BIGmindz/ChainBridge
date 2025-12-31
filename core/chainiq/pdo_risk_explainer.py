"""
PDO Risk Explainer Engine

Generates human-readable explanations for risk-tagged PDO artifacts.
Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023.

Agent: GID-10 (Maggie) — ML & Applied AI Lead
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "risk_threshold": 0.5,
    "max_factors_displayed": 10,
    "confidence_method": "bootstrap",
    "explanation_max_length": 2000,
    "signal_window_default_hours": 24,
    "model_version": "risk-explain-v1.0.0",
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RiskLevel(Enum):
    """Risk severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_score(cls, score: float) -> "RiskLevel":
        """Determine risk level from numeric score."""
        if score < 0.3:
            return cls.LOW
        elif score < 0.5:
            return cls.MEDIUM
        elif score < 0.7:
            return cls.HIGH
        else:
            return cls.CRITICAL


class FactorDirection(Enum):
    """Direction of factor deviation from normal."""
    ABOVE = "ABOVE"
    BELOW = "BELOW"
    OUTSIDE_RANGE = "OUTSIDE_RANGE"
    WITHIN_RANGE = "WITHIN_RANGE"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class RiskExplainerError(Exception):
    """Base exception for risk explainer errors."""
    pass


class ExplanationRequiredError(RiskExplainerError):
    """Raised when explanation is required but missing."""
    pass


class ExplanationImmutableError(RiskExplainerError):
    """Raised when attempting to modify an immutable explanation."""
    pass


class InvalidBindingError(RiskExplainerError):
    """Raised when explanation-PDO binding is invalid."""
    pass


class SignalNotFoundError(RiskExplainerError):
    """Raised when referenced signal source cannot be found."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RiskFactor:
    """
    Individual risk factor contributing to overall risk score.
    
    Per INV-RISK-004: Factor Traceability
    """
    factor_id: str
    signal_id: str
    signal_name: str
    value: float
    threshold: float
    weight: float
    direction: FactorDirection
    contribution: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "factor_id": self.factor_id,
            "signal_id": self.signal_id,
            "signal_name": self.signal_name,
            "value": self.value,
            "threshold": self.threshold,
            "weight": self.weight,
            "direction": self.direction.value,
            "contribution": self.contribution,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class RiskExplanation:
    """
    Complete risk explanation for a PDO artifact.
    
    Implements all invariants from PDO_RISK_EXPLAINABILITY_v1.md:
    - INV-RISK-001: Required for high-risk PDOs
    - INV-RISK-002: Immutability (frozen dataclass)
    - INV-RISK-003: Cryptographic binding (pdo_hash)
    - INV-RISK-004: Factor traceability (factors list)
    - INV-RISK-005: Confidence disclosure (confidence bounds)
    - INV-RISK-006: Temporal validity (signal window)
    """
    explanation_id: str
    pdo_id: str
    pdo_hash: str
    
    risk_score: float
    risk_level: RiskLevel
    
    summary: str
    detailed_reasoning: str
    
    factors: Tuple[RiskFactor, ...]  # Immutable tuple
    mitigations: Tuple[str, ...] = field(default_factory=tuple)
    
    confidence_lower: float = 0.0
    confidence_upper: float = 1.0
    
    signal_window_start: str = ""
    signal_window_end: str = ""
    
    model_version: str = DEFAULT_CONFIG["model_version"]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    explanation_hash: str = ""

    def __post_init__(self):
        """Compute explanation hash after initialization."""
        if not self.explanation_hash:
            # Use object.__setattr__ because dataclass is frozen
            computed_hash = self._compute_hash()
            object.__setattr__(self, "explanation_hash", computed_hash)

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of explanation content."""
        content = {
            "explanation_id": self.explanation_id,
            "pdo_id": self.pdo_id,
            "pdo_hash": self.pdo_hash,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "summary": self.summary,
            "detailed_reasoning": self.detailed_reasoning,
            "factors": [f.to_dict() for f in self.factors],
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "signal_window_start": self.signal_window_start,
            "signal_window_end": self.signal_window_end,
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "explanation_id": self.explanation_id,
            "pdo_id": self.pdo_id,
            "pdo_hash": self.pdo_hash,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "summary": self.summary,
            "detailed_reasoning": self.detailed_reasoning,
            "factors": [f.to_dict() for f in self.factors],
            "mitigations": list(self.mitigations),
            "confidence_lower": self.confidence_lower,
            "confidence_upper": self.confidence_upper,
            "signal_window_start": self.signal_window_start,
            "signal_window_end": self.signal_window_end,
            "model_version": self.model_version,
            "created_at": self.created_at,
            "explanation_hash": self.explanation_hash,
        }


@dataclass
class SignalSource:
    """Source of a risk signal."""
    signal_id: str
    signal_name: str
    category: str  # market, sentiment, technical, onchain, model
    current_value: float
    baseline_value: float
    threshold_low: Optional[float] = None
    threshold_high: Optional[float] = None
    weight: float = 1.0
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLANATION GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ExplanationGenerator:
    """
    Generates human-readable explanations from risk factors.
    
    Uses template-based generation with factor-specific phrasing.
    """
    
    # Factor explanation templates
    TEMPLATES = {
        FactorDirection.ABOVE: "{signal_name} is elevated at {value:.2f} (threshold: {threshold:.2f}), contributing {contribution:.1%} to risk.",
        FactorDirection.BELOW: "{signal_name} is depressed at {value:.2f} (threshold: {threshold:.2f}), contributing {contribution:.1%} to risk.",
        FactorDirection.OUTSIDE_RANGE: "{signal_name} at {value:.2f} is outside normal range, contributing {contribution:.1%} to risk.",
        FactorDirection.WITHIN_RANGE: "{signal_name} at {value:.2f} is within acceptable bounds.",
    }
    
    # Risk level summaries
    LEVEL_SUMMARIES = {
        RiskLevel.LOW: "Risk assessment indicates minimal concerns. Standard monitoring protocols apply.",
        RiskLevel.MEDIUM: "Risk assessment indicates elevated concerns. Enhanced monitoring recommended.",
        RiskLevel.HIGH: "Risk assessment indicates significant concerns. Corrective action likely needed.",
        RiskLevel.CRITICAL: "Risk assessment indicates severe concerns. Immediate intervention required.",
    }

    def generate_factor_explanation(self, factor: RiskFactor) -> str:
        """Generate explanation text for a single factor."""
        template = self.TEMPLATES.get(factor.direction, self.TEMPLATES[FactorDirection.ABOVE])
        return template.format(
            signal_name=factor.signal_name,
            value=factor.value,
            threshold=factor.threshold,
            contribution=factor.contribution,
        )

    def generate_summary(self, risk_level: RiskLevel, top_factors: List[RiskFactor]) -> str:
        """Generate summary text based on risk level and top factors."""
        base_summary = self.LEVEL_SUMMARIES[risk_level]
        
        if top_factors:
            top_factor = top_factors[0]
            factor_note = f" Primary driver: {top_factor.signal_name}."
            return base_summary + factor_note
        
        return base_summary

    def generate_detailed_reasoning(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        factors: List[RiskFactor],
        confidence_lower: float,
        confidence_upper: float,
    ) -> str:
        """Generate detailed reasoning text."""
        lines = [
            f"## Risk Assessment Details",
            f"",
            f"Overall risk score: {risk_score:.3f} ({risk_level.value})",
            f"Confidence interval: [{confidence_lower:.3f}, {confidence_upper:.3f}]",
            f"",
            f"### Contributing Factors ({len(factors)} analyzed)",
            f"",
        ]
        
        # Sort factors by contribution (descending)
        sorted_factors = sorted(factors, key=lambda f: f.contribution, reverse=True)
        
        for i, factor in enumerate(sorted_factors[:10], 1):
            explanation = self.generate_factor_explanation(factor)
            lines.append(f"{i}. {explanation}")
        
        if len(sorted_factors) > 10:
            lines.append(f"")
            lines.append(f"... and {len(sorted_factors) - 10} additional factors")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ConfidenceCalculator:
    """
    Calculates confidence intervals for risk assessments.
    
    Per INV-RISK-005: Confidence Disclosure
    """
    
    @staticmethod
    def bootstrap(
        risk_score: float,
        n_factors: int,
        base_variance: float = 0.1,
    ) -> Tuple[float, float]:
        """
        Calculate confidence bounds using bootstrap-inspired heuristic.
        
        More factors = tighter confidence interval.
        """
        # Variance decreases with more factors (more evidence)
        factor_adjustment = 1.0 / max(1, n_factors ** 0.5)
        variance = base_variance * factor_adjustment
        
        # Calculate bounds, clamped to [0, 1]
        lower = max(0.0, risk_score - variance)
        upper = min(1.0, risk_score + variance)
        
        return (lower, upper)

    @staticmethod
    def fixed_margin(
        risk_score: float,
        margin: float = 0.1,
    ) -> Tuple[float, float]:
        """Calculate confidence bounds with fixed margin."""
        return (
            max(0.0, risk_score - margin),
            min(1.0, risk_score + margin),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RISK EXPLAINER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PDORiskExplainer:
    """
    Main engine for generating risk explanations for PDO artifacts.
    
    Thread-safe and implements all invariants from PDO_RISK_EXPLAINABILITY_v1.md.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the risk explainer."""
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._lock = threading.RLock()
        
        # Storage for explanations (pdo_id -> explanation)
        self._explanations: Dict[str, RiskExplanation] = {}
        
        # Signal registry (signal_id -> SignalSource)
        self._signals: Dict[str, SignalSource] = {}
        
        # Generators
        self._explanation_generator = ExplanationGenerator()
        self._confidence_calculator = ConfidenceCalculator()
        
        # Explanation counter for ID generation
        self._counter = 0

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    @property
    def risk_threshold(self) -> float:
        """Get risk threshold requiring explanation."""
        return self._config["risk_threshold"]

    # ─────────────────────────────────────────────────────────────────────────
    # Signal Management
    # ─────────────────────────────────────────────────────────────────────────

    def register_signal(self, signal: SignalSource) -> None:
        """Register a signal source."""
        with self._lock:
            self._signals[signal.signal_id] = signal

    def get_signal(self, signal_id: str) -> Optional[SignalSource]:
        """Get a registered signal source."""
        with self._lock:
            return self._signals.get(signal_id)

    def list_signals(self) -> List[SignalSource]:
        """List all registered signal sources."""
        with self._lock:
            return list(self._signals.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Factor Analysis
    # ─────────────────────────────────────────────────────────────────────────

    def analyze_signal(self, signal: SignalSource) -> Optional[RiskFactor]:
        """
        Analyze a signal and produce a risk factor if threshold exceeded.
        
        Per INV-RISK-004: Factor Traceability
        """
        value = signal.current_value
        baseline = signal.baseline_value
        
        # Determine if signal indicates risk
        direction: Optional[FactorDirection] = None
        threshold = 0.0
        
        if signal.threshold_high is not None and value > signal.threshold_high:
            direction = FactorDirection.ABOVE
            threshold = signal.threshold_high
        elif signal.threshold_low is not None and value < signal.threshold_low:
            direction = FactorDirection.BELOW
            threshold = signal.threshold_low
        elif signal.threshold_high is not None and signal.threshold_low is not None:
            if value < signal.threshold_low or value > signal.threshold_high:
                direction = FactorDirection.OUTSIDE_RANGE
                threshold = signal.threshold_high if value > signal.threshold_high else signal.threshold_low
        
        if direction is None:
            return None  # No risk factor triggered
        
        # Calculate contribution based on deviation and weight
        if threshold != 0:
            deviation = abs(value - threshold) / abs(threshold)
        else:
            deviation = abs(value - baseline) if baseline != 0 else abs(value)
        
        contribution = min(1.0, deviation * signal.weight * 0.2)  # Scaled contribution
        
        return RiskFactor(
            factor_id=f"FACTOR-{signal.signal_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            signal_id=signal.signal_id,
            signal_name=signal.signal_name,
            value=value,
            threshold=threshold,
            weight=signal.weight,
            direction=direction,
            contribution=contribution,
            explanation=signal.description or f"{signal.signal_name} exceeded threshold",
        )

    def compute_risk_score(self, factors: List[RiskFactor]) -> float:
        """
        Compute aggregate risk score from factors.
        
        Uses weighted average with saturation.
        """
        if not factors:
            return 0.0
        
        total_contribution = sum(f.contribution for f in factors)
        total_weight = sum(f.weight for f in factors)
        
        if total_weight == 0:
            return 0.0
        
        # Weighted average, clamped to [0, 1]
        raw_score = total_contribution / total_weight
        
        # Apply saturation curve (logistic-like)
        saturated_score = 2 * raw_score / (1 + raw_score)
        
        return min(1.0, max(0.0, saturated_score))

    # ─────────────────────────────────────────────────────────────────────────
    # Explanation Generation (Core Operations)
    # ─────────────────────────────────────────────────────────────────────────

    def explain(
        self,
        pdo_id: str,
        pdo_hash: str,
        risk_score: Optional[float] = None,
        signal_ids: Optional[List[str]] = None,
        custom_factors: Optional[List[RiskFactor]] = None,
        mitigations: Optional[List[str]] = None,
    ) -> RiskExplanation:
        """
        Generate a risk explanation for a PDO artifact.
        
        Per INV-RISK-001: Explanation Required for High-Risk PDOs
        Per INV-RISK-003: Cryptographic Binding
        """
        with self._lock:
            # Generate explanation ID
            self._counter += 1
            explanation_id = f"EXPLAIN-{pdo_id}-{self._counter:06d}"
            
            # Analyze signals if provided
            factors: List[RiskFactor] = list(custom_factors or [])
            
            if signal_ids:
                for signal_id in signal_ids:
                    signal = self._signals.get(signal_id)
                    if signal:
                        factor = self.analyze_signal(signal)
                        if factor:
                            factors.append(factor)
                    else:
                        raise SignalNotFoundError(f"Signal not found: {signal_id}")
            
            # Compute risk score if not provided
            if risk_score is None:
                risk_score = self.compute_risk_score(factors)
            
            # Determine risk level
            risk_level = RiskLevel.from_score(risk_score)
            
            # Calculate confidence interval
            confidence_lower, confidence_upper = self._confidence_calculator.bootstrap(
                risk_score, len(factors)
            )
            
            # Generate signal window
            now = datetime.utcnow()
            window_hours = self._config["signal_window_default_hours"]
            signal_window_start = (now - timedelta(hours=window_hours)).isoformat() + "Z"
            signal_window_end = now.isoformat() + "Z"
            
            # Sort factors by contribution for summary generation
            sorted_factors = sorted(factors, key=lambda f: f.contribution, reverse=True)
            top_factors = sorted_factors[:self._config["max_factors_displayed"]]
            
            # Generate text explanations
            summary = self._explanation_generator.generate_summary(risk_level, top_factors)
            detailed_reasoning = self._explanation_generator.generate_detailed_reasoning(
                risk_score, risk_level, factors, confidence_lower, confidence_upper
            )
            
            # Truncate if needed
            max_length = self._config["explanation_max_length"]
            if len(detailed_reasoning) > max_length:
                detailed_reasoning = detailed_reasoning[:max_length - 3] + "..."
            
            # Create explanation (immutable per INV-RISK-002)
            explanation = RiskExplanation(
                explanation_id=explanation_id,
                pdo_id=pdo_id,
                pdo_hash=pdo_hash,
                risk_score=risk_score,
                risk_level=risk_level,
                summary=summary,
                detailed_reasoning=detailed_reasoning,
                factors=tuple(factors),
                mitigations=tuple(mitigations or []),
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                signal_window_start=signal_window_start,
                signal_window_end=signal_window_end,
                model_version=self._config["model_version"],
            )
            
            return explanation

    def attach(self, pdo_id: str, explanation: RiskExplanation) -> None:
        """
        Attach an explanation to a PDO (store the binding).
        
        Per INV-RISK-002: Explanation Immutability
        Per INV-RISK-003: Cryptographic Binding
        """
        with self._lock:
            if pdo_id in self._explanations:
                raise ExplanationImmutableError(
                    f"Explanation already attached for PDO {pdo_id}. "
                    "Explanations cannot be modified or replaced."
                )
            
            if explanation.pdo_id != pdo_id:
                raise InvalidBindingError(
                    f"Explanation pdo_id ({explanation.pdo_id}) does not match "
                    f"target pdo_id ({pdo_id})"
                )
            
            self._explanations[pdo_id] = explanation

    def query(self, pdo_id: str) -> Optional[RiskExplanation]:
        """
        Query explanation for a PDO.
        
        Per INV-RISK-005: Read-only query
        """
        with self._lock:
            return self._explanations.get(pdo_id)

    def validate(self, explanation: RiskExplanation) -> bool:
        """
        Validate explanation integrity.
        
        Checks:
        - Hash integrity
        - Required fields present
        - Confidence bounds valid
        - Temporal validity
        """
        # Check hash integrity
        computed_hash = explanation._compute_hash()
        if computed_hash != explanation.explanation_hash:
            return False
        
        # Check required fields
        if not explanation.pdo_id or not explanation.pdo_hash:
            return False
        
        # Check confidence bounds (INV-RISK-005)
        if explanation.confidence_lower < 0 or explanation.confidence_upper > 1:
            return False
        if explanation.confidence_lower > explanation.confidence_upper:
            return False
        
        # Check temporal validity (INV-RISK-006)
        if explanation.signal_window_start and explanation.signal_window_end:
            try:
                start = datetime.fromisoformat(explanation.signal_window_start.rstrip("Z"))
                end = datetime.fromisoformat(explanation.signal_window_end.rstrip("Z"))
                if start >= end:
                    return False
            except ValueError:
                return False
        
        return True

    def requires_explanation(self, risk_score: float) -> bool:
        """
        Check if a risk score requires explanation.
        
        Per INV-RISK-001: Explanation Required for High-Risk PDOs
        """
        return risk_score >= self._config["risk_threshold"]

    # ─────────────────────────────────────────────────────────────────────────
    # Forbidden Operations (Per Law)
    # ─────────────────────────────────────────────────────────────────────────

    def modify_explanation(self, pdo_id: str, **kwargs) -> None:
        """FORBIDDEN: Modify an explanation."""
        raise ExplanationImmutableError(
            "modify_explanation() is forbidden. "
            "Explanations are immutable per INV-RISK-002."
        )

    def detach_explanation(self, pdo_id: str) -> None:
        """FORBIDDEN: Detach an explanation from a PDO."""
        raise ExplanationImmutableError(
            "detach_explanation() is forbidden. "
            "Explanations cannot be detached per INV-RISK-002."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────────────────────

    def export_json(self, pdo_ids: Optional[List[str]] = None) -> str:
        """Export explanations as JSON."""
        with self._lock:
            if pdo_ids:
                explanations = [
                    self._explanations[pid].to_dict()
                    for pid in pdo_ids
                    if pid in self._explanations
                ]
            else:
                explanations = [e.to_dict() for e in self._explanations.values()]
            
            export_data = {
                "export_id": f"EXP-RISK-{datetime.utcnow().strftime('%Y-%m-%d')}-{len(explanations):03d}",
                "export_timestamp": datetime.utcnow().isoformat() + "Z",
                "pdo_count": len(explanations),
                "high_risk_count": sum(
                    1 for e in explanations 
                    if e["risk_level"] in ("HIGH", "CRITICAL")
                ),
                "explanations": explanations,
                "exported_by": "GID-10",
            }
            
            return json.dumps(export_data, indent=2)

    def export_csv_summary(self, pdo_ids: Optional[List[str]] = None) -> str:
        """Export explanations as CSV summary."""
        with self._lock:
            if pdo_ids:
                explanations = [
                    self._explanations[pid]
                    for pid in pdo_ids
                    if pid in self._explanations
                ]
            else:
                explanations = list(self._explanations.values())
            
            lines = [
                "pdo_id,risk_score,risk_level,summary,factor_count,created_at"
            ]
            
            for e in explanations:
                summary_escaped = e.summary.replace('"', '""')
                lines.append(
                    f'{e.pdo_id},{e.risk_score:.4f},{e.risk_level.value},'
                    f'"{summary_escaped}",{len(e.factors)},{e.created_at}'
                )
            
            return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored explanations."""
        with self._lock:
            if not self._explanations:
                return {
                    "total_explanations": 0,
                    "by_risk_level": {},
                    "average_risk_score": 0.0,
                    "average_factor_count": 0.0,
                }
            
            explanations = list(self._explanations.values())
            
            by_level = {}
            for level in RiskLevel:
                count = sum(1 for e in explanations if e.risk_level == level)
                by_level[level.value] = count
            
            return {
                "total_explanations": len(explanations),
                "by_risk_level": by_level,
                "average_risk_score": sum(e.risk_score for e in explanations) / len(explanations),
                "average_factor_count": sum(len(e.factors) for e in explanations) / len(explanations),
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_explainer: Optional[PDORiskExplainer] = None
_global_lock = threading.Lock()


def get_risk_explainer(config: Optional[Dict[str, Any]] = None) -> PDORiskExplainer:
    """Get or create the global risk explainer instance."""
    global _global_explainer
    
    with _global_lock:
        if _global_explainer is None:
            _global_explainer = PDORiskExplainer(config)
        return _global_explainer


def reset_risk_explainer() -> None:
    """Reset the global risk explainer (for testing)."""
    global _global_explainer
    
    with _global_lock:
        _global_explainer = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def explain_pdo_risk(
    pdo_id: str,
    pdo_hash: str,
    risk_score: Optional[float] = None,
    signal_ids: Optional[List[str]] = None,
    custom_factors: Optional[List[RiskFactor]] = None,
) -> RiskExplanation:
    """
    Convenience function to generate and attach a risk explanation.
    
    Usage:
        explanation = explain_pdo_risk(
            pdo_id="PDO-PAC-023-001",
            pdo_hash="abc123...",
            risk_score=0.75,
        )
    """
    explainer = get_risk_explainer()
    
    explanation = explainer.explain(
        pdo_id=pdo_id,
        pdo_hash=pdo_hash,
        risk_score=risk_score,
        signal_ids=signal_ids,
        custom_factors=custom_factors,
    )
    
    explainer.attach(pdo_id, explanation)
    
    return explanation


def query_pdo_explanation(pdo_id: str) -> Optional[RiskExplanation]:
    """Convenience function to query a PDO explanation."""
    explainer = get_risk_explainer()
    return explainer.query(pdo_id)
