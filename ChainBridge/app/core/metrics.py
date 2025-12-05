"""Tiny metrics façade for counters/timers (stdlib-only)."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, Iterable

_COUNTERS: Dict[str, int] = defaultdict(int)
_LOCK = threading.Lock()


def increment_counter(name: str, value: int = 1) -> None:
    with _LOCK:
        _COUNTERS[name] += value


def get_counter(name: str) -> int:
    with _LOCK:
        return int(_COUNTERS.get(name, 0))


def get_counters(names: Iterable[str]) -> Dict[str, int]:
    with _LOCK:
        return {name: int(_COUNTERS.get(name, 0)) for name in names}
