"""Tests for the Risk API endpoints (ChainIQ Gateway).

Tests cover:
- Risk scoring with DecisionRecord creation
- Risk simulation with DecisionRecord creation
- Health check endpoint
- Error handling when ChainIQ is unavailable

The tests mock the ChainIQ client to avoid external dependencies.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.decision_record import DecisionRecord as DecisionRecordModel
from api.schemas.risk import (
    RiskHealthResponse,
    RiskScoreResponse,
    RiskSimulationResponse,
    RiskSimulationVariantResult,
    ShipmentRiskAssessment,
    TopFactor,
)
from api.server import app

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create a test client with the test database."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_mock_assessment(
    shipment_id: str,
    risk_score: float = 45.0,
    decision: str = "APPROVE",
) -> ShipmentRiskAssessment:
    """Create a mock ShipmentRiskAssessment for testing."""
    return ShipmentRiskAssessment(
        shipment_id=shipment_id,
        assessed_at=datetime.utcnow(),
        model_version="chainiq-v0.1-test",
        risk_score=risk_score,
        operational_risk=risk_score * 0.4,
        financial_risk=risk_score * 0.3,
        fraud_risk=risk_score * 0.2,
        esg_risk=risk_score * 0.1,
        resilience_score=100 - risk_score,
        decision=decision,
        confidence=0.85,
        top_factors=[
            TopFactor(
                name="lane_incident_rate",
                description="Historical lane incident rate is elevated",
                direction="UP",
                weight=35.5,
            ),
            TopFactor(
                name="carrier_reliability",
                description="Carrier has good track record",
                direction="DOWN",
                weight=20.0,
            ),
        ],
        summary_reason=f"Risk assessment: score {risk_score}, decision {decision}",
        tags=["TEST", "MOCK"],
        data_quality_score=0.95,
    )


def _make_mock_score_response(shipment_ids: list[str]) -> RiskScoreResponse:
    """Create a mock RiskScoreResponse for testing."""
    assessments = [_make_mock_assessment(sid, risk_score=30 + i * 15) for i, sid in enumerate(shipment_ids)]
    return RiskScoreResponse(
        assessments=assessments,
        meta={"processing_time_ms": 150, "model_version": "chainiq-v0.1-test"},
    )


def _make_mock_simulation_response(
    base_shipment_id: str,
    variation_names: list[str],
) -> RiskSimulationResponse:
    """Create a mock RiskSimulationResponse for testing."""
    base = _make_mock_assessment(base_shipment_id, risk_score=55.0, decision="TIGHTEN_TERMS")
    variations = [
        RiskSimulationVariantResult(
            name=name,
            assessment=_make_mock_assessment(
                base_shipment_id,
                risk_score=55.0 - (i + 1) * 10,
                decision="APPROVE" if i > 0 else "TIGHTEN_TERMS",
            ),
            delta_risk_score=-(i + 1) * 10.0,
        )
        for i, name in enumerate(variation_names)
    ]
    return RiskSimulationResponse(
        base_assessment=base,
        variation_assessments=variations,
        recommendation=f"Consider {variation_names[-1]}" if variation_names else None,
    )


# =============================================================================
# TEST: RISK SCORING
# =============================================================================


class TestRiskScore:
    """Tests for POST /api/v1/risk/score."""

    @patch("api.routes.risk.chainiq_client.score_shipments")
    def test_risk_score_creates_decision_records(self, mock_score, client, test_db):
        """Risk scoring should create a DecisionRecord for each assessment."""
        # Setup mock
        mock_score.return_value = _make_mock_score_response(["SHP-001", "SHP-002"])

        # Make request
        response = client.post(
            "/api/v1/risk/score",
            json={
                "shipments": [
                    {
                        "shipment_id": "SHP-001",
                        "mode": "OCEAN",
                        "origin_country": "CN",
                        "destination_country": "US",
                        "planned_departure": "2024-12-01T08:00:00Z",
                        "planned_arrival": "2024-12-21T18:00:00Z",
                    },
                    {
                        "shipment_id": "SHP-002",
                        "mode": "AIR",
                        "origin_country": "DE",
                        "destination_country": "US",
                        "planned_departure": "2024-12-05T10:00:00Z",
                        "planned_arrival": "2024-12-06T14:00:00Z",
                    },
                ],
                "include_factors": True,
                "max_factors": 3,
            },
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert len(data["assessments"]) == 2
        assert data["assessments"][0]["shipment_id"] == "SHP-001"
        assert data["assessments"][1]["shipment_id"] == "SHP-002"

        # Assert DecisionRecords were created
        records = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.type == "RISK_ASSESSMENT").all()
        assert len(records) == 2

        # Check first record
        rec1 = next(r for r in records if r.entity_id == "SHP-001")
        assert rec1.tenant_id == "default-tenant"
        assert rec1.actor_type == "SYSTEM"
        assert rec1.actor_id == "CHAINIQ"
        assert rec1.entity_type == "SHIPMENT"
        assert "risk_score" in rec1.outputs
        assert "decision" in rec1.outputs
        assert "top_factors" in rec1.outputs
        assert "model_version" in rec1.outputs

    @patch("api.routes.risk.chainiq_client.score_shipments")
    def test_risk_score_response_shape(self, mock_score, client, test_db):
        """Response should match expected schema with all fields."""
        mock_score.return_value = _make_mock_score_response(["SHP-TEST"])

        response = client.post(
            "/api/v1/risk/score",
            json={
                "shipments": [
                    {
                        "shipment_id": "SHP-TEST",
                        "mode": "TRUCK",
                        "origin_country": "US",
                        "destination_country": "CA",
                        "planned_departure": "2024-12-01T08:00:00Z",
                        "planned_arrival": "2024-12-02T18:00:00Z",
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "assessments" in data
        assert "meta" in data

        # Check assessment fields
        assessment = data["assessments"][0]
        assert "shipment_id" in assessment
        assert "risk_score" in assessment
        assert "decision" in assessment
        assert "confidence" in assessment
        assert "top_factors" in assessment
        assert "summary_reason" in assessment
        assert "tags" in assessment

        # Check top_factors structure
        factor = assessment["top_factors"][0]
        assert "name" in factor
        assert "description" in factor
        assert "direction" in factor
        assert "weight" in factor

    @patch("api.routes.risk.chainiq_client.score_shipments")
    def test_risk_score_decision_record_no_pii(self, mock_score, client, test_db):
        """DecisionRecord details should not contain raw PII."""
        mock_score.return_value = _make_mock_score_response(["SHP-PII-TEST"])

        response = client.post(
            "/api/v1/risk/score",
            json={
                "shipments": [
                    {
                        "shipment_id": "SHP-PII-TEST",
                        "mode": "OCEAN",
                        "origin_country": "CN",
                        "destination_country": "US",
                        "planned_departure": "2024-12-01T08:00:00Z",
                        "planned_arrival": "2024-12-21T18:00:00Z",
                        "value_usd": 500000,  # This is aggregate, not PII
                    },
                ],
            },
        )

        assert response.status_code == 200

        # Check DecisionRecord details
        record = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.entity_id == "SHP-PII-TEST").first()
        assert record is not None

        # Details should have safe fields only
        details = record.outputs
        assert "risk_score" in details
        assert "decision" in details
        assert "confidence" in details
        assert "tags" in details
        assert "top_factors" in details

        # Should NOT have raw PII fields
        # (names, emails, addresses, customer data)
        pii_fields = ["customer_name", "email", "phone", "address", "ssn"]
        for field in pii_fields:
            assert field not in details


# =============================================================================
# TEST: RISK SIMULATION
# =============================================================================


class TestRiskSimulation:
    """Tests for POST /api/v1/risk/simulation."""

    @patch("api.routes.risk.chainiq_client.simulate_risk")
    def test_simulation_returns_variations(self, mock_sim, client, test_db):
        """Simulation should return base and variation assessments."""
        mock_sim.return_value = _make_mock_simulation_response(
            "SHP-SIM-001",
            ["alt_carrier", "earlier_departure"],
        )

        response = client.post(
            "/api/v1/risk/simulation",
            json={
                "base_context": {
                    "shipment_id": "SHP-SIM-001",
                    "mode": "OCEAN",
                    "origin_country": "CN",
                    "destination_country": "US",
                    "planned_departure": "2024-12-01T08:00:00Z",
                    "planned_arrival": "2024-12-21T18:00:00Z",
                    "carrier_code": "MAEU",
                },
                "variations": [
                    {"name": "alt_carrier", "overrides": {"carrier_code": "COSCO"}},
                    {"name": "earlier_departure", "overrides": {"planned_departure": "2024-11-25T08:00:00Z"}},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "base_assessment" in data
        assert "variation_assessments" in data
        assert len(data["variation_assessments"]) == 2

        # Check variation results
        var1 = data["variation_assessments"][0]
        assert var1["name"] == "alt_carrier"
        assert "delta_risk_score" in var1
        assert var1["delta_risk_score"] != 0

    @patch("api.routes.risk.chainiq_client.simulate_risk")
    def test_simulation_creates_decision_record(self, mock_sim, client, test_db):
        """Simulation should create a DecisionRecord summarizing the analysis."""
        mock_sim.return_value = _make_mock_simulation_response(
            "SHP-SIM-002",
            ["alt_route"],
        )

        response = client.post(
            "/api/v1/risk/simulation",
            json={
                "base_context": {
                    "shipment_id": "SHP-SIM-002",
                    "mode": "TRUCK",
                    "origin_country": "US",
                    "destination_country": "MX",
                    "planned_departure": "2024-12-01T08:00:00Z",
                    "planned_arrival": "2024-12-03T18:00:00Z",
                },
                "variations": [
                    {"name": "alt_route", "overrides": {"destination_region": "Monterrey"}},
                ],
            },
        )

        assert response.status_code == 200

        # Check DecisionRecord was created
        record = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.type == "RISK_SIMULATION").first()
        assert record is not None
        assert record.entity_id == "SHP-SIM-002"
        assert record.actor_id == "CHAINIQ"

        # Check record outputs
        outputs = record.outputs
        assert "base_risk_score" in outputs
        assert "base_decision" in outputs
        assert "variations" in outputs
        assert "best_variation" in outputs

    @patch("api.routes.risk.chainiq_client.simulate_risk")
    def test_simulation_recommendation(self, mock_sim, client, test_db):
        """Simulation should include recommendation if provided."""
        mock_sim.return_value = _make_mock_simulation_response(
            "SHP-SIM-003",
            ["option_a", "option_b"],
        )

        response = client.post(
            "/api/v1/risk/simulation",
            json={
                "base_context": {
                    "shipment_id": "SHP-SIM-003",
                    "mode": "AIR",
                    "origin_country": "JP",
                    "destination_country": "US",
                    "planned_departure": "2024-12-01T08:00:00Z",
                    "planned_arrival": "2024-12-02T18:00:00Z",
                },
                "variations": [
                    {"name": "option_a", "overrides": {"carrier_code": "JAL"}},
                    {"name": "option_b", "overrides": {"carrier_code": "ANA"}},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data


# =============================================================================
# TEST: HEALTH CHECK
# =============================================================================


class TestRiskHealth:
    """Tests for GET /api/v1/risk/health."""

    @patch("api.routes.risk.chainiq_client.get_health")
    def test_health_returns_status(self, mock_health, client):
        """Health endpoint should return ChainIQ status."""
        mock_health.return_value = RiskHealthResponse(
            status="healthy",
            model_version="chainiq-v0.1",
            last_check=datetime.utcnow(),
        )

        response = client.get("/api/v1/risk/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model_version" in data
        assert "last_check" in data

    @patch("api.routes.risk.chainiq_client.get_health")
    def test_health_degraded_status(self, mock_health, client):
        """Health endpoint should reflect degraded status."""
        mock_health.return_value = RiskHealthResponse(
            status="degraded",
            model_version="unknown",
            last_check=datetime.utcnow(),
        )

        response = client.get("/api/v1/risk/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"


# =============================================================================
# TEST: ERROR HANDLING
# =============================================================================


class TestRiskErrorHandling:
    """Tests for error handling when ChainIQ is unavailable."""

    @patch("api.routes.risk.chainiq_client.score_shipments")
    def test_score_handles_chainiq_unavailable(self, mock_score, client, test_db):
        """Score endpoint should return 503 when ChainIQ is down."""
        from fastapi import HTTPException

        mock_score.side_effect = HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )

        response = client.post(
            "/api/v1/risk/score",
            json={
                "shipments": [
                    {
                        "shipment_id": "SHP-ERROR",
                        "mode": "OCEAN",
                        "origin_country": "CN",
                        "destination_country": "US",
                        "planned_departure": "2024-12-01T08:00:00Z",
                        "planned_arrival": "2024-12-21T18:00:00Z",
                    },
                ],
            },
        )

        assert response.status_code == 503
        data = response.json()
        assert "ChainIQ" in data["detail"] or "unavailable" in data["detail"].lower()

    @patch("api.routes.risk.chainiq_client.get_health")
    def test_health_handles_chainiq_unavailable(self, mock_health, client):
        """Health endpoint should return 503 when ChainIQ is down."""
        from fastapi import HTTPException

        mock_health.side_effect = HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )

        response = client.get("/api/v1/risk/health")

        assert response.status_code == 503

    @patch("api.routes.risk.chainiq_client.simulate_risk")
    def test_simulation_handles_chainiq_unavailable(self, mock_sim, client, test_db):
        """Simulation endpoint should return 503 when ChainIQ is down."""
        from fastapi import HTTPException

        mock_sim.side_effect = HTTPException(
            status_code=503,
            detail="ChainIQ service unavailable",
        )

        response = client.post(
            "/api/v1/risk/simulation",
            json={
                "base_context": {
                    "shipment_id": "SHP-ERROR-SIM",
                    "mode": "TRUCK",
                    "origin_country": "US",
                    "destination_country": "CA",
                    "planned_departure": "2024-12-01T08:00:00Z",
                    "planned_arrival": "2024-12-02T18:00:00Z",
                },
                "variations": [
                    {"name": "test", "overrides": {"carrier_code": "XYZ"}},
                ],
            },
        )

        assert response.status_code == 503


# =============================================================================
# TEST: INTEGRATION
# =============================================================================


class TestRiskIntegration:
    """Integration tests for risk API with DecisionRecords."""

    @patch("api.routes.risk.chainiq_client.score_shipments")
    def test_decision_record_fields_complete(self, mock_score, client, test_db):
        """DecisionRecord should have all required fields populated."""
        mock_score.return_value = _make_mock_score_response(["SHP-INTEGRATION"])

        response = client.post(
            "/api/v1/risk/score",
            json={
                "shipments": [
                    {
                        "shipment_id": "SHP-INTEGRATION",
                        "mode": "OCEAN",
                        "origin_country": "CN",
                        "destination_country": "US",
                        "planned_departure": "2024-12-01T08:00:00Z",
                        "planned_arrival": "2024-12-21T18:00:00Z",
                    },
                ],
            },
        )

        assert response.status_code == 200

        # Verify DecisionRecord completeness
        record = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.entity_id == "SHP-INTEGRATION").first()
        assert record is not None

        # Required fields
        assert record.id is not None
        assert record.tenant_id is not None
        assert record.type == "RISK_ASSESSMENT"
        assert record.actor_type == "SYSTEM"
        assert record.actor_id == "CHAINIQ"
        assert record.actor_name == "ChainIQ Risk Brain"
        assert record.entity_type == "SHIPMENT"
        assert record.entity_id == "SHP-INTEGRATION"
        assert record.outputs is not None
        assert record.explanation is not None
        assert record.created_at is not None

    @patch("api.routes.risk.chainiq_client.score_shipments")
    def test_multiple_shipments_multiple_records(self, mock_score, client, test_db):
        """Scoring multiple shipments should create one record each."""
        shipment_ids = [f"SHP-BATCH-{i}" for i in range(5)]
        mock_score.return_value = _make_mock_score_response(shipment_ids)

        response = client.post(
            "/api/v1/risk/score",
            json={
                "shipments": [
                    {
                        "shipment_id": sid,
                        "mode": "OCEAN",
                        "origin_country": "CN",
                        "destination_country": "US",
                        "planned_departure": "2024-12-01T08:00:00Z",
                        "planned_arrival": "2024-12-21T18:00:00Z",
                    }
                    for sid in shipment_ids
                ],
            },
        )

        assert response.status_code == 200

        # Verify 5 DecisionRecords created
        records = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.type == "RISK_ASSESSMENT").all()
        assert len(records) == 5

        # Each shipment has its record
        record_ids = {r.entity_id for r in records}
        assert record_ids == set(shipment_ids)
