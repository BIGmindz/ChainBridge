"""
ChainIQ v0.1 - Settlement Recommender

High-level API for generating settlement policy recommendations from shipment contexts.
This is the primary interface for Cody/Pax to integrate settlement intelligence.

Usage:
    recommender = SettlementRecommender()
    recommendation = recommender.recommend_for_context(context)

    # Or batch:
    recommendations = recommender.recommend_for_batch(contexts)

Author: Maggie (GID-10) - ML & Applied AI Lead
Mantra: "Code = Cash. Explain or Perish."
"""

from typing import List, Optional

from .schemas import SettlementPolicyRecommendation, ShipmentRiskAssessment, ShipmentRiskContext
from .scoring import ChainIQScorer, get_default_scorer
from .settlement_rules import (
    RISK_BANDS,
    SETTLEMENT_POLICY_TEMPLATES,
    get_risk_band,
    recommend_settlement_policies,
    recommend_settlement_policy,
)


class SettlementRecommender:
    """
    Settlement policy recommender powered by ChainIQ risk scoring.

    This class orchestrates:
        1. Risk scoring via ChainIQScorer
        2. Risk → settlement mapping via settlement_rules
        3. Recommendation generation

    Design:
        - Stateless (no database writes)
        - Pure functions (deterministic for same inputs)
        - Explainable (all decisions traceable)

    Example:
        >>> recommender = SettlementRecommender()
        >>> context = ShipmentRiskContext(...)
        >>> rec = recommender.recommend_for_context(context)
        >>> print(rec.recommended_policy_code)  # e.g., "LOW_RISK_FAST"
        >>> print(rec.rationale)  # Human-readable explanation
    """

    def __init__(self, scorer: Optional[ChainIQScorer] = None):
        """
        Initialize the recommender.

        Args:
            scorer: ChainIQ scorer instance. If None, uses default scorer.
        """
        self.scorer = scorer or get_default_scorer()

    def recommend_for_context(
        self,
        context: ShipmentRiskContext,
    ) -> SettlementPolicyRecommendation:
        """
        Generate a settlement recommendation for a single shipment context.

        Flow:
            1. Score the context with ChainIQ
            2. Map assessment to settlement policy
            3. Return recommendation

        Args:
            context: Shipment risk context

        Returns:
            Settlement policy recommendation
        """
        assessment = self.scorer.score_single(context)
        return recommend_settlement_policy(assessment)

    def recommend_for_assessment(
        self,
        assessment: ShipmentRiskAssessment,
    ) -> SettlementPolicyRecommendation:
        """
        Generate a settlement recommendation from an existing assessment.

        Use this when you already have a risk assessment and don't need
        to re-score the shipment.

        Args:
            assessment: Pre-computed risk assessment

        Returns:
            Settlement policy recommendation
        """
        return recommend_settlement_policy(assessment)

    def recommend_for_batch(
        self,
        contexts: List[ShipmentRiskContext],
    ) -> List[SettlementPolicyRecommendation]:
        """
        Generate settlement recommendations for multiple shipment contexts.

        Args:
            contexts: List of shipment risk contexts

        Returns:
            List of settlement policy recommendations (same order as input)
        """
        assessments = self.scorer.score_batch(contexts)
        return recommend_settlement_policies(assessments)

    def recommend_for_assessments(
        self,
        assessments: List[ShipmentRiskAssessment],
    ) -> List[SettlementPolicyRecommendation]:
        """
        Generate settlement recommendations from existing assessments.

        Args:
            assessments: List of pre-computed risk assessments

        Returns:
            List of settlement policy recommendations
        """
        return recommend_settlement_policies(assessments)

    # =========================================================================
    # INTROSPECTION METHODS
    # =========================================================================

    @staticmethod
    def get_risk_band_for_score(risk_score: float) -> dict:
        """
        Get the risk band for a given score.

        Useful for UI display or debugging.

        Args:
            risk_score: Risk score (0-100)

        Returns:
            Risk band dict with name, min, max, label
        """
        return get_risk_band(risk_score)

    @staticmethod
    def list_risk_bands() -> list:
        """List all risk bands and their thresholds."""
        return RISK_BANDS.copy()

    @staticmethod
    def list_policy_templates() -> dict:
        """Get all settlement policy templates."""
        return SETTLEMENT_POLICY_TEMPLATES.copy()

    @staticmethod
    def get_policy_template(policy_code: str) -> dict:
        """
        Get a specific policy template by code.

        Args:
            policy_code: Policy code (e.g., "LOW_RISK_FAST")

        Returns:
            Policy template dictionary

        Raises:
            KeyError: If policy code not found
        """
        return SETTLEMENT_POLICY_TEMPLATES[policy_code]


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_default_recommender: Optional[SettlementRecommender] = None


def get_default_recommender() -> SettlementRecommender:
    """Get or create the default settlement recommender instance."""
    global _default_recommender
    if _default_recommender is None:
        _default_recommender = SettlementRecommender()
    return _default_recommender


def recommend_settlement(
    context: ShipmentRiskContext,
) -> SettlementPolicyRecommendation:
    """
    Convenience function to get a settlement recommendation for a single context.

    Uses the default recommender instance.

    Args:
        context: Shipment risk context

    Returns:
        Settlement policy recommendation
    """
    return get_default_recommender().recommend_for_context(context)


def recommend_settlements(
    contexts: List[ShipmentRiskContext],
) -> List[SettlementPolicyRecommendation]:
    """
    Convenience function to get settlement recommendations for multiple contexts.

    Uses the default recommender instance.

    Args:
        contexts: List of shipment risk contexts

    Returns:
        List of settlement policy recommendations
    """
    return get_default_recommender().recommend_for_batch(contexts)
