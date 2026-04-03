"""
FastAPI application factory - main entry point for the API server.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.logging_config import setup_logging
from config.settings import get_settings
from core.middleware import AuditMiddleware, RateLimitMiddleware, TenantMiddleware
from models.database import close_db, init_db
from services.ingestion.pipeline import get_ingestion_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle startup and shutdown events."""
    settings = get_settings()
    logger = setup_logging("DEBUG" if settings.debug else "INFO")
    pipeline = get_ingestion_pipeline()

    logger.info("PrivateGPT API starting up")

    await init_db()
    logger.info("Database initialized")

    settings.ensure_directories()
    await pipeline.start_background_worker()

    yield

    await pipeline.stop_background_worker()
    await close_db()
    logger.info("PrivateGPT API shut down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="PrivateGPT API",
        description="Secure RAG-Based Document Intelligence System",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware)

    from api.routes.admin import router as admin_router
    from api.routes.analytics import router as analytics_router
    from api.routes.auth import router as auth_router
    from api.routes.documents import router as documents_router
    from api.routes.query import router as query_router
    from api.websocket import stream_query_websocket

    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
    app.include_router(query_router, prefix="/api/query", tags=["Query"])
    app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
    app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
    app.add_api_websocket_route("/ws/query", stream_query_websocket)

    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
