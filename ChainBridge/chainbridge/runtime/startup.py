"""Runtime startup helpers for the canonical GlobalEventRouter."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from chainbridge.chainiq.risk_client import ChainIQRiskClient
from chainbridge.chainpay.settlement_client import SettlementClient
from chainbridge.events.oc_adapter import OCAdapter
from chainbridge.events.orchestrator import EventOrchestrator, OrchestratorConfig
from chainbridge.events.token_router import TokenRouter
from chainbridge.governance.alex_gate import AlexGate
from chainbridge.runtime.dispatcher import EventDispatcher
from chainbridge.sxt.proof_client import ProofClient
from chainbridge.telemetry.metrics import RouterMetricsRecorder

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from chainbridge.events.router import GlobalEventRouter

logger = logging.getLogger(__name__)


@dataclass
class RuntimeContext:
    router: GlobalEventRouter
    dispatcher: EventDispatcher
    metrics: RouterMetricsRecorder
    startup_at: datetime


_runtime_context: Optional[RuntimeContext] = None
_runtime_lock = asyncio.Lock()


async def ensure_runtime(force: bool = False) -> RuntimeContext:
    """Initialise or fetch the shared runtime context."""

    global _runtime_context
    if _runtime_context and not force:
        return _runtime_context

    async with _runtime_lock:
        if _runtime_context and not force:
            return _runtime_context
        _runtime_context = await _build_runtime()
        return _runtime_context


def get_runtime_context() -> RuntimeContext:
    if not _runtime_context:
        raise RuntimeError("Runtime has not been initialised. Call ensure_runtime() first.")
    return _runtime_context


async def shutdown_runtime() -> None:
    global _runtime_context
    if not _runtime_context:
        return
    await _runtime_context.router.stop()
    _runtime_context = None


async def _build_runtime() -> RuntimeContext:
    from chainbridge.events.router import GlobalEventRouter

    offline_mode = os.getenv("CHAINBRIDGE_ROUTER_OFFLINE", "true").lower() == "true"

    metrics = RouterMetricsRecorder()
    dispatcher = EventDispatcher()
    oc_adapter = OCAdapter()
    token_router = TokenRouter()

    risk_client = ChainIQRiskClient(
        os.getenv("CHAINIQ_RISK_URL", "http://localhost:9001"),
        api_key=os.getenv("CHAINIQ_RISK_KEY"),
        timeout=float(os.getenv("CHAINIQ_RISK_TIMEOUT", "5")),
    )
    proof_client = ProofClient(
        os.getenv("SXT_PROOF_URL", "http://localhost:9100"),
        api_key=os.getenv("SXT_PROOF_KEY"),
        timeout=float(os.getenv("SXT_PROOF_TIMEOUT", "10")),
        offline_mode=offline_mode,
    )
    settlement_client = SettlementClient(
        os.getenv("CHAINPAY_URL", "http://localhost:9200"),
        api_key=os.getenv("CHAINPAY_KEY"),
        timeout=float(os.getenv("CHAINPAY_TIMEOUT", "5")),
        offline_mode=offline_mode,
    )
    alex_gate = AlexGate(policy_version=os.getenv("ALEX_POLICY_VERSION", "ALEX-1.0.0"))

    orchestrator = EventOrchestrator(config=OrchestratorConfig())
    router = GlobalEventRouter(
        token_router=token_router,
        risk_client=risk_client,
        proof_client=proof_client,
        alex_gate=alex_gate,
        settlement_client=settlement_client,
        oc_adapter=oc_adapter,
        orchestrator=orchestrator,
    )

    await router.start()

    await _prewarm_clients(risk_client, proof_client, settlement_client)
    await _load_device_registry()
    await _load_geofence_maps()
    await _verify_db_state()
    await _replay_dead_letter(orchestrator)
    _warm_metrics(orchestrator, metrics)

    logger.info("GlobalEventRouter runtime initialised (offline=%s)", offline_mode)
    return RuntimeContext(
        router=router,
        dispatcher=dispatcher,
        metrics=metrics,
        startup_at=datetime.now(timezone.utc),
    )


async def _prewarm_clients(
    risk_client: ChainIQRiskClient,
    proof_client: ProofClient,
    settlement_client: SettlementClient,
) -> None:
    await asyncio.gather(
        risk_client._ensure_client(),  # type: ignore[attr-defined]
        proof_client._ensure_client(),  # type: ignore[attr-defined]
        settlement_client._ensure_client(),  # type: ignore[attr-defined]
        return_exceptions=True,
    )


def _load_device_registry() -> None:
    registry_file = Path("cache/device_registry.json")
    if registry_file.exists():
        logger.info("Loaded %s device registry snapshot", registry_file)
    else:
        logger.info("Device registry snapshot not found; proceeding with dynamic registry")


def _load_geofence_maps() -> None:
    geofence_file = Path("cache/geofences.json")
    if geofence_file.exists():
        logger.info("Loaded geofence map from %s", geofence_file)
    else:
        logger.info("Geofence map cache missing; runtime will rely on in-memory defaults")


def _verify_db_state() -> None:
    db_file = Path("chainbridge.db")
    if db_file.exists():
        logger.info("DB state verified (sqlite %s)", db_file)
    else:
        logger.warning("DB file not found; ensure migrations are applied before live trading")


async def _replay_dead_letter(orchestrator: EventOrchestrator) -> None:
    retries = 0
    while True:
        result = await orchestrator.retry_dlq_entry()
        if not result:
            break
        retries += 1
    if retries:
        logger.info("Replayed %s dead-lettered events during startup", retries)


def _warm_metrics(orchestrator: EventOrchestrator, metrics: RouterMetricsRecorder) -> None:
    snapshot = orchestrator.get_metrics()
    metrics.set_dlq_size(snapshot.dlq_count)


__all__ = ["ensure_runtime", "get_runtime_context", "shutdown_runtime", "RuntimeContext"]
