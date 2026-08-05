"""REST API Router for Developer Technical Remediation Exports (JSON, CSV, Markdown)."""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.reporting.developer_export_service import DeveloperExportService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reports/export", tags=["Developer Technical Exports"])


def get_developer_export_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DeveloperExportService:
    """Dependency provider for DeveloperExportService."""
    audit_log_service = AuditLogService(session)
    return DeveloperExportService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.get(
    "/json",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Organizational Findings in Memory-Efficient JSON Stream",
    description="Streams all non-duplicate security findings for the tenant in JSON format.",
    dependencies=[Depends(require_permission("reports:export"))],
)
async def export_bulk_json(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    export_service: Annotated[
        DeveloperExportService, Depends(get_developer_export_service)
    ],
) -> StreamingResponse:
    """Stream bulk findings as JSON array."""
    filename = f"Vulnova_Export_Findings_{str(current_user.organization_id)[:8]}.json"
    return StreamingResponse(
        export_service.export_json_stream(current_user),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get(
    "/csv",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Organizational Findings in Memory-Efficient CSV Stream",
    description="Streams all non-duplicate security findings for the tenant in CSV format.",
    dependencies=[Depends(require_permission("reports:export"))],
)
async def export_bulk_csv(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    export_service: Annotated[
        DeveloperExportService, Depends(get_developer_export_service)
    ],
) -> StreamingResponse:
    """Stream bulk findings as CSV file."""
    filename = f"Vulnova_Export_Findings_{str(current_user.organization_id)[:8]}.csv"
    return StreamingResponse(
        export_service.export_csv_stream(current_user),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get(
    "/markdown",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Export Organizational Findings in Memory-Efficient Markdown Stream",
    description="Streams all non-duplicate security findings for the tenant in Markdown format.",
    dependencies=[Depends(require_permission("reports:export"))],
)
async def export_bulk_markdown(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    export_service: Annotated[
        DeveloperExportService, Depends(get_developer_export_service)
    ],
) -> StreamingResponse:
    """Stream bulk findings as Markdown document."""
    filename = f"Vulnova_Export_Findings_{str(current_user.organization_id)[:8]}.md"
    return StreamingResponse(
        export_service.export_markdown_stream(current_user),
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


@router.get(
    "/{finding_id}",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Export Single Vulnerability Technical Package",
    description="Exports detailed intelligence, evidence, attack paths, and AI remediation for a specific finding in JSON, CSV, or Markdown.",
    dependencies=[Depends(require_permission("reports:export"))],
)
async def export_single_finding(
    finding_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    export_service: Annotated[
        DeveloperExportService, Depends(get_developer_export_service)
    ],
    format: Annotated[
        str, Query(description="Export format: 'json', 'csv', or 'markdown'")
    ] = "markdown",
) -> Response:
    """Export single vulnerability technical remediation package."""
    content, media_type, filename = await export_service.export_single_finding(
        current_user, finding_id, format
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
