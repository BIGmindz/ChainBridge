"""
ChainIQ ML module.

Provides abstract base classes and contracts for risk and anomaly models.
Includes model registry for singleton model access.

Model Types:
- DummyRiskModel/DummyAnomalyModel: Rule-based, always available (production default)
- GlassBoxRiskModel/GlassBoxAnomalyModel: Interpretable ML (EBM), requires trained artifacts

Usage:
    from app.ml import get_risk_model, get_glassbox_risk_model

    # Production default (always works)
    model = get_risk_model()

    # Interpretable ML (requires training)
    glassbox = get_glassbox_risk_model()
"""

import logging
from pathlib import Path
from typing import Optional

from .base import BaseAnomalyModel, BaseRiskModel, ModelPrediction
from .dummy_models import DummyAnomalyModel, DummyRiskModel

logger = logging.getLogger(__name__)

__all__ = [
    "BaseRiskModel",
    "BaseAnomalyModel",
    "ModelPrediction",
    "DummyRiskModel",
    "DummyAnomalyModel",
    "get_risk_model",
    "get_anomaly_model",
    "get_glassbox_risk_model",
    "get_glassbox_anomaly_model",
    "MODEL_REGISTRY",
]

# Module-level singletons for model instances
_risk_model: Optional[BaseRiskModel] = None
_anomaly_model: Optional[BaseAnomalyModel] = None
_glassbox_risk_model: Optional[BaseRiskModel] = None
_glassbox_anomaly_model: Optional[BaseAnomalyModel] = None

# Default model paths (relative to chainiq-service root)
DEFAULT_GLASSBOX_RISK_PATH = Path(__file__).parent.parent.parent / "ml_models" / "risk_glassbox_v1.0.0.pkl"
DEFAULT_GLASSBOX_ANOMALY_PATH = Path(__file__).parent.parent.parent / "ml_models" / "anomaly_glassbox_v1.0.0.pkl"


def get_risk_model() -> BaseRiskModel:
    """
    Get the production risk model instance (singleton).

    Returns DummyRiskModel which is always available (no external dependencies).
    Use for production scoring where availability > accuracy.

    Returns:
        BaseRiskModel: DummyRiskModel instance
    """
    global _risk_model
    if _risk_model is None:
        _risk_model = DummyRiskModel()
    return _risk_model


def get_anomaly_model() -> BaseAnomalyModel:
    """
    Get the production anomaly model instance (singleton).

    Returns DummyAnomalyModel which is always available (no external dependencies).
    Use for production scoring where availability > accuracy.

    Returns:
        BaseAnomalyModel: DummyAnomalyModel instance
    """
    global _anomaly_model
    if _anomaly_model is None:
        _anomaly_model = DummyAnomalyModel()
    return _anomaly_model


def get_glassbox_risk_model(
    model_path: Optional[str] = None,
    *,
    fallback_on_error: bool = True,
) -> BaseRiskModel:
    """
    Get the GlassBox risk model instance (singleton).

    GlassBox models are INTERPRETABLE:
    - Every prediction includes feature contributions
    - No "black box" final decision
    - Supports local + global explanations

    Args:
        model_path: Path to trained model. Uses default if None.
        fallback_on_error: If True, use rule-based fallback when model unavailable.

    Returns:
        BaseRiskModel: GlassBoxRiskModel instance (or fallback)
    """
    global _glassbox_risk_model

    if _glassbox_risk_model is None:
        from .glassbox_models import GlassBoxRiskModel

        path = model_path or str(DEFAULT_GLASSBOX_RISK_PATH)
        _glassbox_risk_model = GlassBoxRiskModel(
            model_path=path,
            fallback_on_error=fallback_on_error,
        )
        logger.info(f"Initialized GlassBoxRiskModel from {path}")

    return _glassbox_risk_model


def get_glassbox_anomaly_model(
    model_path: Optional[str] = None,
    *,
    fallback_on_error: bool = True,
) -> BaseAnomalyModel:
    """
    Get the GlassBox anomaly model instance (singleton).

    GlassBox models are INTERPRETABLE:
    - Every prediction includes feature deviations
    - No "black box" final decision
    - Uses robust statistics for anomaly detection

    Args:
        model_path: Path to trained model. Uses default if None.
        fallback_on_error: If True, use rule-based fallback when model unavailable.

    Returns:
        BaseAnomalyModel: GlassBoxAnomalyModel instance (or fallback)
    """
    global _glassbox_anomaly_model

    if _glassbox_anomaly_model is None:
        from .glassbox_models import GlassBoxAnomalyModel

        path = model_path or str(DEFAULT_GLASSBOX_ANOMALY_PATH)
        _glassbox_anomaly_model = GlassBoxAnomalyModel(
            model_path=path,
            fallback_on_error=fallback_on_error,
        )
        logger.info(f"Initialized GlassBoxAnomalyModel from {path}")

    return _glassbox_anomaly_model


# Model registry for programmatic access
MODEL_REGISTRY = {
    "risk_dummy": {
        "getter": get_risk_model,
        "class": "DummyRiskModel",
        "interpretable": False,
        "requires_training": False,
    },
    "risk_glassbox": {
        "getter": get_glassbox_risk_model,
        "class": "GlassBoxRiskModel",
        "interpretable": True,
        "requires_training": True,
    },
    "anomaly_dummy": {
        "getter": get_anomaly_model,
        "class": "DummyAnomalyModel",
        "interpretable": False,
        "requires_training": False,
    },
    "anomaly_glassbox": {
        "getter": get_glassbox_anomaly_model,
        "class": "GlassBoxAnomalyModel",
        "interpretable": True,
        "requires_training": True,
    },
}
