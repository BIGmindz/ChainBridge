"""Invoice token (IT-01)."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, RelationValidationError, TokenValidationError


class IT01Token(BaseToken):
    """Invoice lifecycle tied to quotes, milestones, and accessorials."""

    TOKEN_TYPE = "IT-01"
    VERSION = "1.0"
    INITIAL_STATE = "COMPUTED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "COMPUTED": ["PUBLISHED"],
        "PUBLISHED": ["ACKNOWLEDGED"],
        "ACKNOWLEDGED": ["SETTLED"],
        "SETTLED": ["ARCHIVED"],
        "ARCHIVED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "invoice_number": str,
        "currency": str,
        "total": float,
        "line_items": list,
        "due_date": str,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "notes": str,
        "governance_packet_id": str,
    }
    REQUIRED_RELATIONS = ("st01_id", "qt01_id")

    def validate_state_constraints(self) -> None:
        accessorial_ids = self.relations.get("at02_ids")
        milestone_ids = self.relations.get("mt01_ids")
        if not accessorial_ids:
            raise RelationValidationError("IT-01 requires linked AT-02 tokens")
        if not milestone_ids:
            raise RelationValidationError("IT-01 requires linked MT-01 tokens")

        if self.state == "PUBLISHED" and not self.metadata.get("alex_governance_id"):
            raise TokenValidationError("IT-01 PUBLISHED state requires ALEX governance approval id")
        if self.state == "SETTLED" and not self.relations.get("pt01_id"):
            raise RelationValidationError("IT-01 SETTLED requires PT-01 linkage")
        if self.state == "ARCHIVED" and not self.metadata.get("archived_at"):
            raise TokenValidationError("IT-01 ARCHIVED state requires archived_at timestamp")
