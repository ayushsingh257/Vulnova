"""Application Service orchestrating Vulnerability Assessment Jobs and Plugin Execution."""

import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.assessment_policy_engine import (
    AssessmentPolicyEngine,
)
from app.application.assessment.continuous_monitoring import (
    ContinuousMonitoringService,
)
from app.application.assessment.correlation_engine import (
    AssessmentCorrelationEngine,
)
from app.application.assessment.deduplication import FindingDeduplicator
from app.application.assessment.dto import (
    AssessmentJobResponse,
    CreateAssessmentRequest,
    EvidenceArtifactDTO,
    FindingDTO,
    PluginMetadataDTO,
    ScanPolicyDTO,
    ScanProfileDTO,
)
from app.application.assessment.finding_triage_service import FindingTriageService
from app.application.assessment.policy_engine import ScanPolicyEngine
from app.application.assessment.risk_engine import RiskIntelligenceEngine
from app.application.assessment.scan_lifecycle_manager import (
    ScanLifecycleManagerService,
)
from app.application.assessment.scan_profiles import ScanProfileRegistry
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import (
    ForbiddenException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.domain.entities.assessment import (
    AssessmentContext,
    Finding,
    ScanPolicy,
)
from app.domain.entities.scan_lifecycle import ScanExecutionState
from app.infrastructure.assessment.evidence_engine import EvidenceCollectionEngine
from app.infrastructure.assessment.plugins import SecurityHeadersPlugin  # noqa: F401
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.database.repositories.evidence_repository import (
    EvidenceRepository,
)
from app.infrastructure.discovery.ssrf_validator import (
    extract_base_domain,
    is_safe_target_url,
)

logger = get_logger("vulnova.assessment_service")


class AssessmentService:
    """Application Service orchestrating scan profiles, policy engines, vulnerability scanning plugins, risk intelligence, evidence collection, finding correlation, continuous monitoring, automated suppression, finding triage, and persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.audit_service = AuditLogService(session)
        self.plugin_registry = PluginRegistry()
        self.profile_registry = ScanProfileRegistry(self.plugin_registry)
        self.policy_engine = ScanPolicyEngine()
        self.risk_engine = RiskIntelligenceEngine()
        self.deduplicator = FindingDeduplicator()
        self.evidence_engine = EvidenceCollectionEngine()
        self.correlation_engine = AssessmentCorrelationEngine()
        self.monitoring_service = ContinuousMonitoringService(session)
        self.triage_service = FindingTriageService(session)
        self.assessment_policy_engine = AssessmentPolicyEngine(session)
        self.scan_lifecycle_manager = ScanLifecycleManagerService(
            session, repo=self.repo
        )

    async def create_and_run_assessment(
        self, req: CreateAssessmentRequest, current_user: UserModel
    ) -> AssessmentJobResponse:
        """Create an assessment job, execute plugins, apply risk intelligence normalization, deduplicate, and persist."""
        start_time = time.time()
        target_str = str(req.target_url).rstrip("/")
        base_domain = extract_base_domain(target_str)
        org_id = current_user.organization_id

        # 0. Pre-validate Authorized Assessment Contract (Phase 6.2)
        authorization = await self.assessment_policy_engine.validate_scan_authorization(
            organization_id=org_id,
            target_url=target_str,
            is_authorized_assessment=req.is_authorized_assessment,
            declared_by=current_user.id,
            authorization_scope=req.authorization_scope,
        )
        if not authorization.is_allowed:
            raise ForbiddenException(
                f"Scan authorization rejected: {authorization.rejection_reason}"
            )

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

        # 2. Determine Profile & Resolve Plugins
        profile_id = req.profile_id or "full_assessment"
        base_profile = self.profile_registry.get_profile(profile_id)

        enabled_ids = self.profile_registry.resolve_plugins_for_profile(
            profile_id=profile_id, custom_plugins=req.plugins
        )

        # 3. Construct & Validate Scan Policy
        base_policy = base_profile.default_policy if base_profile else ScanPolicy()
        if req.policy_override:
            for k, v in req.policy_override.items():
                if hasattr(base_policy, k):
                    setattr(base_policy, k, v)

        validated_policy = self.policy_engine.validate_policy(base_policy)
        policy_dict = {
            "concurrency_limit": validated_policy.concurrency_limit,
            "rate_limit_rps": validated_policy.rate_limit_rps,
            "respect_robots_txt": validated_policy.respect_robots_txt,
            "scope_include_patterns": validated_policy.scope_include_patterns,
            "scope_exclude_patterns": validated_policy.scope_exclude_patterns,
            "max_crawl_depth": validated_policy.max_crawl_depth,
            "max_requests": validated_policy.max_requests,
            "timeout_seconds": validated_policy.timeout_seconds,
            "stop_on_critical": validated_policy.stop_on_critical,
        }

        # 0.5. Acquire Distributed Target Lock (Phase 6.3)
        await self.scan_lifecycle_manager.acquire_target_lock(
            organization_id=org_id,
            target_url=target_str,
            ttl_seconds=3600,
        )

        # 4. Create Assessment Job Record (QUEUED)
        job_model = await self.repo.create_job(
            organization_id=org_id,
            target_url=target_str,
            enabled_plugins=enabled_ids,
            profile_id=profile_id,
            policy_json=policy_dict,
        )

        # Transition state: QUEUED -> CRAWLING
        await self.scan_lifecycle_manager.transition_state(
            organization_id=org_id,
            job_id=job_model.id,
            target_state=ScanExecutionState.CRAWLING,
            current_step="Asset Crawling & Fingerprinting",
            actor_id=current_user.id,
        )

        # 5. Audit Assessment Started
        await self.audit_service.record_event(
            organization_id=org_id,
            action="assessment.started",
            resource_type="assessment_job",
            resource_id=str(job_model.id),
            actor_user_id=current_user.id,
            details={
                "target_url": target_str,
                "profile_id": profile_id,
                "enabled_plugins": enabled_ids,
            },
        )

        # 6. Build Assessment Context with Execution Policy
        context = AssessmentContext(
            target_url=target_str,
            target_domain=base_domain,
            organization_id=org_id,
            policy=validated_policy,
        )

        # Transition state: CRAWLING -> ASSESSING
        await self.scan_lifecycle_manager.transition_state(
            organization_id=org_id,
            job_id=job_model.id,
            target_state=ScanExecutionState.ASSESSING,
            current_step="Plugin Vulnerability Scanning",
            actor_id=current_user.id,
        )

        # 7. Execute Plugins with Policy Safeguards
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
                    "assessment.executing_plugin",
                    plugin_id=pid,
                    target_url=target_str,
                    profile_id=profile_id,
                )
                findings = await plugin.execute(context)
                for f in findings:
                    f.assessment_job_id = job_model.id
                    raw_findings.append(f)

                # Evaluate emergency stop condition if enabled
                if self.policy_engine.should_stop_on_critical(
                    raw_findings, validated_policy
                ):
                    logger.warning(
                        "assessment.emergency_stop_critical",
                        job_id=str(job_model.id),
                    )
                    break

            # Transition state: ASSESSING -> AI_ANALYSIS
            await self.scan_lifecycle_manager.transition_state(
                organization_id=org_id,
                job_id=job_model.id,
                target_state=ScanExecutionState.AI_ANALYSIS,
                current_step="Finding Risk Intelligence & Evidence Capture",
                actor_id=current_user.id,
            )

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(
                "assessment.execution_failed", error=error_msg, job_id=str(job_model.id)
            )
            await self.scan_lifecycle_manager.handle_scan_failure(
                organization_id=org_id,
                job_id=job_model.id,
                exception=e,
            )

        # 8. Apply Risk Intelligence & Deduplication Normalization Pipeline
        enriched_findings = self.risk_engine.enrich_findings(
            raw_findings, context.asset_criticality
        )
        deduped_findings = self.deduplicator.deduplicate_findings(enriched_findings)

        # 9. Capture Multi-Modal Evidence Artifacts
        evidenced_findings = await self.evidence_engine.capture_evidence_batch(
            deduped_findings, context
        )

        # 10. Correlate Findings with Asset Graph & Update Posture
        correlated_findings = await self.correlation_engine.correlate_findings(
            evidenced_findings, context, self.session
        )

        # 11. Evaluate Automated Finding Suppression Rules
        final_findings = await self.triage_service.evaluate_suppression_rules(
            org_id, correlated_findings
        )

        # 12. Persist Correlated Findings & Evidence Artifacts to DB
        for f in final_findings:
            await self.repo.create_finding(org_id, f)
            for art in f.artifacts:
                await self.evidence_repo.create_artifact(org_id, art)

        # 12. Create Continuous Monitoring Posture Snapshot & Detect Changes
        await self.monitoring_service.process_scan_run(
            org_id, job_model.id, final_findings, context
        )

        duration = round(time.time() - start_time, 2)

        # 11. Transition State to COMPLETED or FAILED & Release Target Lock
        target_state = (
            ScanExecutionState.COMPLETED
            if status == "COMPLETED"
            else ScanExecutionState.FAILED
        )
        await self.scan_lifecycle_manager.transition_state(
            organization_id=org_id,
            job_id=job_model.id,
            target_state=target_state,
            current_step="Assessment Complete",
            duration_seconds=duration,
            error_message=error_msg,
            actor_id=current_user.id,
        )

        # 12. Audit Assessment Completed / Failed
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
                "profile_id": profile_id,
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
                evidence_count=len(f.artifacts),
                evidence_available=len(f.artifacts) > 0,
                artifacts=[
                    EvidenceArtifactDTO(
                        id=str(art.id),
                        finding_id=str(art.finding_id),
                        artifact_type=art.artifact_type.value,
                        storage_path=art.storage_path,
                        metadata=art.metadata,
                        checksum=art.checksum,
                        created_at=str(job_model.created_at),
                    )
                    for art in f.artifacts
                ],
                created_at=str(job_model.created_at),
            )
            for f in final_findings
        ]

        policy_dto = ScanPolicyDTO(
            concurrency_limit=validated_policy.concurrency_limit,
            rate_limit_rps=validated_policy.rate_limit_rps,
            respect_robots_txt=validated_policy.respect_robots_txt,
            scope_include_patterns=validated_policy.scope_include_patterns,
            scope_exclude_patterns=validated_policy.scope_exclude_patterns,
            max_crawl_depth=validated_policy.max_crawl_depth,
            max_requests=validated_policy.max_requests,
            timeout_seconds=validated_policy.timeout_seconds,
            stop_on_critical=validated_policy.stop_on_critical,
        )

        return AssessmentJobResponse(
            id=str(job_model.id),
            target_url=job_model.target_url,
            status=status,
            profile_id=profile_id,
            enabled_plugins=enabled_ids,
            policy=policy_dto,
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

        finding_dtos: List[FindingDTO] = []
        for f in job_findings:
            art_models = await self.evidence_repo.list_finding_artifacts(
                current_user.organization_id, f.id
            )
            art_dtos = [
                EvidenceArtifactDTO(
                    id=str(a.id),
                    finding_id=str(a.finding_id),
                    artifact_type=a.artifact_type,
                    storage_path=a.storage_path,
                    metadata=a.metadata_json or {},
                    checksum=a.checksum,
                    created_at=str(a.created_at),
                )
                for a in art_models
            ]
            finding_dtos.append(
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
                    evidence_count=len(art_dtos),
                    evidence_available=len(art_dtos) > 0,
                    artifacts=art_dtos,
                    created_at=str(f.created_at),
                )
            )

        plugins_dict = job.enabled_plugins_json or {}
        plugins_list: List[str] = plugins_dict.get("plugins", [])
        policy_dict: Dict[str, Any] = job.policy_json or {}
        policy_dto = (
            ScanPolicyDTO(
                concurrency_limit=int(policy_dict.get("concurrency_limit") or 5),
                rate_limit_rps=int(policy_dict.get("rate_limit_rps") or 10),
                respect_robots_txt=bool(policy_dict.get("respect_robots_txt", True)),
                scope_include_patterns=list(
                    policy_dict.get("scope_include_patterns") or []
                ),
                scope_exclude_patterns=list(
                    policy_dict.get("scope_exclude_patterns") or []
                ),
                max_crawl_depth=int(policy_dict.get("max_crawl_depth") or 3),
                max_requests=int(policy_dict.get("max_requests") or 500),
                timeout_seconds=float(policy_dict.get("timeout_seconds") or 30.0),
                stop_on_critical=bool(policy_dict.get("stop_on_critical", False)),
            )
            if policy_dict
            else None
        )

        return AssessmentJobResponse(
            id=str(job.id),
            target_url=job.target_url,
            status=job.status,
            profile_id=job.profile_id or "full_assessment",
            enabled_plugins=plugins_list,
            policy=policy_dto,
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
        finding_dtos: List[FindingDTO] = []
        for f in findings_models:
            art_models = await self.evidence_repo.list_finding_artifacts(
                current_user.organization_id, f.id
            )
            art_dtos = [
                EvidenceArtifactDTO(
                    id=str(a.id),
                    finding_id=str(a.finding_id),
                    artifact_type=a.artifact_type,
                    storage_path=a.storage_path,
                    metadata=a.metadata_json or {},
                    checksum=a.checksum,
                    created_at=str(a.created_at),
                )
                for a in art_models
            ]
            finding_dtos.append(
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
                    evidence_count=len(art_dtos),
                    evidence_available=len(art_dtos) > 0,
                    artifacts=art_dtos,
                    created_at=str(f.created_at),
                )
            )
        return finding_dtos

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

    def list_scan_profiles(self) -> List[ScanProfileDTO]:
        """List all available enterprise scan profiles."""
        profiles = self.profile_registry.list_profiles()
        return [
            ScanProfileDTO(
                id=p.id,
                name=p.name,
                description=p.description,
                plugin_ids=p.plugin_ids,
                default_policy=ScanPolicyDTO(
                    concurrency_limit=p.default_policy.concurrency_limit,
                    rate_limit_rps=p.default_policy.rate_limit_rps,
                    respect_robots_txt=p.default_policy.respect_robots_txt,
                    scope_include_patterns=p.default_policy.scope_include_patterns,
                    scope_exclude_patterns=p.default_policy.scope_exclude_patterns,
                    max_crawl_depth=p.default_policy.max_crawl_depth,
                    max_requests=p.default_policy.max_requests,
                    timeout_seconds=p.default_policy.timeout_seconds,
                    stop_on_critical=p.default_policy.stop_on_critical,
                ),
            )
            for p in profiles
        ]
