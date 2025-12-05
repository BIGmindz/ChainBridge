"""Carrier Claim Token (CCT-01)."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, RelationValidationError, TokenValidationError


class CCT01Token(BaseToken):
    """Carrier-facing reconciliation record for unproven accessorials."""

    TOKEN_TYPE = "CCT-01"
    VERSION = "1.0"
    INITIAL_STATE = "CREATED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "CREATED": ["CARRIER_SUBMITTED"],
        "CARRIER_SUBMITTED": ["BROKER_REVIEW"],
        "BROKER_REVIEW": ["RECONCILED"],
        "RECONCILED": ["CLOSED"],
        "CLOSED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "carrier_id": str,
        "period_start": str,
        "period_end": str,
        "currency": str,
        "amount": float,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "notes": str,
        "exception_reason": str,
    }
    REQUIRED_RELATIONS = ("st01_id", "at02_ids")

    def validate_state_constraints(self) -> None:
        if not isinstance(self.relations.get("at02_ids"), list):
            raise RelationValidationError("CCT-01 must track AT-02 linkage list")
        if self.state == "CLOSED" and not self.metadata.get("closed_at"):
            raise TokenValidationError("CCT-01 CLOSED state requires closed_at timestamp")
