"""Tests for Intent Schema — Task 2 of PAC-ACM-02."""

import pytest
from pydantic import ValidationError

from core.governance.intent_schema import AgentIntent, IntentVerb, create_intent, parse_intent


class TestIntentVerbEnum:
    """Test IntentVerb enumeration."""

    def test_all_verbs_defined(self):
        """Test that all canonical verbs are defined."""
        verbs = [v.value for v in IntentVerb]
        assert "READ" in verbs
        assert "PROPOSE" in verbs
        assert "EXECUTE" in verbs
        assert "BLOCK" in verbs
        assert "ESCALATE" in verbs

    def test_from_string_case_insensitive(self):
        """Test verb parsing is case-insensitive."""
        assert IntentVerb.from_string("read") == IntentVerb.READ
        assert IntentVerb.from_string("READ") == IntentVerb.READ
        assert IntentVerb.from_string("Read") == IntentVerb.READ

    def test_from_string_unknown_raises(self):
        """Test unknown verb raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            IntentVerb.from_string("UNKNOWN")

        assert "Unknown intent verb" in str(exc_info.value)


class TestAgentIntentValidation:
    """Test AgentIntent schema validation."""

    def test_valid_intent_creation(self):
        """Test creating a valid intent."""
        intent = AgentIntent(
            agent_gid="GID-01",
            verb=IntentVerb.EXECUTE,
            target="pytest",
            scope="backend.tests",
        )

        assert intent.agent_gid == "GID-01"
        assert intent.verb == IntentVerb.EXECUTE
        assert intent.target == "pytest"
        assert intent.scope == "backend.tests"

    def test_gid_format_validation(self):
        """Test GID format validation (must be GID-XX)."""
        # Valid GID
        intent = AgentIntent(
            agent_gid="GID-01",
            verb=IntentVerb.READ,
            target="test",
        )
        assert intent.agent_gid == "GID-01"

        # Invalid GID format
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="INVALID",
                verb=IntentVerb.READ,
                target="test",
            )

        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-1",  # Must be two digits
                verb=IntentVerb.READ,
                target="test",
            )

    def test_target_required(self):
        """Test target field is required."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-01",
                verb=IntentVerb.READ,
                # Missing target
            )

    def test_target_min_length(self):
        """Test target must have minimum length."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-01",
                verb=IntentVerb.READ,
                target="",  # Empty target
            )

    def test_extra_fields_forbidden(self):
        """Test extra fields are rejected (forbid mode)."""
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-01",
                verb=IntentVerb.READ,
                target="test",
                unknown_field="value",  # type: ignore
            )

    def test_intent_immutability(self):
        """Test intent is frozen (immutable)."""
        intent = AgentIntent(
            agent_gid="GID-01",
            verb=IntentVerb.READ,
            target="test",
        )

        with pytest.raises(ValidationError):
            intent.target = "modified"  # type: ignore

    def test_metadata_validation(self):
        """Test metadata must be string key-value pairs."""
        # Valid metadata
        intent = AgentIntent(
            agent_gid="GID-01",
            verb=IntentVerb.READ,
            target="test",
            metadata={"key": "value"},
        )
        assert intent.metadata == {"key": "value"}

        # Invalid metadata (non-string value)
        with pytest.raises(ValidationError):
            AgentIntent(
                agent_gid="GID-01",
                verb=IntentVerb.READ,
                target="test",
                metadata={"key": 123},  # type: ignore
            )


class TestIntentProperties:
    """Test AgentIntent computed properties."""

    def test_full_target_with_scope(self):
        """Test full_target includes scope when present."""
        intent = AgentIntent(
            agent_gid="GID-01",
            verb=IntentVerb.EXECUTE,
            target="pytest",
            scope="backend.tests",
        )

        assert intent.full_target == "pytest.backend.tests"

    def test_full_target_without_scope(self):
        """Test full_target returns target alone when no scope."""
        intent = AgentIntent(
            agent_gid="GID-01",
            verb=IntentVerb.EXECUTE,
            target="pytest",
        )

        assert intent.full_target == "pytest"

    def test_is_mutating_execute_only(self):
        """Test is_mutating() returns True only for EXECUTE."""
        assert AgentIntent(agent_gid="GID-01", verb=IntentVerb.EXECUTE, target="test").is_mutating()

        assert not AgentIntent(agent_gid="GID-01", verb=IntentVerb.READ, target="test").is_mutating()

        assert not AgentIntent(agent_gid="GID-01", verb=IntentVerb.PROPOSE, target="test").is_mutating()

        assert not AgentIntent(agent_gid="GID-01", verb=IntentVerb.BLOCK, target="test").is_mutating()

        assert not AgentIntent(agent_gid="GID-01", verb=IntentVerb.ESCALATE, target="test").is_mutating()


class TestParseIntent:
    """Test parse_intent helper function."""

    def test_parse_valid_dict(self):
        """Test parsing a valid intent dictionary."""
        data = {
            "agent_gid": "GID-01",
            "verb": "EXECUTE",
            "target": "pytest",
        }

        intent = parse_intent(data)

        assert intent.agent_gid == "GID-01"
        assert intent.verb == IntentVerb.EXECUTE
        assert intent.target == "pytest"

    def test_parse_invalid_dict_raises(self):
        """Test parsing invalid dict raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_intent({"invalid": "data"})

        assert "Invalid intent format" in str(exc_info.value)

    def test_parse_case_insensitive_verb(self):
        """Test verb parsing is case-insensitive."""
        intent = parse_intent(
            {
                "agent_gid": "GID-01",
                "verb": "read",
                "target": "test",
            }
        )

        assert intent.verb == IntentVerb.READ


class TestCreateIntent:
    """Test create_intent factory function."""

    def test_create_with_string_verb(self):
        """Test creating intent with string verb."""
        intent = create_intent(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="pytest",
        )

        assert intent.verb == IntentVerb.EXECUTE

    def test_create_with_enum_verb(self):
        """Test creating intent with enum verb."""
        intent = create_intent(
            agent_gid="GID-01",
            verb=IntentVerb.EXECUTE,
            target="pytest",
        )

        assert intent.verb == IntentVerb.EXECUTE

    def test_create_with_all_fields(self):
        """Test creating intent with all optional fields."""
        intent = create_intent(
            agent_gid="GID-01",
            verb="EXECUTE",
            target="pytest",
            scope="backend.tests",
            metadata={"key": "value"},
            correlation_id="test-123",
        )

        assert intent.scope == "backend.tests"
        assert intent.metadata == {"key": "value"}
        assert intent.correlation_id == "test-123"
