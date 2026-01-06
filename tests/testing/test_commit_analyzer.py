"""
Tests for Commit Analyzer

PAC Reference: PAC-JEFFREY-P50
Agent: CODY (GID-01) — Test Generation

Tests the CommitAnalyzer, CommitInfo, CommitCCIResult,
CCIDelta, FileChange, and related components.
"""

import pytest
from datetime import datetime, timedelta

from core.occ.testing.commit_analyzer import (
    CommitAnalyzer,
    CommitInfo,
    CommitCCIResult,
    CCIDelta,
    FileChange,
    ChangeType,
    ImpactLevel,
    AffectedTest,
    AnalyzerError,
    analyze_single_commit,
)


class TestChangeType:
    """Tests for ChangeType enum."""
    
    def test_all_change_types(self):
        """Test all change types exist."""
        assert ChangeType.ADDED.value == "ADDED"
        assert ChangeType.MODIFIED.value == "MODIFIED"
        assert ChangeType.DELETED.value == "DELETED"
        assert ChangeType.RENAMED.value == "RENAMED"


class TestImpactLevel:
    """Tests for ImpactLevel enum."""
    
    def test_all_impact_levels(self):
        """Test all impact levels exist."""
        assert ImpactLevel.CRITICAL.value == "CRITICAL"
        assert ImpactLevel.HIGH.value == "HIGH"
        assert ImpactLevel.MEDIUM.value == "MEDIUM"
        assert ImpactLevel.LOW.value == "LOW"
        assert ImpactLevel.MINIMAL.value == "MINIMAL"


class TestFileChange:
    """Tests for FileChange dataclass."""
    
    def test_file_change_creation(self):
        """Test file change creation."""
        change = FileChange(
            path="src/app.py",
            change_type=ChangeType.MODIFIED,
            lines_added=10,
            lines_removed=5,
        )
        
        assert change.path == "src/app.py"
        assert change.change_type == ChangeType.MODIFIED
        assert change.total_changes == 15
    
    def test_file_change_default_impact(self):
        """Test default impact level."""
        change = FileChange(
            path="some/file.py",
            change_type=ChangeType.ADDED,
        )
        
        assert change.impact_level == ImpactLevel.MEDIUM
    
    def test_file_change_to_dict(self):
        """Test file change serialization."""
        change = FileChange(
            path="test.py",
            change_type=ChangeType.DELETED,
            lines_removed=50,
        )
        
        data = change.to_dict()
        
        assert data["path"] == "test.py"
        assert data["change_type"] == "DELETED"
        assert data["total_changes"] == 50


class TestCommitInfo:
    """Tests for CommitInfo dataclass."""
    
    def test_commit_info_creation(self):
        """Test commit info creation."""
        commit = CommitInfo(
            sha="abc123def456",
            message="Fix bug",
            author="developer",
            timestamp=datetime.utcnow(),
        )
        
        assert commit.sha == "abc123def456"
        assert commit.short_sha == "abc123de"
        assert commit.total_files_changed == 0
    
    def test_commit_with_changes(self):
        """Test commit with file changes."""
        changes = [
            FileChange("a.py", ChangeType.MODIFIED, 10, 5),
            FileChange("b.py", ChangeType.ADDED, 20, 0),
        ]
        
        commit = CommitInfo(
            sha="sha123",
            message="Feature",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=changes,
        )
        
        assert commit.total_files_changed == 2
        assert commit.total_lines_added == 30
        assert commit.total_lines_removed == 5
    
    def test_commit_to_dict(self):
        """Test commit serialization."""
        commit = CommitInfo(
            sha="abcdef",
            message="Test",
            author="author",
            timestamp=datetime.utcnow(),
        )
        
        data = commit.to_dict()
        
        assert data["sha"] == "abcdef"
        assert "timestamp" in data
        assert data["total_files_changed"] == 0


class TestCCIDelta:
    """Tests for CCIDelta dataclass."""
    
    def test_cci_improvement(self):
        """Test CCI improvement."""
        delta = CCIDelta(
            cci_before=1.0,
            cci_after=1.1,
            delta=0.1,
            delta_percent=10.0,
            is_improvement=True,
            is_regression=False,
        )
        
        assert delta.is_improvement is True
        assert delta.is_regression is False
    
    def test_cci_regression(self):
        """Test CCI regression."""
        delta = CCIDelta(
            cci_before=1.0,
            cci_after=0.9,
            delta=-0.1,
            delta_percent=-10.0,
            is_improvement=False,
            is_regression=True,
        )
        
        assert delta.is_improvement is False
        assert delta.is_regression is True
    
    def test_cci_delta_to_dict(self):
        """Test CCI delta serialization."""
        delta = CCIDelta(1.0, 1.05, 0.05, 5.0, True, False)
        data = delta.to_dict()
        
        assert data["cci_before"] == 1.0
        assert data["delta"] == 0.05


class TestAffectedTest:
    """Tests for AffectedTest dataclass."""
    
    def test_affected_test_creation(self):
        """Test affected test creation."""
        affected = AffectedTest(
            test_path="tests/test_app.py",
            test_name="test_feature",
            affected_by=["src/app.py", "src/utils.py"],
            risk_score=0.75,
        )
        
        assert affected.test_path == "tests/test_app.py"
        assert len(affected.affected_by) == 2
        assert affected.risk_score == 0.75
    
    def test_affected_test_to_dict(self):
        """Test affected test serialization."""
        affected = AffectedTest(
            test_path="test.py",
            test_name="test_x",
            affected_by=["a.py"],
            risk_score=0.5,
        )
        
        data = affected.to_dict()
        
        assert data["test_path"] == "test.py"
        assert data["risk_score"] == 0.5


