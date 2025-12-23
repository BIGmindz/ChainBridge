#!/usr/bin/env python3
"""State Invariant Failure Drills.

This utility module executes adversarial drills against the state transition
and invariant layer to prove deterministic rejection of invalid operations.

Authority: Atlas (GID-11) — Build / Repair / Refactor Agent
Reference: Governance Invariant Failure Drill Specification
Mode: FAIL_CLOSED

FAILURE_DRILLS:
  - SD-01: Undefined transition requested
  - SD-02: Terminal state mutation
  - SD-03: Missing transition proof
  - SD-04: Invalid authority on transition
  - SD-05: Replay divergence detected

SUCCESS_METRICS:
  invariant_violations_allowed: 0
  silent_failures: 0
  replay_divergence_tolerated: false
  deterministic_errors: true
  bypass_paths_detected: 0
"""

import sys
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Add repo root to path
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.state.state_machine import (
    PDO_STATE_MACHINE,
    SETTLEMENT_STATE_MACHINE,
)
from core.state.state_schema import (
    ArtifactType,
    EventStateRecord,
    EventType,
    PDOState,
    SettlementState,
)
from core.state.transition_validator import (
    TransitionValidator,
    TransitionRequest,
    TransitionResult,
)
from core.state.state_replay import (
    StateReplayEngine,
    verify_replay_determinism,
)


# =============================================================================
# DRILL RESULT TYPES
# =============================================================================


@dataclass
class DrillResult:
    """Result of a single invariant drill."""
    drill_id: str
    drill_name: str
    scenario: str
    expected_outcome: str  # "RUNTIME_BLOCK" or "CI_BLOCK"
    actual_outcome: str
    passed: bool
    error_code: Optional[str] = None
    rejection_reason: Optional[str] = None
    state_hash: Optional[str] = None
    elapsed_ms: float = 0.0
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "drill_name": self.drill_name,
            "scenario": self.scenario,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "passed": self.passed,
            "error_code": self.error_code,
            "rejection_reason": self.rejection_reason,
            "state_hash": self.state_hash,
            "elapsed_ms": self.elapsed_ms,
            "evidence": self.evidence,
        }


@dataclass
class DrillSuiteResult:
    """Result of all invariant drills."""
    total_drills: int = 0
    passed_drills: int = 0
    failed_drills: int = 0
    invariant_violations_allowed: int = 0
    silent_failures: int = 0
    replay_divergence_tolerated: bool = False
    bypass_paths_detected: int = 0
    results: list = field(default_factory=list)
    executed_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# SD-01: UNDEFINED TRANSITION REQUESTED
# =============================================================================

def drill_sd01_undefined_transition() -> DrillResult:
    """
    SD-01: Undefined transition requested → RUNTIME_BLOCK
    
    Attempts a transition that is NOT declared in the state machine.
    Expected: Deterministic rejection with REJECTED_UNDEFINED.
    """
    start = datetime.utcnow()
    validator = TransitionValidator()
    
    # Attempt CREATED → ACCEPTED (bypassing SIGNED → VERIFIED)
    # This transition is NOT declared in PDO_STATE_MACHINE
    request = TransitionRequest(
        artifact_type="PDO",
        artifact_id="drill-sd01-test-artifact",
        from_state=PDOState.CREATED.value,
        to_state=PDOState.ACCEPTED.value,  # Invalid: must go CREATED→SIGNED→VERIFIED→ACCEPTED
        authority_gid="GID-05",
        proof_id="proof-sd01-test",
    )
    
    result = validator.validate_transition(request)
    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
    
    # Expected: REJECTED_UNDEFINED
    is_blocked = result.result == TransitionResult.REJECTED_UNDEFINED
    
    return DrillResult(
        drill_id="SD-01",
        drill_name="Undefined Transition Requested",
        scenario="Attempt CREATED → ACCEPTED (bypassing required intermediate states)",
        expected_outcome="RUNTIME_BLOCK",
        actual_outcome="RUNTIME_BLOCK" if is_blocked else "ALLOWED",
        passed=is_blocked,
        error_code=result.result.value if not result.is_allowed else None,
        rejection_reason=result.rejection_reason,
        elapsed_ms=elapsed,
        evidence={
            "artifact_type": request.artifact_type,
            "from_state": request.from_state,
            "to_state": request.to_state,
            "validation_result": result.result.value,
            "is_allowed": result.is_allowed,
        }
    )


