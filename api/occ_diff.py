# ═══════════════════════════════════════════════════════════════════════════════
# OCC Diff API — Decision Diff & Comparison Endpoints
# PAC-BENSON-P22-C: OCC + Control Plane Deepening
#
# Provides GET-only endpoints for decision diff/comparison:
# - /occ/diff/{left_id}/{right_id}     - Compare two decisions/artifacts
# - /occ/diff/ber/{ber_id_a}/{ber_id_b} - Compare two BER records
# - /occ/diff/pdo/{pdo_id_a}/{pdo_id_b} - Compare two PDO snapshots
#
# INVARIANTS:
# - INV-OCC-005: Evidence immutability (no retroactive edits)
# - INV-OCC-006: No hidden transitions (all changes visible)
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - CINDY (GID-04) — Backend Support
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/occ/diff", tags=["OCC Diff"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

DiffChangeType = Literal["added", "removed", "modified", "unchanged"]
DiffEntityType = Literal["ber", "pdo", "wrap", "decision", "artifact"]


class DiffFieldChange(BaseModel):
    """Individual field change in a diff."""
    field_path: str
    change_type: DiffChangeType
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class DiffSection(BaseModel):
    """Section of a diff (grouping related changes)."""
    section_id: str
    section_name: str
    change_type: DiffChangeType
    changes: List[DiffFieldChange]
    old_evidence_hash: Optional[str] = None
    new_evidence_hash: Optional[str] = None


class DiffSummary(BaseModel):
    """Summary statistics for a diff."""
    total_changes: int
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
    has_breaking_changes: bool


class DiffResponse(BaseModel):
    """Full diff comparison response."""
    diff_id: str
    entity_type: DiffEntityType
    left_id: str
    left_label: str
    right_id: str
    right_label: str
    sections: List[DiffSection]
    summary: DiffSummary
    left_evidence_hash: str
    right_evidence_hash: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BERDiffResponse(BaseModel):
    """BER-specific diff response."""
    diff_id: str
    ber_a_id: str
    ber_b_id: str
    pac_id: str
    sections: List[DiffSection]
    summary: DiffSummary
    ber_a_evidence_hash: str
    ber_b_evidence_hash: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PDODiffResponse(BaseModel):
    """PDO-specific diff response."""
    diff_id: str
    pdo_a_id: str
    pdo_b_id: str
    sections: List[DiffSection]
    summary: DiffSummary
    pdo_a_evidence_hash: str
    pdo_b_evidence_hash: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

def _get_mock_diff(left_id: str, right_id: str, entity_type: DiffEntityType) -> DiffResponse:
    """Get mock diff data."""
    sections = [
        DiffSection(
            section_id="sec-001",
            section_name="Metadata",
            change_type="modified",
            changes=[
                DiffFieldChange(
                    field_path="status",
                    change_type="modified",
                    old_value="DRAFT",
                    new_value="FINAL",
                    description="Status updated",
                ),
            ],
            old_evidence_hash="sha256:abc123",
            new_evidence_hash="sha256:def456",
        ),
        DiffSection(
            section_id="sec-002",
            section_name="Tasks",
            change_type="added",
            changes=[
                DiffFieldChange(
                    field_path="tasks.timeline_view",
                    change_type="added",
                    new_value="completed",
                    description="Timeline view task added",
                ),
            ],
        ),
    ]

    summary = DiffSummary(
        total_changes=2,
        added_count=1,
        removed_count=0,
        modified_count=1,
        unchanged_count=10,
        has_breaking_changes=False,
    )

    return DiffResponse(
        diff_id=f"diff-{left_id}-{right_id}",
        entity_type=entity_type,
        left_id=left_id,
        left_label=f"{entity_type.upper()} {left_id}",
        right_id=right_id,
        right_label=f"{entity_type.upper()} {right_id}",
        sections=sections,
        summary=summary,
        left_evidence_hash="sha256:abc123def456",
        right_evidence_hash="sha256:ghi789jkl012",
    )


