"""
Fuzz Generator — Chaos & Adversarial Test Generation

PAC Reference: PAC-JEFFREY-P49
Agent: CODY (GID-01), SAM (GID-06)

Generates fuzz tests and chaos scenarios from API specifications.
Tests boundary conditions, malformed inputs, and adversarial patterns.

INVARIANTS:
- Generated tests are deterministic given same seed
- All fuzz patterns are documented and traceable
- Chaos injection is controlled and bounded
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import random
import string
import hashlib


class FuzzStrategy(Enum):
    """Fuzzing strategy to apply."""
    BOUNDARY = "BOUNDARY"           # Min/max values, edges
    TYPE_CONFUSION = "TYPE_CONFUSION"  # Wrong types
    INJECTION = "INJECTION"         # SQL, XSS, command injection
    OVERFLOW = "OVERFLOW"           # Buffer/integer overflow
    UNICODE = "UNICODE"             # Unicode edge cases
    NULL = "NULL"                   # Null/None handling
    FORMAT = "FORMAT"               # Format string attacks
    RANDOM = "RANDOM"               # Pure random data


class ChaosDimension(Enum):
    """Chaos dimensions to test."""
    AUTH = "AUTH"           # Authentication failures
    TIMING = "TIMING"       # Race conditions, timeouts
    STATE = "STATE"         # Invalid state transitions
    RESOURCE = "RESOURCE"   # Resource exhaustion
    NETWORK = "NETWORK"     # Network failures
    DATA = "DATA"           # Data corruption


@dataclass
class FuzzInput:
    """A single fuzzed input value."""
    original_type: str
    fuzz_strategy: FuzzStrategy
    fuzz_value: Any
    description: str
    expected_behavior: str  # What the API should do
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "original_type": self.original_type,
            "fuzz_strategy": self.fuzz_strategy.value,
            "fuzz_value": repr(self.fuzz_value),
            "description": self.description,
            "expected_behavior": self.expected_behavior,
        }


@dataclass
class FuzzTestCase:
    """A complete fuzz test case for an endpoint."""
    test_id: str
    endpoint_path: str
    http_method: str
    fuzz_inputs: dict[str, FuzzInput]  # param_name -> fuzzed value
    chaos_dimensions: set[ChaosDimension] = field(default_factory=set)
    seed: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "endpoint_path": self.endpoint_path,
            "http_method": self.http_method,
            "fuzz_inputs": {k: v.to_dict() for k, v in self.fuzz_inputs.items()},
            "chaos_dimensions": [d.value for d in self.chaos_dimensions],
            "seed": self.seed,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FuzzSuite:
    """Collection of fuzz test cases."""
    suite_id: str
    api_title: str
    test_cases: list[FuzzTestCase]
    strategies_used: set[FuzzStrategy]
    chaos_dimensions_covered: set[ChaosDimension]
    total_fuzz_inputs: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "api_title": self.api_title,
            "test_count": len(self.test_cases),
            "strategies_used": [s.value for s in self.strategies_used],
            "chaos_dimensions_covered": [d.value for d in self.chaos_dimensions_covered],
            "total_fuzz_inputs": self.total_fuzz_inputs,
            "created_at": self.created_at.isoformat(),
        }


class ChaosInjector:
    """
    Injects chaos scenarios into test execution.
    
    CONTROLLED CHAOS — all injections are:
    - Deterministic given seed
    - Bounded in scope
    - Reversible
    """
    
    # Injection patterns by dimension
    CHAOS_PATTERNS: dict[ChaosDimension, list[dict[str, Any]]] = {
        ChaosDimension.AUTH: [
            {"type": "missing_token", "description": "Omit auth token"},
            {"type": "expired_token", "description": "Use expired token"},
            {"type": "invalid_signature", "description": "Corrupt token signature"},
            {"type": "wrong_scope", "description": "Token with wrong permissions"},
        ],
        ChaosDimension.TIMING: [
            {"type": "slow_response", "delay_ms": 5000, "description": "Simulate slow backend"},
            {"type": "timeout", "description": "Request timeout"},
            {"type": "race_condition", "description": "Concurrent conflicting requests"},
        ],
        ChaosDimension.STATE: [
            {"type": "invalid_transition", "description": "Invalid state transition"},
            {"type": "stale_data", "description": "Operate on stale version"},
            {"type": "missing_prerequisite", "description": "Skip required steps"},
        ],
        ChaosDimension.RESOURCE: [
            {"type": "quota_exceeded", "description": "Exceed rate limits"},
            {"type": "large_payload", "description": "Oversized request body"},
            {"type": "many_parameters", "description": "Maximum parameter count"},
        ],
        ChaosDimension.NETWORK: [
            {"type": "connection_reset", "description": "TCP connection reset"},
            {"type": "partial_response", "description": "Truncated response"},
            {"type": "dns_failure", "description": "DNS resolution failure"},
        ],
        ChaosDimension.DATA: [
            {"type": "corrupt_encoding", "description": "Invalid UTF-8"},
            {"type": "truncated_json", "description": "Incomplete JSON"},
            {"type": "wrong_content_type", "description": "Mismatched Content-Type"},
        ],
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = random.Random(seed)
    
    def get_chaos_scenarios(
        self,
        dimensions: set[ChaosDimension] | None = None
    ) -> list[dict[str, Any]]:
        """Get chaos scenarios for specified dimensions."""
        if dimensions is None:
            dimensions = set(ChaosDimension)
        
        scenarios = []
        for dim in dimensions:
            patterns = self.CHAOS_PATTERNS.get(dim, [])
            for pattern in patterns:
                scenarios.append({
                    "dimension": dim.value,
                    **pattern,
                })
        
        return scenarios
    
    def select_random_scenarios(
        self,
        count: int = 3,
        dimensions: set[ChaosDimension] | None = None
    ) -> list[dict[str, Any]]:
        """Select random chaos scenarios."""
        all_scenarios = self.get_chaos_scenarios(dimensions)
        if len(all_scenarios) <= count:
            return all_scenarios
        return self._rng.sample(all_scenarios, count)


class FuzzGenerator:
    """
    Generates fuzz test cases from API specifications.
    
    DETERMINISTIC — same spec + seed = same tests.
    """
    
    # Fuzz patterns by data type
    STRING_FUZZ: dict[FuzzStrategy, list[tuple[Any, str]]] = {
        FuzzStrategy.BOUNDARY: [
            ("", "Empty string"),
            ("a", "Single character"),
            ("a" * 1000, "Long string (1000 chars)"),
            ("a" * 10000, "Very long string (10000 chars)"),
        ],
        FuzzStrategy.TYPE_CONFUSION: [
            (123, "Integer instead of string"),
            (True, "Boolean instead of string"),
            (None, "Null instead of string"),
            (["a", "b"], "Array instead of string"),
            ({"key": "value"}, "Object instead of string"),
        ],
        FuzzStrategy.INJECTION: [
            ("'; DROP TABLE users; --", "SQL injection"),
            ("<script>alert('xss')</script>", "XSS injection"),
            ("| cat /etc/passwd", "Command injection"),
            ("{{7*7}}", "Template injection"),
            ("../../../etc/passwd", "Path traversal"),
        ],
        FuzzStrategy.UNICODE: [
            ("\u0000", "Null byte"),
            ("\uffff", "Max Unicode"),
            ("café", "Accented characters"),
            ("🔥💯🎉", "Emoji"),
            ("\u202e\u0041\u0042\u0043", "RTL override"),
        ],
        FuzzStrategy.FORMAT: [
            ("%s%s%s%s%s", "Format string"),
            ("%n%n%n%n%n", "Format string write"),
            ("{0}{1}{2}", "Python format"),
        ],
    }
    
    INTEGER_FUZZ: dict[FuzzStrategy, list[tuple[Any, str]]] = {
        FuzzStrategy.BOUNDARY: [
            (0, "Zero"),
            (-1, "Negative one"),
            (1, "One"),
            (2147483647, "Max int32"),
            (-2147483648, "Min int32"),
            (9223372036854775807, "Max int64"),
        ],
        FuzzStrategy.TYPE_CONFUSION: [
            ("123", "String instead of int"),
            (123.456, "Float instead of int"),
            (True, "Boolean instead of int"),
            (None, "Null instead of int"),
        ],
        FuzzStrategy.OVERFLOW: [
            (2147483648, "Int32 overflow"),
            (-2147483649, "Int32 underflow"),
            (10**100, "Very large number"),
        ],
    }
    
    BOOLEAN_FUZZ: dict[FuzzStrategy, list[tuple[Any, str]]] = {
        FuzzStrategy.BOUNDARY: [
            (True, "True"),
            (False, "False"),
        ],
        FuzzStrategy.TYPE_CONFUSION: [
            ("true", "String 'true'"),
            ("false", "String 'false'"),
            (1, "Integer 1"),
            (0, "Integer 0"),
            ("yes", "String 'yes'"),
            (None, "Null"),
        ],
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = random.Random(seed)
        self._chaos_injector = ChaosInjector(seed)
        self._test_counter = 0
    
    def generate_fuzz_suite(
        self,
        spec: Any,  # OpenAPISpec
        strategies: set[FuzzStrategy] | None = None,
        chaos_dimensions: set[ChaosDimension] | None = None,
        max_tests_per_endpoint: int = 50,
    ) -> FuzzSuite:
        """
        Generate a complete fuzz test suite from an API specification.
        
        Args:
            spec: OpenAPISpec object
            strategies: Fuzz strategies to apply (default: all)
            chaos_dimensions: Chaos dimensions to cover (default: all)
            max_tests_per_endpoint: Maximum tests per endpoint
            
        Returns:
            FuzzSuite with generated test cases
        """
        if strategies is None:
            strategies = set(FuzzStrategy)
        if chaos_dimensions is None:
            chaos_dimensions = set(ChaosDimension)
        
        test_cases = []
        total_inputs = 0
        
        for endpoint in spec.endpoints:
            endpoint_tests = self._generate_endpoint_tests(
                endpoint,
                strategies,
                chaos_dimensions,
                max_tests_per_endpoint,
            )
            test_cases.extend(endpoint_tests)
            for tc in endpoint_tests:
                total_inputs += len(tc.fuzz_inputs)
        
        suite_id = hashlib.sha256(
            f"{spec.title}:{self.seed}:{len(test_cases)}".encode()
        ).hexdigest()[:12]
        
        return FuzzSuite(
            suite_id=suite_id,
            api_title=spec.title,
            test_cases=test_cases,
            strategies_used=strategies,
            chaos_dimensions_covered=chaos_dimensions,
            total_fuzz_inputs=total_inputs,
        )
    
    def _generate_endpoint_tests(
        self,
        endpoint: Any,  # EndpointDefinition
        strategies: set[FuzzStrategy],
        chaos_dimensions: set[ChaosDimension],
        max_tests: int,
    ) -> list[FuzzTestCase]:
        """Generate fuzz tests for a single endpoint."""
        tests = []
        
        # Generate parameter fuzz tests
        for param in endpoint.parameters:
            param_tests = self._fuzz_parameter(
                endpoint,
                param,
                strategies,
            )
            tests.extend(param_tests[:max_tests // max(1, len(endpoint.parameters))])
        
        # Add chaos scenario tests
        chaos_tests = self._generate_chaos_tests(
            endpoint,
            chaos_dimensions,
        )
        tests.extend(chaos_tests[:5])  # Max 5 chaos tests per endpoint
        
        return tests[:max_tests]
    
    def _fuzz_parameter(
        self,
        endpoint: Any,
        param: Any,
        strategies: set[FuzzStrategy],
    ) -> list[FuzzTestCase]:
        """Generate fuzz tests for a single parameter."""
        tests = []
        
        # Get fuzz values based on parameter type
        data_type = param.data_type.value if hasattr(param.data_type, 'value') else str(param.data_type)
        fuzz_values = self._get_fuzz_values(data_type, strategies)
        
        for strategy, value, description in fuzz_values:
            self._test_counter += 1
            test_id = f"fuzz_{self._test_counter:06d}"
            
            fuzz_input = FuzzInput(
                original_type=data_type,
                fuzz_strategy=strategy,
                fuzz_value=value,
                description=description,
                expected_behavior=self._expected_behavior(strategy, param.required),
            )
            
            test_case = FuzzTestCase(
                test_id=test_id,
                endpoint_path=endpoint.path,
                http_method=endpoint.method.value if hasattr(endpoint.method, 'value') else str(endpoint.method),
                fuzz_inputs={param.name: fuzz_input},
                seed=self.seed,
            )
            
            tests.append(test_case)
        
        return tests
    
    def _get_fuzz_values(
        self,
        data_type: str,
        strategies: set[FuzzStrategy],
    ) -> list[tuple[FuzzStrategy, Any, str]]:
        """Get fuzz values for a data type."""
        result = []
        
        type_lower = data_type.lower()
        
        if type_lower == "string":
            fuzz_dict = self.STRING_FUZZ
        elif type_lower == "integer":
            fuzz_dict = self.INTEGER_FUZZ
        elif type_lower == "boolean":
            fuzz_dict = self.BOOLEAN_FUZZ
        else:
            # Default to string fuzzing
            fuzz_dict = self.STRING_FUZZ
        
        for strategy in strategies:
            if strategy in fuzz_dict:
                for value, desc in fuzz_dict[strategy]:
                    result.append((strategy, value, desc))
        
        # Add random values
        if FuzzStrategy.RANDOM in strategies:
            result.extend(self._random_values(data_type, 3))
        
        return result
    
    def _random_values(
        self,
        data_type: str,
        count: int
    ) -> list[tuple[FuzzStrategy, Any, str]]:
        """Generate random fuzz values."""
        result = []
        
        for i in range(count):
            if data_type.lower() == "string":
                length = self._rng.randint(1, 100)
                value = ''.join(self._rng.choices(string.printable, k=length))
                result.append((FuzzStrategy.RANDOM, value, f"Random string #{i+1}"))
            elif data_type.lower() == "integer":
                value = self._rng.randint(-1000000, 1000000)
                result.append((FuzzStrategy.RANDOM, value, f"Random integer #{i+1}"))
            else:
                value = self._rng.choice([True, False, None, "", 0, []])
                result.append((FuzzStrategy.RANDOM, value, f"Random value #{i+1}"))
        
        return result
    
    def _generate_chaos_tests(
        self,
        endpoint: Any,
        dimensions: set[ChaosDimension],
    ) -> list[FuzzTestCase]:
        """Generate chaos scenario tests for an endpoint."""
        tests = []
        scenarios = self._chaos_injector.select_random_scenarios(3, dimensions)
        
        for scenario in scenarios:
            self._test_counter += 1
            test_id = f"chaos_{self._test_counter:06d}"
            
            dim = ChaosDimension(scenario["dimension"])
            
            test_case = FuzzTestCase(
                test_id=test_id,
                endpoint_path=endpoint.path,
                http_method=endpoint.method.value if hasattr(endpoint.method, 'value') else str(endpoint.method),
                fuzz_inputs={},
                chaos_dimensions={dim},
                seed=self.seed,
            )
            
            tests.append(test_case)
        
        return tests
    
    def _expected_behavior(self, strategy: FuzzStrategy, required: bool) -> str:
        """Determine expected behavior for a fuzz strategy."""
        if strategy in {FuzzStrategy.TYPE_CONFUSION, FuzzStrategy.INJECTION}:
            return "Should reject with 400 Bad Request or sanitize input"
        elif strategy == FuzzStrategy.OVERFLOW:
            return "Should reject or clamp to valid range"
        elif strategy == FuzzStrategy.NULL:
            if required:
                return "Should reject with 400 Bad Request"
            return "Should handle gracefully"
        elif strategy == FuzzStrategy.BOUNDARY:
            return "Should handle edge case or reject gracefully"
        else:
            return "Should not crash or expose sensitive information"


# Module-level singleton
_fuzz_generator: FuzzGenerator | None = None


def get_fuzz_generator(seed: int = 42) -> FuzzGenerator:
    """Get the fuzz generator singleton."""
    global _fuzz_generator
    if _fuzz_generator is None:
        _fuzz_generator = FuzzGenerator(seed)
    return _fuzz_generator


def reset_fuzz_generator() -> None:
    """Reset the singleton (for testing)."""
    global _fuzz_generator
    _fuzz_generator = None


def generate_fuzz_suite(spec: Any, seed: int = 42) -> FuzzSuite:
    """Convenience function to generate a fuzz suite."""
    generator = FuzzGenerator(seed)
    return generator.generate_fuzz_suite(spec)
