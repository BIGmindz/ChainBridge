#!/usr/bin/env python3
"""
PAC-SANDBOX-STRESS-001: ADVERSARIAL HARDENING STRESS TEST SUITE
================================================================

Stress testing framework for ChainBridge sandbox with adversarial hardening.

SWARM ASSIGNMENTS:
1. CODY (GID-01): Negative amount hardening
2. FORGE (GID-04): Latency jitter simulation under CPU load
3. SAM (GID-06): Malformed ISO 20022 injection testing
4. SONNY (GID-02): UI stress visualization (kinetic mesh load reflection)

GOVERNANCE:
- LAW: CONTROL_OVER_AUTONOMY
- STANDARD: NASA_GRADE_ADVERSARIAL_HARDENING
- PROTOCOL: NEGATIVE_AMOUNT_VALIDATION_FIX

EXPECTED OUTCOME: HARDENED_SANDBOX_WITH_ZERO_NEGATIVE_DRIFT

Author: BENSON (GID-00) Orchestrator
PAC: CB-SANDBOX-STRESS-2026-01-27
"""

import hashlib
import json
import logging
import multiprocessing
import os
import random
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SandboxStressTest")


# ═══════════════════════════════════════════════════════════════════════════════
# CODY (GID-01): NEGATIVE AMOUNT HARDENING
# ═══════════════════════════════════════════════════════════════════════════════

class NegativeAmountViolation(Exception):
    """Raised when negative amount detected in settlement."""
    pass


class UnsignedAmountValidator:
    """
    Strict unsigned integer/decimal validator for settlement amounts.
    
    CODY (GID-01) Task: Implement strict unsigned validation for all settlements.
    
    Governance Invariant: INV-FIN-NEG-001
    - All settlement amounts MUST be non-negative
    - Zero amounts MAY be allowed for specific use cases (void/cancel)
    - Negative amounts MUST raise NegativeAmountViolation
    - Float inputs MUST be rejected (use Decimal only)
    
    Fail-closed behavior: Any validation failure aborts the operation.
    """
    
    def __init__(self, allow_zero: bool = True, strict_decimal: bool = True):
        """
        Initialize validator.
        
        Args:
            allow_zero: Whether to allow zero amounts (for voids/cancels)
            strict_decimal: Require Decimal type (reject float)
        """
        self.allow_zero = allow_zero
        self.strict_decimal = strict_decimal
        self.violation_count = 0
        self.validation_count = 0
        
    def validate(self, amount: Any, context: str = "settlement") -> Decimal:
        """
        Validate amount is non-negative and properly typed.
        
        Args:
            amount: Amount to validate (should be Decimal)
            context: Context for error messages
            
        Returns:
            Validated Decimal amount
            
        Raises:
            NegativeAmountViolation: If amount is negative
            TypeError: If amount is float (when strict_decimal=True)
            InvalidOperation: If amount cannot be converted to Decimal
        """
        self.validation_count += 1
        
        # CODY GID-01: Strict type enforcement
        if self.strict_decimal and isinstance(amount, float):
            self.violation_count += 1
            raise TypeError(
                f"INV-FIN-NEG-001 VIOLATION: {context} amount is float ({amount}). "
                f"Use Decimal to prevent precision drift. "
                f"Example: Decimal('100.50') not 100.50"
            )
        
        # Convert to Decimal if needed
        try:
            if isinstance(amount, Decimal):
                decimal_amount = amount
            else:
                decimal_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError) as e:
            self.violation_count += 1
            raise InvalidOperation(
                f"INV-FIN-NEG-001 VIOLATION: {context} amount cannot be converted "
                f"to Decimal: {amount} ({type(amount).__name__}). Error: {e}"
            )
        
        # CODY GID-01: CRITICAL - Negative amount check
        if decimal_amount < Decimal("0"):
            self.violation_count += 1
            raise NegativeAmountViolation(
                f"INV-FIN-NEG-001 CRITICAL: {context} received NEGATIVE amount: "
                f"{decimal_amount}. Settlement amounts MUST be >= 0. "
                f"For refunds, use separate REFUND transaction type."
            )
        
        # Check zero (if not allowed)
        if not self.allow_zero and decimal_amount == Decimal("0"):
            self.violation_count += 1
            raise NegativeAmountViolation(
                f"INV-FIN-NEG-001 VIOLATION: {context} received ZERO amount "
                f"but zero is not allowed for this operation."
            )
        
        return decimal_amount
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return {
            "total_validations": self.validation_count,
            "violations_caught": self.violation_count,
            "pass_rate": (
                (self.validation_count - self.violation_count) / self.validation_count * 100
                if self.validation_count > 0 else 0
            )
        }


