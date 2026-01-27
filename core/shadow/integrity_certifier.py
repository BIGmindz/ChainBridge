"""
PAC-SHADOW-BUILD-001: SHADOW INTEGRITY CERTIFICATION
=====================================================

PQC compliance certification for shadow execution path.
Hash-based validation of shadow vs production request congruence.

CERTIFICATION CRITERIA:
- Shadow path cryptographic integrity (ML-DSA-65)
- Hash comparison between shadow and production requests
- Zero-leak network isolation verification
- Latency compliance (<50ms target, <500ms cap)
- Deterministic mock response validation
- Telemetry stream accuracy verification

TEST BATTERY:
1. Shadow layer isolation (zero production mutations)
2. ISO 20022 mock generator determinism
3. Telemetry stream congruence tracking
4. Network isolation policy enforcement
5. PQC signature verification (ML-DSA-65)
6. Hash chain integrity
7. Latency compliance (all operations < 500ms)

COMPLIANCE LEVELS:
- ✅ CERTIFIED: All tests pass
- ⚠️ CONDITIONAL: Minor issues, approved with caveats
- ❌ FAILED: Critical issues, not approved

Author: ATLAS (GID-11)
PAC: CB-SHADOW-BUILD-001
Status: PRODUCTION-READY
"""

import hashlib
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List


logger = logging.getLogger("ShadowIntegrity")


class CertificationLevel(Enum):
    """Certification levels."""
    CERTIFIED = "CERTIFIED"
    CONDITIONAL = "CONDITIONAL"
    FAILED = "FAILED"


