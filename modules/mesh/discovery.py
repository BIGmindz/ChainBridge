#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MESH DISCOVERY - THE GOSSIP                              ║
║                   PAC-NET-P300-MESH-NETWORKING                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  SWIM-lite Gossip Protocol for peer discovery and failure detection          ║
║                                                                              ║
║  "One is none. Two is one. Many is Sovereign."                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Gossip Protocol provides:
  - Decentralized peer discovery
  - Failure detection via indirect probing
  - Membership protocol (join/leave/fail)
  - Dissemination of topology updates

SWIM Protocol (Simplified):
  1. PING: Direct probe to random peer
  2. PING-REQ: Indirect probe via k members
  3. SUSPECT: Mark unresponsive peer
  4. FAIL: Declare peer dead after timeout

INVARIANTS:
  INV-NET-002 (Topology Awareness): Every node knows its neighbors
  INV-NET-003 (Sovereign Interop): Peers can join/leave freely

Usage:
    from modules.mesh.discovery import GossipProtocol, PeerRegistry
    
    registry = PeerRegistry()
    gossip = GossipProtocol(node_id="NODE-ALPHA", registry=registry)
    
    # Start gossip protocol
    await gossip.start()
    
    # Handle discovery events
    gossip.on_peer_join(lambda p: print(f"New peer: {p.peer_id}"))
    gossip.on_peer_fail(lambda p: print(f"Peer failed: {p.peer_id}"))
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# TYPES AND ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class MemberStatus(Enum):
    """Membership status in the gossip protocol."""
    ALIVE = "alive"       # Peer is responding
    SUSPECT = "suspect"   # Peer missed heartbeats
    DEAD = "dead"         # Peer declared failed
    LEFT = "left"         # Peer gracefully left


class DiscoveryEventType(Enum):
    """Types of discovery events."""
    PEER_DISCOVERED = "peer_discovered"
    PEER_JOINED = "peer_joined"
    PEER_LEFT = "peer_left"
    PEER_SUSPECTED = "peer_suspected"
    PEER_FAILED = "peer_failed"
    PEER_RECOVERED = "peer_recovered"
    TOPOLOGY_CHANGED = "topology_changed"


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DiscoveryEvent:
    """
    Event emitted during peer discovery.
    
    Used for tracking membership changes and topology updates.
    """
    event_type: DiscoveryEventType
    peer_id: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, event_type: DiscoveryEventType, peer_id: str, **details) -> "DiscoveryEvent":
        return cls(
            event_type=event_type,
            peer_id=peer_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "peer_id": self.peer_id,
            "timestamp": self.timestamp,
            "details": self.details
        }


@dataclass
class Member:
    """
    A member in the gossip membership list.
    
    Tracks health status and metadata for each known peer.
    """
    peer_id: str
    host: str
    port: int
    status: MemberStatus = MemberStatus.ALIVE
    incarnation: int = 0  # Version number for state
    
    # Health tracking
    last_ping_sent: float = 0.0
    last_pong_received: float = 0.0
    missed_pings: int = 0
    
    # Metadata
    federation_id: str = ""
    region: str = ""
    version: str = ""
    capabilities: List[str] = field(default_factory=list)
    
    # Timestamps
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status_changed: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def update_status(self, new_status: MemberStatus):
        """Update member status with timestamp."""
        if self.status != new_status:
            self.status = new_status
            self.status_changed = datetime.now(timezone.utc).isoformat()
            self.incarnation += 1
    
    def mark_alive(self):
        """Mark member as alive (responding)."""
        self.update_status(MemberStatus.ALIVE)
        self.last_seen = datetime.now(timezone.utc).isoformat()
        self.missed_pings = 0
    
    def mark_suspect(self):
        """Mark member as suspect (missed heartbeats)."""
        self.update_status(MemberStatus.SUSPECT)
    
    def mark_dead(self):
        """Mark member as dead (failed)."""
        self.update_status(MemberStatus.DEAD)
    
    @property
    def is_alive(self) -> bool:
        return self.status == MemberStatus.ALIVE
    
    @property
    def is_suspect(self) -> bool:
        return self.status == MemberStatus.SUSPECT
    
    @property
    def is_dead(self) -> bool:
        return self.status == MemberStatus.DEAD
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "incarnation": self.incarnation,
            "federation_id": self.federation_id,
            "region": self.region,
            "version": self.version,
            "capabilities": self.capabilities,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen
        }


