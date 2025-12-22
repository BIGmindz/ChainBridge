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
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.payments.identity import is_valid_milestone_id


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


class AlertSeverity(str, Enum):
    """Control Tower alert severity level"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertSource(str, Enum):
    """Alert origination source"""

    RISK = "risk"
    IOT = "iot"
    PAYMENT = "payment"
    CUSTOMS = "customs"


class AlertStatus(str, Enum):
    """Alert lifecycle status"""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertActionType(str, Enum):
    """Alert action types for triage workflow"""

    ASSIGN = "assign"
    ACKNOWLEDGE = "acknowledge"
    RESOLVE = "resolve"
    COMMENT = "comment"
    ESCALATE = "escalate"
    HOLD_PAYMENT = "hold_payment"
    RELEASE_PAYMENT = "release_payment"
    CUSTOMS_EXPEDITE = "customs_expedite"


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


class SettlementState(str, Enum):
    """Settlement lifecycle derived from ChainPay transactions."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PARTIALLY_PAID = "partially_paid"
    BLOCKED = "blocked"
    COMPLETED = "completed"


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

    milestone_id: str = Field(..., description="Canonical milestone identifier '<shipment_reference>-M<index>'")
    label: str = Field(..., description="Milestone name (e.g., 'Pickup', 'Delivery')")
    percentage: int = Field(..., ge=0, le=100, description="% of total payment value")
    state: MilestoneState = Field(..., description="Release state")
    released_at: Optional[datetime] = Field(None, description="Release timestamp if released")
    freight_token_id: Optional[int] = Field(None, description="Freight token correlation identifier")

    @field_validator("milestone_id")
    @classmethod
    def validate_milestone_id(cls, value: str) -> str:
        if not is_valid_milestone_id(value):
            raise ValueError(
                "milestone_id must match '<shipment_reference>-M<index>' "
                "(e.g., 'SHP-2025-042-M1')"
            )
        return value

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "milestone_id": "SHP-1001-M1",
                "label": "Pickup",
                "percentage": 20,
                "state": "released",
                "released_at": "2025-11-10T09:00:00Z",
                "freight_token_id": 1001,
            }
        }


class PaymentProfile(BaseModel):
    """ChainPay payment state and milestone schedule"""

    state: PaymentState = Field(..., description="Current payment state")
    total_value_usd: Decimal = Field(..., ge=0, description="Total payment value in USD")
    released_usd: Decimal = Field(..., ge=0, description="Amount released to date in USD")
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
                "released_usd": "252000.00",
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
    corridor: str = Field(..., description="Canonical corridor label (e.g., 'Shanghai → Los Angeles')")
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
                "corridor": "Shanghai → Los Angeles",
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
                    "released_usd": "252000.00",
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
    value: Union[float, str] = Field(
        ..., description="Reading value (numeric or string depending on sensor)"
    )
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


class RiskFactor(str, Enum):
    """ChainIQ risk factor classification - why a shipment is risky"""

    ROUTE_VOLATILITY = "route_volatility"
    CARRIER_HISTORY = "carrier_history"
    DOCUMENT_ISSUES = "document_issues"
    IOT_ANOMALIES = "iot_anomalies"
    PAYMENT_BEHAVIOR = "payment_behavior"


class RiskOverview(BaseModel):
    """Aggregated ChainIQ risk snapshot backing the overview tile."""

    total_shipments: int = Field(..., ge=0, description="Shipments evaluated in the risk window")
    high_risk_shipments: int = Field(..., ge=0, description="Shipments in high risk category")
    total_value_usd: Decimal = Field(..., ge=0, description="Aggregate shipment value at risk (USD)")
    average_risk_score: float = Field(..., ge=0, le=100, description="Average ChainIQ risk score")
    updated_at: datetime = Field(..., description="Timestamp of the most recent assessment")

    class Config:
        json_schema_extra = {
            "example": {
                "total_shipments": 48,
                "high_risk_shipments": 6,
                "total_value_usd": "1290000.00",
                "average_risk_score": 57.4,
                "updated_at": "2025-11-12T16:00:00Z",
            }
        }


