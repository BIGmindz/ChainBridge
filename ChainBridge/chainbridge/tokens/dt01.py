"""Dispute token (DT-01)."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, RelationValidationError, TokenValidationError


class DT01Token(BaseToken):
    """Dispute lifecycle independent from invoices until closure."""

    TOKEN_TYPE = "DT-01"
    VERSION = "1.0"
    INITIAL_STATE = "RAISED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "RAISED": ["REVIEWING"],
        "REVIEWING": ["DECIDED"],
        "DECIDED": ["CLOSED"],
        "CLOSED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "dispute_code": str,
        "reason": str,
        "actor": str,
        "raised_at": str,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "supporting_documents": list,
        "resolution_notes": str,
    }
    REQUIRED_RELATIONS = ("st01_id", "it01_id")

    def validate_state_constraints(self) -> None:
        if self.state == "DECIDED" and not self.metadata.get("decision"):
            raise TokenValidationError("DT-01 DECIDED state requires decision metadata")
        if self.state == "CLOSED":
            if not self.metadata.get("closed_at"):
                raise TokenValidationError("DT-01 CLOSED state requires closed_at timestamp")
            if not self.metadata.get("proofpack_id"):
                raise TokenValidationError("DT-01 CLOSED state requires ProofPack id")
        if not self.relations.get("pt01_id"):
            raise RelationValidationError("DT-01 must reference PT-01 for settlement impact")
