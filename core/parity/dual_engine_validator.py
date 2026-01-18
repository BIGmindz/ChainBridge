#!/usr/bin/env python3
"""
DUAL ENGINE VALIDATOR - PAC-DUAL-ENGINE-SYNC-32
1,000-Agent Handshake Test

Validates synchronization between FOUNDRY_LAW_ENGINE and QID_STRATEGY_ENGINE
across 1,000 parallel decision frames. Each frame represents a dual-engine
computation with parity verification.

TEST SCENARIOS:
1. Perfect Parity (900 agents) - Both engines agree
2. Path Divergence (50 agents) - Engines disagree on path
3. Decision Conflict (50 agents) - Engines disagree on decision

PASS CRITERIA:
- 900/1000 agents achieve perfect parity (90%)
- 100/1000 agents trigger GID-12 vaporization (10% failure injection)
- Average latency delta < 2.0ms
- Zero unexpected failures
"""

import sys
import time
import random
import json
from pathlib import Path
from dataclasses import asdict
from typing import List

# Ensure PROJECT_ROOT is available
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.parity.parallel_arbiter import ParallelArbiter, StrategicVector, ParityReport


class DualEngineValidator:
    """
    Executes 1,000-agent handshake test for dual-engine synchronization.
    """
    
    def __init__(self, test_size: int = 1000):
        self.test_size = test_size
        self.arbiter = ParallelArbiter(drift_tolerance=0.0, latency_ceiling_ms=2.0)
        
        # Test configuration
        self.perfect_parity_count = 900
        self.path_divergence_count = 50
        self.decision_conflict_count = 50
        
        # Results
        self.test_results: List[ParityReport] = []
        
        # Logging
        self.log_dir = PROJECT_ROOT / "logs" / "parity"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_vector_pair(self, agent_id: int, scenario: str) -> tuple:
        """
        Generate a pair of vectors (Foundry + QID) for testing.
        
        Scenarios:
        - "perfect": Both engines agree 100%
        - "path_divergence": Engines disagree on path
        - "decision_conflict": Engines disagree on decision
        
        Returns:
            (vec_foundry, vec_qid) tuple
        """
        vector_id = f"V-{agent_id:04d}"
        base_timestamp = time.time()
        
        # Mock signature generation (128 hex chars for HMAC-SHA512)
        sig_foundry = f"{'a' * 64}{agent_id:064d}"[:128]
        sig_qid = f"{'b' * 64}{agent_id:064d}"[:128]
        
        if scenario == "perfect":
            # Perfect parity - engines agree
            path = [float(i) for i in range(3)]
            decision = "PROCEED"
            
            vec_foundry = StrategicVector(
                vector_id=vector_id,
                engine_name="FOUNDRY_LAW_ENGINE",
                path=path,
                decision=decision,
                signature=sig_foundry,
                timestamp=base_timestamp,
                metadata={"scenario": "perfect_parity"}
            )
            
            vec_qid = StrategicVector(
                vector_id=vector_id,
                engine_name="QID_STRATEGY_ENGINE",
                path=path,  # Same path
                decision=decision,  # Same decision
                signature=sig_qid,
                timestamp=base_timestamp,  # Same timestamp
                metadata={"scenario": "perfect_parity"}
            )
            
        elif scenario == "path_divergence":
            # Path divergence - engines disagree on waypoint
            path_foundry = [1.0, 2.0, 3.0]
            path_qid = [1.0, 2.5, 3.0]  # Divergence at waypoint 2
            
            vec_foundry = StrategicVector(
                vector_id=vector_id,
                engine_name="FOUNDRY_LAW_ENGINE",
                path=path_foundry,
                decision="PROCEED",
                signature=sig_foundry,
                timestamp=base_timestamp,
                metadata={"scenario": "path_divergence"}
            )
            
            vec_qid = StrategicVector(
                vector_id=vector_id,
                engine_name="QID_STRATEGY_ENGINE",
                path=path_qid,  # Different path
                decision="PROCEED",
                signature=sig_qid,
                timestamp=base_timestamp,
                metadata={"scenario": "path_divergence"}
            )
            
        elif scenario == "decision_conflict":
            # Decision conflict - engines disagree on GO/HALT
            path = [5.0, 6.0, 7.0]
            
            vec_foundry = StrategicVector(
                vector_id=vector_id,
                engine_name="FOUNDRY_LAW_ENGINE",
                path=path,
                decision="HALT",  # Law says HALT
                signature=sig_foundry,
                timestamp=base_timestamp,
                metadata={"scenario": "decision_conflict"}
            )
            
            vec_qid = StrategicVector(
                vector_id=vector_id,
                engine_name="QID_STRATEGY_ENGINE",
                path=path,
                decision="PROCEED",  # Strategy says PROCEED
                signature=sig_qid,
                timestamp=base_timestamp,
                metadata={"scenario": "decision_conflict"}
            )
        
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        return vec_foundry, vec_qid
    
    def run_handshake_test(self):
        """
        Execute 1,000-agent handshake test.
        
        Distribution:
        - 900 agents: Perfect parity
        - 50 agents: Path divergence
        - 50 agents: Decision conflict
        """
        print("=" * 80)
        print("  DUAL ENGINE VALIDATOR - 1,000-AGENT HANDSHAKE TEST")
        print("  PAC: PAC-DUAL-ENGINE-SYNC-32")
        print(f"  Test Size: {self.test_size:,} agents")
        print("=" * 80)
        print()
        print("Distribution:")
        print(f"  - Perfect Parity: {self.perfect_parity_count} agents (90%)")
        print(f"  - Path Divergence: {self.path_divergence_count} agents (5%)")
        print(f"  - Decision Conflict: {self.decision_conflict_count} agents (5%)")
        print()
        
        # Generate test scenarios
        scenarios = (
            ["perfect"] * self.perfect_parity_count +
            ["path_divergence"] * self.path_divergence_count +
            ["decision_conflict"] * self.decision_conflict_count
        )
        random.shuffle(scenarios)
        
        print("[EXECUTION] Running handshake test...")
        print()
        
        test_start = time.time()
        
        for i, scenario in enumerate(scenarios):
            # Generate vector pair
            vec_foundry, vec_qid = self.generate_vector_pair(i, scenario)
            
            # Compare vectors through arbiter
            report = self.arbiter.compare_vectors(vec_foundry, vec_qid)
            self.test_results.append(report)
            
            # Progress reporting every 100 agents
            if (i + 1) % 100 == 0:
                pct = ((i + 1) / self.test_size) * 100
                successes = self.arbiter.parity_successes
                failures = self.arbiter.parity_failures
                print(f"[PROGRESS] {pct:5.1f}% | Agents: {i+1:4d}/{self.test_size} | "
                      f"Success: {successes:3d} | Failures: {failures:3d}")
        
        test_duration = time.time() - test_start
        
        print()
        print("[EXECUTION] ✅ COMPLETE")
        print(f"[EXECUTION] Duration: {test_duration:.2f}s")
        print()
        
        # Calculate statistics
        self.analyze_results()
    
    def analyze_results(self):
        """
        Analyze test results and validate against pass criteria.
        """
        print("=" * 80)
        print("  TEST RESULTS ANALYSIS")
        print("=" * 80)
        print()
        
        total = len(self.test_results)
        successes = sum(1 for r in self.test_results if r.parity_valid)
        failures = sum(1 for r in self.test_results if not r.parity_valid)
        vaporizations = sum(1 for r in self.test_results if r.gid_12_triggered)
        
        success_rate = (successes / total) * 100 if total > 0 else 0.0
        
        # Latency statistics
        latencies = [r.latency_delta_ms for r in self.test_results]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        
        print(f"Total Agents Tested: {total:,}")
        print(f"Parity Successes: {successes:,} ({success_rate:.2f}%)")
        print(f"Parity Failures: {failures:,} ({(failures/total)*100:.2f}%)")
        print(f"GID-12 Vaporizations: {vaporizations:,}")
        print()
        print("Latency Statistics:")
        print(f"  - Average: {avg_latency:.4f}ms")
        print(f"  - Minimum: {min_latency:.4f}ms")
        print(f"  - Maximum: {max_latency:.4f}ms")
        print(f"  - Ceiling: {self.arbiter.latency_ceiling_ms:.1f}ms")
        print()
        
        # Validate pass criteria
        print("Pass Criteria Validation:")
        print("-" * 80)
        
        criterion_1 = successes >= 900
        print(f"1. Perfect parity ≥ 900 agents: {successes:,} agents - {'✅ PASS' if criterion_1 else '❌ FAIL'}")
        
        criterion_2 = vaporizations == 100
        print(f"2. GID-12 vaporizations = 100: {vaporizations:,} triggers - {'✅ PASS' if criterion_2 else '❌ FAIL'}")
        
        criterion_3 = avg_latency < 2.0
        print(f"3. Avg latency < 2.0ms: {avg_latency:.4f}ms - {'✅ PASS' if criterion_3 else '❌ FAIL'}")
        
        all_pass = criterion_1 and criterion_2 and criterion_3
        print()
        print(f"Overall: {'✅ ALL CRITERIA PASSED' if all_pass else '❌ SOME CRITERIA FAILED'}")
        print()
        
        # Export results
        self.export_test_report(all_pass)
    
    def export_test_report(self, all_pass: bool):
        """
        Export comprehensive test report.
        """
        report = {
            "pac_id": "PAC-DUAL-ENGINE-SYNC-32",
            "test_name": "1000_AGENT_HANDSHAKE",
            "test_size": self.test_size,
            "distribution": {
                "perfect_parity": self.perfect_parity_count,
                "path_divergence": self.path_divergence_count,
                "decision_conflict": self.decision_conflict_count
            },
            "results": {
                "total_agents": len(self.test_results),
                "parity_successes": self.arbiter.parity_successes,
                "parity_failures": self.arbiter.parity_failures,
                "vaporizations": self.arbiter.vaporizations,
                "success_rate_pct": (self.arbiter.parity_successes / len(self.test_results) * 100) if self.test_results else 0.0
            },
            "latency": {
                "average_ms": sum(r.latency_delta_ms for r in self.test_results) / len(self.test_results) if self.test_results else 0.0,
                "min_ms": min(r.latency_delta_ms for r in self.test_results) if self.test_results else 0.0,
                "max_ms": max(r.latency_delta_ms for r in self.test_results) if self.test_results else 0.0,
                "ceiling_ms": self.arbiter.latency_ceiling_ms
            },
            "pass_criteria": {
                "perfect_parity_target": 900,
                "vaporization_target": 100,
                "latency_target_ms": 2.0,
                "all_criteria_passed": all_pass
            },
            "test_results_sample": [asdict(r) for r in self.test_results[:100]],  # First 100 for inspection
            "timestamp": time.time()
        }
        
        report_path = self.log_dir / "dual_engine_handshake_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"[EXPORT] Test report exported to: {report_path}")
        print()


if __name__ == '__main__':
    validator = DualEngineValidator(test_size=1000)
    validator.run_handshake_test()
    
    print("=" * 80)
    print("  HANDSHAKE TEST COMPLETE")
    print("  Two engines, one truth. The Arbiter is watching. Parity is Law.")
    print("=" * 80)
