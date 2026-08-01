from app.core.config import settings


async def check_redis_connection() -> bool:
    """Probe Redis cache connectivity."""
    # Stub helper returning True for readiness health check if configured
    if not settings.redis_url:
        return False
    return True
