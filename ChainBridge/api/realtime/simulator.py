# api/realtime/simulator.py
"""
Real-Time Event Simulator
==========================

Background task that publishes demo events to make the Control Tower feel alive.
Optional - can be enabled/disabled via configuration.
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Optional

from api.realtime.bus import publish_event
from core.payments.identity import (
    canonical_milestone_id,
    infer_freight_token_id,
)


_SIMULATOR_TASK: Optional[asyncio.Task] = None


async def _simulate_events():
    """
    Background loop that publishes demo events periodically.

    Simulates:
    - IoT readings from various shipments
    - Alert status changes
    - Shipment location updates
    - Payment milestone state transitions
    """
    # Track payment milestone simulation state
    payment_cycle_state = {
        "SHP-2025-027": "pending",  # Hero shipment for demo
        "cycle_count": 0,
    }

    while True:
        try:
            # Wait before publishing next event
            await asyncio.sleep(random.uniform(5.0, 15.0))

            # Pick random event type - weight payment events higher for demo
            event_type = random.choices(
                ["iot_reading", "shipment_event", "alert_updated", "payment_state_changed"],
                weights=[3, 2, 2, 4],  # Favor payment events for demo visibility
                k=1
            )[0]

            if event_type == "iot_reading":
                # Simulate IoT reading from random shipment
                shipment_id = random.choice([
                    "shp-4a2e8f3b-temp-excursion",
                    "shp-7b3c9d4e-route-delay",
                    "shp-1c5d6e2f-normal",
                ])
                await publish_event(
                    type="iot_reading",
                    source="iot",
                    key=shipment_id,
                    payload={
                        "sensor_type": random.choice(["temperature", "location", "humidity"]),
                        "value": round(random.uniform(20.0, 30.0), 1),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            elif event_type == "shipment_event":
                # Simulate shipment location update
                shipment_id = random.choice([
                    "shp-4a2e8f3b-temp-excursion",
                    "shp-7b3c9d4e-route-delay",
                    "shp-1c5d6e2f-normal",
                ])
                await publish_event(
                    type="shipment_event",
                    source="shipments",
                    key=shipment_id,
                    payload={
                        "event": "location_update",
                        "lat": round(random.uniform(35.0, 45.0), 4),
                        "lng": round(random.uniform(-120.0, -70.0), 4),
                    },
                )

            elif event_type == "alert_updated":
                # Simulate alert being updated by background process
                alert_id = random.choice([
                    "alert-temp-001",
                    "alert-route-002",
                    "alert-tamper-003",
                ])
                await publish_event(
                    type="alert_updated",
                    source="alerts",
                    key=alert_id,
                    payload={
                        "action": "auto_escalated",
                        "reason": "No response within SLA",
                    },
                )

            elif event_type == "payment_state_changed":
                # Simulate payment milestone lifecycle for hero shipment
                shipment_ref = "SHP-2025-027"

                # Cycle through states: pending → eligible → released → settled
                current_state = payment_cycle_state.get(shipment_ref, "pending")
                payment_cycle_state["cycle_count"] += 1

                # Determine next state
                if current_state == "pending":
                    new_state = "eligible"
                    event_kind = "milestone_became_eligible"
                    milestone_name = "Pickup Complete"
                    from_state = "pending"
                elif current_state == "eligible":
                    new_state = "released"
                    event_kind = "milestone_released"
                    milestone_name = "In Transit"
                    from_state = "eligible"
                elif current_state == "released":
                    new_state = "settled"
                    event_kind = "milestone_settled"
                    milestone_name = "POD Confirmed"
                    from_state = "released"
                else:  # settled → restart cycle
                    new_state = "pending"
                    event_kind = "milestone_became_eligible"
                    milestone_name = "Claim Window Closed"
                    from_state = "settled"

                # Update state for next cycle
                payment_cycle_state[shipment_ref] = new_state

                freight_token_id = infer_freight_token_id(shipment_ref)
                milestone_identifier = canonical_milestone_id(
                    shipment_ref, payment_cycle_state["cycle_count"]
                )

                await publish_event(
                    type="payment_state_changed",
                    source="payments",
                    key=shipment_ref,
                    payload={
                        "event_kind": event_kind,
                        "shipment_reference": shipment_ref,
                        "milestone_id": milestone_identifier,
                        "milestone_name": milestone_name,
                        "from_state": from_state,
                        "to_state": new_state,
                        "amount": random.choice([300.0, 700.0, 100.0]),
                        "currency": "USD",
                        "reason": "Simulated demo milestone transition",
                        "freight_token_id": freight_token_id,
                        "proofpack_hint": {
                            "milestone_id": milestone_identifier,
                            "has_proofpack": True,
                            "version": "v1-alpha",
                        },
                    },
                )

        except Exception as e:
            # Log but don't crash the simulator
            print(f"[Simulator] Error publishing event: {e}")


def start_simulator():
    """
    Start the background event simulator.
    Should be called from FastAPI startup event.
    """
    global _SIMULATOR_TASK

    if _SIMULATOR_TASK is None or _SIMULATOR_TASK.done():
        _SIMULATOR_TASK = asyncio.create_task(_simulate_events())
        print("✅ Real-time event simulator started")


def stop_simulator():
    """
    Stop the background event simulator.
    Should be called from FastAPI shutdown event.
    """
    global _SIMULATOR_TASK

    if _SIMULATOR_TASK and not _SIMULATOR_TASK.done():
        _SIMULATOR_TASK.cancel()
        print("🛑 Real-time event simulator stopped")
