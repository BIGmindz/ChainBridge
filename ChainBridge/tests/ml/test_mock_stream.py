"""
CI-safe mock event stream generator for ChainBridge ML pipeline.
Generates synthetic IoT, shipment, risk, and settlement events.
"""

import json
import random
from datetime import datetime, timedelta
# TODO: The following import is invalid (missing module)
# from ml_engine.ingestion.writer import write_event

def generate_mock_event(event_type, shipment_id, carrier_id):
    return {
        "event_id": f"evt_{random.randint(10000,99999)}",
        "event_type": event_type,
        "timestamp": (datetime.utcnow() - timedelta(minutes=random.randint(0,1440))).isoformat(),
        "shipment_id": shipment_id,
        "carrier_id": carrier_id,
        "details": {"mock": True},
    }

def test_mock_stream():
    shipment_id = "SHIP123"
    carrier_id = "CARR456"
    event_types = ["shipment_events", "iot_events", "risk_events", "settlement_events"]
    for _ in range(50):
        event = generate_mock_event(random.choice(event_types), shipment_id, carrier_id)
        write_event(event)
    print("✓ Mock stream events written.")

if __name__ == "__main__":
    test_mock_stream()
