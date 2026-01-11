"""
ChainBridge Immune Strategies Package
=====================================

Pluggable remediation strategies for the Immune System.

Each strategy handles a specific category of transaction failures
and knows how to fix them (or request specific user input).

Available Strategies:
    - MissingFieldStrategy (P161): Auto-fills missing fields with defaults
    
Future Strategies:
    - FormatCorrectionStrategy (P162): Fixes date/currency/format errors
    - DocumentRetryStrategy (P163): Requests document re-upload
    - WatchlistClearanceStrategy (P164): Initiates manual review workflow

Author: Benson (GID-00)
"""

from .missing_field import MissingFieldStrategy
from .format_correction import FormatCorrectionStrategy
from .document_retry import DocumentRetryStrategy
from .watchlist_clearance import WatchlistClearanceStrategy

__all__ = [
    "MissingFieldStrategy",
    "FormatCorrectionStrategy",
    "DocumentRetryStrategy",
    "WatchlistClearanceStrategy",
]
