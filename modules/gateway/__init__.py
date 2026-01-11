"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GATEWAY MODULE - LEGACY BRIDGE                            ║
║                       PAC-GATE-P500-ISO20022                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Bridge to the Old World: ISO-20022, SWIFT, and Legacy Banking               ║
║                                                                              ║
║  "We speak their language so they can join our economy."                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

This module provides adapters for interoperating with legacy financial systems:
  - ISO-20022 message parsing (pacs.008, pacs.002)
  - SWIFT MX message handling
  - FedNow/SEPA compatibility (future)

Usage:
    from modules.gateway import ISO20022Adapter, PaymentInstruction
    
    adapter = ISO20022Adapter()
    instruction = adapter.parse_pacs008(xml_string)
    ack_xml = adapter.generate_pacs002(instruction, status="ACCP")
"""

__version__ = "3.0.0"

from .iso20022 import (
    # Core Adapter
    ISO20022Adapter,
    
    # Data Models
    PaymentInstruction,
    PaymentParty,
    PaymentAmount,
    StatusReport,
    
    # Enums
    TransactionStatus,
    ReasonCode,
    
    # Exceptions
    ISO20022Error,
    XMLParseError,
    SchemaValidationError,
    CurrencyValidationError,
)

__all__ = [
    # Adapter
    "ISO20022Adapter",
    
    # Models
    "PaymentInstruction",
    "PaymentParty",
    "PaymentAmount",
    "StatusReport",
    
    # Enums
    "TransactionStatus",
    "ReasonCode",
    
    # Exceptions
    "ISO20022Error",
    "XMLParseError",
    "SchemaValidationError",
    "CurrencyValidationError",
]
