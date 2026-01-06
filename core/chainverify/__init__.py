"""
ChainVerify — Infinite Test as a Service (ITaaS)

PAC Reference: PAC-JEFFREY-P49
Classification: PRODUCTIZATION / REVENUE

ChainVerify externalizes ChainBridge's Infinite Test Engine as a sellable,
tenant-isolated verification service. It ingests API specifications and
generates comprehensive test suites without requiring production access.

LEGAL BOUNDARIES (ALEX-ENFORCED):
- NO certification claims
- NO "secure" guarantees  
- NO mutation of client systems
- NO production credentials stored

This is VERIFICATION, not CERTIFICATION.
"""

from core.chainverify.api_ingestion import (
    APIIngestionEngine,
    OpenAPISpec,
    EndpointDefinition,
    ParameterDefinition,
    ingest_openapi,
)

from core.chainverify.tenant_isolation import (
    TenantContext,
    IsolationBoundary,
    TenantManager,
    create_tenant,
    get_tenant,
)

from core.chainverify.fuzz_generator import (
    FuzzGenerator,
    FuzzStrategy,
    ChaosInjector,
    generate_fuzz_suite,
)

from core.chainverify.readonly_executor import (
    ReadOnlyExecutor,
    ExecutionResult,
    SafetyViolation,
    execute_readonly,
)

from core.chainverify.cci_scorer import (
    CCIScorer,
    VerificationScore,
    DimensionCoverage,
    compute_verification_score,
)

from core.chainverify.trust_reporter import (
    TrustReporter,
    TrustGrade,
    VerificationReport,
    generate_trust_report,
)

__all__ = [
    # API Ingestion
    "APIIngestionEngine",
    "OpenAPISpec", 
    "EndpointDefinition",
    "ParameterDefinition",
    "ingest_openapi",
    # Tenant Isolation
    "TenantContext",
    "IsolationBoundary",
    "TenantManager",
    "create_tenant",
    "get_tenant",
    # Fuzz Generation
    "FuzzGenerator",
    "FuzzStrategy",
    "ChaosInjector",
    "generate_fuzz_suite",
    # Read-Only Execution
    "ReadOnlyExecutor",
    "ExecutionResult",
    "SafetyViolation",
    "execute_readonly",
    # CCI Scoring
    "CCIScorer",
    "VerificationScore",
    "DimensionCoverage",
    "compute_verification_score",
    # Trust Reporting
    "TrustReporter",
    "TrustGrade",
    "VerificationReport",
    "generate_trust_report",
]
