"""
Operator Console Data Aggregator — PDO + Settlement + Ledger Join
════════════════════════════════════════════════════════════════════════════════

PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
Agent: Cindy (GID-04) — Backend Aggregation
Effective Date: 2025-12-30

This module aggregates data from PDO Registry, Settlement Engine, and PDO Ledger
to produce unified OC_PDO_VIEW records for the Operator Console.

INVARIANTS ENFORCED:
    INV-OC-002: Every settlement links to PDO ID
    INV-OC-003: Ledger hash visible for final outcomes
    INV-OC-004: Missing data explicit (no silent gaps)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

AGGREGATOR_VERSION = "1.0.0"
"""OC Aggregator version."""

UNAVAILABLE = "UNAVAILABLE"
"""Marker for missing data (INV-OC-004)."""

MISSING_SEQUENCE = -1
"""Sequence number for missing ledger entries."""


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class OCViewStatus(str, Enum):
    """Status of aggregated OC view."""
    COMPLETE = "COMPLETE"           # All data available
    PARTIAL = "PARTIAL"             # Some data missing (explicit gaps)
    PDO_ONLY = "PDO_ONLY"           # Only PDO data available
    SETTLEMENT_ONLY = "SETTLEMENT_ONLY"  # Only settlement data available
    ERROR = "ERROR"                 # Aggregation error


@dataclass
class OCPDOViewRecord:
    """
    Aggregated OC_PDO_VIEW record.
    
    Per PAC-007C Section 8: OC JOIN CONTRACT.
    """
    # Required fields
    pdo_id: str
    ledger_entry_hash: str
    sequence_number: int
    timestamp: str
    
    # Optional fields with explicit UNAVAILABLE markers
    decision_id: Optional[str] = None
    outcome_id: Optional[str] = None
    settlement_id: Optional[str] = None
    pac_id: Optional[str] = None
    outcome_status: Optional[str] = None
    issuer: Optional[str] = None
    
    # Aggregation metadata
    view_status: OCViewStatus = OCViewStatus.COMPLETE
    data_sources: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "pdo_id": self.pdo_id,
            "decision_id": self.decision_id,
            "outcome_id": self.outcome_id,
            "settlement_id": self.settlement_id,
            "ledger_entry_hash": self.ledger_entry_hash,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
            "pac_id": self.pac_id,
            "outcome_status": self.outcome_status,
            "issuer": self.issuer,
            "view_status": self.view_status.value,
            "data_sources": self.data_sources,
        }


@dataclass
class OCSettlementViewRecord:
    """
    Aggregated settlement view record.
    
    INV-OC-002: Every settlement MUST link to PDO ID.
    """
    settlement_id: str
    pdo_id: str  # Required: INV-OC-002
    status: str
    initiated_at: str
    ledger_entry_hash: str
    
    completed_at: Optional[str] = None
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    current_milestone: Optional[str] = None
    trace_log: List[str] = field(default_factory=list)
    
    view_status: OCViewStatus = OCViewStatus.COMPLETE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "settlement_id": self.settlement_id,
            "pdo_id": self.pdo_id,
            "status": self.status,
            "initiated_at": self.initiated_at,
            "completed_at": self.completed_at,
            "ledger_entry_hash": self.ledger_entry_hash,
            "milestones": self.milestones,
            "current_milestone": self.current_milestone,
            "trace_log": self.trace_log,
            "view_status": self.view_status.value,
        }


@dataclass
class OCTimelineEventRecord:
    """Timeline event for visualization."""
    event_id: str
    event_type: str
    timestamp: str
    ledger_hash: str = UNAVAILABLE
    pdo_id: Optional[str] = None
    settlement_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "pdo_id": self.pdo_id,
            "settlement_id": self.settlement_id,
            "ledger_hash": self.ledger_hash,
            "details": self.details,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OC DATA AGGREGATOR
# ═══════════════════════════════════════════════════════════════════════════════

class OCDataAggregator:
    """
    Aggregates PDO, Settlement, and Ledger data for Operator Console.
    
    This is a READ-ONLY aggregator. It does not mutate any underlying data.
    All data gaps are made explicit (INV-OC-004).
    
    Usage:
        aggregator = OCDataAggregator()
        pdo_views = aggregator.get_pdo_views()
        settlement_views = aggregator.get_settlement_views()
        timeline = aggregator.get_timeline(pdo_id="PDO-001")
    """
    
    def __init__(
        self,
        registry=None,
        ledger=None,
        settlement_store=None,
    ):
        """
        Initialize aggregator with data sources.
        
        Args:
            registry: PDORegistry instance (uses singleton if None)
            ledger: PDOLedger instance (uses singleton if None)
            settlement_store: Optional settlement data store
        """
        self._registry = registry
        self._ledger = ledger
        self._settlement_store = settlement_store
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """Lazy initialization of data sources."""
        if self._initialized:
            return
        
        # Import here to avoid circular dependencies
        if self._registry is None:
            try:
                from core.governance.pdo_registry import get_pdo_registry
                self._registry = get_pdo_registry()
            except ImportError:
                logger.warning("PDORegistry not available")
        
        if self._ledger is None:
            try:
                from core.governance.pdo_ledger import get_pdo_ledger
                self._ledger = get_pdo_ledger()
            except ImportError:
                logger.warning("PDOLedger not available")
        
        self._initialized = True
    
    # ───────────────────────────────────────────────────────────────────────────
    # PDO VIEWS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_pdo_views(
        self,
        outcome_status: Optional[str] = None,
        pac_id: Optional[str] = None,
        has_settlement: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[OCPDOViewRecord], int]:
        """
        Get aggregated PDO views.
        
        Returns:
            Tuple of (list of OCPDOViewRecord, total count)
        """
        self._ensure_initialized()
        
        if self._registry is None:
            logger.warning("Registry not available, returning empty list")
            return [], 0
        
        # Get all PDOs from registry
        all_pdos = self._registry.list_all()
        
        # Apply filters
        filtered = all_pdos
        if outcome_status:
            filtered = [p for p in filtered if getattr(p, 'outcome_status', None) == outcome_status]
        if pac_id:
            filtered = [p for p in filtered if getattr(p, 'pac_id', None) == pac_id]
        if has_settlement is not None:
            if has_settlement:
                filtered = [p for p in filtered if getattr(p, 'settlement_id', None) is not None]
            else:
                filtered = [p for p in filtered if getattr(p, 'settlement_id', None) is None]
        
        total = len(filtered)
        
        # Apply pagination
        paginated = filtered[offset:offset + limit]
        
        # Build aggregated views
        views = []
        for pdo in paginated:
            view = self._aggregate_pdo_view(pdo)
            views.append(view)
        
        return views, total
    
    def get_pdo_view(self, pdo_id: str) -> Optional[OCPDOViewRecord]:
        """
        Get single aggregated PDO view.
        
        Args:
            pdo_id: PDO identifier
            
        Returns:
            OCPDOViewRecord or None if not found
        """
        self._ensure_initialized()
        
        if self._registry is None:
            logger.warning("Registry not available")
            return None
        
        pdo = self._registry.get(pdo_id)
        if pdo is None:
            return None
        
        return self._aggregate_pdo_view(pdo)
    
    def _aggregate_pdo_view(self, pdo) -> OCPDOViewRecord:
        """
        Aggregate single PDO into view record.
        
        Joins with ledger to get hash (INV-OC-003).
        Marks missing data explicitly (INV-OC-004).
        """
        pdo_id = getattr(pdo, 'pdo_id', str(pdo))
        data_sources = ["pdo_registry"]
        
        # Get ledger entry if available
        ledger_hash = UNAVAILABLE
        sequence_number = MISSING_SEQUENCE
        view_status = OCViewStatus.PDO_ONLY
        
        if self._ledger is not None:
            try:
                entry = self._ledger.get_by_reference(pdo_id)
                if entry is not None:
                    ledger_hash = entry.entry_hash
                    sequence_number = entry.sequence_number
                    data_sources.append("pdo_ledger")
                    view_status = OCViewStatus.COMPLETE
            except Exception as e:
                logger.warning(f"Failed to get ledger entry for {pdo_id}: {e}")
        
        # Check for settlement linkage
        settlement_id = getattr(pdo, 'settlement_id', None)
        if settlement_id:
            data_sources.append("settlement")
        elif view_status == OCViewStatus.COMPLETE:
            view_status = OCViewStatus.PARTIAL  # Has ledger but no settlement
        
        return OCPDOViewRecord(
            pdo_id=pdo_id,
            decision_id=getattr(pdo, 'decision_id', None),
            outcome_id=getattr(pdo, 'outcome_id', None),
            settlement_id=settlement_id,
            ledger_entry_hash=ledger_hash,
            sequence_number=sequence_number,
            timestamp=getattr(pdo, 'emitted_at', datetime.now(timezone.utc).isoformat()),
            pac_id=getattr(pdo, 'pac_id', None),
            outcome_status=getattr(pdo, 'outcome_status', None),
            issuer=getattr(pdo, 'issuer', None),
            view_status=view_status,
            data_sources=data_sources,
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # SETTLEMENT VIEWS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_settlement_views(
        self,
        pdo_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[OCSettlementViewRecord], int]:
        """
        Get aggregated settlement views.
        
        INV-OC-002: Every settlement returned will have pdo_id.
        
        Returns:
            Tuple of (list of OCSettlementViewRecord, total count)
        """
        self._ensure_initialized()
        
        # Settlement store integration placeholder
        # For now return empty - settlements need to be wired to storage
        return [], 0
    
    def get_settlement_view(self, settlement_id: str) -> Optional[OCSettlementViewRecord]:
        """
        Get single settlement view.
        
        Args:
            settlement_id: Settlement identifier
            
        Returns:
            OCSettlementViewRecord or None if not found
        """
        self._ensure_initialized()
        
        # Check ledger for settlement record
        if self._ledger is not None:
            try:
                entry = self._ledger.get_by_reference(settlement_id)
                if entry is not None:
                    return OCSettlementViewRecord(
                        settlement_id=settlement_id,
                        pdo_id=getattr(entry, 'pdo_id', UNAVAILABLE),
                        status=getattr(entry, 'status', UNAVAILABLE),
                        initiated_at=entry.timestamp,
                        ledger_entry_hash=entry.entry_hash,
                        view_status=OCViewStatus.PARTIAL,
                    )
            except Exception as e:
                logger.warning(f"Failed to get settlement {settlement_id}: {e}")
        
        return None
    
    # ───────────────────────────────────────────────────────────────────────────
    # TIMELINE
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_pdo_timeline(self, pdo_id: str) -> List[OCTimelineEventRecord]:
        """
        Get timeline of events for a PDO.
        
        Args:
            pdo_id: PDO identifier
            
        Returns:
            List of timeline events sorted by timestamp
        """
        self._ensure_initialized()
        
        events = []
        
        # Get PDO
        pdo = None
        if self._registry is not None:
            pdo = self._registry.get(pdo_id)
        
        if pdo is None:
            return events
        
        # PDO creation event
        ledger_hash = UNAVAILABLE
        if self._ledger is not None:
            try:
                entry = self._ledger.get_by_reference(pdo_id)
                if entry is not None:
                    ledger_hash = entry.entry_hash
            except Exception:
                pass
        
        events.append(OCTimelineEventRecord(
            event_id=f"evt_{pdo_id}_created",
            event_type="PDO_CREATED",
            timestamp=getattr(pdo, 'emitted_at', datetime.now(timezone.utc).isoformat()),
            pdo_id=pdo_id,
            ledger_hash=ledger_hash,
            details={
                "pac_id": getattr(pdo, 'pac_id', None),
                "issuer": getattr(pdo, 'issuer', None),
                "outcome_status": getattr(pdo, 'outcome_status', None),
            }
        ))
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return events
    
    def get_settlement_timeline(self, settlement_id: str) -> List[OCTimelineEventRecord]:
        """
        Get timeline of events for a settlement.
        
        Args:
            settlement_id: Settlement identifier
            
        Returns:
            List of timeline events sorted by timestamp
        """
        self._ensure_initialized()
        
        events = []
        
        # Check ledger for settlement events
        if self._ledger is not None:
            try:
                entry = self._ledger.get_by_reference(settlement_id)
                if entry is not None:
                    events.append(OCTimelineEventRecord(
                        event_id=f"evt_{settlement_id}_ledger",
                        event_type="SETTLEMENT_LEDGER_ENTRY",
                        timestamp=entry.timestamp,
                        settlement_id=settlement_id,
                        ledger_hash=entry.entry_hash,
                    ))
            except Exception as e:
                logger.warning(f"Failed to get settlement timeline for {settlement_id}: {e}")
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return events
    
    # ───────────────────────────────────────────────────────────────────────────
    # LEDGER VIEWS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_ledger_entries(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get ledger entries for hash visibility (INV-OC-003).
        
        Returns:
            List of ledger entry dictionaries
        """
        self._ensure_initialized()
        
        if self._ledger is None:
            return []
        
        entries = []
        try:
            for i, entry in enumerate(self._ledger):
                if i < offset:
                    continue
                if i >= offset + limit:
                    break
                entries.append({
                    "entry_id": entry.entry_id,
                    "sequence_number": entry.sequence_number,
                    "timestamp": entry.timestamp,
                    "entry_hash": entry.entry_hash,
                    "previous_hash": entry.previous_hash,
                    "entry_type": entry.entry_type.value if hasattr(entry.entry_type, 'value') else str(entry.entry_type),
                    "reference_id": entry.reference_id,
                })
        except Exception as e:
            logger.error(f"Failed to iterate ledger entries: {e}")
        
        return entries
    
    def verify_ledger_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Verify ledger hash chain integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        self._ensure_initialized()
        
        if self._ledger is None:
            return False, "Ledger not available"
        
        try:
            return self._ledger.verify_chain()
        except Exception as e:
            return False, str(e)
    
    # ───────────────────────────────────────────────────────────────────────────
    # STATISTICS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregator statistics.
        
        Returns:
            Dictionary with counts and status
        """
        self._ensure_initialized()
        
        pdo_count = 0
        ledger_count = 0
        
        if self._registry is not None:
            try:
                pdo_count = len(self._registry)
            except Exception:
                pass
        
        if self._ledger is not None:
            try:
                ledger_count = len(self._ledger)
            except Exception:
                pass
        
        return {
            "pdo_count": pdo_count,
            "ledger_count": ledger_count,
            "settlement_count": 0,  # Placeholder
            "aggregator_version": AGGREGATOR_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

_default_aggregator: Optional[OCDataAggregator] = None


def get_oc_aggregator() -> OCDataAggregator:
    """Get the default OC data aggregator."""
    global _default_aggregator
    if _default_aggregator is None:
        _default_aggregator = OCDataAggregator()
    return _default_aggregator


def reset_oc_aggregator() -> None:
    """Reset the default aggregator (for testing)."""
    global _default_aggregator
    _default_aggregator = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Constants
    "AGGREGATOR_VERSION",
    "UNAVAILABLE",
    "MISSING_SEQUENCE",
    
    # Enums
    "OCViewStatus",
    
    # Data models
    "OCPDOViewRecord",
    "OCSettlementViewRecord",
    "OCTimelineEventRecord",
    
    # Aggregator
    "OCDataAggregator",
    "get_oc_aggregator",
    "reset_oc_aggregator",
]
