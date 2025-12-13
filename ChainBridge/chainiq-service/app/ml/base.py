"""
Base classes and interfaces for ChainIQ ML models.

Defines abstract contracts that all risk and anomaly models must implement.
These interfaces ensure consistent behavior, explainability, and versioning
across all ML models deployed in ChainIQ.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel

from app.models.features import ShipmentFeaturesV0
from app.models.scoring import FeatureContribution


class ModelPrediction(BaseModel):
    """
    Standard prediction output from any ChainIQ ML model.

    Combines a numeric score with explanations (feature contributions)
    and model version metadata for traceability.
    """

    score: float
    explanation: List[FeatureContribution]
    model_version: str


class BaseRiskModel(ABC):
    """
    Abstract base class for ChainIQ risk models.

    All risk models must:
    - Accept ShipmentFeaturesV0 as input
    - Return ModelPrediction with score in [0, 1]
    - Be deterministic (same input -> same output)
    - Have no side effects (pure functions)
    - Provide explainability via feature contributions

    Implementations must set:
    - model_id: Short identifier (e.g., 'risk_glassbox')
    - model_version: Semantic version (e.g., '1.0.0')
    """

    model_id: str = "risk_base"
    model_version: str = "0.0.0"

    @abstractmethod
    def predict(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """
        Compute a risk score and explanation for a single shipment.

        Args:
            features: Fully populated ShipmentFeaturesV0 instance

        Returns:
            ModelPrediction with:
            - score: Risk score in [0.0, 1.0], higher = higher risk
            - explanation: List of FeatureContribution objects
            - model_version: Version string for this model

        Raises:
            ValueError: If features are invalid or missing required fields
        """
        raise NotImplementedError


class BaseAnomalyModel(ABC):
    """
    Abstract base class for ChainIQ anomaly models.

    All anomaly models must:
    - Accept ShipmentFeaturesV0 as input
    - Return ModelPrediction with score in [0, 1]
    - Be deterministic (same input -> same output)
    - Have no side effects (pure functions)
    - Provide explainability via feature contributions

    Implementations must set:
    - model_id: Short identifier (e.g., 'anomaly_density')
    - model_version: Semantic version (e.g., '1.0.0')
    """

    model_id: str = "anomaly_base"
    model_version: str = "0.0.0"

    @abstractmethod
    def predict(self, features: ShipmentFeaturesV0) -> ModelPrediction:
        """
        Compute an anomaly score and explanation for a single shipment.

        Args:
            features: Fully populated ShipmentFeaturesV0 instance

        Returns:
            ModelPrediction with:
            - score: Anomaly score in [0.0, 1.0], higher = more anomalous
            - explanation: List of FeatureContribution objects
            - model_version: Version string for this model

        Raises:
            ValueError: If features are invalid or missing required fields
        """
        raise NotImplementedError
