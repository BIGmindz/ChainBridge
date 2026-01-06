"""
Governance Module Initialization

PAC Reference: PAC-JEFFREY-P47
Provides doctrine enforcement and chaos coverage tracking.
"""

from core.occ.governance.chaos_coverage_index import (
    ChaosCoverageIndex,
    ChaosDimension,
    ChaosTest,
    CCISnapshot,
    get_cci,
    reset_cci,
    register_chaos_test,
    check_cci_gate,
    get_cci_report,
)

from core.occ.governance.doctrine_enforcer import (
    DoctrineEnforcer,
    DoctrineID,
    ViolationSeverity,
    EnforcementAction,
    DoctrineViolation,
    DoctrineCheckResult,
    get_doctrine_enforcer,
    reset_doctrine_enforcer,
    check_doctrine_gate,
    get_compliance_report,
)

__all__ = [
    # CCI
    "ChaosCoverageIndex",
    "ChaosDimension", 
    "ChaosTest",
    "CCISnapshot",
    "get_cci",
    "reset_cci",
    "register_chaos_test",
    "check_cci_gate",
    "get_cci_report",
    # Doctrine Enforcer
    "DoctrineEnforcer",
    "DoctrineID",
    "ViolationSeverity",
    "EnforcementAction",
    "DoctrineViolation",
    "DoctrineCheckResult",
    "get_doctrine_enforcer",
    "reset_doctrine_enforcer",
    "check_doctrine_gate",
    "get_compliance_report",
]
