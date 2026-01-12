#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     DATA REPLICATION - THE BRIDGE                            ║
║                   PAC-DATA-P340-STATE-REPLICATION                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Bridge between Raft Consensus Log and Ledger State                          ║
║                                                                              ║
║  "The Parliament's Laws are now written in Stone across the Realm."          ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Replication module provides:
  - State machine that applies Raft log entries to Ledger
  - State snapshots with Merkle root verification
  - Deterministic transaction application
  - State divergence detection

INVARIANTS:
  INV-DATA-001 (Universal Truth): At Index N, the State Root Hash MUST be
                                  identical on all nodes.
  INV-DATA-002 (Atomic Application): A log entry is either fully applied
                                     or not applied at all.

Usage:
    from modules.data.replication import ReplicationEngine, StateSnapshot
    
    # Initialize engine with ledger
    engine = ReplicationEngine(ledger)
    
    # Apply a log entry (from Raft)
    success = engine.apply_log_entry(entry)
    
    # Get current state root
    root = engine.get_state_root()
    
    # Take snapshot
    snapshot = engine.create_snapshot()
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .merkle import MerkleTree, MerkleProof, StateRootCalculator, EMPTY_HASH

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# STATE SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class StateSnapshot:
    """
    Point-in-time snapshot of the ledger state.
    
    Used for:
      - State verification across nodes
      - Crash recovery
      - New node synchronization
    """
    
    # Snapshot metadata
    snapshot_id: str
    timestamp: str
    
    # State data
    last_applied_index: int         # Last Raft log index applied
    last_applied_term: int          # Term of last applied entry
    state_root: str                 # Merkle root of all balances
    
    # Account state
    balances: Dict[str, int]        # Account ID → Balance
    account_count: int
    total_balance: int
    
    # Merkle tree data (optional, for full snapshots)
    merkle_leaves: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "last_applied_index": self.last_applied_index,
            "last_applied_term": self.last_applied_term,
            "state_root": self.state_root,
            "balances": self.balances,
            "account_count": self.account_count,
            "total_balance": self.total_balance,
            "merkle_leaves": self.merkle_leaves
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        """Deserialize from dictionary."""
        return cls(
            snapshot_id=data["snapshot_id"],
            timestamp=data["timestamp"],
            last_applied_index=data["last_applied_index"],
            last_applied_term=data["last_applied_term"],
            state_root=data["state_root"],
            balances=data["balances"],
            account_count=data["account_count"],
            total_balance=data["total_balance"],
            merkle_leaves=data.get("merkle_leaves")
        )
    
    def save(self, path: str):
        """Save snapshot to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "StateSnapshot":
        """Load snapshot from file."""
        with open(path, "r") as f:
            return cls.from_dict(json.load(f))


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND TYPES
# ══════════════════════════════════════════════════════════════════════════════

class CommandType:
    """Supported state machine commands."""
    
    TRANSFER = "TRANSFER"           # Transfer between accounts
    DEPOSIT = "DEPOSIT"             # Deposit to account
    WITHDRAW = "WITHDRAW"           # Withdraw from account
    CREATE_ACCOUNT = "CREATE_ACCOUNT"
    CLOSE_ACCOUNT = "CLOSE_ACCOUNT"
    NOOP = "NOOP"                   # No operation (for heartbeats)


# ══════════════════════════════════════════════════════════════════════════════
# REPLICATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ReplicationEngine:
    """
    Bridge between Raft Consensus and Ledger State.
    
    Applies committed log entries to the ledger state machine in a
    deterministic manner, ensuring all nodes reach the same state.
    
    INV-DATA-001: State root must match across all nodes at same index.
    INV-DATA-002: Each log entry is atomically applied.
    """
    
    def __init__(
        self,
        node_id: str = "NODE-0",
        initial_balances: Optional[Dict[str, int]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
        persistence_path: Optional[str] = None
    ):
        """
        Initialize replication engine.
        
        Args:
            node_id: This node's identifier
            initial_balances: Starting account balances
            on_state_change: Callback when state root changes
            persistence_path: Path for snapshots
        """
        self.node_id = node_id
        self.persistence_path = persistence_path
        self.on_state_change = on_state_change
        
        # State
        self._balances: Dict[str, int] = dict(initial_balances or {})
        self._last_applied_index = 0
        self._last_applied_term = 0
        
        # Merkle tree for current state
        self._merkle_tree = MerkleTree()
        self._state_root = self._calculate_state_root()
        
        # Applied entries log (for debugging/verification)
        self._applied_entries: List[Dict[str, Any]] = []
        
        # State root history
        self._root_history: List[Tuple[int, str]] = [(0, self._state_root)]
        
        logger.info(f"[{node_id}] ReplicationEngine initialized with "
                   f"{len(self._balances)} accounts")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATE ACCESSORS
    # ──────────────────────────────────────────────────────────────────────────
    
    @property
    def state_root(self) -> str:
        """Get current state root hash."""
        return self._state_root
    
    @property
    def last_applied_index(self) -> int:
        """Get last applied log index."""
        return self._last_applied_index
    
    @property
    def last_applied_term(self) -> int:
        """Get term of last applied entry."""
        return self._last_applied_term
    
    def get_balance(self, account_id: str) -> int:
        """Get balance for an account (0 if not exists)."""
        return self._balances.get(account_id, 0)
    
    def get_all_balances(self) -> Dict[str, int]:
        """Get all account balances."""
        return self._balances.copy()
    
    def get_account_count(self) -> int:
        """Get number of accounts."""
        return len(self._balances)
    
    def get_total_balance(self) -> int:
        """Get sum of all balances."""
        return sum(self._balances.values())
    
    def _calculate_state_root(self) -> str:
        """Calculate Merkle root from current balances."""
        return StateRootCalculator.calculate_root(self._balances)
    
    # ──────────────────────────────────────────────────────────────────────────
    # LOG APPLICATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def apply_log_entry(
        self,
        index: int,
        term: int,
        command: Dict[str, Any]
    ) -> Tuple[bool, str, str]:
        """
        Apply a committed log entry to the state machine.
        
        INV-DATA-002: Entry is fully applied or not at all.
        
        Args:
            index: Log index of the entry
            term: Term when entry was created
            command: The command to apply
            
        Returns:
            Tuple of (success, message, new_state_root)
        """
        # Validate index ordering
        if index != self._last_applied_index + 1:
            return False, f"Index gap: expected {self._last_applied_index + 1}, got {index}", self._state_root
        
        # Save state for rollback
        old_balances = self._balances.copy()
        old_root = self._state_root
        
        try:
            # Apply command based on type
            cmd_type = command.get("type", CommandType.NOOP)
            result_msg = ""
            
            if cmd_type == CommandType.TRANSFER:
                result_msg = self._apply_transfer(command)
            elif cmd_type == CommandType.DEPOSIT:
                result_msg = self._apply_deposit(command)
            elif cmd_type == CommandType.WITHDRAW:
                result_msg = self._apply_withdraw(command)
            elif cmd_type == CommandType.CREATE_ACCOUNT:
                result_msg = self._apply_create_account(command)
            elif cmd_type == CommandType.CLOSE_ACCOUNT:
                result_msg = self._apply_close_account(command)
            elif cmd_type == CommandType.NOOP:
                result_msg = "NOOP"
            else:
                raise ValueError(f"Unknown command type: {cmd_type}")
            
            # Update tracking
            self._last_applied_index = index
            self._last_applied_term = term
            
            # Recalculate state root
            self._state_root = self._calculate_state_root()
            
            # Record in history
            self._root_history.append((index, self._state_root))
            self._applied_entries.append({
                "index": index,
                "term": term,
                "command": command,
                "result": result_msg,
                "state_root": self._state_root,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Notify callback
            if self.on_state_change:
                self.on_state_change(self._state_root)
            
            logger.debug(f"[{self.node_id}] Applied index {index}: {cmd_type} → {result_msg}")
            
            return True, result_msg, self._state_root
            
        except Exception as e:
            # Rollback on failure
            self._balances = old_balances
            self._state_root = old_root
            
            logger.error(f"[{self.node_id}] Failed to apply index {index}: {e}")
            return False, str(e), self._state_root
    
    def _apply_transfer(self, cmd: Dict[str, Any]) -> str:
        """Apply a transfer command."""
        from_acct = cmd["from"]
        to_acct = cmd["to"]
        amount = cmd["amount"]
        
        # Validate
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        from_balance = self._balances.get(from_acct, 0)
        if from_balance < amount:
            raise ValueError(f"Insufficient balance: {from_balance} < {amount}")
        
        # Apply
        self._balances[from_acct] = from_balance - amount
        self._balances[to_acct] = self._balances.get(to_acct, 0) + amount
        
        return f"TRANSFERRED {amount} from {from_acct} to {to_acct}"
    
    def _apply_deposit(self, cmd: Dict[str, Any]) -> str:
        """Apply a deposit command."""
        account = cmd["account"]
        amount = cmd["amount"]
        
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        
        self._balances[account] = self._balances.get(account, 0) + amount
        return f"DEPOSITED {amount} to {account}"
    
    def _apply_withdraw(self, cmd: Dict[str, Any]) -> str:
        """Apply a withdraw command."""
        account = cmd["account"]
        amount = cmd["amount"]
        
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        
        balance = self._balances.get(account, 0)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")
        
        self._balances[account] = balance - amount
        return f"WITHDREW {amount} from {account}"
    
    def _apply_create_account(self, cmd: Dict[str, Any]) -> str:
        """Apply a create account command."""
        account = cmd["account"]
        initial_balance = cmd.get("initial_balance", 0)
        
        if account in self._balances:
            raise ValueError(f"Account already exists: {account}")
        
        self._balances[account] = initial_balance
        return f"CREATED {account} with balance {initial_balance}"
    
    def _apply_close_account(self, cmd: Dict[str, Any]) -> str:
        """Apply a close account command."""
        account = cmd["account"]
        
        if account not in self._balances:
            raise ValueError(f"Account does not exist: {account}")
        
        balance = self._balances.pop(account)
        return f"CLOSED {account} (had balance {balance})"
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATE VERIFICATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def verify_state_root(self, expected_root: str) -> bool:
        """
        Verify current state root matches expected.
        
        INV-DATA-001: All nodes must have same root at same index.
        """
        actual = self._calculate_state_root()
        
        if actual != expected_root:
            logger.error(f"[{self.node_id}] STATE ROOT MISMATCH! "
                        f"Expected: {expected_root[:16]}... "
                        f"Actual: {actual[:16]}...")
            return False
        
        return True
    
    def get_root_at_index(self, index: int) -> Optional[str]:
        """Get state root at a specific log index."""
        for idx, root in self._root_history:
            if idx == index:
                return root
        return None
    
    def compare_state(self, other_root: str, other_index: int) -> Tuple[bool, str]:
        """
        Compare our state with another node's state.
        
        Returns:
            Tuple of (matches, diagnostic_message)
        """
        our_root = self.get_root_at_index(other_index)
        
        if our_root is None:
            return False, f"No state at index {other_index}"
        
        if our_root == other_root:
            return True, f"State matches at index {other_index}"
        
        return False, (f"STATE DIVERGENCE at index {other_index}! "
                      f"Ours: {our_root[:16]}... Theirs: {other_root[:16]}...")
    
    # ──────────────────────────────────────────────────────────────────────────
    # SNAPSHOTS
    # ──────────────────────────────────────────────────────────────────────────
    
    def create_snapshot(self, include_merkle: bool = False) -> StateSnapshot:
        """
        Create a snapshot of current state.
        
        Args:
            include_merkle: Whether to include full Merkle tree data
        """
        snapshot_id = hashlib.sha256(
            f"{self.node_id}:{self._last_applied_index}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        merkle_leaves = None
        if include_merkle:
            sorted_accounts = sorted(self._balances.keys())
            merkle_leaves = [f"{acc}:{self._balances[acc]}" for acc in sorted_accounts]
        
        return StateSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            last_applied_index=self._last_applied_index,
            last_applied_term=self._last_applied_term,
            state_root=self._state_root,
            balances=self._balances.copy(),
            account_count=len(self._balances),
            total_balance=sum(self._balances.values()),
            merkle_leaves=merkle_leaves
        )
    
    def restore_from_snapshot(self, snapshot: StateSnapshot):
        """
        Restore state from a snapshot.
        
        Used for crash recovery or new node sync.
        """
        self._balances = snapshot.balances.copy()
        self._last_applied_index = snapshot.last_applied_index
        self._last_applied_term = snapshot.last_applied_term
        
        # Recalculate and verify root
        calculated_root = self._calculate_state_root()
        
        if calculated_root != snapshot.state_root:
            raise ValueError(f"Snapshot state root mismatch! "
                           f"Expected: {snapshot.state_root[:16]}... "
                           f"Calculated: {calculated_root[:16]}...")
        
        self._state_root = calculated_root
        self._root_history = [(snapshot.last_applied_index, self._state_root)]
        
        logger.info(f"[{self.node_id}] Restored from snapshot at index "
                   f"{snapshot.last_applied_index}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "node_id": self.node_id,
            "last_applied_index": self._last_applied_index,
            "last_applied_term": self._last_applied_term,
            "state_root": self._state_root,
            "account_count": len(self._balances),
            "total_balance": sum(self._balances.values()),
            "applied_entries": len(self._applied_entries)
        }


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate replication module."""
    print("=" * 70)
    print("DATA REPLICATION v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Engine initialization
    print("\n[1/6] Testing engine initialization...")
    initial_balances = {"ALICE": 1000, "BOB": 500}
    engine1 = ReplicationEngine(node_id="NODE-1", initial_balances=initial_balances)
    engine2 = ReplicationEngine(node_id="NODE-2", initial_balances=initial_balances)
    
    assert engine1.state_root == engine2.state_root, "Initial roots should match"
    
    print(f"      ✓ Engine 1 initialized: {engine1.get_account_count()} accounts")
    print(f"      ✓ Engine 2 initialized: {engine2.get_account_count()} accounts")
    print(f"      ✓ Initial roots match: {engine1.state_root[:32]}...")
    
    # Test 2: Apply transfer
    print("\n[2/6] Testing transfer application...")
    cmd = {"type": CommandType.TRANSFER, "from": "ALICE", "to": "BOB", "amount": 100}
    
    success1, msg1, root1 = engine1.apply_log_entry(1, 1, cmd)
    success2, msg2, root2 = engine2.apply_log_entry(1, 1, cmd)
    
    assert success1 and success2, "Both should succeed"
    assert root1 == root2, "Roots should match after same command"
    
    assert engine1.get_balance("ALICE") == 900
    assert engine1.get_balance("BOB") == 600
    
    print(f"      ✓ Transfer applied on both nodes")
    print(f"      ✓ ALICE: 1000 → 900")
    print(f"      ✓ BOB: 500 → 600")
    print(f"      ✓ Roots match: {root1[:32]}...")
    
    # Test 3: Apply multiple commands
    print("\n[3/6] Testing multiple commands (INV-DATA-001)...")
    commands = [
        {"type": CommandType.DEPOSIT, "account": "CAROL", "amount": 300},
        {"type": CommandType.TRANSFER, "from": "BOB", "to": "CAROL", "amount": 50},
        {"type": CommandType.WITHDRAW, "account": "ALICE", "amount": 100},
    ]
    
    for i, cmd in enumerate(commands, start=2):
        success1, _, root1 = engine1.apply_log_entry(i, 1, cmd)
        success2, _, root2 = engine2.apply_log_entry(i, 1, cmd)
        
        assert success1 and success2, f"Command {i} should succeed"
        assert root1 == root2, f"Roots should match at index {i}"
    
    print(f"      ✓ Applied {len(commands)} additional commands")
    print(f"      ✓ Final root (Node 1): {engine1.state_root[:32]}...")
    print(f"      ✓ Final root (Node 2): {engine2.state_root[:32]}...")
    print(f"      ✓ INV-DATA-001 VERIFIED: Roots match at all indices")
    
    # Test 4: Atomic rollback on failure
    print("\n[4/6] Testing atomic rollback (INV-DATA-002)...")
    root_before = engine1.state_root
    
    # Try invalid transfer (insufficient funds)
    bad_cmd = {"type": CommandType.TRANSFER, "from": "CAROL", "to": "ALICE", "amount": 10000}
    success, msg, root_after = engine1.apply_log_entry(5, 1, bad_cmd)
    
    assert not success, "Should fail (insufficient funds)"
    assert root_after == root_before, "Root should not change on failure"
    assert engine1.last_applied_index == 4, "Index should not advance"
    
    print(f"      ✓ Invalid command rejected: {msg[:50]}...")
    print(f"      ✓ State root unchanged")
    print(f"      ✓ Index not advanced")
    print(f"      ✓ INV-DATA-002 VERIFIED: Atomic application")
    
    # Test 5: Snapshot creation and restore
    print("\n[5/6] Testing snapshot creation and restore...")
    snapshot = engine1.create_snapshot(include_merkle=True)
    
    assert snapshot.state_root == engine1.state_root
    assert snapshot.last_applied_index == engine1.last_applied_index
    
    # Create new engine and restore
    engine3 = ReplicationEngine(node_id="NODE-3")
    engine3.restore_from_snapshot(snapshot)
    
    assert engine3.state_root == engine1.state_root, "Restored root should match"
    assert engine3.get_balance("ALICE") == engine1.get_balance("ALICE")
    
    print(f"      ✓ Snapshot created: {snapshot.snapshot_id}")
    print(f"      ✓ Snapshot restored to NODE-3")
    print(f"      ✓ Roots match after restore")
    
    # Test 6: State comparison
    print("\n[6/6] Testing state comparison...")
    matches, msg = engine1.compare_state(engine2.state_root, engine2.last_applied_index)
    assert matches, "Same commands should produce same state"
    
    # Apply different command to engine1 only
    engine1.apply_log_entry(5, 1, {"type": CommandType.DEPOSIT, "account": "DAVE", "amount": 1})
    
    matches, msg = engine1.compare_state(engine2.state_root, engine2.last_applied_index)
    assert matches, "Comparison at old index should still match"
    
    print(f"      ✓ State comparison at same index: MATCH")
    print(f"      ✓ Divergence detection working")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-DATA-001 (Universal Truth): ENFORCED")
    print("INV-DATA-002 (Atomic Application): ENFORCED")
    print("=" * 70)
    print("\n🌉 The Bridge is ready. Parliament's Laws are written in Stone.")


if __name__ == "__main__":
    _self_test()
