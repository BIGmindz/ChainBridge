"""Payment token (PT-01) riding XRPL escrows."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, RelationValidationError, TokenValidationError


class PT01Token(BaseToken):
    """XRPL-backed escrow lifecycle."""

    TOKEN_TYPE = "PT-01"
    VERSION = "1.0"
    INITIAL_STATE = "INITIATED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "INITIATED": ["FUNDED"],
        "FUNDED": ["ESCROWED"],
        "ESCROWED": ["PARTIAL_RELEASE", "FINAL_RELEASE"],
        "PARTIAL_RELEASE": ["FINAL_RELEASE"],
        "FINAL_RELEASE": ["COMPLETE"],
        "COMPLETE": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "payment_reference": str,
        "currency": str,
        "amount": float,
        "escrow_account": str,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "xrpl_tx_hash": str,
        "memo": dict,
    }
    REQUIRED_RELATIONS = ("st01_id", "it01_id")

    def validate_state_constraints(self) -> None:
        if self.state in {"FUNDED", "ESCROWED", "PARTIAL_RELEASE", "FINAL_RELEASE", "COMPLETE"}:
            if not self.metadata.get("xrpl_tx_hash"):
                raise TokenValidationError("PT-01 funded/escrowed states require XRPL transaction hash")
        if self.state in {"PARTIAL_RELEASE", "FINAL_RELEASE", "COMPLETE"}:
            if not self.metadata.get("release_schedule"):
                raise TokenValidationError("PT-01 releases require release_schedule metadata")
        if self.state == "COMPLETE" and not self.metadata.get("completion_at"):
            raise TokenValidationError("PT-01 COMPLETE state requires completion_at timestamp")

        invoice_id = self.relations.get("it01_id")
        if not invoice_id:
            raise RelationValidationError("PT-01 must remain linked to IT-01")
