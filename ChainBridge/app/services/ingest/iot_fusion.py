"""IoT telemetry fusion against the Golden Record."""

from __future__ import annotations

from typing import Any, Dict, List

from api.events.bus import EventType, event_bus
from app.schemas.normalized_logistics import StandardShipment
from app.services.ingest.repository import load_latest_shipment


def fuse_telemetry(shipment_id: str, iot_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare live telemetry against the planned tolerances.
    """
    plan: StandardShipment | None = load_latest_shipment(shipment_id)
    if plan is None:
        raise ValueError("shipment_not_found")

    issues: List[Dict[str, Any]] = []
    temperature = iot_data.get("temp") or iot_data.get("temperature")
    if (
        temperature is not None
        and plan.tolerances
        and plan.tolerances.max_celsius is not None
        and float(temperature) > float(plan.tolerances.max_celsius)
    ):
        issue = {
            "type": "TEMPERATURE_EXCEEDED",
            "threshold": plan.tolerances.max_celsius,
            "observed": temperature,
        }
        issues.append(issue)
        event_bus.publish(
            EventType.SHIPMENT_RISK_FLAGGED,
            {
                "shipment": plan.model_dump(),
                "telemetry": iot_data,
                "issue": issue,
            },
            correlation_id=shipment_id,
            actor="iot_fusion",
        )

    return {"shipment": plan, "telemetry": iot_data, "issues": issues}
