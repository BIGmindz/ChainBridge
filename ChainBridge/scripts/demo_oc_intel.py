from __future__ import annotations

import json
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8001"  # align with api.server.py


def pretty_print_snapshot(data: dict[str, Any]) -> None:
    meta = data.get("livePositionsMeta", {})
    queue_cards = data.get("queueCards", [])[:5]

    print("=== CHAINBRIDGE OC SNAPSHOT ===")
    print(f"Active Shipments : {meta.get('activeShipments', 0)}")
    print(f"Corridors Covered: {meta.get('corridorsCovered', 0)}")
    print(f"Ports Covered    : {meta.get('portsCovered', 0)}")
    print()

    print("Top Queue Cards:")
    if not queue_cards:
        print("  (none)")
        return

    for card in queue_cards:
        sid = card.get("shipmentId")
        corridor = card.get("corridorId")
        risk = card.get("riskBand")
        eta = card.get("etaIso")
        port = card.get("nearestPort")
        print(f"  - {sid} | corridor={corridor} | risk={risk} | eta={eta} | port={port}")


def main() -> None:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{BASE_URL}/intel/global-snapshot")
        resp.raise_for_status()
        data = resp.json()

    # Uncomment for raw payload inspection:
    # print(json.dumps(data, indent=2))

    pretty_print_snapshot(data)


if __name__ == "__main__":
    main()
