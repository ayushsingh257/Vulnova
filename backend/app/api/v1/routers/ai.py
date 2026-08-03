"""FastAPI Router for Multi-Provider LLM Gateway & Prompt Orchestrator (/api/v1/ai/*)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.ai.dto import (
    AIChatCompletionRequest,
    AIChatCompletionResponse,
    AIUsageSummaryDTO,
    CreatePromptTemplateRequest,
    CreateProviderRequest,
    LLMModelDTO,
    LLMProviderConfigDTO,
    PromptTemplateDTO,
    RegisterModelRequest,
)
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
