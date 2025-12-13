"""
ChainIQ ML Event Parsing Module

Parses raw ChainBridge event logs into structured events for ML training.
This module is ONLY used during offline training data preparation.

Key Functions:
- parse_event_log: Parse raw event records into structured ParsedEvent objects
- group_events_by_shipment: Group events by shipment_id
- extract_event_timestamps: Extract key timestamps from event stream
- compute_transit_times: Calculate planned vs actual transit durations

Status: v0.2.1 - Real data ingestion pipeline (PAC-005)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Sequence


class EventType(str, Enum):
    """ChainBridge event types relevant to ML training."""

    # Lifecycle events
    SHIPMENT_CREATED = "SHIPMENT_CREATED"
    SHIPMENT_PICKED_UP = "SHIPMENT_PICKED_UP"
    SHIPMENT_IN_TRANSIT = "SHIPMENT_IN_TRANSIT"
    SHIPMENT_DELIVERED = "SHIPMENT_DELIVERED"
    SHIPMENT_CANCELLED = "SHIPMENT_CANCELLED"

    # Exception events
    DELAY_DETECTED = "DELAY_DETECTED"
    ROUTE_DEVIATION = "ROUTE_DEVIATION"
    TEMPERATURE_VIOLATION = "TEMPERATURE_VIOLATION"
    CUSTODY_GAP = "CUSTODY_GAP"
    MISSING_DOCUMENTATION = "MISSING_DOCUMENTATION"

    # Financial events
    CLAIM_FILED = "CLAIM_FILED"
    CLAIM_APPROVED = "CLAIM_APPROVED"
    CLAIM_DENIED = "CLAIM_DENIED"
    DISPUTE_OPENED = "DISPUTE_OPENED"
    DISPUTE_RESOLVED = "DISPUTE_RESOLVED"

    # IoT events
    SENSOR_READING = "SENSOR_READING"
    SENSOR_OFFLINE = "SENSOR_OFFLINE"
    SENSOR_BATTERY_LOW = "SENSOR_BATTERY_LOW"

    # Handoff events
    HANDOFF_INITIATED = "HANDOFF_INITIATED"
    HANDOFF_COMPLETED = "HANDOFF_COMPLETED"
    DWELL_START = "DWELL_START"
    DWELL_END = "DWELL_END"


@dataclass
class ParsedEvent:
    """
    Structured representation of a ChainBridge event.

    Attributes:
        event_id: Unique event identifier
        shipment_id: Shipment this event belongs to
        event_type: Type of event (from EventType enum)
        timestamp: When the event occurred
        payload: Additional event data (temperature, location, etc.)
        source: Event source (sensor, user, system)
    """

    event_id: str
    shipment_id: str
    event_type: EventType
    timestamp: datetime
    payload: dict[str, Any]
    source: str = "system"

    def __post_init__(self):
        """Validate and normalize event data."""
        # Convert string event_type to enum
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)

        # Parse timestamp if string
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))


def parse_event_log(record: dict[str, Any]) -> ParsedEvent:
    """
    Parse a raw event log record into a structured ParsedEvent.

    Args:
        record: Raw event dictionary from ChainBridge logs
                Expected keys: event_id, shipment_id, event_type, timestamp, payload

    Returns:
        ParsedEvent object with validated fields

    Raises:
        ValueError: If required fields are missing or invalid

    Example:
        >>> raw_event = {
        ...     "event_id": "evt_123",
        ...     "shipment_id": "shp_456",
        ...     "event_type": "DELAY_DETECTED",
        ...     "timestamp": "2024-12-11T10:00:00Z",
        ...     "payload": {"delay_hours": 2.5},
        ...     "source": "system"
        ... }
        >>> event = parse_event_log(raw_event)
        >>> event.event_type == EventType.DELAY_DETECTED
        True
    """
    # Validate required fields
    required_fields = ["event_id", "shipment_id", "event_type", "timestamp"]
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    # Extract fields with defaults
    event_id = record["event_id"]
    shipment_id = record["shipment_id"]
    event_type = record["event_type"]
    timestamp = record["timestamp"]
    payload = record.get("payload", {})
    source = record.get("source", "system")

    # Create ParsedEvent (validation happens in __post_init__)
    try:
        return ParsedEvent(
            event_id=event_id,
            shipment_id=shipment_id,
            event_type=event_type,
            timestamp=timestamp,
            payload=payload,
            source=source,
        )
    except (ValueError, KeyError) as e:
        raise ValueError(f"Failed to parse event {event_id}: {e}") from e


def group_events_by_shipment(
    events: Sequence[ParsedEvent],
) -> dict[str, list[ParsedEvent]]:
    """
    Group events by shipment_id and sort chronologically.

    Args:
        events: Sequence of ParsedEvent objects

    Returns:
        Dictionary mapping shipment_id -> sorted list of events

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {}),
        ...     ParsedEvent("e2", "shp2", EventType.SHIPMENT_CREATED, datetime(2024, 1, 2), {}),
        ...     ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 3), {}),
        ... ]
        >>> grouped = group_events_by_shipment(events)
        >>> len(grouped["shp1"])
        2
        >>> len(grouped["shp2"])
        1
    """
    grouped: dict[str, list[ParsedEvent]] = {}

    for event in events:
        if event.shipment_id not in grouped:
            grouped[event.shipment_id] = []
        grouped[event.shipment_id].append(event)

    # Sort each shipment's events chronologically
    for shipment_id in grouped:
        grouped[shipment_id].sort(key=lambda e: e.timestamp)

    return grouped


def extract_event_timestamps(
    events: Sequence[ParsedEvent],
) -> dict[str, datetime | None]:
    """
    Extract key lifecycle timestamps from event stream.

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        Dictionary with keys:
        - created_at: When shipment was created
        - picked_up_at: When shipment was picked up
        - delivered_at: When shipment was delivered
        - eta: Expected delivery time (from payload)
        - first_delay_at: When first delay was detected
        - first_claim_at: When first claim was filed

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED, datetime(2024, 1, 1), {"eta": "2024-01-03T00:00:00Z"}),
        ...     ParsedEvent("e2", "shp1", EventType.SHIPMENT_DELIVERED, datetime(2024, 1, 5), {}),
        ... ]
        >>> timestamps = extract_event_timestamps(events)
        >>> timestamps["created_at"].date()
        datetime.date(2024, 1, 1)
        >>> timestamps["delivered_at"].date()
        datetime.date(2024, 1, 5)
    """
    timestamps: dict[str, datetime | None] = {
        "created_at": None,
        "picked_up_at": None,
        "delivered_at": None,
        "eta": None,
        "first_delay_at": None,
        "first_claim_at": None,
        "first_dispute_at": None,
    }

    for event in events:
        # Lifecycle timestamps
        if event.event_type == EventType.SHIPMENT_CREATED and timestamps["created_at"] is None:
            timestamps["created_at"] = event.timestamp
            # Extract ETA from payload if present
            if "eta" in event.payload:
                eta_str = event.payload["eta"]
                if isinstance(eta_str, str):
                    timestamps["eta"] = datetime.fromisoformat(eta_str.replace("Z", "+00:00"))
                elif isinstance(eta_str, datetime):
                    timestamps["eta"] = eta_str

        elif event.event_type == EventType.SHIPMENT_PICKED_UP and timestamps["picked_up_at"] is None:
            timestamps["picked_up_at"] = event.timestamp

        elif event.event_type == EventType.SHIPMENT_DELIVERED and timestamps["delivered_at"] is None:
            timestamps["delivered_at"] = event.timestamp

        # Exception timestamps (first occurrence only)
        elif event.event_type == EventType.DELAY_DETECTED and timestamps["first_delay_at"] is None:
            timestamps["first_delay_at"] = event.timestamp

        elif event.event_type == EventType.CLAIM_FILED and timestamps["first_claim_at"] is None:
            timestamps["first_claim_at"] = event.timestamp

        elif event.event_type == EventType.DISPUTE_OPENED and timestamps["first_dispute_at"] is None:
            timestamps["first_dispute_at"] = event.timestamp

    return timestamps


def compute_transit_times(
    events: Sequence[ParsedEvent],
) -> dict[str, float | None]:
    """
    Compute planned vs actual transit times from event stream.

    All timestamps are normalized to UTC for consistent comparison.

    Args:
        events: Chronologically sorted events for a single shipment

    Returns:
        Dictionary with keys:
        - planned_transit_hours: Expected transit time (from creation to ETA)
        - actual_transit_hours: Actual transit time (from pickup to delivery)
        - delay_hours: Difference between actual and planned (positive = late)
        - eta_deviation_hours: Difference between delivered_at and ETA

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.SHIPMENT_CREATED,
        ...                 datetime(2024, 1, 1, 0, 0), {"eta": "2024-01-03T00:00:00Z"}),
        ...     ParsedEvent("e2", "shp1", EventType.SHIPMENT_PICKED_UP,
        ...                 datetime(2024, 1, 1, 6, 0), {}),
        ...     ParsedEvent("e3", "shp1", EventType.SHIPMENT_DELIVERED,
        ...                 datetime(2024, 1, 4, 6, 0), {}),
        ... ]
        >>> times = compute_transit_times(events)
        >>> times["actual_transit_hours"]
        72.0
        >>> times["eta_deviation_hours"]
        30.0
    """
    from datetime import timezone

    def normalize_to_utc(dt: datetime | None) -> datetime | None:
        """Ensure datetime is UTC-aware (treat naive as UTC)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    timestamps = extract_event_timestamps(events)

    # Normalize all timestamps to UTC
    created_at = normalize_to_utc(timestamps["created_at"])
    eta = normalize_to_utc(timestamps["eta"])
    picked_up_at = normalize_to_utc(timestamps["picked_up_at"])
    delivered_at = normalize_to_utc(timestamps["delivered_at"])

    transit_times: dict[str, float | None] = {
        "planned_transit_hours": None,
        "actual_transit_hours": None,
        "delay_hours": None,
        "eta_deviation_hours": None,
    }

    # Planned transit time: created_at to ETA
    if created_at and eta:
        delta = eta - created_at
        transit_times["planned_transit_hours"] = delta.total_seconds() / 3600

    # Actual transit time: picked_up_at to delivered_at
    if picked_up_at and delivered_at:
        delta = delivered_at - picked_up_at
        transit_times["actual_transit_hours"] = delta.total_seconds() / 3600

    # ETA deviation: delivered_at - ETA (positive = late)
    if delivered_at and eta:
        delta = delivered_at - eta
        transit_times["eta_deviation_hours"] = delta.total_seconds() / 3600

    # Delay: actual - planned (rough approximation)
    if transit_times["actual_transit_hours"] and transit_times["planned_transit_hours"]:
        transit_times["delay_hours"] = transit_times["actual_transit_hours"] - transit_times["planned_transit_hours"]

    return transit_times


