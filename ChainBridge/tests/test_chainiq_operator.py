"""
Tests for Operator Console API Endpoints

Validates:
- GET /chainiq/operator/summary aggregates
- GET /chainiq/operator/queue prioritization, filtering, and validation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Sequence, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.canonical import RiskLevel
from api.models.chainiq import DocumentHealthSnapshot, ShipmentEvent, SnapshotExportEvent
from api.server import app

SAMPLE_SNAPSHOT_FIXTURES: List[Dict[str, Any]] = [
    {
        "shipment_id": "SHP-2025-0001",
        "risk_level": RiskLevel.CRITICAL.value,
        "risk_score": 95,
        "corridor_code": "IN_US",
        "mode": "OCEAN",
        "incoterm": "CIF",
        "completeness_pct": 65,
        "blocking_gap_count": 3,
        "template_name": "OCEAN_CIF",
        "latest_snapshot_status": None,
    },
    {
        "shipment_id": "SHP-2025-0002",
        "risk_level": RiskLevel.HIGH.value,
        "risk_score": 79,
        "corridor_code": "IN_SG",
        "mode": "OCEAN",
        "incoterm": "FOB",
        "completeness_pct": 72,
        "blocking_gap_count": 2,
        "template_name": "OCEAN_FOB",
        "latest_snapshot_status": "SUCCESS",
    },
    {
        "shipment_id": "SHP-2025-0003",
        "risk_level": RiskLevel.CRITICAL.value,
        "risk_score": 88,
        "corridor_code": "IN_EU",
        "mode": "OCEAN",
        "incoterm": "DAP",
        "completeness_pct": 58,
        "blocking_gap_count": 4,
        "template_name": "OCEAN_DAP",
        "latest_snapshot_status": "FAILED",
    },
    {
        "shipment_id": "SHP-2025-0004",
        "risk_level": RiskLevel.MEDIUM.value,
        "risk_score": 55,
        "corridor_code": "IN_AE",
        "mode": "AIR",
        "incoterm": "DDP",
        "completeness_pct": 80,
        "blocking_gap_count": 1,
        "template_name": "AIR_DDP",
        "latest_snapshot_status": "SUCCESS",
    },
]


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, sessionmaker]:
    """Test client with isolated in-memory SQLite database."""
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
    yield client, TestingSessionLocal
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def reset_tables(client_with_db: Tuple[TestClient, sessionmaker]) -> None:
    """Ensure clean database state before each test."""
    _, SessionLocal = client_with_db
    with SessionLocal() as session:
        session.query(ShipmentEvent).delete()
        session.query(SnapshotExportEvent).delete()
        session.query(DocumentHealthSnapshot).delete()
        session.commit()


@pytest.fixture
def sample_at_risk_shipments() -> List[Dict[str, Any]]:
    """Provide a deepcopy of the standard fixtures for mutation safety."""
    return [dict(record) for record in SAMPLE_SNAPSHOT_FIXTURES]


@pytest.fixture
def seeded_sample_data(
    client_with_db: Tuple[TestClient, sessionmaker],
    sample_at_risk_shipments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Seed the default fixture data set for tests."""
    _, SessionLocal = client_with_db
    _seed_shipments(SessionLocal, sample_at_risk_shipments)
    return sample_at_risk_shipments


def _seed_shipments(SessionLocal: sessionmaker, fixtures: Sequence[Dict[str, Any]]) -> None:
    """Persist fixture snapshots + optional export events."""
    now = datetime.utcnow()
    with SessionLocal() as session:
        for idx, record in enumerate(fixtures):
            created_at: datetime = record.get("created_at") or (now - timedelta(hours=idx))
            snapshot = DocumentHealthSnapshot(
                shipment_id=record["shipment_id"],
                corridor_code=record.get("corridor_code"),
                mode=record.get("mode"),
                incoterm=record.get("incoterm"),
                template_name=record.get("template_name"),
                present_count=record.get("present_count", 2),
                missing_count=record.get("missing_count", 2),
                required_total=record.get("required_total", 4),
                optional_total=record.get("optional_total", 1),
                blocking_gap_count=record.get("blocking_gap_count", 1),
                completeness_pct=record.get("completeness_pct", 50),
                risk_score=record["risk_score"],
                risk_level=record["risk_level"],
                created_at=created_at,
            )
            session.add(snapshot)
            session.flush()

            status = record.get("latest_snapshot_status")
            if status is not None:
                updated_at = record.get("latest_snapshot_updated_at") or (created_at + timedelta(minutes=idx + 1))
                event = SnapshotExportEvent(
                    snapshot_id=snapshot.id,
                    target_system=record.get("target_system", "BIS"),
                    status=status,
                    created_at=updated_at,
                    updated_at=updated_at,
                )
                session.add(event)
        session.commit()


