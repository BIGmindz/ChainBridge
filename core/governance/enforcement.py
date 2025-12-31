"""
ChainBridge Enforcement Orchestrator — HARD LAW Enforcement
════════════════════════════════════════════════════════════════════════════════

Central orchestration of all enforcement modules:
- GID Registry validation
- Mode Schema enforcement
- Tool Matrix stripping
- WRAP validation
- Echo-Back handshake

PAC Reference: PAC-BENSON-CTO-EXEC-CODY-IDENTITY-MODE-LAW-011
Effective Date: 2025-12-26

ENFORCEMENT PHILOSOPHY:
- FAIL-CLOSED: if uncertain, deny
- HARD FAIL: exceptions, not warnings
- NO CONVERSATIONAL FORGIVENESS

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Import all enforcement modules
from .gid_registry import (
    GID,
    AgentIdentity,
    GIDEnforcementError,
    GIDRegistry,
    InvalidGIDFormatError,
    LaneNotPermittedError,
    Mode,
    ModeNotPermittedError,
    PACAuthorityError,
    UnknownGIDError,
    format_echo_handshake,
    validate_agent_gid,
    validate_agent_lane,
    validate_agent_mode,
    validate_echo_handshake,
    validate_full_identity,
)
from .mode_schema import (
    MalformedFieldError,
    MissingFieldError,
    ModeDeclaration,
    ModeSchemaError,
    RoleMismatchError,
    create_mode_declaration,
    extract_mode_from_pac,
    validate_mode_declaration,
)
from .tool_matrix import (
    ToolCategory,
    ToolMatrix,
    ToolMatrixResult,
    evaluate_tools,
    is_path_permitted,
    is_tool_permitted,
    strip_disallowed_tools,
)
from .wrap_validator import (
    ValidatedWRAP,
    WRAPValidationError,
    check_ber_eligibility,
    is_wrap_valid,
    validate_wrap,
)

# PAC-017: System Identity Enforcement
from .system_identities import (
    ORCHESTRATION_ENGINE,
    EXECUTION_ENGINE,
    DRAFTING_SURFACE,
    SystemIdentity,
    SystemIdentityType,
    SystemIdentityRegistry,
    SystemIdentityError,
    BERAuthorityError,
    WRAPAuthorityError,
    PersonaAuthorityError,
    SelfApprovalError,
    validate_ber_authority,
    validate_wrap_authority,
    reject_persona_authority,
    validate_not_self_approval,
    is_system_component,
    is_ber_authorized,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class EnforcementError(Exception):
    """Base exception for all enforcement failures."""
    pass


class EnforcementChainError(EnforcementError):
    """Raised when enforcement chain is broken."""
    
    def __init__(self, stage: str, reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(
            f"HARD FAIL at stage '{stage}': {reason}. "
            f"Enforcement chain broken. Execution denied."
        )


class ToolDeniedError(EnforcementError):
    """Raised when a tool is denied by the tool matrix."""
    
    def __init__(self, tool: str, mode: str, lane: str):
        self.tool = tool
        self.mode = mode
        self.lane = lane
        super().__init__(
            f"HARD FAIL: Tool '{tool}' denied for MODE={mode}, LANE={lane}. "
            f"Tool stripped from context."
        )


class PathDeniedError(EnforcementError):
    """Raised when a path is denied by lane restrictions."""
    
    def __init__(self, path: str, lane: str):
        self.path = path
        self.lane = lane
        super().__init__(
            f"HARD FAIL: Path '{path}' denied for LANE={lane}. "
            f"Operation rejected."
        )


class EchoHandshakeError(EnforcementError):
    """Raised when echo-back handshake fails."""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            f"HARD FAIL: Echo-back handshake failed. {reason}. "
            f"Session invalid."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EnforcementContext:
    """
    Enforcement context — carries validated identity through execution.
    
    Created by the enforcer after successful validation.
    Required for all subsequent operations.
    """
    
    gid: str
    role: str
    mode: str
    execution_lane: str
    agent_identity: AgentIdentity
    mode_declaration: ModeDeclaration
    tool_matrix_result: ToolMatrixResult
    pac_id: Optional[str] = None
    wrap_id: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    echo_handshake: str = ""
    
    def __post_init__(self):
        # Generate echo handshake line
        self.echo_handshake = format_echo_handshake(self.gid, self.mode, self.execution_lane)
    
    @property
    def allowed_tools(self) -> List[str]:
        """List of allowed tool names."""
        return [t.value for t in self.tool_matrix_result.allowed_tools]
    
    @property
    def denied_tools(self) -> List[str]:
        """List of denied tool names."""
        return [t.value for t in self.tool_matrix_result.denied_tools]
    
    @property
    def path_prefixes(self) -> Optional[List[str]]:
        """Allowed path prefixes, or None if unrestricted."""
        return self.tool_matrix_result.path_prefixes
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed in this context."""
        return is_tool_permitted(tool_name, self.mode, self.execution_lane)
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed in this context."""
        return is_path_permitted(path, self.execution_lane)
    
    def assert_tool_allowed(self, tool_name: str) -> None:
        """Assert a tool is allowed. HARD FAIL if not."""
        if not self.is_tool_allowed(tool_name):
            raise ToolDeniedError(tool_name, self.mode, self.execution_lane)
    
    def assert_path_allowed(self, path: str) -> None:
        """Assert a path is allowed. HARD FAIL if not."""
        if not self.is_path_allowed(path):
            raise PathDeniedError(path, self.execution_lane)


# ═══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class Enforcer:
    """
    Central enforcement orchestrator.
    
    Validates identity, mode, tools, and paths.
    Creates enforcement context for execution.
    """
    
    def __init__(self):
        self.registry = GIDRegistry()
        self.tool_matrix = ToolMatrix()
        self._current_context: Optional[EnforcementContext] = None
    
    @property
    def current_context(self) -> Optional[EnforcementContext]:
        """Get current enforcement context, if any."""
        return self._current_context
    
    def enforce_identity(
        self,
        gid: str,
        role: str,
        mode: str,
        execution_lane: str,
        pac_id: Optional[str] = None,
        wrap_id: Optional[str] = None,
    ) -> EnforcementContext:
        """
        Full identity enforcement chain.
        
        HARD FAIL on any validation error.
        Returns EnforcementContext on success.
        """
        try:
            # Stage 1: GID validation
            agent_identity = validate_full_identity(gid, mode, execution_lane)
            
        except GIDEnforcementError as e:
            raise EnforcementChainError("GID_VALIDATION", str(e))
        
        try:
            # Stage 2: Mode declaration validation
            mode_declaration = create_mode_declaration(
                gid=gid,
                role=role,
                mode=mode,
                execution_lane=execution_lane,
                pac_id=pac_id,
                wrap_id=wrap_id,
            )
            
        except ModeSchemaError as e:
            raise EnforcementChainError("MODE_SCHEMA", str(e))
        
        # Stage 3: Tool matrix evaluation
        tool_result = self.tool_matrix.evaluate(mode, execution_lane)
        
        # Create and store context
        context = EnforcementContext(
            gid=gid,
            role=role,
            mode=mode,
            execution_lane=execution_lane,
            agent_identity=agent_identity,
            mode_declaration=mode_declaration,
            tool_matrix_result=tool_result,
            pac_id=pac_id,
            wrap_id=wrap_id,
        )
        
        self._current_context = context
        return context
    
    def enforce_from_pac(self, pac_text: str) -> EnforcementContext:
        """
        Extract identity from PAC and enforce.
        
        HARD FAIL on any validation error.
        """
        try:
            mode_declaration = extract_mode_from_pac(pac_text)
        except ModeSchemaError as e:
            raise EnforcementChainError("PAC_EXTRACTION", str(e))
        
        return self.enforce_identity(
            gid=mode_declaration.gid,
            role=mode_declaration.role,
            mode=mode_declaration.mode,
            execution_lane=mode_declaration.execution_lane,
            pac_id=mode_declaration.pac_id,
            wrap_id=mode_declaration.wrap_id,
        )
    
    def validate_echo_handshake(
        self,
        response_text: str,
        expected_gid: str,
        expected_mode: str,
    ) -> bool:
        """
        Validate echo-back handshake in response.
        
        HARD FAIL if handshake missing or invalid.
        """
        is_valid, error_msg = validate_echo_handshake(
            response_text,
            expected_gid,
            expected_mode,
        )
        
        if not is_valid:
            raise EchoHandshakeError(error_msg or "Invalid handshake")
        
        return True
    
    def validate_wrap(self, wrap_text: str) -> ValidatedWRAP:
        """
        Validate WRAP document.
        
        HARD FAIL on invalid WRAP.
        """
        try:
            return validate_wrap(wrap_text)
        except WRAPValidationError as e:
            raise EnforcementChainError("WRAP_VALIDATION", str(e))
    
    def check_ber_eligibility(
        self,
        wrap_text: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if WRAP is BER-eligible.
        
        Returns (eligible, reason_if_not).
        """
        return check_ber_eligibility(wrap_text)
    
    def strip_tools(self, available_tools: List[str]) -> List[str]:
        """
        Strip disallowed tools based on current context.
        
        Requires active enforcement context.
        SILENT — no warnings for stripped tools.
        """
        if self._current_context is None:
            # No context → deny all (FAIL-CLOSED)
            return []
        
        return strip_disallowed_tools(
            available_tools,
            self._current_context.mode,
            self._current_context.execution_lane,
        )
    
    def assert_tool(self, tool_name: str) -> None:
        """
        Assert tool is allowed in current context.
        
        HARD FAIL if denied.
        """
        if self._current_context is None:
            raise EnforcementChainError(
                "TOOL_CHECK",
                "No enforcement context. Must call enforce_identity first."
            )
        
        self._current_context.assert_tool_allowed(tool_name)
    
    def assert_path(self, path: str) -> None:
        """
        Assert path is allowed in current context.
        
        HARD FAIL if denied.
        """
        if self._current_context is None:
            raise EnforcementChainError(
                "PATH_CHECK",
                "No enforcement context. Must call enforce_identity first."
            )
        
        self._current_context.assert_path_allowed(path)
    
    def clear_context(self) -> None:
        """Clear current enforcement context."""
        self._current_context = None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_enforcer: Optional[Enforcer] = None


