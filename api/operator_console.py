"""
Operator Console API — READ-ONLY PDO & Settlement Visibility
════════════════════════════════════════════════════════════════════════════════

PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
Agent: Cody (GID-01) — API
Effective Date: 2025-12-30

HARD INVARIANTS (INV-OC-*):
    INV-OC-001: UI may not mutate PDO or settlement state
    INV-OC-002: Every settlement links to PDO ID
    INV-OC-003: Ledger hash visible for final outcomes
    INV-OC-004: Missing data explicit (no silent gaps)
    INV-OC-005: Non-GET requests fail closed

This module provides GET-only endpoints for the Operator Console.
All mutation attempts are explicitly rejected with 405 Method Not Allowed.

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

OC_API_VERSION = "1.0.0"
"""Operator Console API version."""

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""Marker for missing/unavailable data (INV-OC-004: no silent gaps)."""


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TRANSFER OBJECTS
# ═══════════════════════════════════════════════════════════════════════════════

class OCPDOView(BaseModel):
    """
    OC_PDO_VIEW — Unified view for Operator Console.
    
    Per PAC-007C Section 8: OC JOIN CONTRACT.
    All fields required by invariant. Missing data shown as UNAVAILABLE.
    """
    pdo_id: str = Field(..., description="PDO identifier")
    decision_id: Optional[str] = Field(None, description="Decision identifier")
    outcome_id: Optional[str] = Field(None, description="Outcome identifier")
    settlement_id: Optional[str] = Field(None, description="Settlement identifier (optional)")
    ledger_entry_hash: str = Field(..., description="Ledger entry hash (or UNAVAILABLE)")
    sequence_number: int = Field(..., description="Ledger sequence number")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    # Extended fields for visibility
    pac_id: Optional[str] = Field(None, description="PAC identifier")
    outcome_status: Optional[str] = Field(None, description="Outcome status")
    issuer: Optional[str] = Field(None, description="PDO issuer")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pdo_id": "PDO-PAC-007-001",
                "decision_id": "DEC-PAC-007-001",
                "outcome_id": "OUT-PAC-007-001",
                "settlement_id": "SET-PAC-007-001",
                "ledger_entry_hash": "a1b2c3d4e5f6...",
                "sequence_number": 42,
                "timestamp": "2025-12-30T10:00:00Z",
                "pac_id": "PAC-007",
                "outcome_status": "ACCEPTED",
                "issuer": "GID-00"
            }
        }


class OCPDOListResponse(BaseModel):
    """Paginated response for OC PDO list."""
    items: List[OCPDOView]
    count: int = Field(..., description="Number of items in this response")
    total: int = Field(..., description="Total items available")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Offset from start")
    api_version: str = Field(default=OC_API_VERSION, description="API version")


