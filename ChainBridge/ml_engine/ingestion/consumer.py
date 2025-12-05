"""
Async Kafka consumer for ChainBridge event ingestion.
Subscribes to canonical topics, validates schemas, normalizes timestamps, and dispatches to writer.
"""

import asyncio
from aiokafka import AIOKafkaConsumer
from .schemas import validate_event_schema
from .writer import write_event
from .config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPICS
import logging

logger = logging.getLogger("maggie.ingestion.consumer")

async def consume_events():
    consumer = AIOKafkaConsumer(
        *KAFKA_TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: m.decode("utf-8"),
        enable_auto_commit=True,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = validate_event_schema(msg.value)
            if event:
                write_event(event)
            else:
                logger.warning(f"Schema validation failed: {msg.value}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume_events())
