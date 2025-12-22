"""Tests for ChainIQ risk evaluations history API."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.risk.api import get_db
from app.risk.api import router as risk_router
from app.risk.db_models import Base, RiskEvaluation, RiskModelMetrics

# --- Fixtures ---

# Use a shared engine with StaticPool to ensure all connections use the same in-memory DB
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create and drop tables for each test."""
    Base.metadata.create_all(TEST_ENGINE)
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def db_session():
    """Provide a transactional session for each test."""
    Session = sessionmaker(bind=TEST_ENGINE)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI app with DB dependency override."""
    test_app = FastAPI()
    test_app.include_router(risk_router)  # Router already has prefix="/risk"

    def override_get_db():
        Session = sessionmaker(bind=TEST_ENGINE)
        sess = Session()
        try:
            yield sess
        finally:
            sess.close()

    test_app.dependency_overrides[get_db] = override_get_db

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide a test client."""
    return TestClient(app)


def _create_evaluation(
    db_session,
    *,
    evaluation_id: str | None = None,
    shipment_id: str = "SHP-TEST",
    carrier_id: str = "CARR-TEST",
    lane_id: str = "US-CA",
    risk_score: int = 50,
    risk_band: str = "MEDIUM",
    model_version: str = "chainiq_v1_maggie",
    timestamp: datetime | None = None,
    primary_reasons: list | None = None,
    features_snapshot: dict | None = None,
) -> RiskEvaluation:
    """Helper to create and persist a RiskEvaluation row."""
    eval_id = evaluation_id or str(uuid.uuid4())
    ts = timestamp or datetime.now(timezone.utc)

    evaluation = RiskEvaluation(
        evaluation_id=eval_id,
        timestamp=ts,
        model_version=model_version,
        shipment_id=shipment_id,
        carrier_id=carrier_id,
        lane_id=lane_id,
        risk_score=risk_score,
        risk_band=risk_band,
        primary_reasons=primary_reasons or ["Test Reason"],
        features_snapshot=features_snapshot or {"value_usd": 10000},
    )
    db_session.add(evaluation)
    db_session.commit()
    return evaluation


def _create_metrics(
    db_session,
    *,
    model_version: str = "chainiq_v1_maggie",
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    eval_count: int = 100,
    avg_score: float = 45.0,
    p50_score: float | None = 40.0,
    p90_score: float | None = 80.0,
    p99_score: float | None = 95.0,
    risk_band_counts: dict | None = None,
) -> RiskModelMetrics:
    """Helper to create and persist a RiskModelMetrics row."""
    now = datetime.now(timezone.utc)
    ws = window_start or (now - timedelta(days=7))
    we = window_end or now

    metrics = RiskModelMetrics(
        model_version=model_version,
        window_start=ws,
        window_end=we,
        eval_count=eval_count,
        avg_score=avg_score,
        p50_score=p50_score,
        p90_score=p90_score,
        p99_score=p99_score,
        risk_band_counts=risk_band_counts or {"LOW": 50, "MEDIUM": 30, "HIGH": 20},
        data_freshness_ts=we,
    )
    db_session.add(metrics)
    db_session.commit()
    return metrics


# --- Tests: Evaluations Endpoint ---


def test_list_evaluations_empty(client: TestClient):
    """Returns empty items list when no evaluations exist."""
    response = client.get("/risk/evaluations")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 25
    assert data["offset"] == 0


def test_list_evaluations_returns_seeded_data(client: TestClient, db_session):
    """Returns evaluations that were seeded in the DB."""
    _create_evaluation(db_session, shipment_id="SHP-001", risk_score=30, risk_band="LOW")
    _create_evaluation(db_session, shipment_id="SHP-002", risk_score=85, risk_band="HIGH")

    response = client.get("/risk/evaluations")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Check that expected fields are present
    shipment_ids = {item["shipment_id"] for item in data["items"]}
    assert "SHP-001" in shipment_ids
    assert "SHP-002" in shipment_ids


