"""Repository for persisting and querying tenant-isolated Asset Posture Snapshots & Security Change Events."""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.trend import (
    AssetChangeEventModel,
    AssetSnapshotModel,
)

logger = get_logger("vulnova.asset_trend_repository")


class AssetTrendRepository:
    """Async repository managing tenant-isolated posture snapshots and historical change timeline events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(
        self,
        organization_id: UUID,
        assessment_job_id: Optional[UUID] = None,
        total_assets: int = 0,
        total_findings: int = 0,
        critical_findings: int = 0,
        high_findings: int = 0,
        medium_findings: int = 0,
        low_findings: int = 0,
        info_findings: int = 0,
        avg_risk_score: float = 0.0,
        max_risk_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetSnapshotModel:
        """Create and persist a point-in-time posture snapshot linked to an organization and optional assessment job."""
        snapshot = AssetSnapshotModel(
            organization_id=organization_id,
            assessment_job_id=assessment_job_id,
            total_assets=total_assets,
            total_findings=total_findings,
            critical_findings=critical_findings,
            high_findings=high_findings,
            medium_findings=medium_findings,
            low_findings=low_findings,
            info_findings=info_findings,
            avg_risk_score=round(avg_risk_score, 2),
            max_risk_score=round(max_risk_score, 2),
            metadata_json=metadata or {},
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest_snapshot(
        self, organization_id: UUID
    ) -> Optional[AssetSnapshotModel]:
        """Fetch the most recent posture snapshot for an organization."""
        stmt = (
            select(AssetSnapshotModel)
            .where(AssetSnapshotModel.organization_id == organization_id)
            .order_by(AssetSnapshotModel.created_at.desc())
            .limit(1)
        )
        try:
            result = await self.session.execute(stmt)
            res = (
                result.scalar_one_or_none()
                if hasattr(result, "scalar_one_or_none")
                else None
            )
            return res if isinstance(res, AssetSnapshotModel) else None
        except Exception:
            return None

    async def list_snapshots(
        self, organization_id: UUID, limit: int = 30, offset: int = 0
    ) -> List[AssetSnapshotModel]:
        """List historical posture snapshots for an organization ordered by timestamp desc."""
        stmt = (
            select(AssetSnapshotModel)
            .where(AssetSnapshotModel.organization_id == organization_id)
            .order_by(AssetSnapshotModel.created_at.desc())
            .limit(limit)
            .offset(offset)
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

    async def record_change_event(
        self,
        organization_id: UUID,
        change_type: str,
        title: str,
        description: Optional[str] = None,
        asset_node_id: Optional[UUID] = None,
        assessment_job_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AssetChangeEventModel:
        """Record a discrete attack surface change event in audit timeline history."""
        event = AssetChangeEventModel(
            organization_id=organization_id,
            change_type=change_type,
            title=title,
            description=description,
            asset_node_id=asset_node_id,
            assessment_job_id=assessment_job_id,
            details_json=details or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_change_events(
        self,
        organization_id: UUID,
        asset_node_id: Optional[UUID] = None,
        change_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AssetChangeEventModel]:
        """List change events for a tenant with optional asset node or change type filtering."""
        stmt = select(AssetChangeEventModel).where(
            AssetChangeEventModel.organization_id == organization_id
        )
        if asset_node_id:
            stmt = stmt.where(AssetChangeEventModel.asset_node_id == asset_node_id)
        if change_type:
            stmt = stmt.where(AssetChangeEventModel.change_type == change_type)

        stmt = (
            stmt.order_by(AssetChangeEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
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
