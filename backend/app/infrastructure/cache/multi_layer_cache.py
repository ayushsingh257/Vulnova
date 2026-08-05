"""Multi-Layer Caching Strategy for Tenant Metadata, User Sessions, and System Configurations."""

from typing import Any, Dict, Optional

import structlog

from app.infrastructure.cache.cache_service import CacheService, cache_service

logger = structlog.get_logger(__name__)

# TTL Constants (in seconds)
TENANT_CACHE_TTL = 900  # 15 minutes
USER_SESSION_CACHE_TTL = 1800  # 30 minutes
STATIC_CONFIG_CACHE_TTL = 3600  # 1 hour


class MultiLayerCacheManager:
    """Orchestrates structured tenant, user session, and static config caching strategies."""

    def __init__(self, service: Optional[CacheService] = None) -> None:
        self.service = service or cache_service

    # --- A) Tenant Lookup Cache ---
    async def get_tenant(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Fetch cached organization metadata and settings."""
        key = f"tenant:{organization_id}"
        return await self.service.get(key)

    async def set_tenant(
        self, organization_id: str, tenant_data: Dict[str, Any]
    ) -> bool:
        """Cache organization metadata for 15 minutes."""
        key = f"tenant:{organization_id}"
        return await self.service.set(key, tenant_data, ttl=TENANT_CACHE_TTL)

    async def invalidate_tenant(self, organization_id: str) -> int:
        """Invalidate tenant cache and any tenant-scoped subkeys."""
        pattern = f"tenant:{organization_id}*"
        return await self.service.invalidate_pattern(pattern)

    # --- B) User Session Cache ---
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch cached user session, role, and permission data."""
        key = f"session:{user_id}"
        return await self.service.get(key)

    async def set_user_session(
        self, user_id: str, session_data: Dict[str, Any]
    ) -> bool:
        """Cache user session data for 30 minutes."""
        key = f"session:{user_id}"
        return await self.service.set(key, session_data, ttl=USER_SESSION_CACHE_TTL)

    async def invalidate_user_session(self, user_id: str) -> bool:
        """Invalidate single user session."""
        key = f"session:{user_id}"
        return await self.service.delete(key)

    # --- C) Static Configuration Cache ---
    async def get_config(self, config_key: str) -> Optional[Any]:
        """Fetch cached system config or security policy."""
        key = f"config:{config_key}"
        return await self.service.get(key)

    async def set_config(self, config_key: str, config_value: Any) -> bool:
        """Cache static configuration for 1 hour."""
        key = f"config:{config_key}"
        return await self.service.set(key, config_value, ttl=STATIC_CONFIG_CACHE_TTL)

    async def invalidate_config(self, config_key: Optional[str] = None) -> int:
        """Invalidate specific config or all system configs."""
        if config_key:
            key = f"config:{config_key}"
            await self.service.delete(key)
            return 1
        return await self.service.invalidate_pattern("config:*")


# Global singleton instance
multi_layer_cache = MultiLayerCacheManager()
