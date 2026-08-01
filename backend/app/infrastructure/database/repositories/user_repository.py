"""SQLAlchemy User Repository."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
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

    async def update_last_login(self, user_id: UUID) -> None:
        """Update last_login_at timestamp for user."""
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
