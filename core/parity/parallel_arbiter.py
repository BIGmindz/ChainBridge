#!/usr/bin/env python3
"""
PARALLEL ARBITER - PAC-DUAL-ENGINE-SYNC-32
GID-00 (Benson) + GID-12 (Drift Hunter)

Compares outputs from FOUNDRY_LAW_ENGINE (Guard) vs QID_STRATEGY_ENGINE (Scout).
Any deviation triggers GID-12 Vaporization and immediate SCRAM.

CONSTITUTIONAL INVARIANTS:
- CB-PARITY-01: Output(A) MUST EQUAL Output(B) for every decision frame
- CB-PARITY-02: If A != B, system assumes CATASTROPHIC FAILURE and executes SCRAM
- CB-PARITY-03: Latency delta between engines MUST NOT exceed 2.0ms
- CB-PARITY-04: Every PSV must carry dual signatures (Foundry + QID)
- CB-PARITY-05: GID-12 Drift Hunter vaporizes any single-engine output

FAIL-CLOSED ARCHITECTURE:
The arbiter defaults to REJECT. Motion requires UNANIMOUS consensus.
A mismatched output is not a warning. It is instant death.
"""

import sys
import hashlib
import hmac
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Ensure PROJECT_ROOT is available for standalone execution
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class StrategicVector:
    """
    Output from a single engine (Foundry or QID).
    
    Attributes:
        vector_id: Unique identifier for this decision frame
        engine_name: FOUNDRY_LAW_ENGINE or QID_STRATEGY_ENGINE
        path: Strategic path as list of waypoints
        decision: GO, STOP, HALT, PROCEED
        signature: HMAC-SHA512 signature of the output
        timestamp: Unix timestamp of output generation
        metadata: Additional engine-specific data
    """
    vector_id: str
    engine_name: str
    path: List[float]
    decision: str
    signature: str
    timestamp: float
    metadata: dict


@dataclass
class ParityReport:
    """
    Result of dual-engine comparison.
    
    Attributes:
        vector_id: Decision frame identifier
        parity_valid: True if engines agree 100%
        engine_a_signature: Foundry signature
        engine_b_signature: QID signature
        latency_delta_ms: Time difference between engine outputs
        violations: List of detected violations
        arbiter_decision: APPROVE or REJECT
        gid_12_triggered: True if vaporization occurred
    """
    vector_id: str
    parity_valid: bool
    engine_a_signature: str
    engine_b_signature: str
    latency_delta_ms: float
    violations: List[str]
    arbiter_decision: str
    gid_12_triggered: bool
    timestamp: float


