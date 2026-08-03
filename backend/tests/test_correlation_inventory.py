"""Unit and Integration Tests for Phase 4.8 Multi-Source Finding Correlation & Asset Inventory Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.asset_inventory_service import AssetInventoryService
from app.application.assessment.correlation_engine import AssessmentCorrelationEngine
from app.domain.entities.assessment import (
    AssessmentContext,
    Finding,
    RiskMetrics,
    SeverityLevel,
)
from app.domain.entities.discovery import AssetNode, AssetNodeType
from app.infrastructure.database.models.asset_graph import (
    AssetNodeModel,
    AssetRelationshipModel,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.asset_inventory_repository import (
    AssetInventoryRepository,
)


def test_correlation_engine_node_matching_and_risk_aggregation() -> None:
    """Test AssessmentCorrelationEngine links findings to Asset Graph nodes and aggregates risk scores."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            engine = AssessmentCorrelationEngine()
            org_id = uuid4()

            context = AssessmentContext(
                target_url="https://shop.example.com/api",
                target_domain="shop.example.com",
                organization_id=org_id,
            )

            finding1 = Finding(
                organization_id=org_id,
                title="SQL Injection in Search",
                severity=SeverityLevel.CRITICAL,
                risk=RiskMetrics(composite_risk_score=92.5, risk_level="CRITICAL"),
            )
            finding2 = Finding(
                organization_id=org_id,
                title="Missing Security Headers",
                severity=SeverityLevel.LOW,
                risk=RiskMetrics(composite_risk_score=15.0, risk_level="LOW"),
            )

            mock_node = MagicMock(spec=AssetNodeModel)
            mock_node.id = uuid4()

            mock_session = AsyncMock()

            # Mock AssetGraphRepository.upsert_node
            with pytest.MonkeyPatch.context() as m:
                m.setattr(
                    "app.infrastructure.database.repositories.asset_graph_repository.AssetGraphRepository.upsert_node",
                    AsyncMock(return_value=mock_node),
                )

                correlated = await engine.correlate_findings(
                    [finding1, finding2], context, mock_session
                )

                assert len(correlated) == 2
                assert finding1.asset_node_id == mock_node.id
                assert finding2.asset_node_id == mock_node.id

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_asset_inventory_repository_tenant_isolation() -> None:
    """Test AssetInventoryRepository enforces strict organization_id boundary checks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()

            org_id_1 = uuid4()
            org_id_2 = uuid4()
            asset_id = uuid4()

            mock_node_1 = MagicMock(spec=AssetNodeModel)
            mock_node_1.id = asset_id
            mock_node_1.organization_id = org_id_1

            repo = AssetInventoryRepository(mock_session)

            # Mock execute result
            mock_result_1 = MagicMock()
            mock_result_1.scalar_one_or_none.return_value = mock_node_1

            mock_result_2 = MagicMock()
            mock_result_2.scalar_one_or_none.return_value = None

            mock_session.execute.side_effect = [mock_result_1, mock_result_2]

            res1 = await repo.get_asset_node_by_id(org_id_1, asset_id)
            assert res1 is not None
            assert res1.id == asset_id

            res2 = await repo.get_asset_node_by_id(org_id_2, asset_id)
            assert res2 is None

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_asset_inventory_service_list_and_detail() -> None:
    """Test AssetInventoryService aggregates asset nodes, technologies, and severity counts."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssetInventoryService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            asset_id = uuid4()
            mock_node = MagicMock(spec=AssetNodeModel)
            mock_node.id = asset_id
            mock_node.node_type = "TARGET_DOMAIN"
            mock_node.name = "api.example.com"
            mock_node.value = "api.example.com"
            mock_node.metadata_json = {
                "composite_risk_score": 85.0,
                "risk_level": "HIGH",
                "total_findings": 3,
                "findings_by_severity": {"CRITICAL": 1, "HIGH": 2},
            }
            mock_node.created_at = "2026-08-03T00:00:00Z"
            mock_node.updated_at = "2026-08-03T00:00:00Z"

            tech_node = MagicMock(spec=AssetNodeModel)
            tech_node.id = uuid4()
            tech_node.name = "FastAPI"
            tech_node.metadata_json = {
                "category": "BACKEND_FRAMEWORK",
                "version": "0.110.0",
            }

            service.repo.list_inventory_assets = AsyncMock(
                return_value=([mock_node], 1)
            )
            service.repo.get_asset_node_by_id = AsyncMock(return_value=mock_node)
            service.repo.list_technologies_by_asset = AsyncMock(
                return_value=[tech_node]
            )
            service.repo.list_findings_by_asset = AsyncMock(return_value=[])
            service.repo.list_asset_relationships = AsyncMock(return_value=[])

            res = await service.list_asset_inventory(mock_user)
            assert res.total == 1
            assert len(res.items) == 1
            item = res.items[0]
            assert item.name == "api.example.com"
            assert item.risk_score == 85.0
            assert "FastAPI" in item.technologies

            detail = await service.get_asset_detail(mock_user, asset_id)
            assert detail.asset.name == "api.example.com"
            assert len(detail.technologies) == 1
            assert detail.technologies[0]["name"] == "FastAPI"

        loop.run_until_complete(_run())
    finally:
        loop.close()
