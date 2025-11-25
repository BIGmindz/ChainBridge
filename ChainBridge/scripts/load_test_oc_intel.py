from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8001"
CONCURRENCY = 10
REQUESTS_PER_ENDPOINT = 50

PATHS = [
    "/intel/global-snapshot",
    "/chainboard/live-positions",
]


async def hammer_endpoint(client: httpx.AsyncClient, path: str) -> tuple[int, float]:
    url = f"{BASE_URL}{path}"
    start = time.perf_counter()
    try:
        resp = await client.get(url)
        elapsed = time.perf_counter() - start
        return resp.status_code, elapsed
    except Exception:
        elapsed = time.perf_counter() - start
        return 0, elapsed


async def run_load() -> None:
    tasks = []
    for path in PATHS:
        for _ in range(REQUESTS_PER_ENDPOINT):
            tasks.append((path, hammer_endpoint))

    results: list[tuple[str, int, float]] = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        for i in range(0, len(tasks), CONCURRENCY):
            chunk = tasks[i : i + CONCURRENCY]
            coros = [hammer_endpoint(client, PATHS[j // REQUESTS_PER_ENDPOINT]) for j in range(i, min(i + CONCURRENCY, len(tasks)))]
            chunk_results = await asyncio.gather(*coros)
            for idx, (status, elapsed) in enumerate(chunk_results):
                path = PATHS[(i + idx) // REQUESTS_PER_ENDPOINT]
                results.append((path, status, elapsed))

    total = len(results)
    ok = sum(1 for _, status, _ in results if status == 200)
    fail = total - ok
    avg_latency = sum(t for _, _, t in results) / max(total, 1)

    print("=== OC/INTEL LOAD TEST ===")
    print(f"Total Requests: {total}")
    print(f"200 OK       : {ok}")
    print(f"Failures     : {fail}")
    print(f"Avg Latency  : {avg_latency * 1000:.1f} ms")


if __name__ == "__main__":
    asyncio.run(run_load())
