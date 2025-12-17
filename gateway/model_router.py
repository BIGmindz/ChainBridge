"""Model routing abstraction for AI cost control.

The router assigns incoming tasks to predefined model tiers before any
Gateway execution occurs. Tier selection is deterministic and does not
allow user-provided model names, preventing LLM self-selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

_DEFAULT_TIER_MAP = {
    "tier1": "gpt-4o",
    "tier2": "gpt-4o-mini",
}

# USD cost per 1K tokens (approximate; can be adjusted via constructor).
_DEFAULT_PRICING = {
    "gpt-4o": 5.00,
    "gpt-4o-mini": 0.15,
}


class ModelTier(str, Enum):
    """Supported routing tiers."""

    TIER1 = "tier1"  # Complex reasoning / safety-critical
    TIER2 = "tier2"  # Lightweight extraction/classification


@dataclass
class TaskProfile:
    """Describes the task so the router can pick an appropriate model."""

    intent: str
    operation: str = "generic"
    requires_reasoning: bool = False
    preferred_tier: Optional[ModelTier] = None
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: Optional[Dict[str, str]] = None


@dataclass
class RouteDecision:
    """Outcome of routing including cost telemetry."""

    model: str
    tier: ModelTier
    reason: str
    estimated_cost: float
    tokens_in: int
    tokens_out: int
    timestamp: datetime


class ModelRouter:
    """Deterministic model router with tiered pricing awareness."""

    def __init__(
        self,
        tier_map: Optional[Dict[ModelTier | str, str]] = None,
        pricing_per_1k_tokens: Optional[Dict[str, float]] = None,
    ) -> None:
        # Normalize tier map while honoring defaults.
        configured_map = tier_map or {}
        self.tier_map: Dict[ModelTier, str] = {
            ModelTier.TIER1: configured_map.get(ModelTier.TIER1, configured_map.get("tier1", _DEFAULT_TIER_MAP["tier1"])),
            ModelTier.TIER2: configured_map.get(ModelTier.TIER2, configured_map.get("tier2", _DEFAULT_TIER_MAP["tier2"])),
        }

        pricing = pricing_per_1k_tokens or {}
        self.pricing_per_1k_tokens: Dict[str, float] = {**_DEFAULT_PRICING, **pricing}

    def route(self, profile: TaskProfile) -> RouteDecision:
        """Pick a model for the given task and estimate its cost."""

        tier = self._determine_tier(profile)
        model = self.tier_map[tier]
        cost = self._estimate_cost(model, profile.input_tokens, profile.output_tokens)

        return RouteDecision(
            model=model,
            tier=tier,
            reason=self._build_reason(profile, tier),
            estimated_cost=cost,
            tokens_in=profile.input_tokens,
            tokens_out=profile.output_tokens,
            timestamp=datetime.now(timezone.utc),
        )

    def _determine_tier(self, profile: TaskProfile) -> ModelTier:
        """Select tier based on task type and safety needs."""

        if profile.preferred_tier:
            return ModelTier(profile.preferred_tier)

        intent_lower = (profile.intent or "").lower()
        operation_lower = (profile.operation or "").lower()

        # Risk, control, or reasoning-heavy work goes to tier1.
        if profile.requires_reasoning or intent_lower in {"risk", "control"}:
            return ModelTier.TIER1

        # Simple extraction or classification defaults to tier2.
        if operation_lower in {"extraction", "classification"}:
            return ModelTier.TIER2

        # Default safe choice: tier2 unless explicitly reasoning-heavy.
        return ModelTier.TIER2

    def _estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Rough cost estimation based on total tokens and pricing table."""

        price = self.pricing_per_1k_tokens.get(model, 0.0)
        total_tokens = max(tokens_in, 0) + max(tokens_out, 0)
        return round((total_tokens / 1000.0) * price, 6)

    def _build_reason(self, profile: TaskProfile, tier: ModelTier) -> str:
        """Human-friendly routing rationale."""

        parts = [f"intent={profile.intent}", f"operation={profile.operation}", f"tier={tier.value}"]
        if profile.requires_reasoning:
            parts.append("reasoning=true")
        if profile.preferred_tier:
            parts.append("preferred_tier_applied")
        return ",".join(parts)
