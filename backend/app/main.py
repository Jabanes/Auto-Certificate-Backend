"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import certificate_routes, distribution_routes, template_routes
from app.core.config import settings
from app.core.logging_config import logger

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Certificate Generation and Distribution Backend",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(template_routes.router)
app.include_router(certificate_routes.router)
app.include_router(distribution_routes.router)


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        Status message
    """
    return {
        "status": "ok",
        "message": "Certificate Generation Backend is running",
        "version": "2.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Template path: {settings.TEMPLATE_PATH}")
    logger.info(f"Data directory: {settings.DATA_DIR}")
    logger.info(f"Logs directory: {settings.LOGS_DIR}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        reload_dirs=["backend"] if settings.DEBUG else None
    )

