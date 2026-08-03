"""Repository for managing AI confidence analyses, similarity matches, and calibration feedback tracking."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.ai_confidence import (
    AIFindingConfidenceAnalysisModel,
    AIFindingSimilarityMatchModel,
)


class AIConfidenceRepository:
    """Async repository for tenant-isolated AI confidence analysis operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_confidence_analysis(
        self,
        organization_id: UUID,
        finding_id: UUID,
        classification: str,
        confidence_score: float,
        evidence_quality_score: float,
        reasoning: str,
        supporting_evidence: str,
        contradicting_evidence: str,
        missing_information: str,
        validation_requirements: str,
        recommendation: str,
        composite_risk_score: float,
        model_used: str,
        provider_used: str,
        prompt_version: int = 1,
        status: str = "GENERATED",
        error_message: Optional[str] = None,
        similarity_matches_data: Optional[List[Dict[str, Any]]] = None,
    ) -> AIFindingConfidenceAnalysisModel:
        """Create and persist an AI confidence analysis record with optional similarity matches."""
        analysis = AIFindingConfidenceAnalysisModel(
            organization_id=organization_id,
            finding_id=finding_id,
            classification=classification,
            confidence_score=confidence_score,
            evidence_quality_score=evidence_quality_score,
            reasoning=reasoning,
            supporting_evidence=supporting_evidence,
            contradicting_evidence=contradicting_evidence,
            missing_information=missing_information,
            validation_requirements=validation_requirements,
            recommendation=recommendation,
            composite_risk_score=composite_risk_score,
            model_used=model_used,
            provider_used=provider_used,
            prompt_version=prompt_version,
            status=status,
            error_message=error_message,
        )

        if similarity_matches_data:
            for sim in similarity_matches_data:
                match_model = AIFindingSimilarityMatchModel(
                    organization_id=organization_id,
                    source_finding_id=finding_id,
                    matched_finding_id=sim["matched_finding_id"],
                    similarity_score=sim["similarity_score"],
                    similarity_reason=sim["similarity_reason"],
                    matched_signals=sim.get("matched_signals", []),
                    status=sim.get("status", "GENERATED"),
                )
                analysis.similarity_matches.append(match_model)

        self.session.add(analysis)
        await self.session.flush()
        return analysis

    async def get_confidence_analysis_by_id(
        self, organization_id: UUID, analysis_id: UUID
    ) -> Optional[AIFindingConfidenceAnalysisModel]:
        """Fetch single confidence analysis by ID with tenant boundary isolation."""
        stmt = (
            select(AIFindingConfidenceAnalysisModel)
            .options(selectinload(AIFindingConfidenceAnalysisModel.similarity_matches))
            .where(
                AIFindingConfidenceAnalysisModel.organization_id == organization_id,
                AIFindingConfidenceAnalysisModel.id == analysis_id,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_latest_confidence_analysis_for_finding(
        self, organization_id: UUID, finding_id: UUID
    ) -> Optional[AIFindingConfidenceAnalysisModel]:
        """Fetch the most recent confidence analysis for a finding."""
        stmt = (
            select(AIFindingConfidenceAnalysisModel)
            .options(selectinload(AIFindingConfidenceAnalysisModel.similarity_matches))
            .where(
                AIFindingConfidenceAnalysisModel.organization_id == organization_id,
                AIFindingConfidenceAnalysisModel.finding_id == finding_id,
            )
            .order_by(AIFindingConfidenceAnalysisModel.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_confidence_analyses(
        self, organization_id: UUID, limit: int = 50, offset: int = 0
    ) -> List[AIFindingConfidenceAnalysisModel]:
        """List organizational confidence analysis history with pagination."""
        stmt = (
            select(AIFindingConfidenceAnalysisModel)
            .options(selectinload(AIFindingConfidenceAnalysisModel.similarity_matches))
            .where(AIFindingConfidenceAnalysisModel.organization_id == organization_id)
            .order_by(AIFindingConfidenceAnalysisModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_similarity_matches(
        self,
        organization_id: UUID,
        source_finding_id: UUID,
        matches: List[Dict[str, Any]],
        confidence_analysis_id: Optional[UUID] = None,
    ) -> List[AIFindingSimilarityMatchModel]:
        """Bulk insert duplicate finding similarity matches."""
        models: List[AIFindingSimilarityMatchModel] = []
        for m in matches:
            match_model = AIFindingSimilarityMatchModel(
                organization_id=organization_id,
                confidence_analysis_id=confidence_analysis_id,
                source_finding_id=source_finding_id,
                matched_finding_id=m["matched_finding_id"],
                similarity_score=m["similarity_score"],
                similarity_reason=m["similarity_reason"],
                matched_signals=m.get("matched_signals", []),
                status=m.get("status", "GENERATED"),
            )
            self.session.add(match_model)
            models.append(match_model)

        await self.session.flush()
        return models

    async def list_similarity_matches(
        self, organization_id: UUID, finding_id: UUID
    ) -> List[AIFindingSimilarityMatchModel]:
        """Retrieve similarity matches for a finding."""
        stmt = (
            select(AIFindingSimilarityMatchModel)
            .where(
                AIFindingSimilarityMatchModel.organization_id == organization_id,
                AIFindingSimilarityMatchModel.source_finding_id == finding_id,
            )
            .order_by(AIFindingSimilarityMatchModel.similarity_score.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_review_status(
        self,
        organization_id: UUID,
        analysis_id: UUID,
        status: str,
        reviewer_id: UUID,
        review_notes: Optional[str] = None,
    ) -> Optional[AIFindingConfidenceAnalysisModel]:
        """Record SOC analyst review feedback and track AI confidence score calibration metadata."""
        analysis = await self.get_confidence_analysis_by_id(
            organization_id, analysis_id
        )
        if not analysis:
            return None

        now = datetime.utcnow()
        analysis.status = status
        analysis.reviewed_by = reviewer_id
        analysis.reviewed_at = now
        analysis.review_notes = review_notes

        # Record AI Confidence Score Calibration Tracking
        analysis.predicted_confidence_score = analysis.confidence_score
        analysis.analyst_final_decision = status
        analysis.feedback_timestamp = now

        # Calculate accuracy delta: 1.0 if accepted, 0.0 if rejected/false-positive mismatch
        if status in ("ACCEPTED", "APPROVED", "TRUE_POSITIVE"):
            analysis.confidence_accuracy_delta = round(
                1.0 - analysis.confidence_score, 4
            )
        elif status in ("REJECTED", "FALSE_POSITIVE"):
            analysis.confidence_accuracy_delta = round(
                0.0 - analysis.confidence_score, 4
            )
        else:
            analysis.confidence_accuracy_delta = 0.0

        await self.session.flush()
        return analysis
