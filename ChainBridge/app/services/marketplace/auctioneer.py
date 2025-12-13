"""Marketplace auctioneer logic."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.chaindocs import Shipment
from app.models.marketplace import Listing, Bid


def _session(session: Optional[Session]) -> Session:
    return session or SessionLocal()


def create_liquidation_listing(shipment_id: str, *, session: Optional[Session] = None, start_price: float | None = None) -> Listing:
    db = _session(session)
    managed = session is None
    try:
        shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if not shipment:
            raise ValueError("shipment_not_found")
        price = start_price if start_price is not None else (shipment.collateral_value or 0.0) * 0.5
        listing = Listing(
            shipment_id=shipment_id,
            token_id=shipment.ricardian_hash or shipment_id,
            start_price=price,
            buy_now_price=price * 1.2 if price else None,
            status="ACTIVE",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing
    finally:
        if managed:
            db.close()


def place_bid(listing: Listing, amount: float, wallet: str, *, session: Optional[Session] = None) -> Bid:
    db = _session(session)
    managed = session is None
    try:
        top_bid = max((b.amount for b in listing.bids), default=listing.start_price or 0.0)
        if amount <= top_bid:
            raise ValueError("bid_too_low")
        bid = Bid(listing_id=listing.id, bidder_wallet=wallet, amount=amount)
        db.add(bid)
        db.commit()
        db.refresh(bid)
        return bid
    finally:
        if managed:
            db.close()


def execute_sale(listing: Listing, buyer_wallet: str, amount: float, *, session: Optional[Session] = None) -> Listing:
    db = _session(session)
    managed = session is None
    try:
        listing.status = "SOLD"
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing
    finally:
        if managed:
            db.close()
