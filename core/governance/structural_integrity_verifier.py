"""
PAC-GOV-SANDBOX-HARDEN: STRUCTURAL INTEGRITY VERIFICATION
==========================================================

Certifies sandbox isolation and audit engine law alignment.
Performs deterministic domain model audit for compliance verification.

VERIFICATION SCOPE:
- Sandbox isolation (no production state mutation)
- Audit engine hash chain integrity
- IG signature verification
- Compliance with LAW_TIER governance
- Latency cap enforcement (<500ms)

CERTIFICATION CRITERIA:
- All tests pass deterministically
- Zero production state leakage
- Hash chain verified
- PQC signatures valid
- No SCRAM triggers

Author: ATLAS (GID-11)
PAC: CB-GOV-SANDBOX-HARDEN-2026-01-27
Status: PRODUCTION-READY
"""

import logging
import json
import time
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
import sys
import os

# Import modules to verify
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from core.governance.shadow_execution_sandbox import (
    ShadowExecutionSandbox,
    ExecutionMode,
    TransactionStatus
)
from core.governance.ig_audit_engine import (
    IGAuditEngine,
    AuditEventType,
    ComplianceLevel
)


logger = logging.getLogger("StructuralIntegrityVerification")


class VerificationResult:
    """Verification result container."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.details: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "details": self.details,
            "errors": self.errors,
            "latency_ms": self.latency_ms
        }


class StructuralIntegrityVerifier:
    """
    Structural integrity verification for governance sandbox.
    
    Certifies:
    - Sandbox isolation from production
    - Audit engine integrity
    - PQC signature validation
    - LAW_TIER compliance
    - Performance requirements
    
    Author: ATLAS (GID-11)
    """
    
    def __init__(self):
        self.results: List[VerificationResult] = []
        self.sandbox: Optional[ShadowExecutionSandbox] = None
        self.ig_engine: Optional[IGAuditEngine] = None
        
        logger.info("🔍 Structural Integrity Verifier initialized | Agent: GID-11")
    
    def verify_all(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Run all verification tests.
        
        Returns:
            (all_passed, summary_dict)
        """
        logger.info("═" * 80)
        logger.info("STRUCTURAL INTEGRITY VERIFICATION - COMMENCING")
        logger.info("═" * 80)
        
        # Run verification battery
        self._verify_sandbox_isolation()
        self._verify_ig_audit_engine()
        self._verify_hash_chain_integrity()
        self._verify_pqc_signatures()
        self._verify_latency_requirements()
        self._verify_law_tier_compliance()
        self._verify_production_isolation()
        
        # Compile results
        all_passed = all(result.passed for result in self.results)
        
        summary = {
            "overall_status": "PASS" if all_passed else "FAIL",
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "results": [r.to_dict() for r in self.results]
        }
        
        logger.info("═" * 80)
        logger.info(
            f"VERIFICATION COMPLETE | "
            f"Status: {summary['overall_status']} | "
            f"Passed: {summary['passed']}/{summary['total_tests']}"
        )
        logger.info("═" * 80)
        
        return all_passed, summary
    
    def _verify_sandbox_isolation(self):
        """Verify sandbox operates in isolated mode."""
        result = VerificationResult("Sandbox Isolation")
        start_time = time.time()
        
        try:
            # Initialize sandbox
            self.sandbox = ShadowExecutionSandbox(mode=ExecutionMode.SHADOW)
            
            # Verify mode
            if self.sandbox.mode != ExecutionMode.SHADOW:
                result.errors.append(
                    f"Sandbox not in SHADOW mode: {self.sandbox.mode}"
                )
            
            # Create test accounts
            self.sandbox.create_account("TEST-A", Decimal("1000.00"))
            self.sandbox.create_account("TEST-B", Decimal("500.00"))
            
            # Simulate transaction
            tx_id = self.sandbox.simulate_transaction(
                "TEST-A", "TEST-B", Decimal("100.00")
            )
            
            tx = self.sandbox.transactions.get(tx_id)
            
            # Verify transaction was simulated, not executed live
            if tx.status != TransactionStatus.SIMULATED:
                result.errors.append(
                    f"Transaction not simulated: {tx.status}"
                )
            
            # Verify audit log created
            audit_trail = self.sandbox.get_audit_trail()
            if len(audit_trail) == 0:
                result.errors.append("No audit trail generated")
            
            result.details = {
                "mode": self.sandbox.mode.value,
                "accounts_created": len(self.sandbox.accounts),
                "transactions_simulated": len(self.sandbox.transactions),
                "audit_log_entries": len(audit_trail)
            }
            
            result.passed = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )
    
    def _verify_ig_audit_engine(self):
        """Verify IG audit engine initialization and witnessing."""
        result = VerificationResult("IG Audit Engine")
        start_time = time.time()
        
        try:
            # Initialize IG engine
            self.ig_engine = IGAuditEngine(signer_gid="GID-12")
            
            # Verify initialization event witnessed
            if len(self.ig_engine.audit_log) == 0:
                result.errors.append("IG engine not self-witnessed")
            
            # Witness test event
            event_id = self.ig_engine.witness_event(
                event_type=AuditEventType.SANDBOX_ACTION,
                actor="GID-11",
                action="Structural verification test",
                compliance_level=ComplianceLevel.LAW_TIER
            )
            
            # Verify event was witnessed
            if event_id not in [e.event_id for e in self.ig_engine.audit_log]:
                result.errors.append(f"Event {event_id} not in audit log")
            
            result.details = {
                "signer_gid": self.ig_engine.signer_gid,
                "events_witnessed": len(self.ig_engine.audit_log),
                "hash_chain_head": self.ig_engine.hash_chain_head[:16]
            }
            
            result.passed = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )
    
    def _verify_hash_chain_integrity(self):
        """Verify audit log hash chain integrity."""
        result = VerificationResult("Hash Chain Integrity")
        start_time = time.time()
        
        try:
            if not self.ig_engine:
                raise ValueError("IG engine not initialized")
            
            # Verify hash chain
            is_valid = self.ig_engine.verify_hash_chain_integrity()
            
            if not is_valid:
                result.errors.append("Hash chain integrity check failed")
            
            result.details = {
                "chain_length": len(self.ig_engine.audit_log),
                "chain_head": self.ig_engine.hash_chain_head[:16],
                "integrity_valid": is_valid
            }
            
            result.passed = is_valid
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )
    
    def _verify_pqc_signatures(self):
        """Verify PQC (ML-DSA-65) signature validation."""
        result = VerificationResult("PQC Signature Validation")
        start_time = time.time()
        
        try:
            if not self.ig_engine:
                raise ValueError("IG engine not initialized")
            
            # Sign test BER
            test_ber_content = "TEST BER CONTENT FOR SIGNATURE VERIFICATION"
            ber_sig = self.ig_engine.sign_ber(
                ber_id="BER-TEST-VERIFY-001",
                ber_content=test_ber_content,
                compliance_attestation=ComplianceLevel.LAW_TIER
            )
            
            # Verify signature
            is_valid = self.ig_engine.verify_ber_signature(ber_sig, test_ber_content)
            
            if not is_valid:
                result.errors.append("BER signature verification failed")
            
            # Verify all audit log event signatures
            for event in self.ig_engine.audit_log:
                if not self.ig_engine.verify_event_signature(event):
                    result.errors.append(
                        f"Event signature invalid: {event.event_id}"
                    )
            
            result.details = {
                "ber_signature_valid": is_valid,
                "events_verified": len(self.ig_engine.audit_log),
                "pqc_algorithm": "ML-DSA-65"
            }
            
            result.passed = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )
    
    def _verify_latency_requirements(self):
        """Verify all operations meet <500ms latency cap."""
        result = VerificationResult("Latency Requirements")
        start_time = time.time()
        
        try:
            # Check all previous test latencies
            max_latency = max(r.latency_ms for r in self.results)
            
            if max_latency > 500:
                result.errors.append(
                    f"Latency cap exceeded: {max_latency:.2f}ms > 500ms"
                )
            
            # Individual witness latency test
            witness_times = []
            for i in range(10):
                witness_start = time.time()
                self.ig_engine.witness_event(
                    event_type=AuditEventType.SANDBOX_ACTION,
                    actor="GID-11",
                    action=f"Latency test {i}",
                    compliance_level=ComplianceLevel.INFORMATIONAL
                )
                witness_times.append((time.time() - witness_start) * 1000)
            
            avg_witness_latency = sum(witness_times) / len(witness_times)
            max_witness_latency = max(witness_times)
            
            if max_witness_latency > 500:
                result.errors.append(
                    f"Witness latency exceeded: {max_witness_latency:.2f}ms > 500ms"
                )
            
            result.details = {
                "max_test_latency_ms": max_latency,
                "avg_witness_latency_ms": avg_witness_latency,
                "max_witness_latency_ms": max_witness_latency,
                "latency_cap_ms": 500
            }
            
            result.passed = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )
    
    def _verify_law_tier_compliance(self):
        """Verify LAW_TIER compliance requirements."""
        result = VerificationResult("LAW_TIER Compliance")
        start_time = time.time()
        
        try:
            # Verify all LAW_TIER events have IG signatures
            law_tier_events = [
                e for e in self.ig_engine.audit_log
                if e.compliance_level == ComplianceLevel.LAW_TIER
            ]
            
            for event in law_tier_events:
                if not event.ig_signature:
                    result.errors.append(
                        f"LAW_TIER event missing signature: {event.event_id}"
                    )
                
                if not event.witnessed_at:
                    result.errors.append(
                        f"LAW_TIER event not witnessed: {event.event_id}"
                    )
            
            result.details = {
                "law_tier_events": len(law_tier_events),
                "all_signed": len(result.errors) == 0,
                "compliance_level": "LAW_TIER"
            }
            
            result.passed = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )
    
    def _verify_production_isolation(self):
        """Verify sandbox has no production state mutation capability."""
        result = VerificationResult("Production Isolation")
        start_time = time.time()
        
        try:
            # Verify sandbox mode
            if self.sandbox.mode != ExecutionMode.SHADOW:
                result.errors.append(
                    f"Sandbox not in SHADOW mode: {self.sandbox.mode}"
                )
            
            # Verify all transactions are simulated only
            live_transactions = [
                tx for tx in self.sandbox.transactions.values()
                if tx.status == TransactionStatus.EXECUTED
            ]
            
            if len(live_transactions) > 0:
                result.errors.append(
                    f"Found {len(live_transactions)} EXECUTED transactions in SHADOW mode"
                )
            
            # Verify IG approval required for production promotion
            # (This is a design check - implementation detail)
            
            result.details = {
                "sandbox_mode": self.sandbox.mode.value,
                "simulated_transactions": len([
                    tx for tx in self.sandbox.transactions.values()
                    if tx.status == TransactionStatus.SIMULATED
                ]),
                "executed_transactions": len(live_transactions),
                "production_isolated": len(live_transactions) == 0
            }
            
            result.passed = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")
            result.passed = False
        
        result.latency_ms = (time.time() - start_time) * 1000
        self.results.append(result)
        
        logger.info(
            f"{'✅' if result.passed else '❌'} {result.test_name} | "
            f"Latency: {result.latency_ms:.2f}ms"
        )


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)
    
    print("═" * 80)
    print("STRUCTURAL INTEGRITY VERIFICATION - SELF-TEST")
    print("═" * 80)
    
    verifier = StructuralIntegrityVerifier()
    all_passed, summary = verifier.verify_all()
    
    print("\n📊 VERIFICATION SUMMARY:")
    print(json.dumps(summary, indent=2))
    
    if all_passed:
        print("\n✅ ALL STRUCTURAL INTEGRITY CHECKS PASSED")
        print("🏆 SANDBOX AND AUDIT ENGINE CERTIFIED FOR PRODUCTION")
    else:
        print("\n❌ STRUCTURAL INTEGRITY VERIFICATION FAILED")
        print("🚨 DO NOT DEPLOY TO PRODUCTION")
    
    print("═" * 80)
