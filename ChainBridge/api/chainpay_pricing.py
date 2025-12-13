"""ChainPay pricing wrapper."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict

from api.pricing.engine import calculate_price

logger = logging.getLogger(__name__)

try:  # Prefer real Chainlink client when available
    from app.services.oracle.chainlink_client import estimate_gas_cost  # type: ignore
except Exception as exc:  # pragma: no cover - fallback for sandbox/tests
    logger.warning("Using stubbed chainlink gas estimator: %s", exc)

    def estimate_gas_cost() -> float:
        """Return a deterministic placeholder gas cost for test environments."""
        return 0.0


def calculate_pricing_for_intent(shipment: Any, risk_snapshot: Any) -> Dict[str, float]:
    result = calculate_price(shipment, risk_snapshot)
    chainlink_raw = result.chainlink_gas_cost if result.chainlink_gas_cost is not None else Decimal(str(estimate_gas_cost()))
    chainlink_gas = Decimal(str(chainlink_raw))
    total_price = (result.total_price if isinstance(result.total_price, Decimal) else Decimal(str(result.total_price))) + chainlink_gas
    components = {
        "base_rate": float(result.base_rate),
        "fuel_surcharge": float(result.fuel_surcharge),
        "accessorials": float(result.accessorials),
        "volatility_buffer": float(result.volatility_buffer),
        "chainlink_gas_cost": float(chainlink_gas),
        "total_price": float(total_price),
    }
    pct_of_total = {}
    for key, val in components.items():
        if key == "total_price" or total_price == 0:
            continue
        pct_of_total[key] = round((val / components["total_price"] * 100) if components["total_price"] else 0, 2)
    components["pct_of_total"] = pct_of_total
    return components
