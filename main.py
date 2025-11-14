import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.proofpacks_api import router as proofpacks_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("APP_ENV") != "dev" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting ChainBridge ProofPack API...")
    logger.info(f"Environment: {os.getenv('APP_ENV', 'production')}")
    logger.info(f"Runtime directory: {os.getenv('PROOFPACK_RUNTIME_DIR', 'proofpacks/runtime')}")

    # Verify critical environment variables
    if not os.getenv("SIGNING_SECRET") and os.getenv("APP_ENV", "").lower() != "dev":
        logger.error("SIGNING_SECRET not set in production environment!")
        sys.exit(1)

    yield

    # Shutdown
    logger.info("Shutting down ChainBridge ProofPack API...")


# Initialize FastAPI app
app = FastAPI(
    title="ChainBridge ProofPack API",
    version="1.0.0",
    description="Verifiable freight proof packs with cryptographic integrity",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (configure allowed origins in production)
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration and monitoring.

    Returns:
        Health status including service info
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "chainbridge-proofpacks",
            "version": "1.0.0",
            "environment": os.getenv("APP_ENV", "production"),
        }
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return JSONResponse(
        content={
            "service": "ChainBridge ProofPack API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "api_prefix": "/v1/proofpacks",
        }
    )


# Include routers
app.include_router(proofpacks_router)


if __name__ == "__main__":
    import uvicorn

    try:
        port = int(os.getenv("PORT", "8080"))
    except ValueError:
        logger.error("Invalid PORT value, must be an integer")
        sys.exit(1)
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("APP_ENV") == "dev",
        log_level="info",
    )
