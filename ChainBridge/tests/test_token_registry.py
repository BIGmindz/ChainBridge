"""Registry tests for Cody's token factory."""

from chainbridge.tokens import create_token
from chainbridge.tokens.base_token import TokenValidationError


def _shipment_payload():
    return {
        "origin": "LAX",
        "destination": "JFK",
        "carrier_id": "CARRIER-123",
        "broker_id": "BROKER-45",
        "customer_id": "SHIPPER-99",
    }


def test_create_token_returns_expected_type():
    token = create_token(
        "ST-01",
        parent_shipment_id="SHP-1",
        metadata=_shipment_payload(),
    )
    assert token.token_type == "ST-01"
    assert token.state == "CREATED"


def test_create_token_rejects_unknown_type():
    try:
        create_token(
            "UNKNOWN",
            parent_shipment_id="SHP-1",
            metadata=_shipment_payload(),
        )
    except TokenValidationError as exc:
        assert "Unknown token_type" in str(exc)
    else:  # pragma: no cover - defensive fallback
        raise AssertionError("TokenValidationError not raised")
