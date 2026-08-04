"""Distributed Redis Lock Manager preventing duplicate concurrent scan executions on identical targets."""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities.scan_lifecycle import ScanLockMetadata
from app.infrastructure.workers.celery_config import broker_url

logger = get_logger("vulnova.scan_lock_manager")


class DistributedScanLockManager:
    """Manages atomic Redis distributed locks preventing duplicate concurrent scan executions.

    Lock Key Format: ``lock:scan:{organization_id}:{target_url_sha256}``
    Uses Redis TTL auto-expiry and fallback in-memory registry for unit testing without active Redis.
    """

    _in_memory_locks: Dict[str, Tuple[ScanLockMetadata, float]] = {}

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or broker_url
        self._redis_client: Optional[object] = None

    def _generate_lock_key(self, organization_id: UUID, target_url: str) -> str:
        """Compute deterministic SHA-256 lock key from org_id and target_url."""
        normalized_url = target_url.strip().rstrip("/").lower()
        url_hash = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:16]
        return f"lock:scan:{organization_id}:{url_hash}"

    async def _get_redis_client(self) -> Optional[object]:
        """Lazy-initialize async Redis client if redis-py is available."""
        if self._redis_client is not None:
            return self._redis_client
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(  # type: ignore[no-untyped-call]
                self.redis_url, decode_responses=True, socket_timeout=2.0
            )
            # Test ping
            await client.ping()
            self._redis_client = client
            return self._redis_client
        except Exception as e:
            logger.debug(
                "scan_lock.redis_connection_fallback",
                reason=str(e),
                note="Using in-memory lock manager for test/standalone mode",
            )
            return None

    async def acquire_lock(
        self,
        organization_id: UUID,
        target_url: str,
        ttl_seconds: int = 3600,
        owner_id: str = "",
    ) -> bool:
        """Acquire atomic lock for target URL within tenant organization.

        Returns:
            True if lock was successfully acquired, False if target is already locked.
        """
        lock_key = self._generate_lock_key(organization_id, target_url)
        client = await self._get_redis_client()

        if client is not None:
            try:
                # Redis SETNX with EX
                acquired = await client.set(  # type: ignore[attr-defined]
                    lock_key, owner_id or "locked", nx=True, ex=ttl_seconds
                )
                if acquired:
                    logger.info(
                        "scan_lock.acquired_redis",
                        lock_key=lock_key,
                        org_id=str(organization_id),
                        ttl=ttl_seconds,
                    )
                    return True
                else:
                    logger.warning(
                        "scan_lock.collision_redis",
                        lock_key=lock_key,
                        org_id=str(organization_id),
                    )
                    return False
            except Exception as e:
                logger.warning("scan_lock.redis_error_fallback", error=str(e))

        # In-memory fallback
        now_ts = datetime.now(timezone.utc).timestamp()
        if lock_key in self._in_memory_locks:
            meta, expiry_ts = self._in_memory_locks[lock_key]
            if now_ts < expiry_ts:
                logger.warning(
                    "scan_lock.collision_in_memory",
                    lock_key=lock_key,
                    org_id=str(organization_id),
                )
                return False

        # Acquire in-memory lock
        meta = ScanLockMetadata(
            lock_key=lock_key,
            organization_id=organization_id,
            target_url=target_url,
            acquired_at=datetime.now(timezone.utc),
            ttl_seconds=ttl_seconds,
            owner_id=owner_id,
        )
        self._in_memory_locks[lock_key] = (meta, now_ts + ttl_seconds)
        logger.info(
            "scan_lock.acquired_in_memory",
            lock_key=lock_key,
            org_id=str(organization_id),
            ttl=ttl_seconds,
        )
        return True

    async def release_lock(self, organization_id: UUID, target_url: str) -> bool:
        """Release distributed lock for target URL."""
        lock_key = self._generate_lock_key(organization_id, target_url)
        client = await self._get_redis_client()

        if client is not None:
            try:
                deleted = await client.delete(lock_key)  # type: ignore[attr-defined]
                if deleted > 0:
                    logger.info(
                        "scan_lock.released_redis",
                        lock_key=lock_key,
                        org_id=str(organization_id),
                    )
                    return True
            except Exception as e:
                logger.warning("scan_lock.release_redis_error", error=str(e))

        # In-memory release
        if lock_key in self._in_memory_locks:
            del self._in_memory_locks[lock_key]
            logger.info(
                "scan_lock.released_in_memory",
                lock_key=lock_key,
                org_id=str(organization_id),
            )
            return True
        return False

    async def is_locked(self, organization_id: UUID, target_url: str) -> bool:
        """Check if target URL is currently locked."""
        lock_key = self._generate_lock_key(organization_id, target_url)
        client = await self._get_redis_client()

        if client is not None:
            try:
                exists = await client.exists(lock_key)  # type: ignore[attr-defined]
                return bool(exists > 0)
            except Exception as e:
                logger.warning("scan_lock.exists_redis_error", error=str(e))

        now_ts = datetime.now(timezone.utc).timestamp()
        if lock_key in self._in_memory_locks:
            _, expiry_ts = self._in_memory_locks[lock_key]
            if now_ts < expiry_ts:
                return True
            else:
                del self._in_memory_locks[lock_key]
        return False

    async def clear_all_locks(self) -> None:
        """Utility function to clear in-memory locks (used for test teardown)."""
        self._in_memory_locks.clear()
