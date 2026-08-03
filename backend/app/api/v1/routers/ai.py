"""FastAPI Router for Multi-Provider LLM Gateway, Prompt Orchestrator & AI Analysis Engine (/api/v1/ai/*)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.ai.attack_path_service import AIAttackPathService
from app.application.ai.dto import (
    AIAttackPathDTO,
    AIChatCompletionRequest,
    AIChatCompletionResponse,
    AIFindingExplanationDTO,
    AIImpactAnalysisDTO,
    AIUsageSummaryDTO,
    CreatePromptTemplateRequest,
    CreateProviderRequest,
    GenerateAttackPathRequest,
    GenerateExplanationRequest,
    GenerateImpactAnalysisRequest,
    LLMModelDTO,
    LLMProviderConfigDTO,
    PromptTemplateDTO,
    RegisterModelRequest,
    ReviewAttackPathRequest,
)
from app.application.ai.explainer_service import AIFindingExplainerService
from app.application.ai.impact_analysis_service import ImpactAnalysisService
from app.application.ai.llm_gateway_service import LLMGatewayService
from app.application.ai.prompt_orchestrator_service import PromptOrchestratorService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(
    prefix="/ai", tags=["Multi-Provider LLM Gateway & Prompt Orchestrator"]
)


@router.post(
    "/chat/completions",
    response_model=AIChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:ai_analyze"))],
)
async def generate_chat_completion(
    req: AIChatCompletionRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AIChatCompletionResponse:
    """Execute chat completion request with automatic multi-provider fallback & health tracking.

    Requires authentication and 'findings:ai_analyze' RBAC permission (SECURITY_ANALYST+).
    """
    service = LLMGatewayService(session)
    return await service.generate_completion(current_user.organization_id, req)


@router.post(
    "/providers",
    response_model=LLMProviderConfigDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("organization:update"))],
)
async def configure_provider(
    req: CreateProviderRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> LLMProviderConfigDTO:
    """Configure a tenant-isolated LLM provider with encrypted API key.

    Requires authentication and 'organization:update' RBAC permission (ADMIN+).
    """
    service = LLMGatewayService(session)
    return await service.configure_provider(current_user, req)


@router.get(
    "/providers",
    response_model=List[LLMProviderConfigDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:ai_analyze"))],
)
async def list_providers(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[LLMProviderConfigDTO]:
    """List active configured LLM providers for organization.

    Requires authentication and 'findings:ai_analyze' RBAC permission.
    """
    service = LLMGatewayService(session)
    return await service.list_providers(current_user)


@router.post(
    "/models",
    response_model=LLMModelDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("organization:update"))],
)
async def register_model(
    req: RegisterModelRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> LLMModelDTO:
    """Register supported LLM model metadata and pricing limits.

    Requires authentication and 'organization:update' RBAC permission (ADMIN+).
    """
    service = LLMGatewayService(session)
    return await service.register_model(current_user, req)


@router.get(
    "/models",
    response_model=List[LLMModelDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:ai_analyze"))],
)
async def list_models(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[LLMModelDTO]:
    """List registered LLM models for organization.

    Requires authentication and 'findings:ai_analyze' RBAC permission.
    """
    service = LLMGatewayService(session)
    return await service.list_models(current_user)


@router.post(
    "/prompts",
    response_model=PromptTemplateDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("organization:update"))],
)
async def create_prompt_template(
    req: CreatePromptTemplateRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PromptTemplateDTO:
    """Create a new immutable version of a security prompt template.

    Requires authentication and 'organization:update' RBAC permission (ADMIN+).
    """
    orchestrator = PromptOrchestratorService(session)
    return await orchestrator.create_prompt_template(current_user, req)


@router.get(
    "/prompts",
    response_model=List[PromptTemplateDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:ai_analyze"))],
)
async def list_prompt_templates(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[PromptTemplateDTO]:
    """List active security prompt templates for organization.

    Requires authentication and 'findings:ai_analyze' RBAC permission.
    """
    orchestrator = PromptOrchestratorService(session)
    return await orchestrator.list_prompt_templates(current_user)


@router.get(
    "/usage",
    response_model=AIUsageSummaryDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:ai_analyze"))],
)
async def get_token_usage_summary(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AIUsageSummaryDTO:
    """Query organizational token consumption, latency, & cost analytics.

    Requires authentication and 'findings:ai_analyze' RBAC permission.
    """
    service = LLMGatewayService(session)
    return await service.get_token_usage_summary(current_user)


# ── Phase 5.2: AI Finding Explainer & Impact Analysis Endpoints ──


@router.post(
    "/findings/{finding_id}/explain",
    response_model=AIFindingExplanationDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("findings:ai_explain"))],
)
async def generate_finding_explanation(
    finding_id: str = Path(..., description="UUID of the security finding to explain"),
    req: Optional[GenerateExplanationRequest] = None,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AIFindingExplanationDTO:
    """Generate an AI-powered explanation for a security finding.

    Requires authentication and 'findings:ai_explain' RBAC permission (SECURITY_ANALYST+).
    """
    from uuid import UUID as _UUID

    service = AIFindingExplainerService(session)
    return await service.generate_explanation(
        organization_id=current_user.organization_id,
        finding_id=_UUID(finding_id),
        actor_user_id=current_user.id,
        model_alias=req.model_alias if req else None,
        temperature=req.temperature if req else 0.2,
    )


@router.get(
    "/findings/{finding_id}/explanation",
    response_model=Optional[AIFindingExplanationDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_finding_explanation(
    finding_id: str = Path(..., description="UUID of the security finding"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[AIFindingExplanationDTO]:
    """Retrieve the most recent AI explanation for a finding.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    from uuid import UUID as _UUID

    service = AIFindingExplainerService(session)
    return await service.get_explanation(
        organization_id=current_user.organization_id,
        finding_id=_UUID(finding_id),
    )


