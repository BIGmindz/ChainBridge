import json
import logging
from aiokafka import AIOKafkaProducer
from typing import Any, Dict, Optional

logger = logging.getLogger("chainbridge.kafka.producer")

class KafkaProducerWrapper:
    def __init__(self, bootstrap_servers: str, retries: int = 3, **kwargs):
        self.bootstrap_servers = bootstrap_servers
        self.retries = retries
        self._producer: Optional[AIOKafkaProducer] = None
        self._kwargs = kwargs

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            **self._kwargs
        )
        await self._producer.start()
        logger.info(f"Kafka producer started: {self.bootstrap_servers}")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped.")

    async def send(self, topic: str, value: Dict[str, Any], key: Optional[str] = None):
        if not self._producer:
            raise RuntimeError("Producer not started")
        attempt = 0
        while attempt < self.retries:
            try:
                await self._producer.send_and_wait(topic, value, key=key.encode() if key else None)
                logger.info(f"Event sent to topic {topic}: {value}")
                return
            except Exception as e:
                logger.error(f"Kafka send failed (attempt {attempt+1}): {e}")
                attempt += 1
        raise RuntimeError(f"Failed to send event to Kafka after {self.retries} attempts.")
