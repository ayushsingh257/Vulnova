"""FastAPI Router for Discovery Engine & Asset Surface Mapping (/api/v1/discovery)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.discovery.asset_graph_service import AssetGraphService
from app.application.discovery.dto import (
    AssetGraphResponse,
    AssetNodeDTO,
    BuildAssetGraphRequest,
    CrawlRequest,
    CrawlResponse,
    SubdomainScanRequest,
    SubdomainScanResponse,
    TechnologyScanRequest,
    TechnologyScanResponse,
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


@router.post(
    "/technology-scan",
    response_model=TechnologyScanResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:create"))],
)
async def discover_technologies(
    req: TechnologyScanRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> TechnologyScanResponse:
    """Execute a Technology Stack Fingerprinting scan on a target web asset.

    Identifies web servers, frontend frameworks, backend frameworks, CMS platforms,
    and audits security header compliance. Requires authentication and 'targets:create' RBAC permission.
    """
    service = DiscoveryService(session)
    return await service.discover_technologies(req, current_user)


@router.post(
    "/asset-graph/build",
    response_model=AssetGraphResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:create"))],
)
async def build_asset_graph(
    req: BuildAssetGraphRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssetGraphResponse:
    """Build or update Attack Surface Asset Graph for a target domain.

    Correlates subdomains, DNS records, IP classifications, crawling endpoints, and technology stack
    fingerprints into a tenant-isolated asset graph topology.
    Requires authentication and 'targets:create' RBAC permission.
    """
    graph_service = AssetGraphService(session)
    return await graph_service.build_asset_graph(req, current_user)


@router.get(
    "/asset-graph/nodes/{node_id}",
    response_model=AssetNodeDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("targets:read"))],
)
async def get_asset_node_details(
    node_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssetNodeDTO:
    """Retrieve details for a specific asset node in Attack Surface Graph.

    Requires authentication and 'targets:read' RBAC permission. Enforces multi-tenant isolation.
    """
    graph_service = AssetGraphService(session)
    return await graph_service.get_node_details(node_id, current_user)
