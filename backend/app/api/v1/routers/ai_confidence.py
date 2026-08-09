"""FastAPI REST Router for Phase 12.6 AI Finding Confidence & Remediation Workflow (/api/v1/findings, /api/v1/remediation)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.ai_confidence.confidence_service import (
    FindingConfidenceService,
)
from app.infrastructure.ai_confidence.dto import (
    FindingConfidenceResultDTO,
    FindingReviewDTO,
    FindingReviewRequestDTO,
    FindingVerificationAttemptDTO,
    RemediationApprovalDTO,
)
from app.infrastructure.ai_confidence.remediation_governance_service import (
    RemediationGovernanceService,
)
from app.infrastructure.ai_confidence.review_service import FindingReviewService
from app.infrastructure.ai_confidence.verification_service import (
    FindingVerificationService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(
    tags=["AI Finding Confidence & Human-in-the-Loop Remediation Workflow"]
)


@router.get(
    "/findings/{id}/confidence",
    response_model=FindingConfidenceResultDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_finding_confidence(
    id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> FindingConfidenceResultDTO:
    """Calculate and retrieve multi-dimensional confidence score for a security finding.

    Requires 'findings:read' permission.
    """
    service = FindingConfidenceService(session)
    result = await service.calculate_confidence(
        finding_id=id, organization_id=current_user.organization_id
    )
    await session.commit()
    return result


@router.post(
    "/findings/{id}/verify",
    response_model=FindingVerificationAttemptDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:triage"))],
)
async def verify_finding_authenticity(
    id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> FindingVerificationAttemptDTO:
    """Execute automated safe re-probe verification flow for a security finding.

    Requires 'findings:triage' permission.
    """
    service = FindingVerificationService(session)
    result = await service.verify_finding(
        finding_id=id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return result


@router.post(
    "/findings/{id}/review",
    response_model=FindingReviewDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:triage"))],
)
async def review_finding_decision(
    id: UUID,
    req: FindingReviewRequestDTO,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> FindingReviewDTO:
    """Submit human security analyst review decision (CONFIRM, FALSE_POSITIVE, ACCEPT_RISK, REQUEST_MORE_EVIDENCE).

    Requires 'findings:triage' permission.
    """
    service = FindingReviewService(session)
    result = await service.submit_review(
        finding_id=id,
        organization_id=current_user.organization_id,
        reviewer_id=current_user.id,
        decision=req.decision,
        comments=req.comments,
    )
    await session.commit()
    return result


@router.post(
    "/remediation/{id}/approve",
    response_model=RemediationApprovalDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:triage"))],
)
async def approve_remediation_plan(
    id: UUID,
    notes: Optional[str] = Query(None, description="Approval notes"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> RemediationApprovalDTO:
    """Approve an AI-recommended remediation patch plan for implementation (Analyst only).

    Requires 'findings:triage' permission.
    """
    service = RemediationGovernanceService(session)
    result = await service.approve_remediation(
        remediation_plan_id=id,
        organization_id=current_user.organization_id,
        approver_user_id=current_user.id,
        notes=notes,
    )
    await session.commit()
    return result


@router.post(
    "/remediation/{id}/reject",
    response_model=RemediationApprovalDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:triage"))],
)
async def reject_remediation_plan(
    id: UUID,
    notes: Optional[str] = Query(None, description="Rejection notes"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> RemediationApprovalDTO:
    """Reject an AI-recommended remediation patch plan.

    Requires 'findings:triage' permission.
    """
    service = RemediationGovernanceService(session)
    result = await service.reject_remediation(
        remediation_plan_id=id,
        organization_id=current_user.organization_id,
        approver_user_id=current_user.id,
        notes=notes,
    )
    await session.commit()
    return result
