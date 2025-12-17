import pytest

from gateway.decision_engine import DecisionEngine
from gateway.gateway_guard import GatewayExecutionGuard
from gateway.intent_schema import IntentAction, IntentChannel, IntentState, IntentType
from gateway.model_router import ModelRouter, ModelTier, TaskProfile
from gateway.rate_limit import RateLimitConfig, RateLimiter, RateLimitError, RequestContext
from tracking.metrics_collector import MetricsCollector


@pytest.fixture()
def valid_intent_payload():
    return {
        "intent_type": IntentType.PAYMENT,
        "action": IntentAction.CREATE,
        "channel": IntentChannel.API,
        "payload": {
            "resource_id": "ship-123",
            "amount_minor": 1500,
            "currency": "USD",
            "metadata": {"source": "unit-test"},
        },
        "correlation_id": "corr-123",
    }


def test_model_router_prefers_tier1_for_reasoning():
    router = ModelRouter()

    decision = router.route(TaskProfile(intent="risk", operation="analysis", requires_reasoning=True, input_tokens=1200, output_tokens=400))

    assert decision.tier is ModelTier.TIER1
    assert decision.model == "gpt-4o"
    assert decision.estimated_cost > 0


def test_model_router_uses_tier2_for_extraction():
    router = ModelRouter()

    decision = router.route(
        TaskProfile(intent="payment", operation="extraction", requires_reasoning=False, input_tokens=300, output_tokens=50)
    )

    assert decision.tier is ModelTier.TIER2
    assert decision.model == "gpt-4o-mini"


def test_rate_limiter_enforces_per_user_limit():
    clock = {"now": 0.0}

    def time_provider() -> float:
        return clock["now"]

    limiter = RateLimiter(RateLimitConfig(per_user=2, per_agent=5, per_endpoint=5, window_seconds=60), time_provider=time_provider)
    ctx = RequestContext(user_id="user-1", agent_id="agent-1", endpoint="/gateway/decision")

    limiter.enforce(ctx)
    limiter.enforce(ctx)
    with pytest.raises(RateLimitError):
        limiter.enforce(ctx)

    # Advance beyond window to allow again
    clock["now"] += 61
    limiter.enforce(ctx)


def test_gateway_guard_routes_and_logs_cost(tmp_path, valid_intent_payload):
    metrics_path = tmp_path / "metrics.json"
    guard = GatewayExecutionGuard(
        decision_engine=DecisionEngine(),
        router=ModelRouter(),
        rate_limiter=RateLimiter(RateLimitConfig(per_user=10, per_agent=10, per_endpoint=10)),
        metrics_collector=MetricsCollector(metrics_file=str(metrics_path)),
    )

    context = RequestContext(user_id="user-42", agent_id="agent-blue", endpoint="/gateway/decision")
    profile = TaskProfile(intent="payment", operation="classification", input_tokens=500, output_tokens=120)

    pdo, route = guard.evaluate(valid_intent_payload, profile, context)

    assert pdo.state is IntentState.DECIDED
    llm_metrics = guard.metrics.get_llm_metrics()
    assert llm_metrics["by_model"][route.model]["requests"] == 1
    assert llm_metrics["by_user"][context.user_id]["tokens_in"] == 500