class RiskStory(BaseModel):
    """ChainIQ narrative explanation of why a shipment is risky - human-readable intelligence"""

    shipment_id: str = Field(..., description="Unique shipment identifier")
    reference: str = Field(..., description="Human-readable shipment reference")
    corridor: str = Field(..., description="Trade corridor (e.g., 'Asia → US West')")
    risk_category: RiskCategory = Field(..., description="Risk classification band")
    score: int = Field(..., ge=0, le=100, description="ChainIQ risk score (0-100)")
    primary_factor: RiskFactor = Field(..., description="Primary driver of risk")
    factors: List[RiskFactor] = Field(..., description="All contributing risk factors")
    summary: str = Field(..., description="1-2 sentence narrative explanation")
    recommended_action: str = Field(..., description="Suggested operator action")
    last_updated: datetime = Field(..., description="Story generation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-89234",
                "reference": "MAEU-4567890",
                "corridor": "Asia → US West",
                "risk_category": "high",
                "score": 82,
                "primary_factor": "route_volatility",
                "factors": ["route_volatility", "payment_behavior"],
                "summary": "Route through congested Pacific corridor with 3-day delay history. Customer has 2 overdue invoices totaling $45K.",
                "recommended_action": "Escalate to operations and request prepayment for next milestone",
                "last_updated": "2025-11-16T14:23:00Z",
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


class RiskOverviewResponse(BaseModel):
    """Response envelope for GET /risk/overview"""

    overview: RiskOverview
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


class RiskStoryResponse(BaseModel):
    """Response envelope for GET /iq/risk-stories"""

    stories: List[RiskStory] = Field(default_factory=list, description="Risk narratives")
    total: int = Field(..., ge=0, description="Total stories available")
    generated_at: datetime = Field(..., description="Response generation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "stories": [
                    {
                        "shipment_id": "SHP-89234",
                        "reference": "MAEU-4567890",
                        "corridor": "Asia → US West",
                        "risk_category": "high",
                        "score": 82,
                        "primary_factor": "route_volatility",
                        "factors": ["route_volatility", "payment_behavior"],
                        "summary": "Route through congested Pacific corridor with 3-day delay history.",
                        "recommended_action": "Escalate to operations",
                        "last_updated": "2025-11-16T14:23:00Z",
                    }
                ],
                "total": 1,
                "generated_at": "2025-11-16T14:23:00Z",
            }
        }


class PaymentQueueItem(BaseModel):
    """ChainPay payment hold queue item"""

    shipment_id: str = Field(..., description="Shipment identifier")
    reference: str = Field(..., description="Customer shipment reference")
    corridor: str = Field(..., description="Trade lane")
    customer: str = Field(..., description="Customer name")
    total_value_usd: Decimal = Field(..., ge=0, description="Total shipment value")
    holds_usd: Decimal = Field(..., ge=0, description="Payment amount on hold")
    released_usd: Decimal = Field(..., ge=0, description="Payment amount already released")
    aging_days: int = Field(..., ge=0, description="Days since shipment assessment")
    risk_category: Optional[RiskCategory] = Field(None, description="Risk level if applicable")
    milestone_id: str = Field(..., description="Canonical milestone identifier '<shipment_reference>-M<index>'")
    freight_token_id: Optional[int] = Field(None, description="Freight token correlation identifier")

    @field_validator("milestone_id")
    @classmethod
    def validate_milestone_id(cls, value: str) -> str:
        if not is_valid_milestone_id(value):
            raise ValueError(
                "milestone_id must match '<shipment_reference>-M<index>' "
                "(e.g., 'SHP-2025-042-M1')"
            )
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-1001",
                "reference": "MAEU-123456",
                "corridor": "Shanghai → Los Angeles",
                "customer": "Acme Electronics",
                "total_value_usd": "420000.00",
                "holds_usd": "75000.00",
                "released_usd": "252000.00",
                "aging_days": 10,
                "risk_category": "high",
                "milestone_id": "SHP-1001-M3",
                "freight_token_id": 1001,
            }
        }