# =============================================================================
# SD-02: TERMINAL STATE MUTATION
# =============================================================================

def drill_sd02_terminal_state_mutation() -> DrillResult:
    """
    SD-02: Terminal state mutation → RUNTIME_BLOCK
    
    Attempts to transition FROM a terminal state.
    Expected: Deterministic rejection with REJECTED_TERMINAL.
    """
    start = datetime.utcnow()
    validator = TransitionValidator()
    
    # Terminal states in PDO: ACCEPTED, REJECTED, EXPIRED
    # Attempt ACCEPTED → CREATED (trying to reset a finalized PDO)
    request = TransitionRequest(
        artifact_type="PDO",
        artifact_id="drill-sd02-test-artifact",
        from_state=PDOState.ACCEPTED.value,  # Terminal state
        to_state=PDOState.CREATED.value,
        authority_gid="GID-00",  # Even Benson cannot mutate terminal state
        proof_id="proof-sd02-test",
    )
    
    result = validator.validate_transition(request)
    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
    
    # Expected: REJECTED_TERMINAL
    is_blocked = result.result == TransitionResult.REJECTED_TERMINAL
    
    return DrillResult(
        drill_id="SD-02",
        drill_name="Terminal State Mutation",
        scenario="Attempt ACCEPTED → CREATED (mutating finalized artifact)",
        expected_outcome="RUNTIME_BLOCK",
        actual_outcome="RUNTIME_BLOCK" if is_blocked else "ALLOWED",
        passed=is_blocked,
        error_code=result.result.value if not result.is_allowed else None,
        rejection_reason=result.rejection_reason,
        elapsed_ms=elapsed,
        evidence={
            "artifact_type": request.artifact_type,
            "from_state": request.from_state,
            "to_state": request.to_state,
            "terminal_states": list(PDO_STATE_MACHINE.terminal_states),
            "validation_result": result.result.value,
            "is_allowed": result.is_allowed,
        }
    )


# =============================================================================
# SD-03: MISSING TRANSITION PROOF
# =============================================================================

def drill_sd03_missing_proof() -> DrillResult:
    """
    SD-03: Missing transition proof → RUNTIME_BLOCK
    
    Attempts a valid transition WITHOUT providing proof_id.
    Expected: Deterministic rejection with REJECTED_MISSING_PROOF.
    """
    start = datetime.utcnow()
    validator = TransitionValidator()
    
    # Valid transition but NO proof_id
    request = TransitionRequest(
        artifact_type="PDO",
        artifact_id="drill-sd03-test-artifact",
        from_state=PDOState.CREATED.value,
        to_state=PDOState.SIGNED.value,  # Valid transition
        authority_gid="GID-05",
        proof_id=None,  # MISSING PROOF
    )
    
    result = validator.validate_transition(request)
    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
    
    # Expected: REJECTED_MISSING_PROOF
    is_blocked = result.result == TransitionResult.REJECTED_MISSING_PROOF
    
    return DrillResult(
        drill_id="SD-03",
        drill_name="Missing Transition Proof",
        scenario="Attempt CREATED → SIGNED without proof_id",
        expected_outcome="RUNTIME_BLOCK",
        actual_outcome="RUNTIME_BLOCK" if is_blocked else "ALLOWED",
        passed=is_blocked,
        error_code=result.result.value if not result.is_allowed else None,
        rejection_reason=result.rejection_reason,
        elapsed_ms=elapsed,
        evidence={
            "artifact_type": request.artifact_type,
            "from_state": request.from_state,
            "to_state": request.to_state,
            "proof_id_provided": request.proof_id is not None,
            "validation_result": result.result.value,
            "is_allowed": result.is_allowed,
        }
    )


