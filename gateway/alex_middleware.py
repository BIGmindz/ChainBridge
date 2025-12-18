"""
ALEX Middleware — Gateway intercept for ACM enforcement.

This middleware implements the enforcement chokepoint:
- All agent actions must pass through ALEX evaluation
- Denied intents are aborted immediately
- Every decision is logged to the audit sink
- Governance checklist is a HARD DEPENDENCY (missing = refuse to boot)

ALEX (GID-08) is the sole authority for evaluating and denying agent intents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from core.governance.acm_evaluator import ACMDecision, ACMEvaluator, DenialReason, EvaluationResult
from core.governance.acm_loader import ACMLoader, ACMLoadError, ACMValidationError
from core.governance.atlas_scope import (
    AtlasScope,
    AtlasScopeInvalidError,
    AtlasScopeNotFoundError,
    is_atlas,
    load_atlas_scope,
    set_atlas_scope,
)
from core.governance.checklist_loader import (
    ChecklistLoader,
    ChecklistNotFoundError,
    ChecklistValidationError,
    ChecklistVersionError,
    GovernanceChecklist,
)
from core.governance.diggi_corrections import (
    CorrectionMap,
    CorrectionMapInvalidError,
    CorrectionMapNotFoundError,
    NoValidCorrectionError,
    load_correction_map,
)
from core.governance.drcp import (
    DIGGY_GID,
    create_denial_record,
    get_denial_registry,
    is_diggy,
    is_diggy_forbidden_verb,
    requires_diggy_routing,
)
from core.governance.intent_schema import AgentIntent, IntentVerb
from gateway.decision_envelope import GatewayDecisionEnvelope, create_envelope_from_result

# Configure governance audit logger
_GOVERNANCE_LOG_DIR = Path(__file__).parent.parent / "logs"
_GOVERNANCE_LOG_FILE = _GOVERNANCE_LOG_DIR / "governance_events.log"


class GovernanceAuditLogger:
    """Structured audit logger for governance decisions.

    Every decision (ALLOW or DENY) is logged to ensure complete audit trail.
    No logs = failure.

    Uses direct file writes (not Python logging) to ensure immediate flush
    and avoid buffering issues in tests.
    """

    def __init__(self, log_file: Path | None = None) -> None:
        """Initialize the audit logger.

        Args:
            log_file: Path to governance log file. Defaults to logs/governance_events.log
        """
        self._log_file = log_file or _GOVERNANCE_LOG_FILE

        # Ensure log directory exists
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def _write_record(self, record: Dict[str, object]) -> None:
        """Write a record directly to the log file with immediate flush."""
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()

    def set_governance_fingerprint(self, fingerprint_data: Dict[str, str] | None) -> None:
        """Set the governance fingerprint to include in all audit records.

        Args:
            fingerprint_data: Dict with composite_hash and version, or None to disable
        """
        self._governance_fingerprint = fingerprint_data

    def log_decision(self, result: EvaluationResult) -> None:
        """Log an evaluation decision with governance fingerprint.

        Args:
            result: The evaluation result to log
        """
        audit_record = result.to_audit_dict()
        # Enrich with governance fingerprint (additive only, PAC-ALEX-02)
        if hasattr(self, "_governance_fingerprint") and self._governance_fingerprint:
            audit_record["governance_fingerprint"] = self._governance_fingerprint
        self._write_record(audit_record)

    def log_startup(self, manifest_count: int, acm_versions: Dict[str, str]) -> None:
        """Log ALEX startup event.

        Args:
            manifest_count: Number of manifests loaded
            acm_versions: Dict mapping GID to version
        """
        record = {
            "event": "ALEX_STARTUP",
            "manifest_count": manifest_count,
            "acm_versions": acm_versions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_startup_failure(self, error: str) -> None:
        """Log ALEX startup failure.

        Args:
            error: Error message
        """
        record = {
            "event": "ALEX_STARTUP_FAILURE",
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_checklist_loaded(self, version: str, status: str) -> None:
        """Log governance checklist loaded event.

        Args:
            version: Checklist version
            status: Checklist status (e.g., GOVERNANCE-LOCKED)
        """
        record = {
            "event": "CHECKLIST_LOADED",
            "checklist_version": version,
            "checklist_status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_chain_of_command_violation(self, agent_gid: str, verb: str, target: str, next_hop: str) -> None:
        """Log a chain-of-command violation.

        Args:
            agent_gid: The agent that violated
            verb: The verb attempted
            target: The target resource
            next_hop: Where the intent should be routed
        """
        record = {
            "event": "CHAIN_OF_COMMAND_VIOLATION",
            "agent_gid": agent_gid,
            "verb": verb,
            "target": target,
            "next_hop": next_hop,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_drcp_diggy_forbidden(self, agent_gid: str, verb: str, target: str) -> None:
        """Log Diggy attempting a forbidden verb.

        Args:
            agent_gid: Should always be GID-00
            verb: The forbidden verb attempted
            target: The target resource
        """
        record = {
            "event": "DRCP_DIGGY_FORBIDDEN",
            "agent_gid": agent_gid,
            "verb": verb,
            "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_drcp_retry_blocked(self, agent_gid: str, verb: str, target: str) -> None:
        """Log an agent attempting to retry after denial.

        Args:
            agent_gid: The agent attempting retry
            verb: The verb being retried
            target: The target resource
        """
        record = {
            "event": "DRCP_RETRY_BLOCKED",
            "agent_gid": agent_gid,
            "verb": verb,
            "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_drcp_routing(self, agent_gid: str, verb: str, target: str, next_hop: str) -> None:
        """Log DRCP routing of a denial to Diggy.

        Args:
            agent_gid: The denied agent
            verb: The denied verb
            target: The target resource
            next_hop: Where routed (should be GID-00)
        """
        record = {
            "event": "DRCP_DENIAL_ROUTED",
            "agent_gid": agent_gid,
            "verb": verb,
            "target": target,
            "next_hop": next_hop,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_correction_map_loaded(self, version: str, schema_version: str) -> None:
        """Log correction map loaded event.

        Args:
            version: Correction map version
            schema_version: Schema version (e.g., DCC-v1)
        """
        record = {
            "event": "CORRECTION_MAP_LOADED",
            "correction_map_version": version,
            "schema_version": schema_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_correction_attached(self, agent_gid: str, denial_reason: str, correction_steps: int) -> None:
        """Log correction plan attached to denial.

        Args:
            agent_gid: The denied agent
            denial_reason: The denial reason code
            correction_steps: Number of allowed next steps
        """
        record = {
            "event": "DCC_CORRECTION_ATTACHED",
            "agent_gid": agent_gid,
            "denial_reason": denial_reason,
            "correction_steps": correction_steps,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_no_valid_correction(self, agent_gid: str, denial_reason: str) -> None:
        """Log that no valid correction exists for a denial.

        Args:
            agent_gid: The denied agent
            denial_reason: The denial reason code
        """
        record = {
            "event": "DCC_NO_VALID_CORRECTION",
            "agent_gid": agent_gid,
            "denial_reason": denial_reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_atlas_domain_violation(self, agent_gid: str, verb: str, target_path: str, forbidden_pattern: str) -> None:
        """Log Atlas attempting to modify a domain-owned path.

        Args:
            agent_gid: Should always be GID-11
            verb: The verb attempted
            target_path: The path Atlas tried to modify
            forbidden_pattern: The pattern that matched
        """
        record = {
            "event": "ATLAS_DOMAIN_VIOLATION",
            "agent_gid": agent_gid,
            "verb": verb,
            "target_path": target_path,
            "forbidden_pattern": forbidden_pattern,
            "severity": "CRITICAL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_governance_fingerprint_computed(self, composite_hash: str, version: str, file_count: int, categories: list[str]) -> None:
        """Log governance fingerprint computation at startup.

        Args:
            composite_hash: The composite SHA-256 hash
            version: Fingerprint schema version
            file_count: Number of files hashed
            categories: List of governance categories included
        """
        record = {
            "event": "GOVERNANCE_FINGERPRINT_COMPUTED",
            "composite_hash": composite_hash,
            "version": version,
            "file_count": file_count,
            "categories": categories,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)

    def log_governance_drift_detected(self, original_hash: str, current_hash: str, severity: str = "CRITICAL") -> None:
        """Log governance drift detection.

        Args:
            original_hash: Hash at boot time
            current_hash: Hash at drift detection time
            severity: Severity level (always CRITICAL for drift)
        """
        record = {
            "event": "GOVERNANCE_DRIFT_DETECTED",
            "original_hash": original_hash,
            "current_hash": current_hash,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._write_record(record)


class IntentDeniedError(Exception):
    """Raised when an intent is denied by ALEX.

    This exception carries the full evaluation result for inspection.
    """

    def __init__(self, result: EvaluationResult) -> None:
        self.result = result
        super().__init__(f"Intent denied: {result.reason.value if result.reason else 'UNKNOWN'} - {result.reason_detail}")


class ALEXMiddlewareError(Exception):
    """Raised when ALEX middleware encounters a fatal error."""

    pass


class ChecklistEnforcementError(Exception):
    """Raised when governance checklist enforcement fails.

    This is a critical error — the system should not proceed.
    """

    pass


@dataclass
class MiddlewareConfig:
    """Configuration for ALEX middleware."""

    # If True, startup fails if any manifest is invalid
    fail_closed_on_invalid_manifest: bool = True

    # If True, missing ACM for an agent results in denial
    fail_closed_on_unknown_agent: bool = True

    # If True, all decisions are logged (not just denials)
    log_all_decisions: bool = True

    # If True, raises IntentDeniedError on denial
    raise_on_denial: bool = True

    # If True, checklist is REQUIRED (fail-closed on missing)
    require_checklist: bool = True

    # If True, chain-of-command is enforced for EXECUTE/BLOCK/APPROVE
    enforce_chain_of_command: bool = True

    # If True, DRCP (Diggy Rejection & Correction Protocol) is enforced
    enforce_drcp: bool = True

    # If True, DCC (Deterministic Correction Contract) is enforced
    # Attaches correction_plan to all DENY results
    enforce_dcc: bool = True

    # If True, Atlas (GID-11) domain boundary is enforced
    # Atlas cannot modify frontend/backend code — only governance/docs
    enforce_atlas_scope: bool = True


class ALEXMiddleware:
    """Gateway middleware for ACM enforcement.

    This is the enforcement chokepoint. All agent actions must pass through
    this middleware before reaching tools, files, APIs, or databases.

    HARD DEPENDENCIES:
    - ACM manifests must be present and valid
    - Governance checklist must be present and valid
    - Missing either = system refuses to boot

    DRCP ENFORCEMENT:
    - All DENY decisions route to Diggy (GID-00)
    - Agents cannot retry after denial
    - Diggy cannot EXECUTE, BLOCK, or APPROVE

    Usage:
        middleware = ALEXMiddleware()
        middleware.initialize()  # Must call before evaluate

        # For each agent action:
        result = middleware.evaluate(intent)
        if result.decision == ACMDecision.DENY:
            # Handle denial
        else:
            # Proceed with action
    """

    def __init__(
        self,
        config: MiddlewareConfig | None = None,
        loader: ACMLoader | None = None,
        audit_logger: GovernanceAuditLogger | None = None,
        checklist_loader: ChecklistLoader | None = None,
    ) -> None:
        """Initialize the middleware (does not load manifests yet).

        Args:
            config: Middleware configuration
            loader: ACM loader instance
            audit_logger: Audit logger instance
            checklist_loader: Governance checklist loader instance
        """
        self._config = config or MiddlewareConfig()
        self._loader = loader or ACMLoader()
        self._audit = audit_logger or GovernanceAuditLogger()
        self._checklist_loader = checklist_loader or ChecklistLoader()
        self._evaluator: Optional[ACMEvaluator] = None
        self._checklist: Optional[GovernanceChecklist] = None
        self._correction_map: Optional[CorrectionMap] = None
        self._atlas_scope: Optional[AtlasScope] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the middleware by loading all ACM manifests and checklist.

        Must be called before evaluate(). Fails closed if:
        - Manifests are invalid
        - Checklist is missing
        - Checklist version is incompatible
        - Correction map is missing or invalid (if DCC enforced)
        - Atlas scope is missing or invalid (if Atlas scope enforced)

        Raises:
            ALEXMiddlewareError: If ACM initialization fails
            ChecklistEnforcementError: If checklist is missing or invalid
        """
        # Step 1: Load governance checklist (HARD DEPENDENCY)
        if self._config.require_checklist:
            try:
                self._checklist = self._checklist_loader.load()
                self._audit.log_checklist_loaded(
                    self._checklist.version,
                    self._checklist.status,
                )
            except (ChecklistNotFoundError, ChecklistVersionError, ChecklistValidationError) as e:
                self._audit.log_startup_failure(f"Checklist error: {e}")
                raise ChecklistEnforcementError(f"ALEX startup REFUSED: {e}. " "System cannot operate without governance checklist.") from e

        # Step 2: Load correction map (DCC HARD DEPENDENCY)
        if self._config.enforce_dcc:
            try:
                self._correction_map = load_correction_map()
                self._audit.log_correction_map_loaded(
                    self._correction_map.version,
                    self._correction_map.schema_version,
                )
            except (CorrectionMapNotFoundError, CorrectionMapInvalidError) as e:
                self._audit.log_startup_failure(f"Correction map error: {e}")
                raise ALEXMiddlewareError(
                    f"ALEX startup REFUSED: {e}. " "System cannot operate without correction map when DCC is enforced."
                ) from e

        # Step 3: Load Atlas scope (DOMAIN BOUNDARY ENFORCEMENT)
        if self._config.enforce_atlas_scope:
            try:
                self._atlas_scope = load_atlas_scope()
                set_atlas_scope(self._atlas_scope)
            except (AtlasScopeNotFoundError, AtlasScopeInvalidError) as e:
                self._audit.log_startup_failure(f"Atlas scope error: {e}")
                raise ALEXMiddlewareError(
                    f"ALEX startup REFUSED: {e}. " "System cannot operate without Atlas scope when domain enforcement is enabled."
                ) from e

        # Step 4: Load ACM manifests
        try:
            acms = self._loader.load_all()
            self._evaluator = ACMEvaluator(self._loader)
            self._initialized = True

            # Log successful startup
            versions = {gid: acm.version for gid, acm in acms.items()}
            self._audit.log_startup(len(acms), versions)

        except (ACMLoadError, ACMValidationError) as e:
            self._audit.log_startup_failure(str(e))
            if self._config.fail_closed_on_invalid_manifest:
                raise ALEXMiddlewareError(f"ALEX startup failed: {e}") from e

    def is_initialized(self) -> bool:
        """Check if middleware is initialized and ready."""
        return self._initialized

    def has_checklist(self) -> bool:
        """Check if governance checklist is loaded."""
        return self._checklist is not None

    def get_checklist(self) -> Optional[GovernanceChecklist]:
        """Get the loaded governance checklist."""
        return self._checklist

    def has_correction_map(self) -> bool:
        """Check if correction map is loaded."""
        return self._correction_map is not None

    def get_correction_map(self) -> Optional[CorrectionMap]:
        """Get the loaded correction map."""
        return self._correction_map

    def has_atlas_scope(self) -> bool:
        """Check if Atlas scope is loaded."""
        return self._atlas_scope is not None

    def get_atlas_scope(self) -> Optional[AtlasScope]:
        """Get the loaded Atlas scope."""
        return self._atlas_scope

    def _check_atlas_domain_violation(self, intent: AgentIntent) -> Optional[EvaluationResult]:
        """Check if Atlas (GID-11) is attempting to modify a forbidden path.

        Atlas is a meta-agent with zero domain authority. Atlas cannot
        create, modify, patch, or generate any domain-owned code.

        Args:
            intent: The agent intent

        Returns:
            EvaluationResult with DENY if violation, None if OK
        """
        if not self._config.enforce_atlas_scope:
            return None

        if not is_atlas(intent.agent_gid):
            return None

        if self._atlas_scope is None:
            return None

        # Check if the target path is forbidden
        # The intent target may be a path or include path information
        target = intent.full_target

        # Check for path-like targets
        forbidden_pattern = self._atlas_scope.is_path_forbidden(target)

        if forbidden_pattern is None:
            return None  # Not a forbidden path

        # Atlas domain violation detected
        timestamp = datetime.now(timezone.utc).isoformat()
        verb_str = intent.verb.value if hasattr(intent.verb, "value") else str(intent.verb)

        self._audit.log_atlas_domain_violation(
            agent_gid=intent.agent_gid,
            verb=verb_str,
            target_path=target,
            forbidden_pattern=forbidden_pattern,
        )

        return EvaluationResult(
            decision=ACMDecision.DENY,
            agent_gid=intent.agent_gid,
            intent_verb=verb_str,
            intent_target=target,
            reason=DenialReason.ATLAS_DOMAIN_VIOLATION,
            reason_detail=f"Atlas (GID-11) cannot modify domain-owned path: {target} (matched: {forbidden_pattern})",
            acm_version=None,
            timestamp=timestamp,
            correlation_id=intent.correlation_id,
            next_hop=DIGGY_GID,
        )

    def _check_chain_of_command(self, intent: AgentIntent) -> Optional[EvaluationResult]:
        """Check chain-of-command for EXECUTE/BLOCK/APPROVE verbs.

        Returns:
            EvaluationResult with DENY if violation, None if OK
        """
        if not self._config.enforce_chain_of_command:
            return None

        if self._checklist is None:
            return None

        # Check if verb requires chain-of-command
        verb_str = intent.verb.value if hasattr(intent.verb, "value") else str(intent.verb)
        if not self._checklist.requires_chain_of_command(verb_str):
            return None

        # Check if intent has chain-of-command routing
        # Intent must either:
        # 1. Originate from the orchestrator (GID-00)
        # 2. Have chain_of_command field including GID-00
        orchestrator = self._checklist.orchestrator_gid

        # Check origin
        if intent.agent_gid == orchestrator:
            return None  # Orchestrator can always act

        # Check chain_of_command metadata
        metadata = intent.metadata or {}
        chain = metadata.get("chain_of_command", [])
        if isinstance(chain, str):
            chain = [chain]
        if orchestrator in chain:
            return None  # Routed through orchestrator

        # Check authorized_by metadata
        if metadata.get("authorized_by") == orchestrator:
            return None  # Authorized by orchestrator

        # Violation: Log and create denial result
        timestamp = datetime.now(timezone.utc).isoformat()
        self._audit.log_chain_of_command_violation(
            agent_gid=intent.agent_gid,
            verb=verb_str,
            target=intent.full_target,
            next_hop=orchestrator,
        )

        return EvaluationResult(
            decision=ACMDecision.DENY,
            agent_gid=intent.agent_gid,
            intent_verb=verb_str,
            intent_target=intent.full_target,
            reason=DenialReason.CHAIN_OF_COMMAND_VIOLATION,
            reason_detail=f"{verb_str} requires routing through {orchestrator} (Diggy)",
            acm_version=None,
            timestamp=timestamp,
            correlation_id=intent.correlation_id,
            next_hop=DIGGY_GID,
        )

    def _check_drcp_diggy_forbidden(self, intent: AgentIntent) -> Optional[EvaluationResult]:
        """Check if Diggy is attempting a forbidden verb.

        Diggy cannot EXECUTE, BLOCK, or APPROVE — ever.

        Args:
            intent: The agent intent

        Returns:
            EvaluationResult with DENY if violation, None if OK
        """
        if not self._config.enforce_drcp:
            return None

        if not is_diggy(intent.agent_gid):
            return None

        verb_str = intent.verb.value if hasattr(intent.verb, "value") else str(intent.verb)

        if not is_diggy_forbidden_verb(verb_str):
            return None

        # Diggy attempting forbidden verb
        timestamp = datetime.now(timezone.utc).isoformat()

        # Determine specific denial reason
        verb_upper = verb_str.upper()
        if verb_upper == "EXECUTE":
            reason = DenialReason.DIGGY_EXECUTE_FORBIDDEN
            detail = "Diggy (GID-00) cannot EXECUTE — only PROPOSE or ESCALATE"
        elif verb_upper == "BLOCK":
            reason = DenialReason.DIGGY_BLOCK_FORBIDDEN
            detail = "Diggy (GID-00) cannot BLOCK — ALEX-only authority"
        elif verb_upper == "APPROVE":
            reason = DenialReason.DIGGY_APPROVE_FORBIDDEN
            detail = "Diggy (GID-00) cannot APPROVE — human-only authority"
        else:
            reason = DenialReason.VERB_NOT_PERMITTED
            detail = f"Diggy (GID-00) cannot {verb_upper}"

        self._audit.log_drcp_diggy_forbidden(intent.agent_gid, verb_str, intent.full_target)

        return EvaluationResult(
            decision=ACMDecision.DENY,
            agent_gid=intent.agent_gid,
            intent_verb=verb_str,
            intent_target=intent.full_target,
            reason=reason,
            reason_detail=detail,
            acm_version=None,
            timestamp=timestamp,
            correlation_id=intent.correlation_id,
            next_hop=None,  # No next hop — Diggy IS the correction authority
        )

    def _check_drcp_retry_after_deny(self, intent: AgentIntent) -> Optional[EvaluationResult]:
        """Check if an agent is retrying after a denial.

        Agents cannot retry the same action after denial — they must wait
        for Diggy's correction.

        Args:
            intent: The agent intent

        Returns:
            EvaluationResult with DENY if retry detected, None if OK
        """
        if not self._config.enforce_drcp:
            return None

        # Diggy is exempt from retry checks (correction authority)
        if is_diggy(intent.agent_gid):
            return None

        verb_str = intent.verb.value if hasattr(intent.verb, "value") else str(intent.verb)
        registry = get_denial_registry()

        if not registry.has_active_denial(intent.agent_gid, verb_str, intent.full_target):
            return None

        # Retry detected
        timestamp = datetime.now(timezone.utc).isoformat()
        self._audit.log_drcp_retry_blocked(intent.agent_gid, verb_str, intent.full_target)

        return EvaluationResult(
            decision=ACMDecision.DENY,
            agent_gid=intent.agent_gid,
            intent_verb=verb_str,
            intent_target=intent.full_target,
            reason=DenialReason.RETRY_AFTER_DENY_FORBIDDEN,
            reason_detail="Cannot retry after denial — await Diggy correction",
            acm_version=None,
            timestamp=timestamp,
            correlation_id=intent.correlation_id,
            next_hop=DIGGY_GID,
        )

    def _apply_drcp_routing(self, result: EvaluationResult) -> EvaluationResult:
        """Apply DRCP routing to a denial result.

        For denials on EXECUTE/BLOCK/APPROVE, route to Diggy and register.

        Args:
            result: The evaluation result

        Returns:
            Updated result with next_hop if applicable
        """
        if not self._config.enforce_drcp:
            return result

        if result.decision != ACMDecision.DENY:
            return result

        # Check if this verb requires Diggy routing
        if not requires_diggy_routing(result.intent_verb):
            return result

        # Register the denial
        registry = get_denial_registry()
        denial_record = create_denial_record(result)
        registry.register_denial(denial_record)

        # Log the routing
        self._audit.log_drcp_routing(
            result.agent_gid,
            result.intent_verb,
            result.intent_target,
            DIGGY_GID,
        )

        # Return result with next_hop set
        return EvaluationResult(
            decision=result.decision,
            agent_gid=result.agent_gid,
            intent_verb=result.intent_verb,
            intent_target=result.intent_target,
            reason=result.reason,
            reason_detail=result.reason_detail,
            acm_version=result.acm_version,
            timestamp=result.timestamp,
            correlation_id=result.correlation_id,
            next_hop=DIGGY_GID,
            correction_plan=result.correction_plan,
        )

    def _attach_correction_plan(self, result: EvaluationResult) -> EvaluationResult:
        """Attach a correction plan to a denial result.

        This implements the DCC (Deterministic Correction Contract).
        Corrections are looked up from the static mapping file.

        Args:
            result: The evaluation result (must be DENY)

        Returns:
            Updated result with correction_plan attached
        """
        if not self._config.enforce_dcc:
            return result

        if result.decision != ACMDecision.DENY:
            return result

        if result.reason is None:
            return result

        if self._correction_map is None:
            # DCC is enforced but map not loaded — this shouldn't happen
            # since we fail closed on init, but handle gracefully
            return result

        try:
            correction = self._correction_map.get_correction(result.reason)
            correction_dict = correction.to_dict()

            # Log successful correction attachment
            self._audit.log_correction_attached(
                result.agent_gid,
                result.reason.value,
                len(correction.allowed_next_steps),
            )

            # Return result with correction_plan attached
            return EvaluationResult(
                decision=result.decision,
                agent_gid=result.agent_gid,
                intent_verb=result.intent_verb,
                intent_target=result.intent_target,
                reason=result.reason,
                reason_detail=result.reason_detail,
                acm_version=result.acm_version,
                timestamp=result.timestamp,
                correlation_id=result.correlation_id,
                next_hop=result.next_hop,
                correction_plan=correction_dict,
            )

        except NoValidCorrectionError:
            # FAIL CLOSED — no correction exists for this denial
            # Log and return result without correction (or with error indicator)
            self._audit.log_no_valid_correction(
                result.agent_gid,
                result.reason.value,
            )
            # Return result with error in correction_plan
            return EvaluationResult(
                decision=result.decision,
                agent_gid=result.agent_gid,
                intent_verb=result.intent_verb,
                intent_target=result.intent_target,
                reason=DenialReason.DIGGI_NO_VALID_CORRECTION,
                reason_detail=f"Original denial: {result.reason.value}. No correction mapping exists.",
                acm_version=result.acm_version,
                timestamp=result.timestamp,
                correlation_id=result.correlation_id,
                next_hop=result.next_hop,
                correction_plan=None,
            )

    def evaluate(self, intent: AgentIntent) -> EvaluationResult:
        """Evaluate an intent against ACM, governance checklist, and DRCP.

        This is the main enforcement method. All agent actions must pass
        through here before execution.

        Evaluation order:
        1. Atlas domain boundary check (GID-11 only)
        2. DRCP: Check if Diggy is attempting forbidden verb
        3. DRCP: Check if agent is retrying after denial
        4. Chain-of-command check (for EXECUTE/BLOCK/APPROVE)
        5. ACM capability evaluation
        6. DRCP: Apply routing for denials
        7. Audit logging

        Args:
            intent: The agent intent to evaluate

        Returns:
            EvaluationResult with ALLOW or DENY decision

        Raises:
            ALEXMiddlewareError: If middleware is not initialized
            IntentDeniedError: If intent is denied and raise_on_denial is True
        """
        if not self._initialized or self._evaluator is None:
            raise ALEXMiddlewareError("ALEX middleware not initialized. Call initialize() first.")

        # Gate 0: Atlas domain boundary enforcement
        atlas_result = self._check_atlas_domain_violation(intent)
        if atlas_result is not None:
            # Attach correction plan (DCC)
            atlas_result = self._attach_correction_plan(atlas_result)
            self._audit.log_decision(atlas_result)
            if self._config.raise_on_denial:
                raise IntentDeniedError(atlas_result)
            return atlas_result

        # Gate 0a: DRCP — Diggy forbidden verbs
        diggy_result = self._check_drcp_diggy_forbidden(intent)
        if diggy_result is not None:
            # Attach correction plan (DCC)
            diggy_result = self._attach_correction_plan(diggy_result)
            self._audit.log_decision(diggy_result)
            if self._config.raise_on_denial:
                raise IntentDeniedError(diggy_result)
            return diggy_result

        # Gate 0b: DRCP — Retry after deny
        retry_result = self._check_drcp_retry_after_deny(intent)
        if retry_result is not None:
            # Attach correction plan (DCC)
            retry_result = self._attach_correction_plan(retry_result)
            self._audit.log_decision(retry_result)
            if self._config.raise_on_denial:
                raise IntentDeniedError(retry_result)
            return retry_result

        # Gate 1: Chain-of-command enforcement
        coc_result = self._check_chain_of_command(intent)
        if coc_result is not None:
            # Apply DRCP routing
            coc_result = self._apply_drcp_routing(coc_result)
            # Attach correction plan (DCC)
            coc_result = self._attach_correction_plan(coc_result)
            self._audit.log_decision(coc_result)
            if self._config.raise_on_denial:
                raise IntentDeniedError(coc_result)
            return coc_result

        # Gate 2+: ACM capability evaluation
        result = self._evaluator.evaluate(intent)

        # Apply DRCP routing if denied
        if result.decision == ACMDecision.DENY:
            result = self._apply_drcp_routing(result)
            # Attach correction plan (DCC)
            result = self._attach_correction_plan(result)

        # Log the decision
        if self._config.log_all_decisions or result.decision == ACMDecision.DENY:
            self._audit.log_decision(result)

        # Raise on denial if configured
        if result.decision == ACMDecision.DENY and self._config.raise_on_denial:
            raise IntentDeniedError(result)

        return result

    def evaluate_dict(self, intent_data: Dict[str, Any]) -> EvaluationResult:
        """Evaluate an intent from raw dictionary.

        Convenience method that parses the intent first.

        Args:
            intent_data: Raw intent dictionary

        Returns:
            EvaluationResult with ALLOW or DENY decision
        """
        if not self._initialized or self._evaluator is None:
            raise ALEXMiddlewareError("ALEX middleware not initialized. Call initialize() first.")

        result = self._evaluator.evaluate_dict(intent_data)

        # Log the decision
        if self._config.log_all_decisions or result.decision == ACMDecision.DENY:
            self._audit.log_decision(result)

        # Raise on denial if configured
        if result.decision == ACMDecision.DENY and self._config.raise_on_denial:
            raise IntentDeniedError(result)

        return result

    def guard(
        self,
        agent_gid: str,
        verb: str | IntentVerb,
        target: str,
        scope: str | None = None,
        metadata: Dict[str, str] | None = None,
    ) -> EvaluationResult:
        """Convenience method to guard an action with minimal boilerplate.

        Args:
            agent_gid: Agent GID
            verb: Capability verb
            target: Target resource
            scope: Optional scope
            metadata: Optional metadata

        Returns:
            EvaluationResult with ALLOW or DENY decision
        """
        from core.governance.intent_schema import create_intent

        intent = create_intent(
            agent_gid=agent_gid,
            verb=verb,
            target=target,
            scope=scope,
            metadata=metadata,
        )
        return self.evaluate(intent)

    def evaluate_envelope(
        self,
        intent: AgentIntent,
        allowed_tools: list[str] | None = None,
    ) -> GatewayDecisionEnvelope:
        """Evaluate an intent and return a Canonical Decision Envelope (CDE).

        This is the PRIMARY method for downstream consumers.
        Returns a versioned, stable envelope — no internal structures leaked.

        PAC-GATEWAY-01: All consumers should use this method.

        Args:
            intent: The agent intent to evaluate
            allowed_tools: Optional list of tools to allow on ALLOW decision

        Returns:
            GatewayDecisionEnvelope (CDE v1)

        Raises:
            ALEXMiddlewareError: If middleware is not initialized
        """
        # Get the internal result (may raise IntentDeniedError if configured)
        # Temporarily disable raise_on_denial to get the result
        original_raise = self._config.raise_on_denial
        self._config = MiddlewareConfig(
            fail_closed_on_invalid_manifest=self._config.fail_closed_on_invalid_manifest,
            fail_closed_on_unknown_agent=self._config.fail_closed_on_unknown_agent,
            log_all_decisions=self._config.log_all_decisions,
            raise_on_denial=False,  # Don't raise, we need the result
            require_checklist=self._config.require_checklist,
            enforce_chain_of_command=self._config.enforce_chain_of_command,
            enforce_drcp=self._config.enforce_drcp,
            enforce_dcc=self._config.enforce_dcc,
            enforce_atlas_scope=self._config.enforce_atlas_scope,
        )

        try:
            result = self.evaluate(intent)
        finally:
            # Restore original config
            self._config = MiddlewareConfig(
                fail_closed_on_invalid_manifest=self._config.fail_closed_on_invalid_manifest,
                fail_closed_on_unknown_agent=self._config.fail_closed_on_unknown_agent,
                log_all_decisions=self._config.log_all_decisions,
                raise_on_denial=original_raise,
                require_checklist=self._config.require_checklist,
                enforce_chain_of_command=self._config.enforce_chain_of_command,
                enforce_drcp=self._config.enforce_drcp,
                enforce_dcc=self._config.enforce_dcc,
                enforce_atlas_scope=self._config.enforce_atlas_scope,
            )

        # Convert to CDE
        return create_envelope_from_result(result, allowed_tools)

    def guard_envelope(
        self,
        agent_gid: str,
        verb: str | IntentVerb,
        target: str,
        scope: str | None = None,
        metadata: Dict[str, str] | None = None,
        allowed_tools: list[str] | None = None,
    ) -> GatewayDecisionEnvelope:
        """Guard an action and return a CDE (convenience method).

        PAC-GATEWAY-01: Primary API for downstream consumers.

        Args:
            agent_gid: Agent GID
            verb: Capability verb
            target: Target resource
            scope: Optional scope
            metadata: Optional metadata
            allowed_tools: Optional list of tools to allow on ALLOW decision

        Returns:
            GatewayDecisionEnvelope (CDE v1)
        """
        from core.governance.intent_schema import create_intent

        intent = create_intent(
            agent_gid=agent_gid,
            verb=verb,
            target=target,
            scope=scope,
            metadata=metadata,
        )
        return self.evaluate_envelope(intent, allowed_tools)


