"""
ChainFreight Service Client

This module handles communication with ChainFreight to fetch freight token details
including risk scoring information needed for settlement decisions.
"""

import httpx
import logging
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ChainFreight service endpoint (configurable)
CHAINFREIGHT_URL = "http://localhost:8002"


class FreightTokenResponse(BaseModel):
    """Freight token response from ChainFreight."""

    id: int
    shipment_id: int
    face_value: float
    currency: str
    status: str
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    recommended_action: Optional[str] = None
    created_at: str
    updated_at: str


async def fetch_freight_token(token_id: int) -> Optional[FreightTokenResponse]:
    """
    Fetch freight token details from ChainFreight service.

    Args:
        token_id: ID of the freight token to fetch

    Returns:
        FreightTokenResponse or None if not found/unavailable
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{CHAINFREIGHT_URL}/tokens/{token_id}",
            )
            response.raise_for_status()

        data = response.json()
        token = FreightTokenResponse(**data)

        logger.info(f"Successfully fetched freight token {token_id}: " f"status={token.status}, risk={token.risk_category}")

        return token

    except httpx.TimeoutException:
        logger.warning(f"ChainFreight service timeout while fetching token {token_id}")
        return None
    except httpx.ConnectError:
        logger.warning(f"ChainFreight service unavailable while fetching token {token_id}")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"Freight token {token_id} not found")
        else:
            logger.error(f"HTTP error {e.response.status_code} fetching token {token_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching freight token {token_id}: {str(e)}")
        return None


def map_risk_to_tier(risk_category: Optional[str]) -> str:
    """
    Map ChainIQ risk category to payment settlement tier.

    Args:
        risk_category: Risk category from freight token (low, medium, high)

    Returns:
        Settlement tier (low, medium, high)
    """
    if risk_category is None:
        # If no risk data, be conservative
        return "medium"

    category = risk_category.lower().strip()

    if category == "low":
        return "low"
    elif category == "high":
        return "high"
    else:
        return "medium"
