import pytest
from kafka import KafkaAdminClient, KafkaProducer, KafkaConsumer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError


@pytest.fixture(scope="session")
def kafka_broker():
    """Kafka broker address for CI harness."""
    return "localhost:29092"


@pytest.fixture(scope="session")
def kafka_admin(kafka_broker):
    """Kafka admin client for topic management."""
    admin = KafkaAdminClient(bootstrap_servers=kafka_broker)
    yield admin
    admin.close()


@pytest.fixture(scope="function", autouse=True)
def kafka_topics(kafka_admin):
    """Ensure test topics exist and clean them between tests."""
    topics = ["risk.events", "shipment.events", "settlement.events"]
    existing_topics = set(kafka_admin.list_topics())

    # Create topics if they don't exist
    to_create = []
    for topic in topics:
        if topic not in existing_topics:
            to_create.append(NewTopic(name=topic, num_partitions=1, replication_factor=1))

    if to_create:
        try:
            kafka_admin.create_topics(to_create)
        except TopicAlreadyExistsError:
            pass  # Race condition, but ok

    # Purge existing messages by deleting and recreating topics
    # Note: In production, use proper purging, but for CI this works
    kafka_admin.delete_topics(topics)
    kafka_admin.create_topics([
        NewTopic(name=topic, num_partitions=1, replication_factor=1) for topic in topics
    ])

    yield topics


@pytest.fixture(scope="function")
def kafka_producer(kafka_broker):
    """Kafka producer for tests."""
    producer = KafkaProducer(
        bootstrap_servers=kafka_broker,
        value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v
    )
    yield producer
    producer.close()


@pytest.fixture(scope="function")
def kafka_consumer(kafka_broker, kafka_topics):
    """Kafka consumer for tests."""
    consumer = KafkaConsumer(
        *kafka_topics,
        bootstrap_servers=kafka_broker,
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        group_id='test-group',
        value_deserializer=lambda v: v.decode('utf-8') if isinstance(v, bytes) else v
    )
    yield consumer
    consumer.close()
