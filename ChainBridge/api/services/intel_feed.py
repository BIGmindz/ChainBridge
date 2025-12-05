"""OC-ready intel feed aggregator combining snapshot, positions, risk, and settlement rollups."""

from __future__ import annotations

import copy
import time
from collections import OrderedDict
from typing import Dict, List

from sqlalchemy.orm import Session

from api.schemas.intel import (
    LivePositionsMeta,
    LiveShipmentPosition,
    OCIntelFeedResponse,
    OCQueueCardMeta,
)
from api.services.global_intel import compute_global_intel_from_positions
from api.services.live_positions import intel_positions

FEED_CACHE_TTL_SECONDS = 10
_feed_cache: OrderedDict[str, tuple[float, Dict]] = OrderedDict()
_cache_limit = 4


def _cache_get(key: str, ttl: int):
    entry = _feed_cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts > ttl:
        _feed_cache.pop(key, None)
        return None
    _feed_cache.move_to_end(key)
    return copy.deepcopy(value)


def _cache_set(key: str, value):
    _feed_cache[key] = (time.time(), copy.deepcopy(value))
    _feed_cache.move_to_end(key)
    while len(_feed_cache) > _cache_limit:
        _feed_cache.popitem(last=False)


def _build_queue_cards(positions: List[LiveShipmentPosition]) -> List[OCQueueCardMeta]:
    cards: List[OCQueueCardMeta] = []
    for pos in positions:
        cards.append(
            OCQueueCardMeta(
                shipment_id=pos.shipment_id,
                corridor_id=pos.corridor or pos.corridor_normalized or "",
                mode=pos.mode,
                risk_band=(pos.risk_band or (pos.risk_category or "")).lower(),
                settlement_state=pos.settlement_state,
                eta_iso=pos.eta,
                nearest_port=pos.dest_port_code or pos.origin_port_code,
            )
        )
    return cards


def build_oc_feed(db: Session, cache_ttl_seconds: int = FEED_CACHE_TTL_SECONDS) -> Dict:
    cached = _cache_get("oc_feed", cache_ttl_seconds)
    if cached is not None:
        return cached

    raw_positions = intel_positions(db, cache_ttl_seconds=cache_ttl_seconds)
    positions = [LiveShipmentPosition.model_validate(p) for p in raw_positions]

    snapshot = compute_global_intel_from_positions(positions)
    queue_cards = _build_queue_cards(positions)
    corridors_covered = len({p.corridor or p.corridor_normalized for p in positions})
    ports_covered = len({p.dest_port_code or p.origin_port_code for p in positions if (p.dest_port_code or p.origin_port_code)})
    meta = LivePositionsMeta(
        active_shipments=len(positions),
        corridors_covered=corridors_covered,
        ports_covered=ports_covered,
    )

    response = OCIntelFeedResponse(
        queue_cards=queue_cards,
        global_snapshot=snapshot,
        live_positions_meta=meta,
    ).model_dump(by_alias=True)

    _cache_set("oc_feed", response)
    return copy.deepcopy(response)
