"""
Core Governance Module — ALEX Runtime Enforcement

This module implements hard runtime enforcement of the Agent Capability Manifest (ACM).
ALEX (GID-08) is the sole authority for evaluating and denying agent intents.

Enforcement principles:
- Default Deny: Absence of permission = rejection
- No Prompt Reliance: Enforcement is code-only
- No Silent Failure: Every denial emits a structured audit record
- No Capability Inference: Only explicit ACM entries count
- No APPROVE Path: Humans only, never agents
- No Mutation Without EXECUTE: READ/PROPOSE cannot mutate state
- No Drift: Enforcement logic references manifests directly
"""

from core.governance.acm_evaluator import ACMDecision, ACMEvaluator, DenialReason, EvaluationResult
from core.governance.acm_loader import ACMLoader, ACMLoadError, ACMValidationError

# PAC-GOV-AUDIT-01: External Audit Export & Proof Bundle
from core.governance.audit_exporter import (
    AUDIT_BUNDLE_SCHEMA_VERSION,
    AuditBundleConfig,
    AuditBundleExporter,
    AuditBundleResult,
    export_audit_bundle,
)
from core.governance.boot_checks import (
    BootCheckResult,
    GovernanceBootError,
    check_governance_boot,
    enforce_governance_boot,
    get_governance_files,
    get_governance_status,
    validate_governance_file,
)

# PAC-DAN-06: Persistent Denial Registry
from core.governance.denial_registry import (
    DEFAULT_DENIAL_DB_PATH,
    BaseDenialRegistry,
    DenialKey,
    DenialPersistenceError,
    InMemoryDenialRegistry,
    PersistentDenialRegistry,
    configure_denial_registry,
    get_persistent_denial_registry,
    is_persistent_mode,
    reset_persistent_denial_registry,
)
from core.governance.diggi_envelope_handler import (
    DIGGI_ALLOWED_VERBS,
    DIGGI_FORBIDDEN_VERBS,
    DIGGI_GID,
    CorrectionOption,
    DiggiCorrectionResponse,
    DiggiEnvelopeError,
    EnvelopeNotDenyError,
    ForbiddenVerbError,
    NoCorrectionAvailableError,
    can_diggi_handle,
    get_correction_for_reason,
    process_denial_envelope,
)
from core.governance.event_sink import (
    GovernanceEventEmitter,
    GovernanceEventSink,
    InMemorySink,
    JSONLFileSink,
    NullSink,
    configure_default_sink,
    emit_event,
    emitter,
)

# PAC-GOV-OBS-01: Governance Observability & Event Telemetry
from core.governance.events import (
    GovernanceEvent,
    GovernanceEventType,
    acm_evaluated_event,
    artifact_verification_event,
    decision_allowed_event,
    decision_denied_event,
    decision_escalated_event,
    diggi_correction_event,
    drcp_triggered_event,
    governance_boot_event,
    scope_violation_event,
    tool_execution_event,
)

# PAC-GOV-FRESHNESS-01: Trust Data Freshness Contract
from core.governance.freshness import (
    DEFAULT_MAX_STALENESS_SECONDS,
    FRESHNESS_MANIFEST_FILENAME,
    FRESHNESS_SCHEMA_VERSION,
    FreshnessManifest,
    FreshnessVerificationResult,
    SourceTimestamp,
    create_freshness_manifest,
    load_freshness_manifest,
    verify_freshness,
)
from core.governance.governance_fingerprint import (
    FINGERPRINT_VERSION,
    GOVERNANCE_ROOTS,
    FileHash,
    GovernanceDriftError,
    GovernanceFingerprint,
    GovernanceFingerprintEngine,
    GovernanceHashError,
    compute_governance_fingerprint,
    get_fingerprint_engine,
    get_governance_fingerprint,
    verify_governance_integrity,
)

# PAC-DAN-05: Governance Event Retention & Rotation
from core.governance.retention import (
    DEFAULT_ROTATING_LOG_PATH,
    MAX_FILE_COUNT,
    MAX_FILE_SIZE_BYTES,
    RETENTION_POLICY_VERSION,
    GovernanceEventExporter,
    RotatingJSONLSink,
    configure_rotating_sink,
    create_exporter,
)
from core.governance.telemetry import (
    emit_acm_evaluation,
    emit_artifact_verification,
    emit_diggi_correction,
    emit_drcp_triggered,
    emit_envelope_decision,
    emit_scope_violation,
    emit_tool_execution,
    safe_emit,
)

