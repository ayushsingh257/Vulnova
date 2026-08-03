"""Prompt Orchestrator Application Service for Versioned Security Prompts & Context Builder."""

import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    CreatePromptTemplateRequest,
    PromptTemplateDTO,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
from app.domain.entities.ai import PromptCategory
from app.domain.entities.assessment import Finding
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.llm_gateway_repository import (
    LLMGatewayRepository,
)

logger = get_logger("vulnova.prompt_orchestrator_service")

# Regex pattern for masking authorization headers, cookies, API tokens, & passwords
SECRET_MASK_REGEX = re.compile(
    r"(?i)(bearer\s+[a-z0-9\-\._~\+\/]+=*|authorization:\s*[^\n]+|cookie:\s*[^\n]+|password=[\w@#$%^&*!]+|api[_-]?key=[\w-]+)",
    re.IGNORECASE,
)


def mask_sensitive_prompt_context(text: str) -> str:
    """Mask Authorization headers, cookies, session tokens, and passwords in prompt context text."""
    if not text:
        return ""
    return SECRET_MASK_REGEX.sub("[REDACTED_SECRET]", text)


class PromptOrchestratorService:
    """Service managing versioned security prompt resolution, variable interpolation, & context sanitization."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai_repo = LLMGatewayRepository(session)
        self.audit_service = AuditLogService(session)

    async def render_prompt(
        self,
        organization_id: UUID,
        category: str,
        variables: Dict[str, Any],
        name: Optional[str] = None,
    ) -> Dict[str, str]:
        """Resolve active versioned template for category, interpolate variables, & return system + user prompts."""
        template_model = await self.ai_repo.get_active_prompt_template(
            organization_id, category, name
        )

        system_prompt = (
            template_model.system_prompt
            if template_model
            else "You are Vulnova, an expert AI Security Analyst & AppSec Copilot."
        )
        user_template = (
            template_model.user_prompt_template
            if template_model
            else "Analyze the following security finding context:\n\n{finding_context}"
        )

        # Interpolate variables into user prompt
        try:
            rendered_user_prompt = user_template.format(**variables)
        except KeyError as e:
            logger.warning(
                "prompt_orchestrator.missing_variable",
                missing_key=str(e),
                category=category,
            )
            rendered_user_prompt = user_template

        # Sanitize sensitive tokens in prompt output
        sanitized_user_prompt = mask_sensitive_prompt_context(rendered_user_prompt)

        return {
            "system_prompt": system_prompt,
            "user_prompt": sanitized_user_prompt,
        }

    def build_security_finding_context(
        self,
        finding: Finding,
        evidence_dumps: Optional[List[str]] = None,
        asset_topology_info: Optional[str] = None,
        triage_status: Optional[str] = None,
    ) -> str:
        """Construct sanitized markdown security context from Era 4 finding data for LLM prompt ingestion."""
        ctx_lines: List[str] = []
        ctx_lines.append(f"### Security Vulnerability: {finding.title}")
        ctx_lines.append(f"- **Plugin ID**: {finding.plugin_id}")
        ctx_lines.append(f"- **Severity**: {finding.severity.value}")
        ctx_lines.append(f"- **CWE ID**: {finding.cwe_id or 'N/A'}")
        ctx_lines.append(f"- **CVE ID**: {finding.cve_id or 'N/A'}")

        if finding.risk:
            ctx_lines.append(
                f"- **Composite Risk Score**: {finding.risk.composite_risk_score:.1f}/100.0"
            )
            ctx_lines.append(
                f"- **Business Impact Rating**: {finding.risk.business_impact}"
            )
            sla = getattr(
                finding.risk,
                "fix_sla_hours",
                getattr(finding.risk, "remediation_sla_hours", 72),
            )
            ctx_lines.append(f"- **Remediation SLA Hours**: {sla}h")

        if triage_status:
            ctx_lines.append(f"- **Analyst Triage Status**: {triage_status}")

        ctx_lines.append(
            f"\n**Description**:\n{finding.description or 'No description provided.'}"
        )
        ctx_lines.append(
            f"\n**Remediation Recommendation**:\n{finding.remediation or 'N/A'}"
        )

        if asset_topology_info:
            ctx_lines.append(
                f"\n**Target Asset Topology Context**:\n{asset_topology_info}"
            )

        if evidence_dumps:
            ctx_lines.append("\n**Proof-of-Exploit Evidence Dumps**:")
            for idx, dump in enumerate(evidence_dumps, 1):
                clean_dump = mask_sensitive_prompt_context(dump)
                ctx_lines.append(f"\n```text (Evidence {idx})\n{clean_dump}\n```")

        raw_context = "\n".join(ctx_lines)
        return mask_sensitive_prompt_context(raw_context)

    async def create_prompt_template(
        self, current_user: UserModel, req: CreatePromptTemplateRequest
    ) -> PromptTemplateDTO:
        """Create a new version of a prompt template (IMMUTABLE versioning)."""
        org_id = current_user.organization_id

        try:
            cat_enum = PromptCategory(req.category.upper())
        except ValueError as err:
            raise ValidationException(
                f"Invalid prompt category '{req.category}'. Allowed values: {[c.value for c in PromptCategory]}"
            ) from err

        model = await self.ai_repo.create_prompt_template(
            organization_id=org_id,
            category=cat_enum.value,
            name=req.name,
            system_prompt=req.system_prompt,
            user_prompt_template=req.user_prompt_template,
        )

        await self.audit_service.record_event(
            organization_id=org_id,
            action="prompt_template.created",
            resource_type="prompt_template",
            resource_id=str(model.id),
            actor_user_id=current_user.id,
            details={
                "name": model.name,
                "category": model.category,
                "version": model.version,
            },
        )

        return PromptTemplateDTO(
            id=str(model.id),
            category=model.category,
            name=model.name,
            version=model.version,
            system_prompt=model.system_prompt,
            user_prompt_template=model.user_prompt_template,
            is_active=model.is_active,
            created_at=str(model.created_at),
        )

    async def list_prompt_templates(
        self, current_user: UserModel
    ) -> List[PromptTemplateDTO]:
        """List active prompt templates for organization."""
        org_id = current_user.organization_id
        templates = await self.ai_repo.list_prompt_templates(org_id)
        return [
            PromptTemplateDTO(
                id=str(t.id),
                category=t.category,
                name=t.name,
                version=t.version,
                system_prompt=t.system_prompt,
                user_prompt_template=t.user_prompt_template,
                is_active=t.is_active,
                created_at=str(t.created_at),
            )
            for t in templates
        ]
