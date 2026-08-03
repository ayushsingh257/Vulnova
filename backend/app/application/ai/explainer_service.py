"""AI Finding Explainer Application Service with Structured Output Recovery."""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    AIChatCompletionRequest,
    AIFindingExplanationDTO,
    LLMMessageDTO,
)
from app.application.ai.llm_gateway_service import LLMGatewayService
from app.application.ai.prompt_orchestrator_service import PromptOrchestratorService
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.models.ai_analysis import (
    AIFindingExplanationModel,
)
from app.infrastructure.database.repositories.ai_analysis_repository import (
    AIAnalysisRepository,
)
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.database.repositories.evidence_repository import (
    EvidenceRepository,
)
from app.infrastructure.database.repositories.finding_triage_repository import (
    FindingTriageRepository,
)

logger = get_logger("vulnova.ai_finding_explainer_service")

EXPLANATION_KEYS = [
    "vulnerability_summary",
    "technical_root_cause",
    "affected_asset_context",
    "exploitability_analysis",
    "business_impact",
    "attack_prerequisites",
    "severity_reasoning",
    "remediation_priority",
]

# Repair prompt used when initial LLM response is not valid JSON
JSON_REPAIR_SYSTEM_PROMPT = (
    "You are a JSON repair assistant. The user will give you malformed text that was "
    "supposed to be valid JSON. Extract the information and return ONLY a valid JSON "
    "object with exactly these keys: "
    + ", ".join(EXPLANATION_KEYS)
    + ". Do not include any text outside the JSON object."
)


def _model_to_dto(model: AIFindingExplanationModel) -> AIFindingExplanationDTO:
    """Map ORM model to Pydantic DTO."""
    return AIFindingExplanationDTO(
        id=str(model.id),
        finding_id=str(model.finding_id),
        vulnerability_summary=model.vulnerability_summary,
        technical_root_cause=model.technical_root_cause,
        affected_asset_context=model.affected_asset_context,
        exploitability_analysis=model.exploitability_analysis,
        business_impact=model.business_impact,
        attack_prerequisites=model.attack_prerequisites,
        severity_reasoning=model.severity_reasoning,
        remediation_priority=model.remediation_priority,
        model_used=model.model_used,
        provider_used=model.provider_used,
        prompt_version=model.prompt_version,
        status=model.status,
        created_at=str(model.created_at),
    )


