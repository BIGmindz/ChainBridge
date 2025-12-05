"""Lifecycle tests for tokens."""

import pytest

from chainbridge.tokens.at02 import AT02Token
from chainbridge.tokens.base_token import (
    InvalidTransitionError,
    RelationValidationError,
    TokenValidationError,
)
from chainbridge.tokens.dt01 import DT01Token
from chainbridge.tokens.serialization import deserialize, serialize
from chainbridge.tokens.st01 import ST01Token


@pytest.fixture
def shipment_meta() -> dict:
    return {
        "origin": "DFW",
        "destination": "BOS",
        "carrier_id": "C-9",
        "broker_id": "B-2",
        "customer_id": "SHIP-77",
    }


def test_st01_lifecycle_happy_path(shipment_meta):
    token = ST01Token(parent_shipment_id="SHP-9", metadata=shipment_meta)
    for state in ["DISPATCHED", "IN_TRANSIT", "ARRIVED", "DELIVERED"]:
        token.transition(state)
    token.relations["pt01_ids"] = ["PT-22"]
    token.transition("SETTLED")
    token.metadata["claims_closed_at"] = "2025-02-01T00:00:00Z"
    token.transition("CLOSED")
    assert token.state == "CLOSED"


def test_st01_requires_payment_before_settled(shipment_meta):
    token = ST01Token(parent_shipment_id="SHP-19", metadata=shipment_meta)
    for state in ["DISPATCHED", "IN_TRANSIT", "ARRIVED", "DELIVERED"]:
        token.transition(state)
    with pytest.raises(RelationValidationError):
        token.transition("SETTLED")


def test_at02_requires_proof_before_verification():
    token = AT02Token(
        parent_shipment_id="SHP-33",
        metadata={
            "accessorial_type": "DETENTION",
            "amount": 300.0,
            "timestamp": "2025-01-02T10:00:00Z",
            "actor": "carrier",
            "currency": "USD",
        },
        relations={"mt01_id": "MT-5"},
    )
    with pytest.raises(TokenValidationError):
        token.transition("PROOF_ATTACHED")

    token.attach_proof(proof_hash="abc123", metadata={"duration_minutes": 45})
    token.metadata["policy_match_id"] = "ALEX-DET-1"
    token.transition("VERIFIED")
    token.transition("PUBLISHED")
    assert token.state == "PUBLISHED"


def test_dt01_requires_pt01_relation():
    with pytest.raises(RelationValidationError):
        DT01Token(
            parent_shipment_id="SHP-10",
            metadata={
                "dispute_code": "DAMAGED",
                "reason": "Pallet shrink wrap torn",
                "actor": "shipper",
                "raised_at": "2025-03-01T09:00:00Z",
            },
            relations={"it01_id": "INV-9"},
        )


def test_serialization_round_trip(shipment_meta):
    token = ST01Token(parent_shipment_id="SHP-51", metadata=shipment_meta)
    payload = serialize(token)
    hydrated = deserialize(payload)
    assert hydrated.token_id == token.token_id
    assert hydrated.metadata == token.metadata
    assert hydrated.relations == token.relations
    assert hydrated.state == token.state
