"""Distributed Rate Limiter implementing Redis-backed Token Bucket / Sliding Window Algorithm."""

import time
from dataclasses import dataclass
from typing import Optional

import structlog

from app.infrastructure.cache.redis_client import RedisClientManager, redis_manager

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitResult:
    """Result of rate limit evaluation."""

    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int
    identifier: str


class DistributedRateLimiter:
    """Redis-backed distributed rate limiter with support for IP, User, and Organization buckets."""

    # Default Rate Limit Thresholds (requests per 60 seconds)
    DEFAULT_ANONYMOUS_LIMIT = 100
    DEFAULT_AUTHENTICATED_LIMIT = 1000
    DEFAULT_ADMIN_LIMIT = 5000
    WINDOW_SECONDS = 60

    def __init__(self, manager: Optional[RedisClientManager] = None) -> None:
        self.manager = manager or redis_manager
        self._fallback_counts: dict[str, tuple[int, float]] = {}

    async def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "ip",
        custom_limit: Optional[int] = None,
        role: str = "VIEWER",
    ) -> RateLimitResult:
        """Evaluate rate limit bucket for IP, User, or Organization using atomic Redis operations."""
        # Determine maximum allowed limit
        if custom_limit is not None:
            limit = custom_limit
        elif role in ["ADMIN", "SYSTEM"]:
            limit = self.DEFAULT_ADMIN_LIMIT
        elif limit_type == "user":
            limit = self.DEFAULT_AUTHENTICATED_LIMIT
        else:
            limit = self.DEFAULT_ANONYMOUS_LIMIT

        key = f"rate_limit:{limit_type}:{identifier}"
        client = await self.manager.get_client()

        if client is not None:
            try:
                # Atomic pipeline execution
                pipe = client.pipeline()
                pipe.incr(key)
                pipe.ttl(key)
                current_count, ttl = await pipe.execute()

                # Set expiration on fresh bucket creation
                if ttl == -1:
                    await client.expire(key, self.WINDOW_SECONDS)
                    ttl = self.WINDOW_SECONDS

                reset = max(ttl, 1)
                remaining = max(0, limit - current_count)
                allowed = current_count <= limit

                if not allowed:
                    logger.warning(
                        "rate_limit_exceeded",
                        identifier=identifier,
                        limit_type=limit_type,
                        count=current_count,
                        limit=limit,
                    )

                return RateLimitResult(
                    allowed=allowed,
                    limit=limit,
                    remaining=remaining,
                    reset_seconds=reset,
                    identifier=identifier,
                )
            except Exception as err:
                logger.warning("rate_limiter_redis_error_falling_back", error=str(err))

        # Graceful fallback logic when Redis is offline
        now = time.time()
        count, reset_at = self._fallback_counts.get(key, (0, now + self.WINDOW_SECONDS))
        if now > reset_at:
            count = 0
            reset_at = now + self.WINDOW_SECONDS

        count += 1
        self._fallback_counts[key] = (count, reset_at)
        remaining = max(0, limit - count)
        reset_secs = int(max(1, reset_at - now))

        return RateLimitResult(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            reset_seconds=reset_secs,
            identifier=identifier,
        )


# Global singleton instance
rate_limiter = DistributedRateLimiter()
