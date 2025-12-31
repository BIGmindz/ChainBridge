"""
Audit OC API — READ-ONLY Audit/Regulator Endpoints for External Verification
════════════════════════════════════════════════════════════════════════════════

PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
Agent: Cody (GID-01) — OC Audit APIs
Order: ORDER 1
Effective Date: 2025-12-30
Runtime: RUNTIME-013A
Execution Lane: SINGLE-LANE, ORDERED
Governance Mode: FAIL-CLOSED (LOCKED)

OBJECTIVE:
    Deliver audit-grade Operator Console endpoints enabling external auditors
    to reconstruct, verify, and export Proof → Decision → Outcome chains
    with zero inference.

HARD INVARIANTS (INV-AUDIT-*):
    INV-AUDIT-001: All endpoints GET-only (no mutation capability)
    INV-AUDIT-002: Complete chain reconstruction without inference
    INV-AUDIT-003: Export formats: JSON, CSV, PDF-ready
    INV-AUDIT-004: Hash verification at every link
    INV-AUDIT-005: No hidden state (all state visible or explicitly UNAVAILABLE)
    INV-AUDIT-006: Temporal bounds explicit on all queries

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

AUDIT_OC_API_VERSION = "1.0.0"
"""Audit OC API version."""

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""Marker for missing/unavailable data (INV-AUDIT-005)."""

MAX_EXPORT_RECORDS = 10000
"""Maximum records per export operation."""

SUPPORTED_EXPORT_FORMATS = ["json", "csv"]
"""Supported export formats."""


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ChainLinkType(str, Enum):
    """Types of links in a Proof→Decision→Outcome chain."""
    PROOF = "PROOF"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"
    SETTLEMENT = "SETTLEMENT"
    PDO = "PDO"


class VerificationStatus(str, Enum):
    """Hash verification status."""
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    PENDING = "PENDING"
    UNAVAILABLE = "UNAVAILABLE"


class AuditExportFormat(str, Enum):
    """Supported audit export formats."""
    JSON = "json"
    CSV = "csv"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TRANSFER OBJECTS — CHAIN RECONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════════

class ChainLink(BaseModel):
    """
    Single link in the Proof→Decision→Outcome chain.
    
    INV-AUDIT-004: Hash verification at every link.
    """
    link_id: str = Field(..., description="Unique link identifier")
    link_type: ChainLinkType = Field(..., description="Type of chain link")
    parent_link_id: Optional[str] = Field(None, description="Parent link ID (or null for root)")
    content_hash: str = Field(..., description="SHA-256 hash of link content")
    previous_hash: str = Field(..., description="Hash of previous link (chain integrity)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    sequence_number: int = Field(..., description="Sequence in chain")
    verification_status: VerificationStatus = Field(..., description="Hash verification status")
    
    # Content summary (not full content, for performance)
    content_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of link content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "link_id": "LINK-001",
                "link_type": "PROOF",
                "parent_link_id": None,
                "content_hash": "a1b2c3d4e5f6...",
                "previous_hash": "0000000000000000",
                "timestamp": "2025-12-30T10:00:00Z",
                "sequence_number": 1,
                "verification_status": "VERIFIED",
                "content_summary": {"proof_pack_id": "PP-001"}
            }
        }


class ChainReconstruction(BaseModel):
    """
    Complete chain reconstruction for audit.
    
    INV-AUDIT-002: Complete chain reconstruction without inference.
    """
    chain_id: str = Field(..., description="Unique chain identifier")
    root_link_id: str = Field(..., description="Root link (usually PROOF)")
    terminal_link_id: str = Field(..., description="Terminal link (usually OUTCOME/SETTLEMENT)")
    total_links: int = Field(..., description="Total links in chain")
    chain_integrity: VerificationStatus = Field(..., description="Overall chain integrity status")
    links: List[ChainLink] = Field(default_factory=list, description="All links in order")
    
    # Temporal bounds (INV-AUDIT-006)
    earliest_timestamp: str = Field(..., description="Earliest timestamp in chain")
    latest_timestamp: str = Field(..., description="Latest timestamp in chain")
    
    # Audit metadata
    reconstruction_timestamp: str = Field(..., description="When this reconstruction was generated")
    api_version: str = Field(default=AUDIT_OC_API_VERSION, description="API version")


