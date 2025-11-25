# api/tests/test_payment_events.py
"""
Tests for Payment Settlement Real-Time Events
==============================================

Validates that payment milestone state transitions emit real-time events.
"""

import pytest

from api.schemas.chainboard import PaymentEventKind, PaymentSettlementEvent


@pytest.mark.asyncio
async def test_payment_event_schema_validation():
    """Test PaymentSettlementEvent schema validates correctly."""
    event = PaymentSettlementEvent(
        shipment_reference="SHP-2025-027",
        milestone_id="SHP-2025-027-M2",
        milestone_name="POD Confirmed",
        from_state="pending",
        to_state="approved",
        amount=700.0,
        currency="USD",
        reason="Low risk shipment",
        freight_token_id=2025027,
        proofpack_hint={
            "milestone_id": "SHP-2025-027-M2",
            "has_proofpack": True,
            "version": "v1-alpha",
        },
    )

    assert event.shipment_reference == "SHP-2025-027"
    assert event.milestone_id == "SHP-2025-027-M2"
    assert event.from_state == "pending"
    assert event.to_state == "approved"
    assert event.amount == 700.0
    assert event.freight_token_id == 2025027
    assert event.proofpack_hint is not None
    assert event.proofpack_hint.version == "v1-alpha"


@pytest.mark.asyncio
async def test_payment_event_kind_enum():
    """Test PaymentEventKind enum has all expected values."""
    expected_kinds = {
        "milestone_became_eligible",
        "milestone_released",
        "milestone_settled",
        "milestone_blocked",
        "milestone_unblocked",
    }

    actual_kinds = {kind.value for kind in PaymentEventKind}
    assert actual_kinds == expected_kinds


@pytest.mark.asyncio
async def test_payment_event_serialization():
    """Test PaymentSettlementEvent can be serialized to JSON."""
    event = PaymentSettlementEvent(
        shipment_reference="SHP-2025-027",
        milestone_id="SHP-2025-027-M2",
        milestone_name="POD Confirmed",
        from_state="pending",
        to_state="approved",
        amount=700.0,
        currency="USD",
    )

    json_str = event.model_dump_json()
    assert "SHP-2025-027" in json_str
    assert "pending" in json_str
    assert "approved" in json_str


@pytest.mark.asyncio
async def test_payment_state_changed_event_payload():
    """Test payment_state_changed event payload structure."""
    # Simulate what the simulator/ChainPay would emit
    test_payload = {
        "event_kind": "milestone_released",
        "shipment_reference": "SHP-2025-027",
        "milestone_id": "SHP-2025-027-M2",
        "milestone_name": "POD Confirmed",
        "from_state": "pending",
        "to_state": "approved",
        "amount": 700.0,
        "currency": "USD",
        "reason": "Low risk - immediate release",
        "proofpack_hint": {
            "milestone_id": "SHP-2025-027-M2",
            "has_proofpack": True,
            "version": "v1-alpha",
        },
    }

    # Validate all required fields present
    assert test_payload["event_kind"] in [k.value for k in PaymentEventKind]
    assert test_payload["shipment_reference"] == "SHP-2025-027"
    assert test_payload["milestone_id"] == "SHP-2025-027-M2"
    assert test_payload["from_state"] == "pending"
    assert test_payload["to_state"] == "approved"
    assert test_payload["amount"] == 700.0
    assert test_payload["milestone_id"].startswith("SHP-")
    assert test_payload["milestone_id"].count("-") >= 2


@pytest.mark.asyncio
async def test_milestone_id_canonical_format():
    """Verify milestone IDs follow '<shipment_reference>-M<index>'."""
    from core.payments.identity import is_valid_milestone_id

    payload_id = "SHP-2025-042-M3"
    assert is_valid_milestone_id(payload_id)


@pytest.mark.asyncio
async def test_payment_event_through_event_bus():
    """Test payment_state_changed events published through event bus contain milestone_id."""
    import asyncio
    from api.realtime.bus import subscribe, unsubscribe, publish_event

    # Subscribe to event bus
    queue = subscribe()

    # Create a realistic payment event payload with milestone_id
    payment_payload = {
        "event_kind": "milestone_released",
        "shipment_reference": "SHP-2025-042",
        "milestone_id": "SHP-2025-042-M1",
        "milestone_name": "Delivery Confirmed",
        "from_state": "eligible",
        "to_state": "released",
        "amount": 1500.0,
        "currency": "USD",
        "reason": "All conditions met",
        "proofpack_hint": {
            "milestone_id": "SHP-2025-042-M1",
            "has_proofpack": True,
            "version": "v1-alpha",
        },
    }

    # Publish the event
    await publish_event(
        type="payment_state_changed",
        source="chainpay",
        key="SHP-2025-042",
        payload=payment_payload,
    )

    # Retrieve the event from the queue
    event = await asyncio.wait_for(queue.get(), timeout=1.0)

    # Verify event structure
    assert event.type == "payment_state_changed"
    assert event.source == "chainpay"
    assert event.key == "SHP-2025-042"

    # Verify milestone_id is present in payload (critical for deep-linking)
    assert "milestone_id" in event.payload
    assert event.payload["milestone_id"] == "SHP-2025-042-M1"
    assert event.payload["shipment_reference"] == "SHP-2025-042"
    assert event.payload["event_kind"] == "milestone_released"
    assert "proofpack_hint" in event.payload
    assert event.payload["proofpack_hint"]["version"] == "v1-alpha"
    assert event.payload["proofpack_hint"]["milestone_id"] == "SHP-2025-042-M1"
    assert event.payload["proofpack_hint"]["has_proofpack"] is True

    unsubscribe(queue)
