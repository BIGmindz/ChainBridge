"""
Lex Schema Module
=================

Policy-as-Code schema definitions for the Lex runtime law engine.

All rules are deterministic and mechanical.
No probabilistic logic. No heuristics. No learning.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import hashlib
import json


class RuleCategory(Enum):
    """Categories of Lex enforcement rules."""
    
    INTEGRITY = "INTEGRITY"          # Hash, signature verification
    AUTHORIZATION = "AUTHORIZATION"  # Caps, permissions
    COMPLIANCE = "COMPLIANCE"        # Jurisdiction, limits
    GOVERNANCE = "GOVERNANCE"        # PDO structure, gate ordering
    TEMPORAL = "TEMPORAL"            # Time-based constraints


class RuleSeverity(Enum):
    """Severity levels for rule violations."""
    
    CRITICAL = "CRITICAL"  # Immediate block, no override
    HIGH = "HIGH"          # Block, override requires senior authority
    MEDIUM = "MEDIUM"      # Block, standard override path
    LOW = "LOW"            # Warning, execution continues
    INFO = "INFO"          # Informational only


class VerdictStatus(Enum):
    """Lex verdict status values."""
    
    APPROVED = "APPROVED"            # Execution permitted
    REJECTED = "REJECTED"            # Execution blocked
    PENDING_OVERRIDE = "PENDING_OVERRIDE"  # Blocked pending human override
    OVERRIDDEN = "OVERRIDDEN"        # Previously rejected, now overridden


@dataclass(frozen=True)
class LexRule:
    """
    Immutable policy-as-code rule definition.
    
    Rules are deterministic predicates that evaluate to True/False.
    No probabilistic logic allowed.
    """
    
    rule_id: str                     # Unique identifier (e.g., "LEX-INT-001")
    category: RuleCategory
    severity: RuleSeverity
    name: str
    description: str
    predicate_fn: str                # Name of predicate function to execute
    error_template: str              # Template for rejection message
    override_allowed: bool = True    # Can this rule be overridden?
    requires_senior_override: bool = False  # Requires senior authority?
    
    def __hash__(self):
        return hash(self.rule_id)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "name": self.name,
            "description": self.description,
            "predicate_fn": self.predicate_fn,
            "error_template": self.error_template,
            "override_allowed": self.override_allowed,
            "requires_senior_override": self.requires_senior_override,
        }


@dataclass
class RuleViolation:
    """
    Record of a single rule violation.
    
    Immutable after creation.
    """
    
    rule: LexRule
    context: dict[str, Any]
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule.rule_id,
            "rule_name": self.rule.name,
            "category": self.rule.category.value,
            "severity": self.rule.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "override_allowed": self.rule.override_allowed,
        }


@dataclass
class LexVerdict:
    """
    Lex enforcement verdict.
    
    Binary outcome: APPROVED or REJECTED.
    Contains full audit trail of evaluated rules.
    """
    
    verdict_id: str
    status: VerdictStatus
    pdo_hash: str                    # Hash of the PDO being evaluated
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rules_evaluated: list[str] = field(default_factory=list)
    rules_passed: list[str] = field(default_factory=list)
    violations: list[RuleViolation] = field(default_factory=list)
    override_id: Optional[str] = None  # If overridden, the override ID
    
    @property
    def is_approved(self) -> bool:
        """Check if verdict allows execution."""
        return self.status in {VerdictStatus.APPROVED, VerdictStatus.OVERRIDDEN}
    
    @property
    def is_blocked(self) -> bool:
        """Check if verdict blocks execution."""
        return self.status in {VerdictStatus.REJECTED, VerdictStatus.PENDING_OVERRIDE}
    
    @property
    def blocking_rules(self) -> list[str]:
        """Get list of rule IDs causing the block."""
        return [v.rule.rule_id for v in self.violations 
                if v.rule.severity in {RuleSeverity.CRITICAL, RuleSeverity.HIGH, RuleSeverity.MEDIUM}]
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "verdict_id": self.verdict_id,
            "status": self.status.value,
            "pdo_hash": self.pdo_hash,
            "timestamp": self.timestamp.isoformat(),
            "rules_evaluated": self.rules_evaluated,
            "rules_passed": self.rules_passed,
            "violations": [v.to_dict() for v in self.violations],
            "blocking_rules": self.blocking_rules,
            "override_id": self.override_id,
            "is_approved": self.is_approved,
            "is_blocked": self.is_blocked,
        }
    
    def render_terminal(self) -> str:
        """Render canonical terminal output."""
        icon = "✅" if self.is_approved else "🛑"
        
        lines = [
            "",
            "─" * 70,
            f"🟥 LEX VERDICT — {self.verdict_id}",
            "─" * 70,
            f"Status: {icon} {self.status.value}",
            f"PDO Hash: {self.pdo_hash[:16]}...",
            f"Timestamp: {self.timestamp.isoformat()}",
            "",
            f"Rules Evaluated: {len(self.rules_evaluated)}",
            f"Rules Passed: {len(self.rules_passed)}",
            f"Violations: {len(self.violations)}",
        ]
        
        if self.violations:
            lines.append("")
            lines.append("─" * 70)
            lines.append("VIOLATIONS")
            lines.append("─" * 70)
            for v in self.violations:
                sev_icon = "🔴" if v.rule.severity == RuleSeverity.CRITICAL else "🟠" if v.rule.severity == RuleSeverity.HIGH else "🟡"
                lines.append(f"  {sev_icon} [{v.rule.rule_id}] {v.message}")
        
        if self.override_id:
            lines.append("")
            lines.append(f"Override ID: {self.override_id}")
        
        lines.append("─" * 70)
        
        return "\n".join(lines)


@dataclass
class EnforcementRecord:
    """
    Immutable record of a Lex enforcement action.
    
    Stored in audit log for compliance and debugging.
    """
    
    record_id: str
    verdict: LexVerdict
    pdo_snapshot: dict[str, Any]
    context: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def compute_hash(self) -> str:
        """Compute immutable hash of the record."""
        data = json.dumps({
            "record_id": self.record_id,
            "verdict": self.verdict.to_dict(),
            "pdo_snapshot": self.pdo_snapshot,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "record_id": self.record_id,
            "verdict": self.verdict.to_dict(),
            "pdo_snapshot": self.pdo_snapshot,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "hash": self.compute_hash(),
        }
