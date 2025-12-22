"""Lane Guard Middleware — Service Boundary Protection.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🔵 BLUE                                             ║
║ PAC: PAC-CODY-A6-BACKEND-GUARDRAILS-01                               ║
╚══════════════════════════════════════════════════════════════════════╝

DOCTRINE (FAIL-CLOSED):
Service boundaries MUST be enforced at the middleware layer:
1. Runtime → Agent methods: BLOCKED
2. Agent → Agent-only methods: ALLOWED
3. Public → Protected methods: BLOCKED
4. Settlement → Unvalidated PDOs: BLOCKED

INVARIANTS (NON-NEGOTIABLE):
- Lane violations fail immediately
- No soft bypasses
- All violations logged for audit
- Defense in depth (multiple gates)

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Set, TypeVar, cast

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Agent GID pattern
AGENT_GID_PATTERN = re.compile(r"^GID-\d{2}$")

# Known runtime identifiers
RUNTIME_IDENTIFIERS = frozenset({
    "runtime",
    "copilot",
    "chatgpt",
    "assistant",
    "system",
    "executor",
})


class LaneViolationType(str, Enum):
    """Types of lane/boundary violations."""
    
    RUNTIME_CALLS_AGENT_METHOD = "RUNTIME_CALLS_AGENT_METHOD"
    PUBLIC_CALLS_PROTECTED = "PUBLIC_CALLS_PROTECTED"
    UNAUTHENTICATED_ACCESS = "UNAUTHENTICATED_ACCESS"
    INVALID_CALLER_IDENTITY = "INVALID_CALLER_IDENTITY"
    SETTLEMENT_WITHOUT_PDO = "SETTLEMENT_WITHOUT_PDO"
    CROSS_BOUNDARY_VIOLATION = "CROSS_BOUNDARY_VIOLATION"
    MISSING_AUTHORIZATION = "MISSING_AUTHORIZATION"


class ServiceLane(str, Enum):
    """Service lane classifications.
    
    Each lane has specific access rules.
    """
    PUBLIC = "PUBLIC"           # Anyone can access
    AUTHENTICATED = "AUTHENTICATED"  # Requires valid identity
    AGENT_ONLY = "AGENT_ONLY"       # Only agents (GID-XX) can access
    AUTHORITY_ONLY = "AUTHORITY_ONLY"  # Only authority agents
    SETTLEMENT = "SETTLEMENT"       # Settlement services (special rules)


@dataclass(frozen=True)
class LaneGuardResult:
    """Immutable result from lane guard check.
    
    Attributes:
        allowed: True if access is allowed
        violation: Violation type if denied
        lane: The lane being accessed
        caller: Identity of the caller
        details: Human-readable explanation
        checked_at: ISO timestamp
    """
    allowed: bool
    violation: Optional[LaneViolationType]
    lane: ServiceLane
    caller: Optional[str]
    details: str
    checked_at: str
    
    def __bool__(self) -> bool:
        """Allow if result: ... checking."""
        return self.allowed


class LaneGuard:
    """Middleware guard for service lane enforcement.
    
    DOCTRINE (FAIL-CLOSED):
    All lane violations → immediate block.
    No exceptions, no soft bypasses.
    
    Usage:
        guard = LaneGuard()
        result = guard.check_access(ServiceLane.AGENT_ONLY, caller_identity)
        if not result:
            raise LaneViolationError(result.violation)
    """
    
    def __init__(self):
        """Initialize lane guard."""
        # Track lane access stats
        self._access_counts: Dict[ServiceLane, int] = {}
        self._violation_counts: Dict[LaneViolationType, int] = {}
    
    def check_access(
        self,
        lane: ServiceLane,
        caller_identity: Optional[str],
        *,
        pdo_validated: bool = True,
        auth_header: Optional[str] = None,
    ) -> LaneGuardResult:
        """Check if caller can access the specified lane.
        
        DOCTRINE (FAIL-CLOSED):
        - Unknown caller + protected lane → BLOCK
        - Runtime + agent lane → BLOCK
        - Settlement + no PDO → BLOCK
        
        Args:
            lane: The service lane being accessed
            caller_identity: Identity of the caller
            pdo_validated: Whether PDO has been validated (for settlement lane)
            auth_header: Optional authorization header
        
        Returns:
            LaneGuardResult indicating allowed/denied
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Track access
        self._access_counts[lane] = self._access_counts.get(lane, 0) + 1
        
        # PUBLIC lane - always allowed
        if lane == ServiceLane.PUBLIC:
            return LaneGuardResult(
                allowed=True,
                violation=None,
                lane=lane,
                caller=caller_identity,
                details="Public lane access allowed",
                checked_at=timestamp,
            )
        
        # AUTHENTICATED lane - requires some identity
        if lane == ServiceLane.AUTHENTICATED:
            if caller_identity is None and auth_header is None:
                return self._deny(
                    LaneViolationType.UNAUTHENTICATED_ACCESS,
                    lane,
                    caller_identity,
                    "Authenticated lane requires valid identity or auth header",
                    timestamp,
                )
            return LaneGuardResult(
                allowed=True,
                violation=None,
                lane=lane,
                caller=caller_identity,
                details="Authenticated access allowed",
                checked_at=timestamp,
            )
        
        # AGENT_ONLY lane - requires valid agent GID
        if lane == ServiceLane.AGENT_ONLY:
            agent_result = self._check_agent_access(caller_identity)
            if not agent_result["allowed"]:
                return self._deny(
                    agent_result["violation_type"],
                    lane,
                    caller_identity,
                    agent_result["message"],
                    timestamp,
                )
            return LaneGuardResult(
                allowed=True,
                violation=None,
                lane=lane,
                caller=caller_identity,
                details="Agent-only access allowed",
                checked_at=timestamp,
            )
        
        # AUTHORITY_ONLY lane - requires authority agent
        if lane == ServiceLane.AUTHORITY_ONLY:
            authority_result = self._check_authority_access(caller_identity)
            if not authority_result["allowed"]:
                return self._deny(
                    authority_result["violation_type"],
                    lane,
                    caller_identity,
                    authority_result["message"],
                    timestamp,
                )
            return LaneGuardResult(
                allowed=True,
                violation=None,
                lane=lane,
                caller=caller_identity,
                details="Authority-only access allowed",
                checked_at=timestamp,
            )
        
        # SETTLEMENT lane - special rules
        if lane == ServiceLane.SETTLEMENT:
            # Must have validated PDO
            if not pdo_validated:
                return self._deny(
                    LaneViolationType.SETTLEMENT_WITHOUT_PDO,
                    lane,
                    caller_identity,
                    "Settlement lane requires validated PDO",
                    timestamp,
                )
            # Must be agent or authorized service
            settlement_result = self._check_settlement_access(caller_identity)
            if not settlement_result["allowed"]:
                return self._deny(
                    settlement_result["violation_type"],
                    lane,
                    caller_identity,
                    settlement_result["message"],
                    timestamp,
                )
            return LaneGuardResult(
                allowed=True,
                violation=None,
                lane=lane,
                caller=caller_identity,
                details="Settlement access allowed",
                checked_at=timestamp,
            )
        
        # Unknown lane - deny for safety
        return self._deny(
            LaneViolationType.CROSS_BOUNDARY_VIOLATION,
            lane,
            caller_identity,
            f"Unknown lane type: {lane}",
            timestamp,
        )
    
    def _check_agent_access(self, caller: Optional[str]) -> Dict[str, Any]:
        """Check if caller has agent access."""
        if caller is None:
            return {
                "allowed": False,
                "violation_type": LaneViolationType.INVALID_CALLER_IDENTITY,
                "message": "Agent-only lane requires valid caller identity",
            }
        
        # Check if caller is a runtime (blocked)
        caller_lower = caller.lower()
        for runtime in RUNTIME_IDENTIFIERS:
            if runtime in caller_lower:
                return {
                    "allowed": False,
                    "violation_type": LaneViolationType.RUNTIME_CALLS_AGENT_METHOD,
                    "message": f"Runtime '{caller}' cannot access agent-only methods",
                }
        
        # Check for valid GID pattern
        if AGENT_GID_PATTERN.match(caller):
            return {"allowed": True, "violation_type": None, "message": None}
        
        # Check if caller contains valid GID
        if re.search(r"GID-\d{2}", caller):
            return {"allowed": True, "violation_type": None, "message": None}
        
        # Unknown format - deny for safety
        return {
            "allowed": False,
            "violation_type": LaneViolationType.INVALID_CALLER_IDENTITY,
            "message": f"Caller '{caller}' does not have valid agent identity",
        }
    
    def _check_authority_access(self, caller: Optional[str]) -> Dict[str, Any]:
        """Check if caller has authority access.
        
        For now, this is the same as agent access.
        Future: Add specific authority patterns.
        """
        return self._check_agent_access(caller)
    
    def _check_settlement_access(self, caller: Optional[str]) -> Dict[str, Any]:
        """Check if caller can access settlement lane."""
        # Settlement can be accessed by:
        # 1. Valid agents
        # 2. Internal services (settlement-service, gateway)
        
        if caller is None:
            return {
                "allowed": False,
                "violation_type": LaneViolationType.MISSING_AUTHORIZATION,
                "message": "Settlement lane requires caller identity",
            }
        
        # Block runtimes explicitly
        caller_lower = caller.lower()
        for runtime in RUNTIME_IDENTIFIERS:
            if runtime in caller_lower:
                return {
                    "allowed": False,
                    "violation_type": LaneViolationType.RUNTIME_CALLS_AGENT_METHOD,
                    "message": f"Runtime '{caller}' cannot access settlement services",
                }
        
        # Allow valid agents
        if AGENT_GID_PATTERN.match(caller) or re.search(r"GID-\d{2}", caller):
            return {"allowed": True, "violation_type": None, "message": None}
        
        # Allow internal services
        internal_services = {"settlement-service", "gateway", "internal", "service"}
        for service in internal_services:
            if service in caller_lower:
                return {"allowed": True, "violation_type": None, "message": None}
        
        return {
            "allowed": False,
            "violation_type": LaneViolationType.INVALID_CALLER_IDENTITY,
            "message": f"Caller '{caller}' not authorized for settlement lane",
        }
    
    def _deny(
        self,
        violation: LaneViolationType,
        lane: ServiceLane,
        caller: Optional[str],
        details: str,
        timestamp: str,
    ) -> LaneGuardResult:
        """Create denial result and log violation."""
        # Track violation
        self._violation_counts[violation] = self._violation_counts.get(violation, 0) + 1
        
        # Log for audit
        logger.warning(
            "Lane guard DENIED: violation=%s lane=%s caller=%s details=%s",
            violation.value,
            lane.value,
            caller,
            details,
        )
        
        return LaneGuardResult(
            allowed=False,
            violation=violation,
            lane=lane,
            caller=caller,
            details=details,
            checked_at=timestamp,
        )


