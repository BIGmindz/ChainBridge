"""Canonical identifier aliases and enums shared across backend services."""

from __future__ import annotations

from enum import Enum
from typing import NewType

ShipmentID = NewType("ShipmentID", str)
ShipmentLegID = NewType("ShipmentLegID", str)
CarrierID = NewType("CarrierID", str)
ShipperID = NewType("ShipperID", str)
FacilityID = NewType("FacilityID", str)
CorridorID = NewType("CorridorID", str)
EventID = NewType("EventID", str)
ProofID = NewType("ProofID", str)
PaymentID = NewType("PaymentID", str)
ScoreSnapshotID = NewType("ScoreSnapshotID", str)


class TransportMode(str, Enum):
    """Canonical transport modes across ChainBridge services."""

    TRUCK_FTL = "TRUCK_FTL"
    TRUCK_LTL = "TRUCK_LTL"
    OCEAN = "OCEAN"
    AIR = "AIR"
    RAIL = "RAIL"
    INTERMODAL = "INTERMODAL"


class ShipmentStatus(str, Enum):
    """Lifecycle states for multimodal shipments."""

    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    AT_FACILITY = "AT_FACILITY"
    DELAYED = "DELAYED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    EXCEPTION = "EXCEPTION"


class RiskLevel(str, Enum):
    """Risk severity bands shared across ChainIQ and downstream consumers."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def normalize(cls, value: str) -> "RiskLevel":
        """Normalize legacy values (e.g., MODERATE) into canonical enums."""
        candidate = (value or "").strip().upper()
        if candidate == "MODERATE":
            candidate = cls.MEDIUM.value
        try:
            return cls(candidate)
        except ValueError as exc:
            raise ValueError(f"Unsupported risk level '{value}'") from exc


class ShipmentEventType(str, Enum):
    """Shipment event lifecycle types recorded in the platform spine."""

    RISK_DECIDED = "RISK_DECIDED"
    SNAPSHOT_REQUESTED = "SNAPSHOT_REQUESTED"
    SNAPSHOT_CLAIMED = "SNAPSHOT_CLAIMED"
    SNAPSHOT_COMPLETED = "SNAPSHOT_COMPLETED"
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
