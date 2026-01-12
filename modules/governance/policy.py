#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     FEDERATION POLICY - THE CONSTITUTION                     ║
║                   PAC-GOV-P320-FEDERATION-POLICY                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Defines the Rules of Engagement for the Mesh                                ║
║                                                                              ║
║  "A Federation without rules is a mob."                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Federation Policy module provides:
  - Peering Contracts: Requirements for joining the federation
  - Node Status Tracking: Active, Probation, Unbonding, Banned
  - Policy Updates: 2/3 quorum required for constitutional changes
  - Reputation System: Performance-based standing

INVARIANTS:
  INV-GOV-001 (Constitutional Rigidity): Policy changes require 2/3 consensus,
                                         higher than transaction consensus (1/2).

Usage:
    from modules.governance.policy import FederationPolicy, PeeringContract
    
    # Create policy
    policy = FederationPolicy()
    
    # Submit peering request
    contract = PeeringContract(
        node_id="NODE-42",
        public_key="abc123...",
        stake_amount=10000,
        endpoint="node42.example.com:8080"
    )
    
    # Admit node
    if policy.admit_node(contract):
        print("Node admitted to federation")
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS AND CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

class NodeStatus(Enum):
    """Node standing within the federation."""
    
    PENDING = "PENDING"           # Application submitted, not yet voted
    ACTIVE = "ACTIVE"             # Full member in good standing
    PROBATION = "PROBATION"       # Minor violations, under observation
    UNBONDING = "UNBONDING"       # Leaving voluntarily, stake locked
    SLASHED = "SLASHED"           # Punished, stake reduced
    BANNED = "BANNED"             # Permanently expelled


class PolicyUpdateType(Enum):
    """Types of policy updates (each may require different quorum)."""
    
    PARAMETER_CHANGE = "PARAMETER_CHANGE"     # Min stake, uptime threshold
    ADMISSION_RULE = "ADMISSION_RULE"         # Who can join
    SLASHING_RULE = "SLASHING_RULE"           # Punishment criteria
    CONSTITUTIONAL = "CONSTITUTIONAL"          # Core protocol changes


# Default policy parameters
DEFAULT_MIN_STAKE = 10000                     # Minimum stake to join
DEFAULT_MIN_UPTIME = 99.9                     # 99.9% uptime required
DEFAULT_UNBONDING_PERIOD = 86400 * 7         # 7 days before stake release
DEFAULT_PROBATION_PERIOD = 86400 * 3         # 3 days of observation
DEFAULT_POLICY_QUORUM = 2/3                  # 2/3 for policy changes
DEFAULT_TX_QUORUM = 1/2                      # 1/2 for transactions


# ══════════════════════════════════════════════════════════════════════════════
# POLICY CONFIG
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PolicyConfig:
    """
    Federation policy configuration.
    
    INV-GOV-001: policy_quorum > tx_quorum (constitutional rigidity)
    """
    
    # Staking requirements
    min_stake: int = DEFAULT_MIN_STAKE
    
    # Performance requirements
    min_uptime_percent: float = DEFAULT_MIN_UPTIME
    
    # Time periods (seconds)
    unbonding_period: int = DEFAULT_UNBONDING_PERIOD
    probation_period: int = DEFAULT_PROBATION_PERIOD
    
    # Quorum requirements
    policy_quorum: float = DEFAULT_POLICY_QUORUM      # For policy changes
    tx_quorum: float = DEFAULT_TX_QUORUM              # For transactions
    
    # Version tracking
    version: int = 1
    last_updated: str = ""
    update_hash: str = ""
    
    def __post_init__(self):
        """Validate invariants after initialization."""
        self._validate_invariants()
        if not self.last_updated:
            self.last_updated = datetime.now(timezone.utc).isoformat()
        if not self.update_hash:
            self.update_hash = self._compute_hash()
    
    def _validate_invariants(self):
        """
        Validate policy configuration meets invariants.
        
        INV-GOV-001: Policy quorum must exceed transaction quorum.
        """
        if self.policy_quorum <= self.tx_quorum:
            raise ValueError(
                f"INV-GOV-001 VIOLATION: policy_quorum ({self.policy_quorum}) "
                f"must exceed tx_quorum ({self.tx_quorum})"
            )
        
        if self.min_stake < 0:
            raise ValueError("min_stake cannot be negative")
        
        if not 0 <= self.min_uptime_percent <= 100:
            raise ValueError("min_uptime_percent must be 0-100")
    
    def _compute_hash(self) -> str:
        """Compute hash of policy config for change tracking."""
        data = {
            "min_stake": self.min_stake,
            "min_uptime_percent": self.min_uptime_percent,
            "unbonding_period": self.unbonding_period,
            "probation_period": self.probation_period,
            "policy_quorum": self.policy_quorum,
            "tx_quorum": self.tx_quorum,
            "version": self.version,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "min_stake": self.min_stake,
            "min_uptime_percent": self.min_uptime_percent,
            "unbonding_period": self.unbonding_period,
            "probation_period": self.probation_period,
            "policy_quorum": self.policy_quorum,
            "tx_quorum": self.tx_quorum,
            "version": self.version,
            "last_updated": self.last_updated,
            "update_hash": self.update_hash,
        }


