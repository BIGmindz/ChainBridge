"""
core/events.py - Event Schema for Execution Spine
PAC-CODY-EXEC-SPINE-01

Canonical event schema:
- event_type: str
- payload: dict
- timestamp: ISO8601 string
- event_id: UUID

CONSTRAINTS:
- All fields required (no optional)
- Immutable after creation
- Hashable for proof generation
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class IngestEvent(BaseModel):
    """
    Canonical event schema for /events/ingest endpoint.
    
    Minimal schema - event_type + payload.
    event_id and timestamp are generated server-side.
    """
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: str = Field(..., min_length=1, description="Type of event")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp of event creation"
    )
    
    model_config = {"frozen": True}  # Immutable
    
    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Event type must be non-empty string."""
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()
    
    @field_validator("payload")
    @classmethod
    def validate_payload_not_empty(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Payload must contain data."""
        if not v:
            raise ValueError("payload cannot be empty")
        return v
    
    def to_canonical_dict(self) -> Dict[str, Any]:
        """
        Return canonical dict representation for hashing.
        Keys sorted, deterministic.
        """
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }
    
    def compute_hash(self) -> str:
        """
        Compute deterministic SHA-256 hash of this event.
        Uses canonical JSON encoding (sorted keys, no whitespace).
        """
        canonical = json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IngestEventRequest(BaseModel):
    """
    Request schema for POST /events/ingest.
    Client provides event_type and payload only.
    """
    event_type: str = Field(..., min_length=1, description="Type of event")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    
    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Event type must be non-empty string."""
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()
    
    @field_validator("payload")
    @classmethod
    def validate_payload_not_empty(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Payload must contain data."""
        if not v:
            raise ValueError("payload cannot be empty")
        return v


def create_event(event_type: str, payload: Dict[str, Any]) -> IngestEvent:
    """
    Factory function to create an IngestEvent from request data.
    
    Args:
        event_type: Type of event
        payload: Event payload data
        
    Returns:
        Immutable IngestEvent with generated event_id and timestamp
    """
    return IngestEvent(
        event_type=event_type,
        payload=payload,
    )
