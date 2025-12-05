"""Shipment root token (ST-01)."""

from __future__ import annotations

from typing import Any, Dict, List

from .base_token import BaseToken, RelationValidationError, TokenValidationError


class ST01Token(BaseToken):
    """Shipment lifecycle controller that anchors every other token."""

    TOKEN_TYPE = "ST-01"
    VERSION = "1.0"
    INITIAL_STATE = "CREATED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "CREATED": ["DISPATCHED"],
        "DISPATCHED": ["IN_TRANSIT"],
        # Allow carriers to jump straight to DELIVERED when arrival pings are missing
        "IN_TRANSIT": ["ARRIVED", "DELIVERED"],
        "ARRIVED": ["DELIVERED"],
        "DELIVERED": ["SETTLED"],
        "SETTLED": ["CLOSED"],
        "CLOSED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "origin": str,
        "destination": str,
        "carrier_id": str,
        "broker_id": str,
        "customer_id": str,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "equipment_type": str,
        "shipment_class": str,
    }

    def validate_state_constraints(self) -> None:
        if self.state == "SETTLED":
            pt01_ids = self.relations.get("pt01_ids")
            if not pt01_ids:
                raise RelationValidationError("ST-01 requires PT-01 linkage before SETTLED")
        if self.state == "CLOSED":
            if not self.metadata.get("claims_closed_at"):
                raise TokenValidationError("ST-01 CLOSED state requires claims_closed_at timestamp")
