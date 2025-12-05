"""Volatility buffer calculator."""

from decimal import Decimal


def calculate_volatility_buffer(risk_score: int, base_rate: Decimal) -> Decimal:
    score = risk_score or 0
    factor = Decimal(score) / Decimal(100)
    return (base_rate * factor * Decimal("0.1")).quantize(Decimal("0.01")) if base_rate else Decimal("0")
