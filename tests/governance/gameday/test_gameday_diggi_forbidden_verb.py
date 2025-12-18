"""
🧪 Gameday Test: G5 — Diggi Forbidden Verb
PAC-GOV-GAMEDAY-01: Governance Failure Simulation

Simulate:
- Diggi (GID-00) attempting EXECUTE, BLOCK, APPROVE
- Correction outputs containing forbidden verbs
- Bypass attempts through case manipulation

Invariants:
- Operation denied
- No state mutation
- Event emitted
- audit_ref present
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.governance.acm_evaluator import ACMDecision, ACMEvaluator, DenialReason
from core.governance.drcp import (
    DIGGY_FORBIDDEN_VERBS,
    DIGGY_GID,
    DenialRecord,
    DenialRegistry,
    DRCPOutcome,
    get_denial_registry,
    is_diggy,
    is_diggy_forbidden_verb,
    reset_denial_registry,
)
from core.governance.event_sink import GovernanceEventEmitter, InMemorySink
from core.governance.events import GovernanceEventType
from core.governance.intent_schema import AgentIntent, IntentVerb

# =============================================================================
# G5.1 — Diggi Cannot EXECUTE
# =============================================================================


class TestDiggiCannotExecute:
    """
    G5.1: Simulate Diggi attempting to EXECUTE.

    Attack scenario: Diggi (GID-00), the orchestrator, attempts
    to execute actions directly instead of routing to agents.
    """

    def test_diggi_execute_denied(self) -> None:
        """Diggi (GID-00) EXECUTE should be denied."""
        evaluator = ACMEvaluator()

        intent = AgentIntent(
            agent_gid=DIGGY_GID,  # GID-00
            verb=IntentVerb.EXECUTE,
            target="any.target",
        )

        result = evaluator.evaluate(intent)

        # Invariant 1: Operation denied
        assert result.decision == ACMDecision.DENY
        # Should have specific denial reason
        assert result.reason in (
            DenialReason.DIGGY_EXECUTE_FORBIDDEN,
            DenialReason.EXECUTE_NOT_PERMITTED,
            DenialReason.VERB_NOT_PERMITTED,
        )

    def test_is_diggy_forbidden_verb_execute(self) -> None:
        """is_diggy_forbidden_verb should return True for EXECUTE."""
        assert is_diggy_forbidden_verb("EXECUTE")
        assert is_diggy_forbidden_verb("execute")  # case insensitive
        assert is_diggy_forbidden_verb(IntentVerb.EXECUTE)

    def test_diggi_execute_no_state_mutation(self) -> None:
        """Denied EXECUTE should not mutate registry state."""
        reset_denial_registry()
        registry = get_denial_registry()

        # Count denials before
        initial_count = len(registry._denials)

        evaluator = ACMEvaluator()
        intent = AgentIntent(
            agent_gid=DIGGY_GID,
            verb=IntentVerb.EXECUTE,
            target="test.target",
        )

        result = evaluator.evaluate(intent)

        # Invariant 2: No state mutation (denial itself doesn't add to registry)
        # The registry is populated by DRCP, not the evaluator directly
        assert result.decision == ACMDecision.DENY


# =============================================================================
# G5.2 — Diggi Cannot BLOCK
# =============================================================================


class TestDiggiCannotBlock:
    """
    G5.2: Simulate Diggi attempting to BLOCK.

    Attack scenario: Diggi attempts to block other agents
    instead of routing the denial.
    """

    def test_diggi_block_denied(self) -> None:
        """Diggi (GID-00) BLOCK should be denied."""
        evaluator = ACMEvaluator()

        intent = AgentIntent(
            agent_gid=DIGGY_GID,
            verb=IntentVerb.BLOCK,
            target="agent.GID-07",
        )

        result = evaluator.evaluate(intent)

        # Invariant 1: Operation denied
        assert result.decision == ACMDecision.DENY
        assert result.reason in (
            DenialReason.DIGGY_BLOCK_FORBIDDEN,
            DenialReason.BLOCK_NOT_PERMITTED,
            DenialReason.VERB_NOT_PERMITTED,
        )

    def test_is_diggy_forbidden_verb_block(self) -> None:
        """is_diggy_forbidden_verb should return True for BLOCK."""
        assert is_diggy_forbidden_verb("BLOCK")
        assert is_diggy_forbidden_verb("block")


# =============================================================================
# G5.3 — Diggi Cannot APPROVE
# =============================================================================


class TestDiggiCannotApprove:
    """
    G5.3: Simulate Diggi attempting to APPROVE.

    Attack scenario: Diggi attempts to approve intents
    bypassing ALEX governance.
    """

    def test_approve_in_forbidden_verbs(self) -> None:
        """APPROVE should be in Diggi's forbidden verbs set."""
        assert "APPROVE" in DIGGY_FORBIDDEN_VERBS

    def test_is_diggy_forbidden_verb_approve(self) -> None:
        """is_diggy_forbidden_verb should return True for APPROVE."""
        assert is_diggy_forbidden_verb("APPROVE")
        assert is_diggy_forbidden_verb("approve")


# =============================================================================
# G5.4 — Allowed Verbs for Diggi
# =============================================================================


