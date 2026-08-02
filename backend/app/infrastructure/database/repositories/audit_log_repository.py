"""SQLAlchemy AuditLog Repository."""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.audit_log import AuditLogModel


class AuditLogRepository:
    """Async SQLAlchemy AuditLog Repository for security audit persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, audit_log: AuditLogModel) -> AuditLogModel:
        """Persist an immutable audit log record."""
        self.session.add(audit_log)
        await self.session.flush()
        return audit_log

    async def list_by_organization(
        self,
        organization_id: UUID,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        actor_user_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
        load_actor: bool = True,
    ) -> Tuple[List[AuditLogModel], int]:
        """Fetch paginated audit log events for an organization with optional filters."""
        stmt = select(AuditLogModel).where(
            AuditLogModel.organization_id == organization_id
        )
        count_stmt = select(func.count(AuditLogModel.id)).where(
            AuditLogModel.organization_id == organization_id
        )

        if action:
            stmt = stmt.where(AuditLogModel.action == action)
            count_stmt = count_stmt.where(AuditLogModel.action == action)

        if resource_type:
            stmt = stmt.where(AuditLogModel.resource_type == resource_type)
            count_stmt = count_stmt.where(AuditLogModel.resource_type == resource_type)

        if actor_user_id:
            stmt = stmt.where(AuditLogModel.actor_user_id == actor_user_id)
            count_stmt = count_stmt.where(AuditLogModel.actor_user_id == actor_user_id)

        if load_actor:
            stmt = stmt.options(selectinload(AuditLogModel.actor_user))

        stmt = (
            stmt.order_by(AuditLogModel.created_at.desc()).offset(offset).limit(limit)
        )

        result = await self.session.execute(stmt)
        count_result = await self.session.execute(count_stmt)

        logs = list(result.scalars().all())
        total = int(count_result.scalar() or 0)

        return logs, total

    async def get_by_id_and_org(
        self, audit_log_id: UUID, organization_id: UUID, load_actor: bool = True
    ) -> Optional[AuditLogModel]:
        """Fetch a specific audit log record enforcing organization boundary."""
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.id == audit_log_id)
            .where(AuditLogModel.organization_id == organization_id)
        )
        if load_actor:
            stmt = stmt.options(selectinload(AuditLogModel.actor_user))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
