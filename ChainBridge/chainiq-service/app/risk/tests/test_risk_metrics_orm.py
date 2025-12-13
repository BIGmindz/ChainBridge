"""Tests for ChainIQ risk metrics persistence layer."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.risk.db_models import Base, RiskEvaluation, RiskModelMetrics
from app.risk.ingest import metrics_record_to_orm, risk_log_to_orm
from app.risk.metrics_schemas import RiskModelMetricsRecord

# --- Fixtures ---


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine for testing."""
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture(scope="module")
def tables(engine):
    """Create tables for the test session."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables):
    """Provide a transactional session for each test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# --- Tests ---


def test_risk_evaluation_crud(db_session):
    """Test basic create, read, operations for RiskEvaluation."""
    eval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    evaluation = RiskEvaluation(
        evaluation_id=eval_id,
        timestamp=now,
        model_version="test_v1",
        shipment_id="SHP-123",
        carrier_id="CARR-456",
        lane_id="US-CA",
        risk_score=42,
        risk_band="MEDIUM",
        primary_reasons=["Test Reason"],
        features_snapshot={"value_usd": 1000},
    )

    db_session.add(evaluation)
    db_session.commit()

    # Read back
    stored = db_session.query(RiskEvaluation).filter_by(evaluation_id=eval_id).first()
    assert stored is not None
    assert stored.shipment_id == "SHP-123"
    assert stored.risk_score == 42
    assert stored.features_snapshot["value_usd"] == 1000
    # SQLAlchemy SQLite date handling might lose timezone info if not careful.
    # We stored it as UTC, so if it comes back naive, we treat it as UTC.
    stored_ts = stored.timestamp
    if stored_ts.tzinfo is None:
        stored_ts = stored_ts.replace(tzinfo=timezone.utc)

    assert stored_ts == now


def test_ingest_log_event(db_session):
    """Test ingesting a LOG_EVENT dict into the DB."""
    eval_id = str(uuid.uuid4())
    ts_str = datetime.now(timezone.utc).isoformat()

    log_event = {
        "event_type": "RISK_EVALUATION",
        "evaluation_id": eval_id,
        "timestamp": ts_str,
        "model_version": "chainiq_v1_maggie",
        "shipment_id": "SHP-INGEST",
        "carrier_id": "CARR-INGEST",
        "lane_id": "US-MX",
        "risk_score": 85,
        "risk_band": "HIGH",
        "primary_reasons": ["High Value", "Lane Risk"],
        "features_snapshot": {"value_usd": 500000, "is_hazmat": True, "lane_risk_index": 0.8},
    }

    orm_obj = risk_log_to_orm(log_event)
    db_session.add(orm_obj)
    db_session.commit()

    stored = db_session.query(RiskEvaluation).filter_by(evaluation_id=eval_id).first()
    assert stored is not None
    assert stored.risk_band == "HIGH"
    assert stored.primary_reasons == ["High Value", "Lane Risk"]
    assert stored.features_snapshot["is_hazmat"] is True


def test_risk_model_metrics_crud(db_session):
    """Test persistence of aggregated metrics."""
    now = datetime.now(timezone.utc)

    record = RiskModelMetricsRecord(
        model_version="chainiq_v1_maggie",
        window_start=now,
        window_end=now,
        total_evaluations=100,
        avg_score=45.5,
        p50_score=40.0,
        p90_score=80.0,
        p99_score=95.0,
        risk_band_counts={"LOW": 50, "MEDIUM": 30, "HIGH": 20},
        data_freshness_ts=now,
    )

    orm_obj = metrics_record_to_orm(record)
    db_session.add(orm_obj)
    db_session.commit()

    stored = db_session.query(RiskModelMetrics).filter_by(model_version="chainiq_v1_maggie").first()
    assert stored is not None
    assert stored.eval_count == 100
    assert stored.risk_band_counts["HIGH"] == 20
    assert abs(stored.avg_score - 45.5) < 0.001
