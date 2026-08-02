"""Application Service orchestrating Vulnerability Assessment Jobs and Plugin Execution."""

import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.deduplication import FindingDeduplicator
from app.application.assessment.dto import (
    AssessmentJobResponse,
    CreateAssessmentRequest,
    FindingDTO,
    PluginMetadataDTO,
)
from app.application.assessment.risk_engine import RiskIntelligenceEngine
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.domain.entities.assessment import (
    AssessmentContext,
    Finding,
)
from app.infrastructure.assessment.plugins import SecurityHeadersPlugin  # noqa: F401
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.discovery.ssrf_validator import (
    extract_base_domain,
    is_safe_target_url,
)

logger = get_logger("vulnova.assessment_service")


class AssessmentService:
    """Application Service orchestrating vulnerability scanning plugins, risk intelligence, and findings persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)
        self.audit_service = AuditLogService(session)
        self.plugin_registry = PluginRegistry()
        self.risk_engine = RiskIntelligenceEngine()
        self.deduplicator = FindingDeduplicator()

    async def create_and_run_assessment(
        self, req: CreateAssessmentRequest, current_user: UserModel
    ) -> AssessmentJobResponse:
        """Create an assessment job, execute plugins, apply risk intelligence normalization, deduplicate, and persist."""
        start_time = time.time()
        target_str = str(req.target_url).rstrip("/")
        base_domain = extract_base_domain(target_str)
        org_id = current_user.organization_id

        # 1. Pre-validate SSRF Egress Safety
        is_safe, reason = is_safe_target_url(target_str)
        if not is_safe:
            logger.warning(
                "assessment.run_rejected_unsafe_target",
                target_url=target_str,
                reason=reason,
                org_id=str(org_id),
            )
            await self.audit_service.record_event(
                organization_id=org_id,
                action="assessment.rejected",
                resource_type="target",
                resource_id=target_str,
                actor_user_id=current_user.id,
                details={"target_url": target_str, "reason": reason},
            )
            raise ValidationException(f"Target URL is prohibited: {reason}")

        # 2. Determine Plugins to Execute
        available_plugins = self.plugin_registry.list_plugins()
        enabled_ids = req.plugins or [p.id for p in available_plugins]

        # 3. Create Assessment Job Record (PENDING)
        job_model = await self.repo.create_job(
            organization_id=org_id,
            target_url=target_str,
            enabled_plugins=enabled_ids,
        )

        # 4. Audit Assessment Started
        await self.audit_service.record_event(
            organization_id=org_id,
            action="assessment.started",
            resource_type="assessment_job",
            resource_id=str(job_model.id),
            actor_user_id=current_user.id,
            details={"target_url": target_str, "enabled_plugins": enabled_ids},
        )

        # 5. Build Generic Assessment Context
        context = AssessmentContext(
            target_url=target_str,
            target_domain=base_domain,
            organization_id=org_id,
        )

        # 6. Execute Plugins Decoupled from AssessmentService
        raw_findings: List[Finding] = []
        status = "COMPLETED"
        error_msg: Optional[str] = None

        try:
            for pid in enabled_ids:
                plugin = self.plugin_registry.get_plugin(pid)
                if not plugin:
                    logger.warning("assessment.plugin_not_found", plugin_id=pid)
                    continue

                logger.info(
                    "assessment.executing_plugin", plugin_id=pid, target_url=target_str
                )
                findings = await plugin.execute(context)
                for f in findings:
                    f.assessment_job_id = job_model.id
                    raw_findings.append(f)

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(
                "assessment.execution_failed", error=error_msg, job_id=str(job_model.id)
            )

        # 7. Apply Risk Intelligence & Deduplication Normalization Pipeline
        enriched_findings = self.risk_engine.enrich_findings(
            raw_findings, context.asset_criticality
        )
        final_findings = self.deduplicator.deduplicate_findings(enriched_findings)

        # 8. Persist Normalized Findings to DB
        for f in final_findings:
            await self.repo.create_finding(org_id, f)

        duration = round(time.time() - start_time, 2)

        # 9. Update Job Status & Duration
        await self.repo.update_job_status(
            organization_id=org_id,
            job_id=job_model.id,
            status=status,
            duration_seconds=duration,
            error_message=error_msg,
        )

        # 10. Audit Assessment Completed / Failed
        audit_action = (
            "assessment.completed" if status == "COMPLETED" else "assessment.failed"
        )
        await self.audit_service.record_event(
            organization_id=org_id,
            action=audit_action,
            resource_type="assessment_job",
            resource_id=str(job_model.id),
            actor_user_id=current_user.id,
            details={
                "target_url": target_str,
                "total_findings": len(final_findings),
                "duration_seconds": duration,
                "error": error_msg,
            },
        )

        finding_dtos = [
            FindingDTO(
                id=str(f.id),
                assessment_job_id=str(f.assessment_job_id),
                plugin_id=f.plugin_id,
                title=f.title,
                description=f.description,
                severity=f.severity.value,
                category=f.category.value,
                cve_id=f.cve_id,
                cwe_id=f.cwe_id,
                remediation=f.remediation,
                evidence=f.evidence,
                cvss=(
                    {
                        "version": f.cvss.version,
                        "base_score": f.cvss.base_score,
                        "vector_string": f.cvss.vector_string,
                    }
                    if f.cvss
                    else None
                ),
                epss=(
                    {
                        "epss_score": f.epss.epss_score,
                        "percentile": f.epss.percentile,
                    }
                    if f.epss
                    else None
                ),
                risk_score=f.risk.composite_risk_score if f.risk else None,
                business_impact=f.risk.business_impact if f.risk else None,
                confidence=f.confidence.value if f.confidence else "HIGH",
                is_duplicate=f.is_duplicate,
                canonical_finding_id=(
                    str(f.canonical_finding_id) if f.canonical_finding_id else None
                ),
                fix_sla_hours=f.risk.fix_sla_hours if f.risk else None,
                created_at=str(job_model.created_at),
            )
            for f in final_findings
        ]

        return AssessmentJobResponse(
            id=str(job_model.id),
            target_url=job_model.target_url,
            status=status,
            enabled_plugins=enabled_ids,
            total_findings=len(finding_dtos),
            findings=finding_dtos,
            duration_seconds=duration,
            error_message=error_msg,
            created_at=str(job_model.created_at),
        )

    async def get_assessment_job(
        self, job_id: UUID, current_user: UserModel
    ) -> AssessmentJobResponse:
        """Query assessment job status and associated findings."""
        job = await self.repo.get_job_by_id(current_user.organization_id, job_id)
        if not job:
            raise ResourceNotFoundException(f"Assessment job '{job_id}' not found")

        findings_models = await self.repo.list_findings(
            organization_id=current_user.organization_id
        )
        job_findings = [f for f in findings_models if f.assessment_job_id == job_id]

        finding_dtos = [
            FindingDTO(
                id=str(f.id),
                assessment_job_id=str(f.assessment_job_id),
                plugin_id=f.plugin_id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                category=f.category,
                cve_id=f.cve_id,
                cwe_id=f.cwe_id,
                remediation=f.remediation,
                evidence=f.evidence_json or {},
                cvss=f.cvss_json,
                epss=f.epss_json,
                risk_score=f.risk_score,
                confidence=f.confidence,
                is_duplicate=f.is_duplicate,
                canonical_finding_id=(
                    str(f.canonical_finding_id) if f.canonical_finding_id else None
                ),
                created_at=str(f.created_at),
            )
            for f in job_findings
        ]

        plugins_dict = job.enabled_plugins_json or {}
        plugins_list: List[str] = plugins_dict.get("plugins", [])

        return AssessmentJobResponse(
            id=str(job.id),
            target_url=job.target_url,
            status=job.status,
            enabled_plugins=plugins_list,
            total_findings=len(finding_dtos),
            findings=finding_dtos,
            duration_seconds=job.duration_seconds,
            error_message=job.error_message,
            created_at=str(job.created_at),
        )

    async def list_findings(
        self,
        current_user: UserModel,
        severity: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[FindingDTO]:
        """List all discovered security findings for an organization."""
        findings_models = await self.repo.list_findings(
            organization_id=current_user.organization_id,
            severity=severity,
            category=category,
        )
        return [
            FindingDTO(
                id=str(f.id),
                assessment_job_id=str(f.assessment_job_id),
                plugin_id=f.plugin_id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                category=f.category,
                cve_id=f.cve_id,
                cwe_id=f.cwe_id,
                remediation=f.remediation,
                evidence=f.evidence_json or {},
                cvss=f.cvss_json,
                epss=f.epss_json,
                risk_score=f.risk_score,
                confidence=f.confidence,
                is_duplicate=f.is_duplicate,
                canonical_finding_id=(
                    str(f.canonical_finding_id) if f.canonical_finding_id else None
                ),
                created_at=str(f.created_at),
            )
            for f in findings_models
        ]

    def list_registered_plugins(self) -> List[PluginMetadataDTO]:
        """List all available assessment plugins in the system."""
        plugins = self.plugin_registry.list_plugins()
        return [
            PluginMetadataDTO(
                id=p.id,
                name=p.name,
                version=p.version,
                description=p.description,
                category=p.category.value,
                author=p.author,
                supported_asset_types=[a.value for a in p.supported_asset_types],
                required_permissions=p.required_permissions,
            )
            for p in plugins
        ]
