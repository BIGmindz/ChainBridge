import os
import logging
import asyncio
from typing import Dict, Any
from common.kafka.consumer import KafkaConsumerWrapper
from common.events.risk_event import RiskEvent
from common.events.shipment_event import ShipmentEvent
from common.events.event_types import EventType

logger = logging.getLogger("chainbridge.chainpay.event_consumer")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
EVENT_TOPICS = ["chainbridge.events"]

class EventConsumer:
    def __init__(self, settlement_orchestrator):
        self.consumer = KafkaConsumerWrapper(
            topics=EVENT_TOPICS,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="chainpay-settlement"
        )
        self.settlement_orchestrator = settlement_orchestrator
        self._running = False

    async def start(self):
        if not self._running:
            await self.consumer.start()
            self._running = True
            asyncio.create_task(self._consume_loop())
            logger.info("ChainPay event consumer started")

    async def stop(self):
        if self._running:
            await self.consumer.stop()
            self._running = False

    async def _consume_loop(self):
        try:
            await self.consumer.consume(self._handle_event)
        except Exception as e:
            logger.error(f"Event consumer error: {e}")

    async def _handle_event(self, event_data: Dict[str, Any]):
        try:
            event_type = event_data.get("event_type")
            if event_type == EventType.RISK_OK or event_type == EventType.RISK_FAIL:
                event = RiskEvent(**event_data)
                await self.settlement_orchestrator.handle_risk_event(event)
            elif event_type == EventType.SHIPMENT_UPDATE or event_type == EventType.SHIPMENT_DELIVERED:
                event = ShipmentEvent(**event_data)
                await self.settlement_orchestrator.handle_shipment_event(event)
            else:
                logger.info(f"Ignored event type: {event_type}")
        except Exception as e:
            logger.error(f"Failed to handle event: {e}")
