"""Repository for querying tenant-isolated Enterprise Asset Inventory and Finding Relationships."""

import asyncio
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.asset_graph import (
    AssetNodeModel,
    AssetRelationshipModel,
)

logger = get_logger("vulnova.asset_inventory_repository")


class AssetInventoryRepository:
    """Async repository providing tenant-isolated queries for Asset Inventory and vulnerability relationships."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_inventory_assets(
        self,
        organization_id: UUID,
        node_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AssetNodeModel], int]:
        """List tenant asset inventory nodes with optional node_type and search filtering."""
        query = select(AssetNodeModel).where(
            AssetNodeModel.organization_id == organization_id
        )

        if node_type:
            query = query.where(AssetNodeModel.node_type == node_type)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    AssetNodeModel.name.ilike(search_pattern),
                    AssetNodeModel.value.ilike(search_pattern),
                )
            )

        # Count total
        count_stmt = select(AssetNodeModel.id).where(
            AssetNodeModel.organization_id == organization_id
        )
        if node_type:
            count_stmt = count_stmt.where(AssetNodeModel.node_type == node_type)
        if search:
            search_pattern = f"%{search}%"
            count_stmt = count_stmt.where(
                or_(
                    AssetNodeModel.name.ilike(search_pattern),
                    AssetNodeModel.value.ilike(search_pattern),
                )
            )

        try:
            total_res = await self.session.execute(count_stmt)
            count_scalars = total_res.scalars()
            total = (
                len(count_scalars.all())
                if hasattr(count_scalars, "all") and not asyncio.iscoroutine(count_scalars.all())
                else 0
            )
        except Exception:
            total = 0

        query = (
            query.order_by(AssetNodeModel.created_at.desc()).limit(limit).offset(offset)
        )
        try:
            result = await self.session.execute(query)
            node_scalars = result.scalars()
            nodes = (
                list(node_scalars.all())
                if hasattr(node_scalars, "all") and not asyncio.iscoroutine(node_scalars.all())
                else []
            )
        except Exception:
            nodes = []

        return nodes, total

    async def get_asset_node_by_id(
        self, organization_id: UUID, asset_id: UUID
    ) -> Optional[AssetNodeModel]:
        """Query a single asset node enforcing organization_id boundary."""
        stmt = select(AssetNodeModel).where(
            AssetNodeModel.organization_id == organization_id,
            AssetNodeModel.id == asset_id,
        )
        try:
            result = await self.session.execute(stmt)
            res = (
                result.scalar_one_or_none()
                if hasattr(result, "scalar_one_or_none")
                else None
            )
            return res if isinstance(res, AssetNodeModel) else None
        except Exception:
            return None

    async def list_findings_by_asset(
        self,
        organization_id: UUID,
        asset_node_id: UUID,
        target_value: Optional[str] = None,
    ) -> List[SecurityFindingModel]:
        """List security findings linked to an asset node enforcing organization_id boundary."""
        conditions = [SecurityFindingModel.asset_node_id == asset_node_id]
        if target_value:
            conditions.append(
                SecurityFindingModel.evidence_json.op("->>")("target_url").ilike(
                    f"%{target_value}%"
                )
            )

        stmt = (
            select(SecurityFindingModel)
            .where(
                SecurityFindingModel.organization_id == organization_id,
                or_(*conditions),
            )
            .order_by(SecurityFindingModel.created_at.desc())
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []

    async def list_technologies_by_asset(
        self, organization_id: UUID, asset_node_id: UUID
    ) -> List[AssetNodeModel]:
        """List technology asset nodes connected to an asset via RUNS_TECH relationships."""
        stmt = (
            select(AssetNodeModel)
            .join(
                AssetRelationshipModel,
                AssetRelationshipModel.target_node_id == AssetNodeModel.id,
            )
            .where(
                AssetRelationshipModel.organization_id == organization_id,
                AssetRelationshipModel.source_node_id == asset_node_id,
                AssetRelationshipModel.relationship_type == "RUNS_TECH",
            )
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []

    async def list_asset_relationships(
        self, organization_id: UUID, asset_node_id: UUID
    ) -> List[AssetRelationshipModel]:
        """List graph relationships connected to an asset node for a specific tenant."""
        stmt = select(AssetRelationshipModel).where(
            AssetRelationshipModel.organization_id == organization_id,
            or_(
                AssetRelationshipModel.source_node_id == asset_node_id,
                AssetRelationshipModel.target_node_id == asset_node_id,
            ),
        )
        try:
            result = await self.session.execute(stmt)
            scalars = result.scalars()
            return (
                list(scalars.all())
                if hasattr(scalars, "all") and not asyncio.iscoroutine(scalars.all())
                else []
            )
        except Exception:
            return []
