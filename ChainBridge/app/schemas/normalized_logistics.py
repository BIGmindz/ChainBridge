"""Normalized logistics schema (Golden Record) for ingested shipments."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Asset(BaseModel):
    """Standardized representation of a shipped asset/line item."""

    sku: Optional[str] = Field(None, description="Merchant SKU or product code")
    description: Optional[str] = Field(None, description="Human readable description")
    quantity: float = Field(..., description="Quantity shipped")
    unit: str = Field("EA", description="Unit of measure")
    value: Optional[float] = Field(None, description="Optional declared value")


class TemperatureTolerance(BaseModel):
    """Environmental tolerances for the shipment plan."""

    max_celsius: Optional[float] = Field(None, description="Maximum allowable temperature in Celsius")
    min_celsius: Optional[float] = Field(None, description="Minimum allowable temperature in Celsius")


class StandardShipment(BaseModel):
    """
    Golden Record representation of a shipment across ingestion sources.
    """

    source_system: str = Field(..., description="Originating system for the payload")
    external_id: str = Field(..., description="External control number or reference")
    shipment_id: str = Field(..., description="Internal shipment identifier")
    assets: List[Asset] = Field(default_factory=list)
    raw_data_hash: str = Field(..., description="SHA-256 hash of the original payload")
    expected_arrival: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tolerances: Optional[TemperatureTolerance] = None

    @field_validator("raw_data_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("raw_data_hash must be a SHA-256 hex digest")
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValueError("raw_data_hash must be a SHA-256 hex digest") from exc
        return value

    @staticmethod
    def compute_hash(payload: Any) -> str:
        """
        Deterministically hash the inbound payload (dict or raw string) for lineage.
        """
        if isinstance(payload, (dict, list)):
            materialized = json.dumps(payload, sort_keys=True, default=str)
        else:
            materialized = str(payload)
        return hashlib.sha256(materialized.encode("utf-8")).hexdigest()
