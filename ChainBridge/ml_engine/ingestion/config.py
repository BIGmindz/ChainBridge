"""
Config for ChainBridge ML ingestion service.
"""

KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
KAFKA_TOPICS = [
    "shipment_events",
    "iot_events",
    "risk_events",
    "settlement_events",
]
PARQUET_PATH = "../ml_engine/logs/ingestion.parquet"
POSTGRES_URI = "postgresql://user:password@localhost:5432/chainbridge_ml"

# Example event schema (should be loaded from /common/events/)
EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "event_type": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "shipment_id": {"type": "string"},
        "carrier_id": {"type": "string"},
        "details": {"type": "object"},
    },
    "required": ["event_id", "event_type", "timestamp"],
}