class PaymentQueueResponse(BaseModel):
    """Response envelope for GET /pay/queue"""

    items: List[PaymentQueueItem] = Field(default_factory=list)
    total_items: int = Field(..., ge=0, description="Total queue items")
    total_holds_usd: Decimal = Field(..., ge=0, description="Total value of all holds")
    generated_at: datetime = Field(..., description="Queue snapshot timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total_items": 5,
                "total_holds_usd": "185000.00",
                "generated_at": "2025-11-15T10:30:00Z",
        }
    }


# ============================================================================
# Live positions and geo overlays
# ============================================================================


class LiveShipmentPosition(BaseModel):
    shipment_id: str
    corridor: str
    mode: str
    lat: float
    lon: float
    progress_pct: float
    eta: str
    cargo_value_usd: float
    financed_amount_usd: float
    paid_amount_usd: float
    settlement_state: SettlementState
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    nearest_port: Optional[str] = None
    distance_to_nearest_port_km: Optional[float] = None


class LivePositionsResponse(BaseModel):
    positions: List[LiveShipmentPosition]
    generated_at: datetime


class ProofPack(BaseModel):
    """Structured ProofPack payload for settlement verification."""

    milestone_id: str = Field(..., description="Canonical milestone identifier '<shipment_reference>-M<index>'")
    shipment_reference: str = Field(..., description="Shipment reference used by canonical IDs")
    corridor: str = Field(..., description="Shipment corridor (Origin → Destination)")
    customer_name: str = Field(..., description="Customer or shipper name")
    amount: float = Field(..., ge=0, description="Milestone value in currency units")
    currency: str = Field(..., description="ISO 4217 currency code")
    state: str = Field(..., description="Milestone state (blocked/released/settled/etc.)")
    freight_token_id: Optional[int] = Field(None, description="Associated freight token ID if available")
    last_updated: datetime = Field(..., description="When this ProofPack was last updated")
    documents: List[Dict[str, Any]] = Field(default_factory=list, description="Document evidence (placeholder-friendly)")
    iot_signals: List[Dict[str, Any]] = Field(default_factory=list, description="IoT signal evidence (placeholder-friendly)")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="Risk assessment metadata (must note source)")
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list, description="Audit log entries for milestone lifecycle")

    class Config:
        json_schema_extra = {
            "example": {
                "milestone_id": "SHP-2025-042-M2",
                "shipment_reference": "SHP-2025-042",
                "corridor": "Shanghai → Los Angeles",
                "customer_name": "Acme Electronics",
                "amount": 70000.0,
                "currency": "USD",
                "state": "released",
                "freight_token_id": 2025042,
                "last_updated": "2025-11-18T10:00:00Z",
                "documents": [{"type": "POD", "id": "pod-123", "status": "placeholder"}],
                "iot_signals": [{"sensor": "temperature", "value": "22.5C", "source": "mock"}],
                "risk_assessment": {
                    "source": "mock",
                    "score": 82,
                    "category": "high",
                    "notes": "Placeholder until ChainIQ linkage is wired",
                },
                "audit_trail": [{"event": "milestone_created", "actor": "system", "timestamp": "2025-11-18T10:00:00Z"}],
            }
        }


class ShipmentEventType(str, Enum):
    """Timeline event types for shipment lifecycle"""

    CREATED = "created"
    BOOKED = "booked"
    PICKED_UP = "picked_up"
    DEPARTED_PORT = "departed_port"
    ARRIVED_PORT = "arrived_port"
    CUSTOMS_HOLD = "customs_hold"
    CUSTOMS_RELEASED = "customs_released"
    DELIVERED = "delivered"
    PAYMENT_RELEASE = "payment_release"
    IOT_ALERT = "iot_alert"


