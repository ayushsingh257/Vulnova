"""Repository for persisting and querying Attack Surface Asset Graph & Relationships."""

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.asset_graph import (
    AssetNodeModel,
    AssetRelationshipModel,
)

logger = get_logger("vulnova.asset_graph_repository")


class AssetGraphRepository:
    """Async repository for tenant-isolated asset nodes and relationship topology."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_node(
        self,
        organization_id: UUID,
        node_type: str,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetNodeModel:
        """Upsert an asset node for a target organization."""
        clean_value = value.strip()
        stmt = select(AssetNodeModel).where(
            AssetNodeModel.organization_id == organization_id,
            AssetNodeModel.node_type == node_type,
            AssetNodeModel.value == clean_value,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = str(name)
            if metadata:
                merged_meta: Dict[str, Any] = dict(existing.metadata_json or {})
                merged_meta.update(metadata)
                existing.metadata_json = merged_meta
            await self.session.flush()
            return existing

        node = AssetNodeModel(
            organization_id=organization_id,
            node_type=node_type,
            name=name,
            value=clean_value,
            metadata_json=metadata or {},
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def create_relationship(
        self,
        organization_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetRelationshipModel:
        """Create or update an edge relationship between two tenant asset nodes."""
        stmt = select(AssetRelationshipModel).where(
            AssetRelationshipModel.organization_id == organization_id,
            AssetRelationshipModel.source_node_id == source_node_id,
            AssetRelationshipModel.target_node_id == target_node_id,
            AssetRelationshipModel.relationship_type == relationship_type,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if metadata:
                merged_meta: Dict[str, Any] = dict(existing.metadata_json or {})
                merged_meta.update(metadata)
                existing.metadata_json = merged_meta
            await self.session.flush()
            return existing

        rel = AssetRelationshipModel(
            organization_id=organization_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=relationship_type,
            metadata_json=metadata or {},
        )
        self.session.add(rel)
        await self.session.flush()
        return rel

    async def get_graph_by_domain(
        self, organization_id: UUID, base_domain: str
    ) -> Tuple[List[AssetNodeModel], List[AssetRelationshipModel]]:
        """Retrieve all nodes and edge relationships for an organization's target domain."""
        stmt_nodes = select(AssetNodeModel).where(
            AssetNodeModel.organization_id == organization_id
        )
        res_nodes = await self.session.execute(stmt_nodes)
        nodes = list(res_nodes.scalars().all())

        stmt_rels = select(AssetRelationshipModel).where(
            AssetRelationshipModel.organization_id == organization_id
        )
        res_rels = await self.session.execute(stmt_rels)
        relationships = list(res_rels.scalars().all())

        return nodes, relationships

    async def get_node_by_id(
        self, organization_id: UUID, node_id: UUID
    ) -> Optional[AssetNodeModel]:
        """Fetch a specific asset node ensuring multi-tenant isolation."""
        stmt = select(AssetNodeModel).where(
            AssetNodeModel.id == node_id,
            AssetNodeModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
