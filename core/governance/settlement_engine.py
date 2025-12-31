"""
═══════════════════════════════════════════════════════════════════════════════
ChainBridge Control Plane — Settlement Engine
PAC-JEFFREY-P08: Settlement End-to-End Execution
GOLD STANDARD · FAIL_CLOSED · ZERO DRIFT
═══════════════════════════════════════════════════════════════════════════════

Settlement Engine executes the full settlement lifecycle:
    PDO → Settlement Readiness → Ledger Commit → Final BER

SCHEMA REFERENCES:
- SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
- CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0
- LEDGER_COMMIT_ATTESTATION_SCHEMA@v1.0.0
- SETTLEMENT_LIFECYCLE_SCHEMA@v1.0.0

INVARIANTS (P08):
- INV-CP-021: Settlement requires PDO with APPROVED outcome
- INV-CP-022: Settlement readiness must pass before ledger commit
- INV-CP-023: Ledger commit required before BER FINAL
- INV-CP-024: Finality attestation seals settlement lifecycle

CONSTRAINTS:
- Deterministic execution only
- No human override
- Binary outcomes (PASS/FAIL)
- All checkpoints enforced

DAN (GID-07) — CI/CD Lane
CODY (GID-01) — Backend Lane
BENSON (GID-00) — Orchestration Lane
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# P08 SCHEMA CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SETTLEMENT_ENGINE_SCHEMA = "SETTLEMENT_ENGINE_SCHEMA@v1.0.0"
SETTLEMENT_LIFECYCLE_SCHEMA = "SETTLEMENT_LIFECYCLE_SCHEMA@v1.0.0"
LEDGER_COMMIT_ATTESTATION_SCHEMA = "LEDGER_COMMIT_ATTESTATION_SCHEMA@v1.0.0"
FINALITY_ATTESTATION_SCHEMA = "FINALITY_ATTESTATION_SCHEMA@v1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# P08 INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

P08_INVARIANTS = {
    "INV-CP-021": "Settlement requires PDO with APPROVED outcome",
    "INV-CP-022": "Settlement readiness must pass before ledger commit",
    "INV-CP-023": "Ledger commit required before BER FINAL",
    "INV-CP-024": "Finality attestation seals settlement lifecycle",
}


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT LIFECYCLE STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementPhase(str, Enum):
    """
    Settlement lifecycle phases per P08.
    
    State machine is DETERMINISTIC and ONE-WAY.
    No backwards transitions allowed.
    """
    INITIALIZED = "INITIALIZED"
    PDO_RECEIVED = "PDO_RECEIVED"
    PDO_APPROVED = "PDO_APPROVED"
    PDO_REJECTED = "PDO_REJECTED"
    READINESS_EVALUATING = "READINESS_EVALUATING"
    READINESS_ELIGIBLE = "READINESS_ELIGIBLE"
    READINESS_BLOCKED = "READINESS_BLOCKED"
    LEDGER_COMMITTING = "LEDGER_COMMITTING"
    LEDGER_COMMITTED = "LEDGER_COMMITTED"
    LEDGER_FAILED = "LEDGER_FAILED"
    FINALITY_ATTESTING = "FINALITY_ATTESTING"
    FINALITY_ATTESTED = "FINALITY_ATTESTED"
    SETTLEMENT_COMPLETE = "SETTLEMENT_COMPLETE"
    SETTLEMENT_FAILED = "SETTLEMENT_FAILED"


class SettlementOutcome(str, Enum):
    """Binary settlement outcome. No soft states."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# Valid phase transitions (deterministic state machine)
