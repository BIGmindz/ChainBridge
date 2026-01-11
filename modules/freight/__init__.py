"""
ChainFreight Module
===================
PAC: PAC-LOG-P140-CHAINFREIGHT
Lead Agent: Atlas (GID-11)

The third vertical of the ChainBridge Trinity:
- ChainPay: The Money (Finance & Settlement)
- ChainSense: The Data (IoT & Condition Monitoring)
- ChainFreight: The Physical Movement (Logistics & Supply Chain)

"Money and IoT data are useless if we don't know WHAT is being shipped,
WHO owns it, and WHERE the Bill of Lading is."
"""

from modules.freight.bill_of_lading import (
    DigitalBillOfLading,
    BoLStatus,
    Party,
    Signature,
    CargoItem,
    Route,
    CustodyEvent,
    atlas_create_bol,
    atlas_validate_custody_chain,
)

from modules.freight.customs_clearing import (
    CustomsClearance,
    CustomsStatus,
    DocumentType,
    CustomsDocument,
    HSCode,
    DutyCalculation,
    OCRPipeline,
    atlas_create_clearance,
    atlas_preClear,
    atlas_check_release_gate,
)

__all__ = [
    # Bill of Lading
    "DigitalBillOfLading",
    "BoLStatus",
    "Party",
    "Signature",
    "CargoItem",
    "Route",
    "CustodyEvent",
    "atlas_create_bol",
    "atlas_validate_custody_chain",
    # Customs
    "CustomsClearance",
    "CustomsStatus",
    "DocumentType",
    "CustomsDocument",
    "HSCode",
    "DutyCalculation",
    "OCRPipeline",
    "atlas_create_clearance",
    "atlas_preClear",
    "atlas_check_release_gate",
]

__version__ = "0.1.0"
__pac__ = "PAC-LOG-P140-CHAINFREIGHT"
__lead_agent__ = "Atlas (GID-11)"
