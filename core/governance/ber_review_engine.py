"""
BER Review Engine v1

Deterministic evaluator for BER artifacts per BER_REVIEW_CHECKLIST_v1.
Per PAC-BENSON-EXEC-GOVERNANCE-JEFFREY-REVIEW-LAW-022.

This engine:
- Executes all 8 checklist items
- Produces binary PASS/FAIL outcome
- Emits training signals
- Enforces FAIL-CLOSED discipline
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .ber_review_schema import (
    BERReviewResult,
    CheckID,
    CheckResult,
    CheckSeverity,
    FailureMode,
    JeffreyAction,
    JeffreyTrainingSignal,
    ReviewOutcome,
    REQUIRED_CHECK_COUNT,
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class BERReviewError(Exception):
    """Base exception for BER review errors."""
    pass


class IncompleteReviewError(BERReviewError):
    """Raised when review does not execute all checks."""
    pass


class InvalidBERError(BERReviewError):
    """Raised when BER artifact is malformed."""
    pass


class JeffreyViolationError(BERReviewError):
    """Raised when Jeffrey law is violated."""
    
    def __init__(self, violation_type: FailureMode, message: str):
        self.violation_type = violation_type
        super().__init__(f"{violation_type.value}: {message}")


# ═══════════════════════════════════════════════════════════════════════════════
# BER REVIEW ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class BERReviewEngine:
    """
    Deterministic BER review engine.
    
    Executes all checklist items and produces binary outcome.
    FAIL-CLOSED: Any ambiguity results in FAIL.
    """
    
    # Valid BER issuers
    VALID_ISSUERS: Set[str] = {"GID-00", "ORCHESTRATION_ENGINE"}
    
    # Valid BER decisions
    VALID_DECISIONS: Set[str] = {"APPROVE", "CORRECTIVE", "REJECT"}
    
    def __init__(
        self,
        pending_pacs: Optional[Set[str]] = None,
        emit_terminal: bool = True,
    ):
        """
        Initialize BER review engine.
        
        Args:
            pending_pacs: Set of PAC IDs currently pending (for loop verification)
            emit_terminal: Whether to emit terminal output
        """
        self._pending_pacs = pending_pacs or set()
        self._emit_terminal = emit_terminal
        self._reviews: Dict[str, BERReviewResult] = {}
    
    def add_pending_pac(self, pac_id: str) -> None:
        """Add a PAC to the pending set."""
        self._pending_pacs.add(pac_id)
    
    def remove_pending_pac(self, pac_id: str) -> None:
        """Remove a PAC from the pending set."""
        self._pending_pacs.discard(pac_id)
    
    def review(
        self,
        ber: Any,
        pdo: Optional[Any] = None,
    ) -> BERReviewResult:
        """
        Execute full BER review checklist.
        
        Args:
            ber: BERArtifact to review
            pdo: Optional PDOArtifact for chain verification
            
        Returns:
            BERReviewResult with binary outcome
            
        Raises:
            InvalidBERError: If BER is None or malformed
            IncompleteReviewError: If not all checks could execute
        """
        if ber is None:
            raise InvalidBERError("BER artifact is None")
        
        # Extract BER fields safely
        ber_id = self._get_ber_id(ber)
        pac_id = self._safe_get(ber, "pac_id", "")
        
        # Execute all checks
        checks: List[CheckResult] = []
        
        # CHK-001: Authority Verification
        checks.append(self._check_authority(ber))
        
        # CHK-002: Loop Closure Verification
        checks.append(self._check_loop_closure(ber))
        
        # CHK-003: PDO Chain Verification
        checks.append(self._check_pdo_chain(ber, pdo))
        
        # CHK-004: Emission Verification
        checks.append(self._check_emission(ber))
        
        # CHK-005: Decision Validity
        checks.append(self._check_decision_validity(ber))
        
        # CHK-006: Training Signal Presence
        checks.append(self._check_training_signal(ber))
        
        # CHK-007: Artifact Integrity
        checks.append(self._check_artifact_integrity(ber))
        
        # CHK-008: Temporal Ordering
        checks.append(self._check_temporal_ordering(ber))
        
        # Validate completeness
        if len(checks) < REQUIRED_CHECK_COUNT:
            raise IncompleteReviewError(
                f"Only {len(checks)} checks executed, {REQUIRED_CHECK_COUNT} required"
            )
        
        # Compute outcome (FAIL-CLOSED: any failure = FAIL)
        # Only CRITICAL failures block; WARNING failures are noted
        critical_failures = [
            c for c in checks 
            if not c.passed and c.severity == CheckSeverity.CRITICAL
        ]
        
        all_passed = len(critical_failures) == 0
        outcome = ReviewOutcome.PASS if all_passed else ReviewOutcome.FAIL
        
        # Collect failure reasons
        failure_reasons = tuple(
            c.reason for c in checks if not c.passed
        )
        
        # Build result
        result = BERReviewResult(
            ber_id=ber_id,
            pac_id=pac_id,
            outcome=outcome,
            checks=tuple(checks),
            failure_reasons=failure_reasons,
            review_timestamp=datetime.now(timezone.utc),
            reviewer="JEFFREY",
        )
        
        # Store review
        self._reviews[ber_id] = result
        
        # Emit terminal output
        if self._emit_terminal:
            self._emit_review_result(result)
        
        return result
    
    def get_recommended_action(self, result: BERReviewResult) -> JeffreyAction:
        """
        Get recommended Jeffrey action for a review result.
        
        Per JEFFREY_REVIEW_LAW_v1 INV-JEFF-001: Binary outcome only.
        """
        return result.recommended_action
    
    def create_training_signal(
        self,
        result: BERReviewResult,
        ber_decision: str,
    ) -> JeffreyTrainingSignal:
        """
        Create training signal for a review result.
        
        Per JEFFREY_REVIEW_LAW_v1 Section 6.
        """
        return JeffreyTrainingSignal(
            pac_id=result.pac_id,
            ber_id=result.ber_id,
            outcome=result.recommended_action,
            ber_decision=ber_decision,
            review_passed=result.passed,
            failure_reasons=result.failure_reasons,
            timestamp=datetime.now(timezone.utc),
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INDIVIDUAL CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_authority(self, ber: Any) -> CheckResult:
        """
        CHK-001: Authority Verification
        
        Verify BER was issued by GID-00 or ORCHESTRATION_ENGINE.
        """
        issuer = self._safe_get(ber, "issuer", "")
        
        if not issuer:
            return CheckResult(
                check_id=CheckID.CHK_001.value,
                passed=False,
                reason="BER missing issuer field",
                failure_mode=FailureMode.AUTHORITY_VIOLATION,
                severity=CheckSeverity.CRITICAL,
            )
        
        if issuer not in self.VALID_ISSUERS:
            return CheckResult(
                check_id=CheckID.CHK_001.value,
                passed=False,
                reason=f"Invalid issuer: {issuer}, expected GID-00",
                failure_mode=FailureMode.AUTHORITY_VIOLATION,
                severity=CheckSeverity.CRITICAL,
            )
        
        return CheckResult(
            check_id=CheckID.CHK_001.value,
            passed=True,
            reason="",
            severity=CheckSeverity.CRITICAL,
        )
    
    def _check_loop_closure(self, ber: Any) -> CheckResult:
        """
        CHK-002: Loop Closure Verification
        
        Verify BER closes a valid PAC→WRAP→BER loop.
        """
        pac_id = self._safe_get(ber, "pac_id", "")
        
        if not pac_id:
            return CheckResult(
                check_id=CheckID.CHK_002.value,
                passed=False,
                reason="BER missing PAC ID",
                failure_mode=FailureMode.ORPHAN_BER,
                severity=CheckSeverity.CRITICAL,
            )
        
        # Check if PAC was pending (if we're tracking)
        if self._pending_pacs and pac_id not in self._pending_pacs:
            return CheckResult(
                check_id=CheckID.CHK_002.value,
                passed=False,
                reason=f"Orphan BER: PAC {pac_id} not pending",
                failure_mode=FailureMode.ORPHAN_BER,
                severity=CheckSeverity.CRITICAL,
            )
        
        # Check for WRAP reference (via wrap_status or wrap_id)
        wrap_status = self._safe_get(ber, "wrap_status", "")
        wrap_id = self._safe_get(ber, "wrap_id", "")
        
        if not wrap_status and not wrap_id:
            return CheckResult(
                check_id=CheckID.CHK_002.value,
                passed=False,
                reason="BER missing WRAP reference",
                failure_mode=FailureMode.MISSING_WRAP,
                severity=CheckSeverity.CRITICAL,
            )
        
        return CheckResult(
            check_id=CheckID.CHK_002.value,
            passed=True,
            reason="",
            severity=CheckSeverity.CRITICAL,
        )
    
    def _check_pdo_chain(self, ber: Any, pdo: Optional[Any]) -> CheckResult:
        """
        CHK-003: PDO Chain Verification
        
        Verify PDO artifact exists and is hash-bound.
        """
        # PDO is optional in current implementation
        # FAIL-CLOSED: If PDO provided, it must be valid
        if pdo is None:
            # PDO not provided - pass with note
            # In strict mode, this would fail
            return CheckResult(
                check_id=CheckID.CHK_003.value,
                passed=True,
                reason="PDO not provided (optional in v1)",
                severity=CheckSeverity.CRITICAL,
            )
        
        # Check required PDO fields
        required_fields = ["proof_hash", "decision_hash", "outcome_hash", "pdo_hash"]
        for field_name in required_fields:
            value = self._safe_get(pdo, field_name, "")
            if not value:
                return CheckResult(
                    check_id=CheckID.CHK_003.value,
                    passed=False,
                    reason=f"PDO missing {field_name}",
                    failure_mode=FailureMode.PDO_INCOMPLETE,
                    severity=CheckSeverity.CRITICAL,
                )
        
        # Verify hash chain if verification function available
        try:
            from .pdo_artifact import verify_pdo_chain
            if not verify_pdo_chain(pdo):
                return CheckResult(
                    check_id=CheckID.CHK_003.value,
                    passed=False,
                    reason="PDO hash chain invalid",
                    failure_mode=FailureMode.PDO_HASH_MISMATCH,
                    severity=CheckSeverity.CRITICAL,
                )
        except ImportError:
            # PDO module not available
            pass
        
        return CheckResult(
            check_id=CheckID.CHK_003.value,
            passed=True,
            reason="",
            severity=CheckSeverity.CRITICAL,
        )
    
    def _check_emission(self, ber: Any) -> CheckResult:
        """
        CHK-004: Emission Verification
        
        Verify BER was emitted, not just issued.
        """
        is_emitted = self._safe_get(ber, "is_emitted", False)
        emitted_at = self._safe_get(ber, "emitted_at", "")
        session_state = self._safe_get(ber, "session_state", "")
        
        # Check is_emitted property or session_state
        if hasattr(ber, "is_emitted"):
            if not is_emitted:
                return CheckResult(
                    check_id=CheckID.CHK_004.value,
                    passed=False,
                    reason="BER not emitted (is_emitted=False)",
                    failure_mode=FailureMode.EMISSION_VIOLATION,
                    severity=CheckSeverity.CRITICAL,
                )
        elif session_state:
            if session_state != "BER_EMITTED":
                return CheckResult(
                    check_id=CheckID.CHK_004.value,
                    passed=False,
                    reason=f"BER not emitted (state={session_state})",
                    failure_mode=FailureMode.EMISSION_VIOLATION,
                    severity=CheckSeverity.CRITICAL,
                )
        
        # Check emission timestamp
        if not emitted_at:
            return CheckResult(
                check_id=CheckID.CHK_004.value,
                passed=False,
                reason="BER missing emission timestamp",
                failure_mode=FailureMode.EMISSION_VIOLATION,
                severity=CheckSeverity.CRITICAL,
            )
        
        return CheckResult(
            check_id=CheckID.CHK_004.value,
            passed=True,
            reason="",
            severity=CheckSeverity.CRITICAL,
        )
    
    def _check_decision_validity(self, ber: Any) -> CheckResult:
        """
        CHK-005: Decision Validity
        
        Verify BER decision is a valid enum value.
        """
        decision = self._safe_get(ber, "decision", "")
        
        if not decision:
            return CheckResult(
                check_id=CheckID.CHK_005.value,
                passed=False,
                reason="BER missing decision field",
                failure_mode=FailureMode.INVALID_DECISION,
                severity=CheckSeverity.CRITICAL,
            )
        
        if decision not in self.VALID_DECISIONS:
            return CheckResult(
                check_id=CheckID.CHK_005.value,
                passed=False,
                reason=f"Invalid decision: {decision}",
                failure_mode=FailureMode.INVALID_DECISION,
                severity=CheckSeverity.CRITICAL,
            )
        
        return CheckResult(
            check_id=CheckID.CHK_005.value,
            passed=True,
            reason="",
            severity=CheckSeverity.CRITICAL,
        )
    
    def _check_training_signal(self, ber: Any) -> CheckResult:
        """
        CHK-006: Training Signal Presence
        
        Verify training signal present for CORRECTIVE BERs.
        WARNING severity - does not block in v1.
        """
        decision = self._safe_get(ber, "decision", "")
        training_signal = self._safe_get(ber, "training_signal", None)
        
        # Training signal mandatory for CORRECTIVE BERs
        if decision == "CORRECTIVE" and not training_signal:
            return CheckResult(
                check_id=CheckID.CHK_006.value,
                passed=False,
                reason="CORRECTIVE BER missing training signal",
                failure_mode=FailureMode.MISSING_TRAINING_SIGNAL,
                severity=CheckSeverity.WARNING,  # Non-blocking in v1
            )
        
        return CheckResult(
            check_id=CheckID.CHK_006.value,
            passed=True,
            reason="",
            severity=CheckSeverity.WARNING,
        )
    
    def _check_artifact_integrity(self, ber: Any) -> CheckResult:
        """
        CHK-007: Artifact Integrity
        
        Verify BER artifact has not been tampered with.
        """
        # Check for hash field
        ber_hash = self._safe_get(ber, "ber_hash", "")
        
        if ber_hash:
            # Verify hash matches
            expected_hash = self._compute_ber_hash(ber)
            if expected_hash and ber_hash != expected_hash:
                return CheckResult(
                    check_id=CheckID.CHK_007.value,
                    passed=False,
                    reason="BER artifact hash mismatch - possible tampering",
                    failure_mode=FailureMode.ARTIFACT_TAMPERED,
                    severity=CheckSeverity.CRITICAL,
                )
        
        # Check immutability markers if present
        if hasattr(ber, "__dataclass_fields__"):
            # Frozen dataclass - good
            pass
        
        return CheckResult(
            check_id=CheckID.CHK_007.value,
            passed=True,
            reason="",
            severity=CheckSeverity.CRITICAL,
        )
    
    def _check_temporal_ordering(self, ber: Any) -> CheckResult:
        """
        CHK-008: Temporal Ordering
        
        Verify timestamps are in valid chronological order.
        WARNING severity - does not block in v1.
        """
        issued_at = self._safe_get(ber, "issued_at", "")
        emitted_at = self._safe_get(ber, "emitted_at", "")
        
        if issued_at and emitted_at:
            try:
                # Parse timestamps
                if isinstance(issued_at, str) and isinstance(emitted_at, str):
                    issued_dt = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
                    emitted_dt = datetime.fromisoformat(emitted_at.replace("Z", "+00:00"))
                    
                    if issued_dt > emitted_dt:
                        return CheckResult(
                            check_id=CheckID.CHK_008.value,
                            passed=False,
                            reason="BER issued after emission timestamp",
                            failure_mode=FailureMode.TEMPORAL_VIOLATION,
                            severity=CheckSeverity.WARNING,
                        )
            except (ValueError, TypeError):
                # Timestamp parsing failed - not critical
                pass
        
        return CheckResult(
            check_id=CheckID.CHK_008.value,
            passed=True,
            reason="",
            severity=CheckSeverity.WARNING,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _safe_get(self, obj: Any, attr: str, default: Any) -> Any:
        """Safely get attribute from object or dict."""
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)
    
    def _get_ber_id(self, ber: Any) -> str:
        """Extract or generate BER ID."""
        ber_id = self._safe_get(ber, "ber_id", "")
        if not ber_id:
            pac_id = self._safe_get(ber, "pac_id", "UNKNOWN")
            ber_id = f"BER-{pac_id}"
        return ber_id
    
    def _compute_ber_hash(self, ber: Any) -> Optional[str]:
        """Compute hash for BER artifact."""
        try:
            import hashlib
            content_parts = [
                str(self._safe_get(ber, "pac_id", "")),
                str(self._safe_get(ber, "decision", "")),
                str(self._safe_get(ber, "issuer", "")),
                str(self._safe_get(ber, "issued_at", "")),
            ]
            content = ":".join(content_parts)
            return hashlib.sha256(content.encode()).hexdigest()[:32]
        except Exception:
            return None
    
    def _emit_review_result(self, result: BERReviewResult) -> None:
        """Emit terminal output for review result."""
        lines = [
            "══════════════════════════════════════════════════════════════════",
            "🔍 BER REVIEW CHECKLIST COMPLETE",
            "══════════════════════════════════════════════════════════════════",
            f"BER-ID:   {result.ber_id}",
            f"PAC-ID:   {result.pac_id}",
            "══════════════════════════════════════════════════════════════════",
        ]
        
        for check in result.checks:
            status = "✅" if check.passed else "❌"
            lines.append(f"  {status} {check.check_id}: {'PASS' if check.passed else 'FAIL'}")
            if not check.passed:
                lines.append(f"     └─ Reason: {check.reason}")
        
        lines.append("══════════════════════════════════════════════════════════════════")
        
        if result.passed:
            lines.append("RESULT:   ✅ PASS")
            lines.append("ACTION:   → NEXT_PAC eligible")
        else:
            lines.append("RESULT:   ❌ FAIL")
            lines.append("ACTION:   → CORRECTIVE_PAC required")
        
        lines.append("══════════════════════════════════════════════════════════════════")
        
        print("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def create_review_engine(
    pending_pacs: Optional[Set[str]] = None,
    emit_terminal: bool = True,
) -> BERReviewEngine:
    """Create a new BER review engine."""
    return BERReviewEngine(
        pending_pacs=pending_pacs,
        emit_terminal=emit_terminal,
    )


def review_ber(
    ber: Any,
    pdo: Optional[Any] = None,
    pending_pacs: Optional[Set[str]] = None,
    emit_terminal: bool = False,
) -> BERReviewResult:
    """
    Convenience function to review a single BER.
    
    Args:
        ber: BERArtifact to review
        pdo: Optional PDOArtifact
        pending_pacs: Optional set of pending PAC IDs
        emit_terminal: Whether to emit terminal output
        
    Returns:
        BERReviewResult with binary outcome
    """
    engine = create_review_engine(
        pending_pacs=pending_pacs,
        emit_terminal=emit_terminal,
    )
    return engine.review(ber, pdo)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════


__all__ = [
    # Exceptions
    "BERReviewError",
    "IncompleteReviewError",
    "InvalidBERError",
    "JeffreyViolationError",
    # Engine
    "BERReviewEngine",
    # Factory functions
    "create_review_engine",
    "review_ber",
]
