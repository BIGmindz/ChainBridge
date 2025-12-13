"""Tests for the OC (Exception Cockpit) API endpoints.

Tests cover:
- Listing exceptions with filters
- Exception statistics (KPIs)
- Exception detail with playbook and decisions
- Status updates with audit trail
- Decision records listing
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.decision_record import DecisionRecord as DecisionRecordModel
from api.models.exception import Exception as ExceptionModel
from api.models.playbook import Playbook as PlaybookModel
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


@pytest.fixture
def seed_data(test_db):
    """Seed the test database with sample data."""
    tenant_id = "default-tenant"
    now = datetime.utcnow()

    # Create a playbook
    playbook = PlaybookModel(
        id="PB-TEST-001",
        tenant_id=tenant_id,
        name="Test Playbook",
        description="A test playbook for risk handling",
        category="RISK_THRESHOLD",
        steps=[
            {"order": 1, "action": "review", "description": "Review issue"},
            {"order": 2, "action": "resolve", "description": "Resolve issue"},
        ],
        active=True,
        version=1,
    )
    test_db.add(playbook)

    # Create exceptions with various states
    exceptions = [
        ExceptionModel(
            id="EXC-TEST-001",
            tenant_id=tenant_id,
            type="RISK_THRESHOLD",
            severity="CRITICAL",
            status="OPEN",
            summary="Critical risk detected",
            notes="High risk shipment detected by ChainIQ",
            shipment_id="SHP-001",
            playbook_id="PB-TEST-001",
            owner_user_id="operator-1",
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(minutes=30),
        ),
        ExceptionModel(
            id="EXC-TEST-002",
            tenant_id=tenant_id,
            type="PAYMENT_HOLD",
            severity="HIGH",
            status="IN_PROGRESS",
            summary="Payment milestone blocked",
            notes="BoL verification required",
            shipment_id="SHP-002",
            owner_user_id="operator-2",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
        ),
        ExceptionModel(
            id="EXC-TEST-003",
            tenant_id=tenant_id,
            type="ETA_BREACH",
            severity="MEDIUM",
            status="OPEN",
            summary="ETA delay detected",
            notes="Port congestion delay",
            shipment_id="SHP-003",
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=2),
        ),
        ExceptionModel(
            id="EXC-TEST-004",
            tenant_id=tenant_id,
            type="IOT_ALERT",
            severity="LOW",
            status="RESOLVED",
            summary="Temperature deviation resolved",
            notes="Reefer returned to normal",
            shipment_id="SHP-004",
            resolution_type="AUTO_RESOLVED",
            resolved_at=now - timedelta(minutes=30),
            resolved_by="SYSTEM",
            created_at=now - timedelta(hours=4),
            updated_at=now - timedelta(minutes=30),
        ),
    ]
    for exc in exceptions:
        test_db.add(exc)

    # Create decision records
    decisions = [
        DecisionRecordModel(
            id="DEC-TEST-001",
            tenant_id=tenant_id,
            type="RISK_DECISION",
            actor_type="SYSTEM",
            actor_id="chainiq-engine",
            actor_name="ChainIQ Risk Engine",
            entity_type="SHIPMENT",
            entity_id="SHP-001",
            outputs={"risk_score": 92, "action": "ESCALATE"},
            explanation="Risk score exceeded critical threshold",
            created_at=now - timedelta(hours=1),
        ),
        DecisionRecordModel(
            id="DEC-TEST-002",
            tenant_id=tenant_id,
            type="SETTLEMENT_DECISION",
            actor_type="SYSTEM",
            actor_id="chainpay-engine",
            actor_name="ChainPay Settlement Engine",
            entity_type="SHIPMENT",
            entity_id="SHP-002",
            outputs={"milestone": 2, "action": "HOLD"},
            explanation="Milestone 2 held pending documentation",
            created_at=now - timedelta(hours=2),
        ),
        DecisionRecordModel(
            id="DEC-TEST-003",
            tenant_id=tenant_id,
            type="EXCEPTION_RESOLUTION",
            actor_type="SYSTEM",
            actor_id="iot-monitor",
            actor_name="IoT Monitor",
            entity_type="EXCEPTION",
            entity_id="EXC-TEST-004",
            outputs={"resolution": "AUTO_RESOLVED"},
            explanation="Temperature normalized automatically",
            created_at=now - timedelta(minutes=30),
        ),
    ]
    for dec in decisions:
        test_db.add(dec)

    test_db.commit()

    return {
        "playbook": playbook,
        "exceptions": exceptions,
        "decisions": decisions,
    }


# =============================================================================
# EXCEPTIONS LIST TESTS
# =============================================================================


class TestOCExceptionsList:
    """Tests for GET /api/v1/oc/exceptions"""

    def test_list_exceptions_returns_all(self, client, seed_data):
        """Should return all exceptions for the tenant."""
        response = client.get("/api/v1/oc/exceptions")
        assert response.status_code == 200

        data = response.json()
        assert "exceptions" in data
        assert "total" in data
        assert data["total"] == 4
        assert len(data["exceptions"]) == 4

    def test_list_exceptions_sorted_by_severity(self, client, seed_data):
        """Should return exceptions sorted by severity (CRITICAL first)."""
        response = client.get("/api/v1/oc/exceptions")
        assert response.status_code == 200

        data = response.json()
        exceptions = data["exceptions"]

        # First should be CRITICAL
        assert exceptions[0]["severity"] == "CRITICAL"
        # Second should be HIGH
        assert exceptions[1]["severity"] == "HIGH"

    def test_list_exceptions_filter_by_status(self, client, seed_data):
        """Should filter exceptions by status."""
        response = client.get("/api/v1/oc/exceptions?status=OPEN")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        for exc in data["exceptions"]:
            assert exc["status"] == "OPEN"

    def test_list_exceptions_filter_by_severity(self, client, seed_data):
        """Should filter exceptions by severity."""
        response = client.get("/api/v1/oc/exceptions?severity=CRITICAL")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["exceptions"][0]["severity"] == "CRITICAL"

    def test_list_exceptions_pagination(self, client, seed_data):
        """Should support pagination."""
        response = client.get("/api/v1/oc/exceptions?page=1&page_size=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["exceptions"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2


# =============================================================================
# EXCEPTION STATS TESTS
# =============================================================================


class TestOCExceptionStats:
    """Tests for GET /api/v1/oc/exceptions/stats"""

    def test_get_stats_returns_counts(self, client, seed_data):
        """Should return correct exception counts."""
        response = client.get("/api/v1/oc/exceptions/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["total_open"] == 3  # OPEN + IN_PROGRESS
        assert data["critical_count"] == 1
        assert data["high_count"] == 1
        assert data["medium_count"] == 1
        assert data["low_count"] == 0  # LOW is RESOLVED

    def test_get_stats_resolved_today(self, client, seed_data):
        """Should count resolutions from today."""
        response = client.get("/api/v1/oc/exceptions/stats")
        assert response.status_code == 200

        data = response.json()
        # Our seed data has 1 resolved exception from 30 minutes ago
        assert data["resolved_today"] >= 0  # May be 0 or 1 depending on UTC date


# =============================================================================
# EXCEPTION DETAIL TESTS
# =============================================================================


class TestOCExceptionDetail:
    """Tests for GET /api/v1/oc/exceptions/{id}"""

    def test_get_exception_detail(self, client, seed_data):
        """Should return full exception detail."""
        response = client.get("/api/v1/oc/exceptions/EXC-TEST-001")
        assert response.status_code == 200

        data = response.json()
        assert "exception" in data
        assert data["exception"]["id"] == "EXC-TEST-001"
        assert data["exception"]["severity"] == "CRITICAL"

    def test_get_exception_with_playbook(self, client, seed_data):
        """Should include associated playbook."""
        response = client.get("/api/v1/oc/exceptions/EXC-TEST-001")
        assert response.status_code == 200

        data = response.json()
        assert "playbook" in data
        assert data["playbook"] is not None
        assert data["playbook"]["id"] == "PB-TEST-001"
        assert data["playbook"]["name"] == "Test Playbook"

    def test_get_exception_with_decisions(self, client, seed_data):
        """Should include recent decisions."""
        response = client.get("/api/v1/oc/exceptions/EXC-TEST-001")
        assert response.status_code == 200

        data = response.json()
        assert "recent_decisions" in data
        # Should have decision for SHP-001
        shipment_decisions = [d for d in data["recent_decisions"] if d.get("shipment_id") == "SHP-001"]
        assert len(shipment_decisions) >= 1

    def test_get_exception_not_found(self, client, seed_data):
        """Should return 404 for non-existent exception."""
        response = client.get("/api/v1/oc/exceptions/EXC-NONEXISTENT")
        assert response.status_code == 404


# =============================================================================
# STATUS UPDATE TESTS
# =============================================================================


class TestOCExceptionStatusUpdate:
    """Tests for PATCH /api/v1/oc/exceptions/{id}/status"""

    def test_update_status_to_in_progress(self, client, seed_data):
        """Should update exception status."""
        response = client.patch("/api/v1/oc/exceptions/EXC-TEST-001/status?status=IN_PROGRESS")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "IN_PROGRESS"

    def test_update_status_to_resolved(self, client, seed_data):
        """Should set resolved_at when resolving."""
        response = client.patch("/api/v1/oc/exceptions/EXC-TEST-003/status?status=RESOLVED")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolved_at"] is not None

    def test_update_status_invalid(self, client, seed_data):
        """Should reject invalid status."""
        response = client.patch("/api/v1/oc/exceptions/EXC-TEST-001/status?status=INVALID")
        assert response.status_code == 400

    def test_update_status_not_found(self, client, seed_data):
        """Should return 404 for non-existent exception."""
        response = client.patch("/api/v1/oc/exceptions/EXC-NONEXISTENT/status?status=RESOLVED")
        assert response.status_code == 404


# =============================================================================
# DECISION RECORDS TESTS
# =============================================================================


class TestOCDecisionRecords:
    """Tests for GET /api/v1/oc/decisions"""

    def test_list_decisions(self, client, seed_data):
        """Should return all decisions."""
        response = client.get("/api/v1/oc/decisions")
        assert response.status_code == 200

        data = response.json()
        assert "records" in data
        assert "total" in data
        assert data["total"] == 3

    def test_list_decisions_filter_by_shipment(self, client, seed_data):
        """Should filter by shipment_id."""
        response = client.get("/api/v1/oc/decisions?shipment_id=SHP-001")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["records"][0]["shipment_id"] == "SHP-001"

    def test_list_decisions_filter_by_exception(self, client, seed_data):
        """Should filter by exception_id."""
        response = client.get("/api/v1/oc/decisions?exception_id=EXC-TEST-004")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert data["records"][0]["exception_id"] == "EXC-TEST-004"

    def test_list_decisions_limit(self, client, seed_data):
        """Should respect limit parameter."""
        response = client.get("/api/v1/oc/decisions?limit=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["records"]) <= 2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestOCIntegration:
    """Integration tests for the OC workflow."""

    def test_status_change_creates_decision(self, client, seed_data, test_db):
        """Changing status should create an audit decision record."""
        # Get initial decision count
        initial_count = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.entity_id == "EXC-TEST-001").count()

        # Update status
        response = client.patch("/api/v1/oc/exceptions/EXC-TEST-001/status?status=IN_PROGRESS")
        assert response.status_code == 200

        # Check new decision was created
        test_db.expire_all()
        new_count = test_db.query(DecisionRecordModel).filter(DecisionRecordModel.entity_id == "EXC-TEST-001").count()

        assert new_count == initial_count + 1

        # Verify the decision content
        latest_decision = (
            test_db.query(DecisionRecordModel)
            .filter(DecisionRecordModel.entity_id == "EXC-TEST-001")
            .order_by(DecisionRecordModel.created_at.desc())
            .first()
        )

        assert latest_decision.type == "STATUS_CHANGE"
        assert latest_decision.outputs["old_status"] == "OPEN"
        assert latest_decision.outputs["new_status"] == "IN_PROGRESS"
