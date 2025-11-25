from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_get_risk_overview():
    response = client.get("/api/chainboard/risk/overview")
    assert response.status_code == 200

    payload = response.json()
    assert "overview" in payload
    overview = payload["overview"]

    expected_fields = [
        "total_shipments",
        "high_risk_shipments",
        "total_value_usd",
        "average_risk_score",
        "updated_at",
    ]

    for field in expected_fields:
        assert field in overview

    assert overview["total_shipments"] >= overview["high_risk_shipments"] >= 0
    assert overview["average_risk_score"] >= 0
