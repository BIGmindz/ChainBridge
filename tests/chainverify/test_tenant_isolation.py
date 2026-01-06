"""
ChainVerify Tests — Tenant Isolation

PAC Reference: PAC-JEFFREY-P49
"""

import pytest

from core.chainverify.tenant_isolation import (
    TenantContext,
    TenantManager,
    IsolationBoundary,
    ResourceQuota,
    UsageMetrics,
    TenantStatus,
    IsolationLevel,
    TenantError,
    QuotaExceededError,
    get_tenant_manager,
    reset_tenant_manager,
    create_tenant,
    get_tenant,
)


class TestTenantStatus:
    """Test tenant status enumeration."""
    
    def test_all_statuses_defined(self):
        expected = {"PENDING", "ACTIVE", "SUSPENDED", "TERMINATED", "KILLED"}
        actual = {s.value for s in TenantStatus}
        assert actual == expected


class TestIsolationLevel:
    """Test isolation level enumeration."""
    
    def test_all_levels_defined(self):
        expected = {"STANDARD", "ENHANCED", "MAXIMUM"}
        actual = {l.value for l in IsolationLevel}
        assert actual == expected


class TestResourceQuota:
    """Test resource quota dataclass."""
    
    def test_default_quota(self):
        quota = ResourceQuota()
        
        assert quota.max_endpoints == 1000
        assert quota.max_tests_per_run == 10000
        assert quota.max_concurrent_executions == 10
    
    def test_custom_quota(self):
        quota = ResourceQuota(
            max_endpoints=500,
            max_tests_per_run=5000
        )
        
        assert quota.max_endpoints == 500
        assert quota.max_tests_per_run == 5000
    
    def test_to_dict(self):
        quota = ResourceQuota()
        d = quota.to_dict()
        
        assert "max_endpoints" in d
        assert "max_tests_per_run" in d


class TestUsageMetrics:
    """Test usage metrics dataclass."""
    
    def test_default_usage(self):
        usage = UsageMetrics()
        
        assert usage.endpoints_registered == 0
        assert usage.tests_executed == 0
        assert usage.active_executions == 0
    
    def test_to_dict(self):
        usage = UsageMetrics(tests_executed=100)
        d = usage.to_dict()
        
        assert d["tests_executed"] == 100


class TestIsolationBoundary:
    """Test isolation boundary dataclass."""
    
    def test_create_boundary(self):
        boundary = IsolationBoundary(
            tenant_id="tenant-123",
            isolation_level=IsolationLevel.STANDARD,
            namespace="cv_tenant123"
        )
        
        assert boundary.tenant_id == "tenant-123"
        assert boundary.boundary_seal != ""
    
    def test_verify_seal(self):
        boundary = IsolationBoundary(
            tenant_id="tenant-123",
            isolation_level=IsolationLevel.STANDARD,
            namespace="cv_tenant123"
        )
        
        assert boundary.verify_seal()
    
    def test_seal_changes_with_data(self):
        b1 = IsolationBoundary(
            tenant_id="tenant-1",
            isolation_level=IsolationLevel.STANDARD,
            namespace="ns1"
        )
        b2 = IsolationBoundary(
            tenant_id="tenant-2",
            isolation_level=IsolationLevel.STANDARD,
            namespace="ns2"
        )
        
        assert b1.boundary_seal != b2.boundary_seal


class TestTenantContext:
    """Test tenant context dataclass."""
    
    def test_create_context(self):
        boundary = IsolationBoundary(
            tenant_id="t1",
            isolation_level=IsolationLevel.STANDARD,
            namespace="cv_t1"
        )
        
        context = TenantContext(
            tenant_id="t1",
            name="Test Tenant",
            status=TenantStatus.ACTIVE,
            boundary=boundary,
            quota=ResourceQuota(),
            usage=UsageMetrics()
        )
        
        assert context.is_active
        assert context.namespace == "cv_t1"
    
    def test_check_quota_within_limit(self):
        boundary = IsolationBoundary("t1", IsolationLevel.STANDARD, "ns")
        context = TenantContext(
            tenant_id="t1",
            name="Test",
            status=TenantStatus.ACTIVE,
            boundary=boundary,
            quota=ResourceQuota(max_endpoints=100),
            usage=UsageMetrics(endpoints_registered=50)
        )
        
        assert context.check_quota("endpoints", 10)
    
    def test_check_quota_exceeds_limit(self):
        boundary = IsolationBoundary("t1", IsolationLevel.STANDARD, "ns")
        context = TenantContext(
            tenant_id="t1",
            name="Test",
            status=TenantStatus.ACTIVE,
            boundary=boundary,
            quota=ResourceQuota(max_endpoints=100),
            usage=UsageMetrics(endpoints_registered=95)
        )
        
        assert not context.check_quota("endpoints", 10)
    
    def test_arm_kill_switch(self):
        boundary = IsolationBoundary("t1", IsolationLevel.STANDARD, "ns")
        context = TenantContext(
            tenant_id="t1",
            name="Test",
            status=TenantStatus.ACTIVE,
            boundary=boundary,
            quota=ResourceQuota(),
            usage=UsageMetrics()
        )
        
        assert context.is_active
        
        context.arm_kill_switch("Security incident")
        
        assert not context.is_active
        assert context.kill_switch_armed
        assert context.status == TenantStatus.KILLED