def run_negative_amount_tests() -> Tuple[int, int, List[str]]:
    """
    CODY (GID-01): Run negative amount hardening tests.
    
    Tests:
    1. Reject negative Decimal amounts
    2. Reject float type (precision drift prevention)
    3. Accept positive Decimal amounts
    4. Accept zero when allowed
    5. Reject zero when not allowed
    6. Boundary testing (very small/large amounts)
    
    Returns:
        Tuple of (passed, failed, failure_details)
    """
    print("\n" + "="*60)
    print("CODY (GID-01): NEGATIVE AMOUNT HARDENING TESTS")
    print("="*60 + "\n")
    
    validator = UnsignedAmountValidator(allow_zero=True, strict_decimal=True)
    passed = 0
    failed = 0
    failures = []
    
    # Test cases: (amount, should_pass, test_name)
    test_cases = [
        # Negative amount rejection
        (Decimal("-100.00"), False, "Reject negative Decimal"),
        (Decimal("-0.01"), False, "Reject tiny negative"),
        (Decimal("-999999999.99"), False, "Reject large negative"),
        
        # Float type rejection
        (100.50, False, "Reject float type"),
        (-50.25, False, "Reject negative float"),
        (0.0, False, "Reject float zero"),
        
        # Valid positive amounts
        (Decimal("100.00"), True, "Accept positive Decimal"),
        (Decimal("0.01"), True, "Accept tiny positive"),
        (Decimal("999999999.99"), True, "Accept large positive"),
        
        # Zero handling
        (Decimal("0"), True, "Accept zero (allowed)"),
        (Decimal("0.00"), True, "Accept zero with decimals"),
        
        # String conversion
        ("100.50", True, "Accept string conversion"),
        ("-50.00", False, "Reject negative string"),
        
        # Boundary tests
        (Decimal("0.001"), True, "Accept sub-cent positive"),
        (Decimal("-0.001"), False, "Reject sub-cent negative"),
    ]
    
    for amount, should_pass, test_name in test_cases:
        try:
            result = validator.validate(amount, f"test:{test_name}")
            if should_pass:
                print(f"✅ PASS: {test_name} → {result}")
                passed += 1
            else:
                print(f"❌ FAIL: {test_name} → Should have rejected {amount}")
                failed += 1
                failures.append(f"{test_name}: Expected rejection, got acceptance")
        except (NegativeAmountViolation, TypeError, InvalidOperation) as e:
            if not should_pass:
                print(f"✅ PASS: {test_name} → Correctly rejected: {type(e).__name__}")
                passed += 1
            else:
                print(f"❌ FAIL: {test_name} → Unexpected rejection: {e}")
                failed += 1
                failures.append(f"{test_name}: Unexpected rejection - {e}")
    
    # Test zero-disallowed mode
    validator_strict = UnsignedAmountValidator(allow_zero=False, strict_decimal=True)
    try:
        validator_strict.validate(Decimal("0"), "zero-test")
        print(f"❌ FAIL: Zero rejection mode → Should have rejected zero")
        failed += 1
        failures.append("Zero rejection mode: Expected rejection, got acceptance")
    except NegativeAmountViolation:
        print(f"✅ PASS: Zero rejection mode → Correctly rejected zero")
        passed += 1
    
    print("\n" + "-"*60)
    print(f"CODY (GID-01) RESULTS: {passed} passed, {failed} failed")
    print(f"Validation stats: {validator.get_stats()}")
    print("-"*60)
    
    return passed, failed, failures


# ═══════════════════════════════════════════════════════════════════════════════
# FORGE (GID-04): LATENCY JITTER SIMULATION UNDER CPU LOAD
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LatencyMeasurement:
    """Single latency measurement."""
    operation: str
    latency_ms: float
    cpu_load_pct: float
    success: bool
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class CPUStressSimulator:
    """
    CPU stress simulator for latency jitter testing.
    
    FORGE (GID-04) Task: Stress test PQC signing under 90% CPU load.
    
    Creates synthetic CPU load to test system behavior under stress.
    Measures latency jitter for critical operations.
    """
    
    def __init__(self, target_load_pct: float = 90.0):
        """
        Initialize CPU stress simulator.
        
        Args:
            target_load_pct: Target CPU load percentage (0-100)
        """
        self.target_load_pct = min(max(target_load_pct, 0), 100)
        self.stress_threads: List[threading.Thread] = []
        self.running = False
        self.measurements: List[LatencyMeasurement] = []
        
    def _cpu_burn(self, duration_sec: float):
        """Burn CPU cycles for specified duration."""
        end_time = time.time() + duration_sec
        while time.time() < end_time and self.running:
            # Compute-intensive operation
            _ = sum(i * i for i in range(10000))
            # Brief sleep to control load
            sleep_time = 0.01 * (100 - self.target_load_pct) / 100
            time.sleep(max(0.001, sleep_time))
    
    def start_stress(self, duration_sec: float = 10.0, num_threads: int = None):
        """
        Start CPU stress test.
        
        Args:
            duration_sec: Duration of stress test
            num_threads: Number of stress threads (default: CPU count - 1)
        """
        if num_threads is None:
            num_threads = max(1, multiprocessing.cpu_count() - 1)
        
        self.running = True
        logger.info(f"🔥 Starting CPU stress: {self.target_load_pct}% load, "
                   f"{num_threads} threads, {duration_sec}s duration")
        
        for i in range(num_threads):
            t = threading.Thread(target=self._cpu_burn, args=(duration_sec,), daemon=True)
            t.start()
            self.stress_threads.append(t)
    
    def stop_stress(self):
        """Stop CPU stress test."""
        self.running = False
        for t in self.stress_threads:
            t.join(timeout=1.0)
        self.stress_threads.clear()
        logger.info("✅ CPU stress stopped")
    
    def measure_operation_latency(
        self, 
        operation_fn, 
        operation_name: str,
        cpu_load_pct: float = 0.0
    ) -> LatencyMeasurement:
        """
        Measure latency of an operation.
        
        Args:
            operation_fn: Function to measure
            operation_name: Name for logging
            cpu_load_pct: Current CPU load estimate
            
        Returns:
            LatencyMeasurement with results
        """
        start_time = time.time()
        try:
            operation_fn()
            success = True
        except Exception as e:
            logger.warning(f"⚠️ Operation {operation_name} failed: {e}")
            success = False
        
        latency_ms = (time.time() - start_time) * 1000
        
        measurement = LatencyMeasurement(
            operation=operation_name,
            latency_ms=latency_ms,
            cpu_load_pct=cpu_load_pct,
            success=success
        )
        self.measurements.append(measurement)
        return measurement


