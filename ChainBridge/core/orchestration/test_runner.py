#!/usr/bin/env python3
"""
Orchestration Engine Test Runner
================================

Validates the orchestration engine with halt-on-failure semantics.

Usage:
    python -m core.orchestration.test_runner
"""

import sys
from datetime import datetime, timezone

from core.orchestration.engine import OrchestrationEngine
from core.orchestration.gates import create_standard_gates


def create_valid_context() -> dict:
    """Create a valid execution context that should pass all gates."""
    return {
        # PAG-01: Agent Activation
        "agent_name": "Cody",
        "agent_gid": "01",
        "agent_role": "Senior Backend Engineer",
        "agent_authority": ["backend_implementation", "runtime_infrastructure", "deterministic_execution"],
        
        # PAG-02: Runtime Activation
        "runtime_mode": "EXECUTION",
        "governance_mode": "GOLD_STANDARD",
        "failure_discipline": "FAIL-CLOSED",
        "observability": "MANDATORY",
        "pdo_canon_locked": True,
        
        # PAG-03: Execution Lane
        "execution_lane": "backend",
        "requested_outputs": ["code", "tests", "wrap"],
        
        # PAG-04: Governance Mode
        "enforcement_rules_active": True,
        "allow_implicit_success": False,
        "allow_optimistic_execution": False,
        
        # PAG-06: Payload
        "payload_type": "backend_implementation",
        "payload_purpose": "Implement orchestration engine with PAG gates",
    }


def create_failing_context() -> dict:
    """Create a context that will fail at PAG-01 (missing agent_gid)."""
    return {
        "agent_name": "Unknown",
        # Missing agent_gid - will fail
        "agent_role": "Test Role",
    }


def run_success_test():
    """Test successful execution through all gates."""
    print("\n" + "=" * 70)
    print("TEST: Successful Execution (All Gates PASS)")
    print("=" * 70)
    
    engine = OrchestrationEngine(
        execution_id=f"TEST-SUCCESS-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        terminal_output=True,
    )
    
    gates = create_standard_gates()
    engine.register_gates(gates)
    engine.set_context(create_valid_context())
    
    report = engine.run()
    
    assert report.state.value == "COMPLETED", f"Expected COMPLETED, got {report.state.value}"
    assert report.gates_passed == 7, f"Expected 7 gates passed, got {report.gates_passed}"
    assert report.gates_failed == 0, f"Expected 0 gates failed, got {report.gates_failed}"
    
    print("\n✅ SUCCESS TEST PASSED")
    return True


def run_halt_test():
    """Test halt-on-failure behavior."""
    print("\n" + "=" * 70)
    print("TEST: Halt-on-Failure (PAG-01 FAIL)")
    print("=" * 70)
    
    engine = OrchestrationEngine(
        execution_id=f"TEST-HALT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        terminal_output=True,
    )
    
    gates = create_standard_gates()
    engine.register_gates(gates)
    engine.set_context(create_failing_context())
    
    report = engine.run()
    
    assert report.state.value == "HALTED", f"Expected HALTED, got {report.state.value}"
    assert report.gates_executed == 1, f"Expected 1 gate executed, got {report.gates_executed}"
    assert report.gates_failed == 1, f"Expected 1 gate failed, got {report.gates_failed}"
    assert report.halt_reason is not None, "Expected halt_reason to be set"
    
    print("\n✅ HALT TEST PASSED")
    return True


def run_mid_execution_halt_test():
    """Test halt in the middle of execution (PAG-03 fail)."""
    print("\n" + "=" * 70)
    print("TEST: Mid-Execution Halt (PAG-03 FAIL - Lane Violation)")
    print("=" * 70)
    
    engine = OrchestrationEngine(
        execution_id=f"TEST-MID-HALT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        terminal_output=True,
    )
    
    gates = create_standard_gates()
    engine.register_gates(gates)
    
    # Context that passes PAG-01 and PAG-02 but fails PAG-03
    context = create_valid_context()
    context["execution_lane"] = "backend"
    context["requested_outputs"] = ["ui_work"]  # Forbidden for backend lane
    
    engine.set_context(context)
    
    report = engine.run()
    
    assert report.state.value == "HALTED", f"Expected HALTED, got {report.state.value}"
    assert report.gates_executed == 3, f"Expected 3 gates executed, got {report.gates_executed}"
    assert report.gates_failed == 1, f"Expected 1 gate failed, got {report.gates_failed}"
    
    print("\n✅ MID-EXECUTION HALT TEST PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "═" * 70)
    print("🟦🟦🟦 ORCHESTRATION ENGINE TEST SUITE 🟦🟦🟦")
    print("═" * 70)
    
    tests = [
        ("Success Test", run_success_test),
        ("Halt Test", run_halt_test),
        ("Mid-Execution Halt Test", run_mid_execution_halt_test),
    ]
    
    results = []
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ {name} FAILED: {e}")
    
    # Summary
    print("\n" + "═" * 70)
    print("TEST SUMMARY")
    print("═" * 70)
    
    passed = sum(1 for _, r, _ in results if r)
    failed = len(results) - passed
    
    for name, result, error in results:
        icon = "✅" if result else "❌"
        status = "PASS" if result else f"FAIL: {error}"
        print(f"  {icon} {name}: {status}")
    
    print("─" * 70)
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("═" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
