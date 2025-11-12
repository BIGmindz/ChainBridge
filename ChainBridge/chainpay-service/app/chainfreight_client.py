"""
ChainFreight Service Client

This module handles communication with ChainFreight to fetch freight token details
including risk scoring information needed for settlement decisions.
"""

import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ChainFreight service endpoint (configurable)
CHAINFREIGHT_URL = "http://localhost:8002"


def _safe_get(obj: Any, key: str, default: Any = 0.0) -> Any:
    """
    Return obj[key] if obj is a dict-like, otherwise if obj is numeric return it
    (useful when upstream sometimes returns a raw float). Otherwise return default.
    """
    from numbers import Number

    if isinstance(obj, dict):
        return obj.get(key, default)
    if isinstance(obj, Number):
        # treat the numeric as the desired value
        try:
            return obj if isinstance(obj, (int, float)) else float(str(obj))
        except (ValueError, TypeError):
            return default
    return default


def _safe_extract_risk_data(data: dict) -> tuple[Optional[float], Optional[str]]:
    """
    Safely extract risk score and risk category from API response.

    Args:
        data: Raw API response data

    Returns:
        Tuple of (risk_score, risk_category)
    """
    risk_score = _safe_get(data, "risk_score", None)
    risk_category = _safe_get(data, "risk_category", None)

    # Ensure risk_score is properly typed
    if risk_score is not None:
        try:
            risk_score = float(risk_score)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid risk_score format: {risk_score}, defaulting to None"
            )
            risk_score = None

    # Ensure risk_category is a string
    if risk_category is not None and not isinstance(risk_category, str):
        risk_category = str(risk_category) if risk_category else None

    return risk_score, risk_category


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

        # Safely extract risk data using our utility function
        risk_score, risk_category = _safe_extract_risk_data(data)

        # Update the data with safely extracted values
        data["risk_score"] = risk_score
        data["risk_category"] = risk_category

        token = FreightTokenResponse(**data)

        logger.info(
            f"Successfully fetched freight token {token_id}: "
            f"status={token.status}, risk={token.risk_category}"
        )

        return token

    except httpx.TimeoutException:
        logger.warning(f"ChainFreight service timeout while fetching token {token_id}")
        return None
    except httpx.ConnectError:
        logger.warning(
            f"ChainFreight service unavailable while fetching token {token_id}"
        )
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"Freight token {token_id} not found")
        else:
            logger.error(
                f"HTTP error {e.response.status_code} fetching token {token_id}: {e}"
            )
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
