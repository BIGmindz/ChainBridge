"""ChainIQ Risk Client.

Provides an async adapter between the event router and Maggie's risk engine.
The adapter enforces the risk → proof → settlement ordering by marking
transitions that must be halted until Maggie responds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskEvaluationRequest:
    """Request payload sent to Maggie."""

    shipment_id: str
    event_type: str
    tokens: List[Dict[str, Any]]
    actor_id: str
    anomalies: List[str]
    requires_proof_hint: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shipment_id": self.shipment_id,
            "event_type": self.event_type,
            "tokens": self.tokens,
            "actor_id": self.actor_id,
            "anomalies": self.anomalies,
            "requires_proof_hint": self.requires_proof_hint,
        }


@dataclass(frozen=True)
class RiskEvaluationResult:
    """Normalized risk response."""

    risk_score: int
    risk_label: str
    confidence: float
    recommended_action: str
    anomalies: List[str]
    requires_proof: bool
    freeze: bool
    halt_transition: bool
    message: Optional[str] = None

    @property
    def is_high_risk(self) -> bool:
        return self.risk_score >= 80 or self.freeze


class ChainIQRiskClient:
    """Async HTTP client for Maggie's risk engine."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        offline_fallback: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._offline_fallback = offline_fallback
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ChainIQRiskClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> None:
        if self._client is None:
            headers = {"User-Agent": "ChainBridge/ChainIQRiskClient"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(timeout=self._timeout, headers=headers)

    async def evaluate(self, request: RiskEvaluationRequest) -> RiskEvaluationResult:
        """Send payload to Maggie and normalise the response."""

        await self._ensure_client()
        assert self._client is not None

        url = f"{self._base_url}/chainiq/risk/stream"
        try:
            response = await self._client.post(url, json=request.to_dict())
            response.raise_for_status()
            payload = response.json()
            return self._coerce_response(payload)
        except Exception as exc:  # pragma: no cover - network optional
            if not self._offline_fallback:
                raise
            logger.warning("Risk engine unreachable, using deterministic fallback: %s", exc)
            return self._fallback(request)

    def _coerce_response(self, payload: Dict[str, Any]) -> RiskEvaluationResult:
        return RiskEvaluationResult(
            risk_score=int(payload.get("risk_score", 0)),
            risk_label=str(payload.get("risk_label", "LOW")),
            confidence=float(payload.get("confidence", 0.5)),
            recommended_action=str(payload.get("recommended_action", "RELEASE")),
            anomalies=list(payload.get("anomaly_flags", [])),
            requires_proof=bool(payload.get("requires_proof", False)),
            freeze=bool(payload.get("freeze", False)),
            halt_transition=bool(payload.get("halt_transition", False)),
            message=payload.get("explanation"),
        )

    def _fallback(self, request: RiskEvaluationRequest) -> RiskEvaluationResult:
        """Deterministic fallback used in offline/test environments."""

        # Simple heuristic: the more anomalies, the higher the risk.
        base_score = min(20 + len(request.anomalies) * 10, 95)
        requires_proof = base_score >= 60 or request.requires_proof_hint
        freeze = base_score >= 90
        halt_transition = requires_proof or freeze

        return RiskEvaluationResult(
            risk_score=base_score,
            risk_label=self._label_from_score(base_score),
            confidence=0.65,
            recommended_action="HOLD_PAYMENT" if requires_proof else "RELEASE_PAYMENT",
            anomalies=request.anomalies,
            requires_proof=requires_proof,
            freeze=freeze,
            halt_transition=halt_transition,
            message="Offline fallback scoring",
        )

    @staticmethod
    def _label_from_score(score: int) -> str:
        if score < 30:
            return "LOW"
        if score < 60:
            return "MEDIUM"
        if score < 80:
            return "HIGH"
        return "CRITICAL"


__all__ = ["ChainIQRiskClient", "RiskEvaluationRequest", "RiskEvaluationResult"]