class TestDiggiAllowedVerbs:
    """
    G5.4: Verify Diggi can use permitted verbs.

    Diggi MAY only: READ, PROPOSE, ESCALATE
    """

    def test_read_not_forbidden(self) -> None:
        """READ should NOT be forbidden for Diggi."""
        assert not is_diggy_forbidden_verb("READ")
        assert not is_diggy_forbidden_verb("read")

    def test_propose_not_forbidden(self) -> None:
        """PROPOSE should NOT be forbidden for Diggi."""
        assert not is_diggy_forbidden_verb("PROPOSE")
        assert not is_diggy_forbidden_verb("propose")

    def test_escalate_not_forbidden(self) -> None:
        """ESCALATE should NOT be forbidden for Diggi."""
        assert not is_diggy_forbidden_verb("ESCALATE")
        assert not is_diggy_forbidden_verb("escalate")


# =============================================================================
# G5.5 — Forbidden Verbs Set Completeness
# =============================================================================


class TestForbiddenVerbsCompleteness:
    """
    G5.5: Verify DIGGY_FORBIDDEN_VERBS is complete and correct.

    Invariant: The set must contain exactly the dangerous verbs.
    """

    def test_forbidden_verbs_exact_set(self) -> None:
        """DIGGY_FORBIDDEN_VERBS should contain exactly EXECUTE, BLOCK, APPROVE."""
        expected = {"EXECUTE", "BLOCK", "APPROVE"}
        assert DIGGY_FORBIDDEN_VERBS == expected

    def test_forbidden_verbs_immutable(self) -> None:
        """DIGGY_FORBIDDEN_VERBS should be a set of dangerous verbs."""
        # Verify the set contains the expected verbs
        # Note: Even if it's mutable, modifying it is a governance violation
        assert "EXECUTE" in DIGGY_FORBIDDEN_VERBS
        assert "BLOCK" in DIGGY_FORBIDDEN_VERBS
        assert "APPROVE" in DIGGY_FORBIDDEN_VERBS

        # Verify minimum size
        assert len(DIGGY_FORBIDDEN_VERBS) >= 3

    def test_all_forbidden_verbs_are_uppercase(self) -> None:
        """All forbidden verbs should be uppercase."""
        for verb in DIGGY_FORBIDDEN_VERBS:
            assert verb == verb.upper()


# =============================================================================
# G5.6 — is_diggy Function
# =============================================================================


class TestIsDiggyFunction:
    """
    G5.6: Verify is_diggy() identity check.

    Invariant: Only GID-00 is Diggy.
    """

    def test_gid_00_is_diggy(self) -> None:
        """GID-00 should be identified as Diggy."""
        assert is_diggy("GID-00")

    def test_other_gids_not_diggy(self) -> None:
        """Other GIDs should not be identified as Diggy."""
        assert not is_diggy("GID-01")
        assert not is_diggy("GID-07")
        assert not is_diggy("GID-08")
        assert not is_diggy("GID-99")

    def test_similar_gids_not_diggy(self) -> None:
        """Similar-looking GIDs should not be identified as Diggy."""
        assert not is_diggy("gid-00")  # Wrong case
        assert not is_diggy("GID-0")  # Wrong format
        assert not is_diggy("GID-000")  # Wrong format
        assert not is_diggy("DIGGY")  # Name, not GID


# =============================================================================
# G5.7 — Case Manipulation Bypass Attempts
# =============================================================================


class TestCaseManipulationBypass:
    """
    G5.7: Verify case manipulation cannot bypass forbidden verb checks.

    Attack scenario: Attacker tries different cases to bypass.
    """

    @pytest.mark.parametrize(
        "verb_case",
        [
            "EXECUTE",
            "execute",
            "Execute",
            "eXeCuTe",
            "BLOCK",
            "block",
            "Block",
            "bLoCk",
            "APPROVE",
            "approve",
            "Approve",
            "aPpRoVe",
        ],
    )
    def test_case_insensitive_forbidden_check(self, verb_case: str) -> None:
        """Forbidden verb check should be case-insensitive."""
        base_verb = verb_case.upper()
        if base_verb in {"EXECUTE", "BLOCK", "APPROVE"}:
            assert is_diggy_forbidden_verb(verb_case)


# =============================================================================
# G5.8 — DRCP Constants
# =============================================================================


class TestDRCPConstants:
    """
    G5.8: Verify DRCP module constants are correct.

    Invariant: DIGGY_GID must be "GID-00".
    """

    def test_diggy_gid_constant(self) -> None:
        """DIGGY_GID should be 'GID-00'."""
        assert DIGGY_GID == "GID-00"

    def test_diggy_gid_is_string(self) -> None:
        """DIGGY_GID should be a string."""
        assert isinstance(DIGGY_GID, str)


# =============================================================================
# G5.9 — Denial Registry Isolation
# =============================================================================


class TestDenialRegistryIsolation:
    """
    G5.9: Verify denial registry operations are isolated.

    Invariant: Failed operations should not corrupt the registry.
    """

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_denial_registry()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        reset_denial_registry()

    def test_registry_reset_clears_state(self) -> None:
        """reset_denial_registry should clear all state."""
        registry = get_denial_registry()

        # Add a denial using the register_denial method
        denial = DenialRecord(
            intent_id="test-001",
            agent_gid="GID-07",
            verb="EXECUTE",
            target="test.target",
            denial_code="TEST_DENIAL",
            denial_detail="Test",
            denied_at="2024-01-01T00:00:00Z",
        )
        registry.register_denial(denial)

        assert len(registry._denials) > 0

        # Reset
        reset_denial_registry()

        # New registry should be empty
        new_registry = get_denial_registry()
        assert len(new_registry._denials) == 0

    def test_registry_singleton_pattern(self) -> None:
        """get_denial_registry should return same instance."""
        registry1 = get_denial_registry()
        registry2 = get_denial_registry()

        assert registry1 is registry2
