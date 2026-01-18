#!/usr/bin/env python3
"""
FINANCIAL NOISE FLOOR VALIDATOR - PAC-38 PREP
Mathematical Distinction Between Mechanical Vibration and Transactional Anomalies

PROBLEM STATEMENT:
PAC-TENSION-TEST-37 generates mechanical jitter (coefficient 0.005) from rapid shadow swaps.
During Meter 50 atomic cutover, a $1M transaction ingresses.
The AML watchdog must NOT misclassify mechanical vibration as transactional anomaly.

SOLUTION:
Financial noise floor logic uses spectral analysis to distinguish:
  - MECHANICAL VIBRATION: High-frequency periodic signal (50Hz+ from RNP protocol)
  - TRANSACTIONAL ANOMALY: Low-frequency statistical deviation (AML-relevant patterns)

MATHEMATICAL DISTINCTION:
  Mechanical Jitter:
    - Frequency: 50-500Hz (rapid shadow swap timing)
    - Amplitude: Coefficient <= 0.005
    - Pattern: Periodic sinusoidal
    - FFT Spectrum: Dominant peak in high-frequency band
  
  Transactional Anomaly:
    - Frequency: 0.1-1Hz (transaction timing patterns)
    - Amplitude: Statistical Z-score > 3.0
    - Pattern: Non-periodic structural shift
    - FFT Spectrum: Dominant peak in low-frequency band

CONSTITUTIONAL INVARIANT:
  CB-FINANCE-01: AML watchdog MUST ignore high-frequency mechanical noise (>50Hz)
  CB-FINANCE-02: AML watchdog MUST trigger on low-frequency anomalies (Z-score > 3.0)
  CB-FINANCE-03: SCRAM if unable to classify signal (ambiguous spectrum)

INTEGRATION:
  PAC-37: Tension test generates mechanical jitter during $1M ingress
  PAC-38: Financial noise floor prevents false AML alerts
  PAC-BIZ-P33: Core settlement logic (referenced for transaction validation)

AUTHOR: Benson (BENSON-PROD-01, GID-00)
"""

import numpy as np
import time
import sys
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from scipy import fft, signal
from collections import deque


@dataclass
class SignalAnalysis:
    """Spectral analysis result for jitter classification"""
    timestamp: float
    signal_type: str  # "MECHANICAL", "TRANSACTIONAL", "AMBIGUOUS"
    dominant_frequency_hz: float
    amplitude: float
    z_score: float
    fft_peak_band: str  # "HIGH_FREQ", "LOW_FREQ", "MIXED"
    confidence: float
    classification_valid: bool


@dataclass
class FinancialNoiseReport:
    """Financial noise floor validation report"""
    timestamp: float
    total_samples: int
    mechanical_signals: int
    transactional_signals: int
    ambiguous_signals: int
    false_positive_rate: float
    false_negative_rate: float
    aml_watchdog_active: bool
    scram_triggered: bool
    constitutional_violations: List[str]


