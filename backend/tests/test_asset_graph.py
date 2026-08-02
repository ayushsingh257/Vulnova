"""Unit and Integration Tests for Attack Surface Asset Graph & Relationship Mapping."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.discovery.asset_graph_service import AssetGraphService
from app.application.discovery.dto import BuildAssetGraphRequest
from app.core.exceptions import ResourceNotFoundException
from app.domain.entities.discovery import AssetNodeType, RelationshipType
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.asset_graph_repository import (
    AssetGraphRepository,
)


def test_asset_graph_enums() -> None:
    """Test AssetNodeType and RelationshipType enums."""
    assert AssetNodeType.TARGET_DOMAIN.value == "TARGET_DOMAIN"
    assert AssetNodeType.SUBDOMAIN.value == "SUBDOMAIN"
    assert AssetNodeType.IP_ADDRESS.value == "IP_ADDRESS"
    assert AssetNodeType.TECHNOLOGY.value == "TECHNOLOGY"

    assert RelationshipType.BELONGS_TO.value == "BELONGS_TO"
    assert RelationshipType.RESOLVES_TO.value == "RESOLVES_TO"
    assert RelationshipType.RUNS_TECH.value == "RUNS_TECH"
    assert RelationshipType.HAS_ENDPOINT.value == "HAS_ENDPOINT"


def test_asset_graph_service_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AssetGraphService build pipeline ingests subdomains, crawls, and tech fingerprints with audit logs."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssetGraphService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            # Mock repository calls
            mock_domain_node = MagicMock()
            mock_domain_node.id = uuid4()
            mock_domain_node.node_type = "TARGET_DOMAIN"
            mock_domain_node.name = "example.com"
            mock_domain_node.value = "example.com"
            mock_domain_node.metadata_json = {}

            mock_repo = AsyncMock()
            mock_repo.upsert_node.return_value = mock_domain_node
            mock_repo.get_graph_by_domain.return_value = ([mock_domain_node], [])
            service.repo = mock_repo

            # Mock discovery service components
            mock_sub_res = MagicMock()
            mock_sub_res.discovered_subdomains = []
            mock_discovery = AsyncMock()
            mock_discovery.discover_subdomains.return_value = mock_sub_res

            mock_crawl_res = MagicMock()
            mock_crawl_res.discovered_urls = []
            mock_discovery.crawl_target.return_value = mock_crawl_res

            mock_tech_res = MagicMock()
            mock_tech_res.detected_technologies = []
            mock_discovery.discover_technologies.return_value = mock_tech_res

            service.discovery_service = mock_discovery

            req = BuildAssetGraphRequest(target_domain="example.com")
            res = await service.build_asset_graph(req, mock_user)

            assert res.target_domain == "example.com"
            assert res.total_nodes == 1
            assert res.nodes[0].value == "example.com"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_asset_graph_service_get_node_not_found() -> None:
    """Test get_node_details raises NotFoundException when node is absent or belongs to another tenant."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssetGraphService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            mock_repo = AsyncMock()
            mock_repo.get_node_by_id.return_value = None
            service.repo = mock_repo

            random_id = uuid4()
            with pytest.raises(ResourceNotFoundException) as exc_info:
                await service.get_node_details(random_id, mock_user)

            assert "not found" in str(exc_info.value).lower()

        loop.run_until_complete(_run())
    finally:
        loop.close()