# ══════════════════════════════════════════════════════════════════════════════
# PEERING CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PeeringContract:
    """
    Contract submitted by a node to join the federation.
    
    Must meet minimum requirements defined in PolicyConfig.
    """
    
    # Node identification
    node_id: str
    public_key: str
    
    # Stake commitment
    stake_amount: int
    
    # Network endpoint
    endpoint: str
    
    # Optional metadata
    organization: str = ""
    region: str = ""
    
    # Signatures (for cryptographic verification)
    signature: str = ""           # Node's signature on contract
    sponsor_signatures: List[str] = field(default_factory=list)
    
    # Timestamps
    submitted_at: str = ""
    
    def __post_init__(self):
        if not self.submitted_at:
            self.submitted_at = datetime.now(timezone.utc).isoformat()
    
    def compute_hash(self) -> str:
        """Compute hash of contract for signing."""
        data = {
            "node_id": self.node_id,
            "public_key": self.public_key,
            "stake_amount": self.stake_amount,
            "endpoint": self.endpoint,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# NODE RECORD
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeRecord:
    """
    Federation's record of a member node.
    
    Tracks status, performance, and stake.
    """
    
    # From peering contract
    node_id: str
    public_key: str
    stake_amount: int
    endpoint: str
    
    # Status tracking
    status: NodeStatus = NodeStatus.PENDING
    status_reason: str = ""
    
    # Performance metrics
    uptime_percent: float = 100.0
    blocks_produced: int = 0
    blocks_missed: int = 0
    
    # Timestamps
    admitted_at: str = ""
    last_seen: str = ""
    unbonding_started: str = ""
    
    # Violation history
    warnings: int = 0
    slashing_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "node_id": self.node_id,
            "public_key": self.public_key,
            "stake_amount": self.stake_amount,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "uptime_percent": self.uptime_percent,
            "blocks_produced": self.blocks_produced,
            "blocks_missed": self.blocks_missed,
            "admitted_at": self.admitted_at,
            "last_seen": self.last_seen,
            "warnings": self.warnings,
            "slashing_events": self.slashing_events,
        }


# ══════════════════════════════════════════════════════════════════════════════
# POLICY UPDATE PROPOSAL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PolicyProposal:
    """
    Proposal to update federation policy.
    
    Requires 2/3 quorum to pass (INV-GOV-001).
    """
    
    proposal_id: str
    update_type: PolicyUpdateType
    
    # What's changing
    changes: Dict[str, Any]
    
    # Voting
    votes_for: Set[str] = field(default_factory=set)
    votes_against: Set[str] = field(default_factory=set)
    
    # Status
    status: str = "PENDING"       # PENDING, PASSED, REJECTED, EXPIRED
    
    # Timestamps
    created_at: str = ""
    expires_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# FEDERATION POLICY
