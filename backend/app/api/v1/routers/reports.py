"""REST API Router for Executive Security Reports & Document Generation."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from app.application.assessment.executive_analytics_service import (
    ExecutiveAnalyticsService,
)
from app.application.assessment.threat_advisory_service import ThreatAdvisoryService
from app.application.audit_logs.services import AuditLogService
from app.application.reporting.dto import (
    CreateExecutiveReportRequest,
    ExecutiveReportDataPayload,
    ExecutiveReportMetadataResponse,
)
from app.application.reporting.html_renderer import HTMLRendererService
from app.application.reporting.pdf_generator import PDFGeneratorService
from app.application.reporting.report_service import ExecutiveSecurityReportService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Executive Security Reports & Exports"])


def get_reporting_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ExecutiveSecurityReportService:
    """Dependency provider for ExecutiveSecurityReportService."""
    dashboard_service = DashboardAnalyticsService(session)
    executive_analytics_service = ExecutiveAnalyticsService(session)
    threat_advisory_service = ThreatAdvisoryService(session)
    html_renderer = HTMLRendererService()
    pdf_generator = PDFGeneratorService()
    audit_log_service = AuditLogService(session)

    return ExecutiveSecurityReportService(
        session=session,
        dashboard_service=dashboard_service,
        executive_analytics_service=executive_analytics_service,
        threat_advisory_service=threat_advisory_service,
        html_renderer=html_renderer,
        pdf_generator=pdf_generator,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/executive",
    response_model=ExecutiveReportDataPayload,
    status_code=status.HTTP_200_OK,
    summary="Generate CISO Executive Security Report Payload",
    description="Assembles complete executive posture report payload, risk trends, vulnerability overview, attack surface metrics, and advisories.",
    dependencies=[Depends(require_permission("reports:create"))],
)
async def generate_executive_report(
    req: CreateExecutiveReportRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    reporting_service: Annotated[
        ExecutiveSecurityReportService, Depends(get_reporting_service)
    ],
) -> ExecutiveReportDataPayload:
    """Generate executive posture report data payload."""
    return await reporting_service.generate_executive_report_payload(current_user, req)


@router.get(
    "/{report_id}/pdf",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Download Executive Report PDF Document",
    description="Generates and streams binary PDF document for executive security report.",
    dependencies=[Depends(require_permission("reports:export"))],
)
async def download_executive_pdf_report(
    report_id: str,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    reporting_service: Annotated[
        ExecutiveSecurityReportService, Depends(get_reporting_service)
    ],
) -> Response:
    """Stream binary PDF report file."""
    pdf_bytes = await reporting_service.generate_pdf_report(current_user)
    filename = f"Vulnova_Executive_Report_{report_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get(
    "/{report_id}/html",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="View Executive Report HTML Document",
    description="Renders styled HTML document for interactive browser preview.",
    dependencies=[Depends(require_permission("reports:read"))],
)
async def get_executive_html_report(
    report_id: str,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    reporting_service: Annotated[
        ExecutiveSecurityReportService, Depends(get_reporting_service)
    ],
) -> HTMLResponse:
    """Render HTML report string."""
    html_content = await reporting_service.generate_html_report(current_user)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.get(
    "/{report_id}",
    response_model=ExecutiveReportMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Executive Report Metadata",
    description="Returns metadata description, status, and supported export formats for a report.",
    dependencies=[Depends(require_permission("reports:read"))],
)
async def get_report_metadata(
    report_id: str,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    reporting_service: Annotated[
        ExecutiveSecurityReportService, Depends(get_reporting_service)
    ],
) -> ExecutiveReportMetadataResponse:
    """Get report metadata details."""
    return await reporting_service.get_report_metadata(current_user, report_id)
