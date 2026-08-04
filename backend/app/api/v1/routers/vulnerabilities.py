"""Vulnerability Triage, Evidence Record Viewer & AI Remediation REST Router."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.ai.remediation_service import AIRemediationService
from app.application.assessment.dto import (
    FindingAttackPathsResponse,
    FindingEvidenceResponse,
    FindingRemediationResponse,
    VulnerabilityIntelligenceResponse,
)
from app.application.finding.finding_intelligence_service import (
    FindingIntelligenceService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(
    prefix="/vulnerabilities", tags=["Vulnerability Intelligence & Triage"]
)


@router.get(
    "/{finding_id}",
    response_model=VulnerabilityIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Vulnerability Intelligence Record",
    description="Returns comprehensive vulnerability metadata, CVSS/EPSS scoring, risk context, scan origin, and triage history with strict tenant isolation.",
)
async def get_vulnerability_details(
    finding_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("findings:read")),
    db: AsyncSession = Depends(get_async_session),
) -> VulnerabilityIntelligenceResponse:
    """Retrieve vulnerability intelligence record."""
    service = FindingIntelligenceService(db)
    return await service.get_finding_details(current_user.organization_id, finding_id)


@router.get(
    "/{finding_id}/evidence",
    response_model=FindingEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Multi-Modal Evidence Artifacts",
    description="Returns structured proof evidence items (HTTP exchanges, screenshots, DOM snapshots, plugin traces) attached to a finding.",
)
async def get_vulnerability_evidence(
    finding_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("findings:read")),
    db: AsyncSession = Depends(get_async_session),
) -> FindingEvidenceResponse:
    """Retrieve finding proof evidence artifacts."""
    service = FindingIntelligenceService(db)
    return await service.get_finding_evidence(current_user.organization_id, finding_id)


@router.get(
    "/{finding_id}/attack-path",
    response_model=FindingAttackPathsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Attack Path Visualization Data",
    description="Returns graph visualization nodes and step progression describing vulnerability exploitation relationships.",
)
async def get_vulnerability_attack_paths(
    finding_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("findings:ai_attack_path")),
    db: AsyncSession = Depends(get_async_session),
) -> FindingAttackPathsResponse:
    """Retrieve attack chain relationship visualization data."""
    service = FindingIntelligenceService(db)
    return await service.get_finding_attack_paths(
        current_user.organization_id, finding_id
    )


@router.get(
    "/{finding_id}/remediation",
    response_model=FindingRemediationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Remediation Guidance & Patch Suggestions",
    description="Returns AI-synthesized remediation plan, fix steps, code patch suggestions, and verification checklist.",
)
async def get_vulnerability_remediation(
    finding_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("findings:ai_remediate")),
    db: AsyncSession = Depends(get_async_session),
) -> FindingRemediationResponse:
    """Retrieve AI remediation plan and patch suggestions."""
    service = FindingIntelligenceService(db)
    return await service.get_finding_remediation(
        current_user.organization_id, finding_id
    )


@router.post(
    "/{finding_id}/remediation-ai",
    response_model=FindingRemediationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger AI Remediation Guidance Generation",
    description="Executes on-demand AI remediation engine to generate advisory fix recommendations and verification steps for a finding.",
)
async def trigger_ai_remediation(
    finding_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("findings:ai_remediate")),
    db: AsyncSession = Depends(get_async_session),
) -> FindingRemediationResponse:
    """Trigger AI remediation generation and return formatted response."""
    remediation_ai_service = AIRemediationService(db)
    await remediation_ai_service.generate_remediation_plan(
        organization_id=current_user.organization_id,
        finding_id=finding_id,
        actor_user_id=current_user.id,
    )
    service = FindingIntelligenceService(db)
    return await service.get_finding_remediation(
        current_user.organization_id, finding_id
    )
