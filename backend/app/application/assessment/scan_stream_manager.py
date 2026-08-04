"""Application Service managing active WebSocket client connection lifecycle, heartbeat tracking, and event fanout."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket, status

from app.core.exceptions import ForbiddenException
from app.core.logging import get_logger
from app.domain.entities.scan_stream import WebSocketConnectionParams
from app.infrastructure.workers.redis_pubsub_manager import RedisPubSubManager

logger = get_logger("vulnova.scan_stream_manager")

# Rate Limiting & Connection Safeguards (Phase 6.4)
MAX_CONNECTIONS_PER_ORG = 50
HEARTBEAT_INTERVAL_SECONDS = 30
CONNECTION_TIMEOUT_SECONDS = 90

# WebSocket Custom Close Codes
WS_CLOSE_UNAUTHORIZED = 4001
WS_CLOSE_FORBIDDEN = 4003
WS_CLOSE_NOT_FOUND = 4004
WS_CLOSE_LIMIT_EXCEEDED = 4008


class ScanStreamManagerService:
    """Manages active WebSocket connections per tenant/scan and forwards Redis Pub/Sub events."""

    def __init__(self, pubsub_manager: Optional[RedisPubSubManager] = None) -> None:
        self.pubsub = pubsub_manager or RedisPubSubManager()
        # organization_id -> scan_id -> Set of (WebSocket, last_active_datetime)
        self._connections: Dict[UUID, Dict[UUID, Set[WebSocket]]] = {}
        self._connection_meta: Dict[WebSocket, WebSocketConnectionParams] = {}
        self._last_active: Dict[WebSocket, datetime] = {}
        self._lock = asyncio.Lock()

    def get_organization_connection_count(self, organization_id: UUID) -> int:
        """Count total active WebSocket connections for a given organization."""
        org_map = self._connections.get(organization_id, {})
        return sum(len(sockets) for sockets in org_map.values())

    async def connect(
        self, websocket: WebSocket, params: WebSocketConnectionParams
    ) -> None:
        """Register a new authenticated WebSocket client connection under organization and scan_id.

        Raises:
            ForbiddenException: If organization connection count exceeds MAX_CONNECTIONS_PER_ORG.
        """
        async with self._lock:
            current_org_count = self.get_organization_connection_count(
                params.organization_id
            )
            if current_org_count >= MAX_CONNECTIONS_PER_ORG:
                logger.warning(
                    "scan_stream.max_connections_exceeded",
                    org_id=str(params.organization_id),
                    current_count=current_org_count,
                    max_allowed=MAX_CONNECTIONS_PER_ORG,
                )
                raise ForbiddenException(
                    f"Organization connection limit ({MAX_CONNECTIONS_PER_ORG}) reached."
                )

            await websocket.accept()

            if params.organization_id not in self._connections:
                self._connections[params.organization_id] = {}
            if params.scan_id not in self._connections[params.organization_id]:
                self._connections[params.organization_id][params.scan_id] = set()

            self._connections[params.organization_id][params.scan_id].add(websocket)
            self._connection_meta[websocket] = params
            self._last_active[websocket] = datetime.now(timezone.utc)

            logger.info(
                "scan_stream.client_connected",
                org_id=str(params.organization_id),
                scan_id=str(params.scan_id),
                user_id=str(params.user_id),
            )

    async def disconnect(
        self, websocket: WebSocket, params: Optional[WebSocketConnectionParams] = None
    ) -> None:
        """Unregister WebSocket connection cleanly."""
        async with self._lock:
            meta = params or self._connection_meta.get(websocket)
            if meta:
                org_id = meta.organization_id
                scan_id = meta.scan_id
                if org_id in self._connections and scan_id in self._connections[org_id]:
                    self._connections[org_id][scan_id].discard(websocket)
                    if not self._connections[org_id][scan_id]:
                        del self._connections[org_id][scan_id]
                    if not self._connections[org_id]:
                        del self._connections[org_id]

            self._connection_meta.pop(websocket, None)
            self._last_active.pop(websocket, None)

            logger.info("scan_stream.client_disconnected")

    def update_last_active(self, websocket: WebSocket) -> None:
        """Update last active timestamp for a WebSocket connection upon frame receipt."""
        self._last_active[websocket] = datetime.now(timezone.utc)

    async def broadcast_to_scan(
        self, organization_id: UUID, scan_id: UUID, message_json: str
    ) -> None:
        """Send JSON payload to all active WebSocket connections for a specific scan."""
        async with self._lock:
            sockets = (
                self._connections.get(organization_id, {}).get(scan_id, set()).copy()
            )

        dead_sockets: Set[WebSocket] = set()
        for ws in sockets:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.debug("scan_stream.send_failed", error=str(e))
                dead_sockets.add(ws)

        for ws in dead_sockets:
            await self.disconnect(ws)

    async def prune_stale_connections(self) -> int:
        """Identify and close connections inactive for longer than CONNECTION_TIMEOUT_SECONDS."""
        now = datetime.now(timezone.utc)
        stale_sockets: Set[WebSocket] = set()

        async with self._lock:
            for ws, last_time in list(self._last_active.items()):
                idle_seconds = (now - last_time).total_seconds()
                if idle_seconds > CONNECTION_TIMEOUT_SECONDS:
                    stale_sockets.add(ws)

        for ws in stale_sockets:
            try:
                await ws.close(
                    code=status.WS_1000_NORMAL_CLOSURE,
                    reason="Connection timed out due to inactivity",
                )
            except Exception as e:
                logger.debug("scan_stream.ws_close_failed", error=str(e))
            await self.disconnect(ws)

        if stale_sockets:
            logger.info(
                "scan_stream.pruned_stale_connections", count=len(stale_sockets)
            )
        return len(stale_sockets)
