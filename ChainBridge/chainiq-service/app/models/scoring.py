"""
Scoring response models for ChainIQ ML endpoints.

Defines the standard response format for risk and anomaly scoring,
including explainability features.
"""

from typing import List

from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    """
    Represents a single feature's contribution to a score.

    Used for model explainability: each contribution explains why
    a particular feature influenced the final score.
    """

    feature: str = Field(description="Name of the feature that contributed to the score")
    reason: str = Field(description="Human-readable explanation of how this feature influenced the score")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "feature": "eta_deviation_hours",
                "reason": "Shipment is 4.5 hours behind schedule, indicating elevated risk",
            }
        }


class RiskScoreResponse(BaseModel):
    """
    Response model for risk scoring endpoint.

    Returns a risk score [0,1] where higher values indicate higher risk,
    along with explainability features and model version.
    """

    score: float = Field(
        description="Risk score between 0 (low risk) and 1 (high risk)",
        ge=0.0,
        le=1.0,
    )
    explanation: List[FeatureContribution] = Field(description="List of feature contributions explaining the score")
    model_version: str = Field(description="Version identifier of the risk scoring model")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "score": 0.81,
                "explanation": [
                    {
                        "feature": "eta_deviation_hours",
                        "reason": "Shipment is 4.5 hours behind schedule, indicating elevated risk",
                    },
                    {
                        "feature": "missing_required_docs",
                        "reason": "1 required document is missing, increasing documentation risk",
                    },
                ],
                "model_version": "risk_stub_v0.1",
            }
        }


class AnomalyScoreResponse(BaseModel):
    """
    Response model for anomaly detection endpoint.

    Returns an anomaly score [0,1] where higher values indicate
    stronger anomalous behavior, along with explanations.
    """

    score: float = Field(
        description="Anomaly score between 0 (normal) and 1 (highly anomalous)",
        ge=0.0,
        le=1.0,
    )
    explanation: List[FeatureContribution] = Field(description="List of feature contributions explaining the anomaly score")
    model_version: str = Field(description="Version identifier of the anomaly detection model")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "score": 0.37,
                "explanation": [
                    {
                        "feature": "max_route_deviation_km",
                        "reason": "Route deviation of 12.3 km is within normal range for this corridor",
                    },
                    {
                        "feature": "corridor_disruption_index_90d",
                        "reason": "Corridor has below-average disruption levels recently",
                    },
                ],
                "model_version": "anomaly_stub_v0.1",
            }
        }
