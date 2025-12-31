"""
Governance Health Routes — PAC-CODY-P01-GOVERNANCE-HEALTH-BACKEND-AGGREGATION-01

FastAPI routes for governance health dashboard API.
Exposes read-only endpoints for metrics, settlement chains, and compliance mappings.

Authority: CODY (GID-01)
Dispatch: PAC-BENSON-EXEC-P61
Mode: READ-ONLY / FAIL-CLOSED

Endpoints:
    GET /api/governance/health          — Health metrics
    GET /api/governance/settlement-chains — Settlement chain flows
    GET /api/governance/compliance-summary — Enterprise compliance mappings
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.schemas.governance_health import (
    GovernanceHealthResponse,
    SettlementChainsResponse,
    ComplianceSummaryResponse,
    ErrorResponse,
)
from api.services.governance_health import get_governance_health_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/governance",
    tags=["governance", "health"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


# =============================================================================
# HEALTH METRICS
# =============================================================================

@router.get(
    "/health",
    response_model=GovernanceHealthResponse,
    summary="Get Governance Health Metrics",
    description="""
    Returns aggregated governance health metrics from the canonical ledger.
    
    Includes:
    - PAC counts (total, active, blocked, positive closures)
    - BER counts (total, pending, approved)
    - PDO counts (total, finalized)
    - WRAP counts (total, accepted)
    - Settlement statistics (rate, avg time, pending)
    - Ledger integrity status
    
    **Mode**: READ-ONLY
    **Authority**: Public (dashboard consumption)
    """,
    responses={
        200: {
            "description": "Governance health metrics",
            "content": {
                "application/json": {
                    "example": {
                        "metrics": {
                            "total_pacs": 42,
                            "active_pacs": 3,
                            "blocked_pacs": 0,
                            "positive_closures": 39,
                            "total_bers": 39,
                            "pending_bers": 0,
                            "approved_bers": 39,
                            "total_pdos": 39,
                            "finalized_pdos": 39,
                            "total_wraps": 39,
                            "accepted_wraps": 39,
                            "settlement_rate": 92.9,
                            "avg_settlement_time_ms": 180000,
                            "pending_settlements": 3,
                            "ledger_integrity": "HEALTHY",
                            "last_ledger_sync": "2025-12-20T15:30:00Z",
                            "sequence_gaps": 0
                        },
                        "timestamp": "2025-12-20T15:30:00Z",
                        "success": True
                    }
                }
            }
        }
    }
)
async def get_governance_health() -> GovernanceHealthResponse:
    """
    Get governance health metrics.
    
    READ-ONLY aggregation from the canonical governance ledger.
    
    Returns:
        GovernanceHealthResponse with current metrics
    
    Raises:
        HTTPException: On failure to read ledger (fail-closed)
    """
    try:
        service = get_governance_health_service()
        metrics = service.get_health_metrics()
        
        return GovernanceHealthResponse(
            metrics=metrics,
            timestamp=datetime.now(timezone.utc),
            success=True,
        )
    except FileNotFoundError as e:
        logger.error(f"Ledger not found: {e}")
        raise HTTPException(
            status_code=503,
            detail="Governance ledger unavailable — fail-closed"
        )
    except Exception as e:
        logger.exception("Failed to get governance health metrics")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to aggregate governance health: {str(e)}"
        )


# =============================================================================
# SETTLEMENT CHAINS
# =============================================================================

@router.get(
    "/settlement-chains",
    response_model=SettlementChainsResponse,
    summary="Get Settlement Chains",
    description="""
    Returns recent settlement chains showing the PAC → BER → PDO → WRAP flow.
    
    Each chain represents a complete governance cycle from dispatch to settlement.
    
    **Mode**: READ-ONLY
    **Authority**: Public (dashboard consumption)
    """,
    responses={
        200: {
            "description": "Settlement chains",
            "content": {
                "application/json": {
                    "example": {
                        "chains": [
                            {
                                "chain_id": "chain-a1b2c3d4",
                                "pac_id": "PAC-CODY-P01",
                                "ber_id": "BER-CODY-P01",
                                "pdo_id": "PDO-CODY-P01",
                                "wrap_id": "WRAP-CODY-P01-20251220",
                                "current_stage": "LEDGER_COMMIT",
                                "status": "COMPLETED",
                                "started_at": "2025-12-20T14:00:00Z",
                                "completed_at": "2025-12-20T15:30:00Z",
                                "agent_gid": "GID-01",
                                "agent_name": "CODY"
                            }
                        ],
                        "total": 1,
                        "timestamp": "2025-12-20T15:30:00Z",
                        "success": True
                    }
                }
            }
        }
    }
)
async def get_settlement_chains(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of chains to return"
    )
) -> SettlementChainsResponse:
    """
    Get settlement chains.
    
    READ-ONLY aggregation from the canonical governance ledger.
    
    Args:
        limit: Maximum number of chains to return (1-100)
    
    Returns:
        SettlementChainsResponse with recent chains
    
    Raises:
        HTTPException: On failure to read ledger (fail-closed)
    """
    try:
        service = get_governance_health_service()
        chains = service.get_settlement_chains(limit=limit)
        
        return SettlementChainsResponse(
            chains=chains,
            total=len(chains),
            timestamp=datetime.now(timezone.utc),
            success=True,
        )
    except FileNotFoundError as e:
        logger.error(f"Ledger not found: {e}")
        raise HTTPException(
            status_code=503,
            detail="Governance ledger unavailable — fail-closed"
        )
    except Exception as e:
        logger.exception("Failed to get settlement chains")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to aggregate settlement chains: {str(e)}"
        )


# =============================================================================
# COMPLIANCE SUMMARY
# =============================================================================

@router.get(
    "/compliance-summary",
    response_model=ComplianceSummaryResponse,
    summary="Get Enterprise Compliance Summary",
    description="""
    Returns enterprise compliance mappings from Governance Doctrine V1.1.
    
    Maps governance artifacts (PAC, BER, PDO, WRAP, LEDGER) to:
    - SOX controls (§302, §404, §802)
    - SOC 2 controls (CC5.x, CC6.x, CC7.x, CC8.x)
    - NIST CSF controls (PR.x, DE.x, RS.x)
    - ISO 27001 controls (A.9.x, A.12.x, A.14.x)
    
    **Mode**: READ-ONLY
    **Authority**: Public (dashboard consumption)
    """,
    responses={
        200: {
            "description": "Compliance summary",
            "content": {
                "application/json": {
                    "example": {
                        "summary": {
                            "mappings": [
                                {
                                    "framework": "SOX",
                                    "control": "§302",
                                    "description": "Scope Definition",
                                    "artifact": "PAC"
                                }
                            ],
                            "last_audit_date": "2025-12-20",
                            "compliance_score": 100.0,
                            "framework_coverage": {
                                "sox": 100.0,
                                "soc2": 100.0,
                                "nist": 100.0,
                                "iso27001": 100.0
                            }
                        },
                        "timestamp": "2025-12-20T15:30:00Z",
                        "success": True
                    }
                }
            }
        }
    }
)
async def get_compliance_summary() -> ComplianceSummaryResponse:
    """
    Get enterprise compliance summary.
    
    READ-ONLY — returns static mappings from Doctrine V1.1.
    
    Returns:
        ComplianceSummaryResponse with compliance mappings
    """
    try:
        service = get_governance_health_service()
        summary = service.get_compliance_summary()
        
        return ComplianceSummaryResponse(
            summary=summary,
            timestamp=datetime.now(timezone.utc),
            success=True,
        )
    except Exception as e:
        logger.exception("Failed to get compliance summary")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve compliance summary: {str(e)}"
        )
