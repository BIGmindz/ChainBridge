"""Tests for risk metrics computation."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.risk.db_models import Base, RiskEvaluation, RiskModelMetrics
from app.risk.metrics_compute import compute_and_persist_risk_metrics, evaluate_red_flags


@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_eval(
    session,
    band: str,
    is_incident: bool = False,
    is_loss: bool = False,
    loss_value: float = 0.0,
    model_version: str = "test_v1",
):
    """Helper to create a RiskEvaluation row."""
    e = RiskEvaluation(
        evaluation_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        model_version=model_version,
        shipment_id=f"SHP-{uuid.uuid4().hex[:6]}",
        carrier_id="CARR-TEST",
        lane_id="US-CA",
        risk_score={"LOW": 20, "MEDIUM": 50, "HIGH": 80}.get(band, 50),
        risk_band=band,
        primary_reasons=[],
        features_snapshot={"value_usd": 100},
        is_incident=is_incident,
        is_loss=is_loss,
        loss_value=loss_value,
    )
    session.add(e)
    return e


def test_compute_and_persist_risk_metrics_basic(db_session):
    """Test basic metrics computation and persistence."""
    # Insert a mix of evaluations
    _make_eval(db_session, "LOW")
    _make_eval(db_session, "LOW")
    _make_eval(db_session, "MEDIUM", is_incident=True)
    _make_eval(db_session, "HIGH", is_incident=True, is_loss=True, loss_value=1000.0)
    _make_eval(db_session, "HIGH", is_incident=True)
    db_session.commit()

    result = compute_and_persist_risk_metrics(db_session)

    assert result is not None
    assert result.eval_count == 5
    assert result.ops_workload_percent == 40.0  # 2 HIGH out of 5
    assert result.incident_rate_low == 0.0
    assert result.incident_rate_medium == 1.0  # 1/1
    assert result.incident_rate_high == 1.0  # 2/2

    # Verify persistence
    stored = db_session.query(RiskModelMetrics).filter_by(id=result.id).first()
    assert stored is not None
    assert stored.eval_count == 5


def test_compute_and_persist_risk_metrics_red_flags(db_session):
    """Test that red flags are correctly triggered."""
    # Create a scenario that triggers failures:
    # - Many losses NOT in HIGH band -> recall < 0.5
    # - Many HIGH items -> ops_workload > 15%
    # - Poor calibration

    # 10 LOW with losses (not caught)
    for _ in range(10):
        _make_eval(db_session, "LOW", is_loss=True, loss_value=100.0)

    # 1 HIGH with loss (caught)
    _make_eval(db_session, "HIGH", is_loss=True, loss_value=50.0, is_incident=True)

    # 5 more HIGH to push workload above 15%
    for _ in range(5):
        _make_eval(db_session, "HIGH", is_incident=False)

    db_session.commit()

    result = compute_and_persist_risk_metrics(db_session)

    assert result is not None
    assert result.has_failures == 1  # True as int

    # Check specific failures
    assert any("Critical Incident Recall < 50%" in msg for msg in result.fail_messages)
    assert any("Ops Workload > 15%" in msg for msg in result.fail_messages)


def test_compute_metrics_no_data(db_session):
    """Test that no data returns None."""
    result = compute_and_persist_risk_metrics(db_session)
    assert result is None


def test_compute_metrics_with_model_version_filter(db_session):
    """Test filtering by model version."""
    _make_eval(db_session, "LOW", model_version="v1")
    _make_eval(db_session, "HIGH", model_version="v2")
    db_session.commit()

    result = compute_and_persist_risk_metrics(db_session, model_version="v1")

    assert result is not None
    assert result.eval_count == 1
    assert result.model_version == "v1"


def test_evaluate_red_flags_no_issues():
    """Test red flag evaluation with healthy metrics."""
    metrics = {
        "critical_incident_recall": 0.80,
        "ops_workload_percent": 10.0,
        "calibration_monotonic": True,
        "calibration_ratio_high_vs_low": 5.0,
        "loss_value_coverage_pct": 0.90,
    }

    result = evaluate_red_flags(metrics)

    assert result["has_failures"] is False
    assert result["has_warnings"] is False
    assert len(result["fail_messages"]) == 0
    assert len(result["warning_messages"]) == 0


def test_evaluate_red_flags_with_issues():
    """Test red flag evaluation with problematic metrics."""
    metrics = {
        "critical_incident_recall": 0.30,  # FAIL
        "ops_workload_percent": 20.0,  # FAIL
        "calibration_monotonic": False,  # FAIL
        "calibration_ratio_high_vs_low": 1.5,  # FAIL
        "loss_value_coverage_pct": 0.40,  # WARN
    }

    result = evaluate_red_flags(metrics)

    assert result["has_failures"] is True
    assert result["has_warnings"] is True
    assert len(result["fail_messages"]) == 4
    assert len(result["warning_messages"]) == 1
