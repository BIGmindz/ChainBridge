"""
Database models for ChainFreight Service.

This module contains SQLAlchemy models for shipment lifecycle and execution,
including tokenized freight representation.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, func, Enum, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class ShipmentStatus(str, enum.Enum):
    """Enumeration of shipment statuses."""
    PLANNED = "planned"
    PENDING = "pending"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ShipmentEventType(str, enum.Enum):
    """Enumeration of shipment event types."""
    CREATED = "created"
    PICKUP_CONFIRMED = "pickup_confirmed"
    IN_TRANSIT = "in_transit"
    AT_TERMINAL = "at_terminal"
    DELIVERY_ATTEMPTED = "delivery_attempted"
    POD_CONFIRMED = "pod_confirmed"
    CLAIM_WINDOW_CLOSED = "claim_window_closed"


class FreightTokenStatus(str, enum.Enum):
    """Enumeration of freight token statuses."""
    CREATED = "created"
    ACTIVE = "active"
    LOCKED = "locked"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Shipment(Base):
    """
    Shipment model for tracking shipment lifecycle in the supply chain.
    
    This model tracks shipment details from pickup through delivery,
    including planning, execution, and delivery information.
    Can be tokenized into tradeable freight tokens.
    """
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipper_name = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    cargo_value = Column(Float, nullable=True)
    pickup_date = Column(DateTime, nullable=True)
    planned_delivery_date = Column(DateTime, nullable=True)
    actual_delivery_date = Column(DateTime, nullable=True)
    pickup_eta = Column(DateTime, nullable=True)
    delivery_eta = Column(DateTime, nullable=True)
    status = Column(
        Enum(ShipmentStatus),
        default=ShipmentStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Relationship to freight tokens
    freight_tokens = relationship("FreightToken", back_populates="shipment")
    
    # Tracking and audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Shipment(id={self.id}, from={self.origin}, to={self.destination}, status={self.status})>"


class FreightToken(Base):
    """
    Freight token representing a tradeable claim on a shipment's cargo value.
    
    Enables fractionalized ownership and trading of freight assets.
    Each token is backed by a specific shipment and can be traded on-chain.
    Risk scoring is computed at tokenization time via ChainIQ service.
    """
    __tablename__ = "freight_tokens"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    face_value = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    status = Column(
        Enum(FreightTokenStatus),
        default=FreightTokenStatus.CREATED,
        nullable=False,
        index=True
    )
    token_address = Column(String, nullable=True, comment="On-chain token address")
    
    # Risk scoring from ChainIQ
    risk_score = Column(Float, nullable=True, comment="Risk score from ChainIQ (0.0-1.0)")
    risk_category = Column(String, nullable=True, comment="Risk category: low, medium, high")
    recommended_action = Column(String, nullable=True, comment="Recommended action from ChainIQ scoring")
    
    # Relationship to shipment
    shipment = relationship("Shipment", back_populates="freight_tokens")
    
    # Tracking and audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<FreightToken(id={self.id}, shipment_id={self.shipment_id}, value={self.face_value} {self.currency}, status={self.status})>"


class ShipmentEvent(Base):
    """
    Event record for significant milestones in shipment lifecycle.
    
    Tracks events like pickup confirmation, proof of delivery, claim window closure.
    Each event can trigger milestone-based payments via ChainPay webhook.
    """
    __tablename__ = "shipment_events"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    event_type = Column(
        Enum(ShipmentEventType),
        nullable=False,
        index=True,
        comment="Type of shipment event (pickup_confirmed, pod_confirmed, etc.)"
    )
    occurred_at = Column(
        DateTime,
        nullable=False,
        comment="When the event actually occurred (set by client)"
    )
    metadata = Column(
        String(500),
        nullable=True,
        comment="Additional context (JSON-like string, e.g., proof hash, signature)"
    )
    
    # Relationship to shipment
    shipment = relationship("Shipment", backref="events")
    
    # Tracking
    recorded_at = Column(DateTime, server_default=func.now(), nullable=False)
    webhook_sent = Column(Integer, default=0, nullable=False, comment="1 if sent to ChainPay, 0 otherwise")
    webhook_sent_at = Column(DateTime, nullable=True, comment="When webhook was sent to ChainPay")

    def __repr__(self):
        return f"<ShipmentEvent(id={self.id}, shipment_id={self.shipment_id}, event_type={self.event_type}, occurred_at={self.occurred_at})>"

