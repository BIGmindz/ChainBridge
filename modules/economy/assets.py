#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      ASSET FACTORY - THE SOVEREIGN MINT                      ║
║                       PAC-ECON-P410-ASSET-FACTORY                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Tokenize Value with Sovereign Control                                       ║
║                                                                              ║
║  "We do not just move money; we create it (responsibly)."                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Asset Factory enables:
  - Native Asset creation (RWA, Stablecoins, Loyalty Points)
  - Controlled issuance (Only authorized entities can mint)
  - Compliance features (Freeze, Clawback)
  - Supply conservation enforcement

INVARIANTS:
  INV-ECON-003 (Conservation of Supply): Total Supply = Sum(Balances)
  INV-ECON-004 (Sovereign Control): The Issuer can Freeze the Asset

Usage:
    from modules.economy.assets import AssetFactory, Asset
    
    # Create factory
    factory = AssetFactory()
    
    # Create a new asset
    gold = factory.create_asset(
        ticker="GOLD",
        name="Digital Gold",
        decimals=8,
        issuer="TREASURY"
    )
    
    # Mint tokens
    factory.mint("GOLD", amount=1000_00000000, to="TREASURY")
    
    # Transfer
    factory.transfer("GOLD", from_addr="TREASURY", to_addr="USER_001", amount=10_00000000)
"""

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class AssetError(Exception):
    """Base exception for asset operations."""
    pass


class InsufficientBalanceError(AssetError):
    """Raised when account has insufficient balance."""
    pass


class AssetFrozenError(AssetError):
    """Raised when attempting to operate on a frozen asset."""
    pass


class UnauthorizedError(AssetError):
    """Raised when unauthorized entity attempts privileged operation."""
    pass


class DuplicateTickerError(AssetError):
    """Raised when attempting to create asset with existing ticker."""
    pass


class AssetNotFoundError(AssetError):
    """Raised when asset ticker not found."""
    pass


class AccountFrozenError(AssetError):
    """Raised when account is frozen."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class AssetStatus(Enum):
    """Status of an asset."""
    ACTIVE = "ACTIVE"           # Normal operation
    FROZEN = "FROZEN"           # All operations blocked
    DEPRECATED = "DEPRECATED"   # No new mints, transfers allowed


class OperationType(Enum):
    """Types of asset operations."""
    CREATE = "CREATE"
    MINT = "MINT"
    BURN = "BURN"
    TRANSFER = "TRANSFER"
    FREEZE = "FREEZE"
    UNFREEZE = "UNFREEZE"
    CLAWBACK = "CLAWBACK"


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Asset:
    """
    Definition of a native asset (token).
    
    Attributes:
        ticker: Unique identifier (e.g., 'GOLD', 'CBT', 'USDC')
        name: Human-readable name
        decimals: Precision (8 = 8 decimal places, like BTC)
        issuer: Address of the authorized issuer
        total_supply: Current total supply (in base units)
        status: Active, Frozen, or Deprecated
        metadata: Additional properties (logo, website, etc.)
        created_at: Creation timestamp
    """
    
    ticker: str
    name: str
    decimals: int = 8
    issuer: str = ""
    total_supply: int = 0  # In base units (e.g., satoshis for 8 decimals)
    status: AssetStatus = AssetStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    @property
    def divisor(self) -> int:
        """Get the divisor for converting base units to display units."""
        return 10 ** self.decimals
        
    def to_display(self, base_units: int) -> str:
        """Convert base units to display string."""
        value = Decimal(base_units) / Decimal(self.divisor)
        return f"{value:.{self.decimals}f}"
        
    def to_base_units(self, display_value: float) -> int:
        """Convert display value to base units."""
        return int(Decimal(str(display_value)) * Decimal(self.divisor))
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "decimals": self.decimals,
            "issuer": self.issuer,
            "total_supply": self.total_supply,
            "total_supply_display": self.to_display(self.total_supply),
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at
        }


@dataclass
class AssetAccount:
    """
    An account holding a specific asset.
    
    Each (address, ticker) pair has its own account.
    """
    
    address: str
    ticker: str
    balance: int = 0  # In base units
    frozen: bool = False
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "ticker": self.ticker,
            "balance": self.balance,
            "frozen": self.frozen,
            "created_at": self.created_at,
            "last_activity": self.last_activity
        }