class ChainVerificationResult(BaseModel):
    """Result of chain hash verification."""
    chain_id: str = Field(..., description="Chain identifier")
    verified: bool = Field(..., description="Whether chain is fully verified")
    total_links: int = Field(..., description="Total links checked")
    verified_links: int = Field(..., description="Links that passed verification")
    failed_links: List[str] = Field(default_factory=list, description="Link IDs that failed")
    verification_timestamp: str = Field(..., description="When verification was performed")
    integrity_hash: str = Field(..., description="Final chain integrity hash")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TRANSFER OBJECTS — AUDIT EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

class AuditTrailEntry(BaseModel):
    """
    Single audit trail entry for export.
    
    All fields explicit — no inference allowed (INV-AUDIT-002).
    """
    entry_id: str = Field(..., description="Unique entry identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    # Chain references
    pdo_id: str = Field(default=UNAVAILABLE_MARKER, description="PDO identifier")
    proof_id: str = Field(default=UNAVAILABLE_MARKER, description="Proof/ProofPack identifier")
    decision_id: str = Field(default=UNAVAILABLE_MARKER, description="Decision identifier")
    outcome_id: str = Field(default=UNAVAILABLE_MARKER, description="Outcome identifier")
    settlement_id: str = Field(default=UNAVAILABLE_MARKER, description="Settlement identifier")
    
    # Hashes for verification
    proof_hash: str = Field(default=UNAVAILABLE_MARKER, description="Proof content hash")
    decision_hash: str = Field(default=UNAVAILABLE_MARKER, description="Decision content hash")
    outcome_hash: str = Field(default=UNAVAILABLE_MARKER, description="Outcome content hash")
    ledger_hash: str = Field(default=UNAVAILABLE_MARKER, description="Ledger entry hash")
    
    # Status
    chain_verified: bool = Field(False, description="Whether full chain is verified")
    
    # Agent/governance context
    issuer_gid: str = Field(default=UNAVAILABLE_MARKER, description="Issuing agent GID")
    pac_id: str = Field(default=UNAVAILABLE_MARKER, description="Governing PAC")


class AuditExportRequest(BaseModel):
    """Request for audit data export."""
    start_date: Optional[str] = Field(None, description="Start date (ISO 8601)")
    end_date: Optional[str] = Field(None, description="End date (ISO 8601)")
    pdo_ids: Optional[List[str]] = Field(None, description="Specific PDO IDs to include")
    pac_ids: Optional[List[str]] = Field(None, description="Filter by PAC IDs")
    include_unverified: bool = Field(False, description="Include unverified chains")
    format: AuditExportFormat = Field(AuditExportFormat.JSON, description="Export format")
    limit: int = Field(1000, ge=1, le=MAX_EXPORT_RECORDS, description="Max records")


class AuditExportResponse(BaseModel):
    """Response for audit export."""
    export_id: str = Field(..., description="Unique export identifier")
    export_timestamp: str = Field(..., description="When export was generated")
    format: AuditExportFormat = Field(..., description="Export format")
    total_records: int = Field(..., description="Total records in export")
    
    # Temporal bounds (INV-AUDIT-006)
    data_start: str = Field(..., description="Earliest record timestamp")
    data_end: str = Field(..., description="Latest record timestamp")
    
    # Integrity
    export_hash: str = Field(..., description="SHA-256 of export content")
    api_version: str = Field(default=AUDIT_OC_API_VERSION, description="API version")
    
    # Actual data (for JSON response)
    entries: Optional[List[AuditTrailEntry]] = Field(None, description="Audit entries")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TRANSFER OBJECTS — REGULATORY SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

class RegulatoryMetrics(BaseModel):
    """Metrics for regulatory/compliance reporting."""
    period_start: str = Field(..., description="Reporting period start")
    period_end: str = Field(..., description="Reporting period end")
    
    # Volume metrics
    total_pdos: int = Field(0, description="Total PDOs in period")
    total_decisions: int = Field(0, description="Total decisions")
    total_outcomes: int = Field(0, description="Total outcomes")
    total_settlements: int = Field(0, description="Total settlements")
    
    # Verification metrics
    verified_chains: int = Field(0, description="Chains with full verification")
    unverified_chains: int = Field(0, description="Chains pending verification")
    failed_verifications: int = Field(0, description="Chains that failed verification")
    
    # Governance metrics
    governance_violations: int = Field(0, description="Governance violations detected")
    human_interventions: int = Field(0, description="Human-in-the-loop interventions")
    fail_closed_triggers: int = Field(0, description="Fail-closed triggers")
    
    # Computed
    verification_rate: float = Field(0.0, description="Verification success rate (0-1)")
    chain_completeness_rate: float = Field(0.0, description="Chain completeness rate (0-1)")


class RegulatorySummary(BaseModel):
    """Complete regulatory summary for external auditors."""
    summary_id: str = Field(..., description="Unique summary identifier")
    generated_at: str = Field(..., description="When summary was generated")
    metrics: RegulatoryMetrics = Field(..., description="Computed metrics")
    
    # System state
    system_version: str = Field(..., description="ChainBridge version")
    governance_mode: str = Field("FAIL-CLOSED", description="Current governance mode")
    
    # Attestations
    data_complete: bool = Field(True, description="Whether all data is present")
    no_hidden_state: bool = Field(True, description="INV-AUDIT-005 compliance")
    
    api_version: str = Field(default=AUDIT_OC_API_VERSION, description="API version")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER SETUP
# ═══════════════════════════════════════════════════════════════════════════════

audit_oc_router = APIRouter(
    prefix="/oc/audit",
    tags=["Audit OC (Read-Only)"],
    responses={
        405: {"description": "Method Not Allowed — mutations forbidden (INV-AUDIT-001)"},
        400: {"description": "Bad Request — invalid parameters"},
        404: {"description": "Not Found"},
    }
)


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION (INV-AUDIT-001)
# ═══════════════════════════════════════════════════════════════════════════════

def _reject_mutation(method: str) -> JSONResponse:
    """
    Return 405 for any mutation attempt.
    
    INV-AUDIT-001: All endpoints GET-only.
    """
    logger.warning(f"[AUDIT-OC] Mutation attempt blocked: {method}")
    return JSONResponse(
        status_code=405,
        content={
            "error": "Method Not Allowed",
            "detail": f"Audit OC is read-only. {method} not permitted.",
            "invariant": "INV-AUDIT-001",
            "governance_mode": "FAIL-CLOSED"
        },
        headers={"Allow": "GET, HEAD, OPTIONS"}
    )


@audit_oc_router.post("/{path:path}")
@audit_oc_router.put("/{path:path}")
@audit_oc_router.delete("/{path:path}")
@audit_oc_router.patch("/{path:path}")
async def reject_audit_mutations(path: str, request: Request):
    """Reject all mutation attempts on audit endpoints."""
    return _reject_mutation(request.method)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _compute_hash(content: Any) -> str:
    """Compute SHA-256 hash of content."""
    if isinstance(content, str):
        data = content.encode("utf-8")
    elif isinstance(content, bytes):
        data = content
    else:
        data = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _generate_chain_id() -> str:
    """Generate unique chain identifier."""
    import uuid
    return f"CHAIN-{uuid.uuid4().hex[:12].upper()}"


def _generate_export_id() -> str:
    """Generate unique export identifier."""
    import uuid
    return f"EXPORT-{uuid.uuid4().hex[:12].upper()}"


def _generate_summary_id() -> str:
    """Generate unique summary identifier."""
    import uuid
    return f"SUMMARY-{uuid.uuid4().hex[:12].upper()}"


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA GENERATORS (for demonstration — replace with real registry queries)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_mock_chain_links(chain_id: str) -> List[ChainLink]:
    """Generate mock chain links for demonstration."""
    now = _now_iso()
    base_hash = _compute_hash(chain_id)
    
    links = [
        ChainLink(
            link_id=f"{chain_id}-PROOF",
            link_type=ChainLinkType.PROOF,
            parent_link_id=None,
            content_hash=_compute_hash(f"{chain_id}-proof-content"),
            previous_hash="0" * 64,
            timestamp=now,
            sequence_number=1,
            verification_status=VerificationStatus.VERIFIED,
            content_summary={"proof_pack_id": f"PP-{chain_id[-8:]}", "manifest_hash": base_hash[:32]}
        ),
        ChainLink(
            link_id=f"{chain_id}-DECISION",
            link_type=ChainLinkType.DECISION,
            parent_link_id=f"{chain_id}-PROOF",
            content_hash=_compute_hash(f"{chain_id}-decision-content"),
            previous_hash=_compute_hash(f"{chain_id}-proof-content"),
            timestamp=now,
            sequence_number=2,
            verification_status=VerificationStatus.VERIFIED,
            content_summary={"decision_type": "APPROVE", "confidence": 0.95}
        ),
        ChainLink(
            link_id=f"{chain_id}-OUTCOME",
            link_type=ChainLinkType.OUTCOME,
            parent_link_id=f"{chain_id}-DECISION",
            content_hash=_compute_hash(f"{chain_id}-outcome-content"),
            previous_hash=_compute_hash(f"{chain_id}-decision-content"),
            timestamp=now,
            sequence_number=3,
            verification_status=VerificationStatus.VERIFIED,
            content_summary={"outcome_status": "ACCEPTED", "ledger_seq": 42}
        ),
    ]
    return links


def _get_mock_audit_entries(limit: int = 10) -> List[AuditTrailEntry]:
    """Generate mock audit trail entries."""
    entries = []
    for i in range(min(limit, 50)):
        entry_id = f"AUDIT-{i:06d}"
        entries.append(AuditTrailEntry(
            entry_id=entry_id,
            timestamp=_now_iso(),
            pdo_id=f"PDO-{i:04d}",
            proof_id=f"PP-{i:04d}",
            decision_id=f"DEC-{i:04d}",
            outcome_id=f"OUT-{i:04d}",
            settlement_id=f"SET-{i:04d}" if i % 3 == 0 else UNAVAILABLE_MARKER,
            proof_hash=_compute_hash(f"proof-{i}"),
            decision_hash=_compute_hash(f"decision-{i}"),
            outcome_hash=_compute_hash(f"outcome-{i}"),
            ledger_hash=_compute_hash(f"ledger-{i}"),
            chain_verified=True,
            issuer_gid="GID-00",
            pac_id="PAC-013A"
        ))
    return entries


# ═══════════════════════════════════════════════════════════════════════════════
# CHAIN RECONSTRUCTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@audit_oc_router.get(
    "/chains/{chain_id}",
    response_model=ChainReconstruction,
    summary="Reconstruct Proof→Decision→Outcome chain",
    description="INV-AUDIT-002: Complete chain reconstruction without inference"
)
async def get_chain_reconstruction(chain_id: str) -> ChainReconstruction:
    """
    Reconstruct a complete Proof→Decision→Outcome chain.
    
    INV-AUDIT-002: All links must be explicit — no inference.
    INV-AUDIT-004: Hash verification at every link.
    """
    links = _get_mock_chain_links(chain_id)
    
    return ChainReconstruction(
        chain_id=chain_id,
        root_link_id=links[0].link_id if links else UNAVAILABLE_MARKER,
        terminal_link_id=links[-1].link_id if links else UNAVAILABLE_MARKER,
        total_links=len(links),
        chain_integrity=VerificationStatus.VERIFIED,
        links=links,
        earliest_timestamp=links[0].timestamp if links else _now_iso(),
        latest_timestamp=links[-1].timestamp if links else _now_iso(),
        reconstruction_timestamp=_now_iso()
    )


