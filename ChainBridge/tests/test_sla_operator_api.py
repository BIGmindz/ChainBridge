from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base
from api.events.bus import EventType
from api.models.chainiq import DocumentHealthSnapshot, SnapshotExportEvent
from api.models.chainpay import PaymentIntent, SettlementEventAudit
from api.routes.sla import sla_operator
from api.sla.metrics import update_metric


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def _snapshot(session, created_at: datetime) -> DocumentHealthSnapshot:
    snap = DocumentHealthSnapshot(
        shipment_id="SHIP-1",
        corridor_code="CN-US",
        mode="OCEAN",
        incoterm="FOB",
        template_name="DEFAULT",
        present_count=1,
        missing_count=0,
        required_total=1,
        optional_total=0,
        blocking_gap_count=0,
        completeness_pct=100,
        risk_score=10,
        risk_level="LOW",
        created_at=created_at,
    )
    session.add(snap)
    session.flush()
    return snap


def test_sla_operator_windowed_metrics():
    session = _make_session()
    now = datetime.now(timezone.utc)
    snap = _snapshot(session, now - timedelta(hours=1))

    session.add(
        SnapshotExportEvent(
            snapshot_id=snap.id,
            target_system="SYS-A",
            status="SUCCESS",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2) + timedelta(seconds=20),
        )
    )
    session.add(
        SnapshotExportEvent(
            snapshot_id=snap.id,
            target_system="SYS-B",
            status="SUCCESS",
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3) + timedelta(seconds=60),
        )
    )
    session.add(
        SnapshotExportEvent(
            snapshot_id=snap.id,
            target_system="SYS-C",
            status="PENDING",
            created_at=now - timedelta(hours=1),
        )
    )
    session.add(
        SnapshotExportEvent(
            snapshot_id=snap.id,
            target_system="SYS-D",
            status="SUCCESS",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2) + timedelta(seconds=120),
        )
    )

    session.add(
        PaymentIntent(
            id="PI-READY",
            shipment_id="SHIP-1",
            amount=100.0,
            currency="USD",
            status="PENDING",
            risk_score=10,
            risk_level="LOW",
            compliance_blocks=None,
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1),
        )
    )
    session.add(
        PaymentIntent(
            id="PI-BLOCKED",
            shipment_id="SHIP-2",
            amount=200.0,
            currency="USD",
            status="PENDING",
            risk_score=20,
            risk_level="MEDIUM",
            compliance_blocks=["HOLD"],
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1),
        )
    )

    session.add(
        SettlementEventAudit(
            event_type=EventType.WORKER_HEARTBEAT.value,
            source="worker",
            actor="worker:test",
            occurred_at=now - timedelta(minutes=5),
            payload_summary={},
        )
    )
    session.commit()

    snapshot = sla_operator(db=session)
    session.close()

    assert snapshot["snapshot_queue_depth"] == 1
    assert snapshot["snapshot_p95_processing_seconds"] == 60
    assert snapshot["payment_intents_ready"] == 1
    assert snapshot["payment_intents_blocked"] == 1
    assert snapshot["worker_stale"] is False
    assert snapshot["data_window"] == "24h"


def test_sla_operator_nulls_and_stale_when_no_data():
    session = _make_session()
    now = datetime.now(timezone.utc)
    update_metric("worker_heartbeat", now - timedelta(minutes=20))

    snapshot = sla_operator(db=session)
    session.close()

    assert snapshot["snapshot_p95_processing_seconds"] is None
    assert snapshot["snapshot_queue_depth"] == 0
    assert snapshot["payment_intents_ready"] == 0
    assert snapshot["payment_intents_blocked"] == 0
    assert snapshot["worker_stale"] is True
    assert snapshot["data_window"] == "24h"
