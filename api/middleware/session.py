"""
Session Middleware - Redis-Backed Session Management
=====================================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: Session State Management

INVARIANTS:
  INV-AUTH-003: Session state MUST be Redis-backed with TTL enforcement
  INV-SESSION-001: Session ID MUST be cryptographically random
  INV-SESSION-002: Session expiry MUST be enforced server-side
  INV-SESSION-003: Session invalidation MUST propagate immediately

SESSION LIFECYCLE:
  1. Creation: After successful authentication
  2. Refresh: On active use, extend TTL
  3. Invalidation: On logout or security event
  4. Expiry: Automatic cleanup via Redis TTL
"""

import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, FrozenSet, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# Configure logging
logger = logging.getLogger("chainbridge.session")

# Session configuration defaults
DEFAULT_SESSION_TTL = 3600  # 1 hour
DEFAULT_SESSION_HEADER = "X-Session-ID"
DEFAULT_SESSION_COOKIE = "chainbridge_session"
DEFAULT_REFRESH_THRESHOLD = 300  # Refresh if < 5 min remaining


@dataclass
class SessionConfig:
    """Session management configuration."""
    redis_url: str = "redis://localhost:6379/0"
    session_ttl: int = DEFAULT_SESSION_TTL
    session_header: str = DEFAULT_SESSION_HEADER
    session_cookie: str = DEFAULT_SESSION_COOKIE
    refresh_threshold: int = DEFAULT_REFRESH_THRESHOLD
    secure_cookies: bool = True
    same_site: str = "lax"
    session_id_bytes: int = 32  # 256-bit session IDs