@dataclass
class AssetTransfer:
    """Record of an asset transfer."""
    
    transfer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""
    from_address: str = ""
    to_address: str = ""
    amount: int = 0  # In base units
    timestamp: float = field(default_factory=time.time)
    memo: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "ticker": self.ticker,
            "from": self.from_address,
            "to": self.to_address,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "memo": self.memo
        }


@dataclass
class AssetOperation:
    """Record of any asset operation."""
    
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: OperationType = OperationType.TRANSFER
    ticker: str = ""
    operator: str = ""  # Who performed the operation
    target: str = ""    # Target address (if applicable)
    amount: int = 0     # Amount (if applicable)
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "ticker": self.ticker,
            "operator": self.operator,
            "target": self.target,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "details": self.details
        }


# ══════════════════════════════════════════════════════════════════════════════
# ASSET REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

class AssetRegistry:
    """
    Central registry of all assets in the system.
    
    Enforces:
      - Ticker uniqueness
      - Asset existence validation
    """
    
    def __init__(self):
        self._assets: Dict[str, Asset] = {}
        self._operations: List[AssetOperation] = []
        
    def register(self, asset: Asset) -> None:
        """Register a new asset."""
        ticker = asset.ticker.upper()
        
        if ticker in self._assets:
            raise DuplicateTickerError(f"Ticker '{ticker}' already exists")
            
        self._assets[ticker] = asset
        logger.info(f"📝 Registered asset: {ticker} ({asset.name})")
        
    def get(self, ticker: str) -> Asset:
        """Get asset by ticker."""
        ticker = ticker.upper()
        
        if ticker not in self._assets:
            raise AssetNotFoundError(f"Asset '{ticker}' not found")
            
        return self._assets[ticker]
        
    def exists(self, ticker: str) -> bool:
        """Check if asset exists."""
        return ticker.upper() in self._assets
        
    def list_assets(self) -> List[Asset]:
        """List all registered assets."""
        return list(self._assets.values())
        
    def record_operation(self, operation: AssetOperation) -> None:
        """Record an operation in the audit log."""
        self._operations.append(operation)
        
    def get_operations(self, ticker: Optional[str] = None) -> List[AssetOperation]:
        """Get operations, optionally filtered by ticker."""
        if ticker:
            return [op for op in self._operations if op.ticker == ticker.upper()]
        return self._operations.copy()


# ══════════════════════════════════════════════════════════════════════════════
# ASSET FACTORY - THE MINT
# ══════════════════════════════════════════════════════════════════════════════

