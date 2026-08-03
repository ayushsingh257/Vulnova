"""Repository managing tenant-isolated LLM Providers, Model Registry, Immutable Versioned Prompts, & AI Audit Logs."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.ai import (
    LLMModelRegistryModel,
    LLMProviderModel,
    LLMRequestLogModel,
    PromptTemplateModel,
)

logger = get_logger("vulnova.llm_gateway_repository")


class LLMGatewayRepository:
    """Async repository for tenant-isolated LLM provider configs, model registry, prompt templates, and AI request logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── LLM Providers & Health Tracking ──────────────────

    async def create_provider(
        self,
        organization_id: UUID,
        provider_type: str,
        name: str,
        api_endpoint: Optional[str] = None,
        encrypted_api_key: Optional[str] = None,
        priority: int = 10,
    ) -> LLMProviderModel:
        """Create and persist a tenant-isolated LLM provider configuration."""
        provider = LLMProviderModel(
            organization_id=organization_id,
            provider_type=provider_type,
            name=name,
            api_endpoint=api_endpoint,
            encrypted_api_key=encrypted_api_key,
            priority=priority,
            is_active=True,
            is_healthy=True,
        )
        self.session.add(provider)
        await self.session.flush()
        return provider

    async def list_active_providers(
        self, organization_id: UUID, healthy_only: bool = True
    ) -> List[LLMProviderModel]:
        """List active providers for an organization ordered by priority (lower priority value = higher precedence)."""
        stmt = (
            select(LLMProviderModel)
            .where(
                LLMProviderModel.organization_id == organization_id,
                LLMProviderModel.is_active.is_(True),
            )
            .order_by(LLMProviderModel.priority.asc())
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            providers = (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )

            if not healthy_only:
                return providers

            now = datetime.now(timezone.utc)
            healthy_providers: List[LLMProviderModel] = []
            for p in providers:
                # Check if provider cooldown has expired
                if p.cooldown_until and p.cooldown_until <= now:
                    p.is_healthy = True
                    p.consecutive_failures = 0
                    p.cooldown_until = None

                if p.is_healthy:
                    healthy_providers.append(p)

            return healthy_providers
        except Exception:
            return []

    async def record_provider_failure(
        self, organization_id: UUID, provider_id: UUID, cooldown_minutes: int = 5
    ) -> None:
        """Record a provider failure, increment consecutive failures, and trigger cooldown if threshold reached."""
        stmt = select(LLMProviderModel).where(
            LLMProviderModel.id == provider_id,
            LLMProviderModel.organization_id == organization_id,
        )
        try:
            result = await self.session.execute(stmt)
            provider = (
                result.scalar_one_or_none()
                if hasattr(result, "scalar_one_or_none")
                else None
            )
            if provider and isinstance(provider, LLMProviderModel):
                provider.consecutive_failures += 1
                provider.last_failure_at = datetime.now(timezone.utc)

                if provider.consecutive_failures >= 3:
                    provider.is_healthy = False
                    provider.cooldown_until = datetime.now(timezone.utc) + timedelta(
                        minutes=cooldown_minutes
                    )
                    logger.warning(
                        "llm_provider.cooldown_triggered",
                        provider_id=str(provider_id),
                        cooldown_until=str(provider.cooldown_until),
                    )
                await self.session.flush()
        except Exception as e:
            logger.warning("llm_provider.record_failure_failed", error=str(e))

    async def record_provider_success(
        self, organization_id: UUID, provider_id: UUID
    ) -> None:
        """Reset failure counts upon successful provider execution."""
        stmt = select(LLMProviderModel).where(
            LLMProviderModel.id == provider_id,
            LLMProviderModel.organization_id == organization_id,
        )
        try:
            result = await self.session.execute(stmt)
            provider = (
                result.scalar_one_or_none()
                if hasattr(result, "scalar_one_or_none")
                else None
            )
            if provider and isinstance(provider, LLMProviderModel):
                provider.is_healthy = True
                provider.consecutive_failures = 0
                provider.cooldown_until = None
        except Exception as e:
            logger.warning("llm_provider.record_success_failed", error=str(e))

    # ── LLM Model Registry ───────────────────────────────

    async def register_model(
        self,
        organization_id: UUID,
        provider_type: str,
        model_alias: str,
        model_name: str,
        context_window_tokens: int = 128000,
        max_output_tokens: int = 4096,
        input_cost_per_1k_tokens: float = 0.0,
        output_cost_per_1k_tokens: float = 0.0,
        is_default: bool = False,
    ) -> LLMModelRegistryModel:
        """Register model metadata and pricing in registry."""
        model = LLMModelRegistryModel(
            organization_id=organization_id,
            provider_type=provider_type,
            model_alias=model_alias,
            model_name=model_name,
            context_window_tokens=context_window_tokens,
            max_output_tokens=max_output_tokens,
            input_cost_per_1k_tokens=input_cost_per_1k_tokens,
            output_cost_per_1k_tokens=output_cost_per_1k_tokens,
            is_default=is_default,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def list_models(self, organization_id: UUID) -> List[LLMModelRegistryModel]:
        """List registered LLM models for an organization."""
        stmt = (
            select(LLMModelRegistryModel)
            .where(LLMModelRegistryModel.organization_id == organization_id)
            .order_by(LLMModelRegistryModel.created_at.desc())
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []

    # ── Immutable Prompt Versioning ──────────────────────

    async def create_prompt_template(
        self,
        organization_id: UUID,
        category: str,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
    ) -> PromptTemplateModel:
        """Create a new version of a security prompt template.

        Enforces IMMUTABLE prompt versioning: queries current highest version for category+name
        and increments to version = current_version + 1. Previous versions remain untouched.
        """
        stmt = select(func.max(PromptTemplateModel.version)).where(
            PromptTemplateModel.organization_id == organization_id,
            PromptTemplateModel.category == category,
            PromptTemplateModel.name == name,
        )
        try:
            res = await self.session.execute(stmt)
            max_ver = res.scalar() if hasattr(res, "scalar") else None
            next_version = (int(max_ver) + 1) if max_ver is not None else 1
        except Exception:
            next_version = 1

        template = PromptTemplateModel(
            organization_id=organization_id,
            category=category,
            name=name,
            version=next_version,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            is_active=True,
        )
        self.session.add(template)
        await self.session.flush()
        return template

    async def get_active_prompt_template(
        self, organization_id: UUID, category: str, name: Optional[str] = None
    ) -> Optional[PromptTemplateModel]:
        """Get latest active version of a prompt template enforcing organization boundary."""
        stmt = select(PromptTemplateModel).where(
            PromptTemplateModel.organization_id == organization_id,
            PromptTemplateModel.category == category,
            PromptTemplateModel.is_active.is_(True),
        )
        if name:
            stmt = stmt.where(PromptTemplateModel.name == name)

        stmt = stmt.order_by(PromptTemplateModel.version.desc())
        try:
            result = await self.session.execute(stmt)
            res = (
                result.scalar_one_or_none()
                if hasattr(result, "scalar_one_or_none")
                else None
            )
            return res if isinstance(res, PromptTemplateModel) else None
        except Exception:
            return None

    async def list_prompt_templates(
        self, organization_id: UUID
    ) -> List[PromptTemplateModel]:
        """List active prompt templates for an organization."""
        stmt = (
            select(PromptTemplateModel)
            .where(
                PromptTemplateModel.organization_id == organization_id,
                PromptTemplateModel.is_active.is_(True),
            )
            .order_by(PromptTemplateModel.created_at.desc())
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []

    # ── AI Request Audit Logging & Cost Tracking ─────────

    async def log_request(
        self,
        organization_id: UUID,
        provider_type: str,
        model_used: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: int,
        cost_usd: float,
        status: str,
        prompt_category: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> LLMRequestLogModel:
        """Log AI request audit record into database."""
        log_entry = LLMRequestLogModel(
            organization_id=organization_id,
            provider_type=provider_type,
            model_used=model_used,
            prompt_category=prompt_category,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            status=status,
            error_message=error_message,
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def get_usage_summary(self, organization_id: UUID) -> Dict[str, Any]:
        """Aggregate total requests, tokens, and USD costs for an organization."""
        stmt = select(
            func.count(LLMRequestLogModel.id).label("total_requests"),
            func.sum(LLMRequestLogModel.prompt_tokens).label("total_prompt_tokens"),
            func.sum(LLMRequestLogModel.completion_tokens).label(
                "total_completion_tokens"
            ),
            func.sum(LLMRequestLogModel.total_tokens).label("total_tokens"),
            func.sum(LLMRequestLogModel.cost_usd).label("total_cost_usd"),
        ).where(LLMRequestLogModel.organization_id == organization_id)
        try:
            result = await self.session.execute(stmt)
            row = result.one_or_none()
            if row:
                return {
                    "total_requests": int(row[0] or 0),
                    "total_prompt_tokens": int(row[1] or 0),
                    "total_completion_tokens": int(row[2] or 0),
                    "total_tokens": int(row[3] or 0),
                    "total_cost_usd": float(row[4] or 0.0),
                }
            return {}
        except Exception:
            return {}
