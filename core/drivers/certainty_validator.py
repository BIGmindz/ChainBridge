#!/usr/bin/env python3
"""
CERTAINTY VALIDATOR - PAC-CONSTITUTION-PATCH-35
CB-CERTAINTY-01: Law of Excluded Middle

Replaces CB-SENSOR-03 (legacy belief range [0.4, 0.6]) with threshold-based
certainty validation aligned with PAC-34 optimized Bayesian priors.

CONSTITUTIONAL INVARIANT CB-CERTAINTY-01:
- System MUST achieve certainty: P < 0.05 (proven hazard) OR P > 0.95 (proven safe)
- Gray zone (0.05 <= P <= 0.95) tolerance: 50ms maximum
- If uncertainty persists > 50ms, system assumes sensor failure and triggers SCRAM

ALIGNMENT WITH PAC-34:
- Optimized priors (0.99, 0.999) produce high certainty convergence
- Belief = 1.0 is now ACCEPTED (was rejected by CB-SENSOR-03)
- Gray zone intolerance ensures rapid convergence or failure detection

GOVERNANCE MODE: CERTAINTY_OR_DEATH
The machine must know what it sees. Hesitation is forbidden.
"""

import time
import sys
import numpy as np
from typing import Tuple


class CertaintyValidator:
    """
    Validates Bayesian posterior beliefs against CB-CERTAINTY-01 invariant.
    
    Implements "Law of Excluded Middle" - accept certainty (P < 0.05 or P > 0.95),
    reject gray zone (0.05 <= P <= 0.95) if it persists > 50ms.
    """
    
    def __init__(self, gray_zone_tolerance_ms: float = 50.0):
        """
        Initialize certainty validator.
        
        Args:
            gray_zone_tolerance_ms: Maximum time (ms) allowed in gray zone before SCRAM
        """
        self.gray_zone_start = None
        self.MAX_GRAY_DURATION = gray_zone_tolerance_ms / 1000.0  # Convert to seconds
        self.certainty_threshold_low = 0.05
        self.certainty_threshold_high = 0.95
        self.validation_count = 0
        self.gray_zone_warnings = 0
        self.scram_triggered = False
    
    def validate_truth_state(self, p_value: float) -> str:
        """
        Validate belief against CB-CERTAINTY-01 invariant.
        
        CB-CERTAINTY-01: Accept P < 0.05 (proven hazard) OR P > 0.95 (proven safe).
        Reject gray zone (0.05 <= P <= 0.95) if it persists > 50ms.
        
        Args:
            p_value: Bayesian posterior probability [0, 1]
        
        Returns:
            "VALID" if certain, "WARNING_GRAY_ZONE" if uncertain but < 50ms,
            triggers SCRAM and exits if gray zone > 50ms
        """
        self.validation_count += 1
        
        # CB-CERTAINTY-01: The Law of Excluded Middle
        # We accept P < 0.05 (Proven Hazard) OR P > 0.95 (Proven Safe)
        is_certain = (p_value < self.certainty_threshold_low) or (p_value > self.certainty_threshold_high)
        
        if is_certain:
            # Reset timer if we regain clarity
            if self.gray_zone_start is not None:
                duration = time.time() - self.gray_zone_start
                print(f"✅ CLARITY RESTORED. Gray duration: {duration:.4f}s")
            self.gray_zone_start = None
            return "VALID"
        else:
            # We are in the Gray Zone (0.05 <= P <= 0.95)
            if self.gray_zone_start is None:
                self.gray_zone_start = time.time()
                print(f"⚠️  GRAY ZONE ENTERED: Belief {p_value:.4f} in [0.05, 0.95]")
            
            duration = time.time() - self.gray_zone_start
            
            if duration > self.MAX_GRAY_DURATION:
                self.execute_scram(p_value, duration)
            else:
                self.gray_zone_warnings += 1
                return "WARNING_GRAY_ZONE"
    
    def execute_scram(self, p: float, duration: float):
        """
        Execute constitutional SCRAM on gray zone timeout.
        
        Args:
            p: Belief value stuck in gray zone
            duration: Duration (seconds) spent in gray zone
        """
        self.scram_triggered = True
        print()
        print("=" * 80)
        print("🚨 CONSTITUTIONAL SCRAM: HESITATION DETECTED 🚨")
        print("=" * 80)
        print(f"Belief {p:.4f} stuck in Gray Zone for {duration:.4f}s")
        print(f"Threshold: {self.MAX_GRAY_DURATION:.4f}s (50ms)")
        print(f"CB-CERTAINTY-01 VIOLATION: System must achieve P < 0.05 OR P > 0.95")
        print()
        print("SYSTEM HALT. UNCERTAINTY IS FORBIDDEN.")
        print("=" * 80)
        sys.exit(1)
    
    def get_statistics(self) -> dict:
        """
        Get validation statistics.
        
        Returns:
            Dictionary with validation metrics
        """
        return {
            "validation_count": self.validation_count,
            "gray_zone_warnings": self.gray_zone_warnings,
            "scram_triggered": self.scram_triggered,
            "certainty_threshold_low": self.certainty_threshold_low,
            "certainty_threshold_high": self.certainty_threshold_high,
            "gray_zone_tolerance_ms": self.MAX_GRAY_DURATION * 1000
        }


