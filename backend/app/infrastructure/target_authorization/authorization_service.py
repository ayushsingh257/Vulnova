"""Scan Authorization Engine Service (Phase 12.5).

Pre-scan authorization pipeline enforcing target ownership verification,
RFC1918 private network blocklists, cloud metadata prevention, and admin approval workflows.
"""

from ipaddress import ip_address, ip_network
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.repositories.scan_approval_repository import (
    ScanApprovalRepository,
)
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.discovery.ssrf_validator import is_safe_target_url
from app.infrastructure.target_authorization.dto import (
    ApprovalStatus,
    ScanAuthorizationResultDTO,
)

logger = get_logger("vulnova.scan_authorization_service")


class ScanAuthorizationService:
    """Pre-scan authorization engine validating target verification, abuse prevention, and admin approvals."""

    # RFC1918 Private IP Ranges & Prohibited Networks
    PROHIBITED_SUBNETS = [
        ip_network("10.0.0.0/8"),
        ip_network("172.16.0.0/12"),
        ip_network("192.168.0.0/16"),
        ip_network("127.0.0.0/8"),  # Loopback
        ip_network("169.254.0.0/16"),  # Link-local / Cloud Metadata (169.254.169.254)
        ip_network("0.0.0.0/8"),
    ]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.target_repo = ScanTargetRepository(session)
        self.approval_repo = ScanApprovalRepository(session)
        self.audit_service = AuditLogService(session)

    async def authorize_scan(
        self,
        target_id: UUID,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> ScanAuthorizationResultDTO:
        """Evaluate pre-scan authorization pipeline for a target asset."""
        target = await self.target_repo.get_target_by_id(target_id, organization_id)
        if not target:
            raise ResourceNotFoundException("Scan target not found.")

        target_url = target.target_url

        # ── Pipeline Check 1: Target Ownership Verification ──
        if not target.is_ownership_verified:
            logger.warning(
                "scan_authorization.unverified_target_blocked",
                org_id=str(organization_id),
                target_id=str(target_id),
                target_url=target_url,
            )
            await self.audit_service.record_event(
                organization_id=organization_id,
                action="scan_blocked.unverified_target",
                resource_type="scan_target",
                resource_id=str(target_id),
                actor_user_id=actor_user_id,
                details={
                    "target_url": target_url,
                    "reason": "Target ownership verification required before scanning",
                },
            )
            return ScanAuthorizationResultDTO(
                authorized=False,
                is_verified=False,
                requires_approval=False,
                reason="Target ownership verification required before scanning",
                target_id=target_id,
                target_url=target_url,
            )

        # ── Pipeline Check 2: Private Network & Cloud Metadata Abuse Prevention ──
        is_safe, block_reason = self.validate_target_address_safety(target_url)
        if not is_safe:
            logger.warning(
                "scan_authorization.prohibited_target_blocked",
                org_id=str(organization_id),
                target_id=str(target_id),
                target_url=target_url,
                reason=block_reason,
            )
            await self.audit_service.record_event(
                organization_id=organization_id,
                action="scan_blocked.prohibited_target",
                resource_type="scan_target",
                resource_id=str(target_id),
                actor_user_id=actor_user_id,
                details={"target_url": target_url, "reason": block_reason},
            )
            return ScanAuthorizationResultDTO(
                authorized=False,
                is_verified=True,
                requires_approval=False,
                reason=f"Target scanning blocked: {block_reason}",
                target_id=target_id,
                target_url=target_url,
            )

        # ── Pipeline Check 3: Admin Approval Workflow for Production / Sensitive Assets ──
        if target.environment.upper() == "PRODUCTION":
            approved_request = await self.approval_repo.get_approved_request_for_target(
                target_id=target_id, organization_id=organization_id
            )
            if not approved_request:
                logger.warning(
                    "scan_authorization.production_approval_required",
                    org_id=str(organization_id),
                    target_id=str(target_id),
                )
                await self.audit_service.record_event(
                    organization_id=organization_id,
                    action="scan_blocked.pending_approval",
                    resource_type="scan_target",
                    resource_id=str(target_id),
                    actor_user_id=actor_user_id,
                    details={
                        "target_url": target_url,
                        "reason": "Production target requires admin approval",
                    },
                )
                return ScanAuthorizationResultDTO(
                    authorized=False,
                    is_verified=True,
                    requires_approval=True,
                    approval_status=ApprovalStatus.PENDING_APPROVAL,
                    reason="Production scan target requires admin approval before scanning",
                    target_id=target_id,
                    target_url=target_url,
                )

        # ── Pipeline Check 4: Authorization Success ──
        logger.info(
            "scan_authorization.authorized",
            org_id=str(organization_id),
            target_id=str(target_id),
            target_url=target_url,
        )
        return ScanAuthorizationResultDTO(
            authorized=True,
            is_verified=True,
            requires_approval=False,
            reason="Target ownership verified and scan authorized",
            target_id=target_id,
            target_url=target_url,
        )

    def validate_target_address_safety(self, target_url: str) -> tuple[bool, str]:
        """Validate target URL does not target RFC1918 private networks or cloud metadata."""
        parsed = urlparse(
            target_url if "://" in target_url else f"https://{target_url}"
        )
        host = (parsed.netloc or parsed.path).split(":")[0].strip()

        if not host:
            return False, "Invalid target host address"

        if host.lower() in ("localhost", "127.0.0.1", "0.0.0.0"):  # noqa: S104
            return False, "Scanning localhost or loopback interfaces is prohibited"

        try:
            ip_obj = ip_address(host)
            for subnet in self.PROHIBITED_SUBNETS:
                if ip_obj in subnet:
                    return (
                        False,
                        f"Target IP {host} belongs to prohibited private network {subnet}",
                    )
        except ValueError:
            # Host is a domain name -> Check standard SSRF egress validator
            is_safe, ssrf_reason = is_safe_target_url(target_url)
            if not is_safe:
                return False, f"Prohibited domain target: {ssrf_reason}"

        return True, "Target address is safe"
