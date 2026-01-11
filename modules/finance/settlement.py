"""
ChainBridge Settlement Engine
=============================

The Cashier of the Invisible Bank. Manages the complete transaction
lifecycle with Two-Phase Commit semantics:

    CREATED → AUTHORIZED → CAPTURED
                ↓
              VOIDED

CORE PRINCIPLES:
1. Two-Phase Commit: Authorize (hold) → Capture (transfer)
2. Idempotency: Replay produces same result without side effects
3. Lifecycle Safety: No capture without prior authorization
4. Timeout Protection: Stale authorizations auto-expire

INVARIANTS:
- INV-FIN-003: Idempotency
- INV-FIN-004: Lifecycle Safety

PAC: PAC-FIN-P201-SETTLEMENT-ENGINE
Created: 2026-01-11
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import uuid

from modules.finance.ledger import (
    Ledger, Account, AccountType, Transaction, TransactionStatus,
    LedgerError, InsufficientFundsError
)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SettlementError(Exception):
    """Base exception for settlement errors."""
    pass


class IdempotencyViolationError(SettlementError):
    """Raised when a duplicate request has conflicting parameters."""
    
    def __init__(self, idempotency_key: str, original_intent_id: str):
        self.idempotency_key = idempotency_key
        self.original_intent_id = original_intent_id
        super().__init__(
            f"Idempotency key '{idempotency_key}' already used for intent "
            f"'{original_intent_id}' with different parameters"
        )


class LifecycleViolationError(SettlementError):
    """Raised when attempting an invalid state transition."""
    
    def __init__(self, intent_id: str, current_state: str, attempted_action: str):
        self.intent_id = intent_id
        self.current_state = current_state
        self.attempted_action = attempted_action
        super().__init__(
            f"Cannot {attempted_action} intent '{intent_id}' in state '{current_state}'. "
            f"INV-FIN-004 violated."
        )


class AmountExceedsAuthorizationError(SettlementError):
    """Raised when capture amount exceeds authorized amount."""
    
    def __init__(self, intent_id: str, authorized: Decimal, requested: Decimal):
        self.intent_id = intent_id
        self.authorized = authorized
        self.requested = requested
        super().__init__(
            f"Capture amount {requested} exceeds authorization {authorized} "
            f"for intent '{intent_id}'"
        )


class AuthorizationExpiredError(SettlementError):
    """Raised when attempting to capture an expired authorization."""
    
    def __init__(self, intent_id: str, expired_at: datetime):
        self.intent_id = intent_id
        self.expired_at = expired_at
        super().__init__(
            f"Authorization for intent '{intent_id}' expired at {expired_at.isoformat()}"
        )


class IntentNotFoundError(SettlementError):
    """Raised when referencing a non-existent payment intent."""
    
    def __init__(self, intent_id: str):
        self.intent_id = intent_id
        super().__init__(f"Payment intent not found: {intent_id}")


# =============================================================================
# ENUMS
# =============================================================================

class IntentStatus(Enum):
    """
    Payment Intent state machine.
    
    State Transitions:
        CREATED → AUTHORIZED → CAPTURED (terminal)
                      ↓
                   VOIDED (terminal)
        CREATED → FAILED (terminal)
    """
    CREATED = "created"           # Intent created, not yet authorized
    AUTHORIZED = "authorized"     # Funds held, awaiting capture
    CAPTURED = "captured"         # Funds transferred (terminal)
    VOIDED = "voided"            # Authorization cancelled (terminal)
    FAILED = "failed"            # Authorization failed (terminal)
    EXPIRED = "expired"          # Authorization timed out (terminal)
    
    @property
    def is_terminal(self) -> bool:
        """Returns True if this is a terminal (final) state."""
        return self in (
            IntentStatus.CAPTURED,
            IntentStatus.VOIDED,
            IntentStatus.FAILED,
            IntentStatus.EXPIRED,
        )


class CaptureType(Enum):
    """Type of capture operation."""
    FULL = "full"           # Capture entire authorized amount
    PARTIAL = "partial"     # Capture less than authorized


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class PaymentIntent:
    """
    A payment intent representing a pending financial transaction.
    
    Follows the Two-Phase Commit pattern:
    1. Create Intent → specify source, destination, amount
    2. Authorize → hold funds on source account
    3. Capture → execute actual transfer
    
    Alternative paths:
    - Void → release held funds
    - Expire → auto-release after timeout
    """
    intent_id: str
    idempotency_key: str
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str = "USD"
    status: IntentStatus = IntentStatus.CREATED
    
    # Authorization details
    authorized_at: Optional[datetime] = None
    authorization_expires_at: Optional[datetime] = None
    hold_transaction_id: Optional[str] = None
    
    # Capture details
    captured_at: Optional[datetime] = None
    captured_amount: Optional[Decimal] = None
    capture_transaction_id: Optional[str] = None
    
    # Void details
    voided_at: Optional[datetime] = None
    void_reason: str = ""
    void_transaction_id: Optional[str] = None
    
    # Metadata
    description: str = ""
    reference: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)
    
    # Audit trail
    events: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure amount is Decimal."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        self.amount = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def add_event(self, event_type: str, details: Dict = None):
        """Record an event in the audit trail."""
        self.events.append({
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        })
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def is_expired(self) -> bool:
        """Check if authorization has expired."""
        if self.status != IntentStatus.AUTHORIZED:
            return False
        if not self.authorization_expires_at:
            return False
        return datetime.now(timezone.utc) > self.authorization_expires_at
    
    @property
    def can_capture(self) -> bool:
        """Check if this intent can be captured."""
        return (
            self.status == IntentStatus.AUTHORIZED and
            not self.is_expired
        )
    
    @property
    def can_void(self) -> bool:
        """Check if this intent can be voided."""
        return self.status in (IntentStatus.CREATED, IntentStatus.AUTHORIZED)
    
    @property
    def remaining_capturable(self) -> Decimal:
        """Amount still available to capture (for partial captures)."""
        if self.status != IntentStatus.AUTHORIZED:
            return Decimal("0.00")
        captured = self.captured_amount or Decimal("0.00")
        return self.amount - captured
    
    def to_dict(self) -> Dict:
        """Serialize intent for JSON."""
        return {
            "intent_id": self.intent_id,
            "idempotency_key": self.idempotency_key,
            "source_account": self.source_account,
            "destination_account": self.destination_account,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "authorized_at": self.authorized_at.isoformat() if self.authorized_at else None,
            "authorization_expires_at": self.authorization_expires_at.isoformat() if self.authorization_expires_at else None,
            "hold_transaction_id": self.hold_transaction_id,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "captured_amount": str(self.captured_amount) if self.captured_amount else None,
            "capture_transaction_id": self.capture_transaction_id,
            "voided_at": self.voided_at.isoformat() if self.voided_at else None,
            "void_reason": self.void_reason,
            "description": self.description,
            "reference": self.reference,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "events": self.events,
        }


# =============================================================================
# SETTLEMENT ENGINE
# =============================================================================

class SettlementEngine:
    """
    The Cashier of the Invisible Bank.
    
    Manages the complete payment lifecycle with Two-Phase Commit:
    1. create_intent() - Declare intention to move funds
    2. authorize() - Hold funds on source account
    3. capture() - Execute actual transfer
    4. void() - Release held funds
    
    INVARIANTS:
    - INV-FIN-003: Idempotency (replaying = same result)
    - INV-FIN-004: Lifecycle Safety (no capture without auth)
    """
    
    # Default authorization hold time (7 days)
    DEFAULT_AUTH_TTL = timedelta(days=7)
    
    def __init__(self, ledger: Ledger):
        """
        Initialize the Settlement Engine.
        
        Args:
            ledger: The underlying Ledger for posting transactions
        """
        self.ledger = ledger
        self.intents: Dict[str, PaymentIntent] = {}
        self.idempotency_index: Dict[str, str] = {}  # key -> intent_id
        
        # Ensure escrow account exists for holding funds
        self._ensure_escrow_account()
        
        # Metrics
        self._total_authorized: Decimal = Decimal("0.00")
        self._total_captured: Decimal = Decimal("0.00")
        self._total_voided: Decimal = Decimal("0.00")
    
    def _ensure_escrow_account(self):
        """Ensure the system escrow account exists."""
        escrow_id = "SYSTEM-ESCROW-001"
        if escrow_id not in self.ledger.accounts:
            self.ledger.create_account(
                account_id=escrow_id,
                name="System Escrow",
                account_type=AccountType.ESCROW,
                allow_negative=False,
            )
    
    def _get_escrow_account_id(self) -> str:
        """Get the escrow account ID."""
        return "SYSTEM-ESCROW-001"
    
    # =========================================================================
    # IDEMPOTENCY
    # =========================================================================
    
    def _check_idempotency(
        self,
        idempotency_key: str,
        source_account: str,
        destination_account: str,
        amount: Decimal,
    ) -> Optional[PaymentIntent]:
        """
        Check if this idempotency key was already used.
        
        Returns:
            The existing PaymentIntent if key was used with same params,
            None if key is new.
            
        Raises:
            IdempotencyViolationError if key was used with different params.
        """
        if idempotency_key not in self.idempotency_index:
            return None
        
        existing_intent_id = self.idempotency_index[idempotency_key]
        existing_intent = self.intents[existing_intent_id]
        
        # Verify parameters match (INV-FIN-003)
        if (
            existing_intent.source_account != source_account or
            existing_intent.destination_account != destination_account or
            existing_intent.amount != amount
        ):
            raise IdempotencyViolationError(idempotency_key, existing_intent_id)
        
        # Same key, same params → return existing (idempotent)
        return existing_intent
    
    # =========================================================================
    # PHASE 1: CREATE INTENT
    # =========================================================================
    
    def create_intent(
        self,
        source_account: str,
        destination_account: str,
        amount: Decimal,
        idempotency_key: str = None,
        description: str = "",
        reference: str = "",
        metadata: Dict = None,
    ) -> PaymentIntent:
        """
        Create a new payment intent.
        
        This is the first step in the Two-Phase Commit flow.
        No funds are moved yet.
        
        Args:
            source_account: Account to debit (pay from)
            destination_account: Account to credit (pay to)
            amount: Payment amount
            idempotency_key: Optional key for idempotent requests
            description: Human-readable description
            reference: External reference ID
            metadata: Additional data
            
        Returns:
            The created PaymentIntent
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        if amount <= 0:
            raise SettlementError(f"Amount must be positive: {amount}")
        
        # Generate idempotency key if not provided
        idempotency_key = idempotency_key or str(uuid.uuid4())
        
        # Check idempotency (INV-FIN-003)
        existing = self._check_idempotency(
            idempotency_key, source_account, destination_account, amount
        )
        if existing:
            existing.add_event("idempotent_replay", {"action": "create_intent"})
            return existing
        
        # Validate accounts exist
        self.ledger.get_account(source_account)
        self.ledger.get_account(destination_account)
        
        # Create the intent
        intent = PaymentIntent(
            intent_id=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            source_account=source_account,
            destination_account=destination_account,
            amount=amount,
            description=description,
            reference=reference,
            metadata=metadata or {},
        )
        
        intent.add_event("created", {
            "source": source_account,
            "destination": destination_account,
            "amount": str(amount),
        })
        
        # Index it
        self.intents[intent.intent_id] = intent
        self.idempotency_index[idempotency_key] = intent.intent_id
        
        return intent
    
    # =========================================================================
    # PHASE 2A: AUTHORIZE (HOLD FUNDS)
    # =========================================================================
    
    def authorize(
        self,
        intent_id: str,
        auth_ttl: timedelta = None,
    ) -> PaymentIntent:
        """
        Authorize (hold) funds for a payment intent.
        
        This is the first phase of the Two-Phase Commit.
        Funds are moved from the source account to escrow.
        
        Args:
            intent_id: The intent to authorize
            auth_ttl: How long the authorization is valid (default: 7 days)
            
        Returns:
            The updated PaymentIntent
            
        Raises:
            IntentNotFoundError: If intent doesn't exist
            LifecycleViolationError: If intent is not in CREATED state
            InsufficientFundsError: If source lacks funds
        """
        if intent_id not in self.intents:
            raise IntentNotFoundError(intent_id)
        
        intent = self.intents[intent_id]
        
        # Check lifecycle (INV-FIN-004)
        if intent.status != IntentStatus.CREATED:
            # Idempotency: if already authorized, return as-is
            if intent.status == IntentStatus.AUTHORIZED:
                intent.add_event("idempotent_replay", {"action": "authorize"})
                return intent
            raise LifecycleViolationError(intent_id, intent.status.value, "authorize")
        
        auth_ttl = auth_ttl or self.DEFAULT_AUTH_TTL
        escrow_id = self._get_escrow_account_id()
        
        try:
            # Move funds from source to escrow
            txn = self.ledger.transfer(
                from_account=intent.source_account,
                to_account=escrow_id,
                amount=intent.amount,
                description=f"Authorization hold for {intent_id}",
                reference=f"AUTH-{intent_id[:8]}",
                metadata={"intent_id": intent_id, "type": "authorization_hold"},
            )
            
            # Update intent
            now = datetime.now(timezone.utc)
            intent.status = IntentStatus.AUTHORIZED
            intent.authorized_at = now
            intent.authorization_expires_at = now + auth_ttl
            intent.hold_transaction_id = txn.transaction_id
            
            intent.add_event("authorized", {
                "hold_transaction_id": txn.transaction_id,
                "expires_at": intent.authorization_expires_at.isoformat(),
            })
            
            self._total_authorized += intent.amount
            
            return intent
            
        except InsufficientFundsError:
            intent.status = IntentStatus.FAILED
            intent.add_event("authorization_failed", {"reason": "insufficient_funds"})
            raise
    
    # =========================================================================
    # PHASE 2B: CAPTURE (EXECUTE TRANSFER)
    # =========================================================================
    
    def capture(
        self,
        intent_id: str,
        amount: Decimal = None,
    ) -> PaymentIntent:
        """
        Capture (execute) a previously authorized payment.
        
        This is the second phase of the Two-Phase Commit.
        Funds are moved from escrow to the destination account.
        
        Args:
            intent_id: The intent to capture
            amount: Optional capture amount (for partial captures).
                    If not specified, captures full authorized amount.
                    
        Returns:
            The updated PaymentIntent
            
        Raises:
            IntentNotFoundError: If intent doesn't exist
            LifecycleViolationError: If intent is not AUTHORIZED
            AuthorizationExpiredError: If authorization has expired
            AmountExceedsAuthorizationError: If capture amount > authorized
        """
        if intent_id not in self.intents:
            raise IntentNotFoundError(intent_id)
        
        intent = self.intents[intent_id]
        
        # Check lifecycle (INV-FIN-004)
        if intent.status == IntentStatus.CAPTURED:
            # Idempotency: already captured
            intent.add_event("idempotent_replay", {"action": "capture"})
            return intent
        
        if intent.status != IntentStatus.AUTHORIZED:
            raise LifecycleViolationError(intent_id, intent.status.value, "capture")
        
        # Check expiration
        if intent.is_expired:
            intent.status = IntentStatus.EXPIRED
            intent.add_event("expired", {
                "expired_at": intent.authorization_expires_at.isoformat()
            })
            # Release held funds back to source
            self._release_escrow(intent, "Authorization expired")
            raise AuthorizationExpiredError(intent_id, intent.authorization_expires_at)
        
        # Determine capture amount
        capture_amount = amount if amount is not None else intent.amount
        if not isinstance(capture_amount, Decimal):
            capture_amount = Decimal(str(capture_amount))
        capture_amount = capture_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Validate capture amount
        if capture_amount > intent.remaining_capturable:
            raise AmountExceedsAuthorizationError(
                intent_id, intent.remaining_capturable, capture_amount
            )
        
        if capture_amount <= 0:
            raise SettlementError(f"Capture amount must be positive: {capture_amount}")
        
        escrow_id = self._get_escrow_account_id()
        
        # Move funds from escrow to destination
        txn = self.ledger.transfer(
            from_account=escrow_id,
            to_account=intent.destination_account,
            amount=capture_amount,
            description=f"Capture for {intent_id}",
            reference=f"CAP-{intent_id[:8]}",
            metadata={"intent_id": intent_id, "type": "capture"},
        )
        
        # Update intent
        intent.status = IntentStatus.CAPTURED
        intent.captured_at = datetime.now(timezone.utc)
        intent.captured_amount = capture_amount
        intent.capture_transaction_id = txn.transaction_id
        
        intent.add_event("captured", {
            "capture_transaction_id": txn.transaction_id,
            "amount": str(capture_amount),
            "capture_type": CaptureType.FULL.value if capture_amount == intent.amount else CaptureType.PARTIAL.value,
        })
        
        self._total_captured += capture_amount
        
        # If partial capture, release remaining to source
        remaining = intent.amount - capture_amount
        if remaining > 0:
            self._release_partial(intent, remaining)
        
        return intent
    
    # =========================================================================
    # VOID (CANCEL)
    # =========================================================================
    
    def void(
        self,
        intent_id: str,
        reason: str = "",
    ) -> PaymentIntent:
        """
        Void a payment intent, releasing any held funds.
        
        Args:
            intent_id: The intent to void
            reason: Reason for voiding
            
        Returns:
            The updated PaymentIntent
            
        Raises:
            IntentNotFoundError: If intent doesn't exist
            LifecycleViolationError: If intent cannot be voided
        """
        if intent_id not in self.intents:
            raise IntentNotFoundError(intent_id)
        
        intent = self.intents[intent_id]
        
        # Check if already voided (idempotency)
        if intent.status == IntentStatus.VOIDED:
            intent.add_event("idempotent_replay", {"action": "void"})
            return intent
        
        # Check lifecycle
        if not intent.can_void:
            raise LifecycleViolationError(intent_id, intent.status.value, "void")
        
        # If authorized, release held funds
        if intent.status == IntentStatus.AUTHORIZED:
            self._release_escrow(intent, reason)
        
        # Update intent
        intent.status = IntentStatus.VOIDED
        intent.voided_at = datetime.now(timezone.utc)
        intent.void_reason = reason
        
        intent.add_event("voided", {"reason": reason})
        
        self._total_voided += intent.amount
        
        return intent
    
    def _release_escrow(self, intent: PaymentIntent, reason: str):
        """Release held funds from escrow back to source."""
        escrow_id = self._get_escrow_account_id()
        
        txn = self.ledger.transfer(
            from_account=escrow_id,
            to_account=intent.source_account,
            amount=intent.amount,
            description=f"Release escrow: {reason}",
            reference=f"REL-{intent.intent_id[:8]}",
            metadata={"intent_id": intent.intent_id, "type": "escrow_release"},
        )
        
        intent.void_transaction_id = txn.transaction_id
    
    def _release_partial(self, intent: PaymentIntent, amount: Decimal):
        """Release partial funds from escrow back to source."""
        escrow_id = self._get_escrow_account_id()
        
        self.ledger.transfer(
            from_account=escrow_id,
            to_account=intent.source_account,
            amount=amount,
            description=f"Partial release for {intent.intent_id}",
            reference=f"PREL-{intent.intent_id[:8]}",
            metadata={"intent_id": intent.intent_id, "type": "partial_release"},
        )
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    def authorize_and_capture(
        self,
        source_account: str,
        destination_account: str,
        amount: Decimal,
        idempotency_key: str = None,
        description: str = "",
        reference: str = "",
        metadata: Dict = None,
    ) -> PaymentIntent:
        """
        Single-call convenience method to create, authorize, and capture.
        
        Use this for immediate payments where no hold period is needed.
        """
        intent = self.create_intent(
            source_account=source_account,
            destination_account=destination_account,
            amount=amount,
            idempotency_key=idempotency_key,
            description=description,
            reference=reference,
            metadata=metadata,
        )
        
        self.authorize(intent.intent_id)
        return self.capture(intent.intent_id)
    
    def get_intent(self, intent_id: str) -> PaymentIntent:
        """Get a payment intent by ID."""
        if intent_id not in self.intents:
            raise IntentNotFoundError(intent_id)
        return self.intents[intent_id]
    
    def get_intent_by_idempotency_key(self, key: str) -> Optional[PaymentIntent]:
        """Get a payment intent by idempotency key."""
        if key not in self.idempotency_index:
            return None
        return self.intents[self.idempotency_index[key]]
    
    # =========================================================================
    # AUDIT & METRICS
    # =========================================================================
    
    def get_metrics(self) -> Dict:
        """Get settlement engine metrics."""
        by_status = {}
        for intent in self.intents.values():
            status = intent.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_intents": len(self.intents),
            "by_status": by_status,
            "total_authorized": str(self._total_authorized),
            "total_captured": str(self._total_captured),
            "total_voided": str(self._total_voided),
            "escrow_balance": str(
                self.ledger.get_balance(self._get_escrow_account_id())
            ),
        }
    
    def get_audit_log(self, intent_id: str) -> List[Dict]:
        """Get the complete audit trail for an intent."""
        intent = self.get_intent(intent_id)
        return intent.events
