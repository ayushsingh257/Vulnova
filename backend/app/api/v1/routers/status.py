from typing import Any, Dict

from fastapi import APIRouter, status

from app.core.config import settings
from app.infrastructure.database.session import check_database_connection

router = APIRouter(prefix="/status", tags=["System Status"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_v1_status() -> Dict[str, Any]:
    """Retrieve API v1 operational status metadata."""
    is_db_connected = await check_database_connection()

    return {
        "api_version": "v1",
        "status": "operational" if is_db_connected else "degraded",
        "environment": settings.environment,
        "services": {
            "database": "connected" if is_db_connected else "disconnected",
            "cache": "connected",
        },
    }
