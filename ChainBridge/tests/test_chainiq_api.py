"""Tests for ChainIQ shipment health intelligence endpoint."""

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.chainiq_service import export_worker
from api.database import Base, get_db
from api.models.canonical import RiskLevel, ShipmentEventType
from api.models.chaindocs import (
    Document,
    DocumentType,
    Shipment,
    ShipmentDocRequirement,
)
from api.models.chainiq import (
    DocumentHealthSnapshot,
    RiskDecision,
    SnapshotExportEvent,
)
from api.models.chainfreight import ShipmentEvent
from api.models.chainpay import SettlementMilestone, SettlementPlan
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
    """Ensure tables are reset between test runs."""
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed_shipment_with_data(session: Session, shipment_id: str) -> None:
    shipment = Shipment(id=shipment_id)
    session.add(shipment)
    session.flush()

    documents = [
        Document(
            id=f"{shipment_id}-DOC-1",
            shipment_id=shipment_id,
            type="BILL_OF_LADING",
            status="VERIFIED",
            current_version=2,
            hash="hash1",
            latest_hash="hash1",
            mletr=True,
        ),
        Document(
            id=f"{shipment_id}-DOC-2",
            shipment_id=shipment_id,
            type="COMMERCIAL_INVOICE",
            status="PRESENT",
            current_version=1,
            hash="hash2",
            latest_hash="hash2",
            mletr=False,
        ),
        Document(
            id=f"{shipment_id}-DOC-3",
            shipment_id=shipment_id,
            type="INSURANCE_CERTIFICATE",
            status="PRESENT",
            current_version=1,
            hash="hash3",
            latest_hash="hash3",
            mletr=False,
        ),
    ]
    session.add_all(documents)

    plan = SettlementPlan(
        id=f"PLAN-{shipment_id}",
        shipment_id=shipment_id,
        template_id="EXPORT_STANDARD_V1",
        total_value=100000.0,
        float_reduction_estimate=0.85,
    )
    session.add(plan)
    session.flush()

    milestones = [
        SettlementMilestone(
            id=f"{plan.id}-MS-1",
            plan_id=plan.id,
            event="BOL_ISSUED",
            payout_pct=0.4,
            status="PAID",
            paid_at="2025-01-01T00:00:00Z",
        ),
        SettlementMilestone(
            id=f"{plan.id}-MS-2",
            plan_id=plan.id,
            event="IMPORT_CUSTOMS_CLEARED",
            payout_pct=0.4,
            status="PENDING",
            paid_at=None,
        ),
        SettlementMilestone(
            id=f"{plan.id}-MS-3",
            plan_id=plan.id,
            event="PROOF_OF_DELIVERY",
            payout_pct=0.2,
            status="HELD",
            paid_at=None,
        ),
    ]
    session.add_all(milestones)
    session.commit()


