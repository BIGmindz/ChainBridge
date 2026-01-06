"""
OCC Event Stream Tests — PAC-BENSON-P33

Doctrine Law 4, §4.3: Read-only event stream for OCC replay.

Tests for:
- WebSocket /ws/events
- GET /events/recent
- GET /events/types
- GET /events/stream/status

INVARIANTS TESTED:
- INV-OCC-001: Read-only (no write capability)
- INV-OCC-002: Events are immutable
- INV-OCC-003: All events include timestamp and source

Author: CODY (GID-01) — Backend Implementation
Security: SAM (GID-06) — Read-only enforcement
DAN (GID-07) — CI/Test Enforcement
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.occ_events import (
    OCCEvent,
    OCCEventType,
    emit_occ_event,
    get_event_manager,
)
from api.server import app


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Note: We don't reset the event manager between tests since it's
# a global singleton and tests should be independent of state.


# =============================================================================
# EVENT MODEL TESTS
# =============================================================================


class TestOCCEventModel:
    """Tests for OCCEvent model."""

    def test_event_has_required_fields(self):
        """Event includes all required fields (INV-OCC-003)."""
        event = OCCEvent(
            event_type=OCCEventType.DECISION_CREATED,
            source="GID-01",
        )

        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.source == "GID-01"
        assert event.event_type == OCCEventType.DECISION_CREATED

    def test_event_timestamp_is_iso_format(self):
        """Event timestamp is ISO-8601 format."""
        event = OCCEvent(
            event_type=OCCEventType.PROOF_GENERATED,
            source="GID-02",
        )

        # Should parse without error
        parsed = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_event_id_is_unique(self):
        """Each event has a unique ID."""
        events = [
            OCCEvent(event_type=OCCEventType.SETTLEMENT_COMPLETED, source="test")
            for _ in range(100)
        ]

        ids = [e.event_id for e in events]
        assert len(ids) == len(set(ids))  # All unique

    def test_event_with_payload(self):
        """Event can include payload data."""
        payload = {"amount": 1000, "entity_id": "ENT-123"}
        event = OCCEvent(
            event_type=OCCEventType.SETTLEMENT_INITIATED,
            source="GID-00",
            payload=payload,
        )

        assert event.payload == payload


# =============================================================================
# EVENT MANAGER TESTS
# =============================================================================


class TestOCCEventManager:
    """Tests for OCCEventStreamManager."""

    @pytest.mark.asyncio
    async def test_emit_event_adds_to_log(self):
        """Emitted events are added to log."""
        manager = get_event_manager()
        initial_count = len(manager._event_log)

        await emit_occ_event(
            event_type=OCCEventType.DECISION_CREATED,
            source="test-source",
            payload={"test": True},
        )

        assert len(manager._event_log) == initial_count + 1

    @pytest.mark.asyncio
    async def test_get_recent_events(self):
        """Can retrieve recent events."""
        manager = get_event_manager()

        # Emit some events
        for i in range(5):
            await emit_occ_event(
                event_type=OCCEventType.AGENT_TASK_COMPLETED,
                source=f"agent-{i}",
            )

        events = await manager.get_recent_events(limit=10)
        assert len(events) >= 5

    @pytest.mark.asyncio
    async def test_get_recent_events_with_filter(self):
        """Can filter events by type."""
        manager = get_event_manager()

        # Emit mixed events
        await emit_occ_event(OCCEventType.DECISION_CREATED, "test")
        await emit_occ_event(OCCEventType.PROOF_GENERATED, "test")
        await emit_occ_event(OCCEventType.DECISION_APPROVED, "test")

        events = await manager.get_recent_events(
            event_types=["decision.created", "decision.approved"]
        )

        for event in events:
            assert event.event_type in ["decision.created", "decision.approved"]

    @pytest.mark.asyncio
    async def test_event_log_size_limit(self):
        """Event log respects size limit."""
        manager = get_event_manager()
        max_size = manager._max_log_size

        # Emit more than max events
        for i in range(max_size + 100):
            await emit_occ_event(
                event_type=OCCEventType.SYSTEM_HEARTBEAT,
                source="test",
            )

        assert len(manager._event_log) <= max_size


# =============================================================================
# REST ENDPOINT TESTS
# =============================================================================


class TestEventStreamRESTEndpoints:
    """Tests for REST endpoints."""

    def test_get_event_types(self, client):
        """GET /events/types returns all event types."""
        response = client.get("/events/types")

        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert "categories" in data
        assert len(data["event_types"]) == len(OCCEventType)

    def test_get_stream_status(self, client):
        """GET /events/stream/status returns status."""
        response = client.get("/events/stream/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "active_connections" in data
        assert "timestamp" in data

    def test_get_recent_events(self, client):
        """GET /events/recent returns events."""
        response = client.get("/events/recent")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert "timestamp" in data

    def test_get_recent_events_with_limit(self, client):
        """GET /events/recent respects limit parameter."""
        response = client.get("/events/recent", params={"limit": 5})

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 5

    def test_get_recent_events_with_filter(self, client):
        """GET /events/recent supports type filter."""
        response = client.get(
            "/events/recent",
            params={"event_types": "decision.created,proof.generated"},
        )

        assert response.status_code == 200


# =============================================================================
# WEBSOCKET TESTS
# =============================================================================


class TestEventStreamWebSocket:
    """Tests for WebSocket /ws/events."""

    def test_websocket_connect(self, client):
        """WebSocket connection succeeds."""
        with client.websocket_connect("/ws/events") as ws:
            # Connection should be established
            assert ws is not None

    def test_websocket_read_only_warning(self, client):
        """WebSocket returns warning when message sent (read-only)."""
        with client.websocket_connect("/ws/events") as ws:
            # Send a message (should be ignored with warning)
            ws.send_text("test message")

            # Should receive warning response
            response = ws.receive_json()
            assert response["type"] == "warning"
            assert "read-only" in response["message"].lower()

    def test_websocket_with_event_filter(self, client):
        """WebSocket accepts event type filter."""
        with client.websocket_connect(
            "/ws/events?event_types=decision.created,proof.generated"
        ) as ws:
            assert ws is not None


# =============================================================================
# INVARIANT TESTS (INV-OCC-001: Read-only)
# =============================================================================


class TestReadOnlyInvariant:
    """Tests that stream is read-only (INV-OCC-001)."""

    def test_no_post_on_recent(self, client):
        """POST not allowed on /events/recent."""
        response = client.post("/events/recent")
        assert response.status_code == 405

    def test_no_put_on_types(self, client):
        """PUT not allowed on /events/types."""
        response = client.put("/events/types")
        assert response.status_code == 405

    def test_no_delete_on_status(self, client):
        """DELETE not allowed on /events/stream/status."""
        response = client.delete("/events/stream/status")
        assert response.status_code == 405


# =============================================================================
# EVENT TYPE COVERAGE TESTS
# =============================================================================


class TestEventTypeCoverage:
    """Tests that all event types are properly defined."""

    def test_all_event_types_have_category(self):
        """All event types have a category (prefix before dot)."""
        for event_type in OCCEventType:
            assert "." in event_type.value

    def test_event_categories_are_valid(self):
        """Event categories match expected set."""
        expected_categories = {
            "decision",
            "proof",
            "settlement",
            "pipeline",
            "agent",
            "governance",
            "system",
            "pac",
            "wrap",
            "ber",
        }

        actual_categories = set()
        for event_type in OCCEventType:
            category = event_type.value.split(".")[0]
            actual_categories.add(category)

        # All actual categories should be expected
        for cat in actual_categories:
            assert cat in expected_categories, f"Unexpected category: {cat}"

    @pytest.mark.asyncio
    async def test_emit_all_event_types(self):
        """Can emit all event types without error."""
        for event_type in OCCEventType:
            event = await emit_occ_event(
                event_type=event_type,
                source="coverage-test",
                payload={"coverage": True},
            )
            assert event.event_type == event_type
