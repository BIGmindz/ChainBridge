"""
Always-On Test Engine — Continuous Verification Infrastructure

PAC Reference: PAC-JEFFREY-P50
Classification: EXECUTION / NON-MUTATING

The Always-On Test Engine converts PyTest from a periodic validation tool
into a continuous verification system. Tests run perpetually, CCI is
recalculated per commit, and pre-merge risk scores are generated automatically.

INVARIANTS:
- NO runtime mutation (read-only analysis)
- Tests must always pass before merge
- CCI must be monotonically non-decreasing
- Kill-switch operable at all times
"""

from ..engine import (
    AlwaysOnEngine,
    EngineConfig,
    EngineStatus,
    EngineMetrics,
    ExecutionCycle,
    CycleResult,
    EngineError,
    KillSwitchActivated,
    get_engine,
    reset_engine,
)

from ..continuous_executor import (
    ContinuousExecutor,
    ExecutionMode,
    ExecutionPriority,
    ExecutionSchedule,
    ExecutionBatch,
    TestResult,
    ExecutorError,
    ResourceLimitExceeded,
    create_standard_executor,
    create_chaos_executor,
    create_fuzz_executor,
)

from ..commit_analyzer import (
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

from ..premerge_scorer import (
    PreMergeScorer,
    MergeRiskScore,
    RiskLevel,
    RiskCategory,
    RiskFactor,
    TestSummary,
    CoverageInfo,
    ScorerError,
    quick_merge_check,
    create_blocking_factor,
)

__all__ = [
    # Engine
    "AlwaysOnEngine",
    "EngineConfig",
    "EngineStatus",
    "EngineMetrics",
    "ExecutionCycle",
    "CycleResult",
    "EngineError",
    "KillSwitchActivated",
    "get_engine",
    "reset_engine",
    # Continuous Executor
    "ContinuousExecutor",
    "ExecutionMode",
    "ExecutionPriority",
    "ExecutionSchedule",
    "ExecutionBatch",
    "TestResult",
    "ExecutorError",
    "ResourceLimitExceeded",
    "create_standard_executor",
    "create_chaos_executor",
    "create_fuzz_executor",
    # Commit Analyzer
    "CommitAnalyzer",
    "CommitInfo",
    "CommitCCIResult",
    "CCIDelta",
    "FileChange",
    "ChangeType",
    "ImpactLevel",
    "AffectedTest",
    "AnalyzerError",
    "analyze_single_commit",
    # Pre-Merge Scorer
    "PreMergeScorer",
    "MergeRiskScore",
    "RiskLevel",
    "RiskCategory",
    "RiskFactor",
    "TestSummary",
    "CoverageInfo",
    "ScorerError",
    "quick_merge_check",
    "create_blocking_factor",
]
