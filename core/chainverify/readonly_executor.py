"""
Read-Only Executor — Safe Test Execution with Mutation Protection

PAC Reference: PAC-JEFFREY-P49
Agent: SAM (GID-06)

Executes tests against client APIs with HARD guarantees of read-only behavior.
No writes, no mutations, no state changes to client systems.

INVARIANTS (HARD STOPS):
- ❌ NO POST/PUT/PATCH/DELETE to production endpoints
- ❌ NO credential storage
- ❌ NO data persistence from responses
- ❌ NO side effects on client systems

This is the SAFETY BOUNDARY for ChainVerify.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import hashlib


class ExecutionMode(Enum):
    """Execution safety modes."""
    READONLY = "READONLY"      # Only GET/HEAD/OPTIONS
    MOCK = "MOCK"              # Simulated execution
    DRY_RUN = "DRY_RUN"        # Validate without executing


class SafeMethod(Enum):
    """HTTP methods considered safe (read-only)."""
    GET = "GET"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class UnsafeMethod(Enum):
    """HTTP methods that mutate state (BLOCKED)."""
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ViolationType(Enum):
    """Types of safety violations."""
    UNSAFE_METHOD = "UNSAFE_METHOD"
    CREDENTIAL_EXPOSURE = "CREDENTIAL_EXPOSURE"
    DATA_PERSISTENCE = "DATA_PERSISTENCE"
    RATE_LIMIT_ABUSE = "RATE_LIMIT_ABUSE"
    UNAUTHORIZED_SCOPE = "UNAUTHORIZED_SCOPE"


@dataclass
class SafetyViolation:
    """Record of a safety boundary violation."""
    violation_type: ViolationType
    endpoint: str
    method: str
    description: str
    blocked: bool = True  # Was the violation blocked?
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_type": self.violation_type.value,
            "endpoint": self.endpoint,
            "method": self.method,
            "description": self.description,
            "blocked": self.blocked,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ExecutionResult:
    """Result of a single test execution."""
    test_id: str
    endpoint: str
    method: str
    status_code: int | None
    response_time_ms: float
    passed: bool
    error_message: str = ""
    execution_mode: ExecutionMode = ExecutionMode.READONLY
    safety_violations: list[SafetyViolation] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Response metadata (NOT the actual response data)
    response_size_bytes: int = 0
    response_content_type: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "passed": self.passed,
            "error_message": self.error_message,
            "execution_mode": self.execution_mode.value,
            "safety_violations": [v.to_dict() for v in self.safety_violations],
            "timestamp": self.timestamp.isoformat(),
            "response_size_bytes": self.response_size_bytes,
            "response_content_type": self.response_content_type,
        }


@dataclass
class ExecutionBatch:
    """Batch of execution results."""
    batch_id: str
    tenant_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int
    total_violations: int
    execution_time_ms: float
    results: list[ExecutionResult]
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def safety_compliance(self) -> float:
        """Percentage of tests that didn't trigger violations."""
        if self.total_tests == 0:
            return 100.0
        return ((self.total_tests - self.total_violations) / self.total_tests) * 100
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "tenant_id": self.tenant_id,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "blocked_tests": self.blocked_tests,
            "total_violations": self.total_violations,
            "execution_time_ms": self.execution_time_ms,
            "pass_rate": self.pass_rate,
            "safety_compliance": self.safety_compliance,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SafetyBoundaryError(Exception):
    """Raised when a safety boundary is violated."""
    pass