class TimelineEvent(BaseModel):
    """Timeline event for shipment tracking - aggregates events from all systems"""

    shipment_id: str = Field(..., description="Shipment identifier")
    reference: str = Field(..., description="Shipment reference number")
    corridor: str = Field(..., description="Trade corridor")
    event_type: ShipmentEventType = Field(..., description="Event classification")
    description: str = Field(..., description="Human-readable event description")
    occurred_at: datetime = Field(..., description="Event timestamp")
    source: str = Field(..., description="Event source system (TMS, IoT, Finance, etc.)")
    severity: Optional[str] = Field(None, description="Event severity: info, warning, critical")

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-1001",
                "reference": "MAEU-123456",
                "corridor": "Shanghai → Los Angeles",
                "event_type": "picked_up",
                "description": "Container picked up at origin warehouse",
                "occurred_at": "2025-11-15T08:30:00Z",
                "source": "TMS",
                "severity": "info",
            }
        }


class TimelineEventResponse(BaseModel):
    """Response envelope for event endpoints"""

    events: List[TimelineEvent] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total matching events")
    generated_at: datetime = Field(..., description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [],
                "total": 12,
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


class ShipmentIoTSnapshotsResponse(BaseModel):
    """Response envelope for GET /metrics/iot/shipments"""

    snapshots: List[ShipmentIoTSnapshot] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Snapshots returned after filtering")
    available: int = Field(..., ge=0, description="Total snapshots available")
    filtered: bool = Field(False, description="True if filters changed the result set")
    generated_at: datetime = Field(..., description="Timestamp of snapshot aggregation")

    class Config:
        json_schema_extra = {
            "example": {
                "snapshots": [],
                "total": 3,
                "available": 3,
                "filtered": False,
                "generated_at": "2025-11-15T10:30:00Z",
            }
        }


# ============================================================================
# ALERT & TRIAGE MODELS
# ============================================================================


class ControlTowerAlert(BaseModel):
    """Unified alert model across risk, IoT, payment, and customs domains"""

    id: str = Field(..., description="Unique alert identifier (UUID)")
    shipment_reference: str = Field(..., description="Associated shipment ID")
    title: str = Field(..., description="Alert headline")
    description: str = Field(..., description="Detailed alert context")
    source: AlertSource = Field(..., description="Alert origination source")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    status: AlertStatus = Field(..., description="Current triage status")
    created_at: datetime = Field(..., description="Alert creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tags: List[str] = Field(default_factory=list, description="Alert classification tags")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "alert-550e8400-e29b-41d4-a716-446655440000",
                "shipment_reference": "SHP-2025-027",
                "title": "High risk corridor: Shanghai → Los Angeles",
                "description": "Shipment operating in elevated-risk corridor with recent sanctions activity detected",
                "source": "risk",
                "severity": "critical",
                "status": "open",
                "created_at": "2025-11-16T08:15:00Z",
                "updated_at": "2025-11-16T08:15:00Z",
                "tags": ["risk", "sanctions", "corridor_alert"],
            }
        }


class AlertsResponse(BaseModel):
    """Response envelope for GET /alerts"""

    alerts: List[ControlTowerAlert] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total matching alerts")
    generated_at: datetime = Field(..., description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "alerts": [],
                "total": 8,
                "generated_at": "2025-11-16T10:30:00Z",
            }
        }


class AlertDetailResponse(BaseModel):
    """Response envelope for GET /alerts/{alert_id}"""

    alert: ControlTowerAlert

    class Config:
        json_schema_extra = {
            "example": {
                "alert": {
                    "id": "alert-550e8400-e29b-41d4-a716-446655440000",
                    "shipment_reference": "SHP-2025-027",
                    "title": "High risk corridor",
                    "description": "Elevated-risk corridor detected",
                    "source": "risk",
                    "severity": "critical",
                    "status": "open",
                    "created_at": "2025-11-16T08:15:00Z",
                    "updated_at": "2025-11-16T08:15:00Z",
                    "tags": ["risk"],
                }
            }
        }


