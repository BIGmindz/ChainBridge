"""
ChainIQ ML module.

Provides abstract base classes and contracts for risk and anomaly models.
Includes model registry for singleton model access.
"""

from typing import Optional

from .base import BaseAnomalyModel, BaseRiskModel, ModelPrediction
from .dummy_models import DummyAnomalyModel, DummyRiskModel

__all__ = [
    "BaseRiskModel",
    "BaseAnomalyModel",
    "ModelPrediction",
    "DummyRiskModel",
    "DummyAnomalyModel",
    "get_risk_model",
    "get_anomaly_model",
]

# Module-level singletons for model instances
_risk_model: Optional[BaseRiskModel] = None
_anomaly_model: Optional[BaseAnomalyModel] = None


def get_risk_model() -> BaseRiskModel:
    """
    Get the current risk model instance (singleton).

    Returns the same DummyRiskModel instance on every call.
    In future versions, this can be modified to return trained models
    based on configuration or feature flags.

    Returns:
        BaseRiskModel: Current risk model implementation
    """
    global _risk_model
    if _risk_model is None:
        _risk_model = DummyRiskModel()
    return _risk_model


def get_anomaly_model() -> BaseAnomalyModel:
    """
    Get the current anomaly model instance (singleton).

    Returns the same DummyAnomalyModel instance on every call.
    In future versions, this can be modified to return trained models
    based on configuration or feature flags.

    Returns:
        BaseAnomalyModel: Current anomaly model implementation
    """
    global _anomaly_model
    if _anomaly_model is None:
        _anomaly_model = DummyAnomalyModel()
    return _anomaly_model
