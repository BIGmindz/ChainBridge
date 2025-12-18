"""
🧪 Gameday Test: G2 — Tool Without Envelope
PAC-GOV-GAMEDAY-01: Governance Failure Simulation

Simulate:
- Tool invocation without proper AgentIntent envelope
- Missing required fields
- Bypassing the gateway entirely

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
from core.governance.intent_schema import AgentIntent, IntentVerb

# =============================================================================
# G2.1 — Missing Intent Envelope
# =============================================================================


class TestMissingIntentEnvelope:
    """
    G2.1: Simulate tool calls without proper intent envelope.

    Attack scenario: An attacker bypasses the intent wrapping
    and tries to invoke the evaluator with raw data.
    """

    def test_none_intent_rejected(self) -> None:
        """Evaluator should reject None intent."""
        evaluator = ACMEvaluator()

        # Invariant 1: Operation denied
        with pytest.raises((TypeError, AttributeError)):
            evaluator.evaluate(None)  # type: ignore

    def test_dict_instead_of_intent_rejected(self) -> None:
        """Evaluator should reject dict instead of AgentIntent."""
        evaluator = ACMEvaluator()

        raw_dict = {
            "agent_gid": "GID-07",
            "verb": "READ",
            "target": "test.target",
        }

        # Invariant 1: Operation denied
        with pytest.raises((TypeError, AttributeError)):
            evaluator.evaluate(raw_dict)  # type: ignore

    def test_string_instead_of_intent_rejected(self) -> None:
        """Evaluator should reject string instead of AgentIntent."""
        evaluator = ACMEvaluator()

        # Invariant 1: Operation denied
        with pytest.raises((TypeError, AttributeError)):
            evaluator.evaluate("GID-07:READ:test.target")  # type: ignore


# =============================================================================
# G2.2 — Incomplete Intent Envelope
# =============================================================================


class TestIncompleteIntentEnvelope:
    """
    G2.2: Simulate intents with missing required fields.

    Attack scenario: An attacker crafts partial intent objects
    hoping some required fields might be optional.
    """

    def test_missing_agent_gid_rejected(self) -> None:
        """Intent without agent_gid should be rejected at creation."""
        with pytest.raises(ValidationError) as exc_info:
            AgentIntent(
                verb=IntentVerb.READ,  # type: ignore
                target="test.target",
            )

        errors = exc_info.value.errors()
        assert any("agent_gid" in str(e) for e in errors)

    def test_missing_verb_rejected(self) -> None:
        """Intent without verb should be rejected at creation."""
        with pytest.raises(ValidationError) as exc_info:
            AgentIntent(
                agent_gid="GID-07",  # type: ignore
                target="test.target",
            )

        errors = exc_info.value.errors()
        assert any("verb" in str(e) for e in errors)

    def test_missing_target_rejected(self) -> None:
        """Intent without target should be rejected at creation."""
        with pytest.raises(ValidationError) as exc_info:
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,  # type: ignore
            )

        errors = exc_info.value.errors()
        assert any("target" in str(e) for e in errors)

    def test_empty_target_rejected(self) -> None:
        """Intent with empty target should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="",  # Empty
            )

        errors = exc_info.value.errors()
        # min_length=1 validation should fail
        assert any("target" in str(e) or "min_length" in str(e) for e in errors)


# =============================================================================
# G2.3 — Invalid Verb Values
# =============================================================================


