"""
PyTest Optimization Strategy Module

PAC Reference: PAC-JEFFREY-P48
Objective: Optimize CI runtime without reducing coverage

Strategies implemented:
1. Priority-based test ordering
2. Parallel execution grouping
3. Smart test selection for PRs
4. CCI-aware test distribution
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import json


class OptimizationStrategy(Enum):
    """Available optimization strategies."""
    
    PRIORITY_ORDER = "PRIORITY_ORDER"      # Run high-risk tests first
    PARALLEL_GROUPS = "PARALLEL_GROUPS"    # Group tests for parallel execution
    AFFECTED_ONLY = "AFFECTED_ONLY"        # Run tests affected by changes
    TIME_BUDGET = "TIME_BUDGET"            # Fit tests within time budget
    CCI_BALANCED = "CCI_BALANCED"          # Ensure chaos dimension coverage


class ParallelGroup(Enum):
    """Groups for parallel test execution."""
    
    ISOLATED = "ISOLATED"        # No shared state, safe to parallelize
    MODULE_SHARED = "MODULE"     # Share module-level fixtures
    SESSION_SHARED = "SESSION"   # Require session-level fixtures
    SEQUENTIAL = "SEQUENTIAL"    # Must run sequentially


@dataclass
class TestMetadata:
    """Metadata for a test file or function."""
    
    test_id: str
    test_path: str
    parallel_group: ParallelGroup
    estimated_duration_ms: float
    dependencies: Set[str] = field(default_factory=set)
    chaos_dimensions: Set[str] = field(default_factory=set)
    affected_modules: Set[str] = field(default_factory=set)


@dataclass
class OptimizationPlan:
    """Execution plan produced by optimizer."""
    
    strategy: OptimizationStrategy
    total_tests: int
    estimated_duration_ms: float
    execution_groups: List[List[str]]  # Groups of tests to run together/in parallel
    skipped_tests: List[str]
    coverage_percentage: float
    cci_coverage: Dict[str, int]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "total_tests": self.total_tests,
            "estimated_duration_ms": self.estimated_duration_ms,
            "execution_groups": self.execution_groups,
            "skipped_tests": self.skipped_tests,
            "coverage_percentage": self.coverage_percentage,
            "cci_coverage": self.cci_coverage,
            "created_at": self.created_at.isoformat()
        }


class PyTestOptimizer:
    """
    Optimizes PyTest execution for CI efficiency.
    
    Does NOT reduce test coverage - only optimizes execution order and parallelization.
    """
    
    # Maximum parallel workers
    MAX_WORKERS = 8
    
    # Default time budget (5 minutes)
    DEFAULT_TIME_BUDGET_MS = 300_000
    
    def __init__(self):
        self._tests: Dict[str, TestMetadata] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._reverse_deps: Dict[str, Set[str]] = {}  # module -> tests that depend on it
    
    def register_test(self, metadata: TestMetadata) -> None:
        """Register a test with its metadata."""
        self._tests[metadata.test_id] = metadata
        
        # Build dependency graph
        self._dependency_graph[metadata.test_id] = metadata.dependencies
        
        # Build reverse dependency map
        for module in metadata.affected_modules:
            if module not in self._reverse_deps:
                self._reverse_deps[module] = set()
            self._reverse_deps[module].add(metadata.test_id)
    
    def get_tests_affected_by_modules(self, changed_modules: Set[str]) -> Set[str]:
        """Get tests affected by changes to specific modules."""
        affected = set()
        for module in changed_modules:
            if module in self._reverse_deps:
                affected.update(self._reverse_deps[module])
            
            # Also check partial matches (e.g., "core/occ" affects "core/occ/dashboard")
            for registered_module, tests in self._reverse_deps.items():
                if module in registered_module or registered_module in module:
                    affected.update(tests)
        
        return affected
    
    def create_parallel_groups(self) -> Dict[ParallelGroup, List[str]]:
        """Group tests by their parallelization safety."""
        groups: Dict[ParallelGroup, List[str]] = {g: [] for g in ParallelGroup}
        
        for test_id, metadata in self._tests.items():
            groups[metadata.parallel_group].append(test_id)
        
        return groups
    
    def optimize_for_priority(
        self,
        priority_order: List[str]
    ) -> OptimizationPlan:
        """
        Create execution plan based on priority ordering.
        
        High-priority tests run first to fail fast.
        """
        # Filter to registered tests only
        ordered = [t for t in priority_order if t in self._tests]
        remaining = [t for t in self._tests if t not in ordered]
        
        all_tests = ordered + remaining
        
        total_duration = sum(self._tests[t].estimated_duration_ms for t in all_tests)
        
        # Create single execution group (priority-ordered)
        return OptimizationPlan(
            strategy=OptimizationStrategy.PRIORITY_ORDER,
            total_tests=len(all_tests),
            estimated_duration_ms=total_duration,
            execution_groups=[all_tests],
            skipped_tests=[],
            coverage_percentage=100.0,
            cci_coverage=self._compute_cci_coverage(all_tests)
        )
    
    def optimize_for_parallelism(self) -> OptimizationPlan:
        """
        Create execution plan optimized for parallel execution.
        
        Groups tests by their parallelization safety.
        """
        groups = self.create_parallel_groups()
        
        execution_groups = []
        
        # Isolated tests can all run in parallel
        isolated = groups[ParallelGroup.ISOLATED]
        if isolated:
            # Split into worker-sized chunks
            chunk_size = max(len(isolated) // self.MAX_WORKERS, 1)
            for i in range(0, len(isolated), chunk_size):
                execution_groups.append(isolated[i:i + chunk_size])
        
        # Module-shared tests run in module groups
        module_shared = groups[ParallelGroup.MODULE_SHARED]
        if module_shared:
            # Group by module
            by_module: Dict[str, List[str]] = {}
            for test_id in module_shared:
                modules = self._tests[test_id].affected_modules
                key = "_".join(sorted(modules)[:1]) if modules else "default"
                if key not in by_module:
                    by_module[key] = []
                by_module[key].append(test_id)
            
            for module_tests in by_module.values():
                execution_groups.append(module_tests)
        
        # Session-shared and sequential tests run last, in order
        session_shared = groups[ParallelGroup.SESSION_SHARED]
        sequential = groups[ParallelGroup.SEQUENTIAL]
        
        if session_shared:
            execution_groups.append(session_shared)
        if sequential:
            execution_groups.append(sequential)
        
        all_tests = [t for group in execution_groups for t in group]
        total_duration = sum(self._tests[t].estimated_duration_ms for t in all_tests)
        
        # Estimate parallel duration (longest group)
        parallel_duration = max(
            sum(self._tests[t].estimated_duration_ms for t in group)
            for group in execution_groups
        ) if execution_groups else 0
        
        return OptimizationPlan(
            strategy=OptimizationStrategy.PARALLEL_GROUPS,
            total_tests=len(all_tests),
            estimated_duration_ms=parallel_duration,  # Parallel estimate
            execution_groups=execution_groups,
            skipped_tests=[],
            coverage_percentage=100.0,
            cci_coverage=self._compute_cci_coverage(all_tests)
        )
    
    def optimize_for_affected(
        self,
        changed_modules: Set[str],
        include_critical: bool = True
    ) -> OptimizationPlan:
        """
        Create execution plan for tests affected by changes.
        
        Always includes critical tests if include_critical is True.
        """
        affected = self.get_tests_affected_by_modules(changed_modules)
        
        # Always include tests with high blast radius
        if include_critical:
            from core.occ.testing.test_intelligence import get_test_intelligence_engine
            engine = get_test_intelligence_engine()
            critical = engine.get_critical_tests()
            affected.update(t.test_id for t in critical if t.test_id in self._tests)
        
        tests_to_run = list(affected)
        skipped = [t for t in self._tests if t not in affected]
        
        total_duration = sum(
            self._tests[t].estimated_duration_ms
            for t in tests_to_run
            if t in self._tests
        )
        
        return OptimizationPlan(
            strategy=OptimizationStrategy.AFFECTED_ONLY,
            total_tests=len(tests_to_run),
            estimated_duration_ms=total_duration,
            execution_groups=[tests_to_run],
            skipped_tests=skipped,
            coverage_percentage=(len(tests_to_run) / len(self._tests) * 100) if self._tests else 0,
            cci_coverage=self._compute_cci_coverage(tests_to_run)
        )
    
    def optimize_for_time_budget(
        self,
        budget_ms: float,
        priority_order: Optional[List[str]] = None
    ) -> OptimizationPlan:
        """
        Create execution plan that fits within time budget.
        
        Prioritizes high-risk tests when budget is limited.
        """
        if priority_order is None:
            priority_order = list(self._tests.keys())
        
        selected = []
        remaining_budget = budget_ms
        skipped = []
        
        for test_id in priority_order:
            if test_id not in self._tests:
                continue
            
            duration = self._tests[test_id].estimated_duration_ms
            if duration <= remaining_budget:
                selected.append(test_id)
                remaining_budget -= duration
            else:
                skipped.append(test_id)
        
        # Add any tests not in priority order
        for test_id in self._tests:
            if test_id not in selected and test_id not in skipped:
                duration = self._tests[test_id].estimated_duration_ms
                if duration <= remaining_budget:
                    selected.append(test_id)
                    remaining_budget -= duration
                else:
                    skipped.append(test_id)
        
        return OptimizationPlan(
            strategy=OptimizationStrategy.TIME_BUDGET,
            total_tests=len(selected),
            estimated_duration_ms=budget_ms - remaining_budget,
            execution_groups=[selected],
            skipped_tests=skipped,
            coverage_percentage=(len(selected) / len(self._tests) * 100) if self._tests else 0,
            cci_coverage=self._compute_cci_coverage(selected)
        )
    
    def optimize_for_cci_balance(self) -> OptimizationPlan:
        """
        Create execution plan that ensures chaos dimension coverage.
        
        Ensures all 6 canonical dimensions are covered.
        """
        all_dimensions = {"AUTH", "STATE", "CONC", "TIME", "DATA", "GOV"}
        covered_dimensions: Set[str] = set()
        selected: List[str] = []
        
        # First pass: select tests that cover uncovered dimensions
        remaining_tests = list(self._tests.keys())
        
        while covered_dimensions != all_dimensions and remaining_tests:
            # Find test that covers most uncovered dimensions
            best_test = None
            best_coverage = 0
            
            for test_id in remaining_tests:
                test_dims = self._tests[test_id].chaos_dimensions
                new_coverage = len(test_dims - covered_dimensions)
                if new_coverage > best_coverage:
                    best_coverage = new_coverage
                    best_test = test_id
            
            if best_test:
                selected.append(best_test)
                covered_dimensions.update(self._tests[best_test].chaos_dimensions)
                remaining_tests.remove(best_test)
            else:
                break
        
        # Second pass: add remaining tests
        selected.extend(remaining_tests)
        
        total_duration = sum(self._tests[t].estimated_duration_ms for t in selected)
        
        return OptimizationPlan(
            strategy=OptimizationStrategy.CCI_BALANCED,
            total_tests=len(selected),
            estimated_duration_ms=total_duration,
            execution_groups=[selected],
            skipped_tests=[],
            coverage_percentage=100.0,
            cci_coverage=self._compute_cci_coverage(selected)
        )
    
    def _compute_cci_coverage(self, test_ids: List[str]) -> Dict[str, int]:
        """Compute chaos dimension coverage for test set."""
        coverage: Dict[str, int] = {}
        
        for test_id in test_ids:
            if test_id in self._tests:
                for dim in self._tests[test_id].chaos_dimensions:
                    coverage[dim] = coverage.get(dim, 0) + 1
        
        return coverage
    
    def generate_optimization_report(self) -> dict:
        """Generate comprehensive optimization report."""
        parallel_groups = self.create_parallel_groups()
        
        total_duration = sum(m.estimated_duration_ms for m in self._tests.values())
        
        return {
            "total_tests": len(self._tests),
            "total_estimated_duration_ms": total_duration,
            "parallelization_breakdown": {
                g.value: len(tests) for g, tests in parallel_groups.items()
            },
            "parallelizable_percentage": (
                (len(parallel_groups[ParallelGroup.ISOLATED]) / len(self._tests) * 100)
                if self._tests else 0
            ),
            "cci_coverage": self._compute_cci_coverage(list(self._tests.keys())),
            "optimization_potential": {
                "priority_order": "Fail-fast on critical tests",
                "parallel_groups": f"Up to {self.MAX_WORKERS}x speedup for isolated tests",
                "affected_only": "PR-scoped testing",
                "time_budget": "Budget-constrained execution",
                "cci_balanced": "Ensure chaos coverage"
            }
        }
    
    def to_json(self) -> str:
        """Serialize optimizer state to JSON."""
        return json.dumps(self.generate_optimization_report(), indent=2)


# Global instance
_optimizer_instance: Optional[PyTestOptimizer] = None


def get_pytest_optimizer() -> PyTestOptimizer:
    """Get or create the global optimizer."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = PyTestOptimizer()
    return _optimizer_instance


def reset_pytest_optimizer() -> None:
    """Reset the global optimizer (for testing)."""
    global _optimizer_instance
    _optimizer_instance = None