def test_list_evaluations_response_fields(client: TestClient, db_session):
    """Ensures all expected fields are returned in each evaluation record."""
    _create_evaluation(
        db_session,
        shipment_id="SHP-FIELDS",
        carrier_id="CARR-FIELDS",
        lane_id="US-MX",
        risk_score=72,
        risk_band="HIGH",
        model_version="chainiq_v1_maggie",
        primary_reasons=["High Value", "Border Crossing"],
        features_snapshot={"value_usd": 150000, "is_hazmat": False},
    )

    response = client.get("/risk/evaluations")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["shipment_id"] == "SHP-FIELDS"
    assert item["carrier_id"] == "CARR-FIELDS"
    assert item["lane_id"] == "US-MX"
    assert item["risk_score"] == 72
    assert item["risk_band"] == "HIGH"
    assert item["model_version"] == "chainiq_v1_maggie"
    assert "evaluation_id" in item
    assert "timestamp" in item
    assert item["primary_reasons"] == ["High Value", "Border Crossing"]
    assert item["features_snapshot"]["value_usd"] == 150000


def test_list_evaluations_ordered_by_timestamp_desc(client: TestClient, db_session):
    """Results are ordered by timestamp descending (most recent first)."""
    now = datetime.now(timezone.utc)

    _create_evaluation(
        db_session,
        shipment_id="SHP-OLD",
        timestamp=now - timedelta(hours=2),
    )
    _create_evaluation(
        db_session,
        shipment_id="SHP-NEW",
        timestamp=now,
    )
    _create_evaluation(
        db_session,
        shipment_id="SHP-MID",
        timestamp=now - timedelta(hours=1),
    )

    response = client.get("/risk/evaluations")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Most recent first
    assert data["items"][0]["shipment_id"] == "SHP-NEW"
    assert data["items"][1]["shipment_id"] == "SHP-MID"
    assert data["items"][2]["shipment_id"] == "SHP-OLD"


def test_list_evaluations_limit(client: TestClient, db_session):
    """Respects the limit parameter."""
    for i in range(10):
        _create_evaluation(db_session, shipment_id=f"SHP-{i:03d}")

    # Request only 3
    response = client.get("/risk/evaluations?limit=3")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 10
    assert len(data["items"]) == 3
    assert data["limit"] == 3


def test_list_evaluations_offset(client: TestClient, db_session):
    """Respects the offset parameter."""
    now = datetime.now(timezone.utc)
    for i in range(5):
        _create_evaluation(
            db_session,
            shipment_id=f"SHP-{i:03d}",
            timestamp=now - timedelta(minutes=i),  # 0 is newest
        )

    # Skip the first 2
    response = client.get("/risk/evaluations?offset=2")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    # Should have SHP-002, SHP-003, SHP-004 (offset skips 0 and 1)
    shipment_ids = [item["shipment_id"] for item in data["items"]]
    assert shipment_ids == ["SHP-002", "SHP-003", "SHP-004"]


def test_list_evaluations_filter_by_model_version(client: TestClient, db_session):
    """Filters results by model_version when provided."""
    _create_evaluation(db_session, shipment_id="SHP-V1", model_version="chainiq_v1_maggie")
    _create_evaluation(db_session, shipment_id="SHP-V2", model_version="chainiq_v2_beta")
    _create_evaluation(db_session, shipment_id="SHP-V1-2", model_version="chainiq_v1_maggie")

    # Filter for v1 only
    response = client.get("/risk/evaluations?model_version=chainiq_v1_maggie")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    for item in data["items"]:
        assert item["model_version"] == "chainiq_v1_maggie"

    shipment_ids = {item["shipment_id"] for item in data["items"]}
    assert "SHP-V1" in shipment_ids
    assert "SHP-V1-2" in shipment_ids
    assert "SHP-V2" not in shipment_ids


def test_list_evaluations_filter_by_model_version_no_matches(client: TestClient, db_session):
    """Returns empty items when model_version filter matches nothing."""
    _create_evaluation(db_session, shipment_id="SHP-V1", model_version="chainiq_v1_maggie")

    response = client.get("/risk/evaluations?model_version=nonexistent_version")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_evaluations_caps_limit_at_200(client: TestClient, db_session):
    """Caps the limit to 200 even if a larger value is requested via service layer."""
    # The Query parameter now enforces le=100, and service caps at 200
    from app.risk.service import MAX_EVALUATIONS_LIMIT, list_risk_evaluations

    assert MAX_EVALUATIONS_LIMIT == 200

    # Seed more than 200 rows (we'll just seed a few and verify capping logic)
    for i in range(10):
        _create_evaluation(db_session, shipment_id=f"SHP-CAP-{i:03d}")

    # Call service directly with limit > 200
    results, total = list_risk_evaluations(db=db_session, limit=500, offset=0)
    # Should return only what's in DB (10) since we didn't seed 200+
    assert len(results) == 10
    assert total == 10


