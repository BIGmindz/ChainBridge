"""
ChainVerify Tests — Read-Only Executor

PAC Reference: PAC-JEFFREY-P49
"""

import pytest
from dataclasses import dataclass

from core.chainverify.readonly_executor import (
    ReadOnlyExecutor,
    ExecutionMode,
    ExecutionResult,
    ExecutionBatch,
    SafetyViolation,
    ViolationType,
    SafeMethod,
    UnsafeMethod,
    SafetyBoundaryError,
    get_readonly_executor,
    reset_readonly_executor,
)


@dataclass
class MockTestCase:
    """Mock test case for testing the executor."""
    test_id: str
    endpoint_path: str
    http_method: str
    fuzz_inputs: dict = None
    chaos_dimensions: set = None
    
    def __post_init__(self):
        if self.fuzz_inputs is None:
            self.fuzz_inputs = {}
        if self.chaos_dimensions is None:
            self.chaos_dimensions = set()


class TestExecutionMode:
    """Test execution mode enumeration."""
    
    def test_all_modes_defined(self):
        expected = {"READONLY", "MOCK", "DRY_RUN"}
        actual = {m.value for m in ExecutionMode}
        assert actual == expected


class TestSafeMethods:
    """Test safe method enumeration."""
    
    def test_safe_methods(self):
        expected = {"GET", "HEAD", "OPTIONS"}
        actual = {m.value for m in SafeMethod}
        assert actual == expected


class TestUnsafeMethods:
    """Test unsafe method enumeration."""
    
    def test_unsafe_methods(self):
        expected = {"POST", "PUT", "PATCH", "DELETE"}
        actual = {m.value for m in UnsafeMethod}
        assert actual == expected


class TestViolationType:
    """Test violation type enumeration."""
    
    def test_all_types_defined(self):
        expected = {
            "UNSAFE_METHOD", "CREDENTIAL_EXPOSURE", "DATA_PERSISTENCE",
            "RATE_LIMIT_ABUSE", "UNAUTHORIZED_SCOPE"
        }
        actual = {v.value for v in ViolationType}
        assert actual == expected


class TestSafetyViolation:
    """Test safety violation dataclass."""
    
    def test_create_violation(self):
        violation = SafetyViolation(
            violation_type=ViolationType.UNSAFE_METHOD,
            endpoint="/users",
            method="POST",
            description="Blocked unsafe method"
        )
        
        assert violation.violation_type == ViolationType.UNSAFE_METHOD
        assert violation.blocked
    
    def test_to_dict(self):
        violation = SafetyViolation(
            violation_type=ViolationType.RATE_LIMIT_ABUSE,
            endpoint="/api",
            method="GET",
            description="Too many requests"
        )
        
        d = violation.to_dict()
        assert d["violation_type"] == "RATE_LIMIT_ABUSE"


class TestExecutionResult:
    """Test execution result dataclass."""
    
    def test_create_result(self):
        result = ExecutionResult(
            test_id="test_001",
            endpoint="/users",
            method="GET",
            status_code=200,
            response_time_ms=50.0,
            passed=True
        )
        
        assert result.passed
        assert result.status_code == 200
    
    def test_result_with_violation(self):
        violation = SafetyViolation(
            violation_type=ViolationType.UNSAFE_METHOD,
            endpoint="/users",
            method="POST",
            description="Blocked"
        )
        
        result = ExecutionResult(
            test_id="test_002",
            endpoint="/users",
            method="POST",
            status_code=None,
            response_time_ms=0,
            passed=False,
            safety_violations=[violation]
        )
        
        assert not result.passed
        assert len(result.safety_violations) == 1


class TestExecutionBatch:
    """Test execution batch dataclass."""
    
    def test_create_batch(self):
        batch = ExecutionBatch(
            batch_id="batch_001",
            tenant_id="tenant_123",
            total_tests=100,
            passed_tests=90,
            failed_tests=8,
            blocked_tests=2,
            total_violations=2,
            execution_time_ms=5000.0,
            results=[]
        )
        
        assert batch.pass_rate == 90.0
        assert batch.safety_compliance == 98.0
    
    def test_empty_batch(self):
        batch = ExecutionBatch(
            batch_id="empty",
            tenant_id="t",
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            blocked_tests=0,
            total_violations=0,
            execution_time_ms=0,
            results=[]
        )
        
        assert batch.pass_rate == 0.0
        assert batch.safety_compliance == 100.0


