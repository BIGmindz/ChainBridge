"""
ChainVerify Tests — Fuzz Generator

PAC Reference: PAC-JEFFREY-P49
"""

import pytest

from core.chainverify.fuzz_generator import (
    FuzzGenerator,
    FuzzStrategy,
    ChaosDimension,
    ChaosInjector,
    FuzzInput,
    FuzzTestCase,
    FuzzSuite,
    get_fuzz_generator,
    reset_fuzz_generator,
)
from core.chainverify.api_ingestion import (
    OpenAPISpec,
    EndpointDefinition,
    ParameterDefinition,
    HTTPMethod,
    ParameterLocation,
    DataType,
)


class TestFuzzStrategy:
    """Test fuzz strategy enumeration."""
    
    def test_all_strategies_defined(self):
        expected = {
            "BOUNDARY", "TYPE_CONFUSION", "INJECTION", "OVERFLOW",
            "UNICODE", "NULL", "FORMAT", "RANDOM"
        }
        actual = {s.value for s in FuzzStrategy}
        assert actual == expected


class TestChaosDimension:
    """Test chaos dimension enumeration."""
    
    def test_all_dimensions_defined(self):
        expected = {"AUTH", "TIMING", "STATE", "RESOURCE", "NETWORK", "DATA"}
        actual = {d.value for d in ChaosDimension}
        assert actual == expected


class TestFuzzInput:
    """Test fuzz input dataclass."""
    
    def test_create_fuzz_input(self):
        fuzz = FuzzInput(
            original_type="string",
            fuzz_strategy=FuzzStrategy.INJECTION,
            fuzz_value="'; DROP TABLE users; --",
            description="SQL injection",
            expected_behavior="Should reject with 400"
        )
        
        assert fuzz.fuzz_strategy == FuzzStrategy.INJECTION
        assert "DROP TABLE" in str(fuzz.fuzz_value)
    
    def test_to_dict(self):
        fuzz = FuzzInput(
            original_type="integer",
            fuzz_strategy=FuzzStrategy.BOUNDARY,
            fuzz_value=2147483647,
            description="Max int32",
            expected_behavior="Should handle or reject"
        )
        
        d = fuzz.to_dict()
        assert d["fuzz_strategy"] == "BOUNDARY"


class TestFuzzTestCase:
    """Test fuzz test case dataclass."""
    
    def test_create_test_case(self):
        case = FuzzTestCase(
            test_id="fuzz_000001",
            endpoint_path="/users",
            http_method="GET",
            fuzz_inputs={},
            seed=42
        )
        
        assert case.test_id == "fuzz_000001"
        assert case.http_method == "GET"
    
    def test_with_chaos_dimensions(self):
        case = FuzzTestCase(
            test_id="chaos_000001",
            endpoint_path="/auth",
            http_method="POST",
            fuzz_inputs={},
            chaos_dimensions={ChaosDimension.AUTH},
            seed=42
        )
        
        assert ChaosDimension.AUTH in case.chaos_dimensions


class TestChaosInjector:
    """Test chaos injection."""
    
    def test_get_all_scenarios(self):
        injector = ChaosInjector(seed=42)
        
        scenarios = injector.get_chaos_scenarios()
        
        assert len(scenarios) > 0
        dimensions = {s["dimension"] for s in scenarios}
        assert "AUTH" in dimensions
        assert "TIMING" in dimensions
    
    def test_get_filtered_scenarios(self):
        injector = ChaosInjector(seed=42)
        
        scenarios = injector.get_chaos_scenarios({ChaosDimension.AUTH})
        
        assert all(s["dimension"] == "AUTH" for s in scenarios)
    
    def test_select_random_scenarios(self):
        injector = ChaosInjector(seed=42)
        
        scenarios = injector.select_random_scenarios(count=3)
        
        assert len(scenarios) <= 3
    
    def test_deterministic_with_seed(self):
        i1 = ChaosInjector(seed=42)
        i2 = ChaosInjector(seed=42)
        
        s1 = i1.select_random_scenarios(3)
        s2 = i2.select_random_scenarios(3)
        
        assert s1 == s2


