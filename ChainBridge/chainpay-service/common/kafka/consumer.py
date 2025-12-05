import json
import logging
from aiokafka import AIOKafkaConsumer
from typing import Callable, Awaitable, Optional, List

logger = logging.getLogger("chainbridge.kafka.consumer")

class KafkaConsumerWrapper:
    def __init__(self, topics: List[str], bootstrap_servers: str, group_id: str, **kwargs):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._kwargs = kwargs
        self._running = False

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            **self._kwargs
        )
        await self._consumer.start()
        self._running = True
        logger.info(f"Kafka consumer started: {self.topics} @ {self.bootstrap_servers}")

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()
            self._running = False
            logger.info("Kafka consumer stopped.")

    async def consume(self, callback: Callable[[dict], Awaitable[None]]):
        if not self._consumer:
            raise RuntimeError("Consumer not started")
        try:
            async for msg in self._consumer:
                logger.info(f"Received event from topic {msg.topic}: {msg.value}")
                await callback(msg.value)
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")
        finally:
            await self.stop()
