"""
Token Event Flow Tests — PAX (GID-05)
"""
import pytest

from chainpay_service.app.services.token_event_publisher import publish_token_event

@pytest.mark.asyncio
async def test_publish_token_event_payload():
    payload = await publish_token_event(
        event_type="TOKEN_EARNED",
        shipment_id="SHIP123",
        token_amount=200,
        burn_amount=0,
        risk_multiplier=1.1,
        ml_adjustment=1.0,
        severity="LOW",
        rationale="Test event",
        trace_id="abc123"
    )
    assert payload["event_type"] == "TOKEN_EARNED"
    assert payload["canonical_shipment_id"] == "SHIP123"
    assert payload["token_amount"] == 200
    assert payload["burn_amount"] == 0
    assert payload["risk_multiplier"] == 1.1
    assert payload["ml_adjustment"] == 1.0
    assert payload["severity"] == "LOW"
    assert payload["rationale"] == "Test event"
    assert payload["trace_id"] == "abc123"
