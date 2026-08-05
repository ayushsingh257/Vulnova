"""Microsoft Teams Webhook Provider utilizing Office 365 Connector Adaptive MessageCard JSON format."""

from datetime import datetime, timezone
from typing import Any, Dict

import httpx
import structlog

from app.application.notifications.dto import (
    NotificationDeliveryResponse,
    SecurityNotificationEventDTO,
)

logger = structlog.get_logger(__name__)


class TeamsWebhookProvider:
    """Dispatches real-time security alert webhooks to Microsoft Teams Channels using Adaptive MessageCard formatting."""

    SEVERITY_COLORS = {
        "CRITICAL": "DC2626",
        "HIGH": "F97316",
        "MEDIUM": "EAB308",
        "LOW": "3B82F6",
        "INFO": "10B981",
    }

    @staticmethod
    def format_adaptive_card_payload(
        event: SecurityNotificationEventDTO,
    ) -> Dict[str, Any]:
        """Build Microsoft Teams MessageCard JSON payload."""
        sev = event.severity.upper() if event.severity else "HIGH"
        color = TeamsWebhookProvider.SEVERITY_COLORS.get(sev, "6B7280")
        target = event.target_asset or "Enterprise Target Asset"
        score_str = str(event.risk_score) if event.risk_score is not None else "N/A"

        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": f"Vulnova Security Alert: {event.title}",
            "sections": [
                {
                    "activityTitle": f"🛡️ Vulnova Security Alert: {event.title}",
                    "activitySubtitle": f"Event Type: {event.event_type} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    "facts": [
                        {"name": "Severity:", "value": sev},
                        {"name": "Risk Score:", "value": score_str},
                        {"name": "Event Type:", "value": event.event_type},
                        {"name": "Target Asset:", "value": target},
                    ],
                    "text": event.description[:1000],
                    "markdown": True,
                }
            ],
        }

    async def send_alert(
        self,
        channel_id: str,
        webhook_url: str,
        event: SecurityNotificationEventDTO,
    ) -> NotificationDeliveryResponse:
        """Send Microsoft Teams incoming webhook alert."""
        payload = self.format_adaptive_card_payload(event)
        now_iso = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(webhook_url, json=payload)
                if res.status_code not in (200, 201, 204):
                    logger.error(
                        "teams.delivery_failed",
                        channel_id=channel_id,
                        status_code=res.status_code,
                        body=res.text,
                    )
                    return NotificationDeliveryResponse(
                        channel_id=channel_id,
                        provider="teams",
                        event_type=event.event_type,
                        status="FAILED",
                        status_code=res.status_code,
                        delivered_at=now_iso,
                        error_message=f"Teams returned HTTP {res.status_code}: {res.text[:150]}",
                    )

                logger.info("teams.delivered_successfully", channel_id=channel_id)
                return NotificationDeliveryResponse(
                    channel_id=channel_id,
                    provider="teams",
                    event_type=event.event_type,
                    status="DELIVERED",
                    status_code=res.status_code,
                    delivered_at=now_iso,
                )
            except Exception as e:
                logger.error(
                    "teams.http_exception", channel_id=channel_id, error=str(e)
                )
                return NotificationDeliveryResponse(
                    channel_id=channel_id,
                    provider="teams",
                    event_type=event.event_type,
                    status="FAILED",
                    status_code=500,
                    delivered_at=now_iso,
                    error_message=f"HTTP connection failed: {str(e)}",
                )
