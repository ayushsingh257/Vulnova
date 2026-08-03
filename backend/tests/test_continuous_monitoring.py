"""Unit and Integration Tests for Phase 4.9 Attack Surface Trend & Continuous Monitoring Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.continuous_monitoring import (
    ChangeDetectionEngine,
    ContinuousMonitoringService,
)
from app.domain.entities.assessment import (
    AssessmentContext,
    Finding,
    RiskMetrics,
    SeverityLevel,
)
from app.infrastructure.database.models.trend import (
    AssetChangeEventModel,
    AssetSnapshotModel,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.asset_trend_repository import (
    AssetTrendRepository,
)


def test_posture_snapshot_creation_and_risk_aggregation() -> None:
    """Test ContinuousMonitoringService creates an organization-isolated, job-linked, timestamped posture snapshot reusing RiskIntelligenceEngine scores."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = ContinuousMonitoringService(mock_session)

            org_id = uuid4()
            job_id = uuid4()

            context = AssessmentContext(
                target_url="https://app.example.com",
                target_domain="app.example.com",
                organization_id=org_id,
            )

            finding1 = Finding(
                organization_id=org_id,
                title="Reflected XSS in Login",
                severity=SeverityLevel.HIGH,
                risk=RiskMetrics(composite_risk_score=75.0, risk_level="HIGH"),
            )
            finding2 = Finding(
                organization_id=org_id,
                title="Missing HSTS Header",
                severity=SeverityLevel.LOW,
                risk=RiskMetrics(composite_risk_score=15.0, risk_level="LOW"),
            )

            mock_snap_model = MagicMock(spec=AssetSnapshotModel)
            mock_snap_model.id = uuid4()
            mock_snap_model.organization_id = org_id
            mock_snap_model.assessment_job_id = job_id
            mock_snap_model.total_assets = 5
            mock_snap_model.total_findings = 2
            mock_snap_model.critical_findings = 0
            mock_snap_model.high_findings = 1
            mock_snap_model.medium_findings = 0
            mock_snap_model.low_findings = 1
            mock_snap_model.info_findings = 0
            mock_snap_model.avg_risk_score = 45.0
            mock_snap_model.max_risk_score = 75.0
            mock_snap_model.created_at = "2026-08-03T00:00:00Z"

            service.trend_repo.get_latest_snapshot = AsyncMock(return_value=None)
            service.trend_repo.create_snapshot = AsyncMock(return_value=mock_snap_model)
            service.inventory_repo.list_inventory_assets = AsyncMock(
                return_value=([], 5)
            )

            snap, changes = await service.process_scan_run(
                org_id, job_id, [finding1, finding2], context
            )

            assert snap.assessment_job_id == str(job_id)
            assert snap.total_findings == 2
            assert snap.max_risk_score == 75.0

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_change_detection_engine_lifecycle_states() -> None:
    """Test ChangeDetectionEngine identifies NEW and RESOLVED finding lifecycle transitions."""
    engine = ChangeDetectionEngine()

    org_id = uuid4()
    f1 = Finding(
        organization_id=org_id, title="SQL Injection", severity=SeverityLevel.CRITICAL
    )
    f2 = Finding(
        organization_id=org_id, title="XSS Vulnerability", severity=SeverityLevel.HIGH
    )

    prev_titles = {"XSS Vulnerability", "CORS Misconfiguration"}

    changes = engine.analyze_finding_lifecycle([f1, f2], prev_titles)

    change_types = [c[0] for c in changes]
    assert "FINDING_NEW" in change_types  # SQL Injection is NEW
    assert "FINDING_RESOLVED" in change_types  # CORS Misconfiguration is RESOLVED


def test_trend_repository_tenant_isolation() -> None:
    """Test AssetTrendRepository isolates snapshots strictly by organization_id."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            repo = AssetTrendRepository(mock_session)

            org_id_1 = uuid4()
            org_id_2 = uuid4()

            mock_snap_1 = MagicMock(spec=AssetSnapshotModel)
            mock_snap_1.id = uuid4()
            mock_snap_1.organization_id = org_id_1

            mock_result_1 = MagicMock()
            mock_result_1.scalar_one_or_none.return_value = mock_snap_1

            mock_result_2 = MagicMock()
            mock_result_2.scalar_one_or_none.return_value = None

            mock_session.execute.side_effect = [mock_result_1, mock_result_2]

            res1 = await repo.get_latest_snapshot(org_id_1)
            assert res1 is not None
            assert res1.organization_id == org_id_1

            res2 = await repo.get_latest_snapshot(org_id_2)
            assert res2 is None

        loop.run_until_complete(_run())
    finally:
        loop.close()
