"""Document hashing and storage helpers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Tuple


def compute_sha256(data: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest()


def _storage_dir() -> Path:
    base = Path(os.getenv("CHAIN_DOCS_STORAGE_DIR", "cache/chaindocs"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def store_document(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """Persist bytes locally; returns (backend, ref)."""
    backend = "LOCAL"
    storage_path = _storage_dir() / filename
    storage_path.write_bytes(file_bytes)
    return backend, str(storage_path)
