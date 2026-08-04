"""Redis Pub/Sub Manager for broadcasting and subscribing to real-time scan execution events."""

import asyncio
import json
from typing import AsyncGenerator, Dict, List, Optional
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.entities.scan_stream import ScanStreamEvent

logger = get_logger("vulnova.redis_pubsub")

# Connection & Safeguard Constants (Phase 6.4)
MAX_EVENT_PAYLOAD_SIZE = 64 * 1024  # 64KB Max Payload Limit


class RedisPubSubManager:
    """Infrastructure Manager handling Redis Pub/Sub channels for scan execution event fanout."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url: str = str(
            redis_url
            or getattr(settings, "REDIS_URL", None)
            or "redis://localhost:6379/0"
        )
        self._redis_client: Optional[object] = None
        # Offline in-memory Pub/Sub subscriber queues for fallback & unit testing
        self._in_memory_subscribers: Dict[str, List[asyncio.Queue[str]]] = {}

    def get_channel_name(self, organization_id: UUID, scan_id: UUID) -> str:
        """Construct Redis Pub/Sub channel key for an organization's scan job."""
        return f"vulnova:scan:events:{organization_id}:{scan_id}"

    async def _get_redis_client(self) -> Optional[object]:
        """Lazy-initialize async Redis client if redis-py is available."""
        if self._redis_client is not None:
            return self._redis_client
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(  # type: ignore[no-untyped-call]
                self.redis_url, decode_responses=True, socket_timeout=2.0
            )
            await client.ping()
            self._redis_client = client
            return self._redis_client
        except Exception as e:
            logger.debug("redis_pubsub.fallback_in_memory", error=str(e))
            return None

    async def publish_scan_event(
        self, organization_id: UUID, scan_id: UUID, event: ScanStreamEvent
    ) -> bool:
        """Publish a ScanStreamEvent to the target Redis Pub/Sub channel.

        Raises:
            ValueError: If serialized event payload exceeds MAX_EVENT_PAYLOAD_SIZE (64KB).
        """
        channel = self.get_channel_name(organization_id, scan_id)
        raw_json = json.dumps(event.to_dict())

        # Connection Safeguard: Payload Size Validation
        payload_bytes = len(raw_json.encode("utf-8"))
        if payload_bytes > MAX_EVENT_PAYLOAD_SIZE:
            logger.error(
                "redis_pubsub.payload_too_large",
                channel=channel,
                size_bytes=payload_bytes,
                max_bytes=MAX_EVENT_PAYLOAD_SIZE,
            )
            raise ValueError(
                f"Event payload size ({payload_bytes} bytes) exceeds MAX_EVENT_PAYLOAD_SIZE limit of {MAX_EVENT_PAYLOAD_SIZE} bytes."
            )

        client = await self._get_redis_client()
        if client is not None:
            try:
                await client.publish(channel, raw_json)  # type: ignore[attr-defined]
                logger.debug(
                    "redis_pubsub.event_published_redis",
                    channel=channel,
                    event_type=event.event_type.value,
                )
                return True
            except Exception as e:
                logger.warning(
                    "redis_pubsub.redis_publish_error_fallback",
                    channel=channel,
                    error=str(e),
                )

        # Fallback to in-memory event queues
        queues = self._in_memory_subscribers.get(channel, [])
        for q in queues:
            await q.put(raw_json)
        logger.debug(
            "redis_pubsub.event_published_in_memory",
            channel=channel,
            subscribers_count=len(queues),
        )
        return True

    async def subscribe_scan_events(
        self, organization_id: UUID, scan_id: UUID
    ) -> AsyncGenerator[str, None]:
        """Subscribe to scan events and yield JSON event strings."""
        channel = self.get_channel_name(organization_id, scan_id)
        client = await self._get_redis_client()

        if client is not None:
            pubsub = client.pubsub()  # type: ignore[attr-defined]
            await pubsub.subscribe(channel)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        yield str(message["data"])
            finally:
                await pubsub.unsubscribe(channel)
        else:
            # Fallback using in-memory Queue
            q: asyncio.Queue[str] = asyncio.Queue()
            if channel not in self._in_memory_subscribers:
                self._in_memory_subscribers[channel] = []
            self._in_memory_subscribers[channel].append(q)
            try:
                while True:
                    event_json = await q.get()
                    yield event_json
            finally:
                if channel in self._in_memory_subscribers:
                    self._in_memory_subscribers[channel].remove(q)

    async def clear_in_memory_subscribers(self) -> None:
        """Clear all in-memory subscriber queues (for unit testing)."""
        self._in_memory_subscribers.clear()
