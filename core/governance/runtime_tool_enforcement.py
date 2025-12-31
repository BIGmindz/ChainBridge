"""
ChainBridge Runtime Tool Enforcement — FAIL-CLOSED Execution Layer
════════════════════════════════════════════════════════════════════════════════

Runtime enforcement layer that ensures tool stripping is non-bypassable.
Integrates with EnforcementContext and ToolStripGateway.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-TOOL-STRIP-ENFORCEMENT-014
Effective Date: 2025-12-26

ENFORCEMENT INVARIANTS:
- INV-TOOL-001: No tool executes without context
- INV-TOOL-002: Stripped tools are invisible to agent
- INV-TOOL-003: Unknown tools are denied (FAIL-CLOSED)
- INV-TOOL-004: Path restrictions are enforced per lane
- INV-TOOL-005: All denials are logged for audit

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, List, Optional, Set, TypeVar

from core.governance.enforcement import (
    EnforcementChainError,
    EnforcementContext,
    PathDeniedError,
    ToolDeniedError,
    get_enforcer,
    require_context,
)
from core.governance.tool_matrix import (
    ToolCategory,
    evaluate_tools,
    is_path_permitted,
    is_tool_permitted,
)
from gateway.tool_strip_gateway import (
    ToolStripDenialError,
    ToolStripGateway,
    ToolStripResult,
    get_tool_strip_gateway,
)

logger = logging.getLogger("runtime.tool_enforcement")


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME ENFORCEMENT EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class RuntimeEnforcementError(Exception):
    """Base exception for runtime enforcement failures."""
    pass


class ToolExecutionDenied(RuntimeEnforcementError):
    """Raised when tool execution is denied at runtime. HARD FAIL."""
    
    def __init__(
        self,
        tool_name: str,
        reason: str,
        context: Optional[EnforcementContext] = None,
    ):
        self.tool_name = tool_name
        self.reason = reason
        self.context = context
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        ctx_info = ""
        if context:
            ctx_info = f" GID={context.gid}, MODE={context.mode}, LANE={context.execution_lane}"
        
        super().__init__(
            f"RUNTIME DENIAL: Tool '{tool_name}' blocked.{ctx_info} "
            f"Reason: {reason}"
        )


class PathExecutionDenied(RuntimeEnforcementError):
    """Raised when path access is denied at runtime. HARD FAIL."""
    
    def __init__(
        self,
        path: str,
        lane: str,
        reason: str = "Path not permitted for lane",
    ):
        self.path = path
        self.lane = lane
        self.reason = reason
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        super().__init__(
            f"RUNTIME DENIAL: Path '{path}' blocked for LANE={lane}. "
            f"Reason: {reason}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolExecutionRecord:
    """Record of a tool execution attempt."""
    
    tool_name: str
    allowed: bool
    reason: Optional[str]
    mode: str
    lane: str
    gid: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RuntimeToolRegistry:
    """
    Runtime registry for tracking tool access patterns.
    
    Used for audit and debugging of tool enforcement.
    """
    
    def __init__(self):
        self._execution_log: List[ToolExecutionRecord] = []
        self._denial_counts: Dict[str, int] = {}
        self._allow_counts: Dict[str, int] = {}
    
    def record_attempt(
        self,
        tool_name: str,
        allowed: bool,
        mode: str,
        lane: str,
        gid: str,
        reason: Optional[str] = None,
    ) -> None:
        """Record a tool execution attempt."""
        record = ToolExecutionRecord(
            tool_name=tool_name,
            allowed=allowed,
            reason=reason,
            mode=mode,
            lane=lane,
            gid=gid,
        )
        self._execution_log.append(record)
        
        if allowed:
            self._allow_counts[tool_name] = self._allow_counts.get(tool_name, 0) + 1
        else:
            self._denial_counts[tool_name] = self._denial_counts.get(tool_name, 0) + 1
    
    def get_denial_report(self) -> Dict[str, Any]:
        """Get a summary of denials for audit."""
        return {
            "total_denials": sum(self._denial_counts.values()),
            "denial_by_tool": dict(self._denial_counts),
            "total_allows": sum(self._allow_counts.values()),
            "allow_by_tool": dict(self._allow_counts),
        }
    
    def get_recent_denials(self, count: int = 10) -> List[ToolExecutionRecord]:
        """Get recent denial records."""
        denials = [r for r in self._execution_log if not r.allowed]
        return denials[-count:]
    
    def clear(self) -> None:
        """Clear all records."""
        self._execution_log.clear()
        self._denial_counts.clear()
        self._allow_counts.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class RuntimeToolEnforcer:
    """
    Runtime tool enforcer — FAIL-CLOSED execution.
    
    All tool calls MUST go through this enforcer.
    Non-bypassable at the runtime level.
    """
    
    def __init__(self):
        self._registry = RuntimeToolRegistry()
        self._gateway = get_tool_strip_gateway()
        self._active_context: Optional[EnforcementContext] = None
    
    def bind_context(self, context: EnforcementContext) -> None:
        """Bind an enforcement context for this runtime session."""
        self._active_context = context
        logger.debug(
            f"Runtime enforcer bound to context: "
            f"GID={context.gid}, MODE={context.mode}, LANE={context.execution_lane}"
        )
    
    def unbind_context(self) -> None:
        """Unbind the current context."""
        self._active_context = None
    
    def get_context(self) -> EnforcementContext:
        """
        Get current context. HARD FAIL if none.
        """
        if self._active_context is None:
            # Fall back to global enforcer context
            ctx = require_context()
            return ctx
        return self._active_context
    
    def filter_available_tools(self, tools: List[str]) -> List[str]:
        """
        Filter tools to only those allowed.
        
        SILENT operation — no errors for stripped tools.
        """
        ctx = self.get_context()
        result = self._gateway.strip_tools_for_context(tools, ctx)
        return list(result.allowed_tools)
    
    def assert_tool_allowed(self, tool_name: str) -> None:
        """
        Assert a tool is allowed. HARD FAIL if not.
        
        Call this BEFORE executing any tool.
        """
        ctx = self.get_context()
        
        allowed = is_tool_permitted(tool_name, ctx.mode, ctx.execution_lane)
        
        self._registry.record_attempt(
            tool_name=tool_name,
            allowed=allowed,
            mode=ctx.mode,
            lane=ctx.execution_lane,
            gid=ctx.gid,
            reason=None if allowed else "Not permitted for MODE/LANE",
        )
        
        if not allowed:
            raise ToolExecutionDenied(
                tool_name=tool_name,
                reason="Not permitted for MODE/LANE",
                context=ctx,
            )
    
    def assert_path_allowed(self, path: str) -> None:
        """
        Assert a path is allowed. HARD FAIL if not.
        
        Call this BEFORE any file operation.
        """
        ctx = self.get_context()
        
        if not is_path_permitted(path, ctx.execution_lane):
            raise PathExecutionDenied(
                path=path,
                lane=ctx.execution_lane,
            )
    
    def execute_tool(
        self,
        tool_name: str,
        executor: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a tool with enforcement.
        
        HARD FAIL if tool not permitted.
        """
        self.assert_tool_allowed(tool_name)
        
        # Check for path arguments
        for key in ['path', 'filePath', 'file_path', 'dirPath', 'dir_path']:
            if key in kwargs:
                self.assert_path_allowed(kwargs[key])
        
        # Execute
        return executor(*args, **kwargs)
    
    def get_audit_report(self) -> Dict[str, Any]:
        """Get audit report for this runtime session."""
        ctx = self._active_context
        return {
            "context": {
                "gid": ctx.gid if ctx else None,
                "mode": ctx.mode if ctx else None,
                "lane": ctx.execution_lane if ctx else None,
            },
            "enforcement": self._registry.get_denial_report(),
            "gateway_stats": self._gateway.intercept_stats,
        }
    
    @property
    def registry(self) -> RuntimeToolRegistry:
        """Access the tool registry."""
        return self._registry


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGERS
# ═══════════════════════════════════════════════════════════════════════════════