VALID_PHASE_TRANSITIONS: Dict[SettlementPhase, List[SettlementPhase]] = {
    SettlementPhase.INITIALIZED: [SettlementPhase.PDO_RECEIVED],
    SettlementPhase.PDO_RECEIVED: [
        SettlementPhase.PDO_APPROVED,
        SettlementPhase.PDO_REJECTED,
    ],
    SettlementPhase.PDO_APPROVED: [SettlementPhase.READINESS_EVALUATING],
    SettlementPhase.PDO_REJECTED: [SettlementPhase.SETTLEMENT_FAILED],
    SettlementPhase.READINESS_EVALUATING: [
        SettlementPhase.READINESS_ELIGIBLE,
        SettlementPhase.READINESS_BLOCKED,
    ],
    SettlementPhase.READINESS_ELIGIBLE: [SettlementPhase.LEDGER_COMMITTING],
    SettlementPhase.READINESS_BLOCKED: [SettlementPhase.SETTLEMENT_FAILED],
    SettlementPhase.LEDGER_COMMITTING: [
        SettlementPhase.LEDGER_COMMITTED,
        SettlementPhase.LEDGER_FAILED,
    ],
    SettlementPhase.LEDGER_COMMITTED: [SettlementPhase.FINALITY_ATTESTING],
    SettlementPhase.LEDGER_FAILED: [SettlementPhase.SETTLEMENT_FAILED],
    SettlementPhase.FINALITY_ATTESTING: [
        SettlementPhase.FINALITY_ATTESTED,
        SettlementPhase.SETTLEMENT_FAILED,
    ],
    SettlementPhase.FINALITY_ATTESTED: [SettlementPhase.SETTLEMENT_COMPLETE],
    SettlementPhase.SETTLEMENT_COMPLETE: [],  # Terminal state
    SettlementPhase.SETTLEMENT_FAILED: [],  # Terminal state
}


# ═══════════════════════════════════════════════════════════════════════════════
# PDO INTEGRATION (P08 Block 1)
# ═══════════════════════════════════════════════════════════════════════════════

