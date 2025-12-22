"""API routes for Risk Scoring.

This module provides the main API's risk endpoints, proxying to ChainIQ
and persisting DecisionRecords for audit trail.

Every material risk decision creates a DecisionRecord per ALEX governance
policies. No raw PII in details—use IDs, tags, and risk factors only.

Strong types, zero surprises.

Endpoints:
- POST /api/v1/risk/score - Score shipments for risk
- POST /api/v1/risk/simulation - What-if analysis
- GET /api/v1/risk/health - ChainIQ health check
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.clients import chainiq as chainiq_client
from api.database import get_db
from api.models.decision_record import DecisionRecord
from api.schemas.risk import (
    RiskHealthResponse,
    RiskScoreRequest,
    RiskScoreResponse,
    RiskSimulationRequest,
    RiskSimulationResponse,
    ShipmentRiskAssessment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["Risk - ChainIQ Gateway"])

# TODO: Replace with actual tenant/user extraction from auth context
DEFAULT_TENANT_ID = "default-tenant"


def get_tenant_id() -> str:
    """Extract tenant ID from request context.

    TODO(dan): Wire up to real auth/JWT extraction.
    """
    return DEFAULT_TENANT_ID


def _create_risk_decision_record(
    db: Session,
    tenant_id: str,
    assessment: ShipmentRiskAssessment,
    decision_type: str = "RISK_ASSESSMENT",
) -> DecisionRecord:
    """Create a DecisionRecord for a risk assessment.

    The details field includes:
    - risk_score, decision, confidence (core metrics)
    - top_factors (explainability, no PII)
    - tags (risk classification)
    - model_version (reproducibility)

    No raw PII: shipment_id is an ID, not customer data.
    """
    # Convert top_factors to safe dict format
    safe_factors = [
        {
            "name": f.name,
            "description": f.description,
            "direction": f.direction,
            "weight": f.weight,
        }
        for f in assessment.top_factors
    ]

    record = DecisionRecord(
        tenant_id=tenant_id,
        type=decision_type,
        subtype=assessment.decision,  # APPROVE, HOLD, etc.
        actor_type="SYSTEM",
        actor_id="CHAINIQ",
        actor_name="ChainIQ Risk Brain",
        entity_type="SHIPMENT",
        entity_id=assessment.shipment_id,
        policy_type="RISK_POLICY",
        outputs={
            "risk_score": assessment.risk_score,
            "decision": assessment.decision,
            "confidence": assessment.confidence,
            "operational_risk": assessment.operational_risk,
            "financial_risk": assessment.financial_risk,
            "fraud_risk": assessment.fraud_risk,
            "esg_risk": assessment.esg_risk,
            "resilience_score": assessment.resilience_score,
            "tags": assessment.tags,
            "top_factors": safe_factors,
            "model_version": assessment.model_version,
            "data_quality_score": assessment.data_quality_score,
        },
        explanation=assessment.summary_reason,
        primary_factors=[f.name for f in assessment.top_factors[:3]],
    )

    db.add(record)
    return record


# =============================================================================
# RISK SCORING ENDPOINTS
# =============================================================================


@router.post("/score", response_model=RiskScoreResponse)
async def score_shipments(
    request: RiskScoreRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Score shipments for risk.

    Proxies to ChainIQ and creates a DecisionRecord for each assessment.

    **Request limits:** 1-100 shipments per request.

    **DecisionRecord details include:**
    - risk_score (0-100)
    - decision (APPROVE/HOLD/TIGHTEN_TERMS/ESCALATE)
    - confidence (0-1)
    - top_factors (explainability)
    - tags (risk classification)
    - model_version (for reproducibility)
    """
    # Call ChainIQ
    response = await chainiq_client.score_shipments(request, tenant_id)

    # Create DecisionRecords for each assessment
    for assessment in response.assessments:
        _create_risk_decision_record(
            db=db,
            tenant_id=tenant_id,
            assessment=assessment,
            decision_type="RISK_ASSESSMENT",
        )

    # Commit all records
    try:
        db.commit()
    except Exception as e:
        logger.error("Failed to persist decision records: %s", e)
        db.rollback()
        # Don't fail the request - scoring succeeded, audit is secondary
        # TODO: Queue for retry or alert ops

    return response


@router.post("/simulation", response_model=RiskSimulationResponse)
async def simulate_risk(
    request: RiskSimulationRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Run what-if risk analysis.

    Compares base context against variations to help evaluate
    carrier/route/timing alternatives.

    Creates a single DecisionRecord summarizing the simulation.
    """
    # Call ChainIQ
    response = await chainiq_client.simulate_risk(request, tenant_id)

    # Create a single DecisionRecord for the simulation
    # Include base score and best/worst variations
    variation_summary = [
        {
            "name": v.name,
            "risk_score": v.assessment.risk_score,
            "delta": v.delta_risk_score,
            "decision": v.assessment.decision,
        }
        for v in response.variation_assessments
    ]

    best_variation = min(
        response.variation_assessments,
        key=lambda v: v.assessment.risk_score,
        default=None,
    )

    record = DecisionRecord(
        tenant_id=tenant_id,
        type="RISK_SIMULATION",
        actor_type="SYSTEM",
        actor_id="CHAINIQ",
        actor_name="ChainIQ Risk Brain",
        entity_type="SHIPMENT",
        entity_id=request.base_context.shipment_id,
        policy_type="RISK_POLICY",
        outputs={
            "base_risk_score": response.base_assessment.risk_score,
            "base_decision": response.base_assessment.decision,
            "variations": variation_summary,
            "best_variation": best_variation.name if best_variation else None,
            "best_delta": best_variation.delta_risk_score if best_variation else None,
            "recommendation": response.recommendation,
            "model_version": response.base_assessment.model_version,
        },
        explanation=f"Risk simulation: base score {response.base_assessment.risk_score:.1f}, "
        f"{len(response.variation_assessments)} variations analyzed"
        + (f", best: {best_variation.name} ({best_variation.delta_risk_score:+.1f})" if best_variation else ""),
        primary_factors=[v.name for v in response.variation_assessments[:3]],
    )

    db.add(record)

    try:
        db.commit()
    except Exception as e:
        logger.error("Failed to persist simulation decision record: %s", e)
        db.rollback()

    return response


@router.get("/health", response_model=RiskHealthResponse)
async def get_risk_health():
    """
    Check ChainIQ service health.

    Returns model status and version. Use for monitoring and
    degraded-mode detection.
    """
    return await chainiq_client.get_health()