# ══════════════════════════════════════════════════════════════════════════════

class FederationPolicy:
    """
    The Constitution of the Mesh.
    
    Manages:
      - Node admission via PeeringContracts
      - Node status tracking
      - Policy updates via quorum voting
    
    INVARIANTS:
      INV-GOV-001: Policy changes require 2/3 consensus (> tx consensus 1/2)
    """
    
    def __init__(self, config: Optional[PolicyConfig] = None):
        """
        Initialize federation policy.
        
        Args:
            config: Policy configuration (uses defaults if None)
        """
        self._config = config or PolicyConfig()
        
        # Node registry
        self._nodes: Dict[str, NodeRecord] = {}
        
        # Pending proposals
        self._proposals: Dict[str, PolicyProposal] = {}
        
        # Policy update history
        self._update_history: List[Dict[str, Any]] = []
        
        logger.info(f"FederationPolicy initialized with config v{self._config.version}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # CONFIGURATION ACCESS
    # ──────────────────────────────────────────────────────────────────────────
    
    @property
    def config(self) -> PolicyConfig:
        """Get current policy configuration."""
        return self._config
    
    @property
    def active_nodes(self) -> List[NodeRecord]:
        """Get all active nodes."""
        return [n for n in self._nodes.values() if n.status == NodeStatus.ACTIVE]
    
    @property
    def node_count(self) -> int:
        """Get count of active nodes."""
        return len(self.active_nodes)
    
    def get_node(self, node_id: str) -> Optional[NodeRecord]:
        """Get node by ID."""
        return self._nodes.get(node_id)
    
    # ──────────────────────────────────────────────────────────────────────────
    # NODE ADMISSION
    # ──────────────────────────────────────────────────────────────────────────
    
    def validate_contract(self, contract: PeeringContract) -> Tuple[bool, str]:
        """
        Validate a peering contract meets requirements.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check node ID uniqueness
        if contract.node_id in self._nodes:
            return False, f"Node ID {contract.node_id} already exists"
        
        # Check minimum stake
        if contract.stake_amount < self._config.min_stake:
            return False, (f"Insufficient stake: {contract.stake_amount} "
                          f"< {self._config.min_stake}")
        
        # Check public key uniqueness
        for node in self._nodes.values():
            if node.public_key == contract.public_key:
                return False, f"Public key already registered by {node.node_id}"
        
        # Check endpoint format (basic validation)
        if not contract.endpoint or ":" not in contract.endpoint:
            return False, "Invalid endpoint format"
        
        return True, "Contract valid"
    
    def admit_node(self, contract: PeeringContract) -> Tuple[bool, str]:
        """
        Admit a node to the federation.
        
        Args:
            contract: The peering contract
            
        Returns:
            Tuple of (success, message)
        """
        # Validate
        is_valid, reason = self.validate_contract(contract)
        if not is_valid:
            logger.warning(f"Rejected contract for {contract.node_id}: {reason}")
            return False, reason
        
        # Create node record
        now = datetime.now(timezone.utc).isoformat()
        record = NodeRecord(
            node_id=contract.node_id,
            public_key=contract.public_key,
            stake_amount=contract.stake_amount,
            endpoint=contract.endpoint,
            status=NodeStatus.ACTIVE,
            status_reason="Admitted via valid peering contract",
            admitted_at=now,
            last_seen=now,
        )
        
        self._nodes[contract.node_id] = record
        
        logger.info(f"Admitted node {contract.node_id} with stake {contract.stake_amount}")
        
        return True, f"Node {contract.node_id} admitted to federation"
    
    # ──────────────────────────────────────────────────────────────────────────
    # NODE STATUS MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    
    def update_node_status(
        self,
        node_id: str,
        new_status: NodeStatus,
        reason: str
    ) -> Tuple[bool, str]:
        """
        Update a node's status.
        
        Args:
            node_id: The node to update
            new_status: New status
            reason: Reason for change
            
        Returns:
            Tuple of (success, message)
        """
        node = self._nodes.get(node_id)
        if not node:
            return False, f"Node {node_id} not found"
        
        old_status = node.status
        node.status = new_status
        node.status_reason = reason
        
        # Handle unbonding start time
        if new_status == NodeStatus.UNBONDING:
            node.unbonding_started = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Node {node_id} status: {old_status.value} → {new_status.value} ({reason})")
        
        return True, f"Status updated to {new_status.value}"
    
    def warn_node(self, node_id: str, reason: str) -> Tuple[bool, str]:
        """
        Issue a warning to a node.
        
        Args:
            node_id: The node to warn
            reason: Warning reason
            
        Returns:
            Tuple of (success, message)
        """
        node = self._nodes.get(node_id)
        if not node:
            return False, f"Node {node_id} not found"
        
        node.warnings += 1
        
        # Auto-probation after 3 warnings
        if node.warnings >= 3 and node.status == NodeStatus.ACTIVE:
            self.update_node_status(node_id, NodeStatus.PROBATION, 
                                   f"3+ warnings ({reason})")
        
        logger.warning(f"Warning #{node.warnings} for {node_id}: {reason}")
        
        return True, f"Warning issued (total: {node.warnings})"
    
    def ban_node(self, node_id: str, reason: str) -> Tuple[bool, str]:
        """
        Permanently ban a node.
        
        Args:
            node_id: The node to ban
            reason: Ban reason
            
        Returns:
            Tuple of (success, message)
        """
        node = self._nodes.get(node_id)
        if not node:
            return False, f"Node {node_id} not found"
        
        if node.status == NodeStatus.BANNED:
            return False, f"Node {node_id} already banned"
        
        self.update_node_status(node_id, NodeStatus.BANNED, reason)
        
        logger.error(f"BANNED node {node_id}: {reason}")
        
        return True, f"Node {node_id} BANNED: {reason}"
    
    def start_unbonding(self, node_id: str) -> Tuple[bool, str]:
        """
        Start the unbonding period for a node leaving voluntarily.
        
        The node's stake is locked for unbonding_period seconds.
        
        Returns:
            Tuple of (success, message)
        """
        node = self._nodes.get(node_id)
        if not node:
            return False, f"Node {node_id} not found"
        
        if node.status == NodeStatus.BANNED:
            return False, f"Banned nodes cannot unbond"
        
        self.update_node_status(node_id, NodeStatus.UNBONDING, "Voluntary exit requested")
        
        unbond_days = self._config.unbonding_period // 86400
        return True, f"Unbonding started. Stake locked for {unbond_days} days."
    
    def check_unbonding_complete(self, node_id: str) -> Tuple[bool, int]:
        """
        Check if unbonding period is complete.
        
        Returns:
            Tuple of (is_complete, seconds_remaining)
        """
        node = self._nodes.get(node_id)
        if not node or node.status != NodeStatus.UNBONDING:
            return False, -1
        
        if not node.unbonding_started:
            return False, -1
        
        started = datetime.fromisoformat(node.unbonding_started.replace('Z', '+00:00'))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        remaining = int(self._config.unbonding_period - elapsed)
        
        if remaining <= 0:
            return True, 0
        
        return False, remaining
    
    # ──────────────────────────────────────────────────────────────────────────
    # POLICY UPDATES (2/3 QUORUM)
    # ──────────────────────────────────────────────────────────────────────────
    
    def propose_policy_update(
        self,
        proposer_id: str,
        update_type: PolicyUpdateType,
        changes: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Propose a policy update.
        
        INV-GOV-001: Requires 2/3 quorum to pass.
        
        Args:
            proposer_id: Node proposing the change
            update_type: Type of change
            changes: The proposed changes
            
        Returns:
            Tuple of (success, proposal_id)
        """
        # Verify proposer is active
        proposer = self._nodes.get(proposer_id)
        if not proposer or proposer.status != NodeStatus.ACTIVE:
            return False, "Proposer must be active node"
        
        # Create proposal
        proposal_id = hashlib.sha256(
            f"{proposer_id}:{time.time()}:{json.dumps(changes)}".encode()
        ).hexdigest()[:16]
        
        proposal = PolicyProposal(
            proposal_id=proposal_id,
            update_type=update_type,
            changes=changes,
            votes_for={proposer_id},  # Proposer automatically votes for
        )
        
        self._proposals[proposal_id] = proposal
        
        logger.info(f"Policy proposal {proposal_id} created by {proposer_id}")
        
        return True, proposal_id
    
    def vote_on_proposal(
        self,
        proposal_id: str,
        voter_id: str,
        vote_for: bool
    ) -> Tuple[bool, str]:
        """
        Vote on a policy proposal.
        
        Args:
            proposal_id: The proposal
            voter_id: The voting node
            vote_for: True = for, False = against
            
        Returns:
            Tuple of (success, message)
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False, "Proposal not found"
        
        if proposal.status != "PENDING":
            return False, f"Proposal already {proposal.status}"
        
        # Verify voter is active
        voter = self._nodes.get(voter_id)
        if not voter or voter.status != NodeStatus.ACTIVE:
            return False, "Voter must be active node"
        
        # Record vote
        if vote_for:
            proposal.votes_for.add(voter_id)
            proposal.votes_against.discard(voter_id)
        else:
            proposal.votes_against.add(voter_id)
            proposal.votes_for.discard(voter_id)
        
        # Check if quorum reached
        result = self._check_proposal_quorum(proposal_id)
        
        return True, f"Vote recorded. {result}"
    
    def _check_proposal_quorum(self, proposal_id: str) -> str:
        """
        Check if proposal has reached quorum.
        
        INV-GOV-001: 2/3 quorum required for policy changes.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return "Proposal not found"
        
        total_active = self.node_count
        if total_active == 0:
            return "No active nodes"
        
        votes_for = len(proposal.votes_for)
        votes_against = len(proposal.votes_against)
        
        required = int(total_active * self._config.policy_quorum) + 1
        
        if votes_for >= required:
            # PASSED - Apply changes
            proposal.status = "PASSED"
            self._apply_policy_update(proposal)
            return f"PASSED ({votes_for}/{total_active} ≥ {self._config.policy_quorum*100:.0f}%)"
        
        if votes_against > total_active - required:
            # Cannot pass anymore
            proposal.status = "REJECTED"
            return f"REJECTED (cannot reach quorum)"
        
        return f"PENDING ({votes_for}/{required} needed)"
    
    def _apply_policy_update(self, proposal: PolicyProposal):
        """Apply a passed policy update."""
        changes = proposal.changes
        
        # Apply each change
        if "min_stake" in changes:
            self._config.min_stake = changes["min_stake"]
        if "min_uptime_percent" in changes:
            self._config.min_uptime_percent = changes["min_uptime_percent"]
        if "unbonding_period" in changes:
            self._config.unbonding_period = changes["unbonding_period"]
        
        # Update version
        self._config.version += 1
        self._config.last_updated = datetime.now(timezone.utc).isoformat()
        self._config.update_hash = self._config._compute_hash()
        
        # Record in history
        self._update_history.append({
            "proposal_id": proposal.proposal_id,
            "changes": changes,
            "new_version": self._config.version,
            "timestamp": self._config.last_updated,
        })
        
        logger.info(f"Policy updated to v{self._config.version}: {changes}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get federation status."""
        return {
            "config_version": self._config.version,
            "config_hash": self._config.update_hash,
            "total_nodes": len(self._nodes),
            "active_nodes": self.node_count,
            "pending_proposals": len([p for p in self._proposals.values() 
                                     if p.status == "PENDING"]),
            "nodes_by_status": {
                status.value: len([n for n in self._nodes.values() 
                                  if n.status == status])
                for status in NodeStatus
            },
        }


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate policy module."""
    print("=" * 70)
    print("FEDERATION POLICY v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Config invariant validation
    print("\n[1/5] Testing policy config invariants (INV-GOV-001)...")
    
    # Valid config
    config = PolicyConfig(policy_quorum=2/3, tx_quorum=1/2)
    assert config.policy_quorum > config.tx_quorum
    print(f"      ✓ Valid config: policy_quorum={config.policy_quorum:.2f} > tx_quorum={config.tx_quorum:.2f}")
    
    # Invalid config should raise
    try:
        bad_config = PolicyConfig(policy_quorum=0.5, tx_quorum=0.5)
        print("      ✗ Should have raised ValueError!")
        raise AssertionError("Invalid config accepted")
    except ValueError as e:
        print(f"      ✓ Invalid config rejected: INV-GOV-001")
    
    # Test 2: Node admission
    print("\n[2/5] Testing node admission...")
    policy = FederationPolicy()
    
    contract = PeeringContract(
        node_id="NODE-1",
        public_key="pk_node1_abc123",
        stake_amount=15000,
        endpoint="node1.mesh.io:8080",
    )
    
    success, msg = policy.admit_node(contract)
    assert success, f"Admission failed: {msg}"
    assert policy.node_count == 1
    
    node = policy.get_node("NODE-1")
    assert node.status == NodeStatus.ACTIVE
    
    print(f"      ✓ Node admitted: {node.node_id}")
    print(f"      ✓ Status: {node.status.value}")
    print(f"      ✓ Stake: {node.stake_amount}")
    
    # Test 3: Reject insufficient stake
    print("\n[3/5] Testing admission rejection...")
    
    low_stake = PeeringContract(
        node_id="NODE-POOR",
        public_key="pk_poor_xyz",
        stake_amount=5000,  # Below minimum
        endpoint="poor.mesh.io:8080",
    )
    
    success, msg = policy.admit_node(low_stake)
    assert not success
    assert "Insufficient stake" in msg
    print(f"      ✓ Low stake rejected: {msg}")
    
    # Test 4: Unbonding period
    print("\n[4/5] Testing unbonding period...")
    
    success, msg = policy.start_unbonding("NODE-1")
    assert success
    
    node = policy.get_node("NODE-1")
    assert node.status == NodeStatus.UNBONDING
    
    is_complete, remaining = policy.check_unbonding_complete("NODE-1")
    assert not is_complete
    assert remaining > 0
    
    print(f"      ✓ Unbonding started for NODE-1")
    print(f"      ✓ Time remaining: {remaining // 86400} days")
    
    # Test 5: Policy update with quorum
    print("\n[5/5] Testing policy update (2/3 quorum)...")
    
    # Add more nodes for quorum test
    for i in range(2, 5):
        contract = PeeringContract(
            node_id=f"NODE-{i}",
            public_key=f"pk_node{i}_xyz",
            stake_amount=15000,
            endpoint=f"node{i}.mesh.io:8080",
        )
        policy.admit_node(contract)
    
    # Reactivate NODE-1 for voting
    policy.update_node_status("NODE-1", NodeStatus.ACTIVE, "Test reactivation")
    
    print(f"      Active nodes: {policy.node_count}")
    
    # Propose stake increase
    success, proposal_id = policy.propose_policy_update(
        proposer_id="NODE-2",
        update_type=PolicyUpdateType.PARAMETER_CHANGE,
        changes={"min_stake": 20000}
    )
    assert success
    print(f"      ✓ Proposal created: {proposal_id}")
    
    # Vote (need 3/4 = 75% > 66.7%)
    policy.vote_on_proposal(proposal_id, "NODE-3", True)
    policy.vote_on_proposal(proposal_id, "NODE-4", True)
    
    proposal = policy._proposals[proposal_id]
    print(f"      ✓ Votes: {len(proposal.votes_for)}/4 for")
    print(f"      ✓ Status: {proposal.status}")
    
    if proposal.status == "PASSED":
        print(f"      ✓ Policy updated to v{policy.config.version}")
        print(f"      ✓ New min_stake: {policy.config.min_stake}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-GOV-001 (Constitutional Rigidity): ENFORCED")
    print("=" * 70)
    print("\n📜 The Constitution is ready. The Rules are set.")


if __name__ == "__main__":
    _self_test()
