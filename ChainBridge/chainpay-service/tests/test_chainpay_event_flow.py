import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.settlement_orchestrator import SettlementOrchestrator
from common.events.risk_event import RiskEvent
from common.events.shipment_event import ShipmentEvent
from common.events.event_types import EventType
from app.models import PaymentStatus
from datetime import datetime

@pytest.mark.asyncio
async def test_settlement_orchestrator_handles_risk_ok():
    # Mock event publisher
    mock_publisher = MagicMock()
    mock_publisher.publish_settlement_event = AsyncMock()

    orchestrator = SettlementOrchestrator(mock_publisher)

    # Mock database session
    mock_db = MagicMock()
    mock_payment_intent = MagicMock()
    mock_payment_intent.id = 1
    mock_payment_intent.amount = 1000.0
    mock_payment_intent.status = PaymentStatus.PENDING
    mock_db.query.return_value.filter.return_value.first.return_value = mock_payment_intent

    event = RiskEvent(
        canonical_shipment_id="SHIP-001",
        event_type=EventType.RISK_OK,
        timestamp=datetime.utcnow(),
        source="chainiq-service",
        payload={"risk_score": 25, "severity": "LOW", "reasons": []},
        trace_id="trace-123"
    )

    with patch('app.services.settlement_orchestrator.get_db') as mock_get_db:
        mock_get_db.return_value = iter([mock_db])
        await orchestrator.handle_risk_event(event)

    assert mock_payment_intent.status == PaymentStatus.APPROVED
    mock_publisher.publish_settlement_event.assert_called_once_with(
        "SHIP-001", "SETTLEMENT_STARTED", 1000.0, "trace-123"
    )

@pytest.mark.asyncio
async def test_settlement_orchestrator_handles_shipment_delivered():
    # Mock event publisher
    mock_publisher = MagicMock()
    mock_publisher.publish_settlement_event = AsyncMock()

    orchestrator = SettlementOrchestrator(mock_publisher)

    # Mock database session
    mock_db = MagicMock()
    mock_payment_intent = MagicMock()
    mock_payment_intent.id = 1
    mock_payment_intent.amount = 1000.0
    mock_payment_intent.freight_token_id = "SHIP-001"  # Match the shipment ID

    # Set up the query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = mock_payment_intent
    mock_query.filter.return_value = mock_filter
    mock_db.query.return_value = mock_query

    # For the milestone check, return None
    mock_milestone_query = MagicMock()
    mock_milestone_filter = MagicMock()
    mock_milestone_filter.first.return_value = None
    mock_milestone_query.filter.return_value = mock_milestone_filter
    mock_db.query.side_effect = [mock_query, mock_milestone_query]  # First call for payment intent, second for milestone

    event = ShipmentEvent(
        canonical_shipment_id="SHIP-001",
        event_type=EventType.SHIPMENT_DELIVERED,
        timestamp=datetime.utcnow(),
        source="chainiq-service",
        payload={"status": "delivered"},
        trace_id="trace-456"
    )

    with patch('app.services.settlement_orchestrator.get_db') as mock_get_db:
        mock_get_db.return_value = iter([mock_db])
        await orchestrator.handle_shipment_event(event)

    mock_publisher.publish_settlement_event.assert_called_once_with(
        "SHIP-001", "SETTLEMENT_FINALIZED", 100.0, "trace-456"  # 10% of 1000
    )
