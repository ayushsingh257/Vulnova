"""Escalation Notification Providers Package."""

from app.infrastructure.incident_response.escalation.base import BaseEscalationProvider
from app.infrastructure.incident_response.escalation.email import (
    EmailEscalationProvider,
)
from app.infrastructure.incident_response.escalation.pagerduty import (
    PagerDutyEscalationProvider,
)
from app.infrastructure.incident_response.escalation.slack import (
    SlackEscalationProvider,
)

__all__ = [
    "BaseEscalationProvider",
    "PagerDutyEscalationProvider",
    "SlackEscalationProvider",
    "EmailEscalationProvider",
]
