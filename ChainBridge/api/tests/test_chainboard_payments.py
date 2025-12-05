"""
ChainBoard ChainPay Payment Queue Tests
========================================

Tests for the payment hold queue endpoint.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_get_payment_queue():
    """Test GET /api/chainboard/pay/queue returns payment queue."""
    response = client.get("/api/chainboard/pay/queue")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "items" in data
    assert "total_items" in data
    assert "total_holds_usd" in data
    assert "generated_at" in data

    # Validate consistency
    assert data["total_items"] == len(data["items"])

    # Validate total_holds_usd matches sum of holds
    if data["items"]:
        calculated_total = sum(Decimal(item["holds_usd"]) for item in data["items"])
        assert Decimal(data["total_holds_usd"]) == calculated_total


def test_payment_queue_items_have_required_fields():
    """Test that queue items have all required fields."""
    response = client.get("/api/chainboard/pay/queue")

    assert response.status_code == 200
    data = response.json()

    required_fields = [
        "shipment_id",
        "reference",
        "corridor",
        "customer",
        "total_value_usd",
        "holds_usd",
        "released_usd",
        "aging_days",
    ]

    for item in data["items"]:
        for field in required_fields:
            assert field in item

        # Validate aging_days is non-negative
        assert item["aging_days"] >= 0

        # Validate monetary values are positive
        assert Decimal(item["holds_usd"]) >= 0
        assert Decimal(item["total_value_usd"]) >= 0
        assert Decimal(item["released_usd"]) >= 0


def test_payment_queue_only_includes_holds():
    """Test that queue only includes shipments with holds_usd > 0."""
    response = client.get("/api/chainboard/pay/queue")

    assert response.status_code == 200
    data = response.json()

    for item in data["items"]:
        assert Decimal(item["holds_usd"]) > 0, f"Item {item['shipment_id']} has no holds"


def test_payment_queue_limit_parameter():
    """Test that limit parameter restricts queue size."""
    # Get full queue
    response_full = client.get("/api/chainboard/pay/queue?limit=100")
    assert response_full.status_code == 200
    full_data = response_full.json()
    full_count = len(full_data["items"])

    # Get limited queue
    limit = min(5, full_count)
    if limit > 0:
        response_limited = client.get(f"/api/chainboard/pay/queue?limit={limit}")
        assert response_limited.status_code == 200
        limited_data = response_limited.json()

        assert len(limited_data["items"]) <= limit


def test_payment_queue_sorted_by_holds():
    """Test that queue items are sorted by holds_usd descending."""
    response = client.get("/api/chainboard/pay/queue")

    assert response.status_code == 200
    data = response.json()

    if len(data["items"]) > 1:
        holds_values = [Decimal(item["holds_usd"]) for item in data["items"]]

        # Verify descending order
        for i in range(len(holds_values) - 1):
            assert holds_values[i] >= holds_values[i + 1], f"Queue not sorted: {holds_values[i]} < {holds_values[i + 1]}"
