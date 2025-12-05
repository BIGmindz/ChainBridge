"""
ChainIQ Service - FastAPI Application

Production-grade intelligence engine for ChainBridge logistics platform.
Provides risk scoring, payment optimization, and fleet-level analytics.
"""

from core.import_safety import ensure_import_safety

ensure_import_safety()

from fastapi import FastAPI

from .api import router
from .api_iot import router as iot_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ChainIQ Service",
        description="AI-powered intelligence engine for logistics risk assessment and optimization",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Include the API router with all endpoints
    app.include_router(router)

    # Expose IoT facade separately so it can live outside /iq namespace
    app.include_router(iot_router)

    # Mount preset analytics router (no extra prefix; router already has /ai/presets)
    from app.api_ai_presets import router as preset_analytics_router

    app.include_router(preset_analytics_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Service health check."""
        return {"status": "healthy", "service": "chainiq", "version": "2.0.0"}

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
