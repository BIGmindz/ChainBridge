"""Integration tests for core governance API endpoints.

Tests CRUD operations for Party, Exception, Playbook, SettlementPolicy,
DecisionRecord, EsgEvidence, and PartyRelationship entities.
"""

from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.server import app


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, Any, sessionmaker]:
    """Provide a TestClient wired to an in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, engine, TestingSessionLocal

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_database(client_with_db: Tuple[TestClient, Any, sessionmaker]):
    """Ensure tables are reset between tests."""
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


class TestPartiesAPI:
    """Tests for /api/v1/parties endpoints."""

    def test_create_party(self, client_with_db):
        client, _, _ = client_with_db
        response = client.post(
            "/api/v1/parties/",
            json={
                "name": "Acme Shipping Co",
                "type": "CARRIER",
                "country_code": "USA",
                "status": "ACTIVE",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Shipping Co"
        assert data["type"] == "CARRIER"
        assert "id" in data
        assert "created_at" in data

    def test_list_parties(self, client_with_db):
        client, _, _ = client_with_db
        # Create a party first
        client.post(
            "/api/v1/parties/",
            json={"name": "Test Party", "type": "SHIPPER"},
        )
        response = client.get("/api/v1/parties/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_party(self, client_with_db):
        client, _, _ = client_with_db
        # Create a party
        create_response = client.post(
            "/api/v1/parties/",
            json={"name": "Get Test Party", "type": "BROKER"},
        )
        party_id = create_response.json()["id"]

        # Retrieve it
        response = client.get(f"/api/v1/parties/{party_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Party"

    def test_update_party(self, client_with_db):
        client, _, _ = client_with_db
        # Create a party
        create_response = client.post(
            "/api/v1/parties/",
            json={"name": "Update Test", "type": "CARRIER"},
        )
        party_id = create_response.json()["id"]

        # Update it
        response = client.patch(
            f"/api/v1/parties/{party_id}",
            json={"name": "Updated Name", "status": "INACTIVE"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["status"] == "INACTIVE"

    def test_delete_party(self, client_with_db):
        client, _, _ = client_with_db
        # Create a party
        create_response = client.post(
            "/api/v1/parties/",
            json={"name": "Delete Test", "type": "FACILITY"},
        )
        party_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/parties/{party_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/v1/parties/{party_id}")
        assert get_response.status_code == 404


class TestExceptionsAPI:
    """Tests for /api/v1/exceptions endpoints."""

    def test_create_exception(self, client_with_db):
        client, _, _ = client_with_db
        response = client.post(
            "/api/v1/exceptions/",
            json={
                "type": "DELAY",
                "severity": "HIGH",
                "summary": "Shipment delayed at port",
                "shipment_id": "SHIP-001",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "DELAY"
        assert data["severity"] == "HIGH"
        assert data["status"] == "OPEN"

    def test_list_exceptions_with_filters(self, client_with_db):
        client, _, _ = client_with_db
        # Create exceptions
        client.post(
            "/api/v1/exceptions/",
            json={"type": "DELAY", "severity": "HIGH", "summary": "Test 1"},
        )
        client.post(
            "/api/v1/exceptions/",
            json={"type": "MISSING_POD", "severity": "MEDIUM", "summary": "Test 2"},
        )

        # Filter by severity
        response = client.get("/api/v1/exceptions/?severity=HIGH")
        assert response.status_code == 200
        data = response.json()
        assert all(exc["severity"] == "HIGH" for exc in data)

    def test_resolve_exception(self, client_with_db):
        client, _, _ = client_with_db
        # Create an exception
        create_response = client.post(
            "/api/v1/exceptions/",
            json={"type": "CLAIM_RISK", "severity": "MEDIUM", "summary": "Test resolve"},
        )
        exc_id = create_response.json()["id"]

        # Resolve it
        response = client.post(
            f"/api/v1/exceptions/{exc_id}/resolve",
            json={"resolution_type": "MANUAL_FIX", "resolution_notes": "Fixed manually"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution_type"] == "MANUAL_FIX"
        assert data["resolved_at"] is not None


class TestPlaybooksAPI:
    """Tests for /api/v1/playbooks endpoints."""

    def test_create_playbook(self, client_with_db):
        client, _, _ = client_with_db
        response = client.post(
            "/api/v1/playbooks/",
            json={
                "name": "Delay Handling Playbook",
                "description": "Standard playbook for handling delays",
                "category": "DELAY_HANDLING",
                "steps": [
                    {"order": 1, "action": "notify_carrier", "gate": "auto"},
                    {"order": 2, "action": "escalate", "gate": "human_approval"},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Delay Handling Playbook"
        assert data["version"] == 1
        assert data["active"] is True
        assert len(data["steps"]) == 2

    def test_create_playbook_version(self, client_with_db):
        client, _, _ = client_with_db
        # Create initial playbook
        create_response = client.post(
            "/api/v1/playbooks/",
            json={
                "name": "Version Test Playbook",
                "steps": [{"order": 1, "action": "test", "gate": "auto"}],
            },
        )
        playbook_id = create_response.json()["id"]

        # Create new version
        response = client.post(
            f"/api/v1/playbooks/{playbook_id}/new-version",
            json={
                "steps": [
                    {"order": 1, "action": "test", "gate": "auto"},
                    {"order": 2, "action": "new_step", "gate": "auto"},
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["version"] == 2
        assert data["supersedes_id"] == playbook_id
        assert len(data["steps"]) == 2


class TestSettlementPoliciesAPI:
    """Tests for /api/v1/settlement-policies endpoints."""

    def test_create_settlement_policy(self, client_with_db):
        client, _, _ = client_with_db
        response = client.post(
            "/api/v1/settlement-policies/",
            json={
                "name": "Standard Export Policy",
                "policy_type": "MILESTONE",
                "currency": "USD",
                "max_exposure": 1000000.0,
                "curve": [
                    {"name": "Booking", "event_type": "BOOKING_CONFIRMED", "percent": 10},
                    {"name": "BOL Issued", "event_type": "BOL_ISSUED", "percent": 40},
                    {"name": "POD", "event_type": "POD_RECEIVED", "percent": 50},
                ],
                "rails": ["ACH", "WIRE"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Standard Export Policy"
        assert data["currency"] == "USD"
        assert len(data["curve"]) == 3

    def test_approve_settlement_policy(self, client_with_db):
        client, _, _ = client_with_db
        # Create a policy
        create_response = client.post(
            "/api/v1/settlement-policies/",
            json={
                "name": "Approval Test Policy",
                "currency": "USD",
                "curve": [],
            },
        )
        policy_id = create_response.json()["id"]

        # Approve it
        response = client.post(
            f"/api/v1/settlement-policies/{policy_id}/approve",
            params={"approver_id": "user-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approved_by"] == "user-123"
        assert data["approved_at"] is not None


class TestDecisionRecordsAPI:
    """Tests for /api/v1/decision-records endpoints."""

    def test_create_decision_record(self, client_with_db):
        client, _, _ = client_with_db
        response = client.post(
            "/api/v1/decision-records/",
            json={
                "type": "RISK_DECISION",
                "actor_type": "SYSTEM",
                "actor_id": "chainiq-risk-engine",
                "entity_type": "SHIPMENT",
                "entity_id": "SHIP-001",
                "outputs": {
                    "decision": "APPROVED",
                    "score": 75,
                    "confidence": 0.92,
                },
                "explanation": "Risk score within acceptable range",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "RISK_DECISION"
        assert data["outputs"]["decision"] == "APPROVED"

    def test_get_decisions_for_entity(self, client_with_db):
        client, _, _ = client_with_db
        # Create decisions for an entity
        client.post(
            "/api/v1/decision-records/",
            json={
                "type": "RISK_DECISION",
                "actor_type": "SYSTEM",
                "actor_id": "chainiq",
                "entity_type": "SHIPMENT",
                "entity_id": "SHIP-002",
                "outputs": {"decision": "APPROVED"},
            },
        )

        # Query by entity
        response = client.get("/api/v1/decision-records/entity/SHIPMENT/SHIP-002")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(d["entity_id"] == "SHIP-002" for d in data)


class TestEsgEvidenceAPI:
    """Tests for /api/v1/esg-evidence endpoints."""

    def test_create_esg_evidence(self, client_with_db):
        client, _, _ = client_with_db
        # Create a party first
        party_response = client.post(
            "/api/v1/parties/",
            json={"name": "ESG Test Party", "type": "CARRIER"},
        )
        party_id = party_response.json()["id"]

        # Create ESG evidence
        response = client.post(
            "/api/v1/esg-evidence/",
            json={
                "party_id": party_id,
                "type": "CERTIFICATION",
                "category": "ENVIRONMENTAL",
                "source": "ISO",
                "title": "ISO 14001 Certification",
                "score_impact": 15.0,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "CERTIFICATION"
        assert data["score_impact"] == 15.0

    def test_get_evidence_for_party(self, client_with_db):
        client, _, _ = client_with_db
        # Create a party
        party_response = client.post(
            "/api/v1/parties/",
            json={"name": "Evidence Test Party", "type": "SHIPPER"},
        )
        party_id = party_response.json()["id"]

        # Create evidence
        client.post(
            "/api/v1/esg-evidence/",
            json={
                "party_id": party_id,
                "type": "AUDIT",
                "source": "Internal",
                "score_impact": 10.0,
            },
        )

        # Query by party
        response = client.get(f"/api/v1/esg-evidence/party/{party_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestPartyRelationshipsAPI:
    """Tests for /api/v1/party-relationships endpoints."""

    def test_create_party_relationship(self, client_with_db):
        client, _, _ = client_with_db
        # Create two parties
        party1_response = client.post(
            "/api/v1/parties/",
            json={"name": "Shipper A", "type": "SHIPPER"},
        )
        party1_id = party1_response.json()["id"]

        party2_response = client.post(
            "/api/v1/parties/",
            json={"name": "Carrier B", "type": "CARRIER"},
        )
        party2_id = party2_response.json()["id"]

        # Create relationship
        response = client.post(
            "/api/v1/party-relationships/",
            json={
                "from_party_id": party1_id,
                "to_party_id": party2_id,
                "type": "SUPPLIES",
                "tier": "TIER_1",
                "attributes": {"volume_share": 0.35},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "SUPPLIES"
        assert data["tier"] == "TIER_1"

    def test_get_outgoing_relationships(self, client_with_db):
        client, _, _ = client_with_db
        # Create parties and relationship
        party1_response = client.post(
            "/api/v1/parties/",
            json={"name": "Source Party", "type": "SHIPPER"},
        )
        party1_id = party1_response.json()["id"]

        party2_response = client.post(
            "/api/v1/parties/",
            json={"name": "Target Party", "type": "CARRIER"},
        )
        party2_id = party2_response.json()["id"]

        client.post(
            "/api/v1/party-relationships/",
            json={
                "from_party_id": party1_id,
                "to_party_id": party2_id,
                "type": "PARTNERS_WITH",
            },
        )

        # Query outgoing
        response = client.get(f"/api/v1/party-relationships/party/{party1_id}/outgoing")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(r["from_party_id"] == party1_id for r in data)
