"""AI Attack Path Synthesis Application Service with MITRE ATT&CK Validation & Structured Output Recovery."""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    AIAttackPathDTO,
    AIChatCompletionRequest,
    AttackPathStepDTO,
    LLMMessageDTO,
    ReviewAttackPathRequest,
)
from app.application.ai.llm_gateway_service import LLMGatewayService
from app.application.ai.prompt_orchestrator_service import (
    PromptOrchestratorService,
    mask_sensitive_prompt_context,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.domain.entities.ai import KNOWN_MITRE_TECHNIQUES
from app.infrastructure.database.models.ai_attack_path import (
    AIAttackPathModel,
    AIAttackPathStepModel,
)
from app.infrastructure.database.models.assessment import (
    EvidenceArtifactModel,
    SecurityFindingModel,
)
from app.infrastructure.database.models.asset_graph import (
    AssetNodeModel,
    AssetRelationshipModel,
)
from app.infrastructure.database.repositories.ai_attack_path_repository import (
    AIAttackPathRepository,
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

logger = get_logger("vulnova.attack_path_service")

# Repair prompt for malformed JSON recovery
JSON_REPAIR_SYSTEM_PROMPT = (
    "You are a JSON repair assistant. The user will give you malformed text that was "
    "supposed to be valid JSON representing an attack path. Extract the information and return ONLY "
    "a valid JSON object with keys: title, attack_summary, confidence_score, and steps "
    "(an array of objects with keys: sequence_number, step_type, title, description, "
    "mitre_tactic, mitre_technique_id, mitre_technique_name, attacker_action, "
    "required_privilege, evidence_reference, confidence_score). "
    "Do not include any text outside the JSON object."
)


def _step_model_to_dto(model: AIAttackPathStepModel) -> AttackPathStepDTO:
    """Map step ORM model to Pydantic DTO."""
    return AttackPathStepDTO(
        id=str(model.id),
        sequence_number=model.sequence_number,
        step_type=model.step_type,
        asset_node_id=str(model.asset_node_id) if model.asset_node_id else None,
        finding_id=str(model.finding_id) if model.finding_id else None,
        title=model.title,
        description=model.description,
        mitre_tactic=model.mitre_tactic,
        mitre_technique_id=model.mitre_technique_id,
        mitre_technique_name=model.mitre_technique_name,
        attacker_action=model.attacker_action,
        required_privilege=model.required_privilege,
        evidence_reference=model.evidence_reference,
        confidence_score=model.confidence_score,
    )


def _path_model_to_dto(model: AIAttackPathModel) -> AIAttackPathDTO:
    """Map path ORM model to Pydantic DTO."""
    steps_dtos = [_step_model_to_dto(s) for s in (model.steps or [])]
    return AIAttackPathDTO(
        id=str(model.id),
        root_finding_id=str(model.root_finding_id),
        source_asset_id=str(model.source_asset_id) if model.source_asset_id else None,
        target_asset_id=str(model.target_asset_id) if model.target_asset_id else None,
        title=model.title,
        attack_summary=model.attack_summary,
        composite_risk_score=model.composite_risk_score,
        confidence_score=model.confidence_score,
        model_used=model.model_used,
        provider_used=model.provider_used,
        prompt_version=model.prompt_version,
        status=model.status,
        steps=steps_dtos,
        review_notes=model.review_notes,
        reviewed_by=str(model.reviewed_by) if model.reviewed_by else None,
        reviewed_at=str(model.reviewed_at) if model.reviewed_at else None,
        error_message=model.error_message,
        created_at=str(model.created_at),
    )


class AIAttackPathService:
    """Application service synthesizing evidence-grounded AI attack paths with MITRE ATT&CK validation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.path_repo = AIAttackPathRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.triage_repo = FindingTriageRepository(session)
        self.asset_graph_repo = AssetGraphRepository(session)
        self.prompt_service = PromptOrchestratorService(session)
        self.gateway_service = LLMGatewayService(session)
        self.audit_service = AuditLogService(session)

    async def generate_attack_path(
        self,
        organization_id: UUID,
        finding_id: UUID,
        actor_user_id: UUID,
        model_alias: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIAttackPathDTO:
        """Synthesize an evidence-grounded AI attack path for a security finding.

        Workflow:
        1. Fetch finding (tenant-isolated)
        2. Fetch evidence artifacts, asset node, asset graph relationships, triage status
        3. Build evidence-grounded attack context (sanitized via mask_sensitive_prompt_context)
        4. Resolve ATTACK_PATH_SYNTHESIS prompt template
        5. Execute LLM completion via gateway
        6. Parse structured JSON (with retry-once repair recovery)
        7. Validate MITRE ATT&CK techniques and compute path-level confidence score
        8. Persist attack path and steps
        9. Record audit log event
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

        # 3. Fetch associated asset node and domain graph relationships
        asset_node: Optional[AssetNodeModel] = None
        graph_relationships: List[AssetRelationshipModel] = []
        neighbor_nodes: List[AssetNodeModel] = []
        if finding_model.asset_node_id:
            try:
                asset_node = await self.asset_graph_repo.get_node_by_id(
                    organization_id, finding_model.asset_node_id
                )
                if asset_node and asset_node.value:
                    nodes, rels = await self.asset_graph_repo.get_graph_by_domain(
                        organization_id, asset_node.value
                    )
                    graph_relationships = rels if rels else []
                    neighbor_nodes = nodes if nodes else []
            except Exception as e:
                logger.debug("attack_path.graph_fetch_failed", error=str(e))

        # 4. Fetch triage status
        triage_status = await self._get_latest_triage_status(
            organization_id, finding_id
        )

        # 5. Build sanitized attack context
        attack_context = self._build_attack_context(
            finding=finding_model,
            evidence_artifacts=evidence_artifacts,
            asset_node=asset_node,
            graph_relationships=graph_relationships,
            neighbor_nodes=neighbor_nodes,
            triage_status=triage_status,
        )

        # 6. Resolve prompt template and render
        prompt_parts = await self.prompt_service.render_prompt(
            organization_id=organization_id,
            category="ATTACK_PATH_SYNTHESIS",
            variables={"attack_context": attack_context},
        )

        prompt_version = 1
        active_template = await self.gateway_service.ai_repo.get_active_prompt_template(
            organization_id, "ATTACK_PATH_SYNTHESIS"
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
            prompt_category="ATTACK_PATH_SYNTHESIS",
        )

        composite_risk = finding_model.risk_score or 50.0

        try:
            llm_response = await self.gateway_service.generate_completion(
                organization_id, chat_req
            )
        except Exception as e:
            logger.error(
                "attack_path.llm_generation_failed",
                finding_id=str(finding_id),
                error=str(e),
            )
            failed_model = await self.path_repo.create_attack_path(
                organization_id=organization_id,
                root_finding_id=finding_id,
                title=f"Attack Path: {finding_model.title}",
                attack_summary="",
                composite_risk_score=composite_risk,
                confidence_score=0.0,
                model_used=model_alias or "unknown",
                provider_used="unknown",
                prompt_version=prompt_version,
                status="FAILED",
                error_message=str(e)[:2000],
            )
            return _path_model_to_dto(failed_model)

        # 8. Parse structured JSON response with retry-once recovery
        parsed = self._try_parse_json(llm_response.content)
        if parsed is None:
            logger.warning(
                "attack_path.malformed_json_retrying",
                finding_id=str(finding_id),
                model_used=llm_response.model_used,
            )
            parsed = await self._retry_json_repair(
                organization_id, llm_response.content, model_alias
            )

        if parsed is None or not isinstance(parsed, dict):
            logger.error(
                "attack_path.json_repair_failed",
                finding_id=str(finding_id),
            )
            failed_model = await self.path_repo.create_attack_path(
                organization_id=organization_id,
                root_finding_id=finding_id,
                title=f"Attack Path: {finding_model.title}",
                attack_summary="",
                composite_risk_score=composite_risk,
                confidence_score=0.0,
                model_used=llm_response.model_used,
                provider_used=llm_response.provider_used,
                prompt_version=prompt_version,
                status="FAILED",
                error_message="LLM response JSON parsing failed after retry.",
            )
            return _path_model_to_dto(failed_model)

        # 9. Validate MITRE techniques and sanitize step items
        raw_steps = parsed.get("steps", [])
        validated_steps: List[Dict[str, Any]] = []
        step_confidences: List[float] = []

        for idx, step_dict in enumerate(raw_steps, start=1):
            if not isinstance(step_dict, dict):
                continue

            tech_id = str(step_dict.get("mitre_technique_id", "T1190")).upper()
            tech_name = str(step_dict.get("mitre_technique_name", ""))

            # MITRE Validation Registry Check
            if tech_id in KNOWN_MITRE_TECHNIQUES:
                official_name = KNOWN_MITRE_TECHNIQUES[tech_id]
                if not tech_name:
                    tech_name = official_name
            else:
                if not tech_name:
                    tech_name = f"Unverified Technique ({tech_id})"
                else:
                    tech_name = f"{tech_name} (Unverified)"

            conf = float(step_dict.get("confidence_score", 0.9))
            conf = max(0.0, min(1.0, conf))
            step_confidences.append(conf)

            step_entry = {
                "sequence_number": idx,
                "step_type": str(step_dict.get("step_type", "INITIAL_ACCESS")).upper(),
                "asset_node_id": finding_model.asset_node_id,
                "finding_id": finding_id if idx == 1 else None,
                "title": str(step_dict.get("title", f"Step {idx}")),
                "description": str(step_dict.get("description", "")),
                "mitre_tactic": str(step_dict.get("mitre_tactic", "Initial Access")),
                "mitre_technique_id": tech_id,
                "mitre_technique_name": tech_name,
                "attacker_action": str(step_dict.get("attacker_action", "")),
                "required_privilege": str(step_dict.get("required_privilege", "None")),
                "evidence_reference": str(step_dict.get("evidence_reference", ""))
                or None,
                "confidence_score": conf,
            }
            validated_steps.append(step_entry)

        # Calculate path-level overall confidence_score
        path_confidence = float(parsed.get("confidence_score", 0.0))
        if path_confidence <= 0.0 or path_confidence > 1.0:
            if step_confidences:
                # Cumulative product of step confidences or average
                path_confidence = round(
                    sum(step_confidences) / len(step_confidences), 2
                )
            else:
                path_confidence = 0.85

        # 10. Persist attack path model
        path_model = await self.path_repo.create_attack_path(
            organization_id=organization_id,
            root_finding_id=finding_id,
            source_asset_id=finding_model.asset_node_id,
            target_asset_id=finding_model.asset_node_id,
            title=str(parsed.get("title", f"Attack Path: {finding_model.title}")),
            attack_summary=str(parsed.get("attack_summary", "")),
            composite_risk_score=composite_risk,
            confidence_score=path_confidence,
            model_used=llm_response.model_used,
            provider_used=llm_response.provider_used,
            prompt_version=prompt_version,
            status="GENERATED",
            steps_data=validated_steps,
        )

        # 11. Record audit event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="finding.ai_attack_path_synthesized",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=actor_user_id,
            details={
                "model_used": llm_response.model_used,
                "provider_used": llm_response.provider_used,
                "prompt_version": prompt_version,
                "confidence_score": path_confidence,
                "total_steps": len(validated_steps),
            },
        )

        return _path_model_to_dto(path_model)

    async def get_attack_path(
        self, organization_id: UUID, path_id: UUID
    ) -> Optional[AIAttackPathDTO]:
        """Retrieve single attack path by ID with all steps."""
        model = await self.path_repo.get_attack_path_by_id(organization_id, path_id)
        if not model:
            return None
        return _path_model_to_dto(model)

    async def list_attack_paths_for_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[AIAttackPathDTO]:
        """Retrieve all attack paths generated for a specific finding."""
        models = await self.path_repo.list_attack_paths_by_finding(
            organization_id, finding_id
        )
        return [_path_model_to_dto(m) for m in models]

    async def list_attack_paths(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIAttackPathDTO]:
        """List organizational attack path history."""
        models = await self.path_repo.list_attack_paths(organization_id, limit, offset)
        return [_path_model_to_dto(m) for m in models]

    async def review_attack_path(
        self,
        organization_id: UUID,
        path_id: UUID,
        reviewer_id: UUID,
        req: ReviewAttackPathRequest,
    ) -> AIAttackPathDTO:
        """Record analyst review status and feedback notes on an attack path."""
        updated = await self.path_repo.update_review_status(
            organization_id=organization_id,
            path_id=path_id,
            status=req.status,
            reviewer_id=reviewer_id,
            review_notes=req.review_notes,
        )
        if not updated:
            raise ResourceNotFoundException(
                f"Attack path '{path_id}' not found in organization."
            )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="ai_attack_path.reviewed",
            resource_type="ai_attack_path",
            resource_id=str(path_id),
            actor_user_id=reviewer_id,
            details={"new_status": req.status, "notes": req.review_notes},
        )

        return _path_model_to_dto(updated)

    # ── Private Helpers ─────────────────────────────────

    def _build_attack_context(
        self,
        finding: SecurityFindingModel,
        evidence_artifacts: List[EvidenceArtifactModel],
        asset_node: Optional[AssetNodeModel],
        graph_relationships: List[AssetRelationshipModel],
        neighbor_nodes: List[AssetNodeModel],
        triage_status: Optional[str],
    ) -> str:
        """Build structured markdown attack context enforcing strict evidence grounding."""
        ctx: List[str] = []
        ctx.append(f"### Target Vulnerability: {finding.title}")
        ctx.append(f"- **Severity**: {finding.severity}")
        ctx.append(f"- **Category**: {finding.category}")
        ctx.append(f"- **CVE ID**: {finding.cve_id or 'N/A'}")
        ctx.append(f"- **CWE ID**: {finding.cwe_id or 'N/A'}")

        if finding.risk_score is not None:
            ctx.append(f"- **Composite Risk Score**: {finding.risk_score:.1f}/100.0")

        if triage_status:
            ctx.append(f"- **Triage Status**: {triage_status}")

        if asset_node:
            ctx.append(f"\n**Entry Asset Node**: {asset_node.name}")
            ctx.append(f"- **Node Type**: {asset_node.node_type}")
            ctx.append(f"- **Node Value**: {asset_node.value}")

        if neighbor_nodes:
            node_names = [n.name for n in neighbor_nodes[:10]]
            ctx.append(f"\n**Connected Asset Graph Topology**: {', '.join(node_names)}")

        if graph_relationships:
            ctx.append(f"\n**Graph Relationship Edges** ({len(graph_relationships)}):")
            for rel in graph_relationships[:5]:
                ctx.append(f"  - Edge: {rel.relationship_type}")

        ctx.append(f"\n**Vulnerability Description**:\n{finding.description or 'N/A'}")

        if evidence_artifacts:
            ctx.append(
                f"\n**Verified Evidence Proof** ({len(evidence_artifacts)} items):"
            )
            for ea in evidence_artifacts[:5]:
                ctx.append(
                    f"  - Artifact Type: {ea.artifact_type}, Path: {ea.storage_path}"
                )

        raw = "\n".join(ctx)
        return mask_sensitive_prompt_context(raw)

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
            logger.debug("attack_path.json_parse_failed", content_snippet=text[:100])
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
            prompt_category="ATTACK_PATH_SYNTHESIS",
        )
        try:
            repair_resp = await self.gateway_service.generate_completion(
                organization_id, repair_req
            )
            return self._try_parse_json(repair_resp.content)
        except Exception as e:
            logger.error("attack_path.json_repair_request_failed", error=str(e))
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
            logger.debug("attack_path.triage_status_fetch_failed", error=str(e))
        return None