# ============================================================================
# ALERT TRIAGE MODELS - Work Queue & Operator Playbooks
# ============================================================================


class AlertOwner(BaseModel):
    """Alert ownership and assignment tracking"""

    id: str = Field(..., description="Owner/operator unique ID")
    name: str = Field(..., description="Owner display name")
    email: Optional[str] = Field(None, description="Owner email address")
    team: Optional[str] = Field(None, description="Owner team/department")


class AlertNote(BaseModel):
    """Alert triage note for operator collaboration"""

    id: str = Field(..., description="Note unique ID (UUID)")
    alert_id: str = Field(..., description="Parent alert ID")
    author: AlertOwner = Field(..., description="Note author")
    message: str = Field(..., description="Note content")
    created_at: datetime = Field(..., description="Note creation timestamp")


class AlertActionRecord(BaseModel):
    """Alert action audit trail for triage workflow"""

    id: str = Field(..., description="Action record unique ID (UUID)")
    alert_id: str = Field(..., description="Parent alert ID")
    type: AlertActionType = Field(..., description="Action type")
    actor: AlertOwner = Field(..., description="Action performer")
    payload: dict = Field(default_factory=dict, description="Action-specific metadata")
    created_at: datetime = Field(..., description="Action timestamp")


class AlertWorkItem(BaseModel):
    """Work queue item: alert + triage context (owner, notes, actions)"""

    alert: ControlTowerAlert = Field(..., description="Base alert")
    owner: Optional[AlertOwner] = Field(None, description="Assigned owner (null = unassigned)")
    notes: List[AlertNote] = Field(default_factory=list, description="Triage notes")
    actions: List[AlertActionRecord] = Field(default_factory=list, description="Action history")


class AlertWorkQueueResponse(BaseModel):
    """Response envelope for GET /alerts/work-queue"""

    items: List[AlertWorkItem] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total matching items")


class UpdateAlertAssignmentRequest(BaseModel):
    """Request body for POST /alerts/{alert_id}/assign"""

    owner_id: Optional[str] = Field(None, description="Owner ID (null to unassign)")
    owner_name: Optional[str] = Field(None, description="Owner name")
    owner_email: Optional[str] = Field(None, description="Owner email")
    owner_team: Optional[str] = Field(None, description="Owner team")


class AddAlertNoteRequest(BaseModel):
    """Request body for POST /alerts/{alert_id}/notes"""

    message: str = Field(..., description="Note content")
    author_id: str = Field(..., description="Author ID")
    author_name: str = Field(..., description="Author name")
    author_email: Optional[str] = Field(None, description="Author email")
    author_team: Optional[str] = Field(None, description="Author team")


class UpdateAlertStatusRequest(BaseModel):
    """Request body for POST /alerts/{alert_id}/status"""

    status: AlertStatus = Field(..., description="New alert status")
    actor_id: str = Field(..., description="Actor ID")
    actor_name: str = Field(..., description="Actor name")
    actor_email: Optional[str] = Field(None, description="Actor email")
    actor_team: Optional[str] = Field(None, description="Actor team")


# ============================================================================
# REAL-TIME EVENTS - Server-Sent Events (SSE) Support
# ============================================================================


class ControlTowerEventType(str, Enum):
    """Real-time event types for SSE streaming"""

    ALERT_CREATED = "alert_created"
    ALERT_UPDATED = "alert_updated"
    ALERT_STATUS_CHANGED = "alert_status_changed"
    ALERT_NOTE_ADDED = "alert_note_added"
    IOT_READING = "iot_reading"
    SHIPMENT_EVENT = "shipment_event"
    PAYMENT_STATE_CHANGED = "payment_state_changed"


