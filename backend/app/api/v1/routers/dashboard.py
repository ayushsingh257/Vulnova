"""FastAPI Router for Security Operations Dashboard (/api/v1/dashboard).

Exposes consolidated SOC overview metrics, security posture analytics, and active scan progress endpoints.
Strictly enforces tenant isolation and RBAC permissions.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from app.application.assessment.dto import (
    ActiveScanSummaryDTO,
    DashboardOverviewResponse,
    SecurityPostureSummaryDTO,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/dashboard", tags=["Security Operations Dashboard Engine"])


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("dashboard:read"))],
)
async def get_dashboard_overview(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> DashboardOverviewResponse:
    """Retrieve consolidated Security Operations Center (SOC) dashboard metrics.

    Includes composite risk score, posture status, vulnerability severity distribution,
    active scan executions, top vulnerable assets, and recurring schedule summaries.

    Requires authentication and 'dashboard:read' RBAC permission (VIEWER level 10+).
    Enforces strict organization tenant isolation.
    """
    service = DashboardAnalyticsService(session)
    return await service.get_dashboard_overview(current_user)


@router.get(
    "/posture",
    response_model=SecurityPostureSummaryDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def get_dashboard_posture_summary(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SecurityPostureSummaryDTO:
    """Retrieve organization composite security posture risk score and status summary.

    Requires authentication and 'analytics:read' RBAC permission (SECURITY_ANALYST level 20+).
    Enforces strict organization tenant isolation.
    """
    service = DashboardAnalyticsService(session)
    overview = await service.get_dashboard_overview(current_user)
    return overview.posture_summary


@router.get(
    "/scans/active",
    response_model=List[ActiveScanSummaryDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def get_active_dashboard_scans(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[ActiveScanSummaryDTO]:
    """Retrieve real-time active scan jobs for the dashboard monitor.

    Requires authentication and 'scans:read' RBAC permission (VIEWER level 10+).
    Enforces strict organization tenant isolation.
    """
    service = DashboardAnalyticsService(session)
    overview = await service.get_dashboard_overview(current_user)
    return overview.active_scans
