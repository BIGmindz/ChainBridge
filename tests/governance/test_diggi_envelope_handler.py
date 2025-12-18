"""
Tests for Diggi Envelope Handler — PAC-DIGGI-05

These tests verify that Diggi:
1. Consumes only CDE (GatewayDecisionEnvelope)
2. Produces bounded, deterministic corrections
3. Cannot suggest forbidden verbs (EXECUTE, BLOCK, APPROVE)
4. Handles all reason codes with appropriate corrections
5. Preserves audit_ref linkage

Author: ATLAS (GID-11)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.governance.diggi_envelope_handler import (
    DIGGI_ALLOWED_VERBS,
    DIGGI_FORBIDDEN_VERBS,
    DIGGI_GID,
    CorrectionOption,
    DiggiCorrectionResponse,
    DiggiEnvelopeError,
    EnvelopeNotDenyError,
    ForbiddenVerbError,
    can_diggi_handle,
    get_correction_for_reason,
    process_denial_envelope,
)
from gateway.decision_envelope import (
    CDE_VERSION,
    GatewayDecision,
    GatewayDecisionEnvelope,
    ReasonCode,
    create_allow_envelope,
    create_deny_envelope,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def deny_envelope_verb_not_permitted() -> GatewayDecisionEnvelope:
    """DENY envelope for VERB_NOT_PERMITTED."""
    return create_deny_envelope(
        agent_gid="GID-01",
        intent_verb="EXECUTE",
        intent_target="core/payment",
        reason_code=ReasonCode.VERB_NOT_PERMITTED,
        reason_detail="Agent does not have EXECUTE permission",
        next_hop=DIGGI_GID,
    )


@pytest.fixture
def deny_envelope_chain_violation() -> GatewayDecisionEnvelope:
    """DENY envelope for CHAIN_OF_COMMAND_VIOLATION."""
    return create_deny_envelope(
        agent_gid="GID-05",
        intent_verb="EXECUTE",
        intent_target="api/endpoint",
        reason_code=ReasonCode.CHAIN_OF_COMMAND_VIOLATION,
        reason_detail="EXECUTE requires routing through GID-00",
        next_hop=DIGGI_GID,
    )


@pytest.fixture
def deny_envelope_human_required() -> GatewayDecisionEnvelope:
    """DENY envelope that requires human intervention."""
    return create_deny_envelope(
        agent_gid="GID-01",
        intent_verb="APPROVE",
        intent_target="payment/large",
        reason_code=ReasonCode.APPROVE_NOT_PERMITTED,
        reason_detail="APPROVE is human-only",
        next_hop=None,
        human_required=True,
    )


@pytest.fixture
def deny_envelope_with_correction_plan() -> GatewayDecisionEnvelope:
    """DENY envelope with embedded DCC correction_plan."""
    return create_deny_envelope(
        agent_gid="GID-01",
        intent_verb="EXECUTE",
        intent_target="data/records",
        reason_code=ReasonCode.EXECUTE_NOT_PERMITTED,
        reason_detail="No EXECUTE permission",
        next_hop=DIGGI_GID,
        correction_plan={
            "allowed_next_steps": [
                {"verb": "PROPOSE", "description": "Submit for approval"},
                {"verb": "ESCALATE", "target": "human", "description": "Request help"},
            ]
        },
    )


@pytest.fixture
def allow_envelope() -> GatewayDecisionEnvelope:
    """ALLOW envelope (Diggi should not handle)."""
    return create_allow_envelope(
        agent_gid="GID-01",
        intent_verb="READ",
        intent_target="data/metrics",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: ENVELOPE CONSUMPTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnvelopeConsumption:
    """Tests for CDE consumption."""

    def test_processes_deny_envelope(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Diggi processes DENY envelopes."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)

        assert isinstance(response, DiggiCorrectionResponse)
        assert response.reason_code == ReasonCode.VERB_NOT_PERMITTED

    def test_rejects_allow_envelope(self, allow_envelope: GatewayDecisionEnvelope) -> None:
        """Diggi rejects ALLOW envelopes."""
        with pytest.raises(EnvelopeNotDenyError) as exc_info:
            process_denial_envelope(allow_envelope)

        assert "DENY" in str(exc_info.value)
        assert "ALLOW" in str(exc_info.value)

    def test_preserves_audit_ref(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Response preserves original audit_ref."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)

        assert response.original_audit_ref == deny_envelope_verb_not_permitted.audit_ref

    def test_validates_cde_version(self) -> None:
        """Diggi validates CDE version."""
        # Create envelope with wrong version (bypass validation)
        envelope = object.__new__(GatewayDecisionEnvelope)
        object.__setattr__(envelope, "version", "2.0.0")
        object.__setattr__(envelope, "decision", GatewayDecision.DENY)
        object.__setattr__(envelope, "reason_code", ReasonCode.VERB_NOT_PERMITTED)
        object.__setattr__(envelope, "reason_detail", "Test")
        object.__setattr__(envelope, "human_required", False)
        object.__setattr__(envelope, "next_hop", DIGGI_GID)
        object.__setattr__(envelope, "allowed_tools", [])
        object.__setattr__(envelope, "audit_ref", "cde-test123")
        object.__setattr__(envelope, "timestamp", datetime.now(timezone.utc).isoformat())
        object.__setattr__(envelope, "agent_gid", "GID-01")
        object.__setattr__(envelope, "intent_verb", "EXECUTE")
        object.__setattr__(envelope, "intent_target", "test")
        object.__setattr__(envelope, "correction_plan", None)

        with pytest.raises(DiggiEnvelopeError) as exc_info:
            process_denial_envelope(envelope)

        assert "version" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: CORRECTION OPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCorrectionOptions:
    """Tests for correction option generation."""

    def test_produces_bounded_options(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Response contains bounded correction options."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)

        assert len(response.options) > 0
        for opt in response.options:
            assert isinstance(opt, CorrectionOption)
            assert opt.verb in DIGGI_ALLOWED_VERBS

    def test_options_have_descriptions(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """All options have descriptions."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)

        for opt in response.options:
            assert opt.description
            assert len(opt.description) > 0

    def test_uses_dcc_correction_plan_if_present(self, deny_envelope_with_correction_plan: GatewayDecisionEnvelope) -> None:
        """Uses embedded DCC correction_plan from envelope."""
        response = process_denial_envelope(deny_envelope_with_correction_plan)

        # Should use the DCC steps
        verbs = [opt.verb for opt in response.options]
        assert "PROPOSE" in verbs
        assert "ESCALATE" in verbs


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: FORBIDDEN VERBS
# ═══════════════════════════════════════════════════════════════════════════════