def _get_mock_ber_diff(ber_a_id: str, ber_b_id: str) -> BERDiffResponse:
    """Get mock BER diff data."""
    sections = [
        DiffSection(
            section_id="sec-001",
            section_name="Execution Results",
            change_type="modified",
            changes=[
                DiffFieldChange(
                    field_path="completed_tasks",
                    change_type="modified",
                    old_value="5",
                    new_value="9",
                    description="Task count increased",
                ),
                DiffFieldChange(
                    field_path="finality",
                    change_type="modified",
                    old_value="PROVISIONAL",
                    new_value="FINAL",
                    description="BER finalized",
                ),
            ],
        ),
    ]

    summary = DiffSummary(
        total_changes=2,
        added_count=0,
        removed_count=0,
        modified_count=2,
        unchanged_count=8,
        has_breaking_changes=False,
    )

    return BERDiffResponse(
        diff_id=f"ber-diff-{ber_a_id}-{ber_b_id}",
        ber_a_id=ber_a_id,
        ber_b_id=ber_b_id,
        pac_id="PAC-BENSON-P22-C",
        sections=sections,
        summary=summary,
        ber_a_evidence_hash="sha256:ber_abc123",
        ber_b_evidence_hash="sha256:ber_def456",
    )


def _get_mock_pdo_diff(pdo_a_id: str, pdo_b_id: str) -> PDODiffResponse:
    """Get mock PDO diff data."""
    sections = [
        DiffSection(
            section_id="sec-001",
            section_name="Decision State",
            change_type="modified",
            changes=[
                DiffFieldChange(
                    field_path="approved_by",
                    change_type="added",
                    new_value="ALEX (GID-ALEX)",
                    description="Approval added",
                ),
            ],
        ),
    ]

    summary = DiffSummary(
        total_changes=1,
        added_count=1,
        removed_count=0,
        modified_count=0,
        unchanged_count=5,
        has_breaking_changes=False,
    )

    return PDODiffResponse(
        diff_id=f"pdo-diff-{pdo_a_id}-{pdo_b_id}",
        pdo_a_id=pdo_a_id,
        pdo_b_id=pdo_b_id,
        sections=sections,
        summary=summary,
        pdo_a_evidence_hash="sha256:pdo_abc123",
        pdo_b_evidence_hash="sha256:pdo_def456",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/{left_id}/{right_id}", response_model=DiffResponse)
async def get_diff(
    left_id: str,
    right_id: str,
    entity_type: DiffEntityType = "decision",
) -> DiffResponse:
    """
    Get diff between two entities.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-005 (Evidence immutability)
    Invariant: INV-OCC-006 (No hidden transitions)
    """
    return _get_mock_diff(left_id, right_id, entity_type)


@router.get("/ber/{ber_a_id}/{ber_b_id}", response_model=BERDiffResponse)
async def get_ber_diff(ber_a_id: str, ber_b_id: str) -> BERDiffResponse:
    """
    Get diff between two BER records.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-005 (Evidence immutability)
    """
    return _get_mock_ber_diff(ber_a_id, ber_b_id)


@router.get("/pdo/{pdo_a_id}/{pdo_b_id}", response_model=PDODiffResponse)
async def get_pdo_diff(pdo_a_id: str, pdo_b_id: str) -> PDODiffResponse:
    """
    Get diff between two PDO snapshots.

    READ-ONLY: No mutations allowed.
    Invariant: INV-OCC-005 (Evidence immutability)
    """
    return _get_mock_pdo_diff(pdo_a_id, pdo_b_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{left_id}/{right_id}")
@router.put("/{left_id}/{right_id}")
@router.patch("/{left_id}/{right_id}")
@router.delete("/{left_id}/{right_id}")
async def reject_diff_mutations(left_id: str, right_id: str):
    """Reject mutations. READ-ONLY endpoint."""
    raise HTTPException(
        status_code=405,
        detail="Diff endpoints are READ-ONLY. INV-OCC-005: Evidence immutability.",
    )
