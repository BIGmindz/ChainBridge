"""
GIE Storage Package

Proof-addressed PDO storage engine.
"""

from core.gie.storage.pdo_store import (
    PDOStore,
    PDORecord,
    StorageResult,
    StorageStatus,
    StorageOperation,
    get_pdo_store,
    reset_pdo_store,
)
from core.gie.storage.pdo_index import (
    PDOIndex,
    IndexType,
    get_pdo_index,
    reset_pdo_index,
)

__all__ = [
    "PDOStore",
    "PDORecord",
    "StorageResult",
    "StorageStatus",
    "StorageOperation",
    "get_pdo_store",
    "reset_pdo_store",
    "PDOIndex",
    "IndexType",
    "get_pdo_index",
    "reset_pdo_index",
]
