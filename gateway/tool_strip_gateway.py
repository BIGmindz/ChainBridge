"""
ChainBridge Tool-Strip Gateway — Pre-Execution Tool Enforcement
════════════════════════════════════════════════════════════════════════════════

Gateway-level tool stripping enforcement.
Tools are REMOVED from context BEFORE execution, not after.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-TOOL-STRIP-ENFORCEMENT-014
Effective Date: 2025-12-26

ENFORCEMENT PHILOSOPHY:
- Tools are stripped BEFORE agent sees them
- No warnings, no conversational forgiveness
- FAIL-CLOSED: if uncertain, deny
- Non-bypassable: no fallback paths

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, TypeVar

from core.governance.enforcement import (
    EnforcementChainError,
    EnforcementContext,
    ToolDeniedError,
    get_enforcer,
    require_context,
)
from core.governance.gid_registry import (
    GID,
    AgentIdentity,
    GIDEnforcementError,
    validate_agent_gid,
)
from core.governance.tool_matrix import (
    ToolCategory,
    ToolMatrixResult,
    evaluate_tools,
    get_tool_matrix,
    is_tool_permitted,
    strip_disallowed_tools,
)

logger = logging.getLogger("gateway.tool_strip_gateway")


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS — HARD FAIL
# ═══════════════════════════════════════════════════════════════════════════════

class ToolStripError(Exception):
    """Base exception for tool strip gateway failures."""
    pass


class ToolStripDenialError(ToolStripError):
    """Raised when a tool is denied by the strip gateway. HARD FAIL."""
    
    def __init__(
        self,
        tool_name: str,
        mode: str,
        lane: str,
        gid: Optional[str] = None,
        reason: str = "Tool not permitted for MODE/LANE",
    ):
        self.tool_name = tool_name
        self.mode = mode
        self.lane = lane
        self.gid = gid
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        super().__init__(
            f"HARD FAIL: Tool '{tool_name}' denied. "
            f"MODE={mode}, LANE={lane}, GID={gid or 'UNKNOWN'}. "
            f"Reason: {reason}. "
            f"No fallback permitted."
        )


class NoContextError(ToolStripError):
    """Raised when no enforcement context exists. HARD FAIL."""
    
    def __init__(self):
        super().__init__(
            "HARD FAIL: No enforcement context. "
            "Must establish identity before tool access. "
            "Execution denied."
        )


class ToolCallInterceptError(ToolStripError):
    """Raised when a tool call is intercepted and denied. HARD FAIL."""
    
    def __init__(self, tool_name: str, interceptor_name: str, reason: str):
        self.tool_name = tool_name
        self.interceptor_name = interceptor_name
        self.reason = reason
        
        super().__init__(
            f"HARD FAIL: Tool '{tool_name}' intercepted by '{interceptor_name}'. "
            f"Reason: {reason}. "
            f"Execution blocked."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL STRIP RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ToolStripResult:
    """Result of tool stripping operation."""
    
    original_tools: FrozenSet[str]
    allowed_tools: FrozenSet[str]
    stripped_tools: FrozenSet[str]
    mode: str
    lane: str
    gid: Optional[str]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    @property
    def tools_removed(self) -> int:
        """Number of tools removed."""
        return len(self.stripped_tools)
    
    @property
    def is_restricted(self) -> bool:
        """True if any tools were stripped."""
        return self.tools_removed > 0
    
    def was_stripped(self, tool_name: str) -> bool:
        """Check if a specific tool was stripped."""
        return tool_name in self.stripped_tools


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL STRIP GATEWAY
# ═══════════════════════════════════════════════════════════════════════════════

class ToolStripGateway:
    """
    Gateway-level tool stripping enforcer.
    
    Strips tools BEFORE they reach agent execution.
    Non-bypassable — all tool access must go through this gateway.
    """
    
    def __init__(self):
        self._strip_log: List[ToolStripResult] = []
        self._intercept_count: int = 0
        self._allow_count: int = 0
    
    def strip_tools_for_context(
        self,
        available_tools: List[str],
        context: EnforcementContext,
    ) -> ToolStripResult:
        """
        Strip tools based on enforcement context.
        
        Tools not in allowed set are REMOVED (not warned).
        """
        original = frozenset(available_tools)
        
        # Get allowed tools via strip function
        allowed_list = strip_disallowed_tools(
            available_tools,
            context.mode,
            context.execution_lane,
        )
        allowed = frozenset(allowed_list)
        stripped = original - allowed
        
        result = ToolStripResult(
            original_tools=original,
            allowed_tools=allowed,
            stripped_tools=stripped,
            mode=context.mode,
            lane=context.execution_lane,
            gid=context.gid,
        )
        
        self._strip_log.append(result)
        
        if result.is_restricted:
            logger.debug(
                f"Tool strip: {len(stripped)} tools removed for "
                f"GID={context.gid}, MODE={context.mode}, LANE={context.execution_lane}"
            )
        
        return result
    
    def strip_tools(
        self,
        available_tools: List[str],
        mode: str,
        lane: str,
        gid: Optional[str] = None,
    ) -> ToolStripResult:
        """
        Strip tools based on MODE and LANE.
        
        Use when context is not yet established.
        """
        original = frozenset(available_tools)
        
        allowed_list = strip_disallowed_tools(available_tools, mode, lane)
        allowed = frozenset(allowed_list)
        stripped = original - allowed
        
        result = ToolStripResult(
            original_tools=original,
            allowed_tools=allowed,
            stripped_tools=stripped,
            mode=mode,
            lane=lane,
            gid=gid,
        )
        
        self._strip_log.append(result)
        return result
    
    def intercept_tool_call(
        self,
        tool_name: str,
        mode: str,
        lane: str,
        gid: Optional[str] = None,
    ) -> bool:
        """
        Intercept and validate a tool call BEFORE execution.
        
        Returns True if allowed.
        HARD FAIL (exception) if denied.
        """
        if not is_tool_permitted(tool_name, mode, lane):
            self._intercept_count += 1
            raise ToolStripDenialError(
                tool_name=tool_name,
                mode=mode,
                lane=lane,
                gid=gid,
            )
        
        self._allow_count += 1
        return True
    
    def intercept_with_context(
        self,
        tool_name: str,
        context: EnforcementContext,
    ) -> bool:
        """
        Intercept tool call using enforcement context.
        
        HARD FAIL if denied.
        """
        return self.intercept_tool_call(
            tool_name,
            context.mode,
            context.execution_lane,
            context.gid,
        )
    
    def get_allowed_tools(
        self,
        available_tools: List[str],
        mode: str,
        lane: str,
    ) -> List[str]:
        """
        Get only allowed tools. SILENT operation.
        
        Equivalent to strip_tools but returns just the list.
        """
        return strip_disallowed_tools(available_tools, mode, lane)
    
    @property
    def intercept_stats(self) -> Dict[str, int]:
        """Get interception statistics."""
        return {
            "intercepted_and_denied": self._intercept_count,
            "allowed": self._allow_count,
            "total_checks": self._intercept_count + self._allow_count,
        }
    
    @property
    def strip_history(self) -> List[ToolStripResult]:
        """Get history of strip operations."""
        return list(self._strip_log)
    
    def clear_history(self) -> None:
        """Clear strip history."""
        self._strip_log.clear()
        self._intercept_count = 0
        self._allow_count = 0


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL CALL INTERCEPTOR — DECORATOR-BASED ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

F = TypeVar('F', bound=Callable[..., Any])


def tool_strip_required(tool_name: str) -> Callable[[F], F]:
    """
    Decorator that enforces tool stripping before execution.
    
    HARD FAIL if tool not permitted.
    """
    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = require_context()
            
            gateway = get_tool_strip_gateway()
            gateway.intercept_with_context(tool_name, ctx)
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper  # type: ignore
    
    return decorator


def enforce_tool_access(func: F) -> F:
    """
    Decorator that extracts tool name from function and enforces access.
    
    The function name is used as the tool name.
    HARD FAIL if tool not permitted.
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = require_context()
        
        gateway = get_tool_strip_gateway()
        gateway.intercept_with_context(func.__name__, ctx)
        
        return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-EXECUTION FILTER — FOR TOOL LISTS
