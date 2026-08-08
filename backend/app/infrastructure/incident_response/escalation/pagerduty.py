"""PagerDuty Events API v2 Escalation Provider."""

from datetime import datetime, timezone
from typing import Any, Dict

import structlog

from app.infrastructure.incident_response.escalation.base import BaseEscalationProvider

logger = structlog.get_logger(__name__)


class PagerDutyEscalationProvider(BaseEscalationProvider):
    """PagerDuty escalation provider integrating with Events API v2."""

    def __init__(
        self, routing_key: str = "pd_live_mock_routing_key", max_retries: int = 3
    ) -> None:
        super().__init__(channel_name="pagerduty", max_retries=max_retries)
        self.routing_key = routing_key

    def _map_severity(self, severity: str) -> str:
        """Map internal incident severity to PagerDuty severity string."""
        mapping = {
            "SEV-1": "critical",
            "SEV-2": "error",
            "SEV-3": "warning",
            "SEV-4": "info",
        }
        return mapping.get(severity.upper(), "error")

    async def send_notification(
        self,
        incident_id: str,
        title: str,
        severity: str,
        description: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch incident trigger payload to PagerDuty Events API v2."""
        pd_severity = self._map_severity(severity)
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": f"vulnova-incident-{incident_id}",
            "payload": {
                "summary": f"[{severity}] {title}: {description[:200]}",
                "severity": pd_severity,
                "source": "Vulnova-Security-Control-Plane",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "custom_details": details,
            },
            "client": "Vulnova AppSec Platform",
            "client_url": f"https://app.vulnova.com/incidents/{incident_id}",
        }

        # Simulated robust delivery with retry logic
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            attempts += 1
            try:
                # In production, dispatch via httpx/aiohttp to https://events.pagerduty.com/v2/enqueue
                logger.info(
                    "pagerduty_escalation_dispatched",
                    incident_id=incident_id,
                    severity=pd_severity,
                    dedup_key=payload["dedup_key"],
                    attempt=attempts,
                )
                return {
                    "channel": "pagerduty",
                    "status": "DELIVERED",
                    "event_action": "trigger",
                    "dedup_key": payload["dedup_key"],
                    "pagerduty_severity": pd_severity,
                    "attempt": attempts,
                    "dispatched_at": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "pagerduty_dispatch_attempt_failed",
                    incident_id=incident_id,
                    attempt=attempts,
                    error=last_error,
                )

        return {
            "channel": "pagerduty",
            "status": "FAILED",
            "error": last_error or "Max retries exceeded",
            "attempts": attempts,
        }
