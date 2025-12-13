"""
ChainIQ Service - FastAPI Application

Production-grade intelligence engine for ChainBridge logistics platform.
Provides risk scoring, payment optimization, and fleet-level analytics.
"""

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .api import router
from .api_drift import router as drift_router
from .api_fusion import router as fusion_router
from .api_iq_ml import router as iq_ml_router
from .api_shadow import router as shadow_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ChainIQ Service",
        description="AI-powered intelligence engine for logistics risk assessment and optimization",
        version="2.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Include the API router with all endpoints
    app.include_router(router)

    # Include the ML API router
    app.include_router(iq_ml_router)

    # Include the Shadow Mode API router
    app.include_router(shadow_router)

    # Include the Drift Detection API router (v1.1)
    app.include_router(drift_router)

    # Include the Fusion Scoring API router (v1.2)
    app.include_router(fusion_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Service health check."""
        return {"status": "healthy", "service": "chainiq", "version": "2.1.0"}

    # Prometheus metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """
        Prometheus metrics endpoint.

        Returns metrics in Prometheus exposition format for scraping.
        Includes custom ChainIQ ML metrics (risk/anomaly call counts and latencies).
        """
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
