#!/usr/bin/env python3
"""
COUPLED STRESS TEST - PAC-REFLEX-INTERLOCK-39
Motion and Value Coupling Validation with Microsecond Precision

JEFFREY'S MANDATE:
"We cannot deploy the Nervous System without testing the pain reflex. 
I need to see the exact timestamp delta between 'Sensor Block' and 'Ledger Freeze'."

TEST SCENARIOS:
1. POTHOLE TRANSIENT: 20Hz, 0.1 amplitude, 5ms duration
   - Expected: NO ledger freeze (spectral bleed discrimination)
   - Pass: Zero false positives

2. WALL COLLISION HAZARD: 2Hz, 0.8 amplitude, 200ms duration
   - Expected: Ledger freeze within 25ms-50ms window
   - Pass: Sensor-to-ledger latency within spec

3. RAPID HAZARD SEQUENCE: 10 potholes + 1 wall collision
   - Expected: Ignore potholes, freeze on collision
   - Pass: 100% discrimination accuracy

PRECISION LOGGING:
- Microsecond timestamps for all events
- Sensor trigger, hazard detection, ledger freeze timing
- Spectral classification for each event
- Constitutional invariant validation

AUTHOR: Benson (BENSON-PROD-01, GID-00)
"""

import numpy as np
import time
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Import reflex interlock controller
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.safety.reflex_interlock import (
    ReflexInterlockController, 
    HazardType, 
    HazardEvent
)


def generate_pothole_signal(
    sample_rate_hz: float = 1000.0, 
    duration_ms: float = 5.0
) -> np.ndarray:
    """
    Generate synthetic pothole signal (high-frequency transient).
    
    Args:
        sample_rate_hz: Sampling rate
        duration_ms: Signal duration in milliseconds
        
    Returns:
        Numpy array with pothole signal
    """
    num_samples = int((duration_ms / 1000.0) * sample_rate_hz)
    t = np.arange(num_samples) / sample_rate_hz
    
    # 20Hz sinusoid with 0.1 amplitude
    frequency_hz = 20.0
    amplitude = 0.1
    signal = amplitude * np.sin(2 * np.pi * frequency_hz * t)
    
    return signal


def generate_wall_collision_signal(
    sample_rate_hz: float = 1000.0, 
    duration_ms: float = 200.0
) -> np.ndarray:
    """
    Generate synthetic wall collision signal (low-frequency structural hazard).
    
    Args:
        sample_rate_hz: Sampling rate
        duration_ms: Signal duration in milliseconds
        
    Returns:
        Numpy array with wall collision signal
    """
    num_samples = int((duration_ms / 1000.0) * sample_rate_hz)
    t = np.arange(num_samples) / sample_rate_hz
    
    # 2Hz sinusoid with 0.8 amplitude
    frequency_hz = 2.0
    amplitude = 0.8
    signal = amplitude * np.sin(2 * np.pi * frequency_hz * t)
    
    return signal


def run_test_scenario_1_pothole():
    """
    TEST 1: Pothole Transient
    - 20Hz, 0.1 amplitude, 5ms duration
    - Expected: NO ledger freeze (spectral bleed discrimination)
    - Pass: Zero false positives
    """
    print("\n" + "="*80)
    print("  TEST 1: POTHOLE TRANSIENT (Spectral Bleed Discrimination)")
    print("="*80)
    print("[SCENARIO] High-frequency vibration (pothole)")
    print("[EXPECTED] NO ledger freeze, zero false positives")
    
    controller = ReflexInterlockController(sample_rate_hz=1000.0, window_size=100)
    
    # Generate pothole signal
    pothole_signal = generate_pothole_signal(duration_ms=5.0)
    
    # Prepend zeros to fill window (100 samples)
    padding = np.zeros(95)  # 100 - 5 = 95 samples
    full_signal = np.concatenate([padding, pothole_signal])
    
    # Feed signal to controller
    event = None
    for i, sample in enumerate(full_signal):
        sensor_trigger_us = int(time.time() * 1_000_000)
        event = controller.detect_hazard(sample, sensor_trigger_us)
    
    # Validate result
    if event is None:
        print("[RESULT] ❌ FAIL - No hazard event detected")
        return False
    
    print(f"\n[HAZARD DETECTED]")
    print(f"  Type: {event.hazard_type.value}")
    print(f"  Dominant Frequency: {event.dominant_frequency_hz:.2f}Hz")
    print(f"  Amplitude: {event.amplitude:.4f}")
    print(f"  Duration: {event.duration_ms:.2f}ms")
    print(f"  Spectral Classification: {event.spectral_classification}")
    print(f"  Ledger Frozen: {'YES' if event.ledger_freeze_us > 0 else 'NO'}")
    
    # Pass criteria
    if event.hazard_type == HazardType.TRANSIENT_VIBRATION and event.ledger_freeze_us == 0:
        print(f"\n[RESULT] ✅ PASS - Pothole correctly ignored, no ledger freeze")
        return True
    else:
        print(f"\n[RESULT] ❌ FAIL - False positive: Pothole triggered ledger freeze")
        return False