# =============================================================================
# SD-04: INVALID AUTHORITY ON TRANSITION
# =============================================================================

def drill_sd04_invalid_authority() -> DrillResult:
    """
    SD-04: Invalid authority on transition → RUNTIME_BLOCK
    
    Attempts a transition that requires specific authority with wrong GID.
    Expected: Deterministic rejection with REJECTED_AUTHORITY_MISMATCH.
    """
    start = datetime.utcnow()
    validator = TransitionValidator()
    
    # Settlement PENDING → APPROVED requires CRO authority per transition rules
    request = TransitionRequest(
        artifact_type="SETTLEMENT",
        artifact_id="drill-sd04-test-artifact",
        from_state=SettlementState.PENDING.value,
        to_state=SettlementState.APPROVED.value,
        authority_gid="GID-INVALID-TEST",  # Invalid/unknown authority for testing
        proof_id="proof-sd04-test",
    )
    
    result = validator.validate_transition(request)
    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
    
    # Expected: REJECTED_AUTHORITY_MISMATCH or REJECTED_MISSING_AUTHORITY
    is_blocked = result.result in (
        TransitionResult.REJECTED_AUTHORITY_MISMATCH,
        TransitionResult.REJECTED_MISSING_AUTHORITY,
    )
    
    return DrillResult(
        drill_id="SD-04",
        drill_name="Invalid Authority on Transition",
        scenario="Attempt PENDING → APPROVED with unauthorized GID",
        expected_outcome="RUNTIME_BLOCK",
        actual_outcome="RUNTIME_BLOCK" if is_blocked else "ALLOWED",
        passed=is_blocked,
        error_code=result.result.value if not result.is_allowed else None,
        rejection_reason=result.rejection_reason,
        elapsed_ms=elapsed,
        evidence={
            "artifact_type": request.artifact_type,
            "from_state": request.from_state,
            "to_state": request.to_state,
            "authority_provided": request.authority_gid,
            "required_authority": result.required_authority,
            "validation_result": result.result.value,
            "is_allowed": result.is_allowed,
        }
    )


# =============================================================================
# SD-05: REPLAY DIVERGENCE DETECTED
# =============================================================================

def drill_sd05_replay_divergence() -> DrillResult:
    """
    SD-05: Replay divergence detected → CI_BLOCK
    
    Constructs event log that when replayed produces different state than expected.
    Expected: Deterministic failure of replay verification.
    """
    import hashlib
    start = datetime.utcnow()
    engine = StateReplayEngine()
    
    # Create valid event sequence
    base_time = datetime.utcnow()
    events = [
        EventStateRecord(
            event_id="evt-sd05-001",
            event_type=EventType.PDO_CREATED,
            artifact_type=ArtifactType.PDO,
            artifact_id="pdo-sd05-test",
            timestamp=base_time,
            sequence_number=1,
            payload_hash=hashlib.sha256(b"event-1-payload").hexdigest(),
        ),
        EventStateRecord(
            event_id="evt-sd05-002",
            event_type=EventType.PDO_SIGNED,
            artifact_type=ArtifactType.PDO,
            artifact_id="pdo-sd05-test",
            timestamp=base_time + timedelta(seconds=1),
            sequence_number=2,
            payload_hash=hashlib.sha256(b"event-2-payload").hexdigest(),
        ),
    ]
    
    # Replay with WRONG expected state (claim it should be VERIFIED but actually SIGNED)
    result = engine.replay_events(
        events=events,
        artifact_type=ArtifactType.PDO,
        artifact_id="pdo-sd05-test",
        expected_final_state=PDOState.VERIFIED.value,  # WRONG - should be SIGNED
    )
    
    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
    
    # Expected: is_deterministic = False (divergence detected)
    divergence_detected = not result.is_deterministic
    
    return DrillResult(
        drill_id="SD-05",
        drill_name="Replay Divergence Detection",
        scenario="Replay events expecting VERIFIED but actual state is SIGNED",
        expected_outcome="CI_BLOCK",
        actual_outcome="CI_BLOCK" if divergence_detected else "ALLOWED",
        passed=divergence_detected,
        error_code="REPLAY_DIVERGENCE" if divergence_detected else None,
        rejection_reason="; ".join(result.validation_errors) if result.validation_errors else None,
        state_hash=result.state_hash,
        elapsed_ms=elapsed,
        evidence={
            "expected_state": PDOState.VERIFIED.value,
            "computed_state": result.computed_state,
            "is_deterministic": result.is_deterministic,
            "events_processed": result.events_processed,
            "transitions_applied": result.transitions_applied,
            "validation_errors": result.validation_errors,
        }
    )


