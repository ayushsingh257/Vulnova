"""User Application Use Case Services."""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.dto import (
    InviteUserRequest,
    UpdateUserProfileRequest,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    UserDetailResponse,
    UserListResponse,
)
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.domain.entities.role import Role, parse_role
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.security.password import hash_password

logger = get_logger("vulnova.users")


class UserService:
    """Application service for User management use cases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def update_profile(
        self, current_user: UserModel, req: UpdateUserProfileRequest
    ) -> UserDetailResponse:
        """Update authenticated user's own profile."""
        current_user.full_name = req.full_name
        updated_user = await self.user_repo.update(current_user)
        logger.info("user.profile_updated", user_id=str(current_user.id))
        return UserDetailResponse.model_validate(updated_user)

    async def list_organization_users(self, organization_id: UUID) -> UserListResponse:
        """List all users belonging to an organization."""
        users = await self.user_repo.list_by_organization(organization_id)
        user_dtos = [UserDetailResponse.model_validate(u) for u in users]
        return UserListResponse(users=user_dtos, total=len(user_dtos))

    async def get_user_detail(
        self, user_id: UUID, organization_id: UUID
    ) -> UserDetailResponse:
        """Fetch user details enforcing tenant boundary."""
        user = await self.user_repo.get_by_id_and_org(user_id, organization_id)
        if not user:
            raise ResourceNotFoundException(f"User with ID '{user_id}' was not found")
        return UserDetailResponse.model_validate(user)

    async def invite_user(
        self, req: InviteUserRequest, current_user: UserModel
    ) -> UserDetailResponse:
        """Create / invite a new user within the authenticated user's organization."""
        # 1. Check email uniqueness
        existing_user = await self.user_repo.get_by_email(req.email)
        if existing_user:
            raise ConflictException(f"User with email '{req.email}' already exists")

        # 2. Validate assigned role
        try:
            target_role = parse_role(req.role)
        except ValueError as e:
            raise ValidationException(str(e)) from e

        # 3. Non-OWNER caller cannot create an OWNER user
        caller_role = parse_role(current_user.role)
        if target_role == Role.OWNER and caller_role != Role.OWNER:
            raise ForbiddenException("Only an OWNER can assign the OWNER role")

        # 4. Hash password and persist user
        hashed_pwd = hash_password(req.password)
        new_user = UserModel(
            id=uuid4(),
            organization_id=current_user.organization_id,
            email=req.email.lower().strip(),
            password_hash=hashed_pwd,
            full_name=req.full_name.strip(),
            role=target_role.name,
            is_active=True,
            is_mfa_enabled=False,
        )

        saved_user = await self.user_repo.create(new_user)
        logger.info(
            "user.created",
            user_id=str(saved_user.id),
            organization_id=str(current_user.organization_id),
            assigned_role=target_role.name,
            created_by=str(current_user.id),
        )
        return UserDetailResponse.model_validate(saved_user)

    async def update_user_role(
        self, target_user_id: UUID, req: UpdateUserRoleRequest, current_user: UserModel
    ) -> UserDetailResponse:
        """Update a team member's role (OWNER-only guard)."""
        # 1. Fetch target user with org boundary check
        target_user = await self.user_repo.get_by_id_and_org(
            target_user_id, current_user.organization_id
        )
        if not target_user:
            raise ResourceNotFoundException(
                f"User with ID '{target_user_id}' was not found"
            )

        # 2. Validate new role
        try:
            new_role = parse_role(req.role)
        except ValueError as e:
            raise ValidationException(str(e)) from e

        old_role = parse_role(target_user.role)

        # 3. Check sole owner protection if demoting an OWNER
        if old_role == Role.OWNER and new_role != Role.OWNER:
            owner_count = await self.user_repo.count_owners_in_org(
                current_user.organization_id
            )
            if owner_count <= 1:
                raise ValidationException(
                    "Cannot demote the sole active OWNER of an organization"
                )

        target_user.role = new_role.name
        updated_user = await self.user_repo.update(target_user)
        logger.info(
            "user.role_updated",
            target_user_id=str(target_user_id),
            old_role=old_role.name,
            new_role=new_role.name,
            updated_by=str(current_user.id),
        )
        return UserDetailResponse.model_validate(updated_user)

    async def update_user_status(
        self,
        target_user_id: UUID,
        req: UpdateUserStatusRequest,
        current_user: UserModel,
    ) -> UserDetailResponse:
        """Activate or deactivate a team member."""
        # 1. Prevent self-deactivation
        if target_user_id == current_user.id and not req.is_active:
            raise ValidationException("Users cannot deactivate their own account")

        # 2. Fetch target user
        target_user = await self.user_repo.get_by_id_and_org(
            target_user_id, current_user.organization_id
        )
        if not target_user:
            raise ResourceNotFoundException(
                f"User with ID '{target_user_id}' was not found"
            )

        # 3. Sole owner protection if deactivating an OWNER
        if parse_role(target_user.role) == Role.OWNER and not req.is_active:
            owner_count = await self.user_repo.count_owners_in_org(
                current_user.organization_id
            )
            if owner_count <= 1:
                raise ValidationException(
                    "Cannot deactivate the sole active OWNER of an organization"
                )

        target_user.is_active = req.is_active
        updated_user = await self.user_repo.update(target_user)
        logger.info(
            "user.status_updated",
            target_user_id=str(target_user_id),
            is_active=req.is_active,
            updated_by=str(current_user.id),
        )
        return UserDetailResponse.model_validate(updated_user)

    async def remove_user(self, target_user_id: UUID, current_user: UserModel) -> None:
        """Delete a team member from the organization."""
        # 1. Prevent self-deletion
        if target_user_id == current_user.id:
            raise ValidationException("Users cannot remove their own account")

        # 2. Fetch target user
        target_user = await self.user_repo.get_by_id_and_org(
            target_user_id, current_user.organization_id
        )
        if not target_user:
            raise ResourceNotFoundException(
                f"User with ID '{target_user_id}' was not found"
            )

        # 3. Sole owner protection if deleting an OWNER
        if parse_role(target_user.role) == Role.OWNER:
            owner_count = await self.user_repo.count_owners_in_org(
                current_user.organization_id
            )
            if owner_count <= 1:
                raise ValidationException(
                    "Cannot remove the sole active OWNER of an organization"
                )

        deleted = await self.user_repo.delete(
            target_user_id, current_user.organization_id
        )
        if not deleted:
            raise ResourceNotFoundException(
                f"User with ID '{target_user_id}' was not found"
            )

        logger.info(
            "user.deleted",
            target_user_id=str(target_user_id),
            removed_by=str(current_user.id),
        )
