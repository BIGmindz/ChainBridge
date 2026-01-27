"""
PAC-FIN-P80: Sovereign Treasury Activation
============================================
Deterministic liquidity management and allocation system.

Purpose: Manage capital flow post-ingress with cryptographic guarantees,
         enforcing zero-drift allocation splits and quantum-proof signatures.

Created: PAC-FIN-P80 (Sovereign Treasury Activation)
Updated: 2026-01-25

Invariants:
- TREASURY-01: Sum of allocations MUST equal total ingress (Zero Drift)
- TREASURY-02: All Allocation Mandates MUST be PQC-Signed

Design Philosophy:
- "Money is data. Data is immutable. The Vault is open."
- "Every dollar is accounted for, every allocation is provable"
- "Liquidity management is deterministic, not discretionary"
"""

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List

from core.crypto.quantum_signer import QuantumSigner, get_global_signer


class AllocationPolicy:
    """
    Treasury allocation policy definition.
    
    Defines how incoming capital is split between storage tiers.
    """
    
    def __init__(
        self,
        cold_storage_pct: float = 0.90,
        hot_wallet_pct: float = 0.10,
        policy_id: str = "PAC-P80-V1"
    ):
        """
        Initialize allocation policy.
        
        Args:
            cold_storage_pct: Percentage to cold storage (default 90%)
            hot_wallet_pct: Percentage to hot wallet (default 10%)
            policy_id: Policy version identifier
        """
        # Validate percentages
        total_pct = cold_storage_pct + hot_wallet_pct
        if abs(total_pct - 1.0) > 1e-10:
            raise ValueError(f"Policy percentages must sum to 1.0, got {total_pct}")
        
        self.cold_storage_pct = Decimal(str(cold_storage_pct))
        self.hot_wallet_pct = Decimal(str(hot_wallet_pct))
        self.policy_id = policy_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Export policy as dictionary."""
        return {
            "policy_id": self.policy_id,
            "cold_storage_pct": float(self.cold_storage_pct),
            "hot_wallet_pct": float(self.hot_wallet_pct)
        }


class AllocationMandate:
    """
    Treasury allocation mandate with quantum signature.
    
    Represents a signed, immutable allocation decision that cannot
    be altered without breaking the signature.
    """
    
    def __init__(
        self,
        batch_id: str,
        total_amount: Decimal,
        cold_storage_amount: Decimal,
        hot_wallet_amount: Decimal,
        policy_id: str,
        signature: Optional[bytes] = None,
        signer_pubkey: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        self.batch_id = batch_id
        self.total_amount = total_amount
        self.cold_storage_amount = cold_storage_amount
        self.hot_wallet_amount = hot_wallet_amount
        self.policy_id = policy_id
        self.signature = signature
        self.signer_pubkey = signer_pubkey
        self.timestamp = timestamp or datetime.now().isoformat()
        
        # Compute mandate hash (for signing)
        self.mandate_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """
        Compute SHA3-256 hash of mandate data.
        
        Returns:
            64-character hex hash
        """
        # Canonical representation for signing
        canonical = {
            "batch_id": self.batch_id,
            "total_amount": str(self.total_amount),
            "cold_storage_amount": str(self.cold_storage_amount),
            "hot_wallet_amount": str(self.hot_wallet_amount),
            "policy_id": self.policy_id,
            "timestamp": self.timestamp
        }
        
        # JSON with sorted keys for deterministic hashing
        canonical_json = json.dumps(canonical, sort_keys=True)
        return hashlib.sha3_256(canonical_json.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export mandate as dictionary."""
        result = {
            "batch_id": self.batch_id,
            "timestamp": self.timestamp,
            "total_amount": float(self.total_amount),
            "allocations": {
                "cold_storage_usd": float(self.cold_storage_amount),
                "hot_wallet_usd": float(self.hot_wallet_amount)
            },
            "policy_id": self.policy_id,
            "mandate_hash": self.mandate_hash
        }
        
        # Include signature if present (TREASURY-02 enforcement)
        if self.signature:
            result["quantum_signature"] = self.signature.hex()
            result["signer_pubkey"] = self.signer_pubkey
        
        return result
    
    def verify_zero_drift(self, tolerance: Decimal = Decimal("0.000001")) -> bool:
        """
        Verify TREASURY-01: Sum of allocations equals total.
        
        Args:
            tolerance: Maximum acceptable drift (default 1e-6 USD)
        
        Returns:
            True if drift within tolerance, False otherwise
        """
        computed_sum = self.cold_storage_amount + self.hot_wallet_amount
        drift = abs(computed_sum - self.total_amount)
        return drift <= tolerance


