"""Helpers for live shipment positions, risk, and finance overlays."""

from __future__ import annotations

import copy
import logging
import random
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.chaindocs import Shipment
from api.models.chainiq import RiskDecision
from api.models.chainpay import PaymentIntent, SettlementEvent
from api.schemas.chainboard import SettlementState
from api.services.ports import PORTS, nearest_port
from core.payments.identity import canonical_shipment_reference

DEMO_MODE = bool(settings.DEMO_MODE)
logger = logging.getLogger(__name__)


_live_cache: OrderedDict[str, tuple[float, List[Dict]]] = OrderedDict()
_snapshot_cache: OrderedDict[str, tuple[float, Dict]] = OrderedDict()
_intel_cache: OrderedDict[str, tuple[float, List[Dict]]] = OrderedDict()
_cache_limit = 4


@dataclass
class CorridorEndpoints:
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float


CORRIDOR_COORDS: Dict[str, CorridorEndpoints] = {
    "US-MX": CorridorEndpoints(29.7550, -95.3670, 19.1738, -96.1342),
    "US-EU": CorridorEndpoints(40.7128, -74.0060, 51.9244, 4.4777),
    "ASIA-US": CorridorEndpoints(31.2304, 121.4737, 33.7406, -118.2760),
}

SHIPPER_POOL = [
    "Atlas Manufacturing",
    "Nova Apparel",
    "BlueOrbit Pharma",
    "Helix Parts Co.",
]
CARRIER_POOL = ["Maersk", "Flexport", "Hapag-Lloyd", "Evergreen", "UPS Freight"]


def _demo_shipments() -> list[Shipment]:
    """Deterministic fallback shipments for demo mode."""
    return [
        Shipment(
            id="DEMO-SHIP-1",
            corridor_code="US-MX",
            mode="ocean",
            collateral_value=180000.0,
            loan_amount=126000.0,
        ),
        Shipment(
            id="DEMO-SHIP-2",
            corridor_code="US-EU",
            mode="ocean",
            collateral_value=220000.0,
            loan_amount=154000.0,
        ),
        Shipment(
            id="DEMO-SHIP-3",
            corridor_code="ASIA-US",
            mode="air",
            collateral_value=95000.0,
            loan_amount=66500.0,
        ),
    ]


def _cache_get(cache: OrderedDict, key: str, ttl_seconds: int):
    """TTL-aware LRU cache lookup."""
    entry = cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts > ttl_seconds:
        cache.pop(key, None)
        return None
    cache.move_to_end(key)
    return copy.deepcopy(value)


def _cache_set(cache: OrderedDict, key: str, value):
    cache[key] = (time.time(), copy.deepcopy(value))
    cache.move_to_end(key)
    while len(cache) > _cache_limit:
        cache.popitem(last=False)


def _progress_for_shipment(shipment_id: str) -> float:
    rnd = random.Random(shipment_id)
    return min(0.98, max(0.02, rnd.random()))


def _position_for_shipment(
    shipment: Shipment,
) -> tuple[float, float, float, float, float]:
    coords = CORRIDOR_COORDS.get(shipment.corridor_code or "", CorridorEndpoints(0.0, 0.0, 0.0, 0.0))
    progress = _progress_for_shipment(shipment.id)
    lat = coords.origin_lat + (coords.dest_lat - coords.origin_lat) * progress
    lon = coords.origin_lon + (coords.dest_lon - coords.origin_lon) * progress
    eta = datetime.utcnow() + timedelta(hours=(1 - progress) * 72)
    return lat, lon, progress, eta.timestamp(), eta


def _settlement_state(intent: Optional[PaymentIntent], paid_amount: float) -> SettlementState:
    if intent is None:
        return SettlementState.NOT_STARTED
    if intent.status and intent.status.upper() == "BLOCKED":
        return SettlementState.BLOCKED
    if paid_amount and paid_amount > 0:
        if intent.amount and paid_amount >= intent.amount:
            return SettlementState.COMPLETED
        return SettlementState.PARTIALLY_PAID
    if intent.status and intent.status.upper() in {"AUTHORIZED", "CAPTURED"}:
        return SettlementState.IN_PROGRESS
    return SettlementState.NOT_STARTED


