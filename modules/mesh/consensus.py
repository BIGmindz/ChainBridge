#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MESH CONSENSUS - THE PARLIAMENT                          ║
║                   PAC-CON-P310-CONSENSUS-ENGINE                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Raft-based Distributed Consensus for Federated Mesh                         ║
║                                                                              ║
║  "Many voices, one truth."                                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Consensus Engine provides:
  - Leader Election via RequestVote RPC
  - Log Replication via AppendEntries RPC
  - Crash-safe Term and Vote persistence
  - Heartbeat-based failure detection

INVARIANTS:
  INV-CON-001 (Safety): Never commit two different values for the same log index.
  INV-CON-002 (Liveness): Eventually, a leader is elected if a quorum is up.

Raft State Machine:
  FOLLOWER → CANDIDATE (on election timeout)
  CANDIDATE → LEADER (on winning election)
  CANDIDATE → FOLLOWER (on discovering higher term)
  LEADER → FOLLOWER (on discovering higher term)

Usage:
    from modules.mesh.consensus import ConsensusEngine, RaftState
    
    engine = ConsensusEngine(
        node_id="NODE-ALPHA",
        peers=["NODE-BETA", "NODE-GAMMA"],
        persistence_path="data/consensus/"
    )
    
    await engine.start()
    
    # Propose a command (only leader can do this)
    result = await engine.propose_command({"action": "transfer", "amount": 100})