def get_enforcer() -> Enforcer:
    """Get the singleton enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = Enforcer()
    return _enforcer


def enforce(
    gid: str,
    role: str,
    mode: str,
    execution_lane: str,
    pac_id: Optional[str] = None,
) -> EnforcementContext:
    """
    Quick enforcement function.
    
    HARD FAIL on any validation error.
    """
    return get_enforcer().enforce_identity(
        gid=gid,
        role=role,
        mode=mode,
        execution_lane=execution_lane,
        pac_id=pac_id,
    )


def get_current_context() -> Optional[EnforcementContext]:
    """Get current enforcement context."""
    return get_enforcer().current_context


def require_context() -> EnforcementContext:
    """
    Require enforcement context.
    
    HARD FAIL if no context.
    """
    ctx = get_current_context()
    if ctx is None:
        raise EnforcementChainError(
            "CONTEXT_REQUIRED",
            "No enforcement context. Identity enforcement required."
        )
    return ctx


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATOR — FOR ENFORCED FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def requires_enforcement(func):
    """
    Decorator requiring enforcement context.
    
    HARD FAIL if no context when function called.
    """
    def wrapper(*args, **kwargs):
        require_context()
        return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def requires_mode(*allowed_modes: str):
    """
    Decorator requiring specific modes.
    
    HARD FAIL if current mode not in allowed list.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            ctx = require_context()
            if ctx.mode not in allowed_modes:
                raise EnforcementChainError(
                    "MODE_REQUIRED",
                    f"Function requires MODE in {allowed_modes}, got {ctx.mode}"
                )
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


