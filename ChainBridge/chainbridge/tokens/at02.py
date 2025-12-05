"""Accessorial token (AT-02)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_token import BaseToken, TokenValidationError


class AT02Token(BaseToken):
    """Proof-enforced accessorial lifecycle."""

    TOKEN_TYPE = "AT-02"
    VERSION = "1.0"
    INITIAL_STATE = "PROPOSED"
    STATE_MACHINE: Dict[str, List[str]] = {
        "PROPOSED": ["PROOF_ATTACHED"],
        "PROOF_ATTACHED": ["VERIFIED"],
        "VERIFIED": ["PUBLISHED"],
        "PUBLISHED": [],
    }
    REQUIRED_FIELDS: Dict[str, Any] = {
        "accessorial_type": str,
        "amount": float,
        "timestamp": str,
        "actor": str,
        "currency": str,
    }
    OPTIONAL_FIELDS: Dict[str, Any] = {
        "notes": str,
        "policy_reference": str,
    }
    REQUIRED_RELATIONS = ("st01_id", "mt01_id")

    def attach_proof(self, *, proof_hash: str, metadata: Optional[Dict[str, Any]] = None) -> None:  # type: ignore[override]
        super().attach_proof(proof_hash=proof_hash, source="SxT", metadata=metadata)
        if self.state == "PROPOSED":
            self.state = "PROOF_ATTACHED"

    def validate_state_constraints(self) -> None:
        if self.state in {"PROOF_ATTACHED", "VERIFIED", "PUBLISHED"} and not self.proof_hash:
            raise TokenValidationError("AT-02 must include proof hash beyond PROPOSED state")
        if self.state in {"VERIFIED", "PUBLISHED"} and not self.metadata.get("policy_match_id"):
            raise TokenValidationError("AT-02 verification requires policy_match_id (ALEX rules)")
