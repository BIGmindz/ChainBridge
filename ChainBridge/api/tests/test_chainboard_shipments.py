from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_get_shipments_returns_canonical_payload():
    response = client.get("/api/chainboard/shipments")
    assert response.status_code == 200

    payload = response.json()
    assert "shipments" in payload
    assert "total" in payload
    assert "filtered" in payload
    assert isinstance(payload["shipments"], list)
    assert isinstance(payload["filtered"], bool)
    assert payload["total"] >= len(payload["shipments"])

    if payload["shipments"]:
        shipment = payload["shipments"][0]
        required_fields = [
            "id",
            "reference",
            "status",
            "origin",
            "destination",
            "corridor",
            "risk",
            "payment",
            "governance",
        ]
        for field in required_fields:
            assert field in shipment, f"Expected '{field}' in shipment payload"

        # Validate payment fields
        payment = shipment["payment"]
        assert "total_value_usd" in payment
        assert "released_usd" in payment
        assert "released_percentage" in payment
        assert "holds_usd" in payment

        # Validate payment invariants
        total = float(payment["total_value_usd"])
        released = float(payment["released_usd"])
        holds = float(payment["holds_usd"])
        released_pct = payment["released_percentage"]

        assert released <= total, "released_usd must be <= total_value_usd"
        assert holds <= total, "holds_usd must be <= total_value_usd"
        assert 0 <= released_pct <= 100, "released_percentage must be 0-100"

        # Validate corridor exists
        assert shipment["corridor"], "corridor field must not be empty"


def test_get_single_shipment_round_trip():
    list_response = client.get("/api/chainboard/shipments")
    assert list_response.status_code == 200
    shipments = list_response.json().get("shipments", [])
    assert shipments, "Fixture should expose at least one shipment"

    shipment_id = shipments[0]["id"]
    detail_response = client.get(f"/api/chainboard/shipments/{shipment_id}")
    assert detail_response.status_code == 200

    shipment = detail_response.json()
    assert shipment["id"] == shipment_id
    assert shipment["risk"]["score"] >= 0
    assert "corridor" in shipment
    assert shipment["corridor"], "Corridor must not be empty"

    payment = shipment["payment"]
    total_value = float(payment["total_value_usd"])
    released_value = float(payment["released_usd"])
    assert total_value >= 0
    assert released_value >= 0
    assert released_value <= total_value


def test_get_shipments_supports_risk_filter():
    response = client.get("/api/chainboard/shipments", params={"risk": "high"})
    assert response.status_code == 200
    payload = response.json()
    for shipment in payload["shipments"]:
        assert shipment["risk"]["category"] == "high"


def test_get_shipments_supports_corridor_filter():
    """Validate corridor filtering works with partial string matching"""
    # Get all shipments first
    all_response = client.get("/api/chainboard/shipments")
    assert all_response.status_code == 200
    all_shipments = all_response.json()["shipments"]
    assert len(all_shipments) > 0, "Fixtures should have at least one shipment"

    # Get a corridor value from first shipment
    test_corridor = all_shipments[0]["corridor"]
    # Use a substring of the corridor for partial matching
    search_term = test_corridor.split()[0]  # e.g., "Shanghai" from "Shanghai → Los Angeles"

    response = client.get("/api/chainboard/shipments", params={"corridor": search_term})
    assert response.status_code == 200
    payload = response.json()

    # All returned shipments should contain the search term
    for shipment in payload["shipments"]:
        assert search_term.lower() in shipment["corridor"].lower(), \
            f"Expected '{search_term}' in corridor '{shipment['corridor']}'"
