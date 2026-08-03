"""FastAPI Router for Enterprise Asset Inventory & Posture Intelligence (/api/v1/assets)."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.asset_inventory_service import AssetInventoryService
from app.application.assessment.dto import (
    AssetDetailResponse,
    AssetInventoryResponse,
    FindingDTO,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(tags=["Enterprise Asset Inventory & Posture Intelligence"])


@router.get(
    "/assets/inventory",
    response_model=AssetInventoryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("assets:read"))],
)
async def list_asset_inventory(
    node_type: Optional[str] = Query(
        None,
        description="Optional node type filter (TARGET_DOMAIN, SUBDOMAIN, IP_ADDRESS, URL_ENDPOINT)",
    ),
    min_risk_score: Optional[float] = Query(
        None,
        description="Optional minimum composite risk score threshold (0.0 to 100.0)",
    ),
    search: Optional[str] = Query(
        None, description="Optional search term matching asset name or value"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssetInventoryResponse:
    """List tenant asset inventory with composite risk posture, severity breakdowns, and running technologies.

    Requires authentication and 'assets:read' RBAC permission.
    """
    service = AssetInventoryService(session)
    return await service.list_asset_inventory(
        current_user=current_user,
        node_type=node_type,
        min_risk_score=min_risk_score,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/assets/{asset_id}",
    response_model=AssetDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("assets:read"))],
)
async def get_asset_detail(
    asset_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssetDetailResponse:
    """Retrieve detailed inventory posture summary for a specific asset node.

    Requires authentication and 'assets:read' RBAC permission.
    """
    service = AssetInventoryService(session)
    return await service.get_asset_detail(current_user, asset_id)


@router.get(
    "/assets/{asset_id}/findings",
    response_model=List[FindingDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def get_asset_findings(
    asset_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[FindingDTO]:
    """List all security findings affecting a specific asset node.

    Requires authentication and 'findings:read' RBAC permission.
    """
    service = AssetInventoryService(session)
    return await service.get_asset_findings(current_user, asset_id)


@router.get(
    "/assets/{asset_id}/technologies",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("assets:read"))],
)
async def get_asset_technologies(
    asset_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[Dict[str, Any]]:
    """List all technology components running on a specific asset node.

    Requires authentication and 'assets:read' RBAC permission.
    """
    service = AssetInventoryService(session)
    return await service.get_asset_technologies(current_user, asset_id)
