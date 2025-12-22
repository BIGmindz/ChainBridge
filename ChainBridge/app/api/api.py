"""FastAPI app wiring for new v2 endpoints."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.endpoints.audit import router as audit_router
from app.api.endpoints.stake import router as stake_router
from app.api.endpoints.dutch import router as dutch_router
from app.api.endpoints.demo import router as demo_router
from app.api.endpoints.marketplace import router as marketplace_router


def create_app() -> FastAPI:
    app = FastAPI(title="ChainBridge v2")
    app.include_router(audit_router)
    app.include_router(stake_router)
    app.include_router(dutch_router)
    app.include_router(marketplace_router)
    app.include_router(demo_router)
    return app


app = create_app()
