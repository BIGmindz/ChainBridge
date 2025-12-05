"""
Pydantic schemas for ChainPay Service.

Request and response validation for payment intent and settlement API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PaymentStatusEnum(str, Enum):
    """Payment status options."""

    PENDING = "pending"
    APPROVED = "approved"
    SETTLED = "settled"
    DELAYED = "delayed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RiskTierEnum(str, Enum):
    """Risk tier options."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- Payment Intent Schemas ---


class PaymentIntentBase(BaseModel):
    """Base payment intent schema with common fields."""

    freight_token_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=10)
    description: Optional[str] = Field(None, max_length=255)


class PaymentIntentCreate(PaymentIntentBase):
    """Schema for creating a new payment intent."""

    pass


class PaymentIntentUpdate(BaseModel):
    """Schema for updating payment intent."""

    status: Optional[PaymentStatusEnum] = None
    settlement_notes: Optional[str] = None


class PaymentIntentResponse(PaymentIntentBase):
    """Schema for payment intent API responses."""

    id: int
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_category: Optional[str] = None
    risk_tier: RiskTierEnum
    status: PaymentStatusEnum
    settlement_approved_at: Optional[datetime] = None
    settlement_delayed_until: Optional[datetime] = None
    settlement_completed_at: Optional[datetime] = None
    settlement_reason: Optional[str] = None
    settlement_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentIntentListResponse(BaseModel):
    """Schema for listing payment intents."""

    total: int
    payment_intents: list[PaymentIntentResponse]


# --- Settlement Request/Response ---


class SettlementRequest(BaseModel):
    """Request to settle a payment intent."""

    settlement_notes: Optional[str] = Field(None, max_length=500)
    force_approval: bool = Field(default=False, description="Override risk checks (requires special permission)")


class SettlementResponse(BaseModel):
    """Response from settlement operation."""

    payment_intent_id: int
    status: PaymentStatusEnum
    action_taken: str  # "approved", "delayed", "rejected"
    settlement_approved_at: Optional[datetime] = None
    settlement_delayed_until: Optional[datetime] = None
    settlement_reason: str
    risk_factors: Optional[str] = None

    class Config:
        from_attributes = True


class RiskAssessmentResponse(BaseModel):
    """Risk assessment for a payment intent."""

    payment_intent_id: int
    freight_token_id: int
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_category: Optional[str]
    risk_tier: RiskTierEnum
    settlement_delay: str  # Human-readable delay (e.g., "immediate", "24 hours")
    recommended_action: str  # Business recommendation
    created_at: datetime


class SettlementLogResponse(BaseModel):
    """Schema for settlement audit logs."""

    id: int
    payment_intent_id: int
    action: str
    reason: Optional[str] = None
    triggered_by: str
    approved_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SettlementHistoryResponse(BaseModel):
    """Settlement history for a payment intent."""

    payment_intent_id: int
    logs: list[SettlementLogResponse]
    total_actions: int


# --- Payment Schedule & Milestone Schemas ---


class PaymentScheduleItemCreate(BaseModel):
    """Schema for creating a payment schedule item."""

    event_type: str = Field(..., max_length=50, description="Shipment event type")
    percentage: float = Field(..., ge=0.0, le=1.0, description="Percentage of total payment (0.0-1.0)")
    order: int = Field(..., ge=1, description="Sequence order in schedule")


class PaymentScheduleItemResponse(BaseModel):
    """Schema for payment schedule item API response."""

    id: int
    schedule_id: int
    event_type: str
    percentage: float
    order: int
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentScheduleResponse(BaseModel):
    """Schema for payment schedule API response."""

    id: int
    payment_intent_id: int
    risk_tier: RiskTierEnum
    items: list[PaymentScheduleItemResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class MilestoneSettlementCreate(BaseModel):
    """Schema for creating a milestone settlement (internal use via webhook)."""

    payment_intent_id: int = Field(..., gt=0)
    event_type: str = Field(..., max_length=50)
    settlement_amount: float = Field(..., gt=0)
    shipment_event_id: Optional[int] = None


class MilestoneSettlementResponse(BaseModel):
    """Schema for milestone settlement API response."""

    id: int
    payment_intent_id: int
    event_type: str
    settlement_amount: float
    status: PaymentStatusEnum
    shipment_event_id: Optional[int] = None
    settled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentEventWebhookRequest(BaseModel):
    """Request body from ChainFreight webhook for shipment event."""

    shipment_id: int = Field(..., gt=0)
    event_type: str = Field(..., max_length=50)
    occurred_at: datetime
    event_id: Optional[int] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat()}

    def dict(self, *args, **kwargs):  # type: ignore[override]
        data = super().dict(*args, **kwargs)
        occurred = data.get("occurred_at")
        if isinstance(occurred, datetime):
            data["occurred_at"] = occurred.isoformat()
        return data


class ShipmentEventWebhookResponse(BaseModel):
    """Response from shipment event webhook processing."""

    shipment_id: int
    event_type: str
    processed_at: datetime
    milestone_settlements_created: int
    message: str
