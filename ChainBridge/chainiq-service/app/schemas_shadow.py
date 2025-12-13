"""
Shadow Mode API Schemas

Pydantic models for Shadow Mode API endpoints.
ALEX-compliant schemas with strict validation and version tracking.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ShadowEventResponse(BaseModel):
    """
    Individual shadow mode event.

    Represents a single comparison between dummy and real model scores.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Event ID")
    shipment_id: str = Field(..., description="Shipment identifier")
    dummy_score: float = Field(..., ge=0.0, le=1.0, description="Dummy model score [0,1]")
    real_score: float = Field(..., ge=0.0, le=1.0, description="Real model score [0,1]")
    delta: float = Field(..., ge=0.0, le=1.0, description="Absolute score difference")
    model_version: str = Field(..., description="Model version identifier")
    corridor: Optional[str] = Field(None, description="Trade corridor (e.g., US-CN)")
    created_at: datetime = Field(..., description="Event timestamp (UTC)")


class ShadowStatsResponse(BaseModel):
    """
    Aggregated shadow mode statistics.

    Provides P50/P95/P99 metrics for model score deltas.
    ALEX-compliant: includes model_version and drift detection.
    """

    count: int = Field(..., ge=0, description="Total number of shadow events")
    mean_delta: float = Field(..., ge=0.0, description="Mean absolute delta")
    median_delta: float = Field(..., ge=0.0, description="Median absolute delta")
    std_delta: float = Field(..., ge=0.0, description="Standard deviation of deltas")
    p50_delta: float = Field(..., ge=0.0, description="50th percentile delta")
    p95_delta: float = Field(..., ge=0.0, description="95th percentile delta")
    p99_delta: float = Field(..., ge=0.0, description="99th percentile delta")
    max_delta: float = Field(..., ge=0.0, le=1.0, description="Maximum delta observed")
    drift_flag: bool = Field(..., description="True if P95 > 0.25 (drift detected)")
    model_version: str = Field(default="v0.2.0", description="Model version analyzed")
    time_window_hours: int = Field(default=24, ge=1, description="Analysis time window")


class ShadowCorridorStatsResponse(BaseModel):
    """
    Corridor-level shadow mode statistics.

    Enables regional model performance monitoring and drift detection.
    """

    corridor: str = Field(..., description="Trade corridor identifier")
    event_count: int = Field(..., ge=0, description="Number of events in corridor")
    mean_delta: float = Field(..., ge=0.0, description="Mean absolute delta")
    median_delta: float = Field(..., ge=0.0, description="Median absolute delta")
    p95_delta: float = Field(..., ge=0.0, description="95th percentile delta")
    max_delta: float = Field(..., ge=0.0, le=1.0, description="Maximum delta observed")
    drift_flag: bool = Field(..., description="True if P95 > 0.25 (drift detected)")
    time_window_hours: int = Field(..., ge=1, description="Analysis time window")


class ShadowCorridorsResponse(BaseModel):
    """
    Multi-corridor analysis response.

    Returns statistics for all corridors with sufficient data volume.
    """

    corridors: List[ShadowCorridorStatsResponse] = Field(..., description="List of corridor statistics")
    total_corridors: int = Field(..., ge=0, description="Total number of corridors analyzed")
    drifting_count: int = Field(..., ge=0, description="Number of corridors with drift_flag=True")
    model_version: str = Field(default="v0.2.0", description="Model version analyzed")
    time_window_hours: int = Field(default=24, ge=1, description="Analysis time window")


class ShadowDriftResponse(BaseModel):
    """
    Model drift analysis response.

    Provides drift detection metrics and high-delta event identification.
    ALEX-compliant: includes model version and time window metadata.
    """

    drift_detected: bool = Field(..., description="True if significant drift detected")
    p95_delta: float = Field(..., ge=0.0, description="95th percentile delta")
    high_delta_count: int = Field(..., ge=0, description="Number of events with delta > threshold")
    total_events: int = Field(..., ge=0, description="Total events analyzed")
    model_version: str = Field(default="v0.2.0", description="Model version analyzed")
    lookback_hours: int = Field(..., ge=1, description="Analysis time window")
    drift_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="P95 threshold for drift")


class ShadowEventsResponse(BaseModel):
    """
    List of shadow mode events.

    Paginated response with metadata for event browsing.
    """

    events: List[ShadowEventResponse] = Field(..., description="List of shadow events")
    total_count: int = Field(..., ge=0, description="Total events matching filters")
    limit: int = Field(..., ge=1, le=1000, description="Maximum events returned")
    corridor: Optional[str] = Field(None, description="Corridor filter applied (if any)")
    model_version: str = Field(default="v0.2.0", description="Model version filter")
    time_window_hours: int = Field(default=24, ge=1, description="Time window queried")