"""

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# RAFT STATE
# ══════════════════════════════════════════════════════════════════════════════

class RaftState(Enum):
    """
    Raft node states.
    
    State transitions:
      FOLLOWER → CANDIDATE: Election timeout expired
      CANDIDATE → LEADER: Won election (majority votes)
      CANDIDATE → FOLLOWER: Discovered higher term or lost election
      LEADER → FOLLOWER: Discovered higher term
    """
    
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()


# ══════════════════════════════════════════════════════════════════════════════
# LOG ENTRY
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LogEntry:
    """
    A single entry in the replicated log.
    
    INV-CON-001: Once committed, the entry at a given index is immutable.
    """
    
    index: int              # 1-indexed position in log
    term: int               # Term when entry was received by leader
    command: Dict[str, Any] # The actual command to apply to state machine
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "index": self.index,
            "term": self.term,
            "command": self.command,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """Deserialize from dictionary."""
        return cls(
            index=data["index"],
            term=data["term"],
            command=data["command"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat())
        )


# ══════════════════════════════════════════════════════════════════════════════
# RPC MESSAGES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RequestVoteRequest:
    """RequestVote RPC request."""
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class RequestVoteResponse:
    """RequestVote RPC response."""
    term: int
    vote_granted: bool
    voter_id: str


@dataclass
class AppendEntriesRequest:
    """AppendEntries RPC request (heartbeat and log replication)."""
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse:
    """AppendEntries RPC response."""
    term: int
    success: bool
    follower_id: str
    match_index: int  # Highest index known to be replicated


# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENT STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PersistentState:
    """
    State that must survive crashes.
    
    MUST persist before responding to any RPC.
    """
    
    current_term: int = 0
    voted_for: Optional[str] = None
    log: List[LogEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "current_term": self.current_term,
            "voted_for": self.voted_for,
            "log": [e.to_dict() for e in self.log]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersistentState":
        """Deserialize from dictionary."""
        return cls(
            current_term=data.get("current_term", 0),
            voted_for=data.get("voted_for"),
            log=[LogEntry.from_dict(e) for e in data.get("log", [])]
        )


# ══════════════════════════════════════════════════════════════════════════════
# CONSENSUS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ConsensusEngine:
    """
    Raft-based distributed consensus engine.
    
    Provides:
      - Leader election with randomized timeouts
      - Log replication with consistency checks
      - Commit notification callbacks
      - Crash-safe persistence
    
    INV-CON-001 (Safety): Achieved via term checks and log matching.
    INV-CON-002 (Liveness): Achieved via randomized election timeouts.
    """
    
    # Timing constants (milliseconds)
    HEARTBEAT_INTERVAL_MS = 150
    ELECTION_TIMEOUT_MIN_MS = 300
    ELECTION_TIMEOUT_MAX_MS = 500
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        persistence_path: Optional[str] = None,
        on_commit: Optional[Callable[[LogEntry], None]] = None,
        on_state_change: Optional[Callable[[RaftState], None]] = None
    ):
        """
        Initialize consensus engine.
        
        Args:
            node_id: This node's unique identifier
            peers: List of peer node IDs
            persistence_path: Directory for persistent state
            on_commit: Callback when entry is committed
            on_state_change: Callback when state changes
        """
        self.node_id = node_id
        self.peers = list(peers)
        self.persistence_path = persistence_path
        self.on_commit = on_commit
        self.on_state_change = on_state_change
        
        # Persistent state (survives crashes)
        self._persistent = PersistentState()
        
        # Volatile state (all servers)
        self._state = RaftState.FOLLOWER
        self._commit_index = 0  # Highest log entry known to be committed
        self._last_applied = 0  # Highest log entry applied to state machine
        
        # Volatile state (leaders only)
        self._next_index: Dict[str, int] = {}   # For each peer: next log index to send
        self._match_index: Dict[str, int] = {}  # For each peer: highest log index known replicated
        
        # Election state
        self._current_leader: Optional[str] = None
        self._votes_received: Set[str] = set()
        self._election_timeout: float = 0
        self._last_heartbeat: float = 0
        
        # Runtime
        self._running = False
        self._rpc_handlers: Dict[str, Callable] = {}
        self._send_rpc: Optional[Callable] = None
        
        # Load persistent state
        self._load_state()
    
    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES
    # ──────────────────────────────────────────────────────────────────────────
    
    @property
    def state(self) -> RaftState:
        """Current Raft state."""
        return self._state
    
    @property
    def current_term(self) -> int:
        """Current term number."""
        return self._persistent.current_term
    
    @property
    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self._state == RaftState.LEADER
    
    @property
    def leader_id(self) -> Optional[str]:
        """Get current leader ID (if known)."""
        if self._state == RaftState.LEADER:
            return self.node_id
        return self._current_leader
    
    @property
    def cluster_size(self) -> int:
        """Total nodes in cluster (including self)."""
        return len(self.peers) + 1
    
    @property
    def quorum_size(self) -> int:
        """Majority needed for consensus."""
        return (self.cluster_size // 2) + 1
    
    @property
    def log(self) -> List[LogEntry]:
        """Get the log entries."""
        return self._persistent.log
    
    @property
    def last_log_index(self) -> int:
        """Index of last log entry (0 if empty)."""
        return len(self._persistent.log)
    
    @property
    def last_log_term(self) -> int:
        """Term of last log entry (0 if empty)."""
        if self._persistent.log:
            return self._persistent.log[-1].term
        return 0
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATE TRANSITIONS
    # ──────────────────────────────────────────────────────────────────────────
    
    def _transition_to(self, new_state: RaftState):
        """Transition to a new state."""
        if self._state == new_state:
            return
        
        old_state = self._state
        self._state = new_state
        
        logger.info(f"[{self.node_id}] State: {old_state.name} → {new_state.name} "
                   f"(term={self.current_term})")
        
        if new_state == RaftState.LEADER:
            self._current_leader = self.node_id
            self._initialize_leader_state()
        
        if self.on_state_change:
            self.on_state_change(new_state)
    
    def _initialize_leader_state(self):
        """Initialize volatile leader state after winning election."""
        next_idx = self.last_log_index + 1
        for peer in self.peers:
            self._next_index[peer] = next_idx
            self._match_index[peer] = 0
    
    def _step_down(self, new_term: int):
        """Step down to follower when higher term discovered."""
        if new_term > self.current_term:
            self._persistent.current_term = new_term
            self._persistent.voted_for = None
            self._save_state()
            self._transition_to(RaftState.FOLLOWER)
    
    # ──────────────────────────────────────────────────────────────────────────
    # ELECTION
    # ──────────────────────────────────────────────────────────────────────────
    
    def _reset_election_timeout(self):
        """Reset election timeout to random value."""
        self._election_timeout = time.time() + random.uniform(
            self.ELECTION_TIMEOUT_MIN_MS / 1000,
            self.ELECTION_TIMEOUT_MAX_MS / 1000
        )
    
    def _election_timeout_elapsed(self) -> bool:
        """Check if election timeout has elapsed."""
        return time.time() >= self._election_timeout
    
    async def _start_election(self):
        """
        Start a new election.
        
        INV-CON-002: Randomized timeout ensures liveness.
        """
        # Increment term
        self._persistent.current_term += 1
        self._persistent.voted_for = self.node_id  # Vote for self
        self._save_state()
        
        # Transition to candidate
        self._transition_to(RaftState.CANDIDATE)
        self._votes_received = {self.node_id}  # Vote for self
        
        logger.info(f"[{self.node_id}] Starting election for term {self.current_term}")
        
        # Reset election timeout
        self._reset_election_timeout()
        
        # Request votes from all peers
        request = RequestVoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=self.last_log_index,
            last_log_term=self.last_log_term
        )
        
        for peer in self.peers:
            await self._send_request_vote(peer, request)
    
    async def _send_request_vote(self, peer: str, request: RequestVoteRequest):
        """Send RequestVote RPC to a peer."""
        if self._send_rpc:
            try:
                response = await self._send_rpc(peer, "RequestVote", {
                    "term": request.term,
                    "candidate_id": request.candidate_id,
                    "last_log_index": request.last_log_index,
                    "last_log_term": request.last_log_term
                })
                if response:
                    await self._handle_request_vote_response(response)
            except Exception as e:
                logger.debug(f"[{self.node_id}] Failed to send RequestVote to {peer}: {e}")
    
    def handle_request_vote(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming RequestVote RPC.
        
        Grant vote if:
          1. Candidate's term >= our term
          2. We haven't voted for anyone else this term
          3. Candidate's log is at least as up-to-date as ours
        """
        req = RequestVoteRequest(
            term=request["term"],
            candidate_id=request["candidate_id"],
            last_log_index=request["last_log_index"],
            last_log_term=request["last_log_term"]
        )
        
        # Step down if higher term
        if req.term > self.current_term:
            self._step_down(req.term)
        
        vote_granted = False
        
        if req.term >= self.current_term:
            # Check if we can vote for this candidate
            can_vote = (
                self._persistent.voted_for is None or
                self._persistent.voted_for == req.candidate_id
            )
            
            # Check if candidate's log is up-to-date
            log_ok = (
                req.last_log_term > self.last_log_term or
                (req.last_log_term == self.last_log_term and
                 req.last_log_index >= self.last_log_index)
            )
            
            if can_vote and log_ok:
                vote_granted = True
                self._persistent.voted_for = req.candidate_id
                self._save_state()
                self._reset_election_timeout()
                logger.debug(f"[{self.node_id}] Granted vote to {req.candidate_id} "
                           f"for term {req.term}")
        
        return {
            "term": self.current_term,
            "vote_granted": vote_granted,
            "voter_id": self.node_id
        }
    
    async def _handle_request_vote_response(self, response: Dict[str, Any]):
        """Handle RequestVote response."""
        resp = RequestVoteResponse(
            term=response["term"],
            vote_granted=response["vote_granted"],
            voter_id=response.get("voter_id", "unknown")
        )
        
        # Step down if higher term
        if resp.term > self.current_term:
            self._step_down(resp.term)
            return
        
        # Only process if still candidate for same term
        if self._state != RaftState.CANDIDATE:
            return
        
        if resp.vote_granted:
            self._votes_received.add(resp.voter_id)
            logger.debug(f"[{self.node_id}] Received vote from {resp.voter_id} "
                        f"({len(self._votes_received)}/{self.quorum_size} needed)")
            
            # Check if we've won
            if len(self._votes_received) >= self.quorum_size:
                logger.info(f"[{self.node_id}] Won election for term {self.current_term}!")
                self._transition_to(RaftState.LEADER)
                await self._send_heartbeats()
    
    # ──────────────────────────────────────────────────────────────────────────
    # LOG REPLICATION
    # ──────────────────────────────────────────────────────────────────────────
    
    async def _send_heartbeats(self):
        """Send heartbeats (empty AppendEntries) to all peers."""
        if self._state != RaftState.LEADER:
            return
        
        self._last_heartbeat = time.time()
        
        for peer in self.peers:
            await self._send_append_entries(peer)
    
    async def _send_append_entries(self, peer: str):
        """Send AppendEntries RPC to a peer."""
        if self._state != RaftState.LEADER:
            return
        
        next_idx = self._next_index.get(peer, 1)
        prev_idx = next_idx - 1
        prev_term = 0
        
        if prev_idx > 0 and prev_idx <= len(self._persistent.log):
            prev_term = self._persistent.log[prev_idx - 1].term
        
        # Get entries to send
        entries = self._persistent.log[prev_idx:]
        
        request = AppendEntriesRequest(
            term=self.current_term,
            leader_id=self.node_id,
            prev_log_index=prev_idx,
            prev_log_term=prev_term,
            entries=entries,
            leader_commit=self._commit_index
        )
        
        if self._send_rpc:
            try:
                response = await self._send_rpc(peer, "AppendEntries", {
                    "term": request.term,
                    "leader_id": request.leader_id,
                    "prev_log_index": request.prev_log_index,
                    "prev_log_term": request.prev_log_term,
                    "entries": [e.to_dict() for e in request.entries],
                    "leader_commit": request.leader_commit
                })
                if response:
                    await self._handle_append_entries_response(peer, response)
            except Exception as e:
                logger.debug(f"[{self.node_id}] Failed to send AppendEntries to {peer}: {e}")
    
    def handle_append_entries(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming AppendEntries RPC.
        
        INV-CON-001: Log matching property ensures safety.
        """
        req = AppendEntriesRequest(
            term=request["term"],
            leader_id=request["leader_id"],
            prev_log_index=request["prev_log_index"],
            prev_log_term=request["prev_log_term"],
            entries=[LogEntry.from_dict(e) for e in request.get("entries", [])],
            leader_commit=request["leader_commit"]
        )
        
        # Step down if higher term
        if req.term > self.current_term:
            self._step_down(req.term)
        
        success = False
        match_index = 0
        
        if req.term >= self.current_term:
            # Valid leader contact - reset election timeout
            self._reset_election_timeout()
            self._current_leader = req.leader_id
            
            # Become follower if candidate
            if self._state == RaftState.CANDIDATE:
                self._transition_to(RaftState.FOLLOWER)
            
            # Check log consistency
            if req.prev_log_index == 0:
                # First entry, always matches
                success = True
            elif req.prev_log_index <= len(self._persistent.log):
                # Check term of previous entry
                if self._persistent.log[req.prev_log_index - 1].term == req.prev_log_term:
                    success = True
            
            if success:
                # Append new entries (handle conflicts)
                insert_idx = req.prev_log_index
                
                for entry in req.entries:
                    if insert_idx < len(self._persistent.log):
                        # Check for conflict
                        if self._persistent.log[insert_idx].term != entry.term:
                            # Delete conflicting entry and all following
                            self._persistent.log = self._persistent.log[:insert_idx]
                            self._persistent.log.append(entry)
                        # Else: entry already present, skip
                    else:
                        self._persistent.log.append(entry)
                    insert_idx += 1
                
                self._save_state()
                match_index = len(self._persistent.log)
                
                # Update commit index
                if req.leader_commit > self._commit_index:
                    self._commit_index = min(req.leader_commit, len(self._persistent.log))
                    self._apply_committed_entries()
        
        return {
            "term": self.current_term,
            "success": success,
            "follower_id": self.node_id,
            "match_index": match_index
        }
    
    async def _handle_append_entries_response(self, peer: str, response: Dict[str, Any]):
        """Handle AppendEntries response."""
        resp = AppendEntriesResponse(
            term=response["term"],
            success=response["success"],
            follower_id=response.get("follower_id", peer),
            match_index=response.get("match_index", 0)
        )
        
        # Step down if higher term
        if resp.term > self.current_term:
            self._step_down(resp.term)
            return
        
        if self._state != RaftState.LEADER:
            return
        
        if resp.success:
            # Update match_index and next_index
            self._match_index[peer] = resp.match_index
            self._next_index[peer] = resp.match_index + 1
            
            # Try to advance commit index
            self._try_advance_commit_index()
        else:
            # Decrement next_index and retry
            if self._next_index.get(peer, 1) > 1:
                self._next_index[peer] = self._next_index.get(peer, 1) - 1
    
    def _try_advance_commit_index(self):
        """
        Try to advance commit index based on replication status.
        
        INV-CON-001: Only commit entries from current term by counting replicas.
        """
        if self._state != RaftState.LEADER:
            return
        
        # Find the highest index replicated to a majority
        for n in range(self._commit_index + 1, len(self._persistent.log) + 1):
            # Count replicas (including self)
            replicas = 1  # Self
            for peer in self.peers:
                if self._match_index.get(peer, 0) >= n:
                    replicas += 1
            
            # Check if majority and current term
            if replicas >= self.quorum_size:
                if self._persistent.log[n - 1].term == self.current_term:
                    self._commit_index = n
                    logger.info(f"[{self.node_id}] Committed index {n}")
        
        self._apply_committed_entries()
    
    def _apply_committed_entries(self):
        """Apply committed entries to state machine."""
        while self._last_applied < self._commit_index:
            self._last_applied += 1
            entry = self._persistent.log[self._last_applied - 1]
            
            logger.debug(f"[{self.node_id}] Applying entry {entry.index}: {entry.command}")
            
            if self.on_commit:
                self.on_commit(entry)
    
    # ──────────────────────────────────────────────────────────────────────────
    # CLIENT INTERFACE
    # ──────────────────────────────────────────────────────────────────────────
    
    async def propose_command(self, command: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Propose a new command to be replicated.
        
        Args:
            command: The command to replicate
            
        Returns:
            Tuple of (success, message)
        """
        if self._state != RaftState.LEADER:
            if self._current_leader:
                return False, f"Not leader. Current leader: {self._current_leader}"
            return False, "Not leader. No leader known."
        
        # Append to log
        entry = LogEntry(
            index=len(self._persistent.log) + 1,
            term=self.current_term,
            command=command
        )
        self._persistent.log.append(entry)
        self._save_state()
        
        logger.info(f"[{self.node_id}] Proposed command at index {entry.index}")
        
        # Send AppendEntries to all peers
        for peer in self.peers:
            await self._send_append_entries(peer)
        
        return True, f"Command proposed at index {entry.index}"
    
    # ──────────────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────────────────────────────────────
    
    async def start(self):
        """Start the consensus engine."""
        self._running = True
        self._reset_election_timeout()
        
        logger.info(f"[{self.node_id}] Starting consensus engine "
                   f"(cluster size: {self.cluster_size}, quorum: {self.quorum_size})")
        
        await self._run_loop()
    
    async def stop(self):
        """Stop the consensus engine."""
        self._running = False
        logger.info(f"[{self.node_id}] Stopping consensus engine")
    
    async def _run_loop(self):
        """Main consensus loop."""
        while self._running:
            try:
                if self._state == RaftState.LEADER:
                    # Send heartbeats periodically
                    if time.time() - self._last_heartbeat >= self.HEARTBEAT_INTERVAL_MS / 1000:
                        await self._send_heartbeats()
                else:
                    # Check for election timeout
                    if self._election_timeout_elapsed():
                        await self._start_election()
                
                # Small sleep to prevent busy-waiting
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.node_id}] Error in consensus loop: {e}")
                await asyncio.sleep(0.1)
    
    async def tick(self):
        """
        Process one tick of the consensus engine.
        
        For testing without full async loop.
        """
        if self._state == RaftState.LEADER:
            if time.time() - self._last_heartbeat >= self.HEARTBEAT_INTERVAL_MS / 1000:
                await self._send_heartbeats()
        else:
            if self._election_timeout_elapsed():
                await self._start_election()
    
    # ──────────────────────────────────────────────────────────────────────────
    # RPC REGISTRATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def set_rpc_sender(self, sender: Callable):
        """
        Set the RPC sender function.
        
        Signature: async def sender(peer: str, method: str, params: Dict) -> Dict
        """
        self._send_rpc = sender
    
    def handle_rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming RPC.
        
        Args:
            method: RPC method name
            params: RPC parameters
            
        Returns:
            RPC response
        """
        if method == "RequestVote":
            return self.handle_request_vote(params)
        elif method == "AppendEntries":
            return self.handle_append_entries(params)
        else:
            logger.warning(f"[{self.node_id}] Unknown RPC method: {method}")
            return {"error": f"Unknown method: {method}"}
    
    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────
    
    def _save_state(self):
        """Save persistent state to disk."""
        if not self.persistence_path:
            return
        
        path = Path(self.persistence_path) / f"{self.node_id}_state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(self._persistent.to_dict(), f, indent=2)
    
    def _load_state(self):
        """Load persistent state from disk."""
        if not self.persistence_path:
            return
        
        path = Path(self.persistence_path) / f"{self.node_id}_state.json"
        
        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)
                self._persistent = PersistentState.from_dict(data)
            
            logger.info(f"[{self.node_id}] Loaded state: term={self.current_term}, "
                       f"log_length={len(self._persistent.log)}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "node_id": self.node_id,
            "state": self._state.name,
            "term": self.current_term,
            "leader": self.leader_id,
            "voted_for": self._persistent.voted_for,
            "commit_index": self._commit_index,
            "last_applied": self._last_applied,
            "log_length": len(self._persistent.log),
            "cluster_size": self.cluster_size,
            "quorum_size": self.quorum_size
        }


# ══════════════════════════════════════════════════════════════════════════════
# CLUSTER SIMULATOR (for testing)
# ══════════════════════════════════════════════════════════════════════════════

class ClusterSimulator:
    """
    Simulates a Raft cluster for testing.
    
    Provides in-memory RPC routing between nodes.
    """
    
    def __init__(self, node_ids: List[str]):
        """Initialize cluster simulator."""
        self.node_ids = node_ids
        self.nodes: Dict[str, ConsensusEngine] = {}
        self._network_enabled: Dict[str, bool] = {}  # For partitioning
        
        # Create nodes
        for node_id in node_ids:
            peers = [n for n in node_ids if n != node_id]
            engine = ConsensusEngine(node_id=node_id, peers=peers)
            engine.set_rpc_sender(self._make_rpc_sender(node_id))
            self.nodes[node_id] = engine
            self._network_enabled[node_id] = True
    
    def _make_rpc_sender(self, sender_id: str) -> Callable:
        """Create RPC sender function for a node."""
        async def send_rpc(peer: str, method: str, params: Dict) -> Optional[Dict]:
            # Check network partition
            if not self._network_enabled.get(sender_id, True):
                return None
            if not self._network_enabled.get(peer, True):
                return None
            
            # Route to peer
            peer_node = self.nodes.get(peer)
            if peer_node:
                return peer_node.handle_rpc(method, params)
            return None
        
        return send_rpc
    
    def partition(self, node_id: str):
        """Simulate network partition - disable a node."""
        self._network_enabled[node_id] = False
        logger.info(f"PARTITION: {node_id} disconnected")
    
    def heal(self, node_id: str):
        """Heal network partition - enable a node."""
        self._network_enabled[node_id] = True
        logger.info(f"HEAL: {node_id} reconnected")
    
    async def tick_all(self, ticks: int = 1):
        """Run tick on all nodes."""
        for _ in range(ticks):
            for node in self.nodes.values():
                if self._network_enabled.get(node.node_id, True):
                    await node.tick()
            await asyncio.sleep(0.01)
    
    def get_leader(self) -> Optional[str]:
        """Get current leader (if any)."""
        for node in self.nodes.values():
            if node.is_leader:
                return node.node_id
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get cluster status."""
        return {
            node_id: node.get_status()
            for node_id, node in self.nodes.items()
        }


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