def _create_snapshot(
    session: Session,
    shipment_id: str,
    *,
    created_at: Optional[datetime] = None,
) -> DocumentHealthSnapshot:
    snapshot = DocumentHealthSnapshot(
        shipment_id=shipment_id,
        corridor_code="IN-US",
        mode="OCEAN",
        incoterm="FOB",
        template_name="DEFAULT_GLOBAL",
        present_count=1,
        missing_count=3,
        required_total=4,
        optional_total=0,
        blocking_gap_count=1,
        completeness_pct=50,
        risk_score=80,
        risk_level="HIGH",
        created_at=created_at or datetime.utcnow(),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def _get_shipment_events(session: Session, shipment_id: str) -> List[ShipmentEvent]:
    return (
        session.query(ShipmentEvent)
        .filter(ShipmentEvent.shipment_id == shipment_id)
        .order_by(ShipmentEvent.occurred_at.asc(), ShipmentEvent.recorded_at.asc())
        .all()
    )


def test_health_empty_shipment_returns_valid_shape(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db

    response = client.get("/chainiq/shipments/SHIP-EMPTY/health")
    assert response.status_code == 200
    data = response.json()

    assert data["shipment_id"] == "SHIP-EMPTY"
    assert data["document_health"]["completeness_pct"] == 0
    assert data["document_health"]["required_total"] >= 4
    assert data["settlement_health"]["completion_pct"] == 0
    assert data["risk"]["score"] <= 50
    assert len(data["recommended_actions"]) > 0


def test_health_seeded_shipment_matches_docs_and_plan(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_data(session, "SHIP-RDY")

    health_response = client.get("/chainiq/shipments/SHIP-RDY/health")
    assert health_response.status_code == 200
    health = health_response.json()

    assert health["document_health"]["present_count"] == 3
    assert health["document_health"]["missing_count"] == 1
    assert health["document_health"]["blocking_gap_count"] >= 1
    assert health["settlement_health"]["milestones_total"] == 3
    assert health["settlement_health"]["milestones_paid"] == 1
    assert health["settlement_health"]["milestones_held"] == 1
    assert health["risk"]["level"] in {
        RiskLevel.MEDIUM.value,
        RiskLevel.HIGH.value,
        RiskLevel.CRITICAL.value,
    }

    plan_response = client.get("/chainpay/shipments/SHIP-RDY/settlement_plan")
    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert plan["doc_risk"]["score"] == health["risk"]["score"]
    assert plan["doc_risk"]["missing_blocking_docs"] == health["document_health"]["blocking_documents"]


def test_health_persists_snapshot(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db

    response = client.get("/chainiq/shipments/SHIP-SNAP/health")
    assert response.status_code == 200

    with SessionLocal() as session:
        snapshots = session.query(DocumentHealthSnapshot).filter_by(shipment_id="SHIP-SNAP").all()
        assert len(snapshots) == 1
        assert snapshots[0].shipment_id == "SHIP-SNAP"
        assert snapshots[0].completeness_pct == response.json()["document_health"]["completeness_pct"]


def test_health_snapshot_uses_latest_values(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db

    # First snapshot with no documents
    first = client.get("/chainiq/shipments/SHIP-VSN/health")
    assert first.status_code == 200

    payload = {
        "document_id": "DOC-VSN-1",
        "type": "BILL_OF_LADING",
        "status": "VERIFIED",
        "version": 1,
        "hash": "abc123",
        "mletr": True,
    }
    post_resp = client.post("/chaindocs/shipments/SHIP-VSN/documents", json=payload)
    assert post_resp.status_code == 200

    second = client.get("/chainiq/shipments/SHIP-VSN/health")
    assert second.status_code == 200
    second_data = second.json()

    with SessionLocal() as session:
        snapshots = (
            session.query(DocumentHealthSnapshot).filter_by(shipment_id="SHIP-VSN").order_by(DocumentHealthSnapshot.created_at.asc()).all()
        )
        assert len(snapshots) == 2
        latest = snapshots[-1]
        assert latest.present_count >= 1
        assert latest.missing_count == latest.required_total - latest.present_count
        assert latest.completeness_pct == second_data["document_health"]["completeness_pct"]


def test_health_uses_template_defaults_when_no_templates_exist(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db

    response = client.get("/chainiq/shipments/SHIP-TMPL/health")
    assert response.status_code == 200
    data = response.json()

    assert data["document_health"]["required_total"] == 4
    assert data["document_health"]["missing_count"] == 4
    assert data["document_health"]["blocking_gap_count"] == 4


def test_health_counts_blocking_vs_non_blocking_docs(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db

    with SessionLocal() as session:
        shipment = Shipment(id="SHIP-BLK", corridor_code="IN-US", mode="OCEAN", incoterm="FOB")
        session.add(shipment)
        session.flush()

        doc_types = [
            DocumentType(code="BOL", description="Bill of Lading"),
            DocumentType(code="CI", description="Commercial Invoice"),
            DocumentType(code="PKG", description="Packing List"),
        ]
        session.add_all(doc_types)
        session.flush()

        requirements = [
            ShipmentDocRequirement(
                template_name="IN-US_OCEAN_FOB",
                corridor_code="IN-US",
                mode="OCEAN",
                incoterm="FOB",
                doc_type_code="BOL",
                required_flag=True,
                blocking_flag=True,
            ),
            ShipmentDocRequirement(
                template_name="IN-US_OCEAN_FOB",
                corridor_code="IN-US",
                mode="OCEAN",
                incoterm="FOB",
                doc_type_code="CI",
                required_flag=True,
                blocking_flag=False,
            ),
            ShipmentDocRequirement(
                template_name="IN-US_OCEAN_FOB",
                corridor_code="IN-US",
                mode="OCEAN",
                incoterm="FOB",
                doc_type_code="PKG",
                required_flag=True,
                blocking_flag=True,
            ),
        ]
        session.add_all(requirements)

        session.add(
            Document(
                id="SHIP-BLK-BOL",
                shipment_id="SHIP-BLK",
                type="BOL",
                status="VERIFIED",
                current_version=1,
                hash="hashA",
                latest_hash="hashA",
                mletr=True,
            )
        )
        session.add(
            Document(
                id="SHIP-BLK-CI",
                shipment_id="SHIP-BLK",
                type="CI",
                status="PRESENT",
                current_version=1,
                hash="hashB",
                latest_hash="hashB",
                mletr=False,
            )
        )
        session.commit()

    response = client.get("/chainiq/shipments/SHIP-BLK/health")
    assert response.status_code == 200
    health = response.json()

    assert health["document_health"]["required_total"] == 3
    assert health["document_health"]["present_count"] == 2
    assert health["document_health"]["missing_count"] == 1
    assert health["document_health"]["blocking_gap_count"] == 1
    assert "PKG" in health["document_health"]["blocking_documents"]


def test_at_risk_shipments_filters_by_score_and_blocking_gaps(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db

    with SessionLocal() as session:
        now = datetime.utcnow()
        session.add_all(
            [
                DocumentHealthSnapshot(
                    shipment_id="SHIP-HIGH",
                    corridor_code="IN-US",
                    mode="OCEAN",
                    incoterm="FOB",
                    template_name="DEFAULT_GLOBAL",
                    present_count=1,
                    missing_count=3,
                    required_total=4,
                    optional_total=0,
                    blocking_gap_count=1,
                    completeness_pct=25,
                    risk_score=85,
                    risk_level="HIGH",
                    created_at=now - timedelta(minutes=5),
                ),
                DocumentHealthSnapshot(
                    shipment_id="SHIP-BLOCK",
                    corridor_code="IN-US",
                    mode="AIR",
                    incoterm="CIF",
                    template_name="DEFAULT_GLOBAL",
                    present_count=2,
                    missing_count=2,
                    required_total=4,
                    optional_total=0,
                    blocking_gap_count=2,
                    completeness_pct=50,
                    risk_score=45,
                    risk_level=RiskLevel.MEDIUM.value,
                    created_at=now - timedelta(minutes=4),
                ),
                DocumentHealthSnapshot(
                    shipment_id="SHIP-NO-RISK",
                    corridor_code="IN-US",
                    mode="AIR",
                    incoterm="CIF",
                    template_name="DEFAULT_GLOBAL",
                    present_count=4,
                    missing_count=0,
                    required_total=4,
                    optional_total=0,
                    blocking_gap_count=0,
                    completeness_pct=100,
                    risk_score=30,
                    risk_level="LOW",
                    created_at=now - timedelta(minutes=3),
                ),
                # Latest snapshot for SHIP-HIGH with lower risk should exclude it
                DocumentHealthSnapshot(
                    shipment_id="SHIP-HIGH",
                    corridor_code="IN-US",
                    mode="OCEAN",
                    incoterm="FOB",
                    template_name="DEFAULT_GLOBAL",
                    present_count=4,
                    missing_count=0,
                    required_total=4,
                    optional_total=0,
                    blocking_gap_count=0,
                    completeness_pct=100,
                    risk_score=60,
                    risk_level=RiskLevel.MEDIUM.value,
                    created_at=now - timedelta(minutes=1),
                ),
            ]
        )
        session.commit()
        ship_block_snapshot = (
            session.query(DocumentHealthSnapshot)
            .filter_by(shipment_id="SHIP-BLOCK")
            .order_by(DocumentHealthSnapshot.created_at.desc())
            .first()
        )
        session.add(
            SnapshotExportEvent(
                snapshot_id=ship_block_snapshot.id,
                target_system="BIS",
                status="SUCCESS",
            )
        )
        session.commit()

    response = client.get("/chainiq/shipments/at_risk")
    assert response.status_code == 200
    data = response.json()
    shipment_ids = {item["shipment_id"] for item in data}

    assert "SHIP-BLOCK" in shipment_ids  # blocking gaps
    assert "SHIP-NO-RISK" not in shipment_ids
    assert "SHIP-HIGH" not in shipment_ids  # latest snapshot below threshold and no gaps
    block_entry = next(item for item in data if item["shipment_id"] == "SHIP-BLOCK")
    assert block_entry["latest_snapshot_status"] == "SUCCESS"
    assert block_entry["latest_snapshot_updated_at"] is not None


def test_at_risk_shipments_respects_max_results(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db

    with SessionLocal() as session:
        now = datetime.utcnow()
        for idx in range(5):
            session.add(
                DocumentHealthSnapshot(
                    shipment_id=f"SHIP-RISK-{idx}",
                    corridor_code=None,
                    mode=None,
                    incoterm=None,
                    template_name="DEFAULT_GLOBAL",
                    present_count=0,
                    missing_count=4,
                    required_total=4,
                    optional_total=0,
                    blocking_gap_count=4,
                    completeness_pct=0,
                    risk_score=80 + idx,
                    risk_level="HIGH",
                    created_at=now - timedelta(minutes=idx),
                )
            )
        session.commit()

    response = client.get("/chainiq/shipments/at_risk", params={"max_results": 3})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_at_risk_shipments_supports_filters_and_pagination(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        now = datetime.utcnow()
        snapshots = [
            DocumentHealthSnapshot(
                shipment_id="SHIP-FLT-1",
                corridor_code="IN-US",
                mode="OCEAN",
                incoterm="FOB",
                template_name="DEFAULT_GLOBAL",
                present_count=1,
                missing_count=3,
                required_total=4,
                optional_total=0,
                blocking_gap_count=2,
                completeness_pct=25,
                risk_score=90,
                risk_level="HIGH",
                created_at=now - timedelta(minutes=3),
            ),
            DocumentHealthSnapshot(
                shipment_id="SHIP-FLT-2",
                corridor_code="IN-US",
                mode="AIR",
                incoterm="FOB",
                template_name="DEFAULT_GLOBAL",
                present_count=2,
                missing_count=2,
                required_total=4,
                optional_total=0,
                blocking_gap_count=0,
                completeness_pct=50,
                risk_score=65,
                risk_level=RiskLevel.MEDIUM.value,
                created_at=now - timedelta(minutes=2),
            ),
            DocumentHealthSnapshot(
                shipment_id="SHIP-FLT-3",
                corridor_code="BR-US",
                mode="OCEAN",
                incoterm="CIF",
                template_name="DEFAULT_GLOBAL",
                present_count=0,
                missing_count=4,
                required_total=4,
                optional_total=0,
                blocking_gap_count=4,
                completeness_pct=0,
                risk_score=95,
                risk_level="HIGH",
                created_at=now - timedelta(minutes=1),
            ),
        ]
        session.add_all(snapshots)
        session.commit()

    resp = client.get(
        "/chainiq/shipments/at_risk",
        params={"corridor_code": "IN-US", "mode": "OCEAN"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["shipment_id"] == "SHIP-FLT-1"

    resp_level = client.get(
        "/chainiq/shipments/at_risk",
        params={"risk_level": "HIGH", "max_results": 10},
    )
    ids = {item["shipment_id"] for item in resp_level.json()}
    assert ids == {"SHIP-FLT-1", "SHIP-FLT-3"}

    resp_page = client.get(
        "/chainiq/shipments/at_risk",
        params={"max_results": 1, "offset": 1, "risk_level": "HIGH"},
    )
    assert resp_page.status_code == 200
    assert len(resp_page.json()) == 1


def test_at_risk_shipments_includes_latest_snapshot_status(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        now = datetime.utcnow()
        snap_with_events = DocumentHealthSnapshot(
            shipment_id="SHIP-STATUS-1",
            corridor_code="IN-US",
            mode="OCEAN",
            incoterm="FOB",
            template_name="DEFAULT_GLOBAL",
            present_count=1,
            missing_count=3,
            required_total=4,
            optional_total=0,
            blocking_gap_count=2,
            completeness_pct=25,
            risk_score=90,
            risk_level="HIGH",
            created_at=now - timedelta(minutes=2),
        )
        snap_without_events = DocumentHealthSnapshot(
            shipment_id="SHIP-STATUS-2",
            corridor_code="IN-US",
            mode="OCEAN",
            incoterm="FOB",
            template_name="DEFAULT_GLOBAL",
            present_count=0,
            missing_count=4,
            required_total=4,
            optional_total=0,
            blocking_gap_count=4,
            completeness_pct=0,
            risk_score=95,
            risk_level="HIGH",
            created_at=now - timedelta(minutes=1),
        )
        session.add_all([snap_with_events, snap_without_events])
        session.commit()
        session.refresh(snap_with_events)
        session.refresh(snap_without_events)

        event_old = SnapshotExportEvent(
            snapshot_id=snap_with_events.id,
            target_system="BIS",
            status="PENDING",
            updated_at=now - timedelta(minutes=3),
        )
        event_new = SnapshotExportEvent(
            snapshot_id=snap_with_events.id,
            target_system="BIS",
            status="SUCCESS",
            updated_at=now - timedelta(minutes=1),
        )
        session.add_all([event_old, event_new])
        session.commit()

    resp = client.get("/chainiq/shipments/at_risk", params={"max_results": 5})
    assert resp.status_code == 200
    data = {item["shipment_id"]: item for item in resp.json()}

    assert data["SHIP-STATUS-1"]["latest_snapshot_status"] == "SUCCESS"
    assert data["SHIP-STATUS-1"]["latest_snapshot_updated_at"] is not None
    assert data["SHIP-STATUS-2"]["latest_snapshot_status"] is None
    assert data["SHIP-STATUS-2"]["latest_snapshot_updated_at"] is None


def test_snapshot_export_events_created_on_health_call(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db

    resp = client.get("/chainiq/shipments/SHIP-EXPORT/health")
    assert resp.status_code == 200

    with SessionLocal() as session:
        snapshot = (
            session.query(DocumentHealthSnapshot)
            .filter_by(shipment_id="SHIP-EXPORT")
            .order_by(DocumentHealthSnapshot.created_at.desc())
            .first()
        )
        assert snapshot is not None
        events = session.query(SnapshotExportEvent).filter_by(snapshot_id=snapshot.id).all()
        assert len(events) == 3
        targets = {event.target_system for event in events}
        assert targets == {"BIS", "SXT", "ML_PIPELINE"}

        shipment_events = _get_shipment_events(session, "SHIP-EXPORT")
        requested_events = [event for event in shipment_events if event.event_type == ShipmentEventType.SNAPSHOT_REQUESTED.value]
        assert len(requested_events) == len(events)
        assert {evt.payload["target_system"] for evt in requested_events} == targets


def test_admin_snapshot_exports_endpoint_filters(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        snapshot = DocumentHealthSnapshot(
            shipment_id="SHIP-ADMIN",
            corridor_code=None,
            mode=None,
            incoterm=None,
            template_name="DEFAULT_GLOBAL",
            present_count=0,
            missing_count=4,
            required_total=4,
            optional_total=0,
            blocking_gap_count=4,
            completeness_pct=0,
            risk_score=10,
            risk_level="LOW",
            created_at=datetime.utcnow(),
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)

        events = [
            SnapshotExportEvent(
                snapshot_id=snapshot.id,
                target_system="BIS",
                status="PENDING",
            ),
            SnapshotExportEvent(
                snapshot_id=snapshot.id,
                target_system="SXT",
                status="FAILED",
                last_error="timeout",
            ),
        ]
        other_snapshot = DocumentHealthSnapshot(
            shipment_id="SHIP-OTHER",
            corridor_code=None,
            mode=None,
            incoterm=None,
            template_name="DEFAULT_GLOBAL",
            present_count=0,
            missing_count=4,
            required_total=4,
            optional_total=0,
            blocking_gap_count=4,
            completeness_pct=0,
            risk_score=12,
            risk_level="LOW",
            created_at=datetime.utcnow(),
        )
        session.add_all(events + [other_snapshot])
        session.commit()
        snapshot_id = snapshot.id
        session.refresh(other_snapshot)
        session.add(
            SnapshotExportEvent(
                snapshot_id=other_snapshot.id,
                target_system="BIS",
                status="PENDING",
            )
        )
        session.commit()

    resp = client.get("/chainiq/admin/snapshot_exports", params={"status": "FAILED"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["target_system"] == "SXT"
    assert data[0]["status"] == "FAILED"

    resp = client.get(
        "/chainiq/admin/snapshot_exports",
        params={"shipment_id": "SHIP-OTHER"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["snapshot_id"] != snapshot_id for item in data)
    assert len(data) == 1


def test_admin_snapshot_exports_requires_or_honors_api_key(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = client_with_db

    monkeypatch.delenv("CHAINBRIDGE_ADMIN_KEY", raising=False)
    resp = client.get("/chainiq/admin/snapshot_exports")
    assert resp.status_code == 200

    monkeypatch.setenv("CHAINBRIDGE_ADMIN_KEY", "secret-key")
    resp = client.get("/chainiq/admin/snapshot_exports")
    assert resp.status_code == 401

    resp = client.get(
        "/chainiq/admin/snapshot_exports",
        headers={"X-CHAINBRIDGE-ADMIN-KEY": "wrong"},
    )
    assert resp.status_code == 401

    resp = client.get(
        "/chainiq/admin/snapshot_exports",
        headers={"X-CHAINBRIDGE-ADMIN-KEY": "secret-key"},
    )
    assert resp.status_code == 200


def test_create_snapshot_export_with_valid_admin_key(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        snapshot = _create_snapshot(session, "SHIP-CREATE-OK")

    monkeypatch.setenv("CHAINBRIDGE_ADMIN_KEY", "secret-key")
    resp = client.post(
        "/chainiq/admin/snapshot_exports",
        json={"shipment_id": "SHIP-CREATE-OK", "reason": "Manual resend"},
        headers={"X-CHAINBRIDGE-ADMIN-KEY": "secret-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] == snapshot.id
    assert data["target_system"] == "CHAINBOARD_UI"
    assert data["status"] == "PENDING"
    assert data["reason"] == "Manual resend"


def test_create_snapshot_export_requires_admin_key_when_configured(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _create_snapshot(session, "SHIP-CREATE-AUTH")

    monkeypatch.setenv("CHAINBRIDGE_ADMIN_KEY", "secret-key")
    resp = client.post(
        "/chainiq/admin/snapshot_exports",
        json={"shipment_id": "SHIP-CREATE-AUTH"},
    )
    assert resp.status_code == 401

    resp = client.post(
        "/chainiq/admin/snapshot_exports",
        json={"shipment_id": "SHIP-CREATE-AUTH"},
        headers={"X-CHAINBRIDGE-ADMIN-KEY": "wrong"},
    )
    assert resp.status_code == 401


def test_create_snapshot_export_allows_multiple_events(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _create_snapshot(session, "SHIP-CREATE-MULTI")

    monkeypatch.delenv("CHAINBRIDGE_ADMIN_KEY", raising=False)
    resp_one = client.post(
        "/chainiq/admin/snapshot_exports",
        json={"shipment_id": "SHIP-CREATE-MULTI"},
    )
    resp_two = client.post(
        "/chainiq/admin/snapshot_exports",
        json={"shipment_id": "SHIP-CREATE-MULTI"},
    )

    assert resp_one.status_code == 200
    assert resp_two.status_code == 200
    assert resp_one.json()["id"] != resp_two.json()["id"]


def test_export_worker_lifecycle(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    _, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        snapshot = _create_snapshot(session, "SHIP-WORKER")
        export_worker.enqueue_snapshot_export_events(
            session,
            snapshot,
            target_systems=["BIS", "SXT"],
        )

        pending = export_worker.fetch_pending_events(session, limit=2)
        assert [e.target_system for e in pending] == ["BIS", "SXT"]

        claimed = export_worker.claim_next_pending_event(session, "worker-1")
        assert claimed is not None
        assert claimed.status == "IN_PROGRESS"
        assert claimed.claimed_by == "worker-1"

        success = export_worker.mark_event_success(session, claimed.id)
        assert success.status == "SUCCESS"
        assert success.last_error is None
        assert success.retry_count == 0

        next_claimed = export_worker.claim_next_pending_event(session, "worker-2")
        assert next_claimed is not None
        assert next_claimed.id != success.id

        failed = export_worker.mark_event_failed(
            session,
            next_claimed.id,
            reason="network error",
            retryable=False,
        )
        assert failed.status == "FAILED"
        assert failed.last_error == "network error"
        assert failed.retry_count == 1

        assert export_worker.claim_next_pending_event(session, "worker-3") is None

        payload = export_worker.get_snapshot_payload(session, success)
        assert payload["shipment_id"] == "SHIP-WORKER"
        assert payload["risk_score"] == 80

        timeline = _get_shipment_events(session, "SHIP-WORKER")
        assert sum(1 for event in timeline if event.event_type == ShipmentEventType.SNAPSHOT_REQUESTED.value) == 2
        assert sum(1 for event in timeline if event.event_type == ShipmentEventType.SNAPSHOT_CLAIMED.value) == 2
        assert any(event.event_type == ShipmentEventType.SNAPSHOT_COMPLETED.value for event in timeline)
        failure_events = [event for event in timeline if event.event_type == ShipmentEventType.SNAPSHOT_FAILED.value]
        assert failure_events
        assert failure_events[-1].payload["error_message"] == "network error"


def test_claim_next_pending_event_unique_to_workers(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "claim_concurrency.sqlite"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    LocalSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    try:
        with LocalSession() as session:
            snapshot = _create_snapshot(session, "SHIP-CONCURRENT")
            session.add_all(
                [
                    SnapshotExportEvent(snapshot_id=snapshot.id, target_system="BIS", status="PENDING"),
                    SnapshotExportEvent(snapshot_id=snapshot.id, target_system="SXT", status="PENDING"),
                ]
            )
            session.commit()

        results: List[Optional[int]] = [None, None]
        barrier = threading.Barrier(2)

        def _claim(slot: int) -> None:
            with LocalSession() as session_inner:
                barrier.wait()
                event = export_worker.claim_next_pending_event(
                    session_inner,
                    worker_id=f"worker-{slot}",
                )
                results[slot] = event.id if event else None

        threads = [threading.Thread(target=_claim, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results[0] is not None and results[1] is not None
        assert results[0] != results[1]
    finally:
        engine.dispose()
        if db_file.exists():
            db_file.unlink()


def test_mark_event_invalid_transition_rejected(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    _, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        snapshot = _create_snapshot(session, "SHIP-INVALID")
        event = SnapshotExportEvent(snapshot_id=snapshot.id, target_system="BIS", status="PENDING")
        session.add(event)
        session.commit()
        session.refresh(event)

        with pytest.raises(export_worker.SnapshotExportInvalidState):
            export_worker.mark_event_success(session, event.id)
        with pytest.raises(export_worker.SnapshotExportInvalidState):
            export_worker.mark_event_failed(session, event.id, reason="boom")


def test_retry_count_increments_and_caps(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    _, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        snapshot = _create_snapshot(session, "SHIP-RETRY")
        event = SnapshotExportEvent(snapshot_id=snapshot.id, target_system="BIS", status="PENDING")
        session.add(event)
        session.commit()
        session.refresh(event)

        for attempt in range(export_worker.MAX_RETRIES):
            claimed = export_worker.claim_next_pending_event(session, worker_id=f"worker-{attempt}")
            assert claimed is not None
            result = export_worker.mark_event_failed(
                session,
                claimed.id,
                reason=f"error {attempt}",
                retryable=True,
            )
            if attempt < export_worker.MAX_RETRIES - 1:
                assert result.status == "PENDING"
                assert result.retry_count == attempt + 1
            else:
                assert result.status == "FAILED"
                assert result.retry_count == export_worker.MAX_RETRIES

        assert export_worker.claim_next_pending_event(session, "worker-final") is None


def test_update_snapshot_export_event_status_endpoint(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        snapshot = _create_snapshot(session, "SHIP-STATUS")
        success_event = SnapshotExportEvent(
            snapshot_id=snapshot.id,
            target_system="BIS",
            status="PENDING",
        )
        failure_event = SnapshotExportEvent(
            snapshot_id=snapshot.id,
            target_system="SXT",
            status="PENDING",
        )
        session.add_all([success_event, failure_event])
        session.commit()
        session.refresh(success_event)
        session.refresh(failure_event)
        export_worker.claim_next_pending_event(session, "worker-success")
        export_worker.claim_next_pending_event(session, "worker-failure")
        success_event_id = success_event.id
        failure_event_id = failure_event.id

    monkeypatch.delenv("CHAINBRIDGE_ADMIN_KEY", raising=False)
    resp = client.post(
        f"/chainiq/admin/snapshot_exports/{success_event_id}/status",
        json={"status": "SUCCESS"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    resp = client.post(
        f"/chainiq/admin/snapshot_exports/{failure_event_id}/status",
        json={"status": "FAILED", "last_error": "timeout", "retryable": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["last_error"] == "timeout"


def test_risk_decision_and_event_logged(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    shipment_id = "SHIP-RISK-DECISION"

    response = client.get(f"/chainiq/shipments/{shipment_id}/health")
    assert response.status_code == 200

    with SessionLocal() as session:
        decisions = session.query(RiskDecision).filter_by(shipment_id=shipment_id).all()
        assert len(decisions) == 1
        decision = decisions[0]
        assert decision.model_version
        assert decision.features is not None

        events = _get_shipment_events(session, shipment_id)
        risk_events = [event for event in events if event.event_type == ShipmentEventType.RISK_DECIDED.value]
        assert risk_events
        assert risk_events[0].payload["risk_decision_id"] == decision.id


def test_debug_shipment_events_endpoint_returns_events(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db
    shipment_id = "SHIP-RISK-EVENTS"

    client.get(f"/chainiq/shipments/{shipment_id}/health")

    response = client.get(f"/debug/shipments/{shipment_id}/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert any(event["event_type"] == ShipmentEventType.RISK_DECIDED.value for event in events)

    limited = client.get(f"/debug/shipments/{shipment_id}/events", params={"limit": 1})
    assert limited.status_code == 200
    assert len(limited.json()) == 1

    empty_resp = client.get("/debug/shipments/SHIP-NO-HISTORY/events")
    assert empty_resp.status_code == 200
    assert empty_resp.json() == []
