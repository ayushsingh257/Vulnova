"""Base Provider Abstraction for Incident Escalations."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseEscalationProvider(ABC):
    """Abstract interface for all notification and incident escalation channels."""

    def __init__(self, channel_name: str, max_retries: int = 3) -> None:
        self.channel_name = channel_name
        self.max_retries = max_retries

    @abstractmethod
    async def send_notification(
        self,
        incident_id: str,
        title: str,
        severity: str,
        description: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch an escalation alert to the target channel.

        Returns a dictionary containing delivery status, timestamps, and provider metadata.
        """
        pass
