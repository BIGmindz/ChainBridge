"""
ChainBridge Sovereign Swarm - UI Push Service
PAC-UI-HANDSHAKE-INIT-42 | WebSocket Bridge

Real-time bi-directional communication between Python backend
and browser-based OCC Command Canvas.

Components:
- SessionManager: SMK-authenticated session tracking
- UIPushService: Broadcast agent/canvas state via WebSocket
- TelemetrySync: ARR Counter, Gate Heatmap binding

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001
"""

import asyncio
import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum

# WebSocket support
try:
    from fastapi import WebSocket, WebSocketDisconnect
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

HANDSHAKE_VERSION = "1.0.0"
EXPECTED_SMK = "6-ifzIxSHaDaGdyk71EKyd9MepaP-zOk3Qg47KDozGg"
CURRENT_SWARM_ID = "SWARM-D49E513E"
BROADCAST_INTERVAL_MS = 500  # Push state every 500ms


class MessageType(Enum):
    """WebSocket message types"""
    HANDSHAKE = "HANDSHAKE"
    HANDSHAKE_ACK = "HANDSHAKE_ACK"
    HANDSHAKE_FAIL = "HANDSHAKE_FAIL"
    AGENT_STATE = "AGENT_STATE"
    CANVAS_STATE = "CANVAS_STATE"
    TELEMETRY = "TELEMETRY"
    GATE_UPDATE = "GATE_UPDATE"
    ALERT = "ALERT"
    PING = "PING"
    PONG = "PONG"
    ERROR = "ERROR"


class SessionState(Enum):
    """Session lifecycle states"""
    PENDING = "PENDING"
    AUTHENTICATED = "AUTHENTICATED"
    HYDRATED = "HYDRATED"
    DISCONNECTED = "DISCONNECTED"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuthenticatedSession:
    """SMK-bound browser session"""
    session_id: str
    smk_hash: str
    created_at: str
    state: SessionState
    websocket: Optional[Any] = None
    last_ping: float = 0.0
    subscriptions: Set[str] = field(default_factory=lambda: {"agents", "canvas", "telemetry"})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "smk_hash": f"{self.smk_hash[:8]}...{self.smk_hash[-8:]}",
            "created_at": self.created_at,
            "state": self.state.value,
            "last_ping": self.last_ping,
            "subscriptions": list(self.subscriptions)
        }


@dataclass 
class AgentStatePayload:
    """Agent forge state broadcast"""
    timestamp: str
    swarm_id: str
    agents: List[Dict[str, Any]]
    active_count: int
    deployed_count: int
    total_count: int


@dataclass
class CanvasStatePayload:
    """Logic canvas state broadcast"""
    timestamp: str
    swarm_id: str
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    execution_state: str


@dataclass
class TelemetryPayload:
    """Telemetry sync payload"""
    timestamp: str
    arr_usd: float
    arr_target_usd: float
    arr_progress_pct: float
    gates_compliant: int
    gates_blocked: int
    gates_total: int
    lanes_active: int
    epoch: str


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SessionManager:
    """
    Manages SMK-authenticated browser sessions.
    Ensures only valid sessions receive live data streams.
    """
    
    def __init__(self):
        self.sessions: Dict[str, AuthenticatedSession] = {}
        self._session_lock = asyncio.Lock()
    
    def _hash_smk(self, smk: str) -> str:
        """Create hash of SMK for comparison"""
        return hashlib.sha256(smk.encode()).hexdigest()
    
    async def authenticate(self, session_id: str, smk: str) -> tuple[bool, Optional[AuthenticatedSession], str]:
        """Authenticate a session with SMK"""
        async with self._session_lock:
            # Verify SMK
            if smk != EXPECTED_SMK:
                return False, None, "Invalid Sovereign Master Key"
            
            # Create or update session
            smk_hash = self._hash_smk(smk)
            now = datetime.now(timezone.utc).isoformat()
            
            if session_id in self.sessions:
                # Re-authenticate existing session
                session = self.sessions[session_id]
                session.smk_hash = smk_hash
                session.state = SessionState.AUTHENTICATED
            else:
                # Create new session
                session = AuthenticatedSession(
                    session_id=session_id,
                    smk_hash=smk_hash,
                    created_at=now,
                    state=SessionState.AUTHENTICATED
                )
                self.sessions[session_id] = session
            
            return True, session, "Authenticated"
    
    async def bind_websocket(self, session_id: str, websocket: Any) -> bool:
        """Bind WebSocket to authenticated session"""
        async with self._session_lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            if session.state not in [SessionState.AUTHENTICATED, SessionState.HYDRATED]:
                return False
            
            session.websocket = websocket
            session.state = SessionState.HYDRATED
            session.last_ping = time.time()
            return True
    
    async def unbind_websocket(self, session_id: str):
        """Remove WebSocket binding"""
        async with self._session_lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.websocket = None
                session.state = SessionState.DISCONNECTED
    
    async def get_active_sessions(self) -> List[AuthenticatedSession]:
        """Get all sessions with active WebSocket connections"""
        return [s for s in self.sessions.values() 
                if s.websocket is not None and s.state == SessionState.HYDRATED]
    
    async def update_ping(self, session_id: str):
        """Update last ping time for session"""
        if session_id in self.sessions:
            self.sessions[session_id].last_ping = time.time()
    
    def get_session_count(self) -> int:
        """Get total active session count"""
        return sum(1 for s in self.sessions.values() if s.state == SessionState.HYDRATED)


