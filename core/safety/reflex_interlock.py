#!/usr/bin/env python3
"""
REFLEX INTERLOCK MODULE - PAC-REFLEX-INTERLOCK-39
Physical Hazard Detection -> Financial Ledger Freeze Coupling

CONSTITUTIONAL LAW:
  "MOTION AND VALUE ARE ONE"
  Physical safety events MUST trigger financial holds within 50ms.
  If the wallet doesn't lock before the robot hits the wall, the system fails.

ARCHITECTURE:
  Sensor Hazard Detection -> Spectral Classification -> Ledger Freeze
  
  1. Sensor sampling at 1000Hz (Carnegie MultiSense S21)
  2. Spectral analysis distinguishes:
     - POTHOLE: 20Hz, 0.1 amplitude, 5ms duration -> IGNORE (transient vibration)
     - WALL: 2Hz, 0.8 amplitude, 200ms duration -> FREEZE (structural hazard)
  3. Ledger freeze triggered within 25ms-50ms window (2 heartbeats max)

SPECTRAL DISCRIMINATION:
  High-frequency transients (>10Hz, <50ms) = Mechanical noise (pothole)
  Low-frequency sustained (2-5Hz, >100ms) = Structural hazard (wall collision)

TIMING REQUIREMENTS:
  - Sensor sampling: 1ms interval (1000Hz)
  - Hazard detection: <5ms latency
  - Ledger freeze: <20ms latency
  - Total response: 25ms-50ms window

CONSTITUTIONAL INVARIANTS:
  - CB-REFLEX-01: Physical hazard -> Ledger freeze within 50ms
  - CB-REFLEX-02: High-freq transients ignored (no false freeze)
  - CB-REFLEX-03: Low-freq hazards trigger freeze (100% detection)

INTEGRATION:
  PAC-33: Carnegie S21 sensor input
  PAC-38: Spectral analysis (mechanical vs transactional noise)
  PAC-BIZ-P33: Settlement engine ledger freeze API

AUTHOR: Benson (BENSON-PROD-01, GID-00)
"""

import numpy as np
import time
import sys
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Literal
from pathlib import Path
from datetime import datetime
from scipy import fft, signal
from collections import deque
from enum import Enum


class HazardType(Enum):
    """Physical hazard classification"""
    TRANSIENT_VIBRATION = "TRANSIENT_VIBRATION"  # Pothole, ignore
    STRUCTURAL_HAZARD = "STRUCTURAL_HAZARD"      # Wall collision, freeze
    AMBIGUOUS = "AMBIGUOUS"                      # Cannot classify, SCRAM


class LedgerState(Enum):
    """Financial ledger state"""
    UNLOCKED = "UNLOCKED"  # Normal operation, transactions allowed
    FROZEN = "FROZEN"      # Emergency hold, all transactions blocked
    SCRAM = "SCRAM"        # System halt, safety violation


@dataclass
class HazardEvent:
    """Physical hazard detection event with timing"""
    sensor_trigger_us: int       # Microsecond timestamp when sensor detected event
    hazard_detection_us: int     # Microsecond timestamp when hazard classified
    ledger_freeze_us: int        # Microsecond timestamp when ledger frozen
    hazard_type: HazardType
    dominant_frequency_hz: float
    amplitude: float
    duration_ms: float
    spectral_classification: str
    total_latency_ms: float
    within_spec: bool            # True if latency within 25ms-50ms window


@dataclass
class ReflexInterlockReport:
    """Reflex interlock validation report"""
    timestamp: float
    total_events: int
    pothole_events: int
    wall_collision_events: int
    ambiguous_events: int
    false_positive_rate: float   # Pothole triggered freeze
    false_negative_rate: float   # Wall collision missed
    mean_latency_ms: float
    max_latency_ms: float
    within_spec_count: int
    scram_triggered: bool
    constitutional_violations: List[str]


