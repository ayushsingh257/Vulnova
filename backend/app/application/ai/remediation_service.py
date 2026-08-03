"""AI Remediation Engine Application Service with Non-Executable Patch Suggestions & Dual Confidence Metrics."""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    AIChatCompletionRequest,
    AIPatchSuggestionDTO,
    AIRemediationPlanDTO,
    LLMMessageDTO,
    RemediationStepDTO,
    ReviewRemediationPlanRequest,
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
    AIFindingExplanationModel,
    AIImpactAnalysisModel,
)
from app.infrastructure.database.models.ai_attack_path import AIAttackPathModel
from app.infrastructure.database.models.ai_remediation import (
    AIPatchSuggestionModel,
    AIRemediationPlanModel,
    AIRemediationStepModel,
)
from app.infrastructure.database.models.assessment import (
    EvidenceArtifactModel,
    SecurityFindingModel,
)
from app.infrastructure.database.models.asset_graph import (
    AssetNodeModel,
    AssetRelationshipModel,
)
from app.infrastructure.database.repositories.ai_analysis_repository import (
    AIAnalysisRepository,
)
from app.infrastructure.database.repositories.ai_attack_path_repository import (
    AIAttackPathRepository,
)
from app.infrastructure.database.repositories.ai_remediation_repository import (
    AIRemediationRepository,
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

logger = get_logger("vulnova.remediation_service")

# Repair prompt for malformed JSON recovery
JSON_REPAIR_SYSTEM_PROMPT = (
    "You are a JSON repair assistant. The user will give you malformed text that was "
    "supposed to be valid JSON representing a remediation plan. Extract the information and return ONLY "
    "a valid JSON object with keys: title, summary, technical_solution, business_solution, "
    "risk_reduction_explanation, validation_strategy, ai_confidence_score, effectiveness_confidence_score, "
    "requires_backup, requires_downtime, rollback_available, cve_id, cwe_id, affected_version, fixed_version, "
    "steps (array of objects with: sequence_number, step_type, title, description, affected_component, "
    "recommended_action, validation_command, rollback_strategy, confidence_score), and "
    "patch_suggestions (array of objects with: language, file_type, target_file_path, original_code_snippet, "
    "proposed_patch_diff, explanation, security_impact_notes, confidence_score). "
    "Do not include any text outside the JSON object."
)


def _step_model_to_dto(model: AIRemediationStepModel) -> RemediationStepDTO:
    """Map remediation step ORM model to Pydantic DTO."""
    return RemediationStepDTO(
        id=str(model.id),
        sequence_number=model.sequence_number,
        step_type=model.step_type,
        title=model.title,
        description=model.description,
        affected_component=model.affected_component,
        recommended_action=model.recommended_action,
        validation_command=model.validation_command,
        rollback_strategy=model.rollback_strategy,
        confidence_score=model.confidence_score,
    )


def _patch_model_to_dto(model: AIPatchSuggestionModel) -> AIPatchSuggestionDTO:
    """Map patch suggestion ORM model to Pydantic DTO."""
    return AIPatchSuggestionDTO(
        id=str(model.id),
        language=model.language,
        file_type=model.file_type,
        target_file_path=model.target_file_path,
        original_code_snippet=model.original_code_snippet,
        proposed_patch_diff=model.proposed_patch_diff,
        explanation=model.explanation,
        security_impact_notes=model.security_impact_notes,
        confidence_score=model.confidence_score,
    )


def _plan_model_to_dto(model: AIRemediationPlanModel) -> AIRemediationPlanDTO:
    """Map remediation plan ORM model to Pydantic DTO."""
    step_dtos = [_step_model_to_dto(s) for s in (model.steps or [])]
    patch_dtos = [_patch_model_to_dto(p) for p in (model.patch_suggestions or [])]
    return AIRemediationPlanDTO(
        id=str(model.id),
        root_finding_id=str(model.root_finding_id),
        attack_path_id=str(model.attack_path_id) if model.attack_path_id else None,
        cve_id=str(model.cve_id) if model.cve_id else None,
        cwe_id=str(model.cwe_id) if model.cwe_id else None,
        affected_version=(
            str(model.affected_version) if model.affected_version else None
        ),
        fixed_version=str(model.fixed_version) if model.fixed_version else None,
        title=model.title,
        summary=model.summary,
        technical_solution=model.technical_solution,
        business_solution=model.business_solution,
        risk_reduction_explanation=model.risk_reduction_explanation,
        validation_strategy=model.validation_strategy,
        composite_risk_score=model.composite_risk_score,
        ai_confidence_score=model.ai_confidence_score,
        effectiveness_confidence_score=model.effectiveness_confidence_score,
        requires_backup=model.requires_backup,
        requires_downtime=model.requires_downtime,
        rollback_available=model.rollback_available,
        model_used=model.model_used,
        provider_used=model.provider_used,
        prompt_version=model.prompt_version,
        status=model.status,
        steps=step_dtos,
        patch_suggestions=patch_dtos,
        review_notes=str(model.review_notes) if model.review_notes else None,
        reviewed_by=str(model.reviewed_by) if model.reviewed_by else None,
        reviewed_at=str(model.reviewed_at) if model.reviewed_at else None,
        error_message=str(model.error_message) if model.error_message else None,
        created_at=str(model.created_at),
    )


class AIRemediationService:
    """Application service synthesizing non-executable AI remediation plans and patch suggestions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.remediation_repo = AIRemediationRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.triage_repo = FindingTriageRepository(session)
        self.ai_analysis_repo = AIAnalysisRepository(session)
        self.attack_path_repo = AIAttackPathRepository(session)
        self.asset_graph_repo = AssetGraphRepository(session)
        self.prompt_service = PromptOrchestratorService(session)
        self.gateway_service = LLMGatewayService(session)
        self.audit_service = AuditLogService(session)

    async def generate_remediation_plan(
        self,
        organization_id: UUID,
        finding_id: UUID,
        actor_user_id: UUID,
        model_alias: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIRemediationPlanDTO:
        """Synthesize an evidence-grounded remediation plan for a vulnerability finding.

        Workflow:
        1. Fetch finding (tenant-isolated)
        2. Fetch evidence artifacts, triage state, asset node/edges
        3. Fetch latest Phase 5.2 explanation & impact analysis
        4. Fetch latest Phase 5.3 attack path
        5. Build sanitized remediation context
        6. Resolve REMEDIATION_PATCH prompt template
        7. Execute LLM completion via gateway
        8. Parse structured JSON (with retry-once repair recovery)
        9. Persist plan, steps, and non-executable patch diff suggestions
        10. Record audit log event
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

        # 3. Fetch asset node and graph relationships
        asset_node: Optional[AssetNodeModel] = None
        graph_relationships: List[AssetRelationshipModel] = []
        if finding_model.asset_node_id:
            try:
                asset_node = await self.asset_graph_repo.get_node_by_id(
                    organization_id, finding_model.asset_node_id
                )
                if asset_node and asset_node.value:
                    _, rels = await self.asset_graph_repo.get_graph_by_domain(
                        organization_id, asset_node.value
                    )
                    graph_relationships = rels if rels else []
            except Exception as e:
                logger.debug("remediation.graph_fetch_failed", error=str(e))

        # 4. Fetch triage status
        triage_status = await self._get_latest_triage_status(
            organization_id, finding_id
        )

        # 5. Fetch Phase 5.2 explanation and impact analysis
        latest_explanation = await self.ai_analysis_repo.get_explanation_by_finding(
            organization_id, finding_id
        )
        latest_impact = await self.ai_analysis_repo.get_impact_analysis_by_finding(
            organization_id, finding_id
        )

        # 6. Fetch Phase 5.3 attack path
        attack_paths = await self.attack_path_repo.list_attack_paths_by_finding(
            organization_id, finding_id
        )
        latest_attack_path: Optional[AIAttackPathModel] = (
            attack_paths[0] if attack_paths else None
        )

        # 7. Build sanitized remediation context
        remediation_context = self._build_remediation_context(
            finding=finding_model,
            evidence_artifacts=evidence_artifacts,
            asset_node=asset_node,
            graph_relationships=graph_relationships,
            triage_status=triage_status,
            explanation=latest_explanation,
            impact_analysis=latest_impact,
            attack_path=latest_attack_path,
        )

        # 8. Resolve prompt template and render
        prompt_parts = await self.prompt_service.render_prompt(
            organization_id=organization_id,
            category="REMEDIATION_PATCH",
            variables={"remediation_context": remediation_context},
        )

        prompt_version = 1
        active_template = await self.gateway_service.ai_repo.get_active_prompt_template(
            organization_id, "REMEDIATION_PATCH"
        )
        if active_template:
            prompt_version = active_template.version

        # 9. Execute LLM completion
        chat_req = AIChatCompletionRequest(
            messages=[
                LLMMessageDTO(role="system", content=prompt_parts["system_prompt"]),
                LLMMessageDTO(role="user", content=prompt_parts["user_prompt"]),
            ],
            model_alias=model_alias or "gpt-4o",
            max_tokens=4096,
            temperature=temperature,
            prompt_category="REMEDIATION_PATCH",
        )

        composite_risk = finding_model.risk_score or 50.0
        cve_val = finding_model.cve_id
        cwe_val = finding_model.cwe_id

        try:
            llm_response = await self.gateway_service.generate_completion(
                organization_id, chat_req
            )
        except Exception as e:
            logger.error(
                "remediation.llm_generation_failed",
                finding_id=str(finding_id),
                error=str(e),
            )
            failed_model = await self.remediation_repo.create_remediation_plan(
                organization_id=organization_id,
                root_finding_id=finding_id,
                cve_id=cve_val,
                cwe_id=cwe_val,
                title=f"Remediation: {finding_model.title}",
                summary="",
                technical_solution="",
                business_solution="",
                risk_reduction_explanation="",
                validation_strategy="",
                composite_risk_score=composite_risk,
                ai_confidence_score=0.0,
                effectiveness_confidence_score=0.0,
                model_used=model_alias or "unknown",
                provider_used="unknown",
                prompt_version=prompt_version,
                status="FAILED",
                error_message=str(e)[:2000],
            )
            return _plan_model_to_dto(failed_model)

        # 10. Parse structured JSON with retry-once recovery
        parsed = self._try_parse_json(llm_response.content)
        if parsed is None:
            logger.warning(
                "remediation.malformed_json_retrying",
                finding_id=str(finding_id),
                model_used=llm_response.model_used,
            )
            parsed = await self._retry_json_repair(
                organization_id, llm_response.content, model_alias
            )

        if parsed is None or not isinstance(parsed, dict):
            logger.error("remediation.json_repair_failed", finding_id=str(finding_id))
            failed_model = await self.remediation_repo.create_remediation_plan(
                organization_id=organization_id,
                root_finding_id=finding_id,
                cve_id=cve_val,
                cwe_id=cwe_val,
                title=f"Remediation: {finding_model.title}",
                summary="",
                technical_solution="",
                business_solution="",
                risk_reduction_explanation="",
                validation_strategy="",
                composite_risk_score=composite_risk,
                ai_confidence_score=0.0,
                effectiveness_confidence_score=0.0,
                model_used=llm_response.model_used,
                provider_used=llm_response.provider_used,
                prompt_version=prompt_version,
                status="FAILED",
                error_message="LLM response JSON parsing failed after retry.",
            )
            return _plan_model_to_dto(failed_model)

        # Extract step data
        raw_steps = parsed.get("steps", [])
        validated_steps: List[Dict[str, Any]] = []
        for idx, sdict in enumerate(raw_steps, start=1):
            if not isinstance(sdict, dict):
                continue
            validated_steps.append(
                {
                    "sequence_number": idx,
                    "step_type": str(
                        sdict.get("step_type", "SECURITY_CONTROL")
                    ).upper(),
                    "title": str(sdict.get("title", f"Step {idx}")),
                    "description": str(sdict.get("description", "")),
                    "affected_component": str(
                        sdict.get("affected_component", "Application Core")
                    ),
                    "recommended_action": str(sdict.get("recommended_action", "")),
                    "validation_command": str(sdict.get("validation_command", ""))
                    or None,
                    "rollback_strategy": str(sdict.get("rollback_strategy", ""))
                    or None,
                    "confidence_score": float(sdict.get("confidence_score", 0.9)),
                }
            )

        # Extract patch data
        raw_patches = parsed.get("patch_suggestions", [])
        validated_patches: List[Dict[str, Any]] = []
        for pdict in raw_patches:
            if not isinstance(pdict, dict):
                continue
            validated_patches.append(
                {
                    "language": str(pdict.get("language", "PYTHON")).upper(),
                    "file_type": str(pdict.get("file_type", "SOURCE_CODE")).upper(),
                    "target_file_path": str(pdict.get("target_file_path", "")) or None,
                    "original_code_snippet": str(
                        pdict.get("original_code_snippet", "")
                    ),
                    "proposed_patch_diff": str(pdict.get("proposed_patch_diff", "")),
                    "explanation": str(pdict.get("explanation", "")),
                    "security_impact_notes": str(
                        pdict.get("security_impact_notes", "")
                    ),
                    "confidence_score": float(pdict.get("confidence_score", 0.9)),
                }
            )

        # 11. Persist plan model
        plan_model = await self.remediation_repo.create_remediation_plan(
            organization_id=organization_id,
            root_finding_id=finding_id,
            attack_path_id=latest_attack_path.id if latest_attack_path else None,
            cve_id=str(parsed.get("cve_id", cve_val or "")) or None,
            cwe_id=str(parsed.get("cwe_id", cwe_val or "")) or None,
            affected_version=str(parsed.get("affected_version", "")) or None,
            fixed_version=str(parsed.get("fixed_version", "")) or None,
            title=str(parsed.get("title", f"Remediation Plan: {finding_model.title}")),
            summary=str(parsed.get("summary", "")),
            technical_solution=str(parsed.get("technical_solution", "")),
            business_solution=str(parsed.get("business_solution", "")),
            risk_reduction_explanation=str(
                parsed.get("risk_reduction_explanation", "")
            ),
            validation_strategy=str(parsed.get("validation_strategy", "")),
            composite_risk_score=composite_risk,
            ai_confidence_score=float(parsed.get("ai_confidence_score", 0.95)),
            effectiveness_confidence_score=float(
                parsed.get("effectiveness_confidence_score", 0.90)
            ),
            requires_backup=bool(parsed.get("requires_backup", False)),
            requires_downtime=bool(parsed.get("requires_downtime", False)),
            rollback_available=bool(parsed.get("rollback_available", True)),
            model_used=llm_response.model_used,
            provider_used=llm_response.provider_used,
            prompt_version=prompt_version,
            status="GENERATED",
            steps_data=validated_steps,
            patches_data=validated_patches,
        )

        # 12. Record audit log event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="finding.ai_remediation_generated",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=actor_user_id,
            details={
                "model_used": llm_response.model_used,
                "provider_used": llm_response.provider_used,
                "prompt_version": prompt_version,
                "total_steps": len(validated_steps),
                "total_patches": len(validated_patches),
            },
        )

        return _plan_model_to_dto(plan_model)

    async def get_remediation_plan(
        self, organization_id: UUID, plan_id: UUID
    ) -> Optional[AIRemediationPlanDTO]:
        """Retrieve single remediation plan by ID with all steps and patch suggestions."""
        model = await self.remediation_repo.get_remediation_plan_by_id(
            organization_id, plan_id
        )
        if not model:
            return None
        return _plan_model_to_dto(model)

    async def list_remediation_plans_for_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[AIRemediationPlanDTO]:
        """Retrieve all remediation plans generated for a specific finding."""
        models = await self.remediation_repo.list_remediation_plans_by_finding(
            organization_id, finding_id
        )
        return [_plan_model_to_dto(m) for m in models]

    async def list_remediation_plans(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIRemediationPlanDTO]:
        """List organizational remediation history."""
        models = await self.remediation_repo.list_remediation_plans(
            organization_id, limit, offset
        )
        return [_plan_model_to_dto(m) for m in models]

    async def review_remediation_plan(
        self,
        organization_id: UUID,
        plan_id: UUID,
        reviewer_id: UUID,
        req: ReviewRemediationPlanRequest,
    ) -> AIRemediationPlanDTO:
        """Process analyst approval/rejection review workflow on a remediation plan."""
        updated = await self.remediation_repo.update_review_status(
            organization_id=organization_id,
            plan_id=plan_id,
            status=req.status,
            reviewer_id=reviewer_id,
            review_notes=req.review_notes,
        )
        if not updated:
            raise ResourceNotFoundException(
                f"Remediation plan '{plan_id}' not found in organization."
            )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="ai_remediation.reviewed",
            resource_type="ai_remediation_plan",
            resource_id=str(plan_id),
            actor_user_id=reviewer_id,
            details={"new_status": req.status, "notes": req.review_notes},
        )

        return _plan_model_to_dto(updated)

    # ── Private Helpers ─────────────────────────────────

    def _build_remediation_context(
        self,
        finding: SecurityFindingModel,
        evidence_artifacts: List[EvidenceArtifactModel],
        asset_node: Optional[AssetNodeModel],
        graph_relationships: List[AssetRelationshipModel],
        triage_status: Optional[str],
        explanation: Optional[AIFindingExplanationModel],
        impact_analysis: Optional[AIImpactAnalysisModel],
        attack_path: Optional[AIAttackPathModel],
    ) -> str:
        """Build structured markdown remediation context with multi-layer intelligence."""
        ctx: List[str] = []
        ctx.append(f"### Target Finding: {finding.title}")
        ctx.append(f"- **Severity**: {finding.severity}")
        ctx.append(f"- **Category**: {finding.category}")
        ctx.append(f"- **CVE ID**: {finding.cve_id or 'N/A'}")
        ctx.append(f"- **CWE ID**: {finding.cwe_id or 'N/A'}")
        if finding.risk_score is not None:
            ctx.append(f"- **Composite Risk Score**: {finding.risk_score:.1f}/100.0")

        if triage_status:
            ctx.append(f"- **Triage Status**: {triage_status}")

        if asset_node:
            ctx.append(
                f"\n**Affected Asset**: {asset_node.name} ({asset_node.node_type})"
            )

        if explanation:
            ctx.append(
                f"\n**AI Vulnerability Summary**: {explanation.vulnerability_summary}"
            )
            ctx.append(f"**Technical Root Cause**: {explanation.technical_root_cause}")

        if impact_analysis:
            ctx.append(
                f"\n**Technical Impact**: {impact_analysis.technical_impact_summary}"
            )
            ctx.append(
                f"**Executive Impact**: {impact_analysis.executive_impact_summary}"
            )

        if attack_path:
            ctx.append(f"\n**Attack Path Title**: {attack_path.title}")
            ctx.append(f"**Attack Path Summary**: {attack_path.attack_summary}")

        ctx.append(f"\n**Finding Description**:\n{finding.description or 'N/A'}")

        if evidence_artifacts:
            ctx.append(f"\n**Verified Proof Artifacts** ({len(evidence_artifacts)}):")
            for ea in evidence_artifacts[:5]:
                ctx.append(f"  - Artifact: {ea.artifact_type}")

        raw = "\n".join(ctx)
        return mask_sensitive_prompt_context(raw)

    def _try_parse_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Attempt to parse LLM output as JSON, stripping code fences."""
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
            logger.debug("remediation.json_parse_failed", snippet=text[:100])
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
            prompt_category="REMEDIATION_PATCH",
        )
        try:
            repair_resp = await self.gateway_service.generate_completion(
                organization_id, repair_req
            )
            return self._try_parse_json(repair_resp.content)
        except Exception as e:
            logger.error("remediation.json_repair_request_failed", error=str(e))
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
            logger.debug("remediation.triage_status_fetch_failed", error=str(e))
        return None
