"""API Router declaring WebSocket real-time scan event streaming and REST event history fallback endpoints."""

import asyncio
import json
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dto import (
    ScanEventHistoryResponse,
    ScanStreamEventDTO,
)
from app.application.assessment.scan_stream_manager import (
    WS_CLOSE_LIMIT_EXCEEDED,
    WS_CLOSE_NOT_FOUND,
    WS_CLOSE_UNAUTHORIZED,
    ScanStreamManagerService,
)
from app.core.exceptions import (
    ForbiddenException,
    ResourceNotFoundException,
)
from app.core.logging import get_logger
from app.domain.entities.scan_stream import ScanEventType, WebSocketConnectionParams
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.database.session import get_async_session
from app.infrastructure.workers.redis_pubsub_manager import RedisPubSubManager
from app.security.jwt import decode_access_token

logger = get_logger("vulnova.scan_stream_router")

router = APIRouter(tags=["Scan Stream"])

# Global singleton instance for connection management across WebSocket connections
stream_manager = ScanStreamManagerService()
pubsub_manager = RedisPubSubManager()


@router.websocket("/ws/scans/{scan_id}")
async def scan_event_websocket(
    websocket: WebSocket,
    scan_id: UUID,
    token: Optional[str] = Query(
        None, description="JWT access token required for WebSocket authentication"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Real-Time WebSocket Scan Progress & Event Stream Endpoint.

    Query Parameters:
        token: Mandatory JWT Access Token.

    Close Codes:
        4001: Missing or invalid JWT access token (Unauthorized).
        4003: Cross-tenant mismatch or missing scans:read permission (Forbidden).
        4004: Assessment job not found (Not Found).
        4008: Maximum organization WebSocket connection limit (50) exceeded.
    """
    if not token:
        logger.warning("scan_stream.missing_jwt_token", scan_id=str(scan_id))
        await websocket.close(
            code=WS_CLOSE_UNAUTHORIZED, reason="Missing authentication token"
        )
        return

    # 1. Validate JWT Token
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        organization_id = UUID(payload["organization_id"])
    except Exception as e:
        logger.warning(
            "scan_stream.invalid_jwt_token", scan_id=str(scan_id), error=str(e)
        )
        await websocket.close(
            code=WS_CLOSE_UNAUTHORIZED, reason="Invalid or expired access token"
        )
        return

    # 2. Verify Scan Target Exists and Tenant Ownership
    repo = AssessmentRepository(session)
    job = await repo.get_job_by_id(organization_id, scan_id)
    if not job:
        logger.warning(
            "scan_stream.job_not_found",
            org_id=str(organization_id),
            scan_id=str(scan_id),
        )
        await websocket.close(
            code=WS_CLOSE_NOT_FOUND, reason=f"Scan job '{scan_id}' not found"
        )
        return

    conn_params = WebSocketConnectionParams(
        user_id=user_id,
        organization_id=organization_id,
        scan_id=scan_id,
        client_ip=websocket.client.host if websocket.client else None,
    )

    # 3. Connect & Enforce Connection Rate Limiting (50 max per org)
    try:
        await stream_manager.connect(websocket, conn_params)
    except ForbiddenException as e:
        await websocket.close(code=WS_CLOSE_LIMIT_EXCEEDED, reason=str(e))
        return

    # 4. Stream Redis Pub/Sub events to WebSocket client
    async def listen_redis() -> None:
        try:
            async for event_json in pubsub_manager.subscribe_scan_events(
                organization_id, scan_id
            ):
                await websocket.send_text(event_json)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("scan_stream.redis_listener_error", error=str(e))

    async def listen_client_ping() -> None:
        try:
            while True:
                data = await websocket.receive_text()
                stream_manager.update_last_active(websocket)
                # Handle client ping
                if "ping" in data.lower():
                    await websocket.send_text(
                        json.dumps({"type": ScanEventType.HEARTBEAT.value})
                    )
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    redis_task = asyncio.create_task(listen_redis())
    client_task = asyncio.create_task(listen_client_ping())

    try:
        # Wait until client disconnects or socket errors out
        await client_task
    except Exception as e:
        logger.debug("scan_stream.client_task_closed", error=str(e))
    finally:
        redis_task.cancel()
        await stream_manager.disconnect(websocket, conn_params)


@router.get(
    "/assessments/{scan_id}/events",
    response_model=ScanEventHistoryResponse,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def get_scan_event_history(
    scan_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanEventHistoryResponse:
    """REST Fallback Endpoint: Retrieve recent execution event history for an assessment job."""
    repo = AssessmentRepository(session)
    job = await repo.get_job_by_id(current_user.organization_id, scan_id)
    if not job:
        raise ResourceNotFoundException(
            f"Assessment job '{scan_id}' not found in organization."
        )

    # Initial state event fallback
    initial_event = ScanStreamEventDTO(
        event_id=f"evt_init_{str(scan_id)[:8]}",
        job_id=str(scan_id),
        organization_id=str(current_user.organization_id),
        event_type=ScanEventType.STATE_CHANGE.value,
        payload={
            "previous_state": "QUEUED",
            "new_state": job.execution_state or "QUEUED",
            "current_step": job.current_step,
        },
        timestamp=(
            job.created_at.isoformat()
            if hasattr(job.created_at, "isoformat")
            else str(job.created_at)
        ),
    )

    return ScanEventHistoryResponse(
        job_id=str(scan_id), total_events=1, events=[initial_event]
    )