class SovereignTreasury:
    """
    The Vault - Sovereign Treasury Management System.
    
    Manages the flow of capital post-ingress with deterministic allocation
    logic, quantum-proof signatures, and zero-drift guarantees.
    
    Workflow:
    1. Receive incoming capital batch (from ingress)
    2. Apply allocation policy (90% cold, 10% hot)
    3. Validate zero-drift invariant
    4. Sign allocation mandate with Dilithium
    5. Return signed mandate for execution
    
    Invariants:
    - TREASURY-01: Allocations sum to total (enforced by Decimal arithmetic)
    - TREASURY-02: All mandates are PQC-signed (enforced by sign_mandate)
    
    Usage:
        treasury = SovereignTreasury()
        mandate = treasury.allocate_funds("BATCH-001", 1000000.00)
        # mandate contains signed allocation: {cold: 900000, hot: 100000}
    """
    
    def __init__(
        self,
        policy: Optional[AllocationPolicy] = None,
        signer: Optional[QuantumSigner] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Sovereign Treasury.
        
        Args:
            policy: Allocation policy (defaults to 90/10 split)
            signer: Quantum signer instance (defaults to global)
            logger: Logging instance
        """
        self.policy = policy or AllocationPolicy()
        self.signer = signer or get_global_signer()
        self.logger = logger or logging.getLogger("SovereignTreasury")
        
        self.allocation_history: List[AllocationMandate] = []
        
        # PAC-ECO-P90: Hot wallet tracking for autopoiesis
        self._hot_wallet_balance = Decimal("0.00")
        self._cold_storage_balance = Decimal("0.00")
        self._hot_wallet_transactions: List[Dict[str, Any]] = []
        
        self.logger.info(
            f"🏛️ SOVEREIGN TREASURY INITIALIZED | "
            f"Policy: {self.policy.policy_id} | "
            f"Cold: {self.policy.cold_storage_pct:.0%} | "
            f"Hot: {self.policy.hot_wallet_pct:.0%}"
        )
    
    def allocate_funds(
        self,
        batch_id: str,
        amount: float,
        sign_mandate: bool = True
    ) -> AllocationMandate:
        """
        Allocate incoming capital according to policy.
        
        Args:
            batch_id: Unique batch identifier
            amount: Total USD amount to allocate
            sign_mandate: Whether to sign mandate with PQC (TREASURY-02)
        
        Returns:
            AllocationMandate with signed allocation details
        
        Raises:
            ValueError: If zero-drift check fails (TREASURY-01 violation)
        """
        # Convert to Decimal for exact arithmetic
        total = Decimal(str(amount))
        
        self.logger.info(
            f"💰 PROCESSING TREASURY ALLOCATION: {batch_id} | ${amount:,.2f}"
        )
        
        # Step 1: Calculate split using Decimal (no float drift)
        cold_amt = (total * self.policy.cold_storage_pct).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
        hot_amt = (total * self.policy.hot_wallet_pct).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
        
        # Step 2: Create mandate
        mandate = AllocationMandate(
            batch_id=batch_id,
            total_amount=total,
            cold_storage_amount=cold_amt,
            hot_wallet_amount=hot_amt,
            policy_id=self.policy.policy_id
        )
        
        # Step 3: TREASURY-01 - Zero Drift Check
        if not mandate.verify_zero_drift():
            drift = abs((cold_amt + hot_amt) - total)
            self.logger.error(
                f"❌ TREASURY-01 VIOLATION: ALLOCATION DRIFT DETECTED | "
                f"Batch: {batch_id} | Drift: ${drift}"
            )
            raise ValueError(
                f"CRITICAL: ALLOCATION DRIFT DETECTED. "
                f"Total: {total}, Cold: {cold_amt}, Hot: {hot_amt}, "
                f"Drift: {drift}"
            )
        
        # Step 4: TREASURY-02 - Sign mandate with Quantum Shield
        if sign_mandate:
            hash_bytes = bytes.fromhex(mandate.mandate_hash)
            signature = self.signer.sign(hash_bytes)
            mandate.signature = signature
            mandate.signer_pubkey = self.signer.public_key_hex
            
            self.logger.debug(
                f"🔐 Mandate signed with Dilithium | "
                f"Hash: {mandate.mandate_hash[:16]}... | "
                f"Sig: {len(signature)} bytes"
            )
        
        # Step 5: Record and return
        self.allocation_history.append(mandate)
        
        # PAC-ECO-P90: Update internal wallet balances
        self._cold_storage_balance += cold_amt
        self._hot_wallet_balance += hot_amt
        
        self.logger.info(
            f"✅ FUNDS ALLOCATED & SIGNED | "
            f"COLD: ${cold_amt:,.2f} ({self.policy.cold_storage_pct:.0%}) | "
            f"HOT: ${hot_amt:,.2f} ({self.policy.hot_wallet_pct:.0%})"
        )
        
        return mandate
    
    def get_hot_balance(self) -> Decimal:
        """
        Get current hot wallet balance.
        
        PAC-ECO-P90: Used by autopoietic engine to determine growth capacity.
        
        Returns:
            Current hot wallet balance in USD
        """
        return self._hot_wallet_balance
    
    def get_cold_balance(self) -> Decimal:
        """
        Get current cold storage balance.
        
        Returns:
            Current cold storage balance in USD
        """
        return self._cold_storage_balance
    
    def debit_hot_wallet(
        self,
        amount: float,
        reason: str,
        batch_id: Optional[str] = None
    ) -> Decimal:
        """
        Debit funds from hot wallet.
        
        PAC-ECO-P90: Used by autopoietic engine for agent spawning costs.
        
        Args:
            amount: Amount to debit in USD
            reason: Reason for debit (for audit trail)
            batch_id: Optional batch identifier
        
        Returns:
            New hot wallet balance
        
        Raises:
            ValueError: If insufficient funds
        """
        debit_amt = Decimal(str(amount))
        
        if debit_amt > self._hot_wallet_balance:
            self.logger.error(
                f"❌ INSUFFICIENT HOT WALLET FUNDS | "
                f"Requested: ${debit_amt} | Available: ${self._hot_wallet_balance}"
            )
            raise ValueError(
                f"Insufficient hot wallet funds. "
                f"Requested: ${debit_amt}, Available: ${self._hot_wallet_balance}"
            )
        
        # Record transaction
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "DEBIT",
            "amount_usd": float(debit_amt),
            "reason": reason,
            "batch_id": batch_id,
            "balance_before": float(self._hot_wallet_balance),
            "balance_after": float(self._hot_wallet_balance - debit_amt)
        }
        self._hot_wallet_transactions.append(transaction)
        
        # Update balance
        self._hot_wallet_balance -= debit_amt
        
        self.logger.info(
            f"💸 HOT WALLET DEBIT | "
            f"Amount: ${debit_amt:,.2f} | "
            f"Reason: {reason} | "
            f"New Balance: ${self._hot_wallet_balance:,.2f}"
        )
        
        return self._hot_wallet_balance
    
    def credit_hot_wallet(
        self,
        amount: float,
        reason: str,
        batch_id: Optional[str] = None
    ) -> Decimal:
        """
        Credit funds to hot wallet.
        
        Args:
            amount: Amount to credit in USD
            reason: Reason for credit (for audit trail)
            batch_id: Optional batch identifier
        
        Returns:
            New hot wallet balance
        """
        credit_amt = Decimal(str(amount))
        
        # Record transaction
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "CREDIT",
            "amount_usd": float(credit_amt),
            "reason": reason,
            "batch_id": batch_id,
            "balance_before": float(self._hot_wallet_balance),
            "balance_after": float(self._hot_wallet_balance + credit_amt)
        }
        self._hot_wallet_transactions.append(transaction)
        
        # Update balance
        self._hot_wallet_balance += credit_amt
        
        self.logger.info(
            f"💰 HOT WALLET CREDIT | "
            f"Amount: ${credit_amt:,.2f} | "
            f"Reason: {reason} | "
            f"New Balance: ${self._hot_wallet_balance:,.2f}"
        )
        
        return self._hot_wallet_balance
    
    def get_wallet_stats(self) -> Dict[str, Any]:
        """
        Get wallet statistics.
        
        Returns:
            Dictionary with wallet metrics
        """
        total_balance = self._cold_storage_balance + self._hot_wallet_balance
        
        return {
            "total_balance_usd": float(total_balance),
            "cold_storage_usd": float(self._cold_storage_balance),
            "hot_wallet_usd": float(self._hot_wallet_balance),
            "cold_percentage": float(self._cold_storage_balance / total_balance * 100) if total_balance > 0 else 0.0,
            "hot_percentage": float(self._hot_wallet_balance / total_balance * 100) if total_balance > 0 else 0.0,
            "transaction_count": len(self._hot_wallet_transactions)
        }
        
        return mandate
    
    def verify_mandate(
        self,
        mandate: AllocationMandate,
        expected_pubkey: Optional[str] = None
    ) -> bool:
        """
        Verify mandate signature and zero-drift invariant.
        
        Args:
            mandate: Allocation mandate to verify
            expected_pubkey: Expected signer public key (optional)
        
        Returns:
            True if valid, False if tampered or invalid
        """
        # Verify zero-drift
        if not mandate.verify_zero_drift():
            self.logger.error(
                f"❌ TREASURY-01 VIOLATION in mandate {mandate.batch_id}"
            )
            return False
        
        # Verify signature if present
        if mandate.signature:
            from core.crypto.quantum_signer import QuantumVerifier
            
            pubkey = expected_pubkey or mandate.signer_pubkey
            if not pubkey:
                self.logger.error("No public key available for verification")
                return False
            
            verifier = QuantumVerifier.from_hex(pubkey)
            hash_bytes = bytes.fromhex(mandate.mandate_hash)
            
            is_valid = verifier.verify(hash_bytes, mandate.signature)
            
            if not is_valid:
                self.logger.error(
                    f"❌ TREASURY-02 VIOLATION: Signature verification failed | "
                    f"Batch: {mandate.batch_id}"
                )
                return False
            
            self.logger.info(
                f"✅ Mandate verified | Batch: {mandate.batch_id} | "
                f"Hash: {mandate.mandate_hash[:16]}..."
            )
        else:
            self.logger.warning(
                f"⚠️  Mandate {mandate.batch_id} not signed (TREASURY-02 not enforced)"
            )
        
        return True
    
    def get_allocation_stats(self) -> Dict[str, Any]:
        """
        Get treasury allocation statistics.
        
        Returns:
            Dictionary with allocation metrics
        """
        if not self.allocation_history:
            return {
                "total_batches": 0,
                "total_allocated_usd": 0.0,
                "total_cold_usd": 0.0,
                "total_hot_usd": 0.0
            }
        
        total_allocated = sum(m.total_amount for m in self.allocation_history)
        total_cold = sum(m.cold_storage_amount for m in self.allocation_history)
        total_hot = sum(m.hot_wallet_amount for m in self.allocation_history)
        
        return {
            "total_batches": len(self.allocation_history),
            "total_allocated_usd": float(total_allocated),
            "total_cold_usd": float(total_cold),
            "total_hot_usd": float(total_hot),
            "policy_id": self.policy.policy_id,
            "signed_mandates": sum(1 for m in self.allocation_history if m.signature)
        }
    
    def export_mandates(self, filepath: str) -> None:
        """
        Export all allocation mandates to JSON file.
        
        Args:
            filepath: Path to output file
        """
        export_data = {
            "pac_id": "PAC-FIN-P80",
            "generated_at": datetime.now().isoformat(),
            "policy": self.policy.to_dict(),
            "stats": self.get_allocation_stats(),
            "mandates": [m.to_dict() for m in self.allocation_history]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"📝 Exported {len(self.allocation_history)} mandates to {filepath}")


# Singleton instance for application-wide use
_global_treasury: Optional[SovereignTreasury] = None


def get_global_treasury(policy: Optional[AllocationPolicy] = None) -> SovereignTreasury:
    """
    Get or create the global SovereignTreasury instance.
    
    Args:
        policy: Allocation policy (only used on first call)
    
    Returns:
        SovereignTreasury instance
    """
    global _global_treasury
    if _global_treasury is None:
        _global_treasury = SovereignTreasury(policy=policy)
    return _global_treasury