# Module-level singleton
_middleware_instance: Optional[ALEXMiddleware] = None


def get_alex_middleware(config: MiddlewareConfig | None = None) -> ALEXMiddleware:
    """Get or create the ALEX middleware singleton.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        The ALEX middleware instance
    """
    global _middleware_instance
    if _middleware_instance is None:
        _middleware_instance = ALEXMiddleware(config)
    return _middleware_instance


def initialize_alex() -> None:
    """Initialize the ALEX middleware singleton.

    Call this at application startup to load all ACM manifests.

    Raises:
        ALEXMiddlewareError: If initialization fails
    """
    middleware = get_alex_middleware()
    if not middleware.is_initialized():
        middleware.initialize()


def guard_action(
    agent_gid: str,
    verb: str | IntentVerb,
    target: str,
    scope: str | None = None,
) -> EvaluationResult:
    """Guard an action through ALEX (convenience function).

    Args:
        agent_gid: Agent GID
        verb: Capability verb
        target: Target resource
        scope: Optional scope

    Returns:
        EvaluationResult

    Raises:
        IntentDeniedError: If action is denied
    """
    middleware = get_alex_middleware()
    if not middleware.is_initialized():
        middleware.initialize()
    return middleware.guard(agent_gid, verb, target, scope)


def guard_action_envelope(
    agent_gid: str,
    verb: str | IntentVerb,
    target: str,
    scope: str | None = None,
    allowed_tools: list[str] | None = None,
) -> GatewayDecisionEnvelope:
    """Guard an action and return a CDE (convenience function).

    PAC-GATEWAY-01: Primary API for downstream consumers.

    Args:
        agent_gid: Agent GID
        verb: Capability verb
        target: Target resource
        scope: Optional scope
        allowed_tools: Optional list of tools to allow on ALLOW decision

    Returns:
        GatewayDecisionEnvelope (CDE v1)
    """
    middleware = get_alex_middleware()
    if not middleware.is_initialized():
        middleware.initialize()
    return middleware.guard_envelope(agent_gid, verb, target, scope, allowed_tools=allowed_tools)
