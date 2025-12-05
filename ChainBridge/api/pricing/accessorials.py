"""Demo accessorial charges."""

from decimal import Decimal
from typing import Any


def calculate_accessorials(shipment: Any) -> Decimal:
    # Simple flat demo fee when shipment has incoterm FOB
    incoterm = getattr(shipment, "incoterm", None) or ""
    if incoterm.upper() == "FOB":
        return Decimal("50.00")
    return Decimal("0")
