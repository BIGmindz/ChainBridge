"""ChainPay Settlement Client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SettlementRequest:
    st01_id: str
    it01_id: str
    pt01_id: Optional[str]
    amount: float
    currency: str
    stage: str  # PARTIAL_RELEASE, FINAL_RELEASE
    reason: str
    metadata: Dict[str, str]

    def to_dict(self) -> Dict[str, str]:
        return {
            "st01_id": self.st01_id,
            "it01_id": self.it01_id,
            "pt01_id": self.pt01_id,
            "amount": self.amount,
            "currency": self.currency,
            "stage": self.stage,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class SettlementResponse:
    accepted: bool
    pt01_state: str
    xrpl_tx_hash: Optional[str]
    message: str


class SettlementClient:
    """Async HTTP adapter to ChainPay settlement service."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        offline_mode: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._offline_mode = offline_mode
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> None:
        if self._client is None:
            headers = {"User-Agent": "ChainBridge/SettlementClient"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=headers)

    async def __aenter__(self) -> "SettlementClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def trigger(self, request: SettlementRequest) -> SettlementResponse:
        await self._ensure_client()
        assert self._client is not None

        url = f"{self._base_url}/chainpay/settlement"
        try:
            response = await self._client.post(url, json=request.to_dict())
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - network optional
            logger.error("Settlement request failed: %s", exc)
            if self._offline_mode:
                return self.offline_accept(request)
            return SettlementResponse(
                accepted=False,
                pt01_state="ERROR",
                xrpl_tx_hash=None,
                message=str(exc),
            )

        result = SettlementResponse(
            accepted=bool(payload.get("accepted", False)),
            pt01_state=str(payload.get("pt01_state", "ERROR")),
            xrpl_tx_hash=payload.get("xrpl_tx_hash"),
            message=str(payload.get("message", "")),
        )
        if not result.accepted and self._offline_mode:
            return self.offline_accept(request)
        return result

    @staticmethod
    def offline_accept(request: SettlementRequest) -> SettlementResponse:
        """Deterministic acceptance for tests."""
        stage_state = "PARTIAL_RELEASE" if request.stage == "PARTIAL_RELEASE" else "FINAL_RELEASE"
        return SettlementResponse(
            accepted=True,
            pt01_state=stage_state,
            xrpl_tx_hash=f"offline-{request.st01_id}-{request.stage.lower()}",
            message="Offline settlement",
        )


__all__ = ["SettlementClient", "SettlementRequest", "SettlementResponse"]
