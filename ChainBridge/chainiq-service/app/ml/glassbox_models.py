"""
GlassBox ML Models for ChainIQ

Provides interpretable, "no black box" risk and anomaly models using
Explainable Boosting Machines (EBMs) from the `interpret` library.

Key Properties:
- INTERPRETABLE: Every prediction comes with clear feature contributions
- DETERMINISTIC: Same input → same output (no random seeds at inference)
- AUDITABLE: Feature importance is global AND local (per-prediction)
- VERSIONED: All model artifacts include version metadata

EBM Reference:
- https://interpret.ml/docs/ebm.html
- Uses generalized additive models (GAMs) with automatic interaction detection
- Comparable accuracy to gradient boosting, but fully interpretable

Production Notes:
- Models are lazy-loaded (heavy dependencies only when needed)
- Fallback to DummyModel if EBM fails to load
- All predictions bounded to [0, 1] range
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from app.ml.base import BaseAnomalyModel, BaseRiskModel, ModelPrediction
from app.ml.preprocessing import extract_feature_vector, get_feature_names
from app.models.features import ShipmentFeaturesV0
from app.models.scoring import FeatureContribution

logger = logging.getLogger(__name__)


class GlassBoxRiskModel(BaseRiskModel):
    """
    Interpretable risk model using Explainable Boosting Machine (EBM).

    NO BLACK BOX: Every prediction includes:
    - Global feature importance (model-level)
    - Local feature contributions (per-prediction)
    - Clear reasoning for each score

    Model Versioning:
    - model_id: 'risk_glassbox'
    - model_version: Semantic version (e.g., '1.0.0')
    - Artifacts stored in ml_models/ with version suffix

    Usage:
        >>> model = GlassBoxRiskModel(model_path="ml_models/risk_glassbox_v1.0.0.pkl")
        >>> prediction = model.predict(features)
        >>> print(prediction.score, prediction.explanation)
    """

    model_id = "risk_glassbox"
    model_version = "1.0.0"

    def __init__(
        self,
        model_path: Optional[str] = None,
        *,
        fallback_on_error: bool = True,
    ):
        """
        Initialize GlassBox risk model.

        Args:
            model_path: Path to trained EBM model (.pkl file)
            fallback_on_error: If True, use rule-based fallback when model unavailable
        """
        self.model_path = Path(model_path) if model_path else None
        self.fallback_on_error = fallback_on_error
        self._ebm_model = None
        self._feature_names: List[str] = get_feature_names()
        self._loaded = False
        self._load_error: Optional[str] = None

    def _lazy_load(self) -> bool:
        """
        Lazy-load EBM model on first prediction.

        Returns:
            True if model loaded successfully, False otherwise
        """
        if self._loaded:
            return self._ebm_model is not None

        self._loaded = True

        if self.model_path is None or not self.model_path.exists():
            self._load_error = f"Model file not found: {self.model_path}"
            logger.warning(f"GlassBoxRiskModel: {self._load_error}")
            return False

        try:
            import pickle

            with open(self.model_path, "rb") as f:
                self._ebm_model = pickle.load(f)

            logger.info(f"GlassBoxRiskModel: Loaded from {self.model_path}")
            return True

        except Exception as e:
            self._load_error = f"Failed to load model: {e}"
            logger.error(f"GlassBoxRiskModel: {self._load_error}")
            return False

    def predict(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """
        Compute interpretable risk score with feature contributions.

        Args:
            features: Shipment feature vector

        Returns:
            ModelPrediction with:
            - score: Risk probability in [0, 1]
            - explanation: Per-feature contributions to score
            - model_version: Version string
        """
        # Extract feature vector
        feature_vector = extract_feature_vector(features)

        # Try to use EBM model
        if self._lazy_load() and self._ebm_model is not None:
            return self._predict_with_ebm(feature_vector, features)

        # Fallback to rule-based scoring
        if self.fallback_on_error:
            return self._predict_fallback(features)

        raise RuntimeError(f"GlassBoxRiskModel not available: {self._load_error}")

    def _predict_with_ebm(
        self,
        feature_vector: List[float],
        features: ShipmentFeaturesV0,
    ) -> ModelPrediction:
        """
        Predict using trained EBM model with local explanations.

        EBM provides per-feature additive contributions that sum to the prediction.
        """
        import numpy as np

        # Reshape for sklearn API
        X = np.array([feature_vector])

        # Get probability score
        proba = self._ebm_model.predict_proba(X)[:, 1][0]
        score = float(np.clip(proba, 0.0, 1.0))

        # Extract local explanations (EBM feature contributions)
        explanation = self._extract_ebm_explanation(X, features)

        return ModelPrediction(
            score=score,
            explanation=explanation,
            model_version=self.model_version,
        )

    def _extract_ebm_explanation(
        self,
        X,
        features: ShipmentFeaturesV0,
    ) -> List[FeatureContribution]:
        """
        Extract per-feature contributions from EBM model.

        EBM is a GAM: f(x) = intercept + f1(x1) + f2(x2) + ... + interactions
        Each fi(xi) gives the contribution of feature i.
        """
        explanations: List[FeatureContribution] = []

        try:
            # Get local explanation from interpret library
            local_exp = self._ebm_model.explain_local(X)

            # Extract feature contributions
            contrib_data = local_exp._internal_obj["specific"][0]
            names = contrib_data["names"]
            scores = contrib_data["scores"]

            # Sort by absolute contribution (most important first)
            pairs = list(zip(names, scores))
            pairs.sort(key=lambda x: abs(x[1]), reverse=True)

            # Take top 10 contributors
            for name, contrib in pairs[:10]:
                direction = "increases" if contrib > 0 else "decreases"
                explanations.append(
                    FeatureContribution(
                        feature=str(name),
                        reason=f"{name} {direction} risk by {abs(contrib):.3f}",
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to extract EBM explanations: {e}")
            # Return minimal explanation
            explanations = [
                FeatureContribution(
                    feature="model_score",
                    reason="Score computed by GlassBox EBM model",
                )
            ]

        return explanations

    def _predict_fallback(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """
        Rule-based fallback when EBM model is unavailable.

        Uses interpretable rules that can be audited:
        - delay_flag adds 0.25 risk
        - prior_losses_flag adds 0.25 risk
        - low shipper on-time rate (<80%) adds 0.15 risk
        - high ETA deviation (>8h) adds 0.15 risk
        - large dwell time (>24h) adds 0.1 risk
        """
        score = 0.1  # Base risk
        explanations: List[FeatureContribution] = []

        # Rule 1: Delay flag
        if features.delay_flag:
            score += 0.25
            explanations.append(
                FeatureContribution(
                    feature="delay_flag",
                    reason="Shipment is delayed (delay_flag=1), adds 0.25 risk",
                )
            )

        # Rule 2: Prior losses
        if features.prior_losses_flag:
            score += 0.25
            explanations.append(
                FeatureContribution(
                    feature="prior_losses_flag",
                    reason="Shipper has prior losses (prior_losses_flag=1), adds 0.25 risk",
                )
            )

        # Rule 3: Low shipper on-time rate
        if features.shipper_on_time_pct_90d < 0.80:
            score += 0.15
            explanations.append(
                FeatureContribution(
                    feature="shipper_on_time_pct_90d",
                    reason=f"Low shipper on-time rate ({features.shipper_on_time_pct_90d:.0%}), adds 0.15 risk",
                )
            )

        # Rule 4: High ETA deviation
        if features.eta_deviation_hours > 8:
            score += 0.15
            explanations.append(
                FeatureContribution(
                    feature="eta_deviation_hours",
                    reason=f"High ETA deviation ({features.eta_deviation_hours:.1f}h > 8h), adds 0.15 risk",
                )
            )

        # Rule 5: Large dwell time
        if features.total_dwell_hours > 24:
            score += 0.10
            explanations.append(
                FeatureContribution(
                    feature="total_dwell_hours",
                    reason=f"Extended dwell time ({features.total_dwell_hours:.1f}h > 24h), adds 0.10 risk",
                )
            )

        # If no risk factors, note the low-risk status
        if not explanations:
            explanations.append(
                FeatureContribution(
                    feature="baseline",
                    reason="No significant risk factors detected, baseline risk only",
                )
            )

        return ModelPrediction(
            score=min(score, 1.0),
            explanation=explanations,
            model_version=f"{self.model_version}-fallback",
        )

    def get_feature_importance(self) -> List[tuple]:
        """
        Get global feature importance from trained EBM.

        Returns:
            List of (feature_name, importance_score) tuples, sorted by importance
        """
        if not self._lazy_load() or self._ebm_model is None:
            return []

        try:
            global_exp = self._ebm_model.explain_global()
            names = global_exp._internal_obj["overall"]["names"]
            scores = global_exp._internal_obj["overall"]["scores"]

            pairs = list(zip(names, scores))
            pairs.sort(key=lambda x: abs(x[1]), reverse=True)
            return pairs

        except Exception as e:
            logger.error(f"Failed to get feature importance: {e}")
            return []


class GlassBoxAnomalyModel(BaseAnomalyModel):
    """
    Interpretable anomaly model using distance-based scoring.

    NO BLACK BOX: Every prediction includes:
    - Feature-level deviations from normal ranges
    - Clear reasoning for anomaly flags

    Approach:
    - Learn feature distributions from training data
    - Score based on how far each feature deviates from learned norms
    - Use robust statistics (median, MAD) for outlier resistance
    """

    model_id = "anomaly_glassbox"
    model_version = "1.0.0"

    def __init__(
        self,
        model_path: Optional[str] = None,
        *,
        fallback_on_error: bool = True,
    ):
        """
        Initialize GlassBox anomaly model.

        Args:
            model_path: Path to trained model (.pkl file)
            fallback_on_error: If True, use rule-based fallback when model unavailable
        """
        self.model_path = Path(model_path) if model_path else None
        self.fallback_on_error = fallback_on_error
        self._stats = None
        self._loaded = False
        self._load_error: Optional[str] = None

    def _lazy_load(self) -> bool:
        """Lazy-load learned statistics on first prediction."""
        if self._loaded:
            return self._stats is not None

        self._loaded = True

        if self.model_path is None or not self.model_path.exists():
            self._load_error = f"Model file not found: {self.model_path}"
            logger.warning(f"GlassBoxAnomalyModel: {self._load_error}")
            return False

        try:
            import pickle

            with open(self.model_path, "rb") as f:
                self._stats = pickle.load(f)

            logger.info(f"GlassBoxAnomalyModel: Loaded from {self.model_path}")
            return True

        except Exception as e:
            self._load_error = f"Failed to load model: {e}"
            logger.error(f"GlassBoxAnomalyModel: {self._load_error}")
            return False

    def predict(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """
        Compute interpretable anomaly score with feature deviations.
        """
        if self._lazy_load() and self._stats is not None:
            return self._predict_with_stats(features)

        if self.fallback_on_error:
            return self._predict_fallback(features)

        raise RuntimeError(f"GlassBoxAnomalyModel not available: {self._load_error}")

    def _predict_with_stats(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """Predict using learned feature statistics."""
        import numpy as np

        feature_vector = extract_feature_vector(features)
        feature_names = get_feature_names()

        deviations = []
        explanations: List[FeatureContribution] = []

        for i, (name, value) in enumerate(zip(feature_names, feature_vector)):
            if name in self._stats:
                median = self._stats[name]["median"]
                mad = self._stats[name]["mad"]

                if mad > 0:
                    # Modified Z-score using MAD
                    z = abs(value - median) / (1.4826 * mad)
                    deviations.append(min(z / 5.0, 1.0))  # Normalize to [0, 1]

                    if z > 3.0:
                        explanations.append(
                            FeatureContribution(
                                feature=name,
                                reason=f"{name}={value:.2f} deviates {z:.1f} MADs from median ({median:.2f})",
                            )
                        )

        # Aggregate: max deviation with some weight on count
        if deviations:
            score = float(np.clip(max(deviations) * 0.7 + np.mean(deviations) * 0.3, 0.0, 1.0))
        else:
            score = 0.1

        if not explanations:
            explanations.append(
                FeatureContribution(
                    feature="baseline",
                    reason="All features within expected ranges",
                )
            )

        return ModelPrediction(
            score=score,
            explanation=explanations,
            model_version=self.model_version,
        )

    def _predict_fallback(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """Rule-based fallback for anomaly detection."""
        score = 0.1
        explanations: List[FeatureContribution] = []

        # Check for unusual dwell times
        if features.max_single_dwell_hours > 24:
            score += 0.3
            explanations.append(
                FeatureContribution(
                    feature="max_single_dwell_hours",
                    reason=f"Unusually long dwell ({features.max_single_dwell_hours:.1f}h > 24h)",
                )
            )

        # Check for route deviations
        if features.num_route_deviations > 5:
            score += 0.25
            explanations.append(
                FeatureContribution(
                    feature="num_route_deviations",
                    reason=f"Many route deviations ({features.num_route_deviations} > 5)",
                )
            )

        # Check for sensor issues
        if features.sensor_uptime_pct < 0.5:
            score += 0.2
            explanations.append(
                FeatureContribution(
                    feature="sensor_uptime_pct",
                    reason=f"Low sensor uptime ({features.sensor_uptime_pct:.0%} < 50%)",
                )
            )

        # Check for documentation anomalies
        if features.missing_required_docs > 3:
            score += 0.15
            explanations.append(
                FeatureContribution(
                    feature="missing_required_docs",
                    reason=f"Many missing docs ({features.missing_required_docs} > 3)",
                )
            )

        if not explanations:
            explanations.append(
                FeatureContribution(
                    feature="baseline",
                    reason="No significant anomalies detected",
                )
            )

        return ModelPrediction(
            score=min(score, 1.0),
            explanation=explanations,
            model_version=f"{self.model_version}-fallback",
        )
