"""Repository managing tenant-isolated AI Finding Explanations & Impact Analysis Records."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.database.models.ai_analysis import (
    AIFindingExplanationModel,
    AIImpactAnalysisModel,
)

logger = get_logger("vulnova.ai_analysis_repository")


class AIAnalysisRepository:
    """Async repository for tenant-isolated AI explanation and impact analysis persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Finding Explanations ────────────────────────────

    async def create_explanation(
        self,
        organization_id: UUID,
        finding_id: UUID,
        vulnerability_summary: str,
        technical_root_cause: str,
        affected_asset_context: str,
        exploitability_analysis: str,
        business_impact: str,
        attack_prerequisites: str,
        severity_reasoning: str,
        remediation_priority: str,
        model_used: str,
        provider_used: str,
        prompt_version: int,
        status: str = "COMPLETED",
        error_message: Optional[str] = None,
    ) -> AIFindingExplanationModel:
        """Create and persist an immutable AI finding explanation record."""
        model = AIFindingExplanationModel(
            organization_id=organization_id,
            finding_id=finding_id,
            vulnerability_summary=vulnerability_summary,
            technical_root_cause=technical_root_cause,
            affected_asset_context=affected_asset_context,
            exploitability_analysis=exploitability_analysis,
            business_impact=business_impact,
            attack_prerequisites=attack_prerequisites,
            severity_reasoning=severity_reasoning,
            remediation_priority=remediation_priority,
            model_used=model_used,
            provider_used=provider_used,
            prompt_version=prompt_version,
            status=status,
            error_message=error_message,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_explanation_by_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> Optional[AIFindingExplanationModel]:
        """Retrieve the most recent explanation for a finding (tenant-isolated)."""
        stmt = (
            select(AIFindingExplanationModel)
            .where(
                AIFindingExplanationModel.organization_id == organization_id,
                AIFindingExplanationModel.finding_id == finding_id,
                AIFindingExplanationModel.status == "COMPLETED",
            )
            .order_by(AIFindingExplanationModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_explanations(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIFindingExplanationModel]:
        """List AI explanations for an organization with pagination."""
        stmt = (
            select(AIFindingExplanationModel)
            .where(
                AIFindingExplanationModel.organization_id == organization_id,
            )
            .order_by(AIFindingExplanationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Impact Analyses ─────────────────────────────────

    async def create_impact_analysis(
        self,
        organization_id: UUID,
        finding_id: UUID,
        technical_impact_summary: str,
        executive_impact_summary: str,
        risk_justification: str,
        affected_business_components: str,
        cvss_interpretation: str,
        epss_context: str,
        exposure_assessment: str,
        evidence_correlation: str,
        model_used: str,
        provider_used: str,
        prompt_version: int,
        status: str = "COMPLETED",
        error_message: Optional[str] = None,
    ) -> AIImpactAnalysisModel:
        """Create and persist an immutable AI impact analysis record."""
        model = AIImpactAnalysisModel(
            organization_id=organization_id,
            finding_id=finding_id,
            technical_impact_summary=technical_impact_summary,
            executive_impact_summary=executive_impact_summary,
            risk_justification=risk_justification,
            affected_business_components=affected_business_components,
            cvss_interpretation=cvss_interpretation,
            epss_context=epss_context,
            exposure_assessment=exposure_assessment,
            evidence_correlation=evidence_correlation,
            model_used=model_used,
            provider_used=provider_used,
            prompt_version=prompt_version,
            status=status,
            error_message=error_message,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_impact_analysis_by_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> Optional[AIImpactAnalysisModel]:
        """Retrieve the most recent impact analysis for a finding (tenant-isolated)."""
        stmt = (
            select(AIImpactAnalysisModel)
            .where(
                AIImpactAnalysisModel.organization_id == organization_id,
                AIImpactAnalysisModel.finding_id == finding_id,
                AIImpactAnalysisModel.status == "COMPLETED",
            )
            .order_by(AIImpactAnalysisModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_impact_analyses(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIImpactAnalysisModel]:
        """List AI impact analyses for an organization with pagination."""
        stmt = (
            select(AIImpactAnalysisModel)
            .where(
                AIImpactAnalysisModel.organization_id == organization_id,
            )
            .order_by(AIImpactAnalysisModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
