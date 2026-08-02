"""SQLAlchemy Organization Repository."""

from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.user import UserModel


class OrganizationRepository:
    """Async SQLAlchemy Organization Repository for tenant persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, org_id: UUID) -> Optional[OrganizationModel]:
        """Fetch organization by primary key UUID."""
        stmt = select(OrganizationModel).where(OrganizationModel.id == org_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[OrganizationModel]:
        """Fetch organization by unique slug."""
        stmt = select(OrganizationModel).where(OrganizationModel.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, org: OrganizationModel) -> OrganizationModel:
        """Persist a new organization entity."""
        self.session.add(org)
        await self.session.flush()
        return org

    async def update(self, org: OrganizationModel) -> OrganizationModel:
        """Update organization attributes."""
        self.session.add(org)
        await self.session.flush()
        return org

    async def get_with_member_count(
        self, org_id: UUID
    ) -> Tuple[Optional[OrganizationModel], int]:
        """Fetch organization and total count of associated users."""
        org = await self.get_by_id(org_id)
        if not org:
            return None, 0

        stmt = select(func.count(UserModel.id)).where(
            UserModel.organization_id == org_id
        )
        result = await self.session.execute(stmt)
        count = result.scalar()
        return org, int(count or 0)
