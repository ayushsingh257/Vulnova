"""Unit and Integration Test Suite for Executive Security Reporting Engine."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_user
from app.application.assessment.dto import (
    AttackSurfaceCoverageResponse,
    DashboardOverviewResponse,
    HistoricalRiskTrendResponse,
    SchedulesOverviewSummaryDTO,
    SecurityPostureSummaryDTO,
    VulnerabilitySeverityBreakdownDTO,
)
from app.application.reporting.dto import (
    CreateExecutiveReportRequest,
    ExecutiveReportDataPayload,
    ExecutiveReportMetadataResponse,
)
from app.application.reporting.html_renderer import HTMLRendererService
from app.application.reporting.pdf_generator import PDFGeneratorService
from app.application.reporting.report_service import ExecutiveSecurityReportService
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_admin_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "ciso@enterprise.com"
    user.full_name = "CISO User"
    user.role = "ADMIN"
    user.is_active = True
    return user


@pytest.mark.anyio
async def test_executive_report_service_payload_generation(mock_admin_user: UserModel) -> None:
    """Test ExecutiveSecurityReportService.generate_executive_report_payload."""
    mock_session = AsyncMock()

    mock_dashboard = AsyncMock()
    mock_dashboard.get_dashboard_overview.return_value = DashboardOverviewResponse(
        organization_id=str(mock_admin_user.organization_id),
        posture_summary=SecurityPostureSummaryDTO(
            composite_risk_score=24.5,
            posture_status="SECURE",
            total_targets_count=10,
            total_open_findings=12,
            critical_findings_count=1,
            high_findings_count=3,
        ),
        vulnerability_breakdown=VulnerabilitySeverityBreakdownDTO(
            critical_count=1, high_count=3, medium_count=4, low_count=4
        ),
        active_scans=[],
        top_vulnerable_assets=[],
        schedules_summary=SchedulesOverviewSummaryDTO(total_active_schedules=1),
        cached_at="2026-08-05T00:00:00Z",
    )

    mock_executive_analytics = AsyncMock()
    mock_executive_analytics.get_historical_risk_trends.return_value = HistoricalRiskTrendResponse(
        organization_id=str(mock_admin_user.organization_id),
        timeframe_days=30,
        current_risk_score=24.5,
        baseline_risk_score=30.0,
        risk_velocity="IMPROVING",
        mean_time_to_remediate_hours=18.5,
        trend_points=[],
        cached_at="2026-08-05T00:00:00Z",
    )
    mock_executive_analytics.get_attack_surface_coverage.return_value = AttackSurfaceCoverageResponse(
        organization_id=str(mock_admin_user.organization_id),
        total_targets_count=10,
        assessed_targets_count=9,
        unassessed_targets_count=1,
        coverage_percentage=90.0,
        environments_breakdown=[],
    )

    mock_threat_advisories = AsyncMock()
    mock_threat_advisories.evaluate_organization_advisories.return_value = []

    html_renderer = HTMLRendererService()
    pdf_generator = PDFGeneratorService()
    mock_audit = AsyncMock()

    service = ExecutiveSecurityReportService(
        session=mock_session,
        dashboard_service=mock_dashboard,
        executive_analytics_service=mock_executive_analytics,
        threat_advisory_service=mock_threat_advisories,
        html_renderer=html_renderer,
        pdf_generator=pdf_generator,
        audit_log_service=mock_audit,
    )

    req = CreateExecutiveReportRequest(
        title="Q3 Enterprise Security Posture Report", timeframe_days=30
    )
    payload = await service.generate_executive_report_payload(mock_admin_user, req)

    assert payload.metadata.organization_id == str(mock_admin_user.organization_id)
    assert payload.metadata.title == "Q3 Enterprise Security Posture Report"
    assert payload.historical_trends.timeframe_days == 30
    assert payload.metadata.available_formats == ["pdf", "html", "json", "csv"]
    assert len(payload.data_sources) >= 3


@pytest.mark.anyio
async def test_html_report_rendering_service(mock_admin_user: UserModel) -> None:
    """Test HTML rendering engine output formatting."""
    mock_session = AsyncMock()

    mock_dashboard = AsyncMock()
    mock_dashboard.get_dashboard_overview.return_value = DashboardOverviewResponse(
        organization_id=str(mock_admin_user.organization_id),
        posture_summary=SecurityPostureSummaryDTO(
            composite_risk_score=24.5,
            posture_status="SECURE",
            total_targets_count=10,
            total_open_findings=12,
            critical_findings_count=1,
            high_findings_count=3,
        ),
        vulnerability_breakdown=VulnerabilitySeverityBreakdownDTO(),
        active_scans=[],
        top_vulnerable_assets=[],
        schedules_summary=SchedulesOverviewSummaryDTO(total_active_schedules=1),
        cached_at="2026-08-05T00:00:00Z",
    )

    mock_executive_analytics = AsyncMock()
    mock_executive_analytics.get_historical_risk_trends.return_value = HistoricalRiskTrendResponse(
        organization_id=str(mock_admin_user.organization_id),
        timeframe_days=30,
        current_risk_score=24.5,
        baseline_risk_score=30.0,
        risk_velocity="IMPROVING",
        mean_time_to_remediate_hours=18.5,
        trend_points=[],
        cached_at="2026-08-05T00:00:00Z",
    )
    mock_executive_analytics.get_attack_surface_coverage.return_value = AttackSurfaceCoverageResponse(
        organization_id=str(mock_admin_user.organization_id),
        total_targets_count=10,
        assessed_targets_count=9,
        unassessed_targets_count=1,
        coverage_percentage=90.0,
        environments_breakdown=[],
    )

    mock_threat_advisories = AsyncMock()
    mock_threat_advisories.evaluate_organization_advisories.return_value = []

    html_renderer = HTMLRendererService()
    pdf_generator = PDFGeneratorService()
    mock_audit = AsyncMock()

    service = ExecutiveSecurityReportService(
        session=mock_session,
        dashboard_service=mock_dashboard,
        executive_analytics_service=mock_executive_analytics,
        threat_advisory_service=mock_threat_advisories,
        html_renderer=html_renderer,
        pdf_generator=pdf_generator,
        audit_log_service=mock_audit,
    )

    html_output = await service.generate_html_report(mock_admin_user)

    assert "<!DOCTYPE html>" in html_output
    assert "VULNOVA" in html_output
    assert "Executive Security Metrics Summary" in html_output
    assert str(mock_admin_user.organization_id) in html_output


@pytest.mark.anyio
async def test_pdf_report_compilation_service(mock_admin_user: UserModel) -> None:
    """Test PDF generation engine output binary buffer."""
    mock_session = AsyncMock()

    mock_dashboard = AsyncMock()
    mock_dashboard.get_dashboard_overview.return_value = DashboardOverviewResponse(
        organization_id=str(mock_admin_user.organization_id),
        posture_summary=SecurityPostureSummaryDTO(
            composite_risk_score=24.5,
            posture_status="SECURE",
            total_targets_count=10,
            total_open_findings=12,
            critical_findings_count=1,
            high_findings_count=3,
        ),
        vulnerability_breakdown=VulnerabilitySeverityBreakdownDTO(),
        active_scans=[],
        top_vulnerable_assets=[],
        schedules_summary=SchedulesOverviewSummaryDTO(total_active_schedules=1),
        cached_at="2026-08-05T00:00:00Z",
    )

    mock_executive_analytics = AsyncMock()
    mock_executive_analytics.get_historical_risk_trends.return_value = HistoricalRiskTrendResponse(
        organization_id=str(mock_admin_user.organization_id),
        timeframe_days=30,
        current_risk_score=24.5,
        baseline_risk_score=30.0,
        risk_velocity="IMPROVING",
        mean_time_to_remediate_hours=18.5,
        trend_points=[],
        cached_at="2026-08-05T00:00:00Z",
    )
    mock_executive_analytics.get_attack_surface_coverage.return_value = AttackSurfaceCoverageResponse(
        organization_id=str(mock_admin_user.organization_id),
        total_targets_count=10,
        assessed_targets_count=9,
        unassessed_targets_count=1,
        coverage_percentage=90.0,
        environments_breakdown=[],
    )

    mock_threat_advisories = AsyncMock()
    mock_threat_advisories.evaluate_organization_advisories.return_value = []

    html_renderer = HTMLRendererService()
    pdf_generator = PDFGeneratorService()
    mock_audit = AsyncMock()

    service = ExecutiveSecurityReportService(
        session=mock_session,
        dashboard_service=mock_dashboard,
        executive_analytics_service=mock_executive_analytics,
        threat_advisory_service=mock_threat_advisories,
        html_renderer=html_renderer,
        pdf_generator=pdf_generator,
        audit_log_service=mock_audit,
    )

    pdf_bytes = await service.generate_pdf_report(mock_admin_user)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 50
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.anyio
async def test_reports_rest_api_endpoints(mock_admin_user: UserModel) -> None:
    """Test /api/v1/reports REST endpoints integration."""
    from app.api.v1.routers.reports import get_reporting_service

    async def _override_get_current_user() -> UserModel:
        return mock_admin_user

    mock_reporting_service = AsyncMock()

    mock_report_id = str(uuid4())
    now_str = "2026-08-05T00:00:00Z"

    mock_metadata = ExecutiveReportMetadataResponse(
        id=mock_report_id,
        organization_id=str(mock_admin_user.organization_id),
        title="Quarterly CISO Assessment",
        generated_at=now_str,
        posture_score=24.5,
        posture_status="SECURE",
        total_findings=12,
        critical_findings=1,
        high_findings=3,
        available_formats=["pdf", "html", "json", "csv"],
    )

    mock_payload = ExecutiveReportDataPayload(
        metadata=mock_metadata,
        posture_summary=SecurityPostureSummaryDTO(
            composite_risk_score=24.5,
            posture_status="SECURE",
            total_targets_count=10,
            total_open_findings=12,
            critical_findings_count=1,
            high_findings_count=3,
        ),
        historical_trends=HistoricalRiskTrendResponse(
            organization_id=str(mock_admin_user.organization_id),
            timeframe_days=30,
            current_risk_score=24.5,
            baseline_risk_score=30.0,
            risk_velocity="IMPROVING",
            mean_time_to_remediate_hours=18.5,
            trend_points=[],
            cached_at=now_str,
        ),
        attack_surface_coverage=AttackSurfaceCoverageResponse(
            organization_id=str(mock_admin_user.organization_id),
            total_targets_count=10,
            assessed_targets_count=9,
            unassessed_targets_count=1,
            coverage_percentage=90.0,
            environments_breakdown=[],
        ),
        vulnerability_breakdown=VulnerabilitySeverityBreakdownDTO(),
        top_findings=[],
        threat_advisories=[],
    )

    mock_reporting_service.generate_executive_report_payload.return_value = mock_payload
    mock_reporting_service.generate_html_report.return_value = "<!DOCTYPE html><html><body>VULNOVA</body></html>"
    mock_reporting_service.generate_pdf_report.return_value = b"%PDF-1.4 Mock PDF Content"
    mock_reporting_service.get_report_metadata.return_value = mock_metadata

    async def _override_get_reporting_service() -> MagicMock:
        return mock_reporting_service

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = _override_get_current_user
    app.dependency_overrides[get_reporting_service] = _override_get_reporting_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # 1. POST /api/v1/reports/executive
            post_res = await client.post(
                "/api/v1/reports/executive",
                json={
                    "title": "Quarterly CISO Assessment",
                    "timeframe_days": 30,
                },
            )
            assert post_res.status_code == 200
            data = post_res.json()
            assert data["metadata"]["title"] == "Quarterly CISO Assessment"
            report_id = data["metadata"]["id"]

            # 2. GET /api/v1/reports/{id}
            meta_res = await client.get(f"/api/v1/reports/{report_id}")
            assert meta_res.status_code == 200
            assert meta_res.json()["organization_id"] == str(mock_admin_user.organization_id)

            # 3. GET /api/v1/reports/{id}/html
            html_res = await client.get(f"/api/v1/reports/{report_id}/html")
            assert html_res.status_code == 200
            assert "text/html" in html_res.headers["content-type"]
            assert "VULNOVA" in html_res.text

            # 4. GET /api/v1/reports/{id}/pdf
            pdf_res = await client.get(f"/api/v1/reports/{report_id}/pdf")
            assert pdf_res.status_code == 200
            assert "application/pdf" in pdf_res.headers["content-type"]
            assert pdf_res.content.startswith(b"%PDF")

    finally:
        app.dependency_overrides.clear()

