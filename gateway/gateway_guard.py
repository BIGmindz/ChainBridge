"""Gateway execution guard that applies routing and rate limits before decisions."""

from __future__ import annotations

from typing import Mapping, Tuple, Union

from gateway.decision_engine import DecisionEngine
from gateway.model_router import ModelRouter, RouteDecision, TaskProfile
from gateway.rate_limit import RateLimiter, RateLimitError, RequestContext
from gateway.validator import GatewayValidator
from tracking.metrics_collector import MetricsCollector


class GatewayExecutionGuard:
    """Orchestrates rate limiting, model routing, and gateway decisions."""

    def __init__(
        self,
        decision_engine: DecisionEngine | None = None,
        router: ModelRouter | None = None,
        rate_limiter: RateLimiter | None = None,
        metrics_collector: MetricsCollector | None = None,
    ) -> None:
        self.decision_engine = decision_engine or DecisionEngine(validator=GatewayValidator())
        self.router = router or ModelRouter()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.metrics = metrics_collector

    def evaluate(
        self,
        raw_intent: Union[Mapping[str, object], object],
        profile: TaskProfile,
        context: RequestContext,
        previous_state: object | None = None,
    ) -> Tuple[object, RouteDecision]:
        """Apply guardrails, then execute the deterministic gateway engine.

        Routing and rate limiting happen before gateway execution, and cost
        telemetry is recorded after routing to prevent silent blowups.
        """

        # Enforce rate limits first to avoid expensive work when over limit.
        self.rate_limiter.enforce(context)

        # Determine which model to use before the decision engine runs.
        route_decision = self.router.route(profile)

        # Track cost and model selection for observability.
        if self.metrics:
            self.metrics.track_llm_usage(
                model=route_decision.model,
                tier=route_decision.tier.value,
                tokens_in=route_decision.tokens_in,
                tokens_out=route_decision.tokens_out,
                cost=route_decision.estimated_cost,
                user_id=context.user_id,
                agent_id=context.agent_id,
                endpoint=context.endpoint,
                reason=route_decision.reason,
            )

        # Execute the deterministic gateway decision engine.
        pdo = self.decision_engine.evaluate(raw_intent, previous_state=previous_state)
        return pdo, route_decision

    def can_execute(self, context: RequestContext) -> bool:
        """Lightweight check to see if a request would be allowed."""

        try:
            self.rate_limiter.enforce(context)
        except RateLimitError:
            return False
        return True
