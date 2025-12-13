"""
Shadow Mode Database Models

Tracks parallel executions of real ML models vs dummy models
for validation and drift detection before promoting models to production.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RiskShadowEvent(Base):
    """
    Records parallel execution of dummy vs real risk models.

    Used to:
    - Track score deltas between dummy and real models
    - Detect model drift before production promotion
    - Build confidence in real model performance
    - Debug discrepancies and edge cases

    Each event captures one shipment scoring where both models ran.
    """

    __tablename__ = "risk_shadow_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """Primary key."""

    shipment_id = Column(String, index=True, nullable=False)
    """Shipment identifier for correlation."""

    dummy_score = Column(Float, nullable=False)
    """Score from DummyRiskModel (currently in production)."""

    real_score = Column(Float, nullable=False)
    """Score from RealRiskModel_v0.2 (candidate for promotion)."""

    delta = Column(Float, nullable=False)
    """Absolute difference: |dummy_score - real_score|."""

    model_version = Column(String, nullable=False)
    """Version identifier of the real model (e.g., 'v0.2.0')."""

    corridor = Column(String, nullable=True)
    """Trade corridor for segmented analysis (e.g., 'US-MX')."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    """Timestamp of scoring event."""

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<RiskShadowEvent(id={self.id}, "
            f"shipment={self.shipment_id}, "
            f"delta={self.delta:.4f}, "
            f"version={self.model_version})>"
        )
