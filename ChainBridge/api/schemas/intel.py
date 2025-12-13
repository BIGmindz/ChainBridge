"""Intel and snapshot schemas aligned with front-end expectations."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    """Base model enforcing snake_case in code and camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class CorridorEndpoints(CamelModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float


class LiveShipmentPosition(CamelModel):
    shipment_id: str
    canonical_shipment_ref: str
    external_ref: Optional[str] = None
    lat: float
    lon: float
    corridor: str
    corridor_id: Optional[str] = None
    corridor_name: Optional[str] = None
    corridor_endpoints: Optional[CorridorEndpoints] = None
    corridor_normalized: Optional[str] = None
    mode: str
    mode_normalized: Optional[str] = None
    status: str  # ON_TIME | DELAYED | AT_RISK
    risk_score: float  # 0..1
    risk_score_raw: Optional[float] = None
    risk_category: Optional[str] = None
    risk_band: Optional[str] = None
    risk_source: Optional[str] = None

    cargo_value_usd: float
    financed_amount_usd: float
    paid_amount_usd: float
    settlement_state: str  # UNFINANCED | FINANCED_UNPAID | PARTIALLY_PAID | PAID
    stake_apr: Optional[float] = None
    stake_capacity_usd: Optional[float] = None

    origin_port_code: Optional[str] = None
    origin_port_name: Optional[str] = None
    dest_port_code: Optional[str] = None
    dest_port_name: Optional[str] = None
    distance_to_nearest_port_km: Optional[float] = None
    eta: Optional[str] = None
    eta_band_hours: Optional[str] = None
    eta_confidence: Optional[str] = None
    eta_delta_hours: Optional[float] = None
    geo_accuracy_km: Optional[float] = None
    shipper_name: Optional[str] = None
    carrier_name: Optional[str] = None

    last_event_code: str
    last_event_ts: str


class CorridorKPI(CamelModel):
    corridor_id: str
    corridor_name: str
    stp_rate: float
    avg_eta_delta_minutes: float
    high_risk_shipments: int
    at_risk_shipments: int


class ModeKPI(CamelModel):
    mode: str
    stp_rate: float
    avg_eta_delta_minutes: float
    active_shipments: int
    high_risk_shipments: int


class PortHotspot(CamelModel):
    port_code: str
    port_name: str
    country: Optional[str] = None
    congestion_score: float
    high_risk_shipments: int
    active_shipments: int


class GlobalTotals(CamelModel):
    total_shipments: int
    active_shipments: int
    blocked_shipments: int
    settlements_in_flight: int


class GlobalSnapshot(CamelModel):
    corridor_kpis: List[CorridorKPI]
    mode_kpis: List[ModeKPI]
    port_hotspots: List[PortHotspot]
    global_totals: GlobalTotals
    timestamp: datetime


class OCQueueCardMeta(CamelModel):
    shipment_id: str
    corridor_id: str
    mode: str
    risk_band: str
    settlement_state: str
    eta_iso: Optional[datetime] = None
    nearest_port: Optional[str] = None


class LivePositionsMeta(CamelModel):
    active_shipments: int = Field(ge=0)
    corridors_covered: int = Field(ge=0)
    ports_covered: int = Field(ge=0)


class OCIntelFeedResponse(CamelModel):
    global_snapshot: GlobalSnapshot
    queue_cards: List[OCQueueCardMeta]
    live_positions_meta: LivePositionsMeta
