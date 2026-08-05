"""Application Service managing Tenant-Isolated Webhook Channels, Alert Routing, and Notification Dispatch."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.notifications.dto import (
    CreateChannelRequest,
    NotificationChannelDTO,
    NotificationDeliveryResponse,
    NotificationRuleDTO,
    SecurityNotificationEventDTO,
    UpdateChannelRequest,
)
from app.application.notifications.providers.slack_provider import SlackWebhookProvider
from app.application.notifications.providers.teams_provider import TeamsWebhookProvider
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.user import UserModel
from app.security.encryption import SecretEncryptionService

logger = structlog.get_logger(__name__)

# In-memory store for encrypted notification channels per organization
# Key: str(org_id) -> List[Dict[str, Any]]
_ENCRYPTED_NOTIFICATIONS_STORE: Dict[str, List[Dict[str, Any]]] = {}

# Delivery history log per organization for audit visibility
_NOTIFICATION_DELIVERY_LOGS: Dict[str, List[Dict[str, Any]]] = {}


def _mask_url(url: str) -> str:
    """Mask sensitive webhook URL tokens."""
    if not url or len(url) < 15:
        return "https://******"
    prefix = url[:25]
    suffix = url[-6:]
    return f"{prefix}*****{suffix}"


class NotificationService:
    """Service orchestrating Slack & Teams webhook management, event rule evaluation, and non-blocking alert dispatch."""

    SEVERITY_HIERARCHY = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
        "INFO": 0,
        "ALL": -1,
    }

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service
        self.encryption_service = SecretEncryptionService()
        self.slack_provider = SlackWebhookProvider()
        self.teams_provider = TeamsWebhookProvider()

    def _get_tenant_channels(self, organization_id: UUID) -> List[Dict[str, Any]]:
        org_str = str(organization_id)
        return _ENCRYPTED_NOTIFICATIONS_STORE.get(org_str, [])

    def _save_tenant_channels(
        self, organization_id: UUID, channels: List[Dict[str, Any]]
    ) -> None:
        org_str = str(organization_id)
        _ENCRYPTED_NOTIFICATIONS_STORE[org_str] = channels

    async def list_channels(self, user: UserModel) -> List[NotificationChannelDTO]:
        """Fetch all notification channels configured for user's organization (urls masked)."""
        raw_channels = self._get_tenant_channels(user.organization_id)
        dtos: List[NotificationChannelDTO] = []
        for ch in raw_channels:
            plain_url = self.encryption_service.decrypt_secret(
                ch["encrypted_webhook_url"]
            )
            dtos.append(
                NotificationChannelDTO(
                    id=ch["id"],
                    provider=ch["provider"],
                    name=ch["name"],
                    webhook_url_masked=_mask_url(plain_url),
                    event_types=ch["event_types"],
                    min_severity=ch["min_severity"],
                    is_active=ch["is_active"],
                    created_at=ch["created_at"],
                )
            )
        return dtos

    async def create_channel(
        self, user: UserModel, req: CreateChannelRequest
    ) -> NotificationChannelDTO:
        """Create and encrypt a new notification webhook channel for tenant."""
        channel_id = str(uuid.uuid4())
        encrypted_url = self.encryption_service.encrypt_secret(req.webhook_url)
        now_iso = datetime.now(timezone.utc).isoformat()

        channel_record = {
            "id": channel_id,
            "provider": req.provider.lower(),
            "name": req.name,
            "encrypted_webhook_url": encrypted_url,
            "event_types": req.event_types,
            "min_severity": req.min_severity.upper(),
            "is_active": True,
            "created_at": now_iso,
        }

        channels = self._get_tenant_channels(user.organization_id)
        channels.append(channel_record)
        self._save_tenant_channels(user.organization_id, channels)

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="notification.channel_created",
            resource_type="notification_channel",
            resource_id=channel_id,
            actor_user_id=user.id,
            details={
                "provider": req.provider.lower(),
                "name": req.name,
                "min_severity": req.min_severity.upper(),
            },
        )

        return NotificationChannelDTO(
            id=channel_id,
            provider=req.provider.lower(),
            name=req.name,
            webhook_url_masked=_mask_url(req.webhook_url),
            event_types=req.event_types,
            min_severity=req.min_severity.upper(),
            is_active=True,
            created_at=now_iso,
        )

    async def update_channel(
        self, user: UserModel, channel_id: str, req: UpdateChannelRequest
    ) -> NotificationChannelDTO:
        """Update notification webhook channel settings for tenant."""
        channels = self._get_tenant_channels(user.organization_id)
        target: Optional[Dict[str, Any]] = None
        for ch in channels:
            if ch["id"] == channel_id:
                target = ch
                break

        if not target:
            raise ResourceNotFoundException(
                f"Notification channel '{channel_id}' not found"
            )

        if req.name is not None:
            target["name"] = req.name
        if req.webhook_url is not None:
            target["encrypted_webhook_url"] = self.encryption_service.encrypt_secret(
                req.webhook_url
            )
        if req.event_types is not None:
            target["event_types"] = req.event_types
        if req.min_severity is not None:
            target["min_severity"] = req.min_severity.upper()
        if req.is_active is not None:
            target["is_active"] = req.is_active

        self._save_tenant_channels(user.organization_id, channels)

        plain_url = self.encryption_service.decrypt_secret(
            target["encrypted_webhook_url"]
        )

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="notification.channel_updated",
            resource_type="notification_channel",
            resource_id=channel_id,
            actor_user_id=user.id,
            details={"provider": target["provider"], "name": target["name"]},
        )

        return NotificationChannelDTO(
            id=target["id"],
            provider=target["provider"],
            name=target["name"],
            webhook_url_masked=_mask_url(plain_url),
            event_types=target["event_types"],
            min_severity=target["min_severity"],
            is_active=target["is_active"],
            created_at=target["created_at"],
        )

    async def delete_channel(self, user: UserModel, channel_id: str) -> bool:
        """Delete notification channel for tenant."""
        channels = self._get_tenant_channels(user.organization_id)
        filtered = [ch for ch in channels if ch["id"] != channel_id]

        if len(filtered) == len(channels):
            raise ResourceNotFoundException(
                f"Notification channel '{channel_id}' not found"
            )

        self._save_tenant_channels(user.organization_id, filtered)

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="notification.channel_deleted",
            resource_type="notification_channel",
            resource_id=channel_id,
            actor_user_id=user.id,
            details={"channel_id": channel_id},
        )
        return True

    async def get_rules(self, user: UserModel) -> List[NotificationRuleDTO]:
        """Get notification event routing rules."""
        return [
            NotificationRuleDTO(
                id="rule_critical_high_findings",
                name="Critical & High Vulnerability Alerts",
                event_types=["CRITICAL_FINDING_DISCOVERED", "HIGH_FINDING_DISCOVERED"],
                min_severity="HIGH",
                min_risk_score=7.0,
                is_enabled=True,
            ),
            NotificationRuleDTO(
                id="rule_scan_events",
                name="Scan Lifecycle & Error Monitoring",
                event_types=["SCAN_STARTED", "SCAN_COMPLETED", "SCAN_FAILED"],
                min_severity="ALL",
                min_risk_score=0.0,
                is_enabled=True,
            ),
            NotificationRuleDTO(
                id="rule_compliance_events",
                name="Compliance Posture & Control Failures",
                event_types=["COMPLIANCE_SCORE_DROPPED", "FRAMEWORK_CONTROL_FAILED"],
                min_severity="MEDIUM",
                min_risk_score=5.0,
                is_enabled=True,
            ),
            NotificationRuleDTO(
                id="rule_integration_sync",
                name="Jira & GitHub Ticket Sync Events",
                event_types=["TICKET_CREATED", "TICKET_SYNCED"],
                min_severity="ALL",
                min_risk_score=0.0,
                is_enabled=True,
            ),
        ]

    def _should_dispatch_to_channel(
        self, channel: Dict[str, Any], event: SecurityNotificationEventDTO
    ) -> bool:
        """Evaluate if an event matches a channel's subscription rules."""
        if not channel.get("is_active", True):
            return False

        # Event type check
        subscribed_events = channel.get("event_types", [])
        if subscribed_events and event.event_type not in subscribed_events:
            return False

        # Severity filter check
        ch_min_sev = channel.get("min_severity", "ALL").upper()
        ch_rank = self.SEVERITY_HIERARCHY.get(ch_min_sev, -1)
        event_sev = event.severity.upper() if event.severity else "HIGH"
        event_rank = self.SEVERITY_HIERARCHY.get(event_sev, 2)

        return event_rank >= ch_rank

    async def send_notification(
        self,
        organization_id: UUID,
        event: SecurityNotificationEventDTO,
        actor_user_id: Optional[UUID] = None,
    ) -> List[NotificationDeliveryResponse]:
        """Dispatch security event to all matching Slack & Teams channels (non-blocking for callers)."""
        channels = self._get_tenant_channels(organization_id)
        responses: List[NotificationDeliveryResponse] = []

        for ch in channels:
            if not self._should_dispatch_to_channel(ch, event):
                continue

            plain_url = self.encryption_service.decrypt_secret(
                ch["encrypted_webhook_url"]
            )
            provider_type = ch.get("provider", "slack").lower()

            try:
                if provider_type == "teams":
                    deliv = await self.teams_provider.send_alert(
                        ch["id"], plain_url, event
                    )
                else:
                    deliv = await self.slack_provider.send_alert(
                        ch["id"], plain_url, event
                    )

                responses.append(deliv)

                # Record delivery audit event
                audit_action = (
                    "notification.sent"
                    if deliv.status == "DELIVERED"
                    else "notification.failed"
                )
                await self.audit_log_service.record_event(
                    organization_id=organization_id,
                    action=audit_action,
                    resource_type="notification_channel",
                    resource_id=ch["id"],
                    actor_user_id=actor_user_id,
                    details={
                        "provider": provider_type,
                        "event_type": event.event_type,
                        "status": deliv.status,
                        "status_code": deliv.status_code,
                    },
                )
            except Exception as e:
                logger.error(
                    "notification_service.dispatch_error",
                    channel_id=ch["id"],
                    error=str(e),
                )
                fail_deliv = NotificationDeliveryResponse(
                    channel_id=ch["id"],
                    provider=provider_type,
                    event_type=event.event_type,
                    status="FAILED",
                    status_code=500,
                    delivered_at=datetime.now(timezone.utc).isoformat(),
                    error_message=str(e),
                )
                responses.append(fail_deliv)

        return responses

    async def send_test_notification(
        self, user: UserModel, channel_id: str
    ) -> NotificationDeliveryResponse:
        """Send an instant test alert payload to verify channel connectivity."""
        channels = self._get_tenant_channels(user.organization_id)
        target = next((ch for ch in channels if ch["id"] == channel_id), None)
        if not target:
            raise ResourceNotFoundException(
                f"Notification channel '{channel_id}' not found"
            )

        plain_url = self.encryption_service.decrypt_secret(
            target["encrypted_webhook_url"]
        )
        test_event = SecurityNotificationEventDTO(
            event_type="TEST_NOTIFICATION",
            title="Vulnova Webhook Channel Verification Test",
            description="This is a test notification dispatched from the Vulnova Enterprise Control Plane to verify webhook connectivity.",
            severity="INFO",
            risk_score=0.0,
            target_asset="Vulnova Core Platform",
            details={"triggered_by": user.email},
        )

        provider_type = target.get("provider", "slack").lower()
        if provider_type == "teams":
            deliv = await self.teams_provider.send_alert(
                target["id"], plain_url, test_event
            )
        else:
            deliv = await self.slack_provider.send_alert(
                target["id"], plain_url, test_event
            )

        audit_action = (
            "notification.sent"
            if deliv.status == "DELIVERED"
            else "notification.failed"
        )
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action=audit_action,
            resource_type="notification_channel",
            resource_id=channel_id,
            actor_user_id=user.id,
            details={
                "provider": provider_type,
                "event_type": "TEST_NOTIFICATION",
                "status": deliv.status,
            },
        )

        return deliv
