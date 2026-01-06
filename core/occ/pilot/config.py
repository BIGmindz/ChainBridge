"""
Pilot Mode Configuration — External Pilot Guards & Flags

PAC Reference: PAC-JEFFREY-P44
Classification: CONFIGURATION / SECURITY
Author: CODY (GID-01) + SAM (GID-06)

This module provides configuration for external pilot mode,
enforcing trust boundaries and capability constraints.

INVARIANTS:
- INV-PILOT-001: Pilots are capability-constrained, not trust-based
- INV-PILOT-002: Read-only access only
- INV-PILOT-003: SHADOW classification only
- INV-PILOT-004: No production coupling
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, List, Optional


class PilotMode(str, Enum):
    """Pilot operational mode."""
    DISABLED = "DISABLED"           # No pilot access
    EXTERNAL_PILOT = "EXTERNAL_PILOT"   # External third-party pilot
    INTERNAL_PILOT = "INTERNAL_PILOT"   # Internal evaluation
    DEMO = "DEMO"                   # Demo mode (time-limited)


class PDOClassification(str, Enum):
    """PDO classification for pilot visibility."""
    SHADOW = "SHADOW"         # Visible to pilots
    PRODUCTION = "PRODUCTION" # Hidden from pilots


@dataclass(frozen=True)
class PilotPermission:
    """Single pilot permission definition."""
    name: str
    description: str
    allowed: bool = True


@dataclass(frozen=True)
class PilotRateLimits:
    """Rate limit configuration for pilots."""
    requests_per_minute: int = 30
    requests_per_hour: int = 500
    concurrent_connections: int = 5
    burst_limit: int = 10
    burst_window_seconds: int = 10


@dataclass(frozen=True)
class PilotConfig:
    """
    Complete pilot mode configuration.
    
    This configuration is IMMUTABLE once loaded.
    Changes require a new PAC authorization.
    """
    
    # Mode settings
    mode: PilotMode = PilotMode.DISABLED
    enabled: bool = False
    
    # Visibility constraints
    visible_classifications: FrozenSet[PDOClassification] = field(
        default_factory=lambda: frozenset({PDOClassification.SHADOW})
    )
    
    # Rate limits
    rate_limits: PilotRateLimits = field(default_factory=PilotRateLimits)
    
    # Permitted operations (ALLOW LIST)
    permitted_operations: FrozenSet[str] = field(
        default_factory=lambda: frozenset({
            "pdo:read:shadow",
            "timeline:read",
            "activity:read",
            "artifact:read",
            "health:read",
            "ledger:read:integrity",
        })
    )
    
    # Denied operations (DENY LIST - takes precedence)
    denied_operations: FrozenSet[str] = field(
        default_factory=lambda: frozenset({
            "pdo:create",
            "pdo:update",
            "pdo:delete",
            "pdo:read:production",
            "kill_switch:arm",
            "kill_switch:engage",
            "kill_switch:disengage",
            "operator:*",
            "config:*",
            "admin:*",
        })
    )
    
    # Token settings
    token_max_lifetime_hours: int = 24
    token_auto_refresh: bool = False
    token_audience: str = "chainbridge-pilot"
    
    # Audit settings
    audit_all_requests: bool = True
    audit_include_ip_hash: bool = True
    
    # Safety settings
    fail_closed: bool = True  # Deny on any ambiguity
    hide_production_pdos: bool = True  # 404 instead of 403
    
    def is_operation_permitted(self, operation: str) -> bool:
        """
        Check if an operation is permitted for pilots.
        
        DENY LIST takes precedence over ALLOW LIST.
        Unknown operations are DENIED (fail-closed).
        """
        # Check explicit deny first
        for denied in self.denied_operations:
            if denied.endswith("*"):
                prefix = denied[:-1]
                if operation.startswith(prefix):
                    return False
            elif operation == denied:
                return False
        
        # Check explicit allow
        if operation in self.permitted_operations:
            return True
        
        # Fail-closed: unknown operations are denied
        return not self.fail_closed
    
    def can_view_classification(self, classification: PDOClassification) -> bool:
        """Check if pilot can view a PDO classification."""
        return classification in self.visible_classifications


# Default configurations for different pilot modes

EXTERNAL_PILOT_CONFIG = PilotConfig(
    mode=PilotMode.EXTERNAL_PILOT,
    enabled=True,
    visible_classifications=frozenset({PDOClassification.SHADOW}),
    rate_limits=PilotRateLimits(
        requests_per_minute=30,
        requests_per_hour=500,
        concurrent_connections=5,
        burst_limit=10,
    ),
)

INTERNAL_PILOT_CONFIG = PilotConfig(
    mode=PilotMode.INTERNAL_PILOT,
    enabled=True,
    visible_classifications=frozenset({PDOClassification.SHADOW}),
    rate_limits=PilotRateLimits(
        requests_per_minute=100,
        requests_per_hour=2000,
        concurrent_connections=10,
        burst_limit=20,
    ),
)

DEMO_CONFIG = PilotConfig(
    mode=PilotMode.DEMO,
    enabled=True,
    visible_classifications=frozenset({PDOClassification.SHADOW}),
    rate_limits=PilotRateLimits(
        requests_per_minute=60,
        requests_per_hour=1000,
        concurrent_connections=3,
        burst_limit=15,
    ),
    token_max_lifetime_hours=4,  # Demo tokens expire faster
)

DISABLED_CONFIG = PilotConfig(
    mode=PilotMode.DISABLED,
    enabled=False,
)


def get_pilot_config() -> PilotConfig:
    """
    Get the active pilot configuration.
    
    Configuration is determined by environment variable:
    - CHAINBRIDGE_PILOT_MODE: EXTERNAL_PILOT | INTERNAL_PILOT | DEMO | DISABLED
    
    Returns:
        Active PilotConfig (immutable)
    """
    mode_str = os.environ.get("CHAINBRIDGE_PILOT_MODE", "DISABLED").upper()
    
    try:
        mode = PilotMode(mode_str)
    except ValueError:
        # Unknown mode -> fail-closed to DISABLED
        return DISABLED_CONFIG
    
    config_map = {
        PilotMode.EXTERNAL_PILOT: EXTERNAL_PILOT_CONFIG,
        PilotMode.INTERNAL_PILOT: INTERNAL_PILOT_CONFIG,
        PilotMode.DEMO: DEMO_CONFIG,
        PilotMode.DISABLED: DISABLED_CONFIG,
    }
    
    return config_map.get(mode, DISABLED_CONFIG)


# Endpoint permission mapping
ENDPOINT_PERMISSIONS = {
    # PDO endpoints
    "GET /oc/pdo": "pdo:read:shadow",
    "GET /oc/pdo/{pdo_id}": "pdo:read:shadow",
    "GET /oc/pdo/{pdo_id}/timeline": "timeline:read",
    "POST /oc/pdo": "pdo:create",
    
    # Activity endpoints
    "GET /occ/activities": "activity:read",
    "GET /occ/activities/{id}": "activity:read",
    
    # Artifact endpoints
    "GET /occ/artifacts": "artifact:read",
    "GET /occ/artifacts/{id}": "artifact:read",
    
    # Health endpoints
    "GET /health": "health:read",
    
    # Ledger endpoints
    "GET /occ/dashboard/ledger/integrity": "ledger:read:integrity",
    
    # Kill-switch endpoints (all denied)
    "POST /occ/kill-switch/arm": "kill_switch:arm",
    "POST /occ/kill-switch/engage": "kill_switch:engage",
    "POST /occ/kill-switch/disengage": "kill_switch:disengage",
}


def check_pilot_endpoint_access(method: str, path: str) -> bool:
    """
    Check if a pilot can access an endpoint.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
    
    Returns:
        True if access permitted, False otherwise
    """
    config = get_pilot_config()
    
    if not config.enabled:
        return False
    
    # Normalize path for matching
    endpoint_key = f"{method.upper()} {path}"
    
    # Try exact match first
    if endpoint_key in ENDPOINT_PERMISSIONS:
        permission = ENDPOINT_PERMISSIONS[endpoint_key]
        return config.is_operation_permitted(permission)
    
    # Try pattern matching (for path parameters)
    for pattern, permission in ENDPOINT_PERMISSIONS.items():
        pattern_method, pattern_path = pattern.split(" ", 1)
        if method.upper() != pattern_method:
            continue
        
        # Simple pattern matching for {param} segments
        pattern_parts = pattern_path.split("/")
        path_parts = path.split("/")
        
        if len(pattern_parts) != len(path_parts):
            continue
        
        match = True
        for pp, pathp in zip(pattern_parts, path_parts):
            if pp.startswith("{") and pp.endswith("}"):
                continue  # Parameter matches anything
            if pp != pathp:
                match = False
                break
        
        if match:
            return config.is_operation_permitted(permission)
    
    # Unknown endpoint -> fail-closed
    return not config.fail_closed


# Forbidden claims registry (for PAX enforcement)
FORBIDDEN_PILOT_CLAIMS = frozenset({
    "ChainBridge processes real transactions",
    "ChainBridge is auditor-certified",
    "ChainBridge replaces compliance teams",
    "ChainBridge guarantees settlement",
    "ChainBridge is production-ready",
    "ChainBridge provides autonomous compliance",
    "ChainBridge eliminates manual review",
    "ChainBridge is regulatory-approved",
})


def is_claim_forbidden(claim: str) -> bool:
    """
    Check if a claim is forbidden for pilots.
    
    Uses fuzzy matching to catch variations.
    """
    claim_lower = claim.lower()
    
    for forbidden in FORBIDDEN_PILOT_CLAIMS:
        if forbidden.lower() in claim_lower:
            return True
        # Check key phrases
        if "production" in claim_lower and "ready" in claim_lower:
            return True
        if "certified" in claim_lower or "approved" in claim_lower:
            return True
        if "autonomous" in claim_lower and "compliance" in claim_lower:
            return True
    
    return False