def mock_pqc_sign(data: str = "test_payload") -> str:
    """Mock PQC signature operation (simulates ML-DSA-65 signing)."""
    # Simulate crypto computation
    for _ in range(1000):
        _ = hashlib.sha3_256(data.encode()).hexdigest()
    return hashlib.sha3_256(data.encode()).hexdigest()


def run_latency_jitter_tests() -> Tuple[int, int, Dict[str, Any]]:
    """
    FORGE (GID-04): Run latency jitter simulation under CPU load.
    
    Tests:
    1. Baseline latency (no load)
    2. Latency under 50% CPU load
    3. Latency under 90% CPU load
    4. Jitter analysis (variance in latency)
    5. Success rate under stress
    
    Returns:
        Tuple of (passed, failed, stats)
    """
    print("\n" + "="*60)
    print("FORGE (GID-04): LATENCY JITTER SIMULATION")
    print("="*60 + "\n")
    
    passed = 0
    failed = 0
    stats = {
        "baseline_latency_ms": [],
        "stress_latency_ms": [],
        "jitter_variance": 0.0,
        "success_rate_pct": 0.0
    }
    
    # Test 1: Baseline latency (no stress)
    print("[TEST 1/4] Baseline latency measurement (no CPU stress)...")
    simulator = CPUStressSimulator(target_load_pct=0)
    baseline_measurements = []
    
    for i in range(10):
        m = simulator.measure_operation_latency(
            lambda: mock_pqc_sign(f"baseline-{i}"),
            f"PQC-sign-baseline-{i}",
            cpu_load_pct=0.0
        )
        baseline_measurements.append(m.latency_ms)
    
    avg_baseline = sum(baseline_measurements) / len(baseline_measurements)
    stats["baseline_latency_ms"] = baseline_measurements
    print(f"   Baseline avg latency: {avg_baseline:.2f}ms")
    print(f"   ✅ PASS: Baseline measured")
    passed += 1
    
    # Test 2: Latency under 50% CPU load
    print("\n[TEST 2/4] Latency under 50% CPU load...")
    simulator_50 = CPUStressSimulator(target_load_pct=50)
    simulator_50.start_stress(duration_sec=3.0, num_threads=2)
    time.sleep(0.5)  # Let stress stabilize
    
    load_50_measurements = []
    for i in range(5):
        m = simulator_50.measure_operation_latency(
            lambda: mock_pqc_sign(f"load50-{i}"),
            f"PQC-sign-50pct-{i}",
            cpu_load_pct=50.0
        )
        load_50_measurements.append(m.latency_ms)
    
    simulator_50.stop_stress()
    avg_50 = sum(load_50_measurements) / len(load_50_measurements)
    print(f"   50% load avg latency: {avg_50:.2f}ms (baseline: {avg_baseline:.2f}ms)")
    
    # Latency should increase but not dramatically
    if avg_50 < avg_baseline * 10:  # Less than 10x increase
        print(f"   ✅ PASS: 50% load latency acceptable")
        passed += 1
    else:
        print(f"   ❌ FAIL: 50% load latency too high")
        failed += 1
    
    # Test 3: Latency under 90% CPU load
    print("\n[TEST 3/4] Latency under 90% CPU load...")
    simulator_90 = CPUStressSimulator(target_load_pct=90)
    simulator_90.start_stress(duration_sec=3.0, num_threads=4)
    time.sleep(0.5)  # Let stress stabilize
    
    load_90_measurements = []
    successes = 0
    for i in range(5):
        m = simulator_90.measure_operation_latency(
            lambda: mock_pqc_sign(f"load90-{i}"),
            f"PQC-sign-90pct-{i}",
            cpu_load_pct=90.0
        )
        load_90_measurements.append(m.latency_ms)
        if m.success:
            successes += 1
    
    simulator_90.stop_stress()
    avg_90 = sum(load_90_measurements) / len(load_90_measurements)
    stats["stress_latency_ms"] = load_90_measurements
    print(f"   90% load avg latency: {avg_90:.2f}ms (baseline: {avg_baseline:.2f}ms)")
    print(f"   Success rate: {successes}/{len(load_90_measurements)}")
    
    # At 90% load, operations should still complete
    if successes == len(load_90_measurements):
        print(f"   ✅ PASS: All operations completed under 90% load")
        passed += 1
    else:
        print(f"   ❌ FAIL: Some operations failed under 90% load")
        failed += 1
    
    # Test 4: Jitter analysis
    print("\n[TEST 4/4] Jitter variance analysis...")
    all_measurements = baseline_measurements + load_90_measurements
    mean_latency = sum(all_measurements) / len(all_measurements)
    variance = sum((x - mean_latency) ** 2 for x in all_measurements) / len(all_measurements)
    std_dev = variance ** 0.5
    stats["jitter_variance"] = variance
    
    # Calculate coefficient of variation (CV)
    cv = (std_dev / mean_latency) * 100 if mean_latency > 0 else 0
    print(f"   Mean latency: {mean_latency:.2f}ms")
    print(f"   Std deviation: {std_dev:.2f}ms")
    print(f"   Coefficient of variation: {cv:.2f}%")
    
    # CV under 200% is acceptable for stress conditions
    if cv < 200:
        print(f"   ✅ PASS: Jitter variance acceptable")
        passed += 1
    else:
        print(f"   ❌ FAIL: Jitter variance too high")
        failed += 1
    
    stats["success_rate_pct"] = (successes / len(load_90_measurements)) * 100
    
    print("\n" + "-"*60)
    print(f"FORGE (GID-04) RESULTS: {passed} passed, {failed} failed")
    print("-"*60)
    
    return passed, failed, stats