class TestReadOnlyExecutor:
    """Test read-only executor."""
    
    def setup_method(self):
        reset_readonly_executor()
    
    def test_execute_safe_method(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY)
        
        test = MockTestCase(
            test_id="test_001",
            endpoint_path="/users",
            http_method="GET"
        )
        
        result = executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        assert result.passed
        assert len(result.safety_violations) == 0
    
    def test_block_unsafe_method_readonly(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY)
        
        test = MockTestCase(
            test_id="test_002",
            endpoint_path="/users",
            http_method="POST"
        )
        
        result = executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        assert not result.passed
        assert len(result.safety_violations) == 1
        assert result.safety_violations[0].violation_type == ViolationType.UNSAFE_METHOD
    
    def test_mock_unsafe_method(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.MOCK)
        
        test = MockTestCase(
            test_id="test_003",
            endpoint_path="/users",
            http_method="DELETE"
        )
        
        result = executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        # In mock mode, unsafe methods are simulated but flagged
        assert result.passed  # Mock succeeds
        assert result.execution_mode == ExecutionMode.MOCK
    
    def test_dry_run_mode(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.DRY_RUN)
        
        test = MockTestCase(
            test_id="test_004",
            endpoint_path="/users",
            http_method="GET"
        )
        
        result = executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        assert result.passed
        assert result.status_code is None  # No actual request
        assert result.execution_mode == ExecutionMode.DRY_RUN
    
    def test_rate_limit_enforcement(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY, rate_limit=5)
        
        results = []
        for i in range(10):
            test = MockTestCase(
                test_id=f"test_{i:03d}",
                endpoint_path="/users",
                http_method="GET"
            )
            result = executor.execute_test(test, "tenant_1", "https://api.test.com")
            results.append(result)
        
        # First 5 should pass, rest should be blocked
        passed = sum(1 for r in results if r.passed)
        blocked = sum(1 for r in results if r.safety_violations)
        
        assert passed == 5
        assert blocked == 5
    
    def test_rate_limit_per_tenant(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY, rate_limit=3)
        
        test = MockTestCase(
            test_id="test_001",
            endpoint_path="/users",
            http_method="GET"
        )
        
        # Tenant 1 uses their quota
        for _ in range(3):
            executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        # Tenant 2 should have their own quota
        result = executor.execute_test(test, "tenant_2", "https://api.test.com")
        
        assert result.passed
    
    def test_rate_limit_reset(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY, rate_limit=2)
        
        test = MockTestCase(
            test_id="test_001",
            endpoint_path="/users",
            http_method="GET"
        )
        
        # Use quota
        executor.execute_test(test, "tenant_1", "https://api.test.com")
        executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        # Should be blocked
        result = executor.execute_test(test, "tenant_1", "https://api.test.com")
        assert not result.passed
        
        # Reset limits
        executor.reset_rate_limits()
        
        # Should work again
        result = executor.execute_test(test, "tenant_1", "https://api.test.com")
        assert result.passed
    
    def test_execute_batch(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.MOCK)
        
        tests = [
            MockTestCase("t1", "/users", "GET"),
            MockTestCase("t2", "/users", "POST"),
            MockTestCase("t3", "/items", "GET"),
        ]
        
        batch = executor.execute_batch(tests, "tenant_1", "https://api.test.com")
        
        assert batch.total_tests == 3
        assert batch.batch_id is not None
        assert batch.completed_at is not None
    
    def test_get_violations(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY)
        
        tests = [
            MockTestCase("t1", "/users", "POST"),
            MockTestCase("t2", "/users", "DELETE"),
        ]
        
        for test in tests:
            executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        violations = executor.get_violations()
        
        assert len(violations) == 2
        assert all(v.violation_type == ViolationType.UNSAFE_METHOD for v in violations)
    
    def test_clear_violations(self):
        executor = ReadOnlyExecutor(mode=ExecutionMode.READONLY)
        
        test = MockTestCase("t1", "/users", "POST")
        executor.execute_test(test, "tenant_1", "https://api.test.com")
        
        assert len(executor.get_violations()) == 1
        
        executor.clear_violations()
        
        assert len(executor.get_violations()) == 0


class TestGlobalFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        reset_readonly_executor()
    
    def test_get_singleton(self):
        e1 = get_readonly_executor()
        e2 = get_readonly_executor()
        assert e1 is e2
    
    def test_reset_clears_state(self):
        executor = get_readonly_executor()
        executor._request_counts["test"] = 100
        
        reset_readonly_executor()
        
        new_executor = get_readonly_executor()
        assert len(new_executor._request_counts) == 0