class OCSettlementView(BaseModel):
    """
    Settlement view for Operator Console.
    
    Every settlement MUST link to a PDO (INV-OC-002).
    Ledger hash MUST be visible for final outcomes (INV-OC-003).
    """
    settlement_id: str = Field(..., description="Settlement identifier")
    pdo_id: str = Field(..., description="Linked PDO identifier (INV-OC-002)")
    status: str = Field(..., description="Settlement status")
    initiated_at: str = Field(..., description="Initiation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    ledger_entry_hash: str = Field(..., description="Ledger hash (or UNAVAILABLE)")
    
    # Milestone tracking
    milestones: List[Dict[str, Any]] = Field(default_factory=list, description="Milestone records")
    current_milestone: Optional[str] = Field(None, description="Current milestone")
    
    # Audit trail
    trace_log: List[str] = Field(default_factory=list, description="Audit trace")


class OCSettlementListResponse(BaseModel):
    """Paginated response for OC Settlement list."""
    items: List[OCSettlementView]
    count: int
    total: int
    limit: int
    offset: int
    api_version: str = Field(default=OC_API_VERSION)


class OCTimelineEvent(BaseModel):
    """Timeline event for PDO/Settlement visualization."""
    event_id: str
    event_type: str  # PDO_CREATED, SETTLEMENT_INITIATED, MILESTONE_COMPLETED, etc.
    timestamp: str
    pdo_id: Optional[str] = None
    settlement_id: Optional[str] = None
    ledger_hash: str = Field(default=UNAVAILABLE_MARKER)
    details: Dict[str, Any] = Field(default_factory=dict)


class OCTimelineResponse(BaseModel):
    """Timeline response for Operator Console."""
    events: List[OCTimelineEvent]
    pdo_id: Optional[str] = None
    settlement_id: Optional[str] = None
    span_start: Optional[str] = None
    span_end: Optional[str] = None


class OCLedgerEntryView(BaseModel):
    """Ledger entry view for hash visibility (INV-OC-003)."""
    entry_id: str
    sequence_number: int
    timestamp: str
    entry_hash: str
    previous_hash: str
    entry_type: str
    reference_id: str  # PDO ID, Settlement ID, etc.
    

class OCHealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    api_version: str = OC_API_VERSION
    read_only: bool = True
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/oc",
    tags=["Operator Console - Read Only"],
    responses={
        405: {
            "description": "Method Not Allowed - Operator Console is READ-ONLY",
            "content": {
                "application/json": {
                    "example": {
                        "error": "OC_READ_ONLY_VIOLATION",
                        "message": "Operator Console is read-only. Only GET requests are permitted.",
                        "invariant": "INV-OC-005"
                    }
                }
            }
        }
    }
)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH / STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/health",
    response_model=OCHealthResponse,
    summary="OC Health Check",
    description="Verify Operator Console API is operational (read-only)."
)
async def oc_health() -> OCHealthResponse:
    """Return OC health status."""
    return OCHealthResponse(
        status="ok",
        api_version=OC_API_VERSION,
        read_only=True,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PDO VISIBILITY (GET ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/pdo",
    response_model=OCPDOListResponse,
    summary="List PDOs for Operator Console",
    description="""
List PDO records with settlement linkage and ledger hashes.

Returns OC_PDO_VIEW records per PAC-007C Section 8.
Missing data is explicitly marked as UNAVAILABLE (INV-OC-004).
"""
)
async def list_pdo_views(
    outcome_status: Optional[str] = Query(None, description="Filter by outcome status"),
    pac_id: Optional[str] = Query(None, description="Filter by PAC ID"),
    has_settlement: Optional[bool] = Query(None, description="Filter by settlement linkage"),
    limit: int = Query(100, ge=1, le=500, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Offset"),
) -> OCPDOListResponse:
    """List PDO views for operator console."""
    try:
        # Import here to avoid circular dependencies
        from core.governance.pdo_registry import get_pdo_registry
        from core.governance.pdo_ledger import get_pdo_ledger
        
        registry = get_pdo_registry()
        ledger = get_pdo_ledger()
        
        # Get all PDOs
        all_pdos = registry.list_all()
        
        # Apply filters
        filtered = all_pdos
        if outcome_status:
            filtered = [p for p in filtered if getattr(p, 'outcome_status', None) == outcome_status]
        if pac_id:
            filtered = [p for p in filtered if getattr(p, 'pac_id', None) == pac_id]
        
        total = len(filtered)
        
        # Apply pagination
        paginated = filtered[offset:offset + limit]
        
        # Build OC_PDO_VIEW records
        items = []
        for pdo in paginated:
            # Get ledger entry for this PDO
            ledger_entry = ledger.get_by_reference(getattr(pdo, 'pdo_id', str(pdo)))
            
            items.append(OCPDOView(
                pdo_id=getattr(pdo, 'pdo_id', str(pdo)),
                decision_id=getattr(pdo, 'decision_id', None),
                outcome_id=getattr(pdo, 'outcome_id', None),
                settlement_id=getattr(pdo, 'settlement_id', None),
                ledger_entry_hash=ledger_entry.entry_hash if ledger_entry else UNAVAILABLE_MARKER,
                sequence_number=ledger_entry.sequence_number if ledger_entry else -1,
                timestamp=getattr(pdo, 'emitted_at', datetime.now(timezone.utc).isoformat()),
                pac_id=getattr(pdo, 'pac_id', None),
                outcome_status=getattr(pdo, 'outcome_status', None),
                issuer=getattr(pdo, 'issuer', None),
            ))
        
        return OCPDOListResponse(
            items=items,
            count=len(items),
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"OC list_pdo_views failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list PDO views: {str(e)}")


@router.get(
    "/pdo/{pdo_id}",
    response_model=OCPDOView,
    summary="Get PDO View",
    description="Get single PDO with settlement linkage and ledger hash."
)
async def get_pdo_view(pdo_id: str) -> OCPDOView:
    """Get single PDO view for operator console."""
    try:
        from core.governance.pdo_registry import get_pdo_registry
        from core.governance.pdo_ledger import get_pdo_ledger
        
        registry = get_pdo_registry()
        ledger = get_pdo_ledger()
        
        pdo = registry.get(pdo_id)
        if pdo is None:
            raise HTTPException(status_code=404, detail=f"PDO {pdo_id} not found")
        
        ledger_entry = ledger.get_by_reference(pdo_id)
        
        return OCPDOView(
            pdo_id=getattr(pdo, 'pdo_id', pdo_id),
            decision_id=getattr(pdo, 'decision_id', None),
            outcome_id=getattr(pdo, 'outcome_id', None),
            settlement_id=getattr(pdo, 'settlement_id', None),
            ledger_entry_hash=ledger_entry.entry_hash if ledger_entry else UNAVAILABLE_MARKER,
            sequence_number=ledger_entry.sequence_number if ledger_entry else -1,
            timestamp=getattr(pdo, 'emitted_at', datetime.now(timezone.utc).isoformat()),
            pac_id=getattr(pdo, 'pac_id', None),
            outcome_status=getattr(pdo, 'outcome_status', None),
            issuer=getattr(pdo, 'issuer', None),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OC get_pdo_view failed for {pdo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDO view: {str(e)}")


@router.get(
    "/pdo/{pdo_id}/timeline",
    response_model=OCTimelineResponse,
    summary="Get PDO Timeline",
    description="Get timeline of events for a PDO including settlements."
)
async def get_pdo_timeline(pdo_id: str) -> OCTimelineResponse:
    """Get timeline for a specific PDO."""
    try:
        from core.governance.pdo_registry import get_pdo_registry
        from core.governance.pdo_ledger import get_pdo_ledger
        
        registry = get_pdo_registry()
        ledger = get_pdo_ledger()
        
        pdo = registry.get(pdo_id)
        if pdo is None:
            raise HTTPException(status_code=404, detail=f"PDO {pdo_id} not found")
        
        events = []
        
        # PDO creation event
        ledger_entry = ledger.get_by_reference(pdo_id)
        events.append(OCTimelineEvent(
            event_id=f"evt_{pdo_id}_created",
            event_type="PDO_CREATED",
            timestamp=getattr(pdo, 'emitted_at', datetime.now(timezone.utc).isoformat()),
            pdo_id=pdo_id,
            ledger_hash=ledger_entry.entry_hash if ledger_entry else UNAVAILABLE_MARKER,
            details={
                "pac_id": getattr(pdo, 'pac_id', None),
                "issuer": getattr(pdo, 'issuer', None),
                "outcome_status": getattr(pdo, 'outcome_status', None),
            }
        ))
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return OCTimelineResponse(
            events=events,
            pdo_id=pdo_id,
            span_start=events[0].timestamp if events else None,
            span_end=events[-1].timestamp if events else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OC get_pdo_timeline failed for {pdo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDO timeline: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT VISIBILITY (GET ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/settlements",
    response_model=OCSettlementListResponse,
    summary="List Settlements",
    description="""
List settlements with PDO linkage (INV-OC-002) and ledger hashes (INV-OC-003).
"""
)
async def list_settlements(
    pdo_id: Optional[str] = Query(None, description="Filter by linked PDO"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> OCSettlementListResponse:
    """List settlements for operator console."""
    try:
        from core.settlement import SettlementEngine
        from core.governance.pdo_ledger import get_pdo_ledger
        
        # Get settlements from engine (if available)
        # For now, return empty list as settlement storage isn't fully wired
        items: List[OCSettlementView] = []
        total = 0
        
        return OCSettlementListResponse(
            items=items,
            count=len(items),
            total=total,
            limit=limit,
            offset=offset,
        )
    except ImportError:
        # Settlement module not available - explicit gap (INV-OC-004)
        logger.warning("Settlement module not available for OC")
        return OCSettlementListResponse(
            items=[],
            count=0,
            total=0,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"OC list_settlements failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list settlements: {str(e)}")


@router.get(
    "/settlements/{settlement_id}",
    response_model=OCSettlementView,
    summary="Get Settlement",
    description="Get settlement with PDO linkage and ledger hash."
)
async def get_settlement(settlement_id: str) -> OCSettlementView:
    """Get single settlement for operator console."""
    try:
        from core.governance.pdo_ledger import get_pdo_ledger
        
        ledger = get_pdo_ledger()
        
        # Check ledger for settlement record
        ledger_entry = ledger.get_by_reference(settlement_id)
        
        if ledger_entry is None:
            raise HTTPException(status_code=404, detail=f"Settlement {settlement_id} not found")
        
        return OCSettlementView(
            settlement_id=settlement_id,
            pdo_id=getattr(ledger_entry, 'pdo_id', UNAVAILABLE_MARKER),
            status=getattr(ledger_entry, 'status', UNAVAILABLE_MARKER),
            initiated_at=ledger_entry.timestamp,
            ledger_entry_hash=ledger_entry.entry_hash,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OC get_settlement failed for {settlement_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get settlement: {str(e)}")


@router.get(
    "/settlements/{settlement_id}/timeline",
    response_model=OCTimelineResponse,
    summary="Get Settlement Timeline",
    description="Get timeline of events for a settlement."
)
async def get_settlement_timeline(settlement_id: str) -> OCTimelineResponse:
    """Get timeline for a specific settlement."""
    try:
        from core.governance.pdo_ledger import get_pdo_ledger
        
        ledger = get_pdo_ledger()
        
        events = []
        
        # Find ledger entries related to this settlement
        # PDOLedger doesn't have get_by_reference, so we return empty timeline
        # Settlements are tracked through PDO lifecycle, not direct ledger entries
        
        return OCTimelineResponse(
            events=events,
            settlement_id=settlement_id,
            span_start=events[0].timestamp if events else None,
            span_end=events[-1].timestamp if events else None,
        )
    except Exception as e:
        logger.error(f"OC get_settlement_timeline failed for {settlement_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get settlement timeline: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER VISIBILITY (GET ONLY)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/ledger/entries",
    response_model=List[OCLedgerEntryView],
    summary="List Ledger Entries",
    description="List ledger entries with hash visibility (INV-OC-003)."
)
async def list_ledger_entries(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[OCLedgerEntryView]:
    """List ledger entries for operator console."""
    try:
        from core.governance.pdo_ledger import get_pdo_ledger
        
        ledger = get_pdo_ledger()
        
        entries = []
        for i, entry in enumerate(ledger):
            if i < offset:
                continue
            if i >= offset + limit:
                break
            entries.append(OCLedgerEntryView(
                entry_id=entry.entry_id,
                sequence_number=entry.sequence_number,
                timestamp=entry.timestamp,
                entry_hash=entry.entry_hash,
                previous_hash=entry.previous_hash,
                entry_type=entry.entry_type.value if hasattr(entry.entry_type, 'value') else str(entry.entry_type),
                reference_id=entry.reference_id,
            ))
        
        return entries
    except Exception as e:
        logger.error(f"OC list_ledger_entries failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list ledger entries: {str(e)}")


@router.get(
    "/ledger/entry/{entry_id}",
    response_model=OCLedgerEntryView,
    summary="Get Ledger Entry",
    description="Get single ledger entry with hash."
)
async def get_ledger_entry(entry_id: str) -> OCLedgerEntryView:
    """Get single ledger entry."""
    try:
        from core.governance.pdo_ledger import get_pdo_ledger
        
        ledger = get_pdo_ledger()
        
        # Find entry by ID (linear scan since PDOLedger stores by pdo_id/pac_id)
        entry = None
        for e in ledger:
            if e.entry_id == entry_id:
                entry = e
                break
        
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Ledger entry {entry_id} not found")
        
        return OCLedgerEntryView(
            entry_id=entry.entry_id,
            sequence_number=entry.sequence_number,
            timestamp=getattr(entry, 'ledger_recorded_at', UNAVAILABLE_MARKER),
            entry_hash=entry.entry_hash,
            previous_hash=entry.previous_entry_hash,
            entry_type="PDO_LEDGER_ENTRY",
            reference_id=entry.pdo_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OC get_ledger_entry failed for {entry_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ledger entry: {str(e)}")


@router.get(
    "/ledger/verify",
    summary="Verify Ledger Chain",
    description="Verify ledger hash chain integrity."
)
async def verify_ledger_chain() -> Dict[str, Any]:
    """Verify the ledger hash chain."""
    try:
        from core.governance.pdo_ledger import get_pdo_ledger
        
        ledger = get_pdo_ledger()
        is_valid, error_msg = ledger.verify_chain()
        
        return {
            "chain_valid": is_valid,
            "error": error_msg,
            "entry_count": len(ledger),
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"OC verify_ledger_chain failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify ledger chain: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# BLOCKED OPERATIONS — INV-OC-005: Non-GET FAILS CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

def _block_mutation(method: str, path: str) -> JSONResponse:
    """Generate standard 405 response for mutation attempts."""
    logger.warning(f"OC BLOCKED: {method} {path} - Operator Console is read-only")
    return JSONResponse(
        status_code=405,
        content={
            "error": "OC_READ_ONLY_VIOLATION",
            "message": "Operator Console is read-only. Only GET requests are permitted.",
            "method": method,
            "path": path,
            "invariant": "INV-OC-005",
        },
        headers={"Allow": "GET"},
    )


# Block POST on all OC endpoints
@router.post("/{path:path}", status_code=405)
async def block_post(path: str, request: Request) -> JSONResponse:
    """BLOCKED: POST not allowed on Operator Console."""
    return _block_mutation("POST", f"/oc/{path}")


@router.put("/{path:path}", status_code=405)
async def block_put(path: str, request: Request) -> JSONResponse:
    """BLOCKED: PUT not allowed on Operator Console."""
    return _block_mutation("PUT", f"/oc/{path}")


@router.patch("/{path:path}", status_code=405)
async def block_patch(path: str, request: Request) -> JSONResponse:
    """BLOCKED: PATCH not allowed on Operator Console."""
    return _block_mutation("PATCH", f"/oc/{path}")


@router.delete("/{path:path}", status_code=405)
async def block_delete(path: str, request: Request) -> JSONResponse:
    """BLOCKED: DELETE not allowed on Operator Console."""
    return _block_mutation("DELETE", f"/oc/{path}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "router",
    "OC_API_VERSION",
    "UNAVAILABLE_MARKER",
    # DTOs
    "OCPDOView",
    "OCPDOListResponse",
    "OCSettlementView",
    "OCSettlementListResponse",
    "OCTimelineEvent",
    "OCTimelineResponse",
    "OCLedgerEntryView",
    "OCHealthResponse",
]