@contextmanager
def enforced_runtime(context: EnforcementContext) -> Generator[RuntimeToolEnforcer, None, None]:
    """
    Context manager for enforced runtime execution.
    
    Usage:
        with enforced_runtime(ctx) as enforcer:
            enforcer.assert_tool_allowed("read_file")
            # ... execute tool
    """
    enforcer = get_runtime_enforcer()
    enforcer.bind_context(context)
    try:
        yield enforcer
    finally:
        enforcer.unbind_context()


@contextmanager
def tool_enforcement_session(
    gid: str,
    mode: str,
    lane: str,
) -> Generator[RuntimeToolEnforcer, None, None]:
    """
    Quick context manager for tool enforcement.
    
    Creates enforcement context automatically.
    Looks up role from GID registry.
    """
    from core.governance.enforcement import enforce
    from core.governance.gid_registry import validate_agent_gid
    
    # Look up role from registry
    agent = validate_agent_gid(gid)
    
    ctx = enforce(gid=gid, role=agent.role, mode=mode, execution_lane=lane)
    
    enforcer = get_runtime_enforcer()
    enforcer.bind_context(ctx)
    try:
        yield enforcer
    finally:
        enforcer.unbind_context()


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

F = TypeVar('F', bound=Callable[..., Any])


def runtime_tool_check(tool_name: str) -> Callable[[F], F]:
    """
    Decorator that enforces tool check at runtime.
    
    HARD FAIL if tool not permitted.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            enforcer = get_runtime_enforcer()
            enforcer.assert_tool_allowed(tool_name)
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def runtime_path_check(path_param: str = "path") -> Callable[[F], F]:
    """
    Decorator that enforces path check at runtime.
    
    HARD FAIL if path not permitted.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            enforcer = get_runtime_enforcer()
            
            # Get path from kwargs or args
            path = kwargs.get(path_param)
            if path is None and len(args) > 0:
                path = args[0]  # Assume first arg is path
            
            if path:
                enforcer.assert_path_allowed(str(path))
            
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_runtime_enforcer: Optional[RuntimeToolEnforcer] = None


def get_runtime_enforcer() -> RuntimeToolEnforcer:
    """Get the singleton runtime enforcer."""
    global _runtime_enforcer
    if _runtime_enforcer is None:
        _runtime_enforcer = RuntimeToolEnforcer()
    return _runtime_enforcer


def reset_runtime_enforcer() -> None:
    """Reset the singleton (for testing)."""
    global _runtime_enforcer
    _runtime_enforcer = None


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Core classes
    "RuntimeToolEnforcer",
    "RuntimeToolRegistry",
    "ToolExecutionRecord",
    
    # Exceptions
    "RuntimeEnforcementError",
    "ToolExecutionDenied",
    "PathExecutionDenied",
    
    # Context managers
    "enforced_runtime",
    "tool_enforcement_session",
    
    # Decorators
    "runtime_tool_check",
    "runtime_path_check",
    
    # Functions
    "get_runtime_enforcer",
    "reset_runtime_enforcer",
]