# ===== GET /chainiq/operator/summary Tests =====


class TestOperatorSummary:
    """Test suite for GET /chainiq/operator/summary endpoint."""

    def test_summary_returns_correct_schema(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/summary")
        assert response.status_code == 200

        data = response.json()
        for field in [
            "total_at_risk",
            "critical_count",
            "high_count",
            "medium_count",
            "low_count",
            "needs_snapshot_count",
            "payment_holds_count",
            "last_updated_at",
        ]:
            assert field in data, f"Missing summary field: {field}"

    def test_summary_counts_are_accurate(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/summary")
        data = response.json()

        assert data["total_at_risk"] == len(seeded_sample_data)
        assert data["critical_count"] == sum(
            1 for item in seeded_sample_data if item["risk_level"] == RiskLevel.CRITICAL.value
        )
        assert data["high_count"] == sum(
            1 for item in seeded_sample_data if item["risk_level"] == RiskLevel.HIGH.value
        )
        assert data["medium_count"] == sum(
            1 for item in seeded_sample_data if item["risk_level"] == RiskLevel.MEDIUM.value
        )
        assert data["low_count"] == sum(
            1 for item in seeded_sample_data if item["risk_level"] == RiskLevel.LOW.value
        )
        expected_needs = sum(
            1 for item in seeded_sample_data if item.get("latest_snapshot_status") != "SUCCESS"
        )
        assert data["needs_snapshot_count"] == expected_needs

    def test_summary_payment_holds_count_stub(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/summary")
        data = response.json()
        assert data["payment_holds_count"] == 0

    def test_summary_returns_current_timestamp(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        before = datetime.now(timezone.utc)
        response = client.get("/chainiq/operator/summary")
        after = datetime.now(timezone.utc)

        summary = response.json()
        reported = datetime.fromisoformat(summary["last_updated_at"].replace("Z", "+00:00"))
        assert before <= reported <= after


# ===== GET /chainiq/operator/queue Tests =====


class TestOperatorQueue:
    """Test suite for GET /chainiq/operator/queue endpoint."""

    def test_queue_returns_list_of_items(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # Default filter only includes CRITICAL + HIGH
        assert len(data) == 3

    def test_queue_sorting_rule_1_snapshot_need_first(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?max_results=10")
        data = response.json()

        assert data[0]["needs_snapshot"] is True
        assert data[1]["needs_snapshot"] is True
        assert all(item["needs_snapshot"] is False for item in data[2:])

    def test_queue_sorting_rule_2_risk_level_priority(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
    ) -> None:
        _, SessionLocal = client_with_db
        fixtures = [
            {
                "shipment_id": "SHP-CRIT-1",
                "risk_level": RiskLevel.CRITICAL.value,
                "risk_score": 96,
                "corridor_code": "CN_US",
                "mode": "OCEAN",
                "incoterm": "FOB",
                "completeness_pct": 60,
                "blocking_gap_count": 3,
                "template_name": "OCEAN_CRIT",
                "latest_snapshot_status": None,
            },
            {
                "shipment_id": "SHP-HIGH-1",
                "risk_level": RiskLevel.HIGH.value,
                "risk_score": 82,
                "corridor_code": "CN_US",
                "mode": "OCEAN",
                "incoterm": "FOB",
                "completeness_pct": 70,
                "blocking_gap_count": 2,
                "template_name": "OCEAN_HIGH",
                "latest_snapshot_status": "FAILED",
            },
            {
                "shipment_id": "SHP-MOD-1",
                "risk_level": RiskLevel.MEDIUM.value,
                "risk_score": 65,
                "corridor_code": "CN_US",
                "mode": "OCEAN",
                "incoterm": "FOB",
                "completeness_pct": 80,
                "blocking_gap_count": 1,
                "template_name": "OCEAN_MOD",
                "latest_snapshot_status": None,
            },
        ]
        _seed_shipments(SessionLocal, fixtures)

        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=CRITICAL,HIGH,MEDIUM")
        data = response.json()
        assert [item["risk_level"] for item in data[:3]] == [
            RiskLevel.CRITICAL.value,
            RiskLevel.HIGH.value,
            RiskLevel.MEDIUM.value,
        ]

    def test_queue_sorting_rule_3_risk_score_desc(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=CRITICAL")
        data = response.json()
        scores = [item["risk_score"] for item in data]
        assert scores == sorted(scores, reverse=True)

    def test_queue_max_results_parameter(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?max_results=2")
        data = response.json()
        assert len(data) == 2

    def test_queue_max_results_validation_minimum(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?max_results=0")
        assert response.status_code == 422

    def test_queue_max_results_validation_maximum(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?max_results=501")
        assert response.status_code == 422

    def test_queue_include_levels_filter_single(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=CRITICAL")
        data = response.json()
        assert all(item["risk_level"] == RiskLevel.CRITICAL.value for item in data)

    def test_queue_include_levels_filter_multiple(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=CRITICAL,HIGH")
        data = response.json()
        assert all(item["risk_level"] in {RiskLevel.CRITICAL.value, RiskLevel.HIGH.value} for item in data)

    def test_queue_include_levels_accepts_aliases(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=MODERATE")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert all(item["risk_level"] == RiskLevel.MEDIUM.value for item in data)

    def test_queue_include_levels_invalid_value_rejected(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=INVALID")
        assert response.status_code == 422

    def test_queue_needs_snapshot_only_filter(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get(
            "/chainiq/operator/queue?needs_snapshot_only=true&include_levels=CRITICAL,HIGH,MEDIUM"
        )
        data = response.json()
        assert len(data) >= 1
        assert all(item["needs_snapshot"] is True for item in data)

    def test_queue_combined_filters(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get(
            "/chainiq/operator/queue?include_levels=CRITICAL&needs_snapshot_only=true&max_results=10"
        )
        data = response.json()
        assert all(item["risk_level"] == RiskLevel.CRITICAL.value for item in data)
        assert all(item["needs_snapshot"] is True for item in data)

    def test_queue_items_have_required_fields(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue")
        data = response.json()

        assert data, "Expected non-empty queue for field validation"
        item = data[0]
        for field in [
            "shipment_id",
            "risk_level",
            "risk_score",
            "completeness_pct",
            "blocking_gap_count",
            "needs_snapshot",
            "facility_id",
            "risk_last_updated_at",
            "last_export_status",
            "iot_last_seen_at",
            "last_event_at",
        ]:
            assert field in item, f"Missing required field: {field}"

    def test_queue_empty_when_no_matching_items(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        response = client.get("/chainiq/operator/queue?include_levels=LOW")
        data = response.json()
        assert data == []


# ===== Integration Tests =====


class TestOperatorConsoleIntegration:
    """Integration tests for operator console workflow."""

    def test_summary_and_queue_consistency(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        summary = client.get("/chainiq/operator/summary").json()
        queue = client.get("/chainiq/operator/queue?include_levels=CRITICAL,HIGH&max_results=500").json()
        assert summary["total_at_risk"] >= len(queue)

    def test_queue_respects_filter_from_summary(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
        seeded_sample_data: List[Dict[str, Any]],
    ) -> None:
        client, _ = client_with_db
        summary = client.get("/chainiq/operator/summary").json()
        queue = client.get("/chainiq/operator/queue?include_levels=CRITICAL&max_results=500").json()
        assert summary["critical_count"] == len(queue)


# ===== Performance/Edge Case Tests =====


class TestOperatorQueuePerformance:
    """Performance and edge case tests for operator queue."""

    def test_operator_queue_perf_soft_limit(
        self,
        client_with_db: Tuple[TestClient, sessionmaker],
    ) -> None:
        _, SessionLocal = client_with_db
        fixtures = []
        levels = [
            RiskLevel.CRITICAL.value,
            RiskLevel.HIGH.value,
            RiskLevel.MEDIUM.value,
            RiskLevel.LOW.value,
        ]
        for idx in range(120):
            fixtures.append(
                {
                    "shipment_id": f"SHP-BULK-{idx:04d}",
                    "risk_level": levels[idx % len(levels)],
                    "risk_score": 100 - idx % 60,
                    "corridor_code": "IN_US",
                    "mode": "OCEAN",
                    "incoterm": "FOB",
                    "completeness_pct": 50 + (idx % 50),
                    "blocking_gap_count": idx % 4,
                    "template_name": "OCEAN_BULK",
                    "latest_snapshot_status": None if idx % 3 else "SUCCESS",
                }
            )
        _seed_shipments(SessionLocal, fixtures)

        client, _ = client_with_db
        start = time.perf_counter()
        response = client.get("/chainiq/operator/queue?include_levels=CRITICAL,HIGH,MEDIUM&max_results=200")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 0.15, f"Queue query took too long: {elapsed:.4f}s"
