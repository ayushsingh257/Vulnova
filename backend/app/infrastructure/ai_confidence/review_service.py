"""Human Analyst Review Workflow Service (Phase 12.6).

Handles security analyst review decisions (CONFIRM, FALSE_POSITIVE, ACCEPT_RISK, REQUEST_MORE_EVIDENCE)
and persists audit records.
"""

from datetime import datetime, timezone
import json
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.ai_confidence.dto import FindingReviewDTO, ReviewDecision
from app.infrastructure.database.models.ai_confidence import FindingReviewModel
from app.infrastructure.database.models.assessment import SecurityFindingModel

logger = get_logger("vulnova.finding_review_service")


class FindingReviewService:
    """Service managing human analyst review workflows for vulnerability findings."""

    DECISION_STATUS_MAP = {
        ReviewDecision.CONFIRM: "CONFIRMED",
        ReviewDecision.FALSE_POSITIVE: "FALSE_POSITIVE",
        ReviewDecision.ACCEPT_RISK: "RISK_ACCEPTED",
        ReviewDecision.REQUEST_MORE_EVIDENCE: "NEEDS_REVIEW",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    async def submit_review(
        self,
        finding_id: UUID,
        organization_id: UUID,
        reviewer_id: UUID,
        decision: ReviewDecision,
        comments: Optional[str] = None,
    ) -> FindingReviewDTO:
        """Submit a human analyst review decision for a vulnerability finding."""
        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.id == finding_id,
            SecurityFindingModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        finding = res.scalar_one_or_none()
        if not finding:
            raise ResourceNotFoundException("Security finding not found.")

        now = datetime.now(timezone.utc)
        evidence_snapshot = json.dumps(
            {
                "title": finding.title,
                "severity": finding.severity,
                "target_id": str(finding.scan_target_id),
                "plugin_id": finding.plugin_id,
            }
        )

        review_model = FindingReviewModel(
            id=uuid4(),
            organization_id=organization_id,
            finding_id=finding_id,
            reviewer_id=reviewer_id,
            decision=decision.value,
            comments=comments,
            evidence_snapshot=evidence_snapshot,
            created_at=now,
        )
        self.session.add(review_model)

        # Update finding triage status based on decision
        new_status = self.DECISION_STATUS_MAP.get(decision, "NEEDS_REVIEW")
        finding.status = new_status
        await self.session.flush()

        # Record immutable audit event
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="finding.reviewed",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=reviewer_id,
            details={
                "review_id": str(review_model.id),
                "decision": decision.value,
                "new_status": new_status,
                "comments": comments,
            },
        )

        logger.info(
            "finding_review.submitted",
            org_id=str(organization_id),
            finding_id=str(finding_id),
            reviewer_id=str(reviewer_id),
            decision=decision.value,
            new_status=new_status,
        )

        return FindingReviewDTO(
            id=review_model.id,
            organization_id=organization_id,
            finding_id=finding_id,
            reviewer_id=reviewer_id,
            decision=decision,
            comments=comments,
            evidence_snapshot=evidence_snapshot,
            created_at=now,
        )
