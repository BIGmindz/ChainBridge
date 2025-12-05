from fastapi.testclient import TestClient


def test_get_settlement_status_returns_mock_structure(client: TestClient):
    shipment_id = "SHIP-12345"

    response = client.get(f"/api/chainpay/settlements/{shipment_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["shipment_id"] == shipment_id

    cb_usd = data["cb_usd"]
    assert cb_usd["total"] == cb_usd["released"] + cb_usd["reserved"]
    assert cb_usd["released"] <= cb_usd["total"]

    events = data["events"]
    assert isinstance(events, list) and len(events) >= 1

    milestones = {event["milestone"] for event in events}
    assert "PICKUP" in milestones
    assert data["current_milestone"] in milestones

    assert data["settlement_provider"] == "INTERNAL_LEDGER"

    risk_score = data.get("risk_score")
    assert risk_score is None or isinstance(risk_score, (int, float))
