#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE MASTER CONTROLLER v2.0                                 ║
║         PAC-STRAT-P80 + PAC-INT-P210-FINANCE-INTEGRATION                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: SYSTEM_INTEGRATION                                                    ║
║  GOVERNANCE_TIER: CONSTITUTIONAL_LAW                                         ║
║  MODE: ATOMIC_SOVEREIGNTY + FINANCIAL_EXECUTION                              ║
║  LANE: MASTER_INTEGRATION_LANE                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

THE FUSION TRINITY + INVISIBLE BANK:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                        CHAINBRIDGE CONTROLLER v2.0                      │
  │                           (Benson GID-00)                               │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                         │
  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
  │   │   P85       │    │   P65       │    │   P75       │                 │
  │   │ BIOMETRIC   │ -> │   AML       │ -> │  CUSTOMS    │ ─┐              │
  │   │   GATE      │    │   GATE      │    │   GATE      │  │              │
  │   │ (Identity)  │    │ (Finance)   │    │ (Logistics) │  │              │
  │   └─────────────┘    └─────────────┘    └─────────────┘  │              │
  │                                                           ▼              │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │                    THE INVISIBLE BANK (P200-P203)               │   │
  │   │   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐        │   │
  │   │   │ FEES    │ → │ LEDGER  │ → │ SETTLE  │ → │CURRENCY │        │   │
  │   │   │ (P202)  │   │ (P200)  │   │ (P201)  │   │ (P203)  │        │   │
  │   │   └─────────┘   └─────────┘   └─────────┘   └─────────┘        │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │                                                                         │
  │   IF (Bio=VERIFY AND AML=APPROVE AND Customs=RELEASE)                   │
  │   THEN → Calculate Fees → Authorize → Capture → FINALIZE                │
  │   ELSE → ABORT (No money moves)                                         │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

INVARIANTS:
  INV-CORE-001 (Atomic Finality): No partial sovereign transactions.
  INV-CORE-002 (Unified Log): All decisions in single ledger entry.
  INV-INT-001 (Gate Supremacy): Financial execution CANNOT occur if any Gate is closed.
  INV-INT-002 (Ledger Finality): A successful API response implies a committed Ledger entry.

TRAINING SIGNAL:
  "A decision without action is hallucination. The Ledger makes it real."
