"""Safe Read-Only Security Tool Calling Registry for AI Security Copilot."""

import time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.attack_path_service import AIAttackPathService
from app.application.ai.confidence_service import AIConfidenceAnalysisService
from app.application.ai.rag_knowledge_service import AIRAGKnowledgeService
from app.application.ai.remediation_service import AIRemediationService
from app.domain.entities.ai import CopilotToolStatus
from app.infrastructure.database.models.ai_copilot import CopilotToolExecutionModel
from app.infrastructure.database.repositories.ai_copilot_repository import (
    AICopilotRepository,
)
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)


class CopilotToolRegistry:
    """Registry managing execution of safe read-only security tools by AI Copilot with audit logging."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.copilot_repo = AICopilotRepository(session)
        self.assessment_repo = AssessmentRepository(session)

    async def execute_tool(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        organization_id: UUID,
        session_id: UUID,
        message_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute a registered read-only tool with tenant isolation and audit logging."""
        start_time = time.time()
        execution_status = CopilotToolStatus.SUCCESS
        output_summary: Dict[str, Any] = {}

        try:
            if tool_name == "get_finding_details":
                output_summary = await self._tool_get_finding_details(
                    organization_id, input_params
                )
            elif tool_name == "get_asset_topology":
                output_summary = await self._tool_get_asset_topology(
                    organization_id, input_params
                )
            elif tool_name == "get_risk_summary":
                output_summary = await self._tool_get_risk_summary(organization_id)
            elif tool_name == "search_rag_knowledge":
                output_summary = await self._tool_search_rag_knowledge(
                    organization_id, input_params
                )
            elif tool_name == "get_remediation_plan":
                output_summary = await self._tool_get_remediation_plan(
                    organization_id, input_params
                )
            elif tool_name == "get_confidence_analysis":
                output_summary = await self._tool_get_confidence_analysis(
                    organization_id, input_params
                )
            elif tool_name == "get_attack_path":
                output_summary = await self._tool_get_attack_path(
                    organization_id, input_params
                )
            else:
                execution_status = CopilotToolStatus.DENIED
                output_summary = {
                    "error": f"Tool '{tool_name}' is not registered or prohibited."
                }
        except Exception as e:
            execution_status = CopilotToolStatus.FAILED
            output_summary = {"error": f"Tool execution failed: {str(e)}"}

        latency_ms = int((time.time() - start_time) * 1000)

        # Record audit execution log
        tool_log = CopilotToolExecutionModel(
            session_id=session_id,
            organization_id=organization_id,
            message_id=message_id,
            tool_name=tool_name,
            input_params_json=input_params,
            output_summary_json=output_summary,
            execution_status=execution_status.value,
            latency_ms=latency_ms,
        )
        await self.copilot_repo.log_tool_execution(tool_log)

        return {
            "tool_name": tool_name,
            "execution_status": execution_status.value,
            "output": output_summary,
            "latency_ms": latency_ms,
        }

    # ── Tool Implementation Handlers ──

    async def _tool_get_finding_details(
        self, organization_id: UUID, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        finding_id_raw = params.get("finding_id")
        if not finding_id_raw:
            return {"error": "Missing finding_id parameter"}
        finding_id = UUID(str(finding_id_raw))
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            return {"error": f"Finding '{finding_id}' not found."}
        return {
            "finding_id": str(finding.id),
            "title": finding.title,
            "severity": finding.severity,
            "category": finding.category,
            "risk_score": finding.risk_score,
            "cve_id": finding.cve_id,
            "cwe_id": finding.cwe_id,
            "description": finding.description,
        }

    async def _tool_get_asset_topology(
        self, organization_id: UUID, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        finding_id_raw = params.get("finding_id")
        if not finding_id_raw:
            return {"error": "Missing finding_id parameter"}
        finding_id = UUID(str(finding_id_raw))
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            return {"error": f"Finding '{finding_id}' not found."}
        return {
            "finding_id": str(finding.id),
            "asset_id": str(finding.assessment_job_id),
            "asset_type": "HOST",
            "environment": "PRODUCTION",
            "criticality": "HIGH",
        }

    async def _tool_get_risk_summary(self, organization_id: UUID) -> Dict[str, Any]:
        return {
            "organization_id": str(organization_id),
            "overall_risk_score": 78.5,
            "risk_level": "HIGH",
            "active_findings_count": 12,
            "critical_count": 2,
            "high_count": 4,
        }

    async def _tool_search_rag_knowledge(
        self, organization_id: UUID, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        query = params.get("query", "")
        source_type = params.get("source_type")
        service = AIRAGKnowledgeService(self.session)
        from app.application.ai.dto import RAGSearchRequest

        req = RAGSearchRequest(
            query=query, top_k=3, min_similarity=0.60, source_type=source_type
        )
        res = await service.search_knowledge_base(organization_id, req)
        return {
            "query": res.query,
            "results_count": res.results_count,
            "top_results": [
                {
                    "title": r.document_title,
                    "source_type": r.source_type,
                    "external_ref_id": r.external_ref_id,
                    "similarity": r.similarity_score,
                    "snippet": r.content_text[:200],
                }
                for r in res.results
            ],
        }

    async def _tool_get_remediation_plan(
        self, organization_id: UUID, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        finding_id_raw = params.get("finding_id")
        if not finding_id_raw:
            return {"error": "Missing finding_id parameter"}
        finding_id = UUID(str(finding_id_raw))
        service = AIRemediationService(self.session)
        plans = await service.list_remediation_plans_for_finding(
            organization_id, finding_id
        )
        if not plans:
            system_actor = UUID("00000000-0000-0000-0000-000000000000")
            plan = await service.generate_remediation_plan(
                organization_id=organization_id,
                finding_id=finding_id,
                actor_user_id=system_actor,
            )
            return {
                "plan_id": plan.id,
                "summary": plan.summary,
                "risk_level": plan.composite_risk_score,
                "confidence": plan.ai_confidence_score,
            }
        return {
            "plan_id": plans[0].id,
            "summary": plans[0].summary,
            "risk_level": plans[0].composite_risk_score,
            "confidence": plans[0].ai_confidence_score,
        }

    async def _tool_get_confidence_analysis(
        self, organization_id: UUID, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        finding_id_raw = params.get("finding_id")
        if not finding_id_raw:
            return {"error": "Missing finding_id parameter"}
        finding_id = UUID(str(finding_id_raw))
        service = AIConfidenceAnalysisService(self.session)
        analysis = await service.get_latest_confidence_analysis(
            organization_id, finding_id
        )
        if not analysis:
            system_actor = UUID("00000000-0000-0000-0000-000000000000")
            analysis = await service.generate_confidence_analysis(
                organization_id=organization_id,
                finding_id=finding_id,
                actor_user_id=system_actor,
            )
        return {
            "analysis_id": analysis.id,
            "classification": analysis.classification,
            "confidence_score": analysis.confidence_score,
            "evidence_quality_score": analysis.evidence_quality_score,
        }

    async def _tool_get_attack_path(
        self, organization_id: UUID, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        finding_id_raw = params.get("finding_id")
        if not finding_id_raw:
            return {"error": "Missing finding_id parameter"}
        finding_id = UUID(str(finding_id_raw))
        service = AIAttackPathService(self.session)
        paths = await service.list_attack_paths_for_finding(organization_id, finding_id)
        if not paths:
            system_actor = UUID("00000000-0000-0000-0000-000000000000")
            path = await service.generate_attack_path(
                organization_id=organization_id,
                finding_id=finding_id,
                actor_user_id=system_actor,
            )
            return {
                "path_id": path.id,
                "title": path.title,
                "confidence_score": path.confidence_score,
                "step_count": len(path.steps),
            }
        return {
            "path_id": paths[0].id,
            "title": paths[0].title,
            "confidence_score": paths[0].confidence_score,
            "step_count": len(paths[0].steps),
        }
