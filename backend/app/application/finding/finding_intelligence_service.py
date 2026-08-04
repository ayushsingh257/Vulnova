"""Finding Intelligence Application Service for Vulnerability Workspace & Triage."""

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    AIExplanationSummaryDTO,
    AttackPathNodeDTO,
    CVSSDetailDTO,
    EPSSDetailDTO,
    EvidenceItemDTO,
    FindingAttackPathsResponse,
    FindingEvidenceResponse,
    FindingRemediationResponse,
    PatchSuggestionDTO,
    RemediationStepDTO,
    ScanOriginDTO,
    TriageHistoryItemDTO,
    VulnerabilityIntelligenceResponse,
    VulnerabilityRiskContextDTO,
)
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
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
from app.infrastructure.database.repositories.evidence_repository import (
    EvidenceRepository,
)
from app.infrastructure.database.repositories.finding_triage_repository import (
    FindingTriageRepository,
)

logger = get_logger("vulnova.finding_intelligence_service")

# Map of raw evidence types to human-readable UI labels
EVIDENCE_TYPE_LABELS: Dict[str, str] = {
    "HTTP_EXCHANGE": "HTTP Request / Response Exchange",
    "HTTP_REQUEST": "HTTP Request Payload",
    "HTTP_RESPONSE": "HTTP Response Payload",
    "SCREENSHOT": "Visual PNG Screenshot Proof",
    "DOM_SNAPSHOT": "Rendered Playwright DOM Snapshot",
    "PLUGIN_OUTPUT": "Scanner Plugin Terminal Output",
    "TRACE_LOG": "Payload Execution Trace Log",
    "HEADER_DATA": "HTTP Security Header Profile",
    "COOKIE_DATA": "Cookie Security Audit Data",
}


