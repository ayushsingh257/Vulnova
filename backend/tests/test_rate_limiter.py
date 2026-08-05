"""Unit and Integration Test Suite for DistributedRateLimiter & RateLimitMiddleware."""

import pytest
from starlette.testclient import TestClient

from app.infrastructure.cache.redis_client import RedisClientManager
from app.infrastructure.rate_limit.distributed_rate_limiter import (
    DistributedRateLimiter,
)
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_token_bucket_behavior() -> None:
    """Verify rate limiter allows requests up to bucket limit and blocks excess."""
    client_manager = RedisClientManager(redis_url="redis://invalid_host:6379/0")
    client_manager._is_available = False
    limiter = DistributedRateLimiter(manager=client_manager)

    identifier = "192.168.1.50"
    custom_limit = 3

    res1 = await limiter.check_rate_limit(
        identifier, limit_type="ip", custom_limit=custom_limit
    )
    res2 = await limiter.check_rate_limit(
        identifier, limit_type="ip", custom_limit=custom_limit
    )
    res3 = await limiter.check_rate_limit(
        identifier, limit_type="ip", custom_limit=custom_limit
    )
    res4 = await limiter.check_rate_limit(
        identifier, limit_type="ip", custom_limit=custom_limit
    )

    assert res1.allowed is True
    assert res1.remaining == 2

    assert res2.allowed is True
    assert res2.remaining == 1

    assert res3.allowed is True
    assert res3.remaining == 0

    assert res4.allowed is False
    assert res4.remaining == 0


@pytest.mark.anyio
async def test_user_and_role_limits() -> None:
    """Verify role-based rate limit thresholds (ADMIN vs VIEWER vs Anonymous)."""
    client_manager = RedisClientManager(redis_url="redis://invalid_host:6379/0")
    limiter = DistributedRateLimiter(manager=client_manager)

    user_res = await limiter.check_rate_limit(
        "user_10", limit_type="user", role="VIEWER"
    )
    admin_res = await limiter.check_rate_limit(
        "admin_99", limit_type="user", role="ADMIN"
    )

    assert user_res.limit == DistributedRateLimiter.DEFAULT_AUTHENTICATED_LIMIT
    assert admin_res.limit == DistributedRateLimiter.DEFAULT_ADMIN_LIMIT


def test_rate_limit_middleware_headers() -> None:
    """Verify FastAPI requests include X-RateLimit headers."""
    client = TestClient(app)
    response = client.get("/health")
    # Exempt endpoints pass through cleanly
    assert response.status_code == 200

    api_res = client.get("/api/v1/status")
    assert api_res.status_code == 200
    assert "X-RateLimit-Limit" in api_res.headers
    assert "X-RateLimit-Remaining" in api_res.headers
    assert "X-RateLimit-Reset" in api_res.headers