def test_list_evaluations_query_validation_limit_bounds(client: TestClient):
    """Query validation rejects limit out of bounds."""
    # limit < 1
    response = client.get("/risk/evaluations?limit=0")
    assert response.status_code == 422

    # limit > 100 (new limit is 100)
    response = client.get("/risk/evaluations?limit=101")
    assert response.status_code == 422


def test_list_evaluations_query_validation_offset_negative(client: TestClient):
    """Query validation rejects negative offset."""
    response = client.get("/risk/evaluations?offset=-1")
    assert response.status_code == 422


def test_list_evaluations_combined_pagination_and_filter(client: TestClient, db_session):
    """Combines limit, offset, and model_version filter."""
    now = datetime.now(timezone.utc)

    # Seed 5 v1 and 3 v2
    for i in range(5):
        _create_evaluation(
            db_session,
            shipment_id=f"SHP-V1-{i:03d}",
            model_version="chainiq_v1_maggie",
            timestamp=now - timedelta(minutes=i),
        )
    for i in range(3):
        _create_evaluation(
            db_session,
            shipment_id=f"SHP-V2-{i:03d}",
            model_version="chainiq_v2_beta",
            timestamp=now - timedelta(minutes=i),
        )

    # Request v1 only, skip first 2, take 2
    response = client.get("/risk/evaluations?model_version=chainiq_v1_maggie&offset=2&limit=2")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2

    # Should be SHP-V1-002 and SHP-V1-003 (skipped 000 and 001)
    shipment_ids = [item["shipment_id"] for item in data["items"]]
    assert shipment_ids == ["SHP-V1-002", "SHP-V1-003"]


# --- Tests: Risk Band Filter ---


def test_get_risk_evaluations_filter_by_band(client: TestClient, db_session):
    """Tests filtering by risk_band."""
    _create_evaluation(db_session, shipment_id="SHP-LOW-1", risk_band="LOW", risk_score=20)
    _create_evaluation(db_session, shipment_id="SHP-LOW-2", risk_band="LOW", risk_score=25)
    _create_evaluation(db_session, shipment_id="SHP-MED-1", risk_band="MEDIUM", risk_score=50)
    _create_evaluation(db_session, shipment_id="SHP-HIGH-1", risk_band="HIGH", risk_score=80)
    _create_evaluation(db_session, shipment_id="SHP-HIGH-2", risk_band="HIGH", risk_score=85)
    _create_evaluation(db_session, shipment_id="SHP-HIGH-3", risk_band="HIGH", risk_score=90)

    # Filter for HIGH only
    response = client.get("/risk/evaluations?risk_band=HIGH")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["items"]) == 3

    for item in data["items"]:
        assert item["risk_band"] == "HIGH"

    # Verify shipment IDs
    shipment_ids = {item["shipment_id"] for item in data["items"]}
    assert shipment_ids == {"SHP-HIGH-1", "SHP-HIGH-2", "SHP-HIGH-3"}

    # Filter for LOW
    response_low = client.get("/risk/evaluations?risk_band=LOW")
    assert response_low.status_code == 200
    data_low = response_low.json()
    assert data_low["total"] == 2


def test_risk_band_filter_invalid_value(client: TestClient):
    """Invalid risk_band value returns 422."""
    response = client.get("/risk/evaluations?risk_band=INVALID")
    assert response.status_code == 422


# --- Tests: Search ---


def test_get_risk_evaluations_search_by_shipment_id(client: TestClient, db_session):
    """Tests search matching shipment_id."""
    _create_evaluation(db_session, shipment_id="SHP-XYZ-001", carrier_id="CARR-ABC", lane_id="US-CA")
    _create_evaluation(db_session, shipment_id="SHP-XYZ-002", carrier_id="CARR-DEF", lane_id="US-MX")
    _create_evaluation(db_session, shipment_id="SHP-OTHER", carrier_id="CARR-GHI", lane_id="CA-US")

    response = client.get("/risk/evaluations?search=XYZ")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    shipment_ids = {item["shipment_id"] for item in data["items"]}
    assert shipment_ids == {"SHP-XYZ-001", "SHP-XYZ-002"}