class AIFindingExplainerService:
    """Application service generating AI-powered finding explanations with retry-once JSON recovery."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai_analysis_repo = AIAnalysisRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.triage_repo = FindingTriageRepository(session)
        self.prompt_service = PromptOrchestratorService(session)
        self.gateway_service = LLMGatewayService(session)
        self.audit_service = AuditLogService(session)

    async def generate_explanation(
        self,
        organization_id: UUID,
        finding_id: UUID,
        actor_user_id: UUID,
        model_alias: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIFindingExplanationDTO:
        """Generate an AI-powered explanation for a security finding.

        Workflow:
        1. Fetch finding (tenant-isolated)
        2. Fetch evidence artifacts and triage status
        3. Build sanitized security context
        4. Resolve prompt template and render
        5. Execute LLM completion via gateway
        6. Parse structured JSON response (with retry-once recovery)
        7. Persist explanation record
        8. Record audit event
        """
        # 1. Fetch finding
        finding_model = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding_model:
            raise ResourceNotFoundException(
                f"Security finding '{finding_id}' not found in organization."
            )

        # 2. Fetch evidence artifacts
        evidence_artifacts = await self.evidence_repo.list_finding_artifacts(
            organization_id, finding_id
        )
        evidence_dumps = [str(ea.metadata_json or {}) for ea in evidence_artifacts]

        # 3. Fetch latest triage status
        triage_status = await self._get_latest_triage_status(
            organization_id, finding_id
        )

        # 4. Build sanitized finding context using Phase 5.1 context builder
        from app.domain.entities.assessment import (
            CVSSMetrics,
            EPSSMetrics,
            Finding,
            RiskMetrics,
            SeverityLevel,
        )

        domain_finding = Finding(
            id=finding_model.id,
            organization_id=finding_model.organization_id,
            assessment_job_id=finding_model.assessment_job_id,
            plugin_id=finding_model.plugin_id,
            title=finding_model.title,
            description=finding_model.description,
            severity=SeverityLevel(finding_model.severity),
            cve_id=finding_model.cve_id,
            cwe_id=finding_model.cwe_id,
            remediation=finding_model.remediation,
        )

        # Attach CVSS if available
        if finding_model.cvss_json:
            domain_finding.cvss = CVSSMetrics(
                version=finding_model.cvss_json.get("version", "3.1"),
                base_score=finding_model.cvss_json.get("base_score", 0.0),
                vector_string=finding_model.cvss_json.get("vector_string"),
            )

        # Attach EPSS if available
        if finding_model.epss_json:
            domain_finding.epss = EPSSMetrics(
                epss_score=finding_model.epss_json.get("epss_score", 0.0),
                percentile=finding_model.epss_json.get("percentile", 0.0),
            )

        # Attach risk score (reads existing composite_risk_score, does NOT recalculate)
        if finding_model.risk_score is not None:
            domain_finding.risk = RiskMetrics(
                composite_risk_score=finding_model.risk_score,
            )

        finding_context = self.prompt_service.build_security_finding_context(
            finding=domain_finding,
            evidence_dumps=evidence_dumps if evidence_dumps else None,
            triage_status=triage_status,
        )

        # 5. Resolve prompt template and render
        prompt_parts = await self.prompt_service.render_prompt(
            organization_id=organization_id,
            category="FINDING_EXPLAINER",
            variables={"finding_context": finding_context},
        )

        # Determine prompt version
        prompt_version = 1
        active_template = await self.gateway_service.ai_repo.get_active_prompt_template(
            organization_id, "FINDING_EXPLAINER"
        )
        if active_template:
            prompt_version = active_template.version

        # 6. Execute LLM completion
        chat_req = AIChatCompletionRequest(
            messages=[
                LLMMessageDTO(role="system", content=prompt_parts["system_prompt"]),
                LLMMessageDTO(role="user", content=prompt_parts["user_prompt"]),
            ],
            model_alias=model_alias or "gpt-4o",
            max_tokens=4096,
            temperature=temperature,
            prompt_category="FINDING_EXPLAINER",
        )

        try:
            llm_response = await self.gateway_service.generate_completion(
                organization_id, chat_req
            )
        except Exception as e:
            logger.error(
                "ai_explainer.llm_generation_failed",
                finding_id=str(finding_id),
                error=str(e),
            )
            # Persist FAILED record
            failed_model = await self.ai_analysis_repo.create_explanation(
                organization_id=organization_id,
                finding_id=finding_id,
                vulnerability_summary="",
                technical_root_cause="",
                affected_asset_context="",
                exploitability_analysis="",
                business_impact="",
                attack_prerequisites="",
                severity_reasoning="",
                remediation_priority="",
                model_used=model_alias or "unknown",
                provider_used="unknown",
                prompt_version=prompt_version,
                status="FAILED",
                error_message=str(e)[:2000],
            )
            return _model_to_dto(failed_model)

        # 7. Parse structured JSON response with retry-once recovery
        parsed = self._try_parse_json(llm_response.content)
        if parsed is None:
            logger.warning(
                "ai_explainer.malformed_json_retrying",
                finding_id=str(finding_id),
                model_used=llm_response.model_used,
            )
            parsed = await self._retry_json_repair(
                organization_id, llm_response.content, model_alias
            )

        if parsed is None:
            logger.error(
                "ai_explainer.json_repair_failed",
                finding_id=str(finding_id),
            )
            failed_model = await self.ai_analysis_repo.create_explanation(
                organization_id=organization_id,
                finding_id=finding_id,
                vulnerability_summary="",
                technical_root_cause="",
                affected_asset_context="",
                exploitability_analysis="",
                business_impact="",
                attack_prerequisites="",
                severity_reasoning="",
                remediation_priority="",
                model_used=llm_response.model_used,
                provider_used=llm_response.provider_used,
                prompt_version=prompt_version,
                status="FAILED",
                error_message="LLM response JSON parsing failed after retry.",
            )
            return _model_to_dto(failed_model)

        # 8. Persist explanation record
        explanation_model = await self.ai_analysis_repo.create_explanation(
            organization_id=organization_id,
            finding_id=finding_id,
            vulnerability_summary=parsed.get("vulnerability_summary", ""),
            technical_root_cause=parsed.get("technical_root_cause", ""),
            affected_asset_context=parsed.get("affected_asset_context", ""),
            exploitability_analysis=parsed.get("exploitability_analysis", ""),
            business_impact=parsed.get("business_impact", ""),
            attack_prerequisites=parsed.get("attack_prerequisites", ""),
            severity_reasoning=parsed.get("severity_reasoning", ""),
            remediation_priority=parsed.get("remediation_priority", ""),
            model_used=llm_response.model_used,
            provider_used=llm_response.provider_used,
            prompt_version=prompt_version,
            status="COMPLETED",
        )

        # 9. Record audit event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="finding.ai_explained",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=actor_user_id,
            details={
                "model_used": llm_response.model_used,
                "provider_used": llm_response.provider_used,
                "prompt_version": prompt_version,
            },
        )

        return _model_to_dto(explanation_model)

    async def get_explanation(
        self, organization_id: UUID, finding_id: UUID
    ) -> Optional[AIFindingExplanationDTO]:
        """Retrieve the most recent completed explanation for a finding."""
        model = await self.ai_analysis_repo.get_explanation_by_finding(
            organization_id, finding_id
        )
        if not model:
            return None
        return _model_to_dto(model)

    async def list_explanations(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIFindingExplanationDTO]:
        """List explanation history for organization."""
        models = await self.ai_analysis_repo.list_explanations(
            organization_id, limit, offset
        )
        return [_model_to_dto(m) for m in models]

    # ── Private Helpers ─────────────────────────────────

    def _try_parse_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Attempt to parse LLM output as JSON, handling markdown code fences."""
        text = content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            logger.debug("ai_explainer.json_parse_failed", content_snippet=text[:100])
        return None

    async def _retry_json_repair(
        self,
        organization_id: UUID,
        malformed_content: str,
        model_alias: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Retry once with a stricter JSON repair prompt."""
        repair_req = AIChatCompletionRequest(
            messages=[
                LLMMessageDTO(role="system", content=JSON_REPAIR_SYSTEM_PROMPT),
                LLMMessageDTO(
                    role="user",
                    content=f"Please repair and return as valid JSON:\n\n{malformed_content[:3000]}",
                ),
            ],
            model_alias=model_alias or "gpt-4o",
            max_tokens=4096,
            temperature=0.0,
            prompt_category="FINDING_EXPLAINER",
        )
        try:
            repair_resp = await self.gateway_service.generate_completion(
                organization_id, repair_req
            )
            return self._try_parse_json(repair_resp.content)
        except Exception as e:
            logger.error("ai_explainer.json_repair_request_failed", error=str(e))
            return None

    async def _get_latest_triage_status(
        self, organization_id: UUID, finding_id: UUID
    ) -> Optional[str]:
        """Fetch latest triage status for a finding."""
        try:
            history = await self.triage_repo.get_triage_history(
                organization_id, finding_id
            )
            if history:
                return str(history[0].new_status)
        except Exception as e:
            logger.debug("ai_explainer.triage_status_fetch_failed", error=str(e))
        return None
