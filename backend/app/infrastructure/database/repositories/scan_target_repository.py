"""Repository for Phase 6.2 Scan Target CRUD and Authorization Declaration persistence."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.scan_target import (
    AuthorizationDeclarationModel,
    ScanTargetModel,
)

logger = get_logger("vulnova.scan_target_repository")


class ScanTargetRepository:
    """Repository managing scan target persistence and authorization declaration audit records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Scan Target CRUD ──────────────────────────────────

    async def create_target(
        self,
        organization_id: UUID,
        name: str,
        target_url: str,
        environment: str = "PRODUCTION",
        created_by: Optional[UUID] = None,
    ) -> ScanTargetModel:
        """Create a new registered scan target with ownership verification token."""
        verification_token = f"vulnova-verify-{uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        model = ScanTargetModel(
            id=uuid4(),
            organization_id=organization_id,
            name=name.strip(),
            target_url=target_url.strip().rstrip("/"),
            environment=environment.upper(),
            status="ACTIVE",
            is_ownership_verified=False,
            ownership_verification_token=verification_token,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.session.add(model)
        await self.session.flush()
        logger.info(
            "scan_target.created",
            target_id=str(model.id),
            org_id=str(organization_id),
            url=target_url,
        )
        return model

    async def get_target_by_id(
        self, organization_id: UUID, target_id: UUID
    ) -> Optional[ScanTargetModel]:
        """Retrieve a scan target by ID with multi-tenant isolation."""
        stmt = select(ScanTargetModel).where(
            ScanTargetModel.organization_id == organization_id,
            ScanTargetModel.id == target_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_target_by_url(
        self, organization_id: UUID, target_url: str
    ) -> Optional[ScanTargetModel]:
        """Lookup a scan target by normalized URL within organization scope."""
        normalized_url = target_url.strip().rstrip("/")
        stmt = select(ScanTargetModel).where(
            ScanTargetModel.organization_id == organization_id,
            ScanTargetModel.target_url == normalized_url,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_targets(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
    ) -> List[ScanTargetModel]:
        """List all scan targets for an organization with optional status filter."""
        stmt = select(ScanTargetModel).where(
            ScanTargetModel.organization_id == organization_id,
        )
        if status:
            stmt = stmt.where(ScanTargetModel.status == status.upper())
        stmt = stmt.order_by(ScanTargetModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_target(
        self,
        organization_id: UUID,
        target_id: UUID,
        name: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[ScanTargetModel]:
        """Update mutable properties of a registered scan target."""
        values: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if name is not None:
            values["name"] = name.strip()
        if environment is not None:
            values["environment"] = environment.upper()
        if status is not None:
            values["status"] = status.upper()

        stmt = (
            update(ScanTargetModel)
            .where(
                ScanTargetModel.organization_id == organization_id,
                ScanTargetModel.id == target_id,
            )
            .values(**values)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_target_by_id(organization_id, target_id)

    async def archive_target(
        self, organization_id: UUID, target_id: UUID
    ) -> Optional[ScanTargetModel]:
        """Soft-delete a scan target by setting status to ARCHIVED."""
        return await self.update_target(
            organization_id=organization_id,
            target_id=target_id,
            status="ARCHIVED",
        )

    # ── Authorization Declaration Audit ───────────────────

    async def record_authorization_declaration(
        self,
        organization_id: UUID,
        scan_target_id: UUID,
        declared_by: UUID,
        is_authorized: bool,
        authorization_scope: str = "full",
        ip_address: Optional[str] = None,
    ) -> AuthorizationDeclarationModel:
        """Persist an immutable authorization consent declaration for legal audit trail."""
        model = AuthorizationDeclarationModel(
            id=uuid4(),
            organization_id=organization_id,
            scan_target_id=scan_target_id,
            declared_by=declared_by,
            is_authorized=is_authorized,
            authorization_scope=authorization_scope,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(model)
        await self.session.flush()
        logger.info(
            "authorization_declaration.recorded",
            declaration_id=str(model.id),
            target_id=str(scan_target_id),
            org_id=str(organization_id),
            is_authorized=is_authorized,
        )
        return model

    async def get_latest_authorization(
        self,
        organization_id: UUID,
        scan_target_id: UUID,
    ) -> Optional[AuthorizationDeclarationModel]:
        """Retrieve the most recent authorization declaration for a target."""
        stmt = (
            select(AuthorizationDeclarationModel)
            .where(
                AuthorizationDeclarationModel.organization_id == organization_id,
                AuthorizationDeclarationModel.scan_target_id == scan_target_id,
                AuthorizationDeclarationModel.is_authorized.is_(True),
            )
            .order_by(AuthorizationDeclarationModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
