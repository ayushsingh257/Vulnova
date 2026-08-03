"""Repository managing tenant-isolated AI Remediation Plans, Steps, and Patch Suggestions."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.infrastructure.database.models.ai_remediation import (
    AIPatchSuggestionModel,
    AIRemediationPlanModel,
    AIRemediationStepModel,
)

logger = get_logger("vulnova.ai_remediation_repository")


class AIRemediationRepository:
    """Async repository for tenant-isolated AI Remediation Plan, Step, and Patch persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_remediation_plan(
        self,
        organization_id: UUID,
        root_finding_id: UUID,
        title: str,
        summary: str,
        technical_solution: str,
        business_solution: str,
        risk_reduction_explanation: str,
        validation_strategy: str,
        composite_risk_score: float,
        model_used: str,
        provider_used: str,
        prompt_version: int,
        ai_confidence_score: float = 1.0,
        effectiveness_confidence_score: float = 1.0,
        requires_backup: bool = False,
        requires_downtime: bool = False,
        rollback_available: bool = True,
        attack_path_id: Optional[UUID] = None,
        cve_id: Optional[str] = None,
        cwe_id: Optional[str] = None,
        affected_version: Optional[str] = None,
        fixed_version: Optional[str] = None,
        status: str = "GENERATED",
        error_message: Optional[str] = None,
        steps_data: Optional[List[Dict[str, Any]]] = None,
        patches_data: Optional[List[Dict[str, Any]]] = None,
    ) -> AIRemediationPlanModel:
        """Create and persist an AI Remediation Plan with child steps and patch suggestions."""
        plan_model = AIRemediationPlanModel(
            organization_id=organization_id,
            root_finding_id=root_finding_id,
            attack_path_id=attack_path_id,
            cve_id=cve_id,
            cwe_id=cwe_id,
            affected_version=affected_version,
            fixed_version=fixed_version,
            title=title,
            summary=summary,
            technical_solution=technical_solution,
            business_solution=business_solution,
            risk_reduction_explanation=risk_reduction_explanation,
            validation_strategy=validation_strategy,
            composite_risk_score=composite_risk_score,
            ai_confidence_score=ai_confidence_score,
            effectiveness_confidence_score=effectiveness_confidence_score,
            requires_backup=requires_backup,
            requires_downtime=requires_downtime,
            rollback_available=rollback_available,
            model_used=model_used,
            provider_used=provider_used,
            prompt_version=prompt_version,
            status=status,
            error_message=error_message,
        )
        self.session.add(plan_model)
        await self.session.flush()

        if steps_data:
            for sdata in steps_data:
                step_model = AIRemediationStepModel(
                    remediation_plan_id=plan_model.id,
                    sequence_number=sdata.get("sequence_number", 1),
                    step_type=sdata.get("step_type", "SECURITY_CONTROL"),
                    title=sdata.get("title", ""),
                    description=sdata.get("description", ""),
                    affected_component=sdata.get("affected_component", ""),
                    recommended_action=sdata.get("recommended_action", ""),
                    validation_command=sdata.get("validation_command"),
                    rollback_strategy=sdata.get("rollback_strategy"),
                    confidence_score=sdata.get("confidence_score", 1.0),
                )
                self.session.add(step_model)

        if patches_data:
            for pdata in patches_data:
                patch_model = AIPatchSuggestionModel(
                    remediation_plan_id=plan_model.id,
                    language=pdata.get("language", "PYTHON"),
                    file_type=pdata.get("file_type", "SOURCE_CODE"),
                    target_file_path=pdata.get("target_file_path"),
                    original_code_snippet=pdata.get("original_code_snippet", ""),
                    proposed_patch_diff=pdata.get("proposed_patch_diff", ""),
                    explanation=pdata.get("explanation", ""),
                    security_impact_notes=pdata.get("security_impact_notes", ""),
                    confidence_score=pdata.get("confidence_score", 1.0),
                )
                self.session.add(patch_model)

        await self.session.flush()
        return await self.get_remediation_plan_by_id(organization_id, plan_model.id)  # type: ignore[return-value]

    async def get_remediation_plan_by_id(
        self, organization_id: UUID, plan_id: UUID
    ) -> Optional[AIRemediationPlanModel]:
        """Retrieve a single remediation plan by ID with child steps and patch suggestions (tenant-isolated)."""
        stmt = (
            select(AIRemediationPlanModel)
            .options(
                selectinload(AIRemediationPlanModel.steps),
                selectinload(AIRemediationPlanModel.patch_suggestions),
            )
            .where(
                AIRemediationPlanModel.id == plan_id,
                AIRemediationPlanModel.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_remediation_plans_by_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[AIRemediationPlanModel]:
        """List remediation plans associated with a finding (tenant-isolated)."""
        stmt = (
            select(AIRemediationPlanModel)
            .options(
                selectinload(AIRemediationPlanModel.steps),
                selectinload(AIRemediationPlanModel.patch_suggestions),
            )
            .where(
                AIRemediationPlanModel.organization_id == organization_id,
                AIRemediationPlanModel.root_finding_id == finding_id,
            )
            .order_by(AIRemediationPlanModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_remediation_plans(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIRemediationPlanModel]:
        """List remediation plans for an organization with pagination."""
        stmt = (
            select(AIRemediationPlanModel)
            .options(
                selectinload(AIRemediationPlanModel.steps),
                selectinload(AIRemediationPlanModel.patch_suggestions),
            )
            .where(
                AIRemediationPlanModel.organization_id == organization_id,
            )
            .order_by(AIRemediationPlanModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_review_status(
        self,
        organization_id: UUID,
        plan_id: UUID,
        status: str,
        reviewer_id: UUID,
        review_notes: Optional[str] = None,
    ) -> Optional[AIRemediationPlanModel]:
        """Update analyst review status and feedback notes on a remediation plan."""
        model = await self.get_remediation_plan_by_id(organization_id, plan_id)
        if not model:
            return None

        model.status = status
        model.reviewed_by = reviewer_id
        model.review_notes = review_notes
        model.reviewed_at = datetime.utcnow()
        await self.session.flush()
        return model
