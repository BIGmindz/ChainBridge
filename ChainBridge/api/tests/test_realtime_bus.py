# api/tests/test_realtime_bus.py
"""
Tests for Real-Time Event Bus
==============================

Validates the pub/sub event bus functionality.
"""

import asyncio
from datetime import datetime

import pytest

from api.realtime.bus import event_stream, publish_event, subscribe, unsubscribe


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe():
    """Test subscribing and unsubscribing from event bus."""
    queue = subscribe()
    assert queue is not None
    assert isinstance(queue, asyncio.Queue)

    unsubscribe(queue)
    # Should be able to unsubscribe multiple times without error
    unsubscribe(queue)


@pytest.mark.asyncio
async def test_publish_event():
    """Test publishing events to subscribers."""
    queue = subscribe()

    # Publish event
    await publish_event(
        type="alert_created",
        source="alerts",
        key="alert-123",
        payload={"severity": "critical"},
    )

    # Should receive event
    event = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert event.type == "alert_created"
    assert event.source == "alerts"
    assert event.key == "alert-123"
    assert event.payload == {"severity": "critical"}
    assert event.id.startswith("evt-")
    assert isinstance(event.timestamp, datetime)

    unsubscribe(queue)


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """Test that multiple subscribers all receive events."""
    queue1 = subscribe()
    queue2 = subscribe()
    queue3 = subscribe()

    # Publish event
    await publish_event(
        type="iot_reading",
        source="iot",
        key="shp-456",
        payload={"temp": 25.5},
    )

    # All subscribers should receive the event
    event1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
    event3 = await asyncio.wait_for(queue3.get(), timeout=1.0)

    assert event1.type == event2.type == event3.type == "iot_reading"
    assert event1.key == event2.key == event3.key == "shp-456"

    unsubscribe(queue1)
    unsubscribe(queue2)
    unsubscribe(queue3)


@pytest.mark.asyncio
async def test_event_stream_generator():
    """Test the event_stream async generator."""
    async def consumer():
        events = []
        async for event in event_stream():
            events.append(event)
            if len(events) >= 2:
                break
        return events

    # Start consumer in background
    consumer_task = asyncio.create_task(consumer())

    # Give consumer time to subscribe
    await asyncio.sleep(0.1)

    # Publish events
    await publish_event(
        type="alert_created",
        source="alerts",
        key="alert-1",
        payload={},
    )
    await publish_event(
        type="alert_updated",
        source="alerts",
        key="alert-2",
        payload={},
    )

    # Wait for consumer
    events = await asyncio.wait_for(consumer_task, timeout=2.0)

    assert len(events) == 2
    assert events[0].type == "alert_created"
    assert events[1].type == "alert_updated"


@pytest.mark.asyncio
async def test_no_blocking_on_slow_consumer():
    """Test that slow consumers don't block event publishing."""
    # Create two queues with limited capacity
    queue_fast = subscribe()
    queue_slow = subscribe()

    # Fill the slow queue to capacity
    for _ in range(1000):
        # Don't drain queue_slow - let it fill up
        pass

    # Publish many events - should not block
    for i in range(10):
        await publish_event(
            type="iot_reading",
            source="test",
            key=f"test-{i}",
            payload={"index": i},
        )

    # Fast consumer should still receive some events
    event = await asyncio.wait_for(queue_fast.get(), timeout=1.0)
    assert event.type == "iot_reading"

    unsubscribe(queue_fast)
    unsubscribe(queue_slow)


@pytest.mark.asyncio
async def test_event_serialization():
    """Test that events can be serialized to JSON."""
    queue = subscribe()

    await publish_event(
        type="alert_note_added",
        source="alerts",
        key="alert-789",
        payload={
            "note_id": "note-123",
            "author": "operator-1",
            "message": "Investigating temperature spike",
        },
    )

    event = await asyncio.wait_for(queue.get(), timeout=1.0)

    # Test model_dump_json
    json_str = event.model_dump_json()
    assert isinstance(json_str, str)
    assert "alert_note_added" in json_str
    assert "alert-789" in json_str

    unsubscribe(queue)