__all__ = [
    # ACM
    "ACMLoader",
    "ACMLoadError",
    "ACMValidationError",
    "ACMEvaluator",
    "ACMDecision",
    "EvaluationResult",
    "DenialReason",
    # Boot Checks (PAC-GOV-GUARD-01)
    "GovernanceBootError",
    "BootCheckResult",
    "enforce_governance_boot",
    "check_governance_boot",
    "validate_governance_file",
    "get_governance_files",
    "get_governance_status",
    # Diggi Envelope Handler (PAC-DIGGI-05)
    "DIGGI_GID",
    "DIGGI_FORBIDDEN_VERBS",
    "DIGGI_ALLOWED_VERBS",
    "CorrectionOption",
    "DiggiCorrectionResponse",
    "DiggiEnvelopeError",
    "EnvelopeNotDenyError",
    "NoCorrectionAvailableError",
    "ForbiddenVerbError",
    "process_denial_envelope",
    "can_diggi_handle",
    "get_correction_for_reason",
    # Governance Fingerprint (PAC-ALEX-02)
    "FINGERPRINT_VERSION",
    "GOVERNANCE_ROOTS",
    "FileHash",
    "GovernanceFingerprint",
    "GovernanceFingerprintEngine",
    "GovernanceHashError",
    "GovernanceDriftError",
    "compute_governance_fingerprint",
    "get_fingerprint_engine",
    "get_governance_fingerprint",
    "verify_governance_integrity",
    # Governance Events (PAC-GOV-OBS-01)
    "GovernanceEvent",
    "GovernanceEventType",
    "GovernanceEventEmitter",
    "GovernanceEventSink",
    "JSONLFileSink",
    "InMemorySink",
    "NullSink",
    "emit_event",
    "emitter",
    "configure_default_sink",
    # Event factories
    "acm_evaluated_event",
    "decision_allowed_event",
    "decision_denied_event",
    "decision_escalated_event",
    "drcp_triggered_event",
    "diggi_correction_event",
    "tool_execution_event",
    "artifact_verification_event",
    "scope_violation_event",
    "governance_boot_event",
    # Telemetry helpers
    "safe_emit",
    "emit_acm_evaluation",
    "emit_drcp_triggered",
    "emit_diggi_correction",
    "emit_tool_execution",
    "emit_artifact_verification",
    "emit_scope_violation",
    "emit_envelope_decision",
    # Retention & Export (PAC-DAN-05)
    "RETENTION_POLICY_VERSION",
    "MAX_FILE_SIZE_BYTES",
    "MAX_FILE_COUNT",
    "DEFAULT_ROTATING_LOG_PATH",
    "RotatingJSONLSink",
    "GovernanceEventExporter",
    "configure_rotating_sink",
    "create_exporter",
    # Audit Bundle Export (PAC-GOV-AUDIT-01)
    "AUDIT_BUNDLE_SCHEMA_VERSION",
    "AuditBundleConfig",
    "AuditBundleExporter",
    "AuditBundleResult",
    "export_audit_bundle",
    # Freshness Contract (PAC-GOV-FRESHNESS-01)
    "FRESHNESS_SCHEMA_VERSION",
    "FRESHNESS_MANIFEST_FILENAME",
    "DEFAULT_MAX_STALENESS_SECONDS",
    "FreshnessManifest",
    "FreshnessVerificationResult",
    "SourceTimestamp",
    "create_freshness_manifest",
    "load_freshness_manifest",
    "verify_freshness",
    # Persistent Denial Registry (PAC-DAN-06)
    "DEFAULT_DENIAL_DB_PATH",
    "BaseDenialRegistry",
    "DenialKey",
    "DenialPersistenceError",
    "InMemoryDenialRegistry",
    "PersistentDenialRegistry",
    "configure_denial_registry",
    "get_persistent_denial_registry",
    "is_persistent_mode",
    "reset_persistent_denial_registry",
]
