# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Lint v2 OC API — Runtime Enforcement Visibility
# PAC-JEFFREY-P06R: Lint v2 Runtime Enforcement & Control Plane Wiring
# GOLD STANDARD · FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════

"""
FastAPI router for Lint v2 visibility in Operations Console.

Provides GET-only endpoints for:
- Invariant registry
- Evaluation reports
- Enforcement point status
- Training signal emission

All endpoints are READ-ONLY. Mutations return 405.

SCHEMA REFERENCES:
- lint_schema: CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0

Author: CODY (GID-01) — Backend Lane
Orchestration: BENSON (GID-00)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.governance.lint_v2 import (
    INVARIANT_REGISTRY,
    EnforcementPoint,
    EvaluationReport,
    EvaluationResult,
    InvariantClass,
    InvariantDefinition,
    InvariantViolation,
    LintTrainingSignal,
    LintV2Engine,
    emit_lint_training_signals,
    get_invariants_by_class,
    get_invariants_for_enforcement_point,
    get_lint_v2_engine,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantDTO(BaseModel):
    """Invariant definition response model."""
    invariant_id: str
    invariant_class: str
    name: str
    description: str
    enforcement_points: List[str]
    severity: str
    schema_version: str


class ViolationDTO(BaseModel):
    """Invariant violation response model."""
    violation_id: str
    invariant_id: str
    invariant_class: str
    enforcement_point: str
    artifact_id: str
    artifact_type: str
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    detected_at: str
    violation_hash: str


class EvaluationReportDTO(BaseModel):
    """Evaluation report response model."""
    report_id: str
    enforcement_point: str
    artifact_id: str
    artifact_type: str
    result: str
    is_pass: bool
    violations: List[ViolationDTO] = Field(default_factory=list)
    violation_count: int
    invariants_evaluated: List[str]
    invariants_count: int
    evaluation_started_at: str
    evaluation_completed_at: Optional[str] = None
    evaluation_duration_ms: Optional[int] = None
    report_hash: str


class LintTrainingSignalDTO(BaseModel):
    """Lint training signal response model."""
    signal_id: str
    invariant_id: str
    invariant_class: str
    enforcement_point: str
    result: str
    artifact_id: str
    observation: str
    emitted_at: str


class InvariantRegistryDTO(BaseModel):
    """Invariant registry response model."""
    schema_version: str
    total_invariants: int
    by_class: Dict[str, int]
    by_enforcement_point: Dict[str, int]
    invariants: List[InvariantDTO]


# ═══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY STORE (Demo/Dev Mode)
# ═══════════════════════════════════════════════════════════════════════════════

_evaluation_reports: Dict[str, EvaluationReport] = {}
_training_signals: List[LintTrainingSignal] = []


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

lintv2_oc_router = APIRouter(prefix="/oc/lintv2", tags=["lintv2-oc"])


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION
# ═══════════════════════════════════════════════════════════════════════════════

@lintv2_oc_router.api_route(
    "/{path:path}",
    methods=["POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def reject_mutations(path: str, request: Request):
    """
    Reject all mutation attempts.
    
    OC endpoints are GET-only. Any mutation attempt returns 405.
    """
    logger.warning(
        f"LINT_V2 OC: Mutation rejected method={request.method} path={path}"
    )
    raise HTTPException(
        status_code=405,
        detail="Lint v2 OC endpoints are read-only. Mutations not permitted. FAIL_CLOSED.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@lintv2_oc_router.get(
    "/registry",
    response_model=InvariantRegistryDTO,
    summary="Get Invariant Registry",
    description="Returns all registered Lint v2 invariants",
)
async def get_invariant_registry() -> InvariantRegistryDTO:
    """
    Get the complete invariant registry.
    
    Returns all S/M/X/T/A/F/C-INV invariants.
    """
    invariants = list(INVARIANT_REGISTRY.values())
    
    # Count by class
    by_class = {}
    for inv_class in InvariantClass:
        count = len([i for i in invariants if i.invariant_class == inv_class])
        if count > 0:
            by_class[inv_class.value] = count
    
    # Count by enforcement point
    by_ep = {}
    for ep in EnforcementPoint:
        count = len([i for i in invariants if ep in i.enforcement_points])
        if count > 0:
            by_ep[ep.value] = count
    
    return InvariantRegistryDTO(
        schema_version="CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0",
        total_invariants=len(invariants),
        by_class=by_class,
        by_enforcement_point=by_ep,
        invariants=[
            InvariantDTO(
                invariant_id=inv.invariant_id,
                invariant_class=inv.invariant_class.value,
                name=inv.name,
                description=inv.description,
                enforcement_points=[ep.value for ep in inv.enforcement_points],
                severity=inv.severity.value,
                schema_version=inv.schema_version,
            )
            for inv in invariants
        ],
    )


@lintv2_oc_router.get(
    "/invariants/{invariant_id}",
    response_model=InvariantDTO,
    summary="Get Invariant by ID",
    description="Returns a specific invariant definition",
)
async def get_invariant(invariant_id: str) -> InvariantDTO:
    """Get a specific invariant by ID."""
    inv = INVARIANT_REGISTRY.get(invariant_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Invariant not found: {invariant_id}")
    
    return InvariantDTO(
        invariant_id=inv.invariant_id,
        invariant_class=inv.invariant_class.value,
        name=inv.name,
        description=inv.description,
        enforcement_points=[ep.value for ep in inv.enforcement_points],
        severity=inv.severity.value,
        schema_version=inv.schema_version,
    )


@lintv2_oc_router.get(
    "/invariants/class/{inv_class}",
    summary="Get Invariants by Class",
    description="Returns all invariants of a specific class (S/M/X/T/A/F/C)",
)
async def get_invariants_by_class_endpoint(inv_class: str) -> Dict[str, Any]:
    """Get all invariants of a specific class."""
    try:
        invariant_class = InvariantClass(inv_class)
    except ValueError:
        valid = [c.value for c in InvariantClass]
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid invariant class: {inv_class}. Valid: {valid}"
        )
    
    invariants = get_invariants_by_class(invariant_class)
    
    return {
        "invariant_class": inv_class,
        "class_name": {
            "S-INV": "Structural",
            "M-INV": "Semantic",
            "X-INV": "Cross-Artifact",
            "T-INV": "Temporal",
            "A-INV": "Authority",
            "F-INV": "Finality",
            "C-INV": "Training",
        }.get(inv_class, inv_class),
        "count": len(invariants),
        "invariants": [inv.to_dict() for inv in invariants],
    }


@lintv2_oc_router.get(
    "/invariants/enforcement-point/{ep}",
    summary="Get Invariants by Enforcement Point",
    description="Returns all invariants for a specific enforcement point",
)
async def get_invariants_by_ep(ep: str) -> Dict[str, Any]:
    """Get all invariants for a specific enforcement point."""
    try:
        enforcement_point = EnforcementPoint(ep)
    except ValueError:
        valid = [e.value for e in EnforcementPoint]
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid enforcement point: {ep}. Valid: {valid}"
        )
    
    invariants = get_invariants_for_enforcement_point(enforcement_point)
    
    return {
        "enforcement_point": ep,
        "count": len(invariants),
        "invariants": [inv.to_dict() for inv in invariants],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATION REPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@lintv2_oc_router.get(
    "/reports",
    summary="List Evaluation Reports",
    description="Returns all cached evaluation reports",
)
async def list_evaluation_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    enforcement_point: Optional[str] = None,
    result: Optional[str] = None,
) -> Dict[str, Any]:
    """List evaluation reports with optional filtering."""
    reports = list(_evaluation_reports.values())
    
    # Filter by enforcement point
    if enforcement_point:
        try:
            ep = EnforcementPoint(enforcement_point)
            reports = [r for r in reports if r.enforcement_point == ep]
        except ValueError:
            pass
    
    # Filter by result
    if result:
        try:
            res = EvaluationResult(result)
            reports = [r for r in reports if r.result == res]
        except ValueError:
            pass
    
    # Sort by evaluation time (newest first)
    reports.sort(key=lambda r: r.evaluation_started_at, reverse=True)
    
    # Paginate
    total = len(reports)
    paginated = reports[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reports": [r.to_dict() for r in paginated],
    }


@lintv2_oc_router.get(
    "/reports/{report_id}",
    response_model=EvaluationReportDTO,
    summary="Get Evaluation Report",
    description="Returns a specific evaluation report",
)
async def get_evaluation_report(report_id: str) -> EvaluationReportDTO:
    """Get a specific evaluation report by ID."""
    report = _evaluation_reports.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    
    return EvaluationReportDTO(**report.to_dict())


@lintv2_oc_router.get(
    "/reports/artifact/{artifact_id}",
    summary="Get Reports for Artifact",
    description="Returns all evaluation reports for a specific artifact",
)
async def get_reports_for_artifact(artifact_id: str) -> Dict[str, Any]:
    """Get all reports for a specific artifact (PAC/WRAP/BER)."""
    reports = [r for r in _evaluation_reports.values() if r.artifact_id == artifact_id]
    reports.sort(key=lambda r: r.evaluation_started_at, reverse=True)
    
    return {
        "artifact_id": artifact_id,
        "total_reports": len(reports),
        "reports": [r.to_dict() for r in reports],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@lintv2_oc_router.get(
    "/training-signals",
    summary="List Training Signals",
    description="Returns lint-emitted training signals",
)
async def list_training_signals(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """List lint training signals."""
    signals = _training_signals[:]
    signals.sort(key=lambda s: s.emitted_at, reverse=True)
    
    total = len(signals)
    paginated = signals[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "signals": [s.to_dict() for s in paginated],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE STATUS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@lintv2_oc_router.get(
    "/engine/status",
    summary="Get Engine Status",
    description="Returns Lint v2 engine configuration and status",
)
async def get_engine_status() -> Dict[str, Any]:
    """Get Lint v2 engine status."""
    engine = get_lint_v2_engine()
    
    return {
        "schema_version": engine.schema_version,
        "fail_mode": engine.fail_mode,
        "warnings_enabled": engine.warnings_enabled,
        "invariant_classes": [c.value for c in InvariantClass],
        "enforcement_points": [ep.value for ep in EnforcementPoint],
        "total_invariants": len(INVARIANT_REGISTRY),
        "cached_reports": len(_evaluation_reports),
        "emitted_signals": len(_training_signals),
    }


@lintv2_oc_router.get(
    "/engine/enforcement-matrix",
    summary="Get Enforcement Matrix",
    description="Returns matrix of invariants vs enforcement points",
)
async def get_enforcement_matrix() -> Dict[str, Any]:
    """Get matrix showing which invariants apply at each enforcement point."""
    matrix = {}
    
    for ep in EnforcementPoint:
        invariants = get_invariants_for_enforcement_point(ep)
        matrix[ep.value] = {
            "count": len(invariants),
            "invariants": [inv.invariant_id for inv in invariants],
            "by_class": {},
        }
        for inv in invariants:
            cls = inv.invariant_class.value
            if cls not in matrix[ep.value]["by_class"]:
                matrix[ep.value]["by_class"][cls] = []
            matrix[ep.value]["by_class"][cls].append(inv.invariant_id)
    
    return {
        "schema_version": "CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0",
        "enforcement_points": list(matrix.keys()),
        "matrix": matrix,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO/TEST ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@lintv2_oc_router.get(
    "/demo/evaluate-pac",
    summary="Demo: Evaluate Sample PAC",
    description="Demonstrates PAC admission evaluation (dev only)",
)
async def demo_evaluate_pac() -> Dict[str, Any]:
    """
    Demo endpoint to show PAC admission evaluation.
    
    For development/testing only.
    """
    engine = get_lint_v2_engine()
    
    # Sample PAC data
    sample_pac = {
        "pac_id": "PAC-DEMO-001",
        "author": "JEFFREY",
        "classification": "EXECUTING",
        "execution_mode": "PARALLEL",
        "execution_barrier": "AGENT_ACK_BARRIER",
    }
    
    # Evaluate
    report = engine.evaluate_pac_admission(
        pac_id="PAC-DEMO-001",
        pac_data=sample_pac,
        acks=[],
    )
    
    # Cache report
    _evaluation_reports[report.report_id] = report
    
    # Emit training signals
    signals = emit_lint_training_signals(report)
    _training_signals.extend(signals)
    
    return {
        "demo": True,
        "pac_id": "PAC-DEMO-001",
        "report": report.to_dict(),
        "training_signals": [s.to_dict() for s in signals],
    }