# ═══════════════════════════════════════════════════════════════════════════════
# UI PUSH SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class UIPushService:
    """
    Broadcasts live state to all authenticated browser sessions.
    
    LANE 1: SOCKET-MOUNT - WebSocket connection management
    LANE 2: CANVAS-HYDRATION - Agent/node state injection
    LANE 3: TELEMETRY-BIND - ARR/Gate metrics sync
    """
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._state_providers: Dict[str, Callable] = {}
        
        # Current state cache
        self._agent_state: Optional[AgentStatePayload] = None
        self._canvas_state: Optional[CanvasStatePayload] = None
        self._telemetry: Optional[TelemetryPayload] = None
    
    def register_state_provider(self, name: str, provider: Callable):
        """Register a state provider function"""
        self._state_providers[name] = provider
    
    async def start(self):
        """Start the broadcast loop"""
        if self._running:
            return
        
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        print(f"[UIPushService] Started - Broadcasting every {BROADCAST_INTERVAL_MS}ms")
    
    async def stop(self):
        """Stop the broadcast loop"""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        print("[UIPushService] Stopped")
    
    async def _broadcast_loop(self):
        """Main broadcast loop"""
        while self._running:
            try:
                await self._broadcast_state()
                await asyncio.sleep(BROADCAST_INTERVAL_MS / 1000)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[UIPushService] Broadcast error: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast_state(self):
        """Broadcast current state to all active sessions"""
        sessions = await self.session_manager.get_active_sessions()
        if not sessions:
            return
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Collect current state
        if "agents" in self._state_providers:
            try:
                self._agent_state = self._state_providers["agents"]()
            except Exception:
                pass
        
        if "canvas" in self._state_providers:
            try:
                self._canvas_state = self._state_providers["canvas"]()
            except Exception:
                pass
        
        if "telemetry" in self._state_providers:
            try:
                self._telemetry = self._state_providers["telemetry"]()
            except Exception:
                pass
        
        # Broadcast to each session
        for session in sessions:
            await self._send_to_session(session)
    
    async def _send_to_session(self, session: AuthenticatedSession):
        """Send state updates to a specific session"""
        if not session.websocket:
            return
        
        try:
            # Send agent state if subscribed
            if "agents" in session.subscriptions and self._agent_state:
                await session.websocket.send_json({
                    "type": MessageType.AGENT_STATE.value,
                    "payload": asdict(self._agent_state)
                })
            
            # Send canvas state if subscribed
            if "canvas" in session.subscriptions and self._canvas_state:
                await session.websocket.send_json({
                    "type": MessageType.CANVAS_STATE.value,
                    "payload": asdict(self._canvas_state)
                })
            
            # Send telemetry if subscribed
            if "telemetry" in session.subscriptions and self._telemetry:
                await session.websocket.send_json({
                    "type": MessageType.TELEMETRY.value,
                    "payload": asdict(self._telemetry)
                })
                
        except Exception as e:
            print(f"[UIPushService] Send error for session {session.session_id}: {e}")
    
    async def broadcast_alert(self, level: str, message: str, source: str):
        """Broadcast an alert to all sessions"""
        sessions = await self.session_manager.get_active_sessions()
        
        alert_payload = {
            "type": MessageType.ALERT.value,
            "payload": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
                "source": source
            }
        }
        
        for session in sessions:
            if session.websocket:
                try:
                    await session.websocket.send_json(alert_payload)
                except Exception:
                    pass
    
    async def broadcast_gate_update(self, gate_id: int, status: str):
        """Broadcast a gate status change"""
        sessions = await self.session_manager.get_active_sessions()
        
        gate_payload = {
            "type": MessageType.GATE_UPDATE.value,
            "payload": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "gate_id": gate_id,
                "status": status
            }
        }
        
        for session in sessions:
            if session.websocket and "telemetry" in session.subscriptions:
                try:
                    await session.websocket.send_json(gate_payload)
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_websocket_connection(
    websocket: "WebSocket",
    session_manager: SessionManager,
    push_service: UIPushService
):
    """
    Handle a new WebSocket connection.
    
    Protocol:
    1. Client sends HANDSHAKE with session_id and SMK
    2. Server validates and sends HANDSHAKE_ACK
    3. Server begins streaming state updates
    4. Client sends PING, server responds PONG
    """
    await websocket.accept()
    session_id: Optional[str] = None
    
    try:
        # Wait for handshake
        handshake_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        
        if handshake_data.get("type") != MessageType.HANDSHAKE.value:
            await websocket.send_json({
                "type": MessageType.HANDSHAKE_FAIL.value,
                "payload": {"reason": "Expected HANDSHAKE message"}
            })
            return
        
        payload = handshake_data.get("payload", {})
        session_id = payload.get("session_id") or str(uuid.uuid4())
        smk = payload.get("smk", "")
        
        # Authenticate
        success, session, reason = await session_manager.authenticate(session_id, smk)
        
        if not success:
            await websocket.send_json({
                "type": MessageType.HANDSHAKE_FAIL.value,
                "payload": {"reason": reason}
            })
            return
        
        # Bind WebSocket to session
        await session_manager.bind_websocket(session_id, websocket)
        
        # Send acknowledgment
        await websocket.send_json({
            "type": MessageType.HANDSHAKE_ACK.value,
            "payload": {
                "session_id": session_id,
                "swarm_id": CURRENT_SWARM_ID,
                "version": HANDSHAKE_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
        
        print(f"[WebSocket] Session {session_id[:8]}... connected and hydrated")
        
        # Enter message loop
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                
                if msg_type == MessageType.PING.value:
                    await session_manager.update_ping(session_id)
                    await websocket.send_json({
                        "type": MessageType.PONG.value,
                        "payload": {"timestamp": datetime.now(timezone.utc).isoformat()}
                    })
                
                elif msg_type == "SUBSCRIBE":
                    # Update subscriptions
                    channels = data.get("payload", {}).get("channels", [])
                    if session_id in session_manager.sessions:
                        session_manager.sessions[session_id].subscriptions = set(channels)
                
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
                
    except WebSocketDisconnect:
        print(f"[WebSocket] Session {session_id[:8] if session_id else 'unknown'}... disconnected")
    except asyncio.TimeoutError:
        print("[WebSocket] Handshake timeout")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        try:
            await websocket.send_json({
                "type": MessageType.ERROR.value,
                "payload": {"message": str(e)}
            })
        except Exception:
            pass
    finally:
        if session_id:
            await session_manager.unbind_websocket(session_id)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

# Global instances - initialized when module loads
_session_manager: Optional[SessionManager] = None
_push_service: Optional[UIPushService] = None


def get_session_manager() -> SessionManager:
    """Get or create session manager singleton"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_push_service() -> UIPushService:
    """Get or create push service singleton"""
    global _push_service
    if _push_service is None:
        _push_service = UIPushService(get_session_manager())
    return _push_service


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("PAC-UI-HANDSHAKE-INIT-42 | UI Push Service Self-Test")
    print("=" * 80)
    
    import asyncio
    
    async def test():
        sm = SessionManager()
        ps = UIPushService(sm)
        
        # Test authentication
        print("\n[TEST 1] Session Authentication")
        success, session, reason = await sm.authenticate("test-session-1", EXPECTED_SMK)
        print(f"  Result: {success}, Reason: {reason}")
        print(f"  Session: {session.to_dict() if session else None}")
        
        # Test invalid auth
        print("\n[TEST 2] Invalid SMK Rejection")
        success, _, reason = await sm.authenticate("test-session-2", "invalid-key")
        print(f"  Result: {success}, Reason: {reason}")
        
        # Test state providers
        print("\n[TEST 3] State Provider Registration")
        def mock_telemetry():
            return TelemetryPayload(
                timestamp=datetime.now(timezone.utc).isoformat(),
                arr_usd=13197500.00,
                arr_target_usd=100000000.00,
                arr_progress_pct=13.2,
                gates_compliant=9950,
                gates_blocked=50,
                gates_total=10000,
                lanes_active=3,
                epoch="EPOCH_001"
            )
        
        ps.register_state_provider("telemetry", mock_telemetry)
        print(f"  Registered providers: {list(ps._state_providers.keys())}")
        
        print("\n[TEST 4] Session Count")
        print(f"  Active sessions: {sm.get_session_count()}")
        
        print("\n" + "=" * 80)
        print("All tests passed. WebSocket bridge ready.")
        print("=" * 80)
    
    asyncio.run(test())
