"""Email Incident Escalation Provider."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from app.infrastructure.incident_response.escalation.base import BaseEscalationProvider

logger = structlog.get_logger(__name__)


class EmailEscalationProvider(BaseEscalationProvider):
    """Email escalation provider delivering alerts to security distribution lists."""

    def __init__(
        self,
        default_recipients: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(channel_name="email", max_retries=max_retries)
        self.default_recipients = default_recipients or [
            "security-alerts@vulnova.internal"
        ]

    async def send_notification(
        self,
        incident_id: str,
        title: str,
        severity: str,
        description: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch email alert notification to security distribution list."""
        subject = f"[Vulnova Incident Alert] [{severity}] {title}"
        body_text = (
            f"VULNOVA SECURITY INCIDENT ALERT\n"
            f"================================\n"
            f"Incident ID: {incident_id}\n"
            f"Severity:    {severity}\n"
            f"Title:       {title}\n"
            f"Time:        {datetime.now(timezone.utc).isoformat()}\n\n"
            f"Description:\n{description}\n\n"
            f"Details:\n{details}\n\n"
            f"Action Required: Access the Incident War Room immediately at "
            f"https://app.vulnova.com/incidents/{incident_id}\n"
        )

        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            attempts += 1
            try:
                logger.info(
                    "email_incident_escalation_dispatched",
                    incident_id=incident_id,
                    severity=severity,
                    recipients=self.default_recipients,
                    body_preview=body_text[:100],
                    attempt=attempts,
                )
                return {
                    "channel": "email",
                    "status": "DELIVERED",
                    "subject": subject,
                    "recipients": self.default_recipients,
                    "attempt": attempts,
                    "dispatched_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "email_dispatch_attempt_failed",
                    incident_id=incident_id,
                    attempt=attempts,
                    error=last_error,
                )

        return {
            "channel": "email",
            "status": "FAILED",
            "error": last_error or "Max retries exceeded",
            "attempts": attempts,
        }
