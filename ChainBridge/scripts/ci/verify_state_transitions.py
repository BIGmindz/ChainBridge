#!/usr/bin/env python3
"""
ChainBridge State Transition CI Verification

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

PAC: PAC-ATLAS-A12-STATE-TRANSITION-GOVERNANCE-LOCK-01

This script verifies:
1. All state machines are structurally valid (no orphan states)
2. Defined transitions have proper authority requirements
3. Fail-closed semantics: undefined transitions → REJECT
4. Terminal states have no outgoing transitions
5. All transition rules reference valid states

Exit codes:
0 = All checks pass
1 = Verification failures detected
2 = Script execution error
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# Ensure ChainBridge modules are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.state.state_machine import (
    STATE_MACHINES,
    StateMachine,
    validate_all_state_machines,
    get_state_machine,
)
from core.state.transition_validator import (
    TransitionValidator,
    TransitionRequest,
    TransitionResult,
    validate_transition,
)


# =============================================================================
# VERIFICATION RESULT TRACKING
# =============================================================================


class CheckStatus(Enum):
    """Status of a verification check."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    status: CheckStatus
    message: str
    details: list[str]

    def __str__(self) -> str:
        status_icon = {
            CheckStatus.PASS: "✅",
            CheckStatus.FAIL: "❌",
            CheckStatus.WARN: "⚠️",
            CheckStatus.SKIP: "⏭️",
        }
        return f"{status_icon[self.status]} [{self.status.value}] {self.name}: {self.message}"