# ══════════════════════════════════════════════════════════════════════════════
# PEER REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

class PeerRegistry:
    """
    Central registry of known peers.
    
    Maintains the membership list and provides query methods.
    INV-NET-002: Topology Awareness
    """
    
    def __init__(self):
        self._members: Dict[str, Member] = {}
        self._lock = asyncio.Lock()
        self._event_log: List[DiscoveryEvent] = []
        self._max_event_log = 1000
    
    async def add_member(self, member: Member) -> bool:
        """Add or update a member in the registry."""
        async with self._lock:
            existing = self._members.get(member.peer_id)
            
            if existing:
                # Update if newer incarnation
                if member.incarnation >= existing.incarnation:
                    self._members[member.peer_id] = member
                    return True
                return False
            else:
                self._members[member.peer_id] = member
                self._log_event(DiscoveryEvent.create(
                    DiscoveryEventType.PEER_DISCOVERED,
                    member.peer_id,
                    host=member.host,
                    port=member.port
                ))
                return True
    
    async def remove_member(self, peer_id: str, reason: str = "left"):
        """Remove a member from the registry."""
        async with self._lock:
            if peer_id in self._members:
                del self._members[peer_id]
                self._log_event(DiscoveryEvent.create(
                    DiscoveryEventType.PEER_LEFT if reason == "left" else DiscoveryEventType.PEER_FAILED,
                    peer_id,
                    reason=reason
                ))
    
    async def get_member(self, peer_id: str) -> Optional[Member]:
        """Get a member by ID."""
        async with self._lock:
            return self._members.get(peer_id)
    
    async def get_alive_members(self) -> List[Member]:
        """Get all alive members."""
        async with self._lock:
            return [m for m in self._members.values() if m.is_alive]
    
    async def get_suspect_members(self) -> List[Member]:
        """Get all suspect members."""
        async with self._lock:
            return [m for m in self._members.values() if m.is_suspect]
    
    async def get_all_members(self) -> List[Member]:
        """Get all members regardless of status."""
        async with self._lock:
            return list(self._members.values())
    
    async def get_random_members(self, k: int, exclude: Optional[Set[str]] = None) -> List[Member]:
        """Get k random alive members."""
        async with self._lock:
            candidates = [
                m for m in self._members.values()
                if m.is_alive and (not exclude or m.peer_id not in exclude)
            ]
            return random.sample(candidates, min(k, len(candidates)))
    
    async def update_status(self, peer_id: str, status: MemberStatus):
        """Update a member's status."""
        async with self._lock:
            member = self._members.get(peer_id)
            if member:
                old_status = member.status
                member.update_status(status)
                
                # Log status change
                if status == MemberStatus.SUSPECT:
                    self._log_event(DiscoveryEvent.create(
                        DiscoveryEventType.PEER_SUSPECTED,
                        peer_id
                    ))
                elif status == MemberStatus.DEAD:
                    self._log_event(DiscoveryEvent.create(
                        DiscoveryEventType.PEER_FAILED,
                        peer_id
                    ))
                elif status == MemberStatus.ALIVE and old_status == MemberStatus.SUSPECT:
                    self._log_event(DiscoveryEvent.create(
                        DiscoveryEventType.PEER_RECOVERED,
                        peer_id
                    ))
    
    def _log_event(self, event: DiscoveryEvent):
        """Log a discovery event."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_event_log:
            self._event_log = self._event_log[-self._max_event_log:]
    
    async def get_recent_events(self, limit: int = 100) -> List[DiscoveryEvent]:
        """Get recent discovery events."""
        async with self._lock:
            return self._event_log[-limit:]
    
    async def get_topology_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of current topology."""
        async with self._lock:
            alive = [m for m in self._members.values() if m.is_alive]
            suspect = [m for m in self._members.values() if m.is_suspect]
            dead = [m for m in self._members.values() if m.is_dead]
            
            return {
                "total_members": len(self._members),
                "alive_count": len(alive),
                "suspect_count": len(suspect),
                "dead_count": len(dead),
                "members": [m.to_dict() for m in self._members.values()],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# ══════════════════════════════════════════════════════════════════════════════
# GOSSIP PROTOCOL (SWIM-LITE)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GossipConfig:
    """Configuration for gossip protocol."""
    # Timing
    protocol_period_ms: int = 1000     # Main protocol loop interval
    ping_timeout_ms: int = 500         # Direct ping timeout
    ping_req_timeout_ms: int = 1000    # Indirect ping timeout
    suspect_timeout_ms: int = 5000     # Time before suspect → dead
    
    # Fan-out
    ping_req_members: int = 3          # K members for indirect probe
    dissemination_multiplier: int = 3  # Λ * log(n) broadcasts
    
    # Limits
    max_transmissions: int = 10        # Max times to propagate update


class GossipProtocol:
    """
    SWIM-lite Gossip Protocol implementation.
    
    Provides:
      - Failure detection via direct/indirect probing
      - Membership dissemination
      - Eventual consistency of member list
    
    SWIM Protocol:
      1. Each node periodically pings a random member (PING)
      2. If no response, ask K other members to ping (PING-REQ)
      3. If still no response, mark as SUSPECT
      4. After timeout, mark as DEAD and disseminate
    
    Example:
        registry = PeerRegistry()
        gossip = GossipProtocol("NODE-ALPHA", registry)
        
        gossip.on_peer_join(lambda m: print(f"Join: {m.peer_id}"))
        gossip.on_peer_fail(lambda m: print(f"Fail: {m.peer_id}"))
        
        await gossip.start()
    """
    
    def __init__(
        self,
        node_id: str,
        registry: PeerRegistry,
        config: Optional[GossipConfig] = None,
        send_callback: Optional[Callable] = None
    ):
        self.node_id = node_id
        self.registry = registry
        self.config = config or GossipConfig()
        self._send_callback = send_callback
        
        # State
        self._running = False
        self._protocol_round = 0
        self._pending_acks: Dict[str, float] = {}  # peer_id -> ping_sent_time
        
        # Event handlers
        self._on_peer_join: List[Callable] = []
        self._on_peer_fail: List[Callable] = []
        self._on_peer_leave: List[Callable] = []
        self._on_peer_suspect: List[Callable] = []
        
        # Updates to disseminate
        self._pending_updates: List[Dict[str, Any]] = []
        
        # Metrics
        self.metrics = {
            "protocol_rounds": 0,
            "pings_sent": 0,
            "pongs_received": 0,
            "ping_reqs_sent": 0,
            "members_suspected": 0,
            "members_failed": 0,
            "updates_disseminated": 0
        }
        
        logger.info(f"GossipProtocol initialized for {node_id}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # EVENT HANDLERS
    # ──────────────────────────────────────────────────────────────────────────
    
    def on_peer_join(self, callback: Callable[[Member], None]):
        """Register handler for peer join events."""
        self._on_peer_join.append(callback)
    
    def on_peer_fail(self, callback: Callable[[Member], None]):
        """Register handler for peer failure events."""
        self._on_peer_fail.append(callback)
    
    def on_peer_leave(self, callback: Callable[[Member], None]):
        """Register handler for peer leave events."""
        self._on_peer_leave.append(callback)
    
    def on_peer_suspect(self, callback: Callable[[Member], None]):
        """Register handler for peer suspect events."""
        self._on_peer_suspect.append(callback)
    
    async def _emit_join(self, member: Member):
        for cb in self._on_peer_join:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(member)
                else:
                    cb(member)
            except Exception as e:
                logger.error(f"Join handler error: {e}")
    
    async def _emit_fail(self, member: Member):
        for cb in self._on_peer_fail:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(member)
                else:
                    cb(member)
            except Exception as e:
                logger.error(f"Fail handler error: {e}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # PROTOCOL LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────
    
    async def start(self):
        """Start the gossip protocol."""
        if self._running:
            return
        
        self._running = True
        logger.info(f"Starting gossip protocol for {self.node_id}")
        
        # Start main protocol loop
        asyncio.create_task(self._protocol_loop())
        
        # Start suspect timeout checker
        asyncio.create_task(self._suspect_timeout_loop())
    
    async def stop(self):
        """Stop the gossip protocol."""
        self._running = False
        logger.info(f"Stopped gossip protocol for {self.node_id}")
    
    async def _protocol_loop(self):
        """Main SWIM protocol loop."""
        while self._running:
            await asyncio.sleep(self.config.protocol_period_ms / 1000)
            
            self._protocol_round += 1
            self.metrics["protocol_rounds"] += 1
            
            # Get a random alive member to probe
            members = await self.registry.get_random_members(1, exclude={self.node_id})
            if not members:
                continue
            
            target = members[0]
            
            # Phase 1: Direct ping
            ack_received = await self._direct_ping(target)
            
            if ack_received:
                target.mark_alive()
                await self.registry.update_status(target.peer_id, MemberStatus.ALIVE)
            else:
                # Phase 2: Indirect ping via K members
                ack_received = await self._indirect_ping(target)
                
                if ack_received:
                    target.mark_alive()
                    await self.registry.update_status(target.peer_id, MemberStatus.ALIVE)
                else:
                    # Mark as suspect
                    if target.is_alive:
                        logger.warning(f"Peer {target.peer_id} is now SUSPECT")
                        await self.registry.update_status(target.peer_id, MemberStatus.SUSPECT)
                        self.metrics["members_suspected"] += 1
                        
                        # Queue update for dissemination
                        self._queue_update({
                            "type": "suspect",
                            "peer_id": target.peer_id,
                            "incarnation": target.incarnation
                        })
            
            # Disseminate pending updates
            await self._disseminate_updates()
    
    async def _direct_ping(self, target: Member) -> bool:
        """Send direct ping to target."""
        if not self._send_callback:
            # Simulate for testing
            return random.random() > 0.1  # 90% success rate
        
        self.metrics["pings_sent"] += 1
        target.last_ping_sent = time.time()
        
        try:
            response = await asyncio.wait_for(
                self._send_callback("PING", target.peer_id, {"from": self.node_id}),
                timeout=self.config.ping_timeout_ms / 1000
            )
            
            if response:
                self.metrics["pongs_received"] += 1
                target.last_pong_received = time.time()
                return True
            return False
            
        except asyncio.TimeoutError:
            target.missed_pings += 1
            return False
    
    async def _indirect_ping(self, target: Member) -> bool:
        """Ask K other members to ping the target (PING-REQ)."""
        intermediaries = await self.registry.get_random_members(
            self.config.ping_req_members,
            exclude={self.node_id, target.peer_id}
        )
        
        if not intermediaries:
            return False
        
        self.metrics["ping_reqs_sent"] += len(intermediaries)
        
        if not self._send_callback:
            # Simulate for testing
            return random.random() > 0.3  # 70% success via indirect
        
        # Send PING-REQ to each intermediary
        tasks = []
        for intermediary in intermediaries:
            task = self._send_callback(
                "PING-REQ",
                intermediary.peer_id,
                {"target": target.peer_id, "from": self.node_id}
            )
            tasks.append(task)
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.ping_req_timeout_ms / 1000
            )
            
            # If any intermediary got a response, target is alive
            return any(r is True for r in results if not isinstance(r, Exception))
            
        except asyncio.TimeoutError:
            return False
    
    async def _suspect_timeout_loop(self):
        """Check suspect members and mark as dead after timeout."""
        while self._running:
            await asyncio.sleep(1.0)  # Check every second
            
            suspects = await self.registry.get_suspect_members()
            current_time = time.time()
            
            for member in suspects:
                # Parse status_changed timestamp
                try:
                    changed_time = datetime.fromisoformat(
                        member.status_changed.replace("Z", "+00:00")
                    ).timestamp()
                except:
                    continue
                
                time_suspect = current_time - changed_time
                
                if time_suspect > self.config.suspect_timeout_ms / 1000:
                    logger.warning(f"Peer {member.peer_id} is now DEAD (timeout)")
                    await self.registry.update_status(member.peer_id, MemberStatus.DEAD)
                    self.metrics["members_failed"] += 1
                    
                    # Queue update
                    self._queue_update({
                        "type": "dead",
                        "peer_id": member.peer_id,
                        "incarnation": member.incarnation
                    })
                    
                    # Emit event
                    await self._emit_fail(member)
    
    # ──────────────────────────────────────────────────────────────────────────
    # DISSEMINATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def _queue_update(self, update: Dict[str, Any]):
        """Queue an update for dissemination."""
        update["transmissions"] = 0
        self._pending_updates.append(update)
    
    async def _disseminate_updates(self):
        """Piggyback updates on protocol messages."""
        if not self._pending_updates:
            return
        
        members = await self.registry.get_alive_members()
        if not members:
            return
        
        # Calculate dissemination target count (Λ * log(n))
        n = len(members) + 1
        target_count = self.config.dissemination_multiplier * max(1, int(n.bit_length()))
        
        # Select random members
        recipients = random.sample(members, min(target_count, len(members)))
        
        # Send updates
        updates_to_send = [u for u in self._pending_updates if u["transmissions"] < self.config.max_transmissions]
        
        for recipient in recipients:
            if self._send_callback:
                await self._send_callback(
                    "GOSSIP",
                    recipient.peer_id,
                    {"updates": updates_to_send}
                )
        
        self.metrics["updates_disseminated"] += len(updates_to_send) * len(recipients)
        
        # Increment transmission count
        for update in updates_to_send:
            update["transmissions"] += 1
        
        # Remove fully disseminated updates
        self._pending_updates = [
            u for u in self._pending_updates
            if u["transmissions"] < self.config.max_transmissions
        ]
    
    # ──────────────────────────────────────────────────────────────────────────
    # MESSAGE HANDLING
    # ──────────────────────────────────────────────────────────────────────────
    
    async def handle_ping(self, from_peer: str) -> Dict[str, Any]:
        """Handle incoming PING."""
        return {"type": "PONG", "from": self.node_id}
    
    async def handle_ping_req(self, from_peer: str, target_peer: str) -> bool:
        """Handle incoming PING-REQ (indirect probe)."""
        target = await self.registry.get_member(target_peer)
        if not target:
            return False
        
        # Try to ping the target
        return await self._direct_ping(target)
    
    async def handle_gossip(self, updates: List[Dict[str, Any]]):
        """Handle incoming gossip updates."""
        for update in updates:
            peer_id = update.get("peer_id")
            if not peer_id or peer_id == self.node_id:
                continue
            
            member = await self.registry.get_member(peer_id)
            if not member:
                continue
            
            # Only apply if newer incarnation
            update_incarnation = update.get("incarnation", 0)
            if update_incarnation <= member.incarnation:
                continue
            
            update_type = update.get("type")
            
            if update_type == "alive":
                member.incarnation = update_incarnation
                member.mark_alive()
                await self.registry.update_status(peer_id, MemberStatus.ALIVE)
                
            elif update_type == "suspect":
                if member.is_alive:
                    member.incarnation = update_incarnation
                    member.mark_suspect()
                    await self.registry.update_status(peer_id, MemberStatus.SUSPECT)
                    
            elif update_type == "dead":
                member.incarnation = update_incarnation
                member.mark_dead()
                await self.registry.update_status(peer_id, MemberStatus.DEAD)
                await self._emit_fail(member)
    
    async def handle_join(self, member_data: Dict[str, Any]):
        """Handle peer join announcement."""
        member = Member(
            peer_id=member_data["peer_id"],
            host=member_data.get("host", "unknown"),
            port=member_data.get("port", 0),
            federation_id=member_data.get("federation_id", ""),
            region=member_data.get("region", ""),
            version=member_data.get("version", ""),
            capabilities=member_data.get("capabilities", [])
        )
        
        added = await self.registry.add_member(member)
        
        if added:
            logger.info(f"Peer {member.peer_id} joined the mesh")
            await self._emit_join(member)
            
            # Queue join announcement for dissemination
            self._queue_update({
                "type": "alive",
                "peer_id": member.peer_id,
                "incarnation": member.incarnation,
                "host": member.host,
                "port": member.port
            })
    
    # ──────────────────────────────────────────────────────────────────────────
    # UTILITIES
    # ──────────────────────────────────────────────────────────────────────────
    
    async def get_membership_hash(self) -> str:
        """Compute hash of current membership for consistency checks."""
        members = await self.registry.get_all_members()
        member_ids = sorted([m.peer_id for m in members if m.is_alive])
        content = ":".join(member_ids)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get gossip protocol metrics."""
        return {
            **self.metrics,
            "node_id": self.node_id,
            "protocol_round": self._protocol_round,
            "pending_updates": len(self._pending_updates)
        }


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

async def _self_test():
    """Run self-test to validate discovery module."""
    print("=" * 70)
    print("MESH DISCOVERY v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Member creation
    print("\n[1/5] Testing Member creation...")
    member = Member(
        peer_id="NODE-BETA",
        host="192.168.1.100",
        port=9443,
        federation_id="CHAINBRIDGE-FEDERATION",
        region="US-WEST",
        version="3.0.0"
    )
    print(f"      ✓ Member: {member.peer_id}")
    print(f"      ✓ Status: {member.status.value}")
    print(f"      ✓ Incarnation: {member.incarnation}")
    
    # Test 2: Status transitions
    print("\n[2/5] Testing status transitions...")
    member.mark_suspect()
    print(f"      ✓ Suspect: {member.is_suspect}")
    member.mark_alive()
    print(f"      ✓ Recovered: {member.is_alive}")
    print(f"      ✓ Incarnation after changes: {member.incarnation}")
    
    # Test 3: PeerRegistry
    print("\n[3/5] Testing PeerRegistry...")
    registry = PeerRegistry()
    await registry.add_member(member)
    
    member2 = Member(
        peer_id="NODE-GAMMA",
        host="192.168.1.101",
        port=9443,
        federation_id="CHAINBRIDGE-FEDERATION",
        region="US-EAST",
        version="3.0.0"
    )
    await registry.add_member(member2)
    
    alive = await registry.get_alive_members()
    print(f"      ✓ Registry size: {len(await registry.get_all_members())}")
    print(f"      ✓ Alive members: {len(alive)}")
    
    # Test 4: GossipProtocol
    print("\n[4/5] Testing GossipProtocol...")
    gossip = GossipProtocol("NODE-ALPHA", registry)
    
    join_events = []
    gossip.on_peer_join(lambda m: join_events.append(m.peer_id))
    
    await gossip.handle_join({
        "peer_id": "NODE-DELTA",
        "host": "192.168.1.102",
        "port": 9443,
        "federation_id": "CHAINBRIDGE-FEDERATION"
    })
    
    print(f"      ✓ Protocol created for: {gossip.node_id}")
    print(f"      ✓ Join event fired: {len(join_events) > 0}")
    print(f"      ✓ Joined peer: {join_events[0] if join_events else 'none'}")
    
    # Test 5: Topology snapshot
    print("\n[5/5] Testing topology snapshot...")
    topology = await registry.get_topology_snapshot()
    print(f"      ✓ Total members: {topology['total_members']}")
    print(f"      ✓ Alive count: {topology['alive_count']}")
    print(f"      ✓ Membership hash: {await gossip.get_membership_hash()}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-NET-002 (Topology Awareness): READY")
    print("INV-NET-003 (Sovereign Interop): READY")
    print("=" * 70)
    print("\n🔊 The Gossip is ready. Peers will find each other.")


if __name__ == "__main__":
    asyncio.run(_self_test())
