import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.event_consumer import EventConsumer
from common.events.event_types import EventType
from datetime import datetime

@pytest.mark.asyncio
async def test_event_consumer_handles_risk_event():
    # Mock settlement orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.handle_risk_event = AsyncMock()

    consumer = EventConsumer(mock_orchestrator)

    # Mock event data
    event_data = {
        "canonical_shipment_id": "SHIP-001",
        "event_type": EventType.RISK_OK,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "chainiq-service",
        "payload": {"risk_score": 25, "severity": "LOW", "reasons": []},
        "trace_id": "trace-123"
    }

    await consumer._handle_event(event_data)

    mock_orchestrator.handle_risk_event.assert_called_once()
    called_event = mock_orchestrator.handle_risk_event.call_args[0][0]
    assert called_event.canonical_shipment_id == "SHIP-001"
    assert called_event.event_type == EventType.RISK_OK

@pytest.mark.asyncio
async def test_event_consumer_handles_shipment_event():
    # Mock settlement orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.handle_shipment_event = AsyncMock()

    consumer = EventConsumer(mock_orchestrator)

    # Mock event data
    event_data = {
        "canonical_shipment_id": "SHIP-001",
        "event_type": EventType.SHIPMENT_DELIVERED,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "chainiq-service",
        "payload": {"status": "delivered"},
        "trace_id": "trace-456"
    }

    await consumer._handle_event(event_data)

    mock_orchestrator.handle_shipment_event.assert_called_once()
    called_event = mock_orchestrator.handle_shipment_event.call_args[0][0]
    assert called_event.canonical_shipment_id == "SHIP-001"
    assert called_event.event_type == EventType.SHIPMENT_DELIVERED
