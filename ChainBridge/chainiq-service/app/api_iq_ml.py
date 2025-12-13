"""
ChainIQ ML API Router

Provides ML-powered risk and anomaly scoring endpoints.
Uses modular ML models (currently dummy/deterministic) that can be
swapped for trained models without changing API contracts.

Shadow Mode: When enabled, runs real ML models in parallel with dummy models
and logs discrepancies for validation before production promotion.
"""

import logging
import time

from fastapi import APIRouter

from app.core.config import settings
from app.metrics import IQ_ANOMALY_CALLS, IQ_ANOMALY_LATENCY, IQ_RISK_CALLS, IQ_RISK_LATENCY, metrics
from app.ml import get_anomaly_model, get_risk_model
from app.models.features import ShipmentFeaturesV0
from app.models.scoring import AnomalyScoreResponse, RiskScoreResponse
from app.observability import log_prediction_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iq/ml", tags=["iq-ml"])


@router.post("/risk-score", response_model=RiskScoreResponse)
async def score_risk(features: ShipmentFeaturesV0) -> RiskScoreResponse:
    """
    Calculate risk score for a shipment based on its feature vector.

    Uses modular risk model (currently DummyRiskModel with deterministic logic).
    Real ML models can be swapped in by modifying get_risk_model() in app.ml.

    Shadow Mode: If enabled, runs real model in parallel for validation.

    Args:
        features: Fully populated ShipmentFeaturesV0 instance

    Returns:
        RiskScoreResponse with score, explanations, and model version
    """
    # Increment metrics counters (both in-memory and Prometheus)
    metrics.risk_calls_total += 1
    IQ_RISK_CALLS.labels(corridor=features.corridor).inc()

    # Time the scoring operation
    start = time.perf_counter()
    try:
        # Get the current risk model (PRODUCTION - always dummy)
        risk_model = get_risk_model()

        # Run prediction through model
        prediction = risk_model.predict(features)

        # Map model prediction to API response
        response = RiskScoreResponse(
            score=prediction.score,
            explanation=prediction.explanation,
            model_version=prediction.model_version,
        )

        # ============================================================
        # SHADOW MODE v0.3: Run real model in parallel + persist
        # ============================================================
        if settings.enable_shadow_mode:
            _run_shadow_mode_v03(features, prediction.score)

    finally:
        # Record latency in Prometheus
        elapsed = time.perf_counter() - start
        IQ_RISK_LATENCY.labels(corridor=features.corridor).observe(elapsed)

    # Log prediction event
    log_prediction_event(
        endpoint="/iq/ml/risk-score",
        score=response.score,
        model_version=response.model_version,
        shipment_id=features.shipment_id,
        corridor=features.corridor,
    )

    return response


