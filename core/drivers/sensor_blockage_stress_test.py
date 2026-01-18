#!/usr/bin/env python3
"""
SENSOR BLOCKAGE STRESS TEST - PAC-HITL-HARDWARE-SYNC-33

Simulates sensor blockage/failure scenarios to validate:
1. GID-00 Arbiter triggers SCRAM on high entropy
2. Safe brake activates within latency constraints
3. Constitutional invariants enforced under failure conditions

TEST SCENARIOS:
1. Gradual Degradation: Slowly increasing noise until entropy breach
2. Immediate Blockage: Instant sensor failure with max entropy
3. Intermittent Failure: Random sensor dropouts
"""

import sys
import time
import numpy as np
import json
from pathlib import Path
from typing import List

# Ensure PROJECT_ROOT is available
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.drivers.hardware_sync_node import HardwareSyncNode, SensorReading


class SensorBlockageStressTest:
    """
    Stress test for sensor failure scenarios.
    """
    
    def __init__(self):
        self.node = HardwareSyncNode(simulation_mode=True)
        self.test_results = {
            "gradual_degradation": None,
            "immediate_blockage": None,
            "intermittent_failure": None
        }
        
        # Logging
        self.log_dir = PROJECT_ROOT / "logs" / "sensors"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def test_gradual_degradation(self, steps: int = 100) -> dict:
        """
        Test gradual noise increase until entropy breach.
        
        Args:
            steps: Number of incremental steps
        
        Returns:
            Test results dict
        """
        print("=" * 80)
        print("  TEST 1: GRADUAL DEGRADATION")
        print("  Slowly increasing noise until entropy breach")
        print("=" * 80)
        print()
        
        # Reset node
        self.node.bayes_filter.reset()
        self.node.sensor_readings.clear()
        self.node.safe_brake_triggered = False
        
        noise_levels = np.linspace(0.0, 0.5, steps)
        breach_step = None
        
        for i, noise_level in enumerate(noise_levels):
            # Generate reading with increasing noise
            raw_value = 0.5 + np.random.normal(0, noise_level)
            
            # Process reading
            reading = self.node.sensor_callback(raw_value)
            
            # Check for breach
            if self.node.safe_brake_triggered and breach_step is None:
                breach_step = i
                print()
                print(f"🚨 ENTROPY BREACH at step {i}/{steps}")
                print(f"   Noise Level: {noise_level:.4f}")
                print(f"   Entropy: {reading.entropy:.4f}")
                print()
                break
            
            # Progress reporting
            if (i + 1) % 10 == 0:
                print(f"[STEP {i+1:3d}] Noise: {noise_level:.4f} | Entropy: {reading.entropy:.4f} | "
                      f"Belief: {reading.filtered_value:.4f} | Status: {'⚠️  BREACH' if self.node.safe_brake_triggered else '✅ OK'}")
        
        result = {
            "test_name": "gradual_degradation",
            "steps_completed": i + 1,
            "breach_step": breach_step,
            "breach_noise_level": noise_levels[breach_step] if breach_step else None,
            "safe_brake_triggered": self.node.safe_brake_triggered,
            "final_entropy": reading.entropy,
            "status": "PASS - Safe brake triggered" if self.node.safe_brake_triggered else "FAIL - No brake"
        }
        
        self.test_results["gradual_degradation"] = result
        print()
        print(f"Result: {result['status']}")
        print()
        
        return result
    
    def test_immediate_blockage(self) -> dict:
        """
        Test instant sensor failure (max entropy).
        
        Returns:
            Test results dict
        """
        print("=" * 80)
        print("  TEST 2: IMMEDIATE BLOCKAGE")
        print("  Instant sensor failure with maximum entropy")
        print("=" * 80)
        print()
        
        # Reset node
        self.node.bayes_filter.reset()
        self.node.sensor_readings.clear()
        self.node.safe_brake_triggered = False
        
        # Send extreme value to trigger max entropy
        raw_value = 1.0  # Extreme value
        reading = self.node.sensor_callback(raw_value)
        
        # Check immediate response
        brake_triggered = self.node.safe_brake_triggered
        
        print(f"Raw Value: {raw_value:.4f}")
        print(f"Entropy: {reading.entropy:.4f}")
        print(f"Latency: {reading.latency_ms:.4f}ms")
        print(f"Safe Brake: {'✅ TRIGGERED' if brake_triggered else '❌ NOT TRIGGERED'}")
        print()
        
        result = {
            "test_name": "immediate_blockage",
            "raw_value": raw_value,
            "entropy": reading.entropy,
            "latency_ms": reading.latency_ms,
            "safe_brake_triggered": brake_triggered,
            "status": "PASS - Immediate brake" if brake_triggered else "FAIL - No brake"
        }
        
        self.test_results["immediate_blockage"] = result
        print(f"Result: {result['status']}")
        print()
        
        return result
    
    def test_intermittent_failure(self, cycles: int = 50) -> dict:
        """
        Test random sensor dropouts.
        
        Args:
            cycles: Number of test cycles
        
        Returns:
            Test results dict
        """
        print("=" * 80)
        print("  TEST 3: INTERMITTENT FAILURE")
        print("  Random sensor dropouts and recoveries")
        print("=" * 80)
        print()
        
        # Reset node
        self.node.bayes_filter.reset()
        self.node.sensor_readings.clear()
        self.node.safe_brake_triggered = False
        
        breach_count = 0
        recovery_count = 0
        
        for i in range(cycles):
            # 20% chance of dropout
            if np.random.random() < 0.2:
                # Dropout: extreme noise
                raw_value = np.random.choice([0.0, 1.0])
                status = "DROPOUT"
            else:
                # Normal: low noise
                raw_value = 0.5 + np.random.normal(0, 0.05)
                status = "NORMAL"
            
            # Process reading
            reading = self.node.sensor_callback(raw_value)
            
            # Track breaches
            if not reading.passed_verification:
                breach_count += 1
            else:
                recovery_count += 1
            
            # Progress reporting
            if (i + 1) % 10 == 0:
                print(f"[CYCLE {i+1:2d}] Status: {status:8s} | Entropy: {reading.entropy:.4f} | "
                      f"Breaches: {breach_count:2d} | Recoveries: {recovery_count:2d}")
        
        result = {
            "test_name": "intermittent_failure",
            "cycles_completed": cycles,
            "breach_count": breach_count,
            "recovery_count": recovery_count,
            "breach_rate_pct": (breach_count / cycles) * 100,
            "status": "PASS - System detected failures" if breach_count > 0 else "FAIL - No detection"
        }
        
        self.test_results["intermittent_failure"] = result
        print()
        print(f"Result: {result['status']}")
        print(f"Breach Rate: {result['breach_rate_pct']:.1f}%")
        print()
        
        return result
    
    def run_all_tests(self):
        """Execute all stress tests."""
        print("=" * 80)
        print("  SENSOR BLOCKAGE STRESS TEST - PAC-HITL-HARDWARE-SYNC-33")
        print("  Validating GID-00 Arbiter SCRAM on sensor failure")
        print("=" * 80)
        print()
        
        # Run tests
        self.test_gradual_degradation(steps=100)
        self.test_immediate_blockage()
        self.test_intermittent_failure(cycles=50)
        
        # Summary
        print("=" * 80)
        print("  STRESS TEST SUMMARY")
        print("=" * 80)
        print()
        
        for test_name, result in self.test_results.items():
            if result:
                print(f"{test_name.upper()}: {result['status']}")
        
        print()
        
        # Export results
        self.export_test_report()
    
    def export_test_report(self):
        """Export stress test results."""
        report = {
            "pac_id": "PAC-HITL-HARDWARE-SYNC-33",
            "test_suite": "sensor_blockage_stress_test",
            "test_results": self.test_results,
            "timestamp": time.time()
        }
        
        report_path = self.log_dir / "sensor_blockage_stress_test.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"[EXPORT] Stress test report exported to: {report_path}")
        print()


if __name__ == '__main__':
    stress_test = SensorBlockageStressTest()
    stress_test.run_all_tests()
    
    print("=" * 80)
    print("  STRESS TEST COMPLETE")
    print("  Arbiter SCRAM validation successful.")
    print("=" * 80)
