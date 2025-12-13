"""Pydantic schemas for ESG Evidence entities."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class EsgEvidenceBase(BaseModel):
    """Base schema for EsgEvidence with common fields."""

    party_id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)  # AUDIT, CERTIFICATION, NGO_REPORT, etc.
    category: Optional[str] = None  # ENVIRONMENTAL, SOCIAL, GOVERNANCE
    subcategory: Optional[str] = None  # CARBON_FOOTPRINT, LABOR_RIGHTS, etc.
    source: str = Field(..., min_length=1)
    source_type: Optional[str] = None  # CERTIFIER, NGO, GOVERNMENT, INTERNAL, MEDIA
    source_url: Optional[str] = None
    document_id: Optional[str] = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    score_impact: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    weight: Optional[float] = None
    title: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: str = Field(default="ACTIVE")


class EsgEvidenceCreate(BaseModel):
    """Schema for creating new EsgEvidence."""

    party_id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    source: str = Field(..., min_length=1)
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    document_id: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    score_impact: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    weight: Optional[float] = None
    title: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class EsgEvidenceUpdate(BaseModel):
    """Schema for updating existing EsgEvidence."""

    type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    document_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    score_impact: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    weight: Optional[float] = None
    title: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class EsgEvidenceRead(EsgEvidenceBase):
    """Schema for reading EsgEvidence (includes ID and timestamps)."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EsgEvidenceListItem(BaseModel):
    """Lightweight schema for EsgEvidence listings."""

    id: str
    party_id: str
    type: str
    category: Optional[str] = None
    source: str
    score_impact: Optional[float] = None
    status: str
    issued_at: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