class PDOOutcome(str, Enum):
    """PDO decision outcome."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class SettlementPDO:
    """
    Payment/Disbursement Order for settlement.
    
    INV-CP-021: Settlement requires PDO with APPROVED outcome.
    
    Schema: PDO_SETTLEMENT_SCHEMA@v1.0.0
    """
    pdo_id: str
    pac_id: str
    outcome: PDOOutcome
    amount: float
    currency: str
    source_account: str
    destination_account: str
    reasons: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    pdo_hash: str = ""
    
    def __post_init__(self):
        if not self.pdo_hash:
            self.pdo_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for PDO integrity."""
        data = {
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "outcome": self.outcome.value,
            "amount": self.amount,
            "currency": self.currency,
            "source_account": self.source_account,
            "destination_account": self.destination_account,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_approved(self) -> bool:
        """Check if PDO is approved. Binary only."""
        return self.outcome == PDOOutcome.APPROVED


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER COMMIT (P08 Block 9)
# ═══════════════════════════════════════════════════════════════════════════════

class LedgerCommitStatus(str, Enum):
    """Ledger commit status."""
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"


@dataclass
class LedgerCommitResult:
    """
    Ledger commit execution result.
    
    INV-CP-023: Ledger commit required before BER FINAL.
    
    Schema: LEDGER_COMMIT_ATTESTATION_SCHEMA@v1.0.0
    """
    commit_id: str
    pac_id: str
    settlement_id: str
    status: LedgerCommitStatus
    commit_hash: str = ""
    commit_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    commit_authority: str = "BENSON"  # GID-00
    block_number: Optional[int] = None
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    
    def __post_init__(self):
        if not self.commit_hash and self.status == LedgerCommitStatus.COMMITTED:
            self.commit_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for commit integrity."""
        data = {
            "commit_id": self.commit_id,
            "pac_id": self.pac_id,
            "settlement_id": self.settlement_id,
            "status": self.status.value,
            "commit_timestamp": self.commit_timestamp,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_committed(self) -> bool:
        """Check if commit succeeded."""
        return self.status == LedgerCommitStatus.COMMITTED


# ═══════════════════════════════════════════════════════════════════════════════
# FINALITY ATTESTATION (P08 Block 9)
# ═══════════════════════════════════════════════════════════════════════════════

class FinalityStatus(str, Enum):
    """Finality attestation status."""
    PENDING = "PENDING"
    ATTESTED = "ATTESTED"
    FAILED = "FAILED"


@dataclass
class FinalityAttestation:
    """
    Finality attestation sealing settlement lifecycle.
    
    INV-CP-024: Finality attestation seals settlement lifecycle.
    
    Schema: FINALITY_ATTESTATION_SCHEMA@v1.0.0
    """
    attestation_id: str
    pac_id: str
    settlement_id: str
    status: FinalityStatus
    pdo_hash: str
    readiness_verdict_hash: str
    ledger_commit_hash: str
    ber_hash: str
    attested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    attested_by: str = "BENSON"  # GID-00
    attestation_hash: str = ""
    
    def __post_init__(self):
        if not self.attestation_hash:
            self.attestation_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash for attestation integrity."""
        data = {
            "attestation_id": self.attestation_id,
            "pac_id": self.pac_id,
            "settlement_id": self.settlement_id,
            "status": self.status.value,
            "pdo_hash": self.pdo_hash,
            "readiness_verdict_hash": self.readiness_verdict_hash,
            "ledger_commit_hash": self.ledger_commit_hash,
            "ber_hash": self.ber_hash,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def is_attested(self) -> bool:
        """Check if finality is attested."""
        return self.status == FinalityStatus.ATTESTED


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT LIFECYCLE (P08 Block 5)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SettlementCheckpoint:
    """
    Settlement lifecycle checkpoint.
    
    Maps to P08 CHECKPOINT_INVARIANT_MAPPING.
    """
    checkpoint_id: str
    checkpoint_name: str
    phase: SettlementPhase
    passed: bool
    invariants_checked: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SettlementLifecycle:
    """
    Full settlement lifecycle state per P08.
    
    Schema: SETTLEMENT_LIFECYCLE_SCHEMA@v1.0.0
    
    Tracks all phases from PDO → Final BER.
    """
    settlement_id: str
    pac_id: str
    current_phase: SettlementPhase = SettlementPhase.INITIALIZED
    outcome: SettlementOutcome = SettlementOutcome.PENDING
    
    # Phase artifacts
    pdo: Optional[SettlementPDO] = None
    readiness_verdict_hash: Optional[str] = None
    ledger_commit: Optional[LedgerCommitResult] = None
    finality_attestation: Optional[FinalityAttestation] = None
    ber_hash: Optional[str] = None
    
    # Checkpoints
    checkpoints: List[SettlementCheckpoint] = field(default_factory=list)
    
    # Evidence collection
    agent_evidence: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Timestamps
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    
    # Lifecycle hash
    lifecycle_hash: str = ""
    
    def add_checkpoint(self, checkpoint: SettlementCheckpoint) -> None:
        """Add checkpoint to lifecycle."""
        self.checkpoints.append(checkpoint)
    
    def can_transition_to(self, target_phase: SettlementPhase) -> bool:
        """Check if transition to target phase is valid."""
        valid_targets = VALID_PHASE_TRANSITIONS.get(self.current_phase, [])
        return target_phase in valid_targets
    
    def transition_to(self, target_phase: SettlementPhase) -> bool:
        """
        Attempt phase transition.
        
        Returns True if transition succeeded, False otherwise.
        """
        if not self.can_transition_to(target_phase):
            logger.warning(
                f"Invalid phase transition: {self.current_phase} -> {target_phase}"
            )
            return False
        
        self.current_phase = target_phase
        
        # Check for terminal states
        if target_phase == SettlementPhase.SETTLEMENT_COMPLETE:
            self.outcome = SettlementOutcome.SUCCESS
            self.completed_at = datetime.now(timezone.utc).isoformat()
        elif target_phase == SettlementPhase.SETTLEMENT_FAILED:
            self.outcome = SettlementOutcome.FAILED
            self.completed_at = datetime.now(timezone.utc).isoformat()
        
        return True
    
    def is_terminal(self) -> bool:
        """Check if lifecycle is in terminal state."""
        return self.current_phase in [
            SettlementPhase.SETTLEMENT_COMPLETE,
            SettlementPhase.SETTLEMENT_FAILED,
        ]
    
    def compute_hash(self) -> str:
        """Compute deterministic hash for lifecycle integrity."""
        data = {
            "settlement_id": self.settlement_id,
            "pac_id": self.pac_id,
            "current_phase": self.current_phase.value,
            "outcome": self.outcome.value,
            "pdo_hash": self.pdo.pdo_hash if self.pdo else None,
            "readiness_verdict_hash": self.readiness_verdict_hash,
            "ledger_commit_hash": (
                self.ledger_commit.commit_hash if self.ledger_commit else None
            ),
            "finality_attestation_hash": (
                self.finality_attestation.attestation_hash
                if self.finality_attestation else None
            ),
            "ber_hash": self.ber_hash,
        }
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLEMENT ENGINE (P08 Core)
# ═══════════════════════════════════════════════════════════════════════════════

class SettlementEngine:
    """
    Settlement Engine — Full E2E lifecycle execution.
    
    PAC-JEFFREY-P08: Settlement End-to-End Execution
    
    Lifecycle: PDO → Settlement Readiness → Ledger Commit → Final BER
    
    INVARIANTS:
    - INV-CP-021: Settlement requires PDO with APPROVED outcome
    - INV-CP-022: Settlement readiness must pass before ledger commit
    - INV-CP-023: Ledger commit required before BER FINAL
    - INV-CP-024: Finality attestation seals settlement lifecycle
    
    FAIL_MODE: HARD_FAIL / FAIL_CLOSED
    """
    
    def __init__(self) -> None:
        """Initialize settlement engine."""
        self._activated = False
        self._fail_closed = True
        self._lifecycles: Dict[str, SettlementLifecycle] = {}
        logger.info("SettlementEngine initialized (P08)")
    
    def activate(self) -> bool:
        """
        Activate settlement engine.
        
        Must be called before any settlement operations.
        """
        self._activated = True
        logger.info("SettlementEngine activated")
        return True
    
    def is_activated(self) -> bool:
        """Check if engine is activated."""
        return self._activated
    
    def _check_activation(self) -> None:
        """
        Check engine activation.
        
        Raises RuntimeError if not activated (FAIL_CLOSED).
        """
        if not self._activated:
            raise RuntimeError(
                "SettlementEngine not activated. "
                "Call activate() before settlement operations. "
                "FAIL_CLOSED enforced."
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_lifecycle(self, pac_id: str) -> SettlementLifecycle:
        """
        Create new settlement lifecycle.
        
        Returns initialized lifecycle in INITIALIZED phase.
        """
        self._check_activation()
        
        settlement_id = f"SETTLEMENT-{uuid4().hex[:12].upper()}"
        lifecycle = SettlementLifecycle(
            settlement_id=settlement_id,
            pac_id=pac_id,
        )
        self._lifecycles[settlement_id] = lifecycle
        
        logger.info(f"Created settlement lifecycle: {settlement_id} for PAC {pac_id}")
        return lifecycle
    
    def get_lifecycle(self, settlement_id: str) -> Optional[SettlementLifecycle]:
        """Get lifecycle by ID."""
        return self._lifecycles.get(settlement_id)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: PDO PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def process_pdo(
        self,
        lifecycle: SettlementLifecycle,
        pdo: SettlementPDO,
    ) -> bool:
        """
        Process PDO for settlement.
        
        INV-CP-021: Settlement requires PDO with APPROVED outcome.
        
        Returns True if PDO accepted, False if rejected.
        """
        self._check_activation()
        
        # Transition to PDO_RECEIVED
        if not lifecycle.transition_to(SettlementPhase.PDO_RECEIVED):
            logger.error(f"Cannot process PDO: invalid phase {lifecycle.current_phase}")
            return False
        
        lifecycle.pdo = pdo
        
        # Add checkpoint
        lifecycle.add_checkpoint(SettlementCheckpoint(
            checkpoint_id=f"CP-{uuid4().hex[:8].upper()}",
            checkpoint_name="PDO_RECEIVED",
            phase=SettlementPhase.PDO_RECEIVED,
            passed=True,
            invariants_checked=["INV-CP-021"],
            evidence={"pdo_hash": pdo.pdo_hash},
        ))
        
        # Check PDO outcome
        if pdo.is_approved():
            lifecycle.transition_to(SettlementPhase.PDO_APPROVED)
            logger.info(f"PDO approved for settlement {lifecycle.settlement_id}")
            return True
        else:
            lifecycle.transition_to(SettlementPhase.PDO_REJECTED)
            lifecycle.transition_to(SettlementPhase.SETTLEMENT_FAILED)
            logger.warning(
                f"PDO rejected for settlement {lifecycle.settlement_id}: "
                f"{pdo.reasons}"
            )
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: SETTLEMENT READINESS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def evaluate_readiness(
        self,
        lifecycle: SettlementLifecycle,
        readiness_verdict_hash: str,
        is_eligible: bool,
    ) -> bool:
        """
        Evaluate settlement readiness.
        
        INV-CP-022: Settlement readiness must pass before ledger commit.
        
        Args:
            lifecycle: Settlement lifecycle
            readiness_verdict_hash: Hash of SettlementReadinessVerdict
            is_eligible: True if verdict is ELIGIBLE, False if BLOCKED
        
        Returns True if eligible, False if blocked.
        """
        self._check_activation()
        
        # Transition to evaluating
        if not lifecycle.transition_to(SettlementPhase.READINESS_EVALUATING):
            logger.error(
                f"Cannot evaluate readiness: invalid phase {lifecycle.current_phase}"
            )
            return False
        
        lifecycle.readiness_verdict_hash = readiness_verdict_hash
        
        # Add checkpoint
        lifecycle.add_checkpoint(SettlementCheckpoint(
            checkpoint_id=f"CP-{uuid4().hex[:8].upper()}",
            checkpoint_name="READINESS_EVALUATION",
            phase=SettlementPhase.READINESS_EVALUATING,
            passed=is_eligible,
            invariants_checked=["INV-CP-022"],
            evidence={"readiness_verdict_hash": readiness_verdict_hash},
        ))
        
        if is_eligible:
            lifecycle.transition_to(SettlementPhase.READINESS_ELIGIBLE)
            logger.info(f"Settlement {lifecycle.settlement_id} is ELIGIBLE")
            return True
        else:
            lifecycle.transition_to(SettlementPhase.READINESS_BLOCKED)
            lifecycle.transition_to(SettlementPhase.SETTLEMENT_FAILED)
            logger.warning(f"Settlement {lifecycle.settlement_id} is BLOCKED")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: LEDGER COMMIT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute_ledger_commit(
        self,
        lifecycle: SettlementLifecycle,
        ber_hash: str,
    ) -> LedgerCommitResult:
        """
        Execute ledger commit.
        
        INV-CP-023: Ledger commit required before BER FINAL.
        
        Returns LedgerCommitResult with commit status.
        """
        self._check_activation()
        
        # Transition to committing
        if not lifecycle.transition_to(SettlementPhase.LEDGER_COMMITTING):
            raise RuntimeError(
                f"Cannot commit: invalid phase {lifecycle.current_phase}"
            )
        
        lifecycle.ber_hash = ber_hash
        
        # Create commit result (simulated - actual would interact with ledger)
        commit_result = LedgerCommitResult(
            commit_id=f"COMMIT-{uuid4().hex[:12].upper()}",
            pac_id=lifecycle.pac_id,
            settlement_id=lifecycle.settlement_id,
            status=LedgerCommitStatus.COMMITTED,
            block_number=1,
            transaction_id=f"TX-{uuid4().hex[:16].upper()}",
        )
        
        lifecycle.ledger_commit = commit_result
        
        # Add checkpoint
        lifecycle.add_checkpoint(SettlementCheckpoint(
            checkpoint_id=f"CP-{uuid4().hex[:8].upper()}",
            checkpoint_name="LEDGER_COMMIT",
            phase=SettlementPhase.LEDGER_COMMITTING,
            passed=commit_result.is_committed(),
            invariants_checked=["INV-CP-023"],
            evidence={
                "commit_hash": commit_result.commit_hash,
                "ber_hash": ber_hash,
            },
        ))
        
        if commit_result.is_committed():
            lifecycle.transition_to(SettlementPhase.LEDGER_COMMITTED)
            logger.info(
                f"Ledger commit succeeded for settlement {lifecycle.settlement_id}"
            )
        else:
            lifecycle.transition_to(SettlementPhase.LEDGER_FAILED)
            lifecycle.transition_to(SettlementPhase.SETTLEMENT_FAILED)
            logger.error(
                f"Ledger commit failed for settlement {lifecycle.settlement_id}: "
                f"{commit_result.failure_reason}"
            )
        
        return commit_result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 4: FINALITY ATTESTATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def attest_finality(
        self,
        lifecycle: SettlementLifecycle,
    ) -> FinalityAttestation:
        """
        Attest settlement finality.
        
        INV-CP-024: Finality attestation seals settlement lifecycle.
        
        Returns FinalityAttestation sealing the lifecycle.
        """
        self._check_activation()
        
        # Transition to attesting
        if not lifecycle.transition_to(SettlementPhase.FINALITY_ATTESTING):
            raise RuntimeError(
                f"Cannot attest: invalid phase {lifecycle.current_phase}"
            )
        
        # Validate all preconditions
        if not lifecycle.pdo:
            raise RuntimeError("Cannot attest: PDO missing")
        if not lifecycle.readiness_verdict_hash:
            raise RuntimeError("Cannot attest: readiness verdict missing")
        if not lifecycle.ledger_commit:
            raise RuntimeError("Cannot attest: ledger commit missing")
        if not lifecycle.ber_hash:
            raise RuntimeError("Cannot attest: BER hash missing")
        
        # Create finality attestation
        attestation = FinalityAttestation(
            attestation_id=f"FINALITY-{uuid4().hex[:12].upper()}",
            pac_id=lifecycle.pac_id,
            settlement_id=lifecycle.settlement_id,
            status=FinalityStatus.ATTESTED,
            pdo_hash=lifecycle.pdo.pdo_hash,
            readiness_verdict_hash=lifecycle.readiness_verdict_hash,
            ledger_commit_hash=lifecycle.ledger_commit.commit_hash,
            ber_hash=lifecycle.ber_hash,
        )
        
        lifecycle.finality_attestation = attestation
        
        # Add checkpoint
        lifecycle.add_checkpoint(SettlementCheckpoint(
            checkpoint_id=f"CP-{uuid4().hex[:8].upper()}",
            checkpoint_name="FINALITY_ATTESTATION",
            phase=SettlementPhase.FINALITY_ATTESTING,
            passed=attestation.is_attested(),
            invariants_checked=["INV-CP-024"],
            evidence={"attestation_hash": attestation.attestation_hash},
        ))
        
        if attestation.is_attested():
            lifecycle.transition_to(SettlementPhase.FINALITY_ATTESTED)
            lifecycle.transition_to(SettlementPhase.SETTLEMENT_COMPLETE)
            lifecycle.lifecycle_hash = lifecycle.compute_hash()
            logger.info(
                f"Settlement {lifecycle.settlement_id} COMPLETE. "
                f"Lifecycle hash: {lifecycle.lifecycle_hash}"
            )
        else:
            lifecycle.transition_to(SettlementPhase.SETTLEMENT_FAILED)
            logger.error(
                f"Finality attestation failed for settlement {lifecycle.settlement_id}"
            )
        
        return attestation
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FULL LIFECYCLE EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute_full_lifecycle(
        self,
        pac_id: str,
        pdo: SettlementPDO,
        readiness_verdict_hash: str,
        is_eligible: bool,
        ber_hash: str,
    ) -> SettlementLifecycle:
        """
        Execute full settlement lifecycle in one call.
        
        Lifecycle: PDO → Settlement Readiness → Ledger Commit → Final BER
        
        This is the canonical entry point for P08 settlement execution.
        
        Returns completed SettlementLifecycle (SUCCESS or FAILED).
        """
        self._check_activation()
        
        # Create lifecycle
        lifecycle = self.create_lifecycle(pac_id)
        
        # Phase 1: PDO
        if not self.process_pdo(lifecycle, pdo):
            return lifecycle  # Failed at PDO
        
        # Phase 2: Readiness
        if not self.evaluate_readiness(lifecycle, readiness_verdict_hash, is_eligible):
            return lifecycle  # Failed at readiness
        
        # Phase 3: Ledger commit
        commit_result = self.execute_ledger_commit(lifecycle, ber_hash)
        if not commit_result.is_committed():
            return lifecycle  # Failed at ledger commit
        
        # Phase 4: Finality
        self.attest_finality(lifecycle)
        
        return lifecycle
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-AGENT EVIDENCE COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def collect_agent_evidence(
        self,
        lifecycle: SettlementLifecycle,
        agent_gid: str,
        evidence: Dict[str, Any],
    ) -> None:
        """
        Collect evidence from an agent.
        
        Per P08 Block 4: Multi-agent evidence collection.
        """
        self._check_activation()
        lifecycle.agent_evidence[agent_gid] = {
            **evidence,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Collected evidence from agent {agent_gid}")
    
    def get_lifecycle_summary(
        self,
        lifecycle: SettlementLifecycle,
    ) -> Dict[str, Any]:
        """Get human-readable lifecycle summary."""
        return {
            "settlement_id": lifecycle.settlement_id,
            "pac_id": lifecycle.pac_id,
            "current_phase": lifecycle.current_phase.value,
            "outcome": lifecycle.outcome.value,
            "is_terminal": lifecycle.is_terminal(),
            "checkpoints_passed": len([
                cp for cp in lifecycle.checkpoints if cp.passed
            ]),
            "total_checkpoints": len(lifecycle.checkpoints),
            "created_at": lifecycle.created_at,
            "completed_at": lifecycle.completed_at,
            "lifecycle_hash": lifecycle.lifecycle_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_settlement_engine: Optional[SettlementEngine] = None


def get_settlement_engine() -> SettlementEngine:
    """Get or create singleton SettlementEngine instance."""
    global _settlement_engine
    if _settlement_engine is None:
        _settlement_engine = SettlementEngine()
    return _settlement_engine


def reset_settlement_engine() -> None:
    """Reset singleton for testing."""
    global _settlement_engine
    _settlement_engine = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_settlement_pdo(
    pac_id: str,
    amount: float,
    currency: str,
    source_account: str,
    destination_account: str,
    approved: bool = True,
    reasons: Optional[List[str]] = None,
) -> SettlementPDO:
    """Create a SettlementPDO for testing/convenience."""
    return SettlementPDO(
        pdo_id=f"PDO-{uuid4().hex[:12].upper()}",
        pac_id=pac_id,
        outcome=PDOOutcome.APPROVED if approved else PDOOutcome.REJECTED,
        amount=amount,
        currency=currency,
        source_account=source_account,
        destination_account=destination_account,
        reasons=reasons or [],
    )
