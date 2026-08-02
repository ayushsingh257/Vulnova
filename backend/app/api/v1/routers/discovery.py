"""FastAPI Router for Discovery Engine & Asset Surface Mapping (/api/v1/discovery)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.discovery.dto import (
    CrawlRequest,
    CrawlResponse,
    SubdomainScanRequest,
    SubdomainScanResponse,
)
from app.application.discovery.services import DiscoveryService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/discovery", tags=["Asset Discovery & Surface Mapping"])


@router.post(
    "/crawl",
    response_model=CrawlResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:create"))],
)
async def crawl_target(
    req: CrawlRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> CrawlResponse:
    """Execute an async web crawl job on an explicitly approved target URL.

    Requires authentication (Bearer JWT or X-API-Key), 'targets:create' RBAC permission,
    and valid organization context. Enforces SSRF egress filtering and domain scope boundaries.
    """
    service = DiscoveryService(session)
    return await service.crawl_target(req, current_user)


@router.post(
    "/subdomains",
    response_model=SubdomainScanResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:create"))],
)
async def discover_subdomains(
    req: SubdomainScanRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SubdomainScanResponse:
    """Execute a Subdomain & DNS Intelligence discovery scan on a target domain.

    Queries Certificate Transparency (CT) logs and resolves A, AAAA, CNAME, MX, NS, and TXT DNS records.
    Classifies IP findings into PUBLIC, PRIVATE, LOOPBACK for enterprise ASM intelligence.
    Requires authentication and 'targets:create' RBAC permission.
    """
    service = DiscoveryService(session)
    return await service.discover_subdomains(req, current_user)
