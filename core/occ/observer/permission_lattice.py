"""
Observer Permission Lattice — PAC-JEFFREY-P45

Read-only permission lattice for regulated observer access.
Implements audit-grade access control with zero write paths.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional
import os


class ObserverCategory(Enum):
    """Observer category classifications."""
    
    OBSERVER_REG = "OBSERVER_REG"           # Regulatory body
    OBSERVER_AUDIT = "OBSERVER_AUDIT"       # External auditor
    OBSERVER_COMPLIANCE = "OBSERVER_COMPLIANCE"  # Compliance monitor
    DISABLED = "DISABLED"                   # No observer access


class PermissionLevel(Enum):
    """Permission levels in the lattice (ordered from lowest to highest)."""
    
    L0_NONE = 0         # No access
    L1_HEALTH = 1       # Health checks only
    L2_OBSERVE = 2      # Basic observation
    L3_AUDIT = 3        # Full audit access
    L4_VERIFY = 4       # Verification + download


class ResourceType(Enum):
    """Resource types in the permission lattice."""
    
    TIMELINE = "timeline"
    PDO_SHADOW = "pdo:shadow"
    PDO_PRODUCTION = "pdo:production"
    PROOFPACK = "proofpack"
    AUDIT_LOG = "audit_log"
    KILL_SWITCH = "kill_switch"
    HEALTH = "health"
    ACTIVITY = "activity"
    AGENT_STATE = "agent_state"
    GOVERNANCE = "governance"
    CONFIG = "config"
    SETTLEMENT = "settlement"
    OPERATOR = "operator"
    USER = "user"


class Operation(Enum):
    """Operations that can be performed on resources."""
    
    READ = "read"
    LIST = "list"
    VERIFY = "verify"
    DOWNLOAD = "download"
    VIEW_STATE = "view_state"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CONTROL = "control"
    MODIFY = "modify"


@dataclass(frozen=True)
class Permission:
    """A single permission grant."""
    
    resource: ResourceType
    operation: Operation
    
    def __str__(self) -> str:
        return f"{self.resource.value}:{self.operation.value}"


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION SETS
# ═══════════════════════════════════════════════════════════════════════════════

# Read-only permissions available to observers
OBSERVER_READ_PERMISSIONS: FrozenSet[Permission] = frozenset([
    # Timeline access
    Permission(ResourceType.TIMELINE, Operation.READ),
    Permission(ResourceType.TIMELINE, Operation.LIST),
    
    # PDO access (SHADOW only)
    Permission(ResourceType.PDO_SHADOW, Operation.READ),
    Permission(ResourceType.PDO_SHADOW, Operation.LIST),
    
    # ProofPack access
    Permission(ResourceType.PROOFPACK, Operation.READ),
    Permission(ResourceType.PROOFPACK, Operation.LIST),
    Permission(ResourceType.PROOFPACK, Operation.VERIFY),
    Permission(ResourceType.PROOFPACK, Operation.DOWNLOAD),
    
    # Audit log access
    Permission(ResourceType.AUDIT_LOG, Operation.READ),
    Permission(ResourceType.AUDIT_LOG, Operation.LIST),
    
    # Kill-switch visibility (no control)
    Permission(ResourceType.KILL_SWITCH, Operation.VIEW_STATE),
    
    # Health access
    Permission(ResourceType.HEALTH, Operation.READ),
    
    # Activity access
    Permission(ResourceType.ACTIVITY, Operation.READ),
    Permission(ResourceType.ACTIVITY, Operation.LIST),
    
    # Agent state visibility
    Permission(ResourceType.AGENT_STATE, Operation.VIEW_STATE),
    Permission(ResourceType.AGENT_STATE, Operation.READ),
    
    # Governance visibility
    Permission(ResourceType.GOVERNANCE, Operation.READ),
])

# Permissions explicitly denied to all observers (HARD BLOCK)
OBSERVER_DENIED_PERMISSIONS: FrozenSet[Permission] = frozenset([
    # Production PDO access
    Permission(ResourceType.PDO_PRODUCTION, Operation.READ),
    Permission(ResourceType.PDO_PRODUCTION, Operation.LIST),
    
    # All write operations on PDOs
    Permission(ResourceType.PDO_SHADOW, Operation.CREATE),
    Permission(ResourceType.PDO_SHADOW, Operation.UPDATE),
    Permission(ResourceType.PDO_SHADOW, Operation.DELETE),
    Permission(ResourceType.PDO_PRODUCTION, Operation.CREATE),
    Permission(ResourceType.PDO_PRODUCTION, Operation.UPDATE),
    Permission(ResourceType.PDO_PRODUCTION, Operation.DELETE),
    
    # Kill-switch control
    Permission(ResourceType.KILL_SWITCH, Operation.CONTROL),
    Permission(ResourceType.KILL_SWITCH, Operation.MODIFY),
    
    # Settlement operations
    Permission(ResourceType.SETTLEMENT, Operation.READ),
    Permission(ResourceType.SETTLEMENT, Operation.CREATE),
    Permission(ResourceType.SETTLEMENT, Operation.CONTROL),
    
    # Operator operations
    Permission(ResourceType.OPERATOR, Operation.READ),
    Permission(ResourceType.OPERATOR, Operation.MODIFY),
    Permission(ResourceType.OPERATOR, Operation.CONTROL),
    
    # Config operations
    Permission(ResourceType.CONFIG, Operation.READ),
    Permission(ResourceType.CONFIG, Operation.MODIFY),
    
    # User management
    Permission(ResourceType.USER, Operation.READ),
    Permission(ResourceType.USER, Operation.CREATE),
    Permission(ResourceType.USER, Operation.UPDATE),
    Permission(ResourceType.USER, Operation.DELETE),
    
    # Agent modification
    Permission(ResourceType.AGENT_STATE, Operation.MODIFY),
    Permission(ResourceType.AGENT_STATE, Operation.CONTROL),
    
    # Governance modification
    Permission(ResourceType.GOVERNANCE, Operation.MODIFY),
])


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVER RATE LIMITS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ObserverRateLimits:
    """Rate limits for observer access."""
    
    requests_per_minute: int = 20
    requests_per_hour: int = 300
    concurrent_connections: int = 1
    burst_limit: int = 5
    proofpack_downloads_per_day: int = 50
    timeline_queries_per_hour: int = 100
    max_results_per_query: int = 100


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVER SESSION CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ObserverSessionConfig:
    """Session configuration for observer category."""
    
    max_session_hours: int
    idle_timeout_minutes: int = 30
    require_mfa: bool = True
    allow_token_refresh: bool = False
    concurrent_sessions: int = 1


OBSERVER_SESSION_CONFIGS = {
    ObserverCategory.OBSERVER_REG: ObserverSessionConfig(
        max_session_hours=8,
        idle_timeout_minutes=30,
        require_mfa=True,
        allow_token_refresh=False,
        concurrent_sessions=1,
    ),
    ObserverCategory.OBSERVER_AUDIT: ObserverSessionConfig(
        max_session_hours=4,
        idle_timeout_minutes=30,
        require_mfa=True,
        allow_token_refresh=False,
        concurrent_sessions=1,
    ),
    ObserverCategory.OBSERVER_COMPLIANCE: ObserverSessionConfig(
        max_session_hours=2,
        idle_timeout_minutes=15,
        require_mfa=True,
        allow_token_refresh=False,
        concurrent_sessions=1,
    ),
    ObserverCategory.DISABLED: ObserverSessionConfig(
        max_session_hours=0,
        idle_timeout_minutes=0,
        require_mfa=True,
        allow_token_refresh=False,
        concurrent_sessions=0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION LATTICE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ObserverPermissionLattice:
    """
    Permission lattice for observer access.
    
    Implements a fail-closed lattice where:
    - Permissions are explicitly granted (whitelist)
    - Unknown permissions are denied
    - Denied permissions are hard-blocked
    """
    
    category: ObserverCategory
    enabled: bool = True
    
    # Permission sets
    granted_permissions: FrozenSet[Permission] = field(
        default_factory=lambda: OBSERVER_READ_PERMISSIONS
    )
    denied_permissions: FrozenSet[Permission] = field(
        default_factory=lambda: OBSERVER_DENIED_PERMISSIONS
    )
    
    # Rate limits
    rate_limits: ObserverRateLimits = field(
        default_factory=ObserverRateLimits
    )
    
    # Security settings
    fail_closed: bool = True
    audit_all_requests: bool = True
    
    # Token settings
    token_audience: str = "chainbridge-observer"
    token_scope: str = "observer:read"
    
    def is_permission_granted(self, permission: Permission) -> bool:
        """Check if permission is explicitly granted."""
        if not self.enabled:
            return False
        if self.category == ObserverCategory.DISABLED:
            return False
        return permission in self.granted_permissions
    
    def is_permission_denied(self, permission: Permission) -> bool:
        """Check if permission is explicitly denied (hard block)."""
        return permission in self.denied_permissions
    
    def check_permission(self, resource: ResourceType, operation: Operation) -> bool:
        """
        Check if an operation on a resource is permitted.
        
        Returns True only if:
        1. Observer is enabled
        2. Permission is explicitly granted
        3. Permission is not explicitly denied
        
        Returns False otherwise (fail-closed).
        """
        if not self.enabled:
            return False
        
        if self.category == ObserverCategory.DISABLED:
            return False
        
        permission = Permission(resource, operation)
        
        # Hard block takes precedence
        if self.is_permission_denied(permission):
            return False
        
        # Must be explicitly granted
        if self.is_permission_granted(permission):
            return True
        
        # Fail closed - deny unknown permissions
        return False
    
    def get_session_config(self) -> ObserverSessionConfig:
        """Get session configuration for this observer category."""
        return OBSERVER_SESSION_CONFIGS.get(
            self.category,
            OBSERVER_SESSION_CONFIGS[ObserverCategory.DISABLED]
        )
    
    def can_access_kill_switch_state(self) -> bool:
        """Check if observer can view kill-switch state."""
        return self.check_permission(
            ResourceType.KILL_SWITCH,
            Operation.VIEW_STATE
        )
    
    def can_control_kill_switch(self) -> bool:
        """Check if observer can control kill-switch. ALWAYS FALSE."""
        return False  # Hard-coded false - observers never control kill-switch
    
    def can_access_proofpack(self) -> bool:
        """Check if observer can access proofpacks."""
        return self.check_permission(
            ResourceType.PROOFPACK,
            Operation.READ
        )
    
    def can_download_proofpack(self) -> bool:
        """Check if observer can download proofpacks."""
        return self.check_permission(
            ResourceType.PROOFPACK,
            Operation.DOWNLOAD
        )
    
    def can_verify_proofpack(self) -> bool:
        """Check if observer can verify proofpacks."""
        return self.check_permission(
            ResourceType.PROOFPACK,
            Operation.VERIFY
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-CONFIGURED LATTICES
# ═══════════════════════════════════════════════════════════════════════════════

REGULATORY_OBSERVER_LATTICE = ObserverPermissionLattice(
    category=ObserverCategory.OBSERVER_REG,
    enabled=True,
    granted_permissions=OBSERVER_READ_PERMISSIONS,
    denied_permissions=OBSERVER_DENIED_PERMISSIONS,
)

EXTERNAL_AUDITOR_LATTICE = ObserverPermissionLattice(
    category=ObserverCategory.OBSERVER_AUDIT,
    enabled=True,
    granted_permissions=OBSERVER_READ_PERMISSIONS,
    denied_permissions=OBSERVER_DENIED_PERMISSIONS,
)

COMPLIANCE_OBSERVER_LATTICE = ObserverPermissionLattice(
    category=ObserverCategory.OBSERVER_COMPLIANCE,
    enabled=True,
    granted_permissions=OBSERVER_READ_PERMISSIONS,
    denied_permissions=OBSERVER_DENIED_PERMISSIONS,
)

DISABLED_OBSERVER_LATTICE = ObserverPermissionLattice(
    category=ObserverCategory.DISABLED,
    enabled=False,
    granted_permissions=frozenset(),
    denied_permissions=OBSERVER_DENIED_PERMISSIONS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# LATTICE FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_observer_lattice(category: Optional[str] = None) -> ObserverPermissionLattice:
    """
    Get observer permission lattice for category.
    
    Reads from CHAINBRIDGE_OBSERVER_MODE env var if category not specified.
    Defaults to DISABLED if not set (fail-closed).
    """
    if category is None:
        category = os.environ.get("CHAINBRIDGE_OBSERVER_MODE", "DISABLED")
    
    lattice_map = {
        "OBSERVER_REG": REGULATORY_OBSERVER_LATTICE,
        "OBSERVER_AUDIT": EXTERNAL_AUDITOR_LATTICE,
        "OBSERVER_COMPLIANCE": COMPLIANCE_OBSERVER_LATTICE,
        "DISABLED": DISABLED_OBSERVER_LATTICE,
    }
    
    return lattice_map.get(category, DISABLED_OBSERVER_LATTICE)


def check_observer_access(
    category: str,
    resource: str,
    operation: str
) -> bool:
    """
    Check if observer category has access to perform operation on resource.
    
    Args:
        category: Observer category (OBSERVER_REG, OBSERVER_AUDIT, etc.)
        resource: Resource type string
        operation: Operation type string
    
    Returns:
        True if access permitted, False otherwise.
    """
    try:
        lattice = get_observer_lattice(category)
        resource_type = ResourceType(resource)
        op_type = Operation(operation)
        return lattice.check_permission(resource_type, op_type)
    except (ValueError, KeyError):
        # Unknown resource or operation - fail closed
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT ACCESS MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

OBSERVER_ENDPOINT_MAP = {
    # Timeline endpoints
    ("GET", "/occ/timeline"): (ResourceType.TIMELINE, Operation.LIST),
    ("GET", "/occ/timeline/{id}"): (ResourceType.TIMELINE, Operation.READ),
    
    # PDO endpoints (shadow only)
    ("GET", "/oc/pdo"): (ResourceType.PDO_SHADOW, Operation.LIST),
    ("GET", "/oc/pdo/{id}"): (ResourceType.PDO_SHADOW, Operation.READ),
    
    # ProofPack endpoints
    ("GET", "/oc/proofpack"): (ResourceType.PROOFPACK, Operation.LIST),
    ("GET", "/oc/proofpack/{id}"): (ResourceType.PROOFPACK, Operation.READ),
    ("GET", "/oc/proofpack/{id}/verify"): (ResourceType.PROOFPACK, Operation.VERIFY),
    ("GET", "/oc/proofpack/{id}/download"): (ResourceType.PROOFPACK, Operation.DOWNLOAD),
    
    # Audit endpoints
    ("GET", "/oc/audit"): (ResourceType.AUDIT_LOG, Operation.LIST),
    ("GET", "/oc/audit/{id}"): (ResourceType.AUDIT_LOG, Operation.READ),
    
    # Kill-switch state (read-only)
    ("GET", "/occ/kill-switch/state"): (ResourceType.KILL_SWITCH, Operation.VIEW_STATE),
    
    # Health
    ("GET", "/health"): (ResourceType.HEALTH, Operation.READ),
    
    # Activity
    ("GET", "/occ/activity"): (ResourceType.ACTIVITY, Operation.LIST),
    
    # Agent state
    ("GET", "/occ/agents"): (ResourceType.AGENT_STATE, Operation.READ),
    ("GET", "/occ/agents/state"): (ResourceType.AGENT_STATE, Operation.VIEW_STATE),
    
    # Governance
    ("GET", "/governance/rules"): (ResourceType.GOVERNANCE, Operation.READ),
}


def check_observer_endpoint_access(
    category: str,
    method: str,
    path: str
) -> bool:
    """
    Check if observer can access a specific endpoint.
    
    Args:
        category: Observer category
        method: HTTP method (GET, POST, etc.)
        path: Request path
    
    Returns:
        True if access permitted, False otherwise.
    """
    lattice = get_observer_lattice(category)
    
    if not lattice.enabled:
        return False
    
    # Normalize path (remove trailing slash, handle path params)
    normalized_path = path.rstrip("/")
    
    # Check exact match first
    key = (method.upper(), normalized_path)
    if key in OBSERVER_ENDPOINT_MAP:
        resource, operation = OBSERVER_ENDPOINT_MAP[key]
        return lattice.check_permission(resource, operation)
    
    # Check pattern matches (for path parameters)
    for (ep_method, ep_pattern), (resource, operation) in OBSERVER_ENDPOINT_MAP.items():
        if ep_method != method.upper():
            continue
        
        # Simple pattern matching for {id} style params
        if "{" in ep_pattern:
            pattern_parts = ep_pattern.split("/")
            path_parts = normalized_path.split("/")
            
            if len(pattern_parts) != len(path_parts):
                continue
            
            match = True
            for pp, pathp in zip(pattern_parts, path_parts):
                if pp.startswith("{") and pp.endswith("}"):
                    continue  # Parameter placeholder matches anything
                if pp != pathp:
                    match = False
                    break
            
            if match:
                return lattice.check_permission(resource, operation)
    
    # No match found - fail closed
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

def verify_lattice_invariants(lattice: ObserverPermissionLattice) -> dict:
    """
    Verify governance invariants for observer lattice.
    
    Returns dict with invariant check results.
    """
    results = {}
    
    # INV-OBS-001: No Write Paths
    write_ops = [Operation.CREATE, Operation.UPDATE, Operation.DELETE, Operation.MODIFY]
    has_write = any(
        p.operation in write_ops
        for p in lattice.granted_permissions
    )
    results["INV-OBS-001_NO_WRITE_PATHS"] = not has_write
    
    # INV-OBS-002: No Control Paths
    has_control = any(
        p.operation == Operation.CONTROL
        for p in lattice.granted_permissions
    )
    results["INV-OBS-002_NO_CONTROL_PATHS"] = not has_control
    
    # INV-OBS-003: Production Isolation
    has_production = any(
        p.resource == ResourceType.PDO_PRODUCTION
        for p in lattice.granted_permissions
    )
    results["INV-OBS-003_PRODUCTION_ISOLATION"] = not has_production
    
    # INV-OBS-004: Kill-Switch No Control
    kill_switch_control = Permission(ResourceType.KILL_SWITCH, Operation.CONTROL)
    results["INV-OBS-004_KILL_SWITCH_NO_CONTROL"] = (
        kill_switch_control not in lattice.granted_permissions
    )
    
    # INV-OBS-005: Fail Closed
    results["INV-OBS-005_FAIL_CLOSED"] = lattice.fail_closed
    
    # INV-OBS-006: Audit Enabled
    results["INV-OBS-006_AUDIT_ENABLED"] = lattice.audit_all_requests
    
    return results
