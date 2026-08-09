"""FastAPI REST Router for Phase 12.5 Target Verification & Scan Approvals (/api/v1/targets & /api/v1/scan-approvals)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.infrastructure.target_authorization.approval_service import (
    ScanApprovalService,
)
from app.infrastructure.target_authorization.dto import (
    ScanApprovalRequestCreateDTO,
    ScanApprovalRequestDTO,
    TargetVerificationChallengeDTO,
    TargetVerificationResultDTO,
    VerificationType,
)
from app.infrastructure.target_authorization.verification_service import (
    TargetVerificationService,
)

router = APIRouter(tags=["Target Ownership Verification & Scan Authorization"])


# ── Target Verification Endpoints ──────────────────────


@router.post(
    "/targets/{id}/verify",
    response_model=TargetVerificationResultDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:update"))],
)
async def verify_target_ownership(
    id: UUID,
    challenge_type: Optional[VerificationType] = Query(
        None, description="Optional verification type: DNS_TXT or HTTP_WELL_KNOWN"
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> TargetVerificationResultDTO:
    """Execute target ownership verification check (DNS TXT or HTTP well-known token).

    Requires 'targets:update' permission.
    """
    service = TargetVerificationService(session)

    # Ensure challenge exists or create one
    if challenge_type:
        await service.create_challenge(
            target_id=id,
            organization_id=current_user.organization_id,
            verification_type=challenge_type,
            actor_user_id=current_user.id,
        )

    result = await service.verify_target_ownership(
        target_id=id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return result


@router.get(
    "/targets/{id}/verification-status",
    response_model=TargetVerificationChallengeDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:read"))],
)
async def get_target_verification_status(
    id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> TargetVerificationChallengeDTO:
    """Retrieve latest target ownership verification status and instructions.

    Requires 'targets:read' permission.
    """
    service = TargetVerificationService(session)
    result = await service.get_verification_status(
        target_id=id, organization_id=current_user.organization_id
    )
    await session.commit()
    return result


# ── Scan Approval Endpoints ──────────────────────────


@router.post(
    "/scan-approvals",
    response_model=ScanApprovalRequestDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("scans:create"))],
)
async def create_scan_approval_request(
    req: ScanApprovalRequestCreateDTO,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanApprovalRequestDTO:
    """Create a scan authorization approval request for a sensitive target asset.

    Requires 'scans:create' permission.
    """
    service = ScanApprovalService(session)
    result = await service.create_approval_request(
        organization_id=current_user.organization_id,
        target_id=req.target_id,
        requested_by=current_user.id,
        scan_job_id=req.scan_job_id,
        reason=req.reason,
    )
    await session.commit()
    return result


@router.get(
    "/scan-approvals",
    response_model=List[ScanApprovalRequestDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def list_scan_approval_requests(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Optional status filter: REQUESTED, PENDING_APPROVAL, APPROVED, REJECTED",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[ScanApprovalRequestDTO]:
    """List paginated scan authorization approval requests for the organization.

    Requires 'scans:read' permission.
    """
    service = ScanApprovalService(session)
    items, _ = await service.list_approval_requests(
        organization_id=current_user.organization_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return items


@router.post(
    "/scan-approvals/{id}/approve",
    response_model=ScanApprovalRequestDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
)
async def approve_scan_request(
    id: UUID,
    reason: Optional[str] = Query(None, description="Optional approval notes"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanApprovalRequestDTO:
    """Approve a pending scan authorization request for a sensitive target asset.

    Requires 'admin:manage' permission.
    """
    service = ScanApprovalService(session)
    result = await service.approve_request(
        request_id=id,
        organization_id=current_user.organization_id,
        approver_user_id=current_user.id,
        reason=reason,
    )
    await session.commit()
    return result


@router.post(
    "/scan-approvals/{id}/reject",
    response_model=ScanApprovalRequestDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("admin:manage"))],
)
async def reject_scan_request(
    id: UUID,
    reason: str = Query(
        "Admin rejected scan authorization", description="Reason for rejection"
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanApprovalRequestDTO:
    """Reject a pending scan authorization request for a sensitive target asset.

    Requires 'admin:manage' permission.
    """
    service = ScanApprovalService(session)
    result = await service.reject_request(
        request_id=id,
        organization_id=current_user.organization_id,
        approver_user_id=current_user.id,
        rejection_reason=reason,
    )
    await session.commit()
    return result
