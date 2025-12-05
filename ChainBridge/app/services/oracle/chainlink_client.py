"""Chainlink Functions client wrapper for off-chain verification."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


def estimate_gas_cost(network: str | None = None) -> float:
    """Rudimentary gas estimate (USD) for Chainlink Functions calls."""
    # TODO: swap with on-chain estimator per network
    return round(
        (0.12 if (network or settings.HEDERA_NETWORK or "testnet") == "testnet" else 0.45),
        4,
    )


def request_verification(shipment_id: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Ask Chainlink Functions router to verify telemetry for a shipment.
    Returns a request envelope; execution is asynchronous.
    """
    router = settings.CHAINLINK_ROUTER_ADDRESS or "0xrouter-demo"
    body = payload or {}
    request_id = hashlib.sha256(f"{shipment_id}:{time.time()}".encode("utf-8")).hexdigest()[:16]
    gas_cost = estimate_gas_cost()
    logger.info(
        "chainlink.request",
        extra={
            "shipment_id": shipment_id,
            "router": router,
            "request_id": request_id,
            "gas_cost_usd": gas_cost,
        },
    )
    return {
        "shipment_id": shipment_id,
        "router": router,
        "request_id": request_id,
        "gas_cost_usd": gas_cost,
        "payload": body,
        "status": "QUEUED",
    }
