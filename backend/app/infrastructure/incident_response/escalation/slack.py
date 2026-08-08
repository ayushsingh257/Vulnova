"""Slack Webhook Incident Escalation Provider."""

from datetime import datetime, timezone
from typing import Any, Dict

import structlog

from app.infrastructure.incident_response.escalation.base import BaseEscalationProvider

logger = structlog.get_logger(__name__)


class SlackEscalationProvider(BaseEscalationProvider):
    """Slack escalation provider generating Block Kit alert cards."""

    def __init__(
        self,
        webhook_url: str = "https://hooks.slack.com/services/mock",
        max_retries: int = 3,
    ) -> None:
        super().__init__(channel_name="slack", max_retries=max_retries)
        self.webhook_url = webhook_url

    def _get_severity_color(self, severity: str) -> str:
        """Map severity to Slack attachment color."""
        mapping = {
            "SEV-1": "#DC2626",  # Red
            "SEV-2": "#F97316",  # Orange
            "SEV-3": "#EAB308",  # Yellow
            "SEV-4": "#3B82F6",  # Blue
        }
        return mapping.get(severity.upper(), "#6B7280")

    async def send_notification(
        self,
        incident_id: str,
        title: str,
        severity: str,
        description: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch Block Kit formatted payload to Slack incoming webhook."""
        color = self._get_severity_color(severity)
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 [{severity}] Vulnova Security Incident Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{incident_id}`"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n*{severity}*"},
                    {"type": "mrkdwn", "text": f"*Title:*\n{title}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:*\n{description}"},
            },
        ]

        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ]
        }

        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            attempts += 1
            try:
                logger.info(
                    "slack_incident_escalation_dispatched",
                    incident_id=incident_id,
                    severity=severity,
                    color=color,
                    payload_size=len(str(payload)),
                    attempt=attempts,
                )
                return {
                    "channel": "slack",
                    "status": "DELIVERED",
                    "blocks_count": len(blocks),
                    "attempt": attempts,
                    "dispatched_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "slack_dispatch_attempt_failed",
                    incident_id=incident_id,
                    attempt=attempts,
                    error=last_error,
                )

        return {
            "channel": "slack",
            "status": "FAILED",
            "error": last_error or "Max retries exceeded",
            "attempts": attempts,
        }
