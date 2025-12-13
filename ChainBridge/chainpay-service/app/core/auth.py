"""
ChainPay Authentication & Authorization Module

Security-first design:
- All endpoints require authentication by default
- DEV_AUTH_BYPASS=true allows unauthenticated access ONLY in dev (default: false)
- IDOR protection via tenant/shipment access verification
- Returns 401 for missing/invalid auth, 403 for unauthorized access
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def _is_dev_bypass_enabled() -> bool:
    """Check if dev auth bypass is explicitly enabled (default: false)."""
    return os.environ.get("DEV_AUTH_BYPASS", "false").lower() == "true"


# -----------------------------------------------------------------------------
# User Model (stub for integration)
# -----------------------------------------------------------------------------


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user/tenant."""

    user_id: str
    tenant_id: str
    roles: list[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def can_access_shipment(self, shipment_id: str) -> bool:
        """
        Check if user can access a specific shipment.

        Current implementation: tenant-prefix check.
        Future: database lookup for shipment ownership.
        """
        # Admin role bypasses tenant check
        if self.has_role("admin"):
            return True
        # Tenant-prefix check (e.g., "TENANT1-SHIP-123" accessible by TENANT1)
        if shipment_id.startswith(f"{self.tenant_id}-"):
            return True
        # Wildcard for demo tenant (allows SHIP-xxx format)
        if self.tenant_id == "demo" and shipment_id.startswith("SHIP-"):
            return True
        return False


# -----------------------------------------------------------------------------
# Token Validation (stub - replace with real JWT/OAuth validation)
# -----------------------------------------------------------------------------

_VALID_TOKENS: dict[str, AuthenticatedUser] = {
    # Demo tokens for testing - replace with real token validation
    "Bearer demo-token-tenant1": AuthenticatedUser(
        user_id="user-001",
        tenant_id="TENANT1",
        roles=["shipper"],
    ),
    "Bearer demo-token-tenant2": AuthenticatedUser(
        user_id="user-002",
        tenant_id="TENANT2",
        roles=["shipper"],
    ),
    "Bearer demo-token-admin": AuthenticatedUser(
        user_id="admin-001",
        tenant_id="admin",
        roles=["admin"],
    ),
    "Bearer demo-token": AuthenticatedUser(
        user_id="demo-user",
        tenant_id="demo",
        roles=["shipper"],
    ),
}


def _validate_token(authorization: str) -> Optional[AuthenticatedUser]:
    """
    Validate authorization token and return user.

    Stub implementation - replace with real JWT/OAuth validation.
    """
    return _VALID_TOKENS.get(authorization)


# -----------------------------------------------------------------------------
# FastAPI Dependencies
# -----------------------------------------------------------------------------


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """
    FastAPI dependency: Extract and validate current user from Authorization header.

    Raises:
        HTTPException 401: Missing or invalid Authorization header
    """
    # Dev bypass (explicit opt-in only)
    if _is_dev_bypass_enabled():
        return AuthenticatedUser(
            user_id="dev-bypass",
            tenant_id="demo",
            roles=["admin"],
        )

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _validate_token(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def verify_shipment_access(
    shipment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    FastAPI dependency: Verify user has access to a specific shipment.

    Args:
        shipment_id: The shipment ID from the path parameter
        user: The authenticated user (injected by get_current_user)

    Raises:
        HTTPException 403: User does not have access to this shipment

    Returns:
        The authenticated user (for chaining)
    """
    if not user.can_access_shipment(shipment_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to shipment {shipment_id}",
        )
    return user


# -----------------------------------------------------------------------------
# Utility for creating shipment access checker with path param
# -----------------------------------------------------------------------------


def require_shipment_access(shipment_id: str):
    """
    Create a dependency that checks shipment access for a given shipment_id.

    Usage in route:
        @router.get("/settlements/{shipment_id}")
        async def get_settlement(
            shipment_id: str,
            user: AuthenticatedUser = Depends(get_current_user),
        ):
            verify_shipment_access(shipment_id, user)
            ...
    """

    async def checker(user: AuthenticatedUser = Depends(get_current_user)):
        return verify_shipment_access(shipment_id, user)

    return checker
