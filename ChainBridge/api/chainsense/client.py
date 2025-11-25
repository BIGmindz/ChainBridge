# api/chainsense/client.py
"""
ChainSense IoT Data Provider
=============================

This module defines the IoT data provider interface and implementations for
fetching IoT health, shipment snapshots, and events.

Architecture:
- IoTDataProvider: Abstract interface for IoT data sources
- MockIoTDataProvider: Implementation using mock fixtures (for development)
- Future: RealIoTDataProvider for production IoT platform integration

Author: ChainBridge Platform Team
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from api.schemas.chainboard import (
    IoTHealthSummary,
    ShipmentEventType,
    ShipmentIoTSnapshot,
    TimelineEvent,
)


class IoTDataProvider(ABC):
    """
    Abstract interface for IoT data providers.

    This allows swapping between mock data (development) and real IoT platforms
    (production) without changing route handlers.
    """

    @abstractmethod
    def get_global_health(self) -> IoTHealthSummary:
        """
        Fetch network-wide IoT health metrics.

        Returns:
            IoTHealthSummary with coverage, sensor counts, and alert stats
        """
        ...

    @abstractmethod
    def get_shipment_snapshot(self, shipment_ref: str) -> Optional[ShipmentIoTSnapshot]:
        """
        Fetch IoT sensor snapshot for a specific shipment.

        Args:
            shipment_ref: Shipment reference identifier (e.g., "SHP-1001")

        Returns:
            ShipmentIoTSnapshot if IoT data exists, None otherwise
        """
        ...

    @abstractmethod
    def get_shipment_events(self, shipment_ref: str, limit: int = 50) -> List[TimelineEvent]:
        """
        Fetch IoT-related timeline events for a shipment.

        Args:
            shipment_ref: Shipment reference identifier
            limit: Maximum number of events to return

        Returns:
            List of TimelineEvent objects with IoT event types
        """
        ...


class MockIoTDataProvider(IoTDataProvider):
    """
    Mock IoT data provider using in-memory fixtures.

    This implementation reads from existing mock data structures in
    api/mock/chainboard_fixtures.py and normalizes them into the schema models.
    """

    def __init__(self):
        """Initialize mock provider with fixture data."""
        # Import here to avoid circular dependencies
        from api.mock.chainboard_fixtures import (
            mock_iot_health_summary,
            mock_iot_snapshots,
            mock_shipments,
        )

        self._health_summary = mock_iot_health_summary
        self._snapshots: Dict[str, ShipmentIoTSnapshot] = mock_iot_snapshots
        self._shipments = mock_shipments

    def get_global_health(self) -> IoTHealthSummary:
        """Return the mock global IoT health summary."""
        return self._health_summary

    def get_shipment_snapshot(self, shipment_ref: str) -> Optional[ShipmentIoTSnapshot]:
        """
        Return IoT snapshot for a shipment if it exists.

        Args:
            shipment_ref: Shipment ID (e.g., "SHP-1001")

        Returns:
            ShipmentIoTSnapshot or None if no IoT data
        """
        return self._snapshots.get(shipment_ref)

    def get_shipment_events(self, shipment_ref: str, limit: int = 50) -> List[TimelineEvent]:
        """
        Return IoT-related events for a shipment.

        Filters timeline events to only include IoT event types.

        Args:
            shipment_ref: Shipment ID
            limit: Max events to return

        Returns:
            List of IoT TimelineEvent objects
        """
        from api.mock.chainboard_fixtures import build_mock_shipment_events

        # Get all events for this shipment (function returns TimelineEventResponse)
        response = build_mock_shipment_events(reference=shipment_ref)
        all_events = response.events

        # Filter to IoT events only
        iot_event_types = {ShipmentEventType.IOT_ALERT}

        iot_events = [
            event for event in all_events if event.event_type in iot_event_types
        ]

        # Sort by most recent first and apply limit
        iot_events.sort(key=lambda e: e.occurred_at, reverse=True)
        return iot_events[:limit]
