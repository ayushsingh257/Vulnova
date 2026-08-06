"""FastAPI System Health, Readiness, Liveness, and Prometheus Metrics Router."""

import time
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse

from app.infrastructure.cache.redis_client import redis_manager
from app.infrastructure.database.session import check_database_connection
from app.infrastructure.observability.metrics.metrics_service import metrics_service

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["System Health & Observability"])

# Record process startup time
START_TIME = time.time()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Prometheus Operational Metrics",
    description="Exposes application, database, cache, and security audit metrics formatted in standard Prometheus exposition text.",
)
async def get_prometheus_metrics() -> Response:
    """Return Prometheus text format metrics."""
    text_content = metrics_service.generate_prometheus_text()
    return PlainTextResponse(
        content=text_content, media_type="text/plain; version=0.0.4"
    )


@router.get(
    "/api/v1/system/health",
    status_code=status.HTTP_200_OK,
    summary="System Operational Health Summary",
    description="Provides detailed operational health status of database, Redis cache, and background workers.",
)
async def get_system_health() -> Dict[str, Any]:
    """Return comprehensive system health telemetry."""
    db_healthy = await check_database_connection()
    redis_healthy = await redis_manager.is_healthy()
    uptime_seconds = round(time.time() - START_TIME, 2)

    overall_status = "HEALTHY" if (db_healthy and redis_healthy) else "DEGRADED"

    return {
        "status": overall_status,
        "version": "0.1.0-alpha",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "dependencies": {
            "database": "CONNECTED" if db_healthy else "UNREACHABLE",
            "redis": "CONNECTED" if redis_healthy else "DEGRADED_FALLBACK",
            "metrics": "ACTIVE",
        },
    }


@router.get(
    "/api/v1/system/readiness",
    status_code=status.HTTP_200_OK,
    summary="Service Readiness Probe",
    description="Kubernetes readiness probe returning 200 OK when database and dependencies are ready.",
)
async def get_system_readiness(response: Response) -> Dict[str, Any]:
    """Probe if application is ready to accept incoming traffic."""
    db_ready = await check_database_connection()
    if not db_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "UNREADY", "reason": "Database connection unavailable"}
    return {"status": "READY", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get(
    "/api/v1/system/liveness",
    status_code=status.HTTP_200_OK,
    summary="Service Liveness Probe",
    description="Kubernetes liveness probe returning 200 OK to indicate process vitality.",
)
async def get_system_liveness() -> Dict[str, str]:
    """Probe if application process is alive."""
    return {"status": "ALIVE", "ping": "pong"}