class TestTenantManager:
    """Test tenant manager."""
    
    def setup_method(self):
        reset_tenant_manager()
    
    def test_create_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test Company")
        
        assert context.name == "Test Company"
        assert context.status == TenantStatus.ACTIVE
        assert context.tenant_id is not None
        assert context.namespace.startswith("cv_")
    
    def test_create_tenant_with_isolation_level(self):
        manager = TenantManager()
        
        context = manager.create_tenant(
            "Secure Co",
            isolation_level=IsolationLevel.MAXIMUM
        )
        
        assert context.boundary.isolation_level == IsolationLevel.MAXIMUM
    
    def test_create_tenant_with_quota(self):
        manager = TenantManager()
        
        quota = ResourceQuota(max_endpoints=50)
        context = manager.create_tenant("Small Co", quota=quota)
        
        assert context.quota.max_endpoints == 50
    
    def test_get_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        retrieved = manager.get_tenant(context.tenant_id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_get_tenant_by_namespace(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        retrieved = manager.get_tenant_by_namespace(context.namespace)
        assert retrieved is not None
        assert retrieved.tenant_id == context.tenant_id
    
    def test_list_tenants(self):
        manager = TenantManager()
        
        manager.create_tenant("Tenant 1")
        manager.create_tenant("Tenant 2")
        manager.create_tenant("Tenant 3")
        
        tenants = manager.list_tenants()
        assert len(tenants) == 3
    
    def test_list_tenants_by_status(self):
        manager = TenantManager()
        
        t1 = manager.create_tenant("Active")
        t2 = manager.create_tenant("To Suspend")
        manager.suspend_tenant(t2.tenant_id)
        
        active = manager.list_tenants(TenantStatus.ACTIVE)
        suspended = manager.list_tenants(TenantStatus.SUSPENDED)
        
        assert len(active) == 1
        assert len(suspended) == 1
    
    def test_suspend_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        result = manager.suspend_tenant(context.tenant_id, "Maintenance")
        
        assert result
        assert context.status == TenantStatus.SUSPENDED
    
    def test_activate_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        manager.suspend_tenant(context.tenant_id)
        
        result = manager.activate_tenant(context.tenant_id)
        
        assert result
        assert context.status == TenantStatus.ACTIVE
    
    def test_terminate_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        result = manager.terminate_tenant(context.tenant_id)
        
        assert result
        assert context.status == TenantStatus.TERMINATED
    
    def test_kill_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        result = manager.kill_tenant(context.tenant_id, "Emergency")
        
        assert result
        assert context.status == TenantStatus.KILLED
        assert context.kill_switch_armed
    
    def test_cannot_reactivate_killed_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        manager.kill_tenant(context.tenant_id, "Emergency")
        
        result = manager.activate_tenant(context.tenant_id)
        
        assert not result
        assert context.status == TenantStatus.KILLED
    
    def test_validate_access_same_tenant(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        assert manager.validate_access(context.tenant_id, context.namespace)
    
    def test_validate_access_different_tenant(self):
        manager = TenantManager()
        
        t1 = manager.create_tenant("Tenant 1")
        t2 = manager.create_tenant("Tenant 2")
        
        # t1 trying to access t2's namespace
        assert not manager.validate_access(t1.tenant_id, t2.namespace)
    
    def test_record_usage(self):
        manager = TenantManager()
        
        context = manager.create_tenant("Test")
        
        manager.record_usage(
            context.tenant_id,
            endpoints=10,
            tests=100,
            execution_time=5.0
        )
        
        assert context.usage.endpoints_registered == 10
        assert context.usage.tests_executed == 100
        assert context.usage.total_execution_time_seconds == 5.0


class TestGlobalFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        reset_tenant_manager()
    
    def test_get_singleton(self):
        m1 = get_tenant_manager()
        m2 = get_tenant_manager()
        assert m1 is m2
    
    def test_create_tenant_function(self):
        context = create_tenant("Test Company")
        assert context.name == "Test Company"
    
    def test_get_tenant_function(self):
        context = create_tenant("Test")
        
        retrieved = get_tenant(context.tenant_id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_reset_clears_state(self):
        create_tenant("Test")
        
        reset_tenant_manager()
        
        manager = get_tenant_manager()
        assert len(manager.list_tenants()) == 0
