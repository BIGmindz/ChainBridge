"""
Chaos Coverage Index (CCI) Module

PAC Reference: PAC-JEFFREY-P47
Doctrine: DOC-002 - Chaos Coverage Index
Governance Mode: HARD / FAIL-CLOSED

Implements monotonic chaos coverage tracking across canonical dimensions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
import json


class ChaosDimension(Enum):
    """Canonical chaos dimensions per Doctrine DOC-002."""
    
    AUTH = "AUTH"      # Identity, session, permission failures
    STATE = "STATE"    # Inconsistent, stale, corrupted state
    CONC = "CONC"      # Race conditions, deadlocks, ordering
    TIME = "TIME"      # Clock skew, timeout, scheduling
    DATA = "DATA"      # Malformed, missing, overflow, injection
    GOV = "GOV"        # Rule violations, policy conflicts


@dataclass
class ChaosTest:
    """Represents a single chaos test."""
    
    test_id: str
    dimension: ChaosDimension
    description: str
    test_path: str
    added_in_pac: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CCISnapshot:
    """Point-in-time CCI measurement."""
    
    timestamp: datetime
    pac_reference: str
    dimension_counts: Dict[ChaosDimension, int]
    total_chaos_tests: int
    cci_value: float
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "pac_reference": self.pac_reference,
            "dimension_counts": {d.value: c for d, c in self.dimension_counts.items()},
            "total_chaos_tests": self.total_chaos_tests,
            "cci_value": self.cci_value
        }


class ChaosCoverageIndex:
    """
    Manages Chaos Coverage Index per Doctrine DOC-002.
    
    Invariants:
    - CCI is monotonic (must only increase)
    - CCI < threshold blocks execution
    - CCI is surfaced in OCC and CI
    """
    
    # Minimum CCI threshold - below this, execution is blocked
    CCI_THRESHOLD: float = 1.0
    
    def __init__(self):
        self._tests: Dict[str, ChaosTest] = {}
        self._snapshots: List[CCISnapshot] = []
        self._baseline_cci: Optional[float] = None
    
    def register_chaos_test(
        self,
        test_id: str,
        dimension: ChaosDimension,
        description: str,
        test_path: str,
        pac_reference: str
    ) -> ChaosTest:
        """Register a chaos test in the index."""
        test = ChaosTest(
            test_id=test_id,
            dimension=dimension,
            description=description,
            test_path=test_path,
            added_in_pac=pac_reference
        )
        self._tests[test_id] = test
        return test
    
    def get_dimension_count(self, dimension: ChaosDimension) -> int:
        """Get count of chaos tests for a specific dimension."""
        return sum(1 for t in self._tests.values() if t.dimension == dimension)
    
    def get_all_dimension_counts(self) -> Dict[ChaosDimension, int]:
        """Get counts for all dimensions."""
        return {d: self.get_dimension_count(d) for d in ChaosDimension}
    
    def calculate_cci(self) -> float:
        """
        Calculate Chaos Coverage Index.
        
        CCI = total_chaos_tests / number_of_dimensions
        
        This measures average coverage per dimension.
        """
        total_tests = len(self._tests)
        num_dimensions = len(ChaosDimension)
        return total_tests / num_dimensions if num_dimensions > 0 else 0.0
    
    def get_uncovered_dimensions(self) -> Set[ChaosDimension]:
        """Get dimensions with zero chaos tests."""
        counts = self.get_all_dimension_counts()
        return {d for d, c in counts.items() if c == 0}
    
    def take_snapshot(self, pac_reference: str) -> CCISnapshot:
        """Take a point-in-time CCI snapshot."""
        snapshot = CCISnapshot(
            timestamp=datetime.utcnow(),
            pac_reference=pac_reference,
            dimension_counts=self.get_all_dimension_counts(),
            total_chaos_tests=len(self._tests),
            cci_value=self.calculate_cci()
        )
        self._snapshots.append(snapshot)
        return snapshot
    
    def set_baseline(self, pac_reference: str) -> CCISnapshot:
        """Set the current CCI as baseline for monotonicity checks."""
        snapshot = self.take_snapshot(pac_reference)
        self._baseline_cci = snapshot.cci_value
        return snapshot
    
    def check_monotonicity(self) -> tuple[bool, str]:
        """
        Check if CCI is monotonic (not decreased from baseline).
        
        Returns:
            (is_valid, message)
        """
        if self._baseline_cci is None:
            return True, "No baseline set"
        
        current_cci = self.calculate_cci()
        
        if current_cci < self._baseline_cci:
            return False, (
                f"CCI DECREASE DETECTED: {self._baseline_cci:.2f} → {current_cci:.2f}. "
                f"Doctrine DOC-002 violation: CCI must be monotonic."
            )
        
        return True, f"CCI monotonicity maintained: {self._baseline_cci:.2f} → {current_cci:.2f}"
    
    def check_threshold(self) -> tuple[bool, str]:
        """
        Check if CCI meets minimum threshold.
        
        Returns:
            (meets_threshold, message)
        """
        current_cci = self.calculate_cci()
        
        if current_cci < self.CCI_THRESHOLD:
            return False, (
                f"CCI BELOW THRESHOLD: {current_cci:.2f} < {self.CCI_THRESHOLD:.2f}. "
                f"Doctrine DOC-002 violation: Execution blocked."
            )
        
        return True, f"CCI meets threshold: {current_cci:.2f} >= {self.CCI_THRESHOLD:.2f}"
    
    def verify_execution_allowed(self) -> tuple[bool, str]:
        """
        Verify if execution is allowed per Doctrine DOC-002.
        
        Checks:
        1. CCI >= threshold
        2. CCI is monotonic (if baseline set)
        
        Returns:
            (allowed, message)
        """
        # Check threshold
        threshold_ok, threshold_msg = self.check_threshold()
        if not threshold_ok:
            return False, threshold_msg
        
        # Check monotonicity
        mono_ok, mono_msg = self.check_monotonicity()
        if not mono_ok:
            return False, mono_msg
        
        return True, "Execution allowed: CCI requirements met"
    
    def get_coverage_report(self) -> dict:
        """Generate comprehensive CCI report for OCC/CI."""
        dimension_counts = self.get_all_dimension_counts()
        uncovered = self.get_uncovered_dimensions()
        current_cci = self.calculate_cci()
        
        return {
            "cci_value": current_cci,
            "cci_threshold": self.CCI_THRESHOLD,
            "threshold_met": current_cci >= self.CCI_THRESHOLD,
            "baseline_cci": self._baseline_cci,
            "monotonicity_ok": self.check_monotonicity()[0],
            "total_chaos_tests": len(self._tests),
            "dimensions": {
                d.value: {
                    "count": dimension_counts[d],
                    "covered": dimension_counts[d] > 0
                }
                for d in ChaosDimension
            },
            "uncovered_dimensions": [d.value for d in uncovered],
            "coverage_percentage": (
                (len(ChaosDimension) - len(uncovered)) / len(ChaosDimension) * 100
            ),
            "execution_allowed": self.verify_execution_allowed()[0],
            "snapshot_count": len(self._snapshots)
        }
    
    def get_tests_by_dimension(self, dimension: ChaosDimension) -> List[ChaosTest]:
        """Get all chaos tests for a specific dimension."""
        return [t for t in self._tests.values() if t.dimension == dimension]
    
    def to_json(self) -> str:
        """Serialize CCI state to JSON."""
        return json.dumps(self.get_coverage_report(), indent=2)


# Global CCI instance
_cci_instance: Optional[ChaosCoverageIndex] = None


def get_cci() -> ChaosCoverageIndex:
    """Get or create the global CCI instance."""
    global _cci_instance
    if _cci_instance is None:
        _cci_instance = ChaosCoverageIndex()
    return _cci_instance


def reset_cci() -> None:
    """Reset the global CCI instance (for testing)."""
    global _cci_instance
    _cci_instance = None


def register_chaos_test(
    test_id: str,
    dimension: str,
    description: str,
    test_path: str,
    pac_reference: str = "UNKNOWN"
) -> ChaosTest:
    """
    Convenience function to register a chaos test.
    
    Args:
        test_id: Unique test identifier
        dimension: Chaos dimension code (AUTH, STATE, CONC, TIME, DATA, GOV)
        description: Human-readable test description
        test_path: Path to test file
        pac_reference: PAC that added this test
    """
    cci = get_cci()
    dim = ChaosDimension(dimension)
    return cci.register_chaos_test(test_id, dim, description, test_path, pac_reference)


def check_cci_gate() -> tuple[bool, str]:
    """
    CCI gate check for CI/merge operations.
    
    Returns:
        (gate_passed, message)
    """
    cci = get_cci()
    return cci.verify_execution_allowed()


def get_cci_report() -> dict:
    """Get CCI report for OCC dashboard."""
    cci = get_cci()
    return cci.get_coverage_report()
