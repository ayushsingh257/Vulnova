"""Incident Escalation Application Service."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.incident import (
    EscalationEventModel,
    IncidentTimelineModel,
)
from app.infrastructure.database.repositories.incident_repository import (
    IncidentRepository,
)
from app.infrastructure.incident_response.dto import (
    EscalationEventDTO,
    TriggerEscalationRequestDTO,
)
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

logger = structlog.get_logger(__name__)


class IncidentEscalationService:
    """Escalation workflow engine dispatching alerts to PagerDuty, Slack, and Email."""

    def __init__(
        self,
        session: AsyncSession,
        providers: Optional[Dict[str, BaseEscalationProvider]] = None,
    ) -> None:
        self.session = session
        self.repo = IncidentRepository(session)
        self.audit_service = AuditLogService(session)
        self.providers: Dict[str, BaseEscalationProvider] = providers or {
            "pagerduty": PagerDutyEscalationProvider(),
            "slack": SlackEscalationProvider(),
            "email": EmailEscalationProvider(),
        }

    def evaluate_escalation_rules(self, severity: str) -> List[str]:
        """Determine required notification channels according to severity level."""
        sev = severity.upper()
        if sev == "SEV-1":
            return ["pagerduty", "slack", "email"]
        elif sev == "SEV-2":
            return ["pagerduty", "slack", "email"]
        elif sev == "SEV-3":
            return ["slack", "email"]
        else:
            return ["slack"]

    async def trigger_escalation(
        self,
        incident_id: UUID,
        organization_id: UUID,
        request: Optional[TriggerEscalationRequestDTO] = None,
        actor_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
    ) -> EscalationEventDTO:
        """Execute multi-channel escalation dispatch for an incident."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=False
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found in organization."
            )

        target_channels = (
            request.channels
            if request and request.channels
            else self.evaluate_escalation_rules(incident.severity)
        )

        notification_statuses: Dict[str, Any] = {}
        all_success = True
        any_success = False

        for channel in target_channels:
            provider = self.providers.get(channel.lower())
            if provider:
                try:
                    result = await provider.send_notification(
                        incident_id=str(incident_id),
                        title=incident.title,
                        severity=incident.severity,
                        description=incident.description,
                        details={
                            "affected_services": incident.affected_services,
                            "reason": request.reason if request else None,
                            "extra": request.details if request else {},
                        },
                    )
                    notification_statuses[channel] = result
                    if result.get("status") == "DELIVERED":
                        any_success = True
                    else:
                        all_success = False
                except Exception as exc:
                    notification_statuses[channel] = {
                        "status": "FAILED",
                        "error": str(exc),
                    }
                    all_success = False
            else:
                notification_statuses[channel] = {
                    "status": "FAILED",
                    "error": f"Provider '{channel}' not registered",
                }
                all_success = False

        overall_status = (
            "DELIVERED" if all_success else ("PARTIAL" if any_success else "FAILED")
        )

        # Record Escalation Event
        event_id = uuid4()
        now = datetime.now(timezone.utc)
        escalation_event = EscalationEventModel(
            id=event_id,
            incident_id=incident_id,
            triggered_by=actor_id,
            severity=incident.severity,
            channels=target_channels,
            notification_status=notification_statuses,
            status=overall_status,
            triggered_at=now,
            details={
                "reason": request.reason if request else None,
                "extra": request.details if request else {},
            },
        )
        saved_event = await self.repo.create_escalation_event(escalation_event)

        # Record Incident Timeline
        timeline = IncidentTimelineModel(
            id=uuid4(),
            incident_id=incident_id,
            actor_id=actor_id,
            phase="TRIAGE",
            action="incident.escalated",
            description=(
                f"Escalation triggered across channels [{', '.join(target_channels)}] "
                f"with status {overall_status}"
            ),
            timestamp=now,
        )
        await self.repo.add_timeline_event(timeline)

        # Dispatch Audit Event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="incident.escalated",
            resource_type="incident",
            resource_id=str(incident_id),
            actor_user_id=actor_id,
            client_ip=client_ip,
            details={
                "incident_id": str(incident_id),
                "severity": incident.severity,
                "channels": target_channels,
                "status": overall_status,
            },
        )

        logger.info(
            "incident_escalation_completed",
            incident_id=str(incident_id),
            channels=target_channels,
            status=overall_status,
        )

        return EscalationEventDTO.model_validate(saved_event)

    async def get_escalation_history(
        self, incident_id: UUID, organization_id: UUID
    ) -> List[EscalationEventDTO]:
        """Fetch past escalation event history for an incident."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=False
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found."
            )

        events = await self.repo.list_escalation_events(incident_id)
        return [EscalationEventDTO.model_validate(e) for e in events]