class TestCommitAnalyzer:
    """Tests for CommitAnalyzer class."""
    
    def test_analyzer_creation(self):
        """Test analyzer creation."""
        analyzer = CommitAnalyzer()
        
        assert analyzer.current_cci == 1.0
    
    def test_analyzer_with_base_cci(self):
        """Test analyzer with custom base CCI."""
        analyzer = CommitAnalyzer(base_cci=1.5)
        
        assert analyzer.current_cci == 1.5
    
    def test_analyze_commit(self):
        """Test commit analysis."""
        analyzer = CommitAnalyzer()
        
        commit = CommitInfo(
            sha="abc123",
            message="Feature",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=[
                FileChange("src/app.py", ChangeType.MODIFIED, 20, 5),
            ],
        )
        
        result = analyzer.analyze_commit(commit)
        
        assert result.commit.sha == "abc123"
        assert result.cci_delta is not None
        assert isinstance(result.risk_score, float)
    
    def test_critical_path_classification(self):
        """Test critical path classification."""
        analyzer = CommitAnalyzer()
        
        commit = CommitInfo(
            sha="sha",
            message="Security fix",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=[
                FileChange("core/auth/login.py", ChangeType.MODIFIED, 10, 5),
            ],
        )
        
        result = analyzer.analyze_commit(commit)
        
        # Core paths should be classified as critical
        assert result.commit.changes[0].impact_level == ImpactLevel.CRITICAL
    
    def test_low_impact_classification(self):
        """Test low impact classification."""
        analyzer = CommitAnalyzer()
        
        commit = CommitInfo(
            sha="sha",
            message="Docs update",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=[
                FileChange("docs/README.md", ChangeType.MODIFIED, 5, 2),
            ],
        )
        
        result = analyzer.analyze_commit(commit)
        
        assert result.commit.changes[0].impact_level == ImpactLevel.LOW
    
    def test_requires_full_suite_critical(self):
        """Test full suite required for critical changes."""
        analyzer = CommitAnalyzer()
        
        commit = CommitInfo(
            sha="sha",
            message="Breaking change",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=[
                FileChange("core/security/auth.py", ChangeType.MODIFIED, 100, 50),
            ],
        )
        
        result = analyzer.analyze_commit(commit)
        
        assert result.requires_full_suite is True
    
    def test_analyze_range(self):
        """Test analyzing range of commits."""
        analyzer = CommitAnalyzer()
        
        commits = [
            CommitInfo(
                sha=f"sha{i}",
                message=f"Commit {i}",
                author="dev",
                timestamp=datetime.utcnow() - timedelta(days=i),
                changes=[FileChange(f"file{i}.py", ChangeType.MODIFIED, 5, 2)],
            )
            for i in range(3)
        ]
        
        results = analyzer.analyze_range(commits)
        
        assert len(results) == 3
    
    def test_cci_history(self):
        """Test CCI history tracking."""
        analyzer = CommitAnalyzer()
        
        for i in range(5):
            commit = CommitInfo(
                sha=f"sha{i}",
                message=f"Commit {i}",
                author="dev",
                timestamp=datetime.utcnow(),
                changes=[FileChange("app.py", ChangeType.MODIFIED, 5, 2)],
            )
            analyzer.analyze_commit(commit)
        
        history = analyzer.get_cci_history()
        
        assert len(history) == 5
    
    def test_predict_impact(self):
        """Test impact prediction."""
        analyzer = CommitAnalyzer()
        
        files = [
            "core/payment/processor.py",
            "docs/README.md",
        ]
        
        prediction = analyzer.predict_impact(files)
        
        assert prediction["file_count"] == 2
        assert "predicted_risk_score" in prediction
        assert "requires_full_suite" in prediction
    
    def test_register_test_dependency(self):
        """Test registering test dependencies."""
        analyzer = CommitAnalyzer()
        
        analyzer.register_test_dependency(
            "tests/test_app.py",
            ["src/app.py", "src/utils.py"],
        )
        
        commit = CommitInfo(
            sha="sha",
            message="Update",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=[FileChange("src/app.py", ChangeType.MODIFIED, 10, 5)],
        )
        
        result = analyzer.analyze_commit(commit)
        
        # Should find the registered test
        affected_paths = [t.test_path for t in result.affected_tests]
        assert "tests/test_app.py" in affected_paths
    
    def test_high_risk_tests(self):
        """Test high risk test identification."""
        analyzer = CommitAnalyzer()
        
        commit = CommitInfo(
            sha="sha",
            message="Major change",
            author="dev",
            timestamp=datetime.utcnow(),
            changes=[
                FileChange("core/engine.py", ChangeType.MODIFIED, 100, 50),
            ],
        )
        
        result = analyzer.analyze_commit(commit)
        
        # Result should have high risk tests property
        assert hasattr(result, "high_risk_tests")


class TestAnalyzeSingleCommit:
    """Tests for analyze_single_commit convenience function."""
    
    def test_analyze_single_commit(self):
        """Test single commit analysis."""
        result = analyze_single_commit(
            sha="abc123",
            message="Bug fix",
            changes=[
                ("src/app.py", 10, 5),
                ("src/utils.py", 3, 1),
            ],
        )
        
        assert result.commit.sha == "abc123"
        assert len(result.commit.changes) == 2
    
    def test_analyze_empty_commit(self):
        """Test empty commit analysis."""
        result = analyze_single_commit(
            sha="empty",
            message="Empty",
            changes=[],
        )
        
        assert result.commit.total_files_changed == 0