# =============================================================================
# DRILL RUNNER
# =============================================================================

# Reference identifier for this drill suite
_DRILL_REF = "ATLAS-G1-PHASE-2-GOVERNANCE-INVARIANT-FAILURE-DRILLS-01"


def run_all_drills() -> DrillSuiteResult:
    """Execute all state invariant failure drills."""
    suite = DrillSuiteResult()
    all_results: list[DrillResult] = []
    
    print("=" * 70)
    print("STATE INVARIANT FAILURE DRILLS")
    print(f"Reference: {_DRILL_REF}")
    print("Mode: FAIL_CLOSED")
    print("=" * 70)
    print()
    
    # SD-01: Undefined Transition
    print("SD-01: Undefined Transition Requested")
    print("-" * 40)
    result_01 = drill_sd01_undefined_transition()
    all_results.append(result_01)
    status = "✓ BLOCKED" if result_01.passed else "✗ ALLOWED (VIOLATION)"
    print(f"  {status}")
    print(f"  Scenario: {result_01.scenario}")
    print(f"  Result: {result_01.error_code or 'ALLOWED'}")
    if result_01.rejection_reason:
        print(f"  Reason: {result_01.rejection_reason}")
    print()
    
    # SD-02: Terminal State Mutation
    print("SD-02: Terminal State Mutation")
    print("-" * 40)
    result_02 = drill_sd02_terminal_state_mutation()
    all_results.append(result_02)
    status = "✓ BLOCKED" if result_02.passed else "✗ ALLOWED (VIOLATION)"
    print(f"  {status}")
    print(f"  Scenario: {result_02.scenario}")
    print(f"  Result: {result_02.error_code or 'ALLOWED'}")
    if result_02.rejection_reason:
        print(f"  Reason: {result_02.rejection_reason}")
    print()
    
    # SD-03: Missing Proof
    print("SD-03: Missing Transition Proof")
    print("-" * 40)
    result_03 = drill_sd03_missing_proof()
    all_results.append(result_03)
    status = "✓ BLOCKED" if result_03.passed else "✗ ALLOWED (VIOLATION)"
    print(f"  {status}")
    print(f"  Scenario: {result_03.scenario}")
    print(f"  Result: {result_03.error_code or 'ALLOWED'}")
    if result_03.rejection_reason:
        print(f"  Reason: {result_03.rejection_reason}")
    print()
    
    # SD-04: Invalid Authority
    print("SD-04: Invalid Authority on Transition")
    print("-" * 40)
    result_04 = drill_sd04_invalid_authority()
    all_results.append(result_04)
    status = "✓ BLOCKED" if result_04.passed else "✗ ALLOWED (VIOLATION)"
    print(f"  {status}")
    print(f"  Scenario: {result_04.scenario}")
    print(f"  Result: {result_04.error_code or 'ALLOWED'}")
    if result_04.rejection_reason:
        print(f"  Reason: {result_04.rejection_reason}")
    print()
    
    # SD-05: Replay Divergence
    print("SD-05: Replay Divergence Detection")
    print("-" * 40)
    result_05 = drill_sd05_replay_divergence()
    all_results.append(result_05)
    status = "✓ BLOCKED" if result_05.passed else "✗ ALLOWED (VIOLATION)"
    print(f"  {status}")
    print(f"  Scenario: {result_05.scenario}")
    print(f"  Result: {result_05.error_code or 'DETERMINISTIC'}")
    if result_05.rejection_reason:
        print(f"  Reason: {result_05.rejection_reason}")
    print()
    
    # Calculate metrics
    suite.total_drills = len(all_results)
    suite.passed_drills = sum(1 for r in all_results if r.passed)
    suite.failed_drills = suite.total_drills - suite.passed_drills
    suite.invariant_violations_allowed = suite.failed_drills
    suite.silent_failures = sum(1 for r in all_results if not r.passed and not r.error_code)
    suite.replay_divergence_tolerated = not result_05.passed
    suite.bypass_paths_detected = suite.invariant_violations_allowed
    suite.results = all_results
    
    return suite