class FindingIntelligenceService:
    """Read-only orchestrator aggregating vulnerability intelligence, evidence, attack paths, and AI guidance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assessment_repo = AssessmentRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.triage_repo = FindingTriageRepository(session)
        self.ai_analysis_repo = AIAnalysisRepository(session)
        self.ai_attack_path_repo = AIAttackPathRepository(session)
        self.ai_remediation_repo = AIRemediationRepository(session)

    async def get_finding_details(
        self, organization_id: UUID, finding_id: UUID
    ) -> VulnerabilityIntelligenceResponse:
        """Retrieve full vulnerability intelligence details with tenant isolation."""
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            raise ResourceNotFoundException(
                f"Vulnerability finding {finding_id} not found."
            )

        job = await self.assessment_repo.get_job_by_id(
            organization_id, finding.assessment_job_id
        )

        # Parse CVSS JSON
        cvss_data = finding.cvss_json or {}
        cvss_dto = CVSSDetailDTO(
            version=cvss_data.get("version", "3.1"),
            base_score=float(cvss_data.get("base_score", 0.0)),
            vector_string=cvss_data.get("vector_string"),
            exploitability_score=cvss_data.get("exploitability_score"),
            impact_score=cvss_data.get("impact_score"),
        )

        # Parse EPSS JSON
        epss_data = finding.epss_json or {}
        epss_dto = EPSSDetailDTO(
            epss_score=float(epss_data.get("epss_score", 0.0)),
            percentile=float(epss_data.get("percentile", 0.0)),
        )

        # Risk context
        risk_score = float(finding.risk_score or 0.0)
        sla_hours = (
            24
            if finding.severity == "CRITICAL"
            else (72 if finding.severity == "HIGH" else 336)
        )
        risk_context = VulnerabilityRiskContextDTO(
            composite_risk_score=risk_score,
            remediation_sla_hours=sla_hours,
            risk_level=finding.severity,
            affected_asset_count=1,
            exploitability_score=cvss_dto.exploitability_score,
            impact_score=cvss_dto.impact_score,
        )

        # Scan origin
        scan_origin = ScanOriginDTO(
            job_id=str(finding.assessment_job_id),
            target_name=job.target_url if job else "Target Asset",
            target_environment="PRODUCTION",
            scan_profile=job.profile_id if job else "full_assessment",
            completed_at=(
                job.completed_at.isoformat() if (job and job.completed_at) else None
            ),
        )

        # Triage history
        triage_history_models = await self.triage_repo.get_triage_history(
            organization_id, finding_id
        )
        current_status = (
            triage_history_models[0].new_status
            if triage_history_models
            else "UNREVIEWED"
        )
        triage_history_dtos = [
            TriageHistoryItemDTO(
                id=str(th.id),
                previous_status=th.previous_status,
                new_status=th.new_status,
                actor_user_id=str(th.actor_user_id) if th.actor_user_id else None,
                comment=th.comment,
                risk_accepted_until=(
                    th.risk_accepted_until.isoformat()
                    if th.risk_accepted_until
                    else None
                ),
                created_at=th.created_at.isoformat(),
            )
            for th in triage_history_models
        ]

        # AI explanation
        explanation_model = await self.ai_analysis_repo.get_explanation_by_finding(
            organization_id, finding_id
        )
        ai_exp_dto: Optional[AIExplanationSummaryDTO] = None
        if explanation_model:
            ai_exp_dto = AIExplanationSummaryDTO(
                id=str(explanation_model.id),
                summary=explanation_model.vulnerability_summary,
                technical_details=explanation_model.technical_root_cause,
                impact_analysis=explanation_model.business_impact,
                confidence_score=1.0,
                status=explanation_model.status,
            )

        return VulnerabilityIntelligenceResponse(
            id=str(finding.id),
            organization_id=str(finding.organization_id),
            title=finding.title,
            description=finding.description,
            severity=finding.severity,
            category=finding.category,
            cve_id=finding.cve_id,
            cwe_id=finding.cwe_id,
            remediation=finding.remediation,
            cvss=cvss_dto,
            epss=epss_dto,
            risk_context=risk_context,
            scan_origin=scan_origin,
            triage_status=current_status,
            triage_history=triage_history_dtos,
            ai_explanation=ai_exp_dto,
            created_at=finding.created_at.isoformat(),
        )

    async def get_finding_evidence(
        self, organization_id: UUID, finding_id: UUID
    ) -> FindingEvidenceResponse:
        """Retrieve multi-modal proof evidence artifacts for a finding."""
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            raise ResourceNotFoundException(
                f"Vulnerability finding {finding_id} not found."
            )

        artifacts = await self.evidence_repo.list_finding_artifacts(
            organization_id, finding_id
        )

        items = [
            EvidenceItemDTO(
                id=str(art.id),
                finding_id=str(art.finding_id),
                artifact_type=art.artifact_type,
                type_label=EVIDENCE_TYPE_LABELS.get(
                    art.artifact_type, art.artifact_type.replace("_", " ").title()
                ),
                storage_path=art.storage_path,
                metadata=art.metadata_json,
                checksum=art.checksum,
                created_at=art.created_at.isoformat(),
            )
            for art in artifacts
        ]

        return FindingEvidenceResponse(
            finding_id=str(finding_id),
            evidence_items=items,
            total_count=len(items),
        )

    async def get_finding_attack_paths(
        self, organization_id: UUID, finding_id: UUID
    ) -> FindingAttackPathsResponse:
        """Retrieve attack chain relationship visualization for a finding."""
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            raise ResourceNotFoundException(
                f"Vulnerability finding {finding_id} not found."
            )

        attack_paths = await self.ai_attack_path_repo.list_attack_paths_by_finding(
            organization_id, finding_id
        )

        if not attack_paths:
            # Generate default conceptual nodes if AI attack path has not been run yet
            default_nodes = [
                AttackPathNodeDTO(
                    id="node-1",
                    asset_name="Internet Exposure Gateway",
                    asset_type="PUBLIC_INGRESS",
                    vulnerability_title="Public Boundary Probe",
                    relationship="EXTERNAL_TRAFFIC",
                    risk_impact="INFO",
                    sequence_number=1,
                ),
                AttackPathNodeDTO(
                    id="node-2",
                    asset_name=f"Target Endpoint ({finding.category})",
                    asset_type="API_ENDPOINT",
                    vulnerability_title=finding.title,
                    relationship="EXPOSES_VULNERABILITY",
                    risk_impact=finding.severity,
                    sequence_number=2,
                ),
                AttackPathNodeDTO(
                    id="node-3",
                    asset_name="Internal Application Core",
                    asset_type="APPLICATION_SERVER",
                    vulnerability_title="Potential Privilege Escalation / Data Exposure",
                    relationship="IMPACTS_SYSTEM",
                    risk_impact=finding.severity,
                    sequence_number=3,
                ),
            ]
            return FindingAttackPathsResponse(
                finding_id=str(finding_id),
                attack_path_id=None,
                title=f"Attack Path — {finding.title}",
                attack_summary="Conceptual attack chain based on discovered finding metadata.",
                composite_risk_score=float(finding.risk_score or 0.0),
                nodes=default_nodes,
            )

        path = attack_paths[0]
        nodes: List[AttackPathNodeDTO] = []
        for step in path.steps:
            nodes.append(
                AttackPathNodeDTO(
                    id=str(step.id),
                    asset_name=step.mitre_technique_name
                    or f"Step {step.sequence_number}",
                    asset_type=step.step_type or "EXPLOIT_STEP",
                    vulnerability_title=step.title,
                    relationship="PROGRESSES_TO",
                    risk_impact=path.status,
                    sequence_number=step.sequence_number,
                )
            )

        return FindingAttackPathsResponse(
            finding_id=str(finding_id),
            attack_path_id=str(path.id),
            title=path.title,
            attack_summary=path.attack_summary,
            composite_risk_score=float(path.composite_risk_score),
            nodes=nodes,
        )

    async def get_finding_remediation(
        self, organization_id: UUID, finding_id: UUID
    ) -> FindingRemediationResponse:
        """Retrieve AI remediation guidance, steps, and patch suggestions for a finding."""
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            raise ResourceNotFoundException(
                f"Vulnerability finding {finding_id} not found."
            )

        plans = await self.ai_remediation_repo.list_remediation_plans_by_finding(
            organization_id, finding_id
        )
        plan = plans[0] if plans else None

        if not plan:
            # Fallback advisory template if AI plan has not been generated
            default_steps = [
                RemediationStepDTO(
                    sequence_number=1,
                    step_type="INPUT_VALIDATION",
                    title="Validate & Sanitize Input Parameters",
                    description=f"Enforce strict server-side validation on user-supplied input targeting {finding.category}.",
                    estimated_minutes=30,
                ),
                RemediationStepDTO(
                    sequence_number=2,
                    step_type="CONFIGURATION",
                    title="Apply Recommended Security Headers / Controls",
                    description=finding.remediation
                    or "Follow OWASP ASVS guidelines to remediate this finding.",
                    estimated_minutes=45,
                ),
            ]
            default_patch = PatchSuggestionDTO(
                file_path="src/controllers/api_handler.py",
                language="python",
                patch_code=f"# Remediation Patch for {finding.title}\n# Ensure parameterized calls & escape output\n",
                explanation="Apply parameterized queries and safe context encoding.",
            )
            return FindingRemediationResponse(
                finding_id=str(finding_id),
                plan_id=None,
                title=f"Remediation Guidance — {finding.title}",
                summary=f"Recommended resolution steps for {finding.severity} severity {finding.category} finding.",
                explanation=finding.remediation
                or "Inspect finding details and apply recommended patches.",
                verification_steps=[
                    "Re-run Vulnova assessment scan against target asset.",
                    "Confirm finding status transitions to RESOLVED.",
                    "Verify zero regression in application integration tests.",
                ],
                steps=default_steps,
                patch_suggestions=[default_patch],
                ai_confidence_score=0.9,
            )

        steps_dtos = [
            RemediationStepDTO(
                sequence_number=s.sequence_number,
                step_type=s.step_type,
                title=s.title,
                description=s.description,
                estimated_minutes=30,
            )
            for s in plan.steps
        ]

        patch_dtos = [
            PatchSuggestionDTO(
                file_path=p.target_file_path,
                language=p.language,
                patch_code=p.proposed_patch_diff,
                explanation=p.explanation,
            )
            for p in plan.patch_suggestions
        ]

        verification_list = [
            "Re-run Vulnova assessment scan.",
            "Verify finding resolution in security dashboard.",
        ]

        return FindingRemediationResponse(
            finding_id=str(finding_id),
            plan_id=str(plan.id),
            title=plan.title,
            summary=plan.summary,
            explanation=plan.technical_solution,
            verification_steps=verification_list,
            steps=steps_dtos,
            patch_suggestions=patch_dtos,
            ai_confidence_score=float(plan.ai_confidence_score),
        )
