"""Pydantic schemas for Settlement Policy entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PolicyMilestone(BaseModel):
    """Schema for a milestone in a settlement policy curve."""

    name: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    percent: float = Field(..., ge=0, le=100)


class SettlementPolicyBase(BaseModel):
    """Base schema for SettlementPolicy with common fields."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    policy_type: Optional[str] = None  # STANDARD, EXPRESS, MILESTONE, ESCROW
    curve: List[PolicyMilestone] = Field(default_factory=list)
    conditions: Optional[Dict[str, Any]] = None
    max_exposure: Optional[float] = Field(None, ge=0)
    min_transaction: Optional[float] = Field(None, ge=0)
    max_transaction: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    rails: Optional[List[str]] = None  # ACH, WIRE, XRPL, USDC, etc.
    preferred_rail: Optional[str] = None
    fallback_rails: Optional[List[str]] = None
    settlement_delay_hours: Optional[float] = Field(None, ge=0)
    float_reduction_target: Optional[float] = Field(None, ge=0, le=1)
    effective_from: datetime = Field(default_factory=datetime.utcnow)
    effective_to: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    version: Optional[str] = None


class SettlementPolicyCreate(BaseModel):
    """Schema for creating a new SettlementPolicy."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    policy_type: Optional[str] = None
    curve: List[PolicyMilestone] = Field(default_factory=list)
    conditions: Optional[Dict[str, Any]] = None
    max_exposure: Optional[float] = Field(None, ge=0)
    min_transaction: Optional[float] = Field(None, ge=0)
    max_transaction: Optional[float] = Field(None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    rails: Optional[List[str]] = None
    preferred_rail: Optional[str] = None
    fallback_rails: Optional[List[str]] = None
    settlement_delay_hours: Optional[float] = Field(None, ge=0)
    float_reduction_target: Optional[float] = Field(None, ge=0, le=1)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    version: Optional[str] = None


class SettlementPolicyUpdate(BaseModel):
    """Schema for updating an existing SettlementPolicy."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    policy_type: Optional[str] = None
    curve: Optional[List[PolicyMilestone]] = None
    conditions: Optional[Dict[str, Any]] = None
    max_exposure: Optional[float] = Field(None, ge=0)
    min_transaction: Optional[float] = Field(None, ge=0)
    max_transaction: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    rails: Optional[List[str]] = None
    preferred_rail: Optional[str] = None
    fallback_rails: Optional[List[str]] = None
    settlement_delay_hours: Optional[float] = Field(None, ge=0)
    float_reduction_target: Optional[float] = Field(None, ge=0, le=1)
    effective_to: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    version: Optional[str] = None


class SettlementPolicyRead(SettlementPolicyBase):
    """Schema for reading a SettlementPolicy (includes ID and timestamps)."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettlementPolicyListItem(BaseModel):
    """Lightweight schema for SettlementPolicy listings."""

    id: str
    name: str
    policy_type: Optional[str] = None
    currency: str
    max_exposure: Optional[float] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
