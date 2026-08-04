"""Application Service for emitting structured scan stream events to Pub/Sub transport layers."""

from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities.assessment import Finding
from app.domain.entities.scan_stream import ScanEventType, ScanStreamEvent
from app.infrastructure.workers.redis_pubsub_manager import RedisPubSubManager

logger = get_logger("vulnova.scan_event_publisher")


class ScanEventPublisherService:
    """Application Service responsible for constructing and broadcasting real-time scan stream events."""

    def __init__(self, pubsub_manager: Optional[RedisPubSubManager] = None) -> None:
        self.pubsub = pubsub_manager or RedisPubSubManager()

    async def publish_state_change(
        self,
        organization_id: UUID,
        job_id: UUID,
        previous_state: str,
        new_state: str,
        current_step: Optional[str] = None,
    ) -> bool:
        """Publish scan execution state machine transition event."""
        event = ScanStreamEvent(
            job_id=job_id,
            organization_id=organization_id,
            event_type=ScanEventType.STATE_CHANGE,
            payload={
                "previous_state": previous_state,
                "new_state": new_state,
                "current_step": current_step,
            },
        )
        return await self.pubsub.publish_scan_event(organization_id, job_id, event)

    async def publish_plugin_started(
        self,
        organization_id: UUID,
        job_id: UUID,
        plugin_id: str,
        profile_id: Optional[str] = None,
    ) -> bool:
        """Publish plugin execution started event."""
        event = ScanStreamEvent(
            job_id=job_id,
            organization_id=organization_id,
            event_type=ScanEventType.PLUGIN_STARTED,
            payload={
                "plugin_id": plugin_id,
                "profile_id": profile_id or "full_assessment",
            },
        )
        return await self.pubsub.publish_scan_event(organization_id, job_id, event)

    async def publish_plugin_completed(
        self,
        organization_id: UUID,
        job_id: UUID,
        plugin_id: str,
        findings_count: int,
    ) -> bool:
        """Publish plugin execution completed event."""
        event = ScanStreamEvent(
            job_id=job_id,
            organization_id=organization_id,
            event_type=ScanEventType.PLUGIN_COMPLETED,
            payload={
                "plugin_id": plugin_id,
                "findings_count": findings_count,
            },
        )
        return await self.pubsub.publish_scan_event(organization_id, job_id, event)

    async def publish_finding_discovered(
        self, organization_id: UUID, job_id: UUID, finding: Finding
    ) -> bool:
        """Publish security finding discovered alert event."""
        event = ScanStreamEvent(
            job_id=job_id,
            organization_id=organization_id,
            event_type=ScanEventType.FINDING_DISCOVERED,
            payload={
                "title": finding.title,
                "severity": (
                    finding.severity.value
                    if hasattr(finding.severity, "value")
                    else str(finding.severity)
                ),
                "category": finding.category,
                "cve_id": finding.cve_id,
                "cwe_id": finding.cwe_id,
            },
        )
        return await self.pubsub.publish_scan_event(organization_id, job_id, event)

    async def publish_error(
        self, organization_id: UUID, job_id: UUID, error_message: str
    ) -> bool:
        """Publish diagnostic error log event."""
        event = ScanStreamEvent(
            job_id=job_id,
            organization_id=organization_id,
            event_type=ScanEventType.ERROR_LOG,
            payload={"error": error_message},
        )
        return await self.pubsub.publish_scan_event(organization_id, job_id, event)
