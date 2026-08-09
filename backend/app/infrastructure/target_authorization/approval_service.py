"""Scan Approval Request Workflow Service for Sensitive Target Assets (Phase 12.5)."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.infrastructure.database.models.scan_approval_request import (
    ScanApprovalRequestModel,
)
from app.infrastructure.database.repositories.scan_approval_repository import (
    ScanApprovalRepository,
)
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.target_authorization.dto import (
    ApprovalStatus,
    ScanApprovalRequestDTO,
)

logger = get_logger("vulnova.scan_approval_service")


class ScanApprovalService:
    """Service managing admin approval workflows for sensitive asset vulnerability scans."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.approval_repo = ScanApprovalRepository(session)
        self.target_repo = ScanTargetRepository(session)
        self.audit_service = AuditLogService(session)

    async def create_approval_request(
        self,
        organization_id: UUID,
        target_id: UUID,
        requested_by: UUID,
        scan_job_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> ScanApprovalRequestDTO:
        """Create a new scan approval request for a sensitive target asset."""
        target = await self.target_repo.get_target_by_id(target_id, organization_id)
        if not target:
            raise ResourceNotFoundException("Scan target not found.")

        now = datetime.now(timezone.utc)
        request_model = ScanApprovalRequestModel(
            id=uuid4(),
            organization_id=organization_id,
            scan_job_id=scan_job_id,
            target_id=target_id,
            requested_by=requested_by,
            status=ApprovalStatus.PENDING_APPROVAL.value,
            reason=reason
            or f"Scan approval request for sensitive target {target.name}",
            created_at=now,
            updated_at=now,
        )

        saved = await self.approval_repo.create_approval_request(request_model)

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="scan_approval.requested",
            resource_type="scan_target",
            resource_id=str(target_id),
            actor_user_id=requested_by,
            details={
                "request_id": str(saved.id),
                "target_url": target.target_url,
                "reason": reason,
            },
        )

        return self._to_dto(saved)

    async def approve_request(
        self,
        request_id: UUID,
        organization_id: UUID,
        approver_user_id: UUID,
        reason: Optional[str] = None,
    ) -> ScanApprovalRequestDTO:
        """Approve a pending scan authorization request (Admin only)."""
        request = await self.approval_repo.get_approval_request_by_id(
            request_id, organization_id
        )
        if not request:
            raise ResourceNotFoundException("Scan approval request not found.")

        if request.status != ApprovalStatus.PENDING_APPROVAL.value:
            raise ValidationException(
                f"Cannot approve request with status '{request.status}'. Must be PENDING_APPROVAL."
            )

        updated = await self.approval_repo.update_status(
            request_id=request_id,
            status=ApprovalStatus.APPROVED.value,
            approved_by=approver_user_id,
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="scan_approval.granted",
            resource_type="scan_approval_request",
            resource_id=str(request_id),
            actor_user_id=approver_user_id,
            details={
                "target_id": str(request.target_id),
                "approved_by": str(approver_user_id),
                "reason": reason,
            },
        )

        return self._to_dto(updated)  # type: ignore[arg-type]

    async def reject_request(
        self,
        request_id: UUID,
        organization_id: UUID,
        approver_user_id: UUID,
        rejection_reason: str,
    ) -> ScanApprovalRequestDTO:
        """Reject a pending scan authorization request (Admin only)."""
        request = await self.approval_repo.get_approval_request_by_id(
            request_id, organization_id
        )
        if not request:
            raise ResourceNotFoundException("Scan approval request not found.")

        if request.status != ApprovalStatus.PENDING_APPROVAL.value:
            raise ValidationException(
                f"Cannot reject request with status '{request.status}'. Must be PENDING_APPROVAL."
            )

        updated = await self.approval_repo.update_status(
            request_id=request_id,
            status=ApprovalStatus.REJECTED.value,
            approved_by=approver_user_id,
            rejection_reason=rejection_reason,
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="scan_approval.rejected",
            resource_type="scan_approval_request",
            resource_id=str(request_id),
            actor_user_id=approver_user_id,
            details={
                "target_id": str(request.target_id),
                "rejected_by": str(approver_user_id),
                "rejection_reason": rejection_reason,
            },
        )

        return self._to_dto(updated)  # type: ignore[arg-type]

    async def list_approval_requests(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ScanApprovalRequestDTO], int]:
        """List paginated scan approval requests for an organization."""
        models, total = await self.approval_repo.list_approval_requests(
            organization_id, status, page, page_size
        )
        return [self._to_dto(m) for m in models], total

    def _to_dto(self, model: ScanApprovalRequestModel) -> ScanApprovalRequestDTO:
        return ScanApprovalRequestDTO(
            id=model.id,
            organization_id=model.organization_id,
            scan_job_id=model.scan_job_id,
            target_id=model.target_id,
            requested_by=model.requested_by,
            approved_by=model.approved_by,
            status=ApprovalStatus(model.status),
            reason=model.reason,
            rejection_reason=model.rejection_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            expires_at=model.expires_at,
        )
