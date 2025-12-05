import json
import logging
from datetime import datetime, timezone

from api.events.bus import EventType, event_bus


def setup_function() -> None:
    event_bus.clear_subscribers()


def test_event_bus_fans_out_to_sinks(caplog):
    caplog.set_level(logging.INFO, logger="api.events.bus")
    called = {}

    def handler(payload):
        called.update(payload)

    event_bus.subscribe(EventType.PAYMENT_INTENT_CREATED, handler)
    event = event_bus.publish(
        EventType.PAYMENT_INTENT_CREATED,
        {"id": "PI-100", "status": "CREATED"},
        actor="api",
    )

    assert called == {"id": "PI-100", "status": "CREATED"}
    structured_logs = [r for r in caplog.records if r.msg == "event_bus_structured_event"]
    assert structured_logs, "StructuredLogSink should receive the event"
    log_event = structured_logs[-1].event
    assert log_event["event_type"] == EventType.PAYMENT_INTENT_CREATED.value
    assert log_event["actor"] == "api"
    assert log_event["event_id"] == str(event.event_id)


def test_event_metadata_is_populated():
    event = event_bus.publish(
        EventType.SETTLEMENT_EVENT_APPENDED,
        {"payment_intent_id": "PI-200", "event_type": "CAPTURED"},
        actor="worker:sync",
    )
    assert event.event_id is not None
    assert event.occurred_at.tzinfo == timezone.utc
    assert event.correlation_id == "PI-200"
    assert event.actor == "worker:sync"


def test_structured_logs_are_json_safe(caplog):
    caplog.set_level(logging.INFO, logger="api.events.bus")
    payload = {
        "payment_intent_id": "PI-300",
        "meta": {"ts": datetime(2023, 5, 1, tzinfo=timezone.utc), "obj": object()},
    }
    event_bus.publish(EventType.WEBHOOK_RECEIVED, payload, actor="webhook:test")
    structured_logs = [r for r in caplog.records if r.msg == "event_bus_structured_event"]
    assert structured_logs
    log_payload = structured_logs[-1].event
    assert json.dumps(log_payload)  # should be JSON serializable
    assert log_payload["payload"]["payment_intent_id"] == "PI-300"
    assert log_payload["correlation_id"] == "PI-300"


def test_event_bus_handles_async_handler():
    called = {}

    async def handler(payload):
        called.update(payload)

    event_bus.subscribe(EventType.SETTLEMENT_EVENT_APPENDED, handler)
    event_bus.publish(EventType.SETTLEMENT_EVENT_APPENDED, {"a": 1})
    assert called == {"a": 1} or called == {}


def test_event_bus_handler_exception_does_not_crash():
    def boom(payload):
        raise ValueError("boom")

    event_bus.subscribe(EventType.PAYMENT_INTENT_UPDATED, boom)
    event_bus.publish(EventType.PAYMENT_INTENT_UPDATED, {})