def _latest_risk(db: Session, shipment_id: str) -> Optional[RiskDecision]:
    return db.query(RiskDecision).filter(RiskDecision.shipment_id == shipment_id).order_by(RiskDecision.decided_at.desc()).first()


def _payment_intent(db: Session, shipment_id: str) -> Optional[PaymentIntent]:
    return db.query(PaymentIntent).filter(PaymentIntent.shipment_id == shipment_id).order_by(PaymentIntent.created_at.desc()).first()


def _paid_amount(db: Session, intent_id: str | None) -> float:
    if not intent_id:
        return 0.0
    events = (
        db.query(SettlementEvent)
        .filter(
            SettlementEvent.payment_intent_id == intent_id,
            SettlementEvent.status == "SUCCESS",
        )
        .all()
    )
    return float(sum(e.amount or 0.0 for e in events))


def _shipper_for_shipment(shipment_id: str) -> str:
    rnd = random.Random(shipment_id + "-shipper")
    return SHIPPER_POOL[rnd.randint(0, len(SHIPPER_POOL) - 1)]


def _carrier_for_shipment(shipment_id: str) -> str:
    rnd = random.Random(shipment_id + "-carrier")
    return CARRIER_POOL[rnd.randint(0, len(CARRIER_POOL) - 1)]


def _eta_band(hours_remaining: float) -> str:
    if hours_remaining <= 24:
        return "0-24h"
    if hours_remaining <= 72:
        return "24-72h"
    return "72h+"


def _eta_confidence(shipment_id: str) -> str:
    cadence = random.Random(f"eta-conf-{shipment_id}").randint(0, 6)
    if cadence >= 5:
        return "high"
    if cadence >= 3:
        return "medium"
    return "low"


def _tier1_risk_score(shipment_id: str) -> float:
    """Deterministic light-weight fallback risk score (0-1)."""
    rnd = random.Random(f"tier1-{shipment_id}")
    return round(0.2 + (rnd.random() * 0.6), 3)


def _risk_level_from_score(score: float) -> str:
    if score >= 0.8:
        return "CRITICAL"
    if score >= 0.65:
        return "HIGH"
    if score >= 0.4:
        return "MEDIUM"
    return "LOW"


