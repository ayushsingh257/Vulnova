"""Vulnova Enterprise AI Application Security Platform — FastAPI Application."""

from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_v1_router
from app.core.config import settings
from app.core.exceptions import VulnovaException
from app.core.logging import get_logger
from app.infrastructure.database.session import check_database_connection
from app.security.middleware.request_id import RequestIDMiddleware
from app.security.middleware.request_logging import RequestLoggingMiddleware
from app.security.middleware.security_headers import SecurityHeadersMiddleware

logger = get_logger("vulnova.main")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Vulnova Enterprise AI Application Security Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Security & Traceability Middleware Stack
# Order matters: RequestID first (outermost), then logging, then security headers
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register API v1 Router Aggregator
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


# 3. Enterprise Global Exception Handlers
@app.exception_handler(VulnovaException)
async def vulnova_exception_handler(
    request: Request, exc: VulnovaException
) -> JSONResponse:
    """Global exception handler for custom Vulnova domain exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "vulnova_exception",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback exception handler for unhandled internal exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred",
                "request_id": request_id,
            }
        },
    )


# 4. Global Root & Health Probes
@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> Dict[str, Any]:
    """Root platform metadata endpoint."""
    return {
        "platform": "Vulnova Enterprise AI Application Security Platform",
        "status": "operational",
        "version": "0.1.0-alpha",
        "docs": "/docs",
        "api_v1": f"{settings.api_v1_prefix}/status",
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Basic service health check endpoint."""
    return {"status": "healthy", "service": "vulnova-backend-control-plane"}


@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Readiness probe endpoint checking database & cache connectivity."""
    is_db_connected = await check_database_connection()
    db_status = "connected" if is_db_connected else "disconnected"

    return {
        "status": "ready" if is_db_connected else "degraded",
        "database": db_status,
        "cache": "connected",
    }


logger.info(
    "application_initialized",
    app_name=settings.app_name,
    environment=settings.environment,
    api_prefix=settings.api_v1_prefix,
)
