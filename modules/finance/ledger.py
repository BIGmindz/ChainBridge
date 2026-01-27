"""
ChainBridge Double-Entry Ledger
===============================

The heart of the Invisible Bank. A cryptographically verifiable,
immutable ledger that tracks all value movement within the system.

CORE PRINCIPLES:
1. Conservation of Value: Sum(Debits) == Sum(Credits) ALWAYS
2. Immutability: Posted entries cannot be modified, only reversed
3. Precision: All math uses Decimal (NEVER floats)
4. Atomicity: Transactions either fully commit or fully rollback

INVARIANTS:
- INV-FIN-001: Conservation of Value
- INV-FIN-002: Immutability of Posted Entries

PAC: PAC-FIN-P200-INVISIBLE-BANK-INIT
Created: 2026-01-11
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import json
import uuid


# =============================================================================
# EXCEPTIONS
# =============================================================================

class LedgerError(Exception):
    """Base exception for all ledger errors."""


class InsufficientFundsError(LedgerError):
    """Raised when an account has insufficient funds for a debit."""
    
    def __init__(self, account_id: str, required: Decimal, available: Decimal):
        self.account_id = account_id
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient funds in account {account_id}: "
            f"required {required}, available {available}"
        )


class BalanceViolationError(LedgerError):
    """Raised when a transaction would violate the conservation of value."""
    
    def __init__(self, debits: Decimal, credit_amount: Decimal):
        self.debits = debits
        self.credits = credit_amount
        super().__init__(
            f"Balance violation: debits ({debits}) != credits ({credit_amount}). "
            f"INV-FIN-001 violated."
        )


class ImmutabilityViolationError(LedgerError):
    """Raised when attempting to modify a posted entry."""
    
    def __init__(self, entry_id: str):
        self.entry_id = entry_id
        super().__init__(
            f"Cannot modify posted entry {entry_id}. "
            f"INV-FIN-002 violated. Use reversal instead."
        )


class AccountNotFoundError(LedgerError):
    """Raised when referencing a non-existent account."""
    
    def __init__(self, account_id: str):
        self.account_id = account_id
        super().__init__(f"Account not found: {account_id}")


class NegativeAmountError(LedgerError):
    """Raised when attempting to use a negative amount."""
    
    def __init__(self, amount: Decimal):
        self.amount = amount
        super().__init__(f"Amounts must be positive: {amount}")


# =============================================================================
# ENUMS
# =============================================================================

class AccountType(Enum):
    """
    Standard accounting classifications.
    
    The accounting equation: Assets = Liabilities + Equity
    Extended: Assets + Expenses = Liabilities + Equity + Revenue
    """
    ASSET = "asset"           # What we own (increases with debit)
    LIABILITY = "liability"   # What we owe (increases with credit)
    EQUITY = "equity"         # Owner's stake (increases with credit)
    REVENUE = "revenue"       # Income (increases with credit)
    EXPENSE = "expense"       # Costs (increases with debit)
    
    # Special ChainBridge account types
    SETTLEMENT = "settlement"     # Pending settlements (asset-like)
    ESCROW = "escrow"            # Held funds (liability-like)
    FEE_REVENUE = "fee_revenue"  # Platform fees (revenue)
    SUSPENSE = "suspense"        # Unclassified entries (temporary)


class TransactionStatus(Enum):
    """Transaction lifecycle states."""
    PENDING = "pending"       # Created but not yet posted
    POSTED = "posted"         # Committed to ledger (IMMUTABLE)
    REVERSED = "reversed"     # Cancelled via reversal entry
    FAILED = "failed"         # Failed validation


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Account:
    """
    A ledger account that can hold a balance.
    
    Follows standard double-entry conventions:
    - Asset/Expense accounts: Debit increases, Credit decreases
    - Liability/Equity/Revenue accounts: Credit increases, Debit decreases
    """
    account_id: str
    name: str
    account_type: AccountType
    currency: str = "USD"
    balance: Decimal = field(default_factory=lambda: Decimal("0.00"))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    allow_negative: bool = False  # Only true for special accounts (e.g., credit lines)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure balance is Decimal."""
        if not isinstance(self.balance, Decimal):
            self.balance = Decimal(str(self.balance))
        self.balance = self.balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def debit_increases_balance(self) -> bool:
        """Returns True if debits increase this account's balance."""
        return self.account_type in (
            AccountType.ASSET,
            AccountType.EXPENSE,
            AccountType.SETTLEMENT,
            AccountType.ESCROW,  # Escrow holds funds like an asset
        )
    
    def apply_debit(self, amount: Decimal) -> Decimal:
        """Apply a debit to this account. Returns new balance."""
        if self.debit_increases_balance():
            self.balance += amount
        else:
            self.balance -= amount
        self.balance = self.balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.balance
    
    def apply_credit(self, amount: Decimal) -> Decimal:
        """Apply a credit to this account. Returns new balance."""
        if self.debit_increases_balance():
            self.balance -= amount
        else:
            self.balance += amount
        self.balance = self.balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.balance
    
    def to_dict(self) -> Dict:
        """Serialize account for JSON."""
        return {
            "account_id": self.account_id,
            "name": self.name,
            "account_type": self.account_type.value,
            "currency": self.currency,
            "balance": str(self.balance),
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "allow_negative": self.allow_negative,
            "metadata": self.metadata,
        }


