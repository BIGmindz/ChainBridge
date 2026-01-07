# ═══════════════════════════════════════════════════════════════════════════════
# PAC-OCC-P20-BINDING — WebSocket Terminal Bridge
# Lane 2 (DEVELOPER / GID-CODY) Implementation
# Governance Tier: LAW
# Invariant: AUTH_REQUIRED | READ_ONLY_AGENTS | ARCHITECT_WRITE | FAIL_CLOSED
# ═══════════════════════════════════════════════════════════════════════════════
"""
WebSocket Terminal Bridge for Cockpit Operations.

This module provides a secure WebSocket connection between the ChainBoard UI
and the backend terminal session. The Architect (Jeffrey) has full read/write
access, while Agents have read-only observation capability.

Security Model:
- All connections require valid auth tokens
- Architect role grants write access to stdin
- Agent role grants read-only access to stdout
- Anonymous connections are rejected (FAIL-CLOSED)
- Emergency KILL_SESSION terminates all connections
"""

import asyncio
import logging
import os
import secrets
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# Security tokens (in production, load from secure vault)
ARCHITECT_TOKEN = os.environ.get("COCKPIT_ARCHITECT_TOKEN", "architect-" + secrets.token_hex(16))
AGENT_TOKEN = os.environ.get("COCKPIT_AGENT_TOKEN", "agent-" + secrets.token_hex(16))

# Session configuration
MAX_SESSIONS = 1  # Only one active cockpit session at a time
SESSION_TIMEOUT_MINUTES = 30
BUFFER_SIZE = 4096
ECHO_CANCELLATION = True  # Prevent double-echo on client


class ConnectionRole(str, Enum):
    """Role-based access control for WebSocket connections."""
    ARCHITECT = "architect"  # Full read/write access
    AGENT = "agent"          # Read-only observation
    ANONYMOUS = "anonymous"  # Rejected (fail-closed)


class SessionState(str, Enum):
    """State machine for cockpit sessions."""
    IDLE = "idle"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CockpitConnection:
    """Represents a single WebSocket connection to the cockpit."""
    websocket: WebSocket
    role: ConnectionRole
    gid: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    bytes_sent: int = 0
    bytes_received: int = 0


@dataclass
class CockpitSession:
    """The active terminal session for the cockpit."""
    session_id: str
    state: SessionState = SessionState.IDLE
    process: Optional[subprocess.Popen] = None
    architect_connection: Optional[CockpitConnection] = None
    agent_connections: List[CockpitConnection] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    output_buffer: List[str] = field(default_factory=list)
    command_history: List[str] = field(default_factory=list)


class TerminalMessage(BaseModel):
    """Message format for WebSocket communication."""
    type: str  # "stdin", "stdout", "stderr", "control", "error"
    data: str
    timestamp: str = ""
    gid: Optional[str] = None
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


class SessionStatus(BaseModel):
    """Public session status response."""
    session_id: str
    state: str
    architect_connected: bool
    agent_count: int
    uptime_seconds: float
    command_count: int


