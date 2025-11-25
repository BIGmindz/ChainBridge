"""Demo rate card lookups."""
from decimal import Decimal
from typing import Dict, Tuple

_RATE_CARD: Dict[Tuple[str, str], Decimal] = {
    ("CN-US", "OCEAN"): Decimal("1200.00"),
    ("DE-UK", "AIR"): Decimal("800.00"),
}

def get_base_rate(corridor: str, mode: str) -> Decimal:
    key = (corridor or "").upper(), (mode or "").upper()
    return _RATE_CARD.get(key, Decimal("0"))
