# api/mock/chainboard_fixtures.py
"""
Realistic In-Memory Fixtures for ChainBoard API
===============================================

This module provides realistic, in-memory mock data for the ChainBoard FastAPI
endpoints. It is designed to be a plug-and-play data source for local
development and end-to-end testing of the ChainBoard UI.

Data Realism Principles:
- **Corridor Variety**: Includes major global trade lanes (Asia-US, Asia-EU, Intra-Asia).
- **Risk Distribution**: A mix of low, medium, and high-risk shipments.
- **Status Variety**: Shipments in all lifecycle stages (pickup, transit, delivery, etc.).
- **Payment States**: Diverse payment scenarios, including blocked and partial payments.
- **IoT Coverage**: Simulates a fleet where not all shipments have IoT sensors.
- **Exceptions**: Realistic operational exceptions like delays and risk spikes.

Author: ChainBridge Platform Team
Version: 1.0.0 (Production-Ready)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from api.schemas.chainboard import (
    CorridorMetrics,
    CorridorTrend,
    ExceptionCode,
    ExceptionRow,
    FreightDetail,
    FreightMode,
    GlobalSummary,
    GovernanceSnapshot,
    GovernanceSummary,
    IoTHealthSummary,
    IoTHealthSummaryResponse,
    IoTSensorReading,
    IoTSensorType,
    IoTSeverity,
    MilestoneState,
    PaymentMilestone,
    PaymentProfile,
    PaymentQueueItem,
    PaymentQueueResponse,
    PaymentState,
    PaymentSummary,
    ProofpackStatus,
    RiskCategory,
    RiskFactor,
    RiskProfile,
    RiskOverview,
    RiskOverviewResponse,
    RiskStory,
    RiskStoryResponse,
    Shipment,
    ShipmentEventType,
    ShipmentIoTSnapshot,
    ShipmentStatus,
    ShipmentSummary,
    ThreatLevel,
    TimelineEvent,
    TimelineEventResponse,
)
from core.payments.identity import canonical_milestone_id, infer_freight_token_id

# ============================================================================
# MOCK DATA GENERATION
# ============================================================================

NOW = datetime.utcnow()


def _milestone(shipment_ref: str, index: int, **kwargs) -> PaymentMilestone:
    """Helper to build PaymentMilestone with canonical identifiers."""
    return PaymentMilestone(
        milestone_id=canonical_milestone_id(shipment_ref, index),
        freight_token_id=infer_freight_token_id(shipment_ref),
        **kwargs,
    )

# --- Shipments Data ---
mock_shipments: List[Shipment] = [
    Shipment(
        id="SHP-1001",
        reference="MAEU-123456",
        status=ShipmentStatus.IN_TRANSIT,
        origin="Shanghai, CN",
        destination="Los Angeles, US",
        corridor="Shanghai → Los Angeles",
        carrier="Maersk",
        customer="Acme Electronics",
        freight=FreightDetail(
            mode=FreightMode.OCEAN,
            incoterm="FOB",
            vessel="Maersk Horizon",
            container="40' HC",
            lane="Shanghai → Los Angeles",
            departure=NOW - timedelta(days=10),
            eta=NOW + timedelta(days=5),
            events=[],
        ),
        risk=RiskProfile(
            score=82,
            category=RiskCategory.HIGH,
            drivers=["Port congestion", "Carrier capacity constraints"],
            assessed_at=NOW - timedelta(hours=6),
            watchlisted=True,
        ),
        payment=PaymentProfile(
            state=PaymentState.PARTIALLY_PAID,
            total_value_usd=Decimal("420000.00"),
            released_usd=Decimal("252000.00"),
            released_percentage=60,
            holds_usd=Decimal("75000.00"),
            milestones=[
                _milestone(
                    "SHP-1001",
                    1,
                    label="Pickup",
                    percentage=20,
                    state=MilestoneState.RELEASED,
                    released_at=NOW - timedelta(days=9),
                ),
                _milestone(
                    "SHP-1001",
                    2,
                    label="In Transit",
                    percentage=40,
                    state=MilestoneState.RELEASED,
                    released_at=NOW - timedelta(days=2),
                ),
                _milestone(
                    "SHP-1001",
                    3,
                    label="Delivery",
                    percentage=40,
                    state=MilestoneState.PENDING,
                ),
            ],
            updated_at=NOW - timedelta(hours=2),
        ),
        governance=GovernanceSnapshot(
            proofpack_status=ProofpackStatus.VERIFIED,
            last_audit=NOW - timedelta(days=1),
            exceptions=[ExceptionCode.RISK_SPIKE],
        ),
    ),
    Shipment(
        id="SHP-1002",
        reference="CMA-789012",
        status=ShipmentStatus.DELIVERY,
        origin="Hamburg, DE",
        destination="New York, US",
        corridor="Hamburg → New York",
        carrier="CMA CGM",
        customer="Global Imports Inc.",
        freight=FreightDetail(
            mode=FreightMode.OCEAN,
            incoterm="CIF",
            vessel="CMA CGM Antoine",
            container="20' GP",
            lane="Hamburg → New York",
            departure=NOW - timedelta(days=15),
            eta=NOW - timedelta(days=1),
            events=[],
        ),
        risk=RiskProfile(
            score=35,
            category=RiskCategory.LOW,
            drivers=[],
            assessed_at=NOW - timedelta(hours=12),
            watchlisted=False,
        ),
        payment=PaymentProfile(
            state=PaymentState.COMPLETED,
            total_value_usd=Decimal("180000.00"),
            released_usd=Decimal("180000.00"),
            released_percentage=100,
            holds_usd=Decimal("0.00"),
            milestones=[
                _milestone(
                    "SHP-1002",
                    1,
                    label="Full Payment",
                    percentage=100,
                    state=MilestoneState.RELEASED,
                    released_at=NOW - timedelta(days=1),
                ),
            ],
            updated_at=NOW - timedelta(days=1),
        ),
        governance=GovernanceSnapshot(
            proofpack_status=ProofpackStatus.VERIFIED,
            last_audit=NOW - timedelta(days=2),
            exceptions=[],
        ),
    ),
    Shipment(
        id="SHP-1003",
        reference="FEDEX-345678",
        status=ShipmentStatus.DELAYED,
        origin="Shenzhen, CN",
        destination="Singapore, SG",
        corridor="Shenzhen → Singapore",
        carrier="FedEx",
        customer="Tech Components Ltd.",
        freight=FreightDetail(
            mode=FreightMode.AIR,
            incoterm="DAP",
            vessel="FX5821",
            container="ULD",
            lane="Shenzhen → Singapore",
            departure=NOW - timedelta(days=2),
            eta=NOW - timedelta(hours=12),  # Was due 12 hours ago
            events=[],
        ),
        risk=RiskProfile(
            score=65,
            category=RiskCategory.MEDIUM,
            drivers=["Weather delay", "Airport congestion"],
            assessed_at=NOW - timedelta(hours=4),
            watchlisted=False,
        ),
        payment=PaymentProfile(
            state=PaymentState.BLOCKED,
            total_value_usd=Decimal("95000.00"),
            released_usd=Decimal("23750.00"),
            released_percentage=25,
            holds_usd=Decimal("71250.00"),
            milestones=[
                _milestone(
                    "SHP-1003",
                    1,
                    label="Pickup",
                    percentage=25,
                    state=MilestoneState.RELEASED,
                    released_at=NOW - timedelta(days=2),
                ),
                _milestone(
                    "SHP-1003",
                    2,
                    label="Delivery",
                    percentage=75,
                    state=MilestoneState.BLOCKED,
                ),
            ],
            updated_at=NOW - timedelta(hours=1),
        ),
        governance=GovernanceSnapshot(
            proofpack_status=ProofpackStatus.PENDING,
            last_audit=NOW - timedelta(days=3),
            exceptions=[ExceptionCode.LATE_DELIVERY, ExceptionCode.PAYMENT_BLOCKED],
        ),
    ),
]

# --- Exceptions Data ---
mock_exceptions: List[ExceptionRow] = [
    ExceptionRow(
        shipment_id="SHP-1001",
        lane="Shanghai → Los Angeles",
        current_status=ShipmentStatus.IN_TRANSIT,
        risk_score=82,
        payment_state=PaymentState.PARTIALLY_PAID,
        age_of_issue="6h",
        issue_types=[ExceptionCode.RISK_SPIKE],
        last_update=(NOW - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
    ),
    ExceptionRow(
        shipment_id="SHP-1003",
        lane="Shenzhen → Singapore",
        current_status=ShipmentStatus.DELAYED,
        risk_score=65,
        payment_state=PaymentState.BLOCKED,
        age_of_issue="1d",
        issue_types=[ExceptionCode.LATE_DELIVERY, ExceptionCode.PAYMENT_BLOCKED],
        last_update=(NOW - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
    ),
]

# --- Corridor Metrics Data ---
mock_corridor_metrics: List[CorridorMetrics] = [
    CorridorMetrics(
        corridor_id="asia-us-west",
        label="Asia → US West",
        shipment_count=42,
        active_count=28,
        high_risk_count=3,
        blocked_payments=1,
        avg_risk_score=63,
        trend=CorridorTrend.RISING,
    ),
    CorridorMetrics(
        corridor_id="asia-eu",
        label="Asia → Europe",
        shipment_count=35,
        active_count=21,
        high_risk_count=1,
        blocked_payments=0,
        avg_risk_score=45,
        trend=CorridorTrend.STABLE,
    ),
    CorridorMetrics(
        corridor_id="intra-asia",
        label="Intra-Asia",
        shipment_count=58,
        active_count=40,
        high_risk_count=5,
        blocked_payments=2,
        avg_risk_score=55,
        trend=CorridorTrend.IMPROVING,
    ),
]

# --- Shipment IoT Snapshots ---
mock_iot_snapshots: Dict[str, ShipmentIoTSnapshot] = {
    "SHP-1001": ShipmentIoTSnapshot(
        shipment_id="SHP-1001",
        latest_readings=[
            IoTSensorReading(
                sensor_type=IoTSensorType.TEMPERATURE,
                value=18.5,
                unit="C",
                timestamp=NOW - timedelta(minutes=30),
                status=IoTSeverity.INFO,
            ),
            IoTSensorReading(
                sensor_type=IoTSensorType.HUMIDITY,
                value=65.2,
                unit="%",
                timestamp=NOW - timedelta(minutes=30),
                status=IoTSeverity.INFO,
            ),
            IoTSensorReading(
                sensor_type=IoTSensorType.SHOCK,
                value="2.1",
                unit="G",
                timestamp=NOW - timedelta(hours=2),
                status=IoTSeverity.WARN,
            ),
        ],
        alert_count_24h=3,
        critical_alerts_24h=0,
    ),
    "SHP-1003": ShipmentIoTSnapshot(
        shipment_id="SHP-1003",
        latest_readings=[
            IoTSensorReading(
                sensor_type=IoTSensorType.DOOR,
                value="CLOSED",
                timestamp=NOW - timedelta(minutes=15),
                status=IoTSeverity.INFO,
            ),
            IoTSensorReading(
                sensor_type=IoTSensorType.GPS,
                value="1.3521, 103.8198",
                timestamp=NOW - timedelta(minutes=15),
                status=IoTSeverity.INFO,
            ),
        ],
        alert_count_24h=1,
        critical_alerts_24h=1,
    ),
    "SHP-1004": ShipmentIoTSnapshot(
        shipment_id="SHP-1004",
        latest_readings=[
            IoTSensorReading(
                sensor_type=IoTSensorType.TEMPERATURE,
                value=5.4,
                unit="C",
                timestamp=NOW - timedelta(minutes=5),
                status=IoTSeverity.WARN,
            ),
            IoTSensorReading(
                sensor_type=IoTSensorType.DOOR,
                value="OPEN",
                timestamp=NOW - timedelta(minutes=5),
                status=IoTSeverity.CRITICAL,
            ),
            IoTSensorReading(
                sensor_type=IoTSensorType.GPS,
                value="34.0522, -118.2437",
                timestamp=NOW - timedelta(minutes=5),
                status=IoTSeverity.INFO,
            ),
        ],
        alert_count_24h=5,
        critical_alerts_24h=2,
    ),
}

# --- IoT Health Summary ---
mock_iot_health_summary = IoTHealthSummary(
    shipments_with_iot=len(mock_iot_snapshots),
    active_sensors=247,
    alerts_last_24h=6,
    critical_alerts_last_24h=1,
    coverage_percent=72.5,
)


def get_mock_iot_health_summary() -> IoTHealthSummaryResponse:
    """Return a deterministic IoT health snapshot aligned with API schema."""

    return IoTHealthSummaryResponse(
        iot_health=mock_iot_health_summary,
        generated_at=NOW,
    )


def build_mock_risk_overview() -> RiskOverview:
    total_shipments = len(mock_shipments)
    high_risk_shipments = sum(1 for shipment in mock_shipments if shipment.risk.category == RiskCategory.HIGH)
    total_value_usd = sum((shipment.payment.total_value_usd for shipment in mock_shipments), Decimal("0"))
    average_risk_score = (
        sum(shipment.risk.score for shipment in mock_shipments) / total_shipments if total_shipments else 0.0
    )

    return RiskOverview(
        total_shipments=total_shipments,
        high_risk_shipments=high_risk_shipments,
        total_value_usd=total_value_usd,
        average_risk_score=round(float(average_risk_score), 2),
        updated_at=NOW,
    )


def get_mock_risk_overview() -> RiskOverviewResponse:
    """Return a mock risk overview aligned with backend schema."""

    return RiskOverviewResponse(
        overview=build_mock_risk_overview(),
        generated_at=datetime.utcnow(),
    )


def build_mock_payment_queue() -> PaymentQueueResponse:
    """Build payment queue from shipments with holds."""
    items: List[PaymentQueueItem] = []

    for shipment in mock_shipments:
        # Only include shipments with holds
        if shipment.payment.holds_usd > 0:
            # Calculate aging from risk assessment
            aging_delta = datetime.utcnow() - shipment.risk.assessed_at
            aging_days = max(0, aging_delta.days)

            next_milestone = next(
                (m for m in shipment.payment.milestones if m.state != MilestoneState.RELEASED),
                shipment.payment.milestones[-1] if shipment.payment.milestones else None,
            )
            milestone_id = (
                next_milestone.milestone_id
                if next_milestone
                else canonical_milestone_id(shipment.id, 1)
            )
            freight_token_id = (
                next_milestone.freight_token_id
                if next_milestone
                else infer_freight_token_id(shipment.id)
            )

            item = PaymentQueueItem(
                shipment_id=shipment.id,
                reference=shipment.reference,
                corridor=shipment.corridor,
                customer=shipment.customer,
                total_value_usd=shipment.payment.total_value_usd,
                holds_usd=shipment.payment.holds_usd,
                released_usd=shipment.payment.released_usd,
                aging_days=aging_days,
                risk_category=shipment.risk.category if shipment.risk.watchlisted else None,
                milestone_id=milestone_id,
                freight_token_id=freight_token_id,
            )
            items.append(item)

    # Sort by holds amount descending
    items.sort(key=lambda x: x.holds_usd, reverse=True)

    total_holds = sum(item.holds_usd for item in items)

    return PaymentQueueResponse(
        items=items,
        total_items=len(items),
        total_holds_usd=total_holds,
        generated_at=datetime.utcnow(),
    )


def build_mock_risk_stories() -> RiskStoryResponse:
    """Build human-readable risk narratives for all shipments."""
    stories: List[RiskStory] = []

    # Risk narrative templates based on category and characteristics
    narrative_templates = {
        RiskCategory.HIGH: {
            "summaries": [
                "Route through congested {} corridor with {}-day delay history. Customer has {} overdue invoices.",
                "Carrier {} has elevated incident rate. Shipment value exceeds typical threshold by {}%.",
                "Multiple document discrepancies detected. Payment behavior shows {} days average delay.",
                "IoT sensors reporting {} anomalies. Route volatility index at {}/100.",
            ],
            "actions": [
                "Escalate to operations and request prepayment for next milestone",
                "Require full documentation review before release",
                "Contact carrier for updated ETA and implement daily check-ins",
                "Flag for senior management review and consider cargo insurance upgrade",
            ],
            "factor_sets": [
                [RiskFactor.ROUTE_VOLATILITY, RiskFactor.PAYMENT_BEHAVIOR],
                [RiskFactor.CARRIER_HISTORY, RiskFactor.PAYMENT_BEHAVIOR],
                [RiskFactor.DOCUMENT_ISSUES, RiskFactor.PAYMENT_BEHAVIOR],
                [RiskFactor.IOT_ANOMALIES, RiskFactor.ROUTE_VOLATILITY],
            ],
        },
        RiskCategory.MEDIUM: {
            "summaries": [
                "Moderate delays expected in {} region. Payment terms stretched beyond standard {}.",
                "Carrier performance within acceptable range but trending downward. {} minor alerts.",
                "Documentation complete but contains {} clarifications needed.",
                "Route experiencing seasonal congestion. Expected {} days additional transit time.",
            ],
            "actions": [
                "Monitor closely and prepare contingency routing options",
                "Request payment status update from customer",
                "Schedule documentation review with compliance team",
                "Track daily and escalate if ETA slips further",
            ],
            "factor_sets": [
                [RiskFactor.ROUTE_VOLATILITY],
                [RiskFactor.CARRIER_HISTORY, RiskFactor.PAYMENT_BEHAVIOR],
                [RiskFactor.DOCUMENT_ISSUES],
                [RiskFactor.ROUTE_VOLATILITY],
            ],
        },
        RiskCategory.LOW: {
            "summaries": [
                "Shipment proceeding normally on established {} route. All milestones met.",
                "Strong carrier performance record. Payment history excellent with {} on-time settlements.",
                "Documentation verified and complete. No compliance flags.",
                "IoT sensors reporting normal conditions. ETA confidence {}%.",
            ],
            "actions": [
                "Standard monitoring - no special action required",
                "Continue normal operational procedures",
                "Routine status check at next milestone",
                "Maintain current monitoring cadence",
            ],
            "factor_sets": [
                [],
                [RiskFactor.PAYMENT_BEHAVIOR],
                [],
                [RiskFactor.IOT_ANOMALIES],
            ],
        },
    }

    for idx, shipment in enumerate(mock_shipments):
        category = shipment.risk.category
        templates = narrative_templates[category]

        # Use deterministic selection based on shipment ID
        template_idx = idx % len(templates["summaries"])

        # Build context-specific summary
        if category == RiskCategory.HIGH:
            summary_vars = [
                shipment.corridor.split("→")[0].strip(),
                str(3 + (idx % 4)),
                str(1 + (idx % 3)),
            ]
            if template_idx == 1:
                summary_vars = [shipment.carrier, str(15 + (idx % 20))]
            elif template_idx == 2:
                summary_vars = [str(14 + (idx % 10))]
            elif template_idx == 3:
                summary_vars = [str(2 + (idx % 4)), str(75 + (idx % 20))]
        elif category == RiskCategory.MEDIUM:
            summary_vars = [
                shipment.corridor.split("→")[0].strip(),
                "net-30" if idx % 2 == 0 else "net-45",
            ]
            if template_idx == 1:
                summary_vars = [str(1 + (idx % 3))]
            elif template_idx == 2:
                summary_vars = [str(1 + (idx % 2))]
            elif template_idx == 3:
                summary_vars = [str(2 + (idx % 3))]
        else:  # LOW
            summary_vars = [shipment.corridor]
            if template_idx == 1:
                summary_vars = [str(8 + (idx % 5))]
            elif template_idx == 3:
                summary_vars = [str(92 + (idx % 6))]

        # Format summary with variables (handle variable number of placeholders)
        summary_template = templates["summaries"][template_idx]
        try:
            summary = summary_template.format(*summary_vars)
        except (IndexError, KeyError):
            summary = summary_template.replace("{}", "N/A")

        # Select factors and action
        factors = templates["factor_sets"][template_idx]
        primary_factor = factors[0] if factors else RiskFactor.ROUTE_VOLATILITY
        recommended_action = templates["actions"][template_idx]

        story = RiskStory(
            shipment_id=shipment.id,
            reference=shipment.reference,
            corridor=shipment.corridor,
            risk_category=category,
            score=shipment.risk.score,
            primary_factor=primary_factor,
            factors=factors if factors else [primary_factor],
            summary=summary,
            recommended_action=recommended_action,
            last_updated=shipment.risk.assessed_at,
        )
        stories.append(story)

    # Sort by risk score descending (highest risk first)
    stories.sort(key=lambda x: x.score, reverse=True)

    return RiskStoryResponse(
        stories=stories,
        total=len(stories),
        generated_at=datetime.utcnow(),
    )


def build_mock_shipment_events(reference: Optional[str] = None) -> TimelineEventResponse:
    """Build realistic timeline events for shipments.

    Args:
        reference: Optional shipment reference to filter events.
                  If None, returns events for all shipments.
    """
    events: List[TimelineEvent] = []
    base_time = datetime.utcnow() - timedelta(days=3)

    # Filter shipments if reference provided
    target_shipments = (
        [s for s in mock_shipments if s.reference == reference]
        if reference
        else mock_shipments
    )

    for idx, shipment in enumerate(target_shipments):
        # Determine event timeline based on shipment status
        shipment_events = []
        event_time = base_time + timedelta(hours=idx * 2)  # Stagger shipments

        # 1. CREATED (always first)
        shipment_events.append(
            TimelineEvent(
                shipment_id=shipment.id,
                reference=shipment.reference,
                corridor=shipment.corridor,
                event_type=ShipmentEventType.CREATED,
                description=f"Shipment created for {shipment.customer}",
                occurred_at=event_time,
                source="TMS",
                severity="info",
            )
        )
        event_time += timedelta(hours=4)

        # 2. BOOKED (all shipments)
        shipment_events.append(
            TimelineEvent(
                shipment_id=shipment.id,
                reference=shipment.reference,
                corridor=shipment.corridor,
                event_type=ShipmentEventType.BOOKED,
                description=f"Freight booked with carrier {shipment.carrier}",
                occurred_at=event_time,
                source="TMS",
                severity="info",
            )
        )
        event_time += timedelta(hours=8)

        # 3. PICKED_UP (if past pickup status)
        if shipment.status != ShipmentStatus.PICKUP:
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.PICKED_UP,
                    description=f"Container picked up from {shipment.corridor.split('→')[0].strip()}",
                    occurred_at=event_time,
                    source="TMS",
                    severity="info",
                )
            )
            event_time += timedelta(hours=12)

        # 4. DEPARTED_PORT (if in_transit, delivery, or completed)
        if shipment.status in [ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERY, ShipmentStatus.COMPLETED]:
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.DEPARTED_PORT,
                    description=f"Departed {shipment.corridor.split('→')[0].strip()} port",
                    occurred_at=event_time,
                    source="TMS",
                    severity="info",
                )
            )
            event_time += timedelta(hours=24)

        # 5. IOT_ALERT (if has IoT sensors and high/medium risk)
        iot_snapshot = mock_iot_snapshots.get(shipment.id)
        if iot_snapshot and shipment.risk.category in [RiskCategory.HIGH, RiskCategory.MEDIUM]:
            alert_type = "temperature spike" if idx % 2 == 0 else "humidity threshold exceeded"
            severity = "critical" if shipment.risk.category == RiskCategory.HIGH else "warning"
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.IOT_ALERT,
                    description=f"IoT Alert: {alert_type} detected by {len(iot_snapshot.latest_readings)} sensors",
                    occurred_at=event_time,
                    source="IoT",
                    severity=severity,
                )
            )
            event_time += timedelta(hours=6)

        # 6. CUSTOMS_HOLD (for high-risk shipments)
        if shipment.risk.category == RiskCategory.HIGH and idx % 3 == 0:
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.CUSTOMS_HOLD,
                    description=f"Held at {shipment.corridor.split('→')[1].strip()} customs for inspection",
                    occurred_at=event_time,
                    source="TMS",
                    severity="warning",
                )
            )
            event_time += timedelta(hours=18)

            # 7. CUSTOMS_RELEASED (after hold)
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.CUSTOMS_RELEASED,
                    description="Customs clearance approved, shipment released",
                    occurred_at=event_time,
                    source="TMS",
                    severity="info",
                )
            )
            event_time += timedelta(hours=4)

        # 8. ARRIVED_PORT (if at delivery or completed)
        if shipment.status in [ShipmentStatus.DELIVERY, ShipmentStatus.COMPLETED]:
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.ARRIVED_PORT,
                    description=f"Arrived at {shipment.corridor.split('→')[1].strip()} port",
                    occurred_at=event_time,
                    source="TMS",
                    severity="info",
                )
            )
            event_time += timedelta(hours=8)

        # 9. DELIVERED (if completed)
        if shipment.status == ShipmentStatus.COMPLETED:
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.DELIVERED,
                    description=f"Delivered to {shipment.customer}",
                    occurred_at=event_time,
                    source="TMS",
                    severity="info",
                )
            )
            event_time += timedelta(hours=2)

        # 10. PAYMENT_RELEASE (for completed payments)
        if shipment.payment.state == PaymentState.COMPLETED:
            shipment_events.append(
                TimelineEvent(
                    shipment_id=shipment.id,
                    reference=shipment.reference,
                    corridor=shipment.corridor,
                    event_type=ShipmentEventType.PAYMENT_RELEASE,
                    description="Payment completed and funds released",
                    occurred_at=event_time,
                    source="Finance",
                    severity="info",
                )
            )

        events.extend(shipment_events)

    # Sort by occurred_at descending (most recent first)
    events.sort(key=lambda x: x.occurred_at, reverse=True)

    return TimelineEventResponse(
        events=events,
        total=len(events),
        generated_at=datetime.utcnow(),
    )


# --- Global Summary ---
mock_global_summary = GlobalSummary(
    threat_level=ThreatLevel.ELEVATED,
    shipments=ShipmentSummary(
        total_shipments=148,
        active_shipments=92,
        on_time_percent=81,
        exception_count=len(mock_exceptions),
        high_risk_count=5,
        delayed_or_blocked_count=4,
    ),
    payments=PaymentSummary(
        blocked_payments=3,
        partially_paid=14,
        completed=86,
        not_started=12,
        in_progress=33,
        payment_health_score=78,
        capital_locked_hours=420.0,
    ),
    governance=GovernanceSummary(
        proofpack_ok_percent=92.0,
        open_audits=3,
        watchlisted_shipments=5,
    ),
    top_corridor=mock_corridor_metrics[0],
    iot=mock_iot_health_summary,
)


# ============================================================================
# MOCK ALERTS GENERATION
# ============================================================================


def build_mock_alerts() -> List["ControlTowerAlert"]:
    """
    Generate realistic alerts from risk, IoT, payment, and customs domains.

    Returns alerts sorted by created_at descending (most recent first).
    Uses stable IDs for consistent test assertions.
    """
    from api.schemas.chainboard import (
        ControlTowerAlert,
        AlertSource,
        AlertSeverity,
        AlertStatus,
    )

    alerts = []

    # Alert 1: High-risk corridor (from SHP-1001)
    alerts.append(
        ControlTowerAlert(
            id="alert-001",
            shipment_reference="SHP-1001",
            title="High risk corridor: Shanghai → Los Angeles",
            description="Shipment operating in elevated-risk corridor with port congestion and carrier capacity constraints. Risk score: 82/100.",
            source=AlertSource.RISK,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=6),
            updated_at=NOW - timedelta(hours=6),
            tags=["risk", "high_risk", "corridor_alert", "port_congestion"],
        )
    )

    # Alert 2: IoT temperature anomaly (from SHP-1002)
    alerts.append(
        ControlTowerAlert(
            id="alert-002",
            shipment_reference="SHP-1002",
            title="Temperature threshold exceeded",
            description="Container temperature reached 8.2°C, exceeding safe threshold of 5°C for pharmaceuticals. Immediate attention required.",
            source=AlertSource.IOT,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=2),
            updated_at=NOW - timedelta(hours=2),
            tags=["iot", "temperature", "pharma", "cold_chain"],
        )
    )

    # Alert 3: Payment blocked (from SHP-1003)
    alerts.append(
        ControlTowerAlert(
            id="alert-003",
            shipment_reference="SHP-1003",
            title="Payment milestone blocked",
            description="Payment hold detected: compliance review required before milestone release. 2 of 3 milestones blocked.",
            source=AlertSource.PAYMENT,
            severity=AlertSeverity.WARNING,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=12),
            updated_at=NOW - timedelta(hours=12),
            tags=["payment", "payment_hold", "compliance_review"],
        )
    )

    # Alert 4: Customs hold (from SHP-1004)
    alerts.append(
        ControlTowerAlert(
            id="alert-004",
            shipment_reference="SHP-1004",
            title="Customs inspection hold",
            description="Shipment held at Rotterdam port for customs inspection. Estimated delay: 24-48 hours.",
            source=AlertSource.CUSTOMS,
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACKNOWLEDGED,
            created_at=NOW - timedelta(hours=18),
            updated_at=NOW - timedelta(hours=1),
            tags=["customs", "customs_hold", "inspection", "rotterdam"],
        )
    )

    # Alert 5: IoT location dwell (from SHP-2025-027 - hero shipment)
    alerts.append(
        ControlTowerAlert(
            id="alert-005",
            shipment_reference="SHP-2025-027",
            title="Location dwell detected",
            description="Container has been stationary at Long Beach terminal for 36 hours. Expected movement overdue.",
            source=AlertSource.IOT,
            severity=AlertSeverity.WARNING,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=4),
            updated_at=NOW - timedelta(hours=4),
            tags=["iot", "location_dwell", "terminal_delay", "long_beach"],
        )
    )

    # Alert 6: Risk spike for sanctioned entity
    alerts.append(
        ControlTowerAlert(
            id="alert-006",
            shipment_reference="SHP-1005",
            title="Sanctions screening alert",
            description="Potential match detected in sanctions database. Requires immediate compliance review.",
            source=AlertSource.RISK,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=1),
            updated_at=NOW - timedelta(hours=1),
            tags=["risk", "sanctions", "compliance", "screening_alert"],
        )
    )

    # Alert 7: Payment delay (from SHP-1006)
    alerts.append(
        ControlTowerAlert(
            id="alert-007",
            shipment_reference="SHP-1006",
            title="Payment milestone overdue",
            description="Milestone 2 payment is 48 hours overdue. Capital locked: $125,000.",
            source=AlertSource.PAYMENT,
            severity=AlertSeverity.WARNING,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=24),
            updated_at=NOW - timedelta(hours=24),
            tags=["payment", "overdue", "capital_locked"],
        )
    )

    # Alert 8: IoT door open (from SHP-1007)
    alerts.append(
        ControlTowerAlert(
            id="alert-008",
            shipment_reference="SHP-1007",
            title="Unauthorized door opening",
            description="Container door sensor triggered during transit. Security breach suspected.",
            source=AlertSource.IOT,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(minutes=30),
            updated_at=NOW - timedelta(minutes=30),
            tags=["iot", "door", "security", "breach"],
        )
    )

    # Alert 9: High-risk route (from SHP-2025-027 - hero shipment)
    alerts.append(
        ControlTowerAlert(
            id="alert-009",
            shipment_reference="SHP-2025-027",
            title="High-risk corridor alert",
            description="Shipment routing through elevated-risk zone. Enhanced monitoring enabled.",
            source=AlertSource.RISK,
            severity=AlertSeverity.WARNING,
            status=AlertStatus.OPEN,
            created_at=NOW - timedelta(hours=8),
            updated_at=NOW - timedelta(hours=8),
            tags=["risk", "corridor", "route_risk"],
        )
    )

    # Alert 10: Info-level customs documentation
    alerts.append(
        ControlTowerAlert(
            id="alert-010",
            shipment_reference="SHP-1008",
            title="Customs documentation submitted",
            description="Pre-clearance documents submitted to Hamburg customs authority. Awaiting confirmation.",
            source=AlertSource.CUSTOMS,
            severity=AlertSeverity.INFO,
            status=AlertStatus.RESOLVED,
            created_at=NOW - timedelta(days=2),
            updated_at=NOW - timedelta(hours=6),
            tags=["customs", "documentation", "pre_clearance", "hamburg"],
        )
    )

    # Sort by created_at descending (most recent first)
    alerts.sort(key=lambda a: a.created_at, reverse=True)

    return alerts
