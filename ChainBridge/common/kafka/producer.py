import json
import logging
from typing import Any, Dict, Optional

try:
    from aiokafka import AIOKafkaProducer
except ImportError:  # pragma: no cover - optional dependency
    AIOKafkaProducer = None


logger = logging.getLogger("chainbridge.kafka.producer")


class _NoopProducer:
    """Fallback producer used when aiokafka is unavailable."""

    async def start(self):
        return None

    async def stop(self):
        return None

    async def send_and_wait(self, topic: str, value: Dict[str, Any], key: Optional[bytes] = None):
        logger.debug("Noop Kafka producer drop: topic=%s value=%s", topic, value)
        return None

class KafkaProducerWrapper:
    def __init__(self, bootstrap_servers: str, retries: int = 3, **kwargs):
        self.bootstrap_servers = bootstrap_servers
        self.retries = retries
        self._producer: Optional[AIOKafkaProducer] = None
        self._kwargs = kwargs
        self._noop_mode = False

    async def start(self):
        if AIOKafkaProducer is None:
            logger.warning(
                "aiokafka not installed; KafkaProducerWrapper is running in noop mode"
            )
            self._producer = _NoopProducer()
            self._noop_mode = True
        else:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                **self._kwargs
            )
            self._noop_mode = False

        await self._producer.start()
        if not self._noop_mode:
            logger.info(f"Kafka producer started: {self.bootstrap_servers}")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            if not self._noop_mode:
                logger.info("Kafka producer stopped.")

    async def send(self, topic: str, value: Dict[str, Any], key: Optional[str] = None):
        if not self._producer:
            raise RuntimeError("Producer not started")
        attempt = 0
        while attempt < self.retries:
            try:
                await self._producer.send_and_wait(topic, value, key=key.encode() if key else None)
                if not self._noop_mode:
                    logger.info(f"Event sent to topic {topic}: {value}")
                return
            except Exception as e:
                logger.error(f"Kafka send failed (attempt {attempt+1}): {e}")
                attempt += 1
        raise RuntimeError(f"Failed to send event to Kafka after {self.retries} attempts.")