# ---------------------------------------------------------------------------
# Decorator for Lane Protection
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def require_lane(lane: ServiceLane) -> Callable[[F], F]:
    """Decorator to require lane access for a function.
    
    DOCTRINE (FAIL-CLOSED):
    Function will not execute unless lane check passes.
    
    Usage:
        @require_lane(ServiceLane.AGENT_ONLY)
        def agent_method(caller_gid: str, ...):
            ...
    
    Args:
        lane: Required service lane
    
    Returns:
        Decorated function that checks lane before execution
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try to extract caller identity from kwargs
            caller = kwargs.get("caller_identity") or kwargs.get("caller_gid") or kwargs.get("agent_gid")
            
            # Try first positional arg if it looks like a GID
            if caller is None and args:
                first_arg = str(args[0]) if args[0] else ""
                if AGENT_GID_PATTERN.match(first_arg):
                    caller = first_arg
            
            # Check lane access
            guard = _get_lane_guard()
            pdo_validated = kwargs.get("pdo_validated", True)
            auth_header = kwargs.get("auth_header")
            
            result = guard.check_access(
                lane,
                caller,
                pdo_validated=pdo_validated,
                auth_header=auth_header,
            )
            
            if not result:
                raise LaneViolationError(
                    f"Lane access denied: {result.violation.value if result.violation else 'unknown'} - {result.details}"
                )
            
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    return decorator


class LaneViolationError(Exception):
    """Exception raised for lane access violations."""
    
    def __init__(self, message: str, violation: Optional[LaneViolationType] = None):
        super().__init__(message)
        self.violation = violation


# ---------------------------------------------------------------------------
# FastAPI Middleware
# ---------------------------------------------------------------------------

# Singleton guard instance
_lane_guard: Optional[LaneGuard] = None


def _get_lane_guard() -> LaneGuard:
    """Get or create singleton lane guard."""
    global _lane_guard
    if _lane_guard is None:
        _lane_guard = LaneGuard()
    return _lane_guard


async def lane_guard_middleware(request: Any, call_next: Any) -> Any:
    """FastAPI middleware for lane enforcement.
    
    This middleware extracts caller identity from headers
    and enforces lane access based on route patterns.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
    
    Returns:
        Response from handler or 403 on lane violation
    """
    from fastapi import Response
    from fastapi.responses import JSONResponse
    
    # Extract caller identity from headers
    caller_identity = request.headers.get("X-Caller-Identity")
    auth_header = request.headers.get("Authorization")
    
    # Determine lane from path
    path = request.url.path
    lane = _determine_lane_from_path(path)
    
    # PUBLIC paths skip check
    if lane == ServiceLane.PUBLIC:
        return await call_next(request)
    
    # Check lane access
    guard = _get_lane_guard()
    
    # For settlement paths, check PDO validation header
    pdo_validated = request.headers.get("X-PDO-Validated", "").lower() == "true"
    
    result = guard.check_access(
        lane,
        caller_identity,
        pdo_validated=pdo_validated,
        auth_header=auth_header,
    )
    
    if not result:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Lane access denied",
                "violation": result.violation.value if result.violation else "UNKNOWN",
                "details": result.details,
            },
        )
    
    return await call_next(request)


def _determine_lane_from_path(path: str) -> ServiceLane:
    """Determine which lane a path belongs to.
    
    DOCTRINE:
    - /api/v1/public/* → PUBLIC
    - /api/v1/settlement/* → SETTLEMENT
    - /api/v1/agent/* → AGENT_ONLY
    - /api/v1/* (other) → AUTHENTICATED
    - /health, /metrics → PUBLIC
    """
    path_lower = path.lower()
    
    # Public paths
    if any(p in path_lower for p in ["/health", "/metrics", "/public/", "/docs", "/openapi"]):
        return ServiceLane.PUBLIC
    
    # Settlement paths
    if "/settlement" in path_lower:
        return ServiceLane.SETTLEMENT
    
    # Agent-only paths
    if any(p in path_lower for p in ["/agent/", "/pdo/", "/decision/"]):
        return ServiceLane.AGENT_ONLY
    
    # Authority-only paths
    if "/authority/" in path_lower:
        return ServiceLane.AUTHORITY_ONLY
    
    # Default to authenticated
    if path.startswith("/api/"):
        return ServiceLane.AUTHENTICATED
    
    return ServiceLane.PUBLIC


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------

def get_lane_guard() -> LaneGuard:
    """FastAPI dependency to get lane guard instance."""
    return _get_lane_guard()


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