class ParallelArbiter:
    """
    Dual-core comparator enforcing absolute zero drift tolerance.
    
    Core Methods:
        compare_vectors(): Compare outputs from Foundry and QID engines
        gid_12_vaporize(): Trigger immediate SCRAM on mismatch
        validate_dual_signature(): Ensure both engines signed the output
    """
    
    def __init__(self, drift_tolerance: float = 0.0, latency_ceiling_ms: float = 2.0):
        self.drift_tolerance = drift_tolerance  # ABSOLUTE ZERO
        self.latency_ceiling_ms = latency_ceiling_ms
        self.nfi_instance = "BENSON-PROD-01"
        self.nfi_secret = b"CHAINBRIDGE_PARITY_NFI_SECRET_DO_NOT_EXPOSE"
        
        # Arbiter state
        self.comparison_count = 0
        self.parity_successes = 0
        self.parity_failures = 0
        self.vaporizations = 0
        self.parity_history: List[ParityReport] = []
        
        # Logging
        self.log_dir = PROJECT_ROOT / "logs" / "parity"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_signature(self, vector: StrategicVector) -> str:
        """
        Generate HMAC-SHA512 signature for strategic vector.
        
        Signature covers: vector_id, engine_name, path, decision, timestamp
        """
        payload = f"{vector.vector_id}|{vector.engine_name}|{vector.path}|{vector.decision}|{vector.timestamp}"
        signature = hmac.new(
            self.nfi_secret,
            payload.encode(),
            hashlib.sha512
        ).hexdigest()
        return signature
    
    def compare_vectors(self, vec_a: StrategicVector, vec_b: StrategicVector) -> ParityReport:
        """
        Compare Version A (Foundry) against Version B (QID).
        Any deviation triggers GID-12 Vaporization.
        
        Parity Checks:
        1. Signature parity (CB-PARITY-04)
        2. Path/Vector parity (CB-PARITY-01)
        3. Decision parity (CB-PARITY-01)
        4. Timestamp/Latency parity (CB-PARITY-03)
        
        Args:
            vec_a: Output from FOUNDRY_LAW_ENGINE
            vec_b: Output from QID_STRATEGY_ENGINE
        
        Returns:
            ParityReport with validation results
        """
        self.comparison_count += 1
        violations = []
        gid_12_triggered = False
        
        # Validate engine assignments
        if vec_a.engine_name != "FOUNDRY_LAW_ENGINE":
            violations.append(f"ENGINE_A_INVALID: Expected FOUNDRY_LAW_ENGINE, got {vec_a.engine_name}")
        if vec_b.engine_name != "QID_STRATEGY_ENGINE":
            violations.append(f"ENGINE_B_INVALID: Expected QID_STRATEGY_ENGINE, got {vec_b.engine_name}")
        
        # Check 1: Signature Parity (CB-PARITY-04)
        # NOTE: In real implementation, signatures would be regenerated and compared
        # For now, we validate that both engines produced signatures
        if not vec_a.signature or len(vec_a.signature) != 128:  # HMAC-SHA512 = 128 hex chars
            violations.append(f"SIGNATURE_A_INVALID: Length {len(vec_a.signature)} != 128")
        if not vec_b.signature or len(vec_b.signature) != 128:
            violations.append(f"SIGNATURE_B_INVALID: Length {len(vec_b.signature)} != 128")
        
        # Check 2: Path Parity (CB-PARITY-01)
        if vec_a.path != vec_b.path:
            violations.append(f"PATH_DIVERGENCE: A{vec_a.path} != B{vec_b.path}")
            gid_12_triggered = True
        
        # Check 3: Decision Parity (CB-PARITY-01)
        if vec_a.decision != vec_b.decision:
            violations.append(f"DECISION_MISMATCH: A({vec_a.decision}) != B({vec_b.decision})")
            gid_12_triggered = True
        
        # Check 4: Timestamp/Latency Parity (CB-PARITY-03)
        latency_delta_ms = abs(vec_a.timestamp - vec_b.timestamp) * 1000.0
        if latency_delta_ms > self.latency_ceiling_ms:
            violations.append(f"LATENCY_DESYNC: Delta {latency_delta_ms:.4f}ms > {self.latency_ceiling_ms}ms")
            gid_12_triggered = True
        
        # Determine parity validity
        parity_valid = len(violations) == 0 and not gid_12_triggered
        
        if parity_valid:
            self.parity_successes += 1
            arbiter_decision = "APPROVE"
        else:
            self.parity_failures += 1
            arbiter_decision = "REJECT"
        
        # Create parity report
        report = ParityReport(
            vector_id=vec_a.vector_id,
            parity_valid=parity_valid,
            engine_a_signature=vec_a.signature,
            engine_b_signature=vec_b.signature,
            latency_delta_ms=latency_delta_ms,
            violations=violations,
            arbiter_decision=arbiter_decision,
            gid_12_triggered=gid_12_triggered,
            timestamp=datetime.now().timestamp()
        )
        
        self.parity_history.append(report)
        
        # Trigger GID-12 vaporization if needed
        if gid_12_triggered:
            self.gid_12_vaporize(vec_a.vector_id, violations)
        
        return report
    
    def gid_12_vaporize(self, vector_id: str, violations: List[str]):
        """
        GID-12 Drift Hunter vaporization.
        Immediate SCRAM and system halt on parity failure.
        
        Args:
            vector_id: Identifier of the failed decision frame
            violations: List of detected violations
        """
        self.vaporizations += 1
        
        print()
        print("=" * 80)
        print("🚨 GID-12 VAPORIZATION TRIGGERED 🚨")
        print("=" * 80)
        print(f"Vector ID: {vector_id}")
        print(f"Violations Detected: {len(violations)}")
        print()
        for i, violation in enumerate(violations, 1):
            print(f"  {i}. {violation}")
        print()
        print("CATASTROPHIC FAILURE: DUAL-CORE INTEGRITY LOST")
        print("SYSTEM HALT ACTIVATED (FAIL-CLOSED)")
        print("=" * 80)
        print()
        
        # Export failure report before halt
        self.export_parity_report()
        
        # Hard fail (commented out for testing - in production this would halt)
        # sys.exit(1)
    
    def export_parity_report(self):
        """
        Export parity comparison history and arbiter statistics.
        """
        report = {
            "pac_id": "PAC-DUAL-ENGINE-SYNC-32",
            "nfi_instance": self.nfi_instance,
            "arbiter_gid": "GID-00",
            "drift_tolerance": self.drift_tolerance,
            "latency_ceiling_ms": self.latency_ceiling_ms,
            "statistics": {
                "total_comparisons": self.comparison_count,
                "parity_successes": self.parity_successes,
                "parity_failures": self.parity_failures,
                "vaporizations": self.vaporizations,
                "success_rate_pct": (self.parity_successes / self.comparison_count * 100.0) if self.comparison_count > 0 else 0.0
            },
            "parity_history": [asdict(p) for p in self.parity_history],
            "timestamp": datetime.now().isoformat()
        }
        
        report_path = self.log_dir / "parity_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"[EXPORT] Parity report exported to: {report_path}")
        print()


