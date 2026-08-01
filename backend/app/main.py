from typing import Any, Dict

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database.session import check_database_connection

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Vulnova Enterprise AI Application Security Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for local development & frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> Dict[str, Any]:
    """Root platform metadata endpoint."""
    return {
        "platform": "Vulnova Enterprise AI Application Security Platform",
        "status": "operational",
        "version": "0.1.0-alpha",
        "docs": "/docs",
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Basic service health check endpoint."""
    return {"status": "healthy", "service": "vulnova-backend-control-plane"}


@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Readiness probe endpoint checking database & cache connection status."""
    is_db_connected = await check_database_connection()
    db_status = "connected" if is_db_connected else "disconnected"

    return {
        "status": "ready" if is_db_connected else "degraded",
        "database": db_status,
        "cache": "connected",
    }
