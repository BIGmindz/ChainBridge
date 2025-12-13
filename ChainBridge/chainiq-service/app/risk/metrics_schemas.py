"""Contracts for analytics-ready risk metrics.

These Pydantic models mirror the expected warehouse tables while keeping the
service storage-agnostic. They can later be mapped to SQLAlchemy or dbt
models without changing the risk service surface area.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.risk.schemas import RiskBand


class FeaturesSnapshot(BaseModel):
    value_usd: float = Field(..., description="Shipment value in USD")
    is_hazmat: bool = Field(..., description="Hazardous materials flag")
    is_temp_control: bool = Field(..., description="Temperature controlled flag")
    expected_transit_days: int = Field(..., ge=0, description="Planned transit time in days")
    iot_alert_count: int = Field(..., ge=0, description="IoT alerts in the last 30 days")
    recent_delay_events: int = Field(..., ge=0, description="Recent delay events impacting the lane/carrier")
    lane_risk_index: float = Field(..., ge=0, description="Composite risk index for the lane")
    border_crossing_count: int = Field(..., ge=0, description="Number of border crossings for the lane")


class RiskEvaluationRecord(BaseModel):
    event_type: str = Field("RISK_EVALUATION", description="Event discriminator for downstream parsing")
    evaluation_id: str = Field(..., description="Unique identifier for the evaluation event")
    timestamp: datetime = Field(..., description="UTC timestamp when the score was produced")
    model_version: str = Field(..., description="Model version used for scoring")
    shipment_id: str = Field(..., description="Shipment identifier")
    carrier_id: str = Field(..., description="Carrier identifier")
    lane_id: str = Field(..., description="Lane identifier (e.g., ORG-DST)")
    risk_score: int = Field(..., ge=0, le=100, description="Final risk score")
    risk_band: RiskBand = Field(..., description="Risk band classification")
    primary_reasons: List[str] = Field(default_factory=list, description="Primary contributors to the score")
    features_snapshot: FeaturesSnapshot = Field(..., description="Feature vector at evaluation time")


class RiskModelMetricsRecord(BaseModel):
    model_version: str = Field(..., description="Model version the metrics describe")
    window_start: datetime = Field(..., description="Start of the metrics window (UTC)")
    window_end: datetime = Field(..., description="End of the metrics window (UTC)")
    total_evaluations: int = Field(..., ge=0, description="Number of evaluations in the window")
    avg_score: float = Field(..., ge=0, le=100, description="Average score across evaluations")
    p50_score: Optional[float] = Field(None, description="Median score")
    p90_score: Optional[float] = Field(None, description="90th percentile score")
    p99_score: Optional[float] = Field(None, description="99th percentile score")
    risk_band_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts per band, keyed by band name (e.g., LOW, MEDIUM, HIGH)",
    )
    data_freshness_ts: Optional[datetime] = Field(None, description="Timestamp when metrics were computed")


class RiskEvaluationAPIModel(BaseModel):
    """Read-only API response model for risk evaluation history.

    This model is used by the /risk/evaluations endpoint to return
    persisted evaluations to ChainBoard's Risk Console.
    """

    evaluation_id: str = Field(..., description="Unique identifier for the evaluation event")
    timestamp: datetime = Field(..., description="UTC timestamp when the score was produced")
    model_version: str = Field(..., description="Model version used for scoring")
    shipment_id: str = Field(..., description="Shipment identifier")
    carrier_id: Optional[str] = Field(None, description="Carrier identifier")
    lane_id: Optional[str] = Field(None, description="Lane identifier (e.g., ORG-DST)")
    risk_score: int = Field(..., ge=0, le=100, description="Final risk score")
    risk_band: str = Field(..., description="Risk band classification (LOW, MEDIUM, HIGH, CRITICAL)")
    primary_reasons: List[str] = Field(default_factory=list, description="Primary contributors to the score")
    features_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Feature vector at evaluation time",
    )

    class Config:
        from_attributes = True  # Pydantic v2 ORM mode


class RiskEvaluationsResponse(BaseModel):
    """Paginated response model for risk evaluations history.

    Used by GET /risk/evaluations to return a paginated list with metadata.
    """

    items: List[RiskEvaluationAPIModel] = Field(..., description="List of evaluation records")
    total: int = Field(..., ge=0, description="Total count of records matching filters")
    limit: int = Field(..., ge=1, description="Maximum records returned per page")
    offset: int = Field(..., ge=0, description="Number of records skipped")


class RiskModelMetricsAPIModel(BaseModel):
    """Read-only API response model for risk model metrics.

    This model is used by the /risk/metrics/latest endpoint to expose
    aggregated metrics to ChainBoard dashboards and governance.
    """

    model_version: str = Field(..., description="Model version the metrics describe")
    window_start: datetime = Field(..., description="Start of the metrics window (UTC)")
    window_end: datetime = Field(..., description="End of the metrics window (UTC)")
    total_evaluations: int = Field(..., ge=0, description="Number of evaluations in the window")
    avg_score: Optional[float] = Field(None, ge=0, le=100, description="Average score across evaluations")
    p50_score: Optional[float] = Field(None, description="Median score")
    p90_score: Optional[float] = Field(None, description="90th percentile score")
    p99_score: Optional[float] = Field(None, description="99th percentile score")
    risk_band_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts per band, keyed by band name (e.g., LOW, MEDIUM, HIGH)",
    )
    # Maggie-style metrics
    critical_incident_recall: Optional[float] = Field(None, description="Recall for critical incidents")
    high_risk_precision: Optional[float] = Field(None, description="Precision for high-risk predictions")
    ops_workload_percent: Optional[float] = Field(None, description="Percentage of ops workload")
    incident_rate_low: Optional[float] = Field(None, description="Incident rate in LOW band")
    incident_rate_medium: Optional[float] = Field(None, description="Incident rate in MEDIUM band")
    incident_rate_high: Optional[float] = Field(None, description="Incident rate in HIGH band")
    calibration_monotonic: Optional[bool] = Field(None, description="Whether calibration is monotonic")
    calibration_ratio_high_vs_low: Optional[float] = Field(None, description="Calibration ratio HIGH vs LOW")
    loss_value_coverage_pct: Optional[float] = Field(None, description="Loss value coverage percentage")
    # Red flag results
    has_failures: Optional[bool] = Field(None, description="Whether any red-flag failures occurred")
    has_warnings: Optional[bool] = Field(None, description="Whether any red-flag warnings occurred")
    fail_messages: Optional[List[str]] = Field(None, description="Red-flag failure messages")
    warning_messages: Optional[List[str]] = Field(None, description="Red-flag warning messages")
    # Metadata
    data_freshness_ts: Optional[datetime] = Field(None, description="Timestamp when metrics were computed")

    class Config:
        from_attributes = True  # Pydantic v2 ORM mode
