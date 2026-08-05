"""Administrative Aggregator Application Service for Enterprise Control Plane."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.admin.dto import (
    APIKeyAdminItemDTO,
    APIKeyAdminListResponse,
    CreateAPIKeyAdminRequest,
    CreateAPIKeyAdminResponse,
    InviteUserAdminRequest,
    OrganizationAdminResponse,
    PermissionBoundaryDTO,
    RolePermissionBoundaryDTO,
    RolePermissionMatrixResponse,
    SecurityOverviewAdminResponse,
    UpdateOrganizationAdminRequest,
    UpdateUserRoleAdminRequest,
    UserAdminItemDTO,
    UserAdminListResponse,
)
from app.application.api_keys.dto import CreateAPIKeyRequest
from app.application.api_keys.services import APIKeyService
from app.application.audit_logs.services import AuditLogService
from app.application.organizations.dto import UpdateOrganizationRequest
from app.application.organizations.services import OrganizationService
from app.application.users.dto import (
    InviteUserRequest,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
)
from app.application.users.services import UserService
from app.core.exceptions import (
    ForbiddenException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.domain.entities.role import PERMISSION_MAP, Role, parse_role
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.api_key_repository import APIKeyRepository
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository

logger = get_logger("vulnova.admin_service")

PERMISSION_DESCRIPTIONS = {
    "organization:read": "View organization metadata and settings",
    "organization:update": "Modify organization profile and subscription plan",
    "organization:delete": "Delete organization workspace",
    "organization:manage_billing": "Manage organization billing and tier",
    "users:read": "View organization team members and account status",
    "users:invite": "Invite new team members to organization",
    "users:update_role": "Modify team member RBAC permissions",
    "users:remove": "Deactivate or remove team member accounts",
    "targets:read": "View scan target assets",
    "targets:create": "Register new scan target assets",
    "targets:update": "Modify scan target configuration",
    "targets:delete": "Delete scan target assets",
    "scans:read": "View assessment job telemetry and reports",
    "scans:create": "Trigger security assessment scans",
    "scans:cancel": "Cancel active scan jobs",
    "scans:retry": "Retry failed scan jobs",
    "scans:schedule": "Configure recurring scan schedules",
    "scans:delete": "Delete assessment scan records",
    "assets:read": "View enterprise asset graph inventory",
    "findings:read": "View security findings and evidence artifacts",
    "findings:triage": "Triage finding status and apply suppression rules",
    "findings:suppress": "Create automatic finding suppression rules",
    "findings:ai_analyze": "Trigger AI finding analysis",
    "findings:ai_explain": "View AI finding explanations",
    "findings:ai_attack_path": "View AI attack path synthesis",
    "findings:ai_remediate": "View AI remediation guidance and patch suggestions",
    "findings:ai_confidence": "View AI confidence intelligence reports",
    "findings:export": "Export finding reports",
    "knowledge:read": "Search RAG security knowledge base",
    "knowledge:write": "Ingest RAG security reference standards",
    "knowledge:delete": "Manage RAG vector embeddings",
    "copilot:read": "Access AI Security Copilot",
    "copilot:chat": "Interact with AI Security Copilot agent",
    "copilot:manage": "Manage Copilot session memory",
    "copilot:feedback": "Submit Copilot response evaluation",
    "workers:read": "View worker cluster nodes and metrics",
    "workers:manage": "Scale worker node cluster",
    "scans:dispatch": "Dispatch scan jobs to priority queues",
    "scans:authorize": "Declare scan legal consent authorization",
    "dashboard:read": "View SOC security operations dashboard",
    "analytics:read": "View executive analytics and risk trends",
    "reports:read": "View executive report summaries",
    "reports:generate": "Generate executive security reports",
    "reports:export": "Download executive report exports",
    "api_keys:read": "View active machine-to-machine API keys",
    "api_keys:create": "Generate machine-to-machine API keys",
    "api_keys:revoke": "Revoke integration API keys",
    "integrations:read": "View third-party integration Webhooks",
    "integrations:manage": "Manage integration Webhooks",
    "audit_logs:read": "View security audit log events",
}


class AdminService:
    """Administrative control plane service for organization, team user, role matrix, and API key governance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.org_service = OrganizationService(session)
        self.user_service = UserService(session)
        self.api_key_service = APIKeyService(session)
        self.org_repo = OrganizationRepository(session)
        self.user_repo = UserRepository(session)
        self.api_key_repo = APIKeyRepository(session)
        self.audit_service = AuditLogService(session)

    # ── Organization Profile & Statistics ─────────────────

    async def get_organization_details(
        self, organization_id: UUID
    ) -> OrganizationAdminResponse:
        """Fetch organization admin profile and active member statistics."""
        org_dto = await self.org_service.get_organization(organization_id)
        api_keys = await self.api_key_repo.list_by_organization(organization_id)
        now = datetime.now(timezone.utc)
        active_api_keys_count = len(
            [k for k in api_keys if k.expires_at is None or k.expires_at > now]
        )

        return OrganizationAdminResponse(
            id=str(org_dto.id),
            name=org_dto.name,
            slug=org_dto.slug,
            plan_tier=org_dto.plan_tier,
            is_active=org_dto.is_active,
            member_count=org_dto.member_count,
            total_scans_count=0,
            total_findings_count=0,
            active_api_keys_count=active_api_keys_count,
            created_at=org_dto.created_at.isoformat(),
            updated_at=org_dto.updated_at.isoformat(),
        )

    async def update_organization_profile(
        self,
        organization_id: UUID,
        req: UpdateOrganizationAdminRequest,
        current_user: UserModel,
    ) -> OrganizationAdminResponse:
        """Update organization metadata with audit logging."""
        update_req = UpdateOrganizationRequest(
            name=req.name,
            plan_tier=req.plan_tier,
        )
        await self.org_service.update_organization(
            organization_id, update_req, current_user
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="organization.updated",
            resource_type="organization",
            resource_id=str(organization_id),
            actor_user_id=current_user.id,
            details={"name": req.name, "plan_tier": req.plan_tier},
        )

        return await self.get_organization_details(organization_id)

    # ── Team User Management ──────────────────────────────

    async def list_users(self, organization_id: UUID) -> UserAdminListResponse:
        """List all team members belonging to the organization."""
        users_list_dto = await self.user_service.list_organization_users(
            organization_id
        )
        admin_items = [
            UserAdminItemDTO(
                id=str(u.id),
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                is_active=u.is_active,
                is_mfa_enabled=u.is_mfa_enabled,
                created_at=u.created_at.isoformat(),
            )
            for u in users_list_dto.users
        ]
        return UserAdminListResponse(
            total_count=len(admin_items),
            users=admin_items,
        )

    async def invite_user(
        self,
        organization_id: UUID,
        req: InviteUserAdminRequest,
        current_user: UserModel,
    ) -> UserAdminItemDTO:
        """Invite a new team member to the organization."""
        user_req = InviteUserRequest(
            email=req.email,
            full_name=req.full_name,
            password=f"TempPass-{uuid4().hex[:8]}!",
            role=req.role,
        )
        created_user_dto = await self.user_service.invite_user(user_req, current_user)

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="user.invited",
            resource_type="user",
            resource_id=str(created_user_dto.id),
            actor_user_id=current_user.id,
            details={"email": req.email, "role": req.role},
        )

        return UserAdminItemDTO(
            id=str(created_user_dto.id),
            email=created_user_dto.email,
            full_name=created_user_dto.full_name,
            role=created_user_dto.role,
            is_active=created_user_dto.is_active,
            is_mfa_enabled=created_user_dto.is_mfa_enabled,
            created_at=created_user_dto.created_at.isoformat(),
        )

    async def update_user_role(
        self,
        organization_id: UUID,
        target_user_id: UUID,
        req: UpdateUserRoleAdminRequest,
        current_user: UserModel,
    ) -> UserAdminItemDTO:
        """Update a team member's RBAC role enforcing sole owner demotion protection."""
        target_user = await self.user_repo.get_by_id_and_org(
            target_user_id, organization_id
        )
        if not target_user:
            raise ResourceNotFoundException(f"User {target_user_id} not found.")

        # Sole owner demotion check
        if target_user.role == "OWNER" and req.role != "OWNER":
            org_users = await self.user_repo.list_by_organization(organization_id)
            owners_count = len(
                [u for u in org_users if u.role == "OWNER" and u.is_active]
            )
            if owners_count <= 1:
                raise ValidationException(
                    "Cannot demote the sole organization OWNER. Assign another OWNER first."
                )

        role_req = UpdateUserRoleRequest(role=req.role)
        updated_dto = await self.user_service.update_user_role(
            target_user_id, role_req, current_user
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="user.role_updated",
            resource_type="user",
            resource_id=str(target_user_id),
            actor_user_id=current_user.id,
            details={"previous_role": target_user.role, "new_role": req.role},
        )

        return UserAdminItemDTO(
            id=str(updated_dto.id),
            email=updated_dto.email,
            full_name=updated_dto.full_name,
            role=updated_dto.role,
            is_active=updated_dto.is_active,
            is_mfa_enabled=updated_dto.is_mfa_enabled,
            created_at=updated_dto.created_at.isoformat(),
        )

    async def deactivate_user(
        self,
        organization_id: UUID,
        target_user_id: UUID,
        current_user: UserModel,
    ) -> UserAdminItemDTO:
        """Deactivate a team member account enforcing self-deactivation & sole-owner protection."""
        if target_user_id == current_user.id:
            raise ForbiddenException("You cannot deactivate your own account.")

        target_user = await self.user_repo.get_by_id_and_org(
            target_user_id, organization_id
        )
        if not target_user:
            raise ResourceNotFoundException(f"User {target_user_id} not found.")

        if target_user.role == "OWNER":
            org_users = await self.user_repo.list_by_organization(organization_id)
            owners_count = len(
                [u for u in org_users if u.role == "OWNER" and u.is_active]
            )
            if owners_count <= 1:
                raise ValidationException(
                    "Cannot deactivate the sole organization OWNER."
                )

        status_req = UpdateUserStatusRequest(is_active=False)
        deactivated_dto = await self.user_service.update_user_status(
            target_user_id, status_req, current_user
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="user.deactivated",
            resource_type="user",
            resource_id=str(target_user_id),
            actor_user_id=current_user.id,
            details={"email": target_user.email},
        )

        return UserAdminItemDTO(
            id=str(deactivated_dto.id),
            email=deactivated_dto.email,
            full_name=deactivated_dto.full_name,
            role=deactivated_dto.role,
            is_active=deactivated_dto.is_active,
            is_mfa_enabled=deactivated_dto.is_mfa_enabled,
            created_at=deactivated_dto.created_at.isoformat(),
        )

    # ── RBAC Role-Permission Matrix ────────────────────────

    async def get_role_permission_matrix(self) -> RolePermissionMatrixResponse:
        """Construct role permission boundary matrix comparing all 4 roles."""
        role_definitions = [
            RolePermissionBoundaryDTO(
                role_name="OWNER",
                role_level=Role.OWNER.value,
                description="Full organization ownership, billing management, deletion, and role assignment.",
                granted_permissions=[
                    p
                    for p, min_r in PERMISSION_MAP.items()
                    if Role.OWNER
                    >= (min_r if isinstance(min_r, Role) else parse_role(str(min_r)))
                ],
            ),
            RolePermissionBoundaryDTO(
                role_name="ADMIN",
                role_level=Role.ADMIN.value,
                description="Administrative control over team users, scan profiles, integration API keys, and worker nodes.",
                granted_permissions=[
                    p
                    for p, min_r in PERMISSION_MAP.items()
                    if Role.ADMIN
                    >= (min_r if isinstance(min_r, Role) else parse_role(str(min_r)))
                ],
            ),
            RolePermissionBoundaryDTO(
                role_name="SECURITY_ANALYST",
                role_level=Role.SECURITY_ANALYST.value,
                description="Security analyst workflow — launch scans, triage findings, trigger AI analysis, export reports.",
                granted_permissions=[
                    p
                    for p, min_r in PERMISSION_MAP.items()
                    if Role.SECURITY_ANALYST
                    >= (min_r if isinstance(min_r, Role) else parse_role(str(min_r)))
                ],
            ),
            RolePermissionBoundaryDTO(
                role_name="VIEWER",
                role_level=Role.VIEWER.value,
                description="Read-only access to security posture dashboards, scan status, and high-level reports.",
                granted_permissions=[
                    p
                    for p, min_r in PERMISSION_MAP.items()
                    if Role.VIEWER
                    >= (min_r if isinstance(min_r, Role) else parse_role(str(min_r)))
                ],
            ),
        ]

        permission_items = [
            PermissionBoundaryDTO(
                permission_key=perm_key,
                description=PERMISSION_DESCRIPTIONS.get(
                    perm_key, perm_key.replace(":", " ").title()
                ),
                minimum_role=(
                    min_role.name if isinstance(min_role, Role) else str(min_role)
                ),
            )
            for perm_key, min_role in PERMISSION_MAP.items()
        ]

        return RolePermissionMatrixResponse(
            roles=role_definitions,
            permissions=permission_items,
        )

    # ── API Key Governance ────────────────────────────────

    async def list_organization_api_keys(
        self, organization_id: UUID
    ) -> APIKeyAdminListResponse:
        """List active integration API keys for the organization."""
        keys = await self.api_key_repo.list_by_organization(organization_id)
        now = datetime.now(timezone.utc)
        admin_keys = [
            APIKeyAdminItemDTO(
                id=str(k.id),
                name=k.name,
                key_prefix=k.key_prefix,
                scopes=k.scopes or [],
                created_by_user_id=str(k.user_id) if k.user_id else None,
                created_at=k.created_at.isoformat(),
                expires_at=k.expires_at.isoformat() if k.expires_at else None,
                last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
                is_active=k.expires_at is None or k.expires_at > now,
            )
            for k in keys
            if k.expires_at is None or k.expires_at > now
        ]
        return APIKeyAdminListResponse(
            total_count=len(admin_keys),
            api_keys=admin_keys,
        )

    async def list_api_keys(self, organization_id: UUID) -> APIKeyAdminListResponse:
        """Alias for list_organization_api_keys."""
        return await self.list_organization_api_keys(organization_id)

    async def create_api_key(
        self,
        organization_id: UUID,
        req: CreateAPIKeyAdminRequest,
        current_user: UserModel,
    ) -> CreateAPIKeyAdminResponse:
        """Generate a new integration API key with raw key returned ONCE."""
        create_req = CreateAPIKeyRequest(
            name=req.name,
            scopes=req.scopes,
            expires_in_days=req.expires_in_days,
        )
        created_dto = await self.api_key_service.create_api_key(
            create_req, current_user
        )

        # Record detailed audit log event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="api_key.created",
            resource_type="api_key",
            resource_id=str(created_dto.id),
            actor_user_id=current_user.id,
            details={
                "name": req.name,
                "key_prefix": created_dto.key_prefix,
                "scopes": req.scopes,
                "expires_at": (
                    created_dto.expires_at.isoformat()
                    if created_dto.expires_at
                    else None
                ),
            },
        )

        return CreateAPIKeyAdminResponse(
            id=str(created_dto.id),
            name=created_dto.name,
            raw_api_key=created_dto.raw_key,
            key_prefix=created_dto.key_prefix,
            scopes=created_dto.scopes or [],
            created_at=created_dto.created_at.isoformat(),
            expires_at=(
                created_dto.expires_at.isoformat() if created_dto.expires_at else None
            ),
        )

    async def revoke_api_key(
        self,
        organization_id: UUID,
        key_id: UUID,
        current_user: UserModel,
    ) -> bool:
        """Revoke an integration API key with detailed audit event logging."""
        await self.api_key_service.revoke_api_key(
            key_id, organization_id, current_user.id
        )

        # Record detailed audit log event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=str(key_id),
            actor_user_id=current_user.id,
            details={"api_key_id": str(key_id)},
        )

        return True

    # ── Security & MFA Overview ───────────────────────────

    async def get_security_overview(
        self, organization_id: UUID
    ) -> SecurityOverviewAdminResponse:
        """Fetch security configuration and MFA enrollment status visibility."""
        users = await self.user_repo.list_by_organization(organization_id)
        total_users = len(users)
        mfa_count = len([u for u in users if u.is_mfa_enabled])

        now_str = datetime.now(timezone.utc).isoformat()

        return SecurityOverviewAdminResponse(
            organization_id=str(organization_id),
            total_users_count=total_users,
            mfa_enrolled_count=mfa_count,
            mfa_enforcement_status="OPTIONAL",
            session_security_policy="STRICT_JWT_DUAL_TOKEN",
            audit_logging_enabled=True,
            last_security_audit_at=now_str,
        )
