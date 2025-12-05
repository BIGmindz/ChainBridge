"""
ChainIQ Demo Seed Script

Populates the SQLite database with realistic demo data for showcasing ChainIQ features.

Usage:
    python chainiq-service/demo_seed.py

This script creates 3-5 demo shipments with varying risk levels, complete with:
- Risk scoring history
- Payment hold queue entries
- Realistic scenarios for Better Options Advisor
- ProofPack data
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add chainiq-service to path for imports
chainiq_path = Path(__file__).parent
if str(chainiq_path) not in sys.path:
    sys.path.insert(0, str(chainiq_path))

from storage import DB_PATH, init_db  # noqa: E402


def seed_demo_shipments():
    """
    Seed demo database with 3-5 shipments across risk spectrum.

    Idempotent: Skips shipments that already exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    demo_shipments = [
        {
            "shipment_id": "DEMO-LOW-001",
            "route": "US-CA",
            "carrier_id": "CARRIER-RELIABLE-001",
            "shipment_value_usd": 15000.00,
            "days_in_transit": 3,
            "expected_days": 3,
            "documents_complete": True,
            "shipper_payment_score": 95,
            "description": "Low-risk baseline shipment (safe route, documents complete)",
        },
        {
            "shipment_id": "DEMO-MEDIUM-001",
            "route": "CN-US",
            "carrier_id": "CARRIER-STANDARD-002",
            "shipment_value_usd": 35000.00,
            "days_in_transit": 15,
            "expected_days": 14,
            "documents_complete": True,
            "shipper_payment_score": 70,
            "description": "Medium-risk shipment (minor delay, decent carrier)",
        },
        {
            "shipment_id": "DEMO-HIGH-001",
            "route": "IR-TR-EU",
            "carrier_id": "CARRIER-MODERATE-003",
            "shipment_value_usd": 75000.00,
            "days_in_transit": 12,
            "expected_days": 8,
            "documents_complete": False,
            "shipper_payment_score": 55,
            "description": "High-risk shipment (significant delay, docs incomplete)",
        },
        {
            "shipment_id": "DEMO-CRITICAL-001",
            "route": "IR-RU",
            "carrier_id": "CARRIER-RISKY-099",
            "shipment_value_usd": 120000.00,
            "days_in_transit": 25,
            "expected_days": 10,
            "documents_complete": False,
            "shipper_payment_score": 35,
            "description": "Critical-risk shipment (high-risk route, massive delay, poor docs)",
        },
        {
            "shipment_id": "DEMO-HIGH-002",
            "route": "AF-ZA",
            "carrier_id": "CARRIER-UNRELIABLE-007",
            "shipment_value_usd": 92000.00,
            "days_in_transit": 18,
            "expected_days": 12,
            "documents_complete": True,
            "shipper_payment_score": 48,
            "description": "High-risk shipment (unreliable carrier, delay, low shipper score)",
        },
    ]

    seeded_count = 0
    skipped_count = 0

    for shipment in demo_shipments:
        shipment_id = shipment["shipment_id"]

        # Check if shipment already exists
        cursor.execute("SELECT COUNT(*) FROM risk_decisions WHERE shipment_id = ?", (shipment_id,))
        exists = cursor.fetchone()[0] > 0

        if exists:
            print(f"  ⏭️  Skipping {shipment_id} (already exists)")
            skipped_count += 1
            continue

        # Calculate risk score using simple heuristic for demo
        risk_score = _calculate_demo_risk_score(shipment)
        severity = _get_severity(risk_score)
        reason_codes = _get_reason_codes(shipment)

        # Insert risk decision with history
        base_time = datetime.now() - timedelta(hours=24)

        # Insert 2-5 historical scorings to show progression
        num_history_entries = 3 if severity in ["HIGH", "CRITICAL"] else 2

        for i in range(num_history_entries):
            scored_at = base_time + timedelta(hours=i * 8)
            # Simulate score degradation over time for high-risk shipments
            historical_score = max(10, risk_score - (num_history_entries - i - 1) * 10)
            historical_severity = _get_severity(historical_score)

            request_payload = {
                "route": shipment["route"],
                "carrier_id": shipment["carrier_id"],
                "shipment_value_usd": shipment["shipment_value_usd"],
                "days_in_transit": shipment["days_in_transit"],
                "expected_days": shipment["expected_days"],
                "documents_complete": shipment["documents_complete"],
                "shipper_payment_score": shipment["shipper_payment_score"],
            }

            response_payload = {
                "shipment_id": shipment_id,
                "risk_score": historical_score,
                "severity": historical_severity,
                "recommended_action": _get_recommended_action(historical_severity),
                "reason_codes": reason_codes,
            }

            cursor.execute(
                """
                INSERT INTO risk_decisions (
                    shipment_id, risk_score, severity, recommended_action,
                    reason_codes, scored_at, request_data, response_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shipment_id,
                    historical_score,
                    historical_severity,
                    _get_recommended_action(historical_severity),
                    json.dumps(reason_codes),
                    scored_at.isoformat(),
                    json.dumps(request_payload),
                    json.dumps(response_payload),
                ),
            )

        # Note: payment_hold_queue table doesn't exist yet in schema
        # Queue entries are generated dynamically from risk_decisions
        # when /iq/queue endpoint is called

        print(f"  ✅ Seeded {shipment_id} ({severity} risk)")
        seeded_count += 1

    conn.commit()
    conn.close()

    return seeded_count, skipped_count


def _calculate_demo_risk_score(shipment: dict) -> int:
    """
    Calculate risk score using simplified heuristic for demo purposes.

    Mirrors logic from risk_engine.py but simplified.
    """
    score = 0

    # Route risk
    high_risk_routes = {"IR-RU", "IR-TR", "AF-ZA", "IR-CN"}
    medium_risk_routes = {"IR-TR-EU", "CN-US"}

    route = shipment["route"]
    if any(route.startswith(hr) for hr in high_risk_routes):
        score += 35
    elif any(route.startswith(mr) for mr in medium_risk_routes):
        score += 20
    else:
        score += 5

    # Delay risk
    delay_days = shipment["days_in_transit"] - shipment["expected_days"]
    if delay_days > 10:
        score += 30
    elif delay_days > 5:
        score += 20
    elif delay_days > 2:
        score += 10

    # Document completeness
    if not shipment["documents_complete"]:
        score += 15

    # Shipper payment score risk
    payment_score = shipment["shipper_payment_score"]
    if payment_score < 40:
        score += 25
    elif payment_score < 60:
        score += 15
    elif payment_score < 75:
        score += 5

    # Shipment value risk
    value = shipment["shipment_value_usd"]
    if value > 100000:
        score += 10
    elif value > 50000:
        score += 5

    return min(100, score)


def _get_severity(risk_score: int) -> str:
    """Map risk score to severity level."""
    if risk_score >= 80:
        return "CRITICAL"
    elif risk_score >= 60:
        return "HIGH"
    elif risk_score >= 30:
        return "MEDIUM"
    else:
        return "LOW"


def _get_recommended_action(severity: str) -> str:
    """Map severity to recommended action."""
    if severity == "CRITICAL":
        return "ESCALATE_COMPLIANCE"
    elif severity == "HIGH":
        return "HOLD_PAYMENT"
    elif severity == "MEDIUM":
        return "MANUAL_REVIEW"
    else:
        return "RELEASE_PAYMENT"


def _get_reason_codes(shipment: dict) -> list[str]:
    """Generate reason codes for demo shipment."""
    codes = []

    # Route-based codes
    route = shipment["route"]
    if "IR" in route:
        codes.append("HIGH_RISK_CORRIDOR")
    if "RU" in route:
        codes.append("SANCTIONS_ZONE")
    if "AF" in route:
        codes.append("GEOPOLITICAL_INSTABILITY")

    # Delay codes
    delay_days = shipment["days_in_transit"] - shipment["expected_days"]
    if delay_days > 10:
        codes.append("SEVERE_DELAY")
    elif delay_days > 5:
        codes.append("MODERATE_DELAY")
    elif delay_days > 0:
        codes.append("MINOR_DELAY")

    # Document codes
    if not shipment["documents_complete"]:
        codes.append("INCOMPLETE_PAPERWORK")

    # Shipper score codes
    if shipment["shipper_payment_score"] < 50:
        codes.append("POOR_SHIPPER_HISTORY")
    elif shipment["shipper_payment_score"] < 75:
        codes.append("MODERATE_SHIPPER_RISK")

    # Carrier codes
    if "RISKY" in shipment["carrier_id"] or "UNRELIABLE" in shipment["carrier_id"]:
        codes.append("UNVERIFIED_CARRIER")

    # Value codes
    if shipment["shipment_value_usd"] > 100000:
        codes.append("HIGH_VALUE_SHIPMENT")

    return codes if codes else ["STANDARD_RISK"]


def main():
    """Main entry point for demo seeding."""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🌱 ChainIQ Demo Seed Script")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # Ensure database is initialized
    print("📊 Initializing database...")
    init_db()

    print("🚢 Seeding demo shipments...")
    seeded_count, skipped_count = seed_demo_shipments()

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✨ Seeded {seeded_count} new shipments")
    if skipped_count > 0:
        print(f"⏭️  Skipped {skipped_count} existing shipments")
    print()
    print("Demo shipments ready:")
    print("  • DEMO-LOW-001: Safe baseline")
    print("  • DEMO-MEDIUM-001: Minor concerns")
    print("  • DEMO-HIGH-001: Significant delays & doc issues")
    print("  • DEMO-CRITICAL-001: Multiple red flags")
    print("  • DEMO-HIGH-002: Unreliable carrier")
    print()
    print("Test endpoints:")
    print("  curl http://localhost:8000/iq/queue")
    print("  curl http://localhost:8000/iq/history/DEMO-CRITICAL-001")
    print("  curl http://localhost:8000/iq/options/DEMO-CRITICAL-001")
    print("  curl http://localhost:8000/iq/proofpack/DEMO-CRITICAL-001")
    print()
    print("🎬 Ready for demo!")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