# ═══════════════════════════════════════════════════════════════════════════════

def filter_tools_before_execution(
    tools: List[str],
    gid: str,
    mode: str,
    lane: str,
) -> List[str]:
    """
    Filter tools BEFORE they are presented to the agent.
    
    This is the CANONICAL entry point for tool filtering.
    Called before agent execution to remove unavailable tools.
    
    SILENT — no warnings for removed tools.
    """
    # Validate identity first
    try:
        validate_agent_gid(gid)
    except GIDEnforcementError:
        # Unknown GID → no tools (FAIL-CLOSED)
        logger.warning(f"Unknown GID '{gid}' - denying all tools")
        return []
    
    gateway = get_tool_strip_gateway()
    result = gateway.strip_tools(tools, mode, lane, gid)
    
    return list(result.allowed_tools)


def assert_tool_before_execution(
    tool_name: str,
    gid: str,
    mode: str,
    lane: str,
) -> None:
    """
    Assert a tool is allowed BEFORE execution.
    
    HARD FAIL if denied. No return value needed.
    """
    gateway = get_tool_strip_gateway()
    gateway.intercept_tool_call(tool_name, mode, lane, gid)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_gateway: Optional[ToolStripGateway] = None


def get_tool_strip_gateway() -> ToolStripGateway:
    """Get the singleton tool strip gateway."""
    global _gateway
    if _gateway is None:
        _gateway = ToolStripGateway()
    return _gateway


def reset_tool_strip_gateway() -> None:
    """Reset the singleton (for testing)."""
    global _gateway
    _gateway = None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Gateway class
    "ToolStripGateway",
    
    # Result class
    "ToolStripResult",
    
    # Exceptions
    "ToolStripError",
    "ToolStripDenialError",
    "NoContextError",
    "ToolCallInterceptError",
    
    # Decorators
    "tool_strip_required",
    "enforce_tool_access",
    
    # Functions
    "get_tool_strip_gateway",
    "reset_tool_strip_gateway",
    "filter_tools_before_execution",
    "assert_tool_before_execution",
]