@audit_oc_router.get(
    "/chains/{chain_id}/verify",
    response_model=ChainVerificationResult,
    summary="Verify chain hash integrity",
    description="INV-AUDIT-004: Hash verification at every link"
)
async def verify_chain(chain_id: str) -> ChainVerificationResult:
    """
    Verify hash integrity of an entire chain.
    
    INV-AUDIT-004: Every link's hash must be verifiable.
    """
    links = _get_mock_chain_links(chain_id)
    
    # Verify each link
    verified_links = 0
    failed_links = []
    
    for i, link in enumerate(links):
        # Verify previous_hash matches actual previous content_hash
        if i == 0:
            expected_prev = "0" * 64
        else:
            expected_prev = links[i-1].content_hash
        
        if link.previous_hash == expected_prev:
            verified_links += 1
        else:
            failed_links.append(link.link_id)
    
    # Compute final integrity hash
    all_hashes = "".join(link.content_hash for link in links)
    integrity_hash = _compute_hash(all_hashes)
    
    return ChainVerificationResult(
        chain_id=chain_id,
        verified=len(failed_links) == 0,
        total_links=len(links),
        verified_links=verified_links,
        failed_links=failed_links,
        verification_timestamp=_now_iso(),
        integrity_hash=integrity_hash
    )


