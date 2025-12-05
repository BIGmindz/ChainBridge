"""Data models for reconciliation engine and micro-settlement outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ReconciliationLineStatus(str, Enum):
    MATCHED = "MATCHED"
    UNDER_DELIVERED = "UNDER_DELIVERED"
    OVER_DELIVERED = "OVER_DELIVERED"
    PRICE_DELTA = "PRICE_DELTA"
    QUALITY_VIOLATION = "QUALITY_VIOLATION"


class ReconciliationDecision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    PARTIAL_APPROVE = "PARTIAL_APPROVE"
    BLOCK = "BLOCK"


@dataclass
class PoLine:
    line_id: str
    sku: str | None = None
    quantity: float | None = None
    unit_price: float | None = None


@dataclass
class ExecLine:
    line_id: str
    quantity: float | None = None
    unit_price: float | None = None


@dataclass
class InvoiceLine:
    line_id: str
    quantity: float | None = None
    unit_price: float | None = None


@dataclass
class ReconciliationLineResult:
    line_id: str
    status: ReconciliationLineStatus
    reason_code: str
    contract_amount: float
    billed_amount: float
    approved_amount: float
    held_amount: float
    flags: List[str] = field(default_factory=list)


@dataclass
class ReconciliationBundle:
    payment_intent_id: str
    po_lines: List[PoLine]
    exec_lines: List[ExecLine]
    invoice_lines: List[InvoiceLine]
    policy: "ReconciliationPolicy"
    amount_currency: str
    total_billed_amount: float
    temp_excursion_minutes: int = 0


@dataclass
class ReconciliationResult:
    decision: ReconciliationDecision
    approved_amount: float
    held_amount: float
    recon_score: float
    policy_id: str
    flags: List[str]
    lines: List[ReconciliationLineResult]


# Forward declaration type hint
class ReconciliationPolicy:  # pragma: no cover - only used for typing
    ...
