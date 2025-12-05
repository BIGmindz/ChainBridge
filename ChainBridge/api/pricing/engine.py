"""Pricing engine core."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

from api.pricing.accessorials import calculate_accessorials
from api.pricing.fuel_surcharge import calculate_fuel_multiplier
from api.pricing.rate_card import get_base_rate
from api.pricing.volatility import calculate_volatility_buffer


@dataclass
class PricingResult:
    base_rate: Decimal
    fuel_surcharge: Decimal
    accessorials: Decimal
    volatility_buffer: Decimal
    chainlink_gas_cost: Decimal
    total_price: Decimal

    def to_dict(self) -> Dict[str, str]:
        return {
            "base_rate": str(self.base_rate),
            "fuel_surcharge": str(self.fuel_surcharge),
            "accessorials": str(self.accessorials),
            "volatility_buffer": str(self.volatility_buffer),
            "chainlink_gas_cost": str(self.chainlink_gas_cost),
            "total_price": str(self.total_price),
        }


def calculate_price(shipment: Any, risk_snapshot: Any) -> PricingResult:
    corridor = getattr(shipment, "corridor_code", None) or ""
    mode = getattr(shipment, "mode", None) or ""
    base_rate = get_base_rate(corridor, mode)
    accessorials = calculate_accessorials(shipment)
    risk_score = getattr(risk_snapshot, "risk_score", 0) or 0
    fuel_multiplier = calculate_fuel_multiplier(0)
    volatility_buffer = calculate_volatility_buffer(int(risk_score), base_rate)
    subtotal = base_rate + accessorials
    chainlink_gas_cost = Decimal("0.00")
    total = (subtotal * fuel_multiplier) + volatility_buffer
    return PricingResult(
        base_rate=base_rate,
        fuel_surcharge=(subtotal * fuel_multiplier) - subtotal,
        accessorials=accessorials,
        volatility_buffer=volatility_buffer,
        chainlink_gas_cost=chainlink_gas_cost,
        total_price=total,
    )