@router.post(
    "/findings/{finding_id}/impact",
    response_model=AIImpactAnalysisDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("findings:ai_explain"))],
)
async def generate_impact_analysis(
    finding_id: str = Path(..., description="UUID of the security finding to analyze"),
    req: Optional[GenerateImpactAnalysisRequest] = None,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AIImpactAnalysisDTO:
    """Generate an AI-powered impact analysis for a security finding.

    Requires authentication and 'findings:ai_explain' RBAC permission (SECURITY_ANALYST+).
    """
    from uuid import UUID as _UUID

    service = ImpactAnalysisService(session)
    return await service.generate_impact_analysis(
        organization_id=current_user.organization_id,
        finding_id=_UUID(finding_id),
        actor_user_id=current_user.id,
        model_alias=req.model_alias if req else None,
        temperature=req.temperature if req else 0.2,
    )


@router.get(
    "/findings/{finding_id}/impact",
    response_model=Optional[AIImpactAnalysisDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_impact_analysis(
    finding_id: str = Path(..., description="UUID of the security finding"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[AIImpactAnalysisDTO]:
    """Retrieve the most recent AI impact analysis for a finding.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    from uuid import UUID as _UUID

    service = ImpactAnalysisService(session)
    return await service.get_impact_analysis(
        organization_id=current_user.organization_id,
        finding_id=_UUID(finding_id),
    )


@router.get(
    "/explanations",
    response_model=List[AIFindingExplanationDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def list_explanations(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[AIFindingExplanationDTO]:
    """List AI explanation history for organization.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    service = AIFindingExplainerService(session)
    return await service.list_explanations(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/impact-analyses",
    response_model=List[AIImpactAnalysisDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def list_impact_analyses(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[AIImpactAnalysisDTO]:
    """List AI impact analysis history for organization.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    service = ImpactAnalysisService(session)
    return await service.list_impact_analyses(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


# ── Phase 5.3: AI Attack Path Synthesis Endpoints ──


@router.post(
    "/findings/{finding_id}/attack-paths",
    response_model=AIAttackPathDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("findings:ai_attack_path"))],
)
async def generate_attack_path(
    finding_id: str = Path(..., description="UUID of the security finding"),
    req: Optional[GenerateAttackPathRequest] = None,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AIAttackPathDTO:
    """Synthesize an evidence-grounded AI attack path for a security finding.

    Requires authentication and 'findings:ai_attack_path' RBAC permission (SECURITY_ANALYST+).
    """
    from uuid import UUID as _UUID

    service = AIAttackPathService(session)
    return await service.generate_attack_path(
        organization_id=current_user.organization_id,
        finding_id=_UUID(finding_id),
        actor_user_id=current_user.id,
        model_alias=req.model_alias if req else None,
        temperature=req.temperature if req else 0.2,
    )


@router.get(
    "/findings/{finding_id}/attack-paths",
    response_model=List[AIAttackPathDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def list_attack_paths_for_finding(
    finding_id: str = Path(..., description="UUID of the security finding"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[AIAttackPathDTO]:
    """Retrieve all synthesized attack paths for a specific finding.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    from uuid import UUID as _UUID

    service = AIAttackPathService(session)
    return await service.list_attack_paths_for_finding(
        organization_id=current_user.organization_id,
        finding_id=_UUID(finding_id),
    )


@router.get(
    "/attack-paths/{path_id}",
    response_model=Optional[AIAttackPathDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_attack_path_by_id(
    path_id: str = Path(..., description="UUID of the attack path"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[AIAttackPathDTO]:
    """Retrieve single attack path by ID with all steps.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    from uuid import UUID as _UUID

    service = AIAttackPathService(session)
    return await service.get_attack_path(
        organization_id=current_user.organization_id,
        path_id=_UUID(path_id),
    )


@router.get(
    "/attack-paths",
    response_model=List[AIAttackPathDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def list_attack_paths(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[AIAttackPathDTO]:
    """List organizational attack path history.

    Requires authentication and 'findings:read' RBAC permission (VIEWER+).
    """
    service = AIAttackPathService(session)
    return await service.list_attack_paths(
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/attack-paths/{path_id}/review",
    response_model=AIAttackPathDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:ai_attack_path"))],
)
async def review_attack_path(
    req: ReviewAttackPathRequest,
    path_id: str = Path(..., description="UUID of the attack path to review"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AIAttackPathDTO:
    """Record SOC analyst review status and feedback notes on an attack path.

    Requires authentication and 'findings:ai_attack_path' RBAC permission (SECURITY_ANALYST+).
    """
    from uuid import UUID as _UUID

    service = AIAttackPathService(session)
    return await service.review_attack_path(
        organization_id=current_user.organization_id,
        path_id=_UUID(path_id),
        reviewer_id=current_user.id,
        req=req,
    )
