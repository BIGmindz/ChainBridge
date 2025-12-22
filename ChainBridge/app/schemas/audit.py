"""Audit schemas for fuzzy reconciliation."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AuditVector(BaseModel):
    delta_temp_c: float = Field(..., description="Temperature deviation in Celsius")
    duration_mins: float = Field(..., description="Duration of deviation in minutes")
    invoice_amount: float = Field(..., description="Invoice amount in USD")


class ReconciliationResult(BaseModel):
    confidence_score: float
    final_payout: float
    adjustment_reason: str
    status: str
