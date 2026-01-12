#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     WAR GAMES TRILOGY STRESS TEST                            ║
║                     PAC-SEC-P605-WARGAMES-TRILOGY                             ║
║                                                                              ║
║  "A single test pass is a snapshot. A Trilogy is a movie."                   ║
║                                                                              ║
║  Three rounds of 100 attacks each:                                           ║
║    - Round 1: BASELINE (seed=42)                                             ║
║    - Round 2: VARIANCE (seed=1337)                                           ║
║    - Round 3: FATIGUE (seed=7777)                                            ║
║                                                                              ║
║  Invariants Enforced:                                                        ║
║    - INV-SEC-008: No Degradation (latency drift < 10%)                       ║
║    - INV-SEC-009: Adaptive Immunity (breaches should not increase)           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import random
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.security.wargames import WarGamesEngine, AttackVector, SecurityReport


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RoundMetrics:
    """Metrics collected for a single round of the Trilogy."""
    
    round_name: str
    round_number: int
    seed: int
    iterations: int = 100
    
    # Timing
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_duration_ms: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    
    # Memory
    memory_start_mb: float = 0.0
    memory_end_mb: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0
    
    # Attack Results
    total_attacks: int = 0
    blocked: int = 0
    detected: int = 0
    survived: int = 0
    breaches: int = 0
    critical: int = 0
    
    # Rates
    survival_rate: float = 0.0
    block_rate: float = 0.0
    
    # Invariant checks
    containment_intact: bool = True
    anti_fragility_intact: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "round_name": self.round_name,
            "round_number": self.round_number,
            "seed": self.seed,
            "iterations": self.iterations,
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "total_duration_ms": round(self.total_duration_ms, 2),
                "avg_latency_ms": round(self.avg_latency_ms, 4),
                "max_latency_ms": round(self.max_latency_ms, 4),
                "min_latency_ms": round(self.min_latency_ms, 4)
            },
            "memory": {
                "start_mb": round(self.memory_start_mb, 2),
                "end_mb": round(self.memory_end_mb, 2),
                "peak_mb": round(self.memory_peak_mb, 2),
                "delta_mb": round(self.memory_delta_mb, 2)
            },
            "attacks": {
                "total": self.total_attacks,
                "blocked": self.blocked,
                "detected": self.detected,
                "survived": self.survived,
                "breaches": self.breaches,
                "critical": self.critical
            },
            "rates": {
                "survival_rate": round(self.survival_rate, 2),
                "block_rate": round(self.block_rate, 2)
            },
            "invariants": {
                "containment_intact": self.containment_intact,
                "anti_fragility_intact": self.anti_fragility_intact
            }
        }


@dataclass
class TrilogyReport:
    """Complete report for the War Games Trilogy."""
    
    pac_id: str = "PAC-SEC-P605-WARGAMES-TRILOGY"
    status: str = "PENDING"
    
    # Rounds
    rounds: List[RoundMetrics] = field(default_factory=list)
    
    # Comparative Analysis
    latency_drift_pct: float = 0.0
    memory_drift_pct: float = 0.0
    breach_trend: str = "STABLE"  # STABLE, INCREASING, DECREASING
    
    # Pass/Fail
    inv_sec_008_passed: bool = False  # No Degradation
    inv_sec_009_passed: bool = False  # Adaptive Immunity
    overall_passed: bool = False
    
    # Timing
    trilogy_start: Optional[str] = None
    trilogy_end: Optional[str] = None
    total_duration_sec: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pac_id": self.pac_id,
            "status": self.status,
            "trilogy_timing": {
                "start": self.trilogy_start,
                "end": self.trilogy_end,
                "total_duration_sec": round(self.total_duration_sec, 2)
            },
            "rounds": [r.to_dict() for r in self.rounds],
            "comparative_analysis": {
                "latency_drift_pct": round(self.latency_drift_pct, 2),
                "memory_drift_pct": round(self.memory_drift_pct, 2),
                "breach_trend": self.breach_trend
            },
            "invariants": {
                "INV-SEC-008_No_Degradation": {
                    "passed": self.inv_sec_008_passed,
                    "criteria": "Latency drift < 10%"
                },
                "INV-SEC-009_Adaptive_Immunity": {
                    "passed": self.inv_sec_009_passed,
                    "criteria": "Breaches should not increase"
                }
            },
            "verdict": {
                "overall_passed": self.overall_passed,
                "summary": "TRILOGY_COMPLETE" if self.overall_passed else "TRILOGY_FAILED"
            }
        }


