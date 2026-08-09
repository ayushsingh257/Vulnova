"""FastAPI REST Router for Phase 12.7 Cryptographically Signed & Sandboxed Plugin Ecosystem."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.infrastructure.plugin_security.capability_service import (
    PluginCapabilityService,
)
from app.infrastructure.plugin_security.dto import (
    PluginExecutionRequestDTO,
    PluginExecutionResultDTO,
    PluginManifestDTO,
    PluginSecurityReportDTO,
    PluginSignatureVerificationResultDTO,
    RegisterPublisherRequestDTO,
    TrustedPublisherDTO,
)
from app.infrastructure.plugin_security.runner_service import PluginRunnerService
from app.infrastructure.plugin_security.security_report_service import (
    PluginSecurityReportService,
)
from app.infrastructure.plugin_security.signature_service import (
    PluginSignatureService,
)
from app.infrastructure.plugin_security.trust_service import (
    PluginTrustService,
)

router = APIRouter(
    prefix="/plugins",
    tags=["Cryptographically Signed & Sandboxed Plugin Ecosystem Architecture"],
)


class VerifyPluginRequest(BaseModel):
    """Payload for plugin cryptographic verification."""

    manifest: PluginManifestDTO
    signature_hex: str = Field(..., description="Ed25519 signature in hex format")


@router.post(
    "/{id}/verify",
    response_model=PluginSignatureVerificationResultDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("plugins:manage"))],
)
async def verify_plugin_signature(
    id: str,
    payload: VerifyPluginRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PluginSignatureVerificationResultDTO:
    """Verify cryptographic Ed25519 signature and capability manifest for a security plugin.

    Requires 'plugins:manage' permission.
    """
    manifest = payload.manifest
    manifest.plugin_id = id
    sig_service = PluginSignatureService(session)
    cap_service = PluginCapabilityService(session)

    # 1. Verify signature against trusted publisher registry
    verification_result = await sig_service.verify_plugin_signature(
        manifest=manifest,
        signature_hex=payload.signature_hex,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )

    # 2. If valid, register manifest
    if verification_result.is_valid:
        await cap_service.register_manifest(
            manifest=manifest,
            organization_id=current_user.organization_id,
            actor_user_id=current_user.id,
        )

    await session.commit()
    return verification_result


@router.get(
    "/trusted",
    response_model=List[TrustedPublisherDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("plugins:read"))],
)
async def list_trusted_publishers(
    status: Optional[str] = Query(
        None, description="Filter by trust status (TRUSTED, REVOKED, PENDING)"
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[TrustedPublisherDTO]:
    """List trusted plugin publishers and public key fingerprints.

    Requires 'plugins:read' permission.
    """
    trust_service = PluginTrustService(session)
    publishers = await trust_service.list_trusted_publishers(
        organization_id=current_user.organization_id,
        status=status,
    )
    return publishers


@router.post(
    "/trust",
    response_model=TrustedPublisherDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("plugins:manage"))],
)
async def register_trusted_publisher(
    payload: RegisterPublisherRequestDTO,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> TrustedPublisherDTO:
    """Register a new trusted publisher with Ed25519 public key.

    Requires 'plugins:manage' permission.
    """
    trust_service = PluginTrustService(session)
    publisher = await trust_service.register_trusted_publisher(
        req=payload,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return publisher


@router.delete(
    "/trust/{id}",
    response_model=TrustedPublisherDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("plugins:manage"))],
)
async def revoke_trusted_publisher(
    id: str,
    reason: str = Query(
        "Revoked by security administrator", description="Revocation reason"
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> TrustedPublisherDTO:
    """Revoke trust for a plugin publisher by publisher_id.

    Requires 'plugins:manage' permission.
    """
    trust_service = PluginTrustService(session)
    publisher = await trust_service.revoke_publisher(
        publisher_id=id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        reason=reason,
    )
    await session.commit()
    return publisher


@router.post(
    "/{id}/execute",
    response_model=PluginExecutionResultDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:run"))],
)
async def execute_sandboxed_plugin(
    id: str,
    payload: PluginExecutionRequestDTO,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PluginExecutionResultDTO:
    """Execute a cryptographically verified security plugin in an isolated sandbox.

    Requires 'scans:run' permission.
    """
    payload.plugin_id = id
    runner_service = PluginRunnerService(session)
    result = await runner_service.execute_plugin(
        req=payload,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )
    await session.commit()
    return result


@router.get(
    "/{id}/security-report",
    response_model=PluginSecurityReportDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("plugins:read"))],
)
async def get_plugin_security_report(
    id: str,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> PluginSecurityReportDTO:
    """Generate zero-trust security audit report for a registered plugin.

    Requires 'plugins:read' permission.
    """
    report_service = PluginSecurityReportService(session)
    report = await report_service.generate_security_report(
        plugin_id=id,
        organization_id=current_user.organization_id,
    )
    return report
