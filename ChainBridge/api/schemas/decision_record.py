"""Pydantic schemas for Decision Record entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DecisionRecordBase(BaseModel):
    """Base schema for DecisionRecord with common fields."""

    type: str = Field(..., min_length=1)  # RISK_DECISION, SETTLEMENT_DECISION, APPROVAL, OVERRIDE
    subtype: Optional[str] = None
    actor_type: str = Field(...)  # USER, APP, SYSTEM, AGENT
    actor_id: str = Field(..., min_length=1)
    actor_name: Optional[str] = None
    entity_type: Optional[str] = None  # SHIPMENT, PAYMENT_INTENT, PARTY, EXCEPTION
    entity_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_type: Optional[str] = None  # SETTLEMENT_POLICY, RISK_POLICY, COMPLIANCE_RULE
    policy_version: Optional[str] = None
    inputs_hash: Optional[str] = None
    inputs_snapshot: Optional[Dict[str, Any]] = None
    outputs: Dict[str, Any] = Field(...)
    explanation: Optional[str] = None
    primary_factors: Optional[List[str]] = None
    overrides_decision_id: Optional[str] = None
    override_reason: Optional[str] = None


class DecisionRecordCreate(BaseModel):
    """Schema for creating a new DecisionRecord."""

    type: str = Field(..., min_length=1)
    subtype: Optional[str] = None
    actor_type: str = Field(...)
    actor_id: str = Field(..., min_length=1)
    actor_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_type: Optional[str] = None
    policy_version: Optional[str] = None
    inputs_hash: Optional[str] = None
    inputs_snapshot: Optional[Dict[str, Any]] = None
    outputs: Dict[str, Any] = Field(...)
    explanation: Optional[str] = None
    primary_factors: Optional[List[str]] = None
    overrides_decision_id: Optional[str] = None
    override_reason: Optional[str] = None


class DecisionRecordRead(DecisionRecordBase):
    """Schema for reading a DecisionRecord (includes ID and timestamp)."""

    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionRecordListItem(BaseModel):
    """Lightweight schema for DecisionRecord listings."""

    id: str
    type: str
    subtype: Optional[str] = None
    actor_type: str
    actor_id: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# OC Response Types - Match frontend expectations
# =============================================================================


class DecisionRecordOC(BaseModel):
    """Decision record format for OC frontend (matches frontend DecisionRecord)."""

    id: str
    type: str
    actor: str  # Computed: actor_name or actor_id
    actor_type: str  # SYSTEM, OPERATOR, API
    policy_id: Optional[str] = None
    policy_name: Optional[str] = None  # Computed from policy lookup
    exception_id: Optional[str] = None  # entity_id when entity_type=EXCEPTION
    shipment_id: Optional[str] = None  # entity_id when entity_type=SHIPMENT
    summary: str  # explanation field
    details: Optional[Dict[str, Any]] = None  # outputs field
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionRecordsListResponse(BaseModel):
    """Paginated decision records response (matches frontend DecisionRecordsListResponse)."""

    records: List[DecisionRecordOC]
    total: int
    page: int = 1
    page_size: int = 20
