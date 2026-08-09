"""SQLAlchemy Repository for Scan Approval Requests."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.scan_approval_request import (
    ScanApprovalRequestModel,
)


class ScanApprovalRepository:
    """Repository managing scan approval requests for sensitive targets in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_approval_request(
        self, request: ScanApprovalRequestModel
    ) -> ScanApprovalRequestModel:
        """Persist a new scan approval request."""
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_approval_request_by_id(
        self, request_id: UUID, organization_id: UUID
    ) -> Optional[ScanApprovalRequestModel]:
        """Fetch a specific scan approval request enforcing tenant boundaries."""
        query = select(ScanApprovalRequestModel).where(
            ScanApprovalRequestModel.id == request_id,
            ScanApprovalRequestModel.organization_id == organization_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_approved_request_for_target(
        self, target_id: UUID, organization_id: UUID
    ) -> Optional[ScanApprovalRequestModel]:
        """Check if an active APPROVED request exists for a target."""
        query = (
            select(ScanApprovalRequestModel)
            .where(
                ScanApprovalRequestModel.target_id == target_id,
                ScanApprovalRequestModel.organization_id == organization_id,
                ScanApprovalRequestModel.status == "APPROVED",
            )
            .order_by(ScanApprovalRequestModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_approval_requests(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ScanApprovalRequestModel], int]:
        """Fetch paginated scan approval requests for an organization."""
        query = select(ScanApprovalRequestModel).where(
            ScanApprovalRequestModel.organization_id == organization_id
        )
        count_query = select(func.count()).where(
            ScanApprovalRequestModel.organization_id == organization_id
        )

        if status:
            query = query.where(ScanApprovalRequestModel.status == status)
            count_query = count_query.where(ScanApprovalRequestModel.status == status)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        query = (
            query.order_by(ScanApprovalRequestModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(query)
        items = list(res.scalars().all())
        return items, total

    async def update_status(
        self,
        request_id: UUID,
        status: str,
        approved_by: Optional[UUID] = None,
        rejection_reason: Optional[str] = None,
    ) -> Optional[ScanApprovalRequestModel]:
        """Update request status (APPROVED, REJECTED)."""
        values: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if approved_by is not None:
            values["approved_by"] = approved_by
        if rejection_reason is not None:
            values["rejection_reason"] = rejection_reason

        stmt = (
            update(ScanApprovalRequestModel)
            .where(ScanApprovalRequestModel.id == request_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        await self.session.flush()

        query = select(ScanApprovalRequestModel).where(
            ScanApprovalRequestModel.id == request_id
        )
        res = await self.session.execute(query)
        model = res.scalar_one_or_none()
        if model:
            model.status = status
            if approved_by is not None:
                model.approved_by = approved_by
            if rejection_reason is not None:
                model.rejection_reason = rejection_reason
        return model
