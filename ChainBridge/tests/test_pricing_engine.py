from decimal import Decimal

from api.pricing.engine import calculate_price


class DummyShipment:
    def __init__(self, corridor_code: str, mode: str, incoterm: str = "FOB"):
        self.corridor_code = corridor_code
        self.mode = mode
        self.incoterm = incoterm


class DummySnapshot:
    def __init__(self, risk_score: int):
        self.risk_score = risk_score


def test_pricing_engine_happy_path():
    shipment = DummyShipment("CN-US", "OCEAN")
    snapshot = DummySnapshot(50)
    result = calculate_price(shipment, snapshot)
    assert result.base_rate == Decimal("1200.00")
    assert result.total_price > result.base_rate


def test_pricing_engine_unknown_corridor_graceful():
    shipment = DummyShipment("XX-YY", "ROAD", incoterm="DAP")
    snapshot = DummySnapshot(10)
    result = calculate_price(shipment, snapshot)
    assert result.base_rate == Decimal("0")
    assert result.total_price == result.fuel_surcharge + result.accessorials + result.volatility_buffer
