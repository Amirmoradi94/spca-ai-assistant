"""FastAPI application for SPCA chatbot."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import chat, health
from ..chatbot.session_manager import get_session_manager
from ..database.session import init_db
from ..utils.config import get_settings
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    logger.info("Starting SPCA AI Assistant API")
    logger.info(f"Environment: {settings.app_env}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Start session manager cleanup
    session_manager = get_session_manager()
    await session_manager.start()
    logger.info("Session manager started")

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down API")
    await session_manager.stop()
    logger.info("Session manager stopped")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="SPCA AI Assistant API",
    description="AI-powered chatbot for the SPCA Montreal website",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(exc)},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred"},
    )


# Include routers
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(health.admin_router)


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "SPCA AI Assistant API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "health": "/health",
            "docs": "/docs",
            "admin": "/api/v1/admin",
        }
    }


def main():
    """Entry point for running the API with uvicorn."""
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
