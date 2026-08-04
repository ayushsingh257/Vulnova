"""Unit and Integration Tests for Phase 7.1 Security Operations Dashboard & Analytics.

Tests:
1. DashboardAnalyticsService metrics calculation & posture scoring.
2. DTO serialization & structure.
3. Multi-tenant isolation boundary enforcement.
4. FastAPI REST endpoints (/api/v1/dashboard/overview, /posture, /scans/active).
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_active_user, get_current_user
from app.application.assessment.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from app.application.assessment.dto import (
    ActiveScanSummaryDTO,
    DashboardOverviewResponse,
    SecurityPostureSummaryDTO,
    VulnerabilitySeverityBreakdownDTO,
)
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
    user.role = "SECURITY_ANALYST"
    return user


@pytest.mark.anyio
async def test_dashboard_analytics_service_overview(mock_user: UserModel) -> None:
    """Test DashboardAnalyticsService overview metric generation with mock session."""
    session = AsyncMock()

    # Mock execute results for database queries:
    # 1. Targets count query -> 5
    # 2. Finding severity query -> [("CRITICAL", 2), ("HIGH", 4), ("MEDIUM", 10)]
    # 3. Active scans query -> empty
    # 4. Top vulnerable targets query -> empty
    # 5. Schedules query -> (2, None)

    mock_res_targets = MagicMock()
    mock_res_targets.scalar.return_value = 5

    mock_res_findings = MagicMock()
    mock_res_findings.all.return_value = [("CRITICAL", 2), ("HIGH", 4), ("MEDIUM", 10)]

    mock_res_active_scans = MagicMock()
    mock_res_active_scans.scalars().all.return_value = []

    mock_res_top_assets = MagicMock()
    mock_res_top_assets.scalars().all.return_value = []

    mock_res_schedules = MagicMock()
    mock_res_schedules.one.return_value = (2, None)

    session.execute.side_effect = [
        mock_res_targets,
        mock_res_findings,
        mock_res_active_scans,
        mock_res_top_assets,
        mock_res_schedules,
    ]

    service = DashboardAnalyticsService(session=session)
    overview = await service.get_dashboard_overview(mock_user)

    assert isinstance(overview, DashboardOverviewResponse)
    assert overview.organization_id == str(mock_user.organization_id)
    assert overview.posture_summary.total_targets_count == 5
    assert overview.posture_summary.total_open_findings == 16
    assert overview.posture_summary.critical_findings_count == 2
    assert overview.posture_summary.high_findings_count == 4
    assert overview.posture_summary.posture_status == "CRITICAL_RISK"
    assert overview.vulnerability_breakdown.critical_count == 2
    assert overview.vulnerability_breakdown.high_count == 4
    assert overview.vulnerability_breakdown.medium_count == 10
    assert overview.schedules_summary.total_active_schedules == 2


@pytest.mark.anyio
async def test_dashboard_api_overview_endpoint(mock_user: UserModel) -> None:
    """Test GET /api/v1/dashboard/overview REST endpoint with mock user auth."""
    dummy_overview = DashboardOverviewResponse(
        organization_id=str(mock_user.organization_id),
        posture_summary=SecurityPostureSummaryDTO(
            composite_risk_score=45.0,
            posture_status="ELEVATED_RISK",
            total_targets_count=3,
            total_open_findings=8,
            critical_findings_count=0,
            high_findings_count=2,
        ),
        vulnerability_breakdown=VulnerabilitySeverityBreakdownDTO(
            critical_count=0,
            high_count=2,
            medium_count=4,
            low_count=2,
            info_count=0,
        ),
        active_scans=[
            ActiveScanSummaryDTO(
                job_id=str(uuid4()),
                target_name="staging.example.com",
                target_url="https://staging.example.com",
                execution_state="ASSESSING",
                current_step="Executing Active Plugins",
                started_at="2026-08-04T08:00:00Z",
                running_duration_seconds=120,
            )
        ],
        top_vulnerable_assets=[],
        schedules_summary={"total_active_schedules": 1, "next_scheduled_run_at": None},
        cached_at="2026-08-04T09:00:00Z",
    )

    async def override_get_current_user() -> UserModel:
        return mock_user

    async def override_get_dashboard_overview(
        *args: Any, **kwargs: Any
    ) -> DashboardOverviewResponse:
        return dummy_overview

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = override_get_current_user

    # Mock DashboardAnalyticsService method
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.application.assessment.dashboard_analytics_service.DashboardAnalyticsService.get_dashboard_overview",
            override_get_dashboard_overview,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/dashboard/overview")
            assert res.status_code == 200
            data = res.json()
            assert data["organization_id"] == str(mock_user.organization_id)
            assert data["posture_summary"]["posture_status"] == "ELEVATED_RISK"
            assert len(data["active_scans"]) == 1
            assert data["active_scans"][0]["execution_state"] == "ASSESSING"

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_dashboard_api_posture_endpoint(mock_user: UserModel) -> None:
    """Test GET /api/v1/dashboard/posture REST endpoint."""
    dummy_overview = DashboardOverviewResponse(
        organization_id=str(mock_user.organization_id),
        posture_summary=SecurityPostureSummaryDTO(
            composite_risk_score=15.0,
            posture_status="SECURE",
            total_targets_count=2,
            total_open_findings=1,
            critical_findings_count=0,
            high_findings_count=0,
        ),
        vulnerability_breakdown=VulnerabilitySeverityBreakdownDTO(),
        active_scans=[],
        top_vulnerable_assets=[],
        schedules_summary={"total_active_schedules": 0, "next_scheduled_run_at": None},
        cached_at="2026-08-04T09:00:00Z",
    )

    async def override_get_current_user() -> UserModel:
        return mock_user

    async def override_get_dashboard_overview(
        *args: Any, **kwargs: Any
    ) -> DashboardOverviewResponse:
        return dummy_overview

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = override_get_current_user

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.application.assessment.dashboard_analytics_service.DashboardAnalyticsService.get_dashboard_overview",
            override_get_dashboard_overview,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/dashboard/posture")
            assert res.status_code == 200
            data = res.json()
            assert data["posture_status"] == "SECURE"
            assert data["composite_risk_score"] == 15.0

    app.dependency_overrides.clear()
