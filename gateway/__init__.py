"""Gateway core deterministic middleware package.

Includes ALEX middleware for ACM enforcement (GID-08).
Includes Canonical Decision Envelope (CDE) v1 for stable response contracts.
Includes Tool Binding Enforcement (TBE) v1 for envelope-based execution (PAC-GATEWAY-02).
"""

from gateway.alex_middleware import (
    ALEXMiddleware,
    ALEXMiddlewareError,
    GovernanceAuditLogger,
    IntentDeniedError,
    MiddlewareConfig,
    get_alex_middleware,
    guard_action,
    guard_action_envelope,
    initialize_alex,
)
from gateway.decision_envelope import (
    CDE_VERSION,
    EnvelopeError,
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
from gateway.tool_executor import DenialReasonCode, ToolExecutionDenied, ToolExecutionResult, ToolExecutor, can_execute_tool, execute_tool

__all__ = [
    # ALEX Middleware
    "ALEXMiddleware",
    "ALEXMiddlewareError",
    "GovernanceAuditLogger",
    "IntentDeniedError",
    "MiddlewareConfig",
    "get_alex_middleware",
    "guard_action",
    "guard_action_envelope",
    "initialize_alex",
    # CDE v1 (PAC-GATEWAY-01)
    "CDE_VERSION",
    "GatewayDecision",
    "GatewayDecisionEnvelope",
    "ReasonCode",
    "EnvelopeError",
    "EnvelopeVersionError",
    "EnvelopeMalformedError",
    "create_envelope_from_result",
    "create_allow_envelope",
    "create_deny_envelope",
    "map_denial_reason",
    "validate_envelope",
    # Tool Binding Enforcement (PAC-GATEWAY-02)
    "DenialReasonCode",
    "ToolExecutionDenied",
    "ToolExecutionResult",
    "ToolExecutor",
    "can_execute_tool",
    "execute_tool",
]
