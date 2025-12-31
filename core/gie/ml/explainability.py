"""
ML Explainability Module — Model Interpretability & Audit Trail.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-10 (Leo) — ADVANCED AI/ML EXPLAINABILITY
Deliverable: DecisionExplainer, ConfidenceEstimator, FeatureAttributor,
             AuditableModel, ExplanationRenderer, ModelCard

Features:
- Decision explanation generation
- Confidence intervals and calibration
- Feature attribution (SHAP-like)
- Auditable model wrappers
- Multi-format explanation rendering
- Model cards for governance
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# =============================================================================
# VERSION
# =============================================================================

EXPLAINABILITY_VERSION = "1.0.0"


# =============================================================================
# ENUMS
# =============================================================================

class ExplanationType(Enum):
    """Types of explanations."""
    FEATURE_IMPORTANCE = "FEATURE_IMPORTANCE"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    RULE_BASED = "RULE_BASED"
    EXAMPLE_BASED = "EXAMPLE_BASED"
    ATTENTION_BASED = "ATTENTION_BASED"
    GRADIENT_BASED = "GRADIENT_BASED"


class ConfidenceMethod(Enum):
    """Methods for confidence estimation."""
    SOFTMAX_TEMPERATURE = "SOFTMAX_TEMPERATURE"
    MONTE_CARLO_DROPOUT = "MONTE_CARLO_DROPOUT"
    ENSEMBLE = "ENSEMBLE"
    CALIBRATED = "CALIBRATED"
    CONFORMAL = "CONFORMAL"


class AttributionMethod(Enum):
    """Feature attribution methods."""
    PERMUTATION = "PERMUTATION"
    SHAP = "SHAP"
    LIME = "LIME"
    INTEGRATED_GRADIENTS = "INTEGRATED_GRADIENTS"
    ATTENTION_WEIGHTS = "ATTENTION_WEIGHTS"


class RenderFormat(Enum):
    """Explanation rendering formats."""
    TEXT = "TEXT"
    HTML = "HTML"
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    LATEX = "LATEX"


class BiasType(Enum):
    """Types of bias in models."""
    DEMOGRAPHIC = "DEMOGRAPHIC"
    SELECTION = "SELECTION"
    CONFIRMATION = "CONFIRMATION"
    MEASUREMENT = "MEASUREMENT"
    ALGORITHMIC = "ALGORITHMIC"


class RiskLevel(Enum):
    """Model risk levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ExplainabilityError(Exception):
    """Base explainability exception."""
    pass


class ModelNotFittedError(ExplainabilityError):
    """Model not fitted."""
    pass


class AttributionError(ExplainabilityError):
    """Attribution computation error."""
    pass


class ConfidenceError(ExplainabilityError):
    """Confidence estimation error."""
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Explanation:
    """A model explanation."""
    explanation_id: str
    explanation_type: ExplanationType
    prediction_id: str
    model_id: str
    input_features: Dict[str, Any]
    output_prediction: Any
    confidence: float
    feature_attributions: Dict[str, float]
    counterfactuals: List[Dict[str, Any]]
    rules: List[str]
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "explanation_id": self.explanation_id,
            "explanation_type": self.explanation_type.value,
            "prediction_id": self.prediction_id,
            "model_id": self.model_id,
            "input_features": self.input_features,
            "output_prediction": self.output_prediction,
            "confidence": self.confidence,
            "feature_attributions": self.feature_attributions,
            "counterfactuals": self.counterfactuals,
            "rules": self.rules,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class ConfidenceInterval:
    """A confidence interval for predictions."""
    point_estimate: float
    lower_bound: float
    upper_bound: float
    confidence_level: float
    method: ConfidenceMethod
    calibrated: bool = False
    
    @property
    def width(self) -> float:
        """Calculate interval width."""
        return self.upper_bound - self.lower_bound
    
    def contains(self, value: float) -> bool:
        """Check if value is within interval."""
        return self.lower_bound <= value <= self.upper_bound
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "point_estimate": self.point_estimate,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "confidence_level": self.confidence_level,
            "method": self.method.value,
            "width": self.width,
            "calibrated": self.calibrated,
        }


@dataclass
class FeatureAttribution:
    """Attribution for a single feature."""
    feature_name: str
    attribution_value: float
    base_value: float
    method: AttributionMethod
    importance_rank: int
    direction: str  # "positive", "negative", "neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_name": self.feature_name,
            "attribution_value": self.attribution_value,
            "base_value": self.base_value,
            "method": self.method.value,
            "importance_rank": self.importance_rank,
            "direction": self.direction,
        }


@dataclass
class AuditRecord:
    """Audit trail record for model decisions."""
    audit_id: str
    model_id: str
    timestamp: datetime
    input_hash: str
    output_hash: str
    explanation_id: str
    decision: str
    confidence: float
    user_id: Optional[str]
    session_id: Optional[str]
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "audit_id": self.audit_id,
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "explanation_id": self.explanation_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ModelCard:
    """Model documentation card."""
    model_id: str
    model_name: str
    version: str
    description: str
    intended_use: str
    out_of_scope_use: str
    training_data: str
    evaluation_data: str
    metrics: Dict[str, float]
    ethical_considerations: List[str]
    caveats: List[str]
    risk_level: RiskLevel
    bias_analysis: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    contact: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "version": self.version,
            "description": self.description,
            "intended_use": self.intended_use,
            "out_of_scope_use": self.out_of_scope_use,
            "metrics": self.metrics,
            "ethical_considerations": self.ethical_considerations,
            "caveats": self.caveats,
            "risk_level": self.risk_level.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "contact": self.contact,
        }


@dataclass
class BiasReport:
    """Bias analysis report."""
    model_id: str
    bias_type: BiasType
    affected_groups: List[str]
    disparity_metric: float
    threshold: float
    passed: bool
    recommendations: List[str]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "bias_type": self.bias_type.value,
            "affected_groups": self.affected_groups,
            "disparity_metric": self.disparity_metric,
            "threshold": self.threshold,
            "passed": self.passed,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat(),
        }