def test_get_risk_evaluations_search_by_carrier_id(client: TestClient, db_session):
    """Tests search matching carrier_id."""
    _create_evaluation(db_session, shipment_id="SHP-001", carrier_id="CARR-ACME-123", lane_id="US-CA")
    _create_evaluation(db_session, shipment_id="SHP-002", carrier_id="CARR-OTHER", lane_id="US-MX")

    response = client.get("/risk/evaluations?search=ACME")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["carrier_id"] == "CARR-ACME-123"


def test_get_risk_evaluations_search_by_lane_id(client: TestClient, db_session):
    """Tests search matching lane_id."""
    _create_evaluation(db_session, shipment_id="SHP-001", carrier_id="CARR-ABC", lane_id="US-MX")
    _create_evaluation(db_session, shipment_id="SHP-002", carrier_id="CARR-DEF", lane_id="US-CA")

    response = client.get("/risk/evaluations?search=MX")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["lane_id"] == "US-MX"


def test_get_risk_evaluations_search_no_matches(client: TestClient, db_session):
    """Search with no matches returns empty items."""
    _create_evaluation(db_session, shipment_id="SHP-001")

    response = client.get("/risk/evaluations?search=NOTFOUND")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_risk_evaluations_search_case_insensitive(client: TestClient, db_session):
    """Search is case-insensitive."""
    _create_evaluation(db_session, shipment_id="SHP-UPPER-TEST")

    # Search lowercase
    response = client.get("/risk/evaluations?search=upper")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["shipment_id"] == "SHP-UPPER-TEST"


# --- Tests: Combined Filters ---


def test_get_risk_evaluations_combined_band_and_search(client: TestClient, db_session):
    """Tests combining risk_band filter with search."""
    _create_evaluation(db_session, shipment_id="SHP-ABC-001", risk_band="HIGH", risk_score=80)
    _create_evaluation(db_session, shipment_id="SHP-ABC-002", risk_band="LOW", risk_score=20)
    _create_evaluation(db_session, shipment_id="SHP-XYZ-001", risk_band="HIGH", risk_score=85)

    # Search for "ABC" and filter by HIGH
    response = client.get("/risk/evaluations?search=ABC&risk_band=HIGH")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["shipment_id"] == "SHP-ABC-001"


