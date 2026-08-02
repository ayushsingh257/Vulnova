"""Organization Application Use Case Services."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.organizations.dto import (
    OrganizationDetailResponse,
    UpdateOrganizationRequest,
)
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)

logger = get_logger("vulnova.organizations")


class OrganizationService:
    """Application service for Organization management use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.org_repo = OrganizationRepository(session)
        self.audit_service = AuditLogService(session)

    async def get_organization(
        self, organization_id: UUID
    ) -> OrganizationDetailResponse:
        """Fetch organization profile details and active member count."""
        org, count = await self.org_repo.get_with_member_count(organization_id)
        if not org:
            raise ResourceNotFoundException(
                f"Organization with ID '{organization_id}' was not found"
            )

        return OrganizationDetailResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            plan_tier=org.plan_tier,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            member_count=count,
        )

    async def update_organization(
        self,
        organization_id: UUID,
        req: UpdateOrganizationRequest,
        current_user: UserModel,
    ) -> OrganizationDetailResponse:
        """Update organization details (name, plan_tier)."""
        org, count = await self.org_repo.get_with_member_count(organization_id)
        if not org:
            raise ResourceNotFoundException(
                f"Organization with ID '{organization_id}' was not found"
            )

        if req.name is not None:
            org.name = req.name.strip()
        if req.plan_tier is not None:
            org.plan_tier = req.plan_tier.strip().upper()

        updated_org = await self.org_repo.update(org)
        logger.info(
            "organization.updated",
            organization_id=str(organization_id),
            updated_by=str(current_user.id),
        )
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="organization.updated",
            resource_type="organization",
            resource_id=str(organization_id),
            actor_user_id=current_user.id,
            details={"name": updated_org.name, "plan_tier": updated_org.plan_tier},
        )

        return OrganizationDetailResponse(
            id=updated_org.id,
            name=updated_org.name,
            slug=updated_org.slug,
            plan_tier=updated_org.plan_tier,
            is_active=updated_org.is_active,
            created_at=updated_org.created_at,
            updated_at=updated_org.updated_at,
            member_count=count,
        )

    async def deactivate_organization(
        self, organization_id: UUID, current_user: UserModel
    ) -> None:
        """Deactivate organization (OWNER-only action)."""
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise ResourceNotFoundException(
                f"Organization with ID '{organization_id}' was not found"
            )

        org.is_active = False
        await self.org_repo.update(org)
        logger.info(
            "organization.deactivated",
            organization_id=str(organization_id),
            deactivated_by=str(current_user.id),
        )
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="organization.deactivated",
            resource_type="organization",
            resource_id=str(organization_id),
            actor_user_id=current_user.id,
            details={"is_active": False},
        )
