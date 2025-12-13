"""Risk scoring service orchestration for ChainIQ."""

import datetime
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.risk.engine import compute_risk_score
from app.risk.schemas import CarrierProfile, LaneProfile, RiskBand, ShipmentFeatures, ShipmentRiskRequest, ShipmentRiskResponse

DEFAULT_MODEL_VERSION = "chainiq_v1_maggie"
LOG_EVENT_TYPE = "RISK_EVALUATION"
MAX_EVALUATIONS_LIMIT = 200


async def load_carrier_profile(carrier_id: str, db: Any) -> CarrierProfile:
    """Return a safe default carrier profile until a real lookup is wired."""
    return CarrierProfile(
        carrier_id=carrier_id,
        incident_rate_90d=0.02,
        tenure_days=400,
        on_time_rate=0.95,
    )


async def load_lane_profile(origin: str, destination: str, db: Any) -> LaneProfile:
    """Return a safe default lane profile until a real lookup is wired.

    Deterministic heuristic for testing:
    - Treat US-MX corridors as high risk (0.8) to exercise HIGH band tests.
    - Otherwise default to low risk (0.1).
    """
    lane_risk_index = 0.8 if {origin, destination} & {"MX"} else 0.1
    border_crossing_count = 1 if origin != destination else 0
    return LaneProfile(
        origin=origin,
        destination=destination,
        lane_risk_index=lane_risk_index,
        border_crossing_count=border_crossing_count,
    )


def log_risk_decision(
    *,
    evaluation_id: str,
    shipment_id: str,
    carrier_id: str,
    lane_id: str,
    risk_score: int,
    risk_band: RiskBand,
    primary_reasons: list[str],
    model_version: str,
    timestamp: str,
    features_snapshot: dict | None = None,
) -> dict:
    event = {
        "event_type": LOG_EVENT_TYPE,
        "evaluation_id": evaluation_id,
        "timestamp": timestamp,
        "model_version": model_version,
        "shipment_id": shipment_id,
        "carrier_id": carrier_id,
        "lane_id": lane_id,
        "risk_score": risk_score,
        "risk_band": risk_band.value if isinstance(risk_band, RiskBand) else str(risk_band),
        "primary_reasons": primary_reasons,
        "features_snapshot": features_snapshot or {},
    }
    print(f"LOG_EVENT: {json.dumps(event)}")
    return event


async def score_shipment(
    *,
    request: ShipmentRiskRequest,
    db: Any,
) -> ShipmentRiskResponse:
    """Load profiles, invoke the risk engine, and return a structured response."""
    carrier_profile = await load_carrier_profile(carrier_id=request.carrier_id, db=db)
    lane_profile = await load_lane_profile(origin=request.origin, destination=request.destination, db=db)

    shipment_features = ShipmentFeatures(
        value_usd=request.value_usd,
        is_hazmat=request.is_hazmat,
        is_temp_control=request.is_temp_control,
        expected_transit_days=request.expected_transit_days,
        iot_alert_count=request.iot_alert_count,
        recent_delay_events=request.recent_delay_events,
    )

    result = compute_risk_score(
        shipment=shipment_features,
        carrier_profile=carrier_profile,
        lane_profile=lane_profile,
    )

    evaluation_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    model_version = result.model_version or DEFAULT_MODEL_VERSION

    response = ShipmentRiskResponse(
        shipment_id=request.shipment_id,
        risk_score=result.score,
        risk_band=result.band,
        explanation=result.reasons,
        model_version=model_version,
        timestamp=timestamp,
        evaluation_id=evaluation_id,
    )

    lane_id = f"{request.origin}-{request.destination}"
    features_snapshot = {
        "value_usd": shipment_features.value_usd,
        "is_hazmat": shipment_features.is_hazmat,
        "is_temp_control": shipment_features.is_temp_control,
        "expected_transit_days": shipment_features.expected_transit_days,
        "iot_alert_count": shipment_features.iot_alert_count,
        "recent_delay_events": shipment_features.recent_delay_events,
        "lane_risk_index": lane_profile.lane_risk_index,
        "border_crossing_count": lane_profile.border_crossing_count,
        "carrier_incident_rate_90d": carrier_profile.incident_rate_90d,
        "carrier_tenure_days": carrier_profile.tenure_days,
    }

    log_risk_decision(
        evaluation_id=evaluation_id,
        shipment_id=request.shipment_id,
        carrier_id=request.carrier_id,
        lane_id=lane_id,
        risk_score=result.score,
        risk_band=result.band,
        primary_reasons=result.reasons,
        model_version=model_version,
        timestamp=timestamp,
        features_snapshot=features_snapshot,
    )

    return response