# ═══════════════════════════════════════════════════════════════════════════════
# SAM (GID-06): ADVERSARIAL ISO 20022 INJECTION TESTING
# ═══════════════════════════════════════════════════════════════════════════════

class ISO20022ValidationError(Exception):
    """Raised when ISO 20022 message validation fails."""
    pass


class AdversarialISO20022Validator:
    """
    Strict ISO 20022 message validator with adversarial testing.
    
    SAM (GID-06) Task: Simulate malformed ISO 20022 messages and verify fail-closed.
    
    Tests for:
    - XML injection attacks
    - Invalid element structure
    - Missing required fields
    - Malformed amounts
    - BIC/IBAN format violations
    - XXE (XML External Entity) attacks
    - Unicode smuggling
    """
    
    def __init__(self):
        """Initialize validator."""
        self.validation_count = 0
        self.rejection_count = 0
        
    def validate_pacs008(self, xml_content: str) -> Dict[str, Any]:
        """
        Validate pacs.008 message with strict fail-closed behavior.
        
        Args:
            xml_content: Raw XML string
            
        Returns:
            Parsed message dict if valid
            
        Raises:
            ISO20022ValidationError: If validation fails (fail-closed)
        """
        self.validation_count += 1
        
        # SAM GID-06: Check for XXE attack patterns
        xxe_patterns = [
            "<!DOCTYPE",
            "<!ENTITY",
            "SYSTEM",
            "file://",
            "http://",
            "https://",
            "<!\\[CDATA\\[",
        ]
        for pattern in xxe_patterns:
            if pattern.lower() in xml_content.lower():
                self.rejection_count += 1
                raise ISO20022ValidationError(
                    f"XXE_ATTACK_DETECTED: Pattern '{pattern}' found in message. "
                    f"FAIL-CLOSED: Message rejected."
                )
        
        # SAM GID-06: Check for Unicode smuggling
        dangerous_unicode = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # BOM
            "\u2028",  # Line separator
            "\u2029",  # Paragraph separator
        ]
        for char in dangerous_unicode:
            if char in xml_content:
                self.rejection_count += 1
                raise ISO20022ValidationError(
                    f"UNICODE_SMUGGLING_DETECTED: Hidden character U+{ord(char):04X} found. "
                    f"FAIL-CLOSED: Message rejected."
                )
        
        # SAM GID-06: Parse XML with strict mode
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            self.rejection_count += 1
            raise ISO20022ValidationError(
                f"MALFORMED_XML: Parse error at {e.position}. "
                f"FAIL-CLOSED: Message rejected."
            )
        
        # SAM GID-06: Check for SQL injection in text content
        sql_patterns = [
            "SELECT", "INSERT", "UPDATE", "DELETE", "DROP",
            "UNION", "--", ";", "/*", "*/", "xp_", "exec("
        ]
        all_text = " ".join(root.itertext())
        for pattern in sql_patterns:
            if pattern.upper() in all_text.upper():
                self.rejection_count += 1
                raise ISO20022ValidationError(
                    f"SQL_INJECTION_DETECTED: Pattern '{pattern}' found in text content. "
                    f"FAIL-CLOSED: Message rejected."
                )
        
        # SAM GID-06: Validate required pacs.008 structure
        required_elements = ["GrpHdr", "CdtTrfTxInf"]
        for elem_name in required_elements:
            if root.find(f".//{elem_name}") is None:
                # Try with namespace
                for child in root.iter():
                    if child.tag.endswith(elem_name):
                        break
                else:
                    self.rejection_count += 1
                    raise ISO20022ValidationError(
                        f"MISSING_REQUIRED_ELEMENT: {elem_name} not found. "
                        f"FAIL-CLOSED: Message rejected."
                    )
        
        # Extract and validate amount if present
        for amt_elem in root.iter():
            if amt_elem.tag.endswith("InstdAmt") or amt_elem.tag.endswith("Amt"):
                try:
                    amt_text = amt_elem.text or ""
                    if amt_text:
                        amount = Decimal(amt_text)
                        if amount < 0:
                            self.rejection_count += 1
                            raise ISO20022ValidationError(
                                f"NEGATIVE_AMOUNT_DETECTED: {amount}. "
                                f"FAIL-CLOSED: Message rejected."
                            )
                except InvalidOperation:
                    self.rejection_count += 1
                    raise ISO20022ValidationError(
                        f"INVALID_AMOUNT_FORMAT: '{amt_elem.text}'. "
                        f"FAIL-CLOSED: Message rejected."
                    )
        
        return {"status": "VALID", "root_tag": root.tag}
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return {
            "total_validations": self.validation_count,
            "rejections": self.rejection_count,
            "rejection_rate_pct": (
                (self.rejection_count / self.validation_count) * 100
                if self.validation_count > 0 else 0
            )
        }


