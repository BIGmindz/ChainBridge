"""
Canonical payment identity helpers.

These helpers ensure that milestone identifiers follow the shared format across
ChainPay, ChainBoard, and ChainIQ services.
"""

from __future__ import annotations

import re
from typing import Tuple

MILESTONE_ID_PATTERN = re.compile(r"^(?P<shipment>[A-Za-z0-9_\-]+)-M(?P<index>[1-9][0-9]*)$")


def canonical_milestone_id(shipment_reference: str, index: int) -> str:
    """
    Build canonical milestone identifier "<shipment_reference>-M<index>".
    """
    if not shipment_reference:
        raise ValueError("shipment_reference is required for milestone identifier")
    if index < 1:
        raise ValueError("milestone index must be >= 1")
    return f"{shipment_reference}-M{index}"


def parse_milestone_identifier(value: str) -> Tuple[str, int]:
    """
    Parse milestone identifier into (shipment_reference, index).
    """
    match = MILESTONE_ID_PATTERN.match(value or "")
    if not match:
        raise ValueError("Milestone ID must match '<shipment_reference>-M<index>' " "(e.g., 'SHP-2025-042-M1')")
    return match.group("shipment"), int(match.group("index"))


def is_valid_milestone_id(value: str) -> bool:
    """Return True if the milestone ID matches the canonical format."""
    return bool(MILESTONE_ID_PATTERN.match(value or ""))


def canonical_shipment_reference(
    *,
    shipment_reference: str | None = None,
    freight_token_id: int | None = None,
) -> str:
    """
    Return canonical shipment_reference string.

    Preference order:
    1. Explicit shipment_reference (already canonical)
    2. Derived from freight_token_id (SHP-<id>, zero-padded to 4 digits)
    """
    if shipment_reference:
        return shipment_reference
    if freight_token_id is None:
        raise ValueError("Either shipment_reference or freight_token_id is required")
    return f"SHP-{freight_token_id:04d}"


def infer_freight_token_id(shipment_reference: str | None) -> int | None:
    """
    Attempt to infer freight_token_id from shipment_reference.

    Returns None if digits cannot be extracted.
    """
    if not shipment_reference:
        return None
    digits = "".join(ch for ch in shipment_reference if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None