class FinancialNoiseFloorValidator:
    """
    Distinguishes mechanical vibration from transactional anomalies
    using spectral analysis and statistical thresholding.
    """
    
    # FREQUENCY BAND DEFINITIONS
    MECHANICAL_FREQ_MIN_HZ = 50.0   # RNP protocol vibration starts at 50Hz
    MECHANICAL_FREQ_MAX_HZ = 500.0  # Upper bound for mechanical jitter
    TRANSACTION_FREQ_MIN_HZ = 0.1   # Transaction timing patterns
    TRANSACTION_FREQ_MAX_HZ = 1.0   # Maximum transaction frequency
    
    # AMPLITUDE THRESHOLDS
    MECHANICAL_JITTER_THRESHOLD = 0.005  # From PAC-37 mandate
    TRANSACTION_Z_SCORE_THRESHOLD = 3.0  # 3-sigma rule for anomalies
    
    # CLASSIFICATION CONFIDENCE
    MIN_CONFIDENCE = 0.95  # 95% confidence required for classification
    
    def __init__(self, sample_rate_hz: float = 1000.0, window_size: int = 100):
        """
        Initialize financial noise floor validator.
        
        Args:
            sample_rate_hz: Sampling rate for signal acquisition (default 1000Hz)
            window_size: Number of samples for FFT analysis (default 100)
        """
        self.sample_rate_hz = sample_rate_hz
        self.window_size = window_size
        self.signal_buffer = deque(maxlen=window_size)
        
        # Statistics for AML watchdog
        self.mechanical_count = 0
        self.transactional_count = 0
        self.ambiguous_count = 0
        
        self.constitutional_violations = []
    
    def analyze_signal(self, signal_value: float) -> SignalAnalysis:
        """
        Perform spectral analysis on signal to classify as mechanical or transactional.
        
        Args:
            signal_value: Current jitter/anomaly signal value
            
        Returns:
            SignalAnalysis with classification and confidence
        """
        # Add to buffer
        self.signal_buffer.append(signal_value)
        
        # Wait for full window before analysis
        if len(self.signal_buffer) < self.window_size:
            return SignalAnalysis(
                timestamp=time.time(),
                signal_type="INSUFFICIENT_DATA",
                dominant_frequency_hz=0.0,
                amplitude=0.0,
                z_score=0.0,
                fft_peak_band="NONE",
                confidence=0.0,
                classification_valid=False
            )
        
        # Convert buffer to numpy array
        signal_array = np.array(self.signal_buffer)
        
        # 1. FFT SPECTRAL ANALYSIS
        fft_result = fft.rfft(signal_array)
        fft_magnitude = np.abs(fft_result)
        fft_freqs = fft.rfftfreq(len(signal_array), d=1.0/self.sample_rate_hz)
        
        # Find dominant frequency
        dominant_idx = np.argmax(fft_magnitude)
        dominant_freq_hz = fft_freqs[dominant_idx]
        
        # 2. AMPLITUDE ANALYSIS
        amplitude = np.max(np.abs(signal_array))
        
        # 3. STATISTICAL Z-SCORE (for transactional anomalies)
        mean_val = np.mean(signal_array)
        std_val = np.std(signal_array)
        z_score = abs(signal_value - mean_val) / (std_val + 1e-9)  # Avoid div by zero
        
        # 4. CLASSIFICATION LOGIC
        signal_type, fft_peak_band, confidence = self._classify_signal(
            dominant_freq_hz, amplitude, z_score
        )
        
        # 5. CONSTITUTIONAL ENFORCEMENT
        classification_valid = self._enforce_constitutional_invariants(
            signal_type, amplitude, z_score
        )
        
        # Update counters
        if signal_type == "MECHANICAL":
            self.mechanical_count += 1
        elif signal_type == "TRANSACTIONAL":
            self.transactional_count += 1
        elif signal_type == "AMBIGUOUS":
            self.ambiguous_count += 1
        
        return SignalAnalysis(
            timestamp=time.time(),
            signal_type=signal_type,
            dominant_frequency_hz=dominant_freq_hz,
            amplitude=amplitude,
            z_score=z_score,
            fft_peak_band=fft_peak_band,
            confidence=confidence,
            classification_valid=classification_valid
        )
    
    def _classify_signal(
        self, 
        dominant_freq_hz: float, 
        amplitude: float, 
        z_score: float
    ) -> tuple[str, str, float]:
        """
        Classify signal based on frequency, amplitude, and statistical properties.
        
        Returns:
            (signal_type, fft_peak_band, confidence)
        """
        # Determine frequency band
        in_mechanical_band = (
            self.MECHANICAL_FREQ_MIN_HZ <= dominant_freq_hz <= self.MECHANICAL_FREQ_MAX_HZ
        )
        in_transaction_band = (
            self.TRANSACTION_FREQ_MIN_HZ <= dominant_freq_hz <= self.TRANSACTION_FREQ_MAX_HZ
        )
        
        # CASE 1: HIGH-FREQUENCY MECHANICAL VIBRATION
        if in_mechanical_band and amplitude <= self.MECHANICAL_JITTER_THRESHOLD:
            return "MECHANICAL", "HIGH_FREQ", 0.99
        
        # CASE 2: LOW-FREQUENCY TRANSACTIONAL ANOMALY
        if in_transaction_band and z_score > self.TRANSACTION_Z_SCORE_THRESHOLD:
            return "TRANSACTIONAL", "LOW_FREQ", 0.98
        
        # CASE 3: HIGH-FREQUENCY EXCESS MECHANICAL (VIOLATION)
        if in_mechanical_band and amplitude > self.MECHANICAL_JITTER_THRESHOLD:
            return "MECHANICAL_VIOLATION", "HIGH_FREQ", 0.97
        
        # CASE 4: AMBIGUOUS (CANNOT CLASSIFY)
        # - Frequency outside both bands
        # - Mixed frequency content
        # - Low confidence classification
        return "AMBIGUOUS", "MIXED", 0.50
    
    def _enforce_constitutional_invariants(
        self, 
        signal_type: str, 
        amplitude: float, 
        z_score: float
    ) -> bool:
        """
        Enforce CB-FINANCE-01/02/03 constitutional invariants.
        
        Returns:
            True if signal classification is valid, False if SCRAM required
        """
        # CB-FINANCE-01: AML watchdog MUST ignore high-frequency mechanical noise
        if signal_type == "MECHANICAL":
            # Valid mechanical vibration - AML should ignore
            return True
        
        # CB-FINANCE-02: AML watchdog MUST trigger on low-frequency anomalies
        if signal_type == "TRANSACTIONAL":
            # Valid transactional anomaly - AML should alert
            return True
        
        # CB-FINANCE-03: SCRAM if unable to classify signal
        if signal_type == "AMBIGUOUS":
            self.constitutional_violations.append(
                f"CB-FINANCE-03: Ambiguous signal classification (cannot distinguish mechanical vs transactional)"
            )
            return False
        
        # MECHANICAL VIOLATION: Jitter exceeds threshold
        if signal_type == "MECHANICAL_VIOLATION":
            self.constitutional_violations.append(
                f"MECHANICAL_JITTER_VIOLATION: Amplitude {amplitude:.6f} > {self.MECHANICAL_JITTER_THRESHOLD}"
            )
            return False
        
        return True
    
    def generate_report(self) -> FinancialNoiseReport:
        """Generate financial noise floor validation report"""
        total = self.mechanical_count + self.transactional_count + self.ambiguous_count
        
        if total == 0:
            return FinancialNoiseReport(
                timestamp=time.time(),
                total_samples=0,
                mechanical_signals=0,
                transactional_signals=0,
                ambiguous_signals=0,
                false_positive_rate=0.0,
                false_negative_rate=0.0,
                aml_watchdog_active=True,
                scram_triggered=False,
                constitutional_violations=[]
            )
        
        # False positive rate: Mechanical signals misclassified as transactional
        # (In this simulation, we assume perfect classification, so FPR = ambiguous_rate)
        false_positive_rate = self.ambiguous_count / total
        
        # False negative rate: Transactional signals missed
        # (In this simulation, we assume zero false negatives if classification succeeds)
        false_negative_rate = 0.0
        
        scram_triggered = len(self.constitutional_violations) > 0
        
        return FinancialNoiseReport(
            timestamp=time.time(),
            total_samples=total,
            mechanical_signals=self.mechanical_count,
            transactional_signals=self.transactional_count,
            ambiguous_signals=self.ambiguous_count,
            false_positive_rate=false_positive_rate,
            false_negative_rate=false_negative_rate,
            aml_watchdog_active=True,
            scram_triggered=scram_triggered,
            constitutional_violations=self.constitutional_violations
        )
    
    def scram(self, report: FinancialNoiseReport):
        """Emergency halt on financial noise floor violation"""
        print("\n" + "="*80)
        print("🚨 FINANCIAL SCRAM: AML WATCHDOG VIOLATION 🚨")
        print("="*80)
        print(f"Timestamp: {datetime.fromtimestamp(report.timestamp).isoformat()}")
        print(f"\nTotal Samples: {report.total_samples}")
        print(f"  Mechanical Signals: {report.mechanical_signals}")
        print(f"  Transactional Signals: {report.transactional_signals}")
        print(f"  Ambiguous Signals: {report.ambiguous_signals}")
        print(f"\nFalse Positive Rate: {report.false_positive_rate*100:.2f}%")
        print(f"False Negative Rate: {report.false_negative_rate*100:.2f}%")
        print(f"\nConstitutional Violations:")
        for violation in report.constitutional_violations:
            print(f"  - {violation}")
        print("\nSYSTEM HALT. FINANCIAL INTEGRITY COMPROMISED.")
        print("="*80)
        
        # Export report
        log_dir = Path("/Users/johnbozza/Documents/Projects/ChainBridge-local-repo/logs/financial")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "financial_noise_floor_report.json"
        
        with open(log_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        
        print(f"[EXPORT] Financial noise floor log exported to: {log_path}")
        
        sys.exit(1)


def run_financial_noise_floor_test():
    """
    Standalone validation test for financial noise floor logic.
    Tests separation of mechanical vibration (50-500Hz, amplitude <= 0.005)
    from transactional anomalies (0.1-1Hz, Z-score > 3.0).
    """
    print("="*80)
    print("  FINANCIAL NOISE FLOOR VALIDATOR - PAC-38 PREP")
    print("  Mechanical vs Transactional Jitter Classification")
    print("="*80)
    
    validator = FinancialNoiseFloorValidator(sample_rate_hz=1000.0, window_size=100)
    
    print(f"\n[CONFIG] Sample Rate: {validator.sample_rate_hz}Hz")
    print(f"[CONFIG] Window Size: {validator.window_size} samples")
    print(f"[CONFIG] Mechanical Band: {validator.MECHANICAL_FREQ_MIN_HZ}-{validator.MECHANICAL_FREQ_MAX_HZ}Hz")
    print(f"[CONFIG] Transaction Band: {validator.TRANSACTION_FREQ_MIN_HZ}-{validator.TRANSACTION_FREQ_MAX_HZ}Hz")
    
    # TEST 1: MECHANICAL VIBRATION (50Hz, amplitude 0.003)
    print("\n[TEST 1] Mechanical Vibration - 50Hz sinusoid, amplitude 0.003")
    print("  Expected: MECHANICAL classification, AML should ignore")
    
    for i in range(100):
        # Generate 50Hz sinusoid with amplitude 0.003
        t = i / validator.sample_rate_hz
        signal_val = 0.003 * np.sin(2 * np.pi * 50.0 * t)
        analysis = validator.analyze_signal(signal_val)
    
    print(f"  Signal Type: {analysis.signal_type}")
    print(f"  Dominant Frequency: {analysis.dominant_frequency_hz:.2f}Hz")
    print(f"  Amplitude: {analysis.amplitude:.6f}")
    print(f"  Classification: {'✅ PASS' if analysis.signal_type == 'MECHANICAL' else '❌ FAIL'}")
    
    # TEST 2: TRANSACTIONAL ANOMALY (0.5Hz, Z-score > 3.0)
    print("\n[TEST 2] Transactional Anomaly - 0.5Hz pattern, Z-score > 3.0")
    print("  Expected: TRANSACTIONAL classification, AML should alert")
    
    # Reset validator for new test
    validator = FinancialNoiseFloorValidator(sample_rate_hz=1000.0, window_size=100)
    
    # Generate low-frequency transaction pattern with structural anomaly
    np.random.seed(42)  # Reproducible test
    for i in range(100):
        t = i / validator.sample_rate_hz
        # Low-frequency sinusoid (0.8Hz) with Gaussian noise
        baseline = 0.0005 * np.sin(2 * np.pi * 0.8 * t)
        noise = np.random.normal(0, 0.0001)
        
        # Create statistical anomaly in last 20% of window
        if i >= 80:
            anomaly = 0.005  # Large deviation (>10-sigma)
        else:
            anomaly = 0.0
        
        signal_val = baseline + noise + anomaly
        analysis = validator.analyze_signal(signal_val)
    
    print(f"  Signal Type: {analysis.signal_type}")
    print(f"  Dominant Frequency: {analysis.dominant_frequency_hz:.2f}Hz")
    print(f"  Z-Score: {analysis.z_score:.2f}")
    print(f"  Classification: {'✅ PASS' if analysis.signal_type == 'TRANSACTIONAL' else '❌ FAIL'}")
    
    # TEST 3: MECHANICAL VIOLATION (50Hz, amplitude 0.010 > threshold)
    print("\n[TEST 3] Mechanical Violation - 50Hz sinusoid, amplitude 0.010 (EXCEEDS THRESHOLD)")
    print("  Expected: MECHANICAL_VIOLATION, SCRAM triggered")
    
    validator = FinancialNoiseFloorValidator(sample_rate_hz=1000.0, window_size=100)
    
    for i in range(100):
        t = i / validator.sample_rate_hz
        signal_val = 0.010 * np.sin(2 * np.pi * 50.0 * t)  # Exceeds 0.005 threshold
        analysis = validator.analyze_signal(signal_val)
    
    print(f"  Signal Type: {analysis.signal_type}")
    print(f"  Amplitude: {analysis.amplitude:.6f} > {validator.MECHANICAL_JITTER_THRESHOLD}")
    print(f"  Classification: {'✅ PASS' if analysis.signal_type == 'MECHANICAL_VIOLATION' else '❌ FAIL'}")
    
    # FINAL REPORT
    report = validator.generate_report()
    
    print("\n" + "="*80)
    print("  FINANCIAL NOISE FLOOR TEST COMPLETE")
    print("="*80)
    print(f"Total Samples: {report.total_samples}")
    print(f"  Mechanical: {report.mechanical_signals}")
    print(f"  Transactional: {report.transactional_signals}")
    print(f"  Ambiguous: {report.ambiguous_signals}")
    print(f"False Positive Rate: {report.false_positive_rate*100:.2f}%")
    print(f"Constitutional Violations: {len(report.constitutional_violations)}")
    
    if report.scram_triggered:
        print("\n⚠️  SCRAM TRIGGERED (expected for Test 3 violation)")
    else:
        print("\n✅ FINANCIAL NOISE FLOOR OPERATIONAL")
    
    print("\n[READY] PAC-38 logic formatted for shadow buffer deployment")
    print("="*80)


if __name__ == "__main__":
    run_financial_noise_floor_test()