class TestForbiddenVerbs:
    """Tests for forbidden verb enforcement."""

    def test_forbidden_verbs_constant(self) -> None:
        """EXECUTE, BLOCK, APPROVE are forbidden."""
        assert "EXECUTE" in DIGGI_FORBIDDEN_VERBS
        assert "BLOCK" in DIGGI_FORBIDDEN_VERBS
        assert "APPROVE" in DIGGI_FORBIDDEN_VERBS

    def test_correction_option_rejects_execute(self) -> None:
        """CorrectionOption rejects EXECUTE verb."""
        with pytest.raises(ForbiddenVerbError):
            CorrectionOption(verb="EXECUTE", target=None, description="Bad")

    def test_correction_option_rejects_block(self) -> None:
        """CorrectionOption rejects BLOCK verb."""
        with pytest.raises(ForbiddenVerbError):
            CorrectionOption(verb="BLOCK", target=None, description="Bad")

    def test_correction_option_rejects_approve(self) -> None:
        """CorrectionOption rejects APPROVE verb."""
        with pytest.raises(ForbiddenVerbError):
            CorrectionOption(verb="APPROVE", target=None, description="Bad")

    def test_allowed_verbs_are_safe(self) -> None:
        """PROPOSE, ESCALATE, READ are allowed."""
        for verb in DIGGI_ALLOWED_VERBS:
            # Should not raise
            opt = CorrectionOption(verb=verb, target=None, description="OK")
            assert opt.verb == verb

    def test_no_forbidden_verbs_in_any_correction(self) -> None:
        """No correction mapping contains forbidden verbs."""
        for reason_code in ReasonCode:
            if reason_code == ReasonCode.NONE:
                continue
            mapping = get_correction_for_reason(reason_code)
            for opt in mapping.get("options", []):
                assert opt.verb.upper() not in DIGGI_FORBIDDEN_VERBS


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: HUMAN REQUIRED
# ═══════════════════════════════════════════════════════════════════════════════


