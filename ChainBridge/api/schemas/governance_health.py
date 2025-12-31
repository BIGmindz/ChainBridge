"""
Governance Health Schemas — PAC-CODY-P01-GOVERNANCE-HEALTH-BACKEND-AGGREGATION-01

Pydantic models for governance health API responses.
All models are READ-ONLY — no mutation operations.

Authority: CODY (GID-01)
Dispatch: PAC-BENSON-EXEC-P61
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class ArtifactStatus(str, Enum):
    """Status of governance artifacts in settlement flow."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


class SettlementStage(str, Enum):
    """Stage in the PAC → BER → PDO → WRAP settlement flow."""
    PAC_DISPATCH = "PAC_DISPATCH"
    AGENT_EXECUTION = "AGENT_EXECUTION"
    BER_GENERATION = "BER_GENERATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PDO_FINALIZATION = "PDO_FINALIZATION"
    WRAP_GENERATION = "WRAP_GENERATION"
    WRAP_ACCEPTED = "WRAP_ACCEPTED"
    LEDGER_COMMIT = "LEDGER_COMMIT"


class ChainStatus(str, Enum):
    """Status of a settlement chain."""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class LedgerIntegrity(str, Enum):
    """Health status of the governance ledger."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class ComplianceFramework(str, Enum):
    """Enterprise compliance frameworks."""
    SOX = "SOX"
    SOC2 = "SOC2"
    NIST_CSF = "NIST_CSF"
    ISO_27001 = "ISO_27001"


class GovernanceArtifact(str, Enum):
    """Types of governance artifacts."""
    PAC = "PAC"
    BER = "BER"
    PDO = "PDO"
    WRAP = "WRAP"
    LEDGER = "LEDGER"


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class GovernanceHealthMetrics(BaseModel):
    """Governance health metrics for dashboard."""
    
    # PAC metrics
    total_pacs: int = Field(..., description="Total PACs in ledger")
    active_pacs: int = Field(..., description="PACs currently in execution")
    blocked_pacs: int = Field(..., description="PACs blocked for correction")
    positive_closures: int = Field(..., description="PACs with positive closure")
    
    # BER metrics
    total_bers: int = Field(..., description="Total BERs generated")
    pending_bers: int = Field(..., description="BERs awaiting review")
    approved_bers: int = Field(..., description="BERs approved for PDO")
    
    # PDO metrics
    total_pdos: int = Field(..., description="Total PDOs created")
    finalized_pdos: int = Field(..., description="PDOs finalized")
    
    # WRAP metrics
    total_wraps: int = Field(..., description="Total WRAPs generated")
    accepted_wraps: int = Field(..., description="WRAPs accepted to ledger")
    
    # Settlement metrics
    settlement_rate: float = Field(..., description="Percentage of PACs reaching WRAP_ACCEPTED")
    avg_settlement_time_ms: int = Field(..., description="Average settlement time in milliseconds")
    pending_settlements: int = Field(..., description="Settlements in progress")
    
    # Health indicators
    ledger_integrity: LedgerIntegrity = Field(..., description="Ledger health status")
    last_ledger_sync: datetime = Field(..., description="Last ledger sync timestamp")
    sequence_gaps: int = Field(..., description="Number of sequence gaps detected")


class SettlementFlowNode(BaseModel):
    """A node in the settlement flow."""
    stage: SettlementStage = Field(..., description="Settlement stage")
    status: ArtifactStatus = Field(..., description="Status at this stage")
    timestamp: Optional[datetime] = Field(None, description="When stage was reached")
    artifact_id: Optional[str] = Field(None, description="Associated artifact ID")
    authority: Optional[str] = Field(None, description="Authority at this stage")
    details: Optional[str] = Field(None, description="Additional details")


class SettlementChain(BaseModel):
    """A settlement chain from PAC to WRAP."""
    chain_id: str = Field(..., description="Unique chain identifier")
    pac_id: str = Field(..., description="PAC ID")
    ber_id: Optional[str] = Field(None, description="BER ID if generated")
    pdo_id: Optional[str] = Field(None, description="PDO ID if finalized")
    wrap_id: Optional[str] = Field(None, description="WRAP ID if accepted")
    current_stage: SettlementStage = Field(..., description="Current settlement stage")
    status: ChainStatus = Field(..., description="Overall chain status")
    started_at: datetime = Field(..., description="When chain started")
    completed_at: Optional[datetime] = Field(None, description="When chain completed")
    nodes: List[SettlementFlowNode] = Field(..., description="Flow nodes")
    agent_gid: str = Field(..., description="Agent GID")
    agent_name: str = Field(..., description="Agent name")


class EnterpriseMapping(BaseModel):
    """Mapping of governance artifact to compliance framework."""
    framework: ComplianceFramework = Field(..., description="Compliance framework")
    control: str = Field(..., description="Control identifier")
    description: str = Field(..., description="Control description")
    artifact: GovernanceArtifact = Field(..., description="Mapped artifact type")


class FrameworkCoverage(BaseModel):
    """Coverage percentage per framework."""
    sox: float = Field(..., description="SOX coverage percentage")
    soc2: float = Field(..., description="SOC 2 coverage percentage")
    nist: float = Field(..., description="NIST CSF coverage percentage")
    iso27001: float = Field(..., description="ISO 27001 coverage percentage")


class EnterpriseComplianceSummary(BaseModel):
    """Enterprise compliance summary."""
    mappings: List[EnterpriseMapping] = Field(..., description="All compliance mappings")
    last_audit_date: Optional[str] = Field(None, description="Last audit date")
    compliance_score: float = Field(..., description="Overall compliance score (0-100)")
    framework_coverage: FrameworkCoverage = Field(..., description="Coverage per framework")


# =============================================================================
# API RESPONSE WRAPPERS
# =============================================================================


class GovernanceHealthResponse(BaseModel):
    """Response wrapper for governance health endpoint."""
    success: bool = Field(True, description="Request success status")
    data: GovernanceHealthMetrics = Field(..., description="Health metrics")
    timestamp: datetime = Field(..., description="Response timestamp")
    source: str = Field("GOVERNANCE_LEDGER", description="Data source")


class SettlementChainsResponse(BaseModel):
    """Response wrapper for settlement chains endpoint."""
    success: bool = Field(True, description="Request success status")
    data: List[SettlementChain] = Field(..., description="Settlement chains")
    total: int = Field(..., description="Total chains")
    timestamp: datetime = Field(..., description="Response timestamp")


class ComplianceSummaryResponse(BaseModel):
    """Response wrapper for compliance summary endpoint."""
    success: bool = Field(True, description="Request success status")
    data: EnterpriseComplianceSummary = Field(..., description="Compliance summary")
    timestamp: datetime = Field(..., description="Response timestamp")
    doctrine_version: str = Field("1.1.0", description="Governance Doctrine version")


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = Field(False, description="Request failed")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(..., description="Error timestamp")