class VerificationReport:
    """Collects and reports verification results."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.results: list[CheckResult] = []

    def add(self, result: CheckResult) -> None:
        """Add a check result."""
        self.results.append(result)

    @property
    def passed(self) -> bool:
        """All checks passed (no failures)."""
        return all(r.status != CheckStatus.FAIL for r in self.results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARN)

    def print_report(self) -> None:
        """Print the verification report."""
        print(f"\n{'='*60}")
        print(f"🔍 {self.title}")
        print(f"{'='*60}\n")

        for result in self.results:
            print(str(result))
            if result.details and result.status == CheckStatus.FAIL:
                for detail in result.details:
                    print(f"   → {detail}")

        print(f"\n{'-'*60}")
        print(f"Summary: {self.pass_count} passed, {self.fail_count} failed, {self.warn_count} warnings")
        print(f"Verdict: {'✅ PASS' if self.passed else '❌ FAIL'}")
        print(f"{'='*60}\n")


# =============================================================================
# VERIFICATION CHECKS
# =============================================================================


def check_state_machine_registry() -> CheckResult:
    """Verify state machine registry is populated."""
    if not STATE_MACHINES:
        return CheckResult(
            name="State Machine Registry",
            status=CheckStatus.FAIL,
            message="Registry is empty",
            details=["No state machines found in STATE_MACHINES"],
        )

    return CheckResult(
        name="State Machine Registry",
        status=CheckStatus.PASS,
        message=f"Found {len(STATE_MACHINES)} state machines",
        details=list(STATE_MACHINES.keys()),
    )


def check_state_machine_integrity() -> CheckResult:
    """Verify all state machines pass structural validation."""
    results = validate_all_state_machines()

    # validate_all_state_machines returns dict[name, list[errors]]
    all_errors = []
    for name, errors in results.items():
        all_errors.extend(errors)

    if all_errors:
        return CheckResult(
            name="State Machine Integrity",
            status=CheckStatus.FAIL,
            message=f"{len(all_errors)} integrity violations",
            details=all_errors,
        )

    return CheckResult(
        name="State Machine Integrity",
        status=CheckStatus.PASS,
        message="All state machines structurally valid",
        details=[],
    )


def check_terminal_states() -> CheckResult:
    """Verify terminal states have no outgoing transitions."""
    violations: list[str] = []

    for name, machine in STATE_MACHINES.items():
        for state in machine.terminal_states:
            # Check via transitions dict - terminal states should have empty sets
            outgoing = machine.transitions.get(state, set())
            if outgoing:
                violations.append(
                    f"{name}: Terminal state '{state}' has {len(outgoing)} outgoing transition(s)"
                )

    if violations:
        return CheckResult(
            name="Terminal State Invariant",
            status=CheckStatus.FAIL,
            message="Terminal states have outgoing transitions",
            details=violations,
        )

    return CheckResult(
        name="Terminal State Invariant",
        status=CheckStatus.PASS,
        message="All terminal states are immutable",
        details=[],
    )


def check_authority_requirements() -> CheckResult:
    """Verify all transitions have authority requirements."""
    missing: list[str] = []

    for name, machine in STATE_MACHINES.items():
        for (from_state, to_state), rule in machine.transition_rules.items():
            if not rule.required_authority:
                missing.append(
                    f"{name}: {from_state} → {to_state} has no authority"
                )

    if missing:
        return CheckResult(
            name="Authority Requirements",
            status=CheckStatus.WARN,
            message=f"{len(missing)} transitions without explicit authority",
            details=missing,
        )

    return CheckResult(
        name="Authority Requirements",
        status=CheckStatus.PASS,
        message="All transitions have authority requirements",
        details=[],
    )


def check_fail_closed_semantics() -> CheckResult:
    """Verify undefined transitions are rejected."""
    validator = TransitionValidator()
    violations: list[str] = []

    for name, machine in STATE_MACHINES.items():
        # Get all possible states from the machine
        all_states = machine.states

        # Test undefined transitions (transitions not in rules)
        for from_state in all_states:
            for to_state in all_states:
                if from_state == to_state:
                    continue

                # Check if this transition is defined
                is_defined = machine.is_valid_transition(from_state, to_state)

                if not is_defined:
                    # This undefined transition should be rejected
                    request = TransitionRequest(
                        artifact_type=name,
                        artifact_id="test-artifact",
                        from_state=from_state,
                        to_state=to_state,
                    )
                    result = validator.validate_transition(request)

                    if result.is_allowed:
                        violations.append(
                            f"{name}: undefined transition "
                            f"{from_state} → {to_state} was ALLOWED"
                        )

    if violations:
        return CheckResult(
            name="Fail-Closed Semantics",
            status=CheckStatus.FAIL,
            message="Undefined transitions not rejected",
            details=violations,
        )

    return CheckResult(
        name="Fail-Closed Semantics",
        status=CheckStatus.PASS,
        message="All undefined transitions rejected",
        details=[],
    )


def check_initial_states() -> CheckResult:
    """Verify each state machine has reachable initial states."""
    issues: list[str] = []

    for name, machine in STATE_MACHINES.items():
        # Find states that are only targets (derive from transitions dict)
        source_states = set(machine.transitions.keys())
        target_states = set()
        for targets in machine.transitions.values():
            target_states.update(targets)

        # States that are sources but never targets (initial candidates)
        initial_candidates = source_states - target_states

        if not initial_candidates:
            # All source states are also targets - might be cyclical
            # Check for terminal reachability
            terminal_reach = False
            for state in source_states:
                if state in machine.terminal_states:
                    terminal_reach = True
                    break
            if not terminal_reach and machine.terminal_states:
                issues.append(
                    f"{name}: No clear path from initial to terminal states"
                )

    if issues:
        return CheckResult(
            name="Initial State Reachability",
            status=CheckStatus.WARN,
            message="Potential reachability issues",
            details=issues,
        )

    return CheckResult(
        name="Initial State Reachability",
        status=CheckStatus.PASS,
        message="State machines have clear initial states",
        details=[],
    )


def check_proof_requirements() -> CheckResult:
    """Verify critical transitions require proofs."""
    critical_without_proof: list[str] = []

    for name, machine in STATE_MACHINES.items():
        for (from_state, to_state), rule in machine.transition_rules.items():
            # Check for terminal transitions without proof requirement
            if to_state in machine.terminal_states and not rule.requires_proof:
                critical_without_proof.append(
                    f"{name}: {from_state} → {to_state} "
                    f"(terminal) does not require proof"
                )

    if critical_without_proof:
        return CheckResult(
            name="Proof Requirements",
            status=CheckStatus.WARN,
            message="Some terminal transitions lack proof requirement",
            details=critical_without_proof,
        )

    return CheckResult(
        name="Proof Requirements",
        status=CheckStatus.PASS,
        message="Critical transitions require proofs",
        details=[],
    )


def check_required_artifact_types() -> CheckResult:
    """Verify required artifact types are defined."""
    # Registry uses uppercase keys
    required_types = ["PDO", "SETTLEMENT", "PROOF", "DEPLOYMENT", "RISK_DECISION"]
    missing = [t for t in required_types if t not in STATE_MACHINES]

    if missing:
        return CheckResult(
            name="Required Artifact Types",
            status=CheckStatus.FAIL,
            message=f"Missing {len(missing)} required artifact types",
            details=missing,
        )

    return CheckResult(
        name="Required Artifact Types",
        status=CheckStatus.PASS,
        message=f"All {len(required_types)} required types defined",
        details=[],
    )


# =============================================================================
# MAIN VERIFICATION
# =============================================================================


def run_verification() -> bool:
    """Run all verification checks."""
    report = VerificationReport("PAC-ATLAS-A12 State Transition Verification")

    # Run all checks
    report.add(check_state_machine_registry())
    report.add(check_required_artifact_types())
    report.add(check_state_machine_integrity())
    report.add(check_terminal_states())
    report.add(check_authority_requirements())
    report.add(check_fail_closed_semantics())
    report.add(check_initial_states())
    report.add(check_proof_requirements())

    # Print report
    report.print_report()

    return report.passed


def main() -> int:
    """Main entry point."""
    print("\n🔐 PAC-ATLAS-A12: State Transition Governance Verification")
    print("   Atlas (GID-05) — System State Engine")
    print("   Authority: Benson (GID-00)\n")

    try:
        passed = run_verification()
        return 0 if passed else 1
    except Exception as e:
        print(f"\n❌ Script execution error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
