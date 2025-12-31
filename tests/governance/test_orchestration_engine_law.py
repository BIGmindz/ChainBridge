"""
ChainBridge Orchestration Engine Law Tests — PAC-017
════════════════════════════════════════════════════════════════════════════════

Tests for the Orchestration Engine Law per PAC-017:
- Drafting surface cannot issue WRAP/BER
- Agent cannot impersonate orchestrator
- BER rejected if issuer != orchestration engine
- Persona strings ignored for authority

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-ORCHESTRATION-ENGINE-RENAMING-017
Effective Date: 2025-12-26

════════════════════════════════════════════════════════════════════════════════
"""

import pytest

from core.governance.system_identities import (
    # Enums
    SystemIdentityType,
    # Classes
    SystemIdentity,
    SystemIdentityRegistry,
    # Canonical Identities
    ORCHESTRATION_ENGINE,
    EXECUTION_ENGINE,
    DRAFTING_SURFACE,
    # Exceptions
    SystemIdentityError,
    UnknownSystemIdentityError,
    BERAuthorityError,
    WRAPAuthorityError,
    PersonaAuthorityError,
    SelfApprovalError,
    # Validators
    validate_ber_authority,
    validate_wrap_authority,
    reject_persona_authority,
    validate_not_self_approval,
    # Convenience Functions
    get_orchestration_engine,
    get_execution_engine,
    get_drafting_surface,
    is_system_component,
    is_ber_authorized,
    is_wrap_authorized,
    # Invariants
    INVARIANTS,
    check_invariant_orc_001,
    check_invariant_orc_002,
    check_invariant_orc_003,
    check_invariant_orc_005,
)

