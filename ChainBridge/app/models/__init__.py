"""Shared ORM surface for FastAPI app consumers.

This package re-exports the ChainPay SQLAlchemy models so tests and
FastAPI endpoints can import them from `app.models` without reaching
into the hyphenated chainpay-service path directly.
"""

from chainpay_service.app.models import (  # noqa: F401
    Base,
    MilestoneSettlement,
    PaymentIntent,
    PaymentSchedule,
    PaymentScheduleItem,
    PaymentStatus,
    RiskTier,
    ScheduleType,
    SettlementLog,
)

__all__ = [
    "Base",
    "PaymentIntent",
    "PaymentStatus",
    "RiskTier",
    "ScheduleType",
    "PaymentSchedule",
    "PaymentScheduleItem",
    "MilestoneSettlement",
    "SettlementLog",
]
