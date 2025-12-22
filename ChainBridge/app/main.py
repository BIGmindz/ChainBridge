"""FastAPI entrypoint wiring ChainBridge routers together."""

from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api.database import get_db
from api.routes.chain_audit import router as chain_audit_router
from api.routes.chainboard import router as chainboard_router
from api.routes.intel import router as intel_router
from app.api import create_app as create_v2_app
from app.api.endpoints.marketplace import get_authoritative_price


def build_app() -> FastAPI:
    app = create_v2_app()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict:
        return {"status": "online", "mode": "demo"}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/marketplace/pricing/{listing_id}")
    async def pricing_alias(listing_id: str, request: Request, db: Session = Depends(get_db)):
        """Alias endpoint for deterministic Dutch price checks."""
        return await get_authoritative_price(listing_id, request, db)

    app.include_router(chainboard_router)
    app.include_router(intel_router)
    app.include_router(chain_audit_router)
    return app


app = build_app()