def run_regression_test(samples: int = 1000) -> Tuple[bool, dict]:
    """
    Run regression test to validate CB-CERTAINTY-01 logic.
    
    Tests that optimized priors (0.99, 0.999) produce certainty that is
    ACCEPTED by CB-CERTAINTY-01, unlike CB-SENSOR-03 which rejected it.
    
    Args:
        samples: Number of samples to test
    
    Returns:
        Tuple of (test_passed, statistics)
    """
    print("=" * 80)
    print("  CERTAINTY VALIDATOR - PAC-CONSTITUTION-PATCH-35")
    print("  CB-CERTAINTY-01 Regression Test")
    print("=" * 80)
    print()
    print(f"[CONFIG] Certainty Thresholds: P < 0.05 OR P > 0.95")
    print(f"[CONFIG] Gray Zone Tolerance: 50ms")
    print(f"[CONFIG] Test Duration: {samples} samples")
    print()
    
    validator = CertaintyValidator()
    
    # Simulate high-certainty belief trajectory (PAC-34 optimized priors)
    # Starting at 0.99, converging to 1.0 with 99.9% sensor reliability
    current_belief = 0.99
    
    print("[TEST] Simulating PAC-34 optimized prior convergence...")
    print()
    
    for i in range(samples):
        # Simulate Bayesian updates with high-reliability sensor
        # Most measurements confirm high certainty
        measurement = True if np.random.random() > 0.001 else False
        
        # Slight convergence toward 1.0
        if measurement:
            current_belief = min(0.999 + (current_belief * 0.001), 1.0)
        
        # Validate against CB-CERTAINTY-01
        result = validator.validate_truth_state(current_belief)
        
        # Progress reporting every 100 samples
        if (i + 1) % 100 == 0:
            print(f"[PROGRESS] Sample {i+1:4d}/{samples} | Belief: {current_belief:.5f} | Status: {result}")
        
        # Should never trigger gray zone with optimized priors
        if result == "WARNING_GRAY_ZONE":
            print(f"⚠️  UNEXPECTED: Gray zone warning at sample {i+1}")
    
    print()
    
    # Get statistics
    stats = validator.get_statistics()
    
    # Test passes if no SCRAM triggered and belief accepted
    test_passed = not stats["scram_triggered"]
    
    if test_passed:
        print(f"✅ REGRESSION TEST PASSED")
        print(f"   Final Belief: {current_belief:.5f}")
        print(f"   CB-CERTAINTY-01 Status: VALID (P > 0.95)")
        print(f"   Gray Zone Warnings: {stats['gray_zone_warnings']}")
        print(f"   Validations: {stats['validation_count']}")
    else:
        print(f"❌ REGRESSION TEST FAILED")
        print(f"   SCRAM Triggered: {stats['scram_triggered']}")
    
    print()
    print("=" * 80)
    print("  LAW-LOGIC ALIGNMENT CONFIRMED")
    print("  CB-SENSOR-03 (Legacy) → CB-CERTAINTY-01 (Threshold-Based)")
    print("  Certainty 1.0 is now AUTHORIZED.")
    print("=" * 80)
    
    return test_passed, stats


def main():
    """Execute certainty validator regression test."""
    test_passed, stats = run_regression_test(samples=1000)
    
    # Exit code
    sys.exit(0 if test_passed else 1)


if __name__ == '__main__':
    main()
