"""FastAPI Router for Attack Surface Trend & Continuous Monitoring (/api/v1/assets/trends, /api/v1/security/posture/timeline)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.continuous_monitoring import (
    ContinuousMonitoringService,
)
from app.application.assessment.dto import (
    PostureTimelineResponse,
    RiskTrajectoryResponse,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(tags=["Attack Surface Trend & Continuous Monitoring Engine"])


@router.get(
    "/assets/trends",
    response_model=RiskTrajectoryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("assets:read"))],
)
async def get_attack_surface_trends(
    limit: int = Query(30, ge=1, le=100, description="Historical snapshots limit"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> RiskTrajectoryResponse:
    """Query organization attack surface risk score trajectory and historical posture snapshots.

    Requires authentication and 'assets:read' RBAC permission.
    """
    service = ContinuousMonitoringService(session)
    return await service.get_posture_trajectory(current_user, limit=limit)


@router.get(
    "/assets/{asset_id}/history",
    response_model=PostureTimelineResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("assets:read"))],
)
async def get_asset_history(
    asset_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Timeline events limit"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PostureTimelineResponse:
    """Query historical change event timeline for a specific asset node.

    Requires authentication and 'assets:read' RBAC permission.
    """
    service = ContinuousMonitoringService(session)
    return await service.get_posture_timeline(
        current_user, asset_node_id=asset_id, limit=limit
    )


@router.get(
    "/findings/history",
    response_model=PostureTimelineResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_findings_history(
    limit: int = Query(50, ge=1, le=100, description="Findings lifecycle events limit"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PostureTimelineResponse:
    """Query vulnerability finding lifecycle status transitions (NEW, RESOLVED, REOPENED).

    Requires authentication and 'findings:read' RBAC permission.
    """
    service = ContinuousMonitoringService(session)
    return await service.get_posture_timeline(current_user, limit=limit)


@router.get(
    "/security/posture/timeline",
    response_model=PostureTimelineResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("assets:read"))],
)
async def get_security_posture_timeline(
    limit: int = Query(50, ge=1, le=100, description="Posture timeline events limit"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PostureTimelineResponse:
    """Query aggregated security posture event timeline for an organization.

    Requires authentication and 'assets:read' RBAC permission.
    """
    service = ContinuousMonitoringService(session)
    return await service.get_posture_timeline(current_user, limit=limit)
