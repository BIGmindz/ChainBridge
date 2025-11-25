"""
Core payment utilities shared across ChainBridge services.

Provides canonical identifiers for shipments and milestones to ensure that
ChainPay, ChainBoard, and ChainIQ reference the same logical entities.
"""

from .identity import (
    canonical_milestone_id,
    canonical_shipment_reference,
    infer_freight_token_id,
    is_valid_milestone_id,
    parse_milestone_identifier,
)

__all__ = [
    "canonical_milestone_id",
    "canonical_shipment_reference",
    "infer_freight_token_id",
    "is_valid_milestone_id",
    "parse_milestone_identifier",
]
