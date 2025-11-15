# api/schemas/chainboard.py
"""
ChainBoard Backend Schemas - Canonical Domain Models
====================================================

This module defines the authoritative Pydantic schemas for ChainBoard,
ensuring 100% alignment with frontend TypeScript types.

Domain Pillars:
- ChainFreight: Shipment tracking & corridor intelligence
- ChainIQ: Risk scoring & threat analysis
- ChainPay: Payment milestone tracking & rail benchmarking
- ChainSense: IoT telemetry & sensor health

Author: ChainBridge Platform Team
Version: 1.0.0 (Production-Ready)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS - Explicit Domain Vocabularies
# ============================================================================


class ShipmentStatus(str, Enum):
    """Current shipment lifecycle state"""

    PICKUP = "pickup"
    IN_TRANSIT = "in_transit"
    DELIVERY = "delivery"
    DELAYED = "delayed"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class RiskCategory(str, Enum):
    """ChainIQ risk classification bands"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PaymentState(str, Enum):
    """ChainPay payment lifecycle state"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PARTIALLY_PAID = "partially_paid"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class FreightMode(str, Enum):
    """Transportation mode"""

    OCEAN = "ocean"
    AIR = "air"
    GROUND = "ground"


class ExceptionCode(str, Enum):
    """Exception classification for triage"""

    LATE_PICKUP = "late_pickup"
    LATE_DELIVERY = "late_delivery"
    NO_UPDATE = "no_update"
    PAYMENT_BLOCKED = "payment_blocked"
    RISK_SPIKE = "risk_spike"


class ThreatLevel(str, Enum):
    """Overall network threat posture"""

    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class ProofpackStatus(str, Enum):
    """Cryptographic proof verification status"""

    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class PaymentRailId(str, Enum):
    """Payment settlement rail identifier"""

    BANK_WIRE = "bank_wire"
    ACH = "ach"
    SWIFT = "swift"
    BLOCKCHAIN = "blockchain"


class CorridorTrend(str, Enum):
    """Directional risk trend for corridor"""

    RISING = "rising"
    STABLE = "stable"
    IMPROVING = "improving"


class IoTSensorType(str, Enum):
    """Sensor hardware type"""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    DOOR = "door"
    SHOCK = "shock"
    GPS = "gps"
    CUSTOM = "custom"


class IoTSeverity(str, Enum):
    """IoT alert severity level"""

    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class MilestoneState(str, Enum):
    """Payment milestone release state"""

    PENDING = "pending"
    RELEASED = "released"
    BLOCKED = "blocked"


# ============================================================================
# CORE DOMAIN MODELS
# ============================================================================


class ShipmentEvent(BaseModel):
    """Immutable freight event from ChainFreight manifest"""

    code: str = Field(..., description="Event code (e.g., LOAD, DEPART, DELIVERY)")
    description: str = Field(..., description="Human-readable event description")
    at: datetime = Field(..., description="Event timestamp (ISO 8601)")
    location: str = Field(..., description="Event location (city, country)")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "DEPART",
                "description": "Vessel departed origin port",
                "at": "2025-11-05T12:15:00Z",
                "location": "Shanghai, CN",
            }
        }


class FreightDetail(BaseModel):
    """ChainFreight shipment transportation details"""

    mode: FreightMode = Field(..., description="Transportation mode")
    incoterm: str = Field(..., description="Incoterm (FOB, CIF, DAP, etc.)")
    vessel: Optional[str] = Field(None, description="Vessel/flight/truck identifier")
    container: Optional[str] = Field(None, description="Container/ULD identifier")
    lane: str = Field(..., description="Origin → Destination lane (e.g., 'Shanghai → Los Angeles')")
    departure: Optional[datetime] = Field(None, description="Actual/planned departure time")
    eta: Optional[datetime] = Field(None, description="Estimated time of arrival")
    events: List[ShipmentEvent] = Field(default_factory=list, description="Chronological event timeline")

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "ocean",
                "incoterm": "FOB",
                "vessel": "Maersk Horizon",
                "container": "40' HC",
                "lane": "Shanghai → Los Angeles",
                "departure": "2025-11-05T04:00:00Z",
                "eta": "2025-11-18T10:00:00Z",
                "events": [
                    {
                        "code": "LOAD",
                        "description": "Loaded at origin port",
                        "at": "2025-11-05T04:00:00Z",
                        "location": "Shanghai, CN",
                    }
                ],
            }
        }


class RiskProfile(BaseModel):
    """ChainIQ risk assessment output"""

    score: int = Field(..., ge=0, le=100, description="Risk score (0-100, higher = riskier)")
    category: RiskCategory = Field(..., description="Risk classification band")
    drivers: List[str] = Field(
        default_factory=list, description="Risk factors contributing to score (e.g., 'Port congestion')"
    )
    assessed_at: datetime = Field(..., description="Risk assessment timestamp")
    watchlisted: Optional[bool] = Field(False, description="Flagged for manual review if true")

    @field_validator("score")
    @classmethod
    def validate_risk_score(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("Risk score must be between 0 and 100")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "score": 82,
                "category": "high",
                "drivers": ["Port congestion", "Carrier capacity constraints"],
                "assessed_at": "2025-11-12T08:30:00Z",
                "watchlisted": True,
            }
        }


class PaymentMilestone(BaseModel):
    """ChainPay payment milestone with release tracking"""

    label: str = Field(..., description="Milestone name (e.g., 'Pickup', 'Delivery')")
    percentage: int = Field(..., ge=0, le=100, description="% of total payment value")
    state: MilestoneState = Field(..., description="Release state")
    released_at: Optional[datetime] = Field(None, description="Release timestamp if released")

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "label": "Pickup",
                "percentage": 20,
                "state": "released",
                "released_at": "2025-11-10T09:00:00Z",
            }
        }


class PaymentProfile(BaseModel):
    """ChainPay payment state and milestone schedule"""

    state: PaymentState = Field(..., description="Current payment state")
    total_value_usd: Decimal = Field(..., ge=0, description="Total payment value in USD")
    released_percentage: int = Field(..., ge=0, le=100, description="% of payment released so far")
    holds_usd: Decimal = Field(..., ge=0, description="Amount currently held/blocked in USD")
    milestones: List[PaymentMilestone] = Field(
        default_factory=list, description="Milestone release schedule"
    )
    updated_at: datetime = Field(..., description="Last payment state update timestamp")

    @field_validator("released_percentage")
    @classmethod
    def validate_released_percentage(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("Released percentage must be between 0 and 100")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "state": "partially_paid",
                "total_value_usd": "420000.00",
                "released_percentage": 60,
                "holds_usd": "75000.00",
                "milestones": [
                    {"label": "Pickup", "percentage": 20, "state": "released"},
                    {"label": "Delivery", "percentage": 80, "state": "blocked"},
                ],
                "updated_at": "2025-11-12T15:45:00Z",
            }
        }


class GovernanceSnapshot(BaseModel):
    """Governance and audit status"""

    proofpack_status: ProofpackStatus = Field(..., description="Cryptographic proof verification status")
    last_audit: datetime = Field(..., description="Most recent audit timestamp")
    exceptions: List[ExceptionCode] = Field(
        default_factory=list, description="Active exception codes for this shipment"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "proofpack_status": "VERIFIED",
                "last_audit": "2025-11-12T09:00:00Z",
                "exceptions": ["risk_spike", "payment_blocked"],
            }
        }


class Shipment(BaseModel):
    """
    Core shipment entity combining ChainFreight, ChainIQ, and ChainPay data.

    This is the canonical representation consumed by all ChainBoard UI components.
    """

    id: str = Field(..., description="Unique shipment identifier")
    reference: str = Field(..., description="Customer/carrier reference number")
    status: ShipmentStatus = Field(..., description="Current lifecycle status")
    origin: str = Field(..., description="Origin location (city, country)")
    destination: str = Field(..., description="Destination location (city, country)")
    carrier: str = Field(..., description="Carrier name")
    customer: str = Field(..., description="Customer/shipper name")
    freight: FreightDetail = Field(..., description="Transportation and event details")
    risk: RiskProfile = Field(..., description="ChainIQ risk assessment")
    payment: PaymentProfile = Field(..., description="ChainPay payment tracking")
    governance: GovernanceSnapshot = Field(..., description="Governance and compliance status")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "SHP-1001",
                "reference": "MAEU-123456",
                "status": "in_transit",
                "origin": "Shanghai, CN",
                "destination": "Los Angeles, US",
                "carrier": "Maersk",
                "customer": "Acme Electronics",
                "freight": {
                    "mode": "ocean",
                    "incoterm": "FOB",
                    "vessel": "Maersk Horizon",
                    "container": "40' HC",
                    "lane": "Shanghai → Los Angeles",
                    "departure": "2025-11-05T04:00:00Z",
                    "eta": "2025-11-18T10:00:00Z",
                    "events": [],
                },
                "risk": {
                    "score": 82,
                    "category": "high",
                    "drivers": ["Port congestion"],
                    "assessed_at": "2025-11-12T08:30:00Z",
                    "watchlisted": True,
                },
                "payment": {
                    "state": "partially_paid",
                    "total_value_usd": "420000.00",
                    "released_percentage": 60,
                    "holds_usd": "75000.00",
                    "milestones": [],
                    "updated_at": "2025-11-12T15:45:00Z",
                },
                "governance": {
                    "proofpack_status": "VERIFIED",
                    "last_audit": "2025-11-12T09:00:00Z",
                    "exceptions": ["risk_spike"],
                },
            }
        }


# ============================================================================
# IOT TELEMETRY MODELS
# ============================================================================


class IoTSensorReading(BaseModel):
    """Individual sensor reading from ChainSense"""

    sensor_type: IoTSensorType = Field(..., description="Sensor hardware type")
    value: float | str = Field(..., description="Reading value (numeric or string depending on sensor)")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'C', '%', 'G')")
    timestamp: datetime = Field(..., description="Reading timestamp")
    status: IoTSeverity = Field(..., description="Alert severity level")

    class Config:
        json_schema_extra = {
            "example": {
                "sensor_type": "temperature",
                "value": 18.5,
                "unit": "C",
                "timestamp": "2025-11-12T14:30:00Z",
                "status": "info",
            }
        }


class ShipmentIoTSnapshot(BaseModel):
    """IoT telemetry snapshot for a single shipment"""

    shipment_id: str = Field(..., description="Shipment identifier")
    latest_readings: List[IoTSensorReading] = Field(
        default_factory=list, description="Most recent reading per sensor type"
    )
    alert_count_24h: int = Field(..., ge=0, description="Total alerts in last 24 hours")
    critical_alerts_24h: int = Field(..., ge=0, description="Critical alerts in last 24 hours")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-1001",
                "latest_readings": [
                    {
                        "sensor_type": "temperature",
                        "value": 18.5,
                        "unit": "C",
                        "timestamp": "2025-11-12T14:30:00Z",
                        "status": "info",
                    }
                ],
                "alert_count_24h": 3,
                "critical_alerts_24h": 1,
            }
        }


class IoTHealthSummary(BaseModel):
    """Network-wide IoT health metrics"""

    shipments_with_iot: int = Field(..., ge=0, description="Number of shipments with active sensors")
    active_sensors: int = Field(..., ge=0, description="Total active sensors across fleet")
    alerts_last_24h: int = Field(..., ge=0, description="Total alerts in last 24 hours")
    critical_alerts_last_24h: int = Field(..., ge=0, description="Critical alerts in last 24 hours")
    coverage_percent: float = Field(..., ge=0, le=100, description="% of shipments with IoT coverage")

    @field_validator("coverage_percent")
    @classmethod
    def validate_coverage(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("Coverage percent must be between 0 and 100")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "shipments_with_iot": 58,
                "active_sensors": 247,
                "alerts_last_24h": 6,
                "critical_alerts_last_24h": 1,
                "coverage_percent": 72.5,
            }
        }


# ============================================================================
# PAYMENT RAIL BENCHMARKING MODELS
# ============================================================================


class PaymentRailMetrics(BaseModel):
    """Benchmark metrics for a payment settlement rail"""

    id: PaymentRailId = Field(..., description="Rail identifier")
    label: str = Field(..., description="Display name")
    description: str = Field(..., description="Rail description")
    avg_settlement_hours: float = Field(..., ge=0, description="Average settlement time in hours")
    avg_fee_usd: Decimal = Field(..., ge=0, description="Average fee per transaction in USD")
    avg_fx_spread_bps: int = Field(..., ge=0, description="Average FX spread in basis points")
    fail_rate_bps: int = Field(..., ge=0, description="Failure/return rate in basis points")
    capital_locked_hours: float = Field(..., ge=0, description="Average hours capital is locked in transit")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "swift",
                "label": "SWIFT MT103",
                "description": "Cross-border correspondent banking via MT103",
                "avg_settlement_hours": 48.0,
                "avg_fee_usd": "35.00",
                "avg_fx_spread_bps": 22,
                "fail_rate_bps": 60,
                "capital_locked_hours": 60.0,
            }
        }


# ============================================================================
# DASHBOARD METRICS & AGGREGATIONS
# ============================================================================


class ShipmentSummary(BaseModel):
    """Shipment KPI aggregates for dashboard"""

    total_shipments: int = Field(..., ge=0, description="Total shipments in watch window")
    active_shipments: int = Field(..., ge=0, description="Non-completed shipments")
    on_time_percent: int = Field(..., ge=0, le=100, description="On-time percentage (0-100)")
    exception_count: int = Field(..., ge=0, description="Shipments with active exceptions")
    high_risk_count: int = Field(..., ge=0, description="Shipments with high ChainIQ risk")
    delayed_or_blocked_count: int = Field(..., ge=0, description="Shipments in delayed/blocked status")

    class Config:
        json_schema_extra = {
            "example": {
                "total_shipments": 148,
                "active_shipments": 92,
                "on_time_percent": 81,
                "exception_count": 7,
                "high_risk_count": 5,
                "delayed_or_blocked_count": 4,
            }
        }


class PaymentSummary(BaseModel):
    """Payment health aggregates for dashboard"""

    blocked_payments: int = Field(..., ge=0, description="Payments currently blocked")
    partially_paid: int = Field(..., ge=0, description="Payments partially released")
    completed: int = Field(..., ge=0, description="Fully completed payments")
    not_started: int = Field(..., ge=0, description="Payments not yet started")
    in_progress: int = Field(..., ge=0, description="Payments in progress")
    payment_health_score: int = Field(
        ..., ge=0, le=100, description="Overall payment health score (0-100)"
    )
    capital_locked_hours: float = Field(
        ..., ge=0, description="Estimated hours of capital stuck in limbo"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "blocked_payments": 3,
                "partially_paid": 14,
                "completed": 86,
                "not_started": 12,
                "in_progress": 33,
                "payment_health_score": 78,
                "capital_locked_hours": 420.0,
            }
        }


class GovernanceSummary(BaseModel):
    """Governance and compliance aggregates for dashboard"""

    proofpack_ok_percent: float = Field(
        ..., ge=0, le=100, description="% of shipments with verified proofpacks"
    )
    open_audits: int = Field(..., ge=0, description="Active audits/investigations")
    watchlisted_shipments: int = Field(..., ge=0, description="Shipments on governance watchlist")

    class Config:
        json_schema_extra = {
            "example": {
                "proofpack_ok_percent": 92.0,
                "open_audits": 3,
                "watchlisted_shipments": 5,
            }
        }


class CorridorMetrics(BaseModel):
    """Corridor-level intelligence metrics"""

    corridor_id: str = Field(..., description="Corridor identifier (e.g., 'asia-us-west')")
    label: str = Field(..., description="Display name (e.g., 'Asia → US West')")
    shipment_count: int = Field(..., ge=0, description="Total shipments in corridor")
    active_count: int = Field(..., ge=0, description="Active shipments in corridor")
    high_risk_count: int = Field(..., ge=0, description="High-risk shipments")
    blocked_payments: int = Field(..., ge=0, description="Blocked payments in corridor")
    avg_risk_score: int = Field(..., ge=0, le=100, description="Average risk score (0-100)")
    trend: CorridorTrend = Field(..., description="Directional risk trend")

    class Config:
        json_schema_extra = {
            "example": {
                "corridor_id": "asia-us-west",
                "label": "Asia → US West",
                "shipment_count": 42,
                "active_count": 28,
                "high_risk_count": 3,
                "blocked_payments": 1,
                "avg_risk_score": 63,
                "trend": "rising",
            }
        }


class GlobalSummary(BaseModel):
    """
    Top-level dashboard summary combining all domain metrics.

    This is the primary API response for the Overview page.
    """

    threat_level: ThreatLevel = Field(..., description="Overall network threat posture")
    shipments: ShipmentSummary = Field(..., description="Shipment KPIs")
    payments: PaymentSummary = Field(..., description="Payment health metrics")
    governance: GovernanceSummary = Field(..., description="Governance and compliance metrics")
    top_corridor: Optional[CorridorMetrics] = Field(None, description="Highest-priority corridor")
    iot: Optional[IoTHealthSummary] = Field(None, description="IoT health summary (if available)")

    class Config:
        json_schema_extra = {
            "example": {
                "threat_level": "elevated",
                "shipments": {
                    "total_shipments": 148,
                    "active_shipments": 92,
                    "on_time_percent": 81,
                    "exception_count": 7,
                    "high_risk_count": 5,
                    "delayed_or_blocked_count": 4,
                },
                "payments": {
                    "blocked_payments": 3,
                    "partially_paid": 14,
                    "completed": 86,
                    "not_started": 12,
                    "in_progress": 33,
                    "payment_health_score": 78,
                    "capital_locked_hours": 420.0,
                },
                "governance": {
                    "proofpack_ok_percent": 92.0,
                    "open_audits": 3,
                    "watchlisted_shipments": 5,
                },
                "top_corridor": {
                    "corridor_id": "asia-us-west",
                    "label": "Asia → US West",
                    "shipment_count": 42,
                    "active_count": 28,
                    "high_risk_count": 3,
                    "blocked_payments": 1,
                    "avg_risk_score": 63,
                    "trend": "rising",
                },
                "iot": {
                    "shipments_with_iot": 58,
                    "active_sensors": 247,
                    "alerts_last_24h": 6,
                    "critical_alerts_last_24h": 1,
                    "coverage_percent": 72.5,
                },
            }
        }


# ============================================================================
# EXCEPTION MODELS
# ============================================================================


class ExceptionRow(BaseModel):
    """Simplified shipment view for exception reporting"""

    shipment_id: str = Field(..., description="Shipment identifier")
    lane: str = Field(..., description="Origin → Destination lane")
    current_status: ShipmentStatus = Field(..., description="Current shipment status")
    risk_score: int = Field(..., ge=0, le=100, description="ChainIQ risk score")
    payment_state: PaymentState = Field(..., description="ChainPay payment state")
    age_of_issue: str = Field(..., description="Human-readable age (e.g., '3h', '2d')")
    issue_types: List[ExceptionCode] = Field(
        default_factory=list, description="Active exception codes"
    )
    last_update: str = Field(..., description="Last update timestamp (formatted)")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-1001",
                "lane": "Shanghai → Los Angeles",
                "current_status": "delayed",
                "risk_score": 82,
                "payment_state": "blocked",
                "age_of_issue": "3h",
                "issue_types": ["risk_spike", "payment_blocked"],
                "last_update": "2025-11-12 15:45:00",
            }
        }


# ============================================================================
# API RESPONSE ENVELOPES
# ============================================================================


class ShipmentsResponse(BaseModel):
    """Response envelope for GET /shipments"""

    shipments: List[Shipment] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total matching shipments (for pagination)")
    filtered: bool = Field(False, description="True if filters were applied")

    class Config:
        json_schema_extra = {
            "example": {"shipments": [], "total": 148, "filtered": False}
        }


class ExceptionsResponse(BaseModel):
    """Response envelope for GET /exceptions"""

    exceptions: List[ExceptionRow] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total exceptions")
    critical_count: int = Field(..., ge=0, description="High-priority exceptions")

    class Config:
        json_schema_extra = {
            "example": {"exceptions": [], "total": 7, "critical_count": 3}
        }


class GlobalSummaryResponse(BaseModel):
    """Response envelope for GET /metrics/summary"""

    summary: GlobalSummary
    generated_at: datetime = Field(..., description="Summary generation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "summary": {
                    "threat_level": "elevated",
                    "shipments": {"total_shipments": 148},
                    "payments": {"blocked_payments": 3},
                    "governance": {"proofpack_ok_percent": 92.0},
                    "top_corridor": None,
                    "iot": None,
                },
                "generated_at": "2025-11-15T10:30:00Z",
            }
        }


class CorridorMetricsResponse(BaseModel):
    """Response envelope for GET /metrics/corridors"""

    corridors: List[CorridorMetrics] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total corridors")

    class Config:
        json_schema_extra = {
            "example": {"corridors": [], "total": 4}
        }


class IoTHealthSummaryResponse(BaseModel):
    """Response envelope for GET /metrics/iot/summary"""

    iot_health: IoTHealthSummary
    generated_at: datetime = Field(..., description="Metrics generation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "iot_health": {
                    "shipments_with_iot": 58,
                    "active_sensors": 247,
                    "alerts_last_24h": 6,
                    "critical_alerts_last_24h": 1,
                    "coverage_percent": 72.5,
                },
                "generated_at": "2025-11-15T10:30:00Z",
            }
        }


class ShipmentIoTSnapshotResponse(BaseModel):
    """Response envelope for GET /metrics/iot/shipments/{shipment_id}"""

    snapshot: ShipmentIoTSnapshot
    retrieved_at: datetime = Field(..., description="Snapshot retrieval timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "snapshot": {
                    "shipment_id": "SHP-1001",
                    "latest_readings": [],
                    "alert_count_24h": 3,
                    "critical_alerts_24h": 1,
                },
                "retrieved_at": "2025-11-15T10:30:00Z",
            }
        }