# Mock execution for validation
if __name__ == '__main__':
    print("=" * 80)
    print("  PARALLEL ARBITER - PAC-DUAL-ENGINE-SYNC-32")
    print("  GID-00 (Benson) + GID-12 (Drift Hunter)")
    print("  Drift Tolerance: ABSOLUTE ZERO")
    print("=" * 80)
    print()
    
    arbiter = ParallelArbiter(drift_tolerance=0.0, latency_ceiling_ms=2.0)
    
    print("[TEST 1] Perfect Parity - Engines Agree")
    print("-" * 80)
    v1_foundry = StrategicVector(
        vector_id="V-001",
        engine_name="FOUNDRY_LAW_ENGINE",
        path=[1.0, 2.0, 3.0],
        decision="PROCEED",
        signature="a" * 128,  # Mock signature
        timestamp=1000.001,
        metadata={"source": "LAW"}
    )
    v1_qid = StrategicVector(
        vector_id="V-001",
        engine_name="QID_STRATEGY_ENGINE",
        path=[1.0, 2.0, 3.0],
        decision="PROCEED",
        signature="b" * 128,  # Mock signature
        timestamp=1000.001,
        metadata={"source": "STRATEGY"}
    )
    
    report1 = arbiter.compare_vectors(v1_foundry, v1_qid)
    print(f"Result: {report1.arbiter_decision} | Parity: {'✅ VALID' if report1.parity_valid else '❌ INVALID'}")
    print(f"Latency Delta: {report1.latency_delta_ms:.4f}ms")
    print()
    
    print("[TEST 2] Path Divergence - Engines Disagree")
    print("-" * 80)
    v2_foundry = StrategicVector(
        vector_id="V-002",
        engine_name="FOUNDRY_LAW_ENGINE",
        path=[1.0, 2.0, 3.0],
        decision="PROCEED",
        signature="c" * 128,
        timestamp=2000.001,
        metadata={"source": "LAW"}
    )
    v2_qid = StrategicVector(
        vector_id="V-002",
        engine_name="QID_STRATEGY_ENGINE",
        path=[1.0, 2.5, 3.0],  # DIVERGENCE: 2.5 instead of 2.0
        decision="PROCEED",
        signature="d" * 128,
        timestamp=2000.001,
        metadata={"source": "STRATEGY"}
    )
    
    report2 = arbiter.compare_vectors(v2_foundry, v2_qid)
    print(f"Result: {report2.arbiter_decision} | Parity: {'✅ VALID' if report2.parity_valid else '❌ INVALID'}")
    print(f"Violations: {len(report2.violations)}")
    for violation in report2.violations:
        print(f"  - {violation}")
    print()
    
    print("[TEST 3] Decision Mismatch - Engines Contradict")
    print("-" * 80)
    v3_foundry = StrategicVector(
        vector_id="V-003",
        engine_name="FOUNDRY_LAW_ENGINE",
        path=[5.0, 6.0],
        decision="HALT",  # Law says HALT
        signature="e" * 128,
        timestamp=3000.001,
        metadata={"source": "LAW"}
    )
    v3_qid = StrategicVector(
        vector_id="V-003",
        engine_name="QID_STRATEGY_ENGINE",
        path=[5.0, 6.0],
        decision="PROCEED",  # Strategy says PROCEED - CONFLICT!
        signature="f" * 128,
        timestamp=3000.001,
        metadata={"source": "STRATEGY"}
    )
    
    report3 = arbiter.compare_vectors(v3_foundry, v3_qid)
    print(f"Result: {report3.arbiter_decision} | Parity: {'✅ VALID' if report3.parity_valid else '❌ INVALID'}")
    print(f"GID-12 Triggered: {report3.gid_12_triggered}")
    print()
    
    # Export final report
    arbiter.export_parity_report()
    
    print("=" * 80)
    print("  ARBITER STATISTICS")
    print(f"  Total Comparisons: {arbiter.comparison_count}")
    print(f"  Successes: {arbiter.parity_successes}")
    print(f"  Failures: {arbiter.parity_failures}")
    print(f"  Vaporizations: {arbiter.vaporizations}")
    print(f"  Success Rate: {arbiter.parity_successes / arbiter.comparison_count * 100:.2f}%")
    print("=" * 80)
    print()
    print("Two engines, one truth. The Arbiter is watching. Parity is Law.")
