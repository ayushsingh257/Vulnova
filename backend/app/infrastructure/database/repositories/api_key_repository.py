"""SQLAlchemy APIKey Repository."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.api_key import APIKeyModel


class APIKeyRepository:
    """Async SQLAlchemy APIKey Repository for API key persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self, key_id: UUID, organization_id: Optional[UUID] = None
    ) -> Optional[APIKeyModel]:
        """Fetch API key by primary key UUID, optionally enforcing organization scope."""
        stmt = select(APIKeyModel).where(APIKeyModel.id == key_id)
        if organization_id:
            stmt = stmt.where(APIKeyModel.organization_id == organization_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(
        self, key_hash: str, load_relationships: bool = True
    ) -> Optional[APIKeyModel]:
        """Fetch API key by SHA-256 key_hash, loading user and organization relationships."""
        stmt = select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        if load_relationships:
            stmt = stmt.options(
                selectinload(APIKeyModel.user),
                selectinload(APIKeyModel.organization),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: UUID) -> List[APIKeyModel]:
        """List all API keys belonging to an Organization."""
        stmt = (
            select(APIKeyModel)
            .where(APIKeyModel.organization_id == organization_id)
            .order_by(APIKeyModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, api_key: APIKeyModel) -> APIKeyModel:
        """Persist a new API key entity."""
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def update_last_used(self, key_id: UUID) -> None:
        """Update last_used_at timestamp for API key."""
        stmt = (
            update(APIKeyModel)
            .where(APIKeyModel.id == key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    async def delete(self, key_id: UUID, organization_id: UUID) -> bool:
        """Revoke / delete an API key belonging to an organization.

        Returns:
            True if key was deleted, False if key was not found.
        """
        stmt = (
            delete(APIKeyModel)
            .where(APIKeyModel.id == key_id)
            .where(APIKeyModel.organization_id == organization_id)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
