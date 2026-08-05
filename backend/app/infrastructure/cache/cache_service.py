"""Generic Cache Service abstraction offering JSON serialization, TTL management, and pattern invalidation."""

import json
from typing import Any, List, Optional

import structlog

from app.infrastructure.cache.redis_client import RedisClientManager, redis_manager

logger = structlog.get_logger(__name__)


class CacheService:
    """Enterprise Async Cache Service with Redis primary storage and fallback support."""

    def __init__(self, manager: Optional[RedisClientManager] = None) -> None:
        self.manager = manager or redis_manager
        self._fallback_store: dict[str, Any] = {}

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in cache with optional TTL in seconds."""
        client = await self.manager.get_client()
        serialized = json.dumps(value) if not isinstance(value, str) else value

        if client is not None:
            try:
                if ttl:
                    await client.setex(key, ttl, serialized)
                else:
                    await client.set(key, serialized)
                return True
            except Exception as err:
                logger.warning("cache_set_error_falling_back", key=key, error=str(err))

        # Fallback to local memory dictionary
        self._fallback_store[key] = serialized
        return True

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache and deserialize JSON if applicable."""
        client = await self.manager.get_client()

        if client is not None:
            try:
                data = await client.get(key)
                if data is not None:
                    return self._deserialize(data)
            except Exception as err:
                logger.warning("cache_get_error_falling_back", key=key, error=str(err))

        # Fallback check
        if key in self._fallback_store:
            return self._deserialize(self._fallback_store[key])

        return None

    async def delete(self, key: str) -> bool:
        """Remove single key from cache."""
        client = await self.manager.get_client()
        self._fallback_store.pop(key, None)

        if client is not None:
            try:
                res = await client.delete(key)
                return bool(res > 0)
            except Exception as err:
                logger.warning("cache_delete_error", key=key, error=str(err))

        return True

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = await self.manager.get_client()

        if client is not None:
            try:
                res = await client.exists(key)
                return bool(res > 0)
            except Exception as err:
                logger.warning("cache_exists_error", key=key, error=str(err))

        return key in self._fallback_store

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching wildcards (e.g., 'tenant:123:*')."""
        client = await self.manager.get_client()
        count = 0

        if client is not None:
            try:
                keys: List[str] = []
                async for k in client.scan_iter(match=pattern):
                    keys.append(k)
                if keys:
                    deleted = await client.delete(*keys)
                    count = int(deleted)
                    logger.info(
                        "cache_pattern_invalidated", pattern=pattern, count=count
                    )
                return count
            except Exception as err:
                logger.warning(
                    "cache_invalidate_pattern_error", pattern=pattern, error=str(err)
                )

        # Fallback pattern match
        import fnmatch

        to_remove = [k for k in self._fallback_store if fnmatch.fnmatch(k, pattern)]
        for k in to_remove:
            self._fallback_store.pop(k, None)
            count += 1

        return count

    def _deserialize(self, raw: str) -> Any:
        """Safely deserialize JSON or return string as-is."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw


# Global singleton instance
cache_service = CacheService()
