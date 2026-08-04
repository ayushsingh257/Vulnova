"""FastAPI Router for Security Operations Dashboard (/api/v1/dashboard).

Exposes consolidated SOC overview metrics, security posture analytics, and active scan progress endpoints.
Strictly enforces tenant isolation and RBAC permissions.
"""

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from app.application.assessment.dto import (
    ActiveScanSummaryDTO,
    AttackSurfaceCoverageResponse,
    DashboardOverviewResponse,
    ExecutiveSummaryReportResponse,
    ExecutiveThreatAlertDTO,
    HistoricalRiskTrendResponse,
    SecurityPostureSummaryDTO,
)
from app.application.assessment.executive_analytics_service import (
    ExecutiveAnalyticsService,
)
from app.application.assessment.executive_report_service import ExecutiveReportService
from app.application.assessment.threat_advisory_service import ThreatAdvisoryService
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
    """Retrieve real-time active scan jobs for the dashboard monitor."""
    service = DashboardAnalyticsService(session)
    overview = await service.get_dashboard_overview(current_user)
    return overview.active_scans


# Phase 7.3 Executive Analytics, Trends, Threat Advisories & Report Exports


@router.get(
    "/trends",
    response_model=HistoricalRiskTrendResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def get_historical_risk_trends(
    timeframe_days: int = 30,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> HistoricalRiskTrendResponse:
    """Retrieve time-series historical risk score trajectory points and velocity metrics."""
    service = ExecutiveAnalyticsService(session)
    return await service.get_historical_risk_trends(current_user, timeframe_days)


@router.get(
    "/coverage",
    response_model=AttackSurfaceCoverageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("dashboard:read"))],
)
async def get_attack_surface_coverage(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AttackSurfaceCoverageResponse:
    """Retrieve attack surface target asset breakdown by environment and discovery vector."""
    service = ExecutiveAnalyticsService(session)
    return await service.get_attack_surface_coverage(current_user)


@router.get(
    "/threat-advisories",
    response_model=List[ExecutiveThreatAlertDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("dashboard:read"))],
)
async def get_executive_threat_advisories(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[ExecutiveThreatAlertDTO]:
    """Retrieve active executive security threat advisories and SLA breach alerts."""
    service = ThreatAdvisoryService(session)
    return await service.evaluate_organization_advisories(current_user)


@router.get(
    "/executive-summary",
    response_model=ExecutiveSummaryReportResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("reports:read"))],
)
async def get_executive_summary_report(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ExecutiveSummaryReportResponse:
    """Retrieve consolidated executive security posture report payload."""
    dash_service = DashboardAnalyticsService(session)
    exec_service = ExecutiveAnalyticsService(session)
    threat_service = ThreatAdvisoryService(session)
    report_service = ExecutiveReportService(
        session, dash_service, exec_service, threat_service
    )
    return await report_service.generate_executive_summary_report(current_user)


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("reports:export"))],
)
async def export_executive_summary_report(
    format: str = "json",
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    """Export executive security posture report in JSON or CSV format."""
    dash_service = DashboardAnalyticsService(session)
    exec_service = ExecutiveAnalyticsService(session)
    threat_service = ThreatAdvisoryService(session)
    report_service = ExecutiveReportService(
        session, dash_service, exec_service, threat_service
    )
    content, media_type = await report_service.export_report(
        current_user, format_type=format
    )
    return Response(content=content, media_type=media_type)
