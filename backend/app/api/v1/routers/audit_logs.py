"""FastAPI Router for Security Audit Logs (/api/v1/audit-logs)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.dto import (
    AuditLogListResponse,
    AuditLogResponse,
)
from app.application.audit_logs.services import AuditLogService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/audit-logs", tags=["Security Audit Logs"])


@router.get(
    "",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("audit_logs:read"))],
)
async def list_audit_logs(
    action: Optional[str] = Query(
        None, description="Filter audit logs by action (e.g. auth.login, user.created)"
    ),
    resource_type: Optional[str] = Query(
        None,
        description="Filter audit logs by resource type (e.g. user, organization, api_key)",
    ),
    actor_user_id: Optional[UUID] = Query(
        None, description="Filter audit logs by actor user ID"
    ),
    limit: int = Query(50, ge=1, le=100, description="Page size limit (1–100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> AuditLogListResponse:
    """Query paginated security audit logs for the authenticated organization."""
    service = AuditLogService(session)
    return await service.list_audit_logs(
        organization_id=current_user.organization_id,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{audit_log_id}",
    response_model=AuditLogResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("audit_logs:read"))],
)
async def get_audit_log_detail(
    audit_log_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> AuditLogResponse:
    """Get details of a specific security audit log entry within the organization."""
    service = AuditLogService(session)
    return await service.get_audit_log_detail(
        audit_log_id=audit_log_id,
        organization_id=current_user.organization_id,
    )
