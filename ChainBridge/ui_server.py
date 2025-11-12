#!/usr/bin/env python3
"""
Lightweight UI HTTP Server
Serves:
  GET /health                -> {status: ok}
  GET /snapshot              -> ui_snapshot.json contents
  GET /metrics               -> runtime_metrics.json contents
  GET /stream (SSE)          -> pushes snapshot updates every poll (best-effort)

No external dependencies; uses Python stdlib only so it works in restricted envs.

Usage:
  python ui_server.py --port 8080 --host 0.0.0.0

Integrating the external UI:
  - Poll /snapshot every 5-30s OR open an EventSource to /stream
  - Expect JSON shape: { ts, symbols: [...], portfolio: {...}, config: {...} }
"""
from __future__ import annotations
import argparse
import json
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Optional

SNAPSHOT_PATH = Path("ui_snapshot.json")
METRICS_PATH = Path("runtime_metrics.json")
TRADES_PATH = Path("logs/trades.jsonl")
STATIC_DIR = Path("static")

_snapshot_cache = None
_snapshot_mtime: Optional[float] = None
_cache_lock = Lock()


def load_snapshot():
    global _snapshot_cache, _snapshot_mtime
    try:
        if SNAPSHOT_PATH.exists():
            mtime = SNAPSHOT_PATH.stat().st_mtime
            if _snapshot_mtime != mtime:
                with SNAPSHOT_PATH.open("r", encoding="utf-8") as fh:
                    _snapshot_cache = json.load(fh)
                    _snapshot_mtime = mtime
        return _snapshot_cache
    except Exception as exc:
        return {"error": f"failed to load snapshot: {exc}"}


def load_metrics():
    try:
        if METRICS_PATH.exists():
            with METRICS_PATH.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return {"status": "no_metrics"}
    except Exception as exc:
        return {"error": f"failed to load metrics: {exc}"}


class UIServerHandler(BaseHTTPRequestHandler):
    server_version = "UIBridge/0.1"

    def _send_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, rel_path: str):
        try:
            target = STATIC_DIR / rel_path
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
                return
            # Minimal content type detection
            ext = target.suffix.lower()
            ctype = "text/plain"
            if ext in {".html", ".htm"}:
                ctype = "text/html; charset=utf-8"
            elif ext == ".js":
                ctype = "text/javascript; charset=utf-8"
            elif ext == ".css":
                ctype = "text/css; charset=utf-8"
            data = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            self._send_json(
                {"error": f"static_error: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _load_trades(self, limit: int = 50):
        try:
            if not TRADES_PATH.exists():
                return []
            lines = TRADES_PATH.read_text(encoding="utf-8").strip().splitlines()
            recent = lines[-limit:]
            out = []
            for ln in recent:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
            return out
        except Exception as exc:
            return {"error": f"failed_to_load_trades: {exc}"}

    def do_GET(self):  # noqa: N802
        # JSON / API endpoints
        if self.path == "/health":
            return self._send_json({"status": "ok"})
        if self.path == "/snapshot":
            with _cache_lock:
                snap = load_snapshot()
            return self._send_json(snap or {"status": "empty"})
        if self.path == "/metrics":
            return self._send_json(load_metrics())
        if self.path == "/trades":
            return self._send_json({"trades": self._load_trades()})
        if self.path.startswith("/stream"):
            return self._handle_stream()
        if self.path in {"/", "/dashboard"}:
            return self._serve_static("dashboard.html")
        # Static files under /static/*
        if self.path.startswith("/static/"):
            rel = self.path[len("/static/") :]
            return self._serve_static(rel)
        # Default 404
        self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):  # noqa: A003
        # Quiet logging (optional: comment out to see requests)
        return

    def _handle_stream(self):
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            last_sent = None
            while True:
                with _cache_lock:
                    snap = load_snapshot()
                if snap and snap != last_sent:
                    data = json.dumps(snap)
                    self.wfile.write("event: snapshot\n".encode())
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                    last_sent = snap
                time.sleep(5)
        except BrokenPipeError:
            return
        except Exception:
            return


def run(host: str, port: int):
    httpd = ThreadingHTTPServer((host, port), UIServerHandler)
    print(f"🌐 UI server running on http://{host}:{port}")
    print("  /health   /snapshot   /metrics   /trades   /stream   /dashboard")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 UI server stopping...")
    finally:
        httpd.server_close()


def parse_args():
    ap = argparse.ArgumentParser(description="Lightweight UI bridge server")
    ap.add_argument("--host", default=os.getenv("UI_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("UI_PORT", "8080")))
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.host, args.port)
