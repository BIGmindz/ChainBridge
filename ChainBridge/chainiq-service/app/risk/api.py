"""FastAPI router for ChainIQ risk scoring."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.risk.metrics_schemas import RiskEvaluationsResponse, RiskModelMetricsAPIModel
from app.risk.schemas import ShipmentRiskRequest, ShipmentRiskResponse
from app.risk.service import get_latest_risk_metrics, list_risk_evaluations, score_shipment

try:
    from app.dependencies import get_db  # type: ignore
except ImportError:  # pragma: no cover - fallback for current skeleton

    async def get_db():
        return None


router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/score", response_model=ShipmentRiskResponse)
async def score_shipment_endpoint(
    request: ShipmentRiskRequest,
    db=Depends(get_db),
) -> ShipmentRiskResponse:
    """Scores a single shipment using the ChainIQ risk engine."""
    return await score_shipment(request=request, db=db)


@router.get(
    "/evaluations",
    response_model=RiskEvaluationsResponse,
    summary="List risk evaluations with pagination",
    tags=["risk"],
)
def list_risk_evaluations_endpoint(
    limit: int = Query(25, ge=1, le=100, description="Maximum number of evaluations to return"),
    offset: int = Query(0, ge=0, description="Number of evaluations to skip"),
    risk_band: Optional[str] = Query(
        None,
        description="Filter by risk band (LOW, MEDIUM, HIGH, CRITICAL)",
        pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$",
    ),
    search: Optional[str] = Query(None, description="Free-text search across shipment_id, carrier_id, lane_id"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    db: Session = Depends(get_db),
) -> RiskEvaluationsResponse:
    """Returns a paginated list of risk evaluations for ChainIQ Risk Console.

    Supports filtering by risk_band, model_version, and free-text search.
    Results are ordered by timestamp descending (most recent first).
    Maximum limit is 100.
    """
    items, total = list_risk_evaluations(
        db=db,
        limit=limit,
        offset=offset,
        model_version=model_version,
        risk_band=risk_band,
        search=search,
    )

    return RiskEvaluationsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/metrics/latest",
    response_model=RiskModelMetricsAPIModel,
    summary="Get latest risk model metrics",
    tags=["risk"],
)
def get_latest_metrics_endpoint(
    db: Session = Depends(get_db),
) -> RiskModelMetricsAPIModel:
    """Returns the latest computed risk model metrics for dashboards and governance.

    This endpoint exposes aggregated metrics including score distributions,
    percentiles, Maggie-style calibration metrics, and red-flag results.

    Raises:
        HTTPException: 404 if no metrics are available yet.
    """
    metrics = get_latest_risk_metrics(db=db)

    if metrics is None:
        raise HTTPException(status_code=404, detail="No metrics available")

    return metrics
