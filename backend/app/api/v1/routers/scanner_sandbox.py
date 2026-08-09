"""FastAPI Router for Enterprise Scanner Sandbox Infrastructure."""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.infrastructure.scanner_sandbox.dto import (
    SandboxCreationRequestDTO,
    SandboxExecutionResultDTO,
    ScannerSandboxDTO,
)
from app.infrastructure.scanner_sandbox.sandbox_manager import (
    ScannerSandboxManager,
)

router = APIRouter(prefix="/sandbox", tags=["Scanner Sandbox Execution Isolation"])


@router.post(
    "/run",
    response_model=SandboxExecutionResultDTO,
    status_code=status.HTTP_200_OK,
    summary="Execute Sandboxed Scanner Job",
    description="Orchestrate single-use ephemeral container sandbox for isolated vulnerability scan execution.",
)
async def run_sandboxed_scan(
    request: SandboxCreationRequestDTO,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(require_permission("scan:execute")),
) -> SandboxExecutionResultDTO:
    """Trigger an isolated scan job execution inside a single-use container sandbox."""
    if request.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot execute scan outside of current user organization boundary.",
        )

    manager = ScannerSandboxManager(session)
    return await manager.execute_sandboxed_scan(
        request=request, actor_user_id=current_user.id
    )


@router.get(
    "/status/{sandbox_id}",
    response_model=ScannerSandboxDTO,
    summary="Get Sandbox Status & Lifecycle",
    description="Fetch execution status, security limits, and lifecycle timestamps for a scanner sandbox.",
)
async def get_sandbox_status(
    sandbox_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(require_permission("scan:read")),
) -> ScannerSandboxDTO:
    """Fetch status of a specific scanner sandbox."""
    manager = ScannerSandboxManager(session)
    sandbox = await manager.get_sandbox(
        sandbox_id=sandbox_id, organization_id=current_user.organization_id
    )
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scanner sandbox {sandbox_id} not found.",
        )
    return sandbox


@router.get(
    "/active",
    summary="List Organization Scanner Sandboxes",
    description="List active and historical scanner sandboxes for current tenant organization.",
)
async def list_sandboxes(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by sandbox status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(require_permission("scan:read")),
) -> Dict[str, Any]:
    """List sandboxes with optional status filtering and pagination."""
    manager = ScannerSandboxManager(session)
    sandboxes, total = await manager.list_sandboxes(
        organization_id=current_user.organization_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [s.model_dump(mode="json") for s in sandboxes],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete(
    "/{sandbox_id}",
    status_code=status.HTTP_200_OK,
    summary="Force Destroy Scanner Sandbox",
    description="Force terminate and cleanup a running or dangling ephemeral container sandbox.",
)
async def force_destroy_sandbox(
    sandbox_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(require_permission("admin:manage")),
) -> Dict[str, Any]:
    """Force destroy an ephemeral scanner sandbox container."""
    manager = ScannerSandboxManager(session)
    success = await manager.force_destroy_sandbox(
        sandbox_id=sandbox_id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scanner sandbox {sandbox_id} not found or destroy failed.",
        )
    return {"message": f"Scanner sandbox {sandbox_id} destroyed successfully."}
