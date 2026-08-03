"""Finding Triage & Automated Suppression Application Service."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    BulkTriageRequest,
    CreateSuppressionRuleRequest,
    FindingTriageHistoryDTO,
    SuppressionRuleDTO,
    TriageFindingRequest,
    TriageResponse,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.domain.entities.assessment import Finding
from app.domain.entities.triage import FindingTriageStatus, SuppressionRuleType
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)
from app.infrastructure.database.repositories.finding_triage_repository import (
    FindingTriageRepository,
)

logger = get_logger("vulnova.finding_triage_service")


class FindingTriageService:
    """Application service managing analyst finding triage decisions, automated suppression rules, and triage audit history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.triage_repo = FindingTriageRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.audit_service = AuditLogService(session)

    async def triage_finding(
        self, current_user: UserModel, finding_id: UUID, req: TriageFindingRequest
    ) -> TriageResponse:
        """Triage a single finding, updating lifecycle status and recording an audit trail event."""
        org_id = current_user.organization_id

        # Validate status enum string
        try:
            target_status = FindingTriageStatus(req.status.upper())
        except ValueError as err:
            raise ValidationException(
                f"Invalid triage status '{req.status}'. Allowed values: {[s.value for s in FindingTriageStatus]}"
            ) from err

        # Query finding enforcing tenant boundary
        finding_model = await self.assessment_repo.get_finding_by_id(org_id, finding_id)
        if not finding_model:
            raise ResourceNotFoundException("Security finding not found.")

        prev_status = (
            getattr(finding_model, "triage_status", "UNREVIEWED") or "UNREVIEWED"
        )

        # Parse optional risk accepted until date
        risk_until_dt: Optional[datetime] = None
        if req.risk_accepted_until:
            try:
                risk_until_dt = datetime.fromisoformat(
                    req.risk_accepted_until.replace("Z", "+00:00")
                )
            except ValueError as err:
                raise ValidationException(
                    "Invalid ISO format for risk_accepted_until date."
                ) from err

        # Record triage history audit record
        await self.triage_repo.record_triage_action(
            organization_id=org_id,
            finding_id=finding_id,
            new_status=target_status.value,
            previous_status=prev_status,
            actor_user_id=current_user.id,
            comment=req.comment,
            risk_accepted_until=risk_until_dt,
        )

        # Log audit trail using existing AuditLogService pattern
        await self.audit_service.record_event(
            organization_id=org_id,
            action="finding.triaged",
            resource_type="security_finding",
            resource_id=str(finding_id),
            actor_user_id=current_user.id,
            details={
                "previous_status": prev_status,
                "new_status": target_status.value,
                "comment": req.comment,
            },
        )

        logger.info(
            "finding_triage.triaged",
            finding_id=str(finding_id),
            previous_status=prev_status,
            new_status=target_status.value,
            actor_id=str(current_user.id),
        )

        return TriageResponse(
            finding_id=str(finding_id),
            previous_status=prev_status,
            new_status=target_status.value,
            message=f"Finding successfully triaged from '{prev_status}' to '{target_status.value}'.",
        )

    async def bulk_triage_findings(
        self, current_user: UserModel, req: BulkTriageRequest
    ) -> List[TriageResponse]:
        """Perform bulk triage updates across multiple finding records for a tenant."""
        responses: List[TriageResponse] = []
        for fid_str in req.finding_ids:
            try:
                fid = UUID(fid_str)
                single_req = TriageFindingRequest(
                    status=req.status, comment=req.comment
                )
                res = await self.triage_finding(current_user, fid, single_req)
                responses.append(res)
            except Exception as e:
                logger.warning(
                    "finding_triage.bulk_item_failed",
                    finding_id=fid_str,
                    error=str(e),
                )
        return responses

    async def evaluate_suppression_rules(
        self, organization_id: UUID, findings: List[Finding]
    ) -> List[Finding]:
        """Evaluate active suppression rules against findings post-assessment without altering risk scores or evidence."""
        rules = await self.triage_repo.list_suppression_rules(
            organization_id, active_only=True
        )
        if not rules:
            return findings

        for f in findings:
            for rule in rules:
                matched = False
                rtype = rule.rule_type

                if rtype == SuppressionRuleType.EXACT_CWE.value and rule.cwe_id:
                    matched = f.cwe_id == rule.cwe_id
                elif rtype == SuppressionRuleType.PLUGIN_ID.value and rule.plugin_id:
                    matched = f.plugin_id == rule.plugin_id
                elif (
                    rtype == SuppressionRuleType.TARGET_PATTERN.value
                    and rule.target_pattern
                ):
                    matched = bool(
                        rule.target_pattern.lower() in (f.title or "").lower()
                        or rule.target_pattern.lower() in (f.description or "").lower()
                    )
                elif rtype == SuppressionRuleType.COMPOSITE.value:
                    cwe_match = not rule.cwe_id or f.cwe_id == rule.cwe_id
                    plugin_match = not rule.plugin_id or f.plugin_id == rule.plugin_id
                    matched = cwe_match and plugin_match

                if matched:
                    # Overlay suppression status metadata without corrupting original metrics or evidence
                    if f.evidence is not None:
                        f.evidence["suppressed_by_rule_id"] = str(rule.id)
                        f.evidence["suppression_reason"] = rule.reason
                    break

        return findings

    async def create_suppression_rule(
        self, current_user: UserModel, req: CreateSuppressionRuleRequest
    ) -> SuppressionRuleDTO:
        """Create an automated finding suppression rule for an organization."""
        org_id = current_user.organization_id

        try:
            rtype = SuppressionRuleType(req.rule_type.upper())
        except ValueError as err:
            raise ValidationException(
                f"Invalid rule_type '{req.rule_type}'. Allowed values: {[t.value for t in SuppressionRuleType]}"
            ) from err

        expires_dt: Optional[datetime] = None
        if req.expires_at:
            try:
                expires_dt = datetime.fromisoformat(
                    req.expires_at.replace("Z", "+00:00")
                )
            except ValueError as err:
                raise ValidationException(
                    "Invalid ISO format for expires_at timestamp."
                ) from err

        rule_model = await self.triage_repo.create_suppression_rule(
            organization_id=org_id,
            created_by_user_id=current_user.id,
            name=req.name,
            rule_type=rtype.value,
            reason=req.reason,
            plugin_id=req.plugin_id,
            cwe_id=req.cwe_id,
            target_pattern=req.target_pattern,
            expires_at=expires_dt,
        )

        await self.audit_service.record_event(
            organization_id=org_id,
            action="suppression_rule.created",
            resource_type="suppression_rule",
            resource_id=str(rule_model.id),
            actor_user_id=current_user.id,
            details={
                "name": rule_model.name,
                "rule_type": rule_model.rule_type,
                "reason": rule_model.reason,
            },
        )

        return SuppressionRuleDTO(
            id=str(rule_model.id),
            name=rule_model.name,
            rule_type=rule_model.rule_type,
            reason=rule_model.reason,
            plugin_id=rule_model.plugin_id,
            cwe_id=rule_model.cwe_id,
            target_pattern=rule_model.target_pattern,
            is_active=rule_model.is_active,
            created_by_user_id=str(current_user.id),
            expires_at=str(rule_model.expires_at) if rule_model.expires_at else None,
            created_at=str(rule_model.created_at),
        )

    async def list_suppression_rules(
        self, current_user: UserModel
    ) -> List[SuppressionRuleDTO]:
        """List active finding suppression rules for tenant organization."""
        org_id = current_user.organization_id
        rules = await self.triage_repo.list_suppression_rules(org_id, active_only=True)
        return [
            SuppressionRuleDTO(
                id=str(r.id),
                name=r.name,
                rule_type=r.rule_type,
                reason=r.reason,
                plugin_id=r.plugin_id,
                cwe_id=r.cwe_id,
                target_pattern=r.target_pattern,
                is_active=r.is_active,
                created_by_user_id=(
                    str(r.created_by_user_id) if r.created_by_user_id else None
                ),
                expires_at=str(r.expires_at) if r.expires_at else None,
                created_at=str(r.created_at),
            )
            for r in rules
        ]

    async def delete_suppression_rule(
        self, current_user: UserModel, rule_id: UUID
    ) -> bool:
        """Deactivate a finding suppression rule and log audit event."""
        org_id = current_user.organization_id
        deleted = await self.triage_repo.delete_suppression_rule(org_id, rule_id)
        if deleted:
            await self.audit_service.record_event(
                organization_id=org_id,
                action="suppression_rule.deleted",
                resource_type="suppression_rule",
                resource_id=str(rule_id),
                actor_user_id=current_user.id,
                details={"rule_id": str(rule_id)},
            )
        return deleted

    async def get_finding_triage_history(
        self, current_user: UserModel, finding_id: UUID
    ) -> List[FindingTriageHistoryDTO]:
        """Query triage audit trail history for a finding."""
        org_id = current_user.organization_id
        history_models = await self.triage_repo.get_triage_history(org_id, finding_id)
        return [
            FindingTriageHistoryDTO(
                id=str(h.id),
                finding_id=str(h.finding_id),
                actor_user_id=str(h.actor_user_id) if h.actor_user_id else None,
                previous_status=h.previous_status,
                new_status=h.new_status,
                comment=h.comment,
                risk_accepted_until=(
                    str(h.risk_accepted_until) if h.risk_accepted_until else None
                ),
                created_at=str(h.created_at),
            )
            for h in history_models
        ]
