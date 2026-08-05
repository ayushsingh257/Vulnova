"""Enterprise Redis Connection Manager with Connection Pooling, Health Probing and Graceful Degradation."""

from typing import Optional

import redis.asyncio as aioredis
import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RedisClientManager:
    """Manages Async Redis client instance, connection pooling, and error resilience."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or settings.redis_url
        self._redis_client: Optional[Redis] = None
        self._is_available: bool = True

    async def get_client(self) -> Optional[Redis]:
        """Return active Redis client instance with lazy initialization."""
        if not self._is_available:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = aioredis.from_url(  # type: ignore[no-untyped-call]
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                    socket_timeout=3.0,
                    socket_connect_timeout=3.0,
                )
                await self._redis_client.ping()
                self._is_available = True
                logger.info("redis_connection_established", url=self.redis_url)
            except (RedisError, Exception) as err:
                self._is_available = False
                self._redis_client = None
                logger.warning(
                    "redis_connection_failed_graceful_degradation", error=str(err)
                )
                return None

        return self._redis_client

    async def is_healthy(self) -> bool:
        """Check if Redis server is reachable via PING."""
        client = await self.get_client()
        if client is None:
            return False
        try:
            res = await client.ping()
            return bool(res)
        except Exception:
            self._is_available = False
            return False

    async def close(self) -> None:
        """Close active Redis connections."""
        if self._redis_client is not None:
            try:
                await self._redis_client.close()
                logger.info("redis_connection_closed")
            except Exception as err:
                logger.warning("redis_close_error", error=str(err))
            finally:
                self._redis_client = None


# Global singleton instance
redis_manager = RedisClientManager()
