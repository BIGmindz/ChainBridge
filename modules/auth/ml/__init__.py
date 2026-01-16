"""
ChainBridge ML Risk Scoring Module
==================================

Machine learning-powered risk assessment for authentication.

Components:
  - chainiq_scorer: ChainIQ integration for ML risk scoring
"""

from .chainiq_scorer import (
    MLConfig,
    ModelType,
    FeatureVector,
    MLPrediction,
    FeatureExtractor,
    RiskClassifier,
    AnomalyDetector,
    ChainIQClient,
    MLRiskScorer,
    get_ml_scorer,
    init_ml_scorer,
)

__all__ = [
    "MLConfig",
    "ModelType",
    "FeatureVector",
    "MLPrediction",
    "FeatureExtractor",
    "RiskClassifier",
    "AnomalyDetector",
    "ChainIQClient",
    "MLRiskScorer",
    "get_ml_scorer",
    "init_ml_scorer",
]
