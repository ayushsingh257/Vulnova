"""FastAPI Router for Public Enterprise Trust Center & Security Disclosures."""

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    SecurityDisclosureResponse,
    TrustCenterSummaryResponse,
)
from app.application.assessment.trust_center_service import TrustCenterService
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/public", tags=["Public Trust Center & Disclosures"])


def get_trust_center_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TrustCenterService:
    """Dependency injector for TrustCenterService."""
    return TrustCenterService(session=session)


@router.get(
    "/trust",
    response_model=TrustCenterSummaryResponse,
    summary="Retrieve Public Enterprise Trust Center Overview",
    description="Returns public platform security controls, OWASP ASVS v4.0 mappings, encryption specifications, and operational uptime status.",
)
async def get_public_trust_center(
    service: Annotated[TrustCenterService, Depends(get_trust_center_service)],
) -> TrustCenterSummaryResponse:
    """Unauthenticated public endpoint returning platform Trust Center summary."""
    return await service.get_public_trust_center_summary()


@router.get(
    "/status",
    summary="Retrieve Public Operational Health Status",
    description="Returns high-level system operational status (OPERATIONAL, DEGRADED_PERFORMANCE, UNDER_MAINTENANCE).",
)
async def get_public_system_status(
    service: Annotated[TrustCenterService, Depends(get_trust_center_service)],
) -> Dict[str, Any]:
    """Unauthenticated public operational health endpoint."""
    status = await service.get_system_health_status()
    return {"system_status": status.value, "platform": "Vulnova Enterprise"}


@router.get(
    "/security-disclosure",
    response_model=SecurityDisclosureResponse,
    summary="Retrieve Vulnerability Disclosure Policy Details",
    description="Returns RFC 9116 security contact email, PGP encryption key, and disclosure policy metadata.",
)
async def get_security_disclosure_policy(
    service: Annotated[TrustCenterService, Depends(get_trust_center_service)],
) -> SecurityDisclosureResponse:
    """Unauthenticated public endpoint returning vulnerability disclosure policy."""
    return service.get_security_disclosure_info()


@router.get(
    "/security.txt",
    response_class=Response,
    summary="RFC 9116 Security Disclosure Directive",
    description="Returns RFC 9116 plain text security.txt directive for security researchers.",
)
async def get_security_txt_endpoint(
    service: Annotated[TrustCenterService, Depends(get_trust_center_service)],
) -> Response:
    """Return plain text RFC 9116 security.txt."""
    content = service.get_security_txt_content()
    return Response(content=content, media_type="text/plain; charset=utf-8")
