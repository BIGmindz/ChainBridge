"""Simple snapshot export worker loop for local/dev use."""

from __future__ import annotations

import os
import signal
import sys
import time
from datetime import datetime
from typing import Optional

from api.chainiq_service import export_worker
from api.database import SessionLocal, init_db

POLL_SECONDS = float(os.getenv("CHAINIQ_WORKER_IDLE_SLEEP", "3"))
PROCESS_SECONDS = float(os.getenv("CHAINIQ_WORKER_PROCESS_SECONDS", "1.5"))
FAILURE_RATE = float(os.getenv("CHAINIQ_WORKER_FAILURE_RATE", "0.0"))
TARGET_SYSTEM = os.getenv("CHAINIQ_WORKER_TARGET", None)


class WorkerRunner:
    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id
        self._stopping = False

    def stop(self) -> None:
        self._stopping = True

    def run(self) -> None:
        init_db()
        print(f"[Worker {self.worker_id}] starting export loop")
        while not self._stopping:
            event = self._claim_once()
            if not event:
                time.sleep(POLL_SECONDS)
                continue

            event_id = event.id
            target = event.target_system
            print(f"[{self._ts()}] claimed event {event_id} ({target})")
            time.sleep(PROCESS_SECONDS)

            if FAILURE_RATE and FAILURE_RATE > 0.0 and os.urandom(1)[0] / 255.0 < FAILURE_RATE:
                self._mark_failed(event_id, "simulated failure")
            else:
                self._mark_success(event_id)

        print(f"[Worker {self.worker_id}] stopped")

    def _claim_once(self) -> Optional[export_worker.SnapshotExportEvent]:
        with SessionLocal() as session:
            return export_worker.claim_next_pending_event(
                session, self.worker_id, target_system=TARGET_SYSTEM
            )

    def _mark_success(self, event_id: int) -> None:
        with SessionLocal() as session:
            export_worker.mark_event_success(session, event_id)
        print(f"[{self._ts()}] event {event_id} marked SUCCESS")

    def _mark_failed(self, event_id: int, reason: str) -> None:
        with SessionLocal() as session:
            export_worker.mark_event_failed(session, event_id, reason=reason, retryable=True)
        print(f"[{self._ts()}] event {event_id} marked FAILED ({reason})")

    @staticmethod
    def _ts() -> str:
        return datetime.utcnow().strftime("%H:%M:%S")


def _signal_handler(runner: WorkerRunner, *_args) -> None:
    runner.stop()


def main() -> None:
    worker_id = os.getenv("CHAINIQ_WORKER_ID", f"worker-{os.getpid()}")
    runner = WorkerRunner(worker_id)
    signal.signal(signal.SIGINT, lambda sig, frame: _signal_handler(runner))
    signal.signal(signal.SIGTERM, lambda sig, frame: _signal_handler(runner))
    try:
        runner.run()
    except KeyboardInterrupt:
        runner.stop()


if __name__ == "__main__":
    main()
