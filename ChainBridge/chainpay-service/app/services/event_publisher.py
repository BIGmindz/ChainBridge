import os
import logging
from datetime import datetime
from common.kafka.producer import KafkaProducerWrapper
from common.events.event_base import EventBase

logger = logging.getLogger("chainbridge.chainpay.event_publisher")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
EVENT_TOPIC = os.getenv("EVENT_TOPIC", "chainbridge.events")

class EventPublisher:
    def __init__(self):
        self.producer = KafkaProducerWrapper(bootstrap_servers=KAFKA_BOOTSTRAP)
        self._started = False

    async def start(self):
        if not self._started:
            await self.producer.start()
            self._started = True

    async def stop(self):
        if self._started:
            await self.producer.stop()
            self._started = False

    async def publish_settlement_event(self, shipment_id: str, event_type: str, amount: float, trace_id: str):
        event = EventBase(
            canonical_shipment_id=shipment_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source="chainpay-service",
            payload={"amount": amount, "event_type": event_type},
            trace_id=trace_id
        )
        await self.start()
        await self.producer.send(EVENT_TOPIC, event.model_dump())
        logger.info(f"Published settlement event {event_type} for shipment {shipment_id}")
