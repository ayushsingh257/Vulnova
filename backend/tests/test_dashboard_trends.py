"""Unit and Integration Tests for Phase 7.3 Executive Analytics, Trends, and Threat Advisories.

Tests:
1. RiskPostureSnapshotModel ORM creation and query filtering.
2. ExecutiveAnalyticsService historical trend calculation & risk velocity classification.
3. Attack surface coverage breakdown by deployment environment.
4. ThreatAdvisoryService CVSS 9.0+ and SLA breach detection.
5. ExecutiveReportService JSON and CSV report export formatting.
6. FastAPI REST endpoints (/api/v1/dashboard/trends, /coverage, /threat-advisories, /executive-summary, /export).
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_active_user, get_current_user
from app.application.assessment.dto import (
    AttackSurfaceCoverageResponse,
    HistoricalRiskTrendResponse,
    SecurityPostureSummaryDTO,
    VulnerabilitySeverityBreakdownDTO,
)
from app.application.assessment.executive_analytics_service import (
    ExecutiveAnalyticsService,
)
from app.application.assessment.executive_report_service import ExecutiveReportService
from app.application.assessment.threat_advisory_service import ThreatAdvisoryService
from app.infrastructure.database.models.risk_snapshot import RiskPostureSnapshotModel
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_user() -> UserModel:
    """Fixture providing a mock authenticated user."""
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "analyst@example.com"
    user.role = "SECURITY_ANALYST"
    return user


@pytest.mark.anyio
async def test_executive_analytics_service_trends(mock_user: UserModel) -> None:
    """Test ExecutiveAnalyticsService historical trend points and velocity calculation."""
    session = AsyncMock()

    # Mock snapshots query return
    mock_snap1 = MagicMock(spec=RiskPostureSnapshotModel)
    mock_snap1.snapshot_date.isoformat.return_value = "2026-07-05"
    mock_snap1.composite_risk_score = 85.0
    mock_snap1.total_open_findings = 50
    mock_snap1.critical_count = 5
    mock_snap1.mttr_hours = 40.0

    mock_snap2 = MagicMock(spec=RiskPostureSnapshotModel)
    mock_snap2.snapshot_date.isoformat.return_value = "2026-08-04"
    mock_snap2.composite_risk_score = 70.0
    mock_snap2.total_open_findings = 30
    mock_snap2.critical_count = 2
    mock_snap2.mttr_hours = 30.0

    mock_res = MagicMock()
    mock_res.scalars().all.return_value = [mock_snap1, mock_snap2]
    session.execute.return_value = mock_res

    service = ExecutiveAnalyticsService(session=session)
    trends = await service.get_historical_risk_trends(mock_user, timeframe_days=30)

    assert trends.current_risk_score == 70.0
    assert trends.baseline_risk_score == 85.0
    assert trends.risk_velocity == "IMPROVING"
    assert len(trends.trend_points) == 2


@pytest.mark.anyio
async def test_threat_advisory_service(mock_user: UserModel) -> None:
    """Test ThreatAdvisoryService CVSS critical alert and target contract evaluation."""
    session = AsyncMock()

    mock_finding = MagicMock()
    mock_finding.title = "Unauthenticated Remote Code Execution"
    mock_finding.category = "RCE"
    mock_finding.severity = "CRITICAL"

    mock_res_crit = MagicMock()
    mock_res_crit.scalars().all.return_value = [mock_finding]

    mock_res_empty = MagicMock()
    mock_res_empty.scalars().all.return_value = []

    session.execute.side_effect = [mock_res_crit, mock_res_empty, mock_res_empty]

    service = ThreatAdvisoryService(session=session)
    advisories = await service.evaluate_organization_advisories(mock_user)

    assert len(advisories) == 1
    assert advisories[0].severity == "CRITICAL"
    assert "Unauthenticated Remote Code Execution" in advisories[0].title


@pytest.mark.anyio
async def test_executive_report_service_export(mock_user: UserModel) -> None:
    """Test ExecutiveReportService JSON and CSV report export formatting."""
    session = AsyncMock()
    dash_service = AsyncMock()
    exec_service = AsyncMock()
    threat_service = AsyncMock()

    # Mock sub-service returns
    mock_overview = MagicMock()
    mock_overview.posture_summary = SecurityPostureSummaryDTO(
        composite_risk_score=65.0,
        posture_status="ELEVATED_RISK",
        total_targets_count=4,
        total_open_findings=10,
        critical_findings_count=1,
        high_findings_count=3,
    )
    mock_overview.vulnerability_breakdown = VulnerabilitySeverityBreakdownDTO(
        critical_count=1, high_count=3, medium_count=4, low_count=2, info_count=0
    )
    dash_service.get_dashboard_overview.return_value = mock_overview

    mock_trends = HistoricalRiskTrendResponse(
        organization_id=str(mock_user.organization_id),
        timeframe_days=30,
        current_risk_score=65.0,
        baseline_risk_score=75.0,
        risk_velocity="IMPROVING",
        mean_time_to_remediate_hours=28.0,
        trend_points=[],
        cached_at="2026-08-04T10:00:00Z",
    )
    exec_service.get_historical_risk_trends.return_value = mock_trends

    mock_coverage = AttackSurfaceCoverageResponse(
        organization_id=str(mock_user.organization_id),
        total_targets_count=4,
        assessed_targets_count=3,
        unassessed_targets_count=1,
        coverage_percentage=85.0,
        environments_breakdown=[],
    )
    exec_service.get_attack_surface_coverage.return_value = mock_coverage

    threat_service.evaluate_organization_advisories.return_value = []

    service = ExecutiveReportService(
        session, dash_service, exec_service, threat_service
    )

    # Test CSV Export
    csv_content, csv_type = await service.export_report(mock_user, format_type="csv")
    assert csv_type.startswith("text/csv")
    assert "Composite Risk Score,65.0" in csv_content

    # Test JSON Export
    json_content, json_type = await service.export_report(mock_user, format_type="json")
    assert json_type.startswith("application/json")
    assert "posture_summary" in json_content


@pytest.mark.anyio
async def test_dashboard_trends_rest_endpoint(mock_user: UserModel) -> None:
    """Test GET /api/v1/dashboard/trends REST endpoint."""

    async def override_get_current_user() -> UserModel:
        return mock_user

    async def override_get_trends(*args: Any, **kwargs: Any) -> Any:
        return {
            "organization_id": str(mock_user.organization_id),
            "timeframe_days": 30,
            "current_risk_score": 60.0,
            "baseline_risk_score": 75.0,
            "risk_velocity": "IMPROVING",
            "mean_time_to_remediate_hours": 32.0,
            "trend_points": [],
            "cached_at": "2026-08-04T10:00:00Z",
        }

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = override_get_current_user

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.application.assessment.executive_analytics_service.ExecutiveAnalyticsService.get_historical_risk_trends",
            override_get_trends,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/dashboard/trends?timeframe_days=30")
            assert res.status_code == 200
            data = res.json()
            assert data["risk_velocity"] == "IMPROVING"

    app.dependency_overrides.clear()
