"""Compliance Mapping Application Service orchestrating compliance evaluations and audit logging."""

from typing import Any, Dict, List
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.compliance.dto import (
    ComplianceControlDTO,
    ComplianceOverviewResponse,
)
from app.application.compliance.framework_mapper import FrameworkMapper
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)


class ComplianceMappingService:
    """Service providing compliance framework evaluations, posture scores, and audit tracking."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def _fetch_tenant_findings(
        self, organization_id: UUID, batch_size: int = 100
    ) -> List[SecurityFindingModel]:
        """Fetch all non-duplicate findings for the organization using batch cursors."""
        offset = 0
        all_findings: List[SecurityFindingModel] = []
        while True:
            stmt = (
                select(SecurityFindingModel)
                .where(
                    SecurityFindingModel.organization_id == organization_id,
                    SecurityFindingModel.is_duplicate.is_(False),
                )
                .order_by(SecurityFindingModel.created_at.desc())
                .offset(offset)
                .limit(batch_size)
            )
            res = await self.session.execute(stmt)
            findings = list(res.scalars().all())
            if not findings:
                break
            all_findings.extend(findings)
            if len(findings) < batch_size:
                break
            offset += batch_size
        return all_findings

    async def get_compliance_overview(
        self, user: UserModel, framework_id: str
    ) -> ComplianceOverviewResponse:
        """Evaluate compliance posture for a framework and dispatch audit event."""
        findings = await self._fetch_tenant_findings(user.organization_id)
        framework_dto, control_dtos, score_dto = FrameworkMapper.evaluate_framework(
            framework_id=framework_id, findings=findings
        )

        failed_controls = [c for c in control_dtos if c.status == "FAIL"]

        # Build top remediation priorities from failed controls
        priorities = []
        for ctrl in failed_controls[:5]:
            priorities.append(
                {
                    "control_id": ctrl.control_id,
                    "title": ctrl.title,
                    "affected_findings_count": ctrl.mapped_findings_count,
                    "remediation_guidance": ctrl.remediation_guidance,
                }
            )

        # Dispatch audit event
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="compliance.viewed",
            resource_type="compliance_framework",
            resource_id=framework_id,
            actor_user_id=user.id,
            details={
                "framework_id": framework_id,
                "framework_version": framework_dto.version,
                "compliance_percentage": score_dto.compliance_percentage,
                "failed_controls_count": score_dto.failed_controls,
            },
        )

        return ComplianceOverviewResponse(
            framework_id=framework_dto.id,
            framework_name=framework_dto.name,
            framework_version=framework_dto.version,
            score=score_dto,
            controls=control_dtos,
            failed_controls=failed_controls,
            top_remediation_priorities=priorities,
        )

    async def get_compliance_controls(
        self, user: UserModel, framework_id: str
    ) -> List[ComplianceControlDTO]:
        """Fetch evaluated compliance controls with findings evidence."""
        findings = await self._fetch_tenant_findings(user.organization_id)
        _, control_dtos, _ = FrameworkMapper.evaluate_framework(
            framework_id=framework_id, findings=findings
        )
        return control_dtos

    async def export_compliance_report(
        self, user: UserModel, framework_id: str
    ) -> Dict[str, Any]:
        """Generate dynamic compliance report payload and record audit event."""
        overview = await self.get_compliance_overview(user, framework_id)

        # Record export audit event
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="compliance.exported",
            resource_type="compliance_report",
            resource_id=framework_id,
            actor_user_id=user.id,
            details={
                "framework_id": framework_id,
                "framework_version": overview.framework_version,
                "compliance_percentage": overview.score.compliance_percentage,
            },
        )

        return {
            "title": f"Vulnova Compliance Report - {overview.framework_name} ({overview.framework_version})",
            "organization_id": str(user.organization_id),
            "generated_by": user.full_name or user.email,
            "overview": overview.model_dump(),
        }