def list_risk_evaluations(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    model_version: str | None = None,
    risk_band: str | None = None,
    search: str | None = None,
) -> tuple[list, int]:
    """Query persisted risk evaluations with pagination, filtering, and search.

    Args:
        db: SQLAlchemy session.
        limit: Maximum number of records to return (capped at MAX_EVALUATIONS_LIMIT).
        offset: Number of records to skip.
        model_version: Optional filter for specific model version.
        risk_band: Optional filter for risk band (LOW, MEDIUM, HIGH, CRITICAL).
        search: Optional free-text search against shipment_id, carrier_id, or lane_id.

    Returns:
        Tuple of (list of RiskEvaluationAPIModel instances, total count matching filters).
    """
    from sqlalchemy import or_

    from app.risk.db_models import RiskEvaluation
    from app.risk.metrics_schemas import RiskEvaluationAPIModel

    # Cap the limit to prevent excessive queries
    effective_limit = min(limit, MAX_EVALUATIONS_LIMIT)

    # Base query for filtering
    query = db.query(RiskEvaluation)

    # Apply filters
    if model_version is not None:
        query = query.filter(RiskEvaluation.model_version == model_version)

    if risk_band is not None:
        query = query.filter(RiskEvaluation.risk_band == risk_band)

    if search is not None and search.strip():
        search_pattern = f"%{search.strip()}%"
        # Case-insensitive search across shipment_id, carrier_id, lane_id
        query = query.filter(
            or_(
                RiskEvaluation.shipment_id.ilike(search_pattern),
                RiskEvaluation.carrier_id.ilike(search_pattern),
                RiskEvaluation.lane_id.ilike(search_pattern),
            )
        )

    # Get total count before pagination
    total = query.count()

    # Apply ordering and pagination
    query = query.order_by(RiskEvaluation.timestamp.desc())
    query = query.offset(offset).limit(effective_limit)

    results = []
    for row in query.all():
        results.append(
            RiskEvaluationAPIModel(
                evaluation_id=row.evaluation_id,
                timestamp=row.timestamp,
                model_version=row.model_version,
                shipment_id=row.shipment_id,
                carrier_id=row.carrier_id,
                lane_id=row.lane_id,
                risk_score=row.risk_score,
                risk_band=row.risk_band,
                primary_reasons=row.primary_reasons or [],
                features_snapshot=row.features_snapshot or {},
            )
        )

    return results, total


def get_latest_risk_metrics(db: Session):
    """Retrieve the most recent risk model metrics record.

    Args:
        db: SQLAlchemy session.

    Returns:
        RiskModelMetricsAPIModel if a record exists, None otherwise.
    """
    from app.risk.db_models import RiskModelMetrics
    from app.risk.metrics_schemas import RiskModelMetricsAPIModel

    # Get the most recent metrics record by window_end or data_freshness_ts
    row = db.query(RiskModelMetrics).order_by(RiskModelMetrics.window_end.desc()).first()

    if row is None:
        return None

    return RiskModelMetricsAPIModel(
        model_version=row.model_version,
        window_start=row.window_start,
        window_end=row.window_end,
        total_evaluations=row.eval_count,
        avg_score=row.avg_score,
        p50_score=row.p50_score,
        p90_score=row.p90_score,
        p99_score=row.p99_score,
        risk_band_counts=row.risk_band_counts or {},
        critical_incident_recall=row.critical_incident_recall,
        high_risk_precision=row.high_risk_precision,
        ops_workload_percent=row.ops_workload_percent,
        incident_rate_low=row.incident_rate_low,
        incident_rate_medium=row.incident_rate_medium,
        incident_rate_high=row.incident_rate_high,
        calibration_monotonic=bool(row.calibration_monotonic) if row.calibration_monotonic is not None else None,
        calibration_ratio_high_vs_low=row.calibration_ratio_high_vs_low,
        loss_value_coverage_pct=row.loss_value_coverage_pct,
        has_failures=bool(row.has_failures) if row.has_failures is not None else None,
        has_warnings=bool(row.has_warnings) if row.has_warnings is not None else None,
        fail_messages=row.fail_messages,
        warning_messages=row.warning_messages,
        data_freshness_ts=row.data_freshness_ts,
    )