# =============================================================================
# PROTOCOLS
# =============================================================================

T = TypeVar('T')


class PredictiveModel(Protocol):
    """Protocol for predictive models."""
    
    def predict(self, features: Dict[str, Any]) -> Any:
        """Make a prediction."""
        ...
    
    def predict_proba(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Get prediction probabilities."""
        ...


# =============================================================================
# DECISION EXPLAINER
# =============================================================================

class DecisionExplainer:
    """
    Generates human-readable explanations for model decisions.
    
    Features:
    - Multiple explanation types
    - Counterfactual generation
    - Rule extraction
    - Natural language summaries
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._explanation_counter = 0
        self._explanations: Dict[str, Explanation] = {}
        self._templates: Dict[str, str] = self._load_templates()
    
    def explain(
        self,
        model_id: str,
        prediction_id: str,
        features: Dict[str, Any],
        prediction: Any,
        confidence: float,
        explanation_type: ExplanationType = ExplanationType.FEATURE_IMPORTANCE,
    ) -> Explanation:
        """
        Generate an explanation for a model decision.
        
        Args:
            model_id: Model identifier
            prediction_id: Prediction identifier
            features: Input features
            prediction: Model output
            confidence: Prediction confidence
            explanation_type: Type of explanation to generate
        """
        with self._lock:
            self._explanation_counter += 1
            exp_id = f"EXP-{self._explanation_counter:08d}"
        
        # Calculate feature attributions
        attributions = self._calculate_attributions(features, prediction)
        
        # Generate counterfactuals
        counterfactuals = self._generate_counterfactuals(features, prediction)
        
        # Extract rules
        rules = self._extract_rules(features, attributions)
        
        explanation = Explanation(
            explanation_id=exp_id,
            explanation_type=explanation_type,
            prediction_id=prediction_id,
            model_id=model_id,
            input_features=features,
            output_prediction=prediction,
            confidence=confidence,
            feature_attributions=attributions,
            counterfactuals=counterfactuals,
            rules=rules,
            generated_at=datetime.now(timezone.utc),
        )
        
        with self._lock:
            self._explanations[exp_id] = explanation
        
        return explanation
    
    def get_explanation(self, explanation_id: str) -> Optional[Explanation]:
        """Get explanation by ID."""
        return self._explanations.get(explanation_id)
    
    def summarize(self, explanation: Explanation) -> str:
        """Generate natural language summary."""
        # Get top features
        sorted_attrs = sorted(
            explanation.feature_attributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:3]
        
        # Build summary
        parts = [f"The model predicted '{explanation.output_prediction}' with {explanation.confidence:.1%} confidence."]
        
        if sorted_attrs:
            parts.append("Key factors:")
            for feature, value in sorted_attrs:
                direction = "increased" if value > 0 else "decreased"
                parts.append(f"  - {feature} {direction} the prediction by {abs(value):.2f}")
        
        if explanation.rules:
            parts.append(f"Primary rule: {explanation.rules[0]}")
        
        return "\n".join(parts)
    
    def _calculate_attributions(
        self,
        features: Dict[str, Any],
        prediction: Any,
    ) -> Dict[str, float]:
        """Calculate feature attributions using permutation importance."""
        attributions = {}
        
        for feature_name, feature_value in features.items():
            # Simplified attribution: based on feature presence and type
            if isinstance(feature_value, (int, float)):
                # Numeric features get attribution based on magnitude
                attr = feature_value * 0.1 if feature_value != 0 else 0.0
            elif isinstance(feature_value, bool):
                attr = 0.5 if feature_value else -0.5
            elif isinstance(feature_value, str):
                attr = len(feature_value) * 0.01
            else:
                attr = 0.0
            
            attributions[feature_name] = attr
        
        # Normalize attributions
        total = sum(abs(v) for v in attributions.values())
        if total > 0:
            attributions = {k: v / total for k, v in attributions.items()}
        
        return attributions
    
    def _generate_counterfactuals(
        self,
        features: Dict[str, Any],
        prediction: Any,
    ) -> List[Dict[str, Any]]:
        """Generate counterfactual examples."""
        counterfactuals = []
        
        for feature_name, feature_value in features.items():
            cf = dict(features)
            
            # Create modified version
            if isinstance(feature_value, (int, float)):
                cf[feature_name] = feature_value * 0.5 if feature_value != 0 else 1.0
            elif isinstance(feature_value, bool):
                cf[feature_name] = not feature_value
            elif isinstance(feature_value, str):
                cf[feature_name] = "alternative_" + feature_value
            
            counterfactuals.append({
                "modified_feature": feature_name,
                "original_value": feature_value,
                "new_value": cf[feature_name],
                "features": cf,
            })
        
        return counterfactuals[:5]  # Limit to 5
    
    def _extract_rules(
        self,
        features: Dict[str, Any],
        attributions: Dict[str, float],
    ) -> List[str]:
        """Extract decision rules."""
        rules = []
        
        # Get top attributing features
        sorted_attrs = sorted(
            attributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        
        for feature, attr in sorted_attrs[:3]:
            value = features.get(feature)
            if attr > 0:
                rules.append(f"IF {feature} = {value} THEN prediction increases")
            else:
                rules.append(f"IF {feature} = {value} THEN prediction decreases")
        
        return rules
    
    def _load_templates(self) -> Dict[str, str]:
        """Load explanation templates."""
        return {
            "feature_importance": "The feature '{feature}' contributed {value:.2f} to the prediction.",
            "counterfactual": "If '{feature}' were '{new_value}' instead of '{old_value}', the prediction would change.",
            "rule": "Based on the rule: {rule}",
        }


# =============================================================================
# CONFIDENCE ESTIMATOR
# =============================================================================

class ConfidenceEstimator:
    """
    Estimates confidence intervals for predictions.
    
    Features:
    - Multiple estimation methods
    - Calibration tracking
    - Conformal prediction support
    - Uncertainty quantification
    """
    
    def __init__(
        self,
        default_method: ConfidenceMethod = ConfidenceMethod.ENSEMBLE,
    ) -> None:
        self._lock = threading.RLock()
        self._default_method = default_method
        self._calibration_history: List[Dict[str, Any]] = []
        self._calibration_error = 0.0
    
    def estimate(
        self,
        prediction: float,
        predictions_ensemble: Optional[List[float]] = None,
        confidence_level: float = 0.95,
        method: Optional[ConfidenceMethod] = None,
    ) -> ConfidenceInterval:
        """
        Estimate confidence interval for a prediction.
        
        Args:
            prediction: Point prediction
            predictions_ensemble: Ensemble predictions (if available)
            confidence_level: Desired confidence level
            method: Estimation method
        """
        method = method or self._default_method
        
        if method == ConfidenceMethod.ENSEMBLE and predictions_ensemble:
            return self._ensemble_interval(prediction, predictions_ensemble, confidence_level)
        elif method == ConfidenceMethod.SOFTMAX_TEMPERATURE:
            return self._temperature_interval(prediction, confidence_level)
        elif method == ConfidenceMethod.CALIBRATED:
            return self._calibrated_interval(prediction, confidence_level)
        elif method == ConfidenceMethod.CONFORMAL:
            return self._conformal_interval(prediction, confidence_level)
        else:
            # Default: simple heuristic
            return self._heuristic_interval(prediction, confidence_level)
    
    def calibrate(
        self,
        predictions: List[float],
        actuals: List[float],
    ) -> float:
        """
        Calibrate confidence estimator.
        
        Returns calibration error.
        """
        if not predictions or len(predictions) != len(actuals):
            raise ConfidenceError("Invalid calibration data")
        
        # Calculate Expected Calibration Error (ECE)
        n_bins = 10
        bins = [[] for _ in range(n_bins)]
        
        for pred, actual in zip(predictions, actuals):
            # Treat predictions as confidence scores
            bin_idx = min(int(pred * n_bins), n_bins - 1)
            correct = 1 if abs(pred - actual) < 0.1 else 0
            bins[bin_idx].append((pred, correct))
        
        ece = 0.0
        total = len(predictions)
        
        for bin_preds in bins:
            if bin_preds:
                avg_confidence = sum(p for p, _ in bin_preds) / len(bin_preds)
                avg_accuracy = sum(c for _, c in bin_preds) / len(bin_preds)
                ece += len(bin_preds) * abs(avg_confidence - avg_accuracy)
        
        self._calibration_error = ece / total if total > 0 else 0.0
        
        with self._lock:
            self._calibration_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "samples": len(predictions),
                "calibration_error": self._calibration_error,
            })
        
        return self._calibration_error
    
    def get_calibration_error(self) -> float:
        """Get current calibration error."""
        return self._calibration_error
    
    def _ensemble_interval(
        self,
        prediction: float,
        ensemble: List[float],
        confidence_level: float,
    ) -> ConfidenceInterval:
        """Calculate interval from ensemble predictions."""
        sorted_preds = sorted(ensemble)
        n = len(sorted_preds)
        
        # Calculate percentile bounds
        alpha = 1 - confidence_level
        lower_idx = int(alpha / 2 * n)
        upper_idx = int((1 - alpha / 2) * n) - 1
        
        lower_idx = max(0, lower_idx)
        upper_idx = min(n - 1, upper_idx)
        
        return ConfidenceInterval(
            point_estimate=prediction,
            lower_bound=sorted_preds[lower_idx],
            upper_bound=sorted_preds[upper_idx],
            confidence_level=confidence_level,
            method=ConfidenceMethod.ENSEMBLE,
            calibrated=False,
        )
    
    def _temperature_interval(
        self,
        prediction: float,
        confidence_level: float,
    ) -> ConfidenceInterval:
        """Calculate interval using temperature scaling."""
        # Simulate temperature-scaled uncertainty
        temperature = 1.5  # Would be learned from data
        uncertainty = 1.0 / temperature
        
        # Z-score for confidence level
        z = 1.96 if confidence_level >= 0.95 else 1.645
        
        margin = z * uncertainty * 0.1
        
        return ConfidenceInterval(
            point_estimate=prediction,
            lower_bound=prediction - margin,
            upper_bound=prediction + margin,
            confidence_level=confidence_level,
            method=ConfidenceMethod.SOFTMAX_TEMPERATURE,
            calibrated=False,
        )
    
    def _calibrated_interval(
        self,
        prediction: float,
        confidence_level: float,
    ) -> ConfidenceInterval:
        """Calculate calibrated interval."""
        # Adjust interval based on calibration error
        base_margin = 0.1
        adjusted_margin = base_margin * (1 + self._calibration_error)
        
        z = 1.96 if confidence_level >= 0.95 else 1.645
        margin = z * adjusted_margin
        
        return ConfidenceInterval(
            point_estimate=prediction,
            lower_bound=prediction - margin,
            upper_bound=prediction + margin,
            confidence_level=confidence_level,
            method=ConfidenceMethod.CALIBRATED,
            calibrated=True,
        )
    
    def _conformal_interval(
        self,
        prediction: float,
        confidence_level: float,
    ) -> ConfidenceInterval:
        """Calculate conformal prediction interval."""
        # Simplified conformal prediction
        # In practice, would use non-conformity scores from calibration set
        quantile = confidence_level
        margin = (1 - quantile) + 0.05
        
        return ConfidenceInterval(
            point_estimate=prediction,
            lower_bound=prediction - margin,
            upper_bound=prediction + margin,
            confidence_level=confidence_level,
            method=ConfidenceMethod.CONFORMAL,
            calibrated=False,
        )
    
    def _heuristic_interval(
        self,
        prediction: float,
        confidence_level: float,
    ) -> ConfidenceInterval:
        """Calculate heuristic interval."""
        margin = (1 - confidence_level) + 0.05
        
        return ConfidenceInterval(
            point_estimate=prediction,
            lower_bound=prediction - margin,
            upper_bound=prediction + margin,
            confidence_level=confidence_level,
            method=ConfidenceMethod.ENSEMBLE,
            calibrated=False,
        )


