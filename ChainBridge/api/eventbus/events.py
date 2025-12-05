"""Typed event payload stubs for the in-process bus."""

from typing import Optional, TypedDict


class PaymentIntentEvent(TypedDict):
    id: str
    status: str
    risk_level: Optional[str]
    ready_for_payment: Optional[bool]


class SettlementEventAppended(TypedDict):
    payment_intent_id: str
    event_type: str
    status: str
