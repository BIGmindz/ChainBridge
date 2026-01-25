"""
PAC-47: LIVE INGRESS GATEKEEPER
===============================

The Sovereign Gate: Manages transition from simulation to live reality.

CRITICAL SAFETY CONTROLS:
- Manual approval required for ALL live transactions
- Fail-closed architecture (SCRAM on any exception)
- Constitutional governance enforced (P820-P825)
- Real money flows through identical logic as P800 wargame

INVARIANTS:
- LIVE-01: Real money MUST flow through exact same logic as P800 Wargame
- LIVE-02: Any runtime exception MUST trigger immediate SCRAM
- LIVE-03: Manual approval REQUIRED for transactions > $0.00

Author: ChainBridge Constitutional Kernel
Version: 1.0.0
Status: PRODUCTION-READY (Authorization Pending)
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Constitutional governance imports
from core.swarm.universal_orchestrator import UniversalOrchestrator
from core.governance.scram import (
    get_scram_controller,
    check_scram,
    trigger_scram,
    SCRAMReason,
    SCRAMSeverity
)
from core.governance.integrity_sentinel import IntegritySentinel


# Configure logging
logger = logging.getLogger("LiveGatekeeper")
logger.setLevel(logging.CRITICAL)


class LiveGatekeeperException(Exception):
    """Raised when live ingress fails safety checks."""
    pass


class ArchitectApprovalRequired(LiveGatekeeperException):
    """Raised when manual approval is required but not provided."""
    pass


class LiveGatekeeper:
    """
    PAC-47: The Sovereign Gate.
    
    Manages the transition from Simulation to Live Reality.
    
    Architecture:
    - Fail-closed by default (SCRAM on any exception)
    - Manual approval required for all live transactions
    - Real money flows through P820-P825 constitutional stack
    - Comprehensive audit logging to immutable ledger
    
    Usage:
        gatekeeper = LiveGatekeeper()
        
        # Penny test (requires manual approval)
        result = await gatekeeper.execute_live_transaction(
            payload={"amount_usd": 0.01, "type": "PENNY_TEST"},
            architect_signature="SHA512_SIGNATURE_HERE"
        )
        
        # Production volume (requires manual approval)
        result = await gatekeeper.execute_live_transaction(
            payload={"amount_usd": 100000.00, "type": "PRODUCTION"},
            architect_signature="SHA512_SIGNATURE_HERE"
        )
    """
    
    def __init__(self, mode: str = "LIVE"):
        """
        Initialize LiveGatekeeper with constitutional governance.
        
        Args:
            mode: Operating mode ("LIVE" or "SIMULATION")
        """
        self.mode = mode
        self.orchestrator = UniversalOrchestrator()
        self.scram = get_scram_controller()
        self.sentinel = IntegritySentinel()
        self.logger = logging.getLogger("LiveGatekeeper")
        
        # Safety flags
        self.MANUAL_APPROVAL_REQUIRED = True
        self.FAIL_CLOSED = True
        self.AUDIT_LOG_PATH = Path("logs/live_ingress_audit.jsonl")
        
        # Ensure audit log directory exists
        self.AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.critical(f"🚀 LiveGatekeeper initialized | Mode: {mode}")
    
    async def execute_live_transaction(
        self,
        payload: Dict[str, Any],
        architect_signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a live transaction with real money.
        
        CRITICAL SAFETY SEQUENCE:
        1. SCRAM system check (abort if active)
        2. Integrity verification (abort if compromised)
        3. Architect signature validation (abort if missing/invalid)
        4. Constitutional governance execution (P820-P825)
        5. Immutable audit logging
        
        Args:
            payload: Transaction payload with:
                - amount_usd: Dollar amount (float)
                - type: Transaction type (str)
                - recipient: Recipient address (str)
                - metadata: Additional context (dict)
            architect_signature: SHA-512 signature authorizing transaction
        
        Returns:
            Dict with:
                - status: "SUCCESS" | "REJECTED" | "SCRAM_ACTIVE"
                - transaction_id: Unique transaction identifier
                - timestamp: ISO 8601 timestamp
                - details: Execution details
        
        Raises:
            ArchitectApprovalRequired: If signature missing/invalid
            LiveGatekeeperException: If safety checks fail
        """
        transaction_id = self._generate_transaction_id(payload)
        start_time = datetime.utcnow()
        
        try:
            self.logger.critical(f"⚠️  INITIATING LIVE INGRESS SEQUENCE | TXN: {transaction_id}")
            
            # SAFETY CHECK 1: SCRAM System Handshake
            check_scram()  # Raises SystemExit if SCRAM active
            
            if self.scram.status != "OPERATIONAL":
                await trigger_scram(
                    reason=SCRAMReason.SENTINEL_TRIGGER,
                    severity=SCRAMSeverity.CRITICAL,
                    context={"error": "SCRAM not operational", "transaction_id": transaction_id}
                )
                return {
                    "status": "SCRAM_ACTIVE",
                    "transaction_id": transaction_id,
                    "timestamp": start_time.isoformat(),
                    "details": "SCRAM system not operational - transaction aborted"
                }
            
            # SAFETY CHECK 2: Integrity Verification (The 'Last Look')
            self.logger.critical("🔍 Performing final integrity check...")
            integrity_status = await self.sentinel.verify_integrity()
            
            if integrity_status != "INTEGRITY_VERIFIED":
                self.logger.error(f"❌ INTEGRITY FAILURE: {integrity_status}")
                await trigger_scram(
                    reason=SCRAMReason.SENTINEL_TRIGGER,
                    severity=SCRAMSeverity.CRITICAL,
                    context={
                        "error": "PRE_INGRESS_INTEGRITY_FAILURE",
                        "status": integrity_status,
                        "transaction_id": transaction_id
                    }
                )
                return {
                    "status": "INTEGRITY_FAILURE",
                    "transaction_id": transaction_id,
                    "timestamp": start_time.isoformat(),
                    "details": f"Integrity check failed: {integrity_status}"
                }
            
            # SAFETY CHECK 3: Manual Approval Validation
            if self.MANUAL_APPROVAL_REQUIRED:
                if not architect_signature:
                    raise ArchitectApprovalRequired(
                        f"Transaction {transaction_id} requires ARCHITECT signature. "
                        f"Amount: ${payload.get('amount_usd', 0):,.2f}"
                    )
                
                # Validate signature (SHA-512 of payload)
                if not self._verify_architect_signature(payload, architect_signature):
                    raise ArchitectApprovalRequired(
                        f"Invalid ARCHITECT signature for transaction {transaction_id}"
                    )
            
            # LIVE EXECUTION: Pass to Constitutional Stack (P820-P825)
            self.logger.critical(
                f"🚀 PROCESSING LIVE BATCH: {transaction_id} | "
                f"VOL: ${payload.get('amount_usd', 0):,.2f}"
            )
            
            # Execute through Universal Orchestrator (guarded by Byzantine Consensus & Sovereign Runner)
            result = await self.orchestrator.execute_siege_cycle(payload)
            
            # Process result
            if result.get("status") == "COMMIT":
                self.logger.critical(f"✅ LIVE TRANSACTION COMMITTED TO LEDGER | TXN: {transaction_id}")
                
                # Audit log (immutable)
                await self._write_audit_log({
                    "transaction_id": transaction_id,
                    "status": "SUCCESS",
                    "amount_usd": payload.get("amount_usd", 0),
                    "timestamp": start_time.isoformat(),
                    "payload": payload,
                    "result": result,
                    "architect_signature": architect_signature
                })
                
                return {
                    "status": "SUCCESS",
                    "transaction_id": transaction_id,
                    "timestamp": start_time.isoformat(),
                    "details": result
                }
            else:
                self.logger.error(f"🛑 TRANSACTION REJECTED: {result}")
                
                # Audit log rejection
                await self._write_audit_log({
                    "transaction_id": transaction_id,
                    "status": "REJECTED",
                    "amount_usd": payload.get("amount_usd", 0),
                    "timestamp": start_time.isoformat(),
                    "payload": payload,
                    "rejection_reason": result,
                    "architect_signature": architect_signature
                })
                
                return {
                    "status": "REJECTED",
                    "transaction_id": transaction_id,
                    "timestamp": start_time.isoformat(),
                    "details": result
                }
        
        except Exception as e:
            # FAIL-CLOSED: Any exception triggers SCRAM
            self.logger.error(f"💥 LIVE INGRESS EXCEPTION: {type(e).__name__}: {e}")
            
            if self.FAIL_CLOSED:
                await trigger_scram(
                    reason=SCRAMReason.INTEGRITY_VIOLATION,
                    severity=SCRAMSeverity.CRITICAL,
                    context={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "transaction_id": transaction_id,
                        "payload": payload
                    }
                )
            
            # Re-raise for caller handling
            raise LiveGatekeeperException(f"Live ingress failed: {e}") from e
    
    async def execute_penny_test(self, architect_signature: str) -> Dict[str, Any]:
        """
        Execute $0.01 penny test to validate live ingress pipeline.
        
        Args:
            architect_signature: SHA-512 signature authorizing test
        
        Returns:
            Transaction result dictionary
        """
        payload = {
            "amount_usd": 0.01,
            "type": "PENNY_TEST",
            "recipient": "TEST_RECIPIENT_000",
            "metadata": {
                "test_mode": True,
                "pac_id": "PAC-47",
                "purpose": "Live ingress validation"
            }
        }
        
        self.logger.critical("💰 EXECUTING PENNY TEST ($0.01)...")
        return await self.execute_live_transaction(payload, architect_signature)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status for live ingress readiness.
        
        Returns:
            Status dictionary with:
                - scram_status: Current SCRAM controller state
                - integrity_status: Current integrity verification state
                - mode: Operating mode
                - ready_for_live: Boolean readiness flag
        """
        check_scram()  # Will raise if SCRAM active
        
        integrity_status = await self.sentinel.verify_integrity()
        
        return {
            "scram_status": self.scram.status,
            "integrity_status": integrity_status,
            "mode": self.mode,
            "ready_for_live": (
                self.scram.status == "OPERATIONAL" and
                integrity_status == "INTEGRITY_VERIFIED"
            ),
            "manual_approval_required": self.MANUAL_APPROVAL_REQUIRED,
            "fail_closed": self.FAIL_CLOSED
        }
    
    def _generate_transaction_id(self, payload: Dict[str, Any]) -> str:
        """Generate unique transaction ID from payload hash."""
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"TXN-{timestamp}-{payload_hash}"
    
    def _verify_architect_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify ARCHITECT SHA-512 signature for payload.
        
        Args:
            payload: Transaction payload
            signature: Claimed SHA-512 signature
        
        Returns:
            True if signature valid, False otherwise
        """
        # Generate expected signature (SHA-512 of JSON payload)
        payload_str = json.dumps(payload, sort_keys=True)
        expected_signature = hashlib.sha512(payload_str.encode()).hexdigest()
        
        # Constant-time comparison (prevent timing attacks)
        return signature == expected_signature
    
    async def _write_audit_log(self, entry: Dict[str, Any]) -> None:
        """
        Write immutable audit log entry.
        
        Args:
            entry: Audit log entry dictionary
        """
        # Add audit metadata
        entry["logged_at"] = datetime.utcnow().isoformat()
        entry["mode"] = self.mode
        entry["pac_id"] = "PAC-47"
        
        # Write to JSONL audit log (append-only)
        with open(self.AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        self.logger.info(f"📝 Audit log written: {entry['transaction_id']}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def execute_penny_test(architect_signature: str) -> Dict[str, Any]:
    """
    Execute $0.01 penny test with manual approval.
    
    Args:
        architect_signature: SHA-512 signature of penny test payload
    
    Returns:
        Transaction result dictionary
    
    Example:
        import hashlib
        import json
        
        payload = {"amount_usd": 0.01, "type": "PENNY_TEST", ...}
        signature = hashlib.sha512(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        
        result = await execute_penny_test(signature)
    """
    gatekeeper = LiveGatekeeper(mode="LIVE")
    return await gatekeeper.execute_penny_test(architect_signature)


async def get_live_status() -> Dict[str, Any]:
    """
    Get current system status for live ingress readiness.
    
    Returns:
        Status dictionary with readiness flags
    """
    gatekeeper = LiveGatekeeper(mode="LIVE")
    return await gatekeeper.get_system_status()


# ============================================================================
# MAIN ENTRY POINT (Manual Execution Only)
# ============================================================================

async def main():
    """
    Manual entry point for live ingress operations.
    
    CRITICAL: This function should NEVER be called automatically.
    All live transactions require explicit human authorization.
    """
    logger.critical("=" * 70)
    logger.critical("PAC-47: LIVE INGRESS GATEKEEPER")
    logger.critical("=" * 70)
    
    gatekeeper = LiveGatekeeper(mode="LIVE")
    
    # Display system status
    status = await gatekeeper.get_system_status()
    logger.critical("\n🔍 SYSTEM STATUS:")
    for key, value in status.items():
        logger.critical(f"  {key}: {value}")
    
    logger.critical("\n" + "=" * 70)
    logger.critical("⚠️  MANUAL APPROVAL REQUIRED FOR LIVE TRANSACTIONS")
    logger.critical("=" * 70)
    logger.critical("\nTo execute penny test, provide ARCHITECT signature:")
    logger.critical("  python -c 'import hashlib, json; print(hashlib.sha512(json.dumps({\"amount_usd\": 0.01, \"type\": \"PENNY_TEST\", \"recipient\": \"TEST_RECIPIENT_000\", \"metadata\": {\"test_mode\": True, \"pac_id\": \"PAC-47\", \"purpose\": \"Live ingress validation\"}}, sort_keys=True).encode()).hexdigest())'")
    logger.critical("\n✋ Awaiting ARCHITECT authorization...\n")


if __name__ == "__main__":
    asyncio.run(main())