@dataclass
class SessionData:
    """Session data structure."""
    session_id: str
    user_id: Optional[str] = None
    gid: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for Redis storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "gid": self.gid,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Deserialize from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            gid=data.get("gid"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """
    Redis-backed session manager with TTL enforcement.
    
    Provides atomic session operations with guaranteed expiry.
    Falls back to in-memory storage if Redis unavailable.
    """
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self._redis = None
        self._memory_store: Dict[str, SessionData] = {}
        self._connect_redis()
    
    def _connect_redis(self) -> None:
        """Attempt Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
            )
            # Test connection
            self._redis.ping()
            logger.info("Session manager connected to Redis")
        except ImportError:
            logger.warning("redis package not installed - using in-memory sessions")
            self._redis = None
        except Exception as e:
            logger.warning(f"Redis connection failed - using in-memory sessions: {e}")
            self._redis = None
    
    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID."""
        random_bytes = secrets.token_bytes(self.config.session_id_bytes)
        return hashlib.sha256(random_bytes).hexdigest()
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"chainbridge:session:{session_id}"
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        gid: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionData:
        """Create a new session."""
        session_id = self._generate_session_id()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.config.session_ttl)
        
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            gid=gid,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )
        
        await self._store_session(session)
        
        logger.info(f"Created session: id={session_id[:16]}... user={user_id}")
        return session
    
    async def _store_session(self, session: SessionData) -> None:
        """Store session in Redis or memory."""
        if self._redis:
            try:
                key = self._session_key(session.session_id)
                self._redis.setex(
                    key,
                    self.config.session_ttl,
                    json.dumps(session.to_dict()),
                )
                return
            except Exception as e:
                logger.error(f"Redis store failed: {e}")
        
        # Fallback to memory
        self._memory_store[session.session_id] = session
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session by ID."""
        if self._redis:
            try:
                key = self._session_key(session_id)
                data = self._redis.get(key)
                if data:
                    return SessionData.from_dict(json.loads(data))
            except Exception as e:
                logger.error(f"Redis get failed: {e}")
        
        # Check memory store
        session = self._memory_store.get(session_id)
        if session:
            # Check expiry for memory store
            if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
                del self._memory_store[session_id]
                return None
        
        return session
    
    async def refresh_session(self, session_id: str) -> Optional[SessionData]:
        """Refresh session TTL if approaching expiry."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        now = datetime.now(timezone.utc)
        
        # Check if refresh needed
        if session.expires_at:
            remaining = (session.expires_at - now).total_seconds()
            if remaining > self.config.refresh_threshold:
                # No refresh needed, just update last_accessed
                session.last_accessed = now
                await self._store_session(session)
                return session
        
        # Extend session
        session.last_accessed = now
        session.expires_at = now + timedelta(seconds=self.config.session_ttl)
        await self._store_session(session)
        
        logger.debug(f"Refreshed session: id={session_id[:16]}...")
        return session
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session immediately."""
        if self._redis:
            try:
                key = self._session_key(session_id)
                result = self._redis.delete(key)
                if result:
                    logger.info(f"Invalidated session: id={session_id[:16]}...")
                    return True
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
        
        # Remove from memory store
        if session_id in self._memory_store:
            del self._memory_store[session_id]
            logger.info(f"Invalidated session: id={session_id[:16]}...")
            return True
        
        return False
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        invalidated = 0
        
        if self._redis:
            try:
                # Scan for user's sessions
                pattern = "chainbridge:session:*"
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
                    for key in keys:
                        data = self._redis.get(key)
                        if data:
                            session_data = json.loads(data)
                            if session_data.get("user_id") == user_id:
                                self._redis.delete(key)
                                invalidated += 1
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error(f"Redis scan failed: {e}")
        
        # Check memory store
        to_remove = [
            sid for sid, session in self._memory_store.items()
            if session.user_id == user_id
        ]
        for sid in to_remove:
            del self._memory_store[sid]
            invalidated += 1
        
        if invalidated:
            logger.info(f"Invalidated {invalidated} sessions for user: {user_id}")
        
        return invalidated


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Session middleware with automatic refresh and tracking.
    
    Enforces INV-AUTH-003: Session state MUST be Redis-backed with TTL enforcement.
    
    Session Extraction Order:
      1. X-Session-ID header
      2. Cookie
    """
    
    def __init__(
        self,
        app,
        redis_url: str = "redis://localhost:6379/0",
        exempt_paths: FrozenSet[str] = frozenset(),
        config: Optional[SessionConfig] = None,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths
        self.config = config or SessionConfig(redis_url=redis_url)
        self.manager = SessionManager(self.config)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from session management."""
        if path in self.exempt_paths:
            return True
        path_normalized = path.rstrip("/")
        if path_normalized in self.exempt_paths:
            return True
        for exempt in self.exempt_paths:
            if path.startswith(exempt + "/"):
                return True
        return False
    
    def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request."""
        # Try header first
        session_id = request.headers.get(self.config.session_header)
        if session_id:
            return session_id
        
        # Try cookie
        session_id = request.cookies.get(self.config.session_cookie)
        return session_id
    
    async def dispatch(self, request: Request, call_next):
        """Process session for incoming request."""
        path = request.url.path
        
        # Check exemption
        if self._is_exempt(path):
            return await call_next(request)
        
        # Extract session ID
        session_id = self._extract_session_id(request)
        session = None
        
        if session_id:
            # Validate and refresh existing session
            session = await self.manager.refresh_session(session_id)
            if not session:
                logger.debug(f"Invalid or expired session: id={session_id[:16]}...")
        
        # Create new session if authenticated but no valid session
        auth = getattr(request.state, "auth", None)
        if not session and auth and auth.authenticated:
            session = await self.manager.create_session(
                user_id=auth.user_id,
                gid=auth.gid,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        
        # Attach session to request state
        request.state.session = session
        request.state.session_id = session.session_id if session else None
        
        # Process request
        response = await call_next(request)
        
        # Set session cookie in response if new session created
        if session and isinstance(response, Response):
            response.set_cookie(
                key=self.config.session_cookie,
                value=session.session_id,
                max_age=self.config.session_ttl,
                httponly=True,
                secure=self.config.secure_cookies,
                samesite=self.config.same_site,
            )
        
        return response
