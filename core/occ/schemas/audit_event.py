"""
Audit Event Pydantic Models (v2 syntax)

Audit events provide an append-only timeline of changes to artifacts.
Events are immutable once created.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuditEventType(str, Enum):
    """Types of audit events that can occur on an artifact."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    STATUS_CHANGED = "STATUS_CHANGED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"
    COMMENT = "COMMENT"
    CUSTOM = "CUSTOM"


class AuditEventCreate(BaseModel):
    """Schema for creating a new audit event (internal/system use)."""

    model_config = ConfigDict(use_enum_values=True)

    event_type: AuditEventType = Field(..., description="Type of audit event")
    actor: Optional[str] = Field(None, max_length=255, description="User/system that triggered the event")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event-specific details")
    policy_ref: Optional[str] = Field(None, max_length=500, description="Reference to policy/rule that triggered event")
    signature_ref: Optional[str] = Field(None, max_length=500, description="Cryptographic signature reference")


class AuditEvent(BaseModel):
    """Full audit event model with server-generated fields."""

    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    artifact_id: UUID = Field(..., description="ID of the artifact this event belongs to")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    actor: Optional[str] = Field(None, max_length=255, description="User/system that triggered the event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred (UTC)",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Event-specific details")
    policy_ref: Optional[str] = Field(None, max_length=500, description="Reference to policy/rule")
    signature_ref: Optional[str] = Field(None, max_length=500, description="Cryptographic signature reference")


class AuditEventList(BaseModel):
    """Response model for listing audit events."""

    artifact_id: UUID
    events: list[AuditEvent]
    count: int
