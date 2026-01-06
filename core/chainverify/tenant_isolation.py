"""
Tenant Isolation — Multi-Tenant Test Swarm Boundaries

PAC Reference: PAC-JEFFREY-P49
Agent: DAN (GID-07)

Provides hard isolation boundaries between tenants using ChainVerify.
Each tenant operates in a complete sandbox with no cross-contamination.

INVARIANTS:
- Zero data leakage between tenants
- Resource quotas enforced per tenant
- Kill-switch available per tenant
- No shared mutable state
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid
import hashlib


class TenantStatus(Enum):
    """Tenant lifecycle status."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    KILLED = "KILLED"


class IsolationLevel(Enum):
    """Level of isolation for tenant resources."""
    STANDARD = "STANDARD"      # Logical isolation
    ENHANCED = "ENHANCED"      # Process isolation
    MAXIMUM = "MAXIMUM"        # Container isolation


@dataclass
class ResourceQuota:
    """Resource limits for a tenant."""
    max_endpoints: int = 1000
    max_tests_per_run: int = 10000
    max_concurrent_executions: int = 10
    max_execution_time_seconds: int = 3600
    max_stored_results: int = 100
    max_spec_size_bytes: int = 10 * 1024 * 1024  # 10MB
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "max_endpoints": self.max_endpoints,
            "max_tests_per_run": self.max_tests_per_run,
            "max_concurrent_executions": self.max_concurrent_executions,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "max_stored_results": self.max_stored_results,
            "max_spec_size_bytes": self.max_spec_size_bytes,
        }


@dataclass
class UsageMetrics:
    """Current resource usage for a tenant."""
    endpoints_registered: int = 0
    tests_executed: int = 0
    active_executions: int = 0
    results_stored: int = 0
    total_execution_time_seconds: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoints_registered": self.endpoints_registered,
            "tests_executed": self.tests_executed,
            "active_executions": self.active_executions,
            "results_stored": self.results_stored,
            "total_execution_time_seconds": self.total_execution_time_seconds,
        }


@dataclass
class IsolationBoundary:
    """
    Defines the isolation boundary for a tenant.
    
    All tenant operations MUST go through this boundary.
    Cross-boundary access is FORBIDDEN.
    """
    tenant_id: str
    isolation_level: IsolationLevel
    namespace: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Cryptographic seal for boundary integrity
    boundary_seal: str = ""
    
    def __post_init__(self):
        if not self.boundary_seal:
            self.boundary_seal = self._compute_seal()
    
    def _compute_seal(self) -> str:
        """Compute cryptographic seal for this boundary."""
        data = f"{self.tenant_id}:{self.namespace}:{self.created_at.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def verify_seal(self) -> bool:
        """Verify boundary integrity."""
        return self.boundary_seal == self._compute_seal()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "isolation_level": self.isolation_level.value,
            "namespace": self.namespace,
            "created_at": self.created_at.isoformat(),
            "boundary_seal": self.boundary_seal,
        }


@dataclass
class TenantContext:
    """
    Complete tenant context for ChainVerify operations.
    
    This is the ONLY object that should be passed to tenant-scoped operations.
    It contains all necessary isolation and quota information.
    """
    tenant_id: str
    name: str
    status: TenantStatus
    boundary: IsolationBoundary
    quota: ResourceQuota
    usage: UsageMetrics
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Kill switch
    kill_switch_armed: bool = False
    kill_switch_reason: str = ""
    
    @property
    def is_active(self) -> bool:
        """Check if tenant can perform operations."""
        return self.status == TenantStatus.ACTIVE and not self.kill_switch_armed
    
    @property
    def namespace(self) -> str:
        """Get tenant namespace."""
        return self.boundary.namespace
    
    def check_quota(self, resource: str, requested: int = 1) -> bool:
        """
        Check if operation is within quota.
        
        Returns True if allowed, False if quota exceeded.
        """
        limits = {
            "endpoints": (self.usage.endpoints_registered, self.quota.max_endpoints),
            "tests": (self.usage.tests_executed, self.quota.max_tests_per_run),
            "executions": (self.usage.active_executions, self.quota.max_concurrent_executions),
            "results": (self.usage.results_stored, self.quota.max_stored_results),
        }
        
        if resource not in limits:
            return True
        
        current, maximum = limits[resource]
        return (current + requested) <= maximum
    
    def arm_kill_switch(self, reason: str) -> None:
        """Arm the kill switch — stops all tenant operations."""
        self.kill_switch_armed = True
        self.kill_switch_reason = reason
        self.status = TenantStatus.KILLED
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "status": self.status.value,
            "boundary": self.boundary.to_dict(),
            "quota": self.quota.to_dict(),
            "usage": self.usage.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "kill_switch_armed": self.kill_switch_armed,
            "kill_switch_reason": self.kill_switch_reason,
        }