class ReadOnlyExecutor:
    """
    Executes tests with read-only safety guarantees.
    
    HARD INVARIANTS:
    1. Only safe HTTP methods (GET, HEAD, OPTIONS) to production
    2. No credential storage
    3. No response data persistence
    4. Rate limiting enforced
    
    All unsafe methods are:
    - BLOCKED in READONLY mode
    - SIMULATED in MOCK mode
    - SKIPPED in DRY_RUN mode
    """
    
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    # Rate limit: max requests per minute per tenant
    DEFAULT_RATE_LIMIT = 100
    
    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.READONLY,
        rate_limit: int = DEFAULT_RATE_LIMIT,
    ):
        self.mode = mode
        self.rate_limit = rate_limit
        self._violations: list[SafetyViolation] = []
        self._request_counts: dict[str, int] = {}  # tenant_id -> count
    
    def execute_test(
        self,
        test_case: Any,  # FuzzTestCase
        tenant_id: str,
        base_url: str,
    ) -> ExecutionResult:
        """
        Execute a single test case with safety guarantees.
        
        Args:
            test_case: The test to execute
            tenant_id: Tenant performing the execution
            base_url: Base URL for the API
            
        Returns:
            ExecutionResult with pass/fail and any violations
        """
        method = test_case.http_method
        endpoint = test_case.endpoint_path
        
        # Check rate limit
        if not self._check_rate_limit(tenant_id):
            return self._create_blocked_result(
                test_case,
                ViolationType.RATE_LIMIT_ABUSE,
                "Rate limit exceeded"
            )
        
        # Safety check: is this method allowed?
        if method.upper() in self.UNSAFE_METHODS:
            violation = SafetyViolation(
                violation_type=ViolationType.UNSAFE_METHOD,
                endpoint=endpoint,
                method=method,
                description=f"Unsafe method {method} blocked by read-only executor",
            )
            self._violations.append(violation)
            
            if self.mode == ExecutionMode.READONLY:
                return self._create_blocked_result(
                    test_case,
                    ViolationType.UNSAFE_METHOD,
                    f"Method {method} is not allowed in read-only mode"
                )
            elif self.mode == ExecutionMode.MOCK:
                return self._mock_execution(test_case, violation)
            else:  # DRY_RUN
                return self._dry_run_execution(test_case, violation)
        
        # Safe method - execute based on mode
        if self.mode == ExecutionMode.READONLY:
            return self._safe_execution(test_case, base_url)
        elif self.mode == ExecutionMode.MOCK:
            return self._mock_execution(test_case)
        else:
            return self._dry_run_execution(test_case)
    
    def execute_batch(
        self,
        test_cases: list[Any],
        tenant_id: str,
        base_url: str,
    ) -> ExecutionBatch:
        """Execute a batch of tests with safety guarantees."""
        started_at = datetime.utcnow()
        results = []
        passed = 0
        failed = 0
        blocked = 0
        violations = 0
        
        for test_case in test_cases:
            result = self.execute_test(test_case, tenant_id, base_url)
            results.append(result)
            
            if result.passed:
                passed += 1
            elif result.safety_violations:
                blocked += 1
                violations += len(result.safety_violations)
            else:
                failed += 1
        
        completed_at = datetime.utcnow()
        execution_time = (completed_at - started_at).total_seconds() * 1000
        
        batch_id = hashlib.sha256(
            f"{tenant_id}:{started_at.isoformat()}:{len(results)}".encode()
        ).hexdigest()[:12]
        
        return ExecutionBatch(
            batch_id=batch_id,
            tenant_id=tenant_id,
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            blocked_tests=blocked,
            total_violations=violations,
            execution_time_ms=execution_time,
            results=results,
            started_at=started_at,
            completed_at=completed_at,
        )
    
    def get_violations(self) -> list[SafetyViolation]:
        """Get all recorded violations."""
        return self._violations.copy()
    
    def clear_violations(self) -> None:
        """Clear violation history."""
        self._violations = []
    
    def _check_rate_limit(self, tenant_id: str) -> bool:
        """Check if tenant is within rate limit."""
        count = self._request_counts.get(tenant_id, 0)
        if count >= self.rate_limit:
            return False
        self._request_counts[tenant_id] = count + 1
        return True
    
    def reset_rate_limits(self) -> None:
        """Reset rate limit counters (call periodically)."""
        self._request_counts = {}
    
    def _safe_execution(
        self,
        test_case: Any,
        base_url: str,
    ) -> ExecutionResult:
        """
        Execute a safe (read-only) request.
        
        In production, this would make actual HTTP requests.
        For now, we simulate the execution.
        """
        # SIMULATION: In production, would make actual GET request
        # For safety, we simulate the response
        return ExecutionResult(
            test_id=test_case.test_id,
            endpoint=test_case.endpoint_path,
            method=test_case.http_method,
            status_code=200,  # Simulated
            response_time_ms=50.0,  # Simulated
            passed=True,
            execution_mode=ExecutionMode.READONLY,
            response_size_bytes=1024,
            response_content_type="application/json",
        )
    
    def _mock_execution(
        self,
        test_case: Any,
        violation: SafetyViolation | None = None,
    ) -> ExecutionResult:
        """Mock execution without actual HTTP request."""
        violations = [violation] if violation else []
        
        return ExecutionResult(
            test_id=test_case.test_id,
            endpoint=test_case.endpoint_path,
            method=test_case.http_method,
            status_code=200,  # Mocked
            response_time_ms=1.0,  # Fast mock
            passed=True,
            execution_mode=ExecutionMode.MOCK,
            safety_violations=violations,
        )
    
    def _dry_run_execution(
        self,
        test_case: Any,
        violation: SafetyViolation | None = None,
    ) -> ExecutionResult:
        """Dry run - validate without executing."""
        violations = [violation] if violation else []
        
        return ExecutionResult(
            test_id=test_case.test_id,
            endpoint=test_case.endpoint_path,
            method=test_case.http_method,
            status_code=None,  # No actual request
            response_time_ms=0.0,
            passed=True,
            execution_mode=ExecutionMode.DRY_RUN,
            safety_violations=violations,
        )
    
    def _create_blocked_result(
        self,
        test_case: Any,
        violation_type: ViolationType,
        message: str,
    ) -> ExecutionResult:
        """Create a result for a blocked test."""
        violation = SafetyViolation(
            violation_type=violation_type,
            endpoint=test_case.endpoint_path,
            method=test_case.http_method,
            description=message,
            blocked=True,
        )
        
        return ExecutionResult(
            test_id=test_case.test_id,
            endpoint=test_case.endpoint_path,
            method=test_case.http_method,
            status_code=None,
            response_time_ms=0.0,
            passed=False,
            error_message=message,
            execution_mode=self.mode,
            safety_violations=[violation],
        )


# Module-level singleton
_readonly_executor: ReadOnlyExecutor | None = None


def get_readonly_executor(mode: ExecutionMode = ExecutionMode.READONLY) -> ReadOnlyExecutor:
    """Get the singleton executor."""
    global _readonly_executor
    if _readonly_executor is None:
        _readonly_executor = ReadOnlyExecutor(mode)
    return _readonly_executor


def reset_readonly_executor() -> None:
    """Reset the singleton (for testing)."""
    global _readonly_executor
    _readonly_executor = None


def execute_readonly(
    test_case: Any,
    tenant_id: str,
    base_url: str,
) -> ExecutionResult:
    """Convenience function for read-only execution."""
    return get_readonly_executor().execute_test(test_case, tenant_id, base_url)
