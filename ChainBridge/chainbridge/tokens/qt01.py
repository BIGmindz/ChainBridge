"""Quote token (QT-01)."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, TokenValidationError


class QT01Token(BaseToken):
    """Quote lifecycle that feeds pricing into invoices."""

    TOKEN_TYPE = "QT-01"
    VERSION = "1.0"
    INITIAL_STATE = "CREATED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "CREATED": ["FROZEN"],
        "FROZEN": ["LINKED_TO_ST"],
        "LINKED_TO_ST": ["LOCKED"],
        "LOCKED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "quote_number": str,
        "valid_until": str,
        "currency": str,
        "linehaul_amount": float,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "fuel_surcharge": float,
        "accessorial_caps": dict,
    }

    def validate_state_constraints(self) -> None:
        if self.state == "LOCKED" and not self.metadata.get("locked_at"):
            raise TokenValidationError("QT-01 LOCKED state requires locked_at timestamp")