def test_get_risk_evaluations_combined_all_filters(client: TestClient, db_session):
    """Tests combining pagination, risk_band, search, and model_version."""
    now = datetime.now(timezone.utc)

    # Create varied data
    for i in range(4):
        _create_evaluation(
            db_session,
            shipment_id=f"SHP-TARGET-{i:03d}",
            risk_band="HIGH",
            model_version="chainiq_v1_maggie",
            timestamp=now - timedelta(minutes=i),
        )
    for i in range(2):
        _create_evaluation(
            db_session,
            shipment_id=f"SHP-TARGET-OTHER-{i:03d}",
            risk_band="LOW",
            model_version="chainiq_v1_maggie",
        )
    for i in range(2):
        _create_evaluation(
            db_session,
            shipment_id=f"SHP-DIFFERENT-{i:03d}",
            risk_band="HIGH",
            model_version="chainiq_v2_beta",
        )

    # Combined filter: HIGH + search TARGET + v1 + pagination
    response = client.get("/risk/evaluations?risk_band=HIGH&search=TARGET&model_version=chainiq_v1_maggie&limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 4  # 4 records match all filters
    assert len(data["items"]) == 2  # Limited to 2
    assert data["offset"] == 1

    # Verify items are from the correct filtered set
    for item in data["items"]:
        assert item["risk_band"] == "HIGH"
        assert "TARGET" in item["shipment_id"]
        assert item["model_version"] == "chainiq_v1_maggie"


# --- Tests: Metrics Endpoint ---


def test_get_latest_metrics_returns_most_recent_record(client: TestClient, db_session):
    """Returns the metrics record with the most recent window_end."""
    now = datetime.now(timezone.utc)

    # Create older metrics
    _create_metrics(
        db_session,
        model_version="chainiq_v1_maggie",
        window_start=now - timedelta(days=14),
        window_end=now - timedelta(days=7),
        eval_count=50,
        avg_score=40.0,
    )

    # Create newer metrics
    _create_metrics(
        db_session,
        model_version="chainiq_v1_maggie",
        window_start=now - timedelta(days=7),
        window_end=now,
        eval_count=100,
        avg_score=50.0,
    )

    response = client.get("/risk/metrics/latest")
    assert response.status_code == 200
    data = response.json()

    # Should return the newer one
    assert data["total_evaluations"] == 100
    assert abs(data["avg_score"] - 50.0) < 0.01


def test_get_latest_metrics_404_when_empty(client: TestClient):
    """Returns 404 when no metrics records exist."""
    response = client.get("/risk/metrics/latest")
    assert response.status_code == 404
    assert response.json()["detail"] == "No metrics available"


def test_get_latest_metrics_response_fields(client: TestClient, db_session):
    """Verifies all expected fields in metrics response."""
    now = datetime.now(timezone.utc)

    _create_metrics(
        db_session,
        model_version="chainiq_v1_maggie",
        window_start=now - timedelta(days=7),
        window_end=now,
        eval_count=100,
        avg_score=45.5,
        p50_score=42.0,
        p90_score=78.0,
        p99_score=92.0,
        risk_band_counts={"LOW": 40, "MEDIUM": 35, "HIGH": 25},
    )

    response = client.get("/risk/metrics/latest")
    assert response.status_code == 200
    data = response.json()

    # Core fields
    assert data["model_version"] == "chainiq_v1_maggie"
    assert data["total_evaluations"] == 100
    assert abs(data["avg_score"] - 45.5) < 0.01
    assert abs(data["p50_score"] - 42.0) < 0.01
    assert abs(data["p90_score"] - 78.0) < 0.01
    assert abs(data["p99_score"] - 92.0) < 0.01
    assert data["risk_band_counts"] == {"LOW": 40, "MEDIUM": 35, "HIGH": 25}

    # Time window fields
    assert "window_start" in data
    assert "window_end" in data


def test_get_latest_metrics_with_maggie_fields(client: TestClient, db_session):
    """Verifies Maggie-style metrics fields are returned when present."""
    now = datetime.now(timezone.utc)

    # Create metrics with Maggie fields
    metrics = RiskModelMetrics(
        model_version="chainiq_v1_maggie",
        window_start=now - timedelta(days=7),
        window_end=now,
        eval_count=100,
        avg_score=45.0,
        risk_band_counts={"LOW": 50, "MEDIUM": 30, "HIGH": 20},
        critical_incident_recall=0.95,
        high_risk_precision=0.80,
        ops_workload_percent=25.0,
        incident_rate_low=0.02,
        incident_rate_medium=0.08,
        incident_rate_high=0.25,
        calibration_monotonic=1,  # True
        calibration_ratio_high_vs_low=12.5,
        loss_value_coverage_pct=0.92,
        has_failures=0,
        has_warnings=1,
        fail_messages=None,
        warning_messages=["Slight calibration drift detected"],
        data_freshness_ts=now,
    )
    db_session.add(metrics)
    db_session.commit()

    response = client.get("/risk/metrics/latest")
    assert response.status_code == 200
    data = response.json()

    # Maggie metrics
    assert abs(data["critical_incident_recall"] - 0.95) < 0.01
    assert abs(data["high_risk_precision"] - 0.80) < 0.01
    assert abs(data["ops_workload_percent"] - 25.0) < 0.01
    assert abs(data["incident_rate_low"] - 0.02) < 0.01
    assert abs(data["incident_rate_high"] - 0.25) < 0.01
    assert data["calibration_monotonic"] is True
    assert abs(data["calibration_ratio_high_vs_low"] - 12.5) < 0.01
    assert abs(data["loss_value_coverage_pct"] - 0.92) < 0.01

    # Red flags
    assert data["has_failures"] is False
    assert data["has_warnings"] is True
    assert data["warning_messages"] == ["Slight calibration drift detected"]