def live_positions(db: Session, cache_ttl_seconds: int = 10) -> List[Dict]:
    cached = _cache_get(_live_cache, "positions", cache_ttl_seconds)
    if cached is not None:
        return cached

    try:
        shipments = sorted(db.query(Shipment).all(), key=lambda s: s.id)
    except Exception:
        if DEMO_MODE:
            logger.exception(
                "live_positions_db_error_demo_mode",
                extra={"endpoint": "/chainboard/live-positions"},
            )
            shipments = []
        else:
            raise

    if not shipments:
        shipments = _demo_shipments() if DEMO_MODE else []

    positions: List[Dict] = []
    for shipment in shipments:
        lat, lon, progress, _eta_ts, eta_dt = _position_for_shipment(shipment)
        try:
            risk = _latest_risk(db, shipment.id)
        except Exception:
            risk = None
        intent = _payment_intent(db, shipment.id)
        paid_amount = _paid_amount(db, intent.id if intent else None)
        cargo_value = float(shipment.collateral_value or shipment.loan_amount or 0.0)
        financed_amount = (
            float(intent.approved_amount or intent.held_amount or intent.amount) if intent else float(shipment.loan_amount or 0.0)
        )
        state = _settlement_state(intent, paid_amount)
        port, distance_km = nearest_port(lat, lon, PORTS)
        corridor_code = (shipment.corridor_code or "UNKNOWN").upper()
        mode = (shipment.mode or "ocean").lower()

        # Tier-1 fallback risk if ChainIQ tier-2 missing/unavailable
        risk_score = float(risk.risk_score) if risk else _tier1_risk_score(shipment.id)
        risk_level = (risk.risk_level if risk else _risk_level_from_score(risk_score)).upper()

        origin_coords = CORRIDOR_COORDS.get(corridor_code, CorridorEndpoints(port.lat, port.lon, port.lat, port.lon))
        origin_port, _ = nearest_port(origin_coords.origin_lat, origin_coords.origin_lon, PORTS)
        dest_port, _ = nearest_port(origin_coords.dest_lat, origin_coords.dest_lon, PORTS)

        eta_hours_remaining = max((eta_dt - datetime.utcnow()).total_seconds() / 3600, 0.0)
        eta_delta_hours_seed = random.Random(f"eta-delta-{shipment.id}")
        eta_delta_hours = round(((eta_delta_hours_seed.randint(0, 5)) - 2) * 0.5, 2)

        positions.append(
            {
                "shipment_id": shipment.id,
                "canonical_shipment_ref": canonical_shipment_reference(shipment_reference=shipment.id),
                "corridor": corridor_code,
                "corridor_id": corridor_code,
                "corridor_name": corridor_code,
                "corridor_endpoints": {
                    "origin_lat": origin_coords.origin_lat,
                    "origin_lon": origin_coords.origin_lon,
                    "dest_lat": origin_coords.dest_lat,
                    "dest_lon": origin_coords.dest_lon,
                },
                "mode": mode,
                "lat": lat,
                "lon": lon,
                "progress_pct": round(progress * 100, 2),
                "eta": eta_dt.isoformat(),
                "eta_hours_remaining": round(eta_hours_remaining, 2),
                "eta_delta_hours": eta_delta_hours,
                "eta_band_hours": _eta_band(eta_hours_remaining),
                "eta_confidence": _eta_confidence(shipment.id),
                "geo_accuracy_km": round(max(distance_km * 0.25, 5.0), 2),
                "cargo_value_usd": cargo_value,
                "financed_amount_usd": financed_amount,
                "paid_amount_usd": paid_amount,
                "settlement_state": state,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_source": "tier2" if risk else "tier1",
                "nearest_port": port.name,
                "nearest_port_code": port.code,
                "nearest_port_country": port.country,
                "distance_to_nearest_port_km": distance_km,
                "origin_port_code": origin_port.code,
                "origin_port_name": origin_port.name,
                "dest_port_code": dest_port.code,
                "dest_port_name": dest_port.name,
                "shipper_name": _shipper_for_shipment(shipment.id),
                "carrier_name": _carrier_for_shipment(shipment.id),
            }
        )

    positions.sort(key=lambda p: p["shipment_id"])
    _cache_set(_live_cache, "positions", positions)
    return copy.deepcopy(positions)


def global_snapshot(db: Session, cache_ttl_seconds: int = 20) -> Dict:
    cached = _cache_get(_snapshot_cache, "snapshot", cache_ttl_seconds)
    if cached is not None:
        return cached

    positions = live_positions(db, cache_ttl_seconds=cache_ttl_seconds)
    total_value = sum(p["cargo_value_usd"] for p in positions)
    financed_value = sum(p["financed_amount_usd"] for p in positions)
    paid_value = sum(p["paid_amount_usd"] for p in positions)
    at_risk_value = sum(p["cargo_value_usd"] for p in positions if (p.get("risk_level") or "").lower() == "high")
    delayed_value = sum(p["cargo_value_usd"] for p in positions if p["progress_pct"] < 30)

    by_corridor_map: Dict[str, Dict] = {}
    by_mode_map: Dict[str, Dict] = {}
    port_risk: Dict[str, float] = {}

    for p in positions:
        corridor = p["corridor"]
        mode = p["mode"]
        by_corridor_map.setdefault(corridor, {"corridor": corridor, "value_usd": 0.0, "financed_usd": 0.0})
        by_corridor_map[corridor]["value_usd"] += p["cargo_value_usd"]
        by_corridor_map[corridor]["financed_usd"] += p["financed_amount_usd"]

        by_mode_map.setdefault(mode, {"mode": mode, "value_usd": 0.0, "financed_usd": 0.0})
        by_mode_map[mode]["value_usd"] += p["cargo_value_usd"]
        by_mode_map[mode]["financed_usd"] += p["financed_amount_usd"]

        port_name = p.get("nearest_port") or "Unknown"
        port_risk[port_name] = port_risk.get(port_name, 0.0) + (
            p["cargo_value_usd"] if (p.get("risk_level") or "").lower() == "high" else 0.0
        )

    snapshot = {
        "total_value_in_transit_usd": total_value,
        "financed_value_usd": financed_value,
        "unfinanced_value_usd": max(total_value - financed_value, 0.0),
        "paid_value_usd": paid_value,
        "at_risk_value_usd": at_risk_value,
        "delayed_value_usd": delayed_value,
        "by_corridor": list(by_corridor_map.values()),
        "by_mode": list(by_mode_map.values()),
        "top_ports_by_risk": sorted(
            [{"port": k, "at_risk_value_usd": v} for k, v in port_risk.items()],
            key=lambda x: x["at_risk_value_usd"],
            reverse=True,
        )[:5],
        "generated_at": datetime.utcnow().isoformat(),
    }
    _cache_set(_snapshot_cache, "snapshot", snapshot)
    return copy.deepcopy(snapshot)