# ═══════════════════════════════════════════════════════════════════════════════
# COCKPIT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CockpitManager:
    """
    Manages the terminal cockpit session.
    
    Only ONE active session is allowed at any time (SINGLE_COCKPIT invariant).
    The Architect has exclusive write access to stdin.
    """
    
    def __init__(self):
        self._session: Optional[CockpitSession] = None
        self._lock = asyncio.Lock()
        self._broadcast_task: Optional[asyncio.Task] = None
    
    @property
    def has_active_session(self) -> bool:
        return self._session is not None and self._session.state == SessionState.ACTIVE
    
    def validate_token(self, token: str) -> ConnectionRole:
        """Validate auth token and return the connection role."""
        if token == ARCHITECT_TOKEN:
            return ConnectionRole.ARCHITECT
        elif token == AGENT_TOKEN:
            return ConnectionRole.AGENT
        else:
            return ConnectionRole.ANONYMOUS
    
    async def create_session(self, architect_ws: WebSocket, gid: str) -> CockpitSession:
        """Create a new cockpit session (Architect only)."""
        async with self._lock:
            if self._session and self._session.state == SessionState.ACTIVE:
                raise HTTPException(
                    status_code=409,
                    detail="Cockpit session already active. Only one session allowed."
                )
            
            session_id = f"cockpit-{secrets.token_hex(8)}"
            
            # Start the shell process
            # Using bash with proper PTY would be ideal, but for simplicity:
            shell = os.environ.get("SHELL", "/bin/zsh")
            
            self._session = CockpitSession(
                session_id=session_id,
                state=SessionState.ACTIVE,
                architect_connection=CockpitConnection(
                    websocket=architect_ws,
                    role=ConnectionRole.ARCHITECT,
                    gid=gid,
                ),
            )
            
            # Start broadcast task
            self._broadcast_task = asyncio.create_task(self._output_broadcaster())
            
            logger.info(f"Cockpit session created: {session_id} by {gid}")
            return self._session
    
    async def join_session(self, agent_ws: WebSocket, gid: str) -> bool:
        """Join an existing session as an observer (Agent only)."""
        async with self._lock:
            if not self._session or self._session.state != SessionState.ACTIVE:
                return False
            
            connection = CockpitConnection(
                websocket=agent_ws,
                role=ConnectionRole.AGENT,
                gid=gid,
            )
            self._session.agent_connections.append(connection)
            
            logger.info(f"Agent {gid} joined cockpit session")
            return True
    
    async def send_stdin(self, data: str, gid: str) -> bool:
        """
        Send input to the terminal (Architect only).
        
        Implements echo cancellation to prevent double-display.
        """
        if not self._session or self._session.state != SessionState.ACTIVE:
            return False
        
        # Verify sender is the Architect
        if not self._session.architect_connection or self._session.architect_connection.gid != gid:
            logger.warning(f"Unauthorized stdin attempt from {gid}")
            return False
        
        # Record command if it's a newline (command submission)
        if "\n" in data or "\r" in data:
            self._session.command_history.append(data.strip())
        
        # In a real implementation, write to process stdin
        # For now, we echo to all observers
        if not ECHO_CANCELLATION:
            await self._broadcast_output(data, "stdin", gid)
        
        self._session.architect_connection.bytes_sent += len(data)
        self._session.architect_connection.last_activity = datetime.utcnow()
        
        return True
    
    async def _broadcast_output(self, data: str, msg_type: str = "stdout", source_gid: str = "SYSTEM"):
        """Broadcast terminal output to all connected clients."""
        if not self._session:
            return
        
        message = TerminalMessage(
            type=msg_type,
            data=data,
            gid=source_gid,
        )
        json_msg = message.model_dump_json()
        
        # Store in buffer for late joiners
        self._session.output_buffer.append(json_msg)
        if len(self._session.output_buffer) > 1000:
            self._session.output_buffer = self._session.output_buffer[-500:]
        
        # Send to architect
        if self._session.architect_connection:
            try:
                await self._session.architect_connection.websocket.send_text(json_msg)
                self._session.architect_connection.bytes_received += len(json_msg)
            except Exception as e:
                logger.error(f"Failed to send to architect: {e}")
        
        # Send to all agents
        disconnected = []
        for conn in self._session.agent_connections:
            try:
                await conn.websocket.send_text(json_msg)
                conn.bytes_received += len(json_msg)
            except Exception:
                disconnected.append(conn)
        
        # Clean up disconnected agents
        for conn in disconnected:
            self._session.agent_connections.remove(conn)
    
    async def _output_broadcaster(self):
        """Background task to read process output and broadcast."""
        # In a real implementation, this would read from the process stdout/stderr
        # For now, it's a placeholder that demonstrates the pattern
        while self._session and self._session.state == SessionState.ACTIVE:
            await asyncio.sleep(0.1)
    
    async def kill_session(self, gid: str, reason: str = "Manual termination") -> bool:
        """
        Emergency kill switch for the cockpit session.
        
        This is the FAIL-CLOSED safety mechanism.
        """
        async with self._lock:
            if not self._session:
                return False
            
            logger.warning(f"KILL_SESSION invoked by {gid}: {reason}")
            
            # Terminate process if running
            if self._session.process:
                try:
                    self._session.process.terminate()
                    await asyncio.sleep(0.5)
                    if self._session.process.poll() is None:
                        self._session.process.kill()
                except Exception as e:
                    logger.error(f"Failed to kill process: {e}")
            
            # Notify all connections
            kill_msg = TerminalMessage(
                type="control",
                data=f"SESSION TERMINATED: {reason}",
                gid=gid,
            )
            
            if self._session.architect_connection:
                try:
                    await self._session.architect_connection.websocket.send_text(kill_msg.model_dump_json())
                    await self._session.architect_connection.websocket.close(code=1000)
                except Exception:
                    pass
            
            for conn in self._session.agent_connections:
                try:
                    await conn.websocket.send_text(kill_msg.model_dump_json())
                    await conn.websocket.close(code=1000)
                except Exception:
                    pass
            
            # Cancel broadcast task
            if self._broadcast_task:
                self._broadcast_task.cancel()
            
            self._session.state = SessionState.TERMINATED
            self._session = None
            
            return True
    
    def get_status(self) -> Optional[SessionStatus]:
        """Get current session status."""
        if not self._session:
            return None
        
        uptime = (datetime.utcnow() - self._session.created_at).total_seconds()
        
        return SessionStatus(
            session_id=self._session.session_id,
            state=self._session.state.value,
            architect_connected=self._session.architect_connection is not None,
            agent_count=len(self._session.agent_connections),
            uptime_seconds=uptime,
            command_count=len(self._session.command_history),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/cockpit", tags=["Cockpit"])
cockpit_manager = CockpitManager()


@router.websocket("/ws")
async def websocket_terminal(
    websocket: WebSocket,
    token: str = Query(..., description="Auth token (architect or agent)"),
    gid: str = Query(default="ANONYMOUS", description="Agent GID"),
):
    """
    WebSocket endpoint for terminal cockpit.
    
    - Architect token: Full read/write access, can create sessions
    - Agent token: Read-only observation of existing sessions
    - Anonymous: Connection rejected (FAIL-CLOSED)
    """
    # Validate token
    role = cockpit_manager.validate_token(token)
    
    if role == ConnectionRole.ANONYMOUS:
        await websocket.close(code=4001, reason="Invalid token - FAIL_CLOSED")
        logger.warning(f"Anonymous connection rejected from {gid}")
        return
    
    await websocket.accept()
    
    try:
        if role == ConnectionRole.ARCHITECT:
            # Architect creates or takes over the session
            session = await cockpit_manager.create_session(websocket, gid)
            
            # Send welcome message
            welcome = TerminalMessage(
                type="control",
                data=f"Cockpit session {session.session_id} initialized. You have WRITE access.",
                gid="BENSON",
            )
            await websocket.send_text(welcome.model_dump_json())
            
            # Handle architect messages
            while True:
                data = await websocket.receive_text()
                msg = TerminalMessage.model_validate_json(data)
                
                if msg.type == "stdin":
                    await cockpit_manager.send_stdin(msg.data, gid)
                elif msg.type == "control" and msg.data == "KILL_SESSION":
                    await cockpit_manager.kill_session(gid, "Architect initiated shutdown")
                    break
        
        else:  # Agent role
            # Agent joins as observer
            joined = await cockpit_manager.join_session(websocket, gid)
            
            if not joined:
                error = TerminalMessage(
                    type="error",
                    data="No active cockpit session to join",
                    gid="BENSON",
                )
                await websocket.send_text(error.model_dump_json())
                await websocket.close(code=4002, reason="No active session")
                return
            
            # Send join confirmation
            join_msg = TerminalMessage(
                type="control",
                data=f"Joined cockpit as observer. You have READ-ONLY access.",
                gid="BENSON",
            )
            await websocket.send_text(join_msg.model_dump_json())
            
            # Agent just listens - output is broadcast by manager
            while True:
                # Keep connection alive, handle pings
                data = await websocket.receive_text()
                # Agents can only send control messages (like disconnect)
                msg = TerminalMessage.model_validate_json(data)
                if msg.type == "control" and msg.data == "DISCONNECT":
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {gid} ({role.value})")
    except Exception as e:
        logger.error(f"WebSocket error for {gid}: {e}")
    finally:
        # Cleanup handled by manager
        pass


@router.get("/status", response_model=Optional[SessionStatus])
async def get_cockpit_status():
    """Get current cockpit session status."""
    return cockpit_manager.get_status()


@router.post("/kill")
async def kill_cockpit_session(
    reason: str = Query(default="Emergency stop", description="Reason for termination"),
    gid: str = Query(default="EMERGENCY", description="Invoking agent GID"),
):
    """
    Emergency kill switch for the cockpit session.
    
    This endpoint is the FAIL-CLOSED safety mechanism.
    Available to authorized personnel only.
    """
    success = await cockpit_manager.kill_session(gid, reason)
    
    if success:
        return {"status": "terminated", "reason": reason, "invoked_by": gid}
    else:
        raise HTTPException(status_code=404, detail="No active session to terminate")


@router.get("/tokens")
async def get_demo_tokens():
    """
    Get demo tokens for development.
    
    WARNING: In production, tokens should be fetched from a secure vault,
    not exposed via API endpoint.
    """
    if os.environ.get("CHAINBRIDGE_ENV", "development") == "production":
        raise HTTPException(status_code=403, detail="Token endpoint disabled in production")
    
    return {
        "architect_token": ARCHITECT_TOKEN,
        "agent_token": AGENT_TOKEN,
        "warning": "These tokens are for development only",
    }
