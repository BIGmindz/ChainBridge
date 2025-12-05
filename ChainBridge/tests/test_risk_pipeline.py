from datetime import datetime, timezone

import pytest

from chainbridge.chainiq.risk_client import (
    ChainIQRiskClient,
    RiskEvaluationRequest,
    RiskEvaluationResult,
)
from chainbridge.events.schemas import (
    EventSource,
    EventType,
    RoutingDecision,
    TokenEventPayload,
    TokenTransitionEvent,
)
from .helpers.mocks import build_router_harness, seed_st01


@pytest.mark.asyncio
async def test_high_risk_blocks_transition() -> None:
    harness = build_router_harness()
    token = seed_st01(harness.token_router, shipment_id="ST01-100", state="IN_TRANSIT")

    harness.risk_client.queue.append(
        RiskEvaluationResult(
            risk_score=95,
            risk_label="CRITICAL",
            confidence=0.9,
            recommended_action="HOLD",
            anomalies=["GPS_SPOOF"],
            requires_proof=True,
            freeze=True,
            halt_transition=True,
            message="Freeze due to spoofing",
        )
    )

    event = TokenTransitionEvent(
        event_type=EventType.TOKEN_TRANSITION,
        source=EventSource.TOKEN_ENGINE,
        timestamp=datetime.now(timezone.utc),
        parent_shipment_id="ST01-100",
        actor_id="system",
        payload=TokenEventPayload(
            token_id=token.token_id,
            token_type="ST-01",
            previous_state=token.state,
            new_state="ARRIVED",
            metadata_changes={},
            relation_changes={},
        ),
    )

    result = await harness.router.submit(event)
    assert result.decision == RoutingDecision.REJECTED
    assert "Freeze" in (result.error_message or "")


@pytest.mark.asyncio
async def test_risk_requires_proof_triggers_proofpack() -> None:
    harness = build_router_harness()
    token = seed_st01(harness.token_router, shipment_id="ST01-200", state="IN_TRANSIT")

    harness.risk_client.queue.append(
        RiskEvaluationResult(
            risk_score=70,
            risk_label="HIGH",
            confidence=0.8,
            recommended_action="HOLD",
            anomalies=["TEMP_SPIKE"],
            requires_proof=True,
            freeze=False,
            halt_transition=True,
            message="Proof before delivery",
        )
    )

    event = TokenTransitionEvent(
        event_type=EventType.TOKEN_TRANSITION,
        source=EventSource.TOKEN_ENGINE,
        timestamp=datetime.now(timezone.utc),
        parent_shipment_id="ST01-200",
        actor_id="system",
        payload=TokenEventPayload(
            token_id=token.token_id,
            token_type="ST-01",
            previous_state=token.state,
            new_state="DELIVERED",
            metadata_changes={},
            relation_changes={},
        ),
    )

    result = await harness.router.submit(event)
    assert result.decision == RoutingDecision.REJECTED
    assert harness.proof_client.succeed is True
    assert "proof" in (result.error_message or "").lower()


@pytest.mark.asyncio
async def test_risk_client_offline_recommendation() -> None:
    client = ChainIQRiskClient("http://localhost", offline_fallback=True)
    request = RiskEvaluationRequest(
        shipment_id="ST01-300",
        event_type="TOKEN_TRANSITION",
        tokens=[],
        actor_id="system",
        anomalies=["ETA_SLIP"],
        requires_proof_hint=True,
    )

    fallback = client._fallback(request)  # noqa: SLF001 - intentional private call for test
    assert fallback.recommended_action == "HOLD_PAYMENT"
    assert fallback.requires_proof is True
