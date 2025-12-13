"""
Dummy/stub ML models for testing and development.

These models provide deterministic, rule-based predictions that follow
the BaseRiskModel and BaseAnomalyModel contracts. They are useful for:

1. Integration testing (verify API contracts work end-to-end)
2. Baseline comparisons (real ML models should beat these simple rules)
3. Fallback implementations (if real model fails, fall back to dummy)

WARNING: These are NOT production models. They use naive heuristics
and should be replaced with trained ML models in production.
"""

from typing import List

from app.ml.base import BaseAnomalyModel, BaseRiskModel, ModelPrediction
from app.models.features import ShipmentFeaturesV0
from app.models.scoring import FeatureContribution


class DummyRiskModel(BaseRiskModel):
    """
    Deterministic rule-based risk model for testing.

    Scoring logic:
    - Base score: 0.2 (low baseline risk)
    - +0.3 if shipment is delayed
    - +0.3 if shipper has prior losses
    - Capped at 1.0

    This simple model establishes a floor for real ML models to beat.
    """

    model_id = "risk_dummy"
    model_version = "0.1.0"

    def predict(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """Compute deterministic risk score based on delay and prior loss flags."""
        base_score = 0.2

        # Increase risk if delayed
        if features.delay_flag:
            base_score += 0.3

        # Increase risk if prior losses exist
        if features.prior_losses_flag:
            base_score += 0.3

        # Cap at 1.0
        score = max(0.0, min(1.0, base_score))

        # Build simple explanations
        explanation: List[FeatureContribution] = [
            FeatureContribution(
                feature="delay_flag",
                reason="Increases risk when shipment is significantly delayed.",
            ),
            FeatureContribution(
                feature="prior_losses_flag",
                reason="Increases risk when shipper has prior losses.",
            ),
        ]

        return ModelPrediction(
            score=score,
            explanation=explanation,
            model_version=self.model_version,
        )


class DummyAnomalyModel(BaseAnomalyModel):
    """
    Deterministic rule-based anomaly model for testing.

    Scoring logic:
    - Base score: 0.1 (low baseline anomaly)
    - +0.4 if max single dwell > 12 hours
    - +0.3 if ETA deviation > 6 hours
    - Capped at 1.0

    This simple model flags shipments with unusual dwell or timing patterns.
    """

    model_id = "anomaly_dummy"
    model_version = "0.1.0"

    def predict(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """Compute deterministic anomaly score based on dwell and ETA deviation."""
        base_score = 0.1

        # Flag unusual dwell times
        if features.max_single_dwell_hours > 12:
            base_score += 0.4

        # Flag large ETA deviations
        if features.eta_deviation_hours > 6:
            base_score += 0.3

        # Cap at 1.0
        score = max(0.0, min(1.0, base_score))

        # Build simple explanations
        explanation: List[FeatureContribution] = [
            FeatureContribution(
                feature="max_single_dwell_hours",
                reason="Long dwell times are uncommon for this corridor.",
            ),
            FeatureContribution(
                feature="eta_deviation_hours",
                reason="Large positive deviation from planned ETA indicates unusual transit.",
            ),
        ]

        return ModelPrediction(
            score=score,
            explanation=explanation,
            model_version=self.model_version,
        )