@dataclass
class Entry:
    """
    A single debit or credit entry in the ledger.
    
    Entries are always part of a Transaction and cannot exist alone.
    """
    entry_id: str
    transaction_id: str
    account_id: str
    amount: Decimal
    is_debit: bool  # True = debit, False = credit
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure amount is positive Decimal."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        self.amount = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if self.amount < 0:
            raise NegativeAmountError(self.amount)
    
    @property
    def entry_type(self) -> str:
        """Return 'debit' or 'credit'."""
        return "debit" if self.is_debit else "credit"
    
    def to_dict(self) -> Dict:
        """Serialize entry for JSON/hashing."""
        return {
            "entry_id": self.entry_id,
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "amount": str(self.amount),
            "is_debit": self.is_debit,
            "entry_type": self.entry_type,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class Transaction:
    """
    An atomic unit of value transfer containing balanced entries.
    
    INVARIANT: Sum of debits MUST equal sum of credits.
    """
    transaction_id: str
    entries: List[Entry] = field(default_factory=list)
    status: TransactionStatus = TransactionStatus.PENDING
    description: str = ""
    reference: str = ""  # External reference (e.g., payment ID)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    posted_at: Optional[datetime] = None
    previous_hash: str = ""  # Hash chain link
    transaction_hash: str = ""  # This transaction's hash
    metadata: Dict = field(default_factory=dict)
    
    def add_entry(self, account_id: str, amount: Decimal, is_debit: bool, 
                  description: str = "", metadata: Optional[Dict] = None) -> Entry:
        """Add an entry to this transaction."""
        if self.status == TransactionStatus.POSTED:
            raise ImmutabilityViolationError(self.transaction_id)
        
        entry = Entry(
            entry_id=str(uuid.uuid4()),
            transaction_id=self.transaction_id,
            account_id=account_id,
            amount=amount,
            is_debit=is_debit,
            description=description,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        return entry
    
    def debit(self, account_id: str, amount: Decimal, 
              description: str = "", metadata: Optional[Dict] = None) -> Entry:
        """Convenience method to add a debit entry."""
        return self.add_entry(account_id, amount, True, description, metadata)
    
    def credit(self, account_id: str, amount: Decimal,
               description: str = "", metadata: Optional[Dict] = None) -> Entry:
        """Convenience method to add a credit entry."""
        return self.add_entry(account_id, amount, False, description, metadata)
    
    @property
    def total_debits(self) -> Decimal:
        """Sum of all debit entries."""
        return sum(
            (e.amount for e in self.entries if e.is_debit),
            Decimal("0.00")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @property
    def total_credits(self) -> Decimal:
        """Sum of all credit entries."""
        return sum(
            (e.amount for e in self.entries if not e.is_debit),
            Decimal("0.00")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @property
    def is_balanced(self) -> bool:
        """Check if debits equal credits (INV-FIN-001)."""
        return self.total_debits == self.total_credits
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this transaction for chain integrity."""
        data = {
            "transaction_id": self.transaction_id,
            "entries": [e.to_dict() for e in self.entries],
            "description": self.description,
            "reference": self.reference,
            "created_at": self.created_at.isoformat(),
            "previous_hash": self.previous_hash,
        }
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Serialize transaction for JSON."""
        return {
            "transaction_id": self.transaction_id,
            "status": self.status.value,
            "description": self.description,
            "reference": self.reference,
            "entries": [e.to_dict() for e in self.entries],
            "total_debits": str(self.total_debits),
            "total_credits": str(self.total_credits),
            "is_balanced": self.is_balanced,
            "created_at": self.created_at.isoformat(),
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "previous_hash": self.previous_hash,
            "transaction_hash": self.transaction_hash,
            "metadata": self.metadata,
        }


# =============================================================================
# LEDGER - THE CORE
# =============================================================================

class Ledger:
    """
    The Double-Entry Ledger - Heart of the Invisible Bank.
    
    Provides:
    - Account management
    - Atomic transaction processing
    - Balance enforcement
    - Cryptographic audit trail (hash chain)
    
    INVARIANTS:
    - INV-FIN-001: Sum(Debits) == Sum(Credits) for every transaction
    - INV-FIN-002: Posted entries are immutable
    """
    
    def __init__(self, ledger_id: Optional[str] = None):
        """Initialize a new ledger."""
        self.ledger_id = ledger_id or str(uuid.uuid4())
        self.accounts: Dict[str, Account] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.posted_transactions: List[str] = []  # Ordered list for hash chain
        self.genesis_hash: str = self._compute_genesis_hash()
        self.last_hash: str = self.genesis_hash
        self.created_at: datetime = datetime.now(timezone.utc)
        
        # Audit counters
        self._total_debits_posted: Decimal = Decimal("0.00")
        self._total_credits_posted: Decimal = Decimal("0.00")
    
    def _compute_genesis_hash(self) -> str:
        """Compute the genesis block hash."""
        genesis_data = {
            "ledger_id": self.ledger_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": "IN THE BEGINNING, THERE WAS THE LEDGER",
            "invariants": ["INV-FIN-001", "INV-FIN-002"],
        }
        serialized = json.dumps(genesis_data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    # =========================================================================
    # ACCOUNT MANAGEMENT
    # =========================================================================
    
    def create_account(
        self,
        name: str,
        account_type: AccountType,
        currency: str = "USD",
        account_id: Optional[str] = None,
        allow_negative: bool = False,
        metadata: Optional[Dict] = None,
    ) -> Account:
        """
        Create a new account in the ledger.
        
        Args:
            name: Human-readable account name
            account_type: Classification (asset, liability, etc.)
            currency: ISO currency code
            account_id: Optional custom ID (auto-generated if not provided)
            allow_negative: Whether account can go negative
            metadata: Additional account data
            
        Returns:
            The created Account
        """
        account_id = account_id or str(uuid.uuid4())
        
        if account_id in self.accounts:
            raise LedgerError(f"Account {account_id} already exists")
        
        account = Account(
            account_id=account_id,
            name=name,
            account_type=account_type,
            currency=currency,
            allow_negative=allow_negative,
            metadata=metadata or {},
        )
        
        self.accounts[account_id] = account
        return account
    
    def get_account(self, account_id: str) -> Account:
        """Get an account by ID."""
        if account_id not in self.accounts:
            raise AccountNotFoundError(account_id)
        return self.accounts[account_id]
    
    def get_balance(self, account_id: str) -> Decimal:
        """Get the current balance of an account."""
        return self.get_account(account_id).balance
    
    # =========================================================================
    # TRANSACTION PROCESSING
    # =========================================================================
    
    def create_transaction(
        self,
        description: str = "",
        reference: str = "",
        metadata: Optional[Dict] = None,
    ) -> Transaction:
        """
        Create a new pending transaction.
        
        The transaction must be populated with balanced entries
        and then posted with post_transaction().
        
        Args:
            description: Human-readable description
            reference: External reference ID
            metadata: Additional transaction data
            
        Returns:
            A new pending Transaction
        """
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            description=description,
            reference=reference,
            metadata=metadata or {},
        )
        
        self.transactions[transaction.transaction_id] = transaction
        return transaction
    
    def post_transaction(self, transaction_id: str) -> Transaction:
        """
        Post a transaction to the ledger (ATOMIC).
        
        This is the critical method that:
        1. Validates balance (INV-FIN-001)
        2. Checks sufficient funds
        3. Applies all entries atomically
        4. Updates the hash chain
        5. Marks transaction as POSTED (immutable)
        
        Args:
            transaction_id: ID of the transaction to post
            
        Returns:
            The posted Transaction
            
        Raises:
            BalanceViolationError: If debits != credits
            InsufficientFundsError: If any account lacks funds
            AccountNotFoundError: If any entry references unknown account
        """
        if transaction_id not in self.transactions:
            raise LedgerError(f"Transaction {transaction_id} not found")
        
        transaction = self.transactions[transaction_id]
        
        if transaction.status == TransactionStatus.POSTED:
            raise ImmutabilityViolationError(transaction_id)
        
        if not transaction.entries:
            raise LedgerError("Cannot post empty transaction")
        
        # INVARIANT CHECK: INV-FIN-001 - Conservation of Value
        if not transaction.is_balanced:
            transaction.status = TransactionStatus.FAILED
            raise BalanceViolationError(
                transaction.total_debits,
                transaction.total_credits
            )
        
        # VALIDATION PASS: Check all accounts exist and have sufficient funds
        balance_changes: Dict[str, Decimal] = {}
        
        for entry in transaction.entries:
            account = self.get_account(entry.account_id)
            
            # Calculate projected balance change
            if entry.account_id not in balance_changes:
                balance_changes[entry.account_id] = Decimal("0.00")
            
            if entry.is_debit:
                if account.debit_increases_balance():
                    balance_changes[entry.account_id] += entry.amount
                else:
                    balance_changes[entry.account_id] -= entry.amount
            else:
                if account.debit_increases_balance():
                    balance_changes[entry.account_id] -= entry.amount
                else:
                    balance_changes[entry.account_id] += entry.amount
        
        # Check for negative balances (where not allowed)
        for account_id, change in balance_changes.items():
            account = self.accounts[account_id]
            projected_balance = account.balance + change
            
            if projected_balance < 0 and not account.allow_negative:
                transaction.status = TransactionStatus.FAILED
                raise InsufficientFundsError(
                    account_id,
                    required=abs(change),
                    available=account.balance
                )
        
        # COMMIT PASS: Apply all entries (atomic)
        for entry in transaction.entries:
            account = self.accounts[entry.account_id]
            if entry.is_debit:
                account.apply_debit(entry.amount)
            else:
                account.apply_credit(entry.amount)
        
        # Update hash chain
        transaction.previous_hash = self.last_hash
        transaction.transaction_hash = transaction.compute_hash()
        self.last_hash = transaction.transaction_hash
        
        # Mark as posted
        transaction.status = TransactionStatus.POSTED
        transaction.posted_at = datetime.now(timezone.utc)
        self.posted_transactions.append(transaction_id)
        
        # Update audit totals
        self._total_debits_posted += transaction.total_debits
        self._total_credits_posted += transaction.total_credits
        
        return transaction
    
    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: Decimal,
        description: str = "",
        reference: str = "",
        metadata: Optional[Dict] = None,
    ) -> Transaction:
        """
        Convenience method: Create and post a simple A→B transfer.
        
        Args:
            from_account: Source account ID (will be credited)
            to_account: Destination account ID (will be debited)
            amount: Transfer amount (positive Decimal)
            description: Transaction description
            reference: External reference
            metadata: Additional data
            
        Returns:
            The posted Transaction
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if amount <= 0:
            raise NegativeAmountError(amount)
        
        # Create transaction
        txn = self.create_transaction(
            description=description or f"Transfer {amount} from {from_account} to {to_account}",
            reference=reference,
            metadata=metadata,
        )
        
        # For asset accounts:
        # - Debit TO account (increases balance)
        # - Credit FROM account (decreases balance)
        txn.debit(to_account, amount, f"Received from {from_account}")
        txn.credit(from_account, amount, f"Sent to {to_account}")
        
        # Post and return
        return self.post_transaction(txn.transaction_id)
    
    def reverse_transaction(
        self,
        transaction_id: str,
        reason: str = "",
    ) -> Transaction:
        """
        Create a reversal transaction (the only way to 'undo' a posted entry).
        
        INV-FIN-002 mandates that we never modify posted entries.
        Instead, we create an equal and opposite transaction.
        
        Args:
            transaction_id: ID of the transaction to reverse
            reason: Reason for reversal
            
        Returns:
            The reversal Transaction (posted)
        """
        original = self.transactions.get(transaction_id)
        if not original:
            raise LedgerError(f"Transaction {transaction_id} not found")
        
        if original.status != TransactionStatus.POSTED:
            raise LedgerError("Can only reverse posted transactions")
        
        if original.status == TransactionStatus.REVERSED:
            raise LedgerError(f"Transaction {transaction_id} already reversed")
        
        # Create reversal transaction
        reversal = self.create_transaction(
            description=f"REVERSAL: {reason or original.description}",
            reference=f"REV-{transaction_id[:8]}",
            metadata={
                "reverses": transaction_id,
                "reason": reason,
                "original_description": original.description,
            },
        )
        
        # Swap debits and credits
        for entry in original.entries:
            reversal.add_entry(
                account_id=entry.account_id,
                amount=entry.amount,
                is_debit=not entry.is_debit,  # Flip the direction
                description=f"Reversal of {entry.entry_id}",
                metadata={"reverses_entry": entry.entry_id},
            )
        
        # Post the reversal
        self.post_transaction(reversal.transaction_id)
        
        # Mark original as reversed
        original.status = TransactionStatus.REVERSED
        original.metadata["reversed_by"] = reversal.transaction_id
        
        return reversal
    
    # =========================================================================
    # AUDIT & VERIFICATION
    # =========================================================================
    
    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """
        Verify the hash chain integrity of all posted transactions.
        
        Returns:
            (is_valid, message)
        """
        if not self.posted_transactions:
            return True, "No transactions to verify"
        
        expected_hash = self.genesis_hash
        
        for txn_id in self.posted_transactions:
            txn = self.transactions[txn_id]
            
            if txn.previous_hash != expected_hash:
                return False, f"Chain broken at {txn_id}: previous_hash mismatch"
            
            computed_hash = txn.compute_hash()
            if computed_hash != txn.transaction_hash:
                return False, f"Chain broken at {txn_id}: transaction_hash mismatch"
            
            expected_hash = txn.transaction_hash
        
        return True, f"Chain valid: {len(self.posted_transactions)} transactions verified"
    
    def verify_conservation(self) -> Tuple[bool, str]:
        """
        Verify INV-FIN-001: Total debits == Total credits across all time.
        
        Returns:
            (is_valid, message)
        """
        if self._total_debits_posted != self._total_credits_posted:
            return False, (
                f"Conservation violated: "
                f"debits={self._total_debits_posted}, "
                f"credits={self._total_credits_posted}"
            )
        
        return True, (
            f"Conservation verified: "
            f"{self._total_debits_posted} in balanced transactions"
        )
    
    def get_audit_summary(self) -> Dict:
        """Generate a comprehensive audit summary."""
        is_chain_valid, chain_message = self.verify_chain_integrity()
        is_balanced, balance_message = self.verify_conservation()
        
        return {
            "ledger_id": self.ledger_id,
            "created_at": self.created_at.isoformat(),
            "genesis_hash": self.genesis_hash,
            "last_hash": self.last_hash,
            "total_accounts": len(self.accounts),
            "total_transactions": len(self.transactions),
            "posted_transactions": len(self.posted_transactions),
            "total_debits": str(self._total_debits_posted),
            "total_credits": str(self._total_credits_posted),
            "chain_integrity": {
                "valid": is_chain_valid,
                "message": chain_message,
            },
            "conservation_of_value": {
                "valid": is_balanced,
                "message": balance_message,
            },
            "invariants_enforced": [
                "INV-FIN-001 (Conservation of Value)",
                "INV-FIN-002 (Immutability)",
            ],
        }
    
    def to_dict(self) -> Dict:
        """Serialize full ledger state for persistence."""
        return {
            "ledger_id": self.ledger_id,
            "created_at": self.created_at.isoformat(),
            "genesis_hash": self.genesis_hash,
            "last_hash": self.last_hash,
            "accounts": {k: v.to_dict() for k, v in self.accounts.items()},
            "transactions": {k: v.to_dict() for k, v in self.transactions.items()},
            "posted_transactions": self.posted_transactions,
            "audit_totals": {
                "total_debits": str(self._total_debits_posted),
                "total_credits": str(self._total_credits_posted),
            },
        }
