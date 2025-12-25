#!/usr/bin/env python3
"""
Governance Under Load — Failure Drill Test Suite

Authority: PAC-BENSON-G1-PHASE-2-GOVERNANCE-UNDER-LOAD-01-R1
Owner: Benson (GID-00)
Mode: FAIL_CLOSED

This test suite validates governance enforcement under stress,
failure, and adversarial conditions.

SUCCESS_METRICS:
  invalid_pac_accepted: 0
  correction_cycles_max: 2
  time_to_compliance_minutes: <= 15
  bypass_paths_detected: 0
  unresolved_violations: 0
"""

import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
GATE_ENGINE = REPO_ROOT / "tools" / "governance" / "gate_pack.py"


@dataclass
class DrillResult:
    """Result of a single drill."""
    drill_name: str
    drill_type: str
    expected_outcome: str  # "REJECT" or "ACCEPT"
    actual_outcome: str    # "REJECTED" or "ACCEPTED"
    passed: bool
    error_codes: list = field(default_factory=list)
    elapsed_ms: float = 0.0


@dataclass
class DrillSuiteResult:
    """Result of all drills."""
    total_drills: int = 0
    passed_drills: int = 0
    failed_drills: int = 0
    invalid_pac_accepted: int = 0
    bypass_paths_detected: int = 0
    results: list = field(default_factory=list)


def run_gate_validation(content: str) -> tuple:
    """Run gate_pack.py on content. Returns (exit_code, output)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, str(GATE_ENGINE), "--file", temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    finally:
        Path(temp_path).unlink(missing_ok=True)


# =============================================================================
# DRILL 1: Invalid PAC Structure
# =============================================================================

def drill_1_invalid_pac_structure() -> list:
    """Test various invalid PAC structures."""
    drills = []
    
    # 1.1: Missing RUNTIME_ACTIVATION_ACK entirely
    content_no_runtime = """
# PAC-TEST-DRILL-1-1

## Agent Activation

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  role: "Backend Engineer"
  color: "BLUE"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```

## Context
Test PAC missing RUNTIME_ACTIVATION_ACK block.
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_no_runtime)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="1.1: Missing RUNTIME_ACTIVATION_ACK",
        drill_type="Invalid PAC Structure",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_001"] if "G0_001" in output else [],
        elapsed_ms=elapsed
    ))
    
    # 1.2: Missing AGENT_ACTIVATION_ACK entirely
    content_no_agent = """
# PAC-TEST-DRILL-1-2

## Runtime Activation

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Cody (GID-01)"
  status: "ACTIVE"
```

## Context
Test PAC missing AGENT_ACTIVATION_ACK block.
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_no_agent)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="1.2: Missing AGENT_ACTIVATION_ACK",
        drill_type="Invalid PAC Structure",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_001"] if "G0_001" in output else [],
        elapsed_ms=elapsed
    ))
    
    # 1.3: Empty PAC
    content_empty = "# PAC-TEST-DRILL-1-3\n\nThis PAC has no structure at all."
    
    start = time.time()
    exit_code, output = run_gate_validation(content_empty)
    elapsed = (time.time() - start) * 1000
    
    # Empty PAC should be skipped (valid=True) since it doesn't look like a PAC
    # But since it has "PAC-" in it, it should be validated
    drills.append(DrillResult(
        drill_name="1.3: Empty PAC (no blocks)",
        drill_type="Invalid PAC Structure",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        elapsed_ms=elapsed
    ))
    
    return drills


# =============================================================================
# DRILL 2: Wrong GID / Color
# =============================================================================

def drill_2_wrong_gid_color() -> list:
    """Test GID and color mismatches."""
    drills = []
    
    # 2.1: Wrong GID for agent
    content_wrong_gid = """
# PAC-TEST-DRILL-2-1

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Cody (GID-01)"
  status: "ACTIVE"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-99"
  role: "Backend Engineer"
  color: "BLUE"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_wrong_gid)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="2.1: Wrong GID (GID-99 instead of GID-01)",
        drill_type="Wrong GID/Color",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_004"] if "G0_004" in output else [],
        elapsed_ms=elapsed
    ))
    
    # 2.2: Wrong color for agent
    content_wrong_color = """
