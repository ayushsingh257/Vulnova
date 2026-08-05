"""Application Service for Executive Security Report Generation and Exporting."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from app.application.assessment.executive_analytics_service import (
    ExecutiveAnalyticsService,
)
from app.application.assessment.threat_advisory_service import ThreatAdvisoryService
from app.application.audit_logs.services import AuditLogService
from app.application.reporting.dto import (
    CreateExecutiveReportRequest,
    ExecutiveReportDataPayload,
    ExecutiveReportMetadataResponse,
    TopVulnerabilityReportDTO,
)
from app.application.reporting.html_renderer import HTMLRendererService
from app.application.reporting.pdf_generator import PDFGeneratorService
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)


class ExecutiveSecurityReportService:
    """Service compiling CISO executive security posture report payloads, HTML rendering, and PDF exports."""

    def __init__(
        self,
        session: AsyncSession,
        dashboard_service: DashboardAnalyticsService,
        executive_analytics_service: ExecutiveAnalyticsService,
        threat_advisory_service: ThreatAdvisoryService,
        html_renderer: HTMLRendererService,
        pdf_generator: PDFGeneratorService,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.dashboard_service = dashboard_service
        self.executive_analytics_service = executive_analytics_service
        self.threat_advisory_service = threat_advisory_service
        self.html_renderer = html_renderer
        self.pdf_generator = pdf_generator
        self.audit_log_service = audit_log_service

    async def _fetch_top_findings(
        self, organization_id: UUID, limit: int = 5
    ) -> List[TopVulnerabilityReportDTO]:
        """Fetch top open critical and high severity findings for report presentation."""
        stmt = (
            select(SecurityFindingModel)
            .where(
                SecurityFindingModel.organization_id == organization_id,
                SecurityFindingModel.is_duplicate.is_(False),
            )
            .order_by(SecurityFindingModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        findings = []
        if hasattr(result, "scalars"):
            scalars_res = result.scalars()
            if hasattr(scalars_res, "all"):
                findings = list(scalars_res.all())

        top_dtos: List[TopVulnerabilityReportDTO] = []
        for f in findings:
            epss_val = 0.0
            if f.epss_json and isinstance(f.epss_json, dict):
                epss_val = float(f.epss_json.get("epss_score", 0.0))

            target = None
            if hasattr(f, "assessment_job") and f.assessment_job is not None:
                target = getattr(f.assessment_job, "target_url", None)

            top_dtos.append(
                TopVulnerabilityReportDTO(
                    id=str(f.id),
                    title=f.title,
                    severity=str(f.severity),
                    category=str(f.category),
                    cve_id=f.cve_id,
                    cwe_id=f.cwe_id,
                    cvss_score=float(f.risk_score or 0.0),
                    epss_score=epss_val,
                    target_name=target,
                    created_at=(
                        f.created_at.isoformat()
                        if f.created_at
                        else datetime.now(timezone.utc).isoformat()
                    ),
                )
            )
        return top_dtos

    async def generate_executive_report_payload(
        self,
        current_user: UserModel,
        req: Optional[CreateExecutiveReportRequest] = None,
    ) -> ExecutiveReportDataPayload:
        """Assemble complete executive security report payload and record audit event."""
        if req is None:
            req = CreateExecutiveReportRequest()

        report_id = str(uuid4())
        now_str = datetime.now(timezone.utc).isoformat()
        org_id = current_user.organization_id

        # 1. Fetch dashboard overview, historical trends, attack surface, advisories
        overview = await self.dashboard_service.get_dashboard_overview(current_user)
        trends = await self.executive_analytics_service.get_historical_risk_trends(
            current_user, timeframe_days=req.timeframe_days
        )
        coverage = await self.executive_analytics_service.get_attack_surface_coverage(
            current_user
        )
        advisories = (
            await self.threat_advisory_service.evaluate_organization_advisories(
                current_user
            )
        )
        top_findings = await self._fetch_top_findings(org_id)

        # 2. Build Report Metadata
        metadata = ExecutiveReportMetadataResponse(
            id=report_id,
            organization_id=str(org_id),
            title=req.title or "CISO Executive Security Posture Report",
            generated_at=now_str,
            posture_score=overview.posture_summary.composite_risk_score,
            posture_status=overview.posture_summary.posture_status,
            total_findings=overview.posture_summary.total_open_findings,
            critical_findings=overview.posture_summary.critical_findings_count,
            high_findings=overview.posture_summary.high_findings_count,
            available_formats=["pdf", "html", "json", "csv"],
        )

        payload = ExecutiveReportDataPayload(
            metadata=metadata,
            posture_summary=overview.posture_summary,
            historical_trends=trends,
            attack_surface_coverage=coverage,
            vulnerability_breakdown=overview.vulnerability_breakdown,
            top_findings=top_findings,
            threat_advisories=advisories,
        )

        # 3. Record Audit Log Event (report.generated)
        await self.audit_log_service.record_event(
            actor_user_id=current_user.id,
            organization_id=org_id,
            action="report.generated",
            resource_type="report",
            resource_id=report_id,
            details={
                "title": metadata.title,
                "timeframe_days": req.timeframe_days,
                "posture_score": metadata.posture_score,
                "total_findings": metadata.total_findings,
            },
        )

        return payload

    async def generate_html_report(
        self,
        current_user: UserModel,
        req: Optional[CreateExecutiveReportRequest] = None,
    ) -> str:
        """Generate styled HTML executive report string."""
        payload = await self.generate_executive_report_payload(current_user, req)
        return self.html_renderer.render_html_report(payload)

    async def generate_pdf_report(
        self,
        current_user: UserModel,
        req: Optional[CreateExecutiveReportRequest] = None,
    ) -> bytes:
        """Generate PDF binary stream for executive report and record audit event."""
        payload = await self.generate_executive_report_payload(current_user, req)
        html_str = self.html_renderer.render_html_report(payload)
        pdf_bytes = self.pdf_generator.generate_pdf_from_html(html_str)

        await self.audit_log_service.record_event(
            actor_user_id=current_user.id,
            organization_id=current_user.organization_id,
            action="report.downloaded",
            resource_type="report",
            resource_id=payload.metadata.id,
            details={
                "format": "pdf",
                "title": payload.metadata.title,
                "bytes_size": len(pdf_bytes),
            },
        )
        return pdf_bytes

    async def get_report_metadata(
        self, current_user: UserModel, report_id: str
    ) -> ExecutiveReportMetadataResponse:
        """Retrieve metadata description for a report instance."""
        overview = await self.dashboard_service.get_dashboard_overview(current_user)
        now_str = datetime.now(timezone.utc).isoformat()
        return ExecutiveReportMetadataResponse(
            id=report_id,
            organization_id=str(current_user.organization_id),
            title="CISO Executive Security Posture Report",
            generated_at=now_str,
            posture_score=overview.posture_summary.composite_risk_score,
            posture_status=overview.posture_summary.posture_status,
            total_findings=overview.posture_summary.total_open_findings,
            critical_findings=overview.posture_summary.critical_findings_count,
            high_findings=overview.posture_summary.high_findings_count,
            available_formats=["pdf", "html", "json", "csv"],
        )
