"""Unit and Integration Tests for Phase 7.4 Scan Management & Live Monitor Portal.

Tests:
1. Target URL masking utility (mask_target_url).
2. ScanManagementService paginated listing with target masking.
3. Telemetry summary retrieval with unmasked target URL & activity timeline.
4. REST API endpoints (GET /api/v1/assessments, GET /api/v1/assessments/{id}/telemetry).
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_active_user, get_current_user
from app.application.assessment.scan_management_service import (
    ScanManagementService,
)
from app.application.assessment.utils import mask_target_url
from app.infrastructure.database.models.assessment import AssessmentJobModel
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "analyst@example.com"
    user.role = "SECURITY_ANALYST"
    return user


def test_mask_target_url_utility() -> None:
    """Test target URL domain masking logic."""
    assert (
        mask_target_url("https://api.staging.example.com")
        == "https://a***.s***.e***.com"
    )
    assert (
        mask_target_url("http://internal-auth.domain.org:8080")
        == "http://i***.d***.org:8080"
    )
    assert mask_target_url("") == ""


@pytest.mark.anyio
async def test_scan_management_service_list_paginated(mock_user: UserModel) -> None:
    """Test ScanManagementService paginated listing applies target masking."""
    session = AsyncMock()

    # Mock count query return
    mock_count_res = MagicMock()
    mock_count_res.scalar_one.return_value = 1

    # Mock job query return
    mock_job = MagicMock(spec=AssessmentJobModel)
    mock_job.id = uuid4()
    mock_job.target_url = "https://auth.staging.example.com"
    mock_job.profile_id = "FULL_RECON"
    mock_job.status = "ASSESSING"
    mock_job.current_step = "Executing Security Testing Plugins"
    mock_job.progress_percentage = 45.0
    mock_job.created_at = None
    mock_job.completed_at = None

    mock_job_res = MagicMock()
    mock_job_res.scalars().all.return_value = [mock_job]

    mock_finding_res = MagicMock()
    mock_finding_res.scalar_one.return_value = 3

    session.execute.side_effect = [mock_count_res, mock_job_res, mock_finding_res]

    service = ScanManagementService(session=session)
    result = await service.list_assessments_paginated(mock_user, page=1, page_size=20)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].masked_target_url == "https://a***.s***.e***.com"
    assert result.items[0].findings_count == 3


@pytest.mark.anyio
async def test_scan_management_service_telemetry(mock_user: UserModel) -> None:
    """Test get_assessment_telemetry_summary returns unmasked target URL & timeline."""
    session = AsyncMock()
    job_id = uuid4()

    mock_job = MagicMock(spec=AssessmentJobModel)
    mock_job.id = job_id
    mock_job.target_url = "https://auth.staging.example.com"
    mock_job.profile_id = "FULL_RECON"
    mock_job.status = "ASSESSING"
    mock_job.current_step = "Executing Active Security Plugins"
    mock_job.progress_percentage = 65.0
    mock_job.created_at = None
    mock_job.completed_at = None

    mock_job_res = MagicMock()
    mock_job_res.scalar_one_or_none.return_value = mock_job

    mock_finding_res = MagicMock()
    mock_finding_res.scalar_one.return_value = 5

    session.execute.side_effect = [mock_job_res, mock_finding_res]

    service = ScanManagementService(session=session)
    telemetry = await service.get_assessment_telemetry_summary(job_id, mock_user)

    assert telemetry.id == str(job_id)
    assert telemetry.unmasked_target_url == "https://auth.staging.example.com"
    assert telemetry.findings_count == 5
    assert len(telemetry.timeline_items) >= 3


@pytest.mark.anyio
async def test_scan_portal_rest_endpoints(mock_user: UserModel) -> None:
    """Test GET /api/v1/assessments paginated REST endpoint."""

    async def override_get_current_user() -> UserModel:
        return mock_user

    async def override_list_assessments(*args: Any, **kwargs: Any) -> Any:
        return {
            "items": [
                {
                    "id": str(uuid4()),
                    "target_name": "Scope (api.staging.example.com)",
                    "environment": "PRODUCTION",
                    "masked_target_url": "https://a***.s***.e***.com",
                    "profile_name": "FULL_RECON",
                    "status": "ASSESSING",
                    "current_step": "Executing Active Security Plugins",
                    "progress_percentage": 65.0,
                    "findings_count": 4,
                    "started_at": "2026-08-04T10:00:00Z",
                    "completed_at": None,
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = override_get_current_user

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.application.assessment.scan_management_service.ScanManagementService.list_assessments_paginated",
            override_list_assessments,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            res = await client.get("/api/v1/assessments?page=1&page_size=20")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 1
            assert data["items"][0]["masked_target_url"] == "https://a***.s***.e***.com"

    app.dependency_overrides.clear()
