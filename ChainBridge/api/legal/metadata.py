"""Helpers for Ricardian instrument metadata generation."""
from __future__ import annotations

from typing import Any, Dict

from api.models.legal import RicardianInstrument


def build_ricardian_metadata(instrument: RicardianInstrument) -> Dict[str, Any]:
    return {
        "name": f"{instrument.instrument_type}:{instrument.physical_reference}",
        "description": f"Ricardian instrument for {instrument.physical_reference}",
        "legal_structure": instrument.ricardian_version,
        "document_uri": instrument.pdf_ipfs_uri or instrument.pdf_uri,
        "document_hash": instrument.pdf_hash,
        "governing_law": instrument.governing_law,
        "digital_supremacy": {
            "enabled": instrument.supremacy_enabled,
            "precedence": "code_over_prose",
            "ucc_reference": "UCC-7-106",
            "uk_etda_2023": True,
            "hash_binding": instrument.pdf_hash,
            "kill_switch": {
                "enabled": True,
                "conditions": [
                    "blockchain_security_failure",
                    "contract_hacked",
                    "court_order",
                ],
            },
        },
    }
