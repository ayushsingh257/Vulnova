"""FastAPI Router for Phase 6.2 Scan Target Registration & Management (/api/v1/scan-targets)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dto import (
    ScanTargetCreateRequest,
    ScanTargetResponse,
    ScanTargetUpdateRequest,
)
from app.core.exceptions import ResourceNotFoundException
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.database.session import get_async_session
from app.infrastructure.discovery.ssrf_validator import is_safe_target_url

router = APIRouter(tags=["Scan Target Management"])


def _map_target_to_response(
    model: object,
) -> ScanTargetResponse:
    """Map ScanTargetModel ORM instance to ScanTargetResponse DTO."""
    return ScanTargetResponse(
        id=str(model.id),  # type: ignore[attr-defined]
        organization_id=str(model.organization_id),  # type: ignore[attr-defined]
        name=model.name,  # type: ignore[attr-defined]
        target_url=model.target_url,  # type: ignore[attr-defined]
        environment=model.environment,  # type: ignore[attr-defined]
        status=model.status,  # type: ignore[attr-defined]
        is_ownership_verified=model.is_ownership_verified,  # type: ignore[attr-defined]
        ownership_verification_token=model.ownership_verification_token,  # type: ignore[attr-defined]
        created_by=str(model.created_by) if model.created_by else None,  # type: ignore[attr-defined]
        created_at=model.created_at.isoformat() if model.created_at else "",  # type: ignore[attr-defined]
        updated_at=model.updated_at.isoformat() if model.updated_at else None,  # type: ignore[attr-defined]
    )


@router.post(
    "",
    response_model=ScanTargetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("targets:create"))],
)
async def create_scan_target(
    req: ScanTargetCreateRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanTargetResponse:
    """Register a new scan target for the authenticated organization.

    Requires authentication and 'targets:create' RBAC permission.
    Generates an ownership verification token automatically.
    """
    target_url = str(req.target_url).rstrip("/")

    # Validate SSRF safety before registration
    is_safe, reason = is_safe_target_url(target_url)
    if is_safe is False:
        from app.core.exceptions import ValidationException

        raise ValidationException(f"Target URL is prohibited: {reason}")

    repo = ScanTargetRepository(session)
    model = await repo.create_target(
        organization_id=current_user.organization_id,
        name=req.name,
        target_url=target_url,
        environment=req.environment,
        created_by=current_user.id,
    )
    await session.commit()
    return _map_target_to_response(model)


@router.get(
    "",
    response_model=List[ScanTargetResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:read"))],
)
async def list_scan_targets(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Optional status filter: ACTIVE, ARCHIVED, SUSPENDED",
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[ScanTargetResponse]:
    """List all registered scan targets for the authenticated organization.

    Requires authentication and 'targets:read' RBAC permission.
    """
    repo = ScanTargetRepository(session)
    targets = await repo.list_targets(
        organization_id=current_user.organization_id,
        status=status_filter,
    )
    return [_map_target_to_response(t) for t in targets]


@router.get(
    "/{target_id}",
    response_model=ScanTargetResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:read"))],
)
async def get_scan_target(
    target_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanTargetResponse:
    """Retrieve details of a specific registered scan target.

    Requires authentication and 'targets:read' RBAC permission. Enforces multi-tenant isolation.
    """
    repo = ScanTargetRepository(session)
    model = await repo.get_target_by_id(
        organization_id=current_user.organization_id,
        target_id=target_id,
    )
    if model is None:
        raise ResourceNotFoundException(
            f"Scan target '{target_id}' not found in your organization."
        )
    return _map_target_to_response(model)


@router.put(
    "/{target_id}",
    response_model=ScanTargetResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:update"))],
)
async def update_scan_target(
    target_id: UUID,
    req: ScanTargetUpdateRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanTargetResponse:
    """Update properties of a registered scan target.

    Requires authentication and 'targets:update' RBAC permission.
    """
    repo = ScanTargetRepository(session)
    model = await repo.update_target(
        organization_id=current_user.organization_id,
        target_id=target_id,
        name=req.name,
        environment=req.environment,
        status=req.status,
    )
    if model is None:
        raise ResourceNotFoundException(
            f"Scan target '{target_id}' not found in your organization."
        )
    await session.commit()
    return _map_target_to_response(model)


@router.delete(
    "/{target_id}",
    response_model=ScanTargetResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:delete"))],
)
async def archive_scan_target(
    target_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanTargetResponse:
    """Archive (soft-delete) a registered scan target.

    Sets target status to ARCHIVED. Archived targets cannot be used for new scans.
    Requires authentication and 'targets:delete' RBAC permission.
    """
    repo = ScanTargetRepository(session)
    model = await repo.archive_target(
        organization_id=current_user.organization_id,
        target_id=target_id,
    )
    if model is None:
        raise ResourceNotFoundException(
            f"Scan target '{target_id}' not found in your organization."
        )
    await session.commit()
    return _map_target_to_response(model)