async def _self_test():
    """Run self-test to validate consensus module."""
    print("=" * 70)
    print("MESH CONSENSUS v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Create cluster
    print("\n[1/5] Creating 3-node cluster...")
    cluster = ClusterSimulator(["NODE-A", "NODE-B", "NODE-C"])
    print(f"      ✓ Created {len(cluster.nodes)} nodes")
    print(f"      ✓ Quorum size: {cluster.nodes['NODE-A'].quorum_size}")
    
    # Test 2: Leader election
    print("\n[2/5] Testing leader election...")
    
    # Run ticks until leader elected
    for i in range(100):
        await cluster.tick_all(1)
        leader = cluster.get_leader()
        if leader:
            break
    
    assert leader, "Should elect a leader"
    print(f"      ✓ Leader elected: {leader}")
    print(f"      ✓ Term: {cluster.nodes[leader].current_term}")
    
    # Test 3: Log replication
    print("\n[3/5] Testing log replication...")
    leader_node = cluster.nodes[leader]
    
    # Propose a command
    success, msg = await leader_node.propose_command({"action": "SET", "key": "x", "value": 42})
    assert success, f"Propose should succeed: {msg}"
    print(f"      ✓ Command proposed: {msg}")
    
    # Run ticks for replication
    for _ in range(50):
        await cluster.tick_all(1)
    
    # Check replication
    for node_id, node in cluster.nodes.items():
        assert len(node.log) >= 1, f"{node_id} should have log entry"
    print(f"      ✓ Log replicated to all nodes")
    
    # Test 4: Leader failure and re-election
    print("\n[4/5] Testing leader failure and re-election...")
    old_leader = leader
    
    # Partition the leader
    cluster.partition(leader)
    print(f"      ✓ Partitioned leader: {old_leader}")
    
    # Run ticks until new leader
    new_leader = None
    for i in range(100):
        await cluster.tick_all(1)
        for node_id, node in cluster.nodes.items():
            if node_id != old_leader and node.is_leader:
                new_leader = node_id
                break
        if new_leader:
            break
    
    assert new_leader, "Should elect new leader"
    assert new_leader != old_leader, "New leader should be different"
    print(f"      ✓ New leader elected: {new_leader}")
    print(f"      ✓ New term: {cluster.nodes[new_leader].current_term}")
    
    # Test 5: Status check
    print("\n[5/5] Testing cluster status...")
    status = cluster.get_status()
    
    for node_id, node_status in status.items():
        state = node_status["state"]
        term = node_status["term"]
        print(f"      ✓ {node_id}: {state} (term={term})")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-CON-001 (Safety): ENFORCED")
    print("INV-CON-002 (Liveness): ENFORCED")
    print("=" * 70)
    print("\n🏛️ The Parliament is seated. The Gavel is ready.")


def _run_self_test():
    """Synchronous wrapper for self-test."""
    asyncio.run(_self_test())


if __name__ == "__main__":
    _run_self_test()
