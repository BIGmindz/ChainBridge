"""Security utilities and admin auth stubs for ChainBridge APIs."""

import os
from dataclasses import dataclass, field
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-CHAINBRIDGE-ADMIN-KEY", auto_error=False)


@dataclass
class AdminUser:
    """Represents an authenticated admin user context."""

    id: str
    name: str
    roles: List[str] = field(default_factory=list)


def get_current_admin_user(
    api_key: Optional[str] = Depends(api_key_header),
) -> AdminUser:
    """
    Temporary stub for admin auth.

    - In dev (CHAINBRIDGE_ADMIN_KEY unset) we allow access without a key but return a dev admin user.
    - In prod we will require the header to match the configured key.
    """
    expected = os.getenv("CHAINBRIDGE_ADMIN_KEY")
    if expected is None:
        return AdminUser(id="dev-admin", name="Dev Admin", roles=["admin"])

    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )

    return AdminUser(id="admin", name="ChainBridge Admin", roles=["admin"])
