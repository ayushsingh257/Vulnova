"""Post-Incident Review (PIR) Application Service."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.incident import (
    IncidentTimelineModel,
    PostIncidentReviewModel,
)
from app.infrastructure.database.repositories.incident_repository import (
    IncidentRepository,
)
from app.infrastructure.incident_response.dto import (
    CreatePIRRequestDTO,
    PostIncidentReviewDTO,
)

logger = structlog.get_logger(__name__)


class PostIncidentReviewService:
    """Post-Incident Review (PIR) analysis and lessons learned management service."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IncidentRepository(session)
        self.audit_service = AuditLogService(session)

    async def create_or_update_pir(
        self,
        incident_id: UUID,
        organization_id: UUID,
        request: CreatePIRRequestDTO,
        author_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
    ) -> PostIncidentReviewDTO:
        """Create or update a Post-Incident Review record for a security incident."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=False
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found in organization."
            )

        now = datetime.now(timezone.utc)
        pir_model = PostIncidentReviewModel(
            id=uuid4(),
            incident_id=incident_id,
            author_id=author_id,
            summary=request.summary,
            root_cause=request.root_cause,
            impact_assessment=request.impact_assessment,
            timeline_summary=request.timeline_summary,
            lessons_learned=request.lessons_learned,
            action_items=request.action_items,
            created_at=now,
            updated_at=now,
        )

        saved_pir = await self.repo.create_or_update_pir(pir_model)

        # Record Timeline Event
        timeline = IncidentTimelineModel(
            id=uuid4(),
            incident_id=incident_id,
            actor_id=author_id,
            phase="POST_INCIDENT_REVIEW",
            action="incident.pir_completed",
            description="Post-Incident Review (PIR) analysis and remediation plan compiled.",
            timestamp=now,
        )
        await self.repo.add_timeline_event(timeline)

        # Audit Event Logging
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="incident.pir_created",
            resource_type="post_incident_review",
            resource_id=str(saved_pir.id),
            actor_user_id=author_id,
            client_ip=client_ip,
            details={
                "incident_id": str(incident_id),
                "pir_id": str(saved_pir.id),
                "action_items_count": len(request.action_items),
            },
        )

        logger.info(
            "post_incident_review_saved",
            incident_id=str(incident_id),
            pir_id=str(saved_pir.id),
        )

        return PostIncidentReviewDTO.model_validate(saved_pir)

    async def get_pir(
        self, incident_id: UUID, organization_id: UUID
    ) -> PostIncidentReviewDTO:
        """Fetch the PIR for a given incident."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=False
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found."
            )

        pir = await self.repo.get_pir_by_incident_id(incident_id)
        if not pir:
            raise ResourceNotFoundException(
                f"No Post-Incident Review found for incident '{incident_id}'."
            )

        return PostIncidentReviewDTO.model_validate(pir)

    async def generate_lessons_learned_report(
        self, incident_id: UUID, organization_id: UUID
    ) -> Dict[str, Any]:
        """Generate structured markdown and data payload for lessons learned report."""
        incident = await self.repo.get_incident_by_id_and_org(
            incident_id, organization_id, load_relations=True
        )
        if not incident:
            raise ResourceNotFoundException(
                f"Security incident '{incident_id}' not found."
            )

        pir = incident.post_incident_review
        if not pir:
            raise ResourceNotFoundException(
                f"Post-Incident Review not available for incident '{incident_id}'."
            )

        markdown_report = (
            f"# Post-Incident Review Report: {incident.title}\n\n"
            f"**Incident ID:** `{incident_id}`  \n"
            f"**Severity:** {incident.severity}  \n"
            f"**Status:** {incident.status}  \n"
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  \n\n"
            f"## 1. Executive Summary\n{pir.summary}\n\n"
            f"## 2. Root Cause Analysis\n{pir.root_cause}\n\n"
            f"## 3. Impact Assessment\n{pir.impact_assessment}\n\n"
            f"## 4. Timeline Summary\n{pir.timeline_summary}\n\n"
            f"## 5. Lessons Learned\n"
            + "\n".join([f"- {item}" for item in pir.lessons_learned])
            + "\n\n"
            "## 6. Corrective Action Items\n"
            + "\n".join(
                [
                    f"- [{item.get('status', 'OPEN')}] **{item.get('title', 'Action')}** "
                    f"(Owner: {item.get('owner', 'Unassigned')}, Due: {item.get('due_date', 'N/A')})"
                    for item in pir.action_items
                ]
            )
            + "\n"
        )

        return {
            "incident_id": str(incident_id),
            "title": incident.title,
            "severity": incident.severity,
            "markdown_report": markdown_report,
            "action_items_count": len(pir.action_items),
            "lessons_learned_count": len(pir.lessons_learned),
        }