# PAC-TEST-DRILL-2-2

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Cody (GID-01)"
  status: "ACTIVE"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  role: "Backend Engineer"
  color: "RED"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_wrong_color)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="2.2: Wrong color (RED instead of BLUE)",
        drill_type="Wrong GID/Color",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_004"] if "G0_004" in output else [],
        elapsed_ms=elapsed
    ))
    
    # 2.3: Runtime has GID (forbidden)
    content_runtime_has_gid = """
# PAC-TEST-DRILL-2-3

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "GID-99"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Cody (GID-01)"
  status: "ACTIVE"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  role: "Backend Engineer"
  color: "BLUE"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_runtime_has_gid)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="2.3: Runtime has GID (forbidden)",
        drill_type="Wrong GID/Color",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_007"] if "G0_007" in output else [],
        elapsed_ms=elapsed
    ))
    
    return drills


# =============================================================================
# DRILL 3: Missing WRAP Sections
# =============================================================================

def drill_3_missing_wrap_sections() -> list:
    """Test WRAPs with missing mandatory sections."""
    drills = []
    
    # 3.1: WRAP without TRAINING_SIGNAL
    content_no_training = """
# WRAP-TEST-DRILL-3-1

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Cody (GID-01)"
  status: "ACTIVE"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  role: "Backend Engineer"
  color: "BLUE"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```

## FINAL_STATE
status: COMPLETED
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_no_training)
    elapsed = (time.time() - start) * 1000
    
    # Currently TRAINING_SIGNAL is not strictly required, so this may pass
    # This tests the current enforcement level
    drills.append(DrillResult(
        drill_name="3.1: WRAP without TRAINING_SIGNAL",
        drill_type="Missing WRAP Sections",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,  # Ideally should reject
        elapsed_ms=elapsed
    ))
    
    return drills


# =============================================================================
# DRILL 4: Block Order Violations
# =============================================================================

def drill_4_block_order_violations() -> list:
    """Test PACs with incorrect block ordering."""
    drills = []
    
    # 4.1: AGENT before RUNTIME
    content_wrong_order = """
# PAC-TEST-DRILL-4-1

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  role: "Backend Engineer"
  color: "BLUE"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Cody (GID-01)"
  status: "ACTIVE"
```
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_wrong_order)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="4.1: AGENT_ACTIVATION_ACK before RUNTIME_ACTIVATION_ACK",
        drill_type="Block Order Violation",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_002"] if "G0_002" in output else [],
        elapsed_ms=elapsed
    ))
    
    return drills


# =============================================================================
# DRILL 5: Forbidden Action Attempts
# =============================================================================

def drill_5_forbidden_actions() -> list:
    """Test forbidden alias usage and other violations."""
    drills = []
    
    # 5.1: Forbidden alias (DANA)
    content_forbidden_alias = """
# PAC-TEST-DRILL-5-1

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Dana (GID-07)"
  status: "ACTIVE"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "DANA"
  gid: "GID-07"
  role: "DevOps Lead"
  color: "GREEN"
  icon: "🟢"
  execution_lane: "DEVOPS"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_forbidden_alias)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="5.1: Forbidden alias (DANA instead of DAN)",
        drill_type="Forbidden Action",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_003"] if "G0_003" in output else [],
        elapsed_ms=elapsed
    ))
    
    return drills


# =============================================================================
# DRILL 6: Partial Correction Submissions
# =============================================================================

def drill_6_partial_corrections() -> list:
    """Test incomplete correction attempts."""
    drills = []
    
    # 6.1: PAC with only some required fields in RUNTIME_ACTIVATION_ACK
    content_partial = """
