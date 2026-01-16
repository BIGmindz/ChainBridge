"""
Sandbox PDO Collector - Proof, Decision, Outcome Capture Layer
PAC-P752-GOV-SANDBOX-GOVERNANCE-EVOLUTION
TASK-02: Sandbox PDO Capture Layer (GID-01)

Captures complete PDO (Proof, Decision, Outcome) for all sandbox actions.
Enables governance evolution through observation WITHOUT production modification.

Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.

INVARIANTS ENFORCED:
- INV-SDGE-001: Sandbox data SHALL NOT modify production logic directly
- INV-SDGE-003: Audit trail completeness mandatory
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class DecisionType(Enum):
    """Types of governance decisions captured."""
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    ESCALATED = "ESCALATED"
    TIMEOUT = "TIMEOUT"


class OutcomeType(Enum):
    """Outcome types from sandbox execution."""
    EXECUTED = "EXECUTED"
    PREVENTED = "PREVENTED"
    PARTIAL = "PARTIAL"
    ERROR = "ERROR"


class CaptureMode(Enum):
    """Capture modes for PDO collection."""
    SANDBOX = "SANDBOX"
    REPLAY = "REPLAY"
    SIMULATION = "SIMULATION"


@dataclass
class Proof:
    """
    Proof component of PDO - evidence supporting the decision.
    """
    proof_id: str
    proof_type: str
    evidence: dict[str, Any]
    invariants_checked: list[str]
    hash: str = ""
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.hash:
            self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = json.dumps({
            "proof_id": self.proof_id,
            "proof_type": self.proof_type,
            "evidence": self.evidence,
            "invariants_checked": self.invariants_checked
        }, sort_keys=True, default=str)
        return f"sha3-256:{hashlib.sha3_256(data.encode()).hexdigest()[:32]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "proof_type": self.proof_type,
            "evidence": self.evidence,
            "invariants_checked": self.invariants_checked,
            "hash": self.hash,
            "captured_at": self.captured_at.isoformat()
        }


@dataclass
class Decision:
    """
    Decision component of PDO - governance decision made.
    """
    decision_id: str
    decision_type: DecisionType
    authority: str
    rules_applied: list[str]
    reasoning: str
    confidence: float
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "authority": self.authority,
            "rules_applied": self.rules_applied,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "decided_at": self.decided_at.isoformat()
        }


@dataclass
class Outcome:
    """
    Outcome component of PDO - result of the governance decision.
    """
    outcome_id: str
    outcome_type: OutcomeType
    effects: dict[str, Any]
    drift_detected: bool
    drift_score: float
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "outcome_type": self.outcome_type.value,
            "effects": self.effects,
            "drift_detected": self.drift_detected,
            "drift_score": self.drift_score,
            "completed_at": self.completed_at.isoformat()
        }


@dataclass
class PDORecord:
    """
    Complete PDO (Proof, Decision, Outcome) record.
    """
    pdo_id: str
    session_id: str
    capture_mode: CaptureMode
    proof: Proof
    decision: Decision
    outcome: Outcome
    context: dict[str, Any] = field(default_factory=dict)
    pdo_hash: str = ""
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.pdo_hash:
            self.pdo_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = json.dumps({
            "pdo_id": self.pdo_id,
            "proof_hash": self.proof.hash,
            "decision_id": self.decision.decision_id,
            "outcome_id": self.outcome.outcome_id
        }, sort_keys=True)
        return f"sha3-256:{hashlib.sha3_256(data.encode()).hexdigest()[:32]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "session_id": self.session_id,
            "capture_mode": self.capture_mode.value,
            "proof": self.proof.to_dict(),
            "decision": self.decision.to_dict(),
            "outcome": self.outcome.to_dict(),
            "context": self.context,
            "pdo_hash": self.pdo_hash,
            "captured_at": self.captured_at.isoformat()
        }


class SandboxPDOCollector:
    """
    Collects and stores PDO records from sandbox execution.
    
    Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.
    
    This collector is READ-ONLY with respect to production systems.
    It captures observations for governance evolution proposals.
    """

    ISOLATION_LEVEL = "COMPLETE"
    PRODUCTION_ACCESS = "NONE"

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/sandbox_pdo_records.json")
        self._records: list[PDORecord] = []
        self._sessions: dict[str, list[str]] = {}  # session_id -> [pdo_ids]
        self._audit_log: list[dict[str, Any]] = []

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(8).upper()}"

    def _log_audit(self, event: str, details: dict[str, Any]) -> None:
        self._audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
            "isolation_level": self.ISOLATION_LEVEL,
            "production_access": self.PRODUCTION_ACCESS
        })

    def start_session(self, session_context: Optional[dict[str, Any]] = None) -> str:
        """Start a new sandbox capture session."""
        session_id = self._generate_id("SESSION")
        self._sessions[session_id] = []
        
        self._log_audit("SESSION_STARTED", {
            "session_id": session_id,
            "context": session_context or {}
        })
        
        return session_id

    def capture_pdo(
        self,
        session_id: str,
        proof: Proof,
        decision: Decision,
        outcome: Outcome,
        capture_mode: CaptureMode = CaptureMode.SANDBOX,
        context: Optional[dict[str, Any]] = None
    ) -> PDORecord:
        """
        Capture a complete PDO record.
        
        INVARIANT: This is observational only - no production modification.
        """
        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        record = PDORecord(
            pdo_id=self._generate_id("PDO"),
            session_id=session_id,
            capture_mode=capture_mode,
            proof=proof,
            decision=decision,
            outcome=outcome,
            context=context or {}
        )

        self._records.append(record)
        self._sessions[session_id].append(record.pdo_id)

        self._log_audit("PDO_CAPTURED", {
            "pdo_id": record.pdo_id,
            "session_id": session_id,
            "capture_mode": capture_mode.value,
            "decision_type": decision.decision_type.value,
            "outcome_type": outcome.outcome_type.value,
            "pdo_hash": record.pdo_hash
        })

        return record

    def capture_blocked_attempt(
        self,
        session_id: str,
        attempt_description: str,
        block_reasons: list[str],
        invariants_violated: list[str],
        context: Optional[dict[str, Any]] = None
    ) -> PDORecord:
        """
        Convenience method for capturing blocked attempts.
        
        Critical for governance evolution - blocked attempts reveal invariant gaps.
        """
        proof = Proof(
            proof_id=self._generate_id("PROOF"),
            proof_type="BLOCK_EVIDENCE",
            evidence={
                "attempt": attempt_description,
                "block_reasons": block_reasons,
                "invariants_violated": invariants_violated
            },
            invariants_checked=invariants_violated
        )

        decision = Decision(
            decision_id=self._generate_id("DEC"),
            decision_type=DecisionType.BLOCKED,
            authority="GOVERNANCE_ENGINE",
            rules_applied=invariants_violated,
            reasoning="; ".join(block_reasons),
            confidence=1.0
        )

        outcome = Outcome(
            outcome_id=self._generate_id("OUT"),
            outcome_type=OutcomeType.PREVENTED,
            effects={"attempt_blocked": True, "settlement_prevented": True},
            drift_detected=False,
            drift_score=0.0
        )

        return self.capture_pdo(
            session_id=session_id,
            proof=proof,
            decision=decision,
            outcome=outcome,
            capture_mode=CaptureMode.SANDBOX,
            context=context
        )

    def capture_approved_attempt(
        self,
        session_id: str,
        attempt_description: str,
        rules_applied: list[str],
        effects: dict[str, Any],
        context: Optional[dict[str, Any]] = None
    ) -> PDORecord:
        """Convenience method for capturing approved attempts."""
        proof = Proof(
            proof_id=self._generate_id("PROOF"),
            proof_type="APPROVAL_EVIDENCE",
            evidence={
                "attempt": attempt_description,
                "rules_applied": rules_applied
            },
            invariants_checked=rules_applied
        )

        decision = Decision(
            decision_id=self._generate_id("DEC"),
            decision_type=DecisionType.APPROVED,
            authority="GOVERNANCE_ENGINE",
            rules_applied=rules_applied,
            reasoning="All invariants satisfied",
            confidence=1.0
        )

        outcome = Outcome(
            outcome_id=self._generate_id("OUT"),
            outcome_type=OutcomeType.EXECUTED,
            effects=effects,
            drift_detected=False,
            drift_score=0.0
        )

        return self.capture_pdo(
            session_id=session_id,
            proof=proof,
            decision=decision,
            outcome=outcome,
            capture_mode=CaptureMode.SANDBOX,
            context=context
        )

    def get_session_records(self, session_id: str) -> list[PDORecord]:
        """Get all PDO records for a session."""
        pdo_ids = self._sessions.get(session_id, [])
        return [r for r in self._records if r.pdo_id in pdo_ids]

    def get_blocked_records(self) -> list[PDORecord]:
        """Get all blocked attempt records."""
        return [
            r for r in self._records
            if r.decision.decision_type == DecisionType.BLOCKED
        ]

    def get_records_by_invariant(self, invariant_id: str) -> list[PDORecord]:
        """Get records where a specific invariant was checked."""
        return [
            r for r in self._records
            if invariant_id in r.proof.invariants_checked
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get collection statistics for analysis."""
        blocked = len([r for r in self._records if r.decision.decision_type == DecisionType.BLOCKED])
        approved = len([r for r in self._records if r.decision.decision_type == DecisionType.APPROVED])
        
        return {
            "total_records": len(self._records),
            "total_sessions": len(self._sessions),
            "blocked_attempts": blocked,
            "approved_attempts": approved,
            "block_rate": blocked / max(len(self._records), 1),
            "unique_invariants_checked": len(set(
                inv for r in self._records for inv in r.proof.invariants_checked
            )),
            "capture_modes": {
                mode.value: len([r for r in self._records if r.capture_mode == mode])
                for mode in CaptureMode
            }
        }

    def export(self) -> dict[str, Any]:
        """Export collector state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "isolation_level": self.ISOLATION_LEVEL,
            "production_access": self.PRODUCTION_ACCESS,
            "statistics": self.get_statistics(),
            "records": [r.to_dict() for r in self._records],
            "audit_log_size": len(self._audit_log)
        }

    def save(self) -> None:
        """Save collector state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_pdo_collector: Optional[SandboxPDOCollector] = None


def get_sandbox_pdo_collector() -> SandboxPDOCollector:
    """Get global PDO collector instance."""
    global _pdo_collector
    if _pdo_collector is None:
        _pdo_collector = SandboxPDOCollector()
    return _pdo_collector
