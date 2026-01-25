"""
Sovereign Runner - Hardened Execution Engine
============================================

PAC-P821-SOVEREIGN-RUNNER-HARDENING | LAW-TIER
Constitutional Mandate: PAC-CAMPAIGN-P820-P825

This module provides the execution engine for ChainBridge batch processing.
Integrates P820 SCRAM pre-flight checks into the hot loop.

Invariants Enforced:
- RUNNER-01: Execution MUST cease immediately if SCRAM not ARMED
- RUNNER-02: Runner MUST NOT bypass SCRAM controller singleton
- RUNNER-03: Fail-closed on any SCRAM check error
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from core.governance.scram import get_scram_controller, SCRAMState

logger = logging.getLogger("chainbridge.sovereign_runner")


class SovereignRunner:
    """
    PAC-P821: The Hardened Execution Engine
    
    Integrates P820 SCRAM checks into the batch execution hot loop.
    Provides fail-closed behavior when SCRAM is active.
    
    Constitutional Invariants:
    - RUNNER-01: Check SCRAM status before EVERY batch execution
    - RUNNER-02: Use singleton SCRAM controller (no bypass)
    - RUNNER-03: Halt immediately if SCRAM not ARMED
    """
    
    def __init__(self):
        """Initialize runner with SCRAM controller singleton."""
        self.scram = get_scram_controller()
        self.logger = logging.getLogger("SovereignRunner")
        self.logger.info("SovereignRunner initialized with SCRAM integration")
    
    async def execute_batch(
        self,
        batch_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute batch transaction with SCRAM pre-flight check.
        
        RUNNER-01 Enforcement: Check SCRAM state before execution.
        Returns "SCRAM_ABORT" if SCRAM is not ARMED.
        
        Args:
            batch_id: Unique batch identifier
            metadata: Optional batch metadata
        
        Returns:
            "BATCH_COMMITTED" on success
            "SCRAM_ABORT" if SCRAM active
        """
        # CONSTITUTIONAL INTERLOCK: SCRAM PRE-FLIGHT CHECK
        # This is the enforcement point for RUNNER-01
        if not self.scram.is_armed:
            reason = self._get_scram_reason()
            self.logger.critical(
                f"⛔ RUNNER HALTED: SCRAM IS ACTIVE ({reason}) - Batch {batch_id} aborted"
            )
            return "SCRAM_ABORT"
        
        # EXECUTION LOGIC (Placeholder for Universal Orchestrator call)
        self.logger.info(f"✓ SCRAM check passed - Processing Batch {batch_id}")
        
        if metadata:
            self.logger.debug(f"Batch metadata: {metadata}")
        
        # Simulate batch processing
        await asyncio.sleep(0.01)
        
        self.logger.info(f"✓ Batch {batch_id} committed successfully")
        return "BATCH_COMMITTED"
    
    def _get_scram_reason(self) -> str:
        """Extract SCRAM activation reason from audit trail."""
        try:
            trail = self.scram.audit_trail
            if trail:
                latest = trail[-1]
                return latest.reason
        except Exception as e:
            self.logger.warning(f"Could not extract SCRAM reason: {e}")
        return "UNKNOWN"
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check including SCRAM status.
        
        Returns health status with SCRAM state information.
        """
        scram_state = self.scram.state
        return {
            "runner_status": "HEALTHY",
            "scram_state": scram_state.name,
            "scram_armed": self.scram.is_armed,
            "scram_active": self.scram.is_active,
            "scram_complete": self.scram.is_complete
        }