def run_test_scenario_2_wall_collision():
    """
    TEST 2: Wall Collision Hazard
    - 2Hz, 0.8 amplitude, 200ms duration
    - Expected: Ledger freeze within 25ms-50ms window
    - Pass: Sensor-to-ledger latency within spec
    """
    print("\n" + "="*80)
    print("  TEST 2: WALL COLLISION HAZARD (Pain Reflex)")
    print("="*80)
    print("[SCENARIO] Low-frequency structural hazard (wall collision)")
    print("[EXPECTED] Ledger freeze within 25ms-50ms window")
    
    controller = ReflexInterlockController(sample_rate_hz=1000.0, window_size=100)
    
    # Generate wall collision signal (200ms duration, 200 samples at 1000Hz)
    wall_signal = generate_wall_collision_signal(duration_ms=200.0)
    
    # Process first 100 samples (window size)
    event = None
    for i in range(100):
        sensor_trigger_us = int(time.time() * 1_000_000)
        sample = wall_signal[i]
        event = controller.detect_hazard(sample, sensor_trigger_us)
    
    # Validate result
    if event is None:
        print("[RESULT] ❌ FAIL - No hazard event detected")
        return False
    
    print(f"\n[HAZARD DETECTED]")
    print(f"  Type: {event.hazard_type.value}")
    print(f"  Dominant Frequency: {event.dominant_frequency_hz:.2f}Hz")
    print(f"  Amplitude: {event.amplitude:.4f}")
    print(f"  Duration: {event.duration_ms:.2f}ms")
    print(f"  Spectral Classification: {event.spectral_classification}")
    print(f"  Ledger Frozen: {'YES' if event.ledger_freeze_us > 0 else 'NO'}")
    
    # Timing analysis
    if event.ledger_freeze_us > 0:
        print(f"\n[TIMING ANALYSIS]")
        print(f"  Sensor Trigger: {event.sensor_trigger_us} μs")
        print(f"  Hazard Detection: {event.hazard_detection_us} μs")
        print(f"  Ledger Freeze: {event.ledger_freeze_us} μs")
        print(f"  Total Latency: {event.total_latency_ms:.3f}ms")
        print(f"  Within Spec (25-50ms): {'YES' if event.within_spec else 'NO'}")
    
    # Pass criteria
    if (event.hazard_type == HazardType.STRUCTURAL_HAZARD and 
        event.ledger_freeze_us > 0 and 
        event.within_spec):
        print(f"\n[RESULT] ✅ PASS - Wall collision detected, ledger frozen within spec")
        return True
    elif event.hazard_type == HazardType.STRUCTURAL_HAZARD and event.ledger_freeze_us == 0:
        print(f"\n[RESULT] ❌ FAIL - False negative: Wall collision missed, ledger not frozen")
        return False
    elif event.hazard_type == HazardType.STRUCTURAL_HAZARD and not event.within_spec:
        print(f"\n[RESULT] ❌ FAIL - Timing violation: Latency {event.total_latency_ms:.2f}ms outside 25-50ms window")
        return False
    else:
        print(f"\n[RESULT] ❌ FAIL - Incorrect classification")
        return False


