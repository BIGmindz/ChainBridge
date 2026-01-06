"""
Always-On Test Engine — Commit Analyzer

PAC Reference: PAC-JEFFREY-P50
Agent: BENSON (GID-00)

Analyzes commits to calculate CCI impact, identify affected tests,
and track CCI progression over the commit history.

INVARIANTS:
- CCI calculation is deterministic
- No mutation of repository
- Results are auditable
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import hashlib
import re


class ChangeType(Enum):
    """Type of change in a commit."""
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"


class ImpactLevel(Enum):
    """Impact level of a change."""
    CRITICAL = "CRITICAL"  # Breaking changes, security fixes
    HIGH = "HIGH"          # Core logic changes
    MEDIUM = "MEDIUM"      # Feature changes
    LOW = "LOW"            # Minor changes, docs
    MINIMAL = "MINIMAL"    # Formatting, comments


@dataclass
class FileChange:
    """A single file change in a commit."""
    path: str
    change_type: ChangeType
    lines_added: int = 0
    lines_removed: int = 0
    impact_level: ImpactLevel = ImpactLevel.MEDIUM
    
    @property
    def total_changes(self) -> int:
        return self.lines_added + self.lines_removed
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type.value,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "total_changes": self.total_changes,
            "impact_level": self.impact_level.value,
        }


@dataclass
class CommitInfo:
    """Information about a commit."""
    sha: str
    message: str
    author: str
    timestamp: datetime
    changes: list[FileChange] = field(default_factory=list)
    
    @property
    def total_files_changed(self) -> int:
        return len(self.changes)
    
    @property
    def total_lines_added(self) -> int:
        return sum(c.lines_added for c in self.changes)
    
    @property
    def total_lines_removed(self) -> int:
        return sum(c.lines_removed for c in self.changes)
    
    @property
    def short_sha(self) -> str:
        return self.sha[:8]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "message": self.message,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "total_files_changed": self.total_files_changed,
            "total_lines_added": self.total_lines_added,
            "total_lines_removed": self.total_lines_removed,
            "changes": [c.to_dict() for c in self.changes],
        }


@dataclass
class CCIDelta:
    """Change in CCI between commits."""
    cci_before: float
    cci_after: float
    delta: float
    delta_percent: float
    is_improvement: bool
    is_regression: bool
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "cci_before": self.cci_before,
            "cci_after": self.cci_after,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "is_improvement": self.is_improvement,
            "is_regression": self.is_regression,
        }


@dataclass
class AffectedTest:
    """A test affected by commit changes."""
    test_path: str
    test_name: str
    affected_by: list[str]  # File paths that affect this test
    risk_score: float
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "test_path": self.test_path,
            "test_name": self.test_name,
            "affected_by": self.affected_by,
            "risk_score": self.risk_score,
        }


@dataclass
class CommitCCIResult:
    """Complete CCI analysis result for a commit."""
    commit: CommitInfo
    cci_delta: CCIDelta
    affected_tests: list[AffectedTest]
    risk_score: float
    requires_full_suite: bool
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def high_risk_tests(self) -> list[AffectedTest]:
        return [t for t in self.affected_tests if t.risk_score >= 0.7]
    
    @property
    def medium_risk_tests(self) -> list[AffectedTest]:
        return [t for t in self.affected_tests if 0.3 <= t.risk_score < 0.7]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "commit": self.commit.to_dict(),
            "cci_delta": self.cci_delta.to_dict(),
            "affected_tests_count": len(self.affected_tests),
            "high_risk_tests_count": len(self.high_risk_tests),
            "medium_risk_tests_count": len(self.medium_risk_tests),
            "risk_score": self.risk_score,
            "requires_full_suite": self.requires_full_suite,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


class AnalyzerError(Exception):
    """Error during commit analysis."""
    pass


class CommitAnalyzer:
    """
    Commit-level CCI Analyzer.
    
    Analyzes commits to:
    - Calculate CCI delta
    - Identify affected tests
    - Score risk of changes
    - Determine if full suite needed
    
    INVARIANTS:
    - Analysis is deterministic
    - No repository mutation
    - Results are auditable
    """
    
    # Path patterns for impact level detection
    CRITICAL_PATHS = {
        r"core/.*",
        r"api/server\.py",
        r".*security.*",
        r".*auth.*",
        r".*payment.*",
    }
    
    HIGH_IMPACT_PATHS = {
        r"api/.*",
        r"core/occ/.*",
        r".*service.*",
    }
    
    LOW_IMPACT_PATHS = {
        r"docs/.*",
        r".*\.md$",
        r".*\.txt$",
        r"tests/.*",
    }
    
    def __init__(self, base_cci: float = 1.0):
        self._base_cci = base_cci
        self._current_cci = base_cci
        self._history: list[CommitCCIResult] = []
        
        # Test mapping (in production, would scan test files)
        self._test_dependencies: dict[str, list[str]] = {}
    
    @property
    def current_cci(self) -> float:
        """Get current CCI value."""
        return self._current_cci
    
    def analyze_commit(self, commit: CommitInfo) -> CommitCCIResult:
        """
        Analyze a commit and calculate CCI impact.
        
        Args:
            commit: Commit information
        
        Returns:
            CommitCCIResult with full analysis
        """
        # Classify changes by impact
        for change in commit.changes:
            change.impact_level = self._classify_impact(change.path)
        
        # Calculate CCI delta
        cci_before = self._current_cci
        cci_after = self._calculate_cci(commit)
        delta = cci_after - cci_before
        delta_percent = (delta / cci_before * 100) if cci_before > 0 else 0
        
        cci_delta = CCIDelta(
            cci_before=cci_before,
            cci_after=cci_after,
            delta=delta,
            delta_percent=delta_percent,
            is_improvement=delta > 0,
            is_regression=delta < 0,
        )
        
        # Identify affected tests
        affected_tests = self._identify_affected_tests(commit)
        
        # Calculate overall risk
        risk_score = self._calculate_risk_score(commit, affected_tests)
        
        # Determine if full suite needed
        requires_full_suite = self._requires_full_suite(commit, risk_score)
        
        result = CommitCCIResult(
            commit=commit,
            cci_delta=cci_delta,
            affected_tests=affected_tests,
            risk_score=risk_score,
            requires_full_suite=requires_full_suite,
        )
        
        # Update state
        self._current_cci = cci_after
        self._history.append(result)
        
        return result
    
    def analyze_range(
        self,
        commits: list[CommitInfo]
    ) -> list[CommitCCIResult]:
        """
        Analyze a range of commits.
        
        Args:
            commits: List of commits (oldest first)
        
        Returns:
            List of analysis results
        """
        results = []
        for commit in commits:
            result = self.analyze_commit(commit)
            results.append(result)
        return results
    
    def get_cci_history(self) -> list[tuple[str, float, datetime]]:
        """Get CCI history over commits."""
        return [
            (r.commit.sha, r.cci_delta.cci_after, r.analysis_timestamp)
            for r in self._history
        ]
    
    def get_recent_analysis(self, count: int = 10) -> list[CommitCCIResult]:
        """Get most recent analysis results."""
        return self._history[-count:]
    
    def predict_impact(self, files: list[str]) -> dict[str, Any]:
        """
        Predict impact of changing specified files.
        
        Args:
            files: List of file paths that will change
        
        Returns:
            Predicted impact analysis
        """
        # Classify impacts
        impacts = {level: [] for level in ImpactLevel}
        for path in files:
            level = self._classify_impact(path)
            impacts[level].append(path)
        
        # Calculate predicted risk
        critical_count = len(impacts[ImpactLevel.CRITICAL])
        high_count = len(impacts[ImpactLevel.HIGH])
        
        risk_score = min(1.0, (critical_count * 0.3 + high_count * 0.15 + len(files) * 0.01))
        
        return {
            "file_count": len(files),
            "impacts": {
                level.value: paths for level, paths in impacts.items() if paths
            },
            "predicted_risk_score": risk_score,
            "requires_full_suite": critical_count > 0 or risk_score > 0.7,
            "recommended_tests": self._recommend_tests(files),
        }
    
    def register_test_dependency(self, test_path: str, depends_on: list[str]) -> None:
        """Register a test's file dependencies."""
        self._test_dependencies[test_path] = depends_on
    
    def _classify_impact(self, path: str) -> ImpactLevel:
        """Classify the impact level of a file change."""
        for pattern in self.CRITICAL_PATHS:
            if re.match(pattern, path):
                return ImpactLevel.CRITICAL
        
        for pattern in self.HIGH_IMPACT_PATHS:
            if re.match(pattern, path):
                return ImpactLevel.HIGH
        
        for pattern in self.LOW_IMPACT_PATHS:
            if re.match(pattern, path):
                return ImpactLevel.LOW
        
        return ImpactLevel.MEDIUM
    
    def _calculate_cci(self, commit: CommitInfo) -> float:
        """Calculate new CCI after commit."""
        # Base CCI adjustment factors
        additions_factor = commit.total_lines_added * 0.001
        removals_factor = commit.total_lines_removed * 0.0005
        
        # Impact multipliers
        impact_multiplier = 1.0
        for change in commit.changes:
            if change.impact_level == ImpactLevel.CRITICAL:
                impact_multiplier *= 0.95  # Critical changes may reduce CCI
            elif change.impact_level == ImpactLevel.LOW:
                impact_multiplier *= 1.01  # Low-risk changes slightly improve
        
        # Calculate new CCI
        base_change = (additions_factor - removals_factor) * impact_multiplier
        new_cci = self._current_cci + base_change
        
        # Clamp to reasonable range
        return max(0.1, min(2.0, new_cci))
    
    def _identify_affected_tests(self, commit: CommitInfo) -> list[AffectedTest]:
        """Identify tests affected by commit changes."""
        affected = []
        changed_paths = {c.path for c in commit.changes}
        
        # Check registered dependencies
        for test_path, dependencies in self._test_dependencies.items():
            affected_by = [d for d in dependencies if d in changed_paths]
            if affected_by:
                risk = len(affected_by) / len(dependencies) if dependencies else 0
                affected.append(AffectedTest(
                    test_path=test_path,
                    test_name=test_path.split("/")[-1].replace(".py", ""),
                    affected_by=affected_by,
                    risk_score=risk,
                ))
        
        # Heuristic: tests in same directory as changed files
        for change in commit.changes:
            if not change.path.startswith("tests/"):
                # Assume corresponding test exists
                test_path = self._infer_test_path(change.path)
                if test_path and test_path not in [a.test_path for a in affected]:
                    risk = 0.5 if change.impact_level in {ImpactLevel.CRITICAL, ImpactLevel.HIGH} else 0.3
                    affected.append(AffectedTest(
                        test_path=test_path,
                        test_name=test_path.split("/")[-1].replace(".py", ""),
                        affected_by=[change.path],
                        risk_score=risk,
                    ))
        
        return affected
    
    def _calculate_risk_score(
        self,
        commit: CommitInfo,
        affected_tests: list[AffectedTest]
    ) -> float:
        """Calculate overall risk score for commit."""
        # Impact-based risk
        impact_risk = 0.0
        for change in commit.changes:
            if change.impact_level == ImpactLevel.CRITICAL:
                impact_risk += 0.3
            elif change.impact_level == ImpactLevel.HIGH:
                impact_risk += 0.2
            elif change.impact_level == ImpactLevel.MEDIUM:
                impact_risk += 0.1
        
        # Affected tests risk
        test_risk = sum(t.risk_score for t in affected_tests) / max(len(affected_tests), 1)
        
        # Change volume risk
        volume_risk = min(0.3, commit.total_files_changed * 0.02)
        
        # Combined risk (weighted)
        total_risk = (impact_risk * 0.5) + (test_risk * 0.3) + (volume_risk * 0.2)
        
        return min(1.0, total_risk)
    
    def _requires_full_suite(self, commit: CommitInfo, risk_score: float) -> bool:
        """Determine if full test suite is required."""
        # Always run full suite for critical changes
        has_critical = any(
            c.impact_level == ImpactLevel.CRITICAL
            for c in commit.changes
        )
        
        if has_critical:
            return True
        
        # High risk commits need full suite
        if risk_score > 0.7:
            return True
        
        # Many files changed
        if commit.total_files_changed > 10:
            return True
        
        return False
    
    def _infer_test_path(self, source_path: str) -> str | None:
        """Infer test file path from source file path."""
        if source_path.startswith("tests/"):
            return source_path
        
        # Convert source path to test path
        # e.g., "core/engine.py" -> "tests/test_engine.py"
        parts = source_path.split("/")
        filename = parts[-1]
        
        if filename.endswith(".py") and not filename.startswith("test_"):
            test_filename = f"test_{filename}"
            return f"tests/{test_filename}"
        
        return None
    
    def _recommend_tests(self, files: list[str]) -> list[str]:
        """Recommend tests to run for given file changes."""
        recommendations = set()
        
        for path in files:
            # Add directly related tests
            test_path = self._infer_test_path(path)
            if test_path:
                recommendations.add(test_path)
            
            # Add tests with registered dependencies
            for test, deps in self._test_dependencies.items():
                if path in deps:
                    recommendations.add(test)
        
        return list(recommendations)


# Convenience functions

def analyze_single_commit(sha: str, message: str, changes: list[tuple[str, int, int]]) -> CommitCCIResult:
    """
    Quick analysis of a single commit.
    
    Args:
        sha: Commit SHA
        message: Commit message
        changes: List of (path, lines_added, lines_removed)
    
    Returns:
        Analysis result
    """
    file_changes = [
        FileChange(
            path=path,
            change_type=ChangeType.MODIFIED,
            lines_added=added,
            lines_removed=removed,
        )
        for path, added, removed in changes
    ]
    
    commit = CommitInfo(
        sha=sha,
        message=message,
        author="analyzer",
        timestamp=datetime.utcnow(),
        changes=file_changes,
    )
    
    analyzer = CommitAnalyzer()
    return analyzer.analyze_commit(commit)
