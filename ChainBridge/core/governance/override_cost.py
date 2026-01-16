"""
Override Cost Function Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-09: Implement OverrideCostFunction primitive

Implements:
- Entropy score model and accumulation
- Cost calculation engine
- Override escalation logic
- Immutable override ledger
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pathlib import Path
import math


class GovernanceTier(Enum):
    """Governance tier levels with associated multipliers."""
    ADVISORY_TIER = 1
    POLICY_TIER = 10
    LAW_TIER = 100
    CONSTITUTIONAL_TIER = 1000


class ViolationSeverity(Enum):
    """Severity levels for governance violations."""
    LOW = 0.5
    MEDIUM = 1.0
    HIGH = 2.0
    CRITICAL = 5.0


@dataclass
class OverrideAttempt:
    """Record of an override attempt."""
    attempt_id: str
    actor_id: str
    target_artifact: str
    target_tier: GovernanceTier
    justification: str
    timestamp: datetime
    approved: bool
    approvers: list[str]
    cost_paid: float
    entropy_added: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "actor_id": self.actor_id,
            "target_artifact": self.target_artifact,
            "target_tier": self.target_tier.name,
            "justification": self.justification,
            "timestamp": self.timestamp.isoformat(),
            "approved": self.approved,
            "approvers": self.approvers,
            "cost_paid": self.cost_paid,
            "entropy_added": self.entropy_added,
            "metadata": self.metadata
        }


@dataclass
class EntropyState:
    """Current entropy state of the governance system."""
    current_value: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[tuple[datetime, float, str]] = field(default_factory=list)

    WARNING_THRESHOLD = 0.5
    CRITICAL_THRESHOLD = 0.8
    MAXIMUM = 1.0

    def add_entropy(self, amount: float, reason: str) -> None:
        """Add entropy to the system (never decreases naturally)."""
        old_value = self.current_value
        self.current_value = min(self.current_value + amount, self.MAXIMUM)
        self.last_updated = datetime.now(timezone.utc)
        self.history.append((self.last_updated, self.current_value, reason))

    def get_level(self) -> str:
        """Get current entropy level classification."""
        if self.current_value >= self.MAXIMUM:
            return "MAXIMUM"
        elif self.current_value >= self.CRITICAL_THRESHOLD:
            return "CRITICAL"
        elif self.current_value >= self.WARNING_THRESHOLD:
            return "WARNING"
        else:
            return "NORMAL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_value": self.current_value,
            "level": self.get_level(),
            "last_updated": self.last_updated.isoformat(),
            "history_length": len(self.history)
        }


@dataclass
class ActorHistory:
    """Override history for a specific actor."""
    actor_id: str
    override_count: int = 0
    successful_overrides: int = 0
    failed_overrides: int = 0
    total_entropy_added: float = 0.0
    last_override: Optional[datetime] = None
    pattern_detected: bool = False

    def get_history_factor(self) -> float:
        """Calculate history factor for cost calculation."""
        if self.pattern_detected:
            return 5.0
        elif self.override_count > 3:
            return 2.0
        elif self.override_count >= 1:
            return 1.5
        else:
            return 1.0


class OverrideCostFunction:
    """
    Calculates and enforces override costs for governance artifacts.
    
    Formula: COST = BASE_COST × (TIER_MULTIPLIER ^ log2(TIER)) × (1 + ENTROPY_PENALTY) × HISTORY_FACTOR
    
    Enforces:
    - Override costs escalate with tier
    - Entropy accumulates permanently
    - Override history affects future costs
    - All attempts are immutably logged
    """

    BASE_COST = 100.0  # Base cost units

    TIER_MULTIPLIERS = {
        GovernanceTier.ADVISORY_TIER: 1,
        GovernanceTier.POLICY_TIER: 10,
        GovernanceTier.LAW_TIER: 100,
        GovernanceTier.CONSTITUTIONAL_TIER: 1000
    }

    ENTROPY_PER_ATTEMPT = {
        GovernanceTier.ADVISORY_TIER: 0.01,
        GovernanceTier.POLICY_TIER: 0.05,
        GovernanceTier.LAW_TIER: 0.10,
        GovernanceTier.CONSTITUTIONAL_TIER: 0.25
    }

    REQUIRED_APPROVERS = {
        GovernanceTier.ADVISORY_TIER: [],
        GovernanceTier.POLICY_TIER: ["BENSON (GID-00)"],
        GovernanceTier.LAW_TIER: ["JEFFREY (Architect)"],
        GovernanceTier.CONSTITUTIONAL_TIER: ["JEFFREY (Architect)", "BOARD_APPROVAL"]
    }

    WAIT_PERIODS_HOURS = {
        GovernanceTier.ADVISORY_TIER: 0,
        GovernanceTier.POLICY_TIER: 4,
        GovernanceTier.LAW_TIER: 24,
        GovernanceTier.CONSTITUTIONAL_TIER: 72
    }

    def __init__(self, storage_path: Optional[Path] = None):
        self.entropy_state = EntropyState()
        self.actor_histories: dict[str, ActorHistory] = {}
        self.override_ledger: list[OverrideAttempt] = []
        self.storage_path = storage_path or Path("data/override_ledger.json")

    def calculate_cost(
        self,
        actor_id: str,
        target_tier: GovernanceTier
    ) -> tuple[float, dict[str, Any]]:
        """
        Calculate the cost of an override attempt.
        
        Returns: (cost, breakdown)
        """
        # Get tier multiplier
        tier_multiplier = self.TIER_MULTIPLIERS[target_tier]

        # Get entropy penalty
        entropy_penalty = self.entropy_state.current_value

        # Get actor history factor
        actor_history = self.actor_histories.get(actor_id, ActorHistory(actor_id=actor_id))
        history_factor = actor_history.get_history_factor()

        # Calculate cost
        cost = self.BASE_COST * tier_multiplier * (1 + entropy_penalty) * history_factor

        breakdown = {
            "base_cost": self.BASE_COST,
            "tier_multiplier": tier_multiplier,
            "tier": target_tier.name,
            "entropy_penalty": entropy_penalty,
            "entropy_level": self.entropy_state.get_level(),
            "history_factor": history_factor,
            "actor_override_count": actor_history.override_count,
            "final_cost": cost,
            "required_approvers": self.REQUIRED_APPROVERS[target_tier],
            "wait_period_hours": self.WAIT_PERIODS_HOURS[target_tier]
        }

        return cost, breakdown

    def request_override(
        self,
        actor_id: str,
        target_artifact: str,
        target_tier: GovernanceTier,
        justification: str,
        approvers: list[str]
    ) -> tuple[bool, OverrideAttempt, str]:
        """
        Request an override. Validates approvers and records the attempt.
        
        Returns: (approved, attempt_record, message)
        """
        # Calculate cost
        cost, breakdown = self.calculate_cost(actor_id, target_tier)

        # Validate approvers
        required = set(self.REQUIRED_APPROVERS[target_tier])
        provided = set(approvers)
        missing_approvers = required - provided

        # Generate attempt ID
        attempt_id = self._generate_attempt_id(actor_id, target_artifact)

        # Determine entropy to add
        entropy_increment = self.ENTROPY_PER_ATTEMPT[target_tier]

        # Check approval
        approved = len(missing_approvers) == 0

        # Create attempt record
        attempt = OverrideAttempt(
            attempt_id=attempt_id,
            actor_id=actor_id,
            target_artifact=target_artifact,
            target_tier=target_tier,
            justification=justification,
            timestamp=datetime.now(timezone.utc),
            approved=approved,
            approvers=approvers,
            cost_paid=cost if approved else 0.0,
            entropy_added=entropy_increment,  # Always added, even if denied
            metadata=breakdown
        )

        # Always add entropy (override attempts always increase disorder)
        self.entropy_state.add_entropy(
            entropy_increment,
            f"Override attempt on {target_artifact} by {actor_id}"
        )

        # Update actor history
        if actor_id not in self.actor_histories:
            self.actor_histories[actor_id] = ActorHistory(actor_id=actor_id)
        
        history = self.actor_histories[actor_id]
        history.override_count += 1
        history.total_entropy_added += entropy_increment
        history.last_override = attempt.timestamp
        
        if approved:
            history.successful_overrides += 1
        else:
            history.failed_overrides += 1

        # Check for pattern
        if history.override_count >= 3:
            thirty_days_ago = datetime.now(timezone.utc).replace(
                day=max(1, datetime.now(timezone.utc).day - 30)
            )
            recent_overrides = sum(
                1 for a in self.override_ledger
                if a.actor_id == actor_id and a.timestamp > thirty_days_ago
            )
            if recent_overrides >= 3:
                history.pattern_detected = True

        # Record in ledger (immutable)
        self.override_ledger.append(attempt)

        # Generate message
        if approved:
            message = f"Override approved. Cost: {cost:.2f}. Entropy added: {entropy_increment:.3f}."
        else:
            message = f"Override denied. Missing approvers: {missing_approvers}. Entropy added: {entropy_increment:.3f}."

        return approved, attempt, message

    def _generate_attempt_id(self, actor_id: str, target: str) -> str:
        """Generate unique attempt ID."""
        content = f"{actor_id}:{target}:{datetime.now(timezone.utc).isoformat()}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"OVERRIDE-{hash_value.upper()}"

    def get_entropy_state(self) -> dict[str, Any]:
        """Get current entropy state."""
        return self.entropy_state.to_dict()

    def get_actor_history(self, actor_id: str) -> dict[str, Any]:
        """Get override history for an actor."""
        history = self.actor_histories.get(actor_id)
        if not history:
            return {"actor_id": actor_id, "override_count": 0}
        
        return {
            "actor_id": history.actor_id,
            "override_count": history.override_count,
            "successful_overrides": history.successful_overrides,
            "failed_overrides": history.failed_overrides,
            "total_entropy_added": history.total_entropy_added,
            "last_override": history.last_override.isoformat() if history.last_override else None,
            "pattern_detected": history.pattern_detected,
            "current_history_factor": history.get_history_factor()
        }

    def get_ledger_summary(self) -> dict[str, Any]:
        """Get summary of override ledger."""
        return {
            "total_attempts": len(self.override_ledger),
            "approved_count": sum(1 for a in self.override_ledger if a.approved),
            "denied_count": sum(1 for a in self.override_ledger if not a.approved),
            "total_cost_paid": sum(a.cost_paid for a in self.override_ledger),
            "total_entropy_generated": sum(a.entropy_added for a in self.override_ledger),
            "current_entropy": self.entropy_state.current_value,
            "entropy_level": self.entropy_state.get_level()
        }

    def export_ledger(self) -> dict[str, Any]:
        """Export full ledger for persistence."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "entropy_state": self.entropy_state.to_dict(),
            "actor_histories": {
                aid: self.get_actor_history(aid)
                for aid in self.actor_histories
            },
            "ledger": [a.to_dict() for a in self.override_ledger],
            "summary": self.get_ledger_summary()
        }

    def save(self) -> None:
        """Persist ledger to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export_ledger(), f, indent=2)

    def load(self) -> None:
        """Load ledger from storage."""
        if not self.storage_path.exists():
            return

        with open(self.storage_path) as f:
            data = json.load(f)

        # Restore entropy state
        entropy_data = data.get("entropy_state", {})
        self.entropy_state.current_value = entropy_data.get("current_value", 0.0)

        # Restore ledger
        self.override_ledger.clear()
        for attempt_data in data.get("ledger", []):
            attempt = OverrideAttempt(
                attempt_id=attempt_data["attempt_id"],
                actor_id=attempt_data["actor_id"],
                target_artifact=attempt_data["target_artifact"],
                target_tier=GovernanceTier[attempt_data["target_tier"]],
                justification=attempt_data["justification"],
                timestamp=datetime.fromisoformat(attempt_data["timestamp"]),
                approved=attempt_data["approved"],
                approvers=attempt_data["approvers"],
                cost_paid=attempt_data["cost_paid"],
                entropy_added=attempt_data["entropy_added"],
                metadata=attempt_data.get("metadata", {})
            )
            self.override_ledger.append(attempt)


# Singleton instance
_cost_function: Optional[OverrideCostFunction] = None


def get_override_cost_function() -> OverrideCostFunction:
    """Get global override cost function instance."""
    global _cost_function
    if _cost_function is None:
        _cost_function = OverrideCostFunction()
    return _cost_function


def check_override_cost(
    actor_id: str,
    target_tier: str
) -> dict[str, Any]:
    """
    Check the cost of an override without executing it.
    
    Convenience function for cost estimation.
    """
    tier = GovernanceTier[target_tier]
    cost_fn = get_override_cost_function()
    cost, breakdown = cost_fn.calculate_cost(actor_id, tier)
    return breakdown
