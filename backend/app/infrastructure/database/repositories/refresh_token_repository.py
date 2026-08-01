"""SQLAlchemy RefreshToken Repository."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.refresh_token import RefreshTokenModel


class RefreshTokenRepository:
    """Async SQLAlchemy RefreshToken Repository for token family persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: RefreshTokenModel) -> RefreshTokenModel:
        """Persist a new refresh token entity."""
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> Optional[RefreshTokenModel]:
        """Fetch refresh token by unique SHA-256 token hash."""
        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_family(self, family_id: UUID) -> None:
        """Revoke all tokens in a token family when token reuse is detected."""
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id)
            .values(is_revoked=True)
        )
        await self.session.execute(stmt)

    async def revoke_by_hash(self, token_hash: str) -> None:
        """Revoke a specific token by hash."""
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .values(is_revoked=True)
        )
        await self.session.execute(stmt)