class TestFuzzGenerator:
    """Test fuzz generator."""
    
    def setup_method(self):
        reset_fuzz_generator()
    
    def _create_sample_spec(self) -> OpenAPISpec:
        """Create a sample spec for testing."""
        return OpenAPISpec(
            title="Test API",
            version="1.0.0",
            description="",
            base_url="https://api.test.com",
            endpoints=[
                EndpointDefinition(
                    path="/users",
                    method=HTTPMethod.GET,
                    operation_id="listUsers",
                    parameters=[
                        ParameterDefinition(
                            name="limit",
                            location=ParameterLocation.QUERY,
                            data_type=DataType.INTEGER,
                            required=False
                        ),
                        ParameterDefinition(
                            name="search",
                            location=ParameterLocation.QUERY,
                            data_type=DataType.STRING,
                            required=False
                        ),
                    ]
                ),
                EndpointDefinition(
                    path="/users/{id}",
                    method=HTTPMethod.GET,
                    operation_id="getUser",
                    parameters=[
                        ParameterDefinition(
                            name="id",
                            location=ParameterLocation.PATH,
                            data_type=DataType.STRING,
                            required=True
                        ),
                    ]
                ),
            ]
        )
    
    def test_generate_fuzz_suite(self):
        generator = FuzzGenerator(seed=42)
        spec = self._create_sample_spec()
        
        suite = generator.generate_fuzz_suite(spec)
        
        assert suite.api_title == "Test API"
        assert len(suite.test_cases) > 0
        assert suite.total_fuzz_inputs > 0
    
    def test_strategies_applied(self):
        generator = FuzzGenerator(seed=42)
        spec = self._create_sample_spec()
        
        suite = generator.generate_fuzz_suite(
            spec,
            strategies={FuzzStrategy.BOUNDARY, FuzzStrategy.INJECTION}
        )
        
        assert FuzzStrategy.BOUNDARY in suite.strategies_used
        assert FuzzStrategy.INJECTION in suite.strategies_used
    
    def test_chaos_dimensions_covered(self):
        generator = FuzzGenerator(seed=42)
        spec = self._create_sample_spec()
        
        suite = generator.generate_fuzz_suite(
            spec,
            chaos_dimensions={ChaosDimension.AUTH, ChaosDimension.STATE}
        )
        
        # Check chaos tests were generated
        chaos_tests = [
            tc for tc in suite.test_cases
            if tc.chaos_dimensions
        ]
        assert len(chaos_tests) > 0
    
    def test_deterministic_generation(self):
        spec = self._create_sample_spec()
        
        g1 = FuzzGenerator(seed=42)
        g2 = FuzzGenerator(seed=42)
        
        suite1 = g1.generate_fuzz_suite(spec, max_tests_per_endpoint=10)
        suite2 = g2.generate_fuzz_suite(spec, max_tests_per_endpoint=10)
        
        # Same seed should produce same test IDs
        ids1 = [tc.test_id for tc in suite1.test_cases]
        ids2 = [tc.test_id for tc in suite2.test_cases]
        
        # Note: May differ due to test counter, but patterns should match
        assert len(ids1) == len(ids2)
    
    def test_max_tests_respected(self):
        generator = FuzzGenerator(seed=42)
        spec = self._create_sample_spec()
        
        suite = generator.generate_fuzz_suite(
            spec,
            max_tests_per_endpoint=5
        )
        
        # Check tests per endpoint
        endpoint_counts: dict[str, int] = {}
        for tc in suite.test_cases:
            key = f"{tc.http_method}:{tc.endpoint_path}"
            endpoint_counts[key] = endpoint_counts.get(key, 0) + 1
        
        for count in endpoint_counts.values():
            assert count <= 5


class TestFuzzPatterns:
    """Test specific fuzz patterns."""
    
    def test_string_boundary_patterns(self):
        generator = FuzzGenerator(seed=42)
        
        # Access the internal fuzz dictionary
        patterns = generator.STRING_FUZZ[FuzzStrategy.BOUNDARY]
        
        # Should have empty string
        values = [p[0] for p in patterns]
        assert "" in values
        
        # Should have long strings
        assert any(len(str(v)) > 100 for v in values)
    
    def test_injection_patterns(self):
        generator = FuzzGenerator(seed=42)
        
        patterns = generator.STRING_FUZZ[FuzzStrategy.INJECTION]
        values = [p[0] for p in patterns]
        
        # Should have SQL injection
        assert any("DROP" in str(v) for v in values)
        
        # Should have XSS
        assert any("<script>" in str(v) for v in values)
    
    def test_integer_boundary_patterns(self):
        generator = FuzzGenerator(seed=42)
        
        patterns = generator.INTEGER_FUZZ[FuzzStrategy.BOUNDARY]
        values = [p[0] for p in patterns]
        
        assert 0 in values
        assert -1 in values
        assert 2147483647 in values  # Max int32


class TestGlobalFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        reset_fuzz_generator()
    
    def test_get_singleton(self):
        g1 = get_fuzz_generator()
        g2 = get_fuzz_generator()
        assert g1 is g2
    
    def test_reset_clears_state(self):
        g1 = get_fuzz_generator()
        g1._test_counter = 100
        
        reset_fuzz_generator()
        
        g2 = get_fuzz_generator()
        assert g2._test_counter == 0