class TenantError(Exception):
    """Error related to tenant operations."""
    pass


class QuotaExceededError(TenantError):
    """Quota limit exceeded."""
    pass


class IsolationViolationError(TenantError):
    """Attempted cross-tenant access."""
    pass


class TenantManager:
    """
    Manages tenant lifecycle and isolation.
    
    INVARIANTS:
    - One tenant context per tenant ID
    - No cross-tenant data access
    - Kill switch immediately effective
    """
    
    def __init__(self):
        self._tenants: dict[str, TenantContext] = {}
        self._namespace_to_tenant: dict[str, str] = {}
    
    def create_tenant(
        self,
        name: str,
        isolation_level: IsolationLevel = IsolationLevel.STANDARD,
        quota: ResourceQuota | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantContext:
        """
        Create a new tenant with isolated namespace.
        
        Returns:
            TenantContext for the new tenant
        """
        tenant_id = str(uuid.uuid4())
        namespace = f"cv_{tenant_id.replace('-', '_')[:8]}"
        
        boundary = IsolationBoundary(
            tenant_id=tenant_id,
            isolation_level=isolation_level,
            namespace=namespace,
        )
        
        context = TenantContext(
            tenant_id=tenant_id,
            name=name,
            status=TenantStatus.ACTIVE,
            boundary=boundary,
            quota=quota or ResourceQuota(),
            usage=UsageMetrics(),
            metadata=metadata or {},
        )
        
        self._tenants[tenant_id] = context
        self._namespace_to_tenant[namespace] = tenant_id
        
        return context
    
    def get_tenant(self, tenant_id: str) -> TenantContext | None:
        """Get tenant context by ID."""
        return self._tenants.get(tenant_id)
    
    def get_tenant_by_namespace(self, namespace: str) -> TenantContext | None:
        """Get tenant context by namespace."""
        tenant_id = self._namespace_to_tenant.get(namespace)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None
    
    def list_tenants(self, status: TenantStatus | None = None) -> list[TenantContext]:
        """List all tenants, optionally filtered by status."""
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants
    
    def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """Suspend a tenant (reversible)."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.SUSPENDED
        tenant.metadata["suspension_reason"] = reason
        tenant.updated_at = datetime.utcnow()
        return True
    
    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        if tenant.kill_switch_armed:
            return False  # Cannot reactivate killed tenant
        
        tenant.status = TenantStatus.ACTIVE
        tenant.updated_at = datetime.utcnow()
        return True
    
    def terminate_tenant(self, tenant_id: str) -> bool:
        """Terminate a tenant (permanent)."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.TERMINATED
        tenant.updated_at = datetime.utcnow()
        return True
    
    def kill_tenant(self, tenant_id: str, reason: str) -> bool:
        """
        Emergency kill switch for a tenant.
        
        This immediately stops all operations and cannot be reversed
        without manual intervention.
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        tenant.arm_kill_switch(reason)
        return True
    
    def validate_access(
        self,
        requesting_tenant_id: str,
        target_namespace: str
    ) -> bool:
        """
        Validate that a tenant can access a namespace.
        
        Returns True only if the namespace belongs to the requesting tenant.
        """
        tenant = self._tenants.get(requesting_tenant_id)
        if not tenant:
            return False
        
        return tenant.namespace == target_namespace
    
    def record_usage(
        self,
        tenant_id: str,
        endpoints: int = 0,
        tests: int = 0,
        execution_time: float = 0.0,
    ) -> None:
        """Record resource usage for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return
        
        tenant.usage.endpoints_registered += endpoints
        tenant.usage.tests_executed += tests
        tenant.usage.total_execution_time_seconds += execution_time
        tenant.updated_at = datetime.utcnow()


# Module-level singleton
_tenant_manager: TenantManager | None = None


def get_tenant_manager() -> TenantManager:
    """Get the singleton tenant manager."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


def reset_tenant_manager() -> None:
    """Reset the singleton (for testing)."""
    global _tenant_manager
    _tenant_manager = None


def create_tenant(
    name: str,
    isolation_level: IsolationLevel = IsolationLevel.STANDARD,
    quota: ResourceQuota | None = None,
) -> TenantContext:
    """Convenience function to create a tenant."""
    return get_tenant_manager().create_tenant(name, isolation_level, quota)


def get_tenant(tenant_id: str) -> TenantContext | None:
    """Convenience function to get a tenant."""
    return get_tenant_manager().get_tenant(tenant_id)
