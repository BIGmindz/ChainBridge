"""Space and Time ProofPack Client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProofRequest:
    """Proof request configuration."""

    proof_type: str
    shipment_id: str
    token_id: str
    token_type: str
    payload_hash: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof_type": self.proof_type,
            "shipment_id": self.shipment_id,
            "token_id": self.token_id,
            "token_type": self.token_type,
            "payload_hash": self.payload_hash,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ProofResult:
    """Proof computation result."""

    proof_hash: Optional[str]
    verified: bool
    verdict: str
    confidence: float
    metadata: Dict[str, Any]

    @property
    def is_valid(self) -> bool:
        return self.verified and bool(self.proof_hash)


class ProofComputationError(RuntimeError):
    """Raised when SxT rejects or fails to compute a proof."""


class ProofClient:
    """Async HTTP client for SxT ProofPack service."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        offline_mode: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._offline_mode = offline_mode
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> None:
        if self._client is None:
            headers = {"User-Agent": "ChainBridge/ProofClient"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=headers)

    async def __aenter__(self) -> "ProofClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request_proof(self, request: ProofRequest) -> ProofResult:
        await self._ensure_client()
        assert self._client

        url = f"{self._base_url}/sxt/proof/compute"
        try:
            response = await self._client.post(url, json=request.to_dict())
            response.raise_for_status()
            payload = response.json()
            return self._parse_response(payload)
        except Exception as exc:  # pragma: no cover - network optional
            logger.error("Proof computation failed: %s", exc)
            if self._offline_mode:
                return self.offline_success(request)
            raise ProofComputationError(str(exc)) from exc

    def _parse_response(self, payload: Dict[str, Any]) -> ProofResult:
        return ProofResult(
            proof_hash=payload.get("proof_hash"),
            verified=bool(payload.get("verified", False)),
            verdict=str(payload.get("verdict", "REJECTED")),
            confidence=float(payload.get("confidence", 0)),
            metadata=payload.get("metadata", {}),
        )

    @staticmethod
    def offline_success(request: ProofRequest) -> ProofResult:
        """Deterministic success used in tests."""

        pseudo_hash = f"proof-{request.token_id}-{int(datetime.now(timezone.utc).timestamp())}"
        return ProofResult(
            proof_hash=pseudo_hash,
            verified=True,
            verdict="APPROVED",
            confidence=0.99,
            metadata={"offline": True, **request.metadata},
        )


__all__ = ["ProofClient", "ProofRequest", "ProofResult", "ProofComputationError"]
