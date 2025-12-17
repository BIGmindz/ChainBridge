"""Gateway Policy Decision Object (PDO) v1."""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from gateway.intent_schema import GatewayIntent, IntentState


class PDOOutcome(str, Enum):
    """Deterministic outcomes for gateway decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"


class GatewayPDO(BaseModel):
    """Gateway PDO v1 schema (fail-closed by default)."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0", frozen=True, description="PDO schema version")
    outcome: PDOOutcome = Field(..., description="Decision outcome")
    state: IntentState = Field(..., description="Final state after decision")
    intent: GatewayIntent = Field(..., description="Validated intent that was evaluated")
    reasons: List[str] = Field(default_factory=list, description="Deterministic reasons for the outcome")

    def hard_reject(self, reasons: List[str]) -> "GatewayPDO":
        """Return a new hard-reject PDO with provided reasons."""

        return GatewayPDO(
            version=self.version,
            outcome=PDOOutcome.REJECTED,
            state=self.state,
            intent=self.intent,
            reasons=reasons,
        )
