# ═══════════════════════════════════════════════════════════════════════════════
# API Read-Only Enforcement Middleware
# PAC-BENSON-P23-C: Parallel Platform Hardening (Corrective)
#
# Middleware to enforce read-only constraints on OCC endpoints.
# Blocks POST/PUT/PATCH/DELETE on protected paths.
#
# INVARIANTS:
# - INV-OCC-005: Evidence immutability (no retroactive edits)
# - INV-API-001: Read-only endpoint enforcement
#
# Author: CODY (GID-01) — Backend Lead
# Security Review: SAM (GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# PROTECTED PATHS
# ═══════════════════════════════════════════════════════════════════════════════

# Paths that are strictly read-only (GET only)
READ_ONLY_PATH_PREFIXES: Set[str] = {
    "/occ/timeline",
    "/occ/agents",
    "/occ/diff",
    "/occ/dashboard",
    "/occ/activities",
    "/occ/artifacts",
    "/occ/audit-events",
    "/occ/decisions",
    "/occ/pdo",
    "/occ/proofpacks",
    "/oc/",
    "/governance/",
}

# Methods that are forbidden on read-only paths
FORBIDDEN_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints explicitly allowed for writes (whitelist)
WRITE_ALLOWED_PATHS: Set[str] = {
    "/occ/kill-switch/engage",  # Emergency only, requires auth
    "/occ/kill-switch/release",  # Emergency only, requires auth
}


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY ENFORCEMENT MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

class ReadOnlyEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce read-only constraints on OCC/Governance endpoints.
    
    INV-OCC-005: Evidence immutability
    INV-API-001: Read-only endpoint enforcement
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()
        
        # Check if this is a protected path with a forbidden method
        if method in FORBIDDEN_METHODS:
            # Check whitelist first
            if path in WRITE_ALLOWED_PATHS:
                # Allowed but logged
                logger.info(
                    f"Write operation allowed on whitelisted path: {method} {path}",
                    extra={"method": method, "path": path}
                )
            else:
                # Check if path matches any read-only prefix
                for prefix in READ_ONLY_PATH_PREFIXES:
                    if path.startswith(prefix):
                        logger.warning(
                            f"Read-only violation blocked: {method} {path}",
                            extra={
                                "method": method,
                                "path": path,
                                "invariant": "INV-OCC-005",
                            }
                        )
                        return JSONResponse(
                            status_code=405,
                            content={
                                "detail": f"Method {method} not allowed. This endpoint is READ-ONLY. INV-OCC-005: Evidence immutability.",
                                "invariant": "INV-OCC-005",
                                "path": path,
                                "allowed_methods": ["GET", "HEAD", "OPTIONS"],
                            },
                            headers={
                                "Allow": "GET, HEAD, OPTIONS",
                                "X-Invariant-Violation": "INV-OCC-005",
                            },
                        )
        
        return await call_next(request)


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION REJECTION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def reject_mutation(
    path: str,
    method: str,
    invariant: str = "INV-OCC-005",
) -> None:
    """
    Raise HTTPException for mutation attempts.
    
    Use this in route handlers as an extra guard.
    """
    raise HTTPException(
        status_code=405,
        detail=f"Method {method} not allowed on {path}. {invariant}: Evidence immutability.",
        headers={"Allow": "GET, HEAD, OPTIONS"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE HASH ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceHashEnforcer:
    """
    Enforces evidence hash presence on responses.
    
    INV-OCC-005: Evidence immutability
    """
    
    REQUIRED_HASH_PATHS: Set[str] = {
        "/occ/timeline",
        "/occ/agents",
        "/occ/diff",
        "/occ/proofpacks",
        "/occ/decisions",
        "/occ/ber",
    }
    
    @classmethod
    def should_have_hash(cls, path: str) -> bool:
        """Check if path requires evidence hash in response."""
        for prefix in cls.REQUIRED_HASH_PATHS:
            if path.startswith(prefix):
                return True
        return False
    
    @classmethod
    def validate_response_has_hash(cls, path: str, response_data: dict) -> bool:
        """Validate response contains evidence hash if required."""
        if not cls.should_have_hash(path):
            return True
        
        # Check for common hash field names
        hash_fields = {"evidence_hash", "content_hash", "hash", "proof_hash"}
        
        def has_hash_field(obj: dict) -> bool:
            if isinstance(obj, dict):
                if any(field in obj for field in hash_fields):
                    return True
                for value in obj.values():
                    if isinstance(value, dict) and has_hash_field(value):
                        return True
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and has_hash_field(item):
                                return True
            return False
        
        return has_hash_field(response_data)


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST AUDIT DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

def audit_request(
    action: str,
    invariants: Optional[List[str]] = None,
):
    """
    Decorator to audit API requests.
    
    Usage:
        @router.get("/endpoint")
        @audit_request("read_timeline", ["INV-OCC-004"])
        async def get_timeline():
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            
            logger.info(
                f"API request: {action}",
                extra={
                    "action": action,
                    "invariants": invariants or [],
                    "timestamp": start_time.isoformat(),
                }
            )
            
            result = await func(*args, **kwargs)
            
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.info(
                f"API response: {action} ({duration_ms:.2f}ms)",
                extra={
                    "action": action,
                    "duration_ms": duration_ms,
                }
            )
            
            return result
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "READ_ONLY_PATH_PREFIXES",
    "FORBIDDEN_METHODS",
    "WRITE_ALLOWED_PATHS",
    "ReadOnlyEnforcementMiddleware",
    "reject_mutation",
    "EvidenceHashEnforcer",
    "audit_request",
]
