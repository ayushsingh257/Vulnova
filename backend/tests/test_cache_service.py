"""Unit and Integration Test Suite for CacheService and MultiLayerCacheManager."""

import pytest

from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.cache.multi_layer_cache import MultiLayerCacheManager
from app.infrastructure.cache.redis_client import RedisClientManager


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_cache_set_get_delete() -> None:
    """Verify basic set, get, exists, and delete operations with fallback store."""
    client_manager = RedisClientManager(redis_url="redis://invalid_host:6379/0")
    client_manager._is_available = False
    service = CacheService(manager=client_manager)

    key = "test_key_1"
    val = {"name": "Vulnova Tenant", "plan": "ENTERPRISE"}

    assert await service.set(key, val, ttl=300) is True
    assert await service.exists(key) is True

    cached_val = await service.get(key)
    assert cached_val == val

    assert await service.delete(key) is True
    assert await service.exists(key) is False


@pytest.mark.anyio
async def test_cache_invalidate_pattern() -> None:
    """Verify pattern-based cache invalidation."""
    client_manager = RedisClientManager(redis_url="redis://invalid_host:6379/0")
    client_manager._is_available = False
    service = CacheService(manager=client_manager)

    await service.set("tenant:org123:meta", {"id": "org123"})
    await service.set("tenant:org123:settings", {"mfa": True})
    await service.set("tenant:org456:meta", {"id": "org456"})

    invalidated = await service.invalidate_pattern("tenant:org123:*")
    assert invalidated == 2

    assert await service.get("tenant:org123:meta") is None
    assert await service.get("tenant:org123:settings") is None
    assert await service.get("tenant:org456:meta") is not None


@pytest.mark.anyio
async def test_multi_layer_cache_manager() -> None:
    """Verify MultiLayerCacheManager tenant, session, and static config workflows."""
    client_manager = RedisClientManager(redis_url="redis://invalid_host:6379/0")
    client_manager._is_available = False
    service = CacheService(manager=client_manager)
    multi_cache = MultiLayerCacheManager(service=service)

    # Tenant caching
    org_id = "org_test_77"
    org_data = {"id": org_id, "name": "Acme Corp"}
    await multi_cache.set_tenant(org_id, org_data)
    assert await multi_cache.get_tenant(org_id) == org_data
    await multi_cache.invalidate_tenant(org_id)
    assert await multi_cache.get_tenant(org_id) is None

    # User session caching
    user_id = "user_test_99"
    sess_data = {"user_id": user_id, "role": "ADMIN"}
    await multi_cache.set_user_session(user_id, sess_data)
    assert await multi_cache.get_user_session(user_id) == sess_data
    await multi_cache.invalidate_user_session(user_id)
    assert await multi_cache.get_user_session(user_id) is None

    # Config caching
    config_key = "feature_flags"
    config_val = {"mfa_required": True}
    await multi_cache.set_config(config_key, config_val)
    assert await multi_cache.get_config(config_key) == config_val
    await multi_cache.invalidate_config(config_key)
    assert await multi_cache.get_config(config_key) is None