def run_adversarial_injection_tests() -> Tuple[int, int, List[str]]:
    """
    SAM (GID-06): Run adversarial ISO 20022 injection tests.
    
    Tests:
    1. Valid pacs.008 message (should pass)
    2. XXE attack (should fail-closed)
    3. SQL injection in text (should fail-closed)
    4. Missing required elements (should fail-closed)
    5. Negative amount (should fail-closed)
    6. Unicode smuggling (should fail-closed)
    7. Malformed XML (should fail-closed)
    
    Returns:
        Tuple of (passed, failed, rejection_details)
    """
    print("\n" + "="*60)
    print("SAM (GID-06): ADVERSARIAL ISO 20022 INJECTION TESTS")
    print("="*60 + "\n")
    
    validator = AdversarialISO20022Validator()
    passed = 0
    failed = 0
    rejections = []
    
    # Test 1: Valid pacs.008 message
    valid_pacs008 = '''<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG001</MsgId>
                <CreDtTm>2026-01-27T14:00:00Z</CreDtTm>
            </GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <InstrId>INSTR001</InstrId>
                </PmtId>
                <InstdAmt Ccy="USD">1000.00</InstdAmt>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>'''
    
    print("[TEST 1/7] Valid pacs.008 message...")
    try:
        result = validator.validate_pacs008(valid_pacs008)
        print(f"   ✅ PASS: Valid message accepted → {result['status']}")
        passed += 1
    except ISO20022ValidationError as e:
        print(f"   ❌ FAIL: Valid message rejected → {e}")
        failed += 1
    
    # Test 2: XXE attack
    xxe_attack = '''<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <Document>
        <GrpHdr>&xxe;</GrpHdr>
        <CdtTrfTxInf></CdtTrfTxInf>
    </Document>'''
    
    print("\n[TEST 2/7] XXE attack injection...")
    try:
        validator.validate_pacs008(xxe_attack)
        print(f"   ❌ FAIL: XXE attack not detected")
        failed += 1
    except ISO20022ValidationError as e:
        print(f"   ✅ PASS: XXE attack blocked → {str(e)[:60]}...")
        passed += 1
        rejections.append("XXE_ATTACK: Blocked")
    
    # Test 3: SQL injection
    sql_injection = '''<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG001; DROP TABLE users; --</MsgId>
            </GrpHdr>
            <CdtTrfTxInf></CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>'''
    
    print("\n[TEST 3/7] SQL injection in text content...")
    try:
        validator.validate_pacs008(sql_injection)
        print(f"   ❌ FAIL: SQL injection not detected")
        failed += 1
    except ISO20022ValidationError as e:
        print(f"   ✅ PASS: SQL injection blocked → {str(e)[:60]}...")
        passed += 1
        rejections.append("SQL_INJECTION: Blocked")
    
    # Test 4: Missing required elements
    missing_elements = '''<?xml version="1.0" encoding="UTF-8"?>
    <Document>
        <EmptyMessage></EmptyMessage>
    </Document>'''
    
    print("\n[TEST 4/7] Missing required elements...")
    try:
        validator.validate_pacs008(missing_elements)
        print(f"   ❌ FAIL: Missing elements not detected")
        failed += 1
    except ISO20022ValidationError as e:
        print(f"   ✅ PASS: Missing elements caught → {str(e)[:60]}...")
        passed += 1
        rejections.append("MISSING_ELEMENT: Blocked")
    
    # Test 5: Negative amount
    negative_amount = '''<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr><MsgId>MSG001</MsgId></GrpHdr>
            <CdtTrfTxInf>
                <InstdAmt Ccy="USD">-500.00</InstdAmt>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>'''
    
    print("\n[TEST 5/7] Negative amount in message...")
    try:
        validator.validate_pacs008(negative_amount)
        print(f"   ❌ FAIL: Negative amount not detected")
        failed += 1
    except ISO20022ValidationError as e:
        print(f"   ✅ PASS: Negative amount blocked → {str(e)[:60]}...")
        passed += 1
        rejections.append("NEGATIVE_AMOUNT: Blocked")
    
    # Test 6: Unicode smuggling
    unicode_smuggle = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr><MsgId>MSG{chr(0x200b)}001</MsgId></GrpHdr>
            <CdtTrfTxInf></CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>'''
    
    print("\n[TEST 6/7] Unicode smuggling (zero-width chars)...")
    try:
        validator.validate_pacs008(unicode_smuggle)
        print(f"   ❌ FAIL: Unicode smuggling not detected")
        failed += 1
    except ISO20022ValidationError as e:
        print(f"   ✅ PASS: Unicode smuggling blocked → {str(e)[:60]}...")
        passed += 1
        rejections.append("UNICODE_SMUGGLING: Blocked")
    
    # Test 7: Malformed XML
    malformed_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <Document>
        <GrpHdr>
            <MsgId>Unclosed tag
        </GrpHdr>
    </Document>'''
    
    print("\n[TEST 7/7] Malformed XML structure...")
    try:
        validator.validate_pacs008(malformed_xml)
        print(f"   ❌ FAIL: Malformed XML not detected")
        failed += 1
    except ISO20022ValidationError as e:
        print(f"   ✅ PASS: Malformed XML caught → {str(e)[:60]}...")
        passed += 1
        rejections.append("MALFORMED_XML: Blocked")
    
    print("\n" + "-"*60)
    print(f"SAM (GID-06) RESULTS: {passed} passed, {failed} failed")
    print(f"Validation stats: {validator.get_stats()}")
    print("-"*60)
    
    return passed, failed, rejections