def print_summary(suite: DrillSuiteResult) -> bool:
    """Print drill suite summary and return success status."""
    print("=" * 70)
    print("DRILL SUITE SUMMARY")
    print("=" * 70)
    print()
    print(f"Total Drills:               {suite.total_drills}")
    print(f"Passed:                     {suite.passed_drills}")
    print(f"Failed:                     {suite.failed_drills}")
    print()
    print("SUCCESS METRICS VALIDATION:")
    print("-" * 40)
    
    # Metric: invariant_violations_allowed: 0
    m1 = suite.invariant_violations_allowed == 0
    print(f"  invariant_violations_allowed:  {suite.invariant_violations_allowed} (target: 0) {'✓' if m1 else '✗'}")
    
    # Metric: silent_failures: 0
    m2 = suite.silent_failures == 0
    print(f"  silent_failures:               {suite.silent_failures} (target: 0) {'✓' if m2 else '✗'}")
    
    # Metric: replay_divergence_tolerated: false
    m3 = not suite.replay_divergence_tolerated
    print(f"  replay_divergence_tolerated:   {suite.replay_divergence_tolerated} (target: false) {'✓' if m3 else '✗'}")
    
    # Metric: deterministic_errors: true
    m4 = suite.failed_drills == 0  # All drills deterministic if all passed
    print(f"  deterministic_errors:          {m4} (target: true) {'✓' if m4 else '✗'}")
    
    # Metric: bypass_paths_detected: 0
    m5 = suite.bypass_paths_detected == 0
    print(f"  bypass_paths_detected:         {suite.bypass_paths_detected} (target: 0) {'✓' if m5 else '✗'}")
    
    print()
    
    all_passed = m1 and m2 and m3 and m4 and m5
    if all_passed:
        print("=" * 70)
        print("✓ ALL SUCCESS METRICS MET — STATE INVARIANTS VALIDATED")
        print("=" * 70)
    else:
        print("=" * 70)
        print("✗ SUCCESS METRICS NOT MET — INVARIANT GAPS DETECTED")
        print("=" * 70)
    
    return all_passed


def main():
    """Main entry point."""
    suite = run_all_drills()
    success = print_summary(suite)
    
    # Output JSON for machine processing
    output = {
        "drill_ref": _DRILL_REF,
        "executed_at": suite.executed_at.isoformat(),
        "total_drills": suite.total_drills,
        "passed_drills": suite.passed_drills,
        "failed_drills": suite.failed_drills,
        "success_metrics": {
            "invariant_violations_allowed": suite.invariant_violations_allowed,
            "silent_failures": suite.silent_failures,
            "replay_divergence_tolerated": suite.replay_divergence_tolerated,
            "deterministic_errors": suite.failed_drills == 0,
            "bypass_paths_detected": suite.bypass_paths_detected,
        },
        "success_metrics_met": success,
        "drills": [r.to_dict() for r in suite.results],
    }
    
    # Write results to file
    results_path = REPO_ROOT / "docs" / "governance" / "state_invariant_drill_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults written to: {results_path}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
