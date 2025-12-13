"""Tests for the local ETL CLI logic."""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.risk.db_models import Base, RiskEvaluation
from app.risk.etl_cli import process_log_file


@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_etl_loads_single_log_event(db_session, tmp_path):
    """Test loading a valid LOG_EVENT from a file."""
    # Create a dummy log file
    log_file = tmp_path / "test_risk.log"

    eval_id = str(uuid.uuid4())
    ts_str = datetime.now(timezone.utc).isoformat()

    event = {
        "event_type": "RISK_EVALUATION",
        "evaluation_id": eval_id,
        "timestamp": ts_str,
        "model_version": "v1",
        "shipment_id": "SHP-ETL-1",
        "carrier_id": "CARR-1",
        "lane_id": "US-CA",
        "risk_score": 10,
        "risk_band": "LOW",
        "primary_reasons": [],
        "features_snapshot": {"value_usd": 100},
    }

    # Write with prefix
    log_file.write_text(f"LOG_EVENT: {json.dumps(event)}\n")

    success, failures = process_log_file(log_file, db_session)

    assert success == 1
    assert failures == 0

    # Verify DB
    row = db_session.query(RiskEvaluation).filter_by(evaluation_id=eval_id).first()
    assert row is not None
    assert row.shipment_id == "SHP-ETL-1"


def test_etl_ignores_invalid_log_event(db_session, tmp_path):
    """Test that invalid lines are skipped and valid ones processed."""
    log_file = tmp_path / "mixed.log"

    eval_id = str(uuid.uuid4())
    valid_event = {
        "event_type": "RISK_EVALUATION",
        "evaluation_id": eval_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": "v1",
        "shipment_id": "SHP-VALID",
        "carrier_id": "CARR-1",
        "lane_id": "US-CA",
        "risk_score": 10,
        "risk_band": "LOW",
        "primary_reasons": [],
        "features_snapshot": {"value_usd": 100},
    }

    lines = [
        "GARBAGE LINE",
        f"LOG_EVENT: {json.dumps(valid_event)}",
        "LOG_EVENT: {broken_json",
        '{"event_type": "OTHER_EVENT"}',  # Valid JSON but wrong type
    ]

    log_file.write_text("\n".join(lines))

    success, failures = process_log_file(log_file, db_session)

    assert success == 1  # Only the valid RISK_EVALUATION
    assert failures == 2  # Garbage + Broken JSON (OTHER_EVENT is just skipped silently in loop logic or counted? Let's check logic)

    # Logic check:
    # 1. GARBAGE LINE -> json.loads fails -> failure_count++
    # 2. Valid -> success++
    # 3. Broken JSON -> failure_count++
    # 4. OTHER_EVENT -> json.loads ok -> event_type check -> continue (no increment)

    # So failures should be 2.

    row = db_session.query(RiskEvaluation).filter_by(evaluation_id=eval_id).first()
    assert row is not None
