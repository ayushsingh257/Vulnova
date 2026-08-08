"""Security Audit Service: Orchestrates SAST, DAST, SCA, Config, and RBAC Security Verification."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.infrastructure.security_audit.analyzers.api_analyzer import (
    APISecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.auth_analyzer import (
    AuthenticationSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.base import BaseSecurityAnalyzer
from app.infrastructure.security_audit.analyzers.config_analyzer import (
    ConfigurationSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.container_analyzer import (
    ContainerSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.dependency_analyzer import (
    DependencySecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.rbac_analyzer import (
    AuthorizationRBACAnalyzer,
)
from app.infrastructure.security_audit.analyzers.sast_analyzer import (
    SASTSecurityAnalyzer,
)
from app.infrastructure.security_audit.analyzers.secret_analyzer import (
    SecretExposureAnalyzer,
)
from app.infrastructure.security_audit.dto import (
    AuditFindingStatus,
    AuditSeverity,
    RemediateFindingRequestDTO,
    RunSecurityAuditRequestDTO,
    SecurityAuditExecutionDTO,
    SecurityAuditFindingDTO,
    SecurityAuditStatusDTO,
)

logger = structlog.get_logger(__name__)


class SecurityAuditService:
    """Enterprise service coordinating automated static and dynamic security penetration audits."""

    # In-memory findings registry keyed by organization_id -> List[SecurityAuditFindingDTO]
    _findings_store: Dict[UUID, List[SecurityAuditFindingDTO]] = {}
    _audit_history: Dict[UUID, List[SecurityAuditExecutionDTO]] = {}

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session
        self.audit_logger = AuditLogService(session) if session else None
        self.analyzers: List[BaseSecurityAnalyzer] = [
            SASTSecurityAnalyzer(),
            DependencySecurityAnalyzer(),
            ConfigurationSecurityAnalyzer(),
            APISecurityAnalyzer(),
            AuthenticationSecurityAnalyzer(),
            AuthorizationRBACAnalyzer(),
            SecretExposureAnalyzer(),
            ContainerSecurityAnalyzer(),
        ]

    async def execute_security_audit(
        self,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
        request: Optional[RunSecurityAuditRequestDTO] = None,
    ) -> SecurityAuditExecutionDTO:
        """Run full multi-domain security audit and penetration verification."""
        audit_id = uuid4()
        executed_at = datetime.now(timezone.utc)
        target_categories = (
            request.categories if request and request.categories else None
        )

        logger.info(
            "security_audit_execution_started",
            audit_id=str(audit_id),
            organization_id=str(organization_id),
            categories=target_categories,
        )

        if self.audit_logger:
            try:
                await self.audit_logger.record_event(
                    organization_id=organization_id,
                    action="security_audit.started",
                    resource_type="security_audit",
                    resource_id=str(audit_id),
                    actor_user_id=actor_user_id,
                    details={
                        "categories": target_categories or "ALL",
                        "executed_at": executed_at.isoformat(),
                    },
                )
            except Exception as e:
                logger.warning("security_audit_start_audit_log_failed", error=str(e))

        all_findings: List[SecurityAuditFindingDTO] = []
        categories_analyzed: List[str] = []

        for analyzer in self.analyzers:
            if target_categories and analyzer.category_name not in target_categories:
                continue

            categories_analyzed.append(analyzer.category_name)
            category_findings = analyzer.run_analysis(
                request.details if request else None
            )
            all_findings.extend(category_findings)

        # Store in-memory
        self._findings_store[organization_id] = all_findings

        # Calculate metrics
        critical_count = sum(
            1 for f in all_findings if f.severity == AuditSeverity.CRITICAL.value
        )
        high_count = sum(
            1 for f in all_findings if f.severity == AuditSeverity.HIGH.value
        )
        medium_count = sum(
            1 for f in all_findings if f.severity == AuditSeverity.MEDIUM.value
        )
        low_count = sum(
            1 for f in all_findings if f.severity == AuditSeverity.LOW.value
        )

        open_count = sum(
            1
            for f in all_findings
            if f.remediation_status == AuditFindingStatus.OPEN.value
        )
        remediated_count = sum(
            1
            for f in all_findings
            if f.remediation_status
            in (
                AuditFindingStatus.REMEDIATED.value,
                AuditFindingStatus.ACCEPTED_RISK.value,
                AuditFindingStatus.FALSE_POSITIVE.value,
            )
        )

        total_findings = len(all_findings)
        # Compute security posture score
        if total_findings == 0:
            security_score = 100.0
            status = "PASSED"
        else:
            open_critical = sum(
                1
                for f in all_findings
                if f.severity == AuditSeverity.CRITICAL.value
                and f.remediation_status == AuditFindingStatus.OPEN.value
            )
            open_high = sum(
                1
                for f in all_findings
                if f.severity == AuditSeverity.HIGH.value
                and f.remediation_status == AuditFindingStatus.OPEN.value
            )

            if open_critical > 0:
                security_score = 45.0
                status = "CRITICAL"
            elif open_high > 0:
                security_score = 75.0
                status = "DEGRADED"
            else:
                security_score = round(
                    min(100.0, 95.0 + (remediated_count / total_findings) * 5.0), 2
                )
                status = "PASSED"

        # Compute SHA-256 integrity digest
        digest_input = json.dumps(
            [
                {
                    "finding_id": f.finding_id,
                    "severity": f.severity,
                    "category": f.category,
                    "status": f.remediation_status,
                }
                for f in all_findings
            ],
            sort_keys=True,
        )
        integrity_sha256 = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        summary = (
            f"Security audit completed across {len(categories_analyzed)} domains. "
            f"Total findings: {total_findings} ({remediated_count} remediated/verified, {open_count} open). "
            f"Overall Security Score: {security_score}% ({status})."
        )

        execution_dto = SecurityAuditExecutionDTO(
            audit_id=audit_id,
            organization_id=organization_id,
            executed_at=executed_at,
            total_findings=total_findings,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            open_findings_count=open_count,
            remediated_findings_count=remediated_count,
            overall_security_score=security_score,
            status=status,
            categories_analyzed=categories_analyzed,
            findings=all_findings,
            audit_integrity_sha256=integrity_sha256,
            summary=summary,
        )

        # Track history
        if organization_id not in self._audit_history:
            self._audit_history[organization_id] = []
        self._audit_history[organization_id].insert(0, execution_dto)

        if self.audit_logger:
            try:
                await self.audit_logger.record_event(
                    organization_id=organization_id,
                    action="security_audit.completed",
                    resource_type="security_audit",
                    resource_id=str(audit_id),
                    actor_user_id=actor_user_id,
                    details={
                        "score": security_score,
                        "status": status,
                        "total_findings": total_findings,
                        "sha256": integrity_sha256,
                    },
                )
            except Exception as e:
                logger.warning("security_audit_complete_audit_log_failed", error=str(e))

        logger.info(
            "security_audit_execution_completed",
            audit_id=str(audit_id),
            security_score=security_score,
            status=status,
        )

        return execution_dto

    async def get_audit_status(self, organization_id: UUID) -> SecurityAuditStatusDTO:
        """Fetch current security posture and vulnerability tracking metrics."""
        history = self._audit_history.get(organization_id, [])
        findings = self._findings_store.get(organization_id, [])

        if not history and not findings:
            # If never run, trigger baseline
            exec_result = await self.execute_security_audit(
                organization_id=organization_id
            )
            findings = exec_result.findings
            history = [exec_result]

        latest_audit = history[0] if history else None
        total_tracked = len(findings)
        critical_count = sum(
            1 for f in findings if f.severity == AuditSeverity.CRITICAL.value
        )
        high_count = sum(1 for f in findings if f.severity == AuditSeverity.HIGH.value)
        medium_count = sum(
            1 for f in findings if f.severity == AuditSeverity.MEDIUM.value
        )
        low_count = sum(1 for f in findings if f.severity == AuditSeverity.LOW.value)

        remediated_count = sum(
            1
            for f in findings
            if f.remediation_status
            in (
                AuditFindingStatus.REMEDIATED.value,
                AuditFindingStatus.ACCEPTED_RISK.value,
                AuditFindingStatus.FALSE_POSITIVE.value,
            )
        )

        remediation_rate = (
            round((remediated_count / total_tracked) * 100.0, 2)
            if total_tracked > 0
            else 100.0
        )

        if remediation_rate >= 95.0:
            grade = "A+"
        elif remediation_rate >= 85.0:
            grade = "A"
        elif remediation_rate >= 75.0:
            grade = "B"
        else:
            grade = "C"

        return SecurityAuditStatusDTO(
            status=latest_audit.status if latest_audit else "HEALTHY",
            last_audit_id=latest_audit.audit_id if latest_audit else None,
            last_audit_timestamp=latest_audit.executed_at if latest_audit else None,
            total_scans_executed=len(history),
            total_vulnerabilities_tracked=total_tracked,
            critical_findings=critical_count,
            high_findings=high_count,
            medium_findings=medium_count,
            low_findings=low_count,
            remediation_rate_percentage=remediation_rate,
            compliance_grade=grade,
        )

    async def list_findings(
        self,
        organization_id: UUID,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SecurityAuditFindingDTO], int]:
        """Fetch filtered and paginated security audit findings."""
        if organization_id not in self._findings_store:
            exec_result = await self.execute_security_audit(
                organization_id=organization_id
            )
            all_findings = exec_result.findings
        else:
            all_findings = self._findings_store[organization_id]

        filtered = all_findings

        if category:
            filtered = [f for f in filtered if f.category == category]
        if severity:
            filtered = [f for f in filtered if f.severity == severity]
        if status:
            filtered = [f for f in filtered if f.remediation_status == status]

        total = len(filtered)
        paginated = filtered[offset : offset + limit]
        return paginated, total

    async def remediate_finding(
        self,
        organization_id: UUID,
        finding_id: str,
        request: RemediateFindingRequestDTO,
        actor_user_id: Optional[UUID] = None,
    ) -> SecurityAuditFindingDTO:
        """Update remediation state for an audit finding."""
        if organization_id not in self._findings_store:
            await self.execute_security_audit(organization_id=organization_id)

        findings = self._findings_store.get(organization_id, [])
        target_finding: Optional[SecurityAuditFindingDTO] = None

        for f in findings:
            if f.finding_id == finding_id or str(f.id) == finding_id:
                f.remediation_status = request.status.value
                f.remediation_notes = request.remediation_notes
                f.remediated_by = request.remediated_by or (
                    str(actor_user_id) if actor_user_id else "Security Analyst"
                )
                f.remediated_at = datetime.now(timezone.utc)
                target_finding = f
                break

        if not target_finding:
            raise ValueError(f"Security audit finding {finding_id} not found.")

        if self.audit_logger:
            try:
                await self.audit_logger.record_event(
                    organization_id=organization_id,
                    action="security_audit.finding_remediated",
                    resource_type="security_audit_finding",
                    resource_id=str(target_finding.id),
                    actor_user_id=actor_user_id,
                    details={
                        "finding_id": target_finding.finding_id,
                        "status": target_finding.remediation_status,
                        "notes": request.remediation_notes,
                    },
                )
            except Exception as e:
                logger.warning(
                    "security_audit_remediation_audit_log_failed", error=str(e)
                )

        logger.info(
            "security_audit_finding_remediated",
            finding_id=target_finding.finding_id,
            status=target_finding.remediation_status,
            organization_id=str(organization_id),
        )

        return target_finding
