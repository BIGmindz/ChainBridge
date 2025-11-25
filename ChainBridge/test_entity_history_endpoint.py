#!/usr/bin/env python3
"""
Demo script for the new GET /iq/history/{entity_id} endpoint.

This script demonstrates:
1. Scoring a shipment multiple times
2. Retrieving complete history for the entity
3. Analyzing risk score evolution over time
"""

import requests
from datetime import datetime

API_BASE = "http://localhost:8000"
TIMEOUT = 10  # seconds


def score_shipment(payload: dict) -> dict:
    """Score a shipment and return the response."""
    response = requests.post(f"{API_BASE}/iq/score-shipment", json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_entity_history(entity_id: str, limit: int = 100) -> dict:
    """Get scoring history for an entity."""
    response = requests.get(
        f"{API_BASE}/iq/history/{entity_id}",
        params={"limit": limit},
        timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def main():
    print("=" * 70)
    print("ChainIQ Entity History Endpoint Demo")
    print("=" * 70)
    print()

    # Shipment evolves from low-risk to high-risk over time
    shipment_id = "DEMO-EVOLUTION-001"

    scenarios = [
        {
            "name": "Day 1: Normal shipment",
            "payload": {
                "shipment_id": shipment_id,
                "route": "DE-FR",
                "carrier_id": "CARRIER-001",
                "shipment_value_usd": 10000,
                "days_in_transit": 2,
                "expected_days": 5,
                "documents_complete": True,
                "shipper_payment_score": 90
            }
        },
        {
            "name": "Day 5: Slight delay",
            "payload": {
                "shipment_id": shipment_id,
                "route": "DE-FR",
                "carrier_id": "CARRIER-001",
                "shipment_value_usd": 10000,
                "days_in_transit": 6,
                "expected_days": 5,
                "documents_complete": True,
                "shipper_payment_score": 90
            }
        },
        {
            "name": "Day 10: Significant delay + docs missing",
            "payload": {
                "shipment_id": shipment_id,
                "route": "DE-FR",
                "carrier_id": "CARRIER-001",
                "shipment_value_usd": 10000,
                "days_in_transit": 12,
                "expected_days": 5,
                "documents_complete": False,
                "shipper_payment_score": 90
            }
        }
    ]

    # Score the shipment 3 times
    print("Step 1: Scoring shipment at different stages...")
    print("-" * 70)
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        result = score_shipment(scenario['payload'])
        print(f"  Risk Score: {result['risk_score']}")
        print(f"  Severity: {result['severity']}")
        print(f"  Action: {result['recommended_action']}")

    print("\n" + "=" * 70)
    print()

    # Get complete history
    print("Step 2: Retrieving complete history for entity...")
    print("-" * 70)
    history = get_entity_history(shipment_id)

    print(f"\nEntity ID: {history['entity_id']}")
    print(f"Total Records: {history['total_records']}")
    print()

    # Display history (reverse chronological - most recent first)
    print("History (most recent first):")
    print("-" * 70)
    for i, record in enumerate(history['history'], 1):
        timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
        print(f"\n#{i} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Score: {record['score']}")
        print(f"  Severity: {record['severity']}")
        print(f"  Action: {record['recommended_action']}")
        print(f"  Reason Codes: {', '.join(record['reason_codes']) if record['reason_codes'] else 'None'}")
        print(f"  Days in Transit: {record['payload']['days_in_transit']}")
        print(f"  Documents Complete: {record['payload']['documents_complete']}")

    print("\n" + "=" * 70)
    print()

    # Analyze trend
    scores = [r['score'] for r in history['history']]
    scores_chronological = list(reversed(scores))  # Reverse to get oldest -> newest

    print("Step 3: Risk Trend Analysis")
    print("-" * 70)
    print(f"Score Progression: {' → '.join(map(str, scores_chronological))}")

    if scores_chronological[0] < scores_chronological[-1]:
        print("Trend: ⬆️  Risk INCREASED over time")
    elif scores_chronological[0] > scores_chronological[-1]:
        print("Trend: ⬇️  Risk DECREASED over time")
    else:
        print("Trend: ➡️  Risk STABLE over time")

    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Error: API server not running at http://localhost:8000")
        print("\nStart the server with:")
        print("  python api/server.py")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