# ═══════════════════════════════════════════════════════════════════════════════
# SONNY (GID-02): UI STRESS VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StressLoadMetrics:
    """Real-time stress load metrics for UI visualization."""
    cpu_load_pct: float = 0.0
    memory_load_pct: float = 0.0
    active_operations: int = 0
    latency_avg_ms: float = 0.0
    error_rate_pct: float = 0.0
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class StressVisualizationBridge:
    """
    Bridge between stress test metrics and UI visualization.
    
    SONNY (GID-02) Task: Ensure kinetic mesh reflects stress load in real-time.
    
    Maps stress metrics to UI node properties:
    - CPU load → node color (green → yellow → red)
    - Latency → node size (larger = slower)
    - Error rate → node opacity (transparent = errors)
    - Operations → edge thickness
    """
    
    def __init__(self):
        """Initialize visualization bridge."""
        self.metrics_history: List[StressLoadMetrics] = []
        self.max_history = 100
        
    def record_metrics(self, metrics: StressLoadMetrics):
        """Record stress metrics for visualization."""
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
    
    def compute_node_color(self, cpu_load_pct: float) -> Tuple[int, int, int]:
        """
        Compute node color based on CPU load.
        
        Green (0%) → Yellow (50%) → Red (100%)
        
        Args:
            cpu_load_pct: CPU load percentage (0-100)
            
        Returns:
            RGB tuple (0-255 each)
        """
        load = min(max(cpu_load_pct, 0), 100) / 100.0
        
        if load < 0.5:
            # Green to Yellow
            r = int(255 * (load * 2))
            g = 255
            b = 0
        else:
            # Yellow to Red
            r = 255
            g = int(255 * (1 - (load - 0.5) * 2))
            b = 0
        
        return (r, g, b)
    
    def compute_node_size(self, latency_ms: float, base_size: float = 10.0) -> float:
        """
        Compute node size based on latency.
        
        Larger nodes = higher latency (slower response).
        
        Args:
            latency_ms: Operation latency in ms
            base_size: Base node size
            
        Returns:
            Scaled node size
        """
        # Scale: 10ms = 1x, 100ms = 2x, 1000ms = 3x
        scale = 1.0 + (min(latency_ms, 1000) / 500.0)
        return base_size * scale
    
    def compute_node_opacity(self, error_rate_pct: float) -> float:
        """
        Compute node opacity based on error rate.
        
        100% opacity = no errors, 30% opacity = 100% errors.
        
        Args:
            error_rate_pct: Error rate percentage (0-100)
            
        Returns:
            Opacity value (0.3-1.0)
        """
        return max(0.3, 1.0 - (error_rate_pct / 100.0) * 0.7)
    
    def generate_mesh_update(self, metrics: StressLoadMetrics) -> Dict[str, Any]:
        """
        Generate kinetic mesh update payload from stress metrics.
        
        Args:
            metrics: Current stress metrics
            
        Returns:
            Mesh update payload for UI
        """
        color = self.compute_node_color(metrics.cpu_load_pct)
        size = self.compute_node_size(metrics.latency_avg_ms)
        opacity = self.compute_node_opacity(metrics.error_rate_pct)
        
        return {
            "timestamp_ms": metrics.timestamp_ms,
            "stress_node": {
                "color_rgb": color,
                "color_hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                "size": size,
                "opacity": opacity,
                "pulse_rate": 1.0 + (metrics.cpu_load_pct / 50.0)  # Faster pulse = higher load
            },
            "edge_updates": {
                "thickness": 1.0 + (metrics.active_operations / 10.0),
                "flow_speed": 1.0 + (metrics.latency_avg_ms / 100.0)
            },
            "metrics_overlay": {
                "cpu_load": f"{metrics.cpu_load_pct:.1f}%",
                "latency": f"{metrics.latency_avg_ms:.1f}ms",
                "errors": f"{metrics.error_rate_pct:.1f}%",
                "ops": metrics.active_operations
            }
        }


