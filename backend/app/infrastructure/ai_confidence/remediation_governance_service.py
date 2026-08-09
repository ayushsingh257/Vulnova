"""Remediation Approval Governance Service (Phase 12.6).

Enforces human-in-the-loop remediation recommendation approval gates.
AI must NEVER autonomously modify target systems or execute remediation without analyst approval.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.infrastructure.ai_confidence.dto import (
    RemediationApprovalDTO,
    RemediationStatus,
)
from app.infrastructure.database.models.ai_confidence import (
    RemediationApprovalHistoryModel,
)
from app.infrastructure.database.models.ai_remediation import AIRemediationPlanModel

logger = get_logger("vulnova.remediation_governance_service")


class RemediationGovernanceService:
    """Service enforcing human approval gates for AI-generated remediation plans."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    async def approve_remediation(
        self,
        remediation_plan_id: UUID,
        organization_id: UUID,
        approver_user_id: UUID,
        notes: Optional[str] = None,
    ) -> RemediationApprovalDTO:
        """Approve an AI-recommended remediation plan for implementation (Analyst only)."""
        stmt = select(AIRemediationPlanModel).where(
            AIRemediationPlanModel.id == remediation_plan_id,
            AIRemediationPlanModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise ResourceNotFoundException("AI remediation plan not found.")

        previous_state = plan.status or RemediationStatus.AI_RECOMMENDED.value
        new_state = RemediationStatus.APPROVED_FOR_IMPLEMENTATION.value

        target_finding_id = (
            getattr(plan, "root_finding_id", None)
            or getattr(plan, "finding_id", None)
            or uuid4()
        )

        now = datetime.now(timezone.utc)
        plan.status = new_state
        await self.session.flush()

        history_model = RemediationApprovalHistoryModel(
            id=uuid4(),
            organization_id=organization_id,
            remediation_plan_id=remediation_plan_id,
            finding_id=target_finding_id,
            previous_state=previous_state,
            new_state=new_state,
            action_by=approver_user_id,
            notes=notes
            or "Human analyst approved AI remediation plan for implementation",
            created_at=now,
        )
        self.session.add(history_model)
        await self.session.flush()

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="remediation.approved",
            resource_type="remediation_plan",
            resource_id=str(remediation_plan_id),
            actor_user_id=approver_user_id,
            details={
                "finding_id": str(target_finding_id),
                "previous_state": previous_state,
                "new_state": new_state,
                "notes": notes,
            },
        )

        logger.info(
            "remediation_governance.approved",
            org_id=str(organization_id),
            remediation_plan_id=str(remediation_plan_id),
            approver_id=str(approver_user_id),
        )

        return RemediationApprovalDTO(
            id=history_model.id,
            organization_id=organization_id,
            remediation_plan_id=remediation_plan_id,
            finding_id=target_finding_id,
            previous_state=previous_state,
            new_state=RemediationStatus.APPROVED_FOR_IMPLEMENTATION,
            action_by=approver_user_id,
            notes=notes,
            created_at=now,
        )

    async def reject_remediation(
        self,
        remediation_plan_id: UUID,
        organization_id: UUID,
        approver_user_id: UUID,
        notes: Optional[str] = None,
    ) -> RemediationApprovalDTO:
        """Reject an AI remediation plan recommendations with analyst rationale."""
        stmt = select(AIRemediationPlanModel).where(
            AIRemediationPlanModel.id == remediation_plan_id,
            AIRemediationPlanModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if not plan:
            raise ResourceNotFoundException("AI remediation plan not found.")

        previous_state = plan.status or RemediationStatus.AI_RECOMMENDED.value
        new_state = RemediationStatus.REJECTED.value
        target_finding_id = (
            getattr(plan, "root_finding_id", None)
            or getattr(plan, "finding_id", None)
            or uuid4()
        )

        now = datetime.now(timezone.utc)
        plan.status = new_state
        await self.session.flush()

        history_model = RemediationApprovalHistoryModel(
            id=uuid4(),
            organization_id=organization_id,
            remediation_plan_id=remediation_plan_id,
            finding_id=target_finding_id,
            previous_state=previous_state,
            new_state=new_state,
            action_by=approver_user_id,
            notes=notes or "Human analyst rejected AI remediation recommendations",
            created_at=now,
        )
        self.session.add(history_model)
        await self.session.flush()

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="remediation.rejected",
            resource_type="remediation_plan",
            resource_id=str(remediation_plan_id),
            actor_user_id=approver_user_id,
            details={
                "finding_id": str(target_finding_id),
                "previous_state": previous_state,
                "new_state": new_state,
                "notes": notes,
            },
        )

        logger.info(
            "remediation_governance.rejected",
            org_id=str(organization_id),
            remediation_plan_id=str(remediation_plan_id),
            approver_id=str(approver_user_id),
        )

        return RemediationApprovalDTO(
            id=history_model.id,
            organization_id=organization_id,
            remediation_plan_id=remediation_plan_id,
            finding_id=target_finding_id,
            previous_state=previous_state,
            new_state=RemediationStatus.REJECTED,
            action_by=approver_user_id,
            notes=notes,
            created_at=now,
        )

    def validate_execution_allowed(self, plan: AIRemediationPlanModel) -> None:
        """Security guard enforcing human approval before remediation patch execution."""
        if plan.status != RemediationStatus.APPROVED_FOR_IMPLEMENTATION.value:
            raise ValidationException(
                "Remediation patch execution blocked. Human analyst approval (APPROVED_FOR_IMPLEMENTATION) is strictly required."
            )
