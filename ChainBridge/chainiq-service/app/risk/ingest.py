"""Ingestion helpers for ChainIQ risk metrics.

Converts structured log events and Pydantic models into SQLAlchemy ORM objects
for persistence.
"""

from datetime import datetime
from typing import Any, Dict

from app.risk.db_models import RiskEvaluation, RiskModelMetrics
from app.risk.metrics_schemas import RiskModelMetricsRecord


def risk_log_to_orm(log: Dict[str, Any]) -> RiskEvaluation:
    """Convert a raw LOG_EVENT dictionary into a RiskEvaluation ORM object.

    Args:
        log: Dictionary matching the LOG_EVENT structure emitted by service.py.
             Expected keys: evaluation_id, timestamp, model_version, shipment_id,
             carrier_id, lane_id, risk_score, risk_band, primary_reasons,
             features_snapshot.

    Returns:
        RiskEvaluation: Transient ORM object (not added to session).
    """
    # Parse timestamp (handles ISO 8601 strings)
    ts_str = log.get("timestamp")
    if isinstance(ts_str, str):
        timestamp = datetime.fromisoformat(ts_str)
    elif isinstance(ts_str, datetime):
        timestamp = ts_str
    else:
        # Fallback or error - for now let's assume current UTC if missing (though it shouldn't be)
        timestamp = datetime.utcnow()

    return RiskEvaluation(
        evaluation_id=log["evaluation_id"],
        timestamp=timestamp,
        model_version=log["model_version"],
        shipment_id=log["shipment_id"],
        carrier_id=log["carrier_id"],
        lane_id=log["lane_id"],
        risk_score=log["risk_score"],
        risk_band=log["risk_band"],
        primary_reasons=log["primary_reasons"],
        features_snapshot=log["features_snapshot"],
    )


def metrics_record_to_orm(record: RiskModelMetricsRecord) -> RiskModelMetrics:
    """Convert a Pydantic RiskModelMetricsRecord into a RiskModelMetrics ORM object.

    Args:
        record: Validated Pydantic model for metrics.

    Returns:
        RiskModelMetrics: Transient ORM object.
    """
    return RiskModelMetrics(
        model_version=record.model_version,
        window_start=record.window_start,
        window_end=record.window_end,
        eval_count=record.total_evaluations,
        avg_score=record.avg_score,
        p50_score=record.p50_score,
        p90_score=record.p90_score,
        p99_score=record.p99_score,
        risk_band_counts=record.risk_band_counts,
        data_freshness_ts=record.data_freshness_ts,
    )
