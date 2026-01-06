"""
PyTest Optimizer Tests

PAC Reference: PAC-JEFFREY-P48
Tests for test optimization strategies.
"""

import pytest

from core.occ.testing.pytest_optimizer import (
    PyTestOptimizer,
    TestMetadata,
    OptimizationPlan,
    OptimizationStrategy,
    ParallelGroup,
    get_pytest_optimizer,
    reset_pytest_optimizer,
)


class TestParallelGroup:
    """Test parallel group enumeration."""
    
    def test_all_groups_defined(self):
        """Verify all parallel groups exist."""
        expected = {"ISOLATED", "MODULE", "SESSION", "SEQUENTIAL"}
        actual = {g.value for g in ParallelGroup}
        assert actual == expected


class TestOptimizationStrategy:
    """Test optimization strategy enumeration."""
    
    def test_all_strategies_defined(self):
        """Verify all strategies exist."""
        expected = {"PRIORITY_ORDER", "PARALLEL_GROUPS", "AFFECTED_ONLY", "TIME_BUDGET", "CCI_BALANCED"}
        actual = {s.value for s in OptimizationStrategy}
        assert actual == expected


class TestPyTestOptimizer:
    """Test the core optimizer."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_register_test(self):
        """Test registering a test."""
        optimizer = PyTestOptimizer()
        
        metadata = TestMetadata(
            test_id="test_example",
            test_path="tests/test_example.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            affected_modules={"core/module"}
        )
        
        optimizer.register_test(metadata)
        assert "test_example" in optimizer._tests
    
    def test_affected_by_modules(self):
        """Test finding tests affected by module changes."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_core",
            test_path="tests/test_core.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            affected_modules={"core/module"}
        ))
        
        optimizer.register_test(TestMetadata(
            test_id="test_api",
            test_path="tests/test_api.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            affected_modules={"api/endpoints"}
        ))
        
        affected = optimizer.get_tests_affected_by_modules({"core/module"})
        assert "test_core" in affected
        assert "test_api" not in affected


class TestParallelGroups:
    """Test parallel group creation."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_create_parallel_groups(self):
        """Test grouping tests by parallel safety."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_isolated",
            test_path="tests/isolated.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0
        ))
        
        optimizer.register_test(TestMetadata(
            test_id="test_sequential",
            test_path="tests/sequential.py",
            parallel_group=ParallelGroup.SEQUENTIAL,
            estimated_duration_ms=10.0
        ))
        
        groups = optimizer.create_parallel_groups()
        
        assert "test_isolated" in groups[ParallelGroup.ISOLATED]
        assert "test_sequential" in groups[ParallelGroup.SEQUENTIAL]


class TestPriorityOptimization:
    """Test priority-based optimization."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_optimize_for_priority(self):
        """Test priority-based ordering."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_1", test_path="t1.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0
        ))
        optimizer.register_test(TestMetadata(
            test_id="test_2", test_path="t2.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0
        ))
        
        plan = optimizer.optimize_for_priority(["test_2", "test_1"])
        
        assert plan.strategy == OptimizationStrategy.PRIORITY_ORDER
        assert plan.execution_groups[0][0] == "test_2"
        assert plan.coverage_percentage == 100.0


class TestParallelismOptimization:
    """Test parallel execution optimization."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_optimize_for_parallelism(self):
        """Test parallel grouping."""
        optimizer = PyTestOptimizer()
        
        # Add isolated tests
        for i in range(10):
            optimizer.register_test(TestMetadata(
                test_id=f"test_isolated_{i}",
                test_path=f"tests/isolated_{i}.py",
                parallel_group=ParallelGroup.ISOLATED,
                estimated_duration_ms=10.0
            ))
        
        # Add sequential test
        optimizer.register_test(TestMetadata(
            test_id="test_seq",
            test_path="tests/seq.py",
            parallel_group=ParallelGroup.SEQUENTIAL,
            estimated_duration_ms=10.0
        ))
        
        plan = optimizer.optimize_for_parallelism()
        
        assert plan.strategy == OptimizationStrategy.PARALLEL_GROUPS
        assert len(plan.execution_groups) > 1  # Multiple groups
        assert plan.total_tests == 11


class TestAffectedOnlyOptimization:
    """Test affected-only optimization."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_optimize_for_affected(self):
        """Test PR-scoped test selection."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_core",
            test_path="tests/core.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            affected_modules={"core/module"}
        ))
        
        optimizer.register_test(TestMetadata(
            test_id="test_api",
            test_path="tests/api.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            affected_modules={"api/endpoints"}
        ))
        
        plan = optimizer.optimize_for_affected(
            changed_modules={"core/module"},
            include_critical=False
        )
        
        assert plan.strategy == OptimizationStrategy.AFFECTED_ONLY
        assert plan.total_tests == 1
        assert "test_api" in plan.skipped_tests


class TestTimeBudgetOptimization:
    """Test time-budget optimization."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_optimize_for_time_budget(self):
        """Test budget-constrained selection."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_fast",
            test_path="tests/fast.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0
        ))
        
        optimizer.register_test(TestMetadata(
            test_id="test_slow",
            test_path="tests/slow.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=100.0
        ))
        
        plan = optimizer.optimize_for_time_budget(budget_ms=50.0)
        
        assert plan.strategy == OptimizationStrategy.TIME_BUDGET
        assert "test_fast" in plan.execution_groups[0]
        assert "test_slow" in plan.skipped_tests


class TestCCIBalancedOptimization:
    """Test CCI-balanced optimization."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_optimize_for_cci_balance(self):
        """Test chaos dimension balancing."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_auth",
            test_path="tests/auth.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            chaos_dimensions={"AUTH"}
        ))
        
        optimizer.register_test(TestMetadata(
            test_id="test_state",
            test_path="tests/state.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            chaos_dimensions={"STATE"}
        ))
        
        plan = optimizer.optimize_for_cci_balance()
        
        assert plan.strategy == OptimizationStrategy.CCI_BALANCED
        assert plan.coverage_percentage == 100.0
        assert "AUTH" in plan.cci_coverage
        assert "STATE" in plan.cci_coverage


class TestOptimizationReport:
    """Test optimization report generation."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_generate_report(self):
        """Test report structure."""
        optimizer = PyTestOptimizer()
        
        optimizer.register_test(TestMetadata(
            test_id="test_1",
            test_path="tests/1.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0,
            chaos_dimensions={"AUTH"}
        ))
        
        report = optimizer.generate_optimization_report()
        
        assert "total_tests" in report
        assert "parallelization_breakdown" in report
        assert "cci_coverage" in report
        assert "optimization_potential" in report


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def setup_method(self):
        reset_pytest_optimizer()
    
    def test_get_optimizer_singleton(self):
        """Test singleton behavior."""
        o1 = get_pytest_optimizer()
        o2 = get_pytest_optimizer()
        assert o1 is o2
    
    def test_reset_optimizer(self):
        """Test reset clears state."""
        optimizer = get_pytest_optimizer()
        optimizer.register_test(TestMetadata(
            test_id="test",
            test_path="test.py",
            parallel_group=ParallelGroup.ISOLATED,
            estimated_duration_ms=10.0
        ))
        
        reset_pytest_optimizer()
        new_optimizer = get_pytest_optimizer()
        
        assert len(new_optimizer._tests) == 0
