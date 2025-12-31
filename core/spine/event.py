"""
Spine Event Schema - PAC-BENSON-EXEC-SPINE-01

Canonical event schema for the Minimum Execution Spine.

Schema (LOCKED):
- event_type: str
- payload: dict
- timestamp: ISO8601 string

CONSTRAINTS:
- No optional fields in core schema
- Immutable after creation
- Must be hashable for proof generation
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class SpineEventType(str, Enum):
    """
    Canonical event types for V1 Minimum Execution Spine.

    V1: Single event type - payment_request
    Future: Add event types as needed
    """
    PAYMENT_REQUEST = "payment_request"


class SpineEvent(BaseModel):
    """
    Canonical event schema for the Minimum Execution Spine.

    Immutable after creation. All fields are required.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: SpineEventType = Field(..., description="Type of event")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO8601 timestamp of event creation"
    )

    model_config = {"frozen": True}  # Immutable

    @field_validator("payload")
    @classmethod
    def validate_payload_not_empty(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Payload must contain data."""
        if not v:
            raise ValueError("payload cannot be empty")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, v: str) -> str:
        """Timestamp must be valid ISO8601."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"timestamp must be valid ISO8601: {e}")
        return v

    def compute_hash(self) -> str:
        """
        Compute deterministic SHA-256 hash of this event.

        Uses canonical JSON encoding (sorted keys, no whitespace).
        """
        canonical = json.dumps(
            {
                "id": str(self.id),
                "event_type": self.event_type.value,
                "payload": self.payload,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PaymentRequestPayload(BaseModel):
    """
    V1 Canonical Event Payload: Payment Request

    Minimal schema for deterministic payment decisions.
    """
    amount: float = Field(..., gt=0, description="Payment amount (must be positive)")
    currency: str = Field(default="USD", description="Currency code")
    vendor_id: str = Field(..., min_length=1, description="Vendor identifier")
    requestor_id: str = Field(..., min_length=1, description="Requestor identifier")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Currency must be uppercase 3-letter code."""
        if len(v) != 3 or not v.isupper():
            raise ValueError("currency must be 3-letter uppercase code (e.g., USD)")
        return v


def create_payment_request_event(
    amount: float,
    vendor_id: str,
    requestor_id: str,
    currency: str = "USD",
) -> SpineEvent:
    """
    Factory function to create a canonical payment request event.

    Args:
        amount: Payment amount (must be positive)
        vendor_id: Vendor identifier
        requestor_id: Requestor identifier
        currency: Currency code (default: USD)

    Returns:
        Immutable SpineEvent
    """
    # Validate payload first
    payload = PaymentRequestPayload(
        amount=amount,
        currency=currency,
        vendor_id=vendor_id,
        requestor_id=requestor_id,
    )

    return SpineEvent(
        event_type=SpineEventType.PAYMENT_REQUEST,
        payload=payload.model_dump(),
    )