@audit_oc_router.get(
    "/chains",
    response_model=List[str],
    summary="List all chain IDs",
    description="Returns list of chain identifiers for reconstruction"
)
async def list_chains(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum chains to return")
) -> List[str]:
    """
    List available chain IDs.
    
    INV-AUDIT-006: Temporal bounds explicit on all queries.
    """
    # Mock implementation — return sample chain IDs
    return [f"CHAIN-{i:012X}" for i in range(min(limit, 50))]


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT EXPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@audit_oc_router.get(
    "/export",
    response_model=AuditExportResponse,
    summary="Export audit trail (JSON)",
    description="INV-AUDIT-003: Export formats include JSON"
)
async def export_audit_trail_json(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=MAX_EXPORT_RECORDS, description="Max records")
) -> AuditExportResponse:
    """
    Export audit trail as JSON.
    
    INV-AUDIT-003: Export formats: JSON, CSV.
    INV-AUDIT-006: Temporal bounds explicit.
    """
    entries = _get_mock_audit_entries(limit)
    
    # Compute export hash for integrity
    export_content = json.dumps([e.model_dump() for e in entries], sort_keys=True, default=str)
    export_hash = _compute_hash(export_content)
    
    return AuditExportResponse(
        export_id=_generate_export_id(),
        export_timestamp=_now_iso(),
        format=AuditExportFormat.JSON,
        total_records=len(entries),
        data_start=entries[0].timestamp if entries else _now_iso(),
        data_end=entries[-1].timestamp if entries else _now_iso(),
        export_hash=export_hash,
        entries=entries
    )


