"""Pydantic schemas for Party entities."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PartyBase(BaseModel):
    """Base schema for Party with common fields."""

    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., min_length=1, max_length=50)  # SHIPPER, CARRIER, BROKER, etc.
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    duns_number: Optional[str] = None
    country_code: Optional[str] = Field(None, max_length=3)
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str = Field(default="ACTIVE")
    extra_data: Optional[dict] = Field(None, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class PartyCreate(PartyBase):
    """Schema for creating a new Party."""

    pass


class PartyUpdate(BaseModel):
    """Schema for updating an existing Party."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = Field(None, min_length=1, max_length=50)
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    duns_number: Optional[str] = None
    country_code: Optional[str] = Field(None, max_length=3)
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None
    extra_data: Optional[dict] = Field(None, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class PartyRead(BaseModel):
    """Schema for reading a Party (includes ID and timestamps)."""

    id: str
    name: str
    type: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    duns_number: Optional[str] = None
    country_code: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    extra_data: Optional[dict] = None  # Maps to model's extra_data field
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartyListItem(BaseModel):
    """Lightweight schema for Party listings."""

    id: str
    name: str
    type: str
    country_code: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
