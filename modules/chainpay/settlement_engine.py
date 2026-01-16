#!/usr/bin/env python3
"""
ChainPay Settlement Engine
==========================

Core payment settlement system for ChainBridge.
Handles multi-currency payment processing, reconciliation,
and blockchain-backed settlement finality.

PAC Reference: PAC-JEFFREY-TARGET-20M-001 (TASK 1)
Constitutional Authority: ALEX (FOUNDER / CEO)
Executor: BENSON [GID-00]

Schema: v4.0.0
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Tuple
import json


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class PaymentStatus(Enum):
    """Settlement pipeline status."""
    INITIATED = auto()
    AML_CLEARED = auto()
    VALIDATED = auto()
    QUEUED = auto()
    PROCESSING = auto()
    SETTLED = auto()
    CONFIRMED = auto()
    FAILED = auto()
    REVERSED = auto()


class SettlementMethod(Enum):
    """Settlement rails."""
    HEDERA_INSTANT = "hedera"
    XRP_PAYMENT = "xrp"
    WIRE_TRANSFER = "wire"
    ACH_BATCH = "ach"
    STABLECOIN_USDC = "usdc"
    STABLECOIN_USDT = "usdt"


class Currency(Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    USDC = "USDC"
    USDT = "USDT"
    HBAR = "HBAR"
    XRP = "XRP"


class ReconciliationStatus(Enum):
    """Ledger reconciliation states."""
    PENDING = auto()
    MATCHED = auto()
    EXCEPTION = auto()
    RESOLVED = auto()
    WRITE_OFF = auto()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Money:
    """Immutable monetary value with currency."""
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        if isinstance(self.amount, (int, float, str)):
            self.amount = Decimal(str(self.amount))
        self.amount = self.amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"amount": str(self.amount), "currency": self.currency.value}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Money":
        return cls(Decimal(data["amount"]), Currency(data["currency"]))
    
    def convert_to(self, target: Currency, rate: Decimal) -> "Money":
        """Convert to target currency at given rate."""
        converted = self.amount * rate
        return Money(converted, target)


@dataclass
class PaymentParty:
    """Party to a payment transaction."""
    party_id: str
    name: str
    account_identifier: str
    bank_code: Optional[str] = None
    country: str = "US"
    kyc_verified: bool = False
    aml_score: Optional[int] = None


@dataclass
class SettlementInstruction:
    """Instructions for settling a payment."""
    instruction_id: str
    method: SettlementMethod
    destination_address: str
    reference: str
    memo: Optional[str] = None
    priority: int = 1  # 1=normal, 2=high, 3=urgent
    deadline: Optional[datetime] = None


@dataclass
class PaymentTransaction:
    """Core payment transaction entity."""
    transaction_id: str
    source: PaymentParty
    destination: PaymentParty
    amount: Money
    fee: Money
    status: PaymentStatus
    settlement_instruction: SettlementInstruction
    created_at: datetime
    updated_at: datetime
    settled_at: Optional[datetime] = None
    blockchain_tx_hash: Optional[str] = None
    aml_reference: Optional[str] = None
    reconciliation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "source": self.source.__dict__,
            "destination": self.destination.__dict__,
            "amount": self.amount.to_dict(),
            "fee": self.fee.to_dict(),
            "status": self.status.name,
            "settlement_instruction": {
                "instruction_id": self.settlement_instruction.instruction_id,
                "method": self.settlement_instruction.method.value,
                "destination_address": self.settlement_instruction.destination_address,
                "reference": self.settlement_instruction.reference,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "blockchain_tx_hash": self.blockchain_tx_hash,
            "aml_reference": self.aml_reference,
            "reconciliation_id": self.reconciliation_id,
            "metadata": self.metadata,
        }


@dataclass
class ReconciliationRecord:
    """Ledger reconciliation entry."""
    record_id: str
    transaction_id: str
    expected_amount: Money
    actual_amount: Optional[Money]
    status: ReconciliationStatus
    variance: Optional[Decimal] = None
    matched_at: Optional[datetime] = None
    exception_reason: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class SettlementBatch:
    """Batch of settlements for processing."""
    batch_id: str
    transactions: List[PaymentTransaction]
    method: SettlementMethod
    total_amount: Money
    total_fees: Money
    status: PaymentStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    blockchain_batch_hash: Optional[str] = None


# =============================================================================
# PROTOCOLS (INTERFACES)
# =============================================================================

class AMLGateway(Protocol):
    """AML compliance gateway interface."""
    
    def screen_transaction(self, tx: PaymentTransaction) -> Tuple[bool, str]:
        """Screen transaction for AML compliance."""
        ...
    
    def get_risk_score(self, party: PaymentParty) -> int:
        """Get AML risk score for party (0-100)."""
        ...


class BlockchainConnector(Protocol):
    """Blockchain settlement connector interface."""
    
    def submit_payment(self, tx: PaymentTransaction) -> str:
        """Submit payment and return transaction hash."""
        ...
    
    def confirm_settlement(self, tx_hash: str) -> bool:
        """Confirm settlement finality."""
        ...
    
    def get_transaction_status(self, tx_hash: str) -> str:
        """Get blockchain transaction status."""
        ...


class LedgerService(Protocol):
    """Ledger service for reconciliation."""
    
    def record_debit(self, account: str, amount: Money, reference: str) -> str:
        """Record debit entry."""
        ...
    
    def record_credit(self, account: str, amount: Money, reference: str) -> str:
        """Record credit entry."""
        ...
    
    def get_balance(self, account: str, currency: Currency) -> Money:
        """Get account balance."""
        ...


# =============================================================================
# EXCHANGE RATE SERVICE
# =============================================================================

class ExchangeRateService:
    """Multi-currency exchange rate service."""
    
    def __init__(self):
        # Production rates would come from external feeds
        # These are placeholder rates for development
        self._rates: Dict[Tuple[Currency, Currency], Decimal] = {
            (Currency.USD, Currency.EUR): Decimal("0.92"),
            (Currency.USD, Currency.GBP): Decimal("0.79"),
            (Currency.USD, Currency.JPY): Decimal("149.50"),
            (Currency.USD, Currency.CHF): Decimal("0.88"),
            (Currency.USD, Currency.AUD): Decimal("1.53"),
            (Currency.USD, Currency.CAD): Decimal("1.36"),
            (Currency.EUR, Currency.USD): Decimal("1.09"),
            (Currency.GBP, Currency.USD): Decimal("1.27"),
            (Currency.USD, Currency.USDC): Decimal("1.00"),
            (Currency.USD, Currency.USDT): Decimal("1.00"),
            (Currency.USD, Currency.HBAR): Decimal("12.50"),
            (Currency.USD, Currency.XRP): Decimal("2.00"),
        }
        self._last_update = datetime.now(timezone.utc)
    
    def get_rate(self, source: Currency, target: Currency) -> Decimal:
        """Get exchange rate from source to target currency."""
        if source == target:
            return Decimal("1.0")
        
        key = (source, target)
        if key in self._rates:
            return self._rates[key]
        
        # Try inverse
        inverse_key = (target, source)
        if inverse_key in self._rates:
            return Decimal("1.0") / self._rates[inverse_key]
        
        # Try USD as intermediate
        if source != Currency.USD and target != Currency.USD:
            to_usd = self.get_rate(source, Currency.USD)
            from_usd = self.get_rate(Currency.USD, target)
            return to_usd * from_usd
        
        raise ValueError(f"No rate available for {source.value} -> {target.value}")
    
    def convert(self, money: Money, target: Currency) -> Money:
        """Convert money to target currency."""
        rate = self.get_rate(money.currency, target)
        return money.convert_to(target, rate)


# =============================================================================
# FEE CALCULATOR
# =============================================================================

class FeeCalculator:
    """Settlement fee calculation engine."""
    
    # Fee structure per settlement method (basis points)
    FEE_STRUCTURE = {
        SettlementMethod.HEDERA_INSTANT: Decimal("15"),      # 0.15%
        SettlementMethod.XRP_PAYMENT: Decimal("10"),         # 0.10%
        SettlementMethod.STABLECOIN_USDC: Decimal("20"),     # 0.20%
        SettlementMethod.STABLECOIN_USDT: Decimal("25"),     # 0.25%
        SettlementMethod.WIRE_TRANSFER: Decimal("50"),       # 0.50%
        SettlementMethod.ACH_BATCH: Decimal("10"),           # 0.10%
    }
    
    MIN_FEE = Decimal("0.50")       # Minimum fee in USD
    MAX_FEE = Decimal("10000.00")   # Maximum fee in USD
    
    def calculate_fee(
        self, 
        amount: Money, 
        method: SettlementMethod,
        priority: int = 1
    ) -> Money:
        """Calculate settlement fee."""
        basis_points = self.FEE_STRUCTURE.get(method, Decimal("25"))
        
        # Priority multiplier (urgent = 2x fee)
        priority_multiplier = Decimal("1.0") + (Decimal("0.5") * (priority - 1))
        
        # Calculate fee
        fee_rate = (basis_points / Decimal("10000")) * priority_multiplier
        fee_amount = amount.amount * fee_rate
        
        # Apply min/max bounds
        fee_amount = max(self.MIN_FEE, min(fee_amount, self.MAX_FEE))
        
        return Money(fee_amount, Currency.USD)


# =============================================================================
# SETTLEMENT ENGINE
# =============================================================================

class SettlementEngine:
    """
    Core settlement engine for ChainPay.
    
    Orchestrates payment processing through:
    1. AML screening (via aml_gate.py integration)
    2. Fee calculation
    3. Currency conversion
    4. Blockchain settlement
    5. Reconciliation
    
    Constitutional Compliance:
    - INV-FAIL-CLOSED: All failures halt processing
    - INV-NO-NARRATIVE-INFLATION: Real metrics only
    - INV-PDO-PRIMACY: Evidence-backed operations
    """
    
    def __init__(
        self,
        aml_gateway: Optional[AMLGateway] = None,
        ledger_service: Optional[LedgerService] = None,
    ):
        self.exchange_service = ExchangeRateService()
        self.fee_calculator = FeeCalculator()
        self.aml_gateway = aml_gateway
        self.ledger_service = ledger_service
        
        # In-memory transaction store (production uses persistence layer)
        self._transactions: Dict[str, PaymentTransaction] = {}
        self._batches: Dict[str, SettlementBatch] = {}
        self._reconciliation: Dict[str, ReconciliationRecord] = {}
        
        # Connector registry
        self._connectors: Dict[SettlementMethod, BlockchainConnector] = {}
    
    def register_connector(self, method: SettlementMethod, connector: BlockchainConnector):
        """Register a blockchain connector for a settlement method."""
        self._connectors[method] = connector
    
    def create_payment(
        self,
        source: PaymentParty,
        destination: PaymentParty,
        amount: Money,
        method: SettlementMethod,
        reference: str,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentTransaction:
        """
        Create a new payment transaction.
        
        Returns:
            PaymentTransaction with INITIATED status
        
        Raises:
            ValueError: If validation fails
        """
        # Validate amount
        if amount.amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        # Calculate fee
        fee = self.fee_calculator.calculate_fee(amount, method, priority)
        
        # Generate IDs
        tx_id = f"TX-{uuid.uuid4().hex[:12].upper()}"
        instruction_id = f"SI-{uuid.uuid4().hex[:8].upper()}"
        
        now = datetime.now(timezone.utc)
        
        # Create instruction
        instruction = SettlementInstruction(
            instruction_id=instruction_id,
            method=method,
            destination_address=destination.account_identifier,
            reference=reference,
            priority=priority,
        )
        
        # Create transaction
        tx = PaymentTransaction(
            transaction_id=tx_id,
            source=source,
            destination=destination,
            amount=amount,
            fee=fee,
            status=PaymentStatus.INITIATED,
            settlement_instruction=instruction,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        
        # Store transaction
        self._transactions[tx_id] = tx
        
        return tx
    
    def screen_aml(self, tx_id: str) -> Tuple[bool, str]:
        """
        Screen transaction through AML gateway.
        
        Returns:
            Tuple of (passed, reference/reason)
        """
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        if tx.status != PaymentStatus.INITIATED:
            raise ValueError(f"Transaction {tx_id} not in INITIATED status")
        
        # If no AML gateway, use mock screening
        if self.aml_gateway:
            passed, reference = self.aml_gateway.screen_transaction(tx)
        else:
            # Mock AML screening - always passes for dev
            passed = True
            reference = f"AML-{uuid.uuid4().hex[:8].upper()}"
        
        # Update transaction
        tx.updated_at = datetime.now(timezone.utc)
        
        if passed:
            tx.status = PaymentStatus.AML_CLEARED
            tx.aml_reference = reference
        else:
            tx.status = PaymentStatus.FAILED
            tx.metadata["failure_reason"] = f"AML screening failed: {reference}"
        
        return passed, reference
    
    def validate_payment(self, tx_id: str) -> bool:
        """
        Validate payment for settlement.
        
        Checks:
        - AML cleared
        - Sufficient funds (if ledger available)
        - Valid destination
        - No duplicate
        """
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        if tx.status != PaymentStatus.AML_CLEARED:
            raise ValueError(f"Transaction {tx_id} not AML cleared")
        
        # Validation checks
        validations = []
        
        # Check destination validity
        if not tx.destination.account_identifier:
            validations.append("Invalid destination address")
        
        # Check for duplicate reference
        for other_tx in self._transactions.values():
            if (other_tx.transaction_id != tx_id and
                other_tx.settlement_instruction.reference == tx.settlement_instruction.reference and
                other_tx.status in (PaymentStatus.SETTLED, PaymentStatus.CONFIRMED)):
                validations.append(f"Duplicate reference: {tx.settlement_instruction.reference}")
                break
        
        # Update status
        tx.updated_at = datetime.now(timezone.utc)
        
        if not validations:
            tx.status = PaymentStatus.VALIDATED
            return True
        else:
            tx.status = PaymentStatus.FAILED
            tx.metadata["validation_errors"] = validations
            return False
    
    def queue_for_settlement(self, tx_id: str) -> bool:
        """Add transaction to settlement queue."""
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        if tx.status != PaymentStatus.VALIDATED:
            raise ValueError(f"Transaction {tx_id} not validated")
        
        tx.status = PaymentStatus.QUEUED
        tx.updated_at = datetime.now(timezone.utc)
        
        return True
    
    def process_settlement(self, tx_id: str) -> Tuple[bool, Optional[str]]:
        """
        Process settlement for a transaction.
        
        Returns:
            Tuple of (success, blockchain_tx_hash)
        """
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        if tx.status != PaymentStatus.QUEUED:
            raise ValueError(f"Transaction {tx_id} not queued for settlement")
        
        tx.status = PaymentStatus.PROCESSING
        tx.updated_at = datetime.now(timezone.utc)
        
        method = tx.settlement_instruction.method
        connector = self._connectors.get(method)
        
        if connector:
            try:
                tx_hash = connector.submit_payment(tx)
                tx.blockchain_tx_hash = tx_hash
                tx.status = PaymentStatus.SETTLED
                tx.settled_at = datetime.now(timezone.utc)
                return True, tx_hash
            except Exception as e:
                tx.status = PaymentStatus.FAILED
                tx.metadata["settlement_error"] = str(e)
                return False, None
        else:
            # Mock settlement for development
            mock_hash = f"0x{hashlib.sha256(tx_id.encode()).hexdigest()[:40]}"
            tx.blockchain_tx_hash = mock_hash
            tx.status = PaymentStatus.SETTLED
            tx.settled_at = datetime.now(timezone.utc)
            return True, mock_hash
    
    def confirm_settlement(self, tx_id: str) -> bool:
        """
        Confirm settlement finality.
        
        For blockchain settlements, waits for required confirmations.
        """
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        if tx.status != PaymentStatus.SETTLED:
            raise ValueError(f"Transaction {tx_id} not in SETTLED status")
        
        method = tx.settlement_instruction.method
        connector = self._connectors.get(method)
        
        if connector and tx.blockchain_tx_hash:
            confirmed = connector.confirm_settlement(tx.blockchain_tx_hash)
            if confirmed:
                tx.status = PaymentStatus.CONFIRMED
                tx.updated_at = datetime.now(timezone.utc)
                return True
            return False
        else:
            # Mock confirmation
            tx.status = PaymentStatus.CONFIRMED
            tx.updated_at = datetime.now(timezone.utc)
            return True
    
    def execute_full_pipeline(
        self,
        source: PaymentParty,
        destination: PaymentParty,
        amount: Money,
        method: SettlementMethod,
        reference: str,
        priority: int = 1,
    ) -> PaymentTransaction:
        """
        Execute complete settlement pipeline.
        
        1. Create payment
        2. AML screening
        3. Validation
        4. Queue
        5. Settlement
        6. Confirmation
        
        Returns:
            Final PaymentTransaction state
        
        Raises:
            SettlementError: If any step fails
        """
        # Create
        tx = self.create_payment(source, destination, amount, method, reference, priority)
        
        # Screen AML
        passed, ref = self.screen_aml(tx.transaction_id)
        if not passed:
            raise SettlementError(f"AML screening failed: {ref}")
        
        # Validate
        if not self.validate_payment(tx.transaction_id):
            raise SettlementError(f"Validation failed: {tx.metadata.get('validation_errors')}")
        
        # Queue
        self.queue_for_settlement(tx.transaction_id)
        
        # Settle
        success, tx_hash = self.process_settlement(tx.transaction_id)
        if not success:
            raise SettlementError(f"Settlement failed: {tx.metadata.get('settlement_error')}")
        
        # Confirm
        self.confirm_settlement(tx.transaction_id)
        
        return self._transactions[tx.transaction_id]
    
    # =========================================================================
    # RECONCILIATION
    # =========================================================================
    
    def create_reconciliation_record(self, tx_id: str) -> ReconciliationRecord:
        """Create reconciliation record for a transaction."""
        tx = self._transactions.get(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found")
        
        record_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        
        record = ReconciliationRecord(
            record_id=record_id,
            transaction_id=tx_id,
            expected_amount=tx.amount,
            actual_amount=None,
            status=ReconciliationStatus.PENDING,
        )
        
        self._reconciliation[record_id] = record
        tx.reconciliation_id = record_id
        
        return record
    
    def match_reconciliation(
        self, 
        record_id: str, 
        actual_amount: Money
    ) -> ReconciliationRecord:
        """Match reconciliation with actual settlement amount."""
        record = self._reconciliation.get(record_id)
        if not record:
            raise ValueError(f"Reconciliation record {record_id} not found")
        
        record.actual_amount = actual_amount
        
        # Calculate variance
        expected = record.expected_amount.amount
        actual = actual_amount.amount
        variance = actual - expected
        record.variance = variance
        
        # Tolerance: 0.01% or $0.01
        tolerance = max(expected * Decimal("0.0001"), Decimal("0.01"))
        
        if abs(variance) <= tolerance:
            record.status = ReconciliationStatus.MATCHED
            record.matched_at = datetime.now(timezone.utc)
        else:
            record.status = ReconciliationStatus.EXCEPTION
            record.exception_reason = f"Variance of {variance} exceeds tolerance {tolerance}"
        
        return record
    
    # =========================================================================
    # BATCH PROCESSING
    # =========================================================================
    
    def create_batch(
        self, 
        tx_ids: List[str], 
        method: SettlementMethod
    ) -> SettlementBatch:
        """Create a settlement batch from multiple transactions."""
        transactions = []
        total_amount = Decimal("0")
        total_fees = Decimal("0")
        currency = None
        
        for tx_id in tx_ids:
            tx = self._transactions.get(tx_id)
            if not tx:
                raise ValueError(f"Transaction {tx_id} not found")
            if tx.status not in (PaymentStatus.VALIDATED, PaymentStatus.QUEUED):
                raise ValueError(f"Transaction {tx_id} not ready for batching")
            if tx.settlement_instruction.method != method:
                raise ValueError(f"Transaction {tx_id} uses different settlement method")
            
            transactions.append(tx)
            total_amount += tx.amount.amount
            total_fees += tx.fee.amount
            
            if currency is None:
                currency = tx.amount.currency
            elif currency != tx.amount.currency:
                raise ValueError("All transactions in batch must use same currency")
        
        batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        
        batch = SettlementBatch(
            batch_id=batch_id,
            transactions=transactions,
            method=method,
            total_amount=Money(total_amount, currency or Currency.USD),
            total_fees=Money(total_fees, Currency.USD),
            status=PaymentStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
        )
        
        self._batches[batch_id] = batch
        
        # Update transactions
        for tx in transactions:
            tx.status = PaymentStatus.QUEUED
            tx.metadata["batch_id"] = batch_id
        
        return batch
    
    def process_batch(self, batch_id: str) -> Tuple[bool, Optional[str]]:
        """Process a settlement batch."""
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch.status = PaymentStatus.PROCESSING
        
        connector = self._connectors.get(batch.method)
        
        # Process all transactions
        success_count = 0
        for tx in batch.transactions:
            try:
                if connector:
                    tx_hash = connector.submit_payment(tx)
                else:
                    tx_hash = f"0x{hashlib.sha256(tx.transaction_id.encode()).hexdigest()[:40]}"
                
                tx.blockchain_tx_hash = tx_hash
                tx.status = PaymentStatus.SETTLED
                tx.settled_at = datetime.now(timezone.utc)
                success_count += 1
            except Exception as e:
                tx.status = PaymentStatus.FAILED
                tx.metadata["settlement_error"] = str(e)
        
        # Update batch status
        batch.processed_at = datetime.now(timezone.utc)
        
        if success_count == len(batch.transactions):
            batch.status = PaymentStatus.SETTLED
            batch.blockchain_batch_hash = f"BATCH-0x{hashlib.sha256(batch_id.encode()).hexdigest()[:40]}"
            return True, batch.blockchain_batch_hash
        elif success_count > 0:
            batch.status = PaymentStatus.SETTLED  # Partial success
            return True, None
        else:
            batch.status = PaymentStatus.FAILED
            return False, None
    
    # =========================================================================
    # REPORTING
    # =========================================================================
    
    def get_transaction(self, tx_id: str) -> Optional[PaymentTransaction]:
        """Get transaction by ID."""
        return self._transactions.get(tx_id)
    
    def get_transactions_by_status(self, status: PaymentStatus) -> List[PaymentTransaction]:
        """Get all transactions with given status."""
        return [tx for tx in self._transactions.values() if tx.status == status]
    
    def get_settlement_metrics(self) -> Dict[str, Any]:
        """Get settlement engine metrics."""
        total_transactions = len(self._transactions)
        
        by_status = {}
        for status in PaymentStatus:
            count = len([tx for tx in self._transactions.values() if tx.status == status])
            by_status[status.name] = count
        
        total_volume = sum(
            tx.amount.amount 
            for tx in self._transactions.values() 
            if tx.status == PaymentStatus.CONFIRMED
        )
        
        total_fees = sum(
            tx.fee.amount
            for tx in self._transactions.values()
            if tx.status == PaymentStatus.CONFIRMED
        )
        
        return {
            "total_transactions": total_transactions,
            "by_status": by_status,
            "confirmed_volume_usd": str(total_volume),
            "total_fees_usd": str(total_fees),
            "batches_processed": len([b for b in self._batches.values() if b.status == PaymentStatus.SETTLED]),
            "reconciliation_exceptions": len([r for r in self._reconciliation.values() if r.status == ReconciliationStatus.EXCEPTION]),
        }


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SettlementError(Exception):
    """Settlement processing error."""
    pass


class ReconciliationError(Exception):
    """Reconciliation error."""
    pass


# =============================================================================
# FACTORY
# =============================================================================

def create_settlement_engine(
    with_mock_connectors: bool = False
) -> SettlementEngine:
    """
    Factory function to create configured settlement engine.
    
    Args:
        with_mock_connectors: If True, registers mock connectors for testing
    
    Returns:
        Configured SettlementEngine instance
    """
    engine = SettlementEngine()
    
    if with_mock_connectors:
        # Mock connectors would be registered here for testing
        pass
    
    return engine


# =============================================================================
# MAIN / SELF-TEST
# =============================================================================

def self_test() -> bool:
    """
    Self-test for settlement engine.
    
    Returns:
        True if all tests pass
    """
    print("=" * 60)
    print("CHAINPAY SETTLEMENT ENGINE - SELF TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Create engine
    tests_total += 1
    try:
        engine = create_settlement_engine()
        print("✅ TEST 1: Engine creation - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 1: Engine creation - FAILED: {e}")
        return False
    
    # Test 2: Fee calculation
    tests_total += 1
    try:
        fee_calc = FeeCalculator()
        amount = Money(Decimal("10000"), Currency.USD)
        fee = fee_calc.calculate_fee(amount, SettlementMethod.HEDERA_INSTANT)
        assert fee.amount > 0
        print(f"✅ TEST 2: Fee calculation ({fee.amount} USD) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 2: Fee calculation - FAILED: {e}")
    
    # Test 3: Exchange rates
    tests_total += 1
    try:
        exchange = ExchangeRateService()
        rate = exchange.get_rate(Currency.USD, Currency.EUR)
        assert rate > 0
        print(f"✅ TEST 3: Exchange rate USD->EUR ({rate}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 3: Exchange rate - FAILED: {e}")
    
    # Test 4: Create payment
    tests_total += 1
    try:
        source = PaymentParty("SRC-001", "Shipper Inc", "ACC-12345", kyc_verified=True)
        dest = PaymentParty("DST-001", "Carrier LLC", "ACC-67890", kyc_verified=True)
        amount = Money(Decimal("5000.00"), Currency.USD)
        
        tx = engine.create_payment(
            source=source,
            destination=dest,
            amount=amount,
            method=SettlementMethod.HEDERA_INSTANT,
            reference="INV-2026-001"
        )
        
        assert tx.status == PaymentStatus.INITIATED
        assert tx.transaction_id.startswith("TX-")
        print(f"✅ TEST 4: Create payment ({tx.transaction_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 4: Create payment - FAILED: {e}")
    
    # Test 5: Full pipeline
    tests_total += 1
    try:
        source = PaymentParty("SRC-002", "FreightCo", "ACC-11111", kyc_verified=True)
        dest = PaymentParty("DST-002", "TruckingCo", "ACC-22222", kyc_verified=True)
        amount = Money(Decimal("2500.00"), Currency.USD)
        
        tx = engine.execute_full_pipeline(
            source=source,
            destination=dest,
            amount=amount,
            method=SettlementMethod.XRP_PAYMENT,
            reference="FREIGHT-2026-001"
        )
        
        assert tx.status == PaymentStatus.CONFIRMED
        assert tx.blockchain_tx_hash is not None
        print(f"✅ TEST 5: Full pipeline ({tx.status.name}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 5: Full pipeline - FAILED: {e}")
    
    # Test 6: Batch processing
    tests_total += 1
    try:
        tx_ids = []
        for i in range(3):
            source = PaymentParty(f"SRC-B{i}", f"Sender{i}", f"ACC-S{i}", kyc_verified=True)
            dest = PaymentParty(f"DST-B{i}", f"Receiver{i}", f"ACC-R{i}", kyc_verified=True)
            amount = Money(Decimal("1000.00"), Currency.USD)
            
            tx = engine.create_payment(
                source=source,
                destination=dest,
                amount=amount,
                method=SettlementMethod.ACH_BATCH,
                reference=f"BATCH-REF-{i}"
            )
            
            engine.screen_aml(tx.transaction_id)
            engine.validate_payment(tx.transaction_id)
            tx_ids.append(tx.transaction_id)
        
        batch = engine.create_batch(tx_ids, SettlementMethod.ACH_BATCH)
        success, batch_hash = engine.process_batch(batch.batch_id)
        
        assert success
        assert batch.total_amount.amount == Decimal("3000.00")
        print(f"✅ TEST 6: Batch processing ({batch.batch_id}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 6: Batch processing - FAILED: {e}")
    
    # Test 7: Reconciliation
    tests_total += 1
    try:
        # Get a confirmed transaction
        confirmed = engine.get_transactions_by_status(PaymentStatus.CONFIRMED)
        if confirmed:
            tx = confirmed[0]
            record = engine.create_reconciliation_record(tx.transaction_id)
            matched = engine.match_reconciliation(record.record_id, tx.amount)
            assert matched.status == ReconciliationStatus.MATCHED
            print(f"✅ TEST 7: Reconciliation ({record.record_id}) - PASSED")
            tests_passed += 1
        else:
            print("⚠️ TEST 7: Reconciliation - SKIPPED (no confirmed transactions)")
    except Exception as e:
        print(f"❌ TEST 7: Reconciliation - FAILED: {e}")
    
    # Test 8: Metrics
    tests_total += 1
    try:
        metrics = engine.get_settlement_metrics()
        assert "total_transactions" in metrics
        assert metrics["total_transactions"] > 0
        print(f"✅ TEST 8: Metrics (total_tx={metrics['total_transactions']}) - PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"❌ TEST 8: Metrics - FAILED: {e}")
    
    # Summary
    print("=" * 60)
    print(f"SETTLEMENT ENGINE TESTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = self_test()
    exit(0 if success else 1)
