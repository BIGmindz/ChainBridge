"""
Negative Capability Demo — Fail-Closed Governance Demonstration
PAC-P751-NEGATIVE-CAPABILITY-DEMO
TASK-01: Design invalid-but-plausible enterprise instruction
TASK-02: Bind instruction to PDO initiation (sharded execution)
TASK-03: Trigger governance evaluation and drift detection
TASK-04: Block outcome and prevent settlement

Demonstrates:
- Constitutional enforcement of invalid payment blocking
- Zero drift from governance rules
- Complete audit trail generation
- Fail-closed behavior as default

INVARIANTS ENFORCED:
- Control > Autonomy
- Proof > Execution
- Fail-Closed Mandatory
- Human Authority Final
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


class BlockReason(Enum):
    """Reasons for blocking a payment instruction."""
    SANCTIONED_COUNTERPARTY = "SANCTIONED_COUNTERPARTY"
    HIGH_RISK_JURISDICTION = "HIGH_RISK_JURISDICTION"
    VELOCITY_LIMIT_EXCEEDED = "VELOCITY_LIMIT_EXCEEDED"
    UNAUTHORIZED_INITIATOR = "UNAUTHORIZED_INITIATOR"
    MISSING_DUAL_APPROVAL = "MISSING_DUAL_APPROVAL"
    FRAUDULENT_PATTERN_DETECTED = "FRAUDULENT_PATTERN_DETECTED"
    GOVERNANCE_INVARIANT_VIOLATION = "GOVERNANCE_INVARIANT_VIOLATION"
    DRIFT_THRESHOLD_EXCEEDED = "DRIFT_THRESHOLD_EXCEEDED"


class GovernanceOutcome(Enum):
    """Outcome of governance evaluation."""
    BLOCKED = "BLOCKED"
    APPROVED = "APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    SCRAM = "SCRAM"


@dataclass
class InvalidInstruction:
    """
    TASK-01: Invalid-but-plausible enterprise instruction.
    
    This represents a realistic payment attempt that SHOULD be blocked.
    """
    instruction_id: str
    initiator: str
    amount_usd: float
    counterparty_id: str
    counterparty_name: str
    destination_jurisdiction: str
    payment_rail: str
    purpose_code: str
    memo: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Risk indicators (would be detected by system)
    is_sanctioned: bool = False
    is_high_risk_jurisdiction: bool = False
    is_unusual_velocity: bool = False
    is_missing_approval: bool = False
    fraud_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "initiator": self.initiator,
            "amount_usd": self.amount_usd,
            "counterparty_id": self.counterparty_id,
            "counterparty_name": self.counterparty_name,
            "destination_jurisdiction": self.destination_jurisdiction,
            "payment_rail": self.payment_rail,
            "purpose_code": self.purpose_code,
            "memo": self.memo,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class PDOBinding:
    """
    TASK-02: PDO (Payment Delivery Order) initiation binding.
    
    Binds the instruction to sharded execution context.
    """
    pdo_id: str
    instruction: InvalidInstruction
    shard_id: Optional[str] = None
    pac_reference: str = "PAC-P751"
    execution_context: dict[str, Any] = field(default_factory=dict)
    bound_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "instruction_id": self.instruction.instruction_id,
            "shard_id": self.shard_id,
            "pac_reference": self.pac_reference,
            "bound_at": self.bound_at.isoformat()
        }


@dataclass
class GovernanceEvaluation:
    """
    TASK-03: Governance evaluation result.
    
    Contains the evaluation logic and drift detection.
    """
    evaluation_id: str
    pdo_id: str
    outcome: GovernanceOutcome
    block_reasons: list[BlockReason]
    invariants_checked: list[dict[str, Any]]
    drift_score: float  # 0.0 = no drift, 1.0 = complete drift
    authority: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "pdo_id": self.pdo_id,
            "outcome": self.outcome.value,
            "block_reasons": [r.value for r in self.block_reasons],
            "invariants_checked": self.invariants_checked,
            "drift_score": self.drift_score,
            "authority": self.authority,
            "evaluated_at": self.evaluated_at.isoformat()
        }


@dataclass
class BlockedOutcome:
    """
    TASK-04: Blocked outcome record.
    
    Proof that the invalid instruction was blocked.
    """
    block_id: str
    evaluation_id: str
    pdo_id: str
    instruction_id: str
    settlement_prevented: bool
    ledger_unchanged: bool
    block_reasons: list[BlockReason]
    explanation: str
    authority: str
    blocked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    proof_hash: str = ""

    def __post_init__(self):
        if not self.proof_hash:
            self.proof_hash = self._compute_proof_hash()

    def _compute_proof_hash(self) -> str:
        data = json.dumps({
            "block_id": self.block_id,
            "pdo_id": self.pdo_id,
            "instruction_id": self.instruction_id,
            "reasons": [r.value for r in self.block_reasons],
            "blocked_at": self.blocked_at.isoformat()
        }, sort_keys=True)
        return f"sha3-256:{hashlib.sha3_256(data.encode()).hexdigest()[:32]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "evaluation_id": self.evaluation_id,
            "pdo_id": self.pdo_id,
            "instruction_id": self.instruction_id,
            "settlement_prevented": self.settlement_prevented,
            "ledger_unchanged": self.ledger_unchanged,
            "block_reasons": [r.value for r in self.block_reasons],
            "explanation": self.explanation,
            "authority": self.authority,
            "blocked_at": self.blocked_at.isoformat(),
            "proof_hash": self.proof_hash
        }


class NegativeCapabilityDemo:
    """
    Complete demonstration of fail-closed governance.
    
    Shows that an invalid instruction is:
    1. Received
    2. Evaluated against governance rules
    3. BLOCKED (not executed)
    4. Audited with full proof trail
    """

    SINGULAR_AUTHORITY = "BENSON (GID-00)"
    
    # Sanctioned entities (demo list)
    SANCTIONED_ENTITIES = {
        "SHELL-CORP-9847",
        "OFAC-BLOCKED-LLC",
        "SUSPICIOUS-HOLDINGS-LTD"
    }
    
    # High-risk jurisdictions
    HIGH_RISK_JURISDICTIONS = {
        "NK",  # North Korea
        "IR",  # Iran
        "SY",  # Syria
        "CU",  # Cuba
        "UNKNOWN"
    }

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("data/negative_capability_demo.json")
        self._audit_trail: list[dict[str, Any]] = []

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(6).upper()}"

    def _log_audit(self, event: str, details: dict[str, Any]) -> None:
        self._audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details
        })

    def create_invalid_instruction(self) -> InvalidInstruction:
        """
        TASK-01: Create a realistic but invalid payment instruction.
        
        This instruction is DESIGNED TO BE BLOCKED:
        - Counterparty is on sanctions list
        - Destination is high-risk jurisdiction
        - Missing dual approval
        - Fraud pattern detected
        """
        instruction = InvalidInstruction(
            instruction_id=self._generate_id("INSTR"),
            initiator="AUTOMATED_SYSTEM_COMPROMISED",
            amount_usd=2_500_000.00,
            counterparty_id="SHELL-CORP-9847",
            counterparty_name="Oceanic Holdings Ltd (Sanctioned)",
            destination_jurisdiction="UNKNOWN",
            payment_rail="SWIFT",
            purpose_code="TRADE_PAYMENT",
            memo="Urgent wire - bypass normal approval",
            is_sanctioned=True,
            is_high_risk_jurisdiction=True,
            is_unusual_velocity=True,
            is_missing_approval=True,
            fraud_score=0.94
        )

        self._log_audit("INSTRUCTION_CREATED", {
            "instruction_id": instruction.instruction_id,
            "type": "INVALID_BUT_PLAUSIBLE",
            "risk_indicators": {
                "sanctioned": instruction.is_sanctioned,
                "high_risk_jurisdiction": instruction.is_high_risk_jurisdiction,
                "unusual_velocity": instruction.is_unusual_velocity,
                "missing_approval": instruction.is_missing_approval,
                "fraud_score": instruction.fraud_score
            }
        })

        return instruction

    def bind_to_pdo(self, instruction: InvalidInstruction, shard_id: Optional[str] = None) -> PDOBinding:
        """
        TASK-02: Bind instruction to PDO initiation.
        
        Creates execution context for governance evaluation.
        """
        pdo = PDOBinding(
            pdo_id=self._generate_id("PDO"),
            instruction=instruction,
            shard_id=shard_id,
            execution_context={
                "environment": "PRODUCTION_SAFE_DEMO",
                "governance_version": "1.0.0",
                "invariants_active": [
                    "Control > Autonomy",
                    "Proof > Execution",
                    "Fail-Closed Mandatory",
                    "Human Authority Final"
                ]
            }
        )

        self._log_audit("PDO_BOUND", {
            "pdo_id": pdo.pdo_id,
            "instruction_id": instruction.instruction_id,
            "shard_id": shard_id
        })

        return pdo

    def evaluate_governance(self, pdo: PDOBinding) -> GovernanceEvaluation:
        """
        TASK-03: Evaluate instruction against governance rules.
        
        Performs:
        - Sanctions screening
        - Jurisdiction check
        - Velocity analysis
        - Approval verification
        - Fraud detection
        - Drift assessment
        """
        instruction = pdo.instruction
        block_reasons: list[BlockReason] = []
        invariants_checked: list[dict[str, Any]] = []

        # Check: Sanctioned counterparty
        if instruction.counterparty_id in self.SANCTIONED_ENTITIES:
            block_reasons.append(BlockReason.SANCTIONED_COUNTERPARTY)
            invariants_checked.append({
                "invariant": "Control > Autonomy",
                "check": "SANCTIONS_SCREENING",
                "result": "BLOCK",
                "reason": f"Counterparty {instruction.counterparty_id} is sanctioned"
            })

        # Check: High-risk jurisdiction
        if instruction.destination_jurisdiction in self.HIGH_RISK_JURISDICTIONS:
            block_reasons.append(BlockReason.HIGH_RISK_JURISDICTION)
            invariants_checked.append({
                "invariant": "Fail-Closed Mandatory",
                "check": "JURISDICTION_SCREENING",
                "result": "BLOCK",
                "reason": f"Jurisdiction {instruction.destination_jurisdiction} is high-risk"
            })

        # Check: Missing approval
        if instruction.is_missing_approval:
            block_reasons.append(BlockReason.MISSING_DUAL_APPROVAL)
            invariants_checked.append({
                "invariant": "Human Authority Final",
                "check": "APPROVAL_VERIFICATION",
                "result": "BLOCK",
                "reason": "Dual approval not obtained"
            })

        # Check: Fraud pattern
        if instruction.fraud_score > 0.7:
            block_reasons.append(BlockReason.FRAUDULENT_PATTERN_DETECTED)
            invariants_checked.append({
                "invariant": "Proof > Execution",
                "check": "FRAUD_DETECTION",
                "result": "BLOCK",
                "reason": f"Fraud score {instruction.fraud_score} exceeds threshold"
            })

        # Check: Velocity
        if instruction.is_unusual_velocity:
            block_reasons.append(BlockReason.VELOCITY_LIMIT_EXCEEDED)
            invariants_checked.append({
                "invariant": "Control > Autonomy",
                "check": "VELOCITY_ANALYSIS",
                "result": "BLOCK",
                "reason": "Unusual transaction velocity detected"
            })

        # Determine outcome
        outcome = GovernanceOutcome.BLOCKED if block_reasons else GovernanceOutcome.APPROVED
        
        # Drift score: 0.0 means we followed rules perfectly
        drift_score = 0.0 if block_reasons and outcome == GovernanceOutcome.BLOCKED else 1.0

        evaluation = GovernanceEvaluation(
            evaluation_id=self._generate_id("EVAL"),
            pdo_id=pdo.pdo_id,
            outcome=outcome,
            block_reasons=block_reasons,
            invariants_checked=invariants_checked,
            drift_score=drift_score,
            authority=self.SINGULAR_AUTHORITY
        )

        self._log_audit("GOVERNANCE_EVALUATED", {
            "evaluation_id": evaluation.evaluation_id,
            "pdo_id": pdo.pdo_id,
            "outcome": outcome.value,
            "block_count": len(block_reasons),
            "drift_score": drift_score
        })

        return evaluation

    def block_outcome(self, evaluation: GovernanceEvaluation, pdo: PDOBinding) -> BlockedOutcome:
        """
        TASK-04: Block the outcome and prevent settlement.
        
        Creates proof that:
        - Settlement was prevented
        - Ledger was not mutated
        - Reasons are documented
        """
        if evaluation.outcome != GovernanceOutcome.BLOCKED:
            raise RuntimeError("Cannot create BlockedOutcome for non-blocked evaluation")

        # Generate human-readable explanation
        reason_explanations = {
            BlockReason.SANCTIONED_COUNTERPARTY: "Counterparty is on sanctions list",
            BlockReason.HIGH_RISK_JURISDICTION: "Destination jurisdiction is high-risk/prohibited",
            BlockReason.VELOCITY_LIMIT_EXCEEDED: "Transaction velocity exceeds safe limits",
            BlockReason.UNAUTHORIZED_INITIATOR: "Initiator lacks authorization",
            BlockReason.MISSING_DUAL_APPROVAL: "Required dual approval not obtained",
            BlockReason.FRAUDULENT_PATTERN_DETECTED: "Fraud detection system flagged transaction",
            BlockReason.GOVERNANCE_INVARIANT_VIOLATION: "Governance invariant would be violated",
            BlockReason.DRIFT_THRESHOLD_EXCEEDED: "Drift from governance rules detected"
        }

        explanations = [reason_explanations.get(r, r.value) for r in evaluation.block_reasons]

        blocked = BlockedOutcome(
            block_id=self._generate_id("BLOCK"),
            evaluation_id=evaluation.evaluation_id,
            pdo_id=pdo.pdo_id,
            instruction_id=pdo.instruction.instruction_id,
            settlement_prevented=True,
            ledger_unchanged=True,
            block_reasons=evaluation.block_reasons,
            explanation="; ".join(explanations),
            authority=self.SINGULAR_AUTHORITY
        )

        self._log_audit("OUTCOME_BLOCKED", {
            "block_id": blocked.block_id,
            "settlement_prevented": True,
            "ledger_unchanged": True,
            "proof_hash": blocked.proof_hash
        })

        return blocked

    def run_full_demo(self) -> dict[str, Any]:
        """
        Execute complete negative capability demonstration.
        
        Returns full audit trail and proof artifacts.
        """
        self._log_audit("DEMO_STARTED", {
            "pac_reference": "PAC-P751",
            "type": "NEGATIVE_CAPABILITY_DEMONSTRATION"
        })

        # TASK-01: Create invalid instruction
        instruction = self.create_invalid_instruction()

        # TASK-02: Bind to PDO
        pdo = self.bind_to_pdo(instruction, shard_id="SHARD-DEMO-P751")

        # TASK-03: Evaluate governance
        evaluation = self.evaluate_governance(pdo)

        # TASK-04: Block outcome
        blocked = self.block_outcome(evaluation, pdo)

        self._log_audit("DEMO_COMPLETED", {
            "outcome": "BLOCKED",
            "settlement_prevented": True,
            "drift_score": evaluation.drift_score,
            "proof_hash": blocked.proof_hash
        })

        return {
            "demo_id": "DEMO-P751",
            "pac_reference": "PAC-P751-NEGATIVE-CAPABILITY-DEMO",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "authority": self.SINGULAR_AUTHORITY,
            
            "instruction": instruction.to_dict(),
            "pdo": pdo.to_dict(),
            "evaluation": evaluation.to_dict(),
            "blocked_outcome": blocked.to_dict(),
            
            "invariants_enforced": [
                "Control > Autonomy",
                "Proof > Execution",
                "Fail-Closed Mandatory",
                "Human Authority Final"
            ],
            
            "demo_result": {
                "success": True,
                "settlement_executed": False,
                "ledger_mutated": False,
                "governance_bypassed": False,
                "drift_detected": evaluation.drift_score,
                "audit_complete": True
            },
            
            "audit_trail": self._audit_trail
        }

    def save(self, results: dict[str, Any]) -> None:
        """Save demo results."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(results, f, indent=2)


def run_negative_capability_demo() -> dict[str, Any]:
    """Convenience function to run the full demo."""
    demo = NegativeCapabilityDemo()
    results = demo.run_full_demo()
    demo.save(results)
    return results


if __name__ == "__main__":
    results = run_negative_capability_demo()
    print(json.dumps(results, indent=2))
