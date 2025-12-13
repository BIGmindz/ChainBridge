"""
ChainIQ v0.1 - Risk Scoring Package

Glass-box risk brain for ChainBridge logistics operations.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from .evaluation import (
    EvaluationMetrics,
    RetrospectiveReport,
    compute_evaluation_metrics,
    run_retrospective_from_csv,
    run_retrospective_pilot,
)
from .explain import extract_top_factors, generate_risk_tags, generate_summary_reason
from .features import MODEL_FEATURE_NAMES, engineer_features, features_to_array
from .models import BaseRiskModel, HeuristicRiskModel, LogisticRiskModel, ModelConfig, XGBoostRiskModel, get_model, load_model
from .schemas import (
    RiskScoreRequest,
    RiskScoreResponse,
    RiskSimulationRequest,
    RiskSimulationResponse,
    ShipmentEventLite,
    ShipmentRiskAssessment,
    ShipmentRiskContext,
    TopFactor,
)
from .scoring import ChainIQScorer, DecisionThresholds, score_shipment, score_shipments

__version__ = "0.1.0"
__author__ = "Maggie (GID-10)"

__all__ = [
    # Schemas
    "ShipmentRiskContext",
    "ShipmentRiskAssessment",
    "ShipmentEventLite",
    "TopFactor",
    "RiskScoreRequest",
    "RiskScoreResponse",
    "RiskSimulationRequest",
    "RiskSimulationResponse",
    # Features
    "engineer_features",
    "features_to_array",
    "MODEL_FEATURE_NAMES",
    # Models
    "BaseRiskModel",
    "XGBoostRiskModel",
    "LogisticRiskModel",
    "HeuristicRiskModel",
    "get_model",
    "load_model",
    "ModelConfig",
    # Scoring
    "ChainIQScorer",
    "score_shipment",
    "score_shipments",
    "DecisionThresholds",
    # Explanation
    "extract_top_factors",
    "generate_summary_reason",
    "generate_risk_tags",
    # Evaluation
    "run_retrospective_pilot",
    "run_retrospective_from_csv",
    "compute_evaluation_metrics",
    "EvaluationMetrics",
    "RetrospectiveReport",
]