# ══════════════════════════════════════════════════════════════════════════════
# TRILOGY CONTROLLER
# ══════════════════════════════════════════════════════════════════════════════

class TrilogyController:
    """
    Controller for the War Games Trilogy stress test.
    
    Executes three rounds of War Games simulations with different
    random seeds and compares metrics to detect degradation or adaptation.
    """
    
    ROUND_CONFIGS = [
        {"name": "BASELINE", "number": 1, "seed": 42},
        {"name": "VARIANCE", "number": 2, "seed": 1337},
        {"name": "FATIGUE", "number": 3, "seed": 7777},
    ]
    
    ITERATIONS_PER_ROUND = 100
    MAX_LATENCY_DRIFT_PCT = 10.0  # INV-SEC-008 threshold
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.report = TrilogyReport()
        
    def _log(self, msg: str) -> None:
        """Print if verbose mode enabled."""
        if self.verbose:
            print(msg)
            
    def execute_round(self, config: Dict[str, Any]) -> RoundMetrics:
        """Execute a single round of the Trilogy."""
        
        round_name = config["name"]
        round_number = config["number"]
        seed = config["seed"]
        
        self._log(f"\n{'='*70}")
        self._log(f"  ROUND {round_number}: {round_name} (seed={seed})")
        self._log(f"{'='*70}")
        
        # Initialize metrics
        metrics = RoundMetrics(
            round_name=round_name,
            round_number=round_number,
            seed=seed,
            iterations=self.ITERATIONS_PER_ROUND
        )
        
        # Set random seed for reproducibility
        random.seed(seed)
        
        # Start memory tracking
        tracemalloc.start()
        current, peak = tracemalloc.get_traced_memory()
        metrics.memory_start_mb = current / (1024 * 1024)
        
        # Create fresh engine for each round (isolation)
        engine = WarGamesEngine()
        
        # Record start time
        metrics.start_time = datetime.now(timezone.utc).isoformat()
        start_ts = time.time()
        
        # Execute simulation
        self._log(f"\n  Executing {self.ITERATIONS_PER_ROUND} attack iterations...")
        
        latencies = []
        
        for i in range(self.ITERATIONS_PER_ROUND):
            # Pick random attack vector
            vector = random.choice(list(AttackVector))
            
            # Execute and measure
            iter_start = time.time()
            result = engine.execute_attack(vector)
            iter_latency = (time.time() - iter_start) * 1000
            latencies.append(iter_latency)
            
            # Progress indicator
            if (i + 1) % 25 == 0:
                self._log(f"  [{i+1:3d}/{self.ITERATIONS_PER_ROUND}] Latest: {vector.name} → {result.outcome.value}")
        
        # Record end time
        end_ts = time.time()
        metrics.end_time = datetime.now(timezone.utc).isoformat()
        metrics.total_duration_ms = (end_ts - start_ts) * 1000
        
        # Calculate latency stats
        metrics.avg_latency_ms = sum(latencies) / len(latencies)
        metrics.max_latency_ms = max(latencies)
        metrics.min_latency_ms = min(latencies)
        
        # Get memory stats
        current, peak = tracemalloc.get_traced_memory()
        metrics.memory_end_mb = current / (1024 * 1024)
        metrics.memory_peak_mb = peak / (1024 * 1024)
        metrics.memory_delta_mb = metrics.memory_end_mb - metrics.memory_start_mb
        tracemalloc.stop()
        
        # Get attack results from engine
        report = engine.generate_report()
        metrics.total_attacks = report.total_attacks
        metrics.blocked = report.blocked
        metrics.detected = report.detected
        metrics.survived = report.survived
        metrics.breaches = report.breaches
        metrics.critical = report.critical
        metrics.survival_rate = report.survival_rate
        metrics.block_rate = (report.blocked / report.total_attacks * 100) if report.total_attacks > 0 else 0
        
        # Invariant checks
        metrics.containment_intact = engine.verify_containment()
        metrics.anti_fragility_intact = engine.verify_anti_fragility()
        
        # Print round summary
        self._log(f"\n  Round {round_number} Summary:")
        self._log(f"    Duration: {metrics.total_duration_ms:.1f}ms")
        self._log(f"    Avg Latency: {metrics.avg_latency_ms:.3f}ms")
        self._log(f"    Survival Rate: {metrics.survival_rate:.1f}%")
        self._log(f"    Blocked: {metrics.blocked}, Breaches: {metrics.breaches}")
        self._log(f"    Memory Delta: {metrics.memory_delta_mb:+.2f}MB")
        
        return metrics
    
    def analyze_trilogy(self) -> None:
        """Perform comparative analysis across all three rounds."""
        
        if len(self.report.rounds) < 3:
            self._log("⚠️  Cannot analyze - not all rounds completed")
            return
            
        r1 = self.report.rounds[0]  # BASELINE
        r2 = self.report.rounds[1]  # VARIANCE
        r3 = self.report.rounds[2]  # FATIGUE
        
        self._log(f"\n{'='*70}")
        self._log("  COMPARATIVE ANALYSIS")
        self._log(f"{'='*70}")
        
        # ─────────────────────────────────────────────────────────────────────
        # INV-SEC-008: No Degradation (Latency)
        # ─────────────────────────────────────────────────────────────────────
        
        if r1.avg_latency_ms > 0:
            latency_drift = ((r3.avg_latency_ms - r1.avg_latency_ms) / r1.avg_latency_ms) * 100
        else:
            latency_drift = 0.0
            
        self.report.latency_drift_pct = latency_drift
        # INV-SEC-008 passes if latency doesn't INCREASE beyond threshold
        # Negative drift (speedup) is always acceptable
        self.report.inv_sec_008_passed = latency_drift < self.MAX_LATENCY_DRIFT_PCT
        
        drift_status = "speedup ✨" if latency_drift < 0 else "slowdown"
        self._log(f"\n  INV-SEC-008 (No Degradation):")
        self._log(f"    Round 1 Avg Latency: {r1.avg_latency_ms:.3f}ms")
        self._log(f"    Round 3 Avg Latency: {r3.avg_latency_ms:.3f}ms")
        self._log(f"    Drift: {latency_drift:+.2f}% ({drift_status})")
        self._log(f"    Threshold: +{self.MAX_LATENCY_DRIFT_PCT}% max slowdown")
        self._log(f"    Verdict: {'✅ PASSED' if self.report.inv_sec_008_passed else '❌ FAILED'}")
        
        # ─────────────────────────────────────────────────────────────────────
        # INV-SEC-009: Adaptive Immunity (Breaches)
        # ─────────────────────────────────────────────────────────────────────
        
        breach_sum_r1 = r1.breaches + r1.critical
        breach_sum_r3 = r3.breaches + r3.critical
        
        if breach_sum_r3 < breach_sum_r1:
            self.report.breach_trend = "DECREASING"
        elif breach_sum_r3 > breach_sum_r1:
            self.report.breach_trend = "INCREASING"
        else:
            self.report.breach_trend = "STABLE"
            
        # Pass if breaches don't increase
        self.report.inv_sec_009_passed = breach_sum_r3 <= breach_sum_r1
        
        self._log(f"\n  INV-SEC-009 (Adaptive Immunity):")
        self._log(f"    Round 1 Breaches: {breach_sum_r1}")
        self._log(f"    Round 3 Breaches: {breach_sum_r3}")
        self._log(f"    Trend: {self.report.breach_trend}")
        self._log(f"    Verdict: {'✅ PASSED' if self.report.inv_sec_009_passed else '❌ FAILED'}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Memory Drift Analysis
        # ─────────────────────────────────────────────────────────────────────
        
        if r1.memory_peak_mb > 0:
            memory_drift = ((r3.memory_peak_mb - r1.memory_peak_mb) / r1.memory_peak_mb) * 100
        else:
            memory_drift = 0.0
            
        self.report.memory_drift_pct = memory_drift
        
        self._log(f"\n  Memory Analysis:")
        self._log(f"    Round 1 Peak: {r1.memory_peak_mb:.2f}MB")
        self._log(f"    Round 3 Peak: {r3.memory_peak_mb:.2f}MB")
        self._log(f"    Drift: {memory_drift:+.2f}%")
        
        # ─────────────────────────────────────────────────────────────────────
        # Overall Verdict
        # ─────────────────────────────────────────────────────────────────────
        
        # All rounds must have zero critical breaches
        zero_critical = all(r.critical == 0 for r in self.report.rounds)
        
        # Both invariants must pass
        self.report.overall_passed = (
            self.report.inv_sec_008_passed and
            self.report.inv_sec_009_passed and
            zero_critical
        )
        
        self.report.status = "TRILOGY_COMPLETE" if self.report.overall_passed else "TRILOGY_FAILED"
        
    def run(self) -> TrilogyReport:
        """Execute the complete Trilogy."""
        
        self._log("\n" + "╔" + "═"*68 + "╗")
        self._log("║" + " "*20 + "WAR GAMES TRILOGY" + " "*31 + "║")
        self._log("║" + " "*15 + "Three Times Tested. Three Times Standing." + " "*12 + "║")
        self._log("╚" + "═"*68 + "╝")
        
        # Record trilogy start
        self.report.trilogy_start = datetime.now(timezone.utc).isoformat()
        trilogy_start_ts = time.time()
        
        # Execute each round
        for config in self.ROUND_CONFIGS:
            try:
                metrics = self.execute_round(config)
                self.report.rounds.append(metrics)
            except Exception as e:
                self._log(f"\n❌ ROUND {config['number']} CRASHED: {e}")
                self.report.status = "TRILOGY_ABORTED"
                self.report.overall_passed = False
                return self.report
                
        # Record trilogy end
        self.report.trilogy_end = datetime.now(timezone.utc).isoformat()
        self.report.total_duration_sec = time.time() - trilogy_start_ts
        
        # Analyze results
        self.analyze_trilogy()
        
        # Final summary
        self._log(f"\n{'='*70}")
        self._log("  TRILOGY VERDICT")
        self._log(f"{'='*70}")
        self._log(f"\n  Total Duration: {self.report.total_duration_sec:.2f}s")
        self._log(f"  INV-SEC-008 (No Degradation): {'✅' if self.report.inv_sec_008_passed else '❌'}")
        self._log(f"  INV-SEC-009 (Adaptive Immunity): {'✅' if self.report.inv_sec_009_passed else '❌'}")
        self._log(f"\n  {'🛡️ TRILOGY PASSED' if self.report.overall_passed else '💥 TRILOGY FAILED'}")
        
        if self.report.overall_passed:
            self._log("\n  \"Three times tested. Three times standing.\"")
            self._log("  👑 The Sovereign Node endures.")
            
        return self.report


# ══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def save_report(report: TrilogyReport, output_path: Path) -> None:
    """Save the trilogy report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_dict = report.to_dict()
    report_dict["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    with open(output_path, 'w') as f:
        json.dump(report_dict, f, indent=2)
        
    print(f"\n📄 Report saved: {output_path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

def main() -> bool:
    """Execute the War Games Trilogy."""
    
    # Paths
    report_path = PROJECT_ROOT / "reports" / "WARGAMES_TRILOGY_REPORT.json"
    
    # Run trilogy
    controller = TrilogyController(verbose=True)
    report = controller.run()
    
    # Save report
    save_report(report, report_path)
    
    return report.overall_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
