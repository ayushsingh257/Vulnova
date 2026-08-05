"""REST API Router for Slack & Microsoft Teams Security Alert Webhooks."""

from typing import Annotated, List

import structlog
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.notifications.dto import (
    CreateChannelRequest,
    NotificationChannelDTO,
    NotificationDeliveryResponse,
    NotificationRuleDTO,
    TestNotificationRequest,
    UpdateChannelRequest,
)
from app.application.notifications.notification_service import NotificationService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["Security Alert Webhooks"])


def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> NotificationService:
    """Dependency provider for NotificationService."""
    audit_log_service = AuditLogService(session)
    return NotificationService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.get(
    "/channels",
    response_model=List[NotificationChannelDTO],
    status_code=status.HTTP_200_OK,
    summary="List Configured Notification Channels",
    description="Returns all Slack & Microsoft Teams webhook channels configured for organization (urls masked).",
    dependencies=[Depends(require_permission("notifications:read"))],
)
async def list_channels(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> List[NotificationChannelDTO]:
    """List notification channels."""
    return await service.list_channels(current_user)


@router.post(
    "/channels",
    response_model=NotificationChannelDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create Webhook Notification Channel",
    description="Encrypts webhook URL secret and persists new Slack or Microsoft Teams notification channel.",
    dependencies=[Depends(require_permission("notifications:manage"))],
)
async def create_channel(
    req: CreateChannelRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelDTO:
    """Create notification channel."""
    return await service.create_channel(current_user, req)


@router.patch(
    "/channels/{channel_id}",
    response_model=NotificationChannelDTO,
    status_code=status.HTTP_200_OK,
    summary="Update Notification Channel Configuration",
    description="Updates channel settings, event subscriptions, or encrypted webhook URL.",
    dependencies=[Depends(require_permission("notifications:manage"))],
)
async def update_channel(
    channel_id: Annotated[str, Path(description="Channel UUID")],
    req: UpdateChannelRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelDTO:
    """Update notification channel."""
    return await service.update_channel(current_user, channel_id, req)


@router.delete(
    "/channels/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notification Channel",
    description="Removes a Slack or Microsoft Teams webhook notification channel.",
    dependencies=[Depends(require_permission("notifications:manage"))],
)
async def delete_channel(
    channel_id: Annotated[str, Path(description="Channel UUID")],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> None:
    """Delete notification channel."""
    await service.delete_channel(current_user, channel_id)


@router.get(
    "/rules",
    response_model=List[NotificationRuleDTO],
    status_code=status.HTTP_200_OK,
    summary="List Notification Routing Rules",
    description="Returns event routing rules and severity filters for organization alerts.",
    dependencies=[Depends(require_permission("notifications:read"))],
)
async def get_rules(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> List[NotificationRuleDTO]:
    """Get notification routing rules."""
    return await service.get_rules(current_user)


@router.post(
    "/test",
    response_model=NotificationDeliveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Send Test Notification",
    description="Dispatches a test security alert card to verify Slack/Teams webhook connectivity.",
    dependencies=[Depends(require_permission("notifications:create"))],
)
async def send_test_notification(
    req: TestNotificationRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationDeliveryResponse:
    """Send test notification."""
    return await service.send_test_notification(current_user, req.channel_id)