class ControlTowerEvent(BaseModel):
    """Generic event wrapper for real-time event bus"""

    id: str = Field(..., description="Unique event ID")
    type: ControlTowerEventType = Field(..., description="Event type")
    timestamp: datetime = Field(..., description="When the event occurred")
    source: str = Field(..., description="Subsystem emitting the event (e.g. 'alerts', 'iot', 'payments')")
    key: str = Field(..., description="Primary entity key (e.g. shipment ID, alert ID)")
    payload: dict = Field(default_factory=dict, description="Domain-specific payload")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt-123",
                "type": "alert_status_changed",
                "timestamp": "2025-11-17T10:30:00Z",
                "source": "alerts",
                "key": "alert-001",
                "payload": {
                    "alert_id": "alert-001",
                    "status": "acknowledged",
                    "shipment_reference": "SHP-2025-027",
                },
            }
        }


# ==============================================================================
# Smart Settlements / Payment Events
# ==============================================================================


class PaymentEventKind(str, Enum):
    """
    Payment milestone event kind for Smart Settlements.

    Tracks the lifecycle of payment milestones from creation through settlement.
    """
    MILESTONE_BECAME_ELIGIBLE = "milestone_became_eligible"
    MILESTONE_RELEASED = "milestone_released"
    MILESTONE_SETTLED = "milestone_settled"
    MILESTONE_BLOCKED = "milestone_blocked"
    MILESTONE_UNBLOCKED = "milestone_unblocked"


class ProofpackHint(BaseModel):
    """Lightweight indicator that a ProofPack is available."""

    milestone_id: str = Field(..., description="Canonical milestone identifier")
    has_proofpack: bool = Field(..., description="True when backend can return ProofPack")
    version: str = Field(..., description="Version label for ProofPack preview")

    @field_validator("milestone_id")
    @classmethod
    def validate_milestone_id(cls, value: str) -> str:
        if not is_valid_milestone_id(value):
            raise ValueError(
                "milestone_id must match '<shipment_reference>-M<index>' "
                "(e.g., 'SHP-2025-042-M1')"
            )
        return value


class PaymentSettlementEvent(BaseModel):
    """
    Payload for payment state change events.

    Emitted when payment milestones transition between states.
    Used with ControlTowerEvent where type=PAYMENT_STATE_CHANGED.
    """
    shipment_reference: str = Field(
        ...,
        description="Shipment reference ID (e.g., SHP-2025-027)"
    )
    milestone_id: str = Field(
        ...,
        description="Canonical milestone identifier '<shipment_reference>-M<index>'"
    )
    milestone_name: str = Field(
        ...,
        description="Human-readable milestone name (e.g., 'POD Confirmed', 'Pickup Complete')"
    )
    from_state: str = Field(
        ...,
        description="Previous payment status (pending/approved/delayed/etc.)"
    )
    to_state: str = Field(
        ...,
        description="New payment status"
    )
    amount: float = Field(
        ...,
        description="Settlement amount for this milestone"
    )
    currency: str = Field(
        default="USD",
        description="ISO 4217 currency code"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for the state change"
    )
    freight_token_id: Optional[int] = Field(
        default=None,
        description="Freight token correlation identifier"
    )
    proofpack_hint: Optional[ProofpackHint] = Field(
        default=None,
        description="Indicates ProofPack availability without fetching full payload"
    )

    @field_validator("milestone_id")
    @classmethod
    def validate_event_milestone_id(cls, value: str) -> str:
        if not is_valid_milestone_id(value):
            raise ValueError(
                "milestone_id must match '<shipment_reference>-M<index>' "
                "(e.g., 'SHP-2025-042-M1')"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shipment_reference": "SHP-2025-027",
                "milestone_id": "SHP-2025-027-M2",
                "milestone_name": "POD Confirmed",
                "from_state": "pending",
                "to_state": "approved",
                "amount": 700.0,
                "currency": "USD",
                "reason": "Low risk shipment - immediate release",
                "freight_token_id": 2025027,
                "proofpack_hint": {
                    "milestone_id": "SHP-2025-027-M2",
                    "has_proofpack": True,
                    "version": "v1-alpha",
                },
            }
        }
    )
