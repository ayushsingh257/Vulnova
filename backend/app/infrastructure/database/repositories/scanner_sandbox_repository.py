"""SQLAlchemy Repository for Scanner Sandbox Lifecycle Management."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.scanner_sandbox import ScannerSandboxModel


class ScannerSandboxRepository:
    """Async SQLAlchemy Repository for managing ephemeral scanner execution sandboxes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_sandbox(self, sandbox: ScannerSandboxModel) -> ScannerSandboxModel:
        """Persist a new scanner sandbox execution record."""
        self.session.add(sandbox)
        await self.session.flush()
        return sandbox

    async def get_sandbox_by_id(
        self, sandbox_id: UUID, organization_id: UUID
    ) -> Optional[ScannerSandboxModel]:
        """Fetch a specific sandbox record enforcing multi-tenant organization boundary."""
        stmt = (
            select(ScannerSandboxModel)
            .where(ScannerSandboxModel.id == sandbox_id)
            .where(ScannerSandboxModel.organization_id == organization_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_sandbox_by_scan_job_id(
        self, scan_job_id: UUID, organization_id: UUID
    ) -> Optional[ScannerSandboxModel]:
        """Fetch a sandbox record by associated scan job ID."""
        stmt = (
            select(ScannerSandboxModel)
            .where(ScannerSandboxModel.scan_job_id == scan_job_id)
            .where(ScannerSandboxModel.organization_id == organization_id)
            .order_by(ScannerSandboxModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_status(
        self,
        sandbox_id: UUID,
        status: str,
        exit_code: Optional[int] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ScannerSandboxModel]:
        """Update status and lifecycle timestamps of a sandbox."""
        stmt = select(ScannerSandboxModel).where(ScannerSandboxModel.id == sandbox_id)
        result = await self.session.execute(stmt)
        sandbox = result.scalar_one_or_none()
        if not sandbox:
            return None

        sandbox.status = status
        now = datetime.now(timezone.utc)
        if status == "RUNNING" and not sandbox.started_at:
            sandbox.started_at = now
        elif status in ("COMPLETED", "FAILED") and not sandbox.completed_at:
            sandbox.completed_at = now
        elif status == "DESTROYED":
            if not sandbox.completed_at:
                sandbox.completed_at = now
            sandbox.destroyed_at = now

        if exit_code is not None:
            sandbox.exit_code = exit_code

        if execution_metadata:
            current_meta = sandbox.execution_metadata or {}
            current_meta.update(execution_metadata)
            sandbox.execution_metadata = current_meta

        await self.session.flush()
        return sandbox

    async def list_sandboxes_by_org(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ScannerSandboxModel], int]:
        """List paginated sandboxes for an organization with optional status filter."""
        stmt = select(ScannerSandboxModel).where(
            ScannerSandboxModel.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(ScannerSandboxModel.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = (
            stmt.order_by(ScannerSandboxModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, total
