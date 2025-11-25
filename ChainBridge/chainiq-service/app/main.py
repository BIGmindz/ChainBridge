"""
ChainIQ Service - FastAPI Application

Production-grade intelligence engine for ChainBridge logistics platform.
Provides risk scoring, payment optimization, and fleet-level analytics.
"""

from fastapi import FastAPI

from .api import router


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