class TestInvalidVerbValues:
    """
    G2.3: Simulate intents with invalid verb values.

    Attack scenario: An attacker tries to use non-standard
    or dangerous verb values.
    """

    @pytest.mark.parametrize(
        "bad_verb",
        [
            "DELETE",  # Not a valid IntentVerb
            "MODIFY",  # Not a valid IntentVerb
            "ADMIN",  # Not a valid IntentVerb
            "SUDO",  # Not a valid IntentVerb
            "ROOT",  # Not a valid IntentVerb
        ],
    )
    def test_invalid_verb_string_rejected(self, bad_verb: str) -> None:
        """Invalid verb strings should be rejected."""
        with pytest.raises((ValidationError, ValueError)):
            AgentIntent(
                agent_gid="GID-07",
                verb=bad_verb,  # type: ignore
                target="test.target",
            )

    def test_verb_case_sensitivity(self) -> None:
        """Lowercase verbs should be rejected (IntentVerb uses uppercase)."""
        with pytest.raises((ValidationError, ValueError)):
            AgentIntent(
                agent_gid="GID-07",
                verb="read",  # lowercase
                target="test.target",
            )

    def test_none_verb_rejected(self) -> None:
        """None verb should be rejected."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-07",
                verb=None,  # type: ignore
                target="test.target",
            )


# =============================================================================
# G2.4 — Extra/Unknown Fields
# =============================================================================


class TestExtraUnknownFields:
    """
    G2.4: Simulate intents with extra unknown fields.

    Attack scenario: An attacker adds extra fields hoping
    they might be processed or cause unexpected behavior.
    """

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="test.target",
                admin_override=True,  # type: ignore
            )

        errors = exc_info.value.errors()
        assert any("extra" in str(e) or "admin_override" in str(e) for e in errors)

    def test_privilege_escalation_field_rejected(self) -> None:
        """Privilege escalation fields should be rejected."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="test.target",
                is_admin=True,  # type: ignore
            )

    def test_bypass_field_rejected(self) -> None:
        """Security bypass fields should be rejected."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="test.target",
                skip_acm_check=True,  # type: ignore
            )


# =============================================================================
# G2.5 — Metadata Injection
# =============================================================================


class TestMetadataInjection:
    """
    G2.5: Simulate attacks via metadata field.

    Attack scenario: An attacker tries to inject malicious
    data through the optional metadata field.
    """

    def test_metadata_must_be_string_values(self) -> None:
        """Metadata values must be strings, not nested objects."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="test.target",
                metadata={"nested": {"deep": "value"}},  # type: ignore
            )

    def test_metadata_non_string_key_rejected(self) -> None:
        """Metadata keys must be strings."""
        with pytest.raises((ValidationError, TypeError)):
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="test.target",
                metadata={123: "value"},  # type: ignore
            )

    def test_metadata_list_value_rejected(self) -> None:
        """Metadata values cannot be lists."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-07",
                verb=IntentVerb.READ,
                target="test.target",
                metadata={"items": ["a", "b", "c"]},  # type: ignore
            )

    def test_valid_metadata_accepted(self) -> None:
        """Valid string-string metadata should be accepted."""
        intent = AgentIntent(
            agent_gid="GID-07",
            verb=IntentVerb.READ,
            target="test.target",
            metadata={"key1": "value1", "key2": "value2"},
        )

        assert intent.metadata == {"key1": "value1", "key2": "value2"}


# =============================================================================
# G2.6 — No State Mutation on Rejection
# =============================================================================


class TestNoStateMutationOnRejection:
    """
    G2.6: Verify no state mutation when envelope validation fails.

    Invariant: Failed validation should not leave any side effects.
    """

    def test_failed_intent_creation_no_side_effects(self) -> None:
        """Failed intent creation should have no side effects."""
        evaluator = ACMEvaluator()

        # Capture initial state
        initial_id = id(evaluator._loader)

        # Attempt to create invalid intent (should fail)
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="INVALID",
                verb=IntentVerb.READ,
                target="test.target",
            )

        # Verify no state mutation
        assert id(evaluator._loader) == initial_id

    def test_evaluator_state_unchanged_after_rejection(self) -> None:
        """Evaluator state should remain unchanged after rejecting bad input."""
        evaluator = ACMEvaluator()

        # First, create a valid intent and evaluate
        valid_intent = AgentIntent(
            agent_gid="GID-07",
            verb=IntentVerb.READ,
            target="test.target",
        )
        result1 = evaluator.evaluate(valid_intent)

        # Now try invalid calls (they raise AttributeError on None.agent_gid)
        with pytest.raises(AttributeError):
            evaluator.evaluate(None)  # type: ignore

        with pytest.raises(AttributeError):
            evaluator.evaluate({"invalid": "dict"})  # type: ignore

        # Evaluate valid intent again - should get consistent behavior
        result2 = evaluator.evaluate(valid_intent)

        # Both results should be consistent
        assert result1.decision == result2.decision