def count_event_types(
    events: Sequence[ParsedEvent],
) -> dict[EventType, int]:
    """
    Count occurrences of each event type.

    Args:
        events: Sequence of events for a single shipment

    Returns:
        Dictionary mapping EventType -> count

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 1), {}),
        ...     ParsedEvent("e2", "shp1", EventType.DELAY_DETECTED, datetime(2024, 1, 2), {}),
        ...     ParsedEvent("e3", "shp1", EventType.CLAIM_FILED, datetime(2024, 1, 3), {}),
        ... ]
        >>> counts = count_event_types(events)
        >>> counts[EventType.DELAY_DETECTED]
        2
        >>> counts[EventType.CLAIM_FILED]
        1
    """
    counts: dict[EventType, int] = {}

    for event in events:
        counts[event.event_type] = counts.get(event.event_type, 0) + 1

    return counts


def extract_sensor_readings(
    events: Sequence[ParsedEvent],
) -> dict[str, list[float]]:
    """
    Extract sensor readings from event stream.

    Args:
        events: Sequence of events for a single shipment

    Returns:
        Dictionary with keys:
        - temperatures: List of temperature readings (°C)
        - humidities: List of humidity readings (%)
        - battery_levels: List of battery levels (%)

    Example:
        >>> events = [
        ...     ParsedEvent("e1", "shp1", EventType.SENSOR_READING,
        ...                 datetime(2024, 1, 1), {"temperature": 20.5, "humidity": 65.0}),
        ...     ParsedEvent("e2", "shp1", EventType.SENSOR_READING,
        ...                 datetime(2024, 1, 2), {"temperature": 22.0, "humidity": 60.0}),
        ... ]
        >>> readings = extract_sensor_readings(events)
        >>> readings["temperatures"]
        [20.5, 22.0]
    """
    readings: dict[str, list[float]] = {
        "temperatures": [],
        "humidities": [],
        "battery_levels": [],
    }

    for event in events:
        if event.event_type == EventType.SENSOR_READING:
            payload = event.payload

            if "temperature" in payload:
                readings["temperatures"].append(float(payload["temperature"]))

            if "humidity" in payload:
                readings["humidities"].append(float(payload["humidity"]))

            if "battery_level" in payload:
                readings["battery_levels"].append(float(payload["battery_level"]))

    return readings


