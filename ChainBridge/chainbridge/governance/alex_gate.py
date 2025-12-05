"""ALEX Governance Adapter."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GovernanceDecision:
    approved: bool
    reason: str
    freeze: bool
    override_required: bool
    policy_version: str

    @property
    def blocked(self) -> bool:
        return not self.approved or self.freeze


class AlexGate:
    """In-process governance evaluator.

    The real system would call ALEX over gRPC/HTTP. For repo tests we
    simulate the policies deterministically while keeping the API stable.
    """

    def __init__(self, policy_version: str = "ALEX-1.0.0") -> None:
        self._policy_version = policy_version

    async def evaluate(
        self,
        *,
        token_type: str,
        current_state: str,
        new_state: str,
        risk_score: int,
        requires_proof: bool,
        proof_attached: bool,
        disputes_open: int = 0,
    ) -> GovernanceDecision:
        """Evaluate whether the transition can occur."""

        reason = ""
        approved = True
        freeze = False
        override_required = False

        if requires_proof and not proof_attached:
            approved = False
            reason = f"{token_type} transition requires proof before entering {new_state}"
        elif risk_score >= 80:
            approved = False
            freeze = True
            reason = "Risk score in CRITICAL range"
        elif disputes_open > 0 and token_type in {"IT-01", "PT-01"}:
            approved = False
            reason = "Open disputes block settlement transitions"
        elif token_type == "PT-01" and new_state == "FINAL_RELEASE" and risk_score >= 60:
            approved = False
            override_required = True
            reason = "High risk shipments need compliance override before final release"
        else:
            reason = "Policy satisfied"

        logger.debug(
            "ALEX decision token=%s %s→%s risk=%s proof=%s -> approved=%s freeze=%s",
            token_type,
            current_state,
            new_state,
            risk_score,
            proof_attached,
            approved,
            freeze,
        )

        return GovernanceDecision(
            approved=approved,
            reason=reason,
            freeze=freeze,
            override_required=override_required,
            policy_version=self._policy_version,
        )


__all__ = ["AlexGate", "GovernanceDecision"]
