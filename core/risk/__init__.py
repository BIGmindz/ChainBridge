# core/risk/__init__.py
"""
Trust Risk Index (TRI) — Glass-Box Risk Scoring Engine

This module provides deterministic, explainable risk scoring for ChainBridge.
All computations are read-only, have zero authority over governance,
and produce advisory-only outputs with full contribution breakdowns.

Author: MAGGIE (GID-10) — Machine Learning & Applied AI Lead
PAC: PAC-MAGGIE-RISK-IMPL-01
"""

from core.risk.tri_engine import TRIEngine
from core.risk.types import ConfidenceBand, ContributionRow, DomainScore, FeatureValue, TRIResult, TrustWeights

__all__ = [
    "FeatureValue",
    "DomainScore",
    "TrustWeights",
    "TRIResult",
    "ConfidenceBand",
    "ContributionRow",
    "TRIEngine",
]
