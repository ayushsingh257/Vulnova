"""FastAPI Router for Enterprise Finding Triage & Automated Suppression Rules (/api/v1/findings/triage, /api/v1/findings/suppression-rules)."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dto import (
    BulkTriageRequest,
    CreateSuppressionRuleRequest,
    FindingTriageHistoryDTO,
    SuppressionRuleDTO,
    TriageFindingRequest,
    TriageResponse,
)
from app.application.assessment.finding_triage_service import FindingTriageService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(tags=["Enterprise Finding Triage & Vulnerability Lifecycle Engine"])


@router.patch(
    "/findings/{finding_id}/triage",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:triage"))],
)
async def triage_finding(
    finding_id: UUID,
    req: TriageFindingRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> TriageResponse:
    """Update finding triage status (CONFIRMED, FALSE_POSITIVE, RISK_ACCEPTED, REMEDIATED, REOPENED).

    Requires authentication and 'findings:triage' RBAC permission (SECURITY_ANALYST+).
    """
    service = FindingTriageService(session)
    return await service.triage_finding(current_user, finding_id, req)


@router.post(
    "/findings/triage/bulk",
    response_model=List[TriageResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:triage"))],
)
async def bulk_triage_findings(
    req: BulkTriageRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[TriageResponse]:
    """Execute bulk triage status updates on multiple findings.

    Requires authentication and 'findings:triage' RBAC permission (SECURITY_ANALYST+).
    """
    service = FindingTriageService(session)
    return await service.bulk_triage_findings(current_user, req)


@router.get(
    "/findings/{finding_id}/triage-history",
    response_model=List[FindingTriageHistoryDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_finding_triage_history(
    finding_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[FindingTriageHistoryDTO]:
    """Query immutable historical triage audit records for a finding.

    Requires authentication and 'findings:read' RBAC permission.
    """
    service = FindingTriageService(session)
    return await service.get_finding_triage_history(current_user, finding_id)


@router.post(
    "/findings/suppression-rules",
    response_model=SuppressionRuleDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("findings:suppress"))],
)
async def create_suppression_rule(
    req: CreateSuppressionRuleRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SuppressionRuleDTO:
    """Create an automated finding suppression rule for an organization.

    Requires authentication and 'findings:suppress' RBAC permission (ADMIN+).
    """
    service = FindingTriageService(session)
    return await service.create_suppression_rule(current_user, req)


@router.get(
    "/findings/suppression-rules",
    response_model=List[SuppressionRuleDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def list_suppression_rules(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[SuppressionRuleDTO]:
    """List active automated finding suppression rules for tenant organization.

    Requires authentication and 'findings:read' RBAC permission.
    """
    service = FindingTriageService(session)
    return await service.list_suppression_rules(current_user)


@router.delete(
    "/findings/suppression-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("findings:suppress"))],
)
async def delete_suppression_rule(
    rule_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Deactivate or delete an automated finding suppression rule.

    Requires authentication and 'findings:suppress' RBAC permission (ADMIN+).
    """
    service = FindingTriageService(session)
    await service.delete_suppression_rule(current_user, rule_id)
