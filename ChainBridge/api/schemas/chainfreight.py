"""Pydantic schemas for ChainFreight ingestion API."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator


class IngestionBatchCreate(BaseModel):
    """Request payload for creating a new ingestion batch."""

    source_system: str = Field(..., description="Source system identifier")
    batch_type: str = Field(..., description="Type of data being ingested")
    records: List[Dict[str, Any]] = Field(..., description="Raw records to ingest")

    @validator("source_system")
    def validate_source_system(cls, v):
        allowed_systems = {"SEEBURGER", "PROJECT44", "TELEMATICS", "MANUAL", "API"}
        if v not in allowed_systems:
            raise ValueError(f"source_system must be one of {allowed_systems}")
        return v

    @validator("batch_type")
    def validate_batch_type(cls, v):
        allowed_types = {"EDI_214", "EDI_210", "EDI_856", "TELEMATICS", "MILESTONE_UPDATE"}
        if v not in allowed_types:
            raise ValueError(f"batch_type must be one of {allowed_types}")
        return v


class IngestionBatchResponse(BaseModel):
    """Response for ingestion batch operations."""

    id: str
    source_system: str
    batch_type: str
    total_records: int
    processed_records: int
    failed_records: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_summary: Optional[str] = None


class IngestionRecordResponse(BaseModel):
    """Response for individual ingestion records."""

    id: str
    batch_id: str
    external_id: Optional[str] = None
    record_type: str
    shipment_reference: Optional[str] = None
    processing_status: str
    error_message: Optional[str] = None
    reconciliation_status: Optional[str] = None
    matched_shipment_id: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None


class ShipmentEventCreate(BaseModel):
    """Request payload for creating shipment events."""

    shipment_id: str
    event_type: str
    event_timestamp: datetime
    event_code: Optional[str] = None
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    carrier_code: Optional[str] = None
    equipment_id: Optional[str] = None
    source_system: str = "API"
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None

    @validator("event_type")
    def validate_event_type(cls, v):
        allowed_events = {
            "PICKUP",
            "DELIVERY",
            "IN_TRANSIT",
            "ARRIVED_FACILITY",
            "DEPARTED_FACILITY",
            "CUSTOMS_CLEARANCE",
            "EXCEPTION",
            "DELAY",
        }
        if v not in allowed_events:
            raise ValueError(f"event_type must be one of {allowed_events}")
        return v


class ShipmentEventResponse(BaseModel):
    """Response for shipment event operations."""

    id: str
    shipment_id: str
    event_type: str
    event_code: Optional[str] = None
    event_timestamp: datetime
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    carrier_code: Optional[str] = None
    equipment_id: Optional[str] = None
    source_system: str
    source_record_id: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ReconciliationRequest(BaseModel):
    """Request payload for manual reconciliation."""

    batch_id: Optional[str] = None
    shipment_references: Optional[List[str]] = None
    force_reprocess: bool = False


class ReconciliationResponse(BaseModel):
    """Response for reconciliation operations."""

    processed_records: int
    matched_records: int
    unmatched_records: int
    errors: List[str]
    batch_summary: Optional[Dict[str, int]] = None


class IngestionStatsResponse(BaseModel):
    """Statistics for ingestion operations."""

    total_batches: int
    total_records: int
    processed_records: int
    failed_records: int
    pending_records: int
    recent_batches: List[IngestionBatchResponse]
    source_breakdown: Dict[str, int]
    type_breakdown: Dict[str, int]
