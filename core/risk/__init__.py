# core/risk/__init__.py
"""
Trust Risk Index (TRI) — Glass-Box Risk Scoring Engine

This module provides deterministic, explainable risk scoring for ChainBridge.
All computations are read-only, have zero authority over governance,
and produce advisory-only outputs with full contribution breakdowns.

Author: MAGGIE (GID-10) — Machine Learning & Applied AI Lead
PAC: PAC-MAGGIE-RISK-IMPL-01
Extended By: PAC-CODY-TRI-GLASSBOX-WIRING-IMPLEMENTATION-01
"""

from core.risk.tri_engine import TRIEngine
from core.risk.types import ConfidenceBand, ContributionRow, DomainScore, FeatureValue, TRIResult, TrustWeights
from core.risk.tri_glassbox_executor import (
    ExecutorFailureMode,
    GlassBoxScoringFn,
    MonotonicityState,
    TRIExecutionError,
    TRIExecutionResult,
    TRIGlassBoxExecutor,
    create_activation_reference,
    create_tri_risk_input,
)
from core.risk.tri_glassbox_integration import (
    ActivationReference,
    GlassBoxRiskOutput,
    IntegrationFailureMode,
    PDORiskEmbedding,
    RiskSeverityTier,
    TRIAction,
    TRIRiskInput,
)

__all__ = [
    # Original TRI types
    "FeatureValue",
    "DomainScore",
    "TrustWeights",
    "TRIResult",
    "ConfidenceBand",
    "ContributionRow",
    "TRIEngine",
    # Glass-box integration (PAC-MAGGIE)
    "ActivationReference",
    "TRIRiskInput",
    "GlassBoxRiskOutput",
    "PDORiskEmbedding",
    "RiskSeverityTier",
    "TRIAction",
    "IntegrationFailureMode",
    # Glass-box executor (PAC-CODY)
    "ExecutorFailureMode",
    "TRIExecutionError",
    "TRIExecutionResult",
    "MonotonicityState",
    "TRIGlassBoxExecutor",
    "GlassBoxScoringFn",
    "create_activation_reference",
    "create_tri_risk_input",
]
