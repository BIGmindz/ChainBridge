"""
Pydantic schemas for ChainBoard Service.

Request and response validation for driver API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class DriverBase(BaseModel):
    """Base driver schema with common fields."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    dot_number: Optional[str] = Field(None, max_length=50)
    cdl_number: Optional[str] = Field(None, max_length=50)


class DriverCreate(DriverBase):
    """Schema for creating a new driver."""
    pass


class DriverUpdate(BaseModel):
    """Schema for updating driver information."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class DriverResponse(DriverBase):
    """Schema for driver API responses."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DriverListResponse(BaseModel):
    """Schema for listing drivers."""
    total: int
    drivers: list[DriverResponse]