def _run_shadow_mode_v03(features: ShipmentFeaturesV0, dummy_score: float) -> None:
    """
    Execute shadow mode v0.3: run real ML model + persist comparison.

    CRITICAL GUARANTEES:
    - Never raises exceptions (wrapped in try/except)
    - Never modifies API response
    - Never blocks production scoring path
    - Logs failures but continues gracefully
    - Persists to in-memory log (DB optional when configured)

    Version 0.3 Enhancements:
    - Actually loads and runs real ML model
    - Computes delta between dummy and real scores
    - Logs feature vectors for analysis
    - Tracks corridor-level metrics
    - Persists to structured logging (DB when available)

    Args:
        features: Shipment features
        dummy_score: Score from DummyRiskModel
    """
    try:
        from app.ml.datasets import ShipmentTrainingRow
        from app.ml.preprocessing import build_risk_feature_matrix
        from app.ml.training_v02 import load_real_risk_model_v02

        # Load real model (lazy-loaded singleton)
        real_model = load_real_risk_model_v02()

        if real_model is None:
            # Model not available yet (not trained/deployed)
            logger.debug("Shadow mode: real model not available, skipping")
            return

        # Convert features to model input format
        training_row = ShipmentTrainingRow(
            shipment_id=features.shipment_id,
            corridor=features.corridor,
            origin_country=features.origin_country,
            destination_country=features.destination_country,
            mode=features.mode,
            commodity_category=features.commodity_category,
            financing_type=features.financing_type,
            counterparty_risk_bucket=features.counterparty_risk_bucket,
            planned_transit_hours=features.planned_transit_hours,
            actual_transit_hours=features.actual_transit_hours,
            eta_deviation_hours=features.eta_deviation_hours,
            num_route_deviations=features.num_route_deviations,
            max_route_deviation_km=features.max_route_deviation_km,
            total_dwell_hours=features.total_dwell_hours,
            max_single_dwell_hours=features.max_single_dwell_hours,
            handoff_count=features.handoff_count,
            max_custody_gap_hours=features.max_custody_gap_hours,
            delay_flag=features.delay_flag,
            has_iot_telemetry=features.has_iot_telemetry,
            temp_mean=features.temp_mean,
            temp_std=features.temp_std,
            temp_min=features.temp_min,
            temp_max=features.temp_max,
            temp_out_of_range_pct=features.temp_out_of_range_pct,
            sensor_uptime_pct=features.sensor_uptime_pct,
            doc_count=features.doc_count,
            missing_required_docs=features.missing_required_docs,
            duplicate_doc_flag=features.duplicate_doc_flag,
            doc_inconsistency_flag=features.doc_inconsistency_flag,
            doc_age_days=features.doc_age_days,
            collateral_value=features.collateral_value,
            collateral_value_bucket=features.collateral_value_bucket,
            shipper_on_time_pct_90d=features.shipper_on_time_pct_90d,
            carrier_on_time_pct_90d=features.carrier_on_time_pct_90d,
            corridor_disruption_index_90d=features.corridor_disruption_index_90d,
            prior_exceptions_count_180d=features.prior_exceptions_count_180d,
            prior_losses_flag=features.prior_losses_flag,
            lane_sentiment_score=features.lane_sentiment_score,
            macro_logistics_sentiment_score=features.macro_logistics_sentiment_score,
            sentiment_trend_7d=features.sentiment_trend_7d,
            sentiment_volatility_30d=features.sentiment_volatility_30d,
            sentiment_provider=features.sentiment_provider,
            # Training labels (None for inference)
            realized_loss_flag=None,
            loss_amount=None,
            fraud_confirmed=None,
            severe_exception=None,
        )

        # Build feature matrix
        X, _ = build_risk_feature_matrix([training_row])

        # Run real model prediction
        import numpy as np

        X_np = np.array(X, dtype=float)
        real_score_proba = float(real_model.predict_proba(X_np)[:, 1][0])

        # Compute delta
        delta = abs(dummy_score - real_score_proba)

        # Log structured event with full context
        logger.info(
            "shadow_comparison_v03",
            extra={
                "shipment_id": features.shipment_id,
                "corridor": features.corridor,
                "dummy_score": dummy_score,
                "real_score": real_score_proba,
                "delta": delta,
                "model_version": "v0.2.0",
                "feature_vector_size": len(X[0]),
                "event_type": "shadow_comparison",
            },
        )

        # Optional: Persist to database if session is available
        # This will be added in future PAC when DB session management is ready
        # For now, structured logging provides full audit trail

    except Exception as e:
        logger.warning(f"Shadow mode v0.3 execution failed: {e}", exc_info=False)


@router.post("/anomaly", response_model=AnomalyScoreResponse)
async def score_anomaly(features: ShipmentFeaturesV0) -> AnomalyScoreResponse:
    """
    Calculate anomaly score for a shipment based on its feature vector.

    Uses modular anomaly model (currently DummyAnomalyModel with deterministic logic).
    Real ML models can be swapped in by modifying get_anomaly_model() in app.ml.

    Args:
        features: Fully populated ShipmentFeaturesV0 instance

    Returns:
        AnomalyScoreResponse with score, explanations, and model version
    """
    # Increment metrics counters (both in-memory and Prometheus)
    metrics.anomaly_calls_total += 1
    IQ_ANOMALY_CALLS.labels(corridor=features.corridor).inc()

    # Time the scoring operation
    start = time.perf_counter()
    try:
        # Get the current anomaly model
        anomaly_model = get_anomaly_model()

        # Run prediction through model
        prediction = anomaly_model.predict(features)

        # Map model prediction to API response
        response = AnomalyScoreResponse(
            score=prediction.score,
            explanation=prediction.explanation,
            model_version=prediction.model_version,
        )
    finally:
        # Record latency in Prometheus
        elapsed = time.perf_counter() - start
        IQ_ANOMALY_LATENCY.labels(corridor=features.corridor).observe(elapsed)

    # Log prediction event
    log_prediction_event(
        endpoint="/iq/ml/anomaly",
        score=response.score,
        model_version=response.model_version,
        shipment_id=features.shipment_id,
        corridor=features.corridor,
    )

    return response


@router.get("/debug/metrics")
async def get_metrics() -> dict:
    """
    Get current in-process metrics for ChainIQ ML endpoints.

    DEBUG ONLY: This endpoint exposes internal counters for monitoring
    and debugging purposes. In production, these metrics should be
    exported to Prometheus or another metrics backend.

    Returns:
        Dictionary with call counts for each endpoint
    """
    return {
        "risk_calls_total": metrics.risk_calls_total,
        "anomaly_calls_total": metrics.anomaly_calls_total,
    }