def _settlement_state_ts(raw: Dict) -> str:
    paid = float(raw.get("paid_amount_usd") or 0.0)
    financed = float(raw.get("financed_amount_usd") or 0.0)
    state = str(raw.get("settlement_state") or "").lower()
    if "blocked" in state:
        return "BLOCKED"
    if state in {"in_progress", "in-progress"}:
        return "IN_PROGRESS"
    if paid > 0 and paid >= financed and financed > 0:
        return "PAID"
    if paid > 0:
        return "PARTIALLY_PAID"
    if financed > 0:
        return "FINANCED_UNPAID"
    return "UNFINANCED"


def _risk_category(raw: Dict, risk_score_norm: float) -> str:
    if raw.get("risk_level"):
        return str(raw["risk_level"]).upper()
    if risk_score_norm >= 0.75:
        return "HIGH"
    if risk_score_norm >= 0.5:
        return "MEDIUM"
    return "LOW"


def intel_positions(db: Session, cache_ttl_seconds: int = 10) -> List[Dict]:
    """
    Convert live_positions payload into the Intel Map contract used by the frontend.
    Falls back to deterministic demo data when DEMO_MODE is enabled or no rows exist.
    """
    cached = _cache_get(_intel_cache, "intel", cache_ttl_seconds)
    if cached is not None:
        return cached

    try:
        base_positions = live_positions(db, cache_ttl_seconds=cache_ttl_seconds)
    except Exception:
        if not DEMO_MODE:
            raise
        logger.exception(
            "intel_positions_live_positions_error_demo_mode",
            extra={"endpoint": "/intel/live-positions"},
        )
        base_positions = []
    now_iso = datetime.utcnow().isoformat()

    intel_list: List[Dict] = []
    for pos in base_positions:
        risk_score_raw = pos.get("risk_score")
        risk_score_norm = 0.0
        if risk_score_raw is not None:
            risk_score_norm = float(risk_score_raw)
            risk_score_norm = risk_score_norm / 100.0 if risk_score_norm > 1 else risk_score_norm
        else:
            # deterministic pseudo-random based on shipment id for demo stability
            risk_score_norm = random.Random(f"risk-norm-{pos['shipment_id']}").randint(0, 30) / 100.0

        risk_category = _risk_category(pos, risk_score_norm)
        status = "AT_RISK" if risk_category in {"HIGH", "CRITICAL"} else ("DELAYED" if pos.get("progress_pct", 100) < 30 else "ON_TIME")

        nearest_code = pos.get("nearest_port_code") or pos.get("origin_port_code") or "UNKNOWN"
        nearest_name = pos.get("nearest_port") or pos.get("origin_port_name") or "Nearest Port"

        corridor_value = pos.get("corridor") or pos.get("corridor_normalized") or "UNKNOWN"
        eta_value = pos.get("eta") or datetime.utcnow().isoformat()
        origin_code = pos.get("origin_port_code") or nearest_code
        dest_code = pos.get("dest_port_code") or nearest_code

        intel_list.append(
            {
                "shipment_id": pos["shipment_id"],
                "canonical_shipment_ref": pos.get("canonical_shipment_ref") or pos["shipment_id"],
                "external_ref": f"{pos['shipment_id']}-REF",
                "lat": pos["lat"],
                "lon": pos["lon"],
                "corridor": corridor_value,
                "corridor_endpoints": pos.get("corridor_endpoints"),
                "mode": str(pos.get("mode", "OCEAN")).upper(),
                "status": status,
                "risk_score": round(risk_score_norm, 3),
                "risk_category": risk_category,
                "risk_band": (risk_category or "unknown").lower(),
                "risk_source": pos.get("risk_source") or "tier1",
                "risk_score_raw": pos.get("risk_score"),
                "cargo_value_usd": float(pos.get("cargo_value_usd") or 0.0),
                "financed_amount_usd": float(pos.get("financed_amount_usd") or 0.0),
                "paid_amount_usd": float(pos.get("paid_amount_usd") or 0.0),
                "settlement_state": _settlement_state_ts(pos),
                "stake_apr": round(3.0 + (risk_score_norm * 4), 2),
                "stake_capacity_usd": max(float(pos.get("cargo_value_usd") or 0.0) * 0.5, 0.0),
                "origin_port_code": origin_code,
                "origin_port_name": pos.get("origin_port_name") or nearest_name,
                "dest_port_code": dest_code,
                "dest_port_name": pos.get("dest_port_name") or nearest_name,
                "distance_to_nearest_port_km": pos.get("distance_to_nearest_port_km"),
                "eta": eta_value,
                "eta_band_hours": pos.get("eta_band_hours"),
                "eta_confidence": pos.get("eta_confidence"),
                "eta_delta_hours": pos.get("eta_delta_hours"),
                "geo_accuracy_km": pos.get("geo_accuracy_km"),
                "corridor_normalized": pos.get("corridor") or corridor_value,
                "mode_normalized": pos.get("mode"),
                "shipper_name": pos.get("shipper_name"),
                "carrier_name": pos.get("carrier_name"),
                "last_event_code": "POSITION_UPDATE",
                "last_event_ts": now_iso,
            }
        )

    # Ensure demo mode never returns empty set for UI
    if not intel_list and DEMO_MODE:
        intel_list = [
            {
                "shipment_id": "DEMO-GLOBAL-1",
                "canonical_shipment_ref": "DEMO-GLOBAL-1",
                "external_ref": "DEMO-001",
                "lat": 33.7406,
                "lon": -118.2760,
                "corridor": "US-MX",
                "mode": "OCEAN",
                "status": "ON_TIME",
                "risk_score": 0.18,
                "risk_category": "LOW",
                "risk_band": "low",
                "cargo_value_usd": 180000.0,
                "financed_amount_usd": 126000.0,
                "paid_amount_usd": 54000.0,
                "settlement_state": "PARTIALLY_PAID",
                "stake_apr": 3.2,
                "stake_capacity_usd": 95000.0,
                "origin_port_code": "USLAX",
                "origin_port_name": "Los Angeles",
                "dest_port_code": "MXVER",
                "dest_port_name": "Veracruz",
                "distance_to_nearest_port_km": 45.0,
                "eta": now_iso,
                "last_event_code": "DEPARTED_PORT",
                "last_event_ts": now_iso,
                "eta_band_hours": "24-72h",
                "eta_confidence": "high",
            },
            {
                "shipment_id": "DEMO-GLOBAL-2",
                "canonical_shipment_ref": "DEMO-GLOBAL-2",
                "external_ref": "DEMO-002",
                "lat": 51.9244,
                "lon": 4.4777,
                "corridor": "EU-US",
                "mode": "OCEAN",
                "status": "AT_RISK",
                "risk_score": 0.82,
                "risk_category": "HIGH",
                "risk_band": "high",
                "cargo_value_usd": 220000.0,
                "financed_amount_usd": 154000.0,
                "paid_amount_usd": 0.0,
                "settlement_state": "FINANCED_UNPAID",
                "stake_apr": 4.4,
                "stake_capacity_usd": 180000.0,
                "origin_port_code": "NLRDM",
                "origin_port_name": "Rotterdam",
                "dest_port_code": "USNYC",
                "dest_port_name": "New York",
                "distance_to_nearest_port_km": 2.0,
                "eta": now_iso,
                "last_event_code": "TEMP_BREACH",
                "last_event_ts": now_iso,
                "eta_band_hours": "24-72h",
                "eta_confidence": "medium",
            },
        ]

    _cache_set(_intel_cache, "intel", intel_list)
    return copy.deepcopy(intel_list)
