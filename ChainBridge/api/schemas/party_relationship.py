"""Pydantic schemas for Party Relationship entities."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class PartyRelationshipBase(BaseModel):
    """Base schema for PartyRelationship with common fields."""

    from_party_id: str = Field(..., min_length=1)
    to_party_id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)  # SUPPLIES, SUBCONTRACTS_FOR, OPERATES_AT, OWNS, etc.
    description: Optional[str] = None
    role: Optional[str] = None
    tier: Optional[str] = None  # TIER_1, TIER_2, TIER_3
    status: str = Field(default="ACTIVE")  # ACTIVE, INACTIVE, TERMINATED, PENDING
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    attributes: Optional[Dict[str, Any]] = None
    verified: Optional[str] = None  # UNVERIFIED, SELF_REPORTED, VERIFIED, DISPUTED
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    source: Optional[str] = None  # MANUAL, CONTRACT, INTEGRATION, PUBLIC_RECORD
    source_document_id: Optional[str] = None


class PartyRelationshipCreate(BaseModel):
    """Schema for creating a new PartyRelationship."""

    from_party_id: str = Field(..., min_length=1)
    to_party_id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    description: Optional[str] = None
    role: Optional[str] = None
    tier: Optional[str] = None
    status: str = Field(default="ACTIVE")
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    attributes: Optional[Dict[str, Any]] = None
    verified: Optional[str] = None
    source: Optional[str] = None
    source_document_id: Optional[str] = None


class PartyRelationshipUpdate(BaseModel):
    """Schema for updating an existing PartyRelationship."""

    type: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    attributes: Optional[Dict[str, Any]] = None
    verified: Optional[str] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    source: Optional[str] = None
    source_document_id: Optional[str] = None


class PartyRelationshipRead(PartyRelationshipBase):
    """Schema for reading a PartyRelationship (includes ID and timestamps)."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartyRelationshipListItem(BaseModel):
    """Lightweight schema for PartyRelationship listings."""

    id: str
    from_party_id: str
    to_party_id: str
    type: str
    tier: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
