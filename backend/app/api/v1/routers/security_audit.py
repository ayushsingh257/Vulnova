from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.infrastructure.security_audit.audit_service import SecurityAuditService
from app.infrastructure.security_audit.dto import (
    RemediateFindingRequestDTO,
    RunSecurityAuditRequestDTO,
    SecurityAuditExecutionDTO,
    SecurityAuditFindingDTO,
    SecurityAuditStatusDTO,
)

router = APIRouter(
    prefix="/security-audit", tags=["Security Audit & Penetration Testing"]
)


@router.get(
    "/status",
    response_model=SecurityAuditStatusDTO,
    summary="Get overall security audit posture status",
    dependencies=[Depends(require_permission("admin:manage"))],
)
async def get_security_audit_status(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> SecurityAuditStatusDTO:
    """Retrieve high-level security audit posture, total vulnerabilities, remediation rates, and compliance grade."""
    service = SecurityAuditService(session)
    return await service.get_audit_status(current_user.organization_id)


@router.get(
    "/findings",
    response_model=List[SecurityAuditFindingDTO],
    summary="List filtered security audit findings",
    dependencies=[Depends(require_permission("admin:manage"))],
)
async def list_security_audit_findings(
    category: Optional[str] = Query(
        None,
        description="Filter by security audit category (SAST, SCA, CONFIGURATION, etc.)",
    ),
    severity: Optional[str] = Query(
        None, description="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by remediation status (OPEN, REMEDIATED, ACCEPTED_RISK, FALSE_POSITIVE)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[SecurityAuditFindingDTO]:
    """Retrieve paginated list of security audit findings for the authenticated tenant."""
    service = SecurityAuditService(session)
    findings, _ = await service.list_findings(
        organization_id=current_user.organization_id,
        category=category,
        severity=severity,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return findings


@router.post(
    "/run",
    response_model=SecurityAuditExecutionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger automated multi-domain security audit and penetration verification",
    dependencies=[Depends(require_permission("admin:manage"))],
)
async def run_security_audit(
    request: RunSecurityAuditRequestDTO,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> SecurityAuditExecutionDTO:
    """Execute complete SAST, SCA, Configuration, API, Authentication, RBAC, Secret, and Container security audit."""
    service = SecurityAuditService(session)
    return await service.execute_security_audit(
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        request=request,
    )


@router.patch(
    "/findings/{finding_id}/remediate",
    response_model=SecurityAuditFindingDTO,
    summary="Update finding remediation status with audit trail",
    dependencies=[Depends(require_permission("admin:manage"))],
)
async def remediate_audit_finding(
    finding_id: str,
    request: RemediateFindingRequestDTO,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> SecurityAuditFindingDTO:
    """Transition finding remediation status (REMEDIATED, ACCEPTED_RISK, FALSE_POSITIVE) and record audit log."""
    service = SecurityAuditService(session)
    try:
        return await service.remediate_finding(
            organization_id=current_user.organization_id,
            finding_id=finding_id,
            request=request,
            actor_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