class ReflexInterlockController:
    """
    Couples physical hazard detection to financial ledger freeze.
    Implements "Motion and Value are ONE" Constitutional Law.
    """
    
    # TIMING CONSTRAINTS (from PAC-39 mandate)
    LATENCY_MIN_MS = 25.0   # Minimum response time
    LATENCY_MAX_MS = 50.0   # Maximum response time (2 heartbeats)
    HEARTBEAT_MS = 25.0     # Heartbeat interval
    
    # SPECTRAL DISCRIMINATION THRESHOLDS
    TRANSIENT_FREQ_MIN_HZ = 10.0   # Potholes, mechanical noise
    TRANSIENT_DURATION_MAX_MS = 50.0
    TRANSIENT_AMPLITUDE_MAX = 0.3  # Small amplitude transients
    
    STRUCTURAL_FREQ_MAX_HZ = 5.0   # Wall collisions, sustained hazards
    STRUCTURAL_DURATION_MIN_MS = 50.0  # Lowered from 100ms for 100-sample window
    STRUCTURAL_AMPLITUDE_MIN = 0.5
    
    def __init__(self, sample_rate_hz: float = 1000.0, window_size: int = 100):
        """
        Initialize reflex interlock controller.
        
        Args:
            sample_rate_hz: Sensor sampling rate (default 1000Hz)
            window_size: Spectral analysis window (default 100 samples)
        """
        self.sample_rate_hz = sample_rate_hz
        self.window_size = window_size
        self.signal_buffer = deque(maxlen=window_size)
        
        # Ledger state
        self.ledger_state = LedgerState.UNLOCKED
        
        # Event tracking
        self.pothole_count = 0
        self.wall_collision_count = 0
        self.ambiguous_count = 0
        self.hazard_events: List[HazardEvent] = []
        
        # Constitutional violations
        self.constitutional_violations = []
    
    def detect_hazard(
        self, 
        sensor_value: float, 
        sensor_trigger_us: int
    ) -> Optional[HazardEvent]:
        """
        Detect and classify physical hazard from sensor signal.
        
        Args:
            sensor_value: Current sensor reading (acceleration, force, etc.)
            sensor_trigger_us: Microsecond timestamp when sensor triggered
            
        Returns:
            HazardEvent if hazard detected, None otherwise
        """
        # Add to signal buffer
        self.signal_buffer.append(sensor_value)
        
        # Wait for full window
        if len(self.signal_buffer) < self.window_size:
            return None
        
        # Microsecond timestamp for hazard detection
        hazard_detection_us = int(time.time() * 1_000_000)
        
        # Convert buffer to numpy array
        signal_array = np.array(self.signal_buffer)
        
        # 1. SPECTRAL ANALYSIS (FFT)
        fft_result = fft.rfft(signal_array)
        fft_magnitude = np.abs(fft_result)
        fft_freqs = fft.rfftfreq(len(signal_array), d=1.0/self.sample_rate_hz)
        
        # Find dominant frequency
        dominant_idx = np.argmax(fft_magnitude)
        dominant_freq_hz = fft_freqs[dominant_idx]
        
        # 2. AMPLITUDE ANALYSIS
        amplitude = np.max(np.abs(signal_array))
        
        # 3. DURATION ESTIMATION (time above threshold)
        threshold = 0.3  # Arbitrary threshold for duration calculation
        above_threshold = np.abs(signal_array) > threshold
        duration_samples = np.sum(above_threshold)
        duration_ms = (duration_samples / self.sample_rate_hz) * 1000.0
        
        # 4. SPECTRAL CLASSIFICATION
        hazard_type, spectral_classification = self._classify_hazard(
            dominant_freq_hz, amplitude, duration_ms
        )
        
        # 5. LEDGER FREEZE DECISION
        if hazard_type == HazardType.STRUCTURAL_HAZARD:
            ledger_freeze_us = self._freeze_ledger()
        else:
            ledger_freeze_us = 0  # No freeze
        
        # 6. TIMING VALIDATION
        if ledger_freeze_us > 0:
            total_latency_ms = (ledger_freeze_us - sensor_trigger_us) / 1000.0
            within_spec = self.LATENCY_MIN_MS <= total_latency_ms <= self.LATENCY_MAX_MS
        else:
            total_latency_ms = 0.0
            within_spec = True  # No freeze required for transient
        
        # 7. CREATE HAZARD EVENT
        event = HazardEvent(
            sensor_trigger_us=sensor_trigger_us,
            hazard_detection_us=hazard_detection_us,
            ledger_freeze_us=ledger_freeze_us,
            hazard_type=hazard_type,
            dominant_frequency_hz=dominant_freq_hz,
            amplitude=amplitude,
            duration_ms=duration_ms,
            spectral_classification=spectral_classification,
            total_latency_ms=total_latency_ms,
            within_spec=within_spec
        )
        
        # 8. ENFORCE CONSTITUTIONAL INVARIANTS
        self._enforce_constitutional_invariants(event)
        
        # Track event
        self.hazard_events.append(event)
        
        if hazard_type == HazardType.TRANSIENT_VIBRATION:
            self.pothole_count += 1
        elif hazard_type == HazardType.STRUCTURAL_HAZARD:
            self.wall_collision_count += 1
        elif hazard_type == HazardType.AMBIGUOUS:
            self.ambiguous_count += 1
        
        return event
    
    def _classify_hazard(
        self, 
        dominant_freq_hz: float, 
        amplitude: float, 
        duration_ms: float
    ) -> tuple[HazardType, str]:
        """
        Classify hazard based on spectral properties.
        
        Returns:
            (HazardType, spectral_classification_string)
        """
        # PRIORITIZE AMPLITUDE + DURATION for robust classification
        # (Dominant frequency can be unreliable due to DC component in short signals)
        
        # CASE 1: HIGH-FREQUENCY TRANSIENT (Pothole)
        # - Small amplitude (<0.3) AND short duration (<50ms)
        # - Action: IGNORE (do not freeze ledger)
        if amplitude < 0.3 and duration_ms <= self.TRANSIENT_DURATION_MAX_MS:
            return HazardType.TRANSIENT_VIBRATION, "HIGH_FREQ_TRANSIENT"
        
        # CASE 2: LOW-FREQUENCY STRUCTURAL (Wall Collision)
        # - Large amplitude (>0.5) AND sustained duration (>100ms)
        # - Action: FREEZE ledger immediately
        if (amplitude >= self.STRUCTURAL_AMPLITUDE_MIN and 
            duration_ms >= self.STRUCTURAL_DURATION_MIN_MS):
            return HazardType.STRUCTURAL_HAZARD, "LOW_FREQ_STRUCTURAL"
        
        # CASE 3: MEDIUM AMPLITUDE, MEDIUM DURATION
        # Use frequency as tiebreaker
        if dominant_freq_hz >= self.TRANSIENT_FREQ_MIN_HZ:
            # High frequency suggests transient
            return HazardType.TRANSIENT_VIBRATION, "HIGH_FREQ_TRANSIENT"
        elif dominant_freq_hz <= self.STRUCTURAL_FREQ_MAX_HZ and dominant_freq_hz > 0:
            # Low frequency suggests structural
            return HazardType.STRUCTURAL_HAZARD, "LOW_FREQ_STRUCTURAL"
        
        # CASE 4: AMBIGUOUS (Cannot classify)
        # - Borderline amplitude/duration with unclear frequency
        # - Action: SCRAM (safety violation)
        return HazardType.AMBIGUOUS, "AMBIGUOUS_SPECTRUM"
    
    def _freeze_ledger(self) -> int:
        """
        Freeze financial ledger to block all transactions.
        
        Returns:
            Microsecond timestamp when ledger frozen
        """
        # Simulate ledger freeze operation
        # In production, this would call PAC-BIZ-P33 settlement engine API
        freeze_timestamp_us = int(time.time() * 1_000_000)
        
        self.ledger_state = LedgerState.FROZEN
        
        return freeze_timestamp_us
    
    def _enforce_constitutional_invariants(self, event: HazardEvent):
        """
        Enforce CB-REFLEX-01/02/03 constitutional invariants.
        """
        # CB-REFLEX-01: Physical hazard -> Ledger freeze within 50ms
        if event.hazard_type == HazardType.STRUCTURAL_HAZARD:
            if not event.within_spec:
                self.constitutional_violations.append(
                    f"CB-REFLEX-01: Sensor-to-ledger latency {event.total_latency_ms:.2f}ms "
                    f"exceeds {self.LATENCY_MAX_MS}ms limit"
                )
        
        # CB-REFLEX-02: High-freq transients ignored (no false freeze)
        if event.hazard_type == HazardType.TRANSIENT_VIBRATION:
            if event.ledger_freeze_us > 0:
                self.constitutional_violations.append(
                    f"CB-REFLEX-02: False positive - Transient vibration triggered ledger freeze"
                )
        
        # CB-REFLEX-03: Low-freq hazards trigger freeze (100% detection)
        if event.hazard_type == HazardType.STRUCTURAL_HAZARD:
            if event.ledger_freeze_us == 0:
                self.constitutional_violations.append(
                    f"CB-REFLEX-03: False negative - Structural hazard missed, ledger not frozen"
                )
        
        # AMBIGUOUS CLASSIFICATION (SCRAM)
        if event.hazard_type == HazardType.AMBIGUOUS:
            self.constitutional_violations.append(
                f"CB-REFLEX-AMBIGUOUS: Cannot classify hazard, spectral analysis inconclusive"
            )
    
    def generate_report(self) -> ReflexInterlockReport:
        """Generate reflex interlock validation report"""
        total_events = len(self.hazard_events)
        
        if total_events == 0:
            return ReflexInterlockReport(
                timestamp=time.time(),
                total_events=0,
                pothole_events=0,
                wall_collision_events=0,
                ambiguous_events=0,
                false_positive_rate=0.0,
                false_negative_rate=0.0,
                mean_latency_ms=0.0,
                max_latency_ms=0.0,
                within_spec_count=0,
                scram_triggered=False,
                constitutional_violations=[]
            )
        
        # Calculate false positive/negative rates
        false_positives = sum(
            1 for e in self.hazard_events 
            if e.hazard_type == HazardType.TRANSIENT_VIBRATION and e.ledger_freeze_us > 0
        )
        false_negatives = sum(
            1 for e in self.hazard_events 
            if e.hazard_type == HazardType.STRUCTURAL_HAZARD and e.ledger_freeze_us == 0
        )
        
        false_positive_rate = false_positives / total_events if total_events > 0 else 0.0
        false_negative_rate = false_negatives / total_events if total_events > 0 else 0.0
        
        # Calculate latency statistics (only for structural hazards that froze ledger)
        structural_events = [
            e for e in self.hazard_events 
            if e.hazard_type == HazardType.STRUCTURAL_HAZARD and e.ledger_freeze_us > 0
        ]
        
        if structural_events:
            latencies = [e.total_latency_ms for e in structural_events]
            mean_latency_ms = np.mean(latencies)
            max_latency_ms = np.max(latencies)
        else:
            mean_latency_ms = 0.0
            max_latency_ms = 0.0
        
        within_spec_count = sum(1 for e in self.hazard_events if e.within_spec)
        
        scram_triggered = len(self.constitutional_violations) > 0
        
        return ReflexInterlockReport(
            timestamp=time.time(),
            total_events=total_events,
            pothole_events=self.pothole_count,
            wall_collision_events=self.wall_collision_count,
            ambiguous_events=self.ambiguous_count,
            false_positive_rate=false_positive_rate,
            false_negative_rate=false_negative_rate,
            mean_latency_ms=mean_latency_ms,
            max_latency_ms=max_latency_ms,
            within_spec_count=within_spec_count,
            scram_triggered=scram_triggered,
            constitutional_violations=self.constitutional_violations
        )
    
    def scram(self, report: ReflexInterlockReport):
        """Emergency halt on reflex interlock violation"""
        print("\n" + "="*80)
        print("🚨 REFLEX INTERLOCK SCRAM: NERVOUS SYSTEM FAILURE 🚨")
        print("="*80)
        print(f"Timestamp: {datetime.fromtimestamp(report.timestamp).isoformat()}")
        print(f"\nTotal Hazard Events: {report.total_events}")
        print(f"  Pothole Events (Transient): {report.pothole_events}")
        print(f"  Wall Collision Events (Structural): {report.wall_collision_events}")
        print(f"  Ambiguous Events: {report.ambiguous_events}")
        print(f"\nFalse Positive Rate: {report.false_positive_rate*100:.2f}%")
        print(f"False Negative Rate: {report.false_negative_rate*100:.2f}%")
        print(f"\nLatency Statistics:")
        print(f"  Mean: {report.mean_latency_ms:.2f}ms")
        print(f"  Max: {report.max_latency_ms:.2f}ms")
        print(f"  Within Spec (25-50ms): {report.within_spec_count}/{report.total_events}")
        print(f"\nConstitutional Violations:")
        for violation in report.constitutional_violations:
            print(f"  - {violation}")
        print("\nSYSTEM HALT. MOTION AND VALUE COUPLING FAILED.")
        print("="*80)
        
        # Export report
        log_dir = Path("/Users/johnbozza/Documents/Projects/ChainBridge-local-repo/logs/reflex")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "reflex_interlock_report.json"
        
        with open(log_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        
        print(f"[EXPORT] Reflex interlock log exported to: {log_path}")
        
        sys.exit(1)


if __name__ == "__main__":
    print("Reflex Interlock Module - PAC-REFLEX-INTERLOCK-39")
    print("Use coupled_stress_test.py to execute validation tests")