def run_test_scenario_3_mixed_sequence():
    """
    TEST 3: Rapid Hazard Sequence
    - 10 potholes + 1 wall collision
    - Expected: Ignore potholes, freeze on collision
    - Pass: 100% discrimination accuracy
    """
    print("\n" + "="*80)
    print("  TEST 3: RAPID HAZARD SEQUENCE (Discrimination Accuracy)")
    print("="*80)
    print("[SCENARIO] 10 pothole transients + 1 wall collision")
    print("[EXPECTED] Ignore all potholes, freeze only on wall collision")
    
    controller = ReflexInterlockController(sample_rate_hz=1000.0, window_size=100)
    
    # Generate 10 pothole signals
    pothole_events = []
    for i in range(10):
        pothole_signal = generate_pothole_signal(duration_ms=5.0)
        padding = np.zeros(95)
        full_signal = np.concatenate([padding, pothole_signal])
        
        event = None
        for sample in full_signal:
            sensor_trigger_us = int(time.time() * 1_000_000)
            event = controller.detect_hazard(sample, sensor_trigger_us)
        
        if event:
            pothole_events.append(event)
    
    # Generate 1 wall collision signal
    wall_signal = generate_wall_collision_signal(duration_ms=200.0)
    wall_event = None
    for i in range(100):
        sensor_trigger_us = int(time.time() * 1_000_000)
        sample = wall_signal[i]
        wall_event = controller.detect_hazard(sample, sensor_trigger_us)
    
    # Validate results
    print(f"\n[POTHOLE EVENTS]")
    pothole_false_positives = 0
    for i, event in enumerate(pothole_events):
        if event.ledger_freeze_us > 0:
            pothole_false_positives += 1
        print(f"  Pothole {i+1}: Type={event.hazard_type.value}, Frozen={'YES' if event.ledger_freeze_us > 0 else 'NO'}")
    
    print(f"\n[WALL COLLISION EVENT]")
    if wall_event:
        print(f"  Type: {wall_event.hazard_type.value}")
        print(f"  Ledger Frozen: {'YES' if wall_event.ledger_freeze_us > 0 else 'NO'}")
        print(f"  Latency: {wall_event.total_latency_ms:.3f}ms")
    else:
        print(f"  ❌ FAIL - No wall collision detected")
        return False
    
    # Pass criteria
    all_potholes_ignored = pothole_false_positives == 0
    wall_detected_and_frozen = (wall_event and 
                                 wall_event.hazard_type == HazardType.STRUCTURAL_HAZARD and 
                                 wall_event.ledger_freeze_us > 0)
    
    print(f"\n[DISCRIMINATION ACCURACY]")
    print(f"  Pothole False Positives: {pothole_false_positives}/10")
    print(f"  Wall Collision Detected: {'YES' if wall_detected_and_frozen else 'NO'}")
    
    if all_potholes_ignored and wall_detected_and_frozen:
        print(f"\n[RESULT] ✅ PASS - 100% discrimination accuracy")
        return True
    else:
        print(f"\n[RESULT] ❌ FAIL - Discrimination errors detected")
        return False


def main():
    """
    Execute coupled stress test for PAC-REFLEX-INTERLOCK-39.
    Validates "Motion and Value are ONE" Constitutional Law.
    """
    print("="*80)
    print("  COUPLED STRESS TEST - PAC-REFLEX-INTERLOCK-39")
    print("  Motion and Value Coupling Validation")
    print("="*80)
    print("\nJEFFREY'S MANDATE:")
    print("  'We cannot deploy the Nervous System without testing the pain reflex.'")
    print("  'I need to see the exact timestamp delta between Sensor Block and Ledger Freeze.'")
    print("\nCONSTITUTIONAL LAW:")
    print("  'MOTION AND VALUE ARE ONE'")
    print("  Physical hazard detection MUST trigger financial hold within 50ms.")
    print("="*80)
    
    # Run test scenarios
    results = []
    
    # Test 1: Pothole transient
    results.append(("Pothole Transient", run_test_scenario_1_pothole()))
    
    # Test 2: Wall collision
    results.append(("Wall Collision", run_test_scenario_2_wall_collision()))
    
    # Test 3: Mixed sequence
    results.append(("Mixed Sequence", run_test_scenario_3_mixed_sequence()))
    
    # Final summary
    print("\n" + "="*80)
    print("  COUPLED STRESS TEST SUMMARY")
    print("="*80)
    
    all_passed = all(result[1] for result in results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print("\n" + "="*80)
    if all_passed:
        print("  ✅ NERVOUS SYSTEM VALIDATED")
        print("  'Motion and Value are ONE' - Constitutional Law enforced")
        print("  Pain reflex operational: Physical hazard -> Ledger freeze within 50ms")
    else:
        print("  ❌ NERVOUS SYSTEM FAILURE")
        print("  Constitutional Law violations detected")
        print("  Deploy FORBIDDEN until pain reflex validated")
    print("="*80)
    
    # Export detailed report
    log_dir = Path("/Users/johnbozza/Documents/Projects/ChainBridge-local-repo/logs/reflex")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "coupled_stress_test_report.json"
    
    report = {
        "pac_id": "PAC-REFLEX-INTERLOCK-39",
        "test_type": "COUPLED_STRESS_TEST",
        "timestamp": datetime.now().isoformat(),
        "constitutional_law": "MOTION AND VALUE ARE ONE",
        "test_results": {
            "pothole_transient": results[0][1],
            "wall_collision": results[1][1],
            "mixed_sequence": results[2][1]
        },
        "all_tests_passed": all_passed,
        "nervous_system_validated": all_passed
    }
    
    with open(log_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n[EXPORT] Detailed test report exported to: {log_path}")
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
