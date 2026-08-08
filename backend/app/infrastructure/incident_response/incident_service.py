"""Incident Response Application Service."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.incident import (
    IncidentModel,
    IncidentTimelineModel,
)
from app.infrastructure.database.repositories.incident_repository import (
    IncidentRepository,
)
from app.infrastructure.incident_response.dto import (
    CreateIncidentRequestDTO,
    EscalationEventDTO,
    IncidentDurationMetricsDTO,
    IncidentListResponseDTO,
    IncidentResponseDTO,
    IncidentStatus,
    IncidentStatusDTO,
    IncidentTimelineDTO,
    PostIncidentReviewDTO,
    UpdateIncidentStateRequestDTO,
)

logger = structlog.get_logger(__name__)


class IncidentResponseService:
    """Enterprise Incident Response lifecycle orchestration service."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IncidentRepository(session)
        self.audit_service = AuditLogService(session)

    async def create_incident(
        self,
        organization_id: UUID,
        request: CreateIncidentRequestDTO,
        actor_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
    ) -> IncidentResponseDTO:
        """Create a new security incident, record timeline, and dispatch audit log."""
        incident_id = uuid4()
        now = datetime.now(timezone.utc)

        incident = IncidentModel(
            id=incident_id,
            organization_id=organization_id,
            title=request.title,
            description=request.description,
            severity=request.severity.value,
            status=IncidentStatus.DETECTED.value,
            lead_investigator_id=request.lead_investigator_id or actor_id,
            affected_services=request.affected_services,
            indicators_of_compromise=request.indicators_of_compromise,
            details=request.details,
            detected_at=now,
            created_at=now,
            updated_at=now,
        )

        saved_incident = await self.repo.create_incident(incident)

        # Record Initial Detection Timeline
        timeline = IncidentTimelineModel(
            id=uuid4(),
            incident_id=incident_id,
            actor_id=actor_id,
            phase="DETECTION",
            action="incident.detected",
            description=f"Incident declared with severity {request.severity.value}: {request.title}",
            timestamp=now,
        )
        await self.repo.add_timeline_event(timeline)

        # Audit Event Logging
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="incident.created",
            resource_type="incident",
            resource_id=str(incident_id),
            actor_user_id=actor_id,
            client_ip=client_ip,
            details={
                "incident_id": str(incident_id),
                "severity": request.severity.value,
                "title": request.title,
            },
        )

        logger.info(
            "security_incident_created",
            incident_id=str(incident_id),
            organization_id=str(organization_id),
            severity=request.severity.value,
        )

        return self._to_response_dto(saved_incident, [timeline], [], None)

    async def get_incident(
        self, incident_id: UUID, organization_id: UUID
    ) -> IncidentResponseDTO:
        """Fetch an incident by ID enforcing tenant isolation boundaries."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=True
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found in organization."
            )

        timelines = incident.timelines or []
        escalations = incident.escalations or []
        pir = incident.post_incident_review

        return self._to_response_dto(incident, timelines, escalations, pir)

    async def list_incidents(
        self,
        organization_id: UUID,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> IncidentListResponseDTO:
        """List paginated incidents for a tenant organization."""
        incidents, total = await self.repo.list_incidents_by_org(
            organization_id=organization_id,
            severity=severity,
            status=status,
            limit=limit,
            offset=offset,
            load_relations=True,
        )

        results = [
            self._to_response_dto(
                inc,
                inc.timelines or [],
                inc.escalations or [],
                inc.post_incident_review,
            )
            for inc in incidents
        ]

        return IncidentListResponseDTO(
            incidents=results,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_incident_state(
        self,
        incident_id: UUID,
        organization_id: UUID,
        request: UpdateIncidentStateRequestDTO,
        actor_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
    ) -> IncidentResponseDTO:
        """Transition incident lifecycle state and record state changes."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=True
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found."
            )

        old_status = incident.status
        new_status = request.status.value
        now = datetime.now(timezone.utc)

        incident.status = new_status
        incident.updated_at = now

        if request.lead_investigator_id:
            incident.lead_investigator_id = request.lead_investigator_id
        if request.affected_services is not None:
            incident.affected_services = request.affected_services
        if request.indicators_of_compromise is not None:
            incident.indicators_of_compromise = request.indicators_of_compromise
        if request.details is not None:
            incident.details.update(request.details)

        # Lifecycle Phase Tracking
        phase = "INVESTIGATION"
        if new_status == IncidentStatus.TRIAGED.value:
            phase = "TRIAGE"
        elif new_status == IncidentStatus.CONTAINED.value:
            phase = "CONTAINMENT"
            if not incident.contained_at:
                incident.contained_at = now
        elif new_status == IncidentStatus.ERADICATED.value:
            phase = "ERADICATION"
        elif new_status == IncidentStatus.RECOVERED.value:
            phase = "RECOVERY"
            if not incident.resolved_at:
                incident.resolved_at = now
        elif new_status == IncidentStatus.CLOSED.value:
            phase = "POST_INCIDENT_REVIEW"
            if not incident.closed_at:
                incident.closed_at = now
            if not incident.resolved_at:
                incident.resolved_at = now

        # Add Timeline Entry
        timeline = IncidentTimelineModel(
            id=uuid4(),
            incident_id=incident_id,
            actor_id=actor_id,
            phase=phase,
            action=f"status_transition_to_{new_status}",
            description=request.note
            or f"Transitioned status from {old_status} to {new_status}",
            timestamp=now,
        )
        await self.repo.add_timeline_event(timeline)
        updated_incident = await self.repo.update_incident(incident)

        # Audit Event Logging
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="incident.state_updated",
            resource_type="incident",
            resource_id=str(incident_id),
            actor_user_id=actor_id,
            client_ip=client_ip,
            details={
                "incident_id": str(incident_id),
                "old_status": old_status,
                "new_status": new_status,
                "note": request.note,
            },
        )

        logger.info(
            "incident_state_transitioned",
            incident_id=str(incident_id),
            old_status=old_status,
            new_status=new_status,
        )

        timelines = await self.repo.list_timeline_events(incident_id)
        escalations = incident.escalations or []
        pir = incident.post_incident_review

        return self._to_response_dto(updated_incident, timelines, escalations, pir)

    async def add_timeline_event(
        self,
        incident_id: UUID,
        organization_id: UUID,
        phase: str,
        action: str,
        description: str,
        actor_id: Optional[UUID] = None,
        audit_log_id: Optional[UUID] = None,
    ) -> IncidentTimelineDTO:
        """Record an explicit timeline milestone during an active investigation."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=False
        )
        if not incident:
            raise ResourceNotFoundException(f"Incident '{incident_id}' not found.")

        timeline = IncidentTimelineModel(
            id=uuid4(),
            incident_id=incident_id,
            actor_id=actor_id,
            phase=phase.upper(),
            action=action,
            description=description,
            audit_log_id=audit_log_id,
            timestamp=datetime.now(timezone.utc),
        )
        saved_timeline = await self.repo.add_timeline_event(timeline)
        return IncidentTimelineDTO.model_validate(saved_timeline)

    async def get_incident_timeline(
        self, incident_id: UUID, organization_id: UUID
    ) -> List[IncidentTimelineDTO]:
        """Fetch all chronological timeline records for an incident."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=False
        )
        if not incident:
            raise ResourceNotFoundException(f"Incident '{incident_id}' not found.")

        timelines = await self.repo.list_timeline_events(incident_id)
        return [IncidentTimelineDTO.model_validate(t) for t in timelines]

    def calculate_response_durations(
        self, incident: IncidentModel, timelines: List[IncidentTimelineModel]
    ) -> IncidentDurationMetricsDTO:
        """Compute MTTA, MTTC, MTTR, and SLA adherence metrics."""
        mtta: Optional[float] = None
        mttc: Optional[float] = None
        mttr: Optional[float] = None
        total_hours: Optional[float] = None
        sla_met = True

        detected_at = incident.detected_at or incident.created_at

        # Calculate MTTA (Time to Triage)
        for t in timelines:
            if t.phase in ("TRIAGE", "CONTAINMENT", "INVESTIGATION"):
                delta = (t.timestamp - detected_at).total_seconds() / 60.0
                mtta = round(max(0.0, delta), 2)
                break

        # Calculate MTTC (Time to Contain)
        if incident.contained_at:
            delta_c = (incident.contained_at - detected_at).total_seconds() / 60.0
            mttc = round(max(0.0, delta_c), 2)

        # Calculate MTTR (Time to Resolve)
        if incident.resolved_at:
            delta_r = (incident.resolved_at - detected_at).total_seconds() / 60.0
            mttr = round(max(0.0, delta_r), 2)
            total_hours = round(delta_r / 60.0, 2)

        # SLA Threshold Validation
        if incident.severity == "SEV-1" and mtta and mtta > 5.0:
            sla_met = False
        elif incident.severity == "SEV-2" and mtta and mtta > 15.0:
            sla_met = False

        return IncidentDurationMetricsDTO(
            mtta_minutes=mtta,
            mttc_minutes=mttc,
            mttr_minutes=mttr,
            total_duration_hours=total_hours,
            sla_met=sla_met,
        )

    async def get_status_summary(self, organization_id: UUID) -> IncidentStatusDTO:
        """Fetch aggregated metrics for incident response dashboard."""
        incidents, _ = await self.repo.list_incidents_by_org(
            organization_id, limit=200, offset=0, load_relations=False
        )

        total_active = sum(1 for i in incidents if i.status != "CLOSED")
        sev1 = sum(
            1 for i in incidents if i.severity == "SEV-1" and i.status != "CLOSED"
        )
        sev2 = sum(
            1 for i in incidents if i.severity == "SEV-2" and i.status != "CLOSED"
        )
        sev3 = sum(
            1 for i in incidents if i.severity == "SEV-3" and i.status != "CLOSED"
        )
        sev4 = sum(
            1 for i in incidents if i.severity == "SEV-4" and i.status != "CLOSED"
        )
        contained = sum(1 for i in incidents if i.contained_at is not None)

        # Average MTTC & MTTR
        contain_durations = [
            (i.contained_at - (i.detected_at or i.created_at)).total_seconds() / 60.0
            for i in incidents
            if i.contained_at
        ]
        resolve_durations = [
            (i.resolved_at - (i.detected_at or i.created_at)).total_seconds() / 60.0
            for i in incidents
            if i.resolved_at
        ]

        avg_mttc = (
            round(sum(contain_durations) / len(contain_durations), 2)
            if contain_durations
            else 0.0
        )
        avg_mttr = (
            round(sum(resolve_durations) / len(resolve_durations), 2)
            if resolve_durations
            else 0.0
        )

        overall_status = "HEALTHY"
        if sev1 > 0:
            overall_status = "CRITICAL"
        elif sev2 > 0:
            overall_status = "DEGRADED"

        return IncidentStatusDTO(
            total_active_incidents=total_active,
            sev1_critical_count=sev1,
            sev2_high_count=sev2,
            sev3_medium_count=sev3,
            sev4_low_count=sev4,
            contained_count=contained,
            mean_time_to_contain_minutes=avg_mttc,
            mean_time_to_resolve_minutes=avg_mttr,
            status=overall_status,
        )

    def _to_response_dto(
        self,
        incident: IncidentModel,
        timelines: List[IncidentTimelineModel],
        escalations: List[Any],
        pir: Optional[Any],
    ) -> IncidentResponseDTO:
        """Transform SQLAlchemy models to typed Pydantic DTO."""
        duration_metrics = self.calculate_response_durations(incident, timelines)

        timeline_dtos = [IncidentTimelineDTO.model_validate(t) for t in timelines]
        escalation_dtos = [EscalationEventDTO.model_validate(e) for e in escalations]
        pir_dto = PostIncidentReviewDTO.model_validate(pir) if pir else None

        return IncidentResponseDTO(
            id=incident.id,
            organization_id=incident.organization_id,
            title=incident.title,
            description=incident.description,
            severity=incident.severity,
            status=incident.status,
            lead_investigator_id=incident.lead_investigator_id,
            affected_services=incident.affected_services or [],
            indicators_of_compromise=incident.indicators_of_compromise or [],
            details=incident.details or {},
            detected_at=incident.detected_at,
            contained_at=incident.contained_at,
            resolved_at=incident.resolved_at,
            closed_at=incident.closed_at,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            timelines=timeline_dtos,
            escalations=escalation_dtos,
            post_incident_review=pir_dto,
            duration_metrics=duration_metrics,
        )
