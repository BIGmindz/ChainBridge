#!/usr/bin/env python3
"""Security Invariant Drills Module.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Sam (GID-06) — Security & Threat Engineer           ║
║ EXECUTING COLOR: 🟥 DARK RED                                         ║
║ PAC: PAC-SAM-G1-PHASE-2-SECURITY-INVARIANT-HARDENING-01              ║
╚══════════════════════════════════════════════════════════════════════╝

This module defines adversarial drills that attempt to violate security
invariants. All drills MUST be blocked for the system to be considered
secure.

DRILL CATEGORIES:
  - Unauthorized state mutation (SI-01)
  - Authority spoofing (SI-02)
  - Replay attacks (SI-03)
  - Governance downgrade (SI-04)
  - Unsigned corrections (SI-05)
  - Registry bypass (SI-06)
  - Hard gate bypass (SI-07)
  - Mixed authority (SI-08)

DOCTRINE:
  - All drills attempt malicious actions
  - All drills MUST be blocked
  - Any passing drill = SECURITY FAILURE
  - Evidence captured for all outcomes

Author: Sam (GID-06) — Security & Threat Engineer
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from tools.security.security_invariants import (
    SecurityInvariantID,
    SecurityInvariantValidator,
    SecurityInvariantViolation,
    UnauthorizedStateMutationError,
    UnverifiableAuthorityError,
    ReplayDetectionError,
    GovernanceDowngradeError,
    UnsignedCorrectionError,
    RegistryMismatchError,
    HardGateBypassError,
    MixedAuthorityError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DRILL RESULT TYPES
# =============================================================================


class DrillOutcome(str, Enum):
    """Expected and actual drill outcomes."""

    BLOCKED = "BLOCKED"  # Drill was blocked (EXPECTED for security drills)
    PASSED = "PASSED"    # Drill passed through (FAILURE for security drills)
    ERROR = "ERROR"      # Drill encountered unexpected error


@dataclass(frozen=True)
class SecurityDrillResult:
    """Result of a security drill execution."""

    drill_id: str
    invariant_id: SecurityInvariantID
    drill_name: str
    scenario: str
    expected_outcome: DrillOutcome
    actual_outcome: DrillOutcome
    blocked: bool
    error_message: Optional[str] = None
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success(self) -> bool:
        """A security drill succeeds when malicious action is BLOCKED."""
        return self.expected_outcome == self.actual_outcome and self.blocked

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "security_drill_execution",
            "drill_id": self.drill_id,
            "invariant_id": self.invariant_id.value,
            "drill_name": self.drill_name,
            "scenario": self.scenario,
            "expected_outcome": self.expected_outcome.value,
            "actual_outcome": self.actual_outcome.value,
            "blocked": self.blocked,
            "success": self.success,
            "error_message": self.error_message,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class SecurityDrillSuiteResult:
    """Result of running all security drills."""

    total_drills: int = 0
    blocked_drills: int = 0
    passed_drills: int = 0  # BAD - means security violation
    error_drills: int = 0
    results: List[SecurityDrillResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def all_blocked(self) -> bool:
        """All drills must be blocked for security."""
        return self.blocked_drills == self.total_drills and self.passed_drills == 0

    @property
    def verdict(self) -> str:
        """Security verdict."""
        if self.all_blocked:
            return "SECURE"
        elif self.passed_drills > 0:
            return "VULNERABLE"
        else:
            return "ERROR"

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "security_drill_suite_result",
            "total_drills": self.total_drills,
            "blocked_drills": self.blocked_drills,
            "passed_drills": self.passed_drills,
            "error_drills": self.error_drills,
            "all_blocked": self.all_blocked,
            "verdict": self.verdict,
            "timestamp": self.timestamp,
            "drill_results": [r.to_audit_log() for r in self.results],
        }


# =============================================================================
# SECURITY DRILL DEFINITIONS
# =============================================================================


class SecurityInvariantDrills:
    """Adversarial drills that test security invariants.

    DOCTRINE:
    - All drills attempt malicious actions
    - All drills MUST be blocked
    - Success = malicious action blocked
    - Failure = malicious action succeeded
    """

    def __init__(self):
        """Initialize drill runner."""
        self.validator = SecurityInvariantValidator()
        self._results: List[SecurityDrillResult] = []

    # -------------------------------------------------------------------------
    # SI-01: Unauthorized State Mutation Drills
    # -------------------------------------------------------------------------

    def drill_si01_unregistered_actor(self) -> SecurityDrillResult:
        """Attempt state mutation by unregistered actor."""
        drill_id = "SI-01-DRILL-01"

        try:
            self.validator.check_state_mutation_authority(
                actor="GID-99",  # Invalid GID
                target_state="governance.lock_level",
                required_authority="GOVERNANCE",
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_01,
                drill_name="Unregistered Actor Mutation",
                scenario="Unregistered GID-99 attempts state mutation",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"actor": "GID-99"},
            )
        except UnauthorizedStateMutationError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_01,
                drill_name="Unregistered Actor Mutation",
                scenario="Unregistered GID-99 attempts state mutation",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    def drill_si01_wrong_authority(self) -> SecurityDrillResult:
        """Attempt state mutation with wrong authority."""
        drill_id = "SI-01-DRILL-02"

        try:
            self.validator.check_state_mutation_authority(
                actor="GID-03",  # Ruby - UI authority
                target_state="security.threat_model",
                required_authority="SECURITY",  # Wrong authority
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_01,
                drill_name="Wrong Authority Mutation",
                scenario="UI agent attempts security state mutation",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"actor": "GID-03", "actor_authority": "UI"},
            )
        except UnauthorizedStateMutationError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_01,
                drill_name="Wrong Authority Mutation",
                scenario="UI agent attempts security state mutation",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-02: Authority Spoofing Drills
    # -------------------------------------------------------------------------

    def drill_si02_fake_gid(self) -> SecurityDrillResult:
        """Attempt to claim non-existent GID."""
        drill_id = "SI-02-DRILL-01"

        try:
            self.validator.check_authority_verifiable(
                claimed_gid="GID-100",  # Does not exist
                claimed_name="Hacker",
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_02,
                drill_name="Fake GID Claim",
                scenario="Claim non-existent GID-100",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"claimed_gid": "GID-100"},
            )
        except UnverifiableAuthorityError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_02,
                drill_name="Fake GID Claim",
                scenario="Claim non-existent GID-100",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    def drill_si02_name_mismatch(self) -> SecurityDrillResult:
        """Attempt to claim GID with wrong name."""
        drill_id = "SI-02-DRILL-02"

        try:
            self.validator.check_authority_verifiable(
                claimed_gid="GID-06",  # Sam's GID
                claimed_name="NotSam",  # Wrong name
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_02,
                drill_name="Name Mismatch Claim",
                scenario="Claim GID-06 with wrong name",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"claimed_gid": "GID-06", "claimed_name": "NotSam"},
            )
        except UnverifiableAuthorityError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_02,
                drill_name="Name Mismatch Claim",
                scenario="Claim GID-06 with wrong name",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-03: Replay Attack Drills
    # -------------------------------------------------------------------------

    def drill_si03_replay_nonce(self) -> SecurityDrillResult:
        """Attempt to replay a nonce."""
        drill_id = "SI-03-DRILL-01"

        try:
            # First submission - should pass
            self.validator.check_replay_protection(
                artifact_id="PAC-001",
                nonce="unique-nonce-12345",
                timestamp="2024-01-01T00:00:00Z",
            )

            # Replay attempt - should be blocked
            self.validator.check_replay_protection(
                artifact_id="PAC-001",
                nonce="unique-nonce-12345",  # Same nonce
                timestamp="2024-01-01T00:00:01Z",
            )

            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_03,
                drill_name="Nonce Replay Attack",
                scenario="Replay same nonce twice",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"nonce": "unique-nonce-12345"},
            )
        except ReplayDetectionError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_03,
                drill_name="Nonce Replay Attack",
                scenario="Replay same nonce twice",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-04: Governance Downgrade Drills
    # -------------------------------------------------------------------------

    def drill_si04_downgrade_locked(self) -> SecurityDrillResult:
        """Attempt to downgrade from LOCKED to SOFT_GATED."""
        drill_id = "SI-04-DRILL-01"

        try:
            self.validator.check_governance_level(
                current_level="LOCKED",
                requested_level="SOFT_GATED",
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_04,
                drill_name="Governance Downgrade Attack",
                scenario="Downgrade LOCKED to SOFT_GATED",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"current": "LOCKED", "requested": "SOFT_GATED"},
            )
        except GovernanceDowngradeError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_04,
                drill_name="Governance Downgrade Attack",
                scenario="Downgrade LOCKED to SOFT_GATED",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    def drill_si04_invalid_level(self) -> SecurityDrillResult:
        """Attempt to set invalid governance level."""
        drill_id = "SI-04-DRILL-02"

        try:
            self.validator.check_governance_level(
                current_level="HARD_GATED",
                requested_level="DISABLED",  # Invalid level
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_04,
                drill_name="Invalid Governance Level",
                scenario="Set governance to invalid DISABLED",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"requested": "DISABLED"},
            )
        except GovernanceDowngradeError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_04,
                drill_name="Invalid Governance Level",
                scenario="Set governance to invalid DISABLED",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-05: Unsigned Correction Drills
    # -------------------------------------------------------------------------

    def drill_si05_no_signature(self) -> SecurityDrillResult:
        """Attempt correction closure without signature."""
        drill_id = "SI-05-DRILL-01"

        try:
            self.validator.check_correction_signature(
                correction_id="CORR-001",
                signature=None,  # No signature
                signer_gid=None,
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_05,
                drill_name="Unsigned Correction",
                scenario="Close correction without signature",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"correction_id": "CORR-001"},
            )
        except UnsignedCorrectionError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_05,
                drill_name="Unsigned Correction",
                scenario="Close correction without signature",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    def drill_si05_unregistered_signer(self) -> SecurityDrillResult:
        """Attempt correction closure with unregistered signer."""
        drill_id = "SI-05-DRILL-02"

        try:
            self.validator.check_correction_signature(
                correction_id="CORR-002",
                signature="fake-sig-123",
                signer_gid="GID-99",  # Unregistered
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_05,
                drill_name="Unregistered Signer",
                scenario="Correction signed by unregistered agent",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"signer_gid": "GID-99"},
            )
        except UnsignedCorrectionError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_05,
                drill_name="Unregistered Signer",
                scenario="Correction signed by unregistered agent",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-06: Registry Mismatch Drills
    # -------------------------------------------------------------------------

    def drill_si06_unregistered_executor(self) -> SecurityDrillResult:
        """Attempt PAC execution by unregistered agent."""
        drill_id = "SI-06-DRILL-01"

        try:
            self.validator.check_pac_registry_match(
                pac_id="PAC-TEST-001",
                executing_gid="GID-99",  # Unregistered
                declared_gid="GID-06",
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_06,
                drill_name="Unregistered Executor",
                scenario="Unregistered GID-99 executes PAC",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"executing_gid": "GID-99"},
            )
        except RegistryMismatchError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_06,
                drill_name="Unregistered Executor",
                scenario="Unregistered GID-99 executes PAC",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    def drill_si06_gid_mismatch(self) -> SecurityDrillResult:
        """Attempt PAC execution with GID mismatch."""
        drill_id = "SI-06-DRILL-02"

        try:
            self.validator.check_pac_registry_match(
                pac_id="PAC-TEST-002",
                executing_gid="GID-06",  # Sam
                declared_gid="GID-01",   # Cody's PAC
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_06,
                drill_name="GID Mismatch",
                scenario="Sam executes Cody's PAC",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"executing_gid": "GID-06", "declared_gid": "GID-01"},
            )
        except RegistryMismatchError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_06,
                drill_name="GID Mismatch",
                scenario="Sam executes Cody's PAC",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-07: Hard Gate Bypass Drills
    # -------------------------------------------------------------------------

    def drill_si07_bypass_attempt(self) -> SecurityDrillResult:
        """Attempt to bypass hard gate."""
        drill_id = "SI-07-DRILL-01"

        try:
            self.validator.check_hard_gate_enforcement(
                gate_id="GATE-SECURITY-001",
                gate_result="PASS",
                bypass_attempted=True,  # Bypass flag set
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_07,
                drill_name="Hard Gate Bypass",
                scenario="Bypass security gate directly",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"bypass_attempted": True},
            )
        except HardGateBypassError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_07,
                drill_name="Hard Gate Bypass",
                scenario="Bypass security gate directly",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    def drill_si07_invalid_result(self) -> SecurityDrillResult:
        """Attempt to accept invalid gate result."""
        drill_id = "SI-07-DRILL-02"

        try:
            self.validator.check_hard_gate_enforcement(
                gate_id="GATE-SECURITY-002",
                gate_result="FAIL",  # Failed gate
                bypass_attempted=False,
            )
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_07,
                drill_name="Invalid Gate Result",
                scenario="Accept failed gate result",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"gate_result": "FAIL"},
            )
        except HardGateBypassError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_07,
                drill_name="Invalid Gate Result",
                scenario="Accept failed gate result",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # SI-08: Mixed Authority Drills
    # -------------------------------------------------------------------------

    def drill_si08_mixed_authority(self) -> SecurityDrillResult:
        """Attempt execution with mixed authorities."""
        drill_id = "SI-08-DRILL-01"

        try:
            self.validator.check_single_authority({
                "executing_gid": "GID-06",  # SECURITY authority
                "declared_authority": "GOVERNANCE",  # Different authority
                "runtime_authority": "TESTING",  # Third authority
            })
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_08,
                drill_name="Mixed Authority Execution",
                scenario="Execution with 3 different authorities",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.PASSED,
                blocked=False,
                evidence={"authorities": ["SECURITY", "GOVERNANCE", "TESTING"]},
            )
        except MixedAuthorityError as e:
            return SecurityDrillResult(
                drill_id=drill_id,
                invariant_id=SecurityInvariantID.SI_08,
                drill_name="Mixed Authority Execution",
                scenario="Execution with 3 different authorities",
                expected_outcome=DrillOutcome.BLOCKED,
                actual_outcome=DrillOutcome.BLOCKED,
                blocked=True,
                error_message=str(e),
                evidence=e.evidence,
            )

    # -------------------------------------------------------------------------
    # Run All Drills
    # -------------------------------------------------------------------------

    def run_all_drills(self) -> SecurityDrillSuiteResult:
        """Run all security invariant drills.

        Returns:
            SecurityDrillSuiteResult with all outcomes
        """
        suite_result = SecurityDrillSuiteResult()

        # Get all drill methods
        drill_methods = [
            # SI-01 drills
            self.drill_si01_unregistered_actor,
            self.drill_si01_wrong_authority,
            # SI-02 drills
            self.drill_si02_fake_gid,
            self.drill_si02_name_mismatch,
            # SI-03 drills
            self.drill_si03_replay_nonce,
            # SI-04 drills
            self.drill_si04_downgrade_locked,
            self.drill_si04_invalid_level,
            # SI-05 drills
            self.drill_si05_no_signature,
            self.drill_si05_unregistered_signer,
            # SI-06 drills
            self.drill_si06_unregistered_executor,
            self.drill_si06_gid_mismatch,
            # SI-07 drills
            self.drill_si07_bypass_attempt,
            self.drill_si07_invalid_result,
            # SI-08 drills
            self.drill_si08_mixed_authority,
        ]

        for drill_method in drill_methods:
            # Reset validator state between drills
            self.validator.clear_registries()

            try:
                result = drill_method()
                suite_result.results.append(result)
                suite_result.total_drills += 1

                if result.blocked:
                    suite_result.blocked_drills += 1
                else:
                    suite_result.passed_drills += 1
                    logger.error(f"SECURITY FAILURE: {result.drill_id} - {result.drill_name}")

            except Exception as e:
                error_result = SecurityDrillResult(
                    drill_id=drill_method.__name__,
                    invariant_id=SecurityInvariantID.SI_01,  # Default
                    drill_name=drill_method.__name__,
                    scenario="Error during drill execution",
                    expected_outcome=DrillOutcome.BLOCKED,
                    actual_outcome=DrillOutcome.ERROR,
                    blocked=False,
                    error_message=str(e),
                )
                suite_result.results.append(error_result)
                suite_result.total_drills += 1
                suite_result.error_drills += 1
                logger.error(f"DRILL ERROR: {drill_method.__name__}: {e}")

        logger.info(
            f"Security Drill Suite Complete: "
            f"{suite_result.blocked_drills}/{suite_result.total_drills} blocked, "
            f"Verdict: {suite_result.verdict}"
        )

        return suite_result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def run_security_invariant_drills() -> SecurityDrillSuiteResult:
    """Run all security invariant drills.

    Returns:
        SecurityDrillSuiteResult
    """
    drills = SecurityInvariantDrills()
    return drills.run_all_drills()


def verify_security_invariants() -> bool:
    """Verify all security invariants are enforced.

    Returns:
        True if all drills blocked, False otherwise
    """
    result = run_security_invariant_drills()
    return result.all_blocked


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    print("=" * 70)
    print("SECURITY INVARIANT DRILLS")
    print("=" * 70)

    result = run_security_invariant_drills()

    print(f"\nTotal Drills: {result.total_drills}")
    print(f"Blocked: {result.blocked_drills}")
    print(f"Passed (VULNERABLE): {result.passed_drills}")
    print(f"Errors: {result.error_drills}")
    print(f"\nVERDICT: {result.verdict}")

    print("\n" + "=" * 70)
    print("DRILL DETAILS")
    print("=" * 70)

    for drill_result in result.results:
        status = "✓ BLOCKED" if drill_result.blocked else "✗ VULNERABLE"
        print(f"\n[{drill_result.drill_id}] {drill_result.drill_name}")
        print(f"  Invariant: {drill_result.invariant_id.value}")
        print(f"  Scenario: {drill_result.scenario}")
        print(f"  Status: {status}")

    print("\n" + "=" * 70)

    # Exit with appropriate code
    exit(0 if result.all_blocked else 1)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Types
    "DrillOutcome",
    "SecurityDrillResult",
    "SecurityDrillSuiteResult",
    # Classes
    "SecurityInvariantDrills",
    # Functions
    "run_security_invariant_drills",
    "verify_security_invariants",
]
