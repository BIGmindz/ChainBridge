"""Pydantic schemas for Exception entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExceptionBase(BaseModel):
    """Base schema for Exception with common fields."""

    shipment_id: Optional[str] = None
    playbook_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    type: str = Field(..., min_length=1, max_length=50)  # DELAY, MISSING_POD, CLAIM_RISK, etc.
    severity: str = Field(default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status: str = Field(default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED, WONT_FIX, ESCALATED
    owner_user_id: Optional[str] = None
    escalated_to: Optional[str] = None
    summary: str = Field(..., min_length=1, max_length=500)
    details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    source_event_id: Optional[str] = None


class ExceptionCreate(ExceptionBase):
    """Schema for creating a new Exception."""

    pass


class ExceptionUpdate(BaseModel):
    """Schema for updating an existing Exception."""

    playbook_id: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    owner_user_id: Optional[str] = None
    escalated_to: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=500)
    details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None


class ExceptionResolve(BaseModel):
    """Schema for resolving an Exception."""

    resolution_type: str = Field(..., min_length=1)  # MANUAL_FIX, AUTO_RESOLVED, WAIVED, etc.
    resolution_notes: Optional[str] = None


class ExceptionRead(BaseModel):
    """Schema for reading an Exception (matches frontend Exception type)."""

    id: str
    type: str
    severity: str
    status: str
    summary: str
    description: Optional[str] = None  # Alias for notes field
    shipment_id: Optional[str] = None
    shipment_reference: Optional[str] = None  # Computed from shipment lookup
    playbook_id: Optional[str] = None
    owner_id: Optional[str] = None  # Alias for owner_user_id
    owner_name: Optional[str] = None  # Computed from user lookup
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    # Note: 'metadata' field removed to avoid conflict with SQLAlchemy Base.metadata
    # Additional details can be retrieved via the 'details' field in the model

    model_config = ConfigDict(from_attributes=True)


class ExceptionListItem(BaseModel):
    """Lightweight schema for Exception listings."""

    id: str
    shipment_id: Optional[str] = None
    type: str
    severity: str
    status: str
    owner_user_id: Optional[str] = None
    summary: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# OC (Exception Cockpit) Response Types - Match frontend expectations
# =============================================================================


class ExceptionStats(BaseModel):
    """Exception statistics for KPI display (matches frontend ExceptionStats)."""

    total_open: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    resolved_today: int = 0
    avg_resolution_time_hours: Optional[float] = None


class ExceptionsListResponse(BaseModel):
    """Paginated exceptions response (matches frontend ExceptionsListResponse)."""

    exceptions: List[ExceptionRead]
    total: int
    page: int = 1
    page_size: int = 20


class PlaybookSummary(BaseModel):
    """Lightweight playbook info for exception detail response."""

    id: str
    name: str
    description: Optional[str] = None
    exception_type: Optional[str] = None  # category in backend
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class DecisionRecordSummary(BaseModel):
    """Decision record summary for exception detail response."""

    id: str
    type: str
    actor: str  # Computed from actor_name or actor_id
    actor_type: str
    policy_id: Optional[str] = None
    policy_name: Optional[str] = None  # Computed from policy lookup
    exception_id: Optional[str] = None  # entity_id if entity_type is EXCEPTION
    shipment_id: Optional[str] = None  # entity_id if entity_type is SHIPMENT
    summary: str  # explanation field
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExceptionDetailResponse(BaseModel):
    """Full exception detail with related data (matches frontend ExceptionDetailResponse)."""

    exception: ExceptionRead
    playbook: Optional[PlaybookSummary] = None
    recent_decisions: List[DecisionRecordSummary] = Field(default_factory=list)