def run_ui_stress_visualization_tests() -> Tuple[int, int, Dict[str, Any]]:
    """
    SONNY (GID-02): Run UI stress visualization tests.
    
    Tests:
    1. Color gradient computation (CPU load → color)
    2. Node size scaling (latency → size)
    3. Opacity computation (error rate → opacity)
    4. Mesh update generation
    5. Real-time metrics streaming
    
    Returns:
        Tuple of (passed, failed, visualization_data)
    """
    print("\n" + "="*60)
    print("SONNY (GID-02): UI STRESS VISUALIZATION TESTS")
    print("="*60 + "\n")
    
    bridge = StressVisualizationBridge()
    passed = 0
    failed = 0
    viz_data = {"color_samples": [], "size_samples": [], "mesh_updates": []}
    
    # Test 1: Color gradient computation
    print("[TEST 1/5] CPU load → color gradient...")
    color_tests = [
        (0, (0, 255, 0), "green"),     # 0% = pure green
        (50, (255, 255, 0), "yellow"), # 50% = yellow
        (100, (255, 0, 0), "red"),     # 100% = pure red
        (25, (127, 255, 0), "lime"),   # 25% = lime
        (75, (255, 127, 0), "orange"), # 75% = orange
    ]
    
    color_pass = True
    for load, expected, name in color_tests:
        actual = bridge.compute_node_color(load)
        # Allow tolerance of 5 per channel
        match = all(abs(a - e) <= 5 for a, e in zip(actual, expected))
        viz_data["color_samples"].append({"load": load, "color": actual, "name": name})
        if not match:
            print(f"   ⚠️ {load}%: Expected {expected}, got {actual}")
            color_pass = False
    
    if color_pass:
        print(f"   ✅ PASS: Color gradient correct (green → yellow → red)")
        passed += 1
    else:
        print(f"   ❌ FAIL: Color gradient mismatch")
        failed += 1
    
    # Test 2: Node size scaling
    print("\n[TEST 2/5] Latency → node size scaling...")
    size_tests = [
        (10, 10.0, 12.0),   # Low latency = near base size
        (100, 10.0, 12.0),  # 100ms = 1.2x
        (500, 10.0, 20.0),  # 500ms = 2x
        (1000, 10.0, 30.0), # 1000ms = 3x (max)
    ]
    
    size_pass = True
    for latency, base, max_expected in size_tests:
        actual = bridge.compute_node_size(latency, base)
        viz_data["size_samples"].append({"latency": latency, "size": actual})
        if actual < base or actual > max_expected + 5:
            print(f"   ⚠️ {latency}ms: Size {actual} outside expected range")
            size_pass = False
    
    if size_pass:
        print(f"   ✅ PASS: Size scaling correct (higher latency = larger nodes)")
        passed += 1
    else:
        print(f"   ❌ FAIL: Size scaling incorrect")
        failed += 1
    
    # Test 3: Opacity computation
    print("\n[TEST 3/5] Error rate → opacity...")
    opacity_tests = [
        (0, 1.0),    # No errors = full opacity
        (50, 0.65),  # 50% errors = partial opacity
        (100, 0.3),  # 100% errors = minimum opacity
    ]
    
    opacity_pass = True
    for error_rate, expected in opacity_tests:
        actual = bridge.compute_node_opacity(error_rate)
        if abs(actual - expected) > 0.05:
            print(f"   ⚠️ {error_rate}% errors: Expected {expected}, got {actual}")
            opacity_pass = False
    
    if opacity_pass:
        print(f"   ✅ PASS: Opacity computation correct (more errors = more transparent)")
        passed += 1
    else:
        print(f"   ❌ FAIL: Opacity computation incorrect")
        failed += 1
    
    # Test 4: Mesh update generation
    print("\n[TEST 4/5] Mesh update payload generation...")
    test_metrics = StressLoadMetrics(
        cpu_load_pct=75.0,
        memory_load_pct=60.0,
        active_operations=15,
        latency_avg_ms=120.0,
        error_rate_pct=5.0
    )
    
    mesh_update = bridge.generate_mesh_update(test_metrics)
    viz_data["mesh_updates"].append(mesh_update)
    
    required_keys = ["stress_node", "edge_updates", "metrics_overlay"]
    if all(k in mesh_update for k in required_keys):
        print(f"   ✅ PASS: Mesh update contains all required sections")
        print(f"      Node color: {mesh_update['stress_node']['color_hex']}")
        print(f"      Node size: {mesh_update['stress_node']['size']:.2f}")
        print(f"      Pulse rate: {mesh_update['stress_node']['pulse_rate']:.2f}x")
        passed += 1
    else:
        print(f"   ❌ FAIL: Mesh update missing required sections")
        failed += 1
    
    # Test 5: Real-time metrics streaming
    print("\n[TEST 5/5] Real-time metrics streaming simulation...")
    stream_samples = []
    
    for i in range(5):
        metrics = StressLoadMetrics(
            cpu_load_pct=20 * i,
            memory_load_pct=15 * i,
            active_operations=i * 3,
            latency_avg_ms=10 + i * 20,
            error_rate_pct=i * 2
        )
        bridge.record_metrics(metrics)
        update = bridge.generate_mesh_update(metrics)
        stream_samples.append(update)
        print(f"   Frame {i+1}: CPU {metrics.cpu_load_pct}% → "
              f"Color {update['stress_node']['color_hex']}")
    
    if len(bridge.metrics_history) == 5:
        print(f"   ✅ PASS: Metrics streaming working ({len(bridge.metrics_history)} samples)")
        passed += 1
    else:
        print(f"   ❌ FAIL: Metrics streaming failed")
        failed += 1
    
    print("\n" + "-"*60)
    print(f"SONNY (GID-02) RESULTS: {passed} passed, {failed} failed")
    print("-"*60)
    
    return passed, failed, viz_data


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN STRESS TEST ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def run_all_stress_tests() -> Dict[str, Any]:
    """
    Run complete stress test suite.
    
    Executes all 4 swarm agent tasks:
    1. CODY (GID-01): Negative amount hardening
    2. FORGE (GID-04): Latency jitter simulation
    3. SAM (GID-06): Adversarial ISO 20022 injection
    4. SONNY (GID-02): UI stress visualization
    
    Returns:
        Complete test results with WRAP submissions
    """
    print("\n" + "═"*70)
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║    PAC-SANDBOX-STRESS-001: ADVERSARIAL HARDENING STRESS TEST      ║")
    print("║                                                                    ║")
    print("║    EXECUTION ID: CB-SANDBOX-STRESS-2026-01-27                     ║")
    print("║    MODE: WAR_ROOM_STRESS_TEST_MODE                                 ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print("═"*70 + "\n")
    
    results = {
        "execution_id": "CB-SANDBOX-STRESS-2026-01-27",
        "timestamp": int(time.time() * 1000),
        "agents": {},
        "totals": {"passed": 0, "failed": 0},
        "governance_hash": ""
    }
    
    # CODY (GID-01)
    cody_passed, cody_failed, cody_failures = run_negative_amount_tests()
    results["agents"]["CODY_GID01"] = {
        "task": "NEGATIVE_AMOUNT_HARDENING",
        "passed": cody_passed,
        "failed": cody_failed,
        "failures": cody_failures,
        "status": "PASS" if cody_failed == 0 else "FAIL"
    }
    results["totals"]["passed"] += cody_passed
    results["totals"]["failed"] += cody_failed
    
    # FORGE (GID-04)
    forge_passed, forge_failed, forge_stats = run_latency_jitter_tests()
    results["agents"]["FORGE_GID04"] = {
        "task": "LATENCY_JITTER_SIMULATION",
        "passed": forge_passed,
        "failed": forge_failed,
        "stats": forge_stats,
        "status": "PASS" if forge_failed == 0 else "FAIL"
    }
    results["totals"]["passed"] += forge_passed
    results["totals"]["failed"] += forge_failed
    
    # SAM (GID-06)
    sam_passed, sam_failed, sam_rejections = run_adversarial_injection_tests()
    results["agents"]["SAM_GID06"] = {
        "task": "ADVERSARIAL_INJECTION_TEST",
        "passed": sam_passed,
        "failed": sam_failed,
        "rejections": sam_rejections,
        "status": "PASS" if sam_failed == 0 else "FAIL"
    }
    results["totals"]["passed"] += sam_passed
    results["totals"]["failed"] += sam_failed
    
    # SONNY (GID-02)
    sonny_passed, sonny_failed, sonny_viz = run_ui_stress_visualization_tests()
    results["agents"]["SONNY_GID02"] = {
        "task": "UI_STRESS_VISUALIZATION",
        "passed": sonny_passed,
        "failed": sonny_failed,
        "visualization_data": sonny_viz,
        "status": "PASS" if sonny_failed == 0 else "FAIL"
    }
    results["totals"]["passed"] += sonny_passed
    results["totals"]["failed"] += sonny_failed
    
    # Compute governance hash
    results_str = json.dumps(results["totals"], sort_keys=True)
    results["governance_hash"] = hashlib.sha3_256(results_str.encode()).hexdigest()[:16].upper()
    
    # Print summary
    print("\n" + "═"*70)
    print("STRESS TEST SUMMARY")
    print("═"*70)
    
    total_passed = results["totals"]["passed"]
    total_failed = results["totals"]["failed"]
    total_tests = total_passed + total_failed
    
    for agent_name, agent_data in results["agents"].items():
        status_icon = "✅" if agent_data["status"] == "PASS" else "❌"
        print(f"{status_icon} {agent_name}: {agent_data['task']} → {agent_data['status']}")
        print(f"   Tests: {agent_data['passed']} passed, {agent_data['failed']} failed")
    
    print("\n" + "-"*70)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.1f}%)")
    print(f"GOVERNANCE HASH: {results['governance_hash']}")
    
    if total_failed == 0:
        print("\n🎯 OUTCOME: HARDENED_SANDBOX_WITH_ZERO_NEGATIVE_DRIFT ✅")
    else:
        print(f"\n⚠️ OUTCOME: SANDBOX_HARDENING_INCOMPLETE ({total_failed} failures)")
    
    print("═"*70 + "\n")
    
    return results


if __name__ == "__main__":
    results = run_all_stress_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results["totals"]["failed"] == 0 else 1)
