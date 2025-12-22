"""Demo fuel surcharge calculator."""
from decimal import Decimal

def calculate_fuel_multiplier(diesel_index: float) -> Decimal:
    base = Decimal(str(diesel_index or 0))
    if base <= 0:
        return Decimal("1.00")
    return Decimal("1.00") + (base / Decimal("100"))
