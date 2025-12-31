# ═══════════════════════════════════════════════════════════════════════════════
# SOP Library v1 — Enterprise Standard Operating Procedures
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: PAX (GID-05) — Product & SOP Design
# ═══════════════════════════════════════════════════════════════════════════════

"""
Enterprise SOP Library — 10 Canonical Operator Actions

PURPOSE:
    Provide enterprise-grade Standard Operating Procedures (SOPs) for operators.
    Each SOP is a documented, auditable, reversible procedure with validation.

SOP CATEGORIES:
    1. SHIPMENT OPERATIONS (SOP-SHIP-*)
    2. PAYMENT OPERATIONS (SOP-PAY-*)
    3. RISK OPERATIONS (SOP-RISK-*)
    4. GOVERNANCE OPERATIONS (SOP-GOV-*)
    5. SYSTEM OPERATIONS (SOP-SYS-*)

INVARIANTS:
    INV-SOP-001: All SOPs must be documented with preconditions
    INV-SOP-002: All SOPs must produce audit trail entries
    INV-SOP-003: Critical SOPs require dual-approval workflow
    INV-SOP-004: SOP execution is idempotent where possible
    INV-SOP-005: SOP rollback procedures must exist for reversible actions

EXECUTION MODE: PARALLEL
LANE: PRODUCT (GID-05)
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type


# ═══════════════════════════════════════════════════════════════════════════════
# SOP CLASSIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class SOPCategory(Enum):
    """SOP category classifications."""

    SHIPMENT = "SHIPMENT"
    PAYMENT = "PAYMENT"
    RISK = "RISK"
    GOVERNANCE = "GOVERNANCE"
    SYSTEM = "SYSTEM"


class SOPSeverity(Enum):
    """SOP severity levels affecting approval requirements."""

    LOW = "LOW"  # Self-approval allowed
    MEDIUM = "MEDIUM"  # Single approval required
    HIGH = "HIGH"  # Dual approval required
    CRITICAL = "CRITICAL"  # Management + dual approval


class SOPReversibility(Enum):
    """SOP reversibility classification."""

    REVERSIBLE = "REVERSIBLE"  # Can be rolled back
    PARTIAL = "PARTIAL"  # Partial rollback possible
    IRREVERSIBLE = "IRREVERSIBLE"  # Cannot be undone


class SOPExecutionState(Enum):
    """SOP execution state machine."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"


# ═══════════════════════════════════════════════════════════════════════════════
# SOP METADATA AND CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SOPPrecondition:
    """Precondition that must be met before SOP execution."""

    condition_id: str
    description: str
    validation_rule: str
    error_message: str


@dataclass(frozen=True)
class SOPPostcondition:
    """Expected state after successful SOP execution."""

    condition_id: str
    description: str
    validation_rule: str


