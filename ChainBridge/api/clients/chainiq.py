"""ChainIQ Risk Scoring Client.

HTTP client for communicating with Maggie's ChainIQ service.
The main API uses this client to proxy risk scoring requests.

The main API is the single entry point for risk scoring—frontend and
other services should never call ChainIQ directly.

Strong types, zero surprises.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException

from api.schemas.risk import (
    RiskHealthResponse,
    RiskScoreRequest,
    RiskScoreResponse,
    RiskSimulationRequest,
    RiskSimulationResponse,
    RiskSimulationVariantResult,
    ShipmentRiskAssessment,
    TopFactor,
)

logger = logging.getLogger(__name__)

# ChainIQ service configuration
# TODO(dan): Move to centralized settings module
CHAINIQ_BASE_URL = os.getenv("CHAINIQ_BASE_URL", "http://chainiq-service:8102")
CHAINIQ_TIMEOUT_SECONDS = float(os.getenv("CHAINIQ_TIMEOUT_SECONDS", "30"))


class ChainIQUnavailable(Exception):
    """Raised when ChainIQ service is unavailable."""

    pass


def _map_chainiq_factors(chainiq_factors: List[Dict[str, Any]]) -> List[TopFactor]:
    """Map ChainIQ TopFactor format to main API format.

    ChainIQ uses: feature_name, direction (INCREASES_RISK/DECREASES_RISK), magnitude, human_label
    Main API uses: name, direction (UP/DOWN), weight, description
    """
    result = []
    for f in chainiq_factors:
        direction = "UP" if f.get("direction") == "INCREASES_RISK" else "DOWN"
        result.append(
            TopFactor(
                name=f.get("feature_name", "unknown"),
                description=f.get("human_label", ""),
                direction=direction,
                weight=f.get("magnitude", 0.0),
            )
        )
    return result


def _map_chainiq_assessment(raw: Dict[str, Any]) -> ShipmentRiskAssessment:
    """Map ChainIQ assessment response to main API schema."""
    return ShipmentRiskAssessment(
        shipment_id=raw["shipment_id"],
        assessed_at=datetime.fromisoformat(raw["assessed_at"].replace("Z", "+00:00")) if raw.get("assessed_at") else datetime.utcnow(),
        model_version=raw.get("model_version", "chainiq-v0.1"),
        risk_score=raw["risk_score"],
        operational_risk=raw.get("operational_risk"),
        financial_risk=raw.get("financial_risk"),
        fraud_risk=raw.get("fraud_risk"),
        esg_risk=raw.get("esg_risk"),
        resilience_score=raw.get("resilience_score"),
        decision=raw["decision"],
        confidence=raw.get("decision_confidence", raw.get("confidence", 0.8)),
        top_factors=_map_chainiq_factors(raw.get("top_factors", [])),
        summary_reason=raw.get("summary_reason", "No summary provided"),
        tags=raw.get("tags", []),
        data_quality_score=raw.get("data_quality_score"),
    )


async def score_shipments(
    request: RiskScoreRequest,
    tenant_id: str,
) -> RiskScoreResponse:
    """
    Score shipments for risk via ChainIQ service.

    Args:
        request: Risk score request with shipment contexts
        tenant_id: Tenant ID for multi-tenant scoping

    Returns:
        RiskScoreResponse with assessments

    Raises:
        HTTPException: If ChainIQ is unavailable (503) or returns error
    """
    # Build ChainIQ request payload
    # ChainIQ expects tenant_id in each shipment context
    chainiq_payload = {
        "shipments": [{**s.model_dump(mode="json"), "tenant_id": tenant_id} for s in request.shipments],
        "include_factors": request.include_factors,
        "include_summary": request.include_summary,
        "max_factors": request.max_factors,
    }

    try:
        async with httpx.AsyncClient(timeout=CHAINIQ_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{CHAINIQ_BASE_URL}/api/v1/risk/score",
                json=chainiq_payload,
            )

            if response.status_code >= 500:
                logger.error("ChainIQ returned server error: %s", response.status_code)
                raise ChainIQUnavailable(f"ChainIQ server error: {response.status_code}")

            if response.status_code >= 400:
                logger.warning("ChainIQ returned client error: %s", response.text)
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ChainIQ error: {response.text}",
                )

            data = response.json()

            # Map ChainIQ response to main API schema
            assessments = [_map_chainiq_assessment(a) for a in data.get("assessments", [])]

            return RiskScoreResponse(
                assessments=assessments,
                meta=data.get("meta", {}),
            )

    except httpx.ConnectError as e:
        logger.error("Failed to connect to ChainIQ: %s", e)
        raise HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )
    except httpx.TimeoutException as e:
        logger.error("ChainIQ request timed out: %s", e)
        raise HTTPException(
            status_code=504,
            detail="ChainIQ service timeout",
        )
    except ChainIQUnavailable:
        raise HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )


async def simulate_risk(
    request: RiskSimulationRequest,
    tenant_id: str,
) -> RiskSimulationResponse:
    """
    Run risk simulation via ChainIQ service.

    Args:
        request: Simulation request with base context and variations
        tenant_id: Tenant ID for multi-tenant scoping

    Returns:
        RiskSimulationResponse with base and variation assessments

    Raises:
        HTTPException: If ChainIQ is unavailable (503) or returns error
    """
    # Build ChainIQ request payload
    chainiq_payload = {
        "base_context": {**request.base_context.model_dump(mode="json"), "tenant_id": tenant_id},
        "variations": [v.model_dump(mode="json") for v in request.variations],
    }

    try:
        async with httpx.AsyncClient(timeout=CHAINIQ_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{CHAINIQ_BASE_URL}/api/v1/risk/simulation",
                json=chainiq_payload,
            )

            if response.status_code >= 500:
                logger.error("ChainIQ returned server error: %s", response.status_code)
                raise ChainIQUnavailable(f"ChainIQ server error: {response.status_code}")

            if response.status_code >= 400:
                logger.warning("ChainIQ returned client error: %s", response.text)
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ChainIQ error: {response.text}",
                )

            data = response.json()

            # Map response
            base_assessment = _map_chainiq_assessment(data["base_assessment"])
            variation_assessments = [
                RiskSimulationVariantResult(
                    name=v["name"],
                    assessment=_map_chainiq_assessment(v["assessment"]),
                    delta_risk_score=v.get("delta_risk_score", 0.0),
                )
                for v in data.get("variation_assessments", [])
            ]

            # Build recommendation string if present
            recommendation = None
            if data.get("recommendation"):
                rec = data["recommendation"]
                if isinstance(rec, dict):
                    recommendation = rec.get("summary") or rec.get("name") or str(rec)
                else:
                    recommendation = str(rec)

            return RiskSimulationResponse(
                base_assessment=base_assessment,
                variation_assessments=variation_assessments,
                recommendation=recommendation,
            )

    except httpx.ConnectError as e:
        logger.error("Failed to connect to ChainIQ: %s", e)
        raise HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )
    except httpx.TimeoutException as e:
        logger.error("ChainIQ request timed out: %s", e)
        raise HTTPException(
            status_code=504,
            detail="ChainIQ service timeout",
        )
    except ChainIQUnavailable:
        raise HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )


async def get_health() -> RiskHealthResponse:
    """
    Check ChainIQ service health.

    Returns:
        RiskHealthResponse with status and model version

    Raises:
        HTTPException: If ChainIQ is unavailable (503)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CHAINIQ_BASE_URL}/api/v1/risk/health")

            if response.status_code >= 500:
                raise ChainIQUnavailable(f"ChainIQ server error: {response.status_code}")

            if response.status_code >= 400:
                # Return degraded status if health check fails
                return RiskHealthResponse(
                    status="degraded",
                    model_version="unknown",
                    last_check=datetime.utcnow(),
                )

            data = response.json()
            return RiskHealthResponse(
                status=data.get("status", "unknown"),
                model_version=data.get("model_version", "unknown"),
                last_check=(
                    datetime.fromisoformat(data["last_check"].replace("Z", "+00:00")) if data.get("last_check") else datetime.utcnow()
                ),
            )

    except (httpx.ConnectError, httpx.TimeoutException, ChainIQUnavailable) as e:
        logger.warning("ChainIQ health check failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )
