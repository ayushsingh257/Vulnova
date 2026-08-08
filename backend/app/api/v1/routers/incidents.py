"""FastAPI Security Incident Response & Audit Escalation Router."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.infrastructure.incident_response.dto import (
    CreateIncidentRequestDTO,
    CreatePIRRequestDTO,
    EscalationEventDTO,
    ForensicInvestigationResultDTO,
    IncidentListResponseDTO,
    IncidentResponseDTO,
    IncidentStatusDTO,
    IncidentTimelineDTO,
    PostIncidentReviewDTO,
    TriggerEscalationRequestDTO,
    UpdateIncidentStateRequestDTO,
)
from app.infrastructure.incident_response.escalation_service import (
    IncidentEscalationService,
)
from app.infrastructure.incident_response.forensics_service import (
    ForensicInvestigationService,
)
from app.infrastructure.incident_response.incident_service import (
    IncidentResponseService,
)
from app.infrastructure.incident_response.post_incident_service import (
    PostIncidentReviewService,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/incidents", tags=["Security Incident Response"])


@router.get(
    "",
    response_model=IncidentListResponseDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="List Security Incidents",
    description="Retrieve paginated security incidents for the tenant organization.",
)
async def list_incidents(
    severity: Optional[str] = Query(
        None, description="Filter by severity: SEV-1, SEV-2, SEV-3, SEV-4"
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: DETECTED, TRIAGED, CONTAINED, etc.",
    ),
    limit: int = Query(50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> IncidentListResponseDTO:
    """Fetch paginated incidents for the authenticated organization."""
    service = IncidentResponseService(session)
    return await service.list_incidents(
        organization_id=current_user.organization_id,
        severity=severity,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=IncidentResponseDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Create Security Incident",
    description="Declare a new security incident, classify severity, and record initial timeline.",
)
async def create_incident(
    request_dto: CreateIncidentRequestDTO,
    request: Request,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> IncidentResponseDTO:
    """Declare and classify a new security incident."""
    service = IncidentResponseService(session)
    client_ip = request.client.host if request.client else None
    return await service.create_incident(
        organization_id=current_user.organization_id,
        request=request_dto,
        actor_id=current_user.id,
        client_ip=client_ip,
    )


@router.get(
    "/status/summary",
    response_model=IncidentStatusDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Get Incident Response Status Summary",
    description="Retrieve high-level incident response posture, MTTC, and active counts.",
)
async def get_incident_status_summary(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> IncidentStatusDTO:
    """Retrieve operational health metrics for security incidents."""
    service = IncidentResponseService(session)
    return await service.get_status_summary(current_user.organization_id)


@router.get(
    "/{incident_id}",
    response_model=IncidentResponseDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Get Incident Details",
    description="Retrieve details, timeline events, and duration metrics for a specific incident.",
)
async def get_incident_details(
    incident_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> IncidentResponseDTO:
    """Fetch complete security incident metadata and chronology."""
    service = IncidentResponseService(session)
    return await service.get_incident(
        incident_id=incident_id, organization_id=current_user.organization_id
    )


@router.patch(
    "/{incident_id}",
    response_model=IncidentResponseDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Update Incident State",
    description="Transition incident lifecycle state and record timeline actions.",
)
async def update_incident_state(
    incident_id: UUID,
    request_dto: UpdateIncidentStateRequestDTO,
    request: Request,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> IncidentResponseDTO:
    """Advance or update incident lifecycle state."""
    service = IncidentResponseService(session)
    client_ip = request.client.host if request.client else None
    return await service.update_incident_state(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
        request=request_dto,
        actor_id=current_user.id,
        client_ip=client_ip,
    )


@router.post(
    "/{incident_id}/escalate",
    response_model=EscalationEventDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Trigger Incident Escalation",
    description="Dispatch escalation alerts across configured channels (PagerDuty, Slack, Email).",
)
async def trigger_escalation(
    incident_id: UUID,
    request_dto: Optional[TriggerEscalationRequestDTO] = None,
    request: Request = None,  # type: ignore[assignment]
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> EscalationEventDTO:
    """Dispatch multi-channel escalation workflow for an active incident."""
    service = IncidentEscalationService(session)
    client_ip = request.client.host if request and request.client else None
    return await service.trigger_escalation(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
        request=request_dto,
        actor_id=current_user.id,
        client_ip=client_ip,
    )


@router.get(
    "/{incident_id}/timeline",
    response_model=List[IncidentTimelineDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Get Incident Timeline",
    description="Retrieve chronological timeline events and audit log links for an incident.",
)
async def get_incident_timeline(
    incident_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[IncidentTimelineDTO]:
    """Fetch chronological timeline events."""
    service = IncidentResponseService(session)
    return await service.get_incident_timeline(
        incident_id=incident_id, organization_id=current_user.organization_id
    )


@router.post(
    "/{incident_id}/pir",
    response_model=PostIncidentReviewDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Create Post-Incident Review",
    description="Store root cause analysis, timeline synthesis, and remediation action items.",
)
async def create_post_incident_review(
    incident_id: UUID,
    request_dto: CreatePIRRequestDTO,
    request: Request,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PostIncidentReviewDTO:
    """Create or update Post-Incident Review (PIR)."""
    service = PostIncidentReviewService(session)
    client_ip = request.client.host if request.client else None
    return await service.create_or_update_pir(
        incident_id=incident_id,
        organization_id=current_user.organization_id,
        request=request_dto,
        author_id=current_user.id,
        client_ip=client_ip,
    )


@router.get(
    "/{incident_id}/pir",
    response_model=PostIncidentReviewDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Get Post-Incident Review",
    description="Retrieve the Post-Incident Review analysis for an incident.",
)
async def get_post_incident_review(
    incident_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PostIncidentReviewDTO:
    """Fetch PIR analysis and action items."""
    service = PostIncidentReviewService(session)
    return await service.get_pir(
        incident_id=incident_id, organization_id=current_user.organization_id
    )


@router.get(
    "/{incident_id}/forensics",
    response_model=ForensicInvestigationResultDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
    summary="Get Forensic Investigation Package",
    description="Retrieve correlated audit event clusters and SHA-256 evidence integrity package.",
)
async def get_forensic_investigation(
    incident_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> ForensicInvestigationResultDTO:
    """Fetch correlated forensic investigation summary with SHA-256 checksum."""
    service = ForensicInvestigationService(session)
    return await service.preserve_investigation_timeline(
        incident_id=incident_id, organization_id=current_user.organization_id
    )
