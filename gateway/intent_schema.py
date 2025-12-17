"""Pydantic schemas for gateway intents (deterministic, non-AI)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class IntentType(str, Enum):
    """Supported intent types for the gateway input."""

    PAYMENT = "payment"
    SHIPMENT = "shipment"
    RISK = "risk"
    CONTROL = "control"


class IntentChannel(str, Enum):
    """Channel the intent originated from."""

    API = "api"
    DASHBOARD = "dashboard"
    BATCH = "batch"


class IntentAction(str, Enum):
    """Action requested by the intent."""

    CREATE = "create"
    UPDATE = "update"
    CANCEL = "cancel"
    QUERY = "query"


class IntentState(str, Enum):
    """Deterministic state machine for intents."""

    RECEIVED = "received"
    VALIDATED = "validated"
    DECIDED = "decided"


class IntentPayload(BaseModel):
    """Structured payload accepted by the gateway (no free-form blobs)."""

    model_config = ConfigDict(extra="forbid")

    resource_id: Optional[str] = Field(None, description="Target resource identifier if applicable")
    amount_minor: Optional[int] = Field(None, ge=0, description="Minor units amount for payment-related intents")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="ISO currency code")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Deterministic key/value metadata")


class GatewayIntent(BaseModel):
    """Gateway input schema (Intent). Rejects free-form input and enforces deterministic fields."""

    model_config = ConfigDict(extra="forbid")

    intent_type: IntentType = Field(..., description="Type of intent (required)")
    action: IntentAction = Field(..., description="Requested action")
    channel: IntentChannel = Field(..., description="Originating channel")
    state: IntentState = Field(default=IntentState.RECEIVED, description="Current intent lifecycle state")
    payload: IntentPayload = Field(..., description="Structured payload; free-form input is forbidden")
    correlation_id: str = Field(..., min_length=1, max_length=128, description="Idempotency/correlation key")