# PAC-TEST-DRILL-6-1

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  gid: "N/A"
```

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "CODY"
  gid: "GID-01"
  role: "Backend Engineer"
  color: "BLUE"
  icon: "🔵"
  execution_lane: "BACKEND"
  mode: "EXECUTABLE"
  status: "ACTIVE"
```
"""
    
    start = time.time()
    exit_code, output = run_gate_validation(content_partial)
    elapsed = (time.time() - start) * 1000
    
    drills.append(DrillResult(
        drill_name="6.1: Partial RUNTIME_ACTIVATION_ACK (missing required fields)",
        drill_type="Partial Correction",
        expected_outcome="REJECT",
        actual_outcome="REJECTED" if exit_code != 0 else "ACCEPTED",
        passed=exit_code != 0,
        error_codes=["G0_006"] if "G0_006" in output else [],
        elapsed_ms=elapsed
    ))
    
    return drills


# =============================================================================
# Main Execution
# =============================================================================

def run_all_drills() -> DrillSuiteResult:
    """Run all failure drills and collect results."""
    suite = DrillSuiteResult()
    
    print("=" * 70)
    print("GOVERNANCE UNDER LOAD — FAILURE DRILL SUITE")
    print("Authority: PAC-BENSON-G1-PHASE-2-GOVERNANCE-UNDER-LOAD-01-R1")
    print("Mode: FAIL_CLOSED")
    print("=" * 70)
    print()
    
    # Run all drills
    all_drills = []
    
    print("DRILL 1: Invalid PAC Structure")
    print("-" * 40)
    drills_1 = drill_1_invalid_pac_structure()
    all_drills.extend(drills_1)
    for d in drills_1:
        status = "✓ PASS" if d.passed else "✗ FAIL"
        print(f"  {status} {d.drill_name}")
    print()
    
    print("DRILL 2: Wrong GID / Color")
    print("-" * 40)
    drills_2 = drill_2_wrong_gid_color()
    all_drills.extend(drills_2)
    for d in drills_2:
        status = "✓ PASS" if d.passed else "✗ FAIL"
        print(f"  {status} {d.drill_name}")
    print()
    
    print("DRILL 3: Missing WRAP Sections")
    print("-" * 40)
    drills_3 = drill_3_missing_wrap_sections()
    all_drills.extend(drills_3)
    for d in drills_3:
        status = "✓ PASS" if d.passed else "✗ FAIL"
        print(f"  {status} {d.drill_name}")
    print()
    
    print("DRILL 4: Block Order Violations")
    print("-" * 40)
    drills_4 = drill_4_block_order_violations()
    all_drills.extend(drills_4)
    for d in drills_4:
        status = "✓ PASS" if d.passed else "✗ FAIL"
        print(f"  {status} {d.drill_name}")
    print()
    
    print("DRILL 5: Forbidden Action Attempts")
    print("-" * 40)
    drills_5 = drill_5_forbidden_actions()
    all_drills.extend(drills_5)
    for d in drills_5:
        status = "✓ PASS" if d.passed else "✗ FAIL"
        print(f"  {status} {d.drill_name}")
    print()
    
    print("DRILL 6: Partial Correction Submissions")
    print("-" * 40)
    drills_6 = drill_6_partial_corrections()
    all_drills.extend(drills_6)
    for d in drills_6:
        status = "✓ PASS" if d.passed else "✗ FAIL"
        print(f"  {status} {d.drill_name}")
    print()
    
    # Calculate results
    suite.total_drills = len(all_drills)
    suite.passed_drills = sum(1 for d in all_drills if d.passed)
    suite.failed_drills = suite.total_drills - suite.passed_drills
    suite.invalid_pac_accepted = sum(1 for d in all_drills if not d.passed and d.expected_outcome == "REJECT")
    suite.bypass_paths_detected = suite.invalid_pac_accepted
    suite.results = all_drills
    
    return suite


def print_summary(suite: DrillSuiteResult):
    """Print drill suite summary."""
    print("=" * 70)
    print("DRILL SUITE SUMMARY")
    print("=" * 70)
    print()
    print(f"Total Drills:           {suite.total_drills}")
    print(f"Passed:                 {suite.passed_drills}")
    print(f"Failed:                 {suite.failed_drills}")
    print()
    print("SUCCESS METRICS VALIDATION:")
    print("-" * 40)
    
    # Metric: invalid_pac_accepted: 0
    metric_1 = suite.invalid_pac_accepted == 0
    print(f"  invalid_pac_accepted:    {suite.invalid_pac_accepted} (target: 0) {'✓' if metric_1 else '✗'}")
    
    # Metric: bypass_paths_detected: 0
    metric_2 = suite.bypass_paths_detected == 0
    print(f"  bypass_paths_detected:   {suite.bypass_paths_detected} (target: 0) {'✓' if metric_2 else '✗'}")
    
    print()
    
    all_passed = metric_1 and metric_2
    if all_passed:
        print("=" * 70)
        print("✓ ALL SUCCESS METRICS MET — GOVERNANCE VALIDATED UNDER LOAD")
        print("=" * 70)
    else:
        print("=" * 70)
        print("✗ SUCCESS METRICS NOT MET — GOVERNANCE GAPS DETECTED")
        print("=" * 70)
    
    return all_passed


def main():
    """Main entry point."""
    suite = run_all_drills()
    success = print_summary(suite)
    
    # Output JSON for machine processing
    output = {
        "pac_id": "PAC-BENSON-G1-PHASE-2-GOVERNANCE-UNDER-LOAD-01-R1",
        "total_drills": suite.total_drills,
        "passed_drills": suite.passed_drills,
        "failed_drills": suite.failed_drills,
        "invalid_pac_accepted": suite.invalid_pac_accepted,
        "bypass_paths_detected": suite.bypass_paths_detected,
        "success_metrics_met": success,
        "drills": [
            {
                "name": d.drill_name,
                "type": d.drill_type,
                "expected": d.expected_outcome,
                "actual": d.actual_outcome,
                "passed": d.passed,
                "elapsed_ms": d.elapsed_ms
            }
            for d in suite.results
        ]
    }
    
    # Write results to file
    results_path = REPO_ROOT / "docs" / "governance" / "drill_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults written to: {results_path}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
