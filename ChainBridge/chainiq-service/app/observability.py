"""
ChainIQ Observability Module

Provides structured logging and timing utilities for ChainIQ ML endpoints.
Follows existing chainiq-service patterns using Python logging module.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@contextmanager
def timed(operation: str, extra: dict[str, Any] | None = None) -> Iterator[None]:
    """
    Context manager to measure elapsed time for an operation.

    Logs the operation timing with structured data when exiting.

    Args:
        operation: Name of the operation being timed (e.g., "iq_risk_score")
        extra: Optional additional fields to include in the log payload

    Example:
        with timed("iq_risk_score", extra={"corridor": "US-MX"}):
            # do expensive work
            result = compute_risk_score(...)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        payload: dict[str, Any] = {"operation": operation, "elapsed_s": round(elapsed, 4)}
        if extra:
            payload.update(extra)
        logger.info("operation_timing", extra=payload)


def log_prediction_event(
    endpoint: str,
    score: float,
    model_version: str,
    shipment_id: str | None = None,
    corridor: str | None = None,
) -> None:
    """
    Log a structured event for a single ML prediction.

    Args:
        endpoint: API endpoint that generated the prediction (e.g., "/iq/ml/risk-score")
        score: The computed score (0.0 to 1.0)
        model_version: Version identifier of the model used
        shipment_id: Optional shipment identifier
        corridor: Optional corridor/lane identifier

    Example:
        log_prediction_event(
            endpoint="/iq/ml/risk-score",
            score=0.65,
            model_version="risk_stub_v0.1",
            shipment_id="SHP-123",
            corridor="US-MX",
        )
    """
    payload: dict[str, Any] = {
        "event": "iq_prediction",
        "endpoint": endpoint,
        "score": round(score, 4),
        "model_version": model_version,
    }
    if shipment_id is not None:
        payload["shipment_id"] = shipment_id
    if corridor is not None:
        payload["corridor"] = corridor
    logger.info("iq_prediction", extra=payload)
