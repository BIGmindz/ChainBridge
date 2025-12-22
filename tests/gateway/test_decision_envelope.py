"""
Tests for Canonical Decision Envelope (CDE) v1 — PAC-GATEWAY-01

These tests verify the CDE contract:
1. ALLOW returns full envelope
2. DENY returns full envelope
3. Diggi-routed denial sets next_hop
4. human_required is true only when required
5. No internal exception leaks
6. Envelope survives serialization (JSON safe)

Author: ATLAS (GID-11)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Generator

import pytest

from core.governance.acm_evaluator import ACMDecision, DenialReason, EvaluationResult
from gateway.decision_envelope import (
    CDE_VERSION,
    EnvelopeMalformedError,
    EnvelopeVersionError,
    GatewayDecision,
    GatewayDecisionEnvelope,
    ReasonCode,
    create_allow_envelope,
    create_deny_envelope,
    create_envelope_from_result,
    map_denial_reason,
    validate_envelope,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def allow_result() -> EvaluationResult:
    """Create an ALLOW evaluation result."""
    return EvaluationResult(
        decision=ACMDecision.ALLOW,
        agent_gid="GID-01",
        intent_verb="READ",
        intent_target="data/metrics",
        reason=None,
        reason_detail=None,
        acm_version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id="test-123",
        next_hop=None,
        correction_plan=None,
    )


@pytest.fixture
def deny_result() -> EvaluationResult:
    """Create a DENY evaluation result."""
    return EvaluationResult(
        decision=ACMDecision.DENY,
        agent_gid="GID-01",
        intent_verb="EXECUTE",
        intent_target="core/payment",
        reason=DenialReason.EXECUTE_NOT_PERMITTED,
        reason_detail="GID-01 does not have EXECUTE permission on core/payment",
        acm_version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id="test-456",
        next_hop="GID-00",
        correction_plan={"allowed_next_steps": ["PROPOSE", "ESCALATE"]},
    )


@pytest.fixture
def diggi_routed_deny() -> EvaluationResult:
    """Create a DENY result routed to Diggi."""
    return EvaluationResult(
        decision=ACMDecision.DENY,
        agent_gid="GID-05",
        intent_verb="EXECUTE",
        intent_target="api/endpoint",
        reason=DenialReason.CHAIN_OF_COMMAND_VIOLATION,
        reason_detail="EXECUTE requires routing through GID-00 (Diggy)",
        acm_version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id="test-789",
        next_hop="GID-00",
        correction_plan=None,
    )


@pytest.fixture
def human_required_deny() -> EvaluationResult:
    """Create a DENY result that requires human intervention."""
    return EvaluationResult(
        decision=ACMDecision.DENY,
        agent_gid="GID-01",
        intent_verb="APPROVE",
        intent_target="payment/large",
        reason=DenialReason.APPROVE_NOT_PERMITTED,
        reason_detail="APPROVE is a human-only capability",
        acm_version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id="test-human",
        next_hop=None,
        correction_plan=None,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: VERSION LOCK
# ═══════════════════════════════════════════════════════════════════════════════


class TestVersionLock:
    """Tests for CDE version enforcement."""

    def test_cde_version_is_1_0_0(self) -> None:
        """CDE version must be 1.0.0."""
        assert CDE_VERSION == "1.0.0"

    def test_envelope_requires_correct_version(self) -> None:
        """Envelope creation fails if version is wrong."""
        with pytest.raises(EnvelopeVersionError) as exc_info:
            GatewayDecisionEnvelope(
                version="2.0.0",  # Wrong version
                decision=GatewayDecision.ALLOW,
                reason_code=ReasonCode.NONE,
                reason_detail="",
                human_required=False,
                next_hop=None,
                allowed_tools=[],
                audit_ref="cde-test123",
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_gid="GID-01",
                intent_verb="READ",
                intent_target="data",
            )

        assert "1.0.0" in str(exc_info.value)

    def test_envelope_with_correct_version_passes(self) -> None:
        """Envelope creation succeeds with correct version."""
        envelope = GatewayDecisionEnvelope(
            version=CDE_VERSION,
            decision=GatewayDecision.ALLOW,
            reason_code=ReasonCode.NONE,
            reason_detail="",
            human_required=False,
            next_hop=None,
            allowed_tools=[],
            audit_ref="cde-test123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_gid="GID-01",
            intent_verb="READ",
            intent_target="data",
        )
        assert envelope.version == CDE_VERSION


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: ALLOW ENVELOPE
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllowEnvelope:
    """Tests for ALLOW decision envelopes."""

    def test_allow_envelope_has_all_fields(self, allow_result: EvaluationResult) -> None:
        """ALLOW envelope must have all required fields populated."""
        envelope = create_envelope_from_result(allow_result)

        assert envelope.version == CDE_VERSION
        assert envelope.decision == GatewayDecision.ALLOW
        assert envelope.reason_code == ReasonCode.NONE
        assert envelope.reason_detail == ""
        assert envelope.human_required is False
        assert envelope.next_hop is None
        assert isinstance(envelope.allowed_tools, list)
        assert envelope.audit_ref.startswith("cde-")
        assert envelope.timestamp is not None
        assert envelope.agent_gid == "GID-01"
        assert envelope.intent_verb == "READ"
        assert envelope.intent_target == "data/metrics"

    def test_allow_envelope_with_tools(self, allow_result: EvaluationResult) -> None:
        """ALLOW envelope can include allowed_tools."""
        tools = ["read_file", "grep_search", "semantic_search"]
        envelope = create_envelope_from_result(allow_result, allowed_tools=tools)

        assert envelope.decision == GatewayDecision.ALLOW
        assert envelope.allowed_tools == tools

    def test_create_allow_envelope_directly(self) -> None:
        """create_allow_envelope convenience function works."""
        envelope = create_allow_envelope(
            agent_gid="GID-02",
            intent_verb="PROPOSE",
            intent_target="docs/readme",
            allowed_tools=["create_file"],
        )

        assert envelope.decision == GatewayDecision.ALLOW
        assert envelope.reason_code == ReasonCode.NONE
        assert envelope.agent_gid == "GID-02"
        assert envelope.allowed_tools == ["create_file"]

    def test_allow_envelope_reason_code_is_none(self, allow_result: EvaluationResult) -> None:
        """ALLOW decisions must have reason_code NONE."""
        envelope = create_envelope_from_result(allow_result)
        assert envelope.reason_code == ReasonCode.NONE


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: DENY ENVELOPE
# ═══════════════════════════════════════════════════════════════════════════════


class TestDenyEnvelope:
    """Tests for DENY decision envelopes."""

    def test_deny_envelope_has_all_fields(self, deny_result: EvaluationResult) -> None:
        """DENY envelope must have all required fields populated."""
        envelope = create_envelope_from_result(deny_result)

        assert envelope.version == CDE_VERSION
        assert envelope.decision == GatewayDecision.DENY
        assert envelope.reason_code == ReasonCode.EXECUTE_NOT_PERMITTED
        assert "EXECUTE permission" in envelope.reason_detail
        assert envelope.human_required is False
        assert envelope.next_hop == "GID-00"
        assert envelope.allowed_tools == []  # Always empty for DENY
        assert envelope.audit_ref.startswith("cde-")
        assert envelope.agent_gid == "GID-01"
        assert envelope.intent_verb == "EXECUTE"
        assert envelope.intent_target == "core/payment"

    def test_deny_envelope_has_empty_tools(self, deny_result: EvaluationResult) -> None:
        """DENY envelope must have empty allowed_tools."""
        envelope = create_envelope_from_result(deny_result)
        assert envelope.allowed_tools == []

    def test_deny_envelope_preserves_correction_plan(self, deny_result: EvaluationResult) -> None:
        """DENY envelope preserves correction_plan from result."""
        envelope = create_envelope_from_result(deny_result)
        assert envelope.correction_plan is not None
        assert "allowed_next_steps" in envelope.correction_plan

    def test_create_deny_envelope_directly(self) -> None:
        """create_deny_envelope convenience function works."""
        envelope = create_deny_envelope(
            agent_gid="GID-11",
            intent_verb="EXECUTE",
            intent_target="core/backend",
            reason_code=ReasonCode.ATLAS_DOMAIN_VIOLATION,
            reason_detail="Atlas cannot modify domain-owned paths",
            next_hop="GID-00",
        )

        assert envelope.decision == GatewayDecision.DENY
        assert envelope.reason_code == ReasonCode.ATLAS_DOMAIN_VIOLATION
        assert envelope.next_hop == "GID-00"
        assert envelope.allowed_tools == []


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: DIGGI ROUTING
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiggiRouting:
    """Tests for Diggi-routed denials."""

    def test_diggi_routed_denial_has_next_hop(self, diggi_routed_deny: EvaluationResult) -> None:
        """Diggi-routed denial must set next_hop to GID-00."""
        envelope = create_envelope_from_result(diggi_routed_deny)

        assert envelope.decision == GatewayDecision.DENY
        assert envelope.next_hop == "GID-00"
        assert envelope.reason_code == ReasonCode.CHAIN_OF_COMMAND_VIOLATION

    def test_diggi_is_correction_authority(self, diggi_routed_deny: EvaluationResult) -> None:
        """Diggi (GID-00) is the correction authority for routed denials."""
        envelope = create_envelope_from_result(diggi_routed_deny)
        assert envelope.next_hop == "GID-00"  # Diggi's GID


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: HUMAN REQUIRED
# ═══════════════════════════════════════════════════════════════════════════════


class TestHumanRequired:
    """Tests for human_required flag."""

    def test_approve_denial_requires_human(self, human_required_deny: EvaluationResult) -> None:
        """APPROVE_NOT_PERMITTED denial must set human_required=True."""
        envelope = create_envelope_from_result(human_required_deny)

        assert envelope.decision == GatewayDecision.DENY
        assert envelope.human_required is True
        assert envelope.reason_code == ReasonCode.APPROVE_NOT_PERMITTED

    def test_normal_denial_does_not_require_human(self, deny_result: EvaluationResult) -> None:
        """Normal denials do not require human intervention."""
        envelope = create_envelope_from_result(deny_result)
        assert envelope.human_required is False

    def test_allow_does_not_require_human(self, allow_result: EvaluationResult) -> None:
        """ALLOW decisions never require human intervention."""
        envelope = create_envelope_from_result(allow_result)
        assert envelope.human_required is False


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: SERIALIZATION (JSON SAFE)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Tests for envelope serialization."""

    def test_envelope_to_dict(self, allow_result: EvaluationResult) -> None:
        """Envelope can be converted to dictionary."""
        envelope = create_envelope_from_result(allow_result)
        data = envelope.to_dict()

        assert isinstance(data, dict)
        assert data["version"] == CDE_VERSION
        assert data["decision"] == "ALLOW"
        assert data["reason_code"] == "NONE"

    def test_envelope_to_json(self, allow_result: EvaluationResult) -> None:
        """Envelope can be serialized to JSON."""
        envelope = create_envelope_from_result(allow_result)
        json_str = envelope.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["version"] == CDE_VERSION
        assert parsed["decision"] == "ALLOW"

    def test_envelope_survives_roundtrip(self, deny_result: EvaluationResult) -> None:
        """Envelope survives JSON roundtrip."""
        original = create_envelope_from_result(deny_result)
        json_str = original.to_json()
        restored = GatewayDecisionEnvelope.from_json(json_str)

        assert restored.version == original.version
        assert restored.decision == original.decision
        assert restored.reason_code == original.reason_code
        assert restored.agent_gid == original.agent_gid
        assert restored.intent_verb == original.intent_verb
        assert restored.intent_target == original.intent_target

    def test_envelope_from_dict(self) -> None:
        """Envelope can be created from dictionary."""
        data = {
            "version": CDE_VERSION,
            "decision": "DENY",
            "reason_code": "VERB_NOT_PERMITTED",
            "reason_detail": "Agent cannot perform this action",
            "human_required": False,
            "next_hop": "GID-00",
            "allowed_tools": [],
            "audit_ref": "cde-abc123",
            "timestamp": "2025-12-17T00:00:00Z",
            "agent_gid": "GID-03",
            "intent_verb": "DELETE",
            "intent_target": "data/critical",
        }
        envelope = GatewayDecisionEnvelope.from_dict(data)

        assert envelope.decision == GatewayDecision.DENY
        assert envelope.reason_code == ReasonCode.VERB_NOT_PERMITTED


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: NO EXCEPTION LEAKS
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoExceptionLeaks:
    """Tests to ensure no internal exceptions leak through CDE."""

    def test_envelope_creation_does_not_raise_on_valid_input(self, allow_result: EvaluationResult) -> None:
        """Valid input should not raise exceptions."""
        # Should not raise
        envelope = create_envelope_from_result(allow_result)
        assert envelope is not None

    def test_envelope_handles_none_reason_detail(self) -> None:
        """Envelope handles None reason_detail gracefully."""
        result = EvaluationResult(
            decision=ACMDecision.ALLOW,
            agent_gid="GID-01",
            intent_verb="READ",
            intent_target="data",
            reason=None,
            reason_detail=None,  # None
            acm_version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=None,
        )
        envelope = create_envelope_from_result(result)
        assert envelope.reason_detail == ""  # Converted to empty string

    def test_envelope_handles_none_correction_plan(self, allow_result: EvaluationResult) -> None:
        """Envelope handles None correction_plan gracefully."""
        envelope = create_envelope_from_result(allow_result)
        assert envelope.correction_plan is None  # Preserved as None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidation:
    """Tests for envelope validation."""

    def test_validate_allow_envelope(self, allow_result: EvaluationResult) -> None:
        """Valid ALLOW envelope passes validation."""
        envelope = create_envelope_from_result(allow_result)
        assert validate_envelope(envelope) is True

    def test_validate_deny_envelope(self, deny_result: EvaluationResult) -> None:
        """Valid DENY envelope passes validation."""
        envelope = create_envelope_from_result(deny_result)
        assert validate_envelope(envelope) is True

    def test_validation_fails_on_deny_with_none_reason(self) -> None:
        """DENY with NONE reason_code fails validation."""
        envelope = GatewayDecisionEnvelope(
            version=CDE_VERSION,
            decision=GatewayDecision.DENY,
            reason_code=ReasonCode.NONE,  # Invalid for DENY
            reason_detail="This should not be allowed",
            human_required=False,
            next_hop=None,
            allowed_tools=[],
            audit_ref="cde-invalid",
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_gid="GID-01",
            intent_verb="EXECUTE",
            intent_target="data",
        )

        with pytest.raises(EnvelopeMalformedError) as exc_info:
            validate_envelope(envelope)

        assert "DENY" in str(exc_info.value)
        assert "reason_code" in str(exc_info.value)

    def test_validation_fails_on_deny_with_tools(self) -> None:
        """DENY with non-empty allowed_tools fails validation."""
        # Use object.__new__ to bypass __post_init__ for testing
        envelope = object.__new__(GatewayDecisionEnvelope)
        object.__setattr__(envelope, "version", CDE_VERSION)
        object.__setattr__(envelope, "decision", GatewayDecision.DENY)
        object.__setattr__(envelope, "reason_code", ReasonCode.VERB_NOT_PERMITTED)
        object.__setattr__(envelope, "reason_detail", "Not permitted")
        object.__setattr__(envelope, "human_required", False)
        object.__setattr__(envelope, "next_hop", None)
        object.__setattr__(envelope, "allowed_tools", ["some_tool"])  # Invalid
        object.__setattr__(envelope, "audit_ref", "cde-invalid")
        object.__setattr__(envelope, "timestamp", datetime.now(timezone.utc).isoformat())
        object.__setattr__(envelope, "agent_gid", "GID-01")
        object.__setattr__(envelope, "intent_verb", "EXECUTE")
        object.__setattr__(envelope, "intent_target", "data")
        object.__setattr__(envelope, "correction_plan", None)

        with pytest.raises(EnvelopeMalformedError) as exc_info:
            validate_envelope(envelope)

        assert "allowed_tools" in str(exc_info.value)

    def test_validation_fails_on_allow_with_reason(self) -> None:
        """ALLOW with non-NONE reason_code fails validation."""
        # Use object.__new__ to bypass __post_init__ for testing
        envelope = object.__new__(GatewayDecisionEnvelope)
        object.__setattr__(envelope, "version", CDE_VERSION)
        object.__setattr__(envelope, "decision", GatewayDecision.ALLOW)
        object.__setattr__(envelope, "reason_code", ReasonCode.VERB_NOT_PERMITTED)  # Invalid
        object.__setattr__(envelope, "reason_detail", "")
        object.__setattr__(envelope, "human_required", False)
        object.__setattr__(envelope, "next_hop", None)
        object.__setattr__(envelope, "allowed_tools", [])
        object.__setattr__(envelope, "audit_ref", "cde-invalid")
        object.__setattr__(envelope, "timestamp", datetime.now(timezone.utc).isoformat())
        object.__setattr__(envelope, "agent_gid", "GID-01")
        object.__setattr__(envelope, "intent_verb", "READ")
        object.__setattr__(envelope, "intent_target", "data")
        object.__setattr__(envelope, "correction_plan", None)

        with pytest.raises(EnvelopeMalformedError) as exc_info:
            validate_envelope(envelope)

        assert "ALLOW" in str(exc_info.value)

    def test_validation_fails_on_empty_audit_ref(self) -> None:
        """Empty audit_ref fails validation."""
        with pytest.raises(EnvelopeMalformedError) as exc_info:
            GatewayDecisionEnvelope(
                version=CDE_VERSION,
                decision=GatewayDecision.ALLOW,
                reason_code=ReasonCode.NONE,
                reason_detail="",
                human_required=False,
                next_hop=None,
                allowed_tools=[],
                audit_ref="",  # Empty
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_gid="GID-01",
                intent_verb="READ",
                intent_target="data",
            )

        assert "audit_ref" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: REASON CODE MAPPING