from core.governance.enforcement import (
    enforce_ber_authority,
    enforce_wrap_authority,
    enforce_no_self_approval,
    enforce_no_persona_authority,
    enforce_drafting_surface_cannot_govern,
    EnforcementChainError,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SYSTEM IDENTITY TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemIdentityType:
    """Test SystemIdentityType enum properties."""
    
    def test_system_orchestrator_is_system(self):
        """SYSTEM_ORCHESTRATOR is a system component."""
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.is_system is True
    
    def test_system_execution_is_system(self):
        """SYSTEM_EXECUTION is a system component."""
        assert SystemIdentityType.SYSTEM_EXECUTION.is_system is True
    
    def test_drafting_surface_is_not_system(self):
        """DRAFTING_SURFACE is not a system component."""
        assert SystemIdentityType.DRAFTING_SURFACE.is_system is False
    
    def test_agent_is_not_system(self):
        """AGENT is not a system component."""
        assert SystemIdentityType.AGENT.is_system is False
    
    def test_only_agent_has_persona(self):
        """Only AGENT has a persona."""
        assert SystemIdentityType.AGENT.has_persona is True
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.has_persona is False
        assert SystemIdentityType.SYSTEM_EXECUTION.has_persona is False
        assert SystemIdentityType.DRAFTING_SURFACE.has_persona is False
    
    def test_only_drafting_surface_is_conversational(self):
        """Only DRAFTING_SURFACE is conversational."""
        assert SystemIdentityType.DRAFTING_SURFACE.is_conversational is True
        assert SystemIdentityType.AGENT.is_conversational is False
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.is_conversational is False
        assert SystemIdentityType.SYSTEM_EXECUTION.is_conversational is False
    
    def test_only_orchestrator_can_issue_ber(self):
        """Only SYSTEM_ORCHESTRATOR can issue BER."""
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.can_issue_ber is True
        assert SystemIdentityType.SYSTEM_EXECUTION.can_issue_ber is False
        assert SystemIdentityType.DRAFTING_SURFACE.can_issue_ber is False
        assert SystemIdentityType.AGENT.can_issue_ber is False
    
    def test_only_agent_can_issue_wrap(self):
        """Only AGENT can issue WRAP."""
        assert SystemIdentityType.AGENT.can_issue_wrap is True
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.can_issue_wrap is False
        assert SystemIdentityType.SYSTEM_EXECUTION.can_issue_wrap is False
        assert SystemIdentityType.DRAFTING_SURFACE.can_issue_wrap is False
    
    def test_only_drafting_surface_can_emit_pac(self):
        """Only DRAFTING_SURFACE can emit PAC."""
        assert SystemIdentityType.DRAFTING_SURFACE.can_emit_pac is True
        assert SystemIdentityType.AGENT.can_emit_pac is False
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.can_emit_pac is False
        assert SystemIdentityType.SYSTEM_EXECUTION.can_emit_pac is False
    
    def test_only_agent_can_execute_work(self):
        """Only AGENT can execute work."""
        assert SystemIdentityType.AGENT.can_execute_work is True
        assert SystemIdentityType.SYSTEM_ORCHESTRATOR.can_execute_work is False
        assert SystemIdentityType.SYSTEM_EXECUTION.can_execute_work is False
        assert SystemIdentityType.DRAFTING_SURFACE.can_execute_work is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CANONICAL SYSTEM IDENTITIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalIdentities:
    """Test canonical system identity definitions."""
    
    def test_orchestration_engine_identity(self):
        """ORCHESTRATION_ENGINE is correctly defined."""
        assert ORCHESTRATION_ENGINE.identity_id == "ORCHESTRATION_ENGINE"
        assert ORCHESTRATION_ENGINE.identity_type == SystemIdentityType.SYSTEM_ORCHESTRATOR
        assert ORCHESTRATION_ENGINE.is_system is True
        assert ORCHESTRATION_ENGINE.has_persona is False
        assert ORCHESTRATION_ENGINE.can_issue_ber is True
        assert ORCHESTRATION_ENGINE.can_issue_wrap is False
    
    def test_execution_engine_identity(self):
        """EXECUTION_ENGINE is correctly defined."""
        assert EXECUTION_ENGINE.identity_id == "EXECUTION_ENGINE"
        assert EXECUTION_ENGINE.identity_type == SystemIdentityType.SYSTEM_EXECUTION
        assert EXECUTION_ENGINE.is_system is True
        assert EXECUTION_ENGINE.has_persona is False
        assert EXECUTION_ENGINE.can_issue_ber is False
        assert EXECUTION_ENGINE.can_issue_wrap is False
    
    def test_drafting_surface_identity(self):
        """DRAFTING_SURFACE is correctly defined."""
        assert DRAFTING_SURFACE.identity_id == "DRAFTING_SURFACE"
        assert DRAFTING_SURFACE.identity_type == SystemIdentityType.DRAFTING_SURFACE
        assert DRAFTING_SURFACE.is_system is False
        assert DRAFTING_SURFACE.has_persona is False
        assert DRAFTING_SURFACE.is_conversational is True
        assert DRAFTING_SURFACE.can_issue_ber is False
        assert DRAFTING_SURFACE.can_issue_wrap is False
    
    def test_identity_is_frozen(self):
        """SystemIdentity is immutable."""
        with pytest.raises(Exception):  # FrozenInstanceError
            ORCHESTRATION_ENGINE.identity_id = "HACKED"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SYSTEM IDENTITY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemIdentityRegistry:
    """Test SystemIdentityRegistry lookups."""
    
    def test_get_orchestration_engine(self):
        """Can get ORCHESTRATION_ENGINE by ID."""
        identity = SystemIdentityRegistry.get("ORCHESTRATION_ENGINE")
        assert identity == ORCHESTRATION_ENGINE
    
    def test_get_execution_engine(self):
        """Can get EXECUTION_ENGINE by ID."""
        identity = SystemIdentityRegistry.get("EXECUTION_ENGINE")
        assert identity == EXECUTION_ENGINE
    
    def test_get_drafting_surface(self):
        """Can get DRAFTING_SURFACE by ID."""
        identity = SystemIdentityRegistry.get("DRAFTING_SURFACE")
        assert identity == DRAFTING_SURFACE
    
    def test_get_unknown_returns_none(self):
        """Unknown identity returns None."""
        identity = SystemIdentityRegistry.get("UNKNOWN_IDENTITY")
        assert identity is None
    
    def test_get_or_fail_raises_on_unknown(self):
        """get_or_fail raises on unknown identity."""
        with pytest.raises(UnknownSystemIdentityError) as exc_info:
            SystemIdentityRegistry.get_or_fail("UNKNOWN_IDENTITY")
        
        assert "UNKNOWN_IDENTITY" in str(exc_info.value)
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_is_valid(self):
        """is_valid returns correct boolean."""
        assert SystemIdentityRegistry.is_valid("ORCHESTRATION_ENGINE") is True
        assert SystemIdentityRegistry.is_valid("UNKNOWN") is False
    
    def test_all_identities(self):
        """all_identities returns all registered identities."""
        identities = SystemIdentityRegistry.all_identities()
        assert len(identities) == 3
        assert ORCHESTRATION_ENGINE in identities
        assert EXECUTION_ENGINE in identities
        assert DRAFTING_SURFACE in identities
    
    def test_ber_issuers(self):
        """ber_issuers returns only orchestration engine."""
        issuers = SystemIdentityRegistry.ber_issuers()
        assert len(issuers) == 1
        assert ORCHESTRATION_ENGINE in issuers
    
    def test_wrap_issuers(self):
        """wrap_issuers returns empty (only agents can issue WRAP)."""
        issuers = SystemIdentityRegistry.wrap_issuers()
        assert len(issuers) == 0  # No system identities can issue WRAP


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BER AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestBERAuthority:
    """Test BER authority validation."""
    
    def test_orchestrator_can_issue_ber(self):
        """SYSTEM_ORCHESTRATOR can issue BER."""
        assert validate_ber_authority(
            "ORCHESTRATION_ENGINE",
            SystemIdentityType.SYSTEM_ORCHESTRATOR
        ) is True
    
    def test_execution_engine_cannot_issue_ber(self):
        """SYSTEM_EXECUTION cannot issue BER."""
        with pytest.raises(BERAuthorityError) as exc_info:
            validate_ber_authority(
                "EXECUTION_ENGINE",
                SystemIdentityType.SYSTEM_EXECUTION
            )
        
        assert "HARD FAIL" in str(exc_info.value)
        assert "SYSTEM_ORCHESTRATOR" in str(exc_info.value)
    
    def test_drafting_surface_cannot_issue_ber(self):
        """DRAFTING_SURFACE cannot issue BER."""
        with pytest.raises(BERAuthorityError) as exc_info:
            validate_ber_authority(
                "DRAFTING_SURFACE",
                SystemIdentityType.DRAFTING_SURFACE
            )
        
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_agent_cannot_issue_ber(self):
        """AGENT cannot issue BER."""
        with pytest.raises(BERAuthorityError) as exc_info:
            validate_ber_authority(
                "GID-01",
                SystemIdentityType.AGENT
            )
        
        assert "HARD FAIL" in str(exc_info.value)
        assert "GID-01" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: WRAP AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestWRAPAuthority:
    """Test WRAP authority validation."""
    
    def test_agent_can_issue_wrap(self):
        """AGENT can issue WRAP."""
        assert validate_wrap_authority(
            "GID-01",
            SystemIdentityType.AGENT
        ) is True
    
    def test_orchestrator_cannot_issue_wrap(self):
        """SYSTEM_ORCHESTRATOR cannot issue WRAP."""
        with pytest.raises(WRAPAuthorityError) as exc_info:
            validate_wrap_authority(
                "ORCHESTRATION_ENGINE",
                SystemIdentityType.SYSTEM_ORCHESTRATOR
            )
        
        assert "HARD FAIL" in str(exc_info.value)
        assert "AGENT" in str(exc_info.value)
    
    def test_execution_engine_cannot_issue_wrap(self):
        """SYSTEM_EXECUTION cannot issue WRAP."""
        with pytest.raises(WRAPAuthorityError) as exc_info:
            validate_wrap_authority(
                "EXECUTION_ENGINE",
                SystemIdentityType.SYSTEM_EXECUTION
            )
        
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_drafting_surface_cannot_issue_wrap(self):
        """DRAFTING_SURFACE cannot issue WRAP."""
        with pytest.raises(WRAPAuthorityError) as exc_info:
            validate_wrap_authority(
                "DRAFTING_SURFACE",
                SystemIdentityType.DRAFTING_SURFACE
            )
        
        assert "HARD FAIL" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PERSONA AUTHORITY REJECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonaAuthorityRejection:
    """Test persona-based authority rejection."""
    
    def test_persona_authority_always_rejected(self):
        """Persona authority is always rejected."""
        with pytest.raises(PersonaAuthorityError) as exc_info:
            reject_persona_authority("Benson")
        
        assert "HARD FAIL" in str(exc_info.value)
        assert "Benson" in str(exc_info.value)
        assert "zero authority weight" in str(exc_info.value)
    
    def test_any_persona_rejected(self):
        """Any persona string is rejected."""
        personas = ["Benson", "Cody", "Jeffrey", "Admin", "Root"]
        
        for persona in personas:
            with pytest.raises(PersonaAuthorityError):
                reject_persona_authority(persona)
    
    def test_enforce_no_persona_authority(self):
        """enforce_no_persona_authority raises."""
        with pytest.raises(PersonaAuthorityError) as exc_info:
            enforce_no_persona_authority("Benson")
        
        assert "HARD FAIL" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SELF-APPROVAL PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfApprovalPrevention:
    """Test self-approval prevention."""
    
    def test_different_agents_can_approve(self):
        """Different agents can approve each other's work."""
        # GID-00 approving GID-01's work
        assert validate_not_self_approval("GID-00", "GID-01") is True
    
    def test_self_approval_blocked(self):
        """Self-approval is blocked."""
        with pytest.raises(SelfApprovalError) as exc_info:
            validate_not_self_approval("GID-01", "GID-01")
        
        assert "HARD FAIL" in str(exc_info.value)
        assert "GID-01" in str(exc_info.value)
        assert "Self-approval forbidden" in str(exc_info.value)
    
    def test_enforce_no_self_approval(self):
        """enforce_no_self_approval works correctly."""
        # Valid case
        assert enforce_no_self_approval("GID-00", "GID-01") is True
        
        # Invalid case
        with pytest.raises(SelfApprovalError):
            enforce_no_self_approval("GID-01", "GID-01")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: DRAFTING SURFACE GOVERNANCE PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDraftingSurfaceCannotGovern:
    """Test drafting surface cannot perform governance actions."""
    
    def test_drafting_surface_blocked_from_governance(self):
        """Drafting surface cannot govern."""
        with pytest.raises(EnforcementChainError) as exc_info:
            enforce_drafting_surface_cannot_govern("DRAFTING_SURFACE")
        
        assert "DRAFTING_SURFACE_GOVERNANCE" in str(exc_info.value)
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_orchestrator_can_govern(self):
        """Orchestrator can perform governance actions."""
        assert enforce_drafting_surface_cannot_govern("ORCHESTRATION_ENGINE") is True
    
    def test_agent_gid_can_govern(self):
        """Agent GID can perform governance actions (WRAP only)."""
        assert enforce_drafting_surface_cannot_govern("GID-01") is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ENFORCEMENT BER AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnforceBERAuthority:
    """Test enforcement-level BER authority validation."""
    
    def test_orchestration_engine_authorized(self):
        """ORCHESTRATION_ENGINE is authorized to issue BER."""
        assert enforce_ber_authority("ORCHESTRATION_ENGINE") is True
    
    def test_execution_engine_not_authorized(self):
        """EXECUTION_ENGINE is not authorized to issue BER."""
        with pytest.raises(BERAuthorityError):
            enforce_ber_authority("EXECUTION_ENGINE")
    
    def test_drafting_surface_not_authorized(self):
        """DRAFTING_SURFACE is not authorized to issue BER."""
        with pytest.raises(BERAuthorityError):
            enforce_ber_authority("DRAFTING_SURFACE")
    
    def test_agent_gid_not_authorized(self):
        """Agent GID is not authorized to issue BER."""
        with pytest.raises(BERAuthorityError):
            enforce_ber_authority("GID-01")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ENFORCEMENT WRAP AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnforceWRAPAuthority:
    """Test enforcement-level WRAP authority validation."""
    
    def test_agent_gid_authorized(self):
        """Agent GID is authorized to issue WRAP."""
        assert enforce_wrap_authority("GID-01") is True
        assert enforce_wrap_authority("GID-12") is True
    
    def test_orchestration_engine_not_authorized(self):
        """ORCHESTRATION_ENGINE is not authorized to issue WRAP."""
        with pytest.raises(WRAPAuthorityError):
            enforce_wrap_authority("ORCHESTRATION_ENGINE")
    
    def test_execution_engine_not_authorized(self):
        """EXECUTION_ENGINE is not authorized to issue WRAP."""
        with pytest.raises(WRAPAuthorityError):
            enforce_wrap_authority("EXECUTION_ENGINE")
    
    def test_drafting_surface_not_authorized(self):
        """DRAFTING_SURFACE is not authorized to issue WRAP."""
        with pytest.raises(WRAPAuthorityError):
            enforce_wrap_authority("DRAFTING_SURFACE")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INVARIANT CHECKERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariantCheckers:
    """Test invariant checker functions."""
    
    def test_invariants_defined(self):
        """All invariants are defined."""
        expected_invariants = {
            "INV-ORC-001",
            "INV-ORC-002",
            "INV-ORC-003",
            "INV-ORC-004",
            "INV-ORC-005",
            "INV-ORC-006",
            "INV-ORC-007",
        }
        assert INVARIANTS == expected_invariants
    
    def test_orc_001_only_orchestrator_issues_ber(self):
        """INV-ORC-001: Only SYSTEM_ORCHESTRATOR may issue BER."""
        assert check_invariant_orc_001(SystemIdentityType.SYSTEM_ORCHESTRATOR) is True
        assert check_invariant_orc_001(SystemIdentityType.SYSTEM_EXECUTION) is False
        assert check_invariant_orc_001(SystemIdentityType.DRAFTING_SURFACE) is False
        assert check_invariant_orc_001(SystemIdentityType.AGENT) is False
    
    def test_orc_002_drafting_surface_cannot_emit_wrap_ber(self):
        """INV-ORC-002: DRAFTING_SURFACE may never emit WRAP or BER."""
        assert check_invariant_orc_002(SystemIdentityType.SYSTEM_ORCHESTRATOR) is True
        assert check_invariant_orc_002(SystemIdentityType.SYSTEM_EXECUTION) is True
        assert check_invariant_orc_002(SystemIdentityType.AGENT) is True
        assert check_invariant_orc_002(SystemIdentityType.DRAFTING_SURFACE) is False
    
    def test_orc_003_no_self_approval(self):
        """INV-ORC-003: AGENT may never self-approve."""
        assert check_invariant_orc_003("GID-00", "GID-01") is True
        assert check_invariant_orc_003("GID-01", "GID-01") is False
    
    def test_orc_005_system_has_no_persona(self):
        """INV-ORC-005: System components have no persona."""
        assert check_invariant_orc_005(SystemIdentityType.SYSTEM_ORCHESTRATOR) is True
        assert check_invariant_orc_005(SystemIdentityType.SYSTEM_EXECUTION) is True
        # Non-system types always pass this check (it's about system components)
        assert check_invariant_orc_005(SystemIdentityType.AGENT) is True
        assert check_invariant_orc_005(SystemIdentityType.DRAFTING_SURFACE) is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_orchestration_engine(self):
        """get_orchestration_engine returns correct identity."""
        assert get_orchestration_engine() == ORCHESTRATION_ENGINE
    
    def test_get_execution_engine(self):
        """get_execution_engine returns correct identity."""
        assert get_execution_engine() == EXECUTION_ENGINE
    
    def test_get_drafting_surface(self):
        """get_drafting_surface returns correct identity."""
        assert get_drafting_surface() == DRAFTING_SURFACE
    
    def test_is_system_component(self):
        """is_system_component works correctly."""
        assert is_system_component("ORCHESTRATION_ENGINE") is True
        assert is_system_component("EXECUTION_ENGINE") is True
        assert is_system_component("DRAFTING_SURFACE") is False
        assert is_system_component("UNKNOWN") is False
    
    def test_is_ber_authorized(self):
        """is_ber_authorized works correctly."""
        assert is_ber_authorized("ORCHESTRATION_ENGINE") is True
        assert is_ber_authorized("EXECUTION_ENGINE") is False
        assert is_ber_authorized("DRAFTING_SURFACE") is False
        assert is_ber_authorized("GID-01") is False
    
    def test_is_wrap_authorized(self):
        """is_wrap_authorized works correctly (only agents in registry)."""
        # System identities cannot issue WRAP
        assert is_wrap_authorized("ORCHESTRATION_ENGINE") is False
        assert is_wrap_authorized("EXECUTION_ENGINE") is False
        assert is_wrap_authorized("DRAFTING_SURFACE") is False
        # GIDs are not in system identity registry, so None
        assert is_wrap_authorized("GID-01") is False  # Not in system registry


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EXCEPTION MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptionMessages:
    """Test exception message content."""
    
    def test_ber_authority_error_message(self):
        """BERAuthorityError has informative message."""
        error = BERAuthorityError("GID-01", SystemIdentityType.AGENT)
        assert "HARD FAIL" in str(error)
        assert "GID-01" in str(error)
        assert "AGENT" in str(error)
        assert "SYSTEM_ORCHESTRATOR" in str(error)
    
    def test_wrap_authority_error_message(self):
        """WRAPAuthorityError has informative message."""
        error = WRAPAuthorityError("DRAFTING_SURFACE", SystemIdentityType.DRAFTING_SURFACE)
        assert "HARD FAIL" in str(error)
        assert "DRAFTING_SURFACE" in str(error)
        assert "AGENT" in str(error)
    
    def test_persona_authority_error_message(self):
        """PersonaAuthorityError has informative message."""
        error = PersonaAuthorityError("Benson")
        assert "HARD FAIL" in str(error)
        assert "Benson" in str(error)
        assert "zero authority weight" in str(error)
        assert "code-enforced" in str(error)
    
    def test_self_approval_error_message(self):
        """SelfApprovalError has informative message."""
        error = SelfApprovalError("GID-01")
        assert "HARD FAIL" in str(error)
        assert "GID-01" in str(error)
        assert "Self-approval forbidden" in str(error)
        assert "ORCHESTRATION_ENGINE" in str(error)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AGENT IMPERSONATION PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentImpersonationPrevention:
    """Test that agents cannot impersonate the orchestrator."""
    
    def test_agent_cannot_claim_orchestrator_role(self):
        """Agent GID cannot claim orchestrator BER authority."""
        with pytest.raises(BERAuthorityError):
            enforce_ber_authority("GID-01")
    
    def test_agent_cannot_use_orchestrator_identity(self):
        """Agent cannot use ORCHESTRATION_ENGINE identity."""
        # The only way to issue BER is with ORCHESTRATION_ENGINE identity
        assert enforce_ber_authority("ORCHESTRATION_ENGINE") is True
        
        # Any other identity fails
        for gid in ["GID-01", "GID-02", "GID-00"]:
            with pytest.raises(BERAuthorityError):
                enforce_ber_authority(gid)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    def test_valid_pac_to_ber_flow(self):
        """Valid flow: Drafting surface → Agent → Orchestrator BER."""
        # 1. Drafting surface emits PAC (not enforced here, but valid)
        assert DRAFTING_SURFACE.identity_type.can_emit_pac is True
        
        # 2. Agent executes and returns WRAP
        assert enforce_wrap_authority("GID-01") is True
        
        # 3. Orchestrator validates and issues BER
        assert enforce_ber_authority("ORCHESTRATION_ENGINE") is True
        
        # 4. No self-approval (orchestrator != agent)
        assert enforce_no_self_approval("ORCHESTRATION_ENGINE", "GID-01") is True
    
    def test_invalid_agent_ber_attempt(self):
        """Invalid: Agent attempts to issue BER."""
        # Agent returns WRAP (valid)
        assert enforce_wrap_authority("GID-01") is True
        
        # Agent attempts to issue BER (HARD FAIL)
        with pytest.raises(BERAuthorityError):
            enforce_ber_authority("GID-01")
    
    def test_invalid_drafting_surface_wrap_attempt(self):
        """Invalid: Drafting surface attempts to issue WRAP."""
        with pytest.raises(WRAPAuthorityError):
            enforce_wrap_authority("DRAFTING_SURFACE")
    
    def test_invalid_drafting_surface_ber_attempt(self):
        """Invalid: Drafting surface attempts to issue BER."""
        with pytest.raises(BERAuthorityError):
            enforce_ber_authority("DRAFTING_SURFACE")
    
    def test_persona_based_ber_rejected(self):
        """Persona-based BER authority is rejected."""
        # Even if someone claims "As Benson, I approve..."
        with pytest.raises(PersonaAuthorityError):
            enforce_no_persona_authority("Benson")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: OUTPUT DETERMINISM
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputDeterminism:
    """Test that outputs are deterministic."""
    
    def test_identity_properties_are_stable(self):
        """Identity properties are stable across calls."""
        for _ in range(10):
            assert ORCHESTRATION_ENGINE.identity_id == "ORCHESTRATION_ENGINE"
            assert ORCHESTRATION_ENGINE.can_issue_ber is True
            assert DRAFTING_SURFACE.can_issue_ber is False
    
    def test_registry_is_stable(self):
        """Registry returns same identities."""
        for _ in range(10):
            assert SystemIdentityRegistry.get("ORCHESTRATION_ENGINE") == ORCHESTRATION_ENGINE
            assert len(SystemIdentityRegistry.ber_issuers()) == 1
    
    def test_exception_content_is_deterministic(self):
        """Exception messages are deterministic."""
        messages = set()
        for _ in range(10):
            try:
                enforce_ber_authority("GID-01")
            except BERAuthorityError as e:
                messages.add(str(e))
        
        # Should only have one unique message
        assert len(messages) == 1