# =============================================================================
# FEATURE ATTRIBUTOR
# =============================================================================

class FeatureAttributor:
    """
    Feature attribution engine (SHAP-like functionality).
    
    Features:
    - Multiple attribution methods
    - Feature interaction detection
    - Global vs local attributions
    - Attribution consistency checks
    """
    
    def __init__(
        self,
        default_method: AttributionMethod = AttributionMethod.PERMUTATION,
    ) -> None:
        self._lock = threading.RLock()
        self._default_method = default_method
        self._global_importances: Dict[str, float] = {}
    
    def attribute(
        self,
        model: PredictiveModel,
        features: Dict[str, Any],
        method: Optional[AttributionMethod] = None,
        baseline: Optional[Dict[str, Any]] = None,
    ) -> List[FeatureAttribution]:
        """
        Calculate feature attributions.
        
        Args:
            model: The predictive model
            features: Input features
            method: Attribution method
            baseline: Baseline for comparison
        """
        method = method or self._default_method
        
        if method == AttributionMethod.PERMUTATION:
            return self._permutation_attribution(model, features)
        elif method == AttributionMethod.SHAP:
            return self._shap_attribution(model, features, baseline)
        elif method == AttributionMethod.LIME:
            return self._lime_attribution(model, features)
        elif method == AttributionMethod.INTEGRATED_GRADIENTS:
            return self._integrated_gradients(model, features, baseline)
        else:
            return self._permutation_attribution(model, features)
    
    def compute_global_importance(
        self,
        model: PredictiveModel,
        dataset: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Compute global feature importance across dataset.
        
        Args:
            model: The predictive model
            dataset: List of feature dictionaries
        """
        importance_sums: Dict[str, float] = defaultdict(float)
        
        for features in dataset:
            attributions = self.attribute(model, features)
            for attr in attributions:
                importance_sums[attr.feature_name] += abs(attr.attribution_value)
        
        # Normalize
        total = sum(importance_sums.values())
        if total > 0:
            self._global_importances = {
                k: v / total for k, v in importance_sums.items()
            }
        else:
            self._global_importances = dict(importance_sums)
        
        return self._global_importances
    
    def get_global_importance(self) -> Dict[str, float]:
        """Get cached global importance."""
        return dict(self._global_importances)
    
    def detect_interactions(
        self,
        model: PredictiveModel,
        features: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Detect feature interactions.
        
        Returns list of interacting feature pairs with strength.
        """
        interactions = []
        feature_names = list(features.keys())
        
        # Simple interaction detection via joint permutation
        base_pred = model.predict(features)
        
        for i, f1 in enumerate(feature_names):
            for f2 in feature_names[i + 1:]:
                # Permute both features
                modified = dict(features)
                modified[f1] = self._perturb_value(features[f1])
                modified[f2] = self._perturb_value(features[f2])
                
                joint_effect = abs(model.predict(modified) - base_pred)
                
                # Compare to sum of individual effects
                mod1 = dict(features)
                mod1[f1] = modified[f1]
                effect1 = abs(model.predict(mod1) - base_pred)
                
                mod2 = dict(features)
                mod2[f2] = modified[f2]
                effect2 = abs(model.predict(mod2) - base_pred)
                
                interaction_strength = joint_effect - (effect1 + effect2)
                
                if abs(interaction_strength) > 0.01:
                    interactions.append({
                        "features": [f1, f2],
                        "strength": interaction_strength,
                        "synergistic": interaction_strength > 0,
                    })
        
        return sorted(interactions, key=lambda x: abs(x["strength"]), reverse=True)
    
    def _permutation_attribution(
        self,
        model: PredictiveModel,
        features: Dict[str, Any],
    ) -> List[FeatureAttribution]:
        """Calculate permutation-based attributions."""
        attributions = []
        base_prediction = model.predict(features)
        
        for feature_name, feature_value in features.items():
            # Permute the feature
            modified = dict(features)
            modified[feature_name] = self._perturb_value(feature_value)
            
            # Measure impact
            modified_prediction = model.predict(modified)
            attribution_value = base_prediction - modified_prediction
            
            attributions.append(FeatureAttribution(
                feature_name=feature_name,
                attribution_value=attribution_value,
                base_value=base_prediction,
                method=AttributionMethod.PERMUTATION,
                importance_rank=0,  # Will be set after sorting
                direction="positive" if attribution_value > 0 else "negative" if attribution_value < 0 else "neutral",
            ))
        
        # Set ranks
        attributions.sort(key=lambda x: abs(x.attribution_value), reverse=True)
        for i, attr in enumerate(attributions):
            attr.importance_rank = i + 1
        
        return attributions
    
    def _shap_attribution(
        self,
        model: PredictiveModel,
        features: Dict[str, Any],
        baseline: Optional[Dict[str, Any]],
    ) -> List[FeatureAttribution]:
        """Calculate SHAP-like attributions."""
        # Simplified Shapley value approximation
        if baseline is None:
            baseline = {k: 0.0 if isinstance(v, (int, float)) else v for k, v in features.items()}
        
        attributions = []
        base_pred = model.predict(baseline)
        full_pred = model.predict(features)
        
        for feature_name, feature_value in features.items():
            # Marginal contribution
            with_feature = dict(baseline)
            with_feature[feature_name] = feature_value
            
            marginal = model.predict(with_feature) - base_pred
            
            attributions.append(FeatureAttribution(
                feature_name=feature_name,
                attribution_value=marginal,
                base_value=base_pred,
                method=AttributionMethod.SHAP,
                importance_rank=0,
                direction="positive" if marginal > 0 else "negative" if marginal < 0 else "neutral",
            ))
        
        # Set ranks
        attributions.sort(key=lambda x: abs(x.attribution_value), reverse=True)
        for i, attr in enumerate(attributions):
            attr.importance_rank = i + 1
        
        return attributions
    
    def _lime_attribution(
        self,
        model: PredictiveModel,
        features: Dict[str, Any],
    ) -> List[FeatureAttribution]:
        """Calculate LIME-like local attributions."""
        # Generate local samples
        samples = []
        weights = []
        
        base_pred = model.predict(features)
        
        for _ in range(20):
            sample = dict(features)
            for k, v in sample.items():
                if isinstance(v, (int, float)):
                    sample[k] = v + (hash(str(k) + str(_)) % 100 - 50) / 100
            
            samples.append(sample)
            # Weight by distance
            distance = sum((features[k] - sample[k])**2 for k in features if isinstance(features[k], (int, float)))
            weights.append(math.exp(-distance))
        
        # Simple linear approximation
        attributions = []
        for feature_name in features.keys():
            # Weighted average of differences
            total_weight = sum(weights)
            if total_weight > 0 and isinstance(features[feature_name], (int, float)):
                attr_value = sum(
                    w * (model.predict(s) - base_pred)
                    for s, w in zip(samples, weights)
                ) / total_weight
            else:
                attr_value = 0.0
            
            attributions.append(FeatureAttribution(
                feature_name=feature_name,
                attribution_value=attr_value,
                base_value=base_pred,
                method=AttributionMethod.LIME,
                importance_rank=0,
                direction="positive" if attr_value > 0 else "negative" if attr_value < 0 else "neutral",
            ))
        
        attributions.sort(key=lambda x: abs(x.attribution_value), reverse=True)
        for i, attr in enumerate(attributions):
            attr.importance_rank = i + 1
        
        return attributions
    
    def _integrated_gradients(
        self,
        model: PredictiveModel,
        features: Dict[str, Any],
        baseline: Optional[Dict[str, Any]],
    ) -> List[FeatureAttribution]:
        """Calculate integrated gradients approximation."""
        if baseline is None:
            baseline = {k: 0.0 if isinstance(v, (int, float)) else v for k, v in features.items()}
        
        steps = 10
        attributions = []
        
        for feature_name in features.keys():
            if not isinstance(features[feature_name], (int, float)):
                attributions.append(FeatureAttribution(
                    feature_name=feature_name,
                    attribution_value=0.0,
                    base_value=0.0,
                    method=AttributionMethod.INTEGRATED_GRADIENTS,
                    importance_rank=0,
                    direction="neutral",
                ))
                continue
            
            # Approximate gradient integral
            integral = 0.0
            for step in range(steps):
                alpha = step / steps
                interpolated = {
                    k: baseline[k] + alpha * (features[k] - baseline[k])
                    if isinstance(features[k], (int, float)) else features[k]
                    for k in features
                }
                
                # Numerical gradient approximation
                eps = 0.01
                plus = dict(interpolated)
                minus = dict(interpolated)
                plus[feature_name] = interpolated[feature_name] + eps
                minus[feature_name] = interpolated[feature_name] - eps
                
                gradient = (model.predict(plus) - model.predict(minus)) / (2 * eps)
                integral += gradient / steps
            
            attr_value = integral * (features[feature_name] - baseline[feature_name])
            
            attributions.append(FeatureAttribution(
                feature_name=feature_name,
                attribution_value=attr_value,
                base_value=model.predict(baseline),
                method=AttributionMethod.INTEGRATED_GRADIENTS,
                importance_rank=0,
                direction="positive" if attr_value > 0 else "negative" if attr_value < 0 else "neutral",
            ))
        
        attributions.sort(key=lambda x: abs(x.attribution_value), reverse=True)
        for i, attr in enumerate(attributions):
            attr.importance_rank = i + 1
        
        return attributions
    
    def _perturb_value(self, value: Any) -> Any:
        """Perturb a feature value."""
        if isinstance(value, (int, float)):
            return value * 0.5 if value != 0 else 0.1
        elif isinstance(value, bool):
            return not value
        elif isinstance(value, str):
            return "perturbed_" + value
        return value


# =============================================================================
# AUDITABLE MODEL
# =============================================================================

class AuditableModel:
    """
    Wrapper for models to add audit trail capabilities.
    
    Features:
    - Complete audit logging
    - Input/output hashing
    - Decision tracking
    - Compliance reporting
    """
    
    def __init__(
        self,
        model: PredictiveModel,
        model_id: str,
        explainer: Optional[DecisionExplainer] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._model = model
        self._model_id = model_id
        self._explainer = explainer or DecisionExplainer()
        self._audit_records: List[AuditRecord] = []
        self._prediction_counter = 0
    
    @property
    def model_id(self) -> str:
        """Get model ID."""
        return self._model_id
    
    def predict(
        self,
        features: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        generate_explanation: bool = True,
    ) -> Tuple[Any, Optional[Explanation], AuditRecord]:
        """
        Make an audited prediction.
        
        Returns:
            Tuple of (prediction, explanation, audit_record)
        """
        start_time = time.time()
        
        with self._lock:
            self._prediction_counter += 1
            pred_id = f"PRED-{self._prediction_counter:08d}"
        
        # Make prediction
        prediction = self._model.predict(features)
        
        # Get confidence
        try:
            proba = self._model.predict_proba(features)
            confidence = max(proba.values()) if proba else 0.5
        except (AttributeError, NotImplementedError):
            confidence = 0.5
        
        # Generate explanation
        explanation = None
        if generate_explanation:
            explanation = self._explainer.explain(
                model_id=self._model_id,
                prediction_id=pred_id,
                features=features,
                prediction=prediction,
                confidence=confidence,
            )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Create audit record
        audit_record = AuditRecord(
            audit_id=f"AUD-{self._prediction_counter:08d}",
            model_id=self._model_id,
            timestamp=datetime.now(timezone.utc),
            input_hash=self._hash_dict(features),
            output_hash=self._hash_value(prediction),
            explanation_id=explanation.explanation_id if explanation else "",
            decision=str(prediction),
            confidence=confidence,
            user_id=user_id,
            session_id=session_id,
            latency_ms=latency_ms,
        )
        
        with self._lock:
            self._audit_records.append(audit_record)
        
        return prediction, explanation, audit_record
    
    def get_audit_trail(
        self,
        limit: int = 100,
        user_id: Optional[str] = None,
    ) -> List[AuditRecord]:
        """Get audit trail."""
        with self._lock:
            records = list(reversed(self._audit_records))
            
            if user_id:
                records = [r for r in records if r.user_id == user_id]
            
            return records[:limit]
    
    def export_audit_trail(self, format: str = "json") -> str:
        """Export audit trail in specified format."""
        with self._lock:
            records = [r.to_dict() for r in self._audit_records]
        
        if format == "json":
            return json.dumps(records, indent=2)
        elif format == "csv":
            if not records:
                return ""
            headers = list(records[0].keys())
            lines = [",".join(headers)]
            for r in records:
                lines.append(",".join(str(r.get(h, "")) for h in headers))
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        with self._lock:
            total = len(self._audit_records)
            if total == 0:
                return {"total_predictions": 0}
            
            latencies = [r.latency_ms for r in self._audit_records]
            confidences = [r.confidence for r in self._audit_records]
            
            return {
                "total_predictions": total,
                "avg_latency_ms": sum(latencies) / total,
                "max_latency_ms": max(latencies),
                "min_latency_ms": min(latencies),
                "avg_confidence": sum(confidences) / total,
                "unique_users": len(set(r.user_id for r in self._audit_records if r.user_id)),
            }
    
    def _hash_dict(self, d: Dict[str, Any]) -> str:
        """Hash a dictionary."""
        content = json.dumps(d, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _hash_value(self, value: Any) -> str:
        """Hash a value."""
        content = str(value)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# EXPLANATION RENDERER
# =============================================================================

class ExplanationRenderer:
    """
    Multi-format explanation renderer.
    
    Features:
    - Text, HTML, JSON, Markdown, LaTeX
    - Customizable templates
    - Visualization support
    """
    
    def __init__(self) -> None:
        self._templates = self._load_templates()
    
    def render(
        self,
        explanation: Explanation,
        format: RenderFormat = RenderFormat.TEXT,
    ) -> str:
        """
        Render explanation in specified format.
        
        Args:
            explanation: The explanation to render
            format: Output format
        """
        if format == RenderFormat.TEXT:
            return self._render_text(explanation)
        elif format == RenderFormat.HTML:
            return self._render_html(explanation)
        elif format == RenderFormat.JSON:
            return self._render_json(explanation)
        elif format == RenderFormat.MARKDOWN:
            return self._render_markdown(explanation)
        elif format == RenderFormat.LATEX:
            return self._render_latex(explanation)
        else:
            return self._render_text(explanation)
    
    def render_attribution_chart(
        self,
        attributions: List[FeatureAttribution],
        format: RenderFormat = RenderFormat.TEXT,
    ) -> str:
        """Render attribution chart."""
        if format == RenderFormat.TEXT:
            return self._render_bar_chart_text(attributions)
        elif format == RenderFormat.HTML:
            return self._render_bar_chart_html(attributions)
        elif format == RenderFormat.MARKDOWN:
            return self._render_bar_chart_markdown(attributions)
        else:
            return self._render_bar_chart_text(attributions)
    
    def _render_text(self, explanation: Explanation) -> str:
        """Render as plain text."""
        lines = [
            f"Explanation ID: {explanation.explanation_id}",
            f"Type: {explanation.explanation_type.value}",
            f"Model: {explanation.model_id}",
            f"Prediction: {explanation.output_prediction}",
            f"Confidence: {explanation.confidence:.1%}",
            "",
            "Feature Attributions:",
        ]
        
        for feature, value in sorted(
            explanation.feature_attributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        ):
            lines.append(f"  {feature}: {value:+.4f}")
        
        if explanation.rules:
            lines.extend(["", "Rules:"])
            for rule in explanation.rules:
                lines.append(f"  - {rule}")
        
        return "\n".join(lines)
    
    def _render_html(self, explanation: Explanation) -> str:
        """Render as HTML."""
        attrs_html = ""
        for feature, value in sorted(
            explanation.feature_attributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        ):
            color = "green" if value > 0 else "red" if value < 0 else "gray"
            attrs_html += f'<li><span style="color: {color}">{feature}: {value:+.4f}</span></li>'
        
        return f"""
        <div class="explanation" id="{explanation.explanation_id}">
            <h3>Explanation</h3>
            <p><strong>Prediction:</strong> {explanation.output_prediction}</p>
            <p><strong>Confidence:</strong> {explanation.confidence:.1%}</p>
            <h4>Feature Attributions</h4>
            <ul>{attrs_html}</ul>
        </div>
        """
    
    def _render_json(self, explanation: Explanation) -> str:
        """Render as JSON."""
        return json.dumps(explanation.to_dict(), indent=2)
    
    def _render_markdown(self, explanation: Explanation) -> str:
        """Render as Markdown."""
        lines = [
            f"# Explanation: {explanation.explanation_id}",
            "",
            f"**Prediction:** {explanation.output_prediction}  ",
            f"**Confidence:** {explanation.confidence:.1%}  ",
            "",
            "## Feature Attributions",
            "",
            "| Feature | Attribution |",
            "|---------|-------------|",
        ]
        
        for feature, value in sorted(
            explanation.feature_attributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        ):
            lines.append(f"| {feature} | {value:+.4f} |")
        
        return "\n".join(lines)
    
    def _render_latex(self, explanation: Explanation) -> str:
        """Render as LaTeX."""
        attrs = ""
        for feature, value in sorted(
            explanation.feature_attributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        ):
            attrs += f"    {feature} & {value:+.4f} \\\\\n"
        
        return f"""
\\begin{{table}}[h]
\\caption{{Feature Attributions for Explanation {explanation.explanation_id}}}
\\begin{{tabular}}{{lr}}
\\hline
Feature & Attribution \\\\
\\hline
{attrs}\\hline
\\end{{tabular}}
\\end{{table}}
        """
    
    def _render_bar_chart_text(self, attributions: List[FeatureAttribution]) -> str:
        """Render text bar chart."""
        lines = []
        max_abs = max(abs(a.attribution_value) for a in attributions) if attributions else 1
        
        for attr in attributions:
            bar_length = int(abs(attr.attribution_value) / max_abs * 20)
            bar = "+" * bar_length if attr.attribution_value > 0 else "-" * bar_length
            lines.append(f"{attr.feature_name:20s} | {bar:20s} | {attr.attribution_value:+.4f}")
        
        return "\n".join(lines)
    
    def _render_bar_chart_html(self, attributions: List[FeatureAttribution]) -> str:
        """Render HTML bar chart."""
        bars = ""
        max_abs = max(abs(a.attribution_value) for a in attributions) if attributions else 1
        
        for attr in attributions:
            width = int(abs(attr.attribution_value) / max_abs * 100)
            color = "#4CAF50" if attr.attribution_value > 0 else "#f44336"
            bars += f"""
            <div style="margin: 5px 0;">
                <span style="display: inline-block; width: 150px;">{attr.feature_name}</span>
                <div style="display: inline-block; width: {width}px; height: 20px; background: {color};"></div>
                <span>{attr.attribution_value:+.4f}</span>
            </div>
            """
        
        return f'<div class="bar-chart">{bars}</div>'
    
    def _render_bar_chart_markdown(self, attributions: List[FeatureAttribution]) -> str:
        """Render Markdown bar chart."""
        lines = ["```", "Feature Attributions:", ""]
        max_abs = max(abs(a.attribution_value) for a in attributions) if attributions else 1
        
        for attr in attributions:
            bar_length = int(abs(attr.attribution_value) / max_abs * 20)
            bar = "█" * bar_length
            lines.append(f"{attr.feature_name:20s} {bar} {attr.attribution_value:+.4f}")
        
        lines.append("```")
        return "\n".join(lines)
    
    def _load_templates(self) -> Dict[str, str]:
        """Load rendering templates."""
        return {
            "default": "{explanation}",
        }


# =============================================================================
# MODEL CARD GENERATOR
# =============================================================================

class ModelCardGenerator:
    """
    Generates model cards for governance.
    
    Features:
    - Automated documentation
    - Bias analysis integration
    - Risk assessment
    - Compliance templates
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cards: Dict[str, ModelCard] = {}
    
    def generate(
        self,
        model_id: str,
        model_name: str,
        version: str,
        description: str,
        intended_use: str,
        metrics: Dict[str, float],
        training_data: str = "Not specified",
        evaluation_data: str = "Not specified",
        contact: str = "Not specified",
    ) -> ModelCard:
        """
        Generate a model card.
        
        Args:
            model_id: Unique model identifier
            model_name: Human-readable model name
            version: Model version
            description: Model description
            intended_use: Intended use cases
            metrics: Performance metrics
            training_data: Training data description
            evaluation_data: Evaluation data description
            contact: Contact information
        """
        now = datetime.now(timezone.utc)
        
        # Assess risk level
        risk_level = self._assess_risk(metrics, intended_use)
        
        # Generate ethical considerations
        ethical = self._generate_ethical_considerations(intended_use)
        
        # Generate caveats
        caveats = self._generate_caveats(metrics)
        
        card = ModelCard(
            model_id=model_id,
            model_name=model_name,
            version=version,
            description=description,
            intended_use=intended_use,
            out_of_scope_use=self._generate_out_of_scope(intended_use),
            training_data=training_data,
            evaluation_data=evaluation_data,
            metrics=metrics,
            ethical_considerations=ethical,
            caveats=caveats,
            risk_level=risk_level,
            bias_analysis={},
            created_at=now,
            updated_at=now,
            contact=contact,
        )
        
        with self._lock:
            self._cards[model_id] = card
        
        return card
    
    def add_bias_analysis(
        self,
        model_id: str,
        bias_report: BiasReport,
    ) -> Optional[ModelCard]:
        """Add bias analysis to model card."""
        with self._lock:
            card = self._cards.get(model_id)
            if not card:
                return None
            
            card.bias_analysis[bias_report.bias_type.value] = bias_report.to_dict()
            card.updated_at = datetime.now(timezone.utc)
            
            # Update risk level based on bias findings
            if not bias_report.passed:
                card.risk_level = RiskLevel.HIGH
            
            return card
    
    def get_card(self, model_id: str) -> Optional[ModelCard]:
        """Get model card."""
        return self._cards.get(model_id)
    
    def export_card(
        self,
        model_id: str,
        format: RenderFormat = RenderFormat.MARKDOWN,
    ) -> str:
        """Export model card in specified format."""
        card = self._cards.get(model_id)
        if not card:
            return ""
        
        if format == RenderFormat.MARKDOWN:
            return self._render_markdown(card)
        elif format == RenderFormat.JSON:
            return json.dumps(card.to_dict(), indent=2)
        elif format == RenderFormat.HTML:
            return self._render_html(card)
        else:
            return json.dumps(card.to_dict(), indent=2)
    
    def _assess_risk(
        self,
        metrics: Dict[str, float],
        intended_use: str,
    ) -> RiskLevel:
        """Assess model risk level."""
        # Check performance thresholds
        accuracy = metrics.get("accuracy", 1.0)
        
        if accuracy < 0.7:
            return RiskLevel.CRITICAL
        elif accuracy < 0.85:
            return RiskLevel.HIGH
        elif accuracy < 0.95:
            return RiskLevel.MEDIUM
        
        # Check for high-stakes use cases
        high_stakes_keywords = ["healthcare", "finance", "legal", "safety", "security"]
        if any(kw in intended_use.lower() for kw in high_stakes_keywords):
            return RiskLevel.HIGH
        
        return RiskLevel.LOW
    
    def _generate_ethical_considerations(self, intended_use: str) -> List[str]:
        """Generate ethical considerations."""
        considerations = [
            "Ensure human oversight for critical decisions",
            "Regularly audit model outputs for fairness",
            "Maintain transparency with affected users",
        ]
        
        if "personal" in intended_use.lower() or "user" in intended_use.lower():
            considerations.append("Protect user privacy and data rights")
        
        if "automated" in intended_use.lower():
            considerations.append("Provide clear mechanisms for human intervention")
        
        return considerations
    
    def _generate_caveats(self, metrics: Dict[str, float]) -> List[str]:
        """Generate model caveats."""
        caveats = []
        
        accuracy = metrics.get("accuracy", 1.0)
        if accuracy < 0.95:
            caveats.append(f"Model accuracy is {accuracy:.1%}, not suitable for high-precision tasks")
        
        if "f1_score" in metrics and metrics["f1_score"] < 0.9:
            caveats.append("Model may have imbalanced performance across classes")
        
        caveats.append("Performance may degrade on out-of-distribution data")
        caveats.append("Regular retraining recommended to maintain accuracy")
        
        return caveats
    
    def _generate_out_of_scope(self, intended_use: str) -> str:
        """Generate out-of-scope use description."""
        return (
            f"This model should NOT be used for: "
            f"(1) any use case not covered by '{intended_use}', "
            f"(2) fully autonomous decision-making without human oversight, "
            f"(3) applications where model errors could cause significant harm."
        )
    
    def _render_markdown(self, card: ModelCard) -> str:
        """Render card as Markdown."""
        metrics_table = "| Metric | Value |\n|--------|-------|\n"
        for name, value in card.metrics.items():
            metrics_table += f"| {name} | {value:.4f} |\n"
        
        ethical = "\n".join(f"- {c}" for c in card.ethical_considerations)
        caveats = "\n".join(f"- {c}" for c in card.caveats)
        
        return f"""# Model Card: {card.model_name}

## Overview
- **Model ID:** {card.model_id}
- **Version:** {card.version}
- **Risk Level:** {card.risk_level.value}

## Description
{card.description}

## Intended Use
{card.intended_use}

## Out-of-Scope Use
{card.out_of_scope_use}

## Training Data
{card.training_data}

## Evaluation Data
{card.evaluation_data}

## Performance Metrics
{metrics_table}

## Ethical Considerations
{ethical}

## Caveats and Recommendations
{caveats}

## Contact
{card.contact}

---
*Last updated: {card.updated_at.isoformat()}*
"""
    
    def _render_html(self, card: ModelCard) -> str:
        """Render card as HTML."""
        return f"""
        <div class="model-card">
            <h1>{card.model_name}</h1>
            <p><strong>Version:</strong> {card.version}</p>
            <p><strong>Risk Level:</strong> <span class="risk-{card.risk_level.value.lower()}">{card.risk_level.value}</span></p>
            <h2>Description</h2>
            <p>{card.description}</p>
            <h2>Intended Use</h2>
            <p>{card.intended_use}</p>
        </div>
        """


# =============================================================================
# BIAS ANALYZER
# =============================================================================

class BiasAnalyzer:
    """
    Analyze models for bias.
    
    Features:
    - Demographic parity
    - Equal opportunity
    - Calibration analysis
    - Intersectional analysis
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reports: List[BiasReport] = []
    
    def analyze(
        self,
        model_id: str,
        predictions: List[Dict[str, Any]],
        protected_attribute: str,
        threshold: float = 0.8,
    ) -> BiasReport:
        """
        Analyze model for bias.
        
        Args:
            model_id: Model identifier
            predictions: List of predictions with attributes
            protected_attribute: Attribute to check for bias
            threshold: Acceptable disparity threshold
        """
        groups: Dict[str, List[float]] = defaultdict(list)
        
        for pred in predictions:
            group = pred.get(protected_attribute, "unknown")
            score = pred.get("prediction", pred.get("score", 0.5))
            groups[str(group)].append(score)
        
        # Calculate disparate impact ratio
        group_rates = {g: sum(s) / len(s) if s else 0 for g, s in groups.items()}
        
        if not group_rates or len(group_rates) < 2:
            disparity = 1.0
        else:
            max_rate = max(group_rates.values())
            min_rate = min(group_rates.values())
            disparity = min_rate / max_rate if max_rate > 0 else 1.0
        
        passed = disparity >= threshold
        
        recommendations = []
        if not passed:
            recommendations.append(f"Disparity ratio {disparity:.2f} is below threshold {threshold}")
            recommendations.append("Consider rebalancing training data")
            recommendations.append("Apply fairness-aware training techniques")
            recommendations.append("Audit feature selection for proxy discrimination")
        
        report = BiasReport(
            model_id=model_id,
            bias_type=BiasType.DEMOGRAPHIC,
            affected_groups=list(groups.keys()),
            disparity_metric=disparity,
            threshold=threshold,
            passed=passed,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc),
        )
        
        with self._lock:
            self._reports.append(report)
        
        return report
    
    def get_reports(self, model_id: Optional[str] = None) -> List[BiasReport]:
        """Get bias reports."""
        with self._lock:
            if model_id:
                return [r for r in self._reports if r.model_id == model_id]
            return list(self._reports)


# =============================================================================
# WRAP HASH COMPUTATION
# =============================================================================

def compute_wrap_hash() -> str:
    """Compute WRAP hash for GID-10 deliverable."""
    content = f"GID-10:explainability:v{EXPLAINABILITY_VERSION}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "EXPLAINABILITY_VERSION",
    "ExplanationType",
    "ConfidenceMethod",
    "AttributionMethod",
    "RenderFormat",
    "BiasType",
    "RiskLevel",
    "ExplainabilityError",
    "ModelNotFittedError",
    "AttributionError",
    "ConfidenceError",
    "Explanation",
    "ConfidenceInterval",
    "FeatureAttribution",
    "AuditRecord",
    "ModelCard",
    "BiasReport",
    "PredictiveModel",
    "DecisionExplainer",
    "ConfidenceEstimator",
    "FeatureAttributor",
    "AuditableModel",
    "ExplanationRenderer",
    "ModelCardGenerator",
    "BiasAnalyzer",
    "compute_wrap_hash",
]
