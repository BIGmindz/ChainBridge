"""
Governance Red-Team Engine v2 — Adversarial PAC/WRAP/BER Mutation Tests.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-06 (Sam) — SECURITY
Deliverable: Governance Red-Team Engine v2

Features:
- Adversarial mutation testing for PAC/WRAP/BER artifacts
- Invariant violation detection
- Security boundary testing
- Fuzzing and property-based testing
- Attack vector identification

This engine proactively identifies governance vulnerabilities through
adversarial testing techniques before they can be exploited.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar


# =============================================================================
# CONSTANTS
# =============================================================================

ENGINE_VERSION = "2.0.0"
DEFAULT_MUTATION_COUNT = 100
DEFAULT_FUZZ_ITERATIONS = 50


# =============================================================================
# ENUMS
# =============================================================================

class ArtifactType(Enum):
    """Governance artifact types."""
    PAC = "PAC"
    WRAP = "WRAP"
    BER = "BER"
    PDO = "PDO"
    CLOSURE = "CLOSURE"


class MutationType(Enum):
    """Types of mutations applied."""
    FIELD_REMOVAL = "FIELD_REMOVAL"
    FIELD_CORRUPTION = "FIELD_CORRUPTION"
    TYPE_CHANGE = "TYPE_CHANGE"
    HASH_TAMPERING = "HASH_TAMPERING"
    TIMESTAMP_MANIPULATION = "TIMESTAMP_MANIPULATION"
    ID_COLLISION = "ID_COLLISION"
    STATE_INJECTION = "STATE_INJECTION"
    OVERFLOW = "OVERFLOW"
    EMPTY_VALUE = "EMPTY_VALUE"
    INVALID_REFERENCE = "INVALID_REFERENCE"


class VulnerabilityLevel(Enum):
    """Severity levels for discovered vulnerabilities."""
    CRITICAL = "CRITICAL"  # Immediate action required
    HIGH = "HIGH"          # Serious security issue
    MEDIUM = "MEDIUM"      # Moderate risk
    LOW = "LOW"            # Minor issue
    INFO = "INFO"          # Informational


class AttackVector(Enum):
    """Attack vector categories."""
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    DATA_INTEGRITY = "DATA_INTEGRITY"
    STATE_MANIPULATION = "STATE_MANIPULATION"
    REPLAY = "REPLAY"
    INJECTION = "INJECTION"
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"


class TestResult(Enum):
    """Mutation test results."""
    PASSED = "PASSED"      # System correctly rejected mutation
    FAILED = "FAILED"      # System accepted invalid mutation
    ERROR = "ERROR"        # Unexpected error during test
    TIMEOUT = "TIMEOUT"    # Test timed out


# =============================================================================
# EXCEPTIONS
# =============================================================================

class RedTeamError(Exception):
    """Base exception for red team errors."""
    pass


class MutationError(RedTeamError):
    """Raised when mutation operation fails."""
    
    def __init__(self, mutation_type: MutationType, reason: str) -> None:
        self.mutation_type = mutation_type
        self.reason = reason
        super().__init__(f"Mutation {mutation_type.value} failed: {reason}")


class VulnerabilityFound(RedTeamError):
    """Raised when critical vulnerability discovered."""
    
    def __init__(self, vulnerability_id: str, description: str) -> None:
        self.vulnerability_id = vulnerability_id
        self.description = description
        super().__init__(f"VULNERABILITY {vulnerability_id}: {description}")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Mutation:
    """Represents a single mutation operation."""
    
    mutation_id: str
    mutation_type: MutationType
    target_field: str
    original_value: Any
    mutated_value: Any
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize mutation."""
        return {
            "mutation_id": self.mutation_id,
            "mutation_type": self.mutation_type.value,
            "target_field": self.target_field,
            "description": self.description,
        }