@dataclass(frozen=True)
class SOPDefinition:
    """
    Canonical SOP definition — immutable specification.

    INV-SOP-001: All SOPs must be documented with preconditions
    """

    sop_id: str
    name: str
    description: str
    category: SOPCategory
    severity: SOPSeverity
    reversibility: SOPReversibility
    version: str
    preconditions: tuple[SOPPrecondition, ...]
    postconditions: tuple[SOPPostcondition, ...]
    estimated_duration_seconds: int
    requires_maintenance_window: bool
    audit_retention_days: int = 365
    documentation_url: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate SOP definition on creation."""
        if not self.sop_id.startswith("SOP-"):
            raise ValueError(f"SOP ID must start with 'SOP-': {self.sop_id}")
        if not self.preconditions:
            raise ValueError(f"SOP must have at least one precondition: {self.sop_id}")

    def compute_definition_hash(self) -> str:
        """Compute hash of SOP definition for versioning."""
        content = json.dumps(
            {
                "sop_id": self.sop_id,
                "name": self.name,
                "version": self.version,
                "category": self.category.value,
                "severity": self.severity.value,
                "preconditions": [p.condition_id for p in self.preconditions],
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════════
# SOP EXECUTION RECORD
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SOPApproval:
    """Approval record for SOP execution."""

    approver_id: str
    approver_role: str
    approved_at: datetime
    approval_notes: Optional[str] = None


@dataclass
class SOPExecutionRecord:
    """
    Execution record for SOP audit trail.

    INV-SOP-002: All SOPs must produce audit trail entries
    """

    execution_id: str
    sop_id: str
    sop_version: str
    initiator_id: str
    initiated_at: datetime
    state: SOPExecutionState
    approvals: List[SOPApproval] = field(default_factory=list)
    input_parameters: Dict[str, Any] = field(default_factory=dict)
    output_results: Dict[str, Any] = field(default_factory=dict)
    precondition_checks: Dict[str, bool] = field(default_factory=dict)
    postcondition_checks: Dict[str, bool] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_execution_id: Optional[str] = None

    def compute_audit_hash(self) -> str:
        """Compute hash for audit integrity verification."""
        content = json.dumps(
            {
                "execution_id": self.execution_id,
                "sop_id": self.sop_id,
                "initiator_id": self.initiator_id,
                "initiated_at": self.initiated_at.isoformat(),
                "state": self.state.value,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# 10 ENTERPRISE SOP DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

SOP_SHIP_001_HOLD = SOPDefinition(
    sop_id="SOP-SHIP-001",
    name="Place Shipment on Hold",
    description="Places a shipment on administrative hold, preventing further processing until released.",
    category=SOPCategory.SHIPMENT,
    severity=SOPSeverity.MEDIUM,
    reversibility=SOPReversibility.REVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-SHIP-001-01",
            description="Shipment must exist and be active",
            validation_rule="shipment.status IN ['ACTIVE', 'IN_TRANSIT', 'PENDING']",
            error_message="Shipment not found or already in terminal state",
        ),
        SOPPrecondition(
            condition_id="PRE-SHIP-001-02",
            description="No pending payments in settlement",
            validation_rule="shipment.pending_settlements == 0",
            error_message="Cannot hold shipment with pending settlements",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-SHIP-001-01",
            description="Shipment status is HOLD",
            validation_rule="shipment.status == 'HOLD'",
        ),
    ),
    estimated_duration_seconds=5,
    requires_maintenance_window=False,
    documentation_url="/docs/sop/ship-001-hold",
)

SOP_SHIP_002_RELEASE = SOPDefinition(
    sop_id="SOP-SHIP-002",
    name="Release Shipment from Hold",
    description="Releases a shipment from administrative hold, resuming normal processing.",
    category=SOPCategory.SHIPMENT,
    severity=SOPSeverity.MEDIUM,
    reversibility=SOPReversibility.REVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-SHIP-002-01",
            description="Shipment must be on hold",
            validation_rule="shipment.status == 'HOLD'",
            error_message="Shipment is not on hold",
        ),
        SOPPrecondition(
            condition_id="PRE-SHIP-002-02",
            description="Hold reason must be resolved",
            validation_rule="shipment.hold_reason_resolved == True",
            error_message="Hold reason has not been marked as resolved",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-SHIP-002-01",
            description="Shipment status is restored to pre-hold state",
            validation_rule="shipment.status == shipment.pre_hold_status",
        ),
    ),
    estimated_duration_seconds=5,
    requires_maintenance_window=False,
    documentation_url="/docs/sop/ship-002-release",
)

# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

SOP_PAY_001_SETTLE = SOPDefinition(
    sop_id="SOP-PAY-001",
    name="Initiate Settlement",
    description="Initiates settlement for approved payments against verified deliveries.",
    category=SOPCategory.PAYMENT,
    severity=SOPSeverity.HIGH,
    reversibility=SOPReversibility.PARTIAL,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-PAY-001-01",
            description="Payment must be approved",
            validation_rule="payment.status == 'APPROVED'",
            error_message="Payment is not in approved state",
        ),
        SOPPrecondition(
            condition_id="PRE-PAY-001-02",
            description="Delivery verification complete",
            validation_rule="payment.delivery_verified == True",
            error_message="Delivery has not been verified",
        ),
        SOPPrecondition(
            condition_id="PRE-PAY-001-03",
            description="Sufficient funds in settlement account",
            validation_rule="account.available_balance >= payment.amount",
            error_message="Insufficient funds for settlement",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-PAY-001-01",
            description="Payment status is SETTLING",
            validation_rule="payment.status == 'SETTLING'",
        ),
    ),
    estimated_duration_seconds=30,
    requires_maintenance_window=False,
    audit_retention_days=2555,  # 7 years financial records
    documentation_url="/docs/sop/pay-001-settle",
)

SOP_PAY_002_REFUND = SOPDefinition(
    sop_id="SOP-PAY-002",
    name="Process Refund",
    description="Processes a refund for a completed payment due to dispute or error.",
    category=SOPCategory.PAYMENT,
    severity=SOPSeverity.CRITICAL,
    reversibility=SOPReversibility.IRREVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-PAY-002-01",
            description="Original payment must be completed",
            validation_rule="payment.status == 'COMPLETED'",
            error_message="Can only refund completed payments",
        ),
        SOPPrecondition(
            condition_id="PRE-PAY-002-02",
            description="Refund window not expired",
            validation_rule="payment.completed_at + 90_days > now()",
            error_message="Refund window has expired (90 days)",
        ),
        SOPPrecondition(
            condition_id="PRE-PAY-002-03",
            description="Approved dispute or error documentation",
            validation_rule="refund_request.documentation_verified == True",
            error_message="Refund request documentation not verified",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-PAY-002-01",
            description="Refund transaction created",
            validation_rule="refund.status == 'INITIATED'",
        ),
    ),
    estimated_duration_seconds=60,
    requires_maintenance_window=False,
    audit_retention_days=2555,
    documentation_url="/docs/sop/pay-002-refund",
)

# ─────────────────────────────────────────────────────────────────────────────
# RISK OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

SOP_RISK_001_ESCALATE = SOPDefinition(
    sop_id="SOP-RISK-001",
    name="Escalate Risk Alert",
    description="Escalates a risk alert to senior operations for review and action.",
    category=SOPCategory.RISK,
    severity=SOPSeverity.MEDIUM,
    reversibility=SOPReversibility.REVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-RISK-001-01",
            description="Risk alert must be active",
            validation_rule="alert.status == 'ACTIVE'",
            error_message="Alert is not active",
        ),
        SOPPrecondition(
            condition_id="PRE-RISK-001-02",
            description="Alert not already escalated",
            validation_rule="alert.escalation_level < 'SENIOR'",
            error_message="Alert is already at senior escalation level",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-RISK-001-01",
            description="Alert escalation level increased",
            validation_rule="alert.escalation_level == next_level",
        ),
    ),
    estimated_duration_seconds=10,
    requires_maintenance_window=False,
    documentation_url="/docs/sop/risk-001-escalate",
)

SOP_RISK_002_OVERRIDE = SOPDefinition(
    sop_id="SOP-RISK-002",
    name="Override Risk Score",
    description="Manually overrides an automated risk score with documented justification.",
    category=SOPCategory.RISK,
    severity=SOPSeverity.HIGH,
    reversibility=SOPReversibility.REVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-RISK-002-01",
            description="Entity must have automated risk score",
            validation_rule="entity.risk_score IS NOT NULL",
            error_message="No automated risk score exists",
        ),
        SOPPrecondition(
            condition_id="PRE-RISK-002-02",
            description="Override justification provided",
            validation_rule="override_request.justification.length >= 50",
            error_message="Override justification must be at least 50 characters",
        ),
        SOPPrecondition(
            condition_id="PRE-RISK-002-03",
            description="Supporting documentation attached",
            validation_rule="override_request.attachments.count >= 1",
            error_message="At least one supporting document required",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-RISK-002-01",
            description="Risk score updated with override flag",
            validation_rule="entity.risk_score_override == True",
        ),
    ),
    estimated_duration_seconds=15,
    requires_maintenance_window=False,
    documentation_url="/docs/sop/risk-002-override",
)

# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

SOP_GOV_001_AGENT_SUSPEND = SOPDefinition(
    sop_id="SOP-GOV-001",
    name="Suspend Agent Execution",
    description="Suspends an agent's execution privileges pending review.",
    category=SOPCategory.GOVERNANCE,
    severity=SOPSeverity.CRITICAL,
    reversibility=SOPReversibility.REVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-GOV-001-01",
            description="Agent must be active",
            validation_rule="agent.status == 'ACTIVE'",
            error_message="Agent is not in active state",
        ),
        SOPPrecondition(
            condition_id="PRE-GOV-001-02",
            description="Suspension reason documented",
            validation_rule="suspension_request.reason.length >= 100",
            error_message="Suspension reason must be detailed (100+ chars)",
        ),
        SOPPrecondition(
            condition_id="PRE-GOV-001-03",
            description="No in-flight PAC execution",
            validation_rule="agent.current_pac_id IS NULL OR agent.pac_interruptible == True",
            error_message="Agent has non-interruptible PAC in progress",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-GOV-001-01",
            description="Agent status is SUSPENDED",
            validation_rule="agent.status == 'SUSPENDED'",
        ),
    ),
    estimated_duration_seconds=10,
    requires_maintenance_window=False,
    documentation_url="/docs/sop/gov-001-agent-suspend",
)

SOP_GOV_002_PAC_ABORT = SOPDefinition(
    sop_id="SOP-GOV-002",
    name="Abort PAC Execution",
    description="Emergency abort of an in-progress PAC execution.",
    category=SOPCategory.GOVERNANCE,
    severity=SOPSeverity.CRITICAL,
    reversibility=SOPReversibility.PARTIAL,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-GOV-002-01",
            description="PAC must be in executing state",
            validation_rule="pac.state == 'EXECUTING'",
            error_message="PAC is not currently executing",
        ),
        SOPPrecondition(
            condition_id="PRE-GOV-002-02",
            description="Abort reason with impact assessment",
            validation_rule="abort_request.impact_assessment IS NOT NULL",
            error_message="Impact assessment required for PAC abort",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-GOV-002-01",
            description="PAC state is ABORTED",
            validation_rule="pac.state == 'ABORTED'",
        ),
    ),
    estimated_duration_seconds=30,
    requires_maintenance_window=False,
    documentation_url="/docs/sop/gov-002-pac-abort",
)

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

SOP_SYS_001_MAINTENANCE = SOPDefinition(
    sop_id="SOP-SYS-001",
    name="Enter Maintenance Mode",
    description="Places the system in maintenance mode with graceful connection draining.",
    category=SOPCategory.SYSTEM,
    severity=SOPSeverity.CRITICAL,
    reversibility=SOPReversibility.REVERSIBLE,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-SYS-001-01",
            description="System not already in maintenance",
            validation_rule="system.maintenance_mode == False",
            error_message="System is already in maintenance mode",
        ),
        SOPPrecondition(
            condition_id="PRE-SYS-001-02",
            description="Maintenance window scheduled",
            validation_rule="maintenance.scheduled_window IS NOT NULL",
            error_message="No maintenance window has been scheduled",
        ),
        SOPPrecondition(
            condition_id="PRE-SYS-001-03",
            description="Stakeholder notification sent",
            validation_rule="maintenance.notifications_sent == True",
            error_message="Stakeholder notifications have not been sent",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-SYS-001-01",
            description="System is in maintenance mode",
            validation_rule="system.maintenance_mode == True",
        ),
    ),
    estimated_duration_seconds=120,
    requires_maintenance_window=True,
    documentation_url="/docs/sop/sys-001-maintenance",
)

SOP_SYS_002_FAILOVER = SOPDefinition(
    sop_id="SOP-SYS-002",
    name="Initiate Regional Failover",
    description="Initiates failover to secondary region in case of primary region failure.",
    category=SOPCategory.SYSTEM,
    severity=SOPSeverity.CRITICAL,
    reversibility=SOPReversibility.PARTIAL,
    version="1.0.0",
    preconditions=(
        SOPPrecondition(
            condition_id="PRE-SYS-002-01",
            description="Primary region health check failing",
            validation_rule="primary_region.health_check_failures >= 3",
            error_message="Primary region is still healthy",
        ),
        SOPPrecondition(
            condition_id="PRE-SYS-002-02",
            description="Secondary region is healthy",
            validation_rule="secondary_region.status == 'HEALTHY'",
            error_message="Secondary region is not healthy for failover",
        ),
        SOPPrecondition(
            condition_id="PRE-SYS-002-03",
            description="Data replication lag within threshold",
            validation_rule="replication_lag_seconds <= 30",
            error_message="Replication lag exceeds threshold (30s)",
        ),
    ),
    postconditions=(
        SOPPostcondition(
            condition_id="POST-SYS-002-01",
            description="Traffic routing to secondary region",
            validation_rule="traffic_router.active_region == 'SECONDARY'",
        ),
    ),
    estimated_duration_seconds=300,
    requires_maintenance_window=False,  # Emergency procedure
    documentation_url="/docs/sop/sys-002-failover",
)


# ═══════════════════════════════════════════════════════════════════════════════
# SOP REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class SOPRegistry:
    """
    Enterprise SOP Registry — Singleton for SOP management.

    Provides:
    - SOP lookup by ID
    - Category filtering
    - Severity filtering
    - Audit integration
    """

    _instance: Optional["SOPRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "SOPRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if SOPRegistry._initialized:
            return
        SOPRegistry._initialized = True

        self._sops: Dict[str, SOPDefinition] = {}
        self._register_default_sops()

    def _register_default_sops(self) -> None:
        """Register the 10 enterprise SOPs."""
        default_sops = [
            SOP_SHIP_001_HOLD,
            SOP_SHIP_002_RELEASE,
            SOP_PAY_001_SETTLE,
            SOP_PAY_002_REFUND,
            SOP_RISK_001_ESCALATE,
            SOP_RISK_002_OVERRIDE,
            SOP_GOV_001_AGENT_SUSPEND,
            SOP_GOV_002_PAC_ABORT,
            SOP_SYS_001_MAINTENANCE,
            SOP_SYS_002_FAILOVER,
        ]
        for sop in default_sops:
            self._sops[sop.sop_id] = sop

    def get(self, sop_id: str) -> Optional[SOPDefinition]:
        """Get SOP by ID."""
        return self._sops.get(sop_id)

    def get_all(self) -> List[SOPDefinition]:
        """Get all registered SOPs."""
        return list(self._sops.values())

    def get_by_category(self, category: SOPCategory) -> List[SOPDefinition]:
        """Get SOPs by category."""
        return [sop for sop in self._sops.values() if sop.category == category]

    def get_by_severity(self, severity: SOPSeverity) -> List[SOPDefinition]:
        """Get SOPs by severity level."""
        return [sop for sop in self._sops.values() if sop.severity == severity]

    def get_critical(self) -> List[SOPDefinition]:
        """Get all critical SOPs requiring dual approval."""
        return [
            sop
            for sop in self._sops.values()
            if sop.severity in (SOPSeverity.HIGH, SOPSeverity.CRITICAL)
        ]

    def requires_dual_approval(self, sop_id: str) -> bool:
        """
        Check if SOP requires dual approval.

        INV-SOP-003: Critical SOPs require dual-approval workflow
        """
        sop = self._sops.get(sop_id)
        if sop is None:
            return True  # Fail-safe: unknown SOPs require dual approval
        return sop.severity in (SOPSeverity.HIGH, SOPSeverity.CRITICAL)

    def count(self) -> int:
        """Return count of registered SOPs."""
        return len(self._sops)


# ═══════════════════════════════════════════════════════════════════════════════
# RISK SCORECARD — AGENT TRUST INDEX
# ═══════════════════════════════════════════════════════════════════════════════


class TrustDimension(Enum):
    """Dimensions of agent trust scoring."""

    EXECUTION_ACCURACY = "EXECUTION_ACCURACY"
    INVARIANT_COMPLIANCE = "INVARIANT_COMPLIANCE"
    RESPONSE_TIME = "RESPONSE_TIME"
    ERROR_RATE = "ERROR_RATE"
    GOVERNANCE_ADHERENCE = "GOVERNANCE_ADHERENCE"


@dataclass(frozen=True)
class TrustScore:
    """Individual trust score for a dimension."""

    dimension: TrustDimension
    score: float  # 0.0 - 1.0
    sample_count: int
    last_updated: datetime

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0: {self.score}")


@dataclass
class AgentTrustIndex:
    """
    Agent Trust Index — Risk scorecard for agent behavior.

    Tracks multiple dimensions of agent trustworthiness for
    operator visibility and governance decisions.
    """

    agent_id: str
    agent_name: str
    scores: Dict[TrustDimension, TrustScore] = field(default_factory=dict)
    overall_trust: float = 1.0  # Default to full trust
    trust_tier: str = "STANDARD"  # PROBATION, STANDARD, ELEVATED, TRUSTED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_score(
        self, dimension: TrustDimension, score: float, sample_count: int
    ) -> None:
        """Update a trust dimension score."""
        self.scores[dimension] = TrustScore(
            dimension=dimension,
            score=score,
            sample_count=sample_count,
            last_updated=datetime.now(timezone.utc),
        )
        self._recalculate_overall()
        self.updated_at = datetime.now(timezone.utc)

    def _recalculate_overall(self) -> None:
        """Recalculate overall trust score from dimensions."""
        if not self.scores:
            self.overall_trust = 1.0
            return

        # Weighted average with heavier weight on governance and invariants
        weights = {
            TrustDimension.GOVERNANCE_ADHERENCE: 2.0,
            TrustDimension.INVARIANT_COMPLIANCE: 2.0,
            TrustDimension.EXECUTION_ACCURACY: 1.5,
            TrustDimension.ERROR_RATE: 1.0,
            TrustDimension.RESPONSE_TIME: 0.5,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for dimension, trust_score in self.scores.items():
            weight = weights.get(dimension, 1.0)
            weighted_sum += trust_score.score * weight
            total_weight += weight

        self.overall_trust = weighted_sum / total_weight if total_weight > 0 else 1.0
        self._update_tier()

    def _update_tier(self) -> None:
        """Update trust tier based on overall score."""
        if self.overall_trust >= 0.95:
            self.trust_tier = "TRUSTED"
        elif self.overall_trust >= 0.80:
            self.trust_tier = "ELEVATED"
        elif self.overall_trust >= 0.60:
            self.trust_tier = "STANDARD"
        else:
            self.trust_tier = "PROBATION"

    def get_summary(self) -> Dict[str, Any]:
        """Get summary for UI display."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "overall_trust": round(self.overall_trust, 3),
            "trust_tier": self.trust_tier,
            "dimension_count": len(self.scores),
            "dimensions": {
                dim.value: {
                    "score": round(ts.score, 3),
                    "samples": ts.sample_count,
                }
                for dim, ts in self.scores.items()
            },
            "updated_at": self.updated_at.isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "SOPCategory",
    "SOPSeverity",
    "SOPReversibility",
    "SOPExecutionState",
    "TrustDimension",
    # Data classes
    "SOPPrecondition",
    "SOPPostcondition",
    "SOPDefinition",
    "SOPApproval",
    "SOPExecutionRecord",
    "TrustScore",
    "AgentTrustIndex",
    # Registry
    "SOPRegistry",
    # SOP instances
    "SOP_SHIP_001_HOLD",
    "SOP_SHIP_002_RELEASE",
    "SOP_PAY_001_SETTLE",
    "SOP_PAY_002_REFUND",
    "SOP_RISK_001_ESCALATE",
    "SOP_RISK_002_OVERRIDE",
    "SOP_GOV_001_AGENT_SUSPEND",
    "SOP_GOV_002_PAC_ABORT",
    "SOP_SYS_001_MAINTENANCE",
    "SOP_SYS_002_FAILOVER",
]
