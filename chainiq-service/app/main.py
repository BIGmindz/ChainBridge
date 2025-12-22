"""
ChainIQ v0.1 - Risk Scoring Service

FastAPI application exposing ChainIQ risk scoring endpoints.

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .schemas import (
    RiskScoreRequest,
    RiskScoreResponse,
    RiskSimulationRequest,
    RiskSimulationResponse,
    SettlementPolicyRecommendation,
    SettlementRecommendationRequest,
    SettlementRecommendationResponse,
    ShipmentRiskAssessment,
    ShipmentRiskContext,
)
from .scoring import ChainIQScorer, get_default_scorer
from .settlement import get_default_recommender

# =============================================================================
# APPLICATION SETUP
# =============================================================================

# Global scorer instance
_scorer: Optional[ChainIQScorer] = None


def get_scorer() -> ChainIQScorer:
    """Get or create the scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = get_default_scorer()
    return _scorer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup: initialize scorer
    global _scorer
    _scorer = get_default_scorer()
    print(f"ChainIQ v0.1 scorer initialized: {_scorer.model.version}")
    yield
    # Shutdown: cleanup
    _scorer = None


app = FastAPI(
    title="ChainIQ Risk Scoring API",
    description="Glass-box risk brain for ChainBridge logistics operations",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH ENDPOINT
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_version: str
    last_check: datetime


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns model status and version.
    """
    scorer = get_scorer()
    return HealthResponse(
        status="healthy" if scorer.model.is_fitted else "degraded",
        model_version=scorer.model.version,
        last_check=datetime.utcnow(),
    )


@app.get("/api/v1/risk/health", response_model=HealthResponse, tags=["Health"])
async def risk_health():
    """Alias for health check under /api/v1/risk path."""
    return await health_check()


# =============================================================================
# RISK SCORING ENDPOINTS
# =============================================================================


@app.post(
    "/api/v1/risk/score",
    response_model=RiskScoreResponse,
    tags=["Risk Scoring"],
    summary="Score shipments for risk",
    description="""
    Score one or more shipments for risk.

    Returns risk scores, component breakdowns, explainability factors,
    and recommended decisions for each shipment.

    **Request limits:** 1-100 shipments per request.
    """,
)
async def score_shipments(request: RiskScoreRequest) -> RiskScoreResponse:
    """
    Score shipments for risk.

    Accepts batch of ShipmentRiskContext objects and returns
    ShipmentRiskAssessment for each.
    """
    try:
        scorer = get_scorer()
        return scorer.handle_score_request(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoring error: {str(e)}",
        )


@app.post(
    "/api/v1/risk/score/single",
    response_model=ShipmentRiskAssessment,
    tags=["Risk Scoring"],
    summary="Score a single shipment",
    description="Convenience endpoint for scoring a single shipment.",
)
async def score_single_shipment(context: ShipmentRiskContext) -> ShipmentRiskAssessment:
    """
    Score a single shipment.

    Simpler interface when scoring just one shipment.
    """
    try:
        scorer = get_scorer()
        return scorer.score_single(context)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoring error: {str(e)}",
        )


@app.post(
    "/api/v1/risk/simulation",
    response_model=RiskSimulationResponse,
    tags=["Risk Scoring"],
    summary="Run what-if simulation",
    description="""
    Compare risk scores under different scenarios.

    Use this to answer questions like:
    - "What if we used a different carrier?"
    - "What if we shipped next week instead?"
    - "What if we used air freight instead of ocean?"

    Returns base assessment plus assessments for each variation,
    with delta risk scores and recommendations.
    """,
)
async def run_simulation(request: RiskSimulationRequest) -> RiskSimulationResponse:
    """
    Run what-if risk simulation.

    Compares base shipment context against variations to help
    operators make informed routing/timing decisions.
    """
    try:
        scorer = get_scorer()
        return scorer.handle_simulation_request(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation error: {str(e)}",
        )


# =============================================================================
# MODEL INFO ENDPOINTS
# =============================================================================


class ModelInfoResponse(BaseModel):
    """Model information response."""

    version: str
    model_type: str
    feature_count: int
    feature_names: list
    is_fitted: bool


@app.get(
    "/api/v1/risk/model/info",
    response_model=ModelInfoResponse,
    tags=["Model Info"],
    summary="Get model information",
)
async def get_model_info() -> ModelInfoResponse:
    """
    Get information about the current risk model.

    Useful for debugging and integration verification.
    """
    scorer = get_scorer()
    return ModelInfoResponse(
        version=scorer.model.version,
        model_type=type(scorer.model).__name__,
        feature_count=len(scorer.feature_names),
        feature_names=scorer.feature_names,
        is_fitted=scorer.model.is_fitted,
    )


class FeatureImportanceResponse(BaseModel):
    """Feature importance response."""

    importance: dict
    model_version: str


@app.get(
    "/api/v1/risk/model/importance",
    response_model=FeatureImportanceResponse,
    tags=["Model Info"],
    summary="Get feature importance",
)
async def get_feature_importance() -> FeatureImportanceResponse:
    """
    Get feature importance scores from the model.

    Useful for understanding what drives risk predictions globally.
    """
    scorer = get_scorer()
    return FeatureImportanceResponse(
        importance=scorer.model.get_feature_importance(),
        model_version=scorer.model.version,
    )


# =============================================================================
# SETTLEMENT RECOMMENDATION ENDPOINTS
# =============================================================================


@app.post(
    "/api/v1/risk/settlement/recommend",
    response_model=SettlementRecommendationResponse,
    tags=["Settlement"],
    summary="Get settlement policy recommendations",
    description="""
    Generate settlement policy recommendations based on risk assessments.

    This endpoint maps ChainIQ risk scores to suggested payment milestone
    schedules. The recommendations are **advisory** — ChainPay + governance
    make the final decision.

    **Policy codes:**
    - `LOW_RISK_FAST`: Accelerated 20/70/10 split
    - `MODERATE_BALANCED`: Standard 10/60/30 split
    - `HIGH_RISK_GUARDED`: Conservative 0/60/40 split
    - `CRITICAL_REVIEW`: Manual review with 0/40/60 split

    **Request limits:** 1-100 shipments per request.
    """,
)
async def recommend_settlement(
    request: SettlementRecommendationRequest,
) -> SettlementRecommendationResponse:
    """
    Generate settlement policy recommendations for shipments.

    Takes shipment contexts, scores them for risk, and maps risk levels
    to appropriate settlement policies with milestone breakdowns.
    """
    try:
        recommender = get_default_recommender()
        recommendations = recommender.recommend_for_batch(request.shipments)
        return SettlementRecommendationResponse(
            recommendations=recommendations,
            meta={
                "count": len(recommendations),
                "generated_at": datetime.utcnow().isoformat(),
                "model_version": get_scorer().model.version,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Settlement recommendation error: {str(e)}",
        )


@app.post(
    "/api/v1/risk/settlement/recommend/single",
    response_model=SettlementPolicyRecommendation,
    tags=["Settlement"],
    summary="Get single settlement recommendation",
    description="Convenience endpoint for getting recommendation for a single shipment.",
)
async def recommend_settlement_single(
    context: ShipmentRiskContext,
) -> SettlementPolicyRecommendation:
    """
    Generate a settlement recommendation for a single shipment.
    """
    try:
        recommender = get_default_recommender()
        return recommender.recommend_for_context(context)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Settlement recommendation error: {str(e)}",
        )


class SettlementPolicySummary(BaseModel):
    """Summary of available settlement policy templates."""

    risk_bands: list
    policy_templates: dict


@app.get(
    "/api/v1/risk/settlement/policies",
    response_model=SettlementPolicySummary,
    tags=["Settlement"],
    summary="List settlement policy templates",
    description="Get all available settlement policy templates and risk band definitions.",
)
async def list_settlement_policies() -> SettlementPolicySummary:
    """
    List all settlement policy templates.

    Useful for understanding what policies exist and how they map to risk bands.
    """
    recommender = get_default_recommender()
    return SettlementPolicySummary(
        risk_bands=recommender.list_risk_bands(),
        policy_templates=recommender.list_policy_templates(),
    )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8102)
