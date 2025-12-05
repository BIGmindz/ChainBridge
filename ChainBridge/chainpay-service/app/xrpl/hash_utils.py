"""
Deterministic settlement hash utility for ChainBridge XRPL anchoring.
"""
import hashlib
import json
from typing import Any, Dict

def generate_settlement_hash(settlement_payload: Dict[str, Any]) -> str:
    # Canonicalize JSON (sorted keys, no whitespace)
    canonical_json = json.dumps(settlement_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