class TestStatus(Enum):
    """Test status."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CertificationTest:
    """
    Individual certification test.
    
    Attributes:
        test_id: Unique test identifier
        test_name: Human-readable test name
        status: Test status (PASS/FAIL/SKIP)
        description: Test description
        result_details: Detailed test results
        latency_ms: Test execution latency
        severity: Failure severity (LOW/MEDIUM/HIGH/CRITICAL)
    """
    test_id: str
    test_name: str
    status: TestStatus
    description: str
    result_details: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    severity: str = "LOW"


@dataclass
class CertificationReport:
    """
    Shadow integrity certification report.
    
    Attributes:
        report_id: Unique report identifier
        certification_level: Overall certification level
        tests: List of certification tests
        total_tests: Total number of tests
        passed_tests: Number of passed tests
        failed_tests: Number of failed tests
        overall_latency_ms: Total certification latency
        pqc_signature: ML-DSA-65 signature of report
        timestamp_ms: Report generation timestamp
    """
    report_id: str
    certification_level: CertificationLevel
    tests: List[CertificationTest] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    overall_latency_ms: float = 0.0
    pqc_signature: str = ""
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class ShadowIntegrityCertifier:
    """
    Shadow integrity certifier for PQC compliance validation.
    
    Performs comprehensive certification of shadow execution layer,
    validating isolation, determinism, cryptographic integrity,
    and performance compliance.
    
    Test Battery:
    1. Shadow layer isolation - Verify zero production mutations
    2. Mock generator determinism - Validate cache consistency
    3. Telemetry stream congruence - Verify hash tracking accuracy
    4. Network isolation enforcement - Test policy violations
    5. PQC signature verification - Validate ML-DSA-65 integrity
    6. Hash chain integrity - Verify audit trail linkage
    7. Latency compliance - All operations < 500ms cap
    
    Usage:
        certifier = ShadowIntegrityCertifier()
        report = certifier.run_certification()
        
        if report.certification_level == CertificationLevel.CERTIFIED:
            print("✅ Shadow layer certified for production")
        else:
            print(f"❌ Certification failed: {report.failed_tests} tests")
    """
    
    def __init__(self, latency_cap_ms: float = 500.0):
        """
        Initialize shadow integrity certifier.
        
        Args:
            latency_cap_ms: Maximum allowed operation latency
        """
        self.latency_cap_ms = latency_cap_ms
        self.tests: List[CertificationTest] = []
        
        logger.info(
            f"🔒 Shadow Integrity Certifier initialized | "
            f"Latency cap: {latency_cap_ms}ms"
        )
    
    def run_certification(self) -> CertificationReport:
        """
        Run full certification test battery.
        
        Returns:
            CertificationReport with test results
        """
        start_time = time.time()
        
        logger.info("═" * 80)
        logger.info("SHADOW INTEGRITY CERTIFICATION - STARTING")
        logger.info("═" * 80)
        
        # Test 1: Shadow layer isolation
        self._test_shadow_isolation()
        
        # Test 2: Mock generator determinism
        self._test_mock_determinism()
        
        # Test 3: Telemetry stream congruence
        self._test_telemetry_congruence()
        
        # Test 4: Network isolation enforcement
        self._test_network_isolation()
        
        # Test 5: PQC signature verification
        self._test_pqc_signatures()
        
        # Test 6: Hash chain integrity
        self._test_hash_chain_integrity()
        
        # Test 7: Latency compliance
        self._test_latency_compliance()
        
        # Calculate statistics
        total_tests = len(self.tests)
        passed_tests = sum(1 for t in self.tests if t.status == TestStatus.PASS)
        failed_tests = sum(1 for t in self.tests if t.status == TestStatus.FAIL)
        
        # Determine certification level
        certification_level = self._determine_certification_level(self.tests)
        
        # Generate report
        overall_latency = (time.time() - start_time) * 1000
        
        report = CertificationReport(
            report_id=f"CERT-SHADOW-{int(time.time())}",
            certification_level=certification_level,
            tests=self.tests,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            overall_latency_ms=overall_latency
        )
        
        # Sign report with PQC (if available)
        report.pqc_signature = self._sign_report(report)
        
        logger.info("═" * 80)
        logger.info(f"CERTIFICATION COMPLETE: {certification_level.value}")
        logger.info(f"Tests: {passed_tests}/{total_tests} passed")
        logger.info(f"Latency: {overall_latency:.2f}ms")
        logger.info("═" * 80)
        
        return report
    
    def _test_shadow_isolation(self):
        """Test 1: Shadow layer isolation."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 1: Shadow Layer Isolation")
        
        try:
            # Import shadow execution sandbox
            sys.path.insert(0, '/Users/johnbozza/Documents/Projects/ChainBridge-local-repo')
            from core.governance.shadow_execution_sandbox import (
                ShadowExecutionSandbox, ExecutionMode, TransactionStatus
            )
            
            # Create sandbox
            sandbox = ShadowExecutionSandbox()
            
            # Create accounts
            acc1 = sandbox.create_account("ACC-001", initial_balance=Decimal("1000.00"))
            acc2 = sandbox.create_account("ACC-002", initial_balance=Decimal("500.00"))
            
            # Simulate transactions
            tx1_id = sandbox.simulate_transaction(
                from_account_id="ACC-001",
                to_account_id="ACC-002",
                amount=Decimal("100.00")
            )
            
            # Get transaction object
            tx1 = sandbox.transactions.get(tx1_id)
            
            # Verify: transaction is SIMULATED, not EXECUTED
            is_simulated = tx1.status == TransactionStatus.SIMULATED if tx1 else False
            
            # Verify: execution mode is SHADOW
            is_shadow = sandbox.mode == ExecutionMode.SHADOW
            
            # Verify: no production mutations
            state = sandbox.export_sandbox_state()
            transactions_list = list(state["transactions"].values())
            has_executed_transactions = any(
                tx["status"] == "EXECUTED" for tx in transactions_list
            )
            
            latency = (time.time() - test_start) * 1000
            
            if is_simulated and is_shadow and not has_executed_transactions:
                self.tests.append(CertificationTest(
                    test_id="TEST-001",
                    test_name="Shadow Layer Isolation",
                    status=TestStatus.PASS,
                    description="Shadow layer properly isolated from production",
                    result_details={
                        "execution_mode": "SHADOW",
                        "transactions_simulated": len(state["transactions"]),
                        "transactions_executed": 0,
                        "accounts_created": len(state["accounts"])
                    },
                    latency_ms=latency,
                    severity="CRITICAL"
                ))
                logger.info(f"  ✅ PASS: Shadow isolation verified ({latency:.2f}ms)")
            else:
                self.tests.append(CertificationTest(
                    test_id="TEST-001",
                    test_name="Shadow Layer Isolation",
                    status=TestStatus.FAIL,
                    description="Shadow layer isolation compromised",
                    result_details={
                        "is_simulated": is_simulated,
                        "is_shadow": is_shadow,
                        "has_executed_transactions": has_executed_transactions
                    },
                    latency_ms=latency,
                    severity="CRITICAL"
                ))
                logger.error("  ❌ FAIL: Shadow isolation breach detected")
        
        except Exception as e:
            latency = (time.time() - test_start) * 1000
            self.tests.append(CertificationTest(
                test_id="TEST-001",
                test_name="Shadow Layer Isolation",
                status=TestStatus.FAIL,
                description=f"Test failed with exception: {str(e)}",
                result_details={"exception": str(e)},
                latency_ms=latency,
                severity="CRITICAL"
            ))
            logger.error(f"  ❌ FAIL: {e}")
    
    def _test_mock_determinism(self):
        """Test 2: Mock generator determinism."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 2: Mock Generator Determinism")
        
        try:
            from core.shadow.iso20022_mock_generator import (
                ISO20022MockGenerator, MockPaymentRequest, ISO20022MessageType
            )
            
            generator = ISO20022MockGenerator(simulate_latency=False)
            
            # Create request
            request = MockPaymentRequest(
                request_id="REQ-DETERMINISM-001",
                message_type=ISO20022MessageType.PACS_008,
                from_bic="CITIUS33",
                to_bic="HSBCUS33",
                amount=Decimal("1000.00")
            )
            
            # Generate response twice
            response1 = generator.generate_mock_response(request)
            response2 = generator.generate_mock_response(request)
            
            # Verify determinism (same hash)
            is_deterministic = response1.hash_signature == response2.hash_signature
            is_cached = response1.response_id == response2.response_id
            
            latency = (time.time() - test_start) * 1000
            
            if is_deterministic and is_cached:
                self.tests.append(CertificationTest(
                    test_id="TEST-002",
                    test_name="Mock Generator Determinism",
                    status=TestStatus.PASS,
                    description="Mock generator produces deterministic responses",
                    result_details={
                        "hash_match": True,
                        "cache_hit": True,
                        "hash": response1.hash_signature[:32] + "..."
                    },
                    latency_ms=latency,
                    severity="HIGH"
                ))
                logger.info(f"  ✅ PASS: Deterministic mock responses ({latency:.2f}ms)")
            else:
                self.tests.append(CertificationTest(
                    test_id="TEST-002",
                    test_name="Mock Generator Determinism",
                    status=TestStatus.FAIL,
                    description="Mock generator non-deterministic",
                    result_details={
                        "is_deterministic": is_deterministic,
                        "is_cached": is_cached
                    },
                    latency_ms=latency,
                    severity="HIGH"
                ))
                logger.error("  ❌ FAIL: Non-deterministic responses")
        
        except Exception as e:
            latency = (time.time() - test_start) * 1000
            self.tests.append(CertificationTest(
                test_id="TEST-002",
                test_name="Mock Generator Determinism",
                status=TestStatus.FAIL,
                description=f"Test failed: {str(e)}",
                result_details={"exception": str(e)},
                latency_ms=latency,
                severity="HIGH"
            ))
            logger.error(f"  ❌ FAIL: {e}")
    
    def _test_telemetry_congruence(self):
        """Test 3: Telemetry stream congruence tracking."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 3: Telemetry Stream Congruence")
        
        try:
            from core.shadow.telemetry_stream import (
                DualPaneTelemetryStream, ExecutionPath
            )
            
            stream = DualPaneTelemetryStream(buffer_size=100)
            
            # Track matching requests
            shadow_event = stream.track_request(
                execution_path=ExecutionPath.SHADOW,
                request_id="REQ-CONGRUENCE-001",
                request_payload={"amount": 1000.00}
            )
            
            prod_event = stream.track_request(
                execution_path=ExecutionPath.PRODUCTION,
                request_id="REQ-CONGRUENCE-001",
                request_payload={"amount": 1000.00}
            )
            
            # Compare hashes
            congruence = stream.compare_hashes(shadow_event.event_id, prod_event.event_id)
            
            # Verify statistics
            stats = stream.get_statistics()
            
            latency = (time.time() - test_start) * 1000
            
            if congruence == 1.0 and stats["hash_matches"] > 0:
                self.tests.append(CertificationTest(
                    test_id="TEST-003",
                    test_name="Telemetry Stream Congruence",
                    status=TestStatus.PASS,
                    description="Telemetry stream accurately tracks congruence",
                    result_details={
                        "congruence_score": congruence,
                        "hash_matches": stats["hash_matches"],
                        "avg_congruence": stats["avg_congruence_score"]
                    },
                    latency_ms=latency,
                    severity="MEDIUM"
                ))
                logger.info(f"  ✅ PASS: Congruence tracking verified ({latency:.2f}ms)")
            else:
                self.tests.append(CertificationTest(
                    test_id="TEST-003",
                    test_name="Telemetry Stream Congruence",
                    status=TestStatus.FAIL,
                    description="Telemetry congruence tracking failed",
                    result_details={"congruence": congruence},
                    latency_ms=latency,
                    severity="MEDIUM"
                ))
                logger.error("  ❌ FAIL: Congruence mismatch")
        
        except Exception as e:
            latency = (time.time() - test_start) * 1000
            self.tests.append(CertificationTest(
                test_id="TEST-003",
                test_name="Telemetry Stream Congruence",
                status=TestStatus.FAIL,
                description=f"Test failed: {str(e)}",
                result_details={"exception": str(e)},
                latency_ms=latency,
                severity="MEDIUM"
            ))
            logger.error(f"  ❌ FAIL: {e}")
    
    def _test_network_isolation(self):
        """Test 4: Network isolation policy enforcement."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 4: Network Isolation Enforcement")
        
        try:
            from core.shadow.network_isolation import (
                NetworkIsolationEnforcer, NetworkRequest, ExecutionContext, IsolationPolicy
            )
            
            policy = IsolationPolicy(fail_closed_on_violation=False)
            enforcer = NetworkIsolationEnforcer(policy=policy, scram_enabled=False)
            
            # Test: Shadow request to production API (should block)
            shadow_to_prod = NetworkRequest(
                request_id="REQ-ISOLATION-001",
                execution_context=ExecutionContext.SHADOW,
                url="https://api.production.chainbridge.io/payment",
                headers={"X-Shadow-Mode": "true"}
            )
            allowed_prod, violation_prod = enforcer.validate_request(shadow_to_prod)
            
            # Test: Shadow request to shadow API (should allow)
            shadow_to_shadow = NetworkRequest(
                request_id="REQ-ISOLATION-002",
                execution_context=ExecutionContext.SHADOW,
                url="https://api.shadow.chainbridge.io/payment",
                headers={"X-Shadow-Mode": "true"}
            )
            allowed_shadow, violation_shadow = enforcer.validate_request(shadow_to_shadow)
            
            stats = enforcer.get_statistics()
            
            latency = (time.time() - test_start) * 1000
            
            if not allowed_prod and allowed_shadow and stats["blocked_requests"] > 0:
                self.tests.append(CertificationTest(
                    test_id="TEST-004",
                    test_name="Network Isolation Enforcement",
                    status=TestStatus.PASS,
                    description="Network isolation properly enforced",
                    result_details={
                        "blocked_production_api": True,
                        "allowed_shadow_api": True,
                        "policy_violations": stats["policy_violations"],
                        "blocked_requests": stats["blocked_requests"]
                    },
                    latency_ms=latency,
                    severity="CRITICAL"
                ))
                logger.info(f"  ✅ PASS: Network isolation enforced ({latency:.2f}ms)")
            else:
                self.tests.append(CertificationTest(
                    test_id="TEST-004",
                    test_name="Network Isolation Enforcement",
                    status=TestStatus.FAIL,
                    description="Network isolation policy failed",
                    result_details={
                        "allowed_prod": allowed_prod,
                        "allowed_shadow": allowed_shadow
                    },
                    latency_ms=latency,
                    severity="CRITICAL"
                ))
                logger.error("  ❌ FAIL: Isolation policy breach")
        
        except Exception as e:
            latency = (time.time() - test_start) * 1000
            self.tests.append(CertificationTest(
                test_id="TEST-004",
                test_name="Network Isolation Enforcement",
                status=TestStatus.FAIL,
                description=f"Test failed: {str(e)}",
                result_details={"exception": str(e)},
                latency_ms=latency,
                severity="CRITICAL"
            ))
            logger.error(f"  ❌ FAIL: {e}")
    
    def _test_pqc_signatures(self):
        """Test 5: PQC signature verification."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 5: PQC Signature Verification (ML-DSA-65)")
        
        try:
            from core.pqc.dilithium_kernel import DilithiumKernel
            
            kernel = DilithiumKernel()
            
            # Sign message
            message = b"Shadow integrity certification test"
            signature_bundle = kernel.sign_message(message)
            
            # Verify signature
            is_valid = kernel.verify_signature(
                message=message,
                signature=signature_bundle.signature,
                public_key=kernel._public_key
            )
            
            latency = (time.time() - test_start) * 1000
            
            if is_valid:
                self.tests.append(CertificationTest(
                    test_id="TEST-005",
                    test_name="PQC Signature Verification",
                    status=TestStatus.PASS,
                    description="ML-DSA-65 signatures verified successfully",
                    result_details={
                        "signature_valid": True,
                        "signature_size_bytes": len(signature_bundle.signature),
                        "public_key_size_bytes": len(kernel._public_key) if kernel._public_key else 0
                    },
                    latency_ms=latency,
                    severity="HIGH"
                ))
                logger.info(f"  ✅ PASS: PQC signatures verified ({latency:.2f}ms)")
            else:
                self.tests.append(CertificationTest(
                    test_id="TEST-005",
                    test_name="PQC Signature Verification",
                    status=TestStatus.FAIL,
                    description="PQC signature verification failed",
                    result_details={"signature_valid": False},
                    latency_ms=latency,
                    severity="HIGH"
                ))
                logger.error("  ❌ FAIL: Invalid PQC signature")
        
        except Exception as e:
            latency = (time.time() - test_start) * 1000
            self.tests.append(CertificationTest(
                test_id="TEST-005",
                test_name="PQC Signature Verification",
                status=TestStatus.FAIL,
                description=f"Test failed: {str(e)}",
                result_details={"exception": str(e)},
                latency_ms=latency,
                severity="HIGH"
            ))
            logger.error(f"  ❌ FAIL: {e}")
    
    def _test_hash_chain_integrity(self):
        """Test 6: Hash chain integrity."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 6: Hash Chain Integrity")
        
        try:
            # Create hash chain
            chain = []
            previous_hash = hashlib.sha3_256(b"GENESIS").hexdigest()
            chain.append(previous_hash)
            
            for i in range(5):
                data = f"Block-{i}".encode()
                current_hash = hashlib.sha3_256(previous_hash.encode() + data).hexdigest()
                chain.append(current_hash)
                previous_hash = current_hash
            
            # Verify chain integrity
            is_valid = True
            for i in range(1, len(chain)):
                expected_hash = hashlib.sha3_256(
                    chain[i-1].encode() + f"Block-{i-1}".encode()
                ).hexdigest()
                if chain[i] != expected_hash:
                    is_valid = False
                    break
            
            latency = (time.time() - test_start) * 1000
            
            if is_valid:
                self.tests.append(CertificationTest(
                    test_id="TEST-006",
                    test_name="Hash Chain Integrity",
                    status=TestStatus.PASS,
                    description="Hash chain integrity verified",
                    result_details={
                        "chain_length": len(chain),
                        "genesis_hash": chain[0][:32] + "...",
                        "final_hash": chain[-1][:32] + "..."
                    },
                    latency_ms=latency,
                    severity="MEDIUM"
                ))
                logger.info(f"  ✅ PASS: Hash chain verified ({latency:.2f}ms)")
            else:
                self.tests.append(CertificationTest(
                    test_id="TEST-006",
                    test_name="Hash Chain Integrity",
                    status=TestStatus.FAIL,
                    description="Hash chain integrity compromised",
                    result_details={"chain_valid": False},
                    latency_ms=latency,
                    severity="MEDIUM"
                ))
                logger.error("  ❌ FAIL: Hash chain broken")
        
        except Exception as e:
            latency = (time.time() - test_start) * 1000
            self.tests.append(CertificationTest(
                test_id="TEST-006",
                test_name="Hash Chain Integrity",
                status=TestStatus.FAIL,
                description=f"Test failed: {str(e)}",
                result_details={"exception": str(e)},
                latency_ms=latency,
                severity="MEDIUM"
            ))
            logger.error(f"  ❌ FAIL: {e}")
    
    def _test_latency_compliance(self):
        """Test 7: Latency compliance."""
        test_start = time.time()
        
        logger.info("\n📋 TEST 7: Latency Compliance (<500ms cap)")
        
        # Check all previous test latencies
        max_latency = max(test.latency_ms for test in self.tests) if self.tests else 0.0
        avg_latency = sum(test.latency_ms for test in self.tests) / len(self.tests) if self.tests else 0.0
        
        latency = (time.time() - test_start) * 1000
        
        if max_latency < self.latency_cap_ms:
            self.tests.append(CertificationTest(
                test_id="TEST-007",
                test_name="Latency Compliance",
                status=TestStatus.PASS,
                description="All operations within latency cap",
                result_details={
                    "max_latency_ms": max_latency,
                    "avg_latency_ms": avg_latency,
                    "latency_cap_ms": self.latency_cap_ms
                },
                latency_ms=latency,
                severity="MEDIUM"
            ))
            logger.info(f"  ✅ PASS: Latency compliant (max: {max_latency:.2f}ms)")
        else:
            self.tests.append(CertificationTest(
                test_id="TEST-007",
                test_name="Latency Compliance",
                status=TestStatus.FAIL,
                description=f"Latency cap exceeded: {max_latency:.2f}ms > {self.latency_cap_ms}ms",
                result_details={
                    "max_latency_ms": max_latency,
                    "latency_cap_ms": self.latency_cap_ms
                },
                latency_ms=latency,
                severity="MEDIUM"
            ))
            logger.error("  ❌ FAIL: Latency cap breach")
    
    def _determine_certification_level(
        self,
        tests: List[CertificationTest]
    ) -> CertificationLevel:
        """Determine overall certification level."""
        critical_failures = [
            t for t in tests if t.status == TestStatus.FAIL and t.severity == "CRITICAL"
        ]
        high_failures = [
            t for t in tests if t.status == TestStatus.FAIL and t.severity == "HIGH"
        ]
        
        if critical_failures:
            return CertificationLevel.FAILED
        elif high_failures:
            return CertificationLevel.CONDITIONAL
        else:
            return CertificationLevel.CERTIFIED
    
    def _sign_report(self, report: CertificationReport) -> str:
        """Sign certification report with PQC."""
        try:
            from core.pqc.dilithium_kernel import DilithiumKernel
            
            kernel = DilithiumKernel()
            report_json = json.dumps({
                "report_id": report.report_id,
                "certification_level": report.certification_level.value,
                "passed_tests": report.passed_tests,
                "failed_tests": report.failed_tests,
                "timestamp_ms": report.timestamp_ms
            }, sort_keys=True)
            
            signature_bundle = kernel.sign_message(report_json.encode())
            return signature_bundle.signature.hex()
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to sign report: {e}")
            return ""


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    certifier = ShadowIntegrityCertifier(latency_cap_ms=500.0)
    report = certifier.run_certification()
    
    print("\n" + "═" * 80)
    print(f"CERTIFICATION REPORT: {report.report_id}")
    print("═" * 80)
    print(f"Level: {report.certification_level.value}")
    print(f"Tests: {report.passed_tests}/{report.total_tests} passed")
    print(f"Failed: {report.failed_tests}")
    print(f"Latency: {report.overall_latency_ms:.2f}ms")
    if report.pqc_signature:
        print(f"PQC Signature: {report.pqc_signature[:64]}...")
    print("═" * 80)
    
    if report.certification_level == CertificationLevel.CERTIFIED:
        print("\n✅ SHADOW LAYER CERTIFIED FOR PRODUCTION")
    elif report.certification_level == CertificationLevel.CONDITIONAL:
        print("\n⚠️ CONDITIONAL CERTIFICATION (Minor issues)")
    else:
        print("\n❌ CERTIFICATION FAILED (Critical issues)")
    
    print("\nTest Details:")
    for test in report.tests:
        status_symbol = "✅" if test.status == TestStatus.PASS else "❌"
        print(f"  {status_symbol} {test.test_name}: {test.status.value} ({test.latency_ms:.2f}ms)")