@dataclass
class MutationTestCase:
    """A test case with mutation applied."""
    
    test_id: str
    artifact_type: ArtifactType
    original_artifact: Dict[str, Any]
    mutated_artifact: Dict[str, Any]
    mutation: Mutation
    expected_result: TestResult
    attack_vector: AttackVector
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize test case."""
        return {
            "test_id": self.test_id,
            "artifact_type": self.artifact_type.value,
            "mutation": self.mutation.to_dict(),
            "expected_result": self.expected_result.value,
            "attack_vector": self.attack_vector.value,
        }


@dataclass
class TestExecution:
    """Result of executing a mutation test."""
    
    test_case: MutationTestCase
    actual_result: TestResult
    execution_time_ms: float
    error_message: Optional[str] = None
    detected_by: Optional[str] = None  # Component that detected mutation
    
    @property
    def passed(self) -> bool:
        """Check if test passed (mutation correctly rejected)."""
        return (
            self.actual_result == TestResult.PASSED
            or self.actual_result == self.test_case.expected_result
        )
    
    @property
    def is_vulnerability(self) -> bool:
        """Check if result indicates vulnerability."""
        return (
            self.test_case.expected_result == TestResult.PASSED
            and self.actual_result == TestResult.FAILED
        )


@dataclass
class Vulnerability:
    """A discovered vulnerability."""
    
    vulnerability_id: str
    level: VulnerabilityLevel
    attack_vector: AttackVector
    artifact_type: ArtifactType
    mutation_type: MutationType
    description: str
    reproduction_steps: List[str]
    affected_fields: List[str]
    recommendation: str
    discovered_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize vulnerability."""
        return {
            "vulnerability_id": self.vulnerability_id,
            "level": self.level.value,
            "attack_vector": self.attack_vector.value,
            "artifact_type": self.artifact_type.value,
            "mutation_type": self.mutation_type.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "discovered_at": self.discovered_at,
        }


