"""SQLAlchemy User Repository."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.user import UserModel


class UserRepository:
    """Async SQLAlchemy User Repository for user persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self, user_id: UUID, load_organization: bool = False
    ) -> Optional[UserModel]:
        """Fetch user by primary key UUID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        if load_organization:
            stmt = stmt.options(selectinload(UserModel.organization))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(
        self, email: str, load_organization: bool = False
    ) -> Optional[UserModel]:
        """Fetch user by unique email address."""
        stmt = select(UserModel).where(UserModel.email == email)
        if load_organization:
            stmt = stmt.options(selectinload(UserModel.organization))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: UserModel) -> UserModel:
        """Persist a new user entity."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def list_by_organization(
        self, organization_id: UUID, load_organization: bool = False
    ) -> List[UserModel]:
        """List all users belonging to an Organization ordered by creation date."""
        stmt = (
            select(UserModel)
            .where(UserModel.organization_id == organization_id)
            .order_by(UserModel.created_at.desc())
        )
        if load_organization:
            stmt = stmt.options(selectinload(UserModel.organization))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_and_org(
        self, user_id: UUID, organization_id: UUID, load_organization: bool = False
    ) -> Optional[UserModel]:
        """Fetch user by ID enforcing organization boundary."""
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.organization_id == organization_id)
        )
        if load_organization:
            stmt = stmt.options(selectinload(UserModel.organization))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, user: UserModel) -> UserModel:
        """Update user entity attributes."""
        self.session.add(user)
        await self.session.flush()
        return user

    async def count_owners_in_org(self, organization_id: UUID) -> int:
        """Count active users with OWNER role in organization (for sole owner checks)."""
        stmt = (
            select(func.count(UserModel.id))
            .where(UserModel.organization_id == organization_id)
            .where(UserModel.role == "OWNER")
            .where(UserModel.is_active == True)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        count = result.scalar()
        return int(count or 0)

    async def delete(self, user_id: UUID, organization_id: UUID) -> bool:
        """Delete user entity enforcing organization boundary.

        Uses DELETE ... RETURNING for type-safe SQLAlchemy 2.0 compatibility.
        """
        stmt = (
            delete(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.organization_id == organization_id)
            .returning(UserModel.id)
        )
        result = await self.session.execute(stmt)
        deleted_id = result.scalar_one_or_none()
        return deleted_id is not None

    async def update_last_login(self, user_id: UUID) -> None:
        """Update last_login_at timestamp for user."""
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
