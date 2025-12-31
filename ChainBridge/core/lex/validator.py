"""
Lex Validator Engine
====================

Deterministic enforcement engine for PDO validation.

Lex Principles:
    - Enforces state, not intent
    - No discretionary decisions
    - Every rejection cites a rule ID
    - Binary APPROVE / REJECT only
    - PDOs are immutable — Lex cannot modify
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import hashlib
import json
import uuid

from .schema import (
    LexRule,
    RuleCategory,
    RuleSeverity,
    RuleViolation,
    LexVerdict,
    VerdictStatus,
    EnforcementRecord,
)
from .events import LexEventEmitter, LexEventType


# Type alias for rule predicate functions
RulePredicate = Callable[[dict[str, Any], dict[str, Any]], bool]


class LexValidator:
    """
    Lex Validator Engine.
    
    Deterministic enforcement for PDO validation.
    
    Enforcement Model:
        1. Receive PDO for validation
        2. Compute immutable PDO hash
        3. Evaluate all registered rules
        4. Produce verdict (APPROVE / REJECT)
        5. Emit enforcement events
        6. Return verdict (cannot modify PDO)
    
    Governance: GOLD STANDARD
    Failure Discipline: FAIL-CLOSED
    """
    
    def __init__(
        self,
        event_emitter: Optional[LexEventEmitter] = None,
        terminal_output: bool = True,
    ):
        self._rules: dict[str, LexRule] = {}
        self._predicates: dict[str, RulePredicate] = {}
        self._terminal_output = terminal_output
        
        # Initialize event emitter
        self._emitter = event_emitter or LexEventEmitter(
            terminal_output=terminal_output,
            json_output=False,
        )
        
        # Enforcement records (audit log)
        self._records: list[EnforcementRecord] = []
    
    def register_rule(
        self,
        rule: LexRule,
        predicate: RulePredicate,
    ) -> None:
        """
        Register a rule with its predicate function.
        
        Args:
            rule: The LexRule definition
            predicate: Function that evaluates to True (pass) or False (fail)
                      Signature: (pdo: dict, context: dict) -> bool
        """
        self._rules[rule.rule_id] = rule
        self._predicates[rule.rule_id] = predicate
    
    def register_rules(
        self,
        rules: list[tuple[LexRule, RulePredicate]],
    ) -> None:
        """Register multiple rules."""
        for rule, predicate in rules:
            self.register_rule(rule, predicate)
    
    def validate(
        self,
        pdo: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> LexVerdict:
        """
        Validate a PDO against all registered rules.
        
        Args:
            pdo: The Proof-Decision-Outcome object to validate
            context: Additional context for rule evaluation
            
        Returns:
            LexVerdict with APPROVED or REJECTED status
            
        Note:
            - Lex CANNOT modify the PDO
            - All rules are evaluated even if one fails (for complete audit)
            - Critical violations block immediately
        """
        context = context or {}
        
        # Generate verdict ID
        verdict_id = f"LEX-V-{uuid.uuid4().hex[:12].upper()}"
        
        # Compute immutable PDO hash
        pdo_hash = self._compute_pdo_hash(pdo)
        
        # Emit validation start
        self._emitter.emit(
            LexEventType.VALIDATION_START,
            verdict_id,
            payload={"pdo_hash": pdo_hash, "rule_count": len(self._rules)},
        )
        
        if self._terminal_output:
            self._render_header(verdict_id, pdo_hash)
        
        # Track evaluation results
        rules_evaluated: list[str] = []
        rules_passed: list[str] = []
        violations: list[RuleViolation] = []
        critical_violation = False
        
        # Evaluate all rules
        for rule_id, rule in self._rules.items():
            predicate = self._predicates[rule_id]
            
            # Emit rule evaluation event
            self._emitter.emit(
                LexEventType.RULE_EVALUATE,
                verdict_id,
                payload={"rule_id": rule_id, "category": rule.category.value},
            )
            
            rules_evaluated.append(rule_id)
            
            try:
                # Execute predicate (deterministic)
                result = predicate(pdo, context)
                
                if result:
                    # Rule passed
                    rules_passed.append(rule_id)
                    self._emitter.emit(
                        LexEventType.RULE_PASS,
                        verdict_id,
                        payload={"rule_id": rule_id},
                    )
                    
                    if self._terminal_output:
                        print(f"  ✅ [{rule_id}] {rule.name}")
                else:
                    # Rule failed — create violation
                    message = rule.error_template.format(
                        rule_id=rule_id,
                        rule_name=rule.name,
                        pdo_hash=pdo_hash[:16],
                        **context,
                    )
                    
                    violation = RuleViolation(
                        rule=rule,
                        context=context,
                        message=message,
                    )
                    violations.append(violation)
                    
                    self._emitter.emit(
                        LexEventType.RULE_FAIL,
                        verdict_id,
                        payload={"rule_id": rule_id, "message": message},
                    )
                    
                    if self._terminal_output:
                        sev_icon = "🔴" if rule.severity == RuleSeverity.CRITICAL else "🟠" if rule.severity == RuleSeverity.HIGH else "🟡"
                        print(f"  {sev_icon} [{rule_id}] {rule.name}: {message}")
                    
                    # Check for critical violation
                    if rule.severity == RuleSeverity.CRITICAL:
                        critical_violation = True
                        
            except Exception as e:
                # Predicate error — treat as violation (fail-closed)
                message = f"Rule evaluation error: {e}"
                violation = RuleViolation(
                    rule=rule,
                    context={"error": str(e)},
                    message=message,
                )
                violations.append(violation)
                
                self._emitter.emit(
                    LexEventType.RULE_FAIL,
                    verdict_id,
                    payload={"rule_id": rule_id, "error": str(e)},
                )
                
                if self._terminal_output:
                    print(f"  🔴 [{rule_id}] EVALUATION ERROR: {e}")
        
        # Determine verdict status
        # Only LOW and INFO violations don't block
        blocking_violations = [
            v for v in violations
            if v.rule.severity in {RuleSeverity.CRITICAL, RuleSeverity.HIGH, RuleSeverity.MEDIUM}
        ]
        
        if not blocking_violations:
            status = VerdictStatus.APPROVED
            self._emitter.emit(
                LexEventType.VERDICT_APPROVED,
                verdict_id,
                payload={"rules_passed": len(rules_passed)},
            )
        else:
            # Check if all blocking violations are overrideable
            non_overrideable = [v for v in blocking_violations if not v.rule.override_allowed]
            
            if non_overrideable:
                status = VerdictStatus.REJECTED
            else:
                status = VerdictStatus.PENDING_OVERRIDE
            
            self._emitter.emit(
                LexEventType.VERDICT_REJECTED,
                verdict_id,
                payload={
                    "violation_count": len(violations),
                    "blocking_rules": [v.rule.rule_id for v in blocking_violations],
                },
            )
        
        # Create verdict
        verdict = LexVerdict(
            verdict_id=verdict_id,
            status=status,
            pdo_hash=pdo_hash,
            rules_evaluated=rules_evaluated,
            rules_passed=rules_passed,
            violations=violations,
        )
        
        # Emit enforcement event
        if verdict.is_blocked:
            self._emitter.emit(
                LexEventType.EXECUTION_BLOCKED,
                verdict_id,
                payload={"blocking_rules": verdict.blocking_rules},
            )
        else:
            self._emitter.emit(
                LexEventType.EXECUTION_PERMITTED,
                verdict_id,
            )
        
        # Create enforcement record
        record = EnforcementRecord(
            record_id=f"LEX-R-{uuid.uuid4().hex[:12].upper()}",
            verdict=verdict,
            pdo_snapshot=pdo,
            context=context,
        )
        self._records.append(record)
        
        # Emit validation complete
        self._emitter.emit(
            LexEventType.VALIDATION_COMPLETE,
            verdict_id,
            payload={"status": verdict.status.value},
        )
        
        if self._terminal_output:
            print(verdict.render_terminal())
        
        return verdict
    
    def apply_override(
        self,
        verdict: LexVerdict,
        override_id: str,
    ) -> LexVerdict:
        """
        Apply an approved override to a verdict.
        
        Args:
            verdict: The original verdict with PENDING_OVERRIDE status
            override_id: The approved override ID
            
        Returns:
            New verdict with OVERRIDDEN status
            
        Note:
            This creates a NEW verdict — the original is immutable.
        """
        if verdict.status != VerdictStatus.PENDING_OVERRIDE:
            raise ValueError(f"Cannot override verdict with status {verdict.status.value}")
        
        # Create new verdict with override
        new_verdict = LexVerdict(
            verdict_id=f"{verdict.verdict_id}-OVR",
            status=VerdictStatus.OVERRIDDEN,
            pdo_hash=verdict.pdo_hash,
            rules_evaluated=verdict.rules_evaluated,
            rules_passed=verdict.rules_passed,
            violations=verdict.violations,
            override_id=override_id,
        )
        
        self._emitter.emit(
            LexEventType.OVERRIDE_APPROVED,
            new_verdict.verdict_id,
            payload={"override_id": override_id, "original_verdict": verdict.verdict_id},
        )
        
        return new_verdict
    
    def _compute_pdo_hash(self, pdo: dict[str, Any]) -> str:
        """Compute deterministic hash of PDO."""
        data = json.dumps(pdo, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _render_header(self, verdict_id: str, pdo_hash: str) -> None:
        """Render validation header to terminal."""
        print("")
        print("═" * 70)
        print(f"🟥🟥🟥 LEX VALIDATOR — {verdict_id} 🟥🟥🟥")
        print("═" * 70)
        print("")
        print(f"PDO Hash: {pdo_hash}")
        print(f"Rules Registered: {len(self._rules)}")
        print(f"Mode: DETERMINISTIC ENFORCEMENT")
        print("")
        print("─" * 70)
        print("RULE EVALUATION")
        print("─" * 70)
    
    def get_records(self) -> list[EnforcementRecord]:
        """Get all enforcement records (audit log)."""
        return list(self._records)
    
    def get_rule(self, rule_id: str) -> Optional[LexRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)
    
    def get_all_rules(self) -> list[LexRule]:
        """Get all registered rules."""
        return list(self._rules.values())