@dataclass
class RedTeamReport:
    """Complete red team assessment report."""
    
    report_id: str
    generated_at: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    vulnerabilities: List[Vulnerability]
    coverage_by_artifact: Dict[ArtifactType, int]
    coverage_by_mutation: Dict[MutationType, int]
    execution_time_seconds: float
    
    @property
    def pass_rate(self) -> float:
        """Calculate test pass rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def vulnerability_count(self) -> int:
        """Count vulnerabilities."""
        return len(self.vulnerabilities)
    
    @property
    def critical_count(self) -> int:
        """Count critical vulnerabilities."""
        return sum(1 for v in self.vulnerabilities if v.level == VulnerabilityLevel.CRITICAL)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize report."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate": f"{self.pass_rate:.1%}",
            "vulnerability_count": self.vulnerability_count,
            "critical_count": self.critical_count,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }


# =============================================================================
# MUTATION GENERATORS
# =============================================================================

class MutationGenerator:
    """Generates mutations for governance artifacts."""
    
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
    
    def generate_field_removal(
        self,
        artifact: Dict[str, Any],
        field: str,
    ) -> Mutation:
        """Generate field removal mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(field)
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.FIELD_REMOVAL,
            target_field=field,
            original_value=original,
            mutated_value=None,
            description=f"Remove required field '{field}'",
        )
    
    def generate_type_change(
        self,
        artifact: Dict[str, Any],
        field: str,
    ) -> Mutation:
        """Generate type change mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(field)
        
        # Change type to something different
        if isinstance(original, str):
            mutated = 12345
        elif isinstance(original, int):
            mutated = "invalid_string"
        elif isinstance(original, bool):
            mutated = "not_a_bool"
        elif isinstance(original, list):
            mutated = {"invalid": "object"}
        else:
            mutated = ["unexpected", "array"]
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.TYPE_CHANGE,
            target_field=field,
            original_value=original,
            mutated_value=mutated,
            description=f"Change type of '{field}' from {type(original).__name__}",
        )
    
    def generate_hash_tampering(
        self,
        artifact: Dict[str, Any],
        hash_field: str = "hash",
    ) -> Mutation:
        """Generate hash tampering mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(hash_field, "")
        
        # Generate invalid hash
        mutated = hashlib.sha256(b"tampered").hexdigest()
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.HASH_TAMPERING,
            target_field=hash_field,
            original_value=original,
            mutated_value=mutated,
            description=f"Tamper with hash field '{hash_field}'",
        )
    
    def generate_timestamp_manipulation(
        self,
        artifact: Dict[str, Any],
        timestamp_field: str = "timestamp",
    ) -> Mutation:
        """Generate timestamp manipulation mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(timestamp_field)
        
        # Set timestamp to future or past
        future = datetime.now(timezone.utc) + timedelta(days=365)
        mutated = future.isoformat()
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.TIMESTAMP_MANIPULATION,
            target_field=timestamp_field,
            original_value=original,
            mutated_value=mutated,
            description=f"Set '{timestamp_field}' to future date",
        )
    
    def generate_id_collision(
        self,
        artifact: Dict[str, Any],
        id_field: str = "id",
        collision_id: str = "COLLISION-001",
    ) -> Mutation:
        """Generate ID collision mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(id_field)
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.ID_COLLISION,
            target_field=id_field,
            original_value=original,
            mutated_value=collision_id,
            description=f"Create ID collision with '{collision_id}'",
        )
    
    def generate_state_injection(
        self,
        artifact: Dict[str, Any],
        state_field: str = "state",
        injected_state: str = "COMPLETED",
    ) -> Mutation:
        """Generate state injection mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(state_field)
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.STATE_INJECTION,
            target_field=state_field,
            original_value=original,
            mutated_value=injected_state,
            description=f"Inject state '{injected_state}' into '{state_field}'",
        )
    
    def generate_overflow(
        self,
        artifact: Dict[str, Any],
        field: str,
    ) -> Mutation:
        """Generate overflow mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(field)
        
        # Generate oversized value
        mutated = "A" * 1000000  # 1MB string
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.OVERFLOW,
            target_field=field,
            original_value=original,
            mutated_value=mutated,
            description=f"Overflow field '{field}' with large value",
        )
    
    def generate_empty_value(
        self,
        artifact: Dict[str, Any],
        field: str,
    ) -> Mutation:
        """Generate empty value mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(field)
        
        # Determine empty value based on type
        if isinstance(original, str):
            mutated = ""
        elif isinstance(original, list):
            mutated = []
        elif isinstance(original, dict):
            mutated = {}
        else:
            mutated = None
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.EMPTY_VALUE,
            target_field=field,
            original_value=original,
            mutated_value=mutated,
            description=f"Set '{field}' to empty value",
        )
    
    def generate_invalid_reference(
        self,
        artifact: Dict[str, Any],
        ref_field: str,
    ) -> Mutation:
        """Generate invalid reference mutation."""
        mutation_id = f"MUT-{uuid.uuid4().hex[:8].upper()}"
        original = artifact.get(ref_field)
        
        mutated = f"INVALID-{uuid.uuid4().hex[:8].upper()}"
        
        return Mutation(
            mutation_id=mutation_id,
            mutation_type=MutationType.INVALID_REFERENCE,
            target_field=ref_field,
            original_value=original,
            mutated_value=mutated,
            description=f"Set '{ref_field}' to nonexistent reference",
        )
    
    def generate_random_mutation(
        self,
        artifact: Dict[str, Any],
    ) -> Mutation:
        """Generate a random mutation."""
        fields = list(artifact.keys())
        if not fields:
            raise MutationError(
                MutationType.FIELD_CORRUPTION,
                "No fields to mutate"
            )
        
        field = self._rng.choice(fields)
        mutation_type = self._rng.choice(list(MutationType))
        
        generators = {
            MutationType.FIELD_REMOVAL: self.generate_field_removal,
            MutationType.TYPE_CHANGE: self.generate_type_change,
            MutationType.EMPTY_VALUE: self.generate_empty_value,
            MutationType.OVERFLOW: self.generate_overflow,
        }
        
        generator = generators.get(mutation_type, self.generate_field_removal)
        return generator(artifact, field)


# =============================================================================
# RED TEAM ENGINE
# =============================================================================

class RedTeamEngine:
    """
    Governance Red-Team Engine for adversarial testing.
    """
    
    def __init__(self, seed: Optional[int] = None) -> None:
        self._generator = MutationGenerator(seed)
        self._test_cases: List[MutationTestCase] = []
        self._executions: List[TestExecution] = []
        self._vulnerabilities: List[Vulnerability] = []
    
    # -------------------------------------------------------------------------
    # TEST CASE GENERATION
    # -------------------------------------------------------------------------
    
    def generate_test_cases(
        self,
        artifact: Dict[str, Any],
        artifact_type: ArtifactType,
        mutation_count: int = DEFAULT_MUTATION_COUNT,
    ) -> List[MutationTestCase]:
        """Generate mutation test cases for an artifact."""
        test_cases = []
        
        # Generate systematic mutations for each field
        for field in artifact.keys():
            # Field removal test
            mutation = self._generator.generate_field_removal(artifact, field)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.DATA_INTEGRITY,
            ))
            
            # Type change test
            mutation = self._generator.generate_type_change(artifact, field)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.DATA_INTEGRITY,
            ))
            
            # Empty value test
            mutation = self._generator.generate_empty_value(artifact, field)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.DATA_INTEGRITY,
            ))
        
        # Generate targeted mutations
        if "hash" in artifact or "content_hash" in artifact:
            hash_field = "hash" if "hash" in artifact else "content_hash"
            mutation = self._generator.generate_hash_tampering(artifact, hash_field)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.DATA_INTEGRITY,
            ))
        
        if "timestamp" in artifact or "created_at" in artifact:
            ts_field = "timestamp" if "timestamp" in artifact else "created_at"
            mutation = self._generator.generate_timestamp_manipulation(artifact, ts_field)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.REPLAY,
            ))
        
        if "state" in artifact or "status" in artifact:
            state_field = "state" if "state" in artifact else "status"
            mutation = self._generator.generate_state_injection(artifact, state_field)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.STATE_MANIPULATION,
            ))
        
        # Add random mutations to reach mutation_count
        while len(test_cases) < mutation_count:
            mutation = self._generator.generate_random_mutation(artifact)
            test_cases.append(self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.DATA_INTEGRITY,
            ))
        
        self._test_cases.extend(test_cases[:mutation_count])
        return test_cases[:mutation_count]
    
    def _create_test_case(
        self,
        artifact: Dict[str, Any],
        artifact_type: ArtifactType,
        mutation: Mutation,
        attack_vector: AttackVector,
    ) -> MutationTestCase:
        """Create a test case from mutation."""
        test_id = f"TC-{uuid.uuid4().hex[:8].upper()}"
        
        # Apply mutation to create mutated artifact
        mutated = copy.deepcopy(artifact)
        if mutation.mutated_value is None:
            mutated.pop(mutation.target_field, None)
        else:
            mutated[mutation.target_field] = mutation.mutated_value
        
        return MutationTestCase(
            test_id=test_id,
            artifact_type=artifact_type,
            original_artifact=artifact,
            mutated_artifact=mutated,
            mutation=mutation,
            expected_result=TestResult.PASSED,  # System should reject
            attack_vector=attack_vector,
        )
    
    # -------------------------------------------------------------------------
    # TEST EXECUTION
    # -------------------------------------------------------------------------
    
    def execute_tests(
        self,
        validator: Callable[[Dict[str, Any], ArtifactType], Tuple[bool, str]],
    ) -> List[TestExecution]:
        """
        Execute all test cases against a validator.
        
        Args:
            validator: Function that validates artifact, returns (valid, message)
        
        Returns:
            List of test executions
        """
        executions = []
        
        for test_case in self._test_cases:
            start_time = datetime.now()
            
            try:
                valid, message = validator(
                    test_case.mutated_artifact,
                    test_case.artifact_type,
                )
                
                # If validator accepted mutated artifact, it's a failure
                actual_result = TestResult.FAILED if valid else TestResult.PASSED
                detected_by = None if valid else message
                error_msg = None
                
            except Exception as e:
                actual_result = TestResult.ERROR
                detected_by = None
                error_msg = str(e)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            execution = TestExecution(
                test_case=test_case,
                actual_result=actual_result,
                execution_time_ms=execution_time,
                error_message=error_msg,
                detected_by=detected_by,
            )
            
            executions.append(execution)
            
            # Check for vulnerability
            if execution.is_vulnerability:
                self._record_vulnerability(execution)
        
        self._executions.extend(executions)
        return executions
    
    def _record_vulnerability(self, execution: TestExecution) -> None:
        """Record a discovered vulnerability."""
        test_case = execution.test_case
        mutation = test_case.mutation
        
        # Determine severity
        if mutation.mutation_type in (
            MutationType.HASH_TAMPERING,
            MutationType.STATE_INJECTION,
        ):
            level = VulnerabilityLevel.CRITICAL
        elif mutation.mutation_type in (
            MutationType.FIELD_REMOVAL,
            MutationType.INVALID_REFERENCE,
        ):
            level = VulnerabilityLevel.HIGH
        else:
            level = VulnerabilityLevel.MEDIUM
        
        vuln = Vulnerability(
            vulnerability_id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
            level=level,
            attack_vector=test_case.attack_vector,
            artifact_type=test_case.artifact_type,
            mutation_type=mutation.mutation_type,
            description=f"System accepted {mutation.mutation_type.value} on '{mutation.target_field}'",
            reproduction_steps=[
                f"1. Create valid {test_case.artifact_type.value}",
                f"2. Apply mutation: {mutation.description}",
                f"3. Submit mutated artifact",
                f"4. Observe: artifact accepted without error",
            ],
            affected_fields=[mutation.target_field],
            recommendation=f"Add validation for {mutation.target_field} field",
            discovered_at=datetime.now(timezone.utc).isoformat(),
        )
        
        self._vulnerabilities.append(vuln)
    
    # -------------------------------------------------------------------------
    # FUZZING
    # -------------------------------------------------------------------------
    
    def fuzz_artifact(
        self,
        artifact: Dict[str, Any],
        artifact_type: ArtifactType,
        validator: Callable[[Dict[str, Any], ArtifactType], Tuple[bool, str]],
        iterations: int = DEFAULT_FUZZ_ITERATIONS,
    ) -> List[TestExecution]:
        """
        Perform fuzzing on an artifact.
        
        Args:
            artifact: Base artifact to fuzz
            artifact_type: Type of artifact
            validator: Validation function
            iterations: Number of fuzz iterations
        
        Returns:
            List of test executions
        """
        executions = []
        
        for _ in range(iterations):
            # Generate random mutation
            mutation = self._generator.generate_random_mutation(artifact)
            
            test_case = self._create_test_case(
                artifact, artifact_type, mutation,
                AttackVector.INJECTION,
            )
            
            start_time = datetime.now()
            
            try:
                valid, message = validator(
                    test_case.mutated_artifact,
                    artifact_type,
                )
                actual_result = TestResult.FAILED if valid else TestResult.PASSED
                detected_by = None if valid else message
                error_msg = None
            except Exception as e:
                actual_result = TestResult.ERROR
                detected_by = None
                error_msg = str(e)
            
            end_time = datetime.now()
            
            execution = TestExecution(
                test_case=test_case,
                actual_result=actual_result,
                execution_time_ms=(end_time - start_time).total_seconds() * 1000,
                error_message=error_msg,
                detected_by=detected_by,
            )
            
            executions.append(execution)
            
            if execution.is_vulnerability:
                self._record_vulnerability(execution)
        
        return executions
    
    # -------------------------------------------------------------------------
    # REPORTING
    # -------------------------------------------------------------------------
    
    def generate_report(self) -> RedTeamReport:
        """Generate comprehensive red team report."""
        # Calculate coverage
        coverage_by_artifact: Dict[ArtifactType, int] = {}
        coverage_by_mutation: Dict[MutationType, int] = {}
        
        for test_case in self._test_cases:
            coverage_by_artifact[test_case.artifact_type] = (
                coverage_by_artifact.get(test_case.artifact_type, 0) + 1
            )
            coverage_by_mutation[test_case.mutation.mutation_type] = (
                coverage_by_mutation.get(test_case.mutation.mutation_type, 0) + 1
            )
        
        passed = sum(1 for e in self._executions if e.passed)
        failed = len(self._executions) - passed
        
        total_time = sum(e.execution_time_ms for e in self._executions) / 1000
        
        return RedTeamReport(
            report_id=f"RT-{uuid.uuid4().hex[:8].upper()}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_tests=len(self._executions),
            passed_tests=passed,
            failed_tests=failed,
            vulnerabilities=list(self._vulnerabilities),
            coverage_by_artifact=coverage_by_artifact,
            coverage_by_mutation=coverage_by_mutation,
            execution_time_seconds=total_time,
        )
    
    def get_vulnerabilities(
        self,
        min_level: VulnerabilityLevel = VulnerabilityLevel.LOW,
    ) -> List[Vulnerability]:
        """Get vulnerabilities at or above minimum level."""
        level_order = {
            VulnerabilityLevel.INFO: 0,
            VulnerabilityLevel.LOW: 1,
            VulnerabilityLevel.MEDIUM: 2,
            VulnerabilityLevel.HIGH: 3,
            VulnerabilityLevel.CRITICAL: 4,
        }
        
        min_order = level_order[min_level]
        return [
            v for v in self._vulnerabilities
            if level_order[v.level] >= min_order
        ]
    
    # -------------------------------------------------------------------------
    # RESET
    # -------------------------------------------------------------------------
    
    def reset(self) -> None:
        """Reset engine state."""
        self._test_cases.clear()
        self._executions.clear()
        self._vulnerabilities.clear()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_red_team_engine(seed: Optional[int] = None) -> RedTeamEngine:
    """Create a red team engine."""
    return RedTeamEngine(seed=seed)


def create_sample_pac() -> Dict[str, Any]:
    """Create a sample PAC artifact for testing."""
    return {
        "pac_id": f"PAC-{uuid.uuid4().hex[:8].upper()}",
        "title": "Test PAC",
        "directive": "Execute test task",
        "mode": "DRAFT",
        "priority": "STANDARD",
        "state": "PENDING",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash": hashlib.sha256(b"test").hexdigest(),
        "agents": ["GID-01"],
    }


def create_sample_wrap() -> Dict[str, Any]:
    """Create a sample WRAP artifact for testing."""
    return {
        "wrap_id": f"WRAP-{uuid.uuid4().hex[:8].upper()}",
        "pac_id": f"PAC-{uuid.uuid4().hex[:8].upper()}",
        "agent_id": "GID-01",
        "status": "COMPLETE",
        "deliverables": ["file.py"],
        "test_count": 50,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": hashlib.sha256(b"wrap").hexdigest(),
    }


def create_sample_ber() -> Dict[str, Any]:
    """Create a sample BER artifact for testing."""
    return {
        "ber_id": f"BER-{uuid.uuid4().hex[:8].upper()}",
        "pac_id": f"PAC-{uuid.uuid4().hex[:8].upper()}",
        "wrap_ids": [f"WRAP-{uuid.uuid4().hex[:8].upper()}"],
        "status": "ISSUED",
        "closure_id": f"CL-{uuid.uuid4().hex[:8].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash": hashlib.sha256(b"ber").hexdigest(),
    }


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version
    "ENGINE_VERSION",
    # Enums
    "ArtifactType",
    "MutationType",
    "VulnerabilityLevel",
    "AttackVector",
    "TestResult",
    # Exceptions
    "RedTeamError",
    "MutationError",
    "VulnerabilityFound",
    # Data Classes
    "Mutation",
    "MutationTestCase",
    "TestExecution",
    "Vulnerability",
    "RedTeamReport",
    # Core Classes
    "MutationGenerator",
    "RedTeamEngine",
    # Factory Functions
    "create_red_team_engine",
    "create_sample_pac",
    "create_sample_wrap",
    "create_sample_ber",
]
