"""
Governance Economic Finality Layer Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-14: Implement EconomicFinalityLayer primitive

Implements:
- Governance credit system
- Risk budget accounting
- Penalty propagation engine
- Economic finality state machine
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class CreditType(Enum):
    """Types of governance credits."""
    EXECUTION_CREDIT = "EXECUTION_CREDIT"
    AUTHORITY_CREDIT = "AUTHORITY_CREDIT"
    RISK_CREDIT = "RISK_CREDIT"


class RiskCategory(Enum):
    """Categories of governance risk."""
    OPERATIONAL_RISK = "OPERATIONAL_RISK"
    SECURITY_RISK = "SECURITY_RISK"
    GOVERNANCE_RISK = "GOVERNANCE_RISK"
    COMPLIANCE_RISK = "COMPLIANCE_RISK"


class FinalityState(Enum):
    """Finality states for governance decisions."""
    PROVISIONAL = "PROVISIONAL"
    COMMITTED = "COMMITTED"
    FINAL = "FINAL"


class ViolationType(Enum):
    """Types of governance violations."""
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


@dataclass
class CreditBalance:
    """Credit balance for an actor."""
    actor_id: str
    execution_credits: float = 1000.0
    authority_credits: float = 100.0
    risk_credits: float = 50.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    INITIAL_EXECUTION = 1000.0
    INITIAL_AUTHORITY = 100.0
    INITIAL_RISK = 50.0

    def consume(self, credit_type: CreditType, amount: float) -> bool:
        """Consume credits. Returns False if insufficient."""
        if credit_type == CreditType.EXECUTION_CREDIT:
            if self.execution_credits < amount:
                return False
            self.execution_credits -= amount
        elif credit_type == CreditType.AUTHORITY_CREDIT:
            if self.authority_credits < amount:
                return False
            self.authority_credits -= amount
        elif credit_type == CreditType.RISK_CREDIT:
            if self.risk_credits < amount:
                return False
            self.risk_credits -= amount
        
        self.last_updated = datetime.now(timezone.utc)
        return True

    def replenish(self, credit_type: CreditType, amount: float) -> None:
        """Replenish credits."""
        if credit_type == CreditType.EXECUTION_CREDIT:
            self.execution_credits = min(
                self.execution_credits + amount,
                self.INITIAL_EXECUTION * 1.5  # Cap at 150%
            )
        elif credit_type == CreditType.AUTHORITY_CREDIT:
            self.authority_credits = min(
                self.authority_credits + amount,
                self.INITIAL_AUTHORITY
            )
        elif credit_type == CreditType.RISK_CREDIT:
            self.risk_credits = min(
                self.risk_credits + amount,
                self.INITIAL_RISK
            )
        
        self.last_updated = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "execution_credits": self.execution_credits,
            "authority_credits": self.authority_credits,
            "risk_credits": self.risk_credits,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class RiskBudget:
    """Risk budget for a period."""
    period_start: datetime
    period_end: datetime
    total_budget: float = 10000.0
    operational_consumed: float = 0.0
    security_consumed: float = 0.0
    governance_consumed: float = 0.0
    compliance_consumed: float = 0.0

    BUDGET_SHARES = {
        RiskCategory.OPERATIONAL_RISK: 0.4,
        RiskCategory.SECURITY_RISK: 0.3,
        RiskCategory.GOVERNANCE_RISK: 0.2,
        RiskCategory.COMPLIANCE_RISK: 0.1
    }

    def get_category_budget(self, category: RiskCategory) -> float:
        """Get budget for a category."""
        return self.total_budget * self.BUDGET_SHARES[category]

    def get_category_consumed(self, category: RiskCategory) -> float:
        """Get consumed amount for a category."""
        mapping = {
            RiskCategory.OPERATIONAL_RISK: self.operational_consumed,
            RiskCategory.SECURITY_RISK: self.security_consumed,
            RiskCategory.GOVERNANCE_RISK: self.governance_consumed,
            RiskCategory.COMPLIANCE_RISK: self.compliance_consumed
        }
        return mapping[category]

    def consume(self, category: RiskCategory, amount: float) -> bool:
        """Consume from risk budget. Returns False if would exceed."""
        budget = self.get_category_budget(category)
        consumed = self.get_category_consumed(category)
        
        if consumed + amount > budget:
            return False

        if category == RiskCategory.OPERATIONAL_RISK:
            self.operational_consumed += amount
        elif category == RiskCategory.SECURITY_RISK:
            self.security_consumed += amount
        elif category == RiskCategory.GOVERNANCE_RISK:
            self.governance_consumed += amount
        elif category == RiskCategory.COMPLIANCE_RISK:
            self.compliance_consumed += amount

        return True

    def get_utilization(self) -> dict[str, float]:
        """Get budget utilization percentages."""
        result = {}
        for category in RiskCategory:
            budget = self.get_category_budget(category)
            consumed = self.get_category_consumed(category)
            result[category.value] = (consumed / budget * 100) if budget > 0 else 0
        
        total_consumed = (
            self.operational_consumed + self.security_consumed +
            self.governance_consumed + self.compliance_consumed
        )
        result["TOTAL"] = (total_consumed / self.total_budget * 100) if self.total_budget > 0 else 0
        
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_budget": self.total_budget,
            "consumed": {
                "operational": self.operational_consumed,
                "security": self.security_consumed,
                "governance": self.governance_consumed,
                "compliance": self.compliance_consumed
            },
            "utilization": self.get_utilization()
        }


@dataclass
class Penalty:
    """A governance penalty."""
    penalty_id: str
    violation_type: ViolationType
    severity_multiplier: float
    base_penalty: float
    final_penalty: float
    actor_id: str
    reason: str
    timestamp: datetime
    acknowledged: bool = False
    propagated_to: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "penalty_id": self.penalty_id,
            "violation_type": self.violation_type.value,
            "severity_multiplier": self.severity_multiplier,
            "base_penalty": self.base_penalty,
            "final_penalty": self.final_penalty,
            "actor_id": self.actor_id,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "propagated_to": self.propagated_to
        }


@dataclass
class GovernanceDecision:
    """A governance decision with finality tracking."""
    decision_id: str
    actor_id: str
    description: str
    state: FinalityState
    created_at: datetime
    provisional_until: datetime
    committed_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    ledger_hash: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "actor_id": self.actor_id,
            "description": self.description,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "provisional_until": self.provisional_until.isoformat(),
            "committed_at": self.committed_at.isoformat() if self.committed_at else None,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "ledger_hash": self.ledger_hash
        }


@dataclass
class CreditTransaction:
    """Record of a credit transaction."""
    transaction_id: str
    actor_id: str
    credit_type: CreditType
    amount: float
    direction: str  # "CONSUME" or "REPLENISH"
    reason: str
    timestamp: datetime
    balance_after: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "actor_id": self.actor_id,
            "credit_type": self.credit_type.value,
            "amount": self.amount,
            "direction": self.direction,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "balance_after": self.balance_after
        }


# Penalty base values
PENALTY_BASE = {
    ViolationType.MINOR: 10,
    ViolationType.MODERATE: 50,
    ViolationType.SEVERE: 200,
    ViolationType.CRITICAL: 1000
}

# Propagation rates
PROPAGATION_RATES = {
    "agent_to_orchestrator": 0.25,
    "orchestrator_to_architect": 0.1,
    "cross_agent": 0.1
}


class EconomicFinalityLayer:
    """
    Economic finality layer for governance accountability.
    
    Enforces:
    - Governance credit system
    - Risk budget accounting
    - Penalty propagation
    - Economic finality
    """

    PROVISIONAL_DURATION_HOURS = 1
    CREDIT_REPLENISH_INTERVAL_HOURS = 24
    REPLENISH_AMOUNT = 100  # Execution credits per interval

    def __init__(self, storage_path: Optional[Path] = None):
        self._credit_balances: dict[str, CreditBalance] = {}
        self._risk_budget: Optional[RiskBudget] = None
        self._penalties: list[Penalty] = []
        self._decisions: dict[str, GovernanceDecision] = {}
        self._transactions: list[CreditTransaction] = []
        self.storage_path = storage_path or Path("data/economic_finality.json")
        
        self._initialize_budget()

    def _initialize_budget(self) -> None:
        """Initialize monthly risk budget."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate end of month
        if now.month == 12:
            month_end = month_start.replace(year=now.year + 1, month=1)
        else:
            month_end = month_start.replace(month=now.month + 1)
        
        self._risk_budget = RiskBudget(
            period_start=month_start,
            period_end=month_end
        )

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID."""
        ts = datetime.now(timezone.utc).isoformat()
        hash_val = hashlib.sha256(ts.encode()).hexdigest()[:10]
        return f"{prefix}-{hash_val.upper()}"

    def get_or_create_balance(self, actor_id: str) -> CreditBalance:
        """Get or create credit balance for an actor."""
        if actor_id not in self._credit_balances:
            self._credit_balances[actor_id] = CreditBalance(actor_id=actor_id)
        return self._credit_balances[actor_id]

    def consume_credits(
        self,
        actor_id: str,
        credit_type: CreditType,
        amount: float,
        reason: str
    ) -> tuple[bool, str]:
        """Consume credits from an actor's balance."""
        balance = self.get_or_create_balance(actor_id)
        
        success = balance.consume(credit_type, amount)
        
        if not success:
            return False, f"Insufficient {credit_type.value}: needed {amount}"

        # Record transaction
        current = getattr(balance, f"{credit_type.value.lower().replace('_credit', '_credits')}")
        transaction = CreditTransaction(
            transaction_id=self._generate_id("TXN"),
            actor_id=actor_id,
            credit_type=credit_type,
            amount=amount,
            direction="CONSUME",
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            balance_after=current
        )
        self._transactions.append(transaction)

        return True, f"Consumed {amount} {credit_type.value}"

    def replenish_credits(
        self,
        actor_id: str,
        credit_type: CreditType,
        amount: float,
        reason: str
    ) -> None:
        """Replenish credits for an actor."""
        balance = self.get_or_create_balance(actor_id)
        balance.replenish(credit_type, amount)

        current = getattr(balance, f"{credit_type.value.lower().replace('_credit', '_credits')}")
        transaction = CreditTransaction(
            transaction_id=self._generate_id("TXN"),
            actor_id=actor_id,
            credit_type=credit_type,
            amount=amount,
            direction="REPLENISH",
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            balance_after=current
        )
        self._transactions.append(transaction)

    def consume_risk(
        self,
        category: RiskCategory,
        amount: float,
        reason: str
    ) -> tuple[bool, str]:
        """Consume from risk budget."""
        if not self._risk_budget:
            self._initialize_budget()

        success = self._risk_budget.consume(category, amount)
        
        if not success:
            utilization = self._risk_budget.get_utilization()
            return False, f"Risk budget exceeded for {category.value}: {utilization[category.value]:.1f}% utilized"

        return True, f"Consumed {amount} from {category.value} budget"

    def issue_penalty(
        self,
        actor_id: str,
        violation_type: ViolationType,
        reason: str,
        severity_multiplier: float = 1.0
    ) -> Penalty:
        """Issue a penalty to an actor."""
        base = PENALTY_BASE[violation_type]
        final = base * severity_multiplier

        penalty = Penalty(
            penalty_id=self._generate_id("PEN"),
            violation_type=violation_type,
            severity_multiplier=severity_multiplier,
            base_penalty=base,
            final_penalty=final,
            actor_id=actor_id,
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )

        self._penalties.append(penalty)

        # Deduct from credits
        balance = self.get_or_create_balance(actor_id)
        balance.consume(CreditType.EXECUTION_CREDIT, min(final, balance.execution_credits))

        return penalty

    def propagate_penalty(
        self,
        penalty: Penalty,
        propagation_type: str,
        target_actor_id: str
    ) -> Optional[Penalty]:
        """Propagate a penalty to another actor."""
        rate = PROPAGATION_RATES.get(propagation_type, 0.1)
        propagated_amount = penalty.final_penalty * rate

        if propagated_amount < 1:
            return None

        propagated = Penalty(
            penalty_id=self._generate_id("PEN"),
            violation_type=penalty.violation_type,
            severity_multiplier=penalty.severity_multiplier * rate,
            base_penalty=penalty.base_penalty,
            final_penalty=propagated_amount,
            actor_id=target_actor_id,
            reason=f"Propagated from {penalty.penalty_id}: {penalty.reason}",
            timestamp=datetime.now(timezone.utc)
        )

        self._penalties.append(propagated)
        penalty.propagated_to.append(target_actor_id)

        # Deduct from target's credits
        balance = self.get_or_create_balance(target_actor_id)
        balance.consume(CreditType.EXECUTION_CREDIT, min(propagated_amount, balance.execution_credits))

        return propagated

    def create_decision(
        self,
        actor_id: str,
        description: str
    ) -> GovernanceDecision:
        """Create a new governance decision in PROVISIONAL state."""
        now = datetime.now(timezone.utc)
        
        # Consume credits for decision
        success, msg = self.consume_credits(
            actor_id,
            CreditType.AUTHORITY_CREDIT,
            10,
            f"Governance decision: {description[:50]}"
        )
        
        if not success:
            raise PermissionError(f"Cannot create decision: {msg}")

        decision = GovernanceDecision(
            decision_id=self._generate_id("DEC"),
            actor_id=actor_id,
            description=description,
            state=FinalityState.PROVISIONAL,
            created_at=now,
            provisional_until=now + timedelta(hours=self.PROVISIONAL_DURATION_HOURS)
        )

        self._decisions[decision.decision_id] = decision
        return decision

    def advance_decision_state(self, decision_id: str) -> GovernanceDecision:
        """Advance a decision to the next finality state."""
        decision = self._decisions.get(decision_id)
        if not decision:
            raise KeyError(f"Decision {decision_id} not found")

        now = datetime.now(timezone.utc)

        if decision.state == FinalityState.PROVISIONAL:
            if now >= decision.provisional_until:
                decision.state = FinalityState.COMMITTED
                decision.committed_at = now
        elif decision.state == FinalityState.COMMITTED:
            # Generate ledger hash for finalization
            decision.ledger_hash = hashlib.sha3_256(
                json.dumps(decision.to_dict(), default=str).encode()
            ).hexdigest()
            decision.state = FinalityState.FINAL
            decision.finalized_at = now

        return decision

    def reverse_decision(
        self,
        decision_id: str,
        actor_id: str,
        reason: str
    ) -> tuple[bool, str, float]:
        """Attempt to reverse a decision. Cost depends on state."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return False, "Decision not found", 0

        if decision.state == FinalityState.FINAL:
            return False, "FINAL decisions cannot be reversed", 0

        if decision.state == FinalityState.PROVISIONAL:
            cost = 10  # Low cost
        else:  # COMMITTED
            cost = 100  # Higher cost

        success, msg = self.consume_credits(
            actor_id,
            CreditType.AUTHORITY_CREDIT,
            cost,
            f"Reverse decision {decision_id}: {reason}"
        )

        if not success:
            return False, msg, cost

        # Remove decision
        del self._decisions[decision_id]
        return True, f"Decision reversed (cost: {cost})", cost

    def get_actor_summary(self, actor_id: str) -> dict[str, Any]:
        """Get economic summary for an actor."""
        balance = self.get_or_create_balance(actor_id)
        actor_penalties = [p for p in self._penalties if p.actor_id == actor_id]
        actor_decisions = [d for d in self._decisions.values() if d.actor_id == actor_id]

        return {
            "actor_id": actor_id,
            "credits": balance.to_dict(),
            "penalties": {
                "total_count": len(actor_penalties),
                "total_value": sum(p.final_penalty for p in actor_penalties),
                "acknowledged": sum(1 for p in actor_penalties if p.acknowledged)
            },
            "decisions": {
                "total": len(actor_decisions),
                "by_state": {
                    state.value: sum(1 for d in actor_decisions if d.state == state)
                    for state in FinalityState
                }
            }
        }

    def get_system_summary(self) -> dict[str, Any]:
        """Get system-wide economic summary."""
        return {
            "total_actors": len(self._credit_balances),
            "risk_budget": self._risk_budget.to_dict() if self._risk_budget else None,
            "penalties": {
                "total_issued": len(self._penalties),
                "total_value": sum(p.final_penalty for p in self._penalties),
                "by_type": {
                    vt.value: sum(1 for p in self._penalties if p.violation_type == vt)
                    for vt in ViolationType
                }
            },
            "decisions": {
                "total": len(self._decisions),
                "by_state": {
                    state.value: sum(1 for d in self._decisions.values() if d.state == state)
                    for state in FinalityState
                }
            },
            "transactions": {
                "total": len(self._transactions),
                "consumed": sum(t.amount for t in self._transactions if t.direction == "CONSUME"),
                "replenished": sum(t.amount for t in self._transactions if t.direction == "REPLENISH")
            }
        }

    def export(self) -> dict[str, Any]:
        """Export layer state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "balances": {aid: b.to_dict() for aid, b in self._credit_balances.items()},
            "risk_budget": self._risk_budget.to_dict() if self._risk_budget else None,
            "penalties": [p.to_dict() for p in self._penalties],
            "decisions": [d.to_dict() for d in self._decisions.values()],
            "transactions": [t.to_dict() for t in self._transactions[-1000:]],
            "summary": self.get_system_summary()
        }

    def save(self) -> None:
        """Save layer state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_finality_layer: Optional[EconomicFinalityLayer] = None


def get_finality_layer() -> EconomicFinalityLayer:
    """Get global economic finality layer instance."""
    global _finality_layer
    if _finality_layer is None:
        _finality_layer = EconomicFinalityLayer()
    return _finality_layer