# ═══════════════════════════════════════════════════════════════════════════════


class TestReasonCodeMapping:
    """Tests for denial reason to reason code mapping."""

    def test_all_denial_reasons_have_mapping(self) -> None:
        """All DenialReason values should map to a ReasonCode."""
        for reason in DenialReason:
            code = map_denial_reason(reason)
            assert code != ReasonCode.UNKNOWN, f"DenialReason.{reason.name} has no mapping"

    def test_none_reason_maps_to_none_code(self) -> None:
        """None reason maps to ReasonCode.NONE."""
        code = map_denial_reason(None)
        assert code == ReasonCode.NONE

    def test_specific_mappings(self) -> None:
        """Test specific denial reason mappings."""
        assert map_denial_reason(DenialReason.VERB_NOT_PERMITTED) == ReasonCode.VERB_NOT_PERMITTED
        assert map_denial_reason(DenialReason.UNKNOWN_AGENT) == ReasonCode.UNKNOWN_AGENT
        assert map_denial_reason(DenialReason.ATLAS_DOMAIN_VIOLATION) == ReasonCode.ATLAS_DOMAIN_VIOLATION
        assert map_denial_reason(DenialReason.CHAIN_OF_COMMAND_VIOLATION) == ReasonCode.CHAIN_OF_COMMAND_VIOLATION


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: AUDIT REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditReference:
    """Tests for audit reference generation."""

    def test_audit_ref_is_unique(self, allow_result: EvaluationResult) -> None:
        """Each envelope should have a unique audit_ref."""
        envelope1 = create_envelope_from_result(allow_result)
        envelope2 = create_envelope_from_result(allow_result)

        assert envelope1.audit_ref != envelope2.audit_ref

    def test_audit_ref_has_prefix(self, allow_result: EvaluationResult) -> None:
        """audit_ref should have cde- prefix."""
        envelope = create_envelope_from_result(allow_result)
        assert envelope.audit_ref.startswith("cde-")

    def test_audit_ref_is_deterministic_length(self, allow_result: EvaluationResult) -> None:
        """audit_ref should have consistent length."""
        envelope = create_envelope_from_result(allow_result)
        # "cde-" + 12 hex chars = 16 chars
        assert len(envelope.audit_ref) == 16


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: IMMUTABILITY
# ═══════════════════════════════════════════════════════════════════════════════


class TestImmutability:
    """Tests for envelope immutability."""

    def test_envelope_is_frozen(self, allow_result: EvaluationResult) -> None:
        """Envelope should be immutable (frozen dataclass)."""
        envelope = create_envelope_from_result(allow_result)

        with pytest.raises(AttributeError):
            envelope.decision = GatewayDecision.DENY  # type: ignore

    def test_envelope_fields_cannot_be_modified(self, allow_result: EvaluationResult) -> None:
        """Individual fields cannot be modified."""
        envelope = create_envelope_from_result(allow_result)

        with pytest.raises(AttributeError):
            envelope.agent_gid = "GID-99"  # type: ignore