class TestHumanRequired:
    """Tests for human_required handling."""

    def test_human_required_from_envelope(self, deny_envelope_human_required: GatewayDecisionEnvelope) -> None:
        """Response reflects human_required from envelope."""
        response = process_denial_envelope(deny_envelope_human_required)

        assert response.requires_human is True

    def test_human_required_from_mapping(self) -> None:
        """Some reason codes inherently require human."""
        envelope = create_deny_envelope(
            agent_gid="GID-01",
            intent_verb="APPROVE",
            intent_target="payment",
            reason_code=ReasonCode.APPROVE_NOT_PERMITTED,
            reason_detail="Only humans can approve",
        )
        response = process_denial_envelope(envelope)

        assert response.requires_human is True

    def test_unknown_agent_requires_human(self) -> None:
        """UNKNOWN_AGENT requires human intervention."""
        envelope = create_deny_envelope(
            agent_gid="GID-99",
            intent_verb="READ",
            intent_target="data",
            reason_code=ReasonCode.UNKNOWN_AGENT,
            reason_detail="Agent not in ACM",
        )
        response = process_denial_envelope(envelope)

        assert response.requires_human is True


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: REASON CODE COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════


class TestReasonCodeCoverage:
    """Tests for comprehensive reason code handling."""

    def test_handles_all_major_reason_codes(self) -> None:
        """Diggi handles all major denial reason codes."""
        reason_codes_to_test = [
            ReasonCode.VERB_NOT_PERMITTED,
            ReasonCode.TARGET_NOT_IN_SCOPE,
            ReasonCode.EXECUTE_NOT_PERMITTED,
            ReasonCode.BLOCK_NOT_PERMITTED,
            ReasonCode.CHAIN_OF_COMMAND_VIOLATION,
            ReasonCode.APPROVE_NOT_PERMITTED,
            ReasonCode.ATLAS_DOMAIN_VIOLATION,
            ReasonCode.UNKNOWN_AGENT,
        ]

        for reason_code in reason_codes_to_test:
            envelope = create_deny_envelope(
                agent_gid="GID-01",
                intent_verb="TEST",
                intent_target="test/target",
                reason_code=reason_code,
                reason_detail=f"Test for {reason_code.value}",
            )
            response = process_denial_envelope(envelope)

            assert response.reason_code == reason_code
            assert response.analysis  # Has analysis text
            assert response.options or response.requires_human  # Has path forward

    def test_handles_unknown_reason_with_default(self) -> None:
        """Unknown reason codes get default correction."""
        envelope = create_deny_envelope(
            agent_gid="GID-01",
            intent_verb="WEIRD",
            intent_target="unknown",
            reason_code=ReasonCode.UNKNOWN,
            reason_detail="Something unexpected",
        )
        response = process_denial_envelope(envelope)

        # Should get default correction (escalate to human)
        assert response.requires_human is True


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: CAN_DIGGI_HANDLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestCanDiggiHandle:
    """Tests for can_diggi_handle function."""

    def test_can_handle_deny_to_diggi(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Diggi can handle DENY with next_hop=GID-00."""
        assert can_diggi_handle(deny_envelope_verb_not_permitted) is True

    def test_cannot_handle_allow(self, allow_envelope: GatewayDecisionEnvelope) -> None:
        """Diggi cannot handle ALLOW."""
        assert can_diggi_handle(allow_envelope) is False

    def test_cannot_handle_deny_to_other_agent(self) -> None:
        """Diggi cannot handle DENY with next_hop to another agent."""
        envelope = create_deny_envelope(
            agent_gid="GID-01",
            intent_verb="BLOCK",
            intent_target="threat",
            reason_code=ReasonCode.BLOCK_NOT_PERMITTED,
            reason_detail="No BLOCK authority",
            next_hop="GID-06",  # Sam, not Diggi
        )
        assert can_diggi_handle(envelope) is False

    def test_can_handle_deny_with_none_next_hop(self) -> None:
        """Diggi can handle DENY with next_hop=None."""
        envelope = create_deny_envelope(
            agent_gid="GID-01",
            intent_verb="APPROVE",
            intent_target="payment",
            reason_code=ReasonCode.APPROVE_NOT_PERMITTED,
            reason_detail="Human only",
            next_hop=None,
        )
        assert can_diggi_handle(envelope) is True


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: RESPONSE CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════


class TestResponseContract:
    """Tests for DiggiCorrectionResponse contract."""

    def test_response_is_immutable(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Response is immutable (frozen dataclass)."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)

        with pytest.raises(AttributeError):
            response.analysis = "Modified"  # type: ignore

    def test_response_has_timestamp(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Response has timestamp."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)

        assert response.timestamp
        # Should be ISO format
        datetime.fromisoformat(response.timestamp.replace("Z", "+00:00"))

    def test_response_serializes_to_dict(self, deny_envelope_verb_not_permitted: GatewayDecisionEnvelope) -> None:
        """Response serializes to dictionary."""
        response = process_denial_envelope(deny_envelope_verb_not_permitted)
        data = response.to_dict()

        assert "diggi_response" in data
        assert data["diggi_response"]["original_audit_ref"] == response.original_audit_ref
        assert data["diggi_response"]["reason_code"] == response.reason_code.value

    def test_response_requires_audit_ref(self) -> None:
        """Response requires original_audit_ref."""
        with pytest.raises(DiggiEnvelopeError) as exc_info:
            DiggiCorrectionResponse(
                original_audit_ref="",  # Empty
                reason_code=ReasonCode.VERB_NOT_PERMITTED,
                analysis="Test",
                options=(CorrectionOption(verb="PROPOSE", target=None, description="Test"),),
                requires_human=False,
                recommendation=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        assert "audit_ref" in str(exc_info.value)

    def test_response_requires_options_or_human(self) -> None:
        """Response requires options OR requires_human=True."""
        with pytest.raises(DiggiEnvelopeError) as exc_info:
            DiggiCorrectionResponse(
                original_audit_ref="cde-abc123",
                reason_code=ReasonCode.VERB_NOT_PERMITTED,
                analysis="Test",
                options=(),  # Empty
                requires_human=False,  # Also False
                recommendation=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        assert "options" in str(exc_info.value).lower() or "human" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: DIGGI CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiggiConstants:
    """Tests for Diggi constants."""

    def test_diggi_gid_is_gid_00(self) -> None:
        """Diggi's GID is GID-00."""
        assert DIGGI_GID == "GID-00"

    def test_forbidden_and_allowed_are_disjoint(self) -> None:
        """Forbidden and allowed verbs have no overlap."""
        overlap = DIGGI_FORBIDDEN_VERBS & DIGGI_ALLOWED_VERBS
        assert len(overlap) == 0

    def test_allowed_verbs_are_finite(self) -> None:
        """Allowed verbs are a finite set."""
        assert len(DIGGI_ALLOWED_VERBS) < 10  # Bounded
