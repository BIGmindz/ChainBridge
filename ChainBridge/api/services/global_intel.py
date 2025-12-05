"""Global intel aggregation helpers for the Global Intel map."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from api.schemas.intel import (
    CorridorKPI,
    GlobalSnapshot,
    GlobalTotals,
    LiveShipmentPosition,
    ModeKPI,
    PortHotspot,
)

AT_RISK_LEVELS = {"HIGH", "CRITICAL"}


def _as_number(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _stp_rate(total: int, blocked: int) -> float:
    if total <= 0:
        return 0.0
    return round((total - blocked) / total, 4)


def compute_global_intel_from_positions(
    positions: Sequence[LiveShipmentPosition],
) -> GlobalSnapshot:
    """Derive KPI rollups from a list of live shipment positions."""
    now = datetime.utcnow()
    corridor_map: dict[str, list[LiveShipmentPosition]] = {}
    mode_map: dict[str, list[LiveShipmentPosition]] = {}
    port_map: dict[str, list[LiveShipmentPosition]] = {}

    for pos in positions:
        corridor = pos.corridor or pos.corridor_normalized or "UNKNOWN"
        mode = pos.mode or pos.mode_normalized or "UNKNOWN"
        key_port = (pos.dest_port_code or pos.origin_port_code or "UNKNOWN").upper()
        corridor_map.setdefault(corridor, []).append(pos)
        mode_map.setdefault(mode, []).append(pos)
        port_map.setdefault(key_port, []).append(pos)

    corridor_kpis: list[CorridorKPI] = []
    for corridor, items in corridor_map.items():
        blocked = sum(1 for i in items if (i.settlement_state or "").upper() == "BLOCKED")
        high_risk = sum(1 for i in items if (i.risk_category or "").upper() in AT_RISK_LEVELS)
        at_risk = sum(1 for i in items if (i.risk_band or (i.risk_category or "").lower()) in {"medium", "high", "critical"})
        avg_eta_delta = sum(_as_number(i.eta_delta_hours or 0.0) for i in items) / len(items) if items else 0.0
        corridor_kpis.append(
            CorridorKPI(
                corridor_id=corridor,
                corridor_name=corridor,
                stp_rate=_stp_rate(len(items), blocked),
                avg_eta_delta_minutes=round(avg_eta_delta * 60, 2),
                high_risk_shipments=high_risk,
                at_risk_shipments=at_risk,
            )
        )

    mode_kpis: list[ModeKPI] = []
    for mode, items in mode_map.items():
        blocked = sum(1 for i in items if (i.settlement_state or "").upper() == "BLOCKED")
        at_risk = sum(1 for i in items if (i.risk_band or (i.risk_category or "").lower()) in {"medium", "high", "critical"})
        avg_eta_delta = sum(_as_number(i.eta_delta_hours or 0.0) for i in items) / len(items) if items else 0.0
        mode_kpis.append(
            ModeKPI(
                mode=mode,
                stp_rate=_stp_rate(len(items), blocked),
                avg_eta_delta_minutes=round(avg_eta_delta * 60, 2),
                active_shipments=len(items),
                high_risk_shipments=at_risk,
            )
        )

    port_hotspots: list[PortHotspot] = []
    for port_code, items in port_map.items():
        if not items:
            continue
        port_name = items[0].dest_port_name or items[0].origin_port_name or "Unknown Port"
        country = None
        at_risk_shipments = sum(1 for i in items if (i.risk_band or (i.risk_category or "").lower()) in {"high", "critical"})
        congestion_index = round((len(items) / max(len(positions), 1)) * 100, 2)
        port_hotspots.append(
            PortHotspot(
                port_code=port_code,
                port_name=port_name,
                country=country,
                congestion_score=congestion_index,
                high_risk_shipments=at_risk_shipments,
                active_shipments=len(items),
            )
        )

    total_shipments = len(positions)
    blocked_shipments = sum(1 for p in positions if (p.settlement_state or "").upper() == "BLOCKED")
    settlements_in_flight = sum(1 for p in positions if (p.settlement_state or "").upper() in {"IN_PROGRESS", "PARTIALLY_PAID"})
    global_totals = GlobalTotals(
        total_shipments=total_shipments,
        active_shipments=total_shipments,
        blocked_shipments=blocked_shipments,
        settlements_in_flight=settlements_in_flight,
    )

    port_hotspots.sort(key=lambda p: (p.high_risk_shipments, p.congestion_score), reverse=True)
    corridor_kpis.sort(key=lambda c: c.corridor_id)
    mode_kpis.sort(key=lambda m: m.mode)

    return GlobalSnapshot(
        corridor_kpis=corridor_kpis,
        mode_kpis=mode_kpis,
        port_hotspots=port_hotspots[:10],
        global_totals=global_totals,
        timestamp=now,
    )
