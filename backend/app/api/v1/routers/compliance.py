"""REST API Router for Compliance Framework Mapping & Reports."""

from typing import Annotated, List

import structlog
from fastapi import APIRouter, Depends, Path, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.compliance.compliance_service import ComplianceMappingService
from app.application.compliance.dto import (
    ComplianceControlDTO,
    ComplianceOverviewResponse,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/compliance", tags=["Compliance Intelligence"])


def get_compliance_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ComplianceMappingService:
    """Dependency provider for ComplianceMappingService."""
    audit_log_service = AuditLogService(session)
    return ComplianceMappingService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.get(
    "/{framework}/overview",
    response_model=ComplianceOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Framework Compliance Overview",
    description="Calculates compliance posture score, control status, and remediation priorities for a framework.",
    dependencies=[Depends(require_permission("compliance:read"))],
)
async def get_framework_overview(
    framework: Annotated[
        str, Path(description="Framework ID (owasp_top10, asvs_v4, pci_dss, iso27001)")
    ],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    compliance_service: Annotated[
        ComplianceMappingService, Depends(get_compliance_service)
    ],
) -> ComplianceOverviewResponse:
    """Return framework compliance overview payload."""
    return await compliance_service.get_compliance_overview(current_user, framework)


@router.get(
    "/{framework}/controls",
    response_model=List[ComplianceControlDTO],
    status_code=status.HTTP_200_OK,
    summary="Get Framework Compliance Controls",
    description="Returns all framework controls mapped to vulnerability findings and evidence artifacts.",
    dependencies=[Depends(require_permission("compliance:read"))],
)
async def get_framework_controls(
    framework: Annotated[
        str, Path(description="Framework ID (owasp_top10, asvs_v4, pci_dss, iso27001)")
    ],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    compliance_service: Annotated[
        ComplianceMappingService, Depends(get_compliance_service)
    ],
) -> List[ComplianceControlDTO]:
    """Return controls list for the specified framework."""
    return await compliance_service.get_compliance_controls(current_user, framework)


@router.get(
    "/{framework}/export",
    status_code=status.HTTP_200_OK,
    summary="Export Framework Compliance Report",
    description="Generates downloadable dynamic compliance report payload in JSON format.",
    dependencies=[Depends(require_permission("compliance:export"))],
)
async def export_compliance_report(
    framework: Annotated[
        str, Path(description="Framework ID (owasp_top10, asvs_v4, pci_dss, iso27001)")
    ],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    compliance_service: Annotated[
        ComplianceMappingService, Depends(get_compliance_service)
    ],
) -> Response:
    """Export compliance report payload."""
    report_data = await compliance_service.export_compliance_report(
        current_user, framework
    )
    filename = (
        f"Vulnova_Compliance_{framework}_{str(current_user.organization_id)[:8]}.json"
    )
    return JSONResponse(
        content=report_data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
