"""Multi-Provider LLM Gateway Application Service with Provider Fallback & Cooldown Tracking."""

import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    AIChatCompletionRequest,
    AIChatCompletionResponse,
    AIUsageSummaryDTO,
    CreateProviderRequest,
    LLMModelDTO,
    LLMProviderConfigDTO,
    RegisterModelRequest,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import (
    LLMProviderException,
    ValidationException,
)
from app.core.logging import get_logger
from app.domain.entities.ai import (
    LLMMessage,
    LLMProviderType,
    LLMRequest,
)
from app.infrastructure.ai.providers import get_adapter_for_provider
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.llm_gateway_repository import (
    LLMGatewayRepository,
)
from app.security.encryption import SecretEncryptionService

logger = get_logger("vulnova.llm_gateway_service")


class LLMGatewayService:
    """Application Service managing multi-provider LLM request execution, automatic fallback routing, & provider health tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai_repo = LLMGatewayRepository(session)
        self.audit_service = AuditLogService(session)
        self.encryption_service = SecretEncryptionService()

    async def generate_completion(
        self, organization_id: UUID, req: AIChatCompletionRequest
    ) -> AIChatCompletionResponse:
        """Execute chat completion request with automatic multi-provider fallback & health tracking."""
        start_time = time.time()

        # Query active, healthy providers for organization ordered by priority
        providers = await self.ai_repo.list_active_providers(
            organization_id, healthy_only=True
        )

        if not providers:
            # Fallback to local Ollama adapter if no external providers are configured or all are in cooldown
            logger.info(
                "llm_gateway.no_active_healthy_providers_falling_back_to_local_ollama"
            )
            local_req = LLMRequest(
                messages=[
                    LLMMessage(role=m.role, content=m.content) for m in req.messages
                ],
                model_alias=req.model_alias or "llama3",
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )
            adapter = get_adapter_for_provider(LLMProviderType.OLLAMA)
            try:
                res = await adapter.execute(local_req)
                await self.ai_repo.log_request(
                    organization_id=organization_id,
                    provider_type="OLLAMA",
                    model_used=res.model_used,
                    prompt_tokens=res.prompt_tokens,
                    completion_tokens=res.completion_tokens,
                    total_tokens=res.total_tokens,
                    latency_ms=res.latency_ms,
                    cost_usd=0.0,
                    status="SUCCESS",
                    prompt_category=req.prompt_category,
                )
                return AIChatCompletionResponse(
                    content=res.content,
                    model_used=res.model_used,
                    provider_used="OLLAMA",
                    prompt_tokens=res.prompt_tokens,
                    completion_tokens=res.completion_tokens,
                    total_tokens=res.total_tokens,
                    latency_ms=res.latency_ms,
                    cost_usd=0.0,
                    status="SUCCESS",
                )
            except Exception as e:
                err_msg = f"All providers in cooldown and local Ollama fallback failed: {str(e)}"
                await self.ai_repo.log_request(
                    organization_id=organization_id,
                    provider_type="OLLAMA",
                    model_used=req.model_alias or "llama3",
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=int((time.time() - start_time) * 1000),
                    cost_usd=0.0,
                    status="FAILED",
                    prompt_category=req.prompt_category,
                    error_message=err_msg,
                )
                raise LLMProviderException(err_msg) from e

        # Attempt execution across healthy providers in priority order
        last_exception: Optional[Exception] = None
        for provider_model in providers:
            try:
                ptype = LLMProviderType(provider_model.provider_type)
            except ValueError:
                ptype = LLMProviderType.OPENAI

            adapter = get_adapter_for_provider(ptype)

            # Decrypt API key
            plain_api_key = ""
            if provider_model.encrypted_api_key:
                try:
                    plain_api_key = self.encryption_service.decrypt_secret(
                        provider_model.encrypted_api_key
                    )
                except Exception:
                    plain_api_key = ""

            domain_req = LLMRequest(
                messages=[
                    LLMMessage(role=m.role, content=m.content) for m in req.messages
                ],
                model_alias=req.model_alias or "gpt-4o",
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )

            try:
                logger.info(
                    "llm_gateway.executing_provider",
                    provider=provider_model.name,
                    type=ptype.value,
                )
                res = await adapter.execute(
                    domain_req,
                    api_key=plain_api_key,
                    endpoint=provider_model.api_endpoint,
                )

                # Reset failure count on success
                await self.ai_repo.record_provider_success(
                    organization_id, provider_model.id
                )

                # Calculate estimated USD cost
                cost_usd = self._calculate_cost(
                    domain_req.model_alias, res.prompt_tokens, res.completion_tokens
                )

                # Log request audit trail
                await self.ai_repo.log_request(
                    organization_id=organization_id,
                    provider_type=ptype.value,
                    model_used=res.model_used,
                    prompt_tokens=res.prompt_tokens,
                    completion_tokens=res.completion_tokens,
                    total_tokens=res.total_tokens,
                    latency_ms=res.latency_ms,
                    cost_usd=cost_usd,
                    status="SUCCESS",
                    prompt_category=req.prompt_category,
                )

                return AIChatCompletionResponse(
                    content=res.content,
                    model_used=res.model_used,
                    provider_used=ptype.value,
                    prompt_tokens=res.prompt_tokens,
                    completion_tokens=res.completion_tokens,
                    total_tokens=res.total_tokens,
                    latency_ms=res.latency_ms,
                    cost_usd=cost_usd,
                    status="SUCCESS",
                )
            except Exception as e:
                logger.warning(
                    "llm_gateway.provider_failed_triggering_fallback",
                    provider=provider_model.name,
                    error=str(e),
                )
                await self.ai_repo.record_provider_failure(
                    organization_id, provider_model.id
                )
                last_exception = e
                continue

        # If all configured providers failed, raise error
        err_str = (
            f"All configured LLM providers failed. Last error: {str(last_exception)}"
        )
        await self.ai_repo.log_request(
            organization_id=organization_id,
            provider_type="GATEWAY",
            model_used=req.model_alias or "unknown",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=int((time.time() - start_time) * 1000),
            cost_usd=0.0,
            status="FAILED",
            prompt_category=req.prompt_category,
            error_message=err_str,
        )
        raise LLMProviderException(err_str) from last_exception

    def _calculate_cost(
        self, model_alias: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Calculate estimated cost in USD based on model pricing heuristics."""
        alias_lower = (model_alias or "").lower()
        if "gpt-4o" in alias_lower:
            prompt_cost = (prompt_tokens / 1000.0) * 0.005
            completion_cost = (completion_tokens / 1000.0) * 0.015
            return round(prompt_cost + completion_cost, 6)
        elif "claude-3-5" in alias_lower:
            prompt_cost = (prompt_tokens / 1000.0) * 0.003
            completion_cost = (completion_tokens / 1000.0) * 0.015
            return round(prompt_cost + completion_cost, 6)
        return 0.0

    async def configure_provider(
        self, current_user: UserModel, req: CreateProviderRequest
    ) -> LLMProviderConfigDTO:
        """Configure a tenant-isolated LLM provider with encrypted API key."""
        org_id = current_user.organization_id

        try:
            ptype = LLMProviderType(req.provider_type.upper())
        except ValueError as err:
            raise ValidationException(
                f"Invalid provider_type '{req.provider_type}'. Allowed values: {[t.value for t in LLMProviderType]}"
            ) from err

        encrypted_key: Optional[str] = None
        if req.api_key:
            encrypted_key = self.encryption_service.encrypt_secret(req.api_key)

        provider_model = await self.ai_repo.create_provider(
            organization_id=org_id,
            provider_type=ptype.value,
            name=req.name,
            api_endpoint=req.api_endpoint,
            encrypted_api_key=encrypted_key,
            priority=req.priority,
        )

        await self.audit_service.record_event(
            organization_id=org_id,
            action="llm_provider.configured",
            resource_type="llm_provider",
            resource_id=str(provider_model.id),
            actor_user_id=current_user.id,
            details={
                "name": provider_model.name,
                "provider_type": provider_model.provider_type,
            },
        )

        return LLMProviderConfigDTO(
            id=str(provider_model.id),
            provider_type=provider_model.provider_type,
            name=provider_model.name,
            api_endpoint=provider_model.api_endpoint,
            priority=provider_model.priority,
            is_active=provider_model.is_active,
            is_healthy=provider_model.is_healthy,
            consecutive_failures=provider_model.consecutive_failures,
            cooldown_until=(
                str(provider_model.cooldown_until)
                if provider_model.cooldown_until
                else None
            ),
            created_at=str(provider_model.created_at),
        )

    async def list_providers(
        self, current_user: UserModel
    ) -> List[LLMProviderConfigDTO]:
        """List configured active LLM providers for tenant organization."""
        org_id = current_user.organization_id
        providers = await self.ai_repo.list_active_providers(org_id, healthy_only=False)
        return [
            LLMProviderConfigDTO(
                id=str(p.id),
                provider_type=p.provider_type,
                name=p.name,
                api_endpoint=p.api_endpoint,
                priority=p.priority,
                is_active=p.is_active,
                is_healthy=p.is_healthy,
                consecutive_failures=p.consecutive_failures,
                cooldown_until=str(p.cooldown_until) if p.cooldown_until else None,
                created_at=str(p.created_at),
            )
            for p in providers
        ]

    async def register_model(
        self, current_user: UserModel, req: RegisterModelRequest
    ) -> LLMModelDTO:
        """Register model metadata and pricing metrics."""
        org_id = current_user.organization_id
        model = await self.ai_repo.register_model(
            organization_id=org_id,
            provider_type=req.provider_type.upper(),
            model_alias=req.model_alias,
            model_name=req.model_name,
            context_window_tokens=req.context_window_tokens,
            max_output_tokens=req.max_output_tokens,
            input_cost_per_1k_tokens=req.input_cost_per_1k_tokens,
            output_cost_per_1k_tokens=req.output_cost_per_1k_tokens,
            is_default=req.is_default,
        )
        return LLMModelDTO(
            id=str(model.id),
            provider_type=model.provider_type,
            model_alias=model.model_alias,
            model_name=model.model_name,
            context_window_tokens=model.context_window_tokens,
            max_output_tokens=model.max_output_tokens,
            input_cost_per_1k_tokens=float(model.input_cost_per_1k_tokens),
            output_cost_per_1k_tokens=float(model.output_cost_per_1k_tokens),
            is_default=model.is_default,
            created_at=str(model.created_at),
        )

    async def list_models(self, current_user: UserModel) -> List[LLMModelDTO]:
        """List registered LLM models for organization."""
        org_id = current_user.organization_id
        models = await self.ai_repo.list_models(org_id)
        return [
            LLMModelDTO(
                id=str(m.id),
                provider_type=m.provider_type,
                model_alias=m.model_alias,
                model_name=m.model_name,
                context_window_tokens=m.context_window_tokens,
                max_output_tokens=m.max_output_tokens,
                input_cost_per_1k_tokens=float(m.input_cost_per_1k_tokens),
                output_cost_per_1k_tokens=float(m.output_cost_per_1k_tokens),
                is_default=m.is_default,
                created_at=str(m.created_at),
            )
            for m in models
        ]

    async def get_token_usage_summary(
        self, current_user: UserModel
    ) -> AIUsageSummaryDTO:
        """Query token consumption and USD cost analytics for organization."""
        org_id = current_user.organization_id
        summary_dict = await self.ai_repo.get_usage_summary(org_id)
        return (
            AIUsageSummaryDTO(**summary_dict) if summary_dict else AIUsageSummaryDTO()
        )
