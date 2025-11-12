"""
ChainIQ Service Client

This module handles communication with the ChainIQ ML scoring service.
It provides risk scoring for shipments when tokens are created.
"""

import httpx
import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ChainIQ service endpoint (configurable)
CHAINIQ_URL = "http://localhost:8001"
SCORE_ENDPOINT = f"{CHAINIQ_URL}/score/shipment"


class ChainIQRequest(BaseModel):
    """Request to ChainIQ scoring service."""
    shipment_id: str
    driver_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    planned_delivery_date: Optional[str] = None


class ChainIQResponse(BaseModel):
    """Response from ChainIQ scoring service."""
    shipment_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_category: str  # "low", "medium", "high"
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    reasoning: Optional[str] = None


async def score_shipment(
    shipment_id: int,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    planned_delivery_date: Optional[str] = None,
    driver_id: Optional[int] = None,
) -> Optional[tuple[float, str, str]]:
    """
    Call ChainIQ service to score a shipment.
    
    Args:
        shipment_id: ID of shipment to score
        origin: Shipment origin location
        destination: Shipment destination location
        planned_delivery_date: ISO format delivery date
        driver_id: Optional driver ID for enhanced scoring
        
    Returns:
        Tuple of (risk_score, risk_category, recommended_action) or None if scoring fails
        
    Note:
        If the ChainIQ service is unavailable, logs error and returns None.
        The tokenization will still succeed with null risk fields.
    """
    try:
        request_body = ChainIQRequest(
            shipment_id=str(shipment_id),
            origin=origin,
            destination=destination,
            planned_delivery_date=planned_delivery_date,
            driver_id=driver_id,
        )
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SCORE_ENDPOINT,
                json=request_body.model_dump(),
            )
            response.raise_for_status()
            
        data = response.json()
        chainiq_response = ChainIQResponse(**data)
        
        # Generate recommended action based on risk category
        recommended_action = generate_recommended_action(
            chainiq_response.risk_category,
            chainiq_response.risk_score,
        )
        
        logger.info(
            f"ChainIQ scoring successful for shipment {shipment_id}: "
            f"risk_score={chainiq_response.risk_score}, "
            f"risk_category={chainiq_response.risk_category}"
        )
        
        return (
            chainiq_response.risk_score,
            chainiq_response.risk_category,
            recommended_action,
        )
        
    except httpx.TimeoutException:
        logger.warning(
            f"ChainIQ service timeout while scoring shipment {shipment_id}. "
            "Proceeding with token creation without risk scoring."
        )
        return None
    except httpx.ConnectError:
        logger.warning(
            f"ChainIQ service unavailable while scoring shipment {shipment_id}. "
            "Proceeding with token creation without risk scoring."
        )
        return None
    except Exception as e:
        logger.error(
            f"Error calling ChainIQ service for shipment {shipment_id}: {str(e)}"
        )
        return None


def generate_recommended_action(risk_category: str, risk_score: float) -> str:
    """
    Generate a recommended action based on risk scoring.
    
    Args:
        risk_category: Risk category (low, medium, high)
        risk_score: Numeric risk score (0.0-1.0)
        
    Returns:
        Recommended action string
    """
    if risk_category == "low":
        return "APPROVE - Low risk, suitable for standard financing"
    elif risk_category == "medium":
        if risk_score < 0.5:
            return "APPROVE_WITH_CONDITIONS - Monitor closely, may require collateral adjustment"
        else:
            return "REVIEW - Consider additional risk mitigation measures"
    else:  # high
        if risk_score > 0.85:
            return "REJECT - High risk, recommend against tokenization"
        else:
            return "REVIEW_URGENTLY - Requires detailed assessment before approval"
