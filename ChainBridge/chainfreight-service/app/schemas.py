"""
Pydantic schemas for ChainFreight Service.

Request and response validation for shipment and freight token API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ShipmentStatusEnum(str, Enum):
    """Shipment status options."""

    PLANNED = "planned"
    PENDING = "pending"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class FreightTokenStatusEnum(str, Enum):
    """Freight token status options."""

    CREATED = "created"
    ACTIVE = "active"
    LOCKED = "locked"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ShipmentEventTypeEnum(str, Enum):
    """Shipment event type options."""

    CREATED = "created"
    PICKUP_CONFIRMED = "pickup_confirmed"
    IN_TRANSIT = "in_transit"
    AT_TERMINAL = "at_terminal"
    DELIVERY_ATTEMPTED = "delivery_attempted"
    POD_CONFIRMED = "pod_confirmed"
    CLAIM_WINDOW_CLOSED = "claim_window_closed"


class ShipmentBase(BaseModel):
    """Base shipment schema with common fields."""

    shipper_name: str = Field(..., min_length=1, max_length=255)
    origin: str = Field(..., min_length=1, max_length=255)
    destination: str = Field(..., min_length=1, max_length=255)
    cargo_value: Optional[float] = Field(None, gt=0)
    pickup_date: Optional[datetime] = None
    planned_delivery_date: Optional[datetime] = None
    pickup_eta: Optional[datetime] = None
    delivery_eta: Optional[datetime] = None


class ShipmentCreate(ShipmentBase):
    """Schema for creating a new shipment."""

    pass


class ShipmentUpdate(BaseModel):
    """Schema for updating shipment information."""

    shipper_name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[ShipmentStatusEnum] = None
    actual_delivery_date: Optional[datetime] = None


class ShipmentResponse(ShipmentBase):
    """Schema for shipment API responses."""

    id: int
    status: ShipmentStatusEnum
    actual_delivery_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentListResponse(BaseModel):
    """Schema for listing shipments."""

    total: int
    shipments: list[ShipmentResponse]


# --- Freight Token Schemas ---


class FreightTokenBase(BaseModel):
    """Base freight token schema."""

    face_value: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=10)


class FreightTokenCreate(FreightTokenBase):
    """Schema for creating a new freight token."""

    pass


class FreightTokenResponse(FreightTokenBase):
    """Schema for freight token API responses."""

    id: int
    shipment_id: int
    status: FreightTokenStatusEnum
    token_address: Optional[str] = None
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_category: Optional[str] = None
    recommended_action: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FreightTokenListResponse(BaseModel):
    """Schema for listing freight tokens."""

    total: int
    tokens: list[FreightTokenResponse]


class TokenizeShipmentRequest(BaseModel):
    """Request to tokenize a shipment."""

    face_value: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=10)


# --- Shipment Event Schemas ---


class ShipmentEventCreate(BaseModel):
    """Schema for recording a new shipment event."""

    event_type: ShipmentEventTypeEnum = Field(..., description="Type of event")
    occurred_at: Optional[datetime] = Field(None, description="When event occurred; defaults to now if omitted")
    metadata: Optional[str] = Field(None, max_length=500, description="Additional context (e.g., proof hash)")


class ShipmentEventResponse(BaseModel):
    """Schema for shipment event API responses."""

    id: int
    shipment_id: int
    event_type: ShipmentEventTypeEnum
    occurred_at: datetime
    metadata: Optional[str] = None
    recorded_at: datetime
    webhook_sent: int
    webhook_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ShipmentEventListResponse(BaseModel):
    """Schema for listing shipment events."""

    total: int
    events: list[ShipmentEventResponse]