class AssetFactory:
    """
    The Sovereign Mint - Creates and manages native assets.
    
    Features:
      - Controlled issuance (only authorized issuers can mint)
      - Supply conservation enforcement
      - Freeze and clawback capabilities
      
    INVARIANTS:
      INV-ECON-003: Total Supply = Sum(Balances)
      INV-ECON-004: Issuer can Freeze the Asset
    """
    
    def __init__(self, registry: Optional[AssetRegistry] = None):
        self.registry = registry or AssetRegistry()
        self._accounts: Dict[str, AssetAccount] = {}  # "address:ticker" -> Account
        self._transfers: List[AssetTransfer] = []
        
    def _get_account_key(self, address: str, ticker: str) -> str:
        """Generate unique key for account lookup."""
        return f"{address}:{ticker.upper()}"
        
    def _get_or_create_account(self, address: str, ticker: str) -> AssetAccount:
        """Get existing account or create new one."""
        key = self._get_account_key(address, ticker)
        
        if key not in self._accounts:
            self._accounts[key] = AssetAccount(
                address=address,
                ticker=ticker.upper()
            )
            
        return self._accounts[key]
        
    def _validate_asset_active(self, asset: Asset) -> None:
        """Validate asset is active (not frozen)."""
        if asset.status == AssetStatus.FROZEN:
            raise AssetFrozenError(f"Asset '{asset.ticker}' is frozen")
            
    def _validate_account_active(self, account: AssetAccount) -> None:
        """Validate account is not frozen."""
        if account.frozen:
            raise AccountFrozenError(f"Account '{account.address}' is frozen for {account.ticker}")
            
    def _verify_supply_conservation(self, ticker: str) -> bool:
        """
        Verify INV-ECON-003: Total Supply = Sum(Balances).
        
        Returns True if conservation holds.
        """
        asset = self.registry.get(ticker)
        
        # Sum all balances for this ticker
        total_balance = sum(
            acc.balance for acc in self._accounts.values()
            if acc.ticker == ticker.upper()
        )
        
        if total_balance != asset.total_supply:
            logger.error(f"❌ SUPPLY MISMATCH: {ticker} supply={asset.total_supply}, balances={total_balance}")
            return False
            
        return True
        
    # ══════════════════════════════════════════════════════════════════════════
    # ASSET CREATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def create_asset(
        self,
        ticker: str,
        name: str,
        decimals: int = 8,
        issuer: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Asset:
        """
        Create a new native asset.
        
        Args:
            ticker: Unique identifier (uppercase)
            name: Human-readable name
            decimals: Precision (default 8)
            issuer: Authorized issuer address
            metadata: Additional properties
            
        Returns:
            The created Asset
        """
        ticker = ticker.upper()
        
        asset = Asset(
            ticker=ticker,
            name=name,
            decimals=decimals,
            issuer=issuer,
            total_supply=0,
            status=AssetStatus.ACTIVE,
            metadata=metadata or {}
        )
        
        self.registry.register(asset)
        
        # Record operation
        self.registry.record_operation(AssetOperation(
            operation_type=OperationType.CREATE,
            ticker=ticker,
            operator=issuer,
            details={"name": name, "decimals": decimals}
        ))
        
        logger.info(f"🏭 Created asset: {ticker} ({name}) by {issuer}")
        
        return asset
        
    # ══════════════════════════════════════════════════════════════════════════
    # MINTING
    # ══════════════════════════════════════════════════════════════════════════
    
    def mint(
        self,
        ticker: str,
        amount: int,
        to: str,
        operator: Optional[str] = None
    ) -> AssetOperation:
        """
        Mint new tokens to an address.
        
        Only the issuer (or authorized operator) can mint.
        
        Args:
            ticker: Asset ticker
            amount: Amount to mint (in base units)
            to: Recipient address
            operator: Who is minting (must be issuer)
            
        Returns:
            The mint operation record
        """
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        # Validate
        self._validate_asset_active(asset)
        
        operator = operator or asset.issuer
        if operator != asset.issuer:
            raise UnauthorizedError(f"Only issuer '{asset.issuer}' can mint {ticker}")
            
        if amount <= 0:
            raise AssetError("Mint amount must be positive")
            
        # Get or create recipient account
        account = self._get_or_create_account(to, ticker)
        
        # Mint: increase supply and balance atomically
        asset.total_supply += amount
        account.balance += amount
        account.last_activity = time.time()
        
        # Verify invariant
        assert self._verify_supply_conservation(ticker), "INV-ECON-003 violated!"
        
        # Record operation
        operation = AssetOperation(
            operation_type=OperationType.MINT,
            ticker=ticker,
            operator=operator,
            target=to,
            amount=amount,
            details={"new_supply": asset.total_supply}
        )
        self.registry.record_operation(operation)
        
        logger.info(f"🪙 Minted {asset.to_display(amount)} {ticker} to {to}")
        
        return operation
        
    # ══════════════════════════════════════════════════════════════════════════
    # BURNING
    # ══════════════════════════════════════════════════════════════════════════
    
    def burn(
        self,
        ticker: str,
        amount: int,
        from_addr: str,
        operator: Optional[str] = None
    ) -> AssetOperation:
        """
        Burn (destroy) tokens from an address.
        
        Args:
            ticker: Asset ticker
            amount: Amount to burn (in base units)
            from_addr: Address to burn from
            operator: Who is burning (must be issuer or owner)
            
        Returns:
            The burn operation record
        """
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        # Validate
        self._validate_asset_active(asset)
        
        operator = operator or from_addr
        # Issuer can always burn, owner can burn their own
        if operator != asset.issuer and operator != from_addr:
            raise UnauthorizedError(f"Unauthorized to burn {ticker}")
            
        if amount <= 0:
            raise AssetError("Burn amount must be positive")
            
        # Get account
        account = self._get_or_create_account(from_addr, ticker)
        
        if account.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: has {account.balance}, burning {amount}"
            )
            
        # Burn: decrease supply and balance atomically
        asset.total_supply -= amount
        account.balance -= amount
        account.last_activity = time.time()
        
        # Verify invariant
        assert self._verify_supply_conservation(ticker), "INV-ECON-003 violated!"
        
        # Record operation
        operation = AssetOperation(
            operation_type=OperationType.BURN,
            ticker=ticker,
            operator=operator,
            target=from_addr,
            amount=amount,
            details={"new_supply": asset.total_supply}
        )
        self.registry.record_operation(operation)
        
        logger.info(f"🔥 Burned {asset.to_display(amount)} {ticker} from {from_addr}")
        
        return operation
        
    # ══════════════════════════════════════════════════════════════════════════
    # TRANSFER
    # ══════════════════════════════════════════════════════════════════════════
    
    def transfer(
        self,
        ticker: str,
        from_addr: str,
        to_addr: str,
        amount: int,
        memo: str = ""
    ) -> AssetTransfer:
        """
        Transfer tokens between addresses.
        
        Args:
            ticker: Asset ticker
            from_addr: Sender address
            to_addr: Recipient address
            amount: Amount to transfer (in base units)
            memo: Optional memo
            
        Returns:
            The transfer record
        """
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        # Validate asset
        self._validate_asset_active(asset)
        
        if amount <= 0:
            raise AssetError("Transfer amount must be positive")
            
        if from_addr == to_addr:
            raise AssetError("Cannot transfer to same address")
            
        # Get accounts
        from_account = self._get_or_create_account(from_addr, ticker)
        to_account = self._get_or_create_account(to_addr, ticker)
        
        # Validate accounts
        self._validate_account_active(from_account)
        self._validate_account_active(to_account)
        
        if from_account.balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance: has {from_account.balance}, transferring {amount}"
            )
            
        # Transfer: debit and credit atomically
        from_account.balance -= amount
        to_account.balance += amount
        from_account.last_activity = time.time()
        to_account.last_activity = time.time()
        
        # Verify invariant (supply unchanged)
        assert self._verify_supply_conservation(ticker), "INV-ECON-003 violated!"
        
        # Record transfer
        transfer = AssetTransfer(
            ticker=ticker,
            from_address=from_addr,
            to_address=to_addr,
            amount=amount,
            memo=memo
        )
        self._transfers.append(transfer)
        
        # Record operation
        self.registry.record_operation(AssetOperation(
            operation_type=OperationType.TRANSFER,
            ticker=ticker,
            operator=from_addr,
            target=to_addr,
            amount=amount,
            details={"memo": memo}
        ))
        
        logger.info(f"💸 Transferred {asset.to_display(amount)} {ticker}: {from_addr} -> {to_addr}")
        
        return transfer
        
    # ══════════════════════════════════════════════════════════════════════════
    # SOVEREIGN CONTROLS (INV-ECON-004)
    # ══════════════════════════════════════════════════════════════════════════
    
    def freeze_asset(self, ticker: str, operator: str) -> AssetOperation:
        """
        Freeze an asset (block all operations).
        
        Only the issuer can freeze.
        """
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        if operator != asset.issuer:
            raise UnauthorizedError(f"Only issuer can freeze {ticker}")
            
        asset.status = AssetStatus.FROZEN
        
        operation = AssetOperation(
            operation_type=OperationType.FREEZE,
            ticker=ticker,
            operator=operator,
            details={"target": "ASSET"}
        )
        self.registry.record_operation(operation)
        
        logger.warning(f"🧊 Asset FROZEN: {ticker} by {operator}")
        
        return operation
        
    def unfreeze_asset(self, ticker: str, operator: str) -> AssetOperation:
        """Unfreeze an asset."""
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        if operator != asset.issuer:
            raise UnauthorizedError(f"Only issuer can unfreeze {ticker}")
            
        asset.status = AssetStatus.ACTIVE
        
        operation = AssetOperation(
            operation_type=OperationType.UNFREEZE,
            ticker=ticker,
            operator=operator,
            details={"target": "ASSET"}
        )
        self.registry.record_operation(operation)
        
        logger.info(f"🔓 Asset UNFROZEN: {ticker} by {operator}")
        
        return operation
        
    def freeze_account(self, ticker: str, address: str, operator: str) -> AssetOperation:
        """
        Freeze a specific account.
        
        Only the issuer can freeze accounts.
        """
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        if operator != asset.issuer:
            raise UnauthorizedError(f"Only issuer can freeze accounts for {ticker}")
            
        account = self._get_or_create_account(address, ticker)
        account.frozen = True
        
        operation = AssetOperation(
            operation_type=OperationType.FREEZE,
            ticker=ticker,
            operator=operator,
            target=address,
            details={"target": "ACCOUNT"}
        )
        self.registry.record_operation(operation)
        
        logger.warning(f"🧊 Account FROZEN: {address} for {ticker}")
        
        return operation
        
    def clawback(
        self,
        ticker: str,
        from_addr: str,
        amount: int,
        operator: str,
        reason: str = ""
    ) -> AssetOperation:
        """
        Clawback (forcibly transfer) tokens from an address to issuer.
        
        This is a compliance feature for regulatory requirements.
        Only the issuer can clawback.
        """
        ticker = ticker.upper()
        asset = self.registry.get(ticker)
        
        if operator != asset.issuer:
            raise UnauthorizedError(f"Only issuer can clawback {ticker}")
            
        # Get account (don't check frozen - clawback overrides)
        from_account = self._get_or_create_account(from_addr, ticker)
        issuer_account = self._get_or_create_account(asset.issuer, ticker)
        
        # Clamp to available balance
        actual_amount = min(amount, from_account.balance)
        
        if actual_amount <= 0:
            raise AssetError(f"No balance to clawback from {from_addr}")
            
        # Forcible transfer
        from_account.balance -= actual_amount
        issuer_account.balance += actual_amount
        
        # Verify invariant
        assert self._verify_supply_conservation(ticker), "INV-ECON-003 violated!"
        
        operation = AssetOperation(
            operation_type=OperationType.CLAWBACK,
            ticker=ticker,
            operator=operator,
            target=from_addr,
            amount=actual_amount,
            details={"reason": reason, "returned_to": asset.issuer}
        )
        self.registry.record_operation(operation)
        
        logger.warning(f"⚠️ CLAWBACK: {asset.to_display(actual_amount)} {ticker} from {from_addr} - {reason}")
        
        return operation
        
    # ══════════════════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ══════════════════════════════════════════════════════════════════════════
    
    def get_balance(self, address: str, ticker: str) -> int:
        """Get balance for an address and ticker."""
        ticker = ticker.upper()
        key = self._get_account_key(address, ticker)
        
        if key in self._accounts:
            return self._accounts[key].balance
        return 0
        
    def get_account(self, address: str, ticker: str) -> Optional[AssetAccount]:
        """Get account details."""
        key = self._get_account_key(address, ticker)
        return self._accounts.get(key)
        
    def get_total_supply(self, ticker: str) -> int:
        """Get total supply for a ticker."""
        asset = self.registry.get(ticker)
        return asset.total_supply
        
    def get_holders(self, ticker: str) -> List[Tuple[str, int]]:
        """Get all holders of a ticker with their balances."""
        ticker = ticker.upper()
        holders = []
        
        for account in self._accounts.values():
            if account.ticker == ticker and account.balance > 0:
                holders.append((account.address, account.balance))
                
        return sorted(holders, key=lambda x: x[1], reverse=True)
        
    def get_transfers(self, ticker: Optional[str] = None) -> List[AssetTransfer]:
        """Get transfers, optionally filtered by ticker."""
        if ticker:
            return [t for t in self._transfers if t.ticker == ticker.upper()]
        return self._transfers.copy()


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> bool:
    """Run self-tests to verify the Asset Factory."""
    print("=" * 70)
    print("           ASSET FACTORY SELF-TEST")
    print("=" * 70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Create Asset
    tests_total += 1
    print("\n[TEST 1] Create Asset...")
    try:
        factory = AssetFactory()
        gold = factory.create_asset(
            ticker="GOLD",
            name="Digital Gold",
            decimals=8,
            issuer="TREASURY",
            metadata={"type": "commodity"}
        )
        assert gold.ticker == "GOLD"
        assert gold.total_supply == 0
        print("  ✅ PASSED: Asset created")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 2: Mint Tokens
    tests_total += 1
    print("\n[TEST 2] Mint Tokens...")
    try:
        # Mint 1000 GOLD (with 8 decimals: 1000_00000000 base units)
        mint_amount = 1000_00000000
        factory.mint("GOLD", amount=mint_amount, to="TREASURY", operator="TREASURY")
        
        assert factory.get_balance("TREASURY", "GOLD") == mint_amount
        assert factory.get_total_supply("GOLD") == mint_amount
        print(f"  ✅ PASSED: Minted {gold.to_display(mint_amount)} GOLD")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 3: Transfer Tokens
    tests_total += 1
    print("\n[TEST 3] Transfer Tokens...")
    try:
        transfer_amount = 10_00000000  # 10 GOLD
        factory.transfer("GOLD", from_addr="TREASURY", to_addr="USER_001", amount=transfer_amount)
        
        assert factory.get_balance("USER_001", "GOLD") == transfer_amount
        assert factory.get_balance("TREASURY", "GOLD") == mint_amount - transfer_amount
        # Supply unchanged
        assert factory.get_total_supply("GOLD") == mint_amount
        print(f"  ✅ PASSED: Transferred {gold.to_display(transfer_amount)} GOLD to USER_001")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 4: Supply Conservation (INV-ECON-003)
    tests_total += 1
    print("\n[TEST 4] Supply Conservation (INV-ECON-003)...")
    try:
        total_supply = factory.get_total_supply("GOLD")
        holders = factory.get_holders("GOLD")
        sum_balances = sum(bal for _, bal in holders)
        
        assert sum_balances == total_supply, f"Supply mismatch: {sum_balances} != {total_supply}"
        print(f"  ✅ PASSED: Total Supply ({total_supply}) = Sum(Balances) ({sum_balances})")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 5: Burn Tokens
    tests_total += 1
    print("\n[TEST 5] Burn Tokens...")
    try:
        burn_amount = 5_00000000  # 5 GOLD
        factory.burn("GOLD", amount=burn_amount, from_addr="USER_001", operator="USER_001")
        
        assert factory.get_balance("USER_001", "GOLD") == 5_00000000  # 10 - 5 = 5
        assert factory.get_total_supply("GOLD") == 995_00000000  # 1000 - 5 = 995
        print(f"  ✅ PASSED: Burned 5 GOLD, new supply: {gold.to_display(factory.get_total_supply('GOLD'))}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 6: Freeze Asset (INV-ECON-004)
    tests_total += 1
    print("\n[TEST 6] Sovereign Control - Freeze (INV-ECON-004)...")
    try:
        factory.freeze_asset("GOLD", operator="TREASURY")
        
        # Attempt transfer should fail
        try:
            factory.transfer("GOLD", "TREASURY", "USER_002", 1_00000000)
            print("  ❌ FAILED: Transfer should have been blocked")
        except AssetFrozenError:
            print("  ✅ PASSED: Freeze blocks operations")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 7: Unfreeze and Clawback
    tests_total += 1
    print("\n[TEST 7] Unfreeze and Clawback...")
    try:
        factory.unfreeze_asset("GOLD", operator="TREASURY")
        
        # Clawback from USER_001
        clawback_amount = 3_00000000  # 3 GOLD
        factory.clawback("GOLD", from_addr="USER_001", amount=clawback_amount, 
                        operator="TREASURY", reason="Compliance")
        
        assert factory.get_balance("USER_001", "GOLD") == 2_00000000  # 5 - 3 = 2
        print(f"  ✅ PASSED: Clawback executed, USER_001 balance: {gold.to_display(factory.get_balance('USER_001', 'GOLD'))}")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 8: Duplicate Ticker Prevention
    tests_total += 1
    print("\n[TEST 8] Duplicate Ticker Prevention...")
    try:
        try:
            factory.create_asset("GOLD", "Another Gold", issuer="HACKER")
            print("  ❌ FAILED: Duplicate ticker should be rejected")
        except DuplicateTickerError:
            print("  ✅ PASSED: Duplicate ticker rejected")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Summary
    print("\n" + "=" * 70)
    print(f"                    RESULTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 70)
    
    if tests_passed == tests_total:
        print("\n🏭 ASSET FACTORY OPERATIONAL")
        print("INV-ECON-003 (Conservation of Supply): ✅ ENFORCED")
        print("INV-ECON-004 (Sovereign Control): ✅ ENFORCED")
        
    return tests_passed == tests_total


if __name__ == "__main__":
    import sys
    success = _self_test()
    sys.exit(0 if success else 1)
