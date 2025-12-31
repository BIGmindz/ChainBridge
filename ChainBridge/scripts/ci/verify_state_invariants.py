#!/usr/bin/env python3
"""
CI Script: Verify State Invariants

Atlas (GID-05) — System State Engine
Authority: Benson (GID-00)

This script validates all A11 system state invariants before CI pass.
Exit codes:
  0 = All invariants verified
  1 = Invariant violation detected
  2 = Script execution error
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.state import (
        ArtifactType,
        StateValidator,
        ValidationResult,
        ViolationSeverity,
        is_valid_transition,
        get_terminal_states,
        SHIPMENT_TRANSITIONS,
        SETTLEMENT_TRANSITIONS,
        PDO_TRANSITIONS,
        ShipmentState,
        SettlementState,
        PDOState,
    )
except ImportError as e:
    print(f"[FATAL] Failed to import state modules: {e}")
    sys.exit(2)


# =============================================================================
# INVARIANT VERIFICATION
# =============================================================================


def verify_transition_completeness() -> tuple[bool, list[str]]:
    """Verify all state transitions are defined and valid.

    Returns:
        Tuple of (success, list of error messages)
    """
    errors: list[str] = []

    # Verify Shipment transitions
    for from_state in ShipmentState:
        if from_state.value in get_terminal_states(ArtifactType.SHIPMENT):
            # Terminal states should have no outgoing transitions
            if from_state.value in SHIPMENT_TRANSITIONS:
                if SHIPMENT_TRANSITIONS[from_state.value]:
                    errors.append(
                        f"Terminal state {from_state.value} has outgoing transitions"
                    )
        else:
            # Non-terminal states should have at least one transition
            if from_state.value not in SHIPMENT_TRANSITIONS:
                errors.append(
                    f"Non-terminal state {from_state.value} has no transitions defined"
                )

    # Verify Settlement transitions
    for from_state in SettlementState:
        if from_state.value in get_terminal_states(ArtifactType.SETTLEMENT):
            if from_state.value in SETTLEMENT_TRANSITIONS:
                if SETTLEMENT_TRANSITIONS[from_state.value]:
                    errors.append(
                        f"Terminal state {from_state.value} has outgoing transitions"
                    )

    # Verify PDO transitions
    for from_state in PDOState:
        if from_state.value in get_terminal_states(ArtifactType.PDO):
            if from_state.value in PDO_TRANSITIONS:
                if PDO_TRANSITIONS[from_state.value]:
                    errors.append(
                        f"Terminal state {from_state.value} has outgoing transitions"
                    )

    return len(errors) == 0, errors


def verify_no_self_loops_in_transitions() -> tuple[bool, list[str]]:
    """Verify no state transitions to itself (self-loops).

    Note: Cycles between different states may be valid business logic
    (e.g., BLOCKED -> PENDING for unblocking). We only check for
    direct self-transitions which are always invalid.

    Returns:
        Tuple of (success, list of error messages)
    """
    errors: list[str] = []

    # Check Shipment transitions for self-loops
    for state, targets in SHIPMENT_TRANSITIONS.items():
        if state in targets:
            errors.append(f"Self-loop detected in Shipment: {state.value} → {state.value}")

    # Check Settlement transitions for self-loops
    for state, targets in SETTLEMENT_TRANSITIONS.items():
        if state in targets:
            errors.append(f"Self-loop detected in Settlement: {state.value} → {state.value}")

    # Check PDO transitions for self-loops
    for state, targets in PDO_TRANSITIONS.items():
        if state in targets:
            errors.append(f"Self-loop detected in PDO: {state.value} → {state.value}")

    return len(errors) == 0, errors


def verify_terminal_states_defined() -> tuple[bool, list[str]]:
    """Verify all artifact types have terminal states defined.

    Returns:
        Tuple of (success, list of error messages)
    """
    errors: list[str] = []

    for artifact_type in [ArtifactType.SHIPMENT, ArtifactType.SETTLEMENT, ArtifactType.PDO]:
        terminals = get_terminal_states(artifact_type)
        if not terminals:
            errors.append(f"No terminal states defined for {artifact_type.value}")

    return len(errors) == 0, errors


def verify_validator_instantiation() -> tuple[bool, list[str]]:
    """Verify StateValidator can be instantiated.

    Returns:
        Tuple of (success, list of error messages)
    """
    errors: list[str] = []

    try:
        validator = StateValidator()
        if validator is None:
            errors.append("StateValidator instantiated but is None")
    except Exception as e:
        errors.append(f"Failed to instantiate StateValidator: {e}")

    return len(errors) == 0, errors


def verify_all_invariants() -> dict[str, Any]:
    """Run all invariant verifications.

    Returns:
        Dictionary with verification results
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "verifications": [],
        "all_passed": True,
        "total_errors": 0,
    }

    verifications = [
        ("INV-S10: Transition Completeness", verify_transition_completeness),
        ("INV-S02: No Self-Loops", verify_no_self_loops_in_transitions),
        ("INV-S03: Terminal States Defined", verify_terminal_states_defined),
        ("Core: Validator Instantiation", verify_validator_instantiation),
    ]

    for name, func in verifications:
        try:
            passed, errors = func()
            results["verifications"].append({
                "name": name,
                "passed": passed,
                "errors": errors,
            })
            if not passed:
                results["all_passed"] = False
                results["total_errors"] += len(errors)
        except Exception as e:
            results["verifications"].append({
                "name": name,
                "passed": False,
                "errors": [f"Verification raised exception: {e}"],
            })
            results["all_passed"] = False
            results["total_errors"] += 1

    return results


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main() -> int:
    """Main entry point for CI verification.

    Returns:
        Exit code (0 = success, 1 = violations, 2 = error)
    """
    print("=" * 70)
    print("ChainBridge State Invariant Verification")
    print("Atlas (GID-05) — System State Engine")
    print("=" * 70)
    print()

    try:
        results = verify_all_invariants()
    except Exception as e:
        print(f"[FATAL] Verification failed with exception: {e}")
        return 2

    # Print results
    print(f"Timestamp: {results['timestamp']}")
    print()

    for verification in results["verifications"]:
        status = "✓ PASS" if verification["passed"] else "✗ FAIL"
        print(f"  {status}  {verification['name']}")
        if not verification["passed"]:
            for error in verification["errors"]:
                print(f"         └── {error}")

    print()
    print("-" * 70)

    if results["all_passed"]:
        print("RESULT: ALL INVARIANTS VERIFIED")
        print("-" * 70)
        return 0
    else:
        print(f"RESULT: {results['total_errors']} INVARIANT VIOLATION(S) DETECTED")
        print("-" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
