"""Marketplace models for ChainSalvage listings and bids."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from api.database import Base

# Drop existing tables from metadata before redefining to avoid mapper conflicts in tests
for _tbl in [
    "marketplace_listings",
    "marketplace_bids",
    "marketplace_buy_intents",
    "marketplace_settlements",
]:
    if _tbl in Base.metadata.tables:
        Base.metadata.remove(Base.metadata.tables[_tbl])


class Listing(Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (
        Index("ix_marketplace_listings_status", "status"),
        Index("ix_marketplace_listings_expires", "expires_at"),
        {"extend_existing": True},
    )

    id = Column(String, primary_key=True, default=lambda: f"LST-{uuid4()}")
    shipment_id = Column(String, ForeignKey("shipments.id"), nullable=False, index=True)
    token_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    start_price = Column(Float, nullable=False, default=0.0)
    buy_now_price = Column(Float, nullable=True)
    reserve_price = Column(Float, nullable=True)
    decay_rate_per_minute = Column(Float, nullable=True)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    bids = relationship("Bid", back_populates="listing", cascade="all, delete-orphan")


class Bid(Base):
    __tablename__ = "marketplace_bids"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=lambda: f"BID-{uuid4()}")
    listing_id = Column(String, ForeignKey("marketplace_listings.id"), nullable=False, index=True)
    bidder_wallet = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="bids")


class BuyIntent(Base):
    __tablename__ = "marketplace_buy_intents"
    __table_args__ = (
        Index("ix_marketplace_buy_intents_status", "status"),
        Index("ix_marketplace_buy_intents_listing", "listing_id"),
        {"extend_existing": True},
    )

    id = Column(String, primary_key=True, default=lambda: f"INT-{uuid4()}")
    listing_id = Column(String, ForeignKey("marketplace_listings.id"), nullable=False)
    wallet_address = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USDC")
    status = Column(String, nullable=False, default="QUEUED")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    proof_nonce = Column(String, nullable=False)
    price_proof_hash = Column(String, nullable=False)
    external_tx_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    last_transition_at = Column(DateTime, nullable=True)

    listing = relationship("Listing")
    settlement = relationship("SettlementRecord", uselist=False, back_populates="intent")


class SettlementRecord(Base):
    __tablename__ = "marketplace_settlements"
    __table_args__ = (Index("ix_marketplace_settlements_listing", "listing_id"), {"extend_existing": True})

    id = Column(String, primary_key=True, default=lambda: f"STL-{uuid4()}")
    intent_id = Column(String, ForeignKey("marketplace_buy_intents.id"), nullable=False, unique=True)
    listing_id = Column(String, nullable=False)
    wallet_address = Column(String, nullable=False)
    settlement_amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USDC")
    external_tx_id = Column(String, nullable=False)
    auction_reference = Column(String, nullable=True)
    payment_intent_id = Column(String, nullable=True)  # Reserved for Phase 7 ChainPay linkage
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    intent = relationship("BuyIntent", back_populates="settlement")
