"""SQLAlchemy Incident Repository."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.incident import (
    EscalationEventModel,
    IncidentModel,
    IncidentTimelineModel,
    PostIncidentReviewModel,
)


class IncidentRepository:
    """Async SQLAlchemy Repository for security incidents, timelines, escalations, and PIRs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_incident(self, incident: IncidentModel) -> IncidentModel:
        """Persist a newly created security incident."""
        self.session.add(incident)
        await self.session.flush()
        return incident

    async def get_incident_by_id_and_org(
        self,
        incident_id: UUID,
        organization_id: UUID,
        load_relations: bool = True,
    ) -> Optional[IncidentModel]:
        """Fetch a specific incident ensuring tenant boundary isolation."""
        stmt = (
            select(IncidentModel)
            .where(IncidentModel.id == incident_id)
            .where(IncidentModel.organization_id == organization_id)
        )
        if load_relations:
            stmt = stmt.options(
                selectinload(IncidentModel.timelines),
                selectinload(IncidentModel.escalations),
                selectinload(IncidentModel.post_incident_review),
                selectinload(IncidentModel.lead_investigator),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_incidents_by_org(
        self,
        organization_id: UUID,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        load_relations: bool = False,
    ) -> Tuple[List[IncidentModel], int]:
        """Fetch paginated incidents for an organization with optional severity and status filters."""
        stmt = select(IncidentModel).where(
            IncidentModel.organization_id == organization_id
        )
        count_stmt = select(func.count(IncidentModel.id)).where(
            IncidentModel.organization_id == organization_id
        )

        if severity:
            stmt = stmt.where(IncidentModel.severity == severity)
            count_stmt = count_stmt.where(IncidentModel.severity == severity)

        if status:
            stmt = stmt.where(IncidentModel.status == status)
            count_stmt = count_stmt.where(IncidentModel.status == status)

        if load_relations:
            stmt = stmt.options(
                selectinload(IncidentModel.lead_investigator),
                selectinload(IncidentModel.post_incident_review),
            )

        stmt = (
            stmt.order_by(IncidentModel.created_at.desc()).offset(offset).limit(limit)
        )

        result = await self.session.execute(stmt)
        count_result = await self.session.execute(count_stmt)

        incidents = list(result.scalars().all())
        total = int(count_result.scalar() or 0)
        return incidents, total

    async def update_incident(self, incident: IncidentModel) -> IncidentModel:
        """Update an existing incident record."""
        await self.session.flush()
        return incident

    async def add_timeline_event(
        self, timeline: IncidentTimelineModel
    ) -> IncidentTimelineModel:
        """Persist a timeline event for an incident."""
        self.session.add(timeline)
        await self.session.flush()
        return timeline

    async def list_timeline_events(
        self, incident_id: UUID
    ) -> List[IncidentTimelineModel]:
        """Retrieve all chronological timeline events for an incident."""
        stmt = (
            select(IncidentTimelineModel)
            .where(IncidentTimelineModel.incident_id == incident_id)
            .options(
                selectinload(IncidentTimelineModel.actor),
                selectinload(IncidentTimelineModel.audit_log),
            )
            .order_by(IncidentTimelineModel.timestamp.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_escalation_event(
        self, escalation: EscalationEventModel
    ) -> EscalationEventModel:
        """Record an escalation event dispatch record."""
        self.session.add(escalation)
        await self.session.flush()
        return escalation

    async def list_escalation_events(
        self, incident_id: UUID
    ) -> List[EscalationEventModel]:
        """Retrieve escalation event history for an incident."""
        stmt = (
            select(EscalationEventModel)
            .where(EscalationEventModel.incident_id == incident_id)
            .options(selectinload(EscalationEventModel.user))
            .order_by(EscalationEventModel.triggered_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_or_update_pir(
        self, pir: PostIncidentReviewModel
    ) -> PostIncidentReviewModel:
        """Create or update a Post-Incident Review (PIR) record."""
        stmt = select(PostIncidentReviewModel).where(
            PostIncidentReviewModel.incident_id == pir.incident_id
        )
        result = await self.session.execute(stmt)
        existing = (
            result.scalar_one_or_none()
            if hasattr(result, "scalar_one_or_none")
            else None
        )

        if isinstance(existing, PostIncidentReviewModel):
            existing.author_id = pir.author_id
            existing.summary = pir.summary
            existing.root_cause = pir.root_cause
            existing.impact_assessment = pir.impact_assessment
            existing.timeline_summary = pir.timeline_summary
            existing.lessons_learned = pir.lessons_learned
            existing.action_items = pir.action_items
            await self.session.flush()
            return existing
        else:
            self.session.add(pir)
            await self.session.flush()
            return pir

    async def get_pir_by_incident_id(
        self, incident_id: UUID
    ) -> Optional[PostIncidentReviewModel]:
        """Fetch the PIR for a specific incident."""
        stmt = (
            select(PostIncidentReviewModel)
            .where(PostIncidentReviewModel.incident_id == incident_id)
            .options(selectinload(PostIncidentReviewModel.author))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