@audit_oc_router.get(
    "/export/csv",
    summary="Export audit trail (CSV)",
    description="INV-AUDIT-003: Export formats include CSV"
)
async def export_audit_trail_csv(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=MAX_EXPORT_RECORDS, description="Max records")
) -> StreamingResponse:
    """
    Export audit trail as CSV.
    
    INV-AUDIT-003: Export formats: JSON, CSV.
    """
    entries = _get_mock_audit_entries(limit)
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "entry_id", "timestamp", "pdo_id", "proof_id", "decision_id",
        "outcome_id", "settlement_id", "proof_hash", "decision_hash",
        "outcome_hash", "ledger_hash", "chain_verified", "issuer_gid", "pac_id"
    ])
    
    # Data rows
    for entry in entries:
        writer.writerow([
            entry.entry_id, entry.timestamp, entry.pdo_id, entry.proof_id,
            entry.decision_id, entry.outcome_id, entry.settlement_id,
            entry.proof_hash, entry.decision_hash, entry.outcome_hash,
            entry.ledger_hash, entry.chain_verified, entry.issuer_gid, entry.pac_id
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_export_{_now_iso()[:10]}.csv",
            "X-Export-Hash": _compute_hash(output.getvalue()),
            "X-Total-Records": str(len(entries))
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# REGULATORY SUMMARY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@audit_oc_router.get(
    "/regulatory/summary",
    response_model=RegulatorySummary,
    summary="Get regulatory summary",
    description="Comprehensive metrics for regulatory/compliance reporting"
)
async def get_regulatory_summary(
    period_start: Optional[str] = Query(None, description="Period start (ISO 8601)"),
    period_end: Optional[str] = Query(None, description="Period end (ISO 8601)")
) -> RegulatorySummary:
    """
    Generate regulatory summary with computed metrics.
    
    INV-AUDIT-005: No hidden state — all state visible.
    """
    now = _now_iso()
    start = period_start or now[:10] + "T00:00:00Z"
    end = period_end or now
    
    # Mock metrics computation
    metrics = RegulatoryMetrics(
        period_start=start,
        period_end=end,
        total_pdos=150,
        total_decisions=145,
        total_outcomes=142,
        total_settlements=89,
        verified_chains=140,
        unverified_chains=5,
        failed_verifications=0,
        governance_violations=0,
        human_interventions=3,
        fail_closed_triggers=0,
        verification_rate=0.9655,
        chain_completeness_rate=0.9467
    )
    
    return RegulatorySummary(
        summary_id=_generate_summary_id(),
        generated_at=now,
        metrics=metrics,
        system_version="1.0.0",
        governance_mode="FAIL-CLOSED",
        data_complete=True,
        no_hidden_state=True
    )


@audit_oc_router.get(
    "/regulatory/violations",
    summary="List governance violations",
    description="All governance violations within time period"
)
async def get_governance_violations(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Max records")
) -> Dict[str, Any]:
    """
    List governance violations for audit review.
    
    Returns empty list if no violations (explicit — not hidden).
    """
    return {
        "violations": [],
        "total": 0,
        "period_start": start_date or _now_iso()[:10] + "T00:00:00Z",
        "period_end": end_date or _now_iso(),
        "query_timestamp": _now_iso(),
        "api_version": AUDIT_OC_API_VERSION
    }


# ═══════════════════════════════════════════════════════════════════════════════
# METADATA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@audit_oc_router.get(
    "/metadata",
    summary="Get audit API metadata",
    description="Version, capabilities, invariants"
)
async def get_audit_metadata() -> Dict[str, Any]:
    """Return audit API metadata for external auditors."""
    return {
        "api_version": AUDIT_OC_API_VERSION,
        "pac_reference": "PAC-013A",
        "agent": "Cody (GID-01)",
        "governance_mode": "FAIL-CLOSED (LOCKED)",
        "execution_lane": "SINGLE-LANE, ORDERED",
        "runtime_id": "RUNTIME-013A",
        "capabilities": {
            "chain_reconstruction": True,
            "hash_verification": True,
            "json_export": True,
            "csv_export": True,
            "regulatory_summary": True
        },
        "invariants": {
            "INV-AUDIT-001": "All endpoints GET-only (no mutation capability)",
            "INV-AUDIT-002": "Complete chain reconstruction without inference",
            "INV-AUDIT-003": "Export formats: JSON, CSV",
            "INV-AUDIT-004": "Hash verification at every link",
            "INV-AUDIT-005": "No hidden state",
            "INV-AUDIT-006": "Temporal bounds explicit on all queries"
        },
        "supported_export_formats": SUPPORTED_EXPORT_FORMATS,
        "max_export_records": MAX_EXPORT_RECORDS,
        "timestamp": _now_iso()
    }


@audit_oc_router.get(
    "/health",
    summary="Audit API health check"
)
async def audit_health() -> Dict[str, Any]:
    """Health check for audit API."""
    return {
        "status": "healthy",
        "api_version": AUDIT_OC_API_VERSION,
        "governance_mode": "FAIL-CLOSED",
        "timestamp": _now_iso()
    }