# CLI helper for testing
if __name__ == "__main__":
    import json
    import sys

    print("ChainIQ Event Parsing Module")
    print("=" * 60)
    print("\nUsage:")
    print("  python -m app.ml.event_parsing < events.jsonl")
    print("\nExample event format:")
    example = {
        "event_id": "evt_123",
        "shipment_id": "shp_456",
        "event_type": "DELAY_DETECTED",
        "timestamp": "2024-12-11T10:00:00Z",
        "payload": {"delay_hours": 2.5},
        "source": "system",
    }
    print(json.dumps(example, indent=2))

    if not sys.stdin.isatty():
        # Read from stdin
        events = []
        for line in sys.stdin:
            record = json.loads(line.strip())
            event = parse_event_log(record)
            events.append(event)

        print(f"\n✓ Parsed {len(events)} events")

        # Group by shipment
        grouped = group_events_by_shipment(events)
        print(f"✓ Found {len(grouped)} unique shipments")

        # Show summary
        for shipment_id, shipment_events in list(grouped.items())[:3]:
            print(f"\nShipment {shipment_id}:")
            print(f"  Events: {len(shipment_events)}")
            timestamps = extract_event_timestamps(shipment_events)
            print(f"  Created: {timestamps['created_at']}")
            print(f"  Delivered: {timestamps['delivered_at']}")
