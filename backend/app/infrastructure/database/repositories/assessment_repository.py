"""Repository for persisting and querying Assessment Jobs and Security Findings."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities.assessment import Finding
from app.infrastructure.database.models.assessment import (
    AssessmentJobModel,
    SecurityFindingModel,
)

logger = get_logger("vulnova.assessment_repository")


class AssessmentRepository:
    """Async repository managing tenant-isolated assessment jobs and security findings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(
        self,
        organization_id: UUID,
        target_url: str,
        enabled_plugins: Optional[List[str]] = None,
    ) -> AssessmentJobModel:
        """Create a new assessment job record."""
        job = AssessmentJobModel(
            organization_id=organization_id,
            target_url=target_url,
            status="PENDING",
            enabled_plugins_json={"plugins": enabled_plugins or []},
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_job_status(
        self,
        organization_id: UUID,
        job_id: UUID,
        status: str,
        duration_seconds: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[AssessmentJobModel]:
        """Update an assessment job's status and execution metadata."""
        job = await self.get_job_by_id(organization_id, job_id)
        if not job:
            return None

        job.status = status
        if duration_seconds is not None:
            job.duration_seconds = duration_seconds
        if error_message is not None:
            job.error_message = error_message

        await self.session.flush()
        return job

    async def create_finding(
        self, organization_id: UUID, finding: Finding
    ) -> SecurityFindingModel:
        """Persist a security finding for a target tenant."""
        cvss_data = (
            {
                "version": finding.cvss.version,
                "base_score": finding.cvss.base_score,
                "vector_string": finding.cvss.vector_string,
            }
            if finding.cvss
            else None
        )
        epss_data = (
            {
                "epss_score": finding.epss.epss_score,
                "percentile": finding.epss.percentile,
            }
            if finding.epss
            else None
        )
        risk_val = finding.risk.composite_risk_score if finding.risk else None

        finding_model = SecurityFindingModel(
            id=finding.id,
            organization_id=organization_id,
            assessment_job_id=finding.assessment_job_id,
            asset_node_id=finding.asset_node_id,
            plugin_id=finding.plugin_id,
            title=finding.title,
            description=finding.description,
            severity=finding.severity.value,
            category=finding.category.value,
            cve_id=finding.cve_id,
            cwe_id=finding.cwe_id,
            remediation=finding.remediation,
            evidence_json=finding.evidence,
            cvss_json=cvss_data,
            epss_json=epss_data,
            risk_score=risk_val,
            confidence=finding.confidence.value if finding.confidence else "HIGH",
            is_duplicate=finding.is_duplicate,
            canonical_finding_id=finding.canonical_finding_id,
            deduplication_hash=finding.deduplication_hash,
        )
        self.session.add(finding_model)
        await self.session.flush()
        return finding_model

    async def get_job_by_id(
        self, organization_id: UUID, job_id: UUID
    ) -> Optional[AssessmentJobModel]:
        """Fetch an assessment job ensuring multi-tenant isolation."""
        stmt = select(AssessmentJobModel).where(
            AssessmentJobModel.id == job_id,
            AssessmentJobModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(self, organization_id: UUID) -> List[AssessmentJobModel]:
        """List all assessment jobs for an organization."""
        stmt = (
            select(AssessmentJobModel)
            .where(AssessmentJobModel.organization_id == organization_id)
            .order_by(AssessmentJobModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_findings(
        self,
        organization_id: UUID,
        severity: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[SecurityFindingModel]:
        """List security findings for an organization with optional severity and category filters."""
        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.organization_id == organization_id
        )
        if severity:
            stmt = stmt.where(SecurityFindingModel.severity == severity.upper())
        if category:
            stmt = stmt.where(SecurityFindingModel.category == category.upper())

        stmt = stmt.order_by(SecurityFindingModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
