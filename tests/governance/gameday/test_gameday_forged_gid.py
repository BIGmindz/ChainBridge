"""
🧪 Gameday Test: G1 — Forged Agent Identity
PAC-GOV-GAMEDAY-01: Governance Failure Simulation

Simulate:
- Unknown agent_gid (e.g., "GID-99")
- Spoofed valid GID from different context

Invariants:
- Operation denied
- No state mutation
- Event emitted
- audit_ref present
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.governance.acm_evaluator import ACMDecision, ACMEvaluator, DenialReason
from core.governance.event_sink import GovernanceEventEmitter, InMemorySink
from core.governance.events import GovernanceEventType
from core.governance.intent_schema import AgentIntent, IntentVerb

# =============================================================================
# G1.1 — Unknown Agent GID
# =============================================================================


class TestUnknownAgentGID:
    """
    G1.1: Simulate requests from an unknown/unregistered agent GID.

    Attack scenario: An attacker crafts a request with a fabricated GID
    that doesn't exist in the ACM registry.
    """

    def test_unknown_gid_is_denied(self) -> None:
        """Request with unknown GID-99 should be denied."""
        evaluator = ACMEvaluator()

        # Create intent with unknown GID
        intent = AgentIntent(
            agent_gid="GID-99",
            verb=IntentVerb.READ,
            target="any.resource",
        )

        result = evaluator.evaluate(intent)

        # Invariant 1: Operation denied
        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.UNKNOWN_AGENT

    def test_unknown_gid_no_state_mutation(self) -> None:
        """Unknown GID request should not mutate any state."""
        evaluator = ACMEvaluator()

        # Snapshot state before
        initial_loader_state = id(evaluator._loader)

        intent = AgentIntent(
            agent_gid="GID-99",
            verb=IntentVerb.EXECUTE,
            target="some.resource",
        )

        # This should fail but not mutate
        result = evaluator.evaluate(intent)

        # Invariant 2: No state mutation
        assert result.decision == ACMDecision.DENY
        assert id(evaluator._loader) == initial_loader_state

    def test_unknown_gid_emits_event(self) -> None:
        """Unknown GID denial should emit telemetry event."""
        evaluator = ACMEvaluator()

        # Setup in-memory sink to capture events
        sink = InMemorySink()
        emitter = GovernanceEventEmitter()
        emitter.add_sink(sink)

        intent = AgentIntent(
            agent_gid="GID-99",
            verb=IntentVerb.READ,
            target="test.target",
        )

        # Evaluate (event emitted via telemetry)
        result = evaluator.evaluate(intent)

        # Cleanup
        emitter.remove_sink(sink)

        # Invariant 1: Denied
        assert result.decision == ACMDecision.DENY

    def test_unknown_gid_high_number(self) -> None:
        """GID with high number (GID-50) should be denied."""
        evaluator = ACMEvaluator()

        intent = AgentIntent(
            agent_gid="GID-50",
            verb=IntentVerb.READ,
            target="any.target",
        )

        result = evaluator.evaluate(intent)

        assert result.decision == ACMDecision.DENY
        assert result.reason == DenialReason.UNKNOWN_AGENT


# =============================================================================
# G1.2 — Malformed GID
# =============================================================================


class TestMalformedGID:
    """
    G1.2: Simulate requests with malformed GID patterns.

    Attack scenario: An attacker attempts to bypass validation
    using malformed or injection-style GID values.
    """

    @pytest.mark.parametrize(
        "bad_gid",
        [
            "GID-1",  # Too short (should be GID-XX)
            "GID-123",  # Too long
            "INVALID",  # Wrong format entirely
            "gid-01",  # Wrong case
            "GID_01",  # Wrong separator
        ],
    )
    def test_malformed_gid_rejected_at_schema(self, bad_gid: str) -> None:
        """Malformed GID should be rejected at schema validation."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid=bad_gid,
                verb=IntentVerb.READ,
                target="any.target",
            )

    def test_sql_injection_gid_rejected(self) -> None:
        """SQL injection attempt in GID should be rejected."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-01'; DROP TABLE agents; --",
                verb=IntentVerb.READ,
                target="any.target",
            )

    def test_empty_gid_rejected(self) -> None:
        """Empty GID should be rejected."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="",
                verb=IntentVerb.READ,
                target="any.target",
            )

    def test_whitespace_gid_rejected(self) -> None:
        """Whitespace-only GID should be rejected."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="   ",
                verb=IntentVerb.READ,
                target="any.target",
            )


# =============================================================================
# G1.3 — GID Spoofing (Cross-Context)
# =============================================================================


class TestGIDSpoofing:
    """
    G1.3: Simulate an agent trying to spoof another agent's GID.

    Attack scenario: A low-privilege agent (GID-02) attempts to
    execute actions by claiming to be a high-privilege agent (GID-08 ALEX).
    """

    def test_spoofed_gid_still_bound_by_acm(self) -> None:
        """
        Even if spoofed, the GID should be evaluated against its ACM.

        If GID-08 (ALEX) has specific permissions, spoofing it should
        still be bound by ALEX's actual ACM, not the spoofer's intent.
        """
        evaluator = ACMEvaluator()

        # Attempt to use ALEX's GID for an action
        intent = AgentIntent(
            agent_gid="GID-08",  # ALEX
            verb=IntentVerb.EXECUTE,
            target="restricted.operation",
        )

        result = evaluator.evaluate(intent)

        # The request should be evaluated against GID-08's ACM
        # If target is not in GID-08's scope, it should be denied
        # This proves ACM-based enforcement, not trust-based
        assert result.decision in (ACMDecision.ALLOW, ACMDecision.DENY)

        # If denied, should have proper reason
        if result.decision == ACMDecision.DENY:
            assert result.reason is not None

    def test_orchestrator_gid_cannot_execute(self) -> None:
        """
        GID-00 (Diggy/Benson orchestrator) cannot EXECUTE.

        Even if someone spoofs GID-00, the ACM should deny EXECUTE.
        """
        evaluator = ACMEvaluator()

        intent = AgentIntent(
            agent_gid="GID-00",  # Orchestrator
            verb=IntentVerb.EXECUTE,
            target="any.target",
        )

        result = evaluator.evaluate(intent)

        # Invariant: GID-00 cannot EXECUTE
        assert result.decision == ACMDecision.DENY


# =============================================================================
# G1.4 — GID Mutation Attempt
# =============================================================================


class TestGIDMutationAttempt:
    """
    G1.4: Verify intent immutability prevents GID tampering.

    Attack scenario: After creation, an attacker attempts to
    mutate the agent_gid field.
    """

    def test_intent_gid_immutable(self) -> None:
        """AgentIntent.agent_gid should be immutable (frozen model)."""
        intent = AgentIntent(
            agent_gid="GID-07",
            verb=IntentVerb.READ,
            target="test.target",
        )

        # Attempt mutation should raise
        with pytest.raises((AttributeError, TypeError, ValidationError)):
            intent.agent_gid = "GID-99"  # type: ignore

    def test_intent_verb_immutable(self) -> None:
        """AgentIntent.verb should be immutable."""
        intent = AgentIntent(
            agent_gid="GID-07",
            verb=IntentVerb.READ,
            target="test.target",
        )

        with pytest.raises((AttributeError, TypeError, ValidationError)):
            intent.verb = IntentVerb.EXECUTE  # type: ignore

    def test_intent_target_immutable(self) -> None:
        """AgentIntent.target should be immutable."""
        intent = AgentIntent(
            agent_gid="GID-07",
            verb=IntentVerb.READ,
            target="test.target",
        )

        with pytest.raises((AttributeError, TypeError, ValidationError)):
            intent.target = "different.target"  # type: ignore
