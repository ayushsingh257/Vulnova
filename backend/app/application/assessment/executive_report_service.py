"""Application Service for Executive Security Report Generation and Exporting."""

import csv
import io
from datetime import datetime, timezone
from typing import Tuple

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from app.application.assessment.dto import ExecutiveSummaryReportResponse
from app.application.assessment.executive_analytics_service import (
    ExecutiveAnalyticsService,
)
from app.application.assessment.threat_advisory_service import ThreatAdvisoryService
from app.infrastructure.database.models.user import UserModel

logger = structlog.get_logger(__name__)


class ExecutiveReportService:
    """Service compiling executive security posture report payloads and handling JSON/CSV exports."""

    def __init__(
        self,
        session: AsyncSession,
        dashboard_service: DashboardAnalyticsService,
        executive_analytics_service: ExecutiveAnalyticsService,
        threat_advisory_service: ThreatAdvisoryService,
    ) -> None:
        self.session = session
        self.dashboard_service = dashboard_service
        self.executive_analytics_service = executive_analytics_service
        self.threat_advisory_service = threat_advisory_service

    async def generate_executive_summary_report(
        self, current_user: UserModel
    ) -> ExecutiveSummaryReportResponse:
        """Assemble complete executive security posture report payload."""
        now_str = datetime.now(timezone.utc).isoformat()
        overview = await self.dashboard_service.get_dashboard_overview(current_user)
        trends = await self.executive_analytics_service.get_historical_risk_trends(
            current_user, timeframe_days=30
        )
        coverage = await self.executive_analytics_service.get_attack_surface_coverage(
            current_user
        )
        advisories = (
            await self.threat_advisory_service.evaluate_organization_advisories(
                current_user
            )
        )

        return ExecutiveSummaryReportResponse(
            organization_id=str(current_user.organization_id),
            generated_at=now_str,
            posture_summary=overview.posture_summary,
            historical_trends=trends,
            attack_surface_coverage=coverage,
            vulnerability_breakdown=overview.vulnerability_breakdown,
            threat_advisories=advisories,
        )

    async def export_report(
        self, current_user: UserModel, format_type: str = "json"
    ) -> Tuple[str, str]:
        """Export executive summary report in JSON or CSV format.

        Returns:
            Tuple of (report_content_string, media_type)
        """
        report = await self.generate_executive_summary_report(current_user)

        if format_type.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Organization ID", report.organization_id])
            writer.writerow(["Generated At", report.generated_at])
            writer.writerow(
                ["Composite Risk Score", report.posture_summary.composite_risk_score]
            )
            writer.writerow(["Posture Status", report.posture_summary.posture_status])
            writer.writerow(
                ["Total Target Assets", report.posture_summary.total_targets_count]
            )
            writer.writerow(
                ["Total Open Findings", report.posture_summary.total_open_findings]
            )
            writer.writerow(
                ["Critical Findings", report.posture_summary.critical_findings_count]
            )
            writer.writerow(
                ["High Findings", report.posture_summary.high_findings_count]
            )
            writer.writerow(["Risk Velocity", report.historical_trends.risk_velocity])
            writer.writerow(
                ["MTTR (Hours)", report.historical_trends.mean_time_to_remediate_hours]
            )
            writer.writerow(
                [
                    "Coverage Percentage",
                    f"{report.attack_surface_coverage.coverage_percentage}%",
                ]
            )
            return output.getvalue(), "text/csv; charset=utf-8"

        # Default JSON format
        return report.model_dump_json(indent=2), "application/json; charset=utf-8"
