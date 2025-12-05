import os
import logging
from common.kafka.producer import KafkaProducerWrapper

try:  # Prefer fully qualified package when running inside the monorepo
    from ChainBridge.common.events.risk_event import RiskEvent
    from ChainBridge.common.events.shipment_event import ShipmentEvent
    from ChainBridge.common.events.event_types import EventType
except ModuleNotFoundError:  # pragma: no cover - fallback for service-level tests
    from common.events.risk_event import RiskEvent
    from common.events.shipment_event import ShipmentEvent

logger = logging.getLogger("chainbridge.chainiq.event_publisher")

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

    async def publish_risk_event(self, event: RiskEvent):
        await self.start()
        await self.producer.send(EVENT_TOPIC, event.model_dump())

    async def publish_shipment_event(self, event: ShipmentEvent):
        await self.start()
        await self.producer.send(EVENT_TOPIC, event.model_dump())
