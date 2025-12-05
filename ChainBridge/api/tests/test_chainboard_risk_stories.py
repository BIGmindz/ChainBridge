# api/tests/test_chainboard_risk_stories.py
"""
Tests for ChainIQ Risk Stories Endpoint
=======================================

Validates the /api/chainboard/iq/risk-stories endpoint.
"""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_get_risk_stories():
    """Test that risk stories endpoint returns valid structure."""
    response = client.get("/api/chainboard/iq/risk-stories")

    assert response.status_code == 200
    data = response.json()

    # Validate envelope structure
    assert "stories" in data
    assert "total" in data
    assert "generated_at" in data

    # Validate counts
    assert isinstance(data["stories"], list)
    assert data["total"] == len(data["stories"])
    assert data["total"] > 0  # Should have stories from mock data


def test_risk_story_has_required_fields():
    """Test that each story has all required fields with valid data."""
    response = client.get("/api/chainboard/iq/risk-stories")
    assert response.status_code == 200

    stories = response.json()["stories"]
    assert len(stories) > 0

    for story in stories:
        # Required fields
        assert "shipment_id" in story
        assert "reference" in story
        assert "corridor" in story
        assert "risk_category" in story
        assert "score" in story
        assert "primary_factor" in story
        assert "factors" in story
        assert "summary" in story
        assert "recommended_action" in story
        assert "last_updated" in story

        # Validate types and constraints
        assert isinstance(story["shipment_id"], str)
        assert len(story["shipment_id"]) > 0

        assert isinstance(story["reference"], str)
        assert len(story["reference"]) > 0

        assert story["risk_category"] in ["low", "medium", "high"]

        assert isinstance(story["score"], int)
        assert 0 <= story["score"] <= 100

        assert story["primary_factor"] in [
            "route_volatility",
            "carrier_history",
            "document_issues",
            "iot_anomalies",
            "payment_behavior",
        ]

        assert isinstance(story["factors"], list)
        assert len(story["factors"]) > 0

        assert isinstance(story["summary"], str)
        assert len(story["summary"]) > 10  # Should be a real narrative

        assert isinstance(story["recommended_action"], str)
        assert len(story["recommended_action"]) > 5


def test_risk_stories_sorted_by_score():
    """Test that stories are sorted by risk score descending (highest first)."""
    response = client.get("/api/chainboard/iq/risk-stories")
    assert response.status_code == 200

    stories = response.json()["stories"]

    if len(stories) > 1:
        scores = [story["score"] for story in stories]
        # Verify descending order
        assert scores == sorted(scores, reverse=True)


def test_risk_stories_limit_parameter():
    """Test that limit parameter restricts story count."""
    # Get full list
    response_full = client.get("/api/chainboard/iq/risk-stories?limit=100")
    assert response_full.status_code == 200
    full_count = len(response_full.json()["stories"])

    # Get limited list
    limit = min(5, full_count)
    response_limited = client.get(f"/api/chainboard/iq/risk-stories?limit={limit}")
    assert response_limited.status_code == 200

    data = response_limited.json()
    assert len(data["stories"]) == limit


def test_risk_stories_all_factors_valid():
    """Test that all factor enums are valid."""
    response = client.get("/api/chainboard/iq/risk-stories")
    assert response.status_code == 200

    valid_factors = {
        "route_volatility",
        "carrier_history",
        "document_issues",
        "iot_anomalies",
        "payment_behavior",
    }

    stories = response.json()["stories"]
    for story in stories:
        for factor in story["factors"]:
            assert factor in valid_factors, f"Invalid factor: {factor}"
