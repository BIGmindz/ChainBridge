"""
ChainIQ v0.1 - Scoring Pipeline

End-to-end scoring from ShipmentRiskContext to ShipmentRiskAssessment.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from .explain import estimate_decision_confidence, extract_top_factors, generate_risk_tags, generate_summary_reason
from .features import MODEL_FEATURE_NAMES, engineer_features, features_to_array
from .models import BaseRiskModel, HeuristicRiskModel, load_model
from .schemas import (
    RiskScoreRequest,
    RiskScoreResponse,
    RiskSimulationRequest,
    RiskSimulationResponse,
    ShipmentRiskAssessment,
    ShipmentRiskContext,
    TopFactor,
    VariationResult,
)

# =============================================================================
# DECISION THRESHOLDS
# =============================================================================


@dataclass
class DecisionThresholds:
    """Configurable thresholds for risk → decision mapping."""

    approve_max: float = 30.0
    tighten_terms_max: float = 70.0
    hold_max: float = 85.0

    # Value-based adjustments
    high_value_threshold_usd: float = 100_000
    high_value_tighten_reduction: float = 10.0


DEFAULT_THRESHOLDS = DecisionThresholds()


# =============================================================================
# RISK SCORE COMPONENTS
# =============================================================================


def compute_risk_components(
    base_risk_prob: float,
    features: dict,
    context: ShipmentRiskContext,
) -> dict:
    """
    Break down overall risk into component scores.

    Returns dict with:
        - risk_score: 0-100
        - operational_risk: 0-100
        - financial_risk: 0-100
        - fraud_risk: 0-100
        - esg_risk: 0-100
        - resilience_score: 0-100
    """
    # Base transformation: probability (0-1) → score (0-100)
    risk_score = base_risk_prob * 100

    # === OPERATIONAL RISK ===
    # Primary driver in v0 - delays, routing, capacity
    operational_risk = risk_score * 0.85

    # Event-based adjustments
    if features.get("has_port_congestion"):
        operational_risk = min(100, operational_risk + 10)
    if features.get("has_carrier_delay"):
        operational_risk = min(100, operational_risk + 8)
    if features.get("departure_delay_hours", 0) > 24:
        operational_risk = min(100, operational_risk + 12)

    # Mode adjustments
    if features.get("mode_intermodal"):
        operational_risk = min(100, operational_risk * 1.1)  # More handoff risk

    # === FINANCIAL RISK ===
    # Cost overruns, claims, value loss
    financial_risk = risk_score * 0.6

    # Value-based adjustment
    if (context.value_usd or 0) > 100_000:
        financial_risk = min(100, financial_risk * 1.2)

    # Documentation issues increase financial risk
    if features.get("has_documentation_issue"):
        financial_risk = min(100, financial_risk + 15)

    # === FRAUD RISK ===
    # Placeholder - minimal signal in v0
    fraud_risk = max(0, risk_score * 0.1 - 5)

    # Data quality as proxy for fraud risk
    data_quality = features.get("data_completeness_score", 1)
    if data_quality < 0.5:
        fraud_risk = min(100, fraud_risk + 15)
    if data_quality < 0.3:
        fraud_risk = min(100, fraud_risk + 10)

    # === ESG RISK ===
    # Placeholder for v0
    esg_risk = 0.0

    # === RESILIENCE SCORE ===
    # Inverse of risk with buffer considerations
    resilience_score = max(0, 100 - risk_score * 1.1)

    # Lane reliability bonus
    if features.get("lane_historical_delay_rate", 1) < 0.05:
        resilience_score = min(100, resilience_score + 10)

    # Carrier reliability bonus
    if features.get("carrier_historical_delay_rate", 1) < 0.05:
        resilience_score = min(100, resilience_score + 8)

    return {
        "risk_score": round(risk_score, 1),
        "operational_risk": round(min(100, max(0, operational_risk)), 1),
        "financial_risk": round(min(100, max(0, financial_risk)), 1),
        "fraud_risk": round(min(100, max(0, fraud_risk)), 1),
        "esg_risk": round(esg_risk, 1),
        "resilience_score": round(min(100, max(0, resilience_score)), 1),
    }


# =============================================================================
# DECISION MAPPING
# =============================================================================


def map_risk_to_decision(
    risk_score: float,
    value_usd: Optional[float] = None,
    thresholds: DecisionThresholds = DEFAULT_THRESHOLDS,
) -> Literal["APPROVE", "HOLD", "TIGHTEN_TERMS", "ESCALATE"]:
    """
    Map risk score to actionable decision.
    """
    # Adjust thresholds for high-value shipments
    effective_tighten_max = thresholds.tighten_terms_max
    if value_usd and value_usd > thresholds.high_value_threshold_usd:
        effective_tighten_max -= thresholds.high_value_tighten_reduction

    if risk_score <= thresholds.approve_max:
        return "APPROVE"
    elif risk_score <= effective_tighten_max:
        return "APPROVE" if risk_score < 50 else "TIGHTEN_TERMS"
    elif risk_score <= thresholds.hold_max:
        return "TIGHTEN_TERMS"
    elif risk_score <= 95:
        return "HOLD"
    else:
        return "ESCALATE"


# =============================================================================
# SCORING PIPELINE
# =============================================================================


class ChainIQScorer:
    """
    Main scoring pipeline for ChainIQ v0.1.

    Handles the full flow from ShipmentRiskContext to ShipmentRiskAssessment.
    """

    def __init__(
        self,
        model: Optional[BaseRiskModel] = None,
        thresholds: Optional[DecisionThresholds] = None,
        max_factors: int = 5,
    ):
        """
        Initialize scorer.

        Args:
            model: Risk model to use (defaults to HeuristicRiskModel)
            thresholds: Decision thresholds (uses defaults if not provided)
            max_factors: Maximum number of explanation factors to include
        """
        self.model = model or HeuristicRiskModel()
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.max_factors = max_factors
        self.feature_names = MODEL_FEATURE_NAMES

    @classmethod
    def from_model_path(cls, model_path: Path, **kwargs) -> "ChainIQScorer":
        """Load scorer with model from disk."""
        model = load_model(model_path)
        return cls(model=model, **kwargs)

    def score_single(
        self,
        context: ShipmentRiskContext,
        include_factors: bool = True,
        include_summary: bool = True,
    ) -> ShipmentRiskAssessment:
        """
        Score a single shipment.

        Args:
            context: Shipment context to score
            include_factors: Whether to include top factors
            include_summary: Whether to include summary reason

        Returns:
            ShipmentRiskAssessment with all scores and explanations
        """
        # 1. Engineer features
        features = engineer_features(context)

        # 2. Convert to model input
        X = features_to_array(features, self.feature_names)

        # 3. Get base risk probability
        base_prob = self.model.predict_proba(X)[0]

        # 4. Compute risk components
        components = compute_risk_components(base_prob, features, context)

        # 5. Map to decision
        decision = map_risk_to_decision(
            components["risk_score"],
            context.value_usd,
            self.thresholds,
        )

        # 6. Generate explanations
        if include_factors:
            shap_values = self.model.get_shap_values(X)
            top_factors = extract_top_factors(
                shap_values,
                self.feature_names,
                features,
                top_n=self.max_factors,
            )
        else:
            top_factors = [
                TopFactor(
                    feature_name="summary",
                    direction="INCREASES_RISK",
                    magnitude=100.0,
                    human_label="Detailed factors not requested",
                )
            ]

        if include_summary:
            summary_reason = generate_summary_reason(
                components["risk_score"],
                decision,
                top_factors,
                context,
            )
        else:
            summary_reason = f"Risk score: {components['risk_score']:.0f}/100"

        # 7. Generate tags
        tags = generate_risk_tags(context, features, components["risk_score"])

        # 8. Estimate confidence
        confidence = estimate_decision_confidence(
            components["risk_score"],
            features.get("data_completeness_score", 1),
            decision,
            {
                "approve_max": self.thresholds.approve_max,
                "tighten_terms_max": self.thresholds.tighten_terms_max,
                "hold_max": self.thresholds.hold_max,
            },
        )

        # 9. Build assessment
        return ShipmentRiskAssessment(
            shipment_id=context.shipment_id,
            assessed_at=datetime.utcnow(),
            model_version=self.model.version,
            risk_score=components["risk_score"],
            operational_risk=components["operational_risk"],
            financial_risk=components["financial_risk"],
            fraud_risk=components["fraud_risk"],
            esg_risk=components["esg_risk"],
            resilience_score=components["resilience_score"],
            decision=decision,
            decision_confidence=confidence,
            top_factors=top_factors,
            summary_reason=summary_reason,
            tags=tags,
            data_quality_score=features.get("data_completeness_score", 1),
        )

    def score_batch(
        self,
        contexts: List[ShipmentRiskContext],
        include_factors: bool = True,
        include_summary: bool = True,
    ) -> List[ShipmentRiskAssessment]:
        """
        Score multiple shipments.

        Args:
            contexts: List of shipment contexts
            include_factors: Whether to include top factors
            include_summary: Whether to include summary reason

        Returns:
            List of ShipmentRiskAssessment objects
        """
        return [self.score_single(ctx, include_factors, include_summary) for ctx in contexts]

    def handle_score_request(
        self,
        request: RiskScoreRequest,
    ) -> RiskScoreResponse:
        """
        Handle API score request.

        Args:
            request: RiskScoreRequest with shipments and options

        Returns:
            RiskScoreResponse with assessments and metadata
        """
        start_time = datetime.utcnow()

        assessments = self.score_batch(
            request.shipments,
            include_factors=request.include_factors,
            include_summary=request.include_summary,
        )

        # Respect max_factors setting
        if request.max_factors < self.max_factors:
            for assessment in assessments:
                assessment.top_factors = assessment.top_factors[: request.max_factors]

        end_time = datetime.utcnow()
        processing_ms = (end_time - start_time).total_seconds() * 1000

        return RiskScoreResponse(
            assessments=assessments,
            meta={
                "model_version": self.model.version,
                "processing_time_ms": round(processing_ms, 1),
                "batch_size": len(request.shipments),
            },
        )

    def handle_simulation_request(
        self,
        request: RiskSimulationRequest,
    ) -> RiskSimulationResponse:
        """
        Handle API simulation request for what-if analysis.

        Args:
            request: RiskSimulationRequest with base context and variations

        Returns:
            RiskSimulationResponse with base and variation assessments
        """
        # Score base context
        base_assessment = self.score_single(request.base_context)

        # Score each variation
        variation_results = []
        for variation in request.variations:
            # Create modified context
            modified_data = request.base_context.model_dump()
            modified_data.update(variation.overrides)
            modified_context = ShipmentRiskContext(**modified_data)

            # Score modified context
            var_assessment = self.score_single(modified_context)

            variation_results.append(
                VariationResult(
                    name=variation.name,
                    assessment=var_assessment,
                    delta_risk_score=round(var_assessment.risk_score - base_assessment.risk_score, 1),
                )
            )

        # Find best variation (lowest risk)
        best_variation = None
        if variation_results:
            best = min(variation_results, key=lambda v: v.assessment.risk_score)
            if best.delta_risk_score < -5:  # Only recommend if meaningful improvement
                best_variation = {
                    "best_variation": best.name,
                    "savings_estimate": f"{abs(best.delta_risk_score):.0f} point risk reduction",
                }

        return RiskSimulationResponse(
            base_assessment=base_assessment,
            variation_assessments=variation_results,
            recommendation=best_variation,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global default scorer (initialized lazily)
_default_scorer: Optional[ChainIQScorer] = None


def get_default_scorer() -> ChainIQScorer:
    """Get or create the default scorer instance."""
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = ChainIQScorer()
    return _default_scorer


def score_shipment(context: ShipmentRiskContext) -> ShipmentRiskAssessment:
    """
    Convenience function to score a single shipment.

    Uses the default heuristic model.
    """
    return get_default_scorer().score_single(context)


def score_shipments(contexts: List[ShipmentRiskContext]) -> List[ShipmentRiskAssessment]:
    """
    Convenience function to score multiple shipments.

    Uses the default heuristic model.
    """
    return get_default_scorer().score_batch(contexts)
