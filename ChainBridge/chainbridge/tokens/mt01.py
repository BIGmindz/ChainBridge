"""Milestone token (MT-01)."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, RelationValidationError, TokenValidationError


class MT01Token(BaseToken):
    """Transport milestones derived from IoT + Seeburger events."""

    TOKEN_TYPE = "MT-01"
    VERSION = "1.0"
    INITIAL_STATE = "CREATED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "CREATED": ["VERIFIED"],
        "VERIFIED": ["APPLIED"],
        "APPLIED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "milestone_type": str,
        "timestamp": str,
        "location": dict,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "telemetry_snapshot": dict,
        "eta_variance_minutes": int,
    }
    REQUIRED_RELATIONS = ("st01_id", "iot_event_id")

    def validate_state_constraints(self) -> None:
        if not any(key in self.relations for key in ("iot_event_id", "seeburger_event_id")):
            raise RelationValidationError("MT-01 must link to IoT or Seeburger event id")
        if self.state == "APPLIED" and not self.metadata.get("applied_at"):
            raise TokenValidationError("MT-01 APPLIED state requires applied_at timestamp")