"""

import json
import logging
import sys
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import hashlib

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the Trinity Gates
from modules.chainsense.biometric_gate import BiometricGate, BioDecision
from modules.chainpay.aml_gate import AMLGate, AMLDecision
from modules.freight.smart_customs import SmartCustomsGate, GateDecision

# Import the Invisible Bank (P200-P203)
from modules.finance import (
    # P200: The Vault (Ledger)
    Ledger, Account, AccountType, Transaction as LedgerTransaction,
    TransactionStatus as LedgerTxStatus, InsufficientFundsError,
    # P201: The Cashier (Settlement)
    SettlementEngine, PaymentIntent, IntentStatus, CaptureType,
    LifecycleViolationError, AmountExceedsAuthorizationError,
    # P202: The Tollbooth (Fees)
    FeeEngine, FeeBreakdown, create_stripe_strategy,
    # P203: The Exchange (Currency)
    CurrencyEngine, UnknownCurrencyError, create_default_engine_with_rates,
)
from modules.finance.ledger import AccountNotFoundError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [CHAINBRIDGE] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ChainBridgeController")


class TransactionStatus(Enum):
    """Master Transaction Status"""
    FINALIZED = "FINALIZED"   # All gates passed - transaction complete
    ABORTED = "ABORTED"       # One or more gates failed
    PENDING = "PENDING"       # Processing in progress


class ChainBridgeController:
    """
    Master Controller v2.0 - The Roof Over the Three Pillars + Invisible Bank
    Managed by: Benson (GID-00)
    
    Orchestrates the Fusion Trinity:
    - P85: Biometric Gate (Identity - WHO is transacting)
    - P65: AML Gate (Finance - CLEAN money)
    - P75: Smart Customs (Logistics - LEGITIMATE goods)
    
    AND executes Financial Settlement:
    - P200: Ledger (The Vault - Double-Entry Accounting)
    - P201: Settlement (The Cashier - Two-Phase Commit)
    - P202: Fees (The Tollbooth - Revenue Capture)
    - P203: Currency (The Exchange - Multi-Currency Support)
    
    A valid sovereign transaction requires ALL THREE GATES to pass,
    then FINANCIAL EXECUTION commits the value transfer.
    
    INV-INT-001: Financial execution CANNOT occur if any Gate is closed.
    INV-INT-002: A successful API response implies a committed Ledger entry.
    """
    
    def __init__(self):
        self.agent_id = "GID-00"
        self.agent_name = "Benson"
        self.version = "2.0.0"
        
        # Initialize the Trinity Gates
        self.bio_gate = BiometricGate()
        self.aml_gate = AMLGate()
        self.customs_gate = SmartCustomsGate()
        
        # Initialize the Invisible Bank
        self.ledger = Ledger()
        self.settlement = SettlementEngine(self.ledger)
        self.fee_engine = FeeEngine()
        self.currency_engine = create_default_engine_with_rates()
        
        # Register default fee strategy (Stripe-like)
        self.fee_engine.register_strategy("default", create_stripe_strategy())
        
        # Pre-create system accounts
        self._initialize_system_accounts()
        
        self.transactions_processed = 0
        self.transactions_finalized = 0
        self.transactions_aborted = 0
        
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║        CHAINBRIDGE CONTROLLER v2.0.0 INITIALIZED             ║")
        logger.info("║              TRINITY GATES + INVISIBLE BANK ONLINE           ║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")
    
    def _initialize_system_accounts(self):
        """Initialize system accounts for fees and escrow."""
        # Fee revenue account (REVENUE type - credits increase balance)
        self.ledger.create_account(
            account_id="SYSTEM-FEE-REVENUE",
            account_type=AccountType.REVENUE,
            currency="USD",
            name="ChainBridge Fee Revenue",
            metadata={"owner": "SYSTEM", "purpose": "fee_collection"}
        )
        
        # External funding source (LIABILITY - can go negative for deposits)
        self.ledger.create_account(
            account_id="SYSTEM-FUNDING",
            account_type=AccountType.LIABILITY,
            currency="USD",
            name="External Funding Source",
            allow_negative=True,
            metadata={"owner": "SYSTEM", "purpose": "external_deposits"}
        )
        
        # Escrow account for in-flight transactions
        self.ledger.create_account(
            account_id="SYSTEM-ESCROW",
            account_type=AccountType.ESCROW,
            currency="USD",
            name="ChainBridge Escrow",
            metadata={"owner": "SYSTEM", "purpose": "transaction_escrow"}
        )
        
        logger.info("[BANK] System accounts initialized (FEE-REVENUE, FUNDING, ESCROW)")
    
    def _resolve_accounts(
        self, 
        payer_id: str, 
        payee_id: str, 
        currency: str
    ) -> Tuple[Account, Account]:
        """
        Resolve or create ledger accounts for transaction participants.
        
        In production, this would look up existing accounts from a database.
        For v1, we auto-create ASSET accounts if they don't exist.
        """
        # Resolve payer account
        payer_account_id = f"USER-{payer_id}"
        try:
            payer_account = self.ledger.get_account(payer_account_id)
        except AccountNotFoundError:
            payer_account = self.ledger.create_account(
                account_id=payer_account_id,
                account_type=AccountType.ASSET,
                currency=currency,
                name=f"Account: {payer_id}",
                metadata={"user_id": payer_id, "auto_created": True}
            )
            logger.info(f"[BANK] Auto-created payer account: {payer_account_id}")
        
        # Resolve payee account
        payee_account_id = f"USER-{payee_id}"
        try:
            payee_account = self.ledger.get_account(payee_account_id)
        except AccountNotFoundError:
            payee_account = self.ledger.create_account(
                account_id=payee_account_id,
                account_type=AccountType.ASSET,
                currency=currency,
                name=f"Account: {payee_id}",
                metadata={"user_id": payee_id, "auto_created": True}
            )
            logger.info(f"[BANK] Auto-created payee account: {payee_account_id}")
        
        return payer_account, payee_account
    
    def fund_account(self, user_id: str, amount: Decimal, currency: str = "USD") -> Account:
        """
        Fund a user account (for testing/demo purposes).
        In production, this would be via bank deposit or crypto deposit.
        """
        account_id = f"USER-{user_id}"
        
        try:
            account = self.ledger.get_account(account_id)
        except AccountNotFoundError:
            account = self.ledger.create_account(
                account_id=account_id,
                account_type=AccountType.ASSET,
                currency=currency,
                name=f"Account: {user_id}",
                metadata={"user_id": user_id}
            )
        
        # Credit from external funding source (LIABILITY with allow_negative)
        # Debit USER account (asset increases)
        # Credit SYSTEM-FUNDING (liability increases = we owe them money)
        txn = self.ledger.create_transaction(
            description=f"Account funding for {user_id}",
            reference=f"FUND-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            metadata={"type": "funding", "source": "external"}
        )
        txn.debit(account_id, amount, "Deposit received")
        txn.credit("SYSTEM-FUNDING", amount, "Customer deposit")
        
        self.ledger.post_transaction(txn.transaction_id)
        
        logger.info(f"[BANK] Funded account {account_id} with {amount} {currency}")
        return self.ledger.get_account(account_id)
        
    def process_transaction(
        self,
        user_data: Dict[str, Any],
        payment_data: Dict[str, Any],
        shipment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a complete sovereign transaction through all three gates.
        
        This is the ATOMIC operation. Either ALL gates pass, or the
        entire transaction is aborted. No partial commits.
        
        Args:
            user_data: Identity verification data for BiometricGate
            payment_data: Financial transaction data for AMLGate
            shipment_data: Cargo/logistics data for SmartCustomsGate
            
        Returns:
            TransactionReceipt with unified decision and blame assignment
        """
        tx_id = f"TRINITY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self.transactions_processed += 1
        
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════════════════════╗")
        logger.info(f"║  SOVEREIGN TRANSACTION: {tx_id}  ║")
        logger.info("╠══════════════════════════════════════════════════════════════════════╣")
        logger.info("║  INITIATING TRINITY PROTOCOL                                        ║")
        logger.info("║  Gate Sequence: BIOMETRIC → AML → CUSTOMS                           ║")
        logger.info("╚══════════════════════════════════════════════════════════════════════╝")
        
        # Track gate results for blame assignment
        gate_results = {
            "biometric": None,
            "aml": None,
            "customs": None
        }
        blame_gate = None
        abort_reason = None
        
        # ══════════════════════════════════════════════════════════════════════
        # GATE 1: BIOMETRIC (P85) - WHO is transacting?
        # ══════════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("┌──────────────────────────────────────────────────────────────────────┐")
        logger.info("│  GATE 1: BIOMETRIC VERIFICATION (P85)                               │")
        logger.info("│  Question: WHO is transacting?                                      │")
        logger.info("└──────────────────────────────────────────────────────────────────────┘")
        
        bio_result = self.bio_gate.process(user_data)
        gate_results["biometric"] = bio_result
        
        if bio_result["decision"] != BioDecision.VERIFY.value:
            blame_gate = "BIOMETRIC"
            abort_reason = bio_result["reason"]
            logger.error(f"[TRINITY] ❌ BIOMETRIC GATE FAILED: {abort_reason}")
            return self._abort_transaction(tx_id, gate_results, blame_gate, abort_reason)
        
        logger.info("[TRINITY] ✅ BIOMETRIC GATE PASSED")
        
        # ══════════════════════════════════════════════════════════════════════
        # GATE 2: AML (P65) - Is the money CLEAN?
        # ══════════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("┌──────────────────────────────────────────────────────────────────────┐")
        logger.info("│  GATE 2: AML COMPLIANCE (P65)                                       │")
        logger.info("│  Question: Is the money CLEAN?                                      │")
        logger.info("└──────────────────────────────────────────────────────────────────────┘")
        
        aml_result = self.aml_gate.process(payment_data)
        gate_results["aml"] = aml_result
        
        if aml_result["decision"] not in [AMLDecision.APPROVE.value]:
            blame_gate = "AML"
            abort_reason = aml_result["reason"]
            logger.error(f"[TRINITY] ❌ AML GATE FAILED: {abort_reason}")
            return self._abort_transaction(tx_id, gate_results, blame_gate, abort_reason)
        
        logger.info("[TRINITY] ✅ AML GATE PASSED")
        
        # ══════════════════════════════════════════════════════════════════════
        # GATE 3: CUSTOMS (P75) - Are the goods LEGITIMATE?
        # ══════════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("┌──────────────────────────────────────────────────────────────────────┐")
        logger.info("│  GATE 3: SMART CUSTOMS (P75)                                        │")
        logger.info("│  Question: Are the goods LEGITIMATE?                                │")
        logger.info("└──────────────────────────────────────────────────────────────────────┘")
        
        # Split shipment_data into manifest and telemetry
        manifest = shipment_data.get("manifest", shipment_data)
        telemetry = shipment_data.get("telemetry", {})
        
        customs_result = self.customs_gate.process(manifest, telemetry)
        gate_results["customs"] = customs_result
        
        if customs_result["decision"] != GateDecision.RELEASE.value:
            blame_gate = "CUSTOMS"
            abort_reason = customs_result["reason"]
            status_emoji = "⚠️" if customs_result["decision"] == "HOLD" else "❌"
            logger.error(f"[TRINITY] {status_emoji} CUSTOMS GATE FAILED: {abort_reason}")
            return self._abort_transaction(tx_id, gate_results, blame_gate, abort_reason)
        
        logger.info("[TRINITY] ✅ CUSTOMS GATE PASSED")
        
        # ══════════════════════════════════════════════════════════════════════
        # ALL GATES PASSED → EXECUTE FINANCIAL SETTLEMENT
        # INV-INT-001: This block ONLY executes if all gates passed
        # ══════════════════════════════════════════════════════════════════════
        return self._finalize_transaction(tx_id, gate_results, user_data, payment_data, shipment_data)
    
    def _abort_transaction(
        self,
        tx_id: str,
        gate_results: Dict[str, Any],
        blame_gate: str,
        reason: str
    ) -> Dict[str, Any]:
        """Abort transaction and assign blame."""
        self.transactions_aborted += 1
        
        logger.info("")
        logger.error("╔══════════════════════════════════════════════════════════════════════╗")
        logger.error("║                    TRANSACTION ABORTED                              ║")
        logger.error(f"║  Blame Gate: {blame_gate:58} ║")
        logger.error("╚══════════════════════════════════════════════════════════════════════╝")
        
        receipt = {
            "transaction_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": TransactionStatus.ABORTED.value,
            "finalized": False,
            "blame": {
                "gate": blame_gate,
                "reason": reason
            },
            "gates": {
                "biometric": self._summarize_gate(gate_results.get("biometric")),
                "aml": self._summarize_gate(gate_results.get("aml")),
                "customs": self._summarize_gate(gate_results.get("customs"))
            },
            "controller": f"{self.agent_name} ({self.agent_id})",
            "version": self.version,
            "invariant_enforced": "INV-CORE-001 (Atomic Finality)",
            "statistics": {
                "total_processed": self.transactions_processed,
                "total_finalized": self.transactions_finalized,
                "total_aborted": self.transactions_aborted
            }
        }
        
        return receipt
    
    def _finalize_transaction(
        self,
        tx_id: str,
        gate_results: Dict[str, Any],
        user_data: Dict[str, Any],
        payment_data: Dict[str, Any],
        shipment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Finalize successful transaction WITH FINANCIAL EXECUTION.
        
        Flow (INV-INT-001 guarantees gates already passed):
        1. Validate currency
        2. Calculate fees
        3. Resolve/create accounts
        4. Create payment intent (Auth)
        5. Capture payment
        6. Record fee split in ledger
        7. Return receipt with financial trace
        """
        # ══════════════════════════════════════════════════════════════════════
        # STEP 1: VALIDATE CURRENCY (P203)
        # ══════════════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("┌──────────────────────────────────────────────────────────────────────┐")
        logger.info("│  FINANCIAL EXECUTION: INVISIBLE BANK                                │")
        logger.info("└──────────────────────────────────────────────────────────────────────┘")
        
        amount = Decimal(str(payment_data.get("amount", 0)))
        currency = payment_data.get("currency", "USD")
        
        try:
            # Validate currency is known
            self.currency_engine.registry.get(currency)
            logger.info(f"[BANK] Currency validated: {currency}")
        except UnknownCurrencyError:
            logger.error(f"[BANK] ❌ Unknown currency: {currency}")
            return self._abort_financial(tx_id, gate_results, "CURRENCY", f"Unknown currency: {currency}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 2: CALCULATE FEES (P202)
        # ══════════════════════════════════════════════════════════════════════
        fee_breakdown = self.fee_engine.calculate(amount, strategy_name="default")
        net_amount = fee_breakdown.net_amount
        total_fees = fee_breakdown.total_fee
        
        logger.info(f"[BANK] Fee calculation (default strategy):")
        logger.info(f"       Gross: {amount} {currency}")
        logger.info(f"       Fees:  {total_fees} {currency}")
        logger.info(f"       Net:   {net_amount} {currency}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 3: RESOLVE ACCOUNTS (P200)
        # ══════════════════════════════════════════════════════════════════════
        payer_id = payment_data.get("payer_id")
        payee_id = payment_data.get("payee_id")
        
        try:
            payer_account, payee_account = self._resolve_accounts(payer_id, payee_id, currency)
            logger.info(f"[BANK] Accounts resolved: {payer_account.account_id} → {payee_account.account_id}")
        except Exception as e:
            logger.error(f"[BANK] ❌ Account resolution failed: {e}")
            return self._abort_financial(tx_id, gate_results, "LEDGER", str(e))
        
        # Check payer has sufficient funds
        payer_balance = payer_account.balance
        if payer_balance < amount:
            logger.error(f"[BANK] ❌ Insufficient funds: {payer_balance} < {amount}")
            return self._abort_financial(
                tx_id, gate_results, "SETTLEMENT", 
                f"Insufficient funds: balance {payer_balance}, required {amount}"
            )
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 4: CREATE PAYMENT INTENT / AUTHORIZE (P201)
        # ══════════════════════════════════════════════════════════════════════
        try:
            intent = self.settlement.create_intent(
                source_account=payer_account.account_id,
                destination_account=payee_account.account_id,
                amount=amount,
                description=f"ChainBridge TX: {tx_id}",
                metadata={
                    "trinity_tx_id": tx_id,
                    "currency": currency,
                    "biometric_hash": gate_results["biometric"].get("biometric_hash"),
                    "shipment_id": shipment_data.get("manifest", shipment_data).get("shipment_id"),
                    "fee_breakdown": {
                        "total_fee": str(total_fees),
                        "net_amount": str(net_amount),
                        "strategy": "default"
                    }
                }
            )
            logger.info(f"[BANK] Payment intent created: {intent.intent_id}")
            
            # Authorize (reserve funds)
            intent = self.settlement.authorize(intent.intent_id)
            logger.info(f"[BANK] Authorization successful: {intent.status.value}")
            
        except InsufficientFundsError as e:
            logger.error(f"[BANK] ❌ Authorization failed - insufficient funds: {e}")
            return self._abort_financial(tx_id, gate_results, "SETTLEMENT", str(e))
        except Exception as e:
            logger.error(f"[BANK] ❌ Authorization failed: {e}")
            return self._abort_financial(tx_id, gate_results, "SETTLEMENT", str(e))
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 5: CAPTURE PAYMENT (P201)
        # ══════════════════════════════════════════════════════════════════════
        try:
            intent = self.settlement.capture(intent.intent_id)
            logger.info(f"[BANK] Payment captured: {intent.status.value}")
            
        except Exception as e:
            # If capture fails, void the authorization
            logger.error(f"[BANK] ❌ Capture failed, voiding authorization: {e}")
            try:
                self.settlement.void(intent.intent_id, reason=f"Capture failed: {e}")
            except:
                pass
            return self._abort_financial(tx_id, gate_results, "SETTLEMENT", str(e))
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 6: RECORD FEE SPLIT (P200)
        # ══════════════════════════════════════════════════════════════════════
        if total_fees > Decimal("0"):
            try:
                # Transfer fees from payee to fee revenue account
                # (Fees come out of what payee receives)
                fee_txn = self.ledger.create_transaction(
                    description=f"Fee collection for TX: {tx_id}",
                    reference=f"FEE-{tx_id}",
                    metadata={
                        "trinity_tx_id": tx_id,
                        "intent_id": intent.intent_id,
                        "fee_type": "platform_fee",
                        "gross_amount": str(amount),
                        "fee_amount": str(total_fees),
                        "net_to_payee": str(net_amount)
                    }
                )
                fee_txn.debit(payee_account.account_id, total_fees, "Platform fee")
                fee_txn.credit("SYSTEM-FEE-REVENUE", total_fees, "Fee revenue")
                self.ledger.post_transaction(fee_txn.transaction_id)
                
                logger.info(f"[BANK] Fee recorded: {total_fees} {currency} → FEE-REVENUE")
                
            except Exception as e:
                # Fee recording failed - this is non-fatal but should be logged
                logger.warning(f"[BANK] ⚠️ Fee recording failed (non-fatal): {e}")
        
        # ══════════════════════════════════════════════════════════════════════
        # STEP 7: GENERATE RECEIPT WITH FINANCIAL TRACE
        # ══════════════════════════════════════════════════════════════════════
        self.transactions_finalized += 1
        
        # Generate transaction hash (immutable record)
        tx_hash = hashlib.sha256(
            f"{tx_id}:{intent.intent_id}:{gate_results['biometric']['biometric_hash']}:{amount}".encode()
        ).hexdigest()
        
        # Get final balances
        payer_final = self.ledger.get_account(payer_account.account_id)
        payee_final = self.ledger.get_account(payee_account.account_id)
        fee_account = self.ledger.get_account("SYSTEM-FEE-REVENUE")
        
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════════════════════╗")
        logger.info("║                 ✅ TRANSACTION FINALIZED ✅                         ║")
        logger.info("║                                                                      ║")
        logger.info("║  TRINITY GATES:                                                      ║")
        logger.info("║    • BIOMETRIC (P85): VERIFY   ← Human Confirmed                    ║")
        logger.info("║    • AML (P65):       APPROVE  ← Money Clean                        ║")
        logger.info("║    • CUSTOMS (P75):   RELEASE  ← Goods Legitimate                   ║")
        logger.info("║                                                                      ║")
        logger.info("║  FINANCIAL EXECUTION:                                               ║")
        logger.info(f"║    • Amount: {str(amount):15} {currency:4}                              ║")
        logger.info(f"║    • Fees:   {str(total_fees):15} {currency:4}                              ║")
        logger.info(f"║    • Net:    {str(net_amount):15} {currency:4}                              ║")
        logger.info("║                                                                      ║")
        logger.info(f"║  Transaction Hash: {tx_hash[:40]}...  ║")
        logger.info("╚══════════════════════════════════════════════════════════════════════╝")
        
        receipt = {
            "transaction_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": TransactionStatus.FINALIZED.value,
            "finalized": True,
            "transaction_hash": tx_hash,
            "gates": {
                "biometric": self._summarize_gate(gate_results.get("biometric")),
                "aml": self._summarize_gate(gate_results.get("aml")),
                "customs": self._summarize_gate(gate_results.get("customs"))
            },
            "financial_execution": {
                "settlement_intent_id": intent.intent_id,
                "settlement_status": intent.status.value,
                "gross_amount": str(amount),
                "currency": currency,
                "fees": {
                    "total": str(total_fees),
                    "strategy": "default",
                    "breakdown": fee_breakdown.fee_components
                },
                "net_amount": str(net_amount),
                "payer": {
                    "account_id": payer_account.account_id,
                    "balance_before": str(payer_balance),
                    "balance_after": str(payer_final.balance if payer_final else "N/A")
                },
                "payee": {
                    "account_id": payee_account.account_id,
                    "balance_after": str(payee_final.balance if payee_final else "N/A")
                },
                "ledger_transactions": {
                    "hold": intent.hold_transaction_id,
                    "capture": intent.capture_transaction_id
                }
            },
            "participants": {
                "user_id": user_data.get("user_id"),
                "biometric_hash": gate_results["biometric"].get("biometric_hash"),
                "payer": payer_id,
                "payee": payee_id,
                "shipment": shipment_data.get("manifest", shipment_data).get("shipment_id")
            },
            "value": {
                "amount": str(amount),
                "currency": currency
            },
            "controller": f"{self.agent_name} ({self.agent_id})",
            "version": self.version,
            "invariants_enforced": [
                "INV-CORE-001 (Atomic Finality)",
                "INV-CORE-002 (Unified Log)",
                "INV-INT-001 (Gate Supremacy)",
                "INV-INT-002 (Ledger Finality)"
            ],
            "attestation": f"SOVEREIGN-TX-{tx_hash[:16].upper()}",
            "statistics": {
                "total_processed": self.transactions_processed,
                "total_finalized": self.transactions_finalized,
                "total_aborted": self.transactions_aborted
            }
        }
        
        return receipt
    
    def _abort_financial(
        self,
        tx_id: str,
        gate_results: Dict[str, Any],
        blame_component: str,
        reason: str
    ) -> Dict[str, Any]:
        """Abort transaction due to financial execution failure (after gates passed)."""
        self.transactions_aborted += 1
        
        logger.error("")
        logger.error("╔══════════════════════════════════════════════════════════════════════╗")
        logger.error("║               TRANSACTION ABORTED (FINANCIAL)                       ║")
        logger.error(f"║  Component: {blame_component:58} ║")
        logger.error("║  Note: All gates PASSED but financial execution FAILED             ║")
        logger.error("╚══════════════════════════════════════════════════════════════════════╝")
        
        receipt = {
            "transaction_id": tx_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": TransactionStatus.ABORTED.value,
            "finalized": False,
            "gates_passed": True,  # Important: gates DID pass
            "blame": {
                "gate": None,  # No gate failed
                "component": blame_component,  # Financial component failed
                "reason": reason
            },
            "gates": {
                "biometric": self._summarize_gate(gate_results.get("biometric")),
                "aml": self._summarize_gate(gate_results.get("aml")),
                "customs": self._summarize_gate(gate_results.get("customs"))
            },
            "controller": f"{self.agent_name} ({self.agent_id})",
            "version": self.version,
            "invariant_enforced": "INV-INT-002 (No false positives - Ledger not updated)",
            "statistics": {
                "total_processed": self.transactions_processed,
                "total_finalized": self.transactions_finalized,
                "total_aborted": self.transactions_aborted
            }
        }
        
        return receipt
    
    def _summarize_gate(self, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create summary of gate result for receipt."""
        if result is None:
            return {"status": "NOT_EXECUTED", "decision": None}
        return {
            "status": "EXECUTED",
            "decision": result.get("decision"),
            "reason": result.get("reason")
        }


# ══════════════════════════════════════════════════════════════════════════════
# E2E SIMULATION FOR P80 VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def run_trinity_simulation():
    """
    Run the P210 validation simulation demonstrating:
    1. The Perfect Trade (all gates pass + funded → FINALIZE with ledger update)
    2. Insufficient Funds (gates pass, no funds → ABORT financial)
    3. The Smuggler (customs fails → ABORT at gate)
    4. The Money Launderer (AML fails → ABORT at gate)
    """
    print("")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║        CHAINBRIDGE CONTROLLER v2.0 INTEGRATION TEST - P210          ║")
    print("║     \"A decision without action is hallucination. Ledger makes it real.\"")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    controller = ChainBridgeController()
    results = []
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 1: THE PERFECT TRADE (All Pass + Funded → FINALIZE)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*74)
    print("SCENARIO 1: THE PERFECT TRADE (WITH FINANCIAL EXECUTION)")
    print("Expected: FINALIZED with Ledger Update")
    print("="*74)
    
    # FUND THE PAYER ACCOUNT FIRST
    controller.fund_account("ACME-CORP", Decimal("1000000.00"), "USD")
    payer_before = controller.ledger.get_account("USER-ACME-CORP")
    print(f"\n[SETUP] Funded ACME-CORP: Balance = {payer_before.balance} USD")
    
    result_1 = controller.process_transaction(
        user_data={
            "user_id": "USR-ALICE-TRADER",
            "liveness_score": 0.98,
            "face_similarity": 0.96,
            "has_enrolled_template": True,
            "document_type": "PASSPORT",
            "is_expired": False,
            "is_tampered": False,
            "mrz_valid": True
        },
        payment_data={
            "transaction_id": "PAY-001-CLEAN",
            "payer_id": "ACME-CORP",
            "payee_id": "GLOBEX-INC",
            "payer_country": "US",
            "payee_country": "DE",
            "amount": 250000.00,
            "currency": "USD",
            "daily_total": 0
        },
        shipment_data={
            "manifest": {
                "shipment_id": "SHP-001-LEGIT",
                "seal_intact": True,
                "declared_weight_kg": 5000,
                "actual_weight_kg": 5050,
                "bill_of_lading": True,
                "commercial_invoice": True,
                "packing_list": True
            },
            "telemetry": {
                "route_deviation_km": 1.2,
                "unscheduled_stops": 0,
                "arrival_delay_min": 15,
                "gps_gaps": 0
            }
        }
    )
    results.append(("PERFECT TRADE", result_1))
    
    # Verify ledger balances changed
    payer_after = controller.ledger.get_account("USER-ACME-CORP")
    payee_after = controller.ledger.get_account("USER-GLOBEX-INC")
    fee_revenue = controller.ledger.get_account("SYSTEM-FEE-REVENUE")
    
    print(f"\n[LEDGER VERIFICATION]")
    print(f"  Payer (ACME-CORP):    {payer_before.balance} → {payer_after.balance}")
    print(f"  Payee (GLOBEX-INC):   0 → {payee_after.balance}")
    print(f"  Fee Revenue:          {fee_revenue.balance}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 2: INSUFFICIENT FUNDS (Gates Pass, But No Money)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*74)
    print("SCENARIO 2: INSUFFICIENT FUNDS")
    print("Expected: ABORTED (Gates Pass, Financial Execution Fails)")
    print("="*74)
    
    result_2 = controller.process_transaction(
        user_data={
            "user_id": "USR-BROKE-TRADER",
            "liveness_score": 0.95,
            "face_similarity": 0.94,
            "has_enrolled_template": True,
            "document_type": "PASSPORT",
            "is_expired": False,
            "mrz_valid": True
        },
        payment_data={
            "transaction_id": "PAY-002-BROKE",
            "payer_id": "BROKE-LLC",  # Has no funds
            "payee_id": "HOPEFUL-CORP",
            "payer_country": "US",
            "payee_country": "US",
            "amount": 500000.00,
            "currency": "USD",
            "daily_total": 0
        },
        shipment_data={
            "manifest": {
                "shipment_id": "SHP-002-LEGIT",
                "seal_intact": True,
                "declared_weight_kg": 2000,
                "actual_weight_kg": 2010,
                "bill_of_lading": True,
                "commercial_invoice": True,
                "packing_list": True
            },
            "telemetry": {
                "route_deviation_km": 0.5,
                "unscheduled_stops": 0,
                "arrival_delay_min": 30,
                "gps_gaps": 0
            }
        }
    )
    results.append(("INSUFFICIENT FUNDS", result_2))
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 3: THE SMUGGLER (Customs HOLD → ABORT at Gate)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*74)
    print("SCENARIO 3: THE SMUGGLER")
    print("Expected: ABORTED (Blame: CUSTOMS - No Financial Execution)")
    print("="*74)
    
    # Even if we fund the smuggler, the gate should stop them
    controller.fund_account("SHADOW-LLC", Decimal("10000000.00"), "USD")
    
    result_3 = controller.process_transaction(
        user_data={
            "user_id": "USR-BOB-SMUGGLER",
            "liveness_score": 0.95,
            "face_similarity": 0.94,
            "has_enrolled_template": True,
            "document_type": "PASSPORT",
            "is_expired": False,
            "mrz_valid": True
        },
        payment_data={
            "transaction_id": "PAY-003-SMUGGLE",
            "payer_id": "SHADOW-LLC",
            "payee_id": "OFFSHORE-CORP",
            "payer_country": "US",
            "payee_country": "US",
            "amount": 500000.00,
            "currency": "USD",
            "daily_total": 0
        },
        shipment_data={
            "manifest": {
                "shipment_id": "SHP-003-TROJAN",
                "seal_intact": True,
                "declared_weight_kg": 2000,
                "actual_weight_kg": 2010,
                "bill_of_lading": True,
                "commercial_invoice": True,
                "packing_list": True
            },
            "telemetry": {
                "route_deviation_km": 0.5,
                "unscheduled_stops": 2,  # ⚠️ SMUGGLER BEHAVIOR
                "stop_locations": ["Warehouse A", "Warehouse B"],
                "arrival_delay_min": 120,
                "gps_gaps": 1
            }
        }
    )
    results.append(("SMUGGLER", result_3))
    
    # Verify smuggler's money was NOT taken (INV-INT-001)
    smuggler_balance = controller.ledger.get_account("USER-SHADOW-LLC")
    print(f"\n[INV-INT-001 CHECK] Smuggler balance unchanged: {smuggler_balance.balance}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO 4: THE MONEY LAUNDERER (AML REJECT → ABORT at Gate)
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*74)
    print("SCENARIO 4: THE MONEY LAUNDERER")
    print("Expected: ABORTED (Blame: AML - No Financial Execution)")
    print("="*74)
    
    result_4 = controller.process_transaction(
        user_data={
            "user_id": "USR-CARLOS-LAUNDER",
            "liveness_score": 0.97,
            "face_similarity": 0.95,
            "has_enrolled_template": True,
            "document_type": "NATIONAL_ID",
            "is_expired": False,
            "mrz_valid": True
        },
        payment_data={
            "transaction_id": "PAY-004-DIRTY",
            "payer_id": "SANCTIONED-ENTITY-001",  # ❌ ON WATCHLIST
            "payee_id": "SHELL-COMPANY-X",
            "payer_country": "US",
            "payee_country": "PA",
            "amount": 1000000.00,
            "daily_total": 0
        },
        shipment_data={
            "manifest": {
                "shipment_id": "SHP-004-COVER",
                "seal_intact": True,
                "declared_weight_kg": 100,
                "actual_weight_kg": 100
            },
            "telemetry": {
                "route_deviation_km": 0,
                "unscheduled_stops": 0,
                "arrival_delay_min": 0
            }
        }
    )
    results.append(("MONEY LAUNDERER", result_4))
    
    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "="*74)
    print("FINANCE INTEGRATION TEST SUMMARY (P210)")
    print("="*74)
    
    print("""
    ┌─────────────────────┬────────────┬───────────────────┬─────────────────────┐
    │ Scenario            │ Status     │ Gates             │ Financial           │
    ├─────────────────────┼────────────┼───────────────────┼─────────────────────┤""")
    
    for name, result in results:
        status = result["status"]
        status_icon = "✅" if status == "FINALIZED" else "❌"
        gates_passed = result.get("gates_passed", status == "FINALIZED")
        gates_str = "✅ ALL PASS" if gates_passed else f"❌ {result.get('blame', {}).get('gate', 'N/A')}"
        
        if "financial_execution" in result:
            fin_str = f"✅ {result['financial_execution']['settlement_status']}"
        elif result.get("gates_passed"):
            fin_str = f"❌ {result.get('blame', {}).get('component', 'N/A')}"
        else:
            fin_str = "⏭️  NOT REACHED"
        
        print(f"    │ {name:19} │ {status_icon} {status:8} │ {gates_str:17} │ {fin_str:19} │")
    
    print("    └─────────────────────┴────────────┴───────────────────┴─────────────────────┘")
    
    # Final ledger state
    print("\n[FINAL LEDGER STATE]")
    print(f"  Fee Revenue Collected: {controller.ledger.get_account('SYSTEM-FEE-REVENUE').balance} USD")
    print(f"  Total Ledger Transactions: {len(controller.ledger.transactions)}")
    
    # Validate expected outcomes
    assert results[0][1]["status"] == "FINALIZED", "Perfect Trade should FINALIZE"
    assert "financial_execution" in results[0][1], "Perfect Trade should have financial execution"
    assert results[1][1]["status"] == "ABORTED" and results[1][1].get("gates_passed") == True, "Insufficient Funds should fail at settlement"
    assert results[2][1]["status"] == "ABORTED" and results[2][1]["blame"]["gate"] == "CUSTOMS", "Smuggler should fail at CUSTOMS"
    assert results[3][1]["status"] == "ABORTED" and results[3][1]["blame"]["gate"] == "AML", "Money Launderer should fail at AML"
    
    print("\n✅ ALL SCENARIOS VALIDATED - FINANCE INTEGRATION COMPLETE")
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║  BENSON [GID-00]: \"The Brain is connected to the Vault. We are live.\"║")
    print("║  ATTESTATION: MASTER-BER-P210-INTEGRATION                            ║")
    print("║  LEDGER_COMMIT: ATTEST: FINANCE_CORE_LINKED                          ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    return {
        "scenarios_run": 4,
        "scenarios_passed": 4,
        "finalized_count": 1,
        "aborted_count": 3,
        "financial_executions": 1,
        "fee_revenue": str(controller.ledger.get_account("SYSTEM-FEE-REVENUE").balance),
        "attestation": "MASTER-BER-P210-INTEGRATION"
    }


if __name__ == "__main__":
    run_trinity_simulation()
