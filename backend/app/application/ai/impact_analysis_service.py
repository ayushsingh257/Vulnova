"""AI Impact Analysis Application Service with Structured Output Recovery."""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    AIChatCompletionRequest,
    AIImpactAnalysisDTO,
    LLMMessageDTO,
)
from app.application.ai.llm_gateway_service import LLMGatewayService
from app.application.ai.prompt_orchestrator_service import (
    PromptOrchestratorService,
    mask_sensitive_prompt_context,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.models.ai_analysis import (
    AIImpactAnalysisModel,
)
from app.infrastructure.database.models.assessment import (
    EvidenceArtifactModel,
    SecurityFindingModel,
)
from app.infrastructure.database.models.asset_graph import AssetNodeModel
from app.infrastructure.database.repositories.ai_analysis_repository import (
    AIAnalysisRepository,
)
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.database.repositories.asset_graph_repository import (
    AssetGraphRepository,
)
from app.infrastructure.database.repositories.evidence_repository import (
    EvidenceRepository,
)
from app.infrastructure.database.repositories.finding_triage_repository import (
    FindingTriageRepository,
)

logger = get_logger("vulnova.impact_analysis_service")

IMPACT_KEYS = [
    "technical_impact_summary",
    "executive_impact_summary",
    "risk_justification",
    "affected_business_components",
    "cvss_interpretation",
    "epss_context",
    "exposure_assessment",
    "evidence_correlation",
]

# Repair prompt for malformed JSON recovery
JSON_REPAIR_SYSTEM_PROMPT = (
    "You are a JSON repair assistant. The user will give you malformed text that was "
    "supposed to be valid JSON. Extract the information and return ONLY a valid JSON "
    "object with exactly these keys: "
    + ", ".join(IMPACT_KEYS)
    + ". Do not include any text outside the JSON object."
)


def _model_to_dto(model: AIImpactAnalysisModel) -> AIImpactAnalysisDTO:
    """Map ORM model to Pydantic DTO."""
    return AIImpactAnalysisDTO(
        id=str(model.id),
        finding_id=str(model.finding_id),
        technical_impact_summary=model.technical_impact_summary,
        executive_impact_summary=model.executive_impact_summary,
        risk_justification=model.risk_justification,
        affected_business_components=model.affected_business_components,
        cvss_interpretation=model.cvss_interpretation,
        epss_context=model.epss_context,
        exposure_assessment=model.exposure_assessment,
        evidence_correlation=model.evidence_correlation,
        model_used=model.model_used,
        provider_used=model.provider_used,
        prompt_version=model.prompt_version,
        status=model.status,
        created_at=str(model.created_at),
    )


class ImpactAnalysisService:
    """Application service generating AI-powered impact analysis reports with retry-once JSON recovery."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai_analysis_repo = AIAnalysisRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.triage_repo = FindingTriageRepository(session)
        self.asset_graph_repo = AssetGraphRepository(session)
        self.prompt_service = PromptOrchestratorService(session)
        self.gateway_service = LLMGatewayService(session)
        self.audit_service = AuditLogService(session)

    async def generate_impact_analysis(
        self,
        organization_id: UUID,
        finding_id: UUID,
        actor_user_id: UUID,
        model_alias: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIImpactAnalysisDTO:
        """Generate an AI-powered impact analysis for a security finding.

        Workflow:
        1. Fetch finding (tenant-isolated)
        2. Fetch evidence artifacts, asset topology, and triage status
        3. Build enriched impact context with CVSS/EPSS/asset data
        4. Resolve prompt template and render
        5. Execute LLM completion via gateway
        6. Parse structured JSON response (with retry-once recovery)
        7. Persist impact analysis record
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

        # 3. Fetch associated asset node
        asset_node: Optional[AssetNodeModel] = None
        asset_neighbors: List[AssetNodeModel] = []
        if finding_model.asset_node_id:
            try:
                asset_node = await self.asset_graph_repo.get_node_by_id(
                    organization_id, finding_model.asset_node_id
                )
            except Exception as e:
                logger.debug("impact_analysis.asset_node_fetch_failed", error=str(e))

        # 4. Fetch latest triage status
        triage_status = await self._get_latest_triage_status(
            organization_id, finding_id
        )

        # 5. Build enriched impact context
        impact_context = self._build_impact_context(
            finding=finding_model,
            evidence_artifacts=evidence_artifacts,
            asset_node=asset_node,
            asset_neighbors=asset_neighbors,
            triage_status=triage_status,
        )

        # 6. Resolve prompt template and render
        prompt_parts = await self.prompt_service.render_prompt(
            organization_id=organization_id,
            category="IMPACT_ANALYSIS",
            variables={"impact_context": impact_context},
        )

        # Determine prompt version
        prompt_version = 1
        active_template = await self.gateway_service.ai_repo.get_active_prompt_template(
            organization_id, "IMPACT_ANALYSIS"
        )
        if active_template:
            prompt_version = active_template.version

        # 7. Execute LLM completion
        chat_req = AIChatCompletionRequest(
            messages=[
                LLMMessageDTO(role="system", content=prompt_parts["system_prompt"]),
                LLMMessageDTO(role="user", content=prompt_parts["user_prompt"]),
            ],
            model_alias=model_alias or "gpt-4o",
            max_tokens=4096,
            temperature=temperature,
            prompt_category="IMPACT_ANALYSIS",
        )

        try:
            llm_response = await self.gateway_service.generate_completion(
                organization_id, chat_req
            )
        except Exception as e:
            logger.error(
                "impact_analysis.llm_generation_failed",
                finding_id=str(finding_id),
                error=str(e),
            )
            failed_model = await self.ai_analysis_repo.create_impact_analysis(
                organization_id=organization_id,
                finding_id=finding_id,
                technical_impact_summary="",
                executive_impact_summary="",
                risk_justification="",
                affected_business_components="",
                cvss_interpretation="",
                epss_context="",
                exposure_assessment="",
                evidence_correlation="",
                model_used=model_alias or "unknown",
                provider_used="unknown",
                prompt_version=prompt_version,
                status="FAILED",
                error_message=str(e)[:2000],
            )
            return _model_to_dto(failed_model)

        # 8. Parse structured JSON response with retry-once recovery
        parsed = self._try_parse_json(llm_response.content)
        if parsed is None:
            logger.warning(
                "impact_analysis.malformed_json_retrying",
                finding_id=str(finding_id),
                model_used=llm_response.model_used,
            )
            parsed = await self._retry_json_repair(
                organization_id, llm_response.content, model_alias
            )

        if parsed is None:
            logger.error(
                "impact_analysis.json_repair_failed",
                finding_id=str(finding_id),
            )
            failed_model = await self.ai_analysis_repo.create_impact_analysis(
                organization_id=organization_id,
                finding_id=finding_id,
                technical_impact_summary="",
                executive_impact_summary="",
                risk_justification="",
                affected_business_components="",
                cvss_interpretation="",
                epss_context="",
                exposure_assessment="",
                evidence_correlation="",
                model_used=llm_response.model_used,
                provider_used=llm_response.provider_used,
                prompt_version=prompt_version,
                status="FAILED",
                error_message="LLM response JSON parsing failed after retry.",
            )
            return _model_to_dto(failed_model)

        # 9. Persist impact analysis record
        impact_model = await self.ai_analysis_repo.create_impact_analysis(
            organization_id=organization_id,
            finding_id=finding_id,
            technical_impact_summary=parsed.get("technical_impact_summary", ""),
            executive_impact_summary=parsed.get("executive_impact_summary", ""),
            risk_justification=parsed.get("risk_justification", ""),
            affected_business_components=parsed.get("affected_business_components", ""),
            cvss_interpretation=parsed.get("cvss_interpretation", ""),
            epss_context=parsed.get("epss_context", ""),
            exposure_assessment=parsed.get("exposure_assessment", ""),
            evidence_correlation=parsed.get("evidence_correlation", ""),
            model_used=llm_response.model_used,
            provider_used=llm_response.provider_used,
            prompt_version=prompt_version,
            status="COMPLETED",
        )

        # 10. Record audit event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="finding.impact_analyzed",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=actor_user_id,
            details={
                "model_used": llm_response.model_used,
                "provider_used": llm_response.provider_used,
                "prompt_version": prompt_version,
            },
        )

        return _model_to_dto(impact_model)

    async def get_impact_analysis(
        self, organization_id: UUID, finding_id: UUID
    ) -> Optional[AIImpactAnalysisDTO]:
        """Retrieve the most recent completed impact analysis for a finding."""
        model = await self.ai_analysis_repo.get_impact_analysis_by_finding(
            organization_id, finding_id
        )
        if not model:
            return None
        return _model_to_dto(model)

    async def list_impact_analyses(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIImpactAnalysisDTO]:
        """List impact analysis history for organization."""
        models = await self.ai_analysis_repo.list_impact_analyses(
            organization_id, limit, offset
        )
        return [_model_to_dto(m) for m in models]

    # ── Private Helpers ─────────────────────────────────

    def _build_impact_context(
        self,
        finding: SecurityFindingModel,
        evidence_artifacts: List[EvidenceArtifactModel],
        asset_node: Optional[AssetNodeModel],
        asset_neighbors: List[AssetNodeModel],
        triage_status: Optional[str],
    ) -> str:
        """Build enriched markdown impact analysis context for LLM prompt ingestion."""
        ctx: List[str] = []
        ctx.append(f"### Impact Analysis: {finding.title}")
        ctx.append(f"- **Severity**: {finding.severity}")
        ctx.append(f"- **Category**: {finding.category}")
        ctx.append(f"- **CVE ID**: {finding.cve_id or 'N/A'}")
        ctx.append(f"- **CWE ID**: {finding.cwe_id or 'N/A'}")

        # CVSS context (reads existing data, does NOT recalculate)
        if finding.cvss_json:
            ctx.append(f"- **CVSS Version**: {finding.cvss_json.get('version', 'N/A')}")
            ctx.append(
                f"- **CVSS Base Score**: {finding.cvss_json.get('base_score', 'N/A')}"
            )
            ctx.append(
                f"- **CVSS Vector**: {finding.cvss_json.get('vector_string', 'N/A')}"
            )

        # EPSS context
        if finding.epss_json:
            ctx.append(
                f"- **EPSS Probability**: {finding.epss_json.get('epss_score', 'N/A')}"
            )
            ctx.append(
                f"- **EPSS Percentile**: {finding.epss_json.get('percentile', 'N/A')}"
            )

        # Risk score (reads existing composite_risk_score)
        if finding.risk_score is not None:
            ctx.append(f"- **Composite Risk Score**: {finding.risk_score:.1f}/100.0")

        # Triage lifecycle state
        if triage_status:
            ctx.append(f"- **Triage Status**: {triage_status}")

        # Asset topology context
        if asset_node:
            ctx.append(f"\n**Affected Asset**: {asset_node.name}")
            ctx.append(f"- **Asset Type**: {asset_node.node_type}")
            ctx.append(f"- **Asset Value**: {asset_node.value}")
            if asset_neighbors:
                neighbor_labels = [n.name for n in asset_neighbors[:10]]
                ctx.append(f"- **Connected Assets**: {', '.join(neighbor_labels)}")

        # Description
        ctx.append(
            f"\n**Description**:\n{finding.description or 'No description provided.'}"
        )
        ctx.append(f"\n**Remediation**:\n{finding.remediation or 'N/A'}")

        # Evidence artifacts summary
        if evidence_artifacts:
            ctx.append(
                f"\n**Evidence Artifacts** ({len(evidence_artifacts)} collected):"
            )
            for ea in evidence_artifacts[:5]:
                artifact_summary = (
                    f"  - Type: {ea.artifact_type}, Path: {ea.storage_path}"
                )
                ctx.append(artifact_summary)

        raw_context = "\n".join(ctx)
        return mask_sensitive_prompt_context(raw_context)

    def _try_parse_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Attempt to parse LLM output as JSON, handling markdown code fences."""
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            logger.debug(
                "impact_analysis.json_parse_failed", content_snippet=text[:100]
            )
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
            prompt_category="IMPACT_ANALYSIS",
        )
        try:
            repair_resp = await self.gateway_service.generate_completion(
                organization_id, repair_req
            )
            return self._try_parse_json(repair_resp.content)
        except Exception as e:
            logger.error("impact_analysis.json_repair_request_failed", error=str(e))
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
            logger.debug("impact_analysis.triage_status_fetch_failed", error=str(e))
        return None