def requires_lane(*allowed_lanes: str):
    """
    Decorator requiring specific lanes.
    
    HARD FAIL if current lane not in allowed list.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            ctx = require_context()
            if ctx.execution_lane not in allowed_lanes and "ALL" not in allowed_lanes:
                raise EnforcementChainError(
                    "LANE_REQUIRED",
                    f"Function requires LANE in {allowed_lanes}, got {ctx.execution_lane}"
                )
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# BER/WRAP AUTHORITY ENFORCEMENT — PAC-017
# ═══════════════════════════════════════════════════════════════════════════════

def enforce_ber_authority(issuer_id: str) -> bool:
    """
    Enforce that only ORCHESTRATION_ENGINE may issue BER.
    
    HARD FAIL if unauthorized.
    
    Args:
        issuer_id: The identity ID attempting to issue BER
        
    Returns:
        True if authorized
        
    Raises:
        BERAuthorityError: If unauthorized
    """
    if issuer_id == ORCHESTRATION_ENGINE.identity_id:
        return True
    
    # Check if it's a system identity
    identity = SystemIdentityRegistry.get(issuer_id)
    if identity is not None:
        raise BERAuthorityError(issuer_id, identity.identity_type)
    
    # Not a system identity — could be an agent GID trying to issue BER
    raise BERAuthorityError(issuer_id, SystemIdentityType.AGENT)


def enforce_wrap_authority(issuer_gid: str) -> bool:
    """
    Enforce that only AGENT may issue WRAP.
    
    HARD FAIL if unauthorized.
    
    Args:
        issuer_gid: The GID attempting to issue WRAP
        
    Returns:
        True if authorized
        
    Raises:
        WRAPAuthorityError: If unauthorized
    """
    # Check if it's a system identity
    identity = SystemIdentityRegistry.get(issuer_gid)
    if identity is not None:
        raise WRAPAuthorityError(issuer_gid, identity.identity_type)
    
    # If it's a GID pattern, it's an agent — allowed to issue WRAP
    if issuer_gid.startswith("GID-"):
        return True
    
    # Unknown identity type
    raise WRAPAuthorityError(issuer_gid, SystemIdentityType.DRAFTING_SURFACE)


def enforce_no_self_approval(
    approver_gid: str,
    wrap_author_gid: str,
) -> bool:
    """
    Enforce that an agent cannot approve their own work.
    
    HARD FAIL if self-approval attempted.
    
    Args:
        approver_gid: The GID of the entity attempting to approve
        wrap_author_gid: The GID of the WRAP author
        
    Returns:
        True if not self-approval
        
    Raises:
        SelfApprovalError: If self-approval attempted
    """
    if approver_gid == wrap_author_gid:
        raise SelfApprovalError(approver_gid)
    return True


def enforce_no_persona_authority(claimed_persona: str) -> None:
    """
    Reject any persona-based authority claim.
    
    ALWAYS raises — persona authority has zero weight.
    
    Args:
        claimed_persona: The claimed persona string
        
    Raises:
        PersonaAuthorityError: Always
    """
    raise PersonaAuthorityError(claimed_persona)


def enforce_drafting_surface_cannot_govern(issuer_id: str) -> bool:
    """
    Enforce that drafting surface cannot emit WRAP or BER.
    
    HARD FAIL if drafting surface attempts governance action.
    
    Args:
        issuer_id: The identity ID attempting governance action
        
    Returns:
        True if not drafting surface
        
    Raises:
        EnforcementChainError: If drafting surface attempts governance
    """
    identity = SystemIdentityRegistry.get(issuer_id)
    if identity is not None and identity.identity_type == SystemIdentityType.DRAFTING_SURFACE:
        raise EnforcementChainError(
            "DRAFTING_SURFACE_GOVERNANCE",
            "HARD FAIL: Drafting surface may never emit WRAP or BER. "
            "Governance authority is code-enforced, not conversational."
        )
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Core classes
    "Enforcer",
    "EnforcementContext",
    
    # Exceptions
    "EnforcementError",
    "EnforcementChainError",
    "ToolDeniedError",
    "PathDeniedError",
    "EchoHandshakeError",
    
    # PAC-017: System Identity Exceptions
    "SystemIdentityError",
    "BERAuthorityError",
    "WRAPAuthorityError",
    "PersonaAuthorityError",
    "SelfApprovalError",
    
    # Functions
    "get_enforcer",
    "enforce",
    "get_current_context",
    "require_context",
    
    # PAC-017: Authority Enforcement Functions
    "enforce_ber_authority",
    "enforce_wrap_authority",
    "enforce_no_self_approval",
    "enforce_no_persona_authority",
    "enforce_drafting_surface_cannot_govern",
    
    # Decorators
    "requires_enforcement",
    "requires_mode",
    "requires_lane",
    
    # Re-exports from sub-modules
    "GID",
    "Mode",
    "AgentIdentity",
    "ModeDeclaration",
    "ValidatedWRAP",
    "ToolCategory",
    "ToolMatrixResult",
    
    # PAC-017: System Identity Re-exports
    "ORCHESTRATION_ENGINE",
    "EXECUTION_ENGINE",
    "DRAFTING_SURFACE",
    "SystemIdentity",
    "SystemIdentityType",
    "SystemIdentityRegistry",
    "is_system_component",
    "is_ber_authorized",
]
