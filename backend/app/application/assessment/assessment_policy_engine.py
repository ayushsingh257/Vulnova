"""Assessment Policy Engine enforcing mandatory authorization, target registration, and scope policy checks.

Phase 6.2: This service acts as the pre-scan authorization gate. No vulnerability
assessment can execute without passing all validation checks defined here.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import PolicyValidationResult
from app.application.audit_logs.services import AuditLogService
from app.core.logging import get_logger
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.discovery.ssrf_validator import is_safe_target_url

logger = get_logger("vulnova.assessment_policy_engine")


class AssessmentPolicyEngine:
    """Enforces mandatory authorization, target registration, and scope policy checks before scan execution.

    Validation Chain:
        1. ``is_authorized_assessment`` must be ``True`` (hard reject).
        2. Target URL must be registered in ``scan_targets`` for the requesting organization.
        3. Registered target must have ``status == ACTIVE`` (not ``ARCHIVED`` / ``SUSPENDED``).
        4. Target URL must pass SSRF egress safety validation.
        5. Authorization declaration is persisted as an immutable audit record.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scan_target_repo = ScanTargetRepository(session)
        self.audit_service = AuditLogService(session)

    async def validate_scan_authorization(
        self,
        organization_id: UUID,
        target_url: str,
        is_authorized_assessment: bool,
        declared_by: UUID,
        authorization_scope: str = "full",
        ip_address: Optional[str] = None,
    ) -> PolicyValidationResult:
        """Gate function performing all pre-scan authorization checks.

        Returns:
            PolicyValidationResult with ``is_allowed=True`` if all checks pass,
            or ``is_allowed=False`` with a descriptive ``rejection_reason``.
        """
        normalized_url = target_url.strip().rstrip("/")

        # ── Check 1: Mandatory legal authorization declaration ──
        if not is_authorized_assessment:
            logger.warning(
                "assessment_policy.authorization_rejected",
                reason="is_authorized_assessment is False",
                org_id=str(organization_id),
                target_url=normalized_url,
            )
            await self.audit_service.record_event(
                organization_id=organization_id,
                action="scan.authorization_rejected",
                resource_type="scan_target",
                resource_id=normalized_url,
                actor_user_id=declared_by,
                details={
                    "reason": "User did not confirm authorized assessment consent",
                    "target_url": normalized_url,
                },
            )
            return PolicyValidationResult(
                is_allowed=False,
                rejection_reason="Authorized security assessment consent is required. Set is_authorized_assessment to true.",
            )

        # ── Check 2: Target must be registered in scan_targets ──
        scan_target = await self.scan_target_repo.get_target_by_url(
            organization_id=organization_id, target_url=normalized_url
        )
        if scan_target is None:
            logger.warning(
                "assessment_policy.unregistered_target",
                org_id=str(organization_id),
                target_url=normalized_url,
            )
            await self.audit_service.record_event(
                organization_id=organization_id,
                action="scan.unregistered_target_rejected",
                resource_type="scan_target",
                resource_id=normalized_url,
                actor_user_id=declared_by,
                details={
                    "reason": "Target URL is not registered",
                    "target_url": normalized_url,
                },
            )
            return PolicyValidationResult(
                is_allowed=False,
                rejection_reason=f"Target URL '{normalized_url}' is not registered. Register it via POST /api/v1/scan-targets first.",
            )

        # ── Check 3: Target must be ACTIVE ──
        if scan_target.status != "ACTIVE":
            logger.warning(
                "assessment_policy.inactive_target",
                org_id=str(organization_id),
                target_id=str(scan_target.id),
                status=scan_target.status,
            )
            return PolicyValidationResult(
                is_allowed=False,
                rejection_reason=f"Scan target is {scan_target.status}. Only ACTIVE targets can be scanned.",
                scan_target_id=str(scan_target.id),
            )

        # ── Check 3.5: Target Ownership Verification ──
        if not scan_target.is_ownership_verified:
            logger.warning(
                "assessment_policy.unverified_target_rejected",
                org_id=str(organization_id),
                target_id=str(scan_target.id),
                target_url=normalized_url,
            )
            await self.audit_service.record_event(
                organization_id=organization_id,
                action="scan_blocked.unverified_target",
                resource_type="scan_target",
                resource_id=str(scan_target.id),
                actor_user_id=declared_by,
                details={
                    "reason": "Target ownership verification required before scanning",
                    "target_url": normalized_url,
                },
            )
            return PolicyValidationResult(
                is_allowed=False,
                rejection_reason="Target ownership verification required before scanning. Verify ownership via DNS TXT or HTTP challenge first.",
                scan_target_id=str(scan_target.id),
            )

        # ── Check 4: SSRF egress safety ──
        is_safe, ssrf_reason = is_safe_target_url(normalized_url)
        if not is_safe:
            logger.warning(
                "assessment_policy.ssrf_rejected",
                org_id=str(organization_id),
                target_url=normalized_url,
                reason=ssrf_reason,
            )
            return PolicyValidationResult(
                is_allowed=False,
                rejection_reason=f"Target URL is prohibited by SSRF egress firewall: {ssrf_reason}",
                scan_target_id=str(scan_target.id),
            )

        # ── Check 5: Record authorization declaration ──
        declaration = await self.scan_target_repo.record_authorization_declaration(
            organization_id=organization_id,
            scan_target_id=scan_target.id,
            declared_by=declared_by,
            is_authorized=True,
            authorization_scope=authorization_scope,
            ip_address=ip_address,
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="scan.authorized",
            resource_type="scan_target",
            resource_id=str(scan_target.id),
            actor_user_id=declared_by,
            details={
                "target_url": normalized_url,
                "authorization_scope": authorization_scope,
                "declaration_id": str(declaration.id),
            },
        )

        logger.info(
            "assessment_policy.scan_authorized",
            org_id=str(organization_id),
            target_id=str(scan_target.id),
            declared_by=str(declared_by),
            authorization_scope=authorization_scope,
        )

        return PolicyValidationResult(
            is_allowed=True,
            scan_target_id=str(scan_target.id),
            authorization_id=str(declaration.id),
        )
